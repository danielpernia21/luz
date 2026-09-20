"""Descarga del precio de la luz hora a hora, en EUR/kWh.

Fuente: API publica de Red Electrica (apidatos.ree.es), serie PVPC (indicador ESIOS
1001), sin token ni registro. Es exactamente el precio que factura la comercializadora:
verificado contra una factura real de Energia XXI (PVPC, 21/07/2026-22/08/2026), donde
las 792 horas coinciden con una diferencia maxima de 0,000005 EUR/kWh, que es solo el
redondeo de la API, que publica en EUR/MWh con dos decimales.
"""

from __future__ import annotations

import datetime as dt

import requests

from . import config

REE_URL = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
FUENTE = "Red Eléctrica (PVPC)"
USER_AGENT = "Mozilla/5.0 (compatible; luzbot/1.0)"
TIMEOUT = 30


class PriceError(RuntimeError):
    """No se ha podido obtener la tabla de precios."""


def fetch_prices(day: dt.date) -> tuple[dict[int, float], str]:
    """Devuelve ({hora: EUR/kWh}, nombre_de_la_fuente) para el dia indicado."""
    params = {
        "start_date": f"{day.isoformat()}T00:00",
        "end_date": f"{day.isoformat()}T23:59",
        "time_trunc": "hour",
    }
    try:
        resp = requests.get(
            REE_URL, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        raise PriceError(f"no se ha podido consultar REE: {exc}") from exc
    except ValueError as exc:
        raise PriceError(f"REE ha devuelto una respuesta ilegible: {exc}") from exc

    return parse_ree(payload, day), FUENTE


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

    _validate(prices)
    return prices


def _validate(prices: dict[int, float]) -> None:
    # Los domingos del cambio de hora el dia tiene 23 o 25 horas, asi que no se
    # exigen las 24: basta con que esten todas las del horario operativo.
    if len(prices) < 23:
        raise PriceError(f"REE: solo {len(prices)} horas en la tabla")
    missing = sorted(set(range(config.HORA_MIN, config.HORA_MAX)) - set(prices))
    if missing:
        raise PriceError(f"REE: faltan horas {missing}")
    if any(p <= 0 for p in prices.values()):
        raise PriceError("REE: hay precios no positivos")
