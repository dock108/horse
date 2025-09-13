# Issue 091325-6: Email Notification Module

**Priority**: Medium  
**Component**: Notifications - Email Delivery  
**Beta Blocker**: No (System can function with console alerts only)  
**Discovered**: 2025-09-13  
**Status**: Awaiting User Testing  
**Resolved**: [Pending]

## Problem Description

The system needs an email notification module to send formatted alert messages to users when betting conditions are met. The module must support SMTP with TLS, handle authentication securely, format alerts clearly, and manage delivery retries.

## Investigation Areas

1. SMTP configuration and authentication
2. Email formatting (HTML vs plain text)
3. TLS/SSL security implementation
4. Retry logic for failed deliveries
5. Email templates for different alert types
6. Batch sending for multiple alerts
7. Rate limiting to avoid spam filters
8. Delivery confirmation and logging

## Expected Behavior

A robust email notification system with:
- SMTP client with TLS support
- Secure credential handling
- Well-formatted alert emails
- Retry mechanism for failures
- Template-based email generation
- Batch alert aggregation
- Delivery tracking
- Clear error handling and logging

## Files to Investigate

- `src/notifications/email.py` (email sender)
- `src/notifications/templates.py` (email templates)
- `src/notifications/formatter.py` (alert formatting)
- `tests/test_notifications.py` (notification tests)

## Root Cause Analysis

Not applicable - this is initial implementation work.

## Solution Implemented

### 1. Email Sender Core (❌ Not Started)

**email.py**:
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import time

from ..database.models import Alert
from ..utils.config import config

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Handle email notifications for alerts"""
    
    def __init__(self):
        self.email_config = config.get_email_config()
        self.enabled = self.email_config.enabled if self.email_config else False
        self.last_send_time = 0
        self.min_send_interval = 1.0  # seconds between emails
        
    def send_alert(self, alert: Alert) -> bool:
        """Send a single alert via email"""
        if not self.enabled:
            logger.info("Email notifications disabled, skipping")
            return False
        
        subject = self._format_subject(alert)
        body = self._format_body(alert)
        
        return self._send_email(subject, body)
    
    def send_batch_alerts(self, alerts: List[Alert]) -> bool:
        """Send multiple alerts in a single email"""
        if not self.enabled or not alerts:
            return False
        
        subject = f"{self.email_config.subject_prefix} {len(alerts)} New Alerts"
        body = self._format_batch_body(alerts)
        
        return self._send_email(subject, body)
    
    def _send_email(self, subject: str, body: str, retry_count: int = 0) -> bool:
        """Send email with retry logic"""
        max_retries = self.email_config.max_retries
        
        try:
            # Rate limiting
            self._rate_limit()
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config.sender
            msg['To'] = self.email_config.recipient
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            
            # Add both plain text and HTML parts
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(self._to_html(body), 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Connect and send
            with smtplib.SMTP(self.email_config.smtp_server, 
                             self.email_config.smtp_port) as server:
                
                if self.email_config.use_tls:
                    server.starttls()
                
                if self.email_config.smtp_username and self.email_config.smtp_password:
                    server.login(self.email_config.smtp_username, 
                               self.email_config.smtp_password)
                
                server.send_message(msg)
                
            logger.info(f"Email sent successfully: {subject}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
            
        except smtplib.SMTPException as e:
            logger.warning(f"SMTP error (attempt {retry_count + 1}/{max_retries}): {e}")
            
            if retry_count < max_retries - 1:
                time.sleep(2 ** retry_count)  # exponential backoff
                return self._send_email(subject, body, retry_count + 1)
            
            logger.error(f"Failed to send email after {max_retries} attempts")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def _rate_limit(self):
        """Enforce rate limiting between emails"""
        elapsed = time.time() - self.last_send_time
        if elapsed < self.min_send_interval:
            time.sleep(self.min_send_interval - elapsed)
        self.last_send_time = time.time()
    
    def _format_subject(self, alert: Alert) -> str:
        """Format email subject for alert"""
        prefix = self.email_config.subject_prefix
        alert_type = alert.alert_type.replace('_', ' ').title()
        return f"{prefix} {alert_type}"
    
    def _format_body(self, alert: Alert) -> str:
        """Format email body for single alert"""
        template = AlertEmailTemplate()
        return template.format_alert(alert)
    
    def _format_batch_body(self, alerts: List[Alert]) -> str:
        """Format email body for multiple alerts"""
        template = AlertEmailTemplate()
        return template.format_batch(alerts)
    
    def _to_html(self, text_body: str) -> str:
        """Convert plain text body to HTML"""
        # Basic conversion - could be enhanced with templates
        html = text_body.replace('\n', '<br>\n')
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert {{ 
                    background-color: #f0f0f0; 
                    border-left: 4px solid #ff6b6b;
                    padding: 10px;
                    margin: 10px 0;
                }}
                .header {{ font-weight: bold; color: #333; }}
                .value {{ color: #ff6b6b; font-weight: bold; }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        return html
```

### 2. Email Templates (❌ Not Started)

**templates.py**:
```python
from typing import List
from datetime import datetime
from ..database.models import Alert

class AlertEmailTemplate:
    """Templates for formatting alert emails"""
    
    def format_alert(self, alert: Alert) -> str:
        """Format a single alert for email"""
        
        alert_type_descriptions = {
            'win_odds_low': 'Low Win Odds Alert',
            'win_odds_high': 'High Win Odds Alert',
            'odds_change': 'Significant Odds Change',
            'exacta_low': 'Low Exacta Payout',
            'exacta_high': 'High Exacta Payout',
            'discrepancy': 'Pool Discrepancy Detected'
        }
        
        description = alert_type_descriptions.get(alert.alert_type, 'Odds Alert')
        
        body = f"""
