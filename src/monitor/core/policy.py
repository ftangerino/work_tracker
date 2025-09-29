###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

###################################################################################################
# 🧠 REMINDER POLICIES (Strategy)
# Cada policy calcula em quantos segundos ocorrerá o próximo lembrete
# com base no tempo total de atividade decorrido.
###################################################################################################

class Policy(ABC):
    """Contrato para políticas de lembretes (Strategy)."""
    @abstractmethod
    def next_hint_seconds(self, elapsed_total_seconds: int) -> Optional[int]:
        """
        Retorna quantos segundos faltam para o próximo lembrete.
        None = sem sugestão.
        """
        raise NotImplementedError


class _IntervalPolicyBase(Policy):
    """Base para policies periódicas (hidratação, pausa, ficar de pé)."""
    def __init__(self, interval_seconds: int) -> None:
        # Garante intervalo mínimo de 1s para evitar divisão por zero.
        self.interval_seconds: int = max(1, int(interval_seconds))

    def next_hint_seconds(self, elapsed_total_seconds: int) -> int:
        elapsed: int = int(elapsed_total_seconds)
        # Distância até o próximo múltiplo do intervalo.
        return self.interval_seconds - (elapsed % self.interval_seconds)


class HydrationPolicy(_IntervalPolicyBase):
    """Lembrete periódico para beber água."""
    def __init__(self, interval_seconds: int = 3600) -> None:
        super().__init__(interval_seconds)


class BreakPolicy(_IntervalPolicyBase):
    """Lembrete periódico de pausa curta (ex.: técnica Pomodoro)."""
    def __init__(self, interval_seconds: int = 3000) -> None:
        super().__init__(interval_seconds)


class StandPolicy(_IntervalPolicyBase):
    """Lembrete periódico para levantar e esticar as pernas."""
    def __init__(self, interval_seconds: int = 2700) -> None:
        # 45 min por padrão
        super().__init__(interval_seconds)
