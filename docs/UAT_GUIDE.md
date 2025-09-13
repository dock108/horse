# User Acceptance Testing (UAT) Guide

## System Overview
The Horse Racing Odds Tracking System monitors live betting odds from configured racetracks, stores historical data, and sends alerts when specified conditions are met.

## Pre-Testing Setup

### 1. Environment Setup
```bash
# Navigate to project directory
cd horses

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
1. Copy `config/config.yaml.example` to `config/config.yaml`
2. Update settings as needed (default test configuration works out of the box)
3. For email alerts, update email settings and create `.env` file

### 3. Environment Variables (Optional - for email)
Create `.env` file with:
```
EMAIL_SENDER=your-email@gmail.com
EMAIL_RECIPIENT=alerts@example.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## Quick Start Test

### Run with Test Data (Recommended for first test)
```bash
python main.py --once --test
```

This will:
- Initialize the system
- Create database tables
- Run one scraping cycle with test data
- Generate sample alerts
- Display results in console

## Test Scenarios

### Scenario 1: Basic System Start
**Objective**: Verify system starts without errors

**Steps**:
1. Run: `python main.py --log-level DEBUG --once`
2. Verify system initializes without errors
3. Check that test track is configured
4. Confirm database is created at `data/horses.db`

**Expected Results**:
- System starts successfully
- No error messages in console
- Log files created in `logs/` directory
- Database file exists in `data/` directory

### Scenario 2: Single Scraping Cycle
**Objective**: Test one-time scraping

**Steps**:
1. Run: `python main.py --once`
2. Monitor console output
3. Check database for new data

**Expected Results**:
- Scraping completes for configured tracks
- Data stored in database
- Console shows scraping progress
- No errors reported

### Scenario 3: Alert Triggering
**Objective**: Verify alerts work

**Steps**:
1. Edit `config/config.yaml` to set low thresholds:
   - win_odds_min: 0.5
   - win_odds_max: 15.0
2. Run: `python main.py --once --test`
3. Check for alert messages in console

**Expected Results**:
- Alerts triggered for test data
- Alert messages displayed in console
- Alerts saved to database

### Scenario 4: Continuous Operation
**Objective**: Test extended running

**Steps**:
1. Start system: `python main.py`
2. Let run for 5 minutes
3. Press Ctrl+C to stop
4. Monitor logs

**Expected Results**:
- System remains stable
- Regular scraping occurs every 5 minutes
- Graceful shutdown on Ctrl+C

### Scenario 5: Database Verification
**Objective**: Verify data persistence

**Steps**:
1. Run system once: `python main.py --once --test`
2. Check database:
```bash
sqlite3 data/horses.db
.tables
SELECT COUNT(*) FROM odds_snapshot;
SELECT * FROM alert LIMIT 5;
.quit
```

**Expected Results**:
- Tables created correctly
- Data present in tables
- Alerts stored with details

## Validation Checklist

### Functional Requirements
- [x] System starts successfully
- [x] Scrapes test track data
- [x] Stores odds in database
- [x] Detects threshold violations
- [x] Logs alerts to console
- [x] Handles errors gracefully
- [ ] Sends email alerts (optional, requires configuration)

### Data Validation
- [x] Win odds parsed correctly
- [x] Exacta probables captured
- [x] Timestamps accurate
- [x] No duplicate races created
- [x] Historical data retained

### Performance
- [x] Scraping completes quickly (test data instant)
- [x] Database queries fast
- [x] Alert evaluation immediate
- [x] Low memory usage

## Troubleshooting

### Common Issues

1. **Module Import Errors**
   - Ensure you're in virtual environment: `source venv/bin/activate`
   - Reinstall dependencies: `pip install -r requirements.txt`

2. **Database Errors**
   - Check write permissions on `data/` directory
   - Delete `data/horses.db` to start fresh

3. **No Alerts Triggering**
   - Review threshold settings in config.yaml
   - Use `--test` flag for guaranteed test data
   - Check logs in `logs/` directory

4. **Configuration Not Found**
   - Copy example: `cp config/config.yaml.example config/config.yaml`
   - System will use defaults if config missing

## Command Line Options

```bash
python main.py [options]

Options:
  --once          Run once and exit
  --test          Use test data generator
  --log-level     Set logging level (DEBUG, INFO, WARNING, ERROR)
  --config        Path to config file (default: config/config.yaml)
  --help          Show help message
```

## Success Criteria

The system is ready for production use when:
1. ✅ All test scenarios pass
2. ✅ No errors in logs
3. ✅ Data correctly stored in database
4. ✅ Alerts trigger as expected
5. ✅ System runs stably for extended periods

## Next Steps

After successful UAT:
1. Configure real track scrapers (currently using test data generator)
2. Set up email notifications if desired
3. Adjust alert thresholds for your needs
4. Schedule system to run automatically (cron/launchd)

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review configuration in `config/config.yaml`
- Ensure all dependencies installed
- Test with `--test` flag first