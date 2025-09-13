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