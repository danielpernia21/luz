import datetime as dt

from luzbot.message import render_error, render_reminder, render_summary
from luzbot.selector import candidate_windows, day_average, worst_window


def test_resumen_completo(prices):
    ventanas = candidate_windows(prices, 3, 9, 22, 10)
    texto = render_summary(
        dt.date(2026, 9, 20), ventanas,
        worst_window(prices, 3, 9, 22), day_average(prices), 2.2, "Red Eléctrica (PVPC)",
    )
    assert "domingo 20 de septiembre" in texto
    assert "13:00 → 16:00" in texto
    assert "Te aviso otra vez sobre las 12:50." in texto
    assert "Evitar: 19:00 → 22:00" in texto
    assert "sin IVA ni impuesto eléctrico" in texto


def test_el_aviso_avisa_de_que_el_precio_no_lleva_impuestos(prices):
    ventana = candidate_windows(prices, 3, 9, 22, 10)[0]
    assert "(sin impuestos)" in render_reminder(ventana, 10)


def test_resumen_sin_franjas():
    texto = render_summary(dt.date(2026, 9, 20), [], None, 0.1, 2.2, "REE")
    assert "mañana" in texto


def test_aviso(prices):
    ventana = candidate_windows(prices, 3, 9, 22, 10)[0]
    assert "en 10 minutos" in render_reminder(ventana, 10)
    assert "ya</b> (13:00)" in render_reminder(ventana, 1)


def test_error_recorta_el_detalle():
    assert "<code>" in render_error("boom" * 500)
