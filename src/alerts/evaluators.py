from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseEvaluator(ABC):
    """Base class for alert evaluators"""
    
    @abstractmethod
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict], 
                context: Any) -> Optional[Any]:
        """Evaluate alert condition"""
        pass

class WinOddsThresholdEvaluator(BaseEvaluator):
    """Evaluate win odds against min/max thresholds"""
    
    def __init__(self, min_odds: float, max_odds: float):
        self.min_odds = min_odds
        self.max_odds = max_odds
    
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict],
                context: Any) -> Optional[Any]:
        """Check if odds exceed thresholds"""
        from .engine import AlertResult
        
        current_odds = current_data.get('win_odds_decimal')
        
        if current_odds is None:
            return None
        
        if current_odds < self.min_odds:
            return AlertResult(
                should_trigger=True,
                alert_type='win_odds_low',
                message=f"{context.horse_name} ({context.program_number}) odds dropped to {current_odds:.1f} at {context.track_name}",
                threshold_value=self.min_odds,
                actual_value=current_odds,
                context=context
            )
        
        if current_odds > self.max_odds:
            return AlertResult(
                should_trigger=True,
                alert_type='win_odds_high',
                message=f"{context.horse_name} ({context.program_number}) odds rose to {current_odds:.1f} at {context.track_name}",
                threshold_value=self.max_odds,
                actual_value=current_odds,
                context=context
            )
        
        return None

class RateOfChangeEvaluator(BaseEvaluator):
    """Evaluate rate of change in odds"""
    
    def __init__(self, min_change_percent: float = 25.0):
        self.min_change_percent = min_change_percent
    
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict],
                context: Any) -> Optional[Any]:
        """Check for significant odds changes"""
        from .engine import AlertResult
        
        if not previous_data:
            return None
        
        current_odds = current_data.get('win_odds_decimal')
        previous_odds = previous_data.get('win_odds_decimal')
        
        if not current_odds or not previous_odds or previous_odds == 0:
            return None
        
        change_percent = abs((current_odds - previous_odds) / previous_odds) * 100
        
        if change_percent >= self.min_change_percent:
            direction = "increased" if current_odds > previous_odds else "decreased"
            return AlertResult(
                should_trigger=True,
                alert_type='odds_change',
                message=f"{context.horse_name} odds {direction} by {change_percent:.1f}% (from {previous_odds:.1f} to {current_odds:.1f})",
                threshold_value=self.min_change_percent,
                actual_value=change_percent,
                context=context
            )
        
        return None

class ExactaPayoutEvaluator(BaseEvaluator):
    """Evaluate exacta payouts against thresholds"""
    
    def __init__(self, min_payout: float, max_payout: float):
        self.min_payout = min_payout
        self.max_payout = max_payout
    
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict],
                context: Any) -> Optional[Any]:
        """Check exacta payouts"""
        from .engine import AlertResult
        
        payout = current_data.get('payout')
        
        if payout is None:
            return None
        
        if payout < self.min_payout:
            return AlertResult(
                should_trigger=True,
                alert_type='exacta_low',
                message=f"Low exacta payout ${payout:.2f} for combination at {context.track_name}",
                threshold_value=self.min_payout,
                actual_value=payout,
                context=context
            )
        
        if payout > self.max_payout:
            return AlertResult(
                should_trigger=True,
                alert_type='exacta_high',
                message=f"High exacta payout ${payout:.2f} for combination at {context.track_name}",
                threshold_value=self.max_payout,
                actual_value=payout,
                context=context
            )
        
        return None