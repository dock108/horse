import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class TrackConfig:
    name: str
    code: str = ""
    url: str = ""
    enabled: bool = True
    scrape_win: bool = True
    scrape_exacta: bool = True

@dataclass
class EmailConfig:
    enabled: bool
    smtp_server: str
    smtp_port: int
    use_tls: bool
    sender: str
    recipient: str
    smtp_username: str
    smtp_password: str
    subject_prefix: str = "[Odds Alert]"
    include_chart: bool = False
    max_retries: int = 3

@dataclass
class AlertConfig:
    enabled: bool
    win_odds_min: float
    win_odds_max: float
    exacta_min_payout: float
    exacta_max_payout: float
    duplicate_window: int = 300
    max_alerts_per_race: int = 10

class ConfigManager:
    """Singleton configuration manager"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_path: str = "config/config.yaml"):
        """Load configuration from YAML file"""
        # Load environment variables
        load_dotenv()
        
        config_file = Path(config_path)
        if not config_file.exists():
            # Try to use example config
            example_file = Path("config/config.yaml.example")
            if example_file.exists():
                logger.warning(f"Config file not found, using example: {example_file}")
                config_file = example_file
            else:
                # Use default minimal config
                self._config = self._get_default_config()
                return
        
        with open(config_file, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Substitute environment variables
        self._config = self._substitute_env_vars(raw_config)
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"Configuration loaded from {config_file}")
    
    def _get_default_config(self) -> Dict:
        """Get default minimal configuration"""
        return {
            'system': {
                'environment': 'development',
                'log_level': 'INFO',
                'database_path': 'data/horses.db'
            },
            'tracks': [
                {
                    'name': 'Test Track',
                    'code': 'TEST',
                    'url': 'https://example.com',
                    'enabled': True,
                    'scrape_win': True,
                    'scrape_exacta': False
                }
            ],
            'bet_types': {
                'win': {'enabled': True, 'min_pool_size': 1000},
                'exacta': {'enabled': False, 'min_pool_size': 500}
            },
            'scraping': {
                'default_interval': 300,
                'near_post_interval': 60,
                'near_post_threshold': 600,
                'min_request_delay': 2.0,
                'max_retries': 3,
                'retry_delay': 5,
                'timeout': 10
            },
            'alerts': {
                'enabled': True,
                'win_odds': {'min_odds': 1.5, 'max_odds': 20.0},
                'exacta': {'min_payout': 10.0, 'max_payout': 1000.0},
                'suppression': {'duplicate_window': 300, 'max_alerts_per_race': 10}
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'use_tls': True,
                'sender': '',
                'recipient': '',
                'smtp_username': '',
                'smtp_password': '',
                'subject_prefix': '[Odds Alert]',
                'max_retries': 3
            }
        }
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables in config"""
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_var = config[2:-1]
            value = os.getenv(env_var)
            if value is None:
                logger.warning(f"Environment variable {env_var} not set")
            return value or ""
        else:
            return config
    
    def _validate_config(self):
        """Validate configuration structure and values"""
        required_sections = ['system', 'tracks', 'scraping', 'alerts']
        
        for section in required_sections:
            if section not in self._config:
                logger.warning(f"Missing config section: {section}, using defaults")
        
        # Validate tracks
        if not self._config.get('tracks'):
            logger.warning("No tracks configured, using test track")
        
        # Validate email if enabled
        if self._config.get('email', {}).get('enabled'):
            required_email = ['smtp_server', 'smtp_port', 'sender', 'recipient']
            for field in required_email:
                if not self._config['email'].get(field):
                    logger.warning(f"Email {field} is required when email is enabled")
        
        # Validate numeric thresholds
        alerts = self._config.get('alerts', {})
        if alerts.get('enabled'):
            win_odds = alerts.get('win_odds', {})
            min_odds = win_odds.get('min_odds', 0)
            max_odds = win_odds.get('max_odds', float('inf'))
            if min_odds >= max_odds:
                logger.warning("min_odds should be less than max_odds")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated path
        Example: config.get('email.smtp_server')
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_tracks(self, enabled_only: bool = True) -> list[TrackConfig]:
        """Get list of track configurations"""
        tracks = []
        for track_dict in self._config.get('tracks', []):
            if not enabled_only or track_dict.get('enabled', True):
                tracks.append(TrackConfig(
                    name=track_dict.get('name', ''),
                    code=track_dict.get('code', ''),
                    url=track_dict.get('url', ''),
                    enabled=track_dict.get('enabled', True),
                    scrape_win=track_dict.get('scrape_win', True),
                    scrape_exacta=track_dict.get('scrape_exacta', False)
                ))
        return tracks
    
    def get_email_config(self) -> Optional[EmailConfig]:
        """Get email configuration if enabled"""
        email_dict = self._config.get('email', {})
        if email_dict.get('enabled'):
            return EmailConfig(**email_dict)
        return None
    
    def get_alert_config(self) -> AlertConfig:
        """Get alert configuration"""
        alerts = self._config.get('alerts', {})
        return AlertConfig(
            enabled=alerts.get('enabled', False),
            win_odds_min=alerts.get('win_odds', {}).get('min_odds', 1.0),
            win_odds_max=alerts.get('win_odds', {}).get('max_odds', 100.0),
            exacta_min_payout=alerts.get('exacta', {}).get('min_payout', 10.0),
            exacta_max_payout=alerts.get('exacta', {}).get('max_payout', 1000.0),
            duplicate_window=alerts.get('suppression', {}).get('duplicate_window', 300),
            max_alerts_per_race=alerts.get('suppression', {}).get('max_alerts_per_race', 10)
        )
    
    def reload(self):
        """Reload configuration from file"""
        self._config = None
        self.load_config()

# Global config instance
config = ConfigManager()