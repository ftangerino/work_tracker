# src/monitor/core/policy.py
from abc import ABC, abstractmethod
from typing import Optional

class Policy(ABC):
    @abstractmethod
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        """Retorna em quantos segundos sugerir ação; None = sem sugestão."""

class HydrationPolicy(Policy):
    def __init__(self, interval_seconds: int = 3600):
        self.interval = interval_seconds
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        return self.interval - (active_seconds % self.interval)

class BreakPolicy(Policy):
    def __init__(self, interval_seconds: int = 3000):
        self.interval = interval_seconds
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        return self.interval - (active_seconds % self.interval)


class MealPolicy(Policy):
    """Stub: futura regra para janela de refeição; por enquanto, não recomenda."""
    def next_hint_seconds(self, active_seconds: int) -> Optional[int]:
        return None
