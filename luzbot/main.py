"""Punto de entrada: `python -m luzbot.main --mode summary|reminder`."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
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


def _enviar(texto: str, *, dry_run: bool, marker: str | None) -> None:
    """Envia el mensaje y deja constancia para que no salga dos veces.

    El workflow guarda el `marker` en la cache del dia: como GitHub retrasa el
    cron, se sondea varias veces y es esta marca la que evita el duplicado.
    """
    telegram.send(texto, dry_run=dry_run)
    if not dry_run and marker:
        pathlib.Path(marker).write_text("enviado\n", encoding="utf-8")


def _minutos_hasta(now: dt.datetime, hora: int) -> float:
    inicio = now.replace(hour=hora, minute=0, second=0, microsecond=0)
    return (inicio - now).total_seconds() / 60


def run_summary(
    now: dt.datetime, *, dry_run: bool, force: bool, marker: str | None = None
) -> int:
    if not force and not (config.HORA_RESUMEN <= now.hour < config.RESUMEN_LIMITE_H):
        print(f"[summary] son las {now:%H:%M} en Madrid, no toca. Salgo.")
        return 0

    try:
        prices, fuente = fetch_prices(now.date())
    except PriceError as exc:
        # Mientras queden sondeos por delante se reintenta en silencio: un fallo
        # puntual de REE no debe gastar el mensaje del dia.
        if force or now.hour >= config.RESUMEN_LIMITE_H - 1:
            _enviar(message.render_error(str(exc)), dry_run=dry_run, marker=marker)
        else:
            print(f"[summary] REE ha fallado ({exc}); reintento en el siguiente sondeo.")
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
    _enviar(texto, dry_run=dry_run, marker=marker)
    return 0


def _cerca_de_una_hora_en_punto(now: dt.datetime) -> bool:
    """Filtro barato para no consultar REE en sondeos que no pueden avisar."""
    return (60 - now.minute) <= config.AVISO_VENTANA_MIN or now.minute <= config.AVISO_RETRASO_MIN


def run_reminder(
    now: dt.datetime, *, dry_run: bool, force: bool, marker: str | None = None
) -> int:
    if not force and not _cerca_de_una_hora_en_punto(now):
        print(f"[reminder] son las {now:%H:%M}, ninguna franja arranca ahora. Salgo.")
        return 0

    try:
        prices, _ = fetch_prices(now.date())
    except PriceError as exc:
        # El resumen de la manana ya avisa de los fallos de REE; aqui basta con
        # dejarlo en el log y que lo reintente el siguiente sondeo.
        if force:
            _enviar(message.render_error(str(exc)), dry_run=dry_run, marker=marker)
        else:
            print(f"[reminder] REE ha fallado ({exc}); reintento en el siguiente sondeo.")
        return 1

    ventanas = candidate_windows(
        prices, config.DURACION_H, config.HORA_MIN, config.HORA_MAX, reference_start_hour()
    )
    if not ventanas:
        print("[reminder] hoy no hay franja valida. Salgo.")
        return 0

    mejor = ventanas[0]
    faltan = _minutos_hasta(now, mejor.start)
    if not force and not (-config.AVISO_RETRASO_MIN <= faltan <= config.AVISO_VENTANA_MIN):
        print(
            f"[reminder] la franja de hoy empieza a las {mejor.start:02d}:00 "
            f"({faltan:+.0f} min). Salgo."
        )
        return 0

    _enviar(
        message.render_reminder(mejor, max(0, round(faltan))), dry_run=dry_run, marker=marker
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aviso de la mejor hora para lavadora y lavavajillas")
    parser.add_argument("--mode", choices=["summary", "reminder"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="imprime el mensaje en vez de enviarlo")
    parser.add_argument("--force", action="store_true", help="ignora los filtros horarios")
    parser.add_argument("--now", help="fecha/hora simulada en Madrid, p. ej. 2026-09-20T12:50")
    parser.add_argument("--marker", help="fichero que se crea si el mensaje llega a enviarse")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    now = _parse_now(args.now)
    runner = run_summary if args.mode == "summary" else run_reminder
    return runner(now, dry_run=args.dry_run, force=args.force, marker=args.marker)


if __name__ == "__main__":
    raise SystemExit(main())
