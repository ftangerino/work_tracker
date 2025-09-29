###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List
import csv

from ..core.tracker import TimeTracker

###################################################################################################
# 📊 REPORT SERVICE
###################################################################################################

class ReportService:
    """
    Gera resumos (diário/semana) e exporta CSV a partir dos dados do TimeTracker.
    Não conhece detalhes de persistência: apenas consome a API pública do tracker.
    """
    def __init__(self, tracker: TimeTracker) -> None:
        self.tracker: TimeTracker = tracker

    # ----------------- resumos -----------------

    def daily_summary(self, target_day: date) -> Dict:
        """Resumo de um dia (UTC): número de sessões e total trabalhado."""
        sessions = self.tracker.sessions_on(target_day)
        total_seconds = sum(session.duration_seconds for session in sessions)
        return {
            "date": str(target_day),
            "sessions": len(sessions),
            "total_seconds": total_seconds,
            "total_hms": self.tracker.humanize_seconds(total_seconds),
        }

    def week_summary(self, end_day: date) -> Dict:
        """
        Resumo da semana que termina em end_day (7 dias, inclusive).
        Ex.: se end_day=domingo, cobre segunda..domingo (6 dias atrás até hoje).
        """
        start_day = end_day - timedelta(days=6)
        total_seconds = self.tracker.totals_between(start_day, end_day)
        return {
            "start": str(start_day),
            "end": str(end_day),
            "total_seconds": total_seconds,
            "total_hms": self.tracker.humanize_seconds(total_seconds),
        }

    # ----------------- exportação -----------------

    def export_csv(self, file_path: str, days: List[date]) -> None:
        """
        Exporta um CSV com linhas por dia: date, sessions, total_hms, total_seconds.
        A ordem de 'days' define a ordem de saída (ex.: cronológica).
        """
        rows = []
        for current_day in days:
            summary = self.daily_summary(current_day)
            rows.append([
                summary["date"],
                summary["sessions"],
                summary["total_hms"],
                summary["total_seconds"],
            ])

        # newline='' evita linhas em branco extras no Windows.
        with open(file_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "sessions", "total_hms", "total_seconds"])
            writer.writerows(rows)
