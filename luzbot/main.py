"""Punto de entrada: `python -m luzbot.main --mode summary|reminder`."""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from . import config, message, telegram
from .prices import PriceError, fetch_prices
from .selector import candidate_windows, day_average, worst_window


def reference_start_hour() -> int:
    """Primera hora a la que puede arrancar la franja.

    Es un valor fijo (no depende de la hora actual) para que el aviso previo
    reproduzca exactamente la franja que se anuncio en el resumen de la manana.
    """
    return max(config.HORA_MIN, config.HORA_RESUMEN + 1)


def _parse_now(value: str | None) -> dt.datetime:
    if value is None:
        return dt.datetime.now(config.TZ)
    return dt.datetime.fromisoformat(value).replace(tzinfo=config.TZ)


def run_summary(now: dt.datetime, *, dry_run: bool, force: bool) -> int:
    if not force and now.hour != config.HORA_RESUMEN:
        print(f"[summary] son las {now:%H:%M} en Madrid, no toca. Salgo.")
        return 0

    try:
        prices, fuente = fetch_prices(now.date())
    except PriceError as exc:
        telegram.send(message.render_error(str(exc)), dry_run=dry_run)
        return 1

    ventanas = candidate_windows(
        prices, config.DURACION_H, config.HORA_MIN, config.HORA_MAX, reference_start_hour()
    )
    texto = message.render_summary(
        now.date(),
        ventanas,
        worst_window(prices, config.DURACION_H, config.HORA_MIN, config.HORA_MAX),
        day_average(prices),
        config.LAVADORA_KWH + config.LAVAVAJILLAS_KWH,
        fuente,
    )
    telegram.send(texto, dry_run=dry_run)
    return 0


def run_reminder(now: dt.datetime, *, dry_run: bool, force: bool) -> int:
    minutos = 60 - now.minute
    proxima_hora = (now.hour + 1) % 24

    if not force and minutos > config.AVISO_MARGEN_MIN:
        print(f"[reminder] faltan {minutos} min para las {proxima_hora:02d}:00. Salgo.")
        return 0

    try:
        prices, _ = fetch_prices(now.date())
    except PriceError as exc:
        telegram.send(message.render_error(str(exc)), dry_run=dry_run)
        return 1

    ventanas = candidate_windows(
        prices, config.DURACION_H, config.HORA_MIN, config.HORA_MAX, reference_start_hour()
    )
    if not ventanas:
        print("[reminder] hoy no hay franja valida. Salgo.")
        return 0

    mejor = ventanas[0]
    if not force and mejor.start != proxima_hora:
        print(f"[reminder] la franja de hoy empieza a las {mejor.start:02d}:00. Salgo.")
        return 0

    telegram.send(message.render_reminder(mejor, minutos), dry_run=dry_run)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aviso de la mejor hora para lavadora y lavavajillas")
    parser.add_argument("--mode", choices=["summary", "reminder"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="imprime el mensaje en vez de enviarlo")
    parser.add_argument("--force", action="store_true", help="ignora los filtros horarios")
    parser.add_argument("--now", help="fecha/hora simulada en Madrid, p. ej. 2026-09-20T12:50")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    now = _parse_now(args.now)
    runner = run_summary if args.mode == "summary" else run_reminder
    return runner(now, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
