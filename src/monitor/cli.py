###################################################################################################
# 📥 IMPORTS | CODING: UTF-8
###################################################################################################
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone, timedelta, date

from .io.storage import StorageJSON
from .core.tracker import TimeTracker
from .io.report import ReportService
from .core.policy import HydrationPolicy, BreakPolicy, StandPolicy

###################################################################################################
# ⏱️ INTERVALOS (SEGUNDOS)
# Para demo: valores pequenos. Em prod: (ex.: 3600/3000/2700).
###################################################################################################
HYDRATION_INTERVAL_SECONDS = 5     # 💧 aviso (base TOTAL)
BREAK_INTERVAL_SECONDS     = 10    # pausa com ENTER (base EFETIVO)
STAND_INTERVAL_SECONDS     = 8     # "de pé" (base TOTAL)

IS_WINDOWS = (os.name == "nt")

###################################################################################################
# 🗓️ HELPERS
###################################################################################################
def today_utc() -> date:
    """Data atual em UTC (date sem tz)."""
    return datetime.now(tz=timezone.utc).date()

###################################################################################################
# ⌨️ ENTRADA DE PAUSA (com atualização de tela)
###################################################################################################
def _wait_enter_with_updates(render_screen, refresh_interval: float = 0.5) -> int:
    """
    ENTER atualizando a tela via render_screen().
    Retorna a duração da pausa (segundos inteiros).

    - Windows: usa msvcrt (não bloqueia), atualiza a tela durante a pausa.
    - Outros: fallback para input() (tela estática durante a pausa).
    """
    start_ts = time.time()

    if IS_WINDOWS:
        try:
            import msvcrt  # type: ignore
        except ImportError:
            render_screen()
            input("")
            return int(time.time() - start_ts)

        while True:
            render_screen()
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    break
            time.sleep(refresh_interval)
        return int(time.time() - start_ts)

    # Fallback Unix-like: bloqueia enquanto espera ENTER
    render_screen()
    input("")
    return int(time.time() - start_ts)

def _print_pause_screen(effective_hms: str, total_hms: str) -> None:
    """Tela de pausa minimalista (efetivo congelado, total correndo)."""
    os.system("cls" if IS_WINDOWS else "clear")
    print("🔴 PAUSA CURTA")
    print(f"Efetivo (congelado): {effective_hms}")
    print(f"Total   (correndo):  {total_hms}")
    print("\nQuando terminar a pausa, pressione ENTER para voltar ao trabalho…")

