"""Tests for notification system"""

import pytest
import smtplib
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from email.mime.multipart import MIMEMultipart

from src.notifications.email import EmailNotifier
from src.notifications.manager import NotificationManager
from src.notifications.templates import AlertEmailTemplate
from src.database.models import Alert


class TestEmailNotifier:
    """Test email notification system"""

    @pytest.fixture
    def mock_email_config(self):
        """Mock email configuration"""
        config = Mock()
        config.enabled = True
        config.smtp_server = "smtp.test.com"
        config.smtp_port = 587
        config.use_tls = True
        config.sender = "sender@test.com"
        config.recipient = "recipient@test.com"
        config.smtp_username = "testuser"
        config.smtp_password = "testpass"
        config.subject_prefix = "[Test Alert]"
        config.max_retries = 3
        return config

    @pytest.fixture
    def email_notifier(self, mock_email_config):
        """Create email notifier with mock config"""
        with patch("src.notifications.email.config") as mock_config:
            mock_config.get_email_config.return_value = mock_email_config
            return EmailNotifier()

    def test_init_disabled(self):
        """Test initialization with email disabled"""
        with patch("src.notifications.email.config") as mock_config:
            mock_config.get_email_config.return_value = None
            notifier = EmailNotifier()
            assert notifier.enabled is False

    def test_send_alert_disabled(self):
        """Test sending alert when disabled"""
        with patch("src.notifications.email.config") as mock_config:
            mock_config.get_email_config.return_value = None
            notifier = EmailNotifier()

            alert = Mock()
            result = notifier.send_alert(alert)
            assert result is False

    @patch("smtplib.SMTP")
    def test_send_alert_success(self, mock_smtp_class, email_notifier):
        """Test successful alert sending"""
        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        alert = Alert(
            triggered_at=datetime.now(),
            race_id=1,
            entry_id=2,
            alert_type="win_odds_low",
            threshold_value=2.0,
            actual_value=1.5,
            message="Test alert",
            sent=False
        )

        result = email_notifier.send_alert(alert)

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_batch_alerts(self, mock_smtp_class, email_notifier):
        """Test sending batch alerts"""
        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        alerts = [
            Alert(
                triggered_at=datetime.now(),
                race_id=1,
                entry_id=i,
                alert_type="test",
                threshold_value=2.0,
                actual_value=1.5,
                message=f"Alert {i}",
                sent=False
            )
            for i in range(3)
        ]

        result = email_notifier.send_batch_alerts(alerts)

        assert result is True
        mock_smtp.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_email_auth_error(self, mock_smtp_class, email_notifier):
        """Test email authentication error"""
        mock_smtp = Mock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        alert = Mock()
        result = email_notifier._send_email("Subject", "Body")

        assert result is False

    @patch("smtplib.SMTP")
    def test_send_email_with_retry(self, mock_smtp_class, email_notifier):
        """Test email sending with retry on failure"""
        mock_smtp = Mock()

        # Fail twice, succeed on third try
        send_attempts = [
            smtplib.SMTPException("Temporary error"),
            smtplib.SMTPException("Temporary error"),
            None  # Success
        ]
        mock_smtp.send_message.side_effect = send_attempts
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        with patch("time.sleep"):  # Skip actual sleep
            result = email_notifier._send_email("Subject", "Body")

        assert result is True
        assert mock_smtp.send_message.call_count == 3

    @patch("smtplib.SMTP")
    def test_send_email_max_retries_exceeded(self, mock_smtp_class, email_notifier):
        """Test email sending fails after max retries"""
        mock_smtp = Mock()
        mock_smtp.send_message.side_effect = smtplib.SMTPException("Permanent error")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        with patch("time.sleep"):
            result = email_notifier._send_email("Subject", "Body")

        assert result is False
        assert mock_smtp.send_message.call_count == 3

    def test_rate_limiting(self, email_notifier):
        """Test rate limiting between emails"""
        email_notifier.last_send_time = time.time()
        email_notifier.min_send_interval = 0.1

        with patch("time.sleep") as mock_sleep:
            email_notifier._rate_limit()
            mock_sleep.assert_called()

    def test_format_subject(self, email_notifier):
        """Test email subject formatting"""
        alert = Mock(alert_type="win_odds_low")
        subject = email_notifier._format_subject(alert)
        assert "[Test Alert]" in subject
        assert "Win Odds Low" in subject

    def test_format_body(self, email_notifier):
        """Test email body formatting"""
        alert = Mock()
        with patch("src.notifications.templates.AlertEmailTemplate") as mock_template:
            mock_template.return_value.format_alert.return_value = "Formatted body"
            body = email_notifier._format_body(alert)
            assert body == "Formatted body"

    def test_to_html(self, email_notifier):
        """Test converting text to HTML"""
        text = "Line 1\nLine 2\nLine 3"
        html = email_notifier._to_html(text)
        assert "<html>" in html
        assert "<br>" in html
        assert "Line 1" in html


