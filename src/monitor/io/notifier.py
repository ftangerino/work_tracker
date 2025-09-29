###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations
from abc import ABC, abstractmethod

###################################################################################################
# 🔔 NOTIFIER (saída/efeito colateral)
###################################################################################################

class Notifier(ABC):
    """Contrato para mecanismos de notificação (console, desktop, etc.)."""
    @abstractmethod
    def notify(self, message: str) -> None:
        """Entrega a mensagem ao usuário (implementação específica)."""
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """Notificador simples que escreve no stdout."""
    def notify(self, message: str) -> None:
        print(message)
