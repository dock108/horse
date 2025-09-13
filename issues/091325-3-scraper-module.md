# Issue 091325-3: Web Scraper Module Implementation

**Priority**: High  
**Component**: Scraper - Data Collection  
**Beta Blocker**: Yes (Core data collection required for system functionality)  
**Discovered**: 2025-09-13  
**Status**: Awaiting User Testing  
**Resolved**: [Pending]

## Problem Description

The system needs a robust web scraping module to collect live Win odds and Exacta probables from horse racing track websites. The scraper must handle various HTML structures, be resilient to site changes, respect rate limits, and normalize data into a consistent format for database storage.

## Investigation Areas

1. Track website HTML structure analysis
2. Request handling with proper headers and user agents
3. HTML parsing strategies (BeautifulSoup vs lxml)
4. JavaScript-rendered content handling (Selenium/Playwright needs)
5. Rate limiting and polite scraping implementation
6. Error handling and retry logic
7. Data normalization (fractional to decimal odds conversion)
8. Scraper scheduling and cadence management

## Expected Behavior

A modular scraping system with:
- Base scraper class with common functionality
- Track-specific scrapers inheriting from base
- Win odds parsing with normalization
- Exacta probables parsing (matrix or summary)
- Robust error handling and retries
- Rate limiting to avoid blocking
- Data validation before storage
- Clear logging of scraping activities

## Files to Investigate

- `src/scraper/base.py` (base scraper class)
- `src/scraper/tracks/` (track-specific scrapers)
- `src/scraper/parsers.py` (HTML parsing utilities)
- `src/scraper/normalizers.py` (data normalization)
- `src/scraper/scheduler.py` (scraping schedule management)
- `tests/test_scraper.py` (scraper tests)

## Root Cause Analysis

Not applicable - this is initial implementation work.

## Solution Implemented

### 1. Base Scraper Class (❌ Not Started)

**base.py**:
```python
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """Abstract base class for track scrapers"""
    
    def __init__(self, track_name: str, base_url: str):
        self.track_name = track_name
        self.base_url = base_url
        self.session = self._create_session()
        self.last_request_time = 0
        self.min_request_interval = 2.0  # seconds between requests
        
    def _create_session(self) -> requests.Session:
        """Create session with proper headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        return session
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with retries"""
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None
    
    @abstractmethod
    def get_races(self, date: datetime) -> List[Dict[str, Any]]:
        """Get list of races for a given date"""
        pass
    
    @abstractmethod
    def get_win_odds(self, race_id: str) -> Dict[str, Any]:
        """Get win odds for a specific race"""
        pass
    
    @abstractmethod
    def get_exacta_probables(self, race_id: str) -> Dict[str, Any]:
        """Get exacta probable payouts for a race"""
        pass
    
    def scrape_race_data(self, race_id: str) -> Dict[str, Any]:
        """Scrape all data for a race"""
        data = {
            'track': self.track_name,
            'race_id': race_id,
            'timestamp': datetime.now().isoformat(),
            'win_odds': None,
            'exacta_probables': None
        }
        
        # Get win odds
        win_data = self.get_win_odds(race_id)
        if win_data:
            data['win_odds'] = win_data
        
        # Get exacta probables
        exacta_data = self.get_exacta_probables(race_id)
        if exacta_data:
            data['exacta_probables'] = exacta_data
        
        return data
```

### 2. Odds Parser Utilities (❌ Not Started)

