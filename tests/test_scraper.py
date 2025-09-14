"""Tests for scraper modules"""

import pytest
import requests
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.scraper.base import BaseScraper
from src.scraper.parsers import OddsParser
from src.scraper.tracks import get_scraper_for_track
from src.scraper.tracks.test_track import TestTrackScraper


class TestOddsParser:
    """Test odds parsing functions"""

    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return OddsParser()

    def test_parse_fractional_odds_standard(self, parser):
        """Test parsing standard fractional odds"""
        assert parser.parse_fractional_odds("5-2") == 2.5
        assert parser.parse_fractional_odds("7-2") == 3.5
        assert parser.parse_fractional_odds("9-5") == 1.8
        assert parser.parse_fractional_odds("1-1") == 1.0

    def test_parse_fractional_odds_slash_format(self, parser):
        """Test parsing slash format odds"""
        assert parser.parse_fractional_odds("5/2") == 2.5
        assert parser.parse_fractional_odds("7/2") == 3.5
        assert parser.parse_fractional_odds("10/1") == 10.0

    def test_parse_fractional_odds_special_cases(self, parser):
        """Test special case odds"""
        assert parser.parse_fractional_odds("EVN") == 1.0
        assert parser.parse_fractional_odds("EVEN") == 1.0
        assert parser.parse_fractional_odds("SCR") is None
        assert parser.parse_fractional_odds("SCRATCH") is None
        assert parser.parse_fractional_odds("SCRATCHED") is None

    def test_parse_fractional_odds_decimal(self, parser):
        """Test parsing decimal odds"""
        assert parser.parse_fractional_odds("5.5") == 5.5
        assert parser.parse_fractional_odds("10.25") == 10.25

    def test_parse_fractional_odds_invalid(self, parser):
        """Test parsing invalid odds"""
        assert parser.parse_fractional_odds("") is None
        assert parser.parse_fractional_odds(None) is None
        assert parser.parse_fractional_odds("invalid") is None
        assert parser.parse_fractional_odds("5-0") is None  # Division by zero

    def test_parse_win_pool_amount(self, parser):
        """Test parsing pool amounts"""
        assert parser.parse_win_pool_amount("$10,000") == 10000
        assert parser.parse_win_pool_amount("25000") == 25000
        assert parser.parse_win_pool_amount("$1,234,567") == 1234567
        assert parser.parse_win_pool_amount("100.50") == 100

    def test_parse_win_pool_amount_invalid(self, parser):
        """Test parsing invalid pool amounts"""
        assert parser.parse_win_pool_amount("") is None
        assert parser.parse_win_pool_amount(None) is None
        assert parser.parse_win_pool_amount("invalid") is None

    def test_parse_program_number(self, parser):
        """Test parsing program numbers"""
        assert parser.parse_program_number("1") == "1"
        assert parser.parse_program_number("1A") == "1A"
        assert parser.parse_program_number("1a") == "1A"
        assert parser.parse_program_number("12B") == "12B"
        assert parser.parse_program_number(" 3 ") == "3"

    def test_parse_program_number_special(self, parser):
        """Test parsing special program numbers"""
        assert parser.parse_program_number("1-A") == "1A"
        assert parser.parse_program_number("") == ""
        assert parser.parse_program_number(None) == ""

    def test_parse_exacta_payout(self, parser):
        """Test parsing exacta payouts"""
        assert parser.parse_exacta_payout("$25.50") == 25.50
        assert parser.parse_exacta_payout("100.00") == 100.00
        assert parser.parse_exacta_payout("$1,234.56") == 1234.56

    def test_parse_exacta_payout_invalid(self, parser):
        """Test parsing invalid exacta payouts"""
        assert parser.parse_exacta_payout("") is None
        assert parser.parse_exacta_payout(None) is None
        assert parser.parse_exacta_payout("invalid") is None


