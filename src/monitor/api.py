###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from io import StringIO
import csv

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .io.storage import StorageJSON
from .core.tracker import TimeTracker
from .io.report import ReportService
from .core.policy import HydrationPolicy, BreakPolicy, StandPolicy  # lembretes em SEGUNDOS

###################################################################################################
# ⏱️ POLICIES – INTERVALOS PADRÃO (segundos)
# Em produção, ajuste para:
#   hidratação: 3600 (60 min), pausa: 3000 (50 min), de pé: 2700 (45 min)
###################################################################################################
HYDRATION_INTERVAL_SECONDS = 3600
BREAK_INTERVAL_SECONDS     = 3000
STAND_INTERVAL_SECONDS     = 2700

###################################################################################################
# 🗓️ HELPERS
###################################################################################################
def current_utc_date():
    """Retorna a data atual em UTC (sem timezone)."""
    return datetime.now(tz=timezone.utc).date()

def compute_next_hints(elapsed_total_seconds: int) -> dict:
    """
    Calcula em quantos segundos virão os próximos lembretes.
    (Nesta API, todos baseados no tempo TOTAL.)
    """
    hydration = HydrationPolicy(HYDRATION_INTERVAL_SECONDS)
    pause     = BreakPolicy(BREAK_INTERVAL_SECONDS)
    stand     = StandPolicy(STAND_INTERVAL_SECONDS)

    def remaining(interval_seconds: int) -> int:
        if interval_seconds <= 0:
            return 0
        elapsed = int(elapsed_total_seconds)
        return interval_seconds - (elapsed % interval_seconds)

    return {
        "hydration_in_seconds": remaining(hydration.interval_seconds),
        "break_in_seconds":     remaining(pause.interval_seconds),
        "stand_in_seconds":     remaining(stand.interval_seconds),
    }

###################################################################################################
# 💾 SINGLETONS (STATEFUL SERVICES)
###################################################################################################
storage = StorageJSON()
tracker = TimeTracker(storage)
reports = ReportService(tracker)

###################################################################################################
# 🌐 FASTAPI APP
###################################################################################################
app = FastAPI(title="Work Tracker API", version="0.0.1")

# CORS liberado para desenvolvimento local (RESTRINGIR em produção!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

###################################################################################################
# 🔌 ENDPOINTS
###################################################################################################
@app.post("/sessions/start")
def start_session():
    """Inicia uma nova sessão de trabalho."""
    session_id = tracker.start()
    return {"ok": True, "session_id": session_id}

@app.post("/sessions/stop")
def stop_session():
    """Encerra a sessão ativa mais recente (se houver)."""
    session_id = tracker.stop()
    if not session_id:
        raise HTTPException(status_code=409, detail="Nenhuma sessão ativa para encerrar.")
    return {"ok": True, "session_id": session_id}

@app.get("/status")
def get_status():
    """
    Retorna o status atual:
      - active: bool
      - started_at: ISO-8601 ou None
      - elapsed_seconds / elapsed_hms (TOTAL)
      - next_hints: tempos restantes para hidratação/pausa/ficar de pé
    """
    status = tracker.status()
    if not status.active:
        return {
            "active": False,
            "started_at": None,
            "elapsed_seconds": 0,
            "elapsed_hms": TimeTracker.humanize_seconds(0),
            "next_hints": compute_next_hints(0),
        }

    elapsed_total = status.elapsed_seconds
    return {
        "active": True,
        "started_at": status.started_at.isoformat(),
        "elapsed_seconds": elapsed_total,
        "elapsed_hms": TimeTracker.humanize_seconds(elapsed_total),
        "next_hints": compute_next_hints(elapsed_total),
    }

@app.get("/report")
def get_report(scope: str = Query("today", enum=["today", "week"])):
    """
    Retorna um resumo:
      - scope=today  -> { date, sessions, total_seconds, total_hms }
      - scope=week   -> { start, end, total_seconds, total_hms }
    """
    if scope == "today":
        summary = reports.daily_summary(current_utc_date())
        return {
            "scope": "today",
            "date": summary["date"],
            "sessions": summary["sessions"],
            "total_seconds": summary["total_seconds"],
            "total_hms": summary["total_hms"],
        }

    week = reports.week_summary(current_utc_date())
    return {
        "scope": "week",
        "start": week["start"],
        "end": week["end"],
        "total_seconds": week["total_seconds"],
        "total_hms": week["total_hms"],
    }

@app.get("/export")
def export_csv(days: int = Query(7, ge=1, le=31)):
    """
    Exporta CSV com consolidação diária dos últimos N dias.
    Colunas: date, sessions, total_hms, total_seconds.
    """
    end_day = current_utc_date()
    rows = []
    for index in range(days):
        day = end_day - timedelta(days=(days - 1 - index))
        daily = reports.daily_summary(day)
        rows.append([daily["date"], daily["sessions"], daily["total_hms"], daily["total_seconds"]])

    # Gera CSV em memória
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "sessions", "total_hms", "total_seconds"])
    writer.writerows(rows)
    csv_bytes = buffer.getvalue().encode("utf-8")

    headers = {
        "Content-Disposition": f'attachment; filename="report_last_{days}_days.csv"'
    }
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)
