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