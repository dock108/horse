# Issue 091325-7: System Integration and UAT Preparation

**Priority**: High  
**Component**: Integration - End-to-End System  
**Beta Blocker**: Yes (Required for first UAT milestone)  
**Discovered**: 2025-09-13  
**Status**: Awaiting User Testing  
**Resolved**: [Pending]

## Problem Description

The system components need to be integrated into a working end-to-end pipeline that can scrape odds, store them in the database, evaluate alerts, and send notifications. This issue covers creating the main execution script, scheduler, logging framework, and preparing the system for initial UAT testing.

## Investigation Areas

1. Main application entry point and orchestration
2. Scheduler implementation for periodic scraping
3. Logging configuration across all modules
4. Error handling and recovery mechanisms
5. System health checks and monitoring
6. Test data generation for UAT
7. Documentation for UAT testers
8. Performance baseline measurements

## Expected Behavior

A fully integrated system with:
- Main script that orchestrates all components
- Scheduler that runs scraping at configured intervals
- Comprehensive logging for debugging
- Graceful error handling and recovery
- Basic monitoring and health checks
- Test data and scenarios for UAT
- Clear documentation for testing
- Command-line interface for operations

## Files to Investigate

- `main.py` (main application entry point)
- `src/scheduler.py` (scheduling logic)
- `src/utils/logging.py` (logging configuration)
- `src/utils/health.py` (health checks)
- `scripts/generate_test_data.py` (test data generator)
- `docs/UAT_GUIDE.md` (UAT testing guide)
- `tests/test_integration.py` (integration tests)

## Root Cause Analysis

Not applicable - this is initial implementation work.

## Solution Implemented

### 1. Main Application Entry Point (❌ Not Started)

