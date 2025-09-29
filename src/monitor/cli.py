# src/monitor/cli.py
from __future__ import annotations
import argparse
import os
import time
from datetime import datetime, timezone, timedelta, date

from .io.storage import StorageJSON
from .core.tracker import TimeTracker
from .io.report import ReportService
from .core.policy import HydrationPolicy, BreakPolicy, StandPolicy  # <- StandPolicy

# ---------- intervalos (SEGUNDOS) ----------
HYDRATION_SECONDS = 5     # aviso visual 💧 (base TOTAL)
BREAK_SECONDS     = 10    # pausa com ENTER (base EFETIVO)
STAND_SECONDS     = 8     # aviso "de pé" (base TOTAL)

def today_utc() -> date:
    return datetime.now(tz=timezone.utc).date()

IS_WINDOWS = (os.name == "nt")

# -------- helpers para pausa interativa --------
def _wait_enter_with_updates(render_fn, interval: float = 0.5) -> int:
    """
    Espera ENTER atualizando a tela via render_fn(). Retorna duração da pausa (s).
    - Windows: não bloqueia (msvcrt), tela atualiza.
    - Outros: fallback input() (tela estática).
    """
    t0 = time.time()
    if IS_WINDOWS:
        try:
            import msvcrt
        except ImportError:
            render_fn()
            input("")
            return int(time.time() - t0)
        while True:
            render_fn()
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch == "\r" or ch == "\n":
                    break
            time.sleep(interval)
        return int(time.time() - t0)
    else:
        render_fn()
        input("")
        return int(time.time() - t0)

def _print_pause_screen(effective_hms: str, total_hms: str) -> None:
    os.system("cls" if os.name == "nt" else "clear")
    print("🔴 PAUSA CURTA")
    print(f"Efetivo (congelado):     {effective_hms}")
    print(f"Total   (correndo):      {total_hms}")
    print("")
    print("Quando terminar a pausa, pressione ENTER para voltar ao trabalho…")

