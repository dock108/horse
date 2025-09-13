# Development Guidelines

## Core Principles

### 1. PERSISTENCE AND COMPLETION
- **NEVER GIVE UP** - Continue working until tasks are 100% complete or hit a genuine showstopper
- **REMEMBER THE GOAL** - User asked for "UNTIL COMPLETION or a showstopper"
- When stuck on one approach, try another approach
- Fix ALL test failures, don't settle for "good enough"
- 80% coverage means 80%, not 78%
- **COMPLETION MEANS**: Task is ready for user testing, evaluation, or further direction
  - Code compiles and runs without errors
  - All tests pass
  - Feature is implemented and functional
  - Ready to hand over to user for testing
  - If blocked, clearly explain the blocker for user evaluation
- **IMPORTANT**: Never move issues or documentation to 'done' or 'complete' folders until user explicitly confirms testing is complete
  - Keep issues open with status "Awaiting User Testing"
  - Only close/move when user says "testing complete" or similar confirmation

### 2. User First
- Always prioritize what the user is asking for
- Don't assume or execute plans/issues unless explicitly requested
- Execute tasks to full completion as requested
- Respond conversationally to greetings and questions

### 3. Keep It Simple
- Choose simple solutions over complex ones
- Don't add features that weren't requested
- Write clear, readable code
- But simple doesn't mean incomplete - finish the job

### 4. Ask When Unclear
- Only interrupt for critical blockers
- Add TODO comments for non-blocking questions
- Batch questions to minimize interruptions

### 5. Follow Existing Patterns
- Match the codebase's existing style
- Use the frameworks already in the project
- Don't introduce new dependencies without discussion

### 6. No Defensive Coding
- Don't add try/except blocks "just in case" 
- Don't check for conditions that shouldn't happen in normal operation
- Don't add fallback mechanisms for missing dependencies that are required
- Let failures fail fast and clearly - better than silent degradation
- Only handle errors that you can meaningfully recover from

## Project Context
Horse Racing Odds Tracking & Alert System - A Python-based, single-user macOS tool that scrapes live pari-mutuel horse racing odds (Win and Exacta), stores time-series snapshots in SQLite, evaluates alert conditions (thresholds, discrepancies), and notifies the user via email. An optional dashboard visualizes current odds, history, and alert activity.

### Architecture Overview
A modular system with clear separation of concerns and a config-driven runtime.
- **Scraper Module**: Fetches odds from track sites/APIs; parses HTML/JSON; normalizes Win odds and Exacta probables.
- **Database Module**: Persists tracks, races, entries, and odds snapshots in SQLite; maintains indices for fast latest-odds queries.
- **Alert Engine**: Evaluates thresholds (min/max odds, min/max exacta payouts) and cross-pool discrepancies; de-duplicates alerts and supports rate-of-change checks.
- **Notification Module**: Sends formatted email alerts using SMTP (TLS), credentials from config.
- **Dashboard Module (optional)**: Flask/FastAPI or Streamlit UI for live tables, historical charts, and alerts log.
- **Configuration**: Central `config.yaml` controls tracks, bet types, thresholds, and email settings.
- **Flow**: Config → Scrape → Normalize → Store (SQLite) → Evaluate Alerts → Notify (Email) → Visualize (Dashboard)

### Key Principles
- Config-driven behavior (`config.yaml`) for tracks, bet types, thresholds, email
- Robust, resilient scraping; prefer structured endpoints when available; polite cadence
- Single-responsibility modules with clear interfaces
- Deterministic, idempotent DB writes; avoid duplicate races/entries
- Fail fast with clear logging; only handle recoverable errors
- Local-first, single-user scope; protect dashboard if exposed
- Start simple; optimize and extend where justified (parallelism/async, batching)

### Technical Stack
- **Core Language**: Python 3.11+ (macOS)
- **Framework**: None required; Flask/FastAPI or Streamlit optional for dashboard
- **Database**: SQLite (standard `sqlite3`), indexed on `race_id` and timestamps
- **Testing**: pytest; target ≥ 80% coverage for core modules
- **Config**: YAML via PyYAML; support environment variables for secrets

### Key Features
- Live scraping of Win odds for configured tracks
- Exacta probables ingestion (full matrix or summarized extremes)
- Threshold-based alerts (min/max odds, min/max exacta payouts)
- Cross-pool discrepancy detection (Win vs Exacta favoritism)
- Email notifications with contextual details (track/race/horse/values)
- Dashboard showing live odds, highlights for alerts, and history charts
- Comprehensive logging and alert history persisted in SQLite

## Post-Sprint Cleanup
After completing any sprint or major task:
- **Check for duplication** - Remove duplicate methods/functions
- **Performance review** - Profile slow operations, optimize bottlenecks
- **File cleanup** - Delete temporary files, organize outputs
- **Size check** - Monitor data files, logs, and cache growth
- **Line count review** - If files exceed ~1000 lines, consider breaking them down
- **Documentation sync** - Update README, but DO NOT move issues to done/ until user confirms
- **Test coverage** - Verify all new code has tests
- **Code quality** - Run linters, fix warnings
- **CRITICAL**: Keep issues in active folder with "Awaiting User Testing" status until user explicitly confirms testing is complete

## Remember
- Do what's asked, nothing more
- The user knows their priorities
- Simple working code beats perfect architecture

---
**Version**: 0.1.0  
**Last Updated**: 2025-09-13
