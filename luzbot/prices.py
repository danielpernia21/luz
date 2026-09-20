"""Descarga del precio de la luz hora a hora, en EUR/kWh.

Fuente principal: tabla HTML de energiaxxi.com, la comercializadora contratada.
Respaldo: API publica de Red Electrica (apidatos.ree.es), serie PVPC.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re

import requests

from . import config

REE_URL = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
EXXI_URL = "https://www.energiaxxi.com/es/facturas/como-saber-cual-es-el-precio-de-la-luz"
USER_AGENT = "Mozilla/5.0 (compatible; luzbot/1.0)"
TIMEOUT = 30
# Peticiones a energiaxxi antes de rendirse: su CDN alterna copias de varios dias.
EXXI_INTENTOS = 4


class PriceError(RuntimeError):
    """No se ha podido obtener la tabla de precios de ninguna fuente."""


def fetch_prices(day: dt.date) -> tuple[dict[int, float], str]:
    """Devuelve ({hora: EUR/kWh}, nombre_de_la_fuente) para el dia indicado.

    La fuente principal es energiaxxi, que es la comercializadora contratada: sus
    precios no coinciden exactamente con el PVPC que publica REE, asi que la eleccion
    de franja se hace con la tabla que de verdad se factura. REE queda de respaldo.

    Ojo: la pagina de energiaxxi solo publica la tabla del dia en curso, por lo que
    `day` solo se respeta cuando se acaba usando el respaldo de REE.
    """
    errors = []
    if day == dt.date.today():
        try:
            return _from_energiaxxi(day), "energiaxxi.com"
        except Exception as exc:  # noqa: BLE001 - cualquier fallo cae al respaldo
            errors.append(f"energiaxxi: {exc}")

    try:
        return _from_ree(day), "Red Eléctrica (PVPC)"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"REE: {exc}")

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


def _from_energiaxxi(day: dt.date, intentos: int = EXXI_INTENTOS) -> dict[int, float]:
    """Descarga la tabla de energiaxxi y comprueba que sea la del dia pedido.

    Su CDN sirve varias copias cacheadas a la vez, algunas de dias anteriores, y
    va alternando entre ellas. Por eso se reintenta: si ninguna copia es del dia
    correcto se falla para que se use el respaldo de REE, en lugar de recomendar
    una franja calculada con precios viejos.
    """
    vistas = []
    for _ in range(intentos):
        resp = requests.get(EXXI_URL, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        prices, publicado = parse_energiaxxi(resp.text)
        if publicado is None or publicado == day:
            return prices
        vistas.append(publicado.strftime("%d/%m"))

    raise PriceError(f"la tabla publicada es del {', '.join(sorted(set(vistas)))}, no del dia pedido")


def parse_energiaxxi(page: str) -> tuple[dict[int, float], dt.date | None]:
    """Extrae la tabla horaria de energiaxxi (EUR/kWh) y el dia al que corresponde.

    Se prefiere el JSON que la pagina incrusta en el componente PricingTable, porque
    ademas de los precios trae la fecha; si no aparece, se cae a la tabla HTML, que
    no dice de que dia es (se devuelve None).
    """
    texto = html.unescape(html.unescape(page))
    prices, publicado = _from_pricing_table_json(texto)

    if not prices:
        publicado = None
        for hour, value in _ROW_RE.findall(texto.replace("&euro;", "\u20ac")):
            prices.setdefault(int(hour), float(value.replace(".", "").replace(",", ".")))

    _validate(prices, "energiaxxi")
    return prices, publicado


def _from_pricing_table_json(texto: str) -> tuple[dict[int, float], dt.date | None]:
    marca = '"priceDataToday":'
    inicio = texto.find(marca)
    if inicio == -1:
        return {}, None

    try:
        # raw_decode no tolera espacios por delante, y la pagina no siempre los omite.
        filas, _ = json.JSONDecoder().raw_decode(texto[inicio + len(marca):].lstrip())
    except ValueError:
        return {}, None

    prices: dict[int, float] = {}
    dias: set[dt.date] = set()
    for fila in filas:
        try:
            hora = int(str(fila["hora"]).split("-")[0])
            prices.setdefault(hora, float(fila["precio"]))
            dias.add(dt.datetime.strptime(fila["dia"], "%d/%m/%Y").date())
        except (KeyError, ValueError, TypeError):
            continue

    # Si la copia mezcla dias, nos quedamos con el mas reciente para compararlo fuera.
    return prices, max(dias) if dias else None


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
