###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict

###################################################################################################
# 🗓️ DATETIME HELPERS (UTC + ISO-8601)
###################################################################################################

ISO_UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

def now_utc() -> datetime:
    """Retorna o instante atual em UTC (timezone-aware)."""
    return datetime.now(tz=timezone.utc)

def dt_to_str(dt: datetime) -> str:
    """Converte datetime para string ISO-8601 UTC (com 'Z')."""
    return dt.astimezone(timezone.utc).strftime(ISO_UTC_FORMAT)

def str_to_dt(value: str) -> datetime:
    """Converte string ISO-8601 UTC (com 'Z') para datetime (timezone-aware)."""
    # Observação: assume que a string segue exatamente ISO_UTC_FORMAT.
    return datetime.strptime(value, ISO_UTC_FORMAT).replace(tzinfo=timezone.utc)

###################################################################################################
# 🧱 DOMAIN MODEL: WorkSession
###################################################################################################

class WorkSession:
    """
    Representa uma sessão de trabalho.
    - started_at / ended_at sempre em UTC
    - duration_seconds considera 'agora' quando a sessão está ativa
    """
    def __init__(self, id: str, started_at: datetime, ended_at: Optional[datetime] = None) -> None:
        self.id: str = id
        self.started_at: datetime = started_at
        self.ended_at: Optional[datetime] = ended_at

    def end(self) -> None:
        """Finaliza a sessão, caso ainda esteja ativa."""
        if self.ended_at is None:
            self.ended_at = now_utc()

    @property
    def is_active(self) -> bool:
        """True se a sessão ainda não foi finalizada."""
        return self.ended_at is None

    @property
    def duration_seconds(self) -> int:
        """Duração em segundos (até 'agora' se ativa)."""
        end_instant = self.ended_at or now_utc()
        return int((end_instant - self.started_at).total_seconds())

    # ----------------- (de)serialização -----------------

    def to_dict(self) -> Dict:
        """Representação serializável (JSON-friendly)."""
        return {
            "id": self.id,
            "started_at": dt_to_str(self.started_at),
            "ended_at": dt_to_str(self.ended_at) if self.ended_at else None,
        }

    @staticmethod
    def from_dict(data: Dict) -> "WorkSession":
        """Restaura WorkSession a partir de um dict armazenado."""
        return WorkSession(
            id=data["id"],
            started_at=str_to_dt(data["started_at"]),
            ended_at=str_to_dt(data["ended_at"]) if data.get("ended_at") else None,
        )