**parsers.py**:
```python
import re
from typing import Optional, Tuple
from decimal import Decimal

class OddsParser:
    """Utilities for parsing various odds formats"""
    
    @staticmethod
    def parse_fractional_odds(odds_str: str) -> Optional[float]:
        """
        Parse fractional odds (e.g., '5-2', '7/2') to decimal
        Returns decimal odds (e.g., 2.5 for 5-2)
        """
        if not odds_str:
            return None
        
        # Handle special cases
        if odds_str.upper() in ['SCR', 'SCRATCH', 'SCRATCHED']:
            return None
        if odds_str.upper() in ['EVN', 'EVEN', '1-1']:
            return 1.0
        
        # Try fractional formats
        patterns = [
            r'(\d+)-(\d+)',  # 5-2 format
            r'(\d+)/(\d+)',  # 5/2 format
        ]
        
        for pattern in patterns:
            match = re.match(pattern, odds_str.strip())
            if match:
                numerator = float(match.group(1))
                denominator = float(match.group(2))
                if denominator > 0:
                    return numerator / denominator
        
        # Try direct decimal
        try:
            return float(odds_str)
        except ValueError:
            return None
    
    @staticmethod
    def parse_win_pool_amount(amount_str: str) -> Optional[int]:
        """Parse pool amount string to integer"""
        if not amount_str:
            return None
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,]', '', amount_str.strip())
        
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    
    @staticmethod
    def parse_program_number(prog_str: str) -> str:
        """Parse and normalize program number"""
        if not prog_str:
            return ""
        
        # Handle coupled entries (1A, 1B, etc.)
        cleaned = prog_str.strip().upper()
        
        # Remove any non-alphanumeric characters except letters
        cleaned = re.sub(r'[^0-9A-Z]', '', cleaned)
        
        return cleaned
    
    @staticmethod
    def parse_exacta_payout(payout_str: str) -> Optional[float]:
        """Parse exacta payout string to float"""
        if not payout_str:
            return None
        
        # Remove currency symbols
        cleaned = re.sub(r'[$]', '', payout_str.strip())
        
        try:
            return float(cleaned)
        except ValueError:
            return None
```

### 3. Sample Track Scraper (❌ Not Started)

**tracks/belmont.py**:
```python
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import json
import logging

from ..base import BaseScraper
from ..parsers import OddsParser

logger = logging.getLogger(__name__)

class BelmontScraper(BaseScraper):
    """Scraper for Belmont Park racing data"""
    
    def __init__(self):
        super().__init__(
            track_name="Belmont Park",
            base_url="https://www.example-racing-site.com/belmont"
        )
        self.parser = OddsParser()
    
    def get_races(self, date: datetime) -> List[Dict[str, Any]]:
        """Get list of races for a given date"""
        date_str = date.strftime("%Y-%m-%d")
        url = f"{self.base_url}/racing/{date_str}"
        
        response = self._make_request(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        races = []
        
        # Parse race list (example structure)
        race_elements = soup.find_all('div', class_='race-card')
        for elem in race_elements:
            race_num = elem.get('data-race-number')
            post_time = elem.find('span', class_='post-time').text
            
            races.append({
                'race_number': int(race_num),
                'post_time': post_time,
                'date': date_str,
                'track': self.track_name
            })
        
        return races
    
    def get_win_odds(self, race_id: str) -> Dict[str, Any]:
        """Get win odds for a specific race"""
        url = f"{self.base_url}/odds/win/{race_id}"
        
        response = self._make_request(url)
        if not response:
            return {}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for JSON data first
        json_script = soup.find('script', type='application/json', id='odds-data')
        if json_script:
            try:
                data = json.loads(json_script.string)
                return self._parse_json_win_odds(data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON odds data")
        
        # Fall back to HTML parsing
        return self._parse_html_win_odds(soup)
    
    def _parse_json_win_odds(self, data: dict) -> Dict[str, Any]:
        """Parse win odds from JSON data"""
        result = {
            'total_pool': data.get('totalPool', 0),
            'horses': []
        }
        
        for horse in data.get('entries', []):
            result['horses'].append({
                'program_number': self.parser.parse_program_number(horse.get('programNumber')),
                'name': horse.get('horseName', ''),
                'odds': self.parser.parse_fractional_odds(horse.get('currentOdds')),
                'pool_amount': horse.get('poolAmount', 0)
            })
        
        return result
    
    def _parse_html_win_odds(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse win odds from HTML"""
        result = {
            'total_pool': 0,
            'horses': []
        }
        
        # Find total pool
        pool_elem = soup.find('div', class_='total-pool')
        if pool_elem:
            result['total_pool'] = self.parser.parse_win_pool_amount(pool_elem.text)
        
        # Find horse odds
        horse_rows = soup.find_all('tr', class_='horse-row')
        for row in horse_rows:
            prog_num = row.find('td', class_='program-number').text
            horse_name = row.find('td', class_='horse-name').text
            odds_text = row.find('td', class_='odds').text
            
            result['horses'].append({
                'program_number': self.parser.parse_program_number(prog_num),
                'name': horse_name.strip(),
                'odds': self.parser.parse_fractional_odds(odds_text),
                'pool_amount': None
            })
        
        return result
    
    def get_exacta_probables(self, race_id: str) -> Dict[str, Any]:
        """Get exacta probable payouts"""
        url = f"{self.base_url}/odds/exacta/{race_id}"
        
        response = self._make_request(url)
        if not response:
            return {}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        result = {
            'total_pool': 0,
            'probables': {}
        }
        
        # Parse exacta matrix
        exacta_table = soup.find('table', class_='exacta-matrix')
        if exacta_table:
            for row in exacta_table.find_all('tr')[1:]:  # skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    first = self.parser.parse_program_number(cells[0].text)
                    second = self.parser.parse_program_number(cells[1].text)
                    payout = self.parser.parse_exacta_payout(cells[2].text)
                    
                    if first and second and payout:
                        key = f"{first}-{second}"
                        result['probables'][key] = payout
        
        return result
```