###################################################################################################
# 👀 WATCH (painel ao vivo)
###################################################################################################
def watch_simple(tracker: TimeTracker, refresh_interval: float = 1.0) -> None:
    """
    Painel ao vivo sem spam de logs:
      - Mostra Tempo Total (bruto) e Tempo Efetivo (descontando pausas confirmadas).
      - Hidratação e "De pé": alertas visuais ~60s, baseados no tempo TOTAL.
      - Pausa: gatilho baseado no tempo EFETIVO (não avança enquanto pausado).
    """
    # Acumulador de segundos de pausa (desconta do EFETIVO)
    paused_total_seconds = 0

    # Estado de alertas visuais (expiram por tempo)
    hydration_flash_until_ts: float = 0.0
    stand_flash_until_ts: float = 0.0

    # Controle de ciclos para evitar retriggers
    last_hydration_cycle: int = -1
    last_stand_cycle: int = -1
    last_break_cycle: int = -1
    in_break_pause: bool = False

    hydration_policy = HydrationPolicy(HYDRATION_INTERVAL_SECONDS)
    break_policy = BreakPolicy(BREAK_INTERVAL_SECONDS)
    stand_policy = StandPolicy(STAND_INTERVAL_SECONDS)

    # Valor textual do efetivo congelado durante a pausa (para a tela)
    effective_hms_before_pause = "00:00:00"

    def render_pause_screen():
        """Atualiza a tela de pausa com Total correndo e Efetivo congelado."""
        current_status = tracker.status()
        total_hms_now = TimeTracker.humanize_seconds(current_status.elapsed_seconds)
        _print_pause_screen(effective_hms_before_pause, total_hms_now)

    try:
        while True:
            os.system("cls" if IS_WINDOWS else "clear")
            status = tracker.status()

            if status.active:
                # --- tempos
                elapsed_total_seconds = status.elapsed_seconds
                elapsed_effective_seconds = max(0, elapsed_total_seconds - paused_total_seconds)

                total_hms = TimeTracker.humanize_seconds(elapsed_total_seconds)
                effective_hms = TimeTracker.humanize_seconds(elapsed_effective_seconds)

                # --- ciclos (hidratação/“de pé” base TOTAL; pausa base EFETIVO)
                hydration_cycle = (
                    int(elapsed_total_seconds // hydration_policy.interval_seconds)
                    if hydration_policy.interval_seconds > 0 else 0
                )
                if hydration_cycle > last_hydration_cycle and elapsed_total_seconds > 0:
                    hydration_flash_until_ts = time.time() + 60
                    last_hydration_cycle = hydration_cycle

                stand_cycle = (
                    int(elapsed_total_seconds // stand_policy.interval_seconds)
                    if stand_policy.interval_seconds > 0 else 0
                )
                if stand_cycle > last_stand_cycle and elapsed_total_seconds > 0:
                    stand_flash_until_ts = time.time() + 60
                    last_stand_cycle = stand_cycle

                break_cycle = (
                    int(elapsed_effective_seconds // break_policy.interval_seconds)
                    if break_policy.interval_seconds > 0 else 0
                )

                # --- entrada em pausa (somente se não estiver pausado)
                if (not in_break_pause) and (break_cycle > last_break_cycle) \
                   and (elapsed_effective_seconds > 0) and break_policy.interval_seconds > 0:
                    in_break_pause = True
                    effective_hms_before_pause = effective_hms

                    pause_duration_seconds = _wait_enter_with_updates(
                        render_screen=render_pause_screen,
                        refresh_interval=refresh_interval,
                    )
                    paused_total_seconds += pause_duration_seconds

                    # Atualiza ciclo de pausa com base no EFETIVO pós-pausa
                    status_after = tracker.status()
                    effective_after = max(0, status_after.elapsed_seconds - paused_total_seconds)
                    last_break_cycle = int(effective_after // break_policy.interval_seconds)
                    in_break_pause = False

                # --- contagens regressivas
                hydration_remaining = (
                    hydration_policy.interval_seconds
                    - int(elapsed_total_seconds % hydration_policy.interval_seconds)
                    if hydration_policy.interval_seconds else 0
                )
                stand_remaining = (
                    stand_policy.interval_seconds
                    - int(elapsed_total_seconds % stand_policy.interval_seconds)
                    if stand_policy.interval_seconds else 0
                )
                break_remaining = (
                    break_policy.interval_seconds
                    - int(elapsed_effective_seconds % break_policy.interval_seconds)
                    if break_policy.interval_seconds else 0
                )

                next_hints = []
                if hydration_policy.interval_seconds:
                    next_hints.append(f"hidratação em {TimeTracker.humanize_seconds(hydration_remaining)}")
                if stand_policy.interval_seconds:
                    next_hints.append(f"de pé em {TimeTracker.humanize_seconds(stand_remaining)}")
                if break_policy.interval_seconds:
                    next_hints.append(f"pausa em {TimeTracker.humanize_seconds(break_remaining)}")
                next_hints_str = " | ".join(next_hints) if next_hints else "—"

                # --- render principal
                print("🟢 sessão ativa")
                print(f"Início:    {status.started_at.isoformat()}")
                print(f"Total:     {total_hms}")
                print(f"Efetivo:   {effective_hms}  (desconta pausas)")
                print(f"Hidratação: {'💧 agora' if time.time() < hydration_flash_until_ts else '—'}")
                print(f"De pé:     {'AGORA' if time.time() < stand_flash_until_ts else '—'}")
                print(f"Próximos:  {next_hints_str}")
                print("\nENTER para finalizar pausas quando solicitado • Ctrl+C para sair")

            else:
                print("🔴 nenhuma sessão ativa")
                print("use: monitor start")
                print("\nCtrl+C para sair")

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n🔴 saindo do modo watch...")

###################################################################################################
# 🖥️ WATCH FULLSCREEN (curses) — sem pausa interativa
###################################################################################################
def watch_fullscreen(tracker: TimeTracker, refresh_interval: float = 1.0) -> None:
    """
    Tela fixa com curses (Windows: `pip install windows-curses`).
    A pausa interativa (ENTER) está disponível apenas no modo simples.
    """
    try:
        import curses  # type: ignore
    except ImportError:
        print("⚠ 'curses' não disponível. No Windows, rode: pip install windows-curses")
        return watch_simple(tracker, refresh_interval)

    def _run(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)

        hydration_flash_until_ts = 0.0
        stand_flash_until_ts = 0.0
        last_hydration_cycle = -1
        last_stand_cycle = -1

        hydration_policy = HydrationPolicy(HYDRATION_INTERVAL_SECONDS)
        stand_policy = StandPolicy(STAND_INTERVAL_SECONDS)

        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            title = " Monitor de Horas – WATCH (Ctrl+C para sair) "
            stdscr.addstr(0, max(0, (width - len(title)) // 2), title, curses.A_REVERSE)

            status = tracker.status()
            if status.active:
                elapsed_total_seconds = status.elapsed_seconds
                total_hms = TimeTracker.humanize_seconds(elapsed_total_seconds)

                hydration_cycle = int(elapsed_total_seconds // hydration_policy.interval_seconds)
                if hydration_cycle > last_hydration_cycle and elapsed_total_seconds > 0:
                    hydration_flash_until_ts = time.time() + 60
                    last_hydration_cycle = hydration_cycle

                stand_cycle = int(elapsed_total_seconds // stand_policy.interval_seconds)
                if stand_cycle > last_stand_cycle and elapsed_total_seconds > 0:
                    stand_flash_until_ts = time.time() + 60
                    last_stand_cycle = stand_cycle

                hydration_remaining = hydration_policy.interval_seconds - int(
                    elapsed_total_seconds % hydration_policy.interval_seconds
                )
                stand_remaining = stand_policy.interval_seconds - int(
                    elapsed_total_seconds % stand_policy.interval_seconds
                )

                lines = [
                    "Status:     🟢 SESSÃO ATIVA",
                    f"Início:     {status.started_at.isoformat()}",
                    f"Total:      {total_hms}",
                    f"Hidratação: {'💧 agora' if time.time() < hydration_flash_until_ts else f'em {TimeTracker.humanize_seconds(hydration_remaining)}'}",
                    f"De pé:      {'AGORA' if time.time() < stand_flash_until_ts else f'em {TimeTracker.humanize_seconds(stand_remaining)}'}",
                    "Obs.: pausas com ENTER disponíveis no modo simples (sem curses)",
                ]
            else:
                lines = [
                    "Status:     🔴 SEM SESSÃO ATIVA",
                    "Comando:    monitor start",
                ]

            for i, line in enumerate(lines, start=2):
                if i < height:
                    stdscr.addstr(i, 2, line)

            stdscr.refresh()
            time.sleep(refresh_interval)

    try:
        import curses  # type: ignore
        curses.wrapper(_run)
    except KeyboardInterrupt:
        print("\n🔴 saindo do modo fullscreen...")

###################################################################################################
# 🧰 CLI
###################################################################################################
def main():
    parser = argparse.ArgumentParser(prog="monitor", description="Monitor de horas (CLI)")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    subparsers.add_parser("start", help="inicia sessão de trabalho")
    subparsers.add_parser("stop", help="encerra sessão ativa")
    subparsers.add_parser("status", help="mostra status atual")

    report_parser = subparsers.add_parser("report", help="relatórios")
    report_parser.add_argument("--today", action="store_true", help="relatório do dia")
    report_parser.add_argument("--week", action="store_true", help="relatório da semana (últimos 7 dias)")

    export_parser = subparsers.add_parser("export", help="exporta CSV")
    export_parser.add_argument("path", help="caminho do arquivo CSV a gerar")
    export_parser.add_argument("--days", type=int, default=7, help="quantidade de dias (padrão: 7)")

    watch_parser = subparsers.add_parser("watch", help="painel ao vivo (Total x Efetivo, pausa, hidratação, de pé)")
    watch_parser.add_argument("--interval", type=float, default=1.0, help="intervalo de atualização em segundos")
    watch_parser.add_argument("--fullscreen", action="store_true", help="usa curses (tela fixa)")

    args = parser.parse_args()

    storage = StorageJSON()
    tracker = TimeTracker(storage)
    reports = ReportService(tracker)

    if args.cmd == "start":
        session_id = tracker.start()
        print(f"🟢 sessão iniciada: {session_id}")

    elif args.cmd == "stop":
        session_id = tracker.stop()
        if session_id:
            print(f"🟢 sessão encerrada: {session_id}")
        else:
            print("🔴 nenhuma sessão ativa para encerrar")

    elif args.cmd == "status":
        status = tracker.status()
        if status.active:
            print(
                f"🟢 sessão ativa desde {status.started_at.isoformat()} "
                f"(decorridos: {tracker.humanize_seconds(status.elapsed_seconds)})"
            )
        else:
            print("🔴 nenhuma sessão ativa")

    elif args.cmd == "report":
        if args.today:
            summary = reports.daily_summary(today_utc())
            print(f"📅 {summary['date']} | sessões: {summary['sessions']} | total: {summary['total_hms']}")
        elif args.week:
            summary = reports.week_summary(today_utc())
            print(f"📅 semana {summary['start']} → {summary['end']} | total: {summary['total_hms']}")
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
