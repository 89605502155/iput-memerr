"""Валидаторы входных данных и параметров библиотеки iput-memerr."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


def as_float_array(name: str, value: object) -> np.ndarray:
    """Привести вход к массиву float; число или одномерный вектор конечных значений."""
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name}: ожидается число или вектор чисел") from exc
    if arr.ndim > 1:
        raise ValueError(f"{name}: допускается только число или одномерный вектор, получено ndim={arr.ndim}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name}: все значения должны быть конечными (без NaN и inf)")
    return arr


def check_nonnegative(name: str, arr: np.ndarray) -> None:
    if np.any(arr < 0):
        raise ValueError(f"{name}: значения не могут быть отрицательными")


def check_scalar(name: str, value: object, *, low: float | None = None, high: float | None = None,
                 strict_low: bool = False) -> float:
    """Проверить скалярный параметр: конечное число в заданном диапазоне."""
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name}: ожидается число, получено {type(value).__name__}")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name}: значение должно быть конечным")
    if low is not None:
        if (x <= low) if strict_low else (x < low):
            op = ">" if strict_low else ">="
            raise ValueError(f"{name}: должно быть {op} {low}, получено {x}")
    if high is not None and x > high:
        raise ValueError(f"{name}: должно быть <= {high}, получено {x}")
    return x


def check_choice(name: str, value: object, options: Iterable[str]) -> str:
    opts = tuple(options)
    if value not in opts:
        raise ValueError(f"{name}: допустимые значения {opts}, получено {value!r}")
    return str(value)


def check_components(components: Iterable[str], known: tuple[str, ...]) -> tuple[str, ...]:
    names = tuple(components)
    if not names:
        raise ValueError("components: нужна хотя бы одна компонента погрешности")
    if len(set(names)) != len(names):
        raise ValueError(f"components: имена не должны повторяться: {names}")
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(f"components: неизвестные компоненты {unknown}, допустимы {known}")
    return names


def check_timestamps(t: np.ndarray, *, scalar: bool) -> None:
    if scalar:
        return
    if t.size < 2:
        raise ValueError("timestamp: для вектора нужно не меньше двух моментов времени")
    if np.any(np.diff(t) <= 0):
        raise ValueError("timestamp: моменты времени должны строго возрастать")