### 4. Data Normalizer (❌ Not Started)

**normalizers.py**:
```python
from typing import Dict, Any, List
from datetime import datetime

class DataNormalizer:
    """Normalize scraped data for database storage"""
    
    @staticmethod
    def normalize_win_odds_snapshot(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize win odds data for database insertion"""
        normalized = {
            'track': raw_data.get('track'),
            'race_id': raw_data.get('race_id'),
            'fetched_at': datetime.now(),
            'total_win_pool': raw_data.get('win_odds', {}).get('total_pool', 0),
            'entries': []
        }
        
        for horse in raw_data.get('win_odds', {}).get('horses', []):
            if horse.get('odds') is not None:
                normalized['entries'].append({
                    'program_number': horse.get('program_number'),
                    'horse_name': horse.get('name'),
                    'win_odds': horse.get('odds'),
                    'win_odds_decimal': horse.get('odds'),  # already decimal
                    'win_pool_amount': horse.get('pool_amount')
                })
        
        return normalized
    
    @staticmethod
    def normalize_exacta_probables(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize exacta probable data for database insertion"""
        normalized = []
        
        for combo, payout in raw_data.get('exacta_probables', {}).get('probables', {}).items():
            first, second = combo.split('-')
            normalized.append({
                'race_id': raw_data.get('race_id'),
                'fetched_at': datetime.now(),
                'first_horse': first,
                'second_horse': second,
                'payout': payout,
                'total_exacta_pool': raw_data.get('exacta_probables', {}).get('total_pool')
            })
        
        return normalized
```

## Testing Requirements

### Manual Testing Steps
1. Test scraper against sample HTML files
2. Verify odds parsing for various formats
3. Test rate limiting with multiple requests
4. Verify retry logic on failures
5. Test data normalization
6. Validate against live track website
7. Check resilience to HTML structure changes

### Test Scenarios
- [ ] Base scraper initializes correctly
- [ ] Session headers set properly
- [ ] Rate limiting enforces delays
- [ ] Retry logic handles failures
- [ ] Fractional odds parse correctly
- [ ] Program numbers normalize properly
- [ ] Win odds data structure correct
- [ ] Exacta probables parse accurately
- [ ] Data normalizes for DB storage
- [ ] Handles missing/invalid data gracefully

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