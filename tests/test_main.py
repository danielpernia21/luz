"""Los filtros horarios, que son los que deciden si el mensaje sale o no.

GitHub retrasa el cron con frecuencia, asi que lo que se comprueba aqui es que
un sondeo tardio sigue enviando y que los demas se callan.
"""

import datetime as dt

import pytest

from luzbot import main
from luzbot.prices import PriceError


@pytest.fixture
def enviados(monkeypatch, prices):
    """Captura lo que se enviaria a Telegram en vez de mandarlo."""
    salida: list[str] = []
    monkeypatch.setattr(main.telegram, "send", lambda texto, dry_run=False: salida.append(texto))
    monkeypatch.setattr(main, "fetch_prices", lambda day: (prices, "REE"))
    return salida


def correr(modo, cuando, **kwargs):
    return main.main([f"--mode={modo}", f"--now={cuando}"] + [f"--{k}" for k in kwargs])


# La franja mas barata del fixture es 13:00 -> 16:00.


def test_el_resumen_sale_a_las_nueve(enviados):
    assert correr("summary", "2026-09-20T09:00") == 0
    assert "Mejor franja: 13:00 → 16:00" in enviados[0]


def test_el_resumen_sale_igual_si_el_cron_llega_tarde(enviados):
    assert correr("summary", "2026-09-20T10:50") == 0
    assert len(enviados) == 1


def test_el_resumen_no_sale_fuera_de_su_ventana(enviados):
    assert correr("summary", "2026-09-20T11:00") == 0
    assert enviados == []


def test_un_fallo_de_ree_temprano_se_reintenta_en_silencio(monkeypatch, enviados):
    monkeypatch.setattr(main, "fetch_prices", _explota)
    assert correr("summary", "2026-09-20T09:00") == 1
    assert enviados == []


def test_un_fallo_de_ree_en_el_ultimo_sondeo_si_avisa(monkeypatch, enviados):
    monkeypatch.setattr(main, "fetch_prices", _explota)
    assert correr("summary", "2026-09-20T10:50") == 1
    assert "No he podido consultar" in enviados[0]


def test_el_recordatorio_sale_diez_minutos_antes(enviados):
    assert correr("reminder", "2026-09-20T12:50") == 0
    assert "en 10 minutos</b> (13:00)" in enviados[0]


def test_el_recordatorio_sale_aunque_el_cron_se_retrase_al_ultimo_minuto(enviados):
    assert correr("reminder", "2026-09-20T12:59") == 0
    assert "en 1 minutos" in enviados[0] or "ya</b>" in enviados[0]


def test_el_recordatorio_sale_aunque_la_franja_ya_haya_empezado(enviados):
    assert correr("reminder", "2026-09-20T13:07") == 0
    assert "ya</b> (13:00)" in enviados[0]


def test_el_recordatorio_no_sale_si_el_retraso_es_demasiado(enviados):
    assert correr("reminder", "2026-09-20T13:20") == 0
    assert enviados == []


def test_el_recordatorio_no_sale_antes_de_tiempo(enviados):
    assert correr("reminder", "2026-09-20T11:50") == 0
    assert enviados == []


def test_force_ignora_la_hora(enviados):
    assert correr("summary", "2026-09-20T18:00", force=True) == 0
    assert len(enviados) == 1


def test_la_marca_solo_se_escribe_si_hubo_envio(tmp_path, enviados):
    marca = tmp_path / ".enviado"
    main.main(["--mode=summary", "--now=2026-09-20T09:00", f"--marker={marca}"])
    assert marca.exists()

    otra = tmp_path / "otra"
    main.main(["--mode=summary", "--now=2026-09-20T11:00", f"--marker={otra}"])
    assert not otra.exists()


def _explota(day):
    raise PriceError("REE no responde")
