from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random
import logging

from ..base import BaseScraper
from ..parsers import OddsParser

logger = logging.getLogger(__name__)

class TestTrackScraper(BaseScraper):
    """Test scraper that generates sample data for testing"""
    
    def __init__(self):
        super().__init__(
            track_name="Test Track",
            base_url="https://test.example.com"
        )
        self.parser = OddsParser()
    
    def get_races(self, date: datetime) -> List[Dict[str, Any]]:
        """Generate test races for a given date"""
        races = []
        
        # Generate 8 races for testing
        for i in range(1, 9):
            post_time = datetime.now() + timedelta(hours=i)
            races.append({
                'race_number': i,
                'post_time': post_time.strftime("%H:%M"),
                'date': date.strftime("%Y-%m-%d"),
                'track': self.track_name
            })
        
        logger.info(f"Generated {len(races)} test races")
        return races
    
    def get_win_odds(self, race_id: str) -> Dict[str, Any]:
        """Generate test win odds for a race"""
        horses = [
            ("1", "Thunder Bolt", "5-2", 25000),
            ("2", "Lightning Strike", "3-1", 22000),
            ("3", "Storm Chaser", "7-2", 18000),
            ("4", "Wind Runner", "10-1", 8000),
            ("5", "Rain Dancer", "15-1", 5000),
            ("6", "Cloud Walker", "20-1", 3000),
            ("7", "Sun Blazer", "8-1", 10000),
            ("8", "Moon Shadow", "12-1", 7000),
        ]
        
        # Randomly vary the odds slightly
        result = {
            'total_pool': sum(h[3] for h in horses),
            'horses': []
        }
        
        for prog_num, name, base_odds, pool in horses:
            # Add some randomness to odds
            odds_value = self.parser.parse_fractional_odds(base_odds)
            if odds_value:
                odds_value *= random.uniform(0.8, 1.2)
            
            result['horses'].append({
                'program_number': prog_num,
                'name': name,
                'odds': odds_value,
                'pool_amount': int(pool * random.uniform(0.9, 1.1))
            })
        
        return result
    
    def get_exacta_probables(self, race_id: str) -> Dict[str, Any]:
        """Generate test exacta probable payouts"""
        result = {
            'total_pool': 50000,
            'probables': {}
        }
        
        # Generate some sample exacta payouts
        horses = ["1", "2", "3", "4", "5", "6", "7", "8"]
        
        for first in horses[:4]:  # Only first 4 horses for simplicity
            for second in horses[:4]:
                if first != second:
                    # Generate payout based on odds
                    base_payout = (int(first) + int(second)) * 10
                    payout = base_payout * random.uniform(0.8, 1.5)
                    result['probables'][f"{first}-{second}"] = round(payout, 2)
        
        return result