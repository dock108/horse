from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional


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
