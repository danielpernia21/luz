"""Descarga del precio de la luz hora a hora, en EUR/kWh.

Fuente principal: API publica de Red Electrica (apidatos.ree.es), serie PVPC.
Respaldo: tabla HTML de energiaxxi.com (mismo PVPC, por si la API falla).
"""

from __future__ import annotations

import datetime as dt
import html
import re

import requests

from . import config

REE_URL = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
EXXI_URL = "https://www.energiaxxi.com/es/facturas/como-saber-cual-es-el-precio-de-la-luz"
USER_AGENT = "Mozilla/5.0 (compatible; luzbot/1.0)"
TIMEOUT = 30


class PriceError(RuntimeError):
    """No se ha podido obtener la tabla de precios de ninguna fuente."""


def fetch_prices(day: dt.date) -> tuple[dict[int, float], str]:
    """Devuelve ({hora: EUR/kWh}, nombre_de_la_fuente) para el dia indicado."""
    errors = []
    try:
        return _from_ree(day), "Red Eléctrica (PVPC)"
    except Exception as exc:  # noqa: BLE001 - cualquier fallo cae al respaldo
        errors.append(f"REE: {exc}")

    try:
        return _from_energiaxxi(), "energiaxxi.com"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"energiaxxi: {exc}")

    raise PriceError(" | ".join(errors))


def _from_ree(day: dt.date) -> dict[int, float]:
    params = {
        "start_date": f"{day.isoformat()}T00:00",
        "end_date": f"{day.isoformat()}T23:59",
        "time_trunc": "hour",
    }
    resp = requests.get(
        REE_URL, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
    )
    resp.raise_for_status()
    return parse_ree(resp.json(), day)


def parse_ree(payload: dict, day: dt.date) -> dict[int, float]:
    """Extrae la serie PVPC (EUR/MWh) y la pasa a EUR/kWh."""
    series = None
    for item in payload.get("included", []):
        if item.get("type") == "PVPC" or item.get("id") == "1001":
            series = item
            break
    if series is None:
        raise PriceError("la respuesta de REE no incluye la serie PVPC")

    prices: dict[int, float] = {}
    for point in series["attributes"]["values"]:
        stamp = dt.datetime.fromisoformat(point["datetime"])
        if stamp.date() != day:
            continue
        # El domingo de octubre las 02:00 llegan dos veces: nos quedamos con la primera.
        prices.setdefault(stamp.hour, float(point["value"]) / 1000.0)

    _validate(prices, "REE")
    return prices


# <td>08:00 a 09:00</td> ... <td class="high-price price">0,26560 &euro;/kWh</td>
_ROW_RE = re.compile(
    r"<td[^>]*>\s*(\d{2}):00\s*a\s*\d{2}:00\s*</td>\s*"
    r"<td[^>]*>\s*([\d.,]+)\s*(?:&euro;|\u20ac)\s*/\s*kWh",
    re.IGNORECASE,
)


def _from_energiaxxi() -> dict[int, float]:
    resp = requests.get(EXXI_URL, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return parse_energiaxxi(resp.text)


def parse_energiaxxi(page: str) -> dict[int, float]:
    """Extrae la tabla horaria de la pagina de energiaxxi (ya en EUR/kWh)."""
    prices: dict[int, float] = {}
    for hour, value in _ROW_RE.findall(html.unescape(page).replace("&euro;", "\u20ac")):
        prices.setdefault(int(hour), float(value.replace(".", "").replace(",", ".")))

    _validate(prices, "energiaxxi")
    return prices


def _validate(prices: dict[int, float], source: str) -> None:
    # Los domingos del cambio de hora el dia tiene 23 o 25 horas, asi que no se
    # exigen las 24: basta con que esten todas las del horario operativo.
    if len(prices) < 23:
        raise PriceError(f"{source}: solo {len(prices)} horas en la tabla")
    missing = sorted(set(range(config.HORA_MIN, config.HORA_MAX)) - set(prices))
    if missing:
        raise PriceError(f"{source}: faltan horas {missing}")
    if any(p <= 0 for p in prices.values()):
        raise PriceError(f"{source}: hay precios no positivos")