class TestNotificationManager:
    """Test notification manager"""

    @pytest.fixture
    def mock_db(self):
        """Mock database manager"""
        return Mock()

    @pytest.fixture
    def notification_manager(self, mock_db):
        """Create notification manager"""
        with patch("src.notifications.manager.EmailNotifier") as mock_notifier:
            mock_notifier.return_value = Mock()
            return NotificationManager(mock_db)

    def test_notify_success(self, notification_manager, mock_db):
        """Test successful notification"""
        alert = Alert(
            alert_id=1,
            triggered_at=datetime.now(),
            race_id=1,
            entry_id=2,
            alert_type="test",
            threshold_value=2.0,
            actual_value=1.5,
            message="Test",
            sent=False
        )

        notification_manager.email_notifier.send_alert.return_value = True

        result = notification_manager.notify(alert)

        assert result is True
        mock_db.execute_update.assert_called_once()

    def test_notify_failure(self, notification_manager):
        """Test notification failure"""
        alert = Mock(alert_id=1)
        notification_manager.email_notifier.send_alert.return_value = False

        result = notification_manager.notify(alert)

        assert result is False

    def test_notify_batch(self, notification_manager, mock_db):
        """Test batch notification"""
        alerts = [Mock(alert_id=i) for i in range(5)]

        notification_manager.email_notifier.send_batch_alerts.return_value = True

        result = notification_manager.notify_batch(alerts)

        assert result is True
        assert mock_db.execute_update.call_count == 5

    def test_send_unsent_alerts(self, notification_manager, mock_db):
        """Test sending unsent alerts"""
        mock_db.execute_query.return_value = [
            {
                "alert_id": 1,
                "triggered_at": datetime.now(),
                "race_id": 1,
                "entry_id": 2,
                "alert_type": "test",
                "threshold_value": 2.0,
                "actual_value": 1.5,
                "message": "Test",
            }
        ]

        notification_manager.email_notifier.send_alert.return_value = True

        notification_manager.send_unsent_alerts()

        notification_manager.email_notifier.send_alert.assert_called_once()

    def test_mark_as_sent(self, notification_manager, mock_db):
        """Test marking alert as sent"""
        alert = Mock(alert_id=123)

        notification_manager._mark_as_sent(alert)

        mock_db.execute_update.assert_called_with(
            "UPDATE alert SET sent = 1 WHERE alert_id = ?",
            (123,)
        )

    def test_get_alert_context(self, notification_manager, mock_db):
        """Test getting alert context"""
        alert = Mock(race_id=1, entry_id=2)

        mock_db.execute_query.side_effect = [
            [{"name": "Test Track"}],  # Track query
            [{"race_number": 5, "post_time": "14:30"}],  # Race query
            [{"name": "Thunder", "program_number": "1"}]  # Entry query
        ]

        context = notification_manager._get_alert_context(alert)

        assert context["track_name"] == "Test Track"
        assert context["race_number"] == 5
        assert context["horse_name"] == "Thunder"


class TestAlertEmailTemplate:
    """Test email templates"""

    @pytest.fixture
    def template(self):
        """Create template instance"""
        return AlertEmailTemplate()

    def test_format_alert(self, template):
        """Test formatting single alert"""
        alert = Alert(
            triggered_at=datetime.now(),
            race_id=1,
            entry_id=2,
            alert_type="win_odds_low",
            threshold_value=2.0,
            actual_value=1.5,
            message="Test alert message",
            sent=False
        )

        formatted = template.format_alert(alert)

        assert "Low Win Odds Alert" in formatted
        assert "Test alert message" in formatted
        assert "Threshold: 2.0" in formatted
        assert "Actual: 1.5" in formatted

    def test_format_batch(self, template):
        """Test formatting batch alerts"""
        alerts = [
            Alert(
                triggered_at=datetime.now(),
                race_id=1,
                entry_id=i,
                alert_type="win_odds_low" if i % 2 == 0 else "win_odds_high",
                threshold_value=2.0,
                actual_value=1.5,
                message=f"Alert {i}",
                sent=False
            )
            for i in range(10)
        ]

        formatted = template.format_batch(alerts)

        assert "Alert Summary" in formatted
        assert "10 new alerts" in formatted
        assert "Win Odds Low" in formatted
        assert "Win Odds High" in formatted
        assert "Alert 0" in formatted
        assert "... and" in formatted  # Truncation message

    def test_format_batch_grouped_by_type(self, template):
        """Test batch formatting groups by alert type"""
        alerts = [
            Alert(
                triggered_at=datetime.now(),
                race_id=1,
                entry_id=1,
                alert_type="type_a",
                threshold_value=2.0,
                actual_value=1.5,
                message="Alert A",
                sent=False
            ),
            Alert(
                triggered_at=datetime.now(),
                race_id=1,
                entry_id=2,
                alert_type="type_b",
                threshold_value=2.0,
                actual_value=1.5,
                message="Alert B",
                sent=False
            ),
            Alert(
                triggered_at=datetime.now(),
                race_id=1,
                entry_id=3,
                alert_type="type_a",
                threshold_value=2.0,
                actual_value=1.5,
                message="Alert A2",
                sent=False
            ),
        ]

        formatted = template.format_batch(alerts)

        assert "Type A (2 alerts)" in formatted
        assert "Type B (1 alerts)" in formatted

    def test_format_empty_batch(self, template):
        """Test formatting empty batch"""
        formatted = template.format_batch([])

        assert "0 new alerts" in formatted
        assert "No alerts to report" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])