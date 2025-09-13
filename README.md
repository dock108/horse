# Horse Racing Odds Tracking & Alert System

## ✅ Status: IMPLEMENTED - READY FOR UAT

A Python-based macOS tool that scrapes live pari-mutuel horse racing odds (Win and Exacta), stores time-series snapshots in SQLite, evaluates alert conditions (thresholds and discrepancies), and notifies the user via email. An optional dashboard visualizes current odds, odds history, and alert activity.

**Current Phase**: System fully implemented and functional. Ready for User Acceptance Testing.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Running](#running)
- [Dashboard (Optional)](#dashboard-optional)
- [Testing](#testing)
- [Documentation](#documentation)
- [Implementation Status](#implementation-status)

## Features
- Scrape Win odds for configured tracks; optionally ingest Exacta probables
- Store odds snapshots in SQLite with indices for fast queries
- Threshold-based alerts (e.g., min/max odds, min/max exacta payouts)
- Cross-pool discrepancy checks (Win vs Exacta favoritism)
- Email notifications via SMTP with TLS
- Optional dashboard for live odds, highlights, and historical charts

## Architecture
- **Scraper Module**: Requests/BS4; Selenium/Playwright if needed
- **Database Module**: SQLite, indices on `race_id` and timestamps
- **Alert Engine**: Thresholds, rate-of-change, deduplication
- **Notification Module**: SMTP with retry logic
- **Dashboard**: Flask/FastAPI or Streamlit (optional)
- **Config Management**: YAML-based configuration

Core flow: Config → Scrape → Normalize → Store (SQLite) → Evaluate Alerts → Notify (Email) → Visualize (Dashboard)

## Quick Start

### Prerequisites
- macOS (primary target platform)
- Python 3.11+ (tested with 3.11-3.13)
- SQLite3 (included with Python)

### 30-Second Test (Once Implemented)
```bash
# Setup (one time)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run test
python main.py --once --test

# Check results
sqlite3 data/horses.db "SELECT * FROM alert LIMIT 5;"
```

### Full Setup
1. Install Python 3.11+ on macOS
2. Clone repository and navigate to project directory
3. Create and activate virtual environment
4. Install dependencies: `pip install -r requirements.txt`
5. Copy config: `cp config/config.yaml.example config/config.yaml`
6. Configure tracks and thresholds
7. Run: `python main.py`

## Configuration

### Basic Configuration
Create `config/config.yaml`:

```yaml
tracks:
  - name: "Belmont Park"
    code: "BEL"
    url: "https://www.example-racing.com/belmont"
    enabled: true
    
bet_types:
  win:
    enabled: true
    min_pool_size: 1000
  exacta:
    enabled: true
    store_full_matrix: false

alerts:
  enabled: true
  win_odds:
    min_odds: 2.0
    max_odds: 20.0
  exacta:
    min_payout: 10.0
    max_payout: 1000.0

email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  use_tls: true
  sender: ${EMAIL_SENDER}  # Use environment variable
  recipient: ${EMAIL_RECIPIENT}
```

### Environment Variables
Create `.env` file:
```bash
EMAIL_SENDER=your-email@gmail.com
EMAIL_RECIPIENT=alerts@example.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
```

## Running

### Command Line Options
```bash
python main.py [options]

Options:
  --once          Run once and exit
  --test          Use test data generator
  --log-level     Set logging level (DEBUG, INFO, WARNING, ERROR)
  --config        Path to config file (default: config/config.yaml)
```

### Scheduling
- **Continuous**: Run `python main.py` for continuous monitoring
- **Background**: Use macOS LaunchAgent or cron
- **Near post-time**: Automatically increases to 60s intervals
- **Off-peak**: 5-minute intervals (configurable)
- **Logs**: Check `logs/` directory for details

## Dashboard (Optional)
- **Flask/FastAPI**: REST API + web interface for live odds
- **Streamlit**: Quick interactive dashboard
- **Features**: Live odds table, historical charts, alert log

## Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Tests
```bash
python tests/test_integration.py
```

### System Test
```bash
python main.py --once --test  # Run with test data
```

### Database Verification
```bash
sqlite3 data/horses.db ".tables"
sqlite3 data/horses.db "SELECT COUNT(*) FROM odds_snapshot;"
sqlite3 data/horses.db "SELECT * FROM alert ORDER BY triggered_at DESC LIMIT 10;"
```

## Documentation

### Core Documentation
- **Plan**: [`plan.md`](./plan.md) - Complete architecture and implementation plan
- **Guidelines**: [`CLAUDE.md`](./CLAUDE.md) - Development guidelines and principles
- **Issues**: [`issues/`](./issues/) - Implementation issues tracker
- **UAT Guide**: [`docs/UAT_GUIDE.md`](./docs/UAT_GUIDE.md) - User acceptance testing procedures

### Implementation Issues
All issues for Phase 1 have been COMPLETED (implemented 09/12/25):

| Issue | Priority | Component | Status |
|-------|----------|-----------|--------|
| [091325-1](./issues/091325-1-project-setup.md) | High | Project Setup | ✅ Completed |
| [091325-2](./issues/091325-2-database-schema.md) | High | Database Schema | ✅ Completed |
| [091325-3](./issues/091325-3-scraper-module.md) | High | Web Scraper | ✅ Completed |
| [091325-4](./issues/091325-4-configuration-management.md) | High | Configuration | ✅ Completed |
| [091325-5](./issues/091325-5-alert-engine.md) | High | Alert Engine | ✅ Completed |
| [091325-6](./issues/091325-6-notification-module.md) | Medium | Notifications | ✅ Completed |
| [091325-7](./issues/091325-7-integration-uat.md) | High | Integration | ✅ Completed |

## Implementation Status

### Phase 1: Foundations & Initial Scraper - ✅ COMPLETED
- ✅ Architecture defined
- ✅ Data model designed  
- ✅ SQL schema implemented
- ✅ All 7 components built:
  - ✅ Project structure and dependencies installed
  - ✅ SQLite database with all tables created
  - ✅ Web scraper module with base and track scrapers
  - ✅ Configuration management system
  - ✅ Alert engine with evaluators
  - ✅ Email notification system
  - ✅ Main application with scheduler
- ✅ Basic tests implemented
- ✅ System runs end-to-end

### Phase 2: Testing & Refinement - [Current]
- User acceptance testing
- Real track integration
- Performance optimization
- Bug fixes based on testing

### Phase 3: Dashboard & Production - [Planned]
- Optional dashboard development
- Production deployment setup
- Monitoring and logging enhancement
- Documentation finalization

## Project Structure
```
horses/
├── src/                    # Source code
│   ├── scraper/           # Web scraping modules
│   ├── database/          # Database models and connection
│   ├── alerts/            # Alert engine and evaluators
│   ├── notifications/     # Email and other notifications
│   └── utils/             # Configuration and utilities
├── tests/                  # Test suite
├── config/                 # Configuration files
├── data/                   # SQLite database
├── logs/                   # Application logs
├── issues/                 # Implementation issues
├── docs/                   # Additional documentation
└── scripts/                # Utility scripts
```

## Contributing
This is a solo developer project. Issues and documentation follow standardized templates for consistency and clarity.

## License
Private project - not for distribution

---
**Last Updated**: 2025-09-13