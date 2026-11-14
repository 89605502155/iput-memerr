"""Валидаторы входа: типы, формы, знаки, диапазоны, неизвестные имена."""

import numpy as np
import pytest

from iput_memerr import MemoryUncertainty


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_non_finite_values_rejected(bad):
    with pytest.raises(ValueError, match="конечными"):
        MemoryUncertainty().evaluate(np.array([1.0, bad]))


def test_negative_memory_rejected():
    with pytest.raises(ValueError, match="отрицательными"):
        MemoryUncertainty().evaluate(np.array([1.0, -2.0]))


def test_two_dimensional_input_rejected():
    with pytest.raises(ValueError, match="ndim"):
        MemoryUncertainty().evaluate(np.ones((2, 2)))


def test_non_numeric_input_rejected():
    with pytest.raises(TypeError):
        MemoryUncertainty().evaluate(["a", "b"])


def test_unknown_component_rejected():
    with pytest.raises(ValueError, match="неизвестные"):
        MemoryUncertainty(components=("instrument", "cosmic_rays"))


def test_empty_and_duplicate_components_rejected():
    with pytest.raises(ValueError, match="хотя бы одна"):
        MemoryUncertainty(components=())
    with pytest.raises(ValueError, match="не должны повторяться"):
        MemoryUncertainty(components=("float", "float"))


def test_unknown_formula_and_dtype_rejected():
    with pytest.raises(ValueError, match="formula"):
        MemoryUncertainty(formula="montecarlo")
    with pytest.raises(ValueError, match="dtype"):
        MemoryUncertainty(dtype="float128")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"instrument_rel": -0.1},
        {"shared_fraction": 1.5},
        {"sampling_factor": -1.0},
        {"page_size": 0.0},
        {"round_step": 0.0},
        {"coverage": 0.0},
    ],
)
def test_out_of_range_parameters_rejected(kwargs):
    with pytest.raises(ValueError):
        MemoryUncertainty(**kwargs)


def test_boolean_parameter_rejected():
    with pytest.raises(TypeError):
        MemoryUncertainty(page_size=True)


def test_timestamps_must_increase_and_match_shape():
    m = MemoryUncertainty(components=("time",))
    with pytest.raises(ValueError, match="строго возрастать"):
        m.evaluate(np.array([1.0, 2.0]), timestamp=np.array([1.0, 1.0]))
    with pytest.raises(ValueError, match="форма"):
        m.evaluate(np.array([1.0, 2.0]), timestamp=np.array([0.0, 1.0, 2.0]))


def test_slope_and_neighbours_shape_checked():
    with pytest.raises(ValueError, match="slope"):
        MemoryUncertainty(components=("time",)).evaluate(np.array([1.0, 2.0]), slope=np.array([1.0]))
    with pytest.raises(ValueError, match="neighbours"):
        MemoryUncertainty(components=("sampling",)).evaluate(
            np.array([1.0, 2.0]), neighbours=(np.array([1.0]), np.array([1.0, 2.0]))
        )
