# Issue 091325-5: Alert Engine Implementation

**Priority**: High  
**Component**: Alerts - Detection & Evaluation  
**Beta Blocker**: No (Core functionality works without alerts, but reduced value)  
**Discovered**: 2025-09-13  
**Status**: Awaiting User Testing  
**Resolved**: [Pending]

## Problem Description

The system needs an alert engine that evaluates odds snapshots against configured thresholds, detects significant changes, identifies cross-pool discrepancies, and triggers notifications. The engine must handle alert suppression to avoid duplicates and manage rate-of-change detection.

## Investigation Areas

1. Alert evaluation logic for various conditions
2. Threshold comparison algorithms
3. Rate-of-change calculation methods
4. Cross-pool discrepancy detection
5. Alert deduplication and suppression
6. Alert priority and severity levels
7. Alert history tracking and querying
8. Performance optimization for real-time evaluation

## Expected Behavior

A comprehensive alert engine with:
- Multiple alert type evaluators (threshold, change, discrepancy)
- Configurable threshold checking
- Percentage change detection between snapshots
- Cross-pool odds comparison
- Alert suppression within time windows
- Alert persistence in database
- Clear alert messages with context
- Efficient evaluation of multiple conditions

## Files to Investigate

- `src/alerts/engine.py` (main alert engine)
- `src/alerts/evaluators.py` (alert condition evaluators)
- `src/alerts/suppressors.py` (deduplication logic)
- `src/alerts/formatters.py` (alert message formatting)
- `tests/test_alerts.py` (alert engine tests)

## Root Cause Analysis

Not applicable - this is initial implementation work.

## Solution Implemented

### 1. Alert Engine Core (❌ Not Started)

**engine.py**:
```python
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from ..database.models import Alert, OddsSnapshot, ExactaProbable
from ..database.connection import DatabaseManager
from ..utils.config import config

logger = logging.getLogger(__name__)

@dataclass
class AlertContext:
    """Context information for alert evaluation"""
    race_id: int
    entry_id: Optional[int]
    track_name: str
    horse_name: Optional[str]
    program_number: Optional[str]
    timestamp: datetime
    
@dataclass
class AlertResult:
    """Result of alert evaluation"""
    should_trigger: bool
    alert_type: str
    message: str
    threshold_value: Optional[float]
    actual_value: Optional[float]
    context: AlertContext

class AlertEngine:
    """Main alert evaluation and management engine"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.config = config.get_alert_config()
        self.evaluators = self._init_evaluators()
        self.suppressor = AlertSuppressor(db_manager)
        
    def _init_evaluators(self) -> Dict[str, 'BaseEvaluator']:
        """Initialize alert evaluators based on config"""
        evaluators = {}
        
        if self.config.enabled:
            evaluators['win_threshold'] = WinOddsThresholdEvaluator(
                min_odds=self.config.win_odds_min,
                max_odds=self.config.win_odds_max
            )
            evaluators['exacta_threshold'] = ExactaPayoutEvaluator(
                min_payout=self.config.exacta_min_payout,
                max_payout=self.config.exacta_max_payout
            )
            evaluators['rate_change'] = RateOfChangeEvaluator()
            evaluators['discrepancy'] = CrossPoolDiscrepancyEvaluator()
        
        return evaluators
    
    def evaluate_snapshot(self, snapshot_data: Dict[str, Any]) -> List[Alert]:
        """Evaluate a new snapshot for alert conditions"""
        if not self.config.enabled:
            return []
        
        alerts = []
        race_id = snapshot_data.get('race_id')
        
        # Get previous snapshot for comparison
        previous_snapshot = self._get_previous_snapshot(race_id)
        
        # Evaluate each entry in the snapshot
        for entry_data in snapshot_data.get('entries', []):
            context = AlertContext(
                race_id=race_id,
                entry_id=entry_data.get('entry_id'),
                track_name=snapshot_data.get('track'),
                horse_name=entry_data.get('horse_name'),
                program_number=entry_data.get('program_number'),
                timestamp=snapshot_data.get('fetched_at')
            )
            
            # Run each evaluator
            for evaluator_name, evaluator in self.evaluators.items():
                result = evaluator.evaluate(
                    current_data=entry_data,
                    previous_data=self._get_previous_entry_data(
                        previous_snapshot, 
                        entry_data.get('entry_id')
                    ),
                    context=context
                )
                
                if result and result.should_trigger:
                    # Check suppression
                    if not self.suppressor.is_suppressed(result):
                        alert = self._create_alert(result)
                        alerts.append(alert)
                        logger.info(f"Alert triggered: {result.alert_type} - {result.message}")
        
        # Evaluate exacta-specific alerts
        if 'exacta_probables' in snapshot_data:
            alerts.extend(self._evaluate_exacta_alerts(snapshot_data))
        
        # Save alerts to database
        self._save_alerts(alerts)
        
        return alerts
    
    def _get_previous_snapshot(self, race_id: int) -> Optional[Dict]:
        """Get the previous snapshot for a race"""
        query = """
            SELECT * FROM odds_snapshot 
            WHERE race_id = ? 
            ORDER BY fetched_at DESC 
            LIMIT 1 OFFSET 1
        """
        result = self.db.execute_query(query, (race_id,))
        return dict(result[0]) if result else None
    
    def _get_previous_entry_data(self, snapshot: Optional[Dict], entry_id: int) -> Optional[Dict]:
        """Extract entry data from previous snapshot"""
        if not snapshot:
            return None
        # Implementation depends on snapshot structure
        return None
    
    def _evaluate_exacta_alerts(self, snapshot_data: Dict) -> List[Alert]:
        """Evaluate exacta-specific alerts"""
        alerts = []
        exacta_data = snapshot_data.get('exacta_probables', {})
        
        for combo, payout in exacta_data.get('probables', {}).items():
            if self.config.exacta_min_payout and payout < self.config.exacta_min_payout:
                # Create low payout alert
                pass
            if self.config.exacta_max_payout and payout > self.config.exacta_max_payout:
                # Create high payout alert
                pass
        
        return alerts
    
    def _create_alert(self, result: AlertResult) -> Alert:
        """Create an Alert object from evaluation result"""
        return Alert(
            triggered_at=result.context.timestamp,
            race_id=result.context.race_id,
            entry_id=result.context.entry_id,
            alert_type=result.alert_type,
            threshold_value=result.threshold_value,
            actual_value=result.actual_value,
            message=result.message,
            sent=False
        )
    
    def _save_alerts(self, alerts: List[Alert]):
        """Save alerts to database"""
        for alert in alerts:
            query = """
                INSERT INTO alert (
                    triggered_at, race_id, entry_id, alert_type,
                    threshold_value, actual_value, message, sent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db.execute_insert(query, (
                alert.triggered_at,
                alert.race_id,
                alert.entry_id,
                alert.alert_type,
                alert.threshold_value,
                alert.actual_value,
                alert.message,
                alert.sent
            ))
```

