# Issue 091325-4: Configuration Management System

**Priority**: High  
**Component**: Configuration - System Settings  
**Beta Blocker**: Yes (Required for configurable behavior across all modules)  
**Discovered**: 2025-09-13  
**Status**: Awaiting User Testing  
**Resolved**: [Pending]

## Problem Description

The system needs a centralized configuration management system using YAML files to control track selection, bet types, alert thresholds, email settings, and scraping cadence. Configuration must be validated, support environment variables for secrets, and be easily accessible across all modules.

## Investigation Areas

1. YAML schema design and validation
2. Environment variable integration for secrets
3. Configuration loading and caching strategy
4. Default values and override mechanisms
5. Configuration hot-reloading capabilities
6. Validation of required fields and data types
7. Secure handling of credentials

## Expected Behavior

A robust configuration system with:
- Central config.yaml file with clear structure
- Schema validation on load
- Environment variable support for sensitive data
- Default configuration template
- Configuration singleton for global access
- Clear error messages for invalid configs
- Support for multiple environments (dev, prod)

## Files to Investigate

- `config/config.yaml.example` (configuration template)
- `src/utils/config.py` (configuration loader)
- `src/utils/validators.py` (configuration validators)
- `tests/test_config.py` (configuration tests)
- `.env.example` (environment variables template)

## Root Cause Analysis

Not applicable - this is initial implementation work.

## Solution Implemented

### 1. Configuration Schema (❌ Not Started)

**config/config.yaml.example**:
```yaml
# Horse Racing Odds Tracking Configuration
# Copy to config.yaml and update with your settings

# System Settings
system:
  environment: development  # development, production
  log_level: INFO          # DEBUG, INFO, WARNING, ERROR
  database_path: data/horses.db
  
# Track Configuration
tracks:
  - name: "Belmont Park"
    code: "BEL"
    url: "https://www.example-racing.com/belmont"
    enabled: true
    scrape_win: true
    scrape_exacta: true
    
  - name: "Santa Anita Park"
    code: "SA"
    url: "https://www.example-racing.com/santa-anita"
    enabled: true
    scrape_win: true
    scrape_exacta: false
    
  - name: "Churchill Downs"
    code: "CD"
    url: "https://www.example-racing.com/churchill"
    enabled: false
    scrape_win: true
    scrape_exacta: true

# Bet Types to Monitor
bet_types:
  win:
    enabled: true
    min_pool_size: 1000  # Minimum pool size to track
  exacta:
    enabled: true
    min_pool_size: 500
    store_full_matrix: false  # If false, only store min/max payouts

# Scraping Configuration
scraping:
  # Default intervals (seconds)
  default_interval: 300  # 5 minutes
  near_post_interval: 60  # 1 minute when < 10 min to post
  near_post_threshold: 600  # seconds before post to increase frequency
  
  # Rate limiting
  min_request_delay: 2.0  # Minimum seconds between requests to same site
  max_retries: 3
  retry_delay: 5
  
  # Request settings
  timeout: 10
  user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# Alert Thresholds
alerts:
  enabled: true
  
  # Win pool alerts
  win_odds:
    min_odds: 1.5          # Alert if odds drop below
    max_odds: 20.0         # Alert if odds rise above
    min_change_percent: 25  # Alert on % change
    
  # Exacta alerts  
  exacta:
    min_payout: 10.0       # Alert if payout below
    max_payout: 1000.0     # Alert if payout above
    track_combinations:    # Specific combos to monitor
      - "1-2"
      - "2-1"
    
  # Cross-pool discrepancy
  discrepancy:
    enabled: true
    threshold_percent: 30   # Alert if win vs exacta implied odds differ by %
    
  # Alert suppression
  suppression:
    duplicate_window: 300   # Don't repeat same alert within seconds
    max_alerts_per_race: 10

# Email Notification Settings
email:
  enabled: true
  smtp_server: smtp.gmail.com
  smtp_port: 587
  use_tls: true
  sender: ${EMAIL_SENDER}  # Use environment variable
  recipient: ${EMAIL_RECIPIENT}
  # Credentials from environment
  smtp_username: ${SMTP_USERNAME}
  smtp_password: ${SMTP_PASSWORD}
  
  # Email format
  subject_prefix: "[Odds Alert]"
  include_chart: false
  max_retries: 3

# Dashboard Settings (optional)
dashboard:
  enabled: false
  host: "127.0.0.1"
  port: 8080
  auto_refresh: 30  # seconds
  show_historical: true
  chart_lookback: 3600  # seconds

# Data Retention
retention:
  odds_snapshots_days: 30
  alerts_days: 90
  cleanup_hour: 3  # Hour to run cleanup (24-hour format)
```

### 2. Configuration Loader (❌ Not Started)

**src/utils/config.py**:
```python
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
    code: str
    url: str
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
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Substitute environment variables
        self._config = self._substitute_env_vars(raw_config)
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"Configuration loaded from {config_file}")
    
    def _substitute_env_vars(self, config: Dict) -> Dict:
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
            return value
        else:
            return config
    
    def _validate_config(self):
        """Validate configuration structure and values"""
        required_sections = ['system', 'tracks', 'scraping', 'alerts', 'email']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required config section: {section}")
        
        # Validate tracks
        if not self._config.get('tracks'):
            raise ValueError("At least one track must be configured")
        
        for track in self._config['tracks']:
            if not track.get('name') or not track.get('url'):
                raise ValueError("Track must have name and url")
        
        # Validate email if enabled
        if self._config['email'].get('enabled'):
            required_email = ['smtp_server', 'smtp_port', 'sender', 'recipient']
            for field in required_email:
                if not self._config['email'].get(field):
                    raise ValueError(f"Email {field} is required when email is enabled")
        
        # Validate numeric thresholds
        alerts = self._config.get('alerts', {})
        if alerts.get('enabled'):
            win_odds = alerts.get('win_odds', {})
            if win_odds.get('min_odds', 0) >= win_odds.get('max_odds', float('inf')):
                raise ValueError("min_odds must be less than max_odds")
    
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
                tracks.append(TrackConfig(**track_dict))
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
```

### 3. Environment Variables Template (❌ Not Started)

**.env.example**:
```bash
# Email Configuration
EMAIL_SENDER=your-email@gmail.com
EMAIL_RECIPIENT=alerts@example.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password

# Optional: Database path override
# DATABASE_PATH=/custom/path/to/horses.db

# Optional: Environment override
# ENVIRONMENT=production
```

## Testing Requirements

### Manual Testing Steps
1. Copy config.yaml.example to config.yaml
2. Set environment variables in .env file
3. Load configuration: `python -m src.utils.config`
4. Verify all values load correctly
5. Test with missing required fields (should error)
6. Test with invalid values (should error)
7. Test environment variable substitution

### Test Scenarios
- [ ] Configuration loads from YAML file
- [ ] Environment variables substitute correctly
- [ ] Missing config file uses example
- [ ] Required fields validated
- [ ] Invalid values caught
- [ ] Track configurations parse correctly
- [ ] Email settings load when enabled
- [ ] Alert thresholds accessible
- [ ] Config singleton works globally
- [ ] Reload functionality works

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