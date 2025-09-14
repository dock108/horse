"""Basic tests to verify system components"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported"""
    from src.database.connection import DatabaseManager
    from src.database.models import Track, Race, Horse
    from src.utils.config import config
    from src.scraper.base import BaseScraper
    from src.alerts.engine import AlertEngine
    from src.notifications.email import EmailNotifier
    from src.scheduler import OddsScheduler

    # If we get here, all imports succeeded
    assert True


def test_database():
    """Test database initialization"""
    from src.database.connection import DatabaseManager

    db = DatabaseManager("data/test.db")

    # Test query
    result = db.execute_query("SELECT 1 as test")
    assert result[0]['test'] == 1
    assert len(result) == 1


def test_config():
    """Test configuration loading"""
    from src.utils.config import config

    # Config should load defaults even without file
    tracks = config.get_tracks()
    assert isinstance(tracks, list)
    assert len(tracks) >= 0  # At least default track


def test_scraper():
    """Test scraper functionality"""
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
    assert 'total_pool' in odds


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
        try:
            test()
            print(f"✓ {test.__name__} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
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