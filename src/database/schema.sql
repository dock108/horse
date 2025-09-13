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