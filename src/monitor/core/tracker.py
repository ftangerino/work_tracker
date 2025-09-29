from datetime import datetime, date
from typing import List, Optional
import uuid

from .session import WorkSession, now_utc
from ..io.storage import StorageJSON

class Status:
    def __init__(self, active: bool, started_at: Optional[datetime], elapsed_seconds: int):
        self.active = active
        self.started_at = started_at
        self.elapsed_seconds = elapsed_seconds

class TimeTracker:
    """Rastreador de sessões com persistência em JSON."""
    def __init__(self, storage: StorageJSON):
        self.storage = storage

    def start(self) -> str:
        state = self.storage.load()
        # encerra eventual sessão ativa anterior (evita sobreposição)
        for s in state["sessions"]:
            if s.get("ended_at") is None:
                ws = WorkSession.from_dict(s)
                ws.end()
                s.update(ws.to_dict())

        ws = WorkSession(id=str(uuid.uuid4()), started_at=now_utc())
        state["sessions"].append(ws.to_dict())
        self.storage.save(state)
        return ws.id

    def stop(self) -> Optional[str]:
        state = self.storage.load()
        for s in reversed(state["sessions"]):
            if s.get("ended_at") is None:
                ws = WorkSession.from_dict(s)
                ws.end()
                s.update(ws.to_dict())
                self.storage.save(state)
                return ws.id
        return None

    def status(self) -> Status:
        state = self.storage.load()
        for s in reversed(state["sessions"]):
            if s.get("ended_at") is None:
                ws = WorkSession.from_dict(s)
                return Status(True, ws.started_at, ws.duration_seconds)
        return Status(False, None, 0)

    def sessions_on(self, day: date) -> List[WorkSession]:
        state = self.storage.load()
        out: List[WorkSession] = []
        for s in state["sessions"]:
            ws = WorkSession.from_dict(s)
            if ws.started_at.date() == day:
                out.append(ws)
        return out

    def totals_between(self, start: date, end: date) -> int:
        """Total de segundos trabalhados no intervalo [start, end] (datas UTC)."""
        sec = 0
        state = self.storage.load()
        for s in state["sessions"]:
            ws = WorkSession.from_dict(s)
            d = ws.started_at.date()
            if start <= d <= end:
                sec += ws.duration_seconds
        return sec

    @staticmethod
    def humanize_seconds(sec: int) -> str:
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
