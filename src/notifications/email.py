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
        if not self.email_config:
            return False
            
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
        if not self.email_config:
            return "Odds Alert"
        prefix = self.email_config.subject_prefix
        alert_type = alert.alert_type.replace('_', ' ').title()
        return f"{prefix} {alert_type}"
    
    def _format_body(self, alert: Alert) -> str:
        """Format email body for single alert"""
        from .templates import AlertEmailTemplate
        template = AlertEmailTemplate()
        return template.format_alert(alert)
    
    def _format_batch_body(self, alerts: List[Alert]) -> str:
        """Format email body for multiple alerts"""
        from .templates import AlertEmailTemplate
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