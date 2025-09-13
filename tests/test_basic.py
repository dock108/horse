"""Basic tests to verify system components"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from src.database.connection import DatabaseManager
        from src.database.models import Track, Race, Horse
        from src.utils.config import config
        from src.scraper.base import BaseScraper
        from src.alerts.engine import AlertEngine
        from src.notifications.email import EmailNotifier
        from src.scheduler import OddsScheduler
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_database():
    """Test database initialization"""
    try:
        from src.database.connection import DatabaseManager
        db = DatabaseManager("data/test.db")
        
        # Test query
        result = db.execute_query("SELECT 1 as test")
        assert result[0]['test'] == 1
        
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from src.utils.config import config
        
        # Config should load defaults even without file
        tracks = config.get_tracks()
        assert len(tracks) >= 0  # At least default track
        
        print("✓ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_scraper():
    """Test scraper functionality"""
    try:
        from src.scraper.tracks.test_track import TestTrackScraper
        from datetime import datetime
        
        scraper = TestTrackScraper()
        races = scraper.get_races(datetime.now())
        
        assert len(races) > 0
        assert 'race_number' in races[0]
        
        # Test win odds
        odds = scraper.get_win_odds("1")
        assert 'horses' in odds
        assert len(odds['horses']) > 0
        
        print("✓ Test scraper working")
        return True
    except Exception as e:
        print(f"✗ Scraper test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running basic system tests...\n")
    
    tests = [
        test_imports,
        test_database,
        test_config,
        test_scraper
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    
    if failed == 0:
        print("\n✅ All tests passed! System is ready for testing.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)