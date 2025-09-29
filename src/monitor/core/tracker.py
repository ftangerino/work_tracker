###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional
import uuid

from .session import WorkSession, now_utc
from ..io.storage import StorageJSON

###################################################################################################
# 🧭 STATUS DTO
###################################################################################################

class Status:
    """Snapshot de status atual do rastreador."""
    def __init__(self, active: bool, started_at: Optional[datetime], elapsed_seconds: int) -> None:
        self.active: bool = active
        self.started_at: Optional[datetime] = started_at
        self.elapsed_seconds: int = int(elapsed_seconds)

###################################################################################################
# ⏱️ TIME TRACKER (Regra de negócio + persistência)
###################################################################################################

class TimeTracker:
    """
    Gerencia sessões de trabalho com persistência em JSON (via StorageJSON).
    Responsabilidades:
      - iniciar/encerrar sessão
      - consultar status atual
      - listar sessões por dia
      - somar duração em intervalo
    """
    def __init__(self, storage: StorageJSON) -> None:
        self.storage: StorageJSON = storage

    # ----------------- comandos -----------------

    def start(self) -> str:
        """
        Inicia nova sessão. Se existir sessão ativa no estado, finaliza-a antes
        para evitar sobreposição.
        """
        state = self.storage.load()
        sessions = state.get("sessions", [])

        # Finaliza sessão ativa pendente, se houver.
        for session_dict in sessions:
            if session_dict.get("ended_at") is None:
                active_session = WorkSession.from_dict(session_dict)
                active_session.end()
                session_dict.update(active_session.to_dict())

        new_session = WorkSession(id=str(uuid.uuid4()), started_at=now_utc())
        sessions.append(new_session.to_dict())
        state["sessions"] = sessions
        self.storage.save(state)
        return new_session.id

    def stop(self) -> Optional[str]:
        """
        Encerra a sessão ativa mais recente, se existir.
        Retorna o id da sessão encerrada ou None.
        """
        state = self.storage.load()
        sessions = state.get("sessions", [])

        for session_dict in reversed(sessions):
            if session_dict.get("ended_at") is None:
                active_session = WorkSession.from_dict(session_dict)
                active_session.end()
                session_dict.update(active_session.to_dict())
                self.storage.save(state)
                return active_session.id
        return None

    # ----------------- consultas -----------------

    def status(self) -> Status:
        """
        Retorna o status atual:
          - active=True com início e segundos decorridos se há sessão ativa;
          - active=False caso contrário.
        """
        state = self.storage.load()
        sessions = state.get("sessions", [])

        for session_dict in reversed(sessions):
            if session_dict.get("ended_at") is None:
                active_session = WorkSession.from_dict(session_dict)
                return Status(True, active_session.started_at, active_session.duration_seconds)
        return Status(False, None, 0)

    def sessions_on(self, day: date) -> List[WorkSession]:
        """Lista as sessões cujo 'started_at' cai na data (UTC) informada."""
        state = self.storage.load()
        sessions = state.get("sessions", [])
        result: List[WorkSession] = []

        for session_dict in sessions:
            session = WorkSession.from_dict(session_dict)
            if session.started_at.date() == day:
                result.append(session)

        return result

    def totals_between(self, start_day: date, end_day: date) -> int:
        """
        Soma total de segundos trabalhados no intervalo [start_day, end_day] (UTC).
        """
        total_seconds = 0
        state = self.storage.load()
        sessions = state.get("sessions", [])

        for session_dict in sessions:
            session = WorkSession.from_dict(session_dict)
            started_date = session.started_at.date()
            if start_day <= started_date <= end_day:
                total_seconds += session.duration_seconds

        return int(total_seconds)

    # ----------------- util -----------------

    @staticmethod
    def humanize_seconds(seconds: int) -> str:
        """Formata segundos como HH:MM:SS (sempre zero-padded)."""
        total = int(seconds)  # garantir inteiro para formatação
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
