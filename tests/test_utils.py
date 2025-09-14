"""Tests for utility modules"""

import pytest
import tempfile
import os
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml

from src.utils.config import ConfigManager, TrackConfig, EmailConfig, AlertConfig
from src.utils.health import HealthMonitor
from src.utils.logging_config import setup_logging


class TestConfigManager:
    """Test configuration management"""

    def test_default_config(self):
        """Test loading default configuration"""
        with patch("src.utils.config.Path.exists", return_value=False):
            config = ConfigManager()
            config.load_config("nonexistent.yaml")

            # Should load defaults
            assert config.get("system.environment") == "development"
            assert config.get("system.log_level") == "INFO"
            assert len(config.get_tracks()) > 0

    def test_load_from_file(self):
        """Test loading configuration from file"""
        config_data = {
            "system": {
                "environment": "test",
                "log_level": "DEBUG",
                "database_path": "test.db"
            },
            "tracks": [
                {
                    "name": "Test Track",
                    "code": "TST",
                    "url": "http://test.com",
                    "enabled": True
                }
            ],
            "alerts": {
                "enabled": True,
                "win_odds": {"min_odds": 2.0, "max_odds": 10.0}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            config = ConfigManager()
            config.load_config(temp_path)

            assert config.get("system.environment") == "test"
            assert config.get("system.log_level") == "DEBUG"
            tracks = config.get_tracks()
            assert len(tracks) == 1
            assert tracks[0].name == "Test Track"
        finally:
            os.unlink(temp_path)

    def test_environment_variable_substitution(self):
        """Test environment variable substitution in config"""
        config_data = {
            "email": {
                "smtp_username": "${TEST_SMTP_USER}",
                "smtp_password": "${TEST_SMTP_PASS}"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            os.environ["TEST_SMTP_USER"] = "testuser"
            os.environ["TEST_SMTP_PASS"] = "testpass"

            config = ConfigManager()
            config.load_config(temp_path)

            assert config.get("email.smtp_username") == "testuser"
            assert config.get("email.smtp_password") == "testpass"
        finally:
            os.unlink(temp_path)
            os.environ.pop("TEST_SMTP_USER", None)
            os.environ.pop("TEST_SMTP_PASS", None)

    def test_get_tracks(self):
        """Test getting track configurations"""
        config = Config()
        config._config = {
            "tracks": [
                {"name": "Track1", "code": "T1", "url": "http://t1.com", "enabled": True},
                {"name": "Track2", "code": "T2", "url": "http://t2.com", "enabled": False},
            ]
        }

        # Get all tracks
        all_tracks = config.get_tracks(enabled_only=False)
        assert len(all_tracks) == 2

        # Get enabled tracks only
        enabled_tracks = config.get_tracks(enabled_only=True)
        assert len(enabled_tracks) == 1
        assert enabled_tracks[0].name == "Track1"

    def test_get_email_config(self):
        """Test getting email configuration"""
        config = Config()

        # No email config
        config._config = {}
        assert config.get_email_config() is None

        # Email disabled
        config._config = {"email": {"enabled": False}}
        assert config.get_email_config() is None

        # Email enabled
        config._config = {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "sender": "test@test.com",
                "recipient": "user@test.com"
            }
        }
        email_config = config.get_email_config()
        assert email_config is not None
        assert email_config.smtp_server == "smtp.test.com"
        assert email_config.smtp_port == 587

    def test_get_alert_config(self):
        """Test getting alert configuration"""
        config = Config()
        config._config = {
            "alerts": {
                "enabled": True,
                "win_odds": {"min_odds": 1.5, "max_odds": 20.0},
                "exacta": {"min_payout": 5.0, "max_payout": 500.0}
            }
        }

        alert_config = config.get_alert_config()
        assert alert_config.enabled is True
        assert alert_config.win_odds_min == 1.5
        assert alert_config.win_odds_max == 20.0
        assert alert_config.exacta_min_payout == 5.0
        assert alert_config.exacta_max_payout == 500.0

    def test_reload_config(self):
        """Test reloading configuration"""
        config = Config()
        config._config = {"test": "value"}

        with patch.object(config, 'load_config') as mock_load:
            config.reload()
            assert config._config is None
            mock_load.assert_called_once()


class TestHealthMonitor:
    """Test health monitoring"""

    def test_check_system_health_all_pass(self):
        """Test system health check when all checks pass"""
        mock_db = Mock()
        mock_db.execute_query.return_value = [{"count": 5}]

        with patch("src.utils.health.Path.exists", return_value=True):
            monitor = HealthMonitor(mock_db)
            result = monitor.check_system_health()
            assert result is True

    def test_check_system_health_with_failure(self):
        """Test system health check with failures"""
        mock_db = Mock()
        mock_db.execute_query.side_effect = Exception("DB Error")

        monitor = HealthMonitor(mock_db)
        result = monitor.check_system_health()
        assert result is False

    def test_check_database(self):
        """Test database health check"""
        mock_db = Mock()

        # Success case
        mock_db.execute_query.return_value = [{"count": 5}]
        monitor = HealthMonitor(mock_db)
        assert monitor._check_database() is True

        # No tables (still OK)
        mock_db.execute_query.return_value = [{"count": 0}]
        assert monitor._check_database() is True

        # Database error
        mock_db.execute_query.side_effect = Exception("Connection failed")
        assert monitor._check_database() is False

    def test_check_directories(self):
        """Test directory health check"""
        mock_db = Mock()
        monitor = HealthMonitor(mock_db)

        with patch("src.utils.health.Path") as mock_path:
            mock_dir = Mock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            # Should create missing directories
            result = monitor._check_directories()
            assert result is True
            assert mock_dir.mkdir.called

    def test_check_configuration(self):
        """Test configuration health check"""
        mock_db = Mock()
        monitor = HealthMonitor(mock_db)

        with patch("src.utils.health.config") as mock_config:
            # With tracks
            mock_config.get_tracks.return_value = [Mock(), Mock()]
            assert monitor._check_configuration() is True

            # No tracks (still OK)
            mock_config.get_tracks.return_value = []
            assert monitor._check_configuration() is True

    def test_get_status(self):
        """Test getting detailed status"""
        mock_db = Mock()
        mock_db.execute_query.return_value = [{"count": 5}]

        with patch("src.utils.health.Path.exists", return_value=True):
            monitor = HealthMonitor(mock_db)
            status = monitor.get_status()

            assert "healthy" in status
            assert "checks" in status
            assert "database" in status["checks"]
            assert "directories" in status["checks"]
            assert "configuration" in status["checks"]


class TestLoggingConfig:
    """Test logging configuration"""

    def test_setup_logging_creates_directory(self):
        """Test that logging setup creates log directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            setup_logging(level="INFO", log_dir=str(log_dir))
            assert log_dir.exists()

    def test_setup_logging_configures_handlers(self):
        """Test logging handler configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                setup_logging(level="DEBUG", log_dir=tmpdir)

                # Should add handlers
                assert mock_logger.addHandler.called
                assert mock_logger.setLevel.called_with(logging.DEBUG)

    def test_setup_logging_levels(self):
        """Test different logging levels"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test INFO level
            setup_logging(level="INFO", log_dir=tmpdir)
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG  # Root is always DEBUG

            # Test ERROR level
            setup_logging(level="ERROR", log_dir=tmpdir)

    def test_logging_formatters(self):
        """Test logging formatters are set correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            setup_logging(level="INFO", log_dir=tmpdir)

            root_logger = logging.getLogger()
            handlers = root_logger.handlers

            # Should have multiple handlers
            assert len(handlers) > 0

            # Check formatters are set
            for handler in handlers:
                assert handler.formatter is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])