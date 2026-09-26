import datetime as dt

import pytest

from luzbot.prices import PriceError, parse_ree


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


def test_ignora_las_horas_de_otro_dia():
    payload = _ree_payload("2026-09-20", {h: 200.0 for h in range(24)})
    payload["included"][1]["attributes"]["values"].append(
        {"value": 999.0, "datetime": "2026-09-21T00:00:00.000+02:00"}
    )
    prices = parse_ree(payload, dt.date(2026, 9, 20))
    assert prices[0] == pytest.approx(0.200)


def test_dia_de_23_horas_marzo():
    """El ultimo domingo de marzo no existen las 02:00 y aun asi debe valer."""
    valores = {h: 200.0 for h in range(24) if h != 2}
    prices = parse_ree(_ree_payload("2027-03-28", valores), dt.date(2027, 3, 28))
    assert len(prices) == 23
    assert 2 not in prices
    assert all(h in prices for h in range(9, 22))


def test_dia_de_25_horas_octubre():
    """El ultimo domingo de octubre las 02:00 se repiten: gana la primera."""
    day = "2026-10-25"
    payload = _ree_payload(day, {h: 200.0 + h for h in range(24)})
    payload["included"][1]["attributes"]["values"].insert(
        3, {"value": 999.0, "datetime": f"{day}T02:00:00.000+01:00"}
    )
    prices = parse_ree(payload, dt.date(2026, 10, 25))
    assert prices[2] == pytest.approx(0.202)


def test_falla_si_faltan_horas():
    payload = _ree_payload("2026-09-20", {h: 200.0 for h in range(20)})
    with pytest.raises(PriceError):
        parse_ree(payload, dt.date(2026, 9, 20))


def test_falla_si_falta_una_hora_del_horario_operativo():
    valores = {h: 200.0 for h in range(24) if h != 14}
    with pytest.raises(PriceError, match="faltan horas"):
        parse_ree(_ree_payload("2026-09-20", valores), dt.date(2026, 9, 20))


def test_falla_sin_serie_pvpc():
    with pytest.raises(PriceError):
        parse_ree({"included": []}, dt.date(2026, 9, 20))


def test_acepta_precios_negativos():
    valores = {h: 200.0 for h in range(24)}
    valores[13] = -12.35
    valores[14] = 0.0
    prices = parse_ree(_ree_payload("2026-09-20", valores), dt.date(2026, 9, 20))
    assert prices[13] == pytest.approx(-0.01235)
    assert prices[14] == 0.0


def test_falla_con_todos_los_precios_a_cero():
    valores = {h: 0.0 for h in range(24)}
    with pytest.raises(PriceError, match="a cero"):
        parse_ree(_ree_payload("2026-09-20", valores), dt.date(2026, 9, 20))
