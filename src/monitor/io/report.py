from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List
import csv
from ..core.tracker import TimeTracker

class ReportService:
    def __init__(self, tracker: TimeTracker):
        self.tracker = tracker

    def daily_summary(self, day: date) -> Dict:
        sessions = self.tracker.sessions_on(day)
        total = sum(s.duration_seconds for s in sessions)
        return {
            "date": str(day),
            "sessions": len(sessions),
            "total_seconds": total,
            "total_hms": self.tracker.humanize_seconds(total),
        }

    def week_summary(self, end_day: date) -> Dict:
        start = end_day - timedelta(days=6)
        total = self.tracker.totals_between(start, end_day)
        return {
            "start": str(start),
            "end": str(end_day),
            "total_seconds": total,
            "total_hms": self.tracker.humanize_seconds(total),
        }

    def export_csv(self, path: str, days: List[date]) -> None:
        rows = []
        for d in days:
            ds = self.daily_summary(d)
            rows.append([ds["date"], ds["sessions"], ds["total_hms"], ds["total_seconds"]])
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "sessions", "total_hms", "total_seconds"])
            w.writerows(rows)
