import logging
from typing import Dict, Any
from pathlib import Path

from ..database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor system health and perform checks"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.checks = {
            "database": self._check_database,
            "directories": self._check_directories,
            "configuration": self._check_configuration,
        }

    def check_system_health(self) -> bool:
        """Perform all health checks"""
        all_healthy = True

        for check_name, check_func in self.checks.items():
            try:
                result = check_func()
                if result:
                    logger.info(f"Health check passed: {check_name}")
                else:
                    logger.error(f"Health check failed: {check_name}")
                    all_healthy = False
            except Exception as e:
                logger.error(f"Health check error ({check_name}): {e}")
                all_healthy = False

        return all_healthy

    def _check_database(self) -> bool:
        """Check database connectivity and schema"""
        try:
            # Check if we can query the database
            query = "SELECT COUNT(*) as count FROM sqlite_master " "WHERE type='table'"
            result = self.db.execute_query(query)

            if result and result[0]["count"] > 0:
                logger.info(f"Database has {result[0]['count']} tables")
                return True
            else:
                logger.warning("Database has no tables")
                return True  # Still OK, tables will be created

        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return False

    def _check_directories(self) -> bool:
        """Check required directories exist"""
        required_dirs = ["data", "logs", "config"]

        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {dir_name}")
                except Exception as e:
                    logger.error(f"Failed to create directory {dir_name}: {e}")
                    return False

        return True

    def _check_configuration(self) -> bool:
        """Check configuration is valid"""
        from ..utils.config import config

        # Check if we have at least one track configured
        tracks = config.get_tracks()
        if not tracks:
            logger.warning("No tracks configured")
            return True  # Not a fatal error

        logger.info(f"Configuration has {len(tracks)} tracks")
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get detailed status information"""
        status = {"healthy": True, "checks": {}}

        for check_name, check_func in self.checks.items():
            try:
                status["checks"][check_name] = check_func()
            except Exception as e:
                status["checks"][check_name] = False
                status["healthy"] = False
                logger.error(f"Status check failed ({check_name}): {e}")

        return status