### 2. Alert Evaluators (❌ Not Started)

**evaluators.py**:
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from .engine import AlertResult, AlertContext

class BaseEvaluator(ABC):
    """Base class for alert evaluators"""
    
    @abstractmethod
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict], 
                context: AlertContext) -> Optional[AlertResult]:
        """Evaluate alert condition"""
        pass

class WinOddsThresholdEvaluator(BaseEvaluator):
    """Evaluate win odds against min/max thresholds"""
    
    def __init__(self, min_odds: float, max_odds: float):
        self.min_odds = min_odds
        self.max_odds = max_odds
    
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict],
                context: AlertContext) -> Optional[AlertResult]:
        """Check if odds exceed thresholds"""
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
                context: AlertContext) -> Optional[AlertResult]:
        """Check for significant odds changes"""
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
                context: AlertContext) -> Optional[AlertResult]:
        """Check exacta payouts"""
        # This would be called specifically for exacta data
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

class CrossPoolDiscrepancyEvaluator(BaseEvaluator):
    """Detect discrepancies between win and exacta pools"""
    
    def __init__(self, threshold_percent: float = 30.0):
        self.threshold_percent = threshold_percent
    
    def evaluate(self, current_data: Dict, previous_data: Optional[Dict],
                context: AlertContext) -> Optional[AlertResult]:
        """Check for pool discrepancies"""
        # This requires comparing win odds with exacta implied odds
        # Implementation would need access to both pools
        # Placeholder for now
        return None
```

### 3. Alert Suppression (❌ Not Started)

**suppressors.py**:
```python
from typing import Dict, Set
from datetime import datetime, timedelta
import hashlib

from .engine import AlertResult
from ..database.connection import DatabaseManager

class AlertSuppressor:
    """Handle alert deduplication and suppression"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.recent_alerts: Dict[str, datetime] = {}
        self.duplicate_window = 300  # seconds
        
    def is_suppressed(self, result: AlertResult) -> bool:
        """Check if alert should be suppressed"""
        # Generate hash for alert
        alert_hash = self._generate_alert_hash(result)
        
        # Check in-memory cache first
        if alert_hash in self.recent_alerts:
            last_triggered = self.recent_alerts[alert_hash]
            if (datetime.now() - last_triggered).seconds < self.duplicate_window:
                return True
        
        # Check database for recent similar alerts
        if self._check_database_suppression(result):
            return True
        
        # Update cache
        self.recent_alerts[alert_hash] = datetime.now()
        
        # Clean old entries from cache
        self._clean_cache()
        
        return False
    
    def _generate_alert_hash(self, result: AlertResult) -> str:
        """Generate unique hash for alert"""
        key = f"{result.alert_type}:{result.context.race_id}:{result.context.entry_id}:{result.threshold_value}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _check_database_suppression(self, result: AlertResult) -> bool:
        """Check if similar alert exists in database within window"""
        query = """
            SELECT COUNT(*) as count FROM alert
            WHERE alert_type = ?
            AND race_id = ?
            AND (entry_id = ? OR entry_id IS NULL)
            AND triggered_at > ?
        """
        
        window_start = datetime.now() - timedelta(seconds=self.duplicate_window)
        
        result_row = self.db.execute_query(query, (
            result.alert_type,
            result.context.race_id,
            result.context.entry_id,
            window_start
        ))
        
        return result_row[0]['count'] > 0 if result_row else False
    
    def _clean_cache(self):
        """Remove old entries from in-memory cache"""
        cutoff = datetime.now() - timedelta(seconds=self.duplicate_window)
        self.recent_alerts = {
            k: v for k, v in self.recent_alerts.items()
            if v > cutoff
        }
```

## Testing Requirements

### Manual Testing Steps
1. Create test snapshot data with various odds
2. Test threshold evaluations (min/max)
3. Test rate of change detection
4. Test alert suppression
5. Verify alerts save to database
6. Test with missing/invalid data
7. Verify performance with multiple entries

### Test Scenarios
- [ ] Alert engine initializes with config
- [ ] Win odds threshold alerts trigger correctly
- [ ] Rate of change alerts calculate properly
- [ ] Exacta payout alerts work
- [ ] Alert suppression prevents duplicates
- [ ] Alerts persist to database
- [ ] Alert messages format correctly
- [ ] Invalid data handled gracefully
- [ ] Multiple evaluators work together
- [ ] Performance acceptable for real-time

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