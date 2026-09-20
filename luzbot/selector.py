"""Eleccion de la mejor franja horaria para un ciclo de N horas seguidas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    """Una franja candidata: arranca a las `start` y termina a las `end` (exclusiva)."""

    start: int
    end: int
    avg: float

    @property
    def label(self) -> str:
        return f"{self.start:02d}:00 \u2192 {self.end:02d}:00"


def candidate_windows(
    prices: dict[int, float],
    duracion: int,
    hora_min: int,
    hora_max: int,
    desde_hora: int | None = None,
) -> list[Window]:
    """Todas las franjas validas, ordenadas de mas barata a mas cara.

    `desde_hora` descarta las franjas que ya no se pueden empezar (horas pasadas).
    """
    inicio_min = hora_min if desde_hora is None else max(hora_min, desde_hora)
    ventanas = []
    for start in range(inicio_min, hora_max - duracion + 1):
        horas = range(start, start + duracion)
        if any(h not in prices for h in horas):
            continue
        avg = sum(prices[h] for h in horas) / duracion
        ventanas.append(Window(start, start + duracion, avg))

    # Empates: gana la franja mas temprana.
    return sorted(ventanas, key=lambda w: (round(w.avg, 6), w.start))


def best_window(
    prices: dict[int, float],
    duracion: int,
    hora_min: int,
    hora_max: int,
    desde_hora: int | None = None,
) -> Window | None:
    ventanas = candidate_windows(prices, duracion, hora_min, hora_max, desde_hora)
    return ventanas[0] if ventanas else None


def worst_window(
    prices: dict[int, float], duracion: int, hora_min: int, hora_max: int
) -> Window | None:
    """La peor franja del rango permitido, para dar contexto en el resumen."""
    ventanas = candidate_windows(prices, duracion, hora_min, hora_max)
    return ventanas[-1] if ventanas else None


def day_average(prices: dict[int, float]) -> float:
    return sum(prices.values()) / len(prices)
