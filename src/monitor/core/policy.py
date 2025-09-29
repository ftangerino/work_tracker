# src/monitor/core/policy.py
from abc import ABC, abstractmethod
from typing import Optional

class Policy(ABC):
    @abstractmethod
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        """Retorna em quantos segundos sugerir ação; None = sem sugestão."""

class HydrationPolicy(Policy):
    def __init__(self, interval_seconds: int = 3600):
        self.interval = max(1, int(interval_seconds))
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        a = int(active_seconds)
        return self.interval - (a % self.interval)

class BreakPolicy(Policy):
    def __init__(self, interval_seconds: int = 3000):
        self.interval = max(1, int(interval_seconds))
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        a = int(active_seconds)
        return self.interval - (a % self.interval)

class StandPolicy(Policy):
    """Lembrete para ficar de pé/esticar as pernas em intervalos regulares."""
    def __init__(self, interval_seconds: int = 2700):  # 45 min por padrão
        self.interval = max(1, int(interval_seconds))
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        a = int(active_seconds)
        return self.interval - (a % self.interval)
