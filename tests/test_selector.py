import pytest

from luzbot.selector import best_window, candidate_windows, day_average, worst_window


def test_elige_la_franja_mas_barata(prices):
    w = best_window(prices, duracion=3, hora_min=9, hora_max=22)
    assert (w.start, w.end) == (13, 16)
    assert w.avg == pytest.approx((0.08 + 0.07 + 0.09) / 3)


def test_respeta_los_limites_del_horario(prices):
    ventanas = candidate_windows(prices, duracion=3, hora_min=9, hora_max=22)
    assert all(v.start >= 9 and v.end <= 22 for v in ventanas)
    # De 9 a 22 con ciclos de 3h hay 11 arranques posibles (09:00 ... 19:00).
    assert len(ventanas) == 11


def test_las_horas_baratas_de_madrugada_quedan_fuera(prices):
    ventanas = candidate_windows(prices, duracion=3, hora_min=9, hora_max=22)
    assert all(v.start != 2 for v in ventanas)


def test_descarta_las_horas_ya_pasadas(prices):
    w = best_window(prices, duracion=3, hora_min=9, hora_max=22, desde_hora=16)
    assert w.start == 16


def test_sin_franja_posible_devuelve_none(prices):
    assert best_window(prices, duracion=3, hora_min=9, hora_max=22, desde_hora=20) is None


def test_empate_gana_la_mas_temprana():
    planos = {h: 0.10 for h in range(24)}
    assert best_window(planos, duracion=3, hora_min=9, hora_max=22).start == 9


def test_peor_franja_y_media(prices):
    assert worst_window(prices, duracion=3, hora_min=9, hora_max=22).start == 19
    assert day_average(prices) == pytest.approx(sum(prices.values()) / 24)