🏇 {description}
{'=' * 50}

Alert Details:
• Time: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
• Message: {alert.message}
"""
        
        if alert.threshold_value is not None:
            body += f"• Threshold: {alert.threshold_value:.2f}\n"
        
        if alert.actual_value is not None:
            body += f"• Actual Value: {alert.actual_value:.2f}\n"
        
        body += f"""
• Race ID: {alert.race_id}
• Entry ID: {alert.entry_id if alert.entry_id else 'N/A'}

{'=' * 50}
This is an automated alert from your Horse Racing Odds Tracking System.
        """
        
        return body.strip()
    
    def format_batch(self, alerts: List[Alert]) -> str:
        """Format multiple alerts for batch email"""
        
        body = f"""
🏇 Multiple Alerts Triggered
{'=' * 50}

You have {len(alerts)} new alerts:

"""
        
        # Group alerts by type
        alerts_by_type = {}
        for alert in alerts:
            alert_type = alert.alert_type
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = []
            alerts_by_type[alert_type].append(alert)
        
        # Format each group
        for alert_type, type_alerts in alerts_by_type.items():
            type_name = alert_type.replace('_', ' ').title()
            body += f"\n{type_name} ({len(type_alerts)} alerts):\n"
            body += "-" * 30 + "\n"
            
            for alert in type_alerts[:5]:  # Limit to first 5 of each type
                body += f"  • {alert.triggered_at.strftime('%H:%M:%S')} - {alert.message}\n"
            
            if len(type_alerts) > 5:
                body += f"  ... and {len(type_alerts) - 5} more\n"
        
        body += f"""

{'=' * 50}
Summary:
• Total Alerts: {len(alerts)}
• Time Range: {alerts[0].triggered_at.strftime('%H:%M')} - {alerts[-1].triggered_at.strftime('%H:%M')}
• Alert Types: {', '.join(alerts_by_type.keys())}

This is an automated alert from your Horse Racing Odds Tracking System.
        """
        
        return body.strip()
    
    def format_daily_summary(self, alerts: List[Alert], date: datetime) -> str:
        """Format daily summary email"""
        
        body = f"""
📊 Daily Alert Summary - {date.strftime('%Y-%m-%d')}
{'=' * 50}

Total Alerts Today: {len(alerts)}

Alert Breakdown:
"""
        
        # Count by type
        type_counts = {}
        for alert in alerts:
            type_counts[alert.alert_type] = type_counts.get(alert.alert_type, 0) + 1
        
        for alert_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            type_name = alert_type.replace('_', ' ').title()
            body += f"  • {type_name}: {count} alerts\n"
        
        # Top triggering races
        race_counts = {}
        for alert in alerts:
            race_counts[alert.race_id] = race_counts.get(alert.race_id, 0) + 1
        
        body += f"\nMost Active Races:\n"
        for race_id, count in sorted(race_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            body += f"  • Race {race_id}: {count} alerts\n"
        
        body += f"""

{'=' * 50}
This is your daily summary from the Horse Racing Odds Tracking System.
        """
        
        return body.strip()
```

### 3. Notification Manager (❌ Not Started)

**manager.py**:
```python
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
        
        # Update alert status in database
        if success:
            self._mark_alert_sent(alert)
        
        # Could add other notification channels here (SMS, webhook, etc.)
        
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
    
    def send_daily_summary(self, date: Optional[datetime] = None):
        """Send daily summary email"""
        if not date:
            date = datetime.now().date()
        
        query = """
            SELECT * FROM alert 
            WHERE DATE(triggered_at) = ? 
            ORDER BY triggered_at
        """
        
        results = self.db.execute_query(query, (date,))
        
        if results:
            alerts = [Alert(**dict(row)) for row in results]
            
            from .templates import AlertEmailTemplate
            template = AlertEmailTemplate()
            
            subject = f"Daily Alert Summary - {date}"
            body = template.format_daily_summary(alerts, date)
            
            self.email_notifier._send_email(subject, body)
```

## Testing Requirements

### Manual Testing Steps
1. Configure SMTP settings in config.yaml
2. Test SMTP connection
3. Send test email
4. Test with invalid credentials
5. Test retry logic with network issues
6. Test batch alert sending
7. Verify email formatting (HTML and plain text)

### Test Scenarios
- [ ] Email configuration loads correctly
- [ ] SMTP connection establishes with TLS
- [ ] Authentication works with credentials
- [ ] Single alert email sends successfully
- [ ] Batch alerts aggregate properly
- [ ] Email templates format correctly
- [ ] HTML conversion works
- [ ] Retry logic handles failures
- [ ] Rate limiting prevents spam
- [ ] Unsent alerts get retried
- [ ] Daily summary generates correctly

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