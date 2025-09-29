from datetime import datetime, timezone
from typing import Optional, Dict

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"

def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

def dt_to_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(ISO)

def str_to_dt(s: str) -> datetime:
    return datetime.strptime(s, ISO).replace(tzinfo=timezone.utc)

class WorkSession:
    def __init__(self, id: str, started_at: datetime, ended_at: Optional[datetime] = None):
        self.id = id
        self.started_at = started_at
        self.ended_at = ended_at

    def end(self) -> None:
        if not self.ended_at:
            self.ended_at = now_utc()

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    @property
    def duration_seconds(self) -> int:
        end = self.ended_at or now_utc()
        return int((end - self.started_at).total_seconds())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "started_at": dt_to_str(self.started_at),
            "ended_at": dt_to_str(self.ended_at) if self.ended_at else None,
        }

    @staticmethod
    def from_dict(d: Dict) -> "WorkSession":
        return WorkSession(
            id=d["id"],
            started_at=str_to_dt(d["started_at"]),
            ended_at=str_to_dt(d["ended_at"]) if d.get("ended_at") else None,
        )