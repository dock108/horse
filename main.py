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
            # Test mode uses the TestTrackScraper which generates sample data
        
        if args.once:
            system.run_once()
        else:
            system.start()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()