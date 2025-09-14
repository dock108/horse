"""Tests for scheduler module"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.scheduler import OddsScheduler


class TestOddsScheduler:
    """Test odds tracking scheduler"""

    @pytest.fixture
    def mock_db(self):
        """Mock database manager"""
        db = Mock()
        db.execute_query.return_value = []
        db.execute_insert.return_value = 1
        return db

    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        config = Mock()
        config.get_tracks.return_value = [
            Mock(name="Track1", enabled=True),
            Mock(name="Track2", enabled=True)
        ]
        config.get.return_value = 300  # Default interval
        return config

    @pytest.fixture
    def scheduler(self, mock_db, mock_config):
        """Create scheduler with mocks"""
        with patch("src.scheduler.config", mock_config):
            with patch("src.scheduler.AlertEngine") as mock_alert_engine:
                with patch("src.scheduler.NotificationManager") as mock_notif:
                    scheduler = OddsScheduler()
                    scheduler.db = mock_db
                    scheduler.config = mock_config
                    return scheduler

    def test_init(self, mock_config):
        """Test scheduler initialization"""
        with patch("src.scheduler.config", mock_config):
            with patch("src.scheduler.DatabaseManager"):
                with patch("src.scheduler.AlertEngine"):
                    with patch("src.scheduler.NotificationManager"):
                        scheduler = OddsScheduler()
                        assert scheduler.running is False
                        assert scheduler.scrapers == {}
                        assert scheduler.last_scrape_times == {}

    def test_init_scrapers(self, scheduler):
        """Test scraper initialization"""
        with patch("src.scheduler.get_scraper_for_track") as mock_get_scraper:
            mock_scraper = Mock()
            mock_get_scraper.return_value = mock_scraper

            scheduler._init_scrapers()

            assert mock_get_scraper.call_count == 2
            assert "Track1" in scheduler.scrapers
            assert "Track2" in scheduler.scrapers

    def test_init_scrapers_with_failure(self, scheduler):
        """Test scraper initialization with failures"""
        with patch("src.scheduler.get_scraper_for_track") as mock_get_scraper:
            mock_get_scraper.side_effect = [Mock(), None]  # Second scraper fails

            scheduler._init_scrapers()

            assert len(scheduler.scrapers) == 1

    def test_start_stop(self, scheduler):
        """Test starting and stopping scheduler"""
        assert scheduler.running is False

        scheduler.start()
        assert scheduler.running is True

        scheduler.stop()
        assert scheduler.running is False

    def test_should_scrape_never_scraped(self, scheduler):
        """Test should scrape when never scraped before"""
        result = scheduler._should_scrape("Track1", datetime.now())
        assert result is True

    def test_should_scrape_interval_passed(self, scheduler):
        """Test should scrape when interval has passed"""
        past_time = datetime.now() - timedelta(minutes=10)
        scheduler.last_scrape_times["Track1"] = past_time

        result = scheduler._should_scrape("Track1", datetime.now())
        assert result is True

    def test_should_scrape_too_soon(self, scheduler):
        """Test should not scrape when too soon"""
        recent_time = datetime.now() - timedelta(seconds=10)
        scheduler.last_scrape_times["Track1"] = recent_time

        result = scheduler._should_scrape("Track1", datetime.now())
        assert result is False

    def test_get_scrape_interval(self, scheduler):
        """Test getting scrape interval"""
        scheduler.config.get.return_value = 300

        interval = scheduler._get_scrape_interval("Track1", datetime.now())
        assert interval == 300

    def test_run_single_cycle(self, scheduler):
        """Test running single scraping cycle"""
        mock_scraper = Mock()
        mock_scraper.get_races.return_value = []
        scheduler.scrapers = {"Track1": mock_scraper}

        with patch.object(scheduler, "_scrape_track") as mock_scrape:
            scheduler.run_single_cycle()
            mock_scrape.assert_called_once_with("Track1", mock_scraper)

    def test_scrape_track(self, scheduler, mock_db):
        """Test scraping a track"""
        mock_scraper = Mock()
        mock_scraper.get_races.return_value = [
            {
                "race_number": 1,
                "date": "2024-01-01",
                "post_time": "14:00",
                "track": "Track1",
                "win_odds": {"horses": [{"name": "Horse1", "odds": 5.0}]}
            }
        ]

        # Mock internal methods
        scheduler._store_race = Mock(return_value=1)
        scheduler._store_snapshot = Mock(return_value={"race_id": 1, "entries": []})
        scheduler.alert_engine.evaluate_snapshot = Mock(return_value=[])

        scheduler._scrape_track("Track1", mock_scraper)

        mock_scraper.get_races.assert_called_once()
        scheduler._store_race.assert_called_once()
        scheduler._store_snapshot.assert_called_once()
        scheduler.alert_engine.evaluate_snapshot.assert_called_once()

    def test_store_race_new(self, scheduler, mock_db):
        """Test storing new race"""
        # No existing track
        mock_db.execute_query.side_effect = [[], []]  # No track, no race
        mock_db.execute_insert.side_effect = [10, 20]  # Track ID, Race ID

        race_data = {
            "date": "2024-01-01",
            "race_number": 1,
            "post_time": "14:00"
        }

        race_id = scheduler._store_race("Track1", race_data)

        assert race_id == 20
        assert mock_db.execute_insert.call_count == 2

    def test_store_race_existing(self, scheduler, mock_db):
        """Test storing existing race"""
        # Existing track and race
        mock_db.execute_query.side_effect = [
            [{"track_id": 10}],  # Track exists
            [{"race_id": 20}]    # Race exists
        ]

        race_data = {
            "date": "2024-01-01",
            "race_number": 1,
            "post_time": "14:00"
        }

        race_id = scheduler._store_race("Track1", race_data)

        assert race_id == 20
        mock_db.execute_insert.assert_not_called()

    def test_store_snapshot(self, scheduler, mock_db):
        """Test storing odds snapshot"""
        race_data = {
            "track": "Track1",
            "win_odds": {
                "total_pool": 100000,
                "horses": [
                    {
                        "name": "Horse1",
                        "program_number": "1",
                        "odds": 5.0,
                        "pool_amount": 20000
                    }
                ]
            }
        }

        scheduler._store_horse = Mock(return_value=1)
        scheduler._store_entry = Mock(return_value=2)

        snapshot = scheduler._store_snapshot(1, race_data)

        assert snapshot["race_id"] == 1
        assert len(snapshot["entries"]) == 1
        assert snapshot["entries"][0]["horse_name"] == "Horse1"
        mock_db.execute_insert.assert_called()

    def test_store_snapshot_with_exacta(self, scheduler, mock_db):
        """Test storing snapshot with exacta probables"""
        race_data = {
            "track": "Track1",
            "win_odds": {"horses": []},
            "exacta_probables": {
                "total_pool": 50000,
                "probables": {
                    "1-2": 25.50,
                    "1-3": 45.00
                }
            }
        }

        snapshot = scheduler._store_snapshot(1, race_data)

        assert "exacta_probables" in snapshot
        assert mock_db.execute_insert.call_count == 2  # Two exacta combos

    def test_store_horse_new(self, scheduler, mock_db):
        """Test storing new horse"""
        mock_db.execute_query.return_value = []
        mock_db.execute_insert.return_value = 123

        horse_id = scheduler._store_horse("Thunder")

        assert horse_id == 123
        mock_db.execute_insert.assert_called_with(
            "INSERT INTO horse (name) VALUES (?)",
            ("Thunder",)
        )

    def test_store_horse_existing(self, scheduler, mock_db):
        """Test storing existing horse"""
        mock_db.execute_query.return_value = [{"horse_id": 123}]

        horse_id = scheduler._store_horse("Thunder")

        assert horse_id == 123
        mock_db.execute_insert.assert_not_called()

    def test_store_horse_empty_name(self, scheduler, mock_db):
        """Test storing horse with empty name"""
        mock_db.execute_query.return_value = []
        mock_db.execute_insert.return_value = 123

        horse_id = scheduler._store_horse("")

        assert horse_id == 123
        mock_db.execute_insert.assert_called_with(
            "INSERT INTO horse (name) VALUES (?)",
            ("Unknown",)
        )

    def test_store_entry_new(self, scheduler, mock_db):
        """Test storing new entry"""
        mock_db.execute_query.return_value = []
        mock_db.execute_insert.return_value = 456

        entry_id = scheduler._store_entry(1, 123, "1A")

        assert entry_id == 456
        mock_db.execute_insert.assert_called()

    def test_store_entry_existing(self, scheduler, mock_db):
        """Test storing existing entry"""
        mock_db.execute_query.return_value = [{"entry_id": 456}]

        entry_id = scheduler._store_entry(1, 123, "1A")

        assert entry_id == 456
        mock_db.execute_insert.assert_not_called()

    def test_run_cycle(self, scheduler):
        """Test running a cycle"""
        mock_scraper = Mock()
        mock_scraper.get_races.return_value = []
        scheduler.scrapers = {"Track1": mock_scraper}
        scheduler.running = True

        with patch.object(scheduler, "_should_scrape", return_value=True):
            with patch.object(scheduler, "_scrape_track"):
                with patch("time.sleep") as mock_sleep:
                    # Run one cycle then stop
                    def stop_after_one(*args):
                        scheduler.running = False

                    mock_sleep.side_effect = stop_after_one

                    scheduler.run_cycle()

                    scheduler._scrape_track.assert_called()

    def test_run_cycle_with_error(self, scheduler):
        """Test cycle continues on error"""
        mock_scraper = Mock()
        mock_scraper.get_races.side_effect = Exception("Scraper error")
        scheduler.scrapers = {"Track1": mock_scraper}
        scheduler.running = True

        with patch.object(scheduler, "_should_scrape", return_value=True):
            with patch("time.sleep") as mock_sleep:
                # Run one cycle then stop
                def stop_after_one(*args):
                    scheduler.running = False

                mock_sleep.side_effect = stop_after_one

                # Should not raise exception
                scheduler.run_cycle()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])