import time
from datetime import datetime
from typing import Dict
import logging

from .database.connection import DatabaseManager
from .scraper.base import BaseScraper
from .scraper.tracks import get_scraper_for_track
from .alerts.engine import AlertEngine
from .notifications.manager import NotificationManager
from .utils.config import config

logger = logging.getLogger(__name__)


class OddsScheduler:
    """Schedule and coordinate scraping activities"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.config = config
        self.scrapers: Dict[str, BaseScraper] = {}
        self.alert_engine = AlertEngine(db_manager)
        self.notification_manager = NotificationManager(db_manager)
        self.running = False
        self.last_scrape_times: Dict[str, datetime] = {}

        self._initialize_scrapers()

    def _initialize_scrapers(self):
        """Initialize scrapers for configured tracks"""
        for track_config in self.config.get_tracks(enabled_only=True):
            try:
                scraper = get_scraper_for_track(track_config.name)
                if scraper:
                    self.scrapers[track_config.name] = scraper
                    logger.info(f"Initialized scraper for {track_config.name}")
                else:
                    logger.warning(f"No scraper available for {track_config.name}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize scraper for " f"{track_config.name}: {e}"
                )

    def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")

    def run_cycle(self):
        """Run a single scheduling cycle"""
        if not self.running:
            return

        current_time = datetime.now()

        for track_name, scraper in self.scrapers.items():
            try:
                # Check if it's time to scrape this track
                if self._should_scrape(track_name, current_time):
                    self._scrape_track(track_name, scraper)
                    self.last_scrape_times[track_name] = current_time

            except Exception as e:
                logger.error(f"Error scraping {track_name}: {e}", exc_info=True)

        # Send any pending notifications
        self.notification_manager.send_unsent_alerts()

        # Sleep before next cycle
        time.sleep(10)  # Check every 10 seconds

    def run_single_cycle(self):
        """Run a single scraping cycle for all tracks"""
        for track_name, scraper in self.scrapers.items():
            try:
                self._scrape_track(track_name, scraper)
            except Exception as e:
                logger.error(f"Error scraping {track_name}: {e}", exc_info=True)

    def _should_scrape(self, track_name: str, current_time: datetime) -> bool:
        """Determine if a track should be scraped"""
        # Get last scrape time
        last_scrape = self.last_scrape_times.get(track_name)
        if not last_scrape:
            return True  # Never scraped

        # Get scraping interval from config
        interval = self._get_scrape_interval(track_name, current_time)

        # Check if enough time has passed
        elapsed = (current_time - last_scrape).seconds
        return elapsed >= interval

    def _get_scrape_interval(self, track_name: str, current_time: datetime) -> int:
        """Get scraping interval based on proximity to post time"""
        # Check if any races are near post time
        # near_post_threshold = self.config.get(
        #     'scraping.near_post_threshold', 600)
        # near_post_interval = self.config.get(
        #     'scraping.near_post_interval', 60)
        default_interval = self.config.get("scraping.default_interval", 300)

        # For now, use default interval
        # In production, would query upcoming races
        return default_interval

    def _scrape_track(self, track_name: str, scraper: BaseScraper):
        """Scrape a single track"""
        logger.info(f"Scraping {track_name}...")

        # Get today's races
        races = scraper.get_races(datetime.now())

        for race in races:
            try:
                # Store race in database
                race_id = self._store_race(track_name, race)

                # Scrape race data
                race_data = scraper.scrape_race_data(str(race_id))

                # Store odds snapshot
                snapshot = self._store_snapshot(race_id, race_data)

                # Evaluate alerts
                alerts = self.alert_engine.evaluate_snapshot(snapshot)

                # Send notifications
                for alert in alerts:
                    self.notification_manager.notify(alert)

                logger.info(
                    f"Scraped race {race_id}: {len(alerts)} alerts " f"triggered"
                )

            except Exception as e:
                logger.error(f"Error processing race {race.get('race_number')}: {e}")

    def _store_race(self, track_name: str, race_data: Dict) -> int:
        """Store or update race in database"""
        # Get track ID
        track_query = "SELECT track_id FROM track WHERE name = ?"
        track_result = self.db.execute_query(track_query, (track_name,))

        if not track_result:
            # Insert track
            insert_track = "INSERT INTO track (name) VALUES (?)"
            track_id = self.db.execute_insert(insert_track, (track_name,))
        else:
            track_id = track_result[0]["track_id"]

        # Check if race exists
        race_query = """
            SELECT race_id FROM race
            WHERE track_id = ? AND race_date = ? AND race_number = ?
        """
        race_result = self.db.execute_query(
            race_query, (track_id, race_data.get("date"), race_data.get("race_number"))
        )

        if race_result:
            return race_result[0]["race_id"]

        # Insert race
        insert_race = """
            INSERT INTO race (track_id, race_date, race_number,
                             post_time, status)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.db.execute_insert(
            insert_race,
            (
                track_id,
                race_data.get("date"),
                race_data.get("race_number"),
                race_data.get("post_time"),
                "scheduled",
            ),
        )

    def _store_snapshot(self, race_id: int, race_data: Dict) -> Dict:
        """Store odds snapshot in database"""
        snapshot = {
            "race_id": race_id,
            "fetched_at": datetime.now(),
            "track": race_data.get("track"),
            "entries": [],
        }

        # Store win odds
        if race_data.get("win_odds"):
            for horse in race_data["win_odds"].get("horses", []):
                # Store or get horse
                horse_id = self._store_horse(horse.get("name"))

                # Store or get entry
                entry_id = self._store_entry(
                    race_id, horse_id, horse.get("program_number")
                )

                # Store odds snapshot
                insert_odds = """
                    INSERT INTO odds_snapshot (
                        race_id, entry_id, fetched_at,
                        win_odds, win_odds_decimal, win_pool_amount,
                        total_win_pool
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                self.db.execute_insert(
                    insert_odds,
                    (
                        race_id,
                        entry_id,
                        snapshot["fetched_at"],
                        horse.get("odds"),
                        horse.get("odds"),
                        horse.get("pool_amount"),
                        race_data["win_odds"].get("total_pool"),
                    ),
                )

                snapshot["entries"].append(
                    {
                        "entry_id": entry_id,
                        "horse_name": horse.get("name"),
                        "program_number": horse.get("program_number"),
                        "win_odds_decimal": horse.get("odds"),
                        "win_pool_amount": horse.get("pool_amount"),
                    }
                )

        # Store exacta probables
        if race_data.get("exacta_probables"):
            snapshot["exacta_probables"] = race_data["exacta_probables"]

            for combo, payout in (
                race_data["exacta_probables"].get("probables", {}).items()
            ):
                first, second = combo.split("-")
                insert_exacta = """
                    INSERT INTO exacta_probable (
                        race_id, fetched_at, first_horse, second_horse,
                        payout, total_exacta_pool
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """

                self.db.execute_insert(
                    insert_exacta,
                    (
                        race_id,
                        snapshot["fetched_at"],
                        first,
                        second,
                        payout,
                        race_data["exacta_probables"].get("total_pool"),
                    ),
                )

        return snapshot

    def _store_horse(self, name: str) -> int:
        """Store or get horse ID"""
        if not name:
            name = "Unknown"

        query = "SELECT horse_id FROM horse WHERE name = ?"
        result = self.db.execute_query(query, (name,))

        if result:
            return result[0]["horse_id"]

        insert = "INSERT INTO horse (name) VALUES (?)"
        return self.db.execute_insert(insert, (name,))

    def _store_entry(self, race_id: int, horse_id: int, program_number: str) -> int:
        """Store or get entry ID"""
        if not program_number:
            program_number = "0"

        query = "SELECT entry_id FROM entry " "WHERE race_id = ? AND program_number = ?"
        result = self.db.execute_query(query, (race_id, program_number))

        if result:
            return result[0]["entry_id"]

        insert = """
            INSERT INTO entry (race_id, horse_id, program_number)
            VALUES (?, ?, ?)
        """
        return self.db.execute_insert(insert, (race_id, horse_id, program_number))
