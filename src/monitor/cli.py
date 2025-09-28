from __future__ import annotations
import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta, date

from .io.storage import StorageJSON
from .core.tracker import TimeTracker
from .io.report import ReportService

def today_utc() -> date:
    return datetime.now(tz=timezone.utc).date()

# ---------------- WATCH SIMPLES (sem scroll) ----------------
def watch_simple(tracker: TimeTracker, interval: float = 1.0) -> None:
    """Atualiza a tela inteira, sem ficar spammando linhas."""
    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            st = tracker.status()
            if st.active:
                elapsed = tracker.humanize_seconds(st.elapsed_seconds)
                print("🟢 sessão ativa")
                print(f"Início:    {st.started_at.isoformat()}")
                print(f"Decorrido: {elapsed}")
                print("\nCtrl+C para sair")
            else:
                print("🔴 nenhuma sessão ativa")
                print("use: monitor start")
                print("\nCtrl+C para sair")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n👋 saindo do modo watch...")

# ---------------- WATCH FULLSCREEN (curses) ----------------
def watch_fullscreen(tracker: TimeTracker, interval: float = 1.0) -> None:
    """Tela fixa com curses (Windows: pip install windows-curses)."""
    try:
        import curses
    except ImportError:
        print("⚠ 'curses' não disponível. No Windows rode: pip install windows-curses")
        return watch_simple(tracker, interval)

    def run(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            title = " Monitor de Horas – WATCH (Ctrl+C para sair) "
            stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.A_REVERSE)

            st = tracker.status()
            if st.active:
                elapsed = tracker.humanize_seconds(st.elapsed_seconds)
                lines = [
                    f"Status:     🟢 SESSÃO ATIVA",
                    f"Início:     {st.started_at.isoformat()}",
                    f"Decorrido:  {elapsed}",
                ]
            else:
                lines = [
                    f"Status:     🔴 SEM SESSÃO ATIVA",
                    "use: monitor start",
                ]

            for i, ln in enumerate(lines, start=2):
                if i < h:
                    stdscr.addstr(i, 2, ln)

            stdscr.refresh()
            time.sleep(interval)

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        print("\n👋 saindo do modo fullscreen...")

# ---------------- CLI PRINCIPAL ----------------
def main():
    parser = argparse.ArgumentParser(prog="monitor", description="Monitor de horas (CLI)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="inicia sessão de trabalho")
    sub.add_parser("stop", help="encerra sessão ativa")
    sub.add_parser("status", help="mostra status atual")

    p_report = sub.add_parser("report", help="relatórios")
    p_report.add_argument("--today", action="store_true", help="relatório do dia")
    p_report.add_argument("--week", action="store_true", help="relatório da semana (últimos 7 dias)")

    p_export = sub.add_parser("export", help="exporta CSV")
    p_export.add_argument("path", help="caminho do arquivo CSV a gerar")
    p_export.add_argument("--days", type=int, default=7, help="quantidade de dias (padrão: 7)")

    p_watch = sub.add_parser("watch", help="painel ao vivo sem logs infinitos")
    p_watch.add_argument("--interval", type=float, default=1.0, help="intervalo de atualização em segundos")
    p_watch.add_argument("--fullscreen", action="store_true", help="usa curses para tela fixa")

    args = parser.parse_args()

    storage = StorageJSON()
    tracker = TimeTracker(storage)
    reports = ReportService(tracker)

    if args.cmd == "start":
        sid = tracker.start()
        print(f"✔ sessão iniciada: {sid}")
    elif args.cmd == "stop":
        sid = tracker.stop()
        if sid:
            print(f"✔ sessão encerrada: {sid}")
        else:
            print("⚠ nenhuma sessão ativa para encerrar")
    elif args.cmd == "status":
        st = tracker.status()
        if st.active:
            print(f"🟢 sessão ativa desde {st.started_at.isoformat()} "
                  f"(decorridos: {tracker.humanize_seconds(st.elapsed_seconds)})")
        else:
            print("🛑 nenhuma sessão ativa")
    elif args.cmd == "report":
        if args.today:
            dsum = reports.daily_summary(today_utc())
            print(f"📅 {dsum['date']} | sessões: {dsum['sessions']} | total: {dsum['total_hms']}")
        elif args.week:
            wsum = reports.week_summary(today_utc())
            print(f"🗓 semana {wsum['start']} → {wsum['end']} | total: {wsum['total_hms']}")
        else:
            print("use --today ou --week")
    elif args.cmd == "export":
        end = today_utc()
        days = [end - timedelta(days=i) for i in range(args.days)][::-1]
        reports.export_csv(args.path, days)
        print(f"📤 CSV exportado em: {args.path}")
    elif args.cmd == "watch":
        if args.fullscreen:
            watch_fullscreen(tracker, args.interval)
        else:
            watch_simple(tracker, args.interval)

if __name__ == "__main__":
    main()
