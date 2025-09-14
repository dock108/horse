"""Tests for alert system"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from src.alerts.engine import AlertEngine, AlertContext, AlertResult
from src.alerts.evaluators import (
    WinOddsThresholdEvaluator,
    RateOfChangeEvaluator,
    ExactaPayoutEvaluator
)
from src.alerts.suppressors import AlertSuppressor
from src.database.models import Alert


class TestAlertEngine:
    """Test alert engine"""

    @pytest.fixture
    def mock_db(self):
        """Mock database manager"""
        return Mock()

    @pytest.fixture
    def alert_engine(self, mock_db):
        """Create alert engine with mock database"""
        with patch("src.alerts.engine.config") as mock_config:
            mock_config.get_alert_config.return_value = Mock(
                enabled=True,
                win_odds_min=2.0,
                win_odds_max=20.0,
                exacta_min_payout=10.0,
                exacta_max_payout=1000.0
            )
            return AlertEngine(mock_db)

    def test_init_evaluators(self, alert_engine):
        """Test evaluator initialization"""
        assert "win_threshold" in alert_engine.evaluators
        assert "exacta_threshold" in alert_engine.evaluators
        assert "rate_change" in alert_engine.evaluators

    def test_evaluate_snapshot_disabled(self, mock_db):
        """Test evaluation when alerts are disabled"""
        with patch("src.alerts.engine.config") as mock_config:
            mock_config.get_alert_config.return_value = Mock(enabled=False)
            engine = AlertEngine(mock_db)

            result = engine.evaluate_snapshot({"race_id": 1})
            assert result == []

    def test_evaluate_snapshot_with_alerts(self, alert_engine, mock_db):
        """Test snapshot evaluation that triggers alerts"""
        snapshot_data = {
            "race_id": 1,
            "track": "Test Track",
            "fetched_at": datetime.now(),
            "entries": [
                {
                    "entry_id": 1,
                    "horse_name": "Thunder",
                    "program_number": "1",
                    "win_odds_decimal": 1.5  # Below min threshold
                }
            ]
        }

        # Mock previous snapshot
        alert_engine._get_previous_snapshot = Mock(return_value=None)
        alert_engine._save_alerts = Mock()
        alert_engine.suppressor.is_suppressed = Mock(return_value=False)

        alerts = alert_engine.evaluate_snapshot(snapshot_data)

        assert len(alerts) > 0
        alert_engine._save_alerts.assert_called_once()

    def test_get_previous_snapshot(self, alert_engine, mock_db):
        """Test getting previous snapshot"""
        mock_db.execute_query.return_value = [{"test": "data"}]

        result = alert_engine._get_previous_snapshot(1)
        assert result == {"test": "data"}

        # No previous snapshot
        mock_db.execute_query.return_value = []
        result = alert_engine._get_previous_snapshot(1)
        assert result is None

    def test_get_previous_entry_data(self, alert_engine, mock_db):
        """Test getting previous entry data"""
        # With snapshot
        mock_db.execute_query.return_value = [{
            "win_odds_decimal": 5.0,
            "win_pool_amount": 10000
        }]

        result = alert_engine._get_previous_entry_data({"test": "snapshot"}, 1)
        assert result["win_odds_decimal"] == 5.0

        # No snapshot
        result = alert_engine._get_previous_entry_data(None, 1)
        assert result is None

    def test_evaluate_exacta_alerts(self, alert_engine):
        """Test exacta alert evaluation"""
        snapshot_data = {
            "race_id": 1,
            "track": "Test Track",
            "fetched_at": datetime.now(),
            "exacta_probables": {
                "probables": {
                    "1-2": 5.0,   # Below min payout
                    "1-3": 2000.0  # Above max payout
                }
            }
        }

        alert_engine.suppressor.is_suppressed = Mock(return_value=False)
        alerts = alert_engine._evaluate_exacta_alerts(snapshot_data)

        assert len(alerts) == 2
        assert any(a.alert_type == "exacta_low" for a in alerts)
        assert any(a.alert_type == "exacta_high" for a in alerts)

    def test_create_alert(self, alert_engine):
        """Test alert creation from result"""
        context = AlertContext(
            race_id=1,
            entry_id=2,
            track_name="Test Track",
            horse_name="Thunder",
            program_number="1",
            timestamp=datetime.now()
        )

        result = AlertResult(
            should_trigger=True,
            alert_type="win_odds_low",
            message="Test alert",
            threshold_value=2.0,
            actual_value=1.5,
            context=context
        )

        alert = alert_engine._create_alert(result)

        assert alert.race_id == 1
        assert alert.entry_id == 2
        assert alert.alert_type == "win_odds_low"
        assert alert.message == "Test alert"
        assert alert.sent is False

    def test_save_alerts(self, alert_engine, mock_db):
        """Test saving alerts to database"""
        alert = Alert(
            triggered_at=datetime.now(),
            race_id=1,
            entry_id=2,
            alert_type="test",
            threshold_value=2.0,
            actual_value=1.5,
            message="Test",
            sent=False
        )

        mock_db.execute_insert.return_value = 123
        alert_engine._save_alerts([alert])

        mock_db.execute_insert.assert_called_once()
        assert alert.alert_id == 123


class TestEvaluators:
    """Test alert evaluators"""

    def test_win_odds_threshold_evaluator_low(self):
        """Test win odds below minimum threshold"""
        evaluator = WinOddsThresholdEvaluator(min_odds=2.0, max_odds=20.0)

        context = Mock(
            horse_name="Thunder",
            program_number="1",
            track_name="Test Track"
        )

        result = evaluator.evaluate(
            {"win_odds_decimal": 1.5},
            None,
            context
        )

        assert result is not None
        assert result.should_trigger is True
        assert result.alert_type == "win_odds_low"
        assert result.actual_value == 1.5

    def test_win_odds_threshold_evaluator_high(self):
        """Test win odds above maximum threshold"""
        evaluator = WinOddsThresholdEvaluator(min_odds=2.0, max_odds=20.0)

        context = Mock(
            horse_name="Thunder",
            program_number="1",
            track_name="Test Track"
        )

        result = evaluator.evaluate(
            {"win_odds_decimal": 25.0},
            None,
            context
        )

        assert result is not None
        assert result.alert_type == "win_odds_high"
        assert result.actual_value == 25.0

    def test_win_odds_threshold_evaluator_within_range(self):
        """Test win odds within acceptable range"""
        evaluator = WinOddsThresholdEvaluator(min_odds=2.0, max_odds=20.0)

        result = evaluator.evaluate(
            {"win_odds_decimal": 10.0},
            None,
            Mock()
        )

        assert result is None

    def test_rate_of_change_evaluator(self):
        """Test rate of change evaluator"""
        evaluator = RateOfChangeEvaluator(min_change_percent=25.0)

        context = Mock(horse_name="Thunder")

        # Significant increase
        result = evaluator.evaluate(
            {"win_odds_decimal": 10.0},
            {"win_odds_decimal": 5.0},
            context
        )

        assert result is not None
        assert result.alert_type == "odds_change"
        assert "increased" in result.message

        # Significant decrease
        result = evaluator.evaluate(
            {"win_odds_decimal": 5.0},
            {"win_odds_decimal": 10.0},
            context
        )

        assert result is not None
        assert "decreased" in result.message

        # Small change (no alert)
        result = evaluator.evaluate(
            {"win_odds_decimal": 5.5},
            {"win_odds_decimal": 5.0},
            context
        )

        assert result is None

    def test_rate_of_change_evaluator_no_previous(self):
        """Test rate of change with no previous data"""
        evaluator = RateOfChangeEvaluator()

        result = evaluator.evaluate(
            {"win_odds_decimal": 10.0},
            None,
            Mock()
        )

        assert result is None

    def test_exacta_payout_evaluator(self):
        """Test exacta payout evaluator"""
        evaluator = ExactaPayoutEvaluator(min_payout=10.0, max_payout=1000.0)

        context = Mock(track_name="Test Track")

        # Low payout
        result = evaluator.evaluate(
            {"payout": 5.0},
            None,
            context
        )

        assert result is not None
        assert result.alert_type == "exacta_low"

        # High payout
        result = evaluator.evaluate(
            {"payout": 2000.0},
            None,
            context
        )

        assert result is not None
        assert result.alert_type == "exacta_high"

        # Normal payout
        result = evaluator.evaluate(
            {"payout": 100.0},
            None,
            context
        )

        assert result is None


class TestAlertSuppressor:
    """Test alert suppression"""

    @pytest.fixture
    def suppressor(self):
        """Create suppressor with mock database"""
        mock_db = Mock()
        mock_db.execute_query.return_value = []
        return AlertSuppressor(mock_db)

    def test_is_suppressed_new_alert(self, suppressor):
        """Test suppression for new alert"""
        result = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=2),
            threshold_value=2.0
        )

        assert suppressor.is_suppressed(result) is False

    def test_is_suppressed_duplicate_in_cache(self, suppressor):
        """Test suppression for duplicate in cache"""
        result = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=2),
            threshold_value=2.0
        )

        # Add to cache
        alert_hash = suppressor._generate_alert_hash(result)
        suppressor.recent_alerts[alert_hash] = datetime.now()

        assert suppressor.is_suppressed(result) is True

    def test_is_suppressed_old_duplicate_in_cache(self, suppressor):
        """Test old duplicate in cache is not suppressed"""
        result = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=2),
            threshold_value=2.0
        )

        # Add old entry to cache
        alert_hash = suppressor._generate_alert_hash(result)
        suppressor.recent_alerts[alert_hash] = datetime.now() - timedelta(hours=1)

        assert suppressor.is_suppressed(result) is False

    def test_check_database_suppression(self, suppressor):
        """Test database suppression check"""
        result = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=2)
        )

        # No duplicates
        suppressor.db.execute_query.return_value = [{"count": 0}]
        assert suppressor._check_database_suppression(result) is False

        # Has duplicates
        suppressor.db.execute_query.return_value = [{"count": 1}]
        assert suppressor._check_database_suppression(result) is True

    def test_clean_cache(self, suppressor):
        """Test cache cleaning"""
        # Add old and new entries
        suppressor.recent_alerts = {
            "old": datetime.now() - timedelta(hours=1),
            "new": datetime.now()
        }

        suppressor.duplicate_window = 300  # 5 minutes
        suppressor._clean_cache()

        assert "old" not in suppressor.recent_alerts
        assert "new" in suppressor.recent_alerts

    def test_generate_alert_hash(self, suppressor):
        """Test alert hash generation"""
        result1 = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=2),
            threshold_value=2.0
        )

        result2 = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=2),
            threshold_value=2.0
        )

        result3 = Mock(
            alert_type="test",
            context=Mock(race_id=1, entry_id=3),  # Different entry
            threshold_value=2.0
        )

        hash1 = suppressor._generate_alert_hash(result1)
        hash2 = suppressor._generate_alert_hash(result2)
        hash3 = suppressor._generate_alert_hash(result3)

        assert hash1 == hash2  # Same alert
        assert hash1 != hash3  # Different alert


if __name__ == "__main__":
    pytest.main([__file__, "-v"])