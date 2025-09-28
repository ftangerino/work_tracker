from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta, date
from .io.storage import StorageJSON
from .core.tracker import TimeTracker
from .io.report import ReportService

def today_utc() -> date:
    return datetime.now(tz=timezone.utc).date()

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
            print(f"⏱ sessão ativa desde {st.started_at.isoformat()}  "
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

if __name__ == "__main__":
    main()
