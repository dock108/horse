from typing import Dict, Set, Any
from datetime import datetime, timedelta
import hashlib

from ..database.connection import DatabaseManager

class AlertSuppressor:
    """Handle alert deduplication and suppression"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.recent_alerts: Dict[str, datetime] = {}
        self.duplicate_window = 300  # seconds
        
    def is_suppressed(self, result: Any) -> bool:
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
    
    def _generate_alert_hash(self, result: Any) -> str:
        """Generate unique hash for alert"""
        key = f"{result.alert_type}:{result.context.race_id}:{result.context.entry_id}:{result.threshold_value}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _check_database_suppression(self, result: Any) -> bool:
        """Check if similar alert exists in database within window"""
        query = """
            SELECT COUNT(*) as count FROM alert
            WHERE alert_type = ?
            AND race_id = ?
            AND (entry_id = ? OR (entry_id IS NULL AND ? IS NULL))
            AND triggered_at > ?
        """
        
        window_start = datetime.now() - timedelta(seconds=self.duplicate_window)
        
        result_row = self.db.execute_query(query, (
            result.alert_type,
            result.context.race_id,
            result.context.entry_id,
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