class TestBaseScraper:
    """Test base scraper functionality"""

    class MockScraper(BaseScraper):
        """Mock concrete scraper for testing"""

        def get_races(self, date):
            return []

        def get_win_odds(self, race_id):
            return {}

        def get_exacta_probables(self, race_id):
            return {}

    @pytest.fixture
    def scraper(self):
        """Create mock scraper instance"""
        return self.MockScraper("Test Track", "https://test.com")

    def test_init(self, scraper):
        """Test scraper initialization"""
        assert scraper.track_name == "Test Track"
        assert scraper.base_url == "https://test.com"
        assert scraper.session is not None
        assert scraper.last_request_time == 0
        assert scraper.min_request_interval == 2.0

    def test_create_session(self, scraper):
        """Test session creation with headers"""
        session = scraper._create_session()
        assert "User-Agent" in session.headers
        assert "Accept" in session.headers
        assert session.headers["Accept"] == "text/html,application/json"

    def test_rate_limit(self, scraper):
        """Test rate limiting"""
        with patch("time.sleep") as mock_sleep:
            scraper.last_request_time = time.time()
            scraper._rate_limit()
            mock_sleep.assert_called()

    def test_rate_limit_no_wait(self, scraper):
        """Test rate limiting when enough time passed"""
        with patch("time.sleep") as mock_sleep:
            scraper.last_request_time = time.time() - 10
            scraper._rate_limit()
            mock_sleep.assert_not_called()

    @patch("requests.Session.get")
    def test_make_request_success(self, mock_get, scraper):
        """Test successful request"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = scraper._make_request("https://test.com/page")

        assert response == mock_response
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_make_request_with_retry(self, mock_get, scraper):
        """Test request with retry on failure"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None

        # Fail twice, succeed on third
        mock_get.side_effect = [
            requests.RequestException("Error"),
            requests.RequestException("Error"),
            mock_response
        ]

        with patch("time.sleep"):
            response = scraper._make_request("https://test.com/page")

        assert response == mock_response
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_make_request_max_retries(self, mock_get, scraper):
        """Test request fails after max retries"""
        mock_get.side_effect = requests.RequestException("Permanent error")

        with patch("time.sleep"):
            response = scraper._make_request("https://test.com/page", max_retries=3)

        assert response is None
        assert mock_get.call_count == 3

    def test_scrape_race_data(self, scraper):
        """Test scraping all race data"""
        scraper.get_win_odds = Mock(return_value={"horses": []})
        scraper.get_exacta_probables = Mock(return_value={"probables": {}})

        data = scraper.scrape_race_data("race123")

        assert data["track"] == "Test Track"
        assert data["race_id"] == "race123"
        assert "timestamp" in data
        assert "win_odds" in data
        assert "exacta_probables" in data

        scraper.get_win_odds.assert_called_once_with("race123")
        scraper.get_exacta_probables.assert_called_once_with("race123")


class TestTestTrackScraper:
    """Test the test track scraper"""

    @pytest.fixture
    def scraper(self):
        """Create test track scraper"""
        return TestTrackScraper()

    def test_init(self, scraper):
        """Test test track scraper initialization"""
        assert scraper.track_name == "Test Track"
        assert scraper.parser is not None

    def test_get_races(self, scraper):
        """Test generating test races"""
        races = scraper.get_races(datetime.now())

        assert len(races) == 8
        assert all("race_number" in r for r in races)
        assert all("post_time" in r for r in races)
        assert races[0]["race_number"] == 1
        assert races[-1]["race_number"] == 8

    def test_get_win_odds(self, scraper):
        """Test generating test win odds"""
        odds = scraper.get_win_odds("1")

        assert "total_pool" in odds
        assert "horses" in odds
        assert len(odds["horses"]) > 0

        horse = odds["horses"][0]
        assert "program_number" in horse
        assert "name" in horse
        assert "odds" in horse
        assert "pool_amount" in horse

    def test_get_exacta_probables(self, scraper):
        """Test generating test exacta probables"""
        exacta = scraper.get_exacta_probables("1")

        assert "total_pool" in exacta
        assert "probables" in exacta
        assert len(exacta["probables"]) > 0

        # Check format of keys
        for combo, payout in exacta["probables"].items():
            assert "-" in combo
            assert isinstance(payout, float)


class TestScraperFactory:
    """Test scraper factory function"""

    def test_get_scraper_for_track_test(self):
        """Test getting scraper for test track"""
        scraper = get_scraper_for_track("Test Track")
        assert scraper is not None
        assert isinstance(scraper, TestTrackScraper)

    def test_get_scraper_for_track_placeholder(self):
        """Test getting scraper for placeholder tracks"""
        scraper = get_scraper_for_track("Belmont Park")
        assert scraper is not None
        assert isinstance(scraper, TestTrackScraper)

    def test_get_scraper_for_track_unknown(self):
        """Test getting scraper for unknown track"""
        scraper = get_scraper_for_track("Unknown Track")
        assert scraper is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])