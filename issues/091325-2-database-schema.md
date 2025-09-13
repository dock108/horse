# Issue 091325-2: Database Schema and Models Implementation

**Priority**: High  
**Component**: Database - Schema & Models  
**Beta Blocker**: Yes (Core data persistence required for all features)  
**Discovered**: 2025-09-13  
**Status**: Awaiting User Testing  
**Resolved**: [Pending]

## Problem Description

The system requires a SQLite database schema to persist tracks, races, entries, odds snapshots, and alerts. The schema must support efficient queries for latest odds, historical analysis, and alert tracking while maintaining referential integrity and avoiding duplicate data.

## Investigation Areas

1. SQLite schema design for optimal performance
2. Index strategy for frequent queries (latest odds, race lookups)
3. Handling of Exacta data (JSON blob vs separate table)
4. Migration strategy for schema changes
5. Database connection pooling approach
6. Transaction management for concurrent operations
7. Data retention policies and cleanup

## Expected Behavior

A fully functional database layer with:
- Tables for Track, Race, Entry, Horse, OddsSnapshot, and Alert
- Proper foreign key relationships and constraints
- Indices optimized for common queries
- Python models using dataclasses or SQLAlchemy
- Database initialization and migration scripts
- Helper functions for common operations
- Efficient queries for latest odds and historical data

## Files to Investigate

- `src/database/models.py` (data models)
- `src/database/schema.sql` (SQL schema definition)
- `src/database/connection.py` (database connection management)
- `src/database/migrations.py` (schema migration logic)
- `tests/test_database.py` (database tests)

## Root Cause Analysis

Not applicable - this is initial implementation work.

## Solution Implemented

### 1. SQL Schema Definition (❌ Not Started)

**schema.sql**:
```sql
-- Track information
CREATE TABLE IF NOT EXISTS track (
    track_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    code TEXT,
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Race information
CREATE TABLE IF NOT EXISTS race (
    race_id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    race_date DATE NOT NULL,
    race_number INTEGER NOT NULL,
    post_time TIME,
    status TEXT DEFAULT 'scheduled',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (track_id) REFERENCES track(track_id),
    UNIQUE(track_id, race_date, race_number)
);

-- Horse information (normalized)
CREATE TABLE IF NOT EXISTS horse (
    horse_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Race entries
CREATE TABLE IF NOT EXISTS entry (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL,
    horse_id INTEGER NOT NULL,
    program_number TEXT NOT NULL,
    morning_line_odds REAL,
    jockey TEXT,
    trainer TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES race(race_id),
    FOREIGN KEY (horse_id) REFERENCES horse(horse_id),
    UNIQUE(race_id, program_number)
);

-- Odds snapshots
CREATE TABLE IF NOT EXISTS odds_snapshot (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL,
    entry_id INTEGER NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    win_odds REAL,
    win_odds_decimal REAL,
    win_pool_amount INTEGER,
    total_win_pool INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES race(race_id),
    FOREIGN KEY (entry_id) REFERENCES entry(entry_id)
);

-- Exacta probables (separate table for flexibility)
CREATE TABLE IF NOT EXISTS exacta_probable (
    exacta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    race_id INTEGER NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    first_horse TEXT NOT NULL,
    second_horse TEXT NOT NULL,
    payout REAL NOT NULL,
    total_exacta_pool INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES race(race_id)
);

-- Alerts
CREATE TABLE IF NOT EXISTS alert (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    triggered_at TIMESTAMP NOT NULL,
    race_id INTEGER,
    entry_id INTEGER,
    alert_type TEXT NOT NULL,
    threshold_value REAL,
    actual_value REAL,
    message TEXT NOT NULL,
    sent BOOLEAN DEFAULT 0,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (race_id) REFERENCES race(race_id),
    FOREIGN KEY (entry_id) REFERENCES entry(entry_id)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_race_date ON race(race_date);
CREATE INDEX IF NOT EXISTS idx_race_track ON race(track_id, race_date);
CREATE INDEX IF NOT EXISTS idx_odds_race_time ON odds_snapshot(race_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_odds_entry ON odds_snapshot(entry_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_exacta_race_time ON exacta_probable(race_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_race ON alert(race_id, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_sent ON alert(sent, triggered_at DESC);
```

### 2. Python Models (❌ Not Started)

**models.py**:
```python
from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional, List

@dataclass
class Track:
    track_id: Optional[int] = None
    name: str = ""
    code: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Race:
    race_id: Optional[int] = None
    track_id: int = 0
    race_date: date = field(default_factory=date.today)
    race_number: int = 0
    post_time: Optional[time] = None
    status: str = "scheduled"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class Horse:
    horse_id: Optional[int] = None
    name: str = ""
    created_at: Optional[datetime] = None

@dataclass
class Entry:
    entry_id: Optional[int] = None
    race_id: int = 0
    horse_id: int = 0
    program_number: str = ""
    morning_line_odds: Optional[float] = None
    jockey: Optional[str] = None
    trainer: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class OddsSnapshot:
    snapshot_id: Optional[int] = None
    race_id: int = 0
    entry_id: int = 0
    fetched_at: datetime = field(default_factory=datetime.now)
    win_odds: Optional[float] = None
    win_odds_decimal: Optional[float] = None
    win_pool_amount: Optional[int] = None
    total_win_pool: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class ExactaProbable:
    exacta_id: Optional[int] = None
    race_id: int = 0
    fetched_at: datetime = field(default_factory=datetime.now)
    first_horse: str = ""
    second_horse: str = ""
    payout: float = 0.0
    total_exacta_pool: Optional[int] = None
    created_at: Optional[datetime] = None

@dataclass
class Alert:
    alert_id: Optional[int] = None
    triggered_at: datetime = field(default_factory=datetime.now)
    race_id: Optional[int] = None
    entry_id: Optional[int] = None
    alert_type: str = ""
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    message: str = ""
    sent: bool = False
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
```

### 3. Database Connection Manager (❌ Not Started)

**connection.py**:
```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "data/horses.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent / "schema.sql"
        with self.get_connection() as conn:
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    conn.executescript(f.read())
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None  # autocommit mode
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple = ()):
        """Execute an insert and return last row id"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid
    
    def execute_many(self, query: str, params_list: list):
        """Execute multiple inserts efficiently"""
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()
```

## Testing Requirements

### Manual Testing Steps
1. Initialize database: `python -m src.database.connection`
2. Verify schema creation: `sqlite3 data/horses.db ".schema"`
3. Test CRUD operations for each model
4. Verify foreign key constraints
5. Test index performance with sample data
6. Verify transaction rollback on errors

### Test Scenarios
- [ ] Database initializes with correct schema
- [ ] All tables created with proper constraints
- [ ] Foreign key relationships enforced
- [ ] Indices created and functional
- [ ] CRUD operations work for all models
- [ ] Duplicate prevention (unique constraints) works
- [ ] Transaction rollback on errors
- [ ] Connection pooling handles concurrent access
- [ ] Latest odds query performs efficiently

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