# --------- WATCH SIMPLES (Total x Efetivo, pausa, hidratação, de pé) ----------
def watch_simple(tracker: TimeTracker, interval: float = 1.0) -> None:
    """
    - Mostra 'Total' (bruto) e 'Efetivo' (descontando pausas confirmadas).
    - Hidratação: aviso 💧 por ~60s (base TOTAL).
    - De pé: aviso visual por ~60s (base TOTAL).
    - Pausa: gatilho baseado no EFETIVO (não avança durante pausa).
    """
    paused_accum_seconds = 0               # desconta do EFETIVO
    hydrate_flash_until: float = 0.0
    stand_flash_until: float = 0.0
    last_hydration_cycle: int = -1
    last_stand_cycle: int = -1
    last_break_cycle: int = -1
    in_break_pause = False

    hydration = HydrationPolicy(HYDRATION_SECONDS)
    breakpol  = BreakPolicy(BREAK_SECONDS)
    standpol  = StandPolicy(STAND_SECONDS)

    # placeholders capturados por closure no render da pausa
    effective_hms_before = "00:00:00"

    def render_pause():
        """Renderiza a tela de pausa: TOTAL atualiza, EFETIVO congelado."""
        st_local = tracker.status()
        total_hms_local = TimeTracker.humanize_seconds(st_local.elapsed_seconds)  # TOTAL corre
        _print_pause_screen(effective_hms_before, total_hms_local)

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            st = tracker.status()

            if st.active:
                # tempos
                raw_elapsed = st.elapsed_seconds                          # TOTAL
                effective_elapsed = max(0, raw_elapsed - paused_accum_seconds)  # EFETIVO
                total_hms = TimeTracker.humanize_seconds(raw_elapsed)
                effective_hms = TimeTracker.humanize_seconds(effective_elapsed)

                # ----- ciclos -----
                # HIDRATAÇÃO & DE PÉ: base TOTAL (avisos visuais)
                hyd_cycle = int(raw_elapsed // hydration.interval) if hydration.interval > 0 else 0
                if hyd_cycle > last_hydration_cycle and raw_elapsed > 0:
                    hydrate_flash_until = time.time() + 60
                    last_hydration_cycle = hyd_cycle

                stand_cycle = int(raw_elapsed // standpol.interval) if standpol.interval > 0 else 0
                if stand_cycle > last_stand_cycle and raw_elapsed > 0:
                    stand_flash_until = time.time() + 60
                    last_stand_cycle = stand_cycle

                # PAUSA: base EFETIVO (não avança durante pausa)
                brk_cycle = int(effective_elapsed // breakpol.interval) if breakpol.interval > 0 else 0
                if (not in_break_pause) and (brk_cycle > last_break_cycle) and (effective_elapsed > 0) and breakpol.interval > 0:
                    in_break_pause = True
                    effective_hms_before = effective_hms
                    pause_secs = _wait_enter_with_updates(render_fn=render_pause, interval=interval)
                    paused_accum_seconds += pause_secs
                    st_after = tracker.status()
                    raw_after = st_after.elapsed_seconds
                    effective_after = max(0, raw_after - paused_accum_seconds)
                    last_break_cycle = int(effective_after // breakpol.interval)
                    in_break_pause = False

                # contagens regressivas (Hidratação/De pé: TOTAL; Pausa: EFETIVO)
                hyd_rem = hydration.interval - int(raw_elapsed % hydration.interval) if hydration.interval else 0
                std_rem = standpol.interval   - int(raw_elapsed % standpol.interval) if standpol.interval  else 0
                brk_rem = breakpol.interval   - int(effective_elapsed % breakpol.interval) if breakpol.interval else 0

                hints = []
                if hydration.interval:
                    hints.append(f"hidratação em {TimeTracker.humanize_seconds(hyd_rem)}")
                if standpol.interval:
                    hints.append(f"de pé em {TimeTracker.humanize_seconds(std_rem)}")
                if breakpol.interval:
                    hints.append(f"pausa em {TimeTracker.humanize_seconds(brk_rem)}")
                hints_str = " | ".join(hints) if hints else "—"

                # render normal
                print("🟢 sessão ativa")
                print(f"Início:    {st.started_at.isoformat()}")
                print(f"Total:     {total_hms}")
                print(f"Efetivo:   {effective_hms}  (desconta pausas)")
                print(f"Hidratação: {'💧 agora' if time.time() < hydrate_flash_until else '—'}")
                print(f"De pé:     {'AGORA' if time.time() < stand_flash_until else '—'}")
                print(f"Próximos:  {hints_str}")
                print("\nENTER para finalizar pausas quando solicitado • Ctrl+C para sair")

            else:
                print("🔴 nenhuma sessão ativa")
                print("use: monitor start")
                print("\nCtrl+C para sair")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n🔴 saindo do modo watch...")

# --------- WATCH FULLSCREEN (opcional; sem pausa interativa) ----------
def watch_fullscreen(tracker: TimeTracker, interval: float = 1.0) -> None:
    """Tela fixa com curses (Windows: pip install windows-curses). Pausa interativa só no modo simples."""
    try:
        import curses
    except ImportError:
        print("⚠ 'curses' não disponível. No Windows, rode: pip install windows-curses")
        return watch_simple(tracker, interval)

    def run(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        hydrate_flash_until = 0.0
        stand_flash_until = 0.0
        last_hydration_cycle = -1
        last_stand_cycle = -1

        hydration = HydrationPolicy(HYDRATION_SECONDS)
        standpol  = StandPolicy(STAND_SECONDS)

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            title = " Monitor de Horas – WATCH (Ctrl+C para sair) "
            stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.A_REVERSE)

            st = tracker.status()
            if st.active:
                raw_elapsed = st.elapsed_seconds
                total_hms = TimeTracker.humanize_seconds(raw_elapsed)

                hyd_cycle = int(raw_elapsed // hydration.interval) if hydration.interval > 0 else 0
                if hyd_cycle > last_hydration_cycle and raw_elapsed > 0:
                    hydrate_flash_until = time.time() + 60
                    last_hydration_cycle = hyd_cycle

                stand_cycle = int(raw_elapsed // standpol.interval) if standpol.interval > 0 else 0
                if stand_cycle > last_stand_cycle and raw_elapsed > 0:
                    stand_flash_until = time.time() + 60
                    last_stand_cycle = stand_cycle

                hyd_rem = hydration.interval - int(raw_elapsed % hydration.interval) if hydration.interval else 0
                std_rem = standpol.interval   - int(raw_elapsed % standpol.interval) if standpol.interval  else 0

                lines = [
                    f"Status:     🟢 SESSÃO ATIVA",
                    f"Início:     {st.started_at.isoformat()}",
                    f"Total:      {total_hms}",
                    f"Hidratação: {'💧 agora' if time.time() < hydrate_flash_until else f'em {TimeTracker.humanize_seconds(hyd_rem)}'}",
                    f"De pé:      {'AGORA' if time.time() < stand_flash_until else f'em {TimeTracker.humanize_seconds(std_rem)}'}",
                    "Obs.: pausas com ENTER disponíveis no modo simples (sem curses)",
                ]
            else:
                lines = [
                    f"Status:     🔴 SEM SESSÃO ATIVA",
                    "Comando:    monitor start",
                ]

            for i, ln in enumerate(lines, start=2):
                if i < h:
                    stdscr.addstr(i, 2, ln)

            stdscr.refresh()
            time.sleep(interval)

    try:
        import curses
        curses.wrapper(run)
    except KeyboardInterrupt:
        print("\n🔴 saindo do modo fullscreen...")

# ---------------------- CLI ------------------------------
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

    p_watch = sub.add_parser("watch", help="painel ao vivo (Total x Efetivo, pausa, hidratação, de pé)")
    p_watch.add_argument("--interval", type=float, default=1.0, help="intervalo de atualização em segundos")
    p_watch.add_argument("--fullscreen", action="store_true", help="usa curses (tela fixa)")

    args = parser.parse_args()

    storage = StorageJSON()
    tracker = TimeTracker(storage)
    reports = ReportService(tracker)

    if args.cmd == "start":
        sid = tracker.start()
        print(f"🟢 sessão iniciada: {sid}")
    elif args.cmd == "stop":
        sid = tracker.stop()
        if sid:
            print(f"🟢 sessão encerrada: {sid}")
        else:
            print("🔴 nenhuma sessão ativa para encerrar")
    elif args.cmd == "status":
        st = tracker.status()
        if st.active:
            print(f"🟢 sessão ativa desde {st.started_at.isoformat()} "
                  f"(decorridos: {tracker.humanize_seconds(st.elapsed_seconds)})")
        else:
            print("🔴 nenhuma sessão ativa")
    elif args.cmd == "report":
        if args.today:
            dsum = reports.daily_summary(today_utc())
            print(f"📅 {dsum['date']} | sessões: {dsum['sessions']} | total: {dsum['total_hms']}")
        elif args.week:
            wsum = reports.week_summary(today_utc())
            print(f"📅 semana {wsum['start']} → {wsum['end']} | total: {wsum['total_hms']}")
        else:
            print("use --today ou --week")
    elif args.cmd == "export":
        end = today_utc()
        days = [end - timedelta(days=i) for i in range(args.days)][::-1]
        reports.export_csv(args.path, days)
        print(f"🟢 CSV exportado em: {args.path}")
    elif args.cmd == "watch":
        if args.fullscreen:
            watch_fullscreen(tracker, args.interval)
        else:
            watch_simple(tracker, args.interval)

if __name__ == "__main__":
    main()
