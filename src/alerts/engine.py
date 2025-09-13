from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from ..database.models import Alert, OddsSnapshot, ExactaProbable
from ..database.connection import DatabaseManager
from ..utils.config import config
from .evaluators import (
    WinOddsThresholdEvaluator,
    RateOfChangeEvaluator,
    ExactaPayoutEvaluator
)
from .suppressors import AlertSuppressor

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
        
    def _init_evaluators(self) -> Dict[str, Any]:
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
                if evaluator_name == 'exacta_threshold':
                    continue  # Handle separately
                    
                result = evaluator.evaluate(
                    current_data=entry_data,
                    previous_data=self._get_previous_entry_data(
                        previous_snapshot, 
                        entry_data.get('entry_id')
                    ) if previous_snapshot else None,
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
    
    def _get_previous_entry_data(self, snapshot: Dict, entry_id: int) -> Optional[Dict]:
        """Extract entry data from previous snapshot"""
        if not snapshot:
            return None
        
        # Query for the specific entry's previous odds
        query = """
            SELECT * FROM odds_snapshot 
            WHERE entry_id = ? 
            ORDER BY fetched_at DESC 
            LIMIT 1 OFFSET 1
        """
        result = self.db.execute_query(query, (entry_id,))
        
        if result:
            row = dict(result[0])
            return {
                'win_odds_decimal': row.get('win_odds_decimal'),
                'win_pool_amount': row.get('win_pool_amount')
            }
        return None
    
    def _evaluate_exacta_alerts(self, snapshot_data: Dict) -> List[Alert]:
        """Evaluate exacta-specific alerts"""
        alerts = []
        exacta_data = snapshot_data.get('exacta_probables', {})
        
        for combo, payout in exacta_data.get('probables', {}).items():
            context = AlertContext(
                race_id=snapshot_data.get('race_id'),
                entry_id=None,
                track_name=snapshot_data.get('track'),
                horse_name=combo,
                program_number=combo,
                timestamp=snapshot_data.get('fetched_at')
            )
            
            if self.config.exacta_min_payout and payout < self.config.exacta_min_payout:
                result = AlertResult(
                    should_trigger=True,
                    alert_type='exacta_low',
                    message=f"Low exacta payout ${payout:.2f} for {combo} at {context.track_name}",
                    threshold_value=self.config.exacta_min_payout,
                    actual_value=payout,
                    context=context
                )
                
                if not self.suppressor.is_suppressed(result):
                    alerts.append(self._create_alert(result))
                    
            if self.config.exacta_max_payout and payout > self.config.exacta_max_payout:
                result = AlertResult(
                    should_trigger=True,
                    alert_type='exacta_high',
                    message=f"High exacta payout ${payout:.2f} for {combo} at {context.track_name}",
                    threshold_value=self.config.exacta_max_payout,
                    actual_value=payout,
                    context=context
                )
                
                if not self.suppressor.is_suppressed(result):
                    alerts.append(self._create_alert(result))
        
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
            alert.alert_id = self.db.execute_insert(query, (
                alert.triggered_at,
                alert.race_id,
                alert.entry_id,
                alert.alert_type,
                alert.threshold_value,
                alert.actual_value,
                alert.message,
                alert.sent
            ))