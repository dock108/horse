from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .email import EmailNotifier
from ..database.models import Alert
from ..database.connection import DatabaseManager

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manage all notification channels"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.email_notifier = EmailNotifier()
        self.batch_window = 60  # seconds to batch alerts
        self.pending_alerts: List[Alert] = []
        self.last_batch_time = datetime.now()
    
    def notify(self, alert: Alert) -> bool:
        """Send notification for an alert"""
        success = False
        
        # Try email notification
        if self.email_notifier.enabled:
            # Check if we should batch
            if self._should_batch():
                self.pending_alerts.append(alert)
                
                # Check if batch window expired
                if self._batch_window_expired():
                    success = self._send_batch()
            else:
                success = self.email_notifier.send_alert(alert)
        else:
            # If email is disabled, just log the alert
            logger.info(f"Alert (email disabled): {alert.message}")
            success = True
        
        # Update alert status in database
        if success and alert.alert_id:
            self._mark_alert_sent(alert)
        
        return success
    
    def _should_batch(self) -> bool:
        """Determine if alerts should be batched"""
        # Could be based on config, alert rate, etc.
        return len(self.pending_alerts) > 0
    
    def _batch_window_expired(self) -> bool:
        """Check if batch window has expired"""
        elapsed = (datetime.now() - self.last_batch_time).seconds
        return elapsed >= self.batch_window
    
    def _send_batch(self) -> bool:
        """Send batched alerts"""
        if not self.pending_alerts:
            return True
        
        success = self.email_notifier.send_batch_alerts(self.pending_alerts)
        
        if success:
            for alert in self.pending_alerts:
                if alert.alert_id:
                    self._mark_alert_sent(alert)
            self.pending_alerts.clear()
            self.last_batch_time = datetime.now()
        
        return success
    
    def _mark_alert_sent(self, alert: Alert):
        """Mark alert as sent in database"""
        query = """
            UPDATE alert 
            SET sent = 1, sent_at = ? 
            WHERE alert_id = ?
        """
        self.db.execute_query(query, (datetime.now(), alert.alert_id))
    
    def send_unsent_alerts(self):
        """Send any unsent alerts from database"""
        query = """
            SELECT * FROM alert 
            WHERE sent = 0 
            ORDER BY triggered_at
            LIMIT 10
        """
        
        results = self.db.execute_query(query)
        
        for row in results:
            alert = Alert(
                alert_id=row['alert_id'],
                triggered_at=row['triggered_at'],
                race_id=row['race_id'],
                entry_id=row['entry_id'],
                alert_type=row['alert_type'],
                threshold_value=row['threshold_value'],
                actual_value=row['actual_value'],
                message=row['message'],
                sent=False
            )
            
            self.notify(alert)