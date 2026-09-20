import datetime as dt
import json

import pytest

from luzbot.prices import (
    PriceError,
    _from_energiaxxi,
    parse_energiaxxi,
    parse_ree,
)


def _ree_payload(day: str, valores: dict[int, float]) -> dict:
    return {
        "included": [
            {
                "type": "Precio mercado spot",
                "id": "600",
                "attributes": {"values": [{"value": 1.0, "datetime": f"{day}T00:00:00.000+02:00"}]},
            },
            {
                "type": "PVPC",
                "id": "1001",
                "attributes": {
                    "values": [
                        {"value": v, "datetime": f"{day}T{h:02d}:00:00.000+02:00"}
                        for h, v in valores.items()
                    ]
                },
            },
        ]
    }


def test_parse_ree_pasa_de_mwh_a_kwh():
    day = dt.date(2026, 9, 20)
    payload = _ree_payload("2026-09-20", {h: 200.0 + h for h in range(24)})
    prices = parse_ree(payload, day)
    assert len(prices) == 24
    assert prices[0] == pytest.approx(0.200)
    assert prices[23] == pytest.approx(0.223)


def test_parse_ree_dia_de_23_horas_marzo():
    """El ultimo domingo de marzo no existen las 02:00 y aun asi debe valer."""
    valores = {h: 200.0 for h in range(24) if h != 2}
    prices = parse_ree(_ree_payload("2027-03-28", valores), dt.date(2027, 3, 28))
    assert len(prices) == 23
    assert 2 not in prices
    assert all(h in prices for h in range(9, 22))


def test_parse_ree_dia_de_25_horas_octubre():
    """El ultimo domingo de octubre las 02:00 se repiten: gana la primera."""
    day = "2026-10-25"
    payload = _ree_payload(day, {h: 200.0 + h for h in range(24)})
    payload["included"][1]["attributes"]["values"].insert(
        3, {"value": 999.0, "datetime": f"{day}T02:00:00.000+01:00"}
    )
    prices = parse_ree(payload, dt.date(2026, 10, 25))
    assert prices[2] == pytest.approx(0.202)


def test_parse_ree_falla_si_faltan_horas():
    payload = _ree_payload("2026-09-20", {h: 200.0 for h in range(20)})
    with pytest.raises(PriceError):
        parse_ree(payload, dt.date(2026, 9, 20))


def test_parse_ree_falla_sin_serie_pvpc():
    with pytest.raises(PriceError):
        parse_ree({"included": []}, dt.date(2026, 9, 20))


HTML_FILA = (
    '<tr><td>{h:02d}:00 a {n:02d}:00</td>'
    '<td class="average-price price">0,{v:05d} &euro;/kWh</td></tr>'
)


def test_parse_energiaxxi_html_sin_fecha():
    page = "<table>" + "".join(
        HTML_FILA.format(h=h, n=(h + 1) % 24, v=20000 + h) for h in range(24)
    ) + "</table>"
    prices, publicado = parse_energiaxxi(page)
    assert len(prices) == 24
    assert prices[0] == pytest.approx(0.20000)
    assert prices[7] == pytest.approx(0.20007)
    assert publicado is None


def test_parse_energiaxxi_tabla_incompleta():
    page = "<table>" + HTML_FILA.format(h=0, n=1, v=20000) + "</table>"
    with pytest.raises(PriceError):
        parse_energiaxxi(page)


def _pagina_con_json(dia: str) -> str:
    filas = [
        {"precio": 0.2 + h / 1000, "hora": f"{h:02d}-{(h + 1) % 24:02d}", "id": h, "dia": dia}
        for h in range(24)
    ]
    # La pagina incrusta el JSON escapado dentro de un atributo HTML.
    crudo = json.dumps({"ivaRate": "10", "priceDataToday": filas, "priceDataTomorrow": []})
    return f"<div data-content='{crudo.replace('\"', '&quot;')}'></div>"


def test_parse_energiaxxi_lee_el_json_y_su_fecha():
    prices, publicado = parse_energiaxxi(_pagina_con_json("20/09/2026"))
    assert len(prices) == 24
    assert prices[14] == pytest.approx(0.214)
    assert publicado == dt.date(2026, 9, 20)


def test_energiaxxi_rechaza_la_copia_de_otro_dia(monkeypatch):
    """Su CDN sirve copias viejas: hay que descartarlas, no recomendar con ellas."""
    respuestas = [_pagina_con_json("12/09/2026"), _pagina_con_json("18/09/2026")]

    class FakeResp:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        return FakeResp(respuestas[fake_get.n % len(respuestas)])

    fake_get.n = 0
    monkeypatch.setattr("luzbot.prices.requests.get", fake_get)

    with pytest.raises(PriceError, match="no del dia pedido"):
        _from_energiaxxi(dt.date(2026, 9, 20), intentos=2)


def test_energiaxxi_acepta_la_copia_del_dia(monkeypatch):
    class FakeResp:
        text = _pagina_con_json("20/09/2026")

        def raise_for_status(self):
            pass

    monkeypatch.setattr("luzbot.prices.requests.get", lambda url, **kw: FakeResp())
    prices = _from_energiaxxi(dt.date(2026, 9, 20))
    assert prices[0] == pytest.approx(0.2)