**main.py**:
```python
#!/usr/bin/env python3
"""
Horse Racing Odds Tracking System
Main application entry point
"""

import argparse
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path

from src.utils.config import config
from src.utils.logging_config import setup_logging
from src.database.connection import DatabaseManager
from src.scheduler import OddsScheduler
from src.utils.health import HealthMonitor

logger = logging.getLogger(__name__)

class OddsTrackingSystem:
    """Main application controller"""
    
    def __init__(self):
        self.config = config
        self.db = None
        self.scheduler = None
        self.health_monitor = None
        self.running = False
        
    def initialize(self):
        """Initialize system components"""
        logger.info("Initializing Horse Racing Odds Tracking System")
        
        # Initialize database
        logger.info("Connecting to database...")
        self.db = DatabaseManager(self.config.get('system.database_path'))
        
        # Initialize scheduler
        logger.info("Setting up scheduler...")
        self.scheduler = OddsScheduler(self.db)
        
        # Initialize health monitor
        logger.info("Starting health monitor...")
        self.health_monitor = HealthMonitor(self.db)
        
        logger.info("System initialization complete")
        
    def start(self):
        """Start the system"""
        if self.running:
            logger.warning("System already running")
            return
        
        try:
            self.running = True
            logger.info("Starting odds tracking system...")
            
            # Perform initial health check
            if not self.health_monitor.check_system_health():
                logger.error("System health check failed")
                return
            
            # Start scheduler
            self.scheduler.start()
            
            logger.info("System started successfully")
            logger.info(f"Monitoring {len(config.get_tracks())} tracks")
            
            # Keep running until interrupted
            while self.running:
                try:
                    self.scheduler.run_cycle()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    
        finally:
            self.stop()
    
    def stop(self):
        """Stop the system gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping odds tracking system...")
        self.running = False
        
        if self.scheduler:
            self.scheduler.stop()
        
        logger.info("System stopped")
    
    def run_once(self):
        """Run a single scraping cycle"""
        logger.info("Running single scraping cycle...")
        
        if not self.health_monitor.check_system_health():
            logger.error("System health check failed")
            return
        
        self.scheduler.run_single_cycle()
        logger.info("Single cycle complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Horse Racing Odds Tracking System'
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode with sample data'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    if args.config:
        config.load_config(args.config)
    
    # Create and initialize system
    system = OddsTrackingSystem()
    
    try:
        system.initialize()
        
        if args.test:
            logger.info("Running in test mode")
            # Load test data
            from scripts.generate_test_data import generate_test_data
            generate_test_data(system.db)
        
        if args.once:
            system.run_once()
        else:
            system.start()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### 2. Scheduler Implementation (❌ Not Started)

**scheduler.py**:
```python
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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
                logger.error(f"Failed to initialize scraper for {track_config.name}: {e}")
    
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
        near_post_threshold = self.config.get('scraping.near_post_threshold', 600)
        near_post_interval = self.config.get('scraping.near_post_interval', 60)
        default_interval = self.config.get('scraping.default_interval', 300)
        
        # Query upcoming races
        query = """
            SELECT MIN(
                CAST((julianday(date || ' ' || post_time) - julianday('now')) * 86400 AS INTEGER)
            ) as seconds_to_post
            FROM race
            WHERE track_id = (SELECT track_id FROM track WHERE name = ?)
            AND date >= date('now')
            AND status != 'complete'
        """
        
        result = self.db.execute_query(query, (track_name,))
        
        if result and result[0]['seconds_to_post']:
            seconds_to_post = result[0]['seconds_to_post']
            if 0 < seconds_to_post < near_post_threshold:
                return near_post_interval
        
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
                    
                logger.info(f"Scraped race {race_id}: {len(alerts)} alerts triggered")
                
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
            track_id = track_result[0]['track_id']
        
        # Check if race exists
        race_query = """
            SELECT race_id FROM race 
            WHERE track_id = ? AND race_date = ? AND race_number = ?
        """
        race_result = self.db.execute_query(race_query, (
            track_id,
            race_data.get('date'),
            race_data.get('race_number')
        ))
        
        if race_result:
            return race_result[0]['race_id']
        
        # Insert race
        insert_race = """
            INSERT INTO race (track_id, race_date, race_number, post_time, status)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.db.execute_insert(insert_race, (
            track_id,
            race_data.get('date'),
            race_data.get('race_number'),
            race_data.get('post_time'),
            'scheduled'
        ))
    
    def _store_snapshot(self, race_id: int, race_data: Dict) -> Dict:
        """Store odds snapshot in database"""
        snapshot = {
            'race_id': race_id,
            'fetched_at': datetime.now(),
            'track': race_data.get('track'),
            'entries': []
        }
        
        # Store win odds
        if race_data.get('win_odds'):
            for horse in race_data['win_odds'].get('horses', []):
                # Store or get horse
                horse_id = self._store_horse(horse.get('name'))
                
                # Store or get entry
                entry_id = self._store_entry(race_id, horse_id, horse.get('program_number'))
                
                # Store odds snapshot
                insert_odds = """
                    INSERT INTO odds_snapshot (
                        race_id, entry_id, fetched_at, 
                        win_odds, win_odds_decimal, win_pool_amount, total_win_pool
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                
                self.db.execute_insert(insert_odds, (
                    race_id,
                    entry_id,
                    snapshot['fetched_at'],
                    horse.get('odds'),
                    horse.get('odds'),
                    horse.get('pool_amount'),
                    race_data['win_odds'].get('total_pool')
                ))
                
                snapshot['entries'].append({
                    'entry_id': entry_id,
                    'horse_name': horse.get('name'),
                    'program_number': horse.get('program_number'),
                    'win_odds_decimal': horse.get('odds'),
                    'win_pool_amount': horse.get('pool_amount')
                })
        
        return snapshot
    
    def _store_horse(self, name: str) -> int:
        """Store or get horse ID"""
        query = "SELECT horse_id FROM horse WHERE name = ?"
        result = self.db.execute_query(query, (name,))
        
        if result:
            return result[0]['horse_id']
        
        insert = "INSERT INTO horse (name) VALUES (?)"
        return self.db.execute_insert(insert, (name,))
    
    def _store_entry(self, race_id: int, horse_id: int, program_number: str) -> int:
        """Store or get entry ID"""
        query = "SELECT entry_id FROM entry WHERE race_id = ? AND program_number = ?"
        result = self.db.execute_query(query, (race_id, program_number))
        
        if result:
            return result[0]['entry_id']
        
        insert = """
            INSERT INTO entry (race_id, horse_id, program_number)
            VALUES (?, ?, ?)
        """
        return self.db.execute_insert(insert, (race_id, horse_id, program_number))
```

### 3. Logging Configuration (❌ Not Started)

**utils/logging_config.py**:
```python
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

def setup_logging(level='INFO', log_dir='logs'):
    """Configure logging for the application"""
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(simple_formatter)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / f'odds_tracker_{datetime.now():%Y%m%d}.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / 'errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Reduce noise from libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured - Level: {level}, Directory: {log_dir}")
```

### 4. UAT Testing Guide (❌ Not Started)

**docs/UAT_GUIDE.md**:
```markdown
# User Acceptance Testing (UAT) Guide

## System Overview
The Horse Racing Odds Tracking System monitors live betting odds from configured racetracks, stores historical data, and sends alerts when specified conditions are met.

## Pre-Testing Setup

### 1. Environment Setup
```bash
# Clone repository
git clone [repository-url]
cd horses

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
1. Copy `config/config.yaml.example` to `config/config.yaml`
2. Update email settings with your SMTP credentials
3. Configure at least one track to monitor
4. Set alert thresholds as desired

### 3. Environment Variables
Create `.env` file with:
```
EMAIL_SENDER=your-email@gmail.com
EMAIL_RECIPIENT=alerts@example.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## Test Scenarios

### Scenario 1: Basic System Start
**Objective**: Verify system starts without errors

**Steps**:
1. Run: `python main.py --log-level DEBUG`
2. Verify system initializes without errors
3. Check that configured tracks are listed
4. Confirm database is created at `data/horses.db`

**Expected Results**:
- System starts successfully
- No error messages in console
- Log files created in `logs/` directory

### Scenario 2: Single Scraping Cycle
**Objective**: Test one-time scraping

**Steps**:
1. Run: `python main.py --once`
2. Monitor console output
3. Check database for new data

**Expected Results**:
- Scraping completes for all tracks
- Data stored in database
- No errors reported

### Scenario 3: Alert Triggering
**Objective**: Verify alerts work

**Steps**:
1. Set low threshold (e.g., win_odds_min: 100.0)
2. Run system with test data: `python main.py --test`
3. Check for alert messages

**Expected Results**:
- Alerts triggered for test data
- Alert messages in console
- Alerts saved to database

### Scenario 4: Email Notifications
**Objective**: Test email delivery

**Steps**:
1. Ensure email configured correctly
2. Trigger an alert (use test data if needed)
3. Check recipient inbox

**Expected Results**:
- Email received at configured address
- Email contains alert details
- Formatting is readable

### Scenario 5: Continuous Operation
**Objective**: Test extended running

**Steps**:
1. Start system: `python main.py`
2. Let run for 30 minutes
3. Monitor logs and database

**Expected Results**:
- System remains stable
- Regular scraping occurs
- Memory usage stable
- Database grows appropriately

## Validation Checklist

### Functional Requirements
- [ ] System starts successfully
- [ ] Scrapes configured tracks
- [ ] Stores odds in database
- [ ] Detects threshold violations
- [ ] Sends email alerts
- [ ] Handles errors gracefully

### Data Validation
- [ ] Win odds parsed correctly
- [ ] Exacta probables captured (if configured)
- [ ] Timestamps accurate
- [ ] No duplicate races created
- [ ] Historical data retained

### Performance
- [ ] Scraping completes < 5 seconds per track
- [ ] Database queries < 100ms
- [ ] Alert evaluation < 1 second
- [ ] Memory usage < 200MB

## Troubleshooting

### Common Issues

1. **Database Errors**
   - Check write permissions on `data/` directory
   - Verify SQLite installed

2. **Scraping Failures**
   - Check internet connection
   - Verify track URLs in config
   - Review scraper logs

3. **Email Not Sending**
   - Verify SMTP credentials
   - Check spam folder
   - Enable "less secure apps" if using Gmail

4. **No Alerts Triggering**
   - Review threshold settings
   - Check if odds data is being collected
   - Verify alert engine enabled

## Reporting Issues

When reporting issues, please include:
1. Full error message/traceback
2. Configuration file (remove passwords)
3. Log files from `logs/` directory
4. Steps to reproduce
5. Expected vs actual behavior

## Contact

For questions or support during UAT:
- Create issue in repository
- Include "UAT" tag
- Attach relevant logs and config
```

## Testing Requirements

### Manual Testing Steps
1. Set up clean environment
2. Configure system with test settings
3. Run basic start test
4. Execute single cycle
5. Test with sample data
6. Verify alert triggering
7. Confirm email delivery
8. Run continuous operation test

### Test Scenarios
- [ ] System initializes all components
- [ ] Scheduler coordinates scraping
- [ ] Database operations work correctly
- [ ] Alerts evaluate and trigger
- [ ] Notifications send successfully
- [ ] Logging captures all events
- [ ] Error recovery works
- [ ] Health checks pass
- [ ] Performance meets targets
- [ ] Documentation is clear

## Status

**Current Status**: New  
**Last Updated**: 2025-09-13

### Implementation Checklist
- [ ] Root cause identified
- [ ] Solution designed
- [ ] Code changes made
- [ ] Tests written
- [ ] Manual testing completed
- [ ] Code review passed
- [ ] Deployed to beta

### Completion Criteria (Ready for User Testing)
- [ ] Code compiles without errors
- [ ] All tests pass
- [ ] Feature/fix is functional
- [ ] Ready for user testing
- [ ] Any blockers clearly documented

### User Testing Confirmation
- [ ] User has tested the fix/feature
- [ ] User confirms issue is resolved
- [ ] User approves moving to done/complete

## Result

[Pending implementation]