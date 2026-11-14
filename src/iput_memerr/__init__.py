"""iput-memerr: погрешности измерения потребления оперативной памяти виртуальной машины.

Библиотека принимает число или вектор значений памяти и возвращает для каждой точки левую и правую
полуширины погрешности. Компоненты погрешности и способ их сложения задаются параметрами.
"""

from iput_memerr.core import COMPONENTS, FORMULAS, MemoryUncertainty, UncertaintyResult

__all__ = ["COMPONENTS", "FORMULAS", "MemoryUncertainty", "UncertaintyResult"]
__version__ = "0.0.1"
