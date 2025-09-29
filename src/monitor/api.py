# src/monitor/api.py
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
from io import StringIO
import csv

from .io.storage import StorageJSON
from .core.tracker import TimeTracker
from .io.report import ReportService
from .core.policy import HydrationPolicy, BreakPolicy, StandPolicy  # intervalos em SEGUNDOS

# ---------- intervals (ajuste como quiser; segundos) ----------
HYDRATION_SECONDS = 3600   # 60 min
BREAK_SECONDS     = 3000   # 50 min
STAND_SECONDS     = 2700   # 45 min

def today_utc():
    return datetime.now(tz=timezone.utc).date()

storage = StorageJSON()
tracker = TimeTracker(storage)
reports = ReportService(tracker)

app = FastAPI(title="Work Tracker API", version="0.0.1")

# CORS para permitir dev local do front (ajuste origins depois)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # em prod: restrinja!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _next_hints(elapsed_total_seconds: int):
    """Calcula próximos lembretes (baseados no total para hidratação/de pé; no total aqui)."""
    hyd = HydrationPolicy(HYDRATION_SECONDS)
    brk = BreakPolicy(BREAK_SECONDS)
    std = StandPolicy(STAND_SECONDS)

    def remain(interval: int) -> int:
        if interval <= 0:
            return 0
        return interval - (int(elapsed_total_seconds) % interval)

    return {
        "hydration_in_seconds": remain(hyd.interval),
        "break_in_seconds":     remain(brk.interval),
        "stand_in_seconds":     remain(std.interval),
    }

@app.post("/sessions/start")
def start_session():
    sid = tracker.start()
    return {"ok": True, "session_id": sid}

@app.post("/sessions/stop")
def stop_session():
    sid = tracker.stop()
    if not sid:
        raise HTTPException(status_code=409, detail="Nenhuma sessão ativa para encerrar.")
    return {"ok": True, "session_id": sid}

@app.get("/status")
def get_status():
    st = tracker.status()
    if not st.active:
        return {
            "active": False,
            "started_at": None,
            "elapsed_seconds": 0,
            "elapsed_hms": TimeTracker.humanize_seconds(0),
            "next_hints": _next_hints(0),
        }
    return {
        "active": True,
        "started_at": st.started_at.isoformat(),
        "elapsed_seconds": st.elapsed_seconds,  # total bruto
        "elapsed_hms": TimeTracker.humanize_seconds(st.elapsed_seconds),
        "next_hints": _next_hints(st.elapsed_seconds),
    }

@app.get("/report")
def get_report(scope: str = Query("today", enum=["today", "week"])):
    if scope == "today":
        dsum = reports.daily_summary(today_utc())
        return {
            "scope": "today",
            "date": dsum["date"],
            "sessions": dsum["sessions"],
            "total_seconds": dsum["total_seconds"],
            "total_hms": dsum["total_hms"],
        }
    else:
        wsum = reports.week_summary(today_utc())
        return {
            "scope": "week",
            "start": wsum["start"],
            "end": wsum["end"],
            "total_seconds": wsum["total_seconds"],
            "total_hms": wsum["total_hms"],
        }

@app.get("/export")
def export_csv(days: int = Query(7, ge=1, le=31)):
    # gera CSV em memória e devolve como attachment
    end = today_utc()
    rows = []
    for i in range(days):
        d = end - timedelta(days=(days - 1 - i))
        dsum = reports.daily_summary(d)
        rows.append([dsum["date"], dsum["sessions"], dsum["total_hms"], dsum["total_seconds"]])

    sio = StringIO()
    w = csv.writer(sio)
    w.writerow(["date", "sessions", "total_hms", "total_seconds"])
    w.writerows(rows)
    csv_bytes = sio.getvalue().encode("utf-8")

    headers = {
        "Content-Disposition": f'attachment; filename="report_last_{days}_days.csv"'
    }
    return Response(content=csv_bytes, media_type="text/csv; charset=utf-8", headers=headers)
