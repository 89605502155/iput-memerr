"""Модель погрешности измерения потребления оперативной памяти.

Для каждой точки ряда библиотека считает полуширины погрешности слева (ниже значения) и справа
(выше значения). Каждая компонента даёт свою пару полуширин (left, right). Компоненты складываются
по формуле, которую выбирает параметр ``formula``:

* ``linear``: суммы модулей (консервативная граница, если каждая компонента есть граница);
* ``rss``: корень из суммы квадратов полуширин;
* ``gum``: корень из суммы квадратов стандартных неопределённостей по JCGM 100:2008. Полуширина
  равномерного распределения делится на sqrt(3), полуширина нормального на коэффициент ``normal_k``.
* ``gum_shift``: как ``gum``, но одностороння компонента определения величины (равномерная на
  отрезке [0; b]) учитывается со своим средним b/2 и дисперсией b**2/12. Центр интервала сдвигается
  на b/2, левая полуширина равна b/2 + c*sigma, правая max(0; c*sigma - b/2). Для сумм без компоненты
  определения величины совпадает с ``gum``.

Все величины в байтах, моменты времени в секундах, доли безразмерные.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from iput_memerr import validate as v

COMPONENTS: tuple[str, ...] = (
    "instrument",
    "storage",
    "time",
    "sampling",
    "rounding",
    "float",
    "definition",
)
FORMULAS: tuple[str, ...] = ("linear", "rss", "gum", "gum_shift")
DTYPE_UNIT_ROUNDOFF: dict[str, float] = {
    "float16": 2.0**-11,
    "float32": 2.0**-24,
    "float64": 2.0**-53,
}
_SQRT3 = math.sqrt(3.0)


@dataclass(frozen=True)
class UncertaintyResult:
    """Значения и погрешности; все массивы одной формы с ``value``."""

    value: np.ndarray
    left: np.ndarray
    right: np.ndarray
    components: dict[str, tuple[np.ndarray, np.ndarray]] = field(default_factory=dict)
    formula: str = "linear"

    @property
    def lower(self) -> np.ndarray:
        return self.value - self.left

    @property
    def upper(self) -> np.ndarray:
        return self.value + self.right

    @property
    def symmetric(self) -> np.ndarray:
        return np.isclose(self.left, self.right)

    def to_dict(self) -> dict[str, list[float] | str | list[str]]:
        """Выгрузка в простые типы (для JSON и CSV)."""
        return {
            "value": np.atleast_1d(self.value).tolist(),
            "left": np.atleast_1d(self.left).tolist(),
            "right": np.atleast_1d(self.right).tolist(),
            "formula": self.formula,
            "components": list(self.components),
        }


class MemoryUncertainty:
    """Оценка погрешности значений потребления памяти.

    Параметры конструктора задают состав компонент и их константы. Параметры ``evaluate`` задают данные
    конкретного ряда. Значения по умолчанию условные и подлежат калибровке на стенде (см. docs).

    Parameters
    ----------
    components : подмножество COMPONENTS, которые учитываются.
    formula : один из FORMULAS, способ сложения компонент.
    instrument_rel : относительная погрешность измерительной системы (доля от значения).
    normal_k : коэффициент для нормально распределённых компонент (2 соответствует 95 %).
    page_size : размер страницы памяти в байтах, гранулярность хранилища счётчика.
    clock_jitter_s : джиттер часов при отсчёте момента времени, с.
    read_latency_s : время чтения счётчика, с (вклад в момент времени берётся как половина).
    round_step : шаг округления при записи значения, байты.
    dtype : тип, в котором хранится значение (float16, float32, float64).
    shared_fraction : доля разделяемых страниц, которые учтены в значении, но не принадлежат ВМ.
    sampling_factor : доля размаха соседних отсчётов, которая переходит в погрешность дискретизации.
    coverage : коэффициент охвата для формулы gum.
    """

    def __init__(
        self,
        components: tuple[str, ...] = COMPONENTS,
        formula: str = "linear",
        *,
        instrument_rel: float = 0.01,
        normal_k: float = 2.0,
        page_size: float = 4096.0,
        clock_jitter_s: float = 0.001,
        read_latency_s: float = 0.0,
        round_step: float = 1.0,
        dtype: str = "float64",
        shared_fraction: float = 0.0,
        sampling_factor: float = 0.5,
        coverage: float = 1.0,
    ) -> None:
        self.components = v.check_components(components, COMPONENTS)
        self.formula = v.check_choice("formula", formula, FORMULAS)
        self.instrument_rel = v.check_scalar("instrument_rel", instrument_rel, low=0.0)
        self.normal_k = v.check_scalar("normal_k", normal_k, low=0.0, strict_low=True)
        self.page_size = v.check_scalar("page_size", page_size, low=0.0, strict_low=True)
        self.clock_jitter_s = v.check_scalar("clock_jitter_s", clock_jitter_s, low=0.0)
        self.read_latency_s = v.check_scalar("read_latency_s", read_latency_s, low=0.0)
        self.round_step = v.check_scalar("round_step", round_step, low=0.0, strict_low=True)
        self.dtype = v.check_choice("dtype", dtype, tuple(DTYPE_UNIT_ROUNDOFF))
        self.shared_fraction = v.check_scalar("shared_fraction", shared_fraction, low=0.0, high=1.0)
        self.sampling_factor = v.check_scalar("sampling_factor", sampling_factor, low=0.0, high=1.0)
        self.coverage = v.check_scalar("coverage", coverage, low=0.0, strict_low=True)

    def evaluate(
        self,
        value: object,
        *,
        timestamp: object | None = None,
        slope: object | None = None,
        neighbours: tuple[object, object] | None = None,
    ) -> UncertaintyResult:
        """Посчитать значения и погрешности.

        Parameters
        ----------
        value : число или вектор значений памяти, байты.
        timestamp : моменты отсчётов, с, той же формы, что value (нужны для компоненты time).
        slope : производная памяти по времени, байты/с (для скаляра вместо timestamp).
        neighbours : пара (предыдущие, следующие) отсчёты той же формы (нужны для sampling у скаляра).
            Для вектора соседи берутся из самого ряда, края дублируются.
        """
        x = v.as_float_array("value", value)
        v.check_nonnegative("value", x)
        scalar = x.ndim == 0
        xv = np.atleast_1d(x)

        t = None
        if timestamp is not None:
            t_raw = v.as_float_array("timestamp", timestamp)
            if t_raw.shape != x.shape:
                raise ValueError("timestamp: форма должна совпадать с value")
            v.check_timestamps(t_raw, scalar=scalar)
            t = np.atleast_1d(t_raw)

        prev, nxt = self._neighbours(x, xv, scalar, neighbours)
        s = self._slope(x, xv, t, scalar, slope)

        parts = self._components(xv, s, prev, nxt)
        left, right = self._combine(parts)
        shape = x.shape
        comps = {
            name: (np.reshape(lo, shape), np.reshape(ro, shape)) for name, (lo, ro, _) in parts.items()
        }
        return UncertaintyResult(
            value=x,
            left=np.reshape(left, shape),
            right=np.reshape(right, shape),
            components=comps,
            formula=self.formula,
        )

    # ---- входные данные -------------------------------------------------------------------

    @staticmethod
    def _neighbours(x, xv, scalar, neighbours):
        if neighbours is None:
            if scalar:
                return None, None
            prev = np.concatenate(([xv[0]], xv[:-1]))
            nxt = np.concatenate((xv[1:], [xv[-1]]))
            return prev, nxt
        prev_raw, next_raw = neighbours
        prev = v.as_float_array("neighbours[0]", prev_raw)
        nxt = v.as_float_array("neighbours[1]", next_raw)
        if prev.shape != x.shape or nxt.shape != x.shape:
            raise ValueError("neighbours: формы должны совпадать с value")
        v.check_nonnegative("neighbours", prev)
        v.check_nonnegative("neighbours", nxt)
        return np.atleast_1d(prev), np.atleast_1d(nxt)

    def _slope(self, x, xv, t, scalar, slope):
        if "time" not in self.components:
            return None
        if slope is not None:
            s_raw = v.as_float_array("slope", slope)
            if s_raw.shape != x.shape:
                raise ValueError("slope: форма должна совпадать с value")
            return np.atleast_1d(s_raw)
        if t is None:
            raise ValueError("time: нужен timestamp или slope")
        if scalar:
            raise ValueError("time: для скалярного value нужен slope")
        return np.gradient(xv, t)

    # ---- компоненты -------------------------------------------------------------------------

    def _components(self, xv, s, prev, nxt):
        """Вернуть {имя: (левая, правая, распределение)} для включённых компонент."""
        out: dict[str, tuple[np.ndarray, np.ndarray, str]] = {}
        n = xv.size
        for name in self.components:
            if name == "instrument":
                a = self.instrument_rel * xv
                out[name] = (a, a, "norm")
            elif name == "storage":
                a = np.full(n, self.page_size / 2.0)
                out[name] = (a, a, "rect")
            elif name == "time":
                a = np.abs(s) * (self.clock_jitter_s + self.read_latency_s / 2.0)
                out[name] = (a, a, "rect")
            elif name == "sampling":
                if prev is None or nxt is None:
                    raise ValueError("sampling: для скалярного value нужны neighbours")
                lo = self.sampling_factor * np.maximum(0.0, xv - np.minimum(prev, nxt))
                ro = self.sampling_factor * np.maximum(0.0, np.maximum(prev, nxt) - xv)
                out[name] = (lo, ro, "rect")
            elif name == "rounding":
                a = np.full(n, self.round_step / 2.0)
                out[name] = (a, a, "rect")
            elif name == "float":
                a = DTYPE_UNIT_ROUNDOFF[self.dtype] * xv
                out[name] = (a, a, "rect")
            elif name == "definition":
                lo = self.shared_fraction * xv
                out[name] = (lo, np.zeros(n), "rect")
        return out

    def _combine(self, parts):
        if not parts:
            raise ValueError("нет включённых компонент")
        n = next(iter(parts.values()))[0].size
        if self.formula == "linear":
            left = sum((lo for lo, _, _ in parts.values()), np.zeros(n))
            right = sum((ro for _, ro, _ in parts.values()), np.zeros(n))
            return left, right
        if self.formula == "rss":
            left = np.sqrt(sum((lo**2 for lo, _, _ in parts.values()), np.zeros(n)))
            right = np.sqrt(sum((ro**2 for _, ro, _ in parts.values()), np.zeros(n)))
            return left, right
        def divisor(dist: str) -> float:
            return _SQRT3 if dist == "rect" else self.normal_k

        if self.formula == "gum_shift":
            # одностороння компонента определения величины: равномерна на [0; b], b = L_7,
            # среднее b/2 сдвигает центр, дисперсия b^2/12 входит в обе стороны (распределение ошибки)
            var_l = sum(
                ((lo / divisor(d)) ** 2 for name, (lo, _, d) in parts.items() if name != "definition"),
                np.zeros(n),
            )
            var_r = sum(
                ((ro / divisor(d)) ** 2 for name, (_, ro, d) in parts.items() if name != "definition"),
                np.zeros(n),
            )
            shift = np.zeros(n)
            if "definition" in parts:
                b = parts["definition"][0]
                shift = b / 2.0
                var_l = var_l + b**2 / 12.0
                var_r = var_r + b**2 / 12.0
            left = shift + self.coverage * np.sqrt(var_l)
            right = np.maximum(0.0, self.coverage * np.sqrt(var_r) - shift)
            return left, right

        # gum
        left = self.coverage * np.sqrt(
            sum(((lo / divisor(d)) ** 2 for lo, _, d in parts.values()), np.zeros(n))
        )
        right = self.coverage * np.sqrt(
            sum(((ro / divisor(d)) ** 2 for _, ro, d in parts.values()), np.zeros(n))
        )
        return left, right
