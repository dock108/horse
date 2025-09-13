# Implementation Issues Index

## Overview
This document provides a comprehensive index of all implementation issues for the Horse Racing Odds Tracking System. Issues are organized by phase, priority, and dependencies.

**Total Issues Created**: 7  
**Phase 1 UAT Milestone**: All 7 issues  
**Status**: All issues in "New" status, awaiting implementation

## Issue Naming Convention
Format: `MMDDYY-N-brief-description.md`
- MM: Month (09)
- DD: Day (13)
- YY: Year (25)
- N: Sequential number for that day (1-7)

## Phase 1: Foundations & Initial Scraper

### Critical Path (Beta Blockers)
These issues must be completed in order for the system to function:

| Issue | Title | Priority | Dependencies | Description |
|-------|-------|----------|--------------|-------------|
| [091325-1](./091325-1-project-setup.md) | Project Setup and Environment Configuration | High | None | Python environment, project structure, dependencies |
| [091325-2](./091325-2-database-schema.md) | Database Schema and Models Implementation | High | 091325-1 | SQLite schema, models, connection management |
| [091325-3](./091325-3-scraper-module.md) | Web Scraper Module Implementation | High | 091325-1, 091325-2 | Base scraper, parsers, track-specific scrapers |
| [091325-4](./091325-4-configuration-management.md) | Configuration Management System | High | 091325-1 | YAML config, environment variables, validation |
| [091325-7](./091325-7-integration-uat.md) | System Integration and UAT Preparation | High | All others | Main script, scheduler, logging, UAT guide |

### Enhancement Features
These issues add value but system can function without them initially:

| Issue | Title | Priority | Dependencies | Description |
|-------|-------|----------|--------------|-------------|
| [091325-5](./091325-5-alert-engine.md) | Alert Engine Implementation | High | 091325-2, 091325-4 | Threshold evaluation, discrepancy detection, suppression |
| [091325-6](./091325-6-notification-module.md) | Email Notification Module | Medium | 091325-5 | SMTP email sending, templates, retry logic |

## Implementation Order

### Recommended Sequence
1. **091325-1**: Project Setup *(Required first)*
2. **091325-4**: Configuration Management *(Enable config-driven development)*
3. **091325-2**: Database Schema *(Data persistence foundation)*
4. **091325-3**: Web Scraper *(Core data collection)*
5. **091325-5**: Alert Engine *(Value-add feature)*
6. **091325-6**: Notifications *(User communication)*
7. **091325-7**: Integration *(Bring it all together)*

### Parallel Work Opportunities
After completing 091325-1 and 091325-4, these can be worked in parallel:
- Team A: 091325-2 (Database) → 091325-3 (Scraper)
- Team B: 091325-5 (Alerts) → 091325-6 (Notifications)

## Issue Status Tracking

### Status Definitions
- **New**: Issue created, not started
- **In Progress**: Active development
- **Awaiting User Testing**: Implementation complete, needs UAT
- **User Testing Complete**: User has verified functionality
- **RESOLVED**: Issue closed after user confirmation

### Current Status (2025-09-13)
| Issue | Status | Assigned | Started | Completed | Notes |
|-------|--------|----------|---------|-----------|-------|
| 091325-1 | New | - | - | - | Ready to start |
| 091325-2 | New | - | - | - | Ready to start |
| 091325-3 | New | - | - | - | Depends on 091325-2 |
| 091325-4 | New | - | - | - | Ready to start |
| 091325-5 | New | - | - | - | Can start after 091325-2 |
| 091325-6 | New | - | - | - | Can start after 091325-5 |
| 091325-7 | New | - | - | - | Final integration |

## Acceptance Criteria Summary

### System Ready for UAT When:
- [x] All 7 issues created with detailed specifications
- [ ] Python environment configured (091325-1)
- [ ] Database schema implemented (091325-2)
- [ ] Basic scraper working for one track (091325-3)
- [ ] Configuration system operational (091325-4)
- [ ] Alert engine evaluating conditions (091325-5)
- [ ] Email notifications sending (091325-6)
- [ ] System integrated and documented (091325-7)

### Each Issue Must Have:
- [ ] Code compiles without errors
- [ ] All tests pass
- [ ] Feature is functional
- [ ] Ready for user testing
- [ ] Any blockers clearly documented

## Key Technical Decisions

### Architecture Choices
- **Database**: SQLite (serverless, file-based)
- **Scraping**: BeautifulSoup + Requests (Selenium if JS required)
- **Configuration**: YAML with environment variable support
- **Notifications**: SMTP email (Gmail with app passwords)
- **Testing**: pytest with 80% coverage target

### Performance Targets
- Scrape cadence: 30-60s near post, 1-5m off-peak
- Latest odds query: < 100ms (indexed)
- Alert delivery: < 15s after snapshot
- Dashboard refresh: < 2s

## Risk Mitigation

### Identified Risks
1. **HTML Structure Changes**: Scrapers may break
   - Mitigation: Modular scrapers, robust parsing
2. **Rate Limiting**: Sites may block excessive requests
   - Mitigation: Polite delays, retry logic
3. **Email Delivery**: SMTP authentication issues
   - Mitigation: App passwords, TLS, dry-run mode

## Documentation References

### Core Documents
- [Plan](../plan.md): Complete architecture and implementation plan
- [README](../README.md): Project overview and quick start
- [CLAUDE](../CLAUDE.md): Development guidelines
- [UAT Guide](../docs/UAT_GUIDE.md): Testing procedures

### Issue Template
- [Template](./STANDARDIZED_ISSUE_TEMPLATE.md): Standard format for all issues

## Notes

- All issues follow standardized template for consistency
- Beta blockers must be resolved before UAT can begin
- Issues remain "New" until implementation starts
- Only move to "RESOLVED" after user confirms testing complete

---
**Last Updated**: 2025-09-13  
**Created By**: Claude (Assistant)  
**Purpose**: Track and organize implementation work for Phase 1 UAT milestone