"""Redacción de los mensajes de Telegram (parse_mode HTML)."""

from __future__ import annotations

import datetime as dt

from .selector import Window

DIAS = [
    "lunes", "martes", "miércoles", "jueves",
    "viernes", "sábado", "domingo",
]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def fecha_larga(day: dt.date) -> str:
    return f"{DIAS[day.weekday()]} {day.day} de {MESES[day.month - 1]}"


def eur_kwh(value: float) -> str:
    # Con precios muy bajos hacen falta 4 decimales para notar la diferencia.
    decimales = 4 if value < 0.1 else 3
    return f"{value:.{decimales}f}".replace(".", ",") + " €/kWh"


def eur(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " €"


def render_summary(
    day: dt.date,
    ventanas: list[Window],
    peor: Window | None,
    media_dia: float,
    kwh_total: float,
    fuente: str,
) -> str:
    """Resumen de las 09:00 con la mejor franja del día y las alternativas."""
    if not ventanas:
        return (
            f"🔌 <b>Luz de hoy, {fecha_larga(day)}</b>\n\n"
            "No queda ninguna franja completa dentro del horario permitido. "
            "Hoy toca dejarlo para mañana."
        )

    mejor = ventanas[0]
    ahorro = (media_dia - mejor.avg) * kwh_total

    lineas = [
        f"🔌 <b>Luz de hoy, {fecha_larga(day)}</b>",
        "",
        f"✅ <b>Mejor franja: {mejor.label}</b>  ({eur_kwh(mejor.avg)})",
        f"   Ahorro frente a la media del día: ~{eur(ahorro)} por lavado",
    ]

    alternativas = ventanas[1:3]
    if alternativas:
        lineas += ["", "Otras opciones:"]
        lineas += [f"   {w.label}   {eur_kwh(w.avg)}" for w in alternativas]

    if peor is not None and peor.start != mejor.start:
        lineas.append(f"   ⚠️ Evitar: {peor.label}   {eur_kwh(peor.avg)}")

    aviso = (
        dt.datetime.combine(day, dt.time(mejor.start)) - dt.timedelta(minutes=10)
    ).strftime("%H:%M")
    lineas += [
        "",
        f"Te aviso otra vez sobre las {aviso}.",
        f"<i>Fuente: {fuente}. Precios sin IVA ni impuesto eléctrico.</i>",
    ]
    return "\n".join(lineas)


def render_reminder(ventana: Window, minutos: int) -> str:
    """Aviso corto justo antes de que arranque la franja elegida."""
    cuando = "ya" if minutos <= 1 else f"en {minutos} minutos"
    return (
        f"⏰ <b>{cuando}</b> ({ventana.start:02d}:00): pon la lavadora y el lavavajillas.\n"
        f"Media hasta las {ventana.end:02d}:00: {eur_kwh(ventana.avg)} (sin impuestos)."
    )


def render_error(detalle: str) -> str:
    return (
        "⚠️ No he podido consultar el precio de la luz hoy.\n"
        f"<code>{detalle[:500]}</code>"
    )
