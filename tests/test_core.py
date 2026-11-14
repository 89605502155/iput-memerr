"""Проверки модели погрешности: компоненты, формулы, асимметрия, форма результатов."""

import math

import numpy as np
import pytest

from iput_memerr import COMPONENTS, FORMULAS, MemoryUncertainty


def test_scalar_input_returns_zero_dimensional_arrays():
    res = MemoryUncertainty(components=("rounding",), round_step=2.0).evaluate(1000.0)
    assert res.value.shape == ()
    assert float(res.left) == pytest.approx(1.0)
    assert float(res.right) == pytest.approx(1.0)


def test_vector_input_shape_is_preserved():
    x = np.arange(1.0, 6.0) * 1e6
    res = MemoryUncertainty(components=("instrument",)).evaluate(x)
    assert res.left.shape == x.shape
    assert np.allclose(res.left, 0.01 * x)


def test_rounding_and_storage_are_symmetric_and_exact():
    res = MemoryUncertainty(components=("rounding", "storage"), round_step=8.0, page_size=4096.0).evaluate(
        np.array([10.0, 20.0])
    )
    assert np.allclose(res.left, 4.0 + 2048.0)
    assert np.allclose(res.right, res.left)
    assert res.symmetric.all()


def test_definition_is_one_sided_and_sampling_is_asymmetric():
    m = MemoryUncertainty(components=("definition",), shared_fraction=0.1)
    res = m.evaluate(np.array([100.0, 300.0]))
    assert np.allclose(res.left, [10.0, 30.0])
    assert np.allclose(res.right, 0.0)
    assert not res.symmetric.any()


def test_sampling_peak_gives_left_bound_and_trough_gives_right_bound():
    m = MemoryUncertainty(components=("sampling",), sampling_factor=1.0)
    peak = m.evaluate(np.array([100.0, 500.0, 100.0]))
    assert peak.left[1] == pytest.approx(400.0)
    assert peak.right[1] == pytest.approx(0.0)
    trough = m.evaluate(np.array([500.0, 100.0, 500.0]))
    assert trough.left[1] == pytest.approx(0.0)
    assert trough.right[1] == pytest.approx(400.0)


def test_sampling_scalar_requires_neighbours():
    with pytest.raises(ValueError, match="neighbours"):
        MemoryUncertainty(components=("sampling",)).evaluate(10.0)


def test_sampling_scalar_with_neighbours_works():
    res = MemoryUncertainty(components=("sampling",), sampling_factor=0.5).evaluate(
        10.0, neighbours=(4.0, 30.0)
    )
    # min(4, 30) = 4: левая граница 0,5 * (10 - 4) = 3; правая 0,5 * (30 - 10) = 10
    assert float(res.left) == pytest.approx(3.0)
    assert float(res.right) == pytest.approx(10.0)


def test_time_component_needs_timestamp_or_slope():
    with pytest.raises(ValueError, match="timestamp или slope"):
        MemoryUncertainty(components=("time",)).evaluate(np.array([1.0, 2.0]))


def test_time_component_uses_gradient_of_series():
    t = np.array([0.0, 1.0, 2.0])
    x = np.array([100.0, 200.0, 300.0])
    m = MemoryUncertainty(components=("time",), clock_jitter_s=0.5, read_latency_s=0.0)
    res = m.evaluate(x, timestamp=t)
    # jitter 0,5 с умножается на наклон 100 байт/с: полуширина 50 байт
    assert np.allclose(res.left, 50.0)


def test_float_component_depends_on_dtype():
    x = np.array([2.0**20])
    f32 = MemoryUncertainty(components=("float",), dtype="float32").evaluate(x)
    f64 = MemoryUncertainty(components=("float",), dtype="float64").evaluate(x)
    assert f32.left[0] == pytest.approx(2.0**20 * 2.0**-24)
    assert f64.left[0] == pytest.approx(2.0**20 * 2.0**-53)


@pytest.mark.parametrize("formula", FORMULAS)
def test_each_formula_is_bounded_by_linear_sum(formula):
    x = np.array([1e8, 2e8, 3e8])
    t = np.array([0.0, 1.0, 2.0])
    lin = MemoryUncertainty(formula="linear").evaluate(x, timestamp=t)
    res = MemoryUncertainty(formula=formula).evaluate(x, timestamp=t)
    assert np.all(res.left <= lin.left + 1e-9)
    assert np.all(res.right <= lin.right + 1e-9)


def test_gum_uses_rectangular_divisor():
    res = MemoryUncertainty(components=("rounding",), formula="gum", round_step=2.0).evaluate(5.0)
    assert float(res.left) == pytest.approx(1.0 / math.sqrt(3.0))


def test_gum_uses_normal_divisor_for_instrument():
    res = MemoryUncertainty(components=("instrument",), formula="gum", instrument_rel=0.02, normal_k=2.0)
    out = res.evaluate(np.array([1000.0]))
    assert out.left[0] == pytest.approx(0.02 * 1000.0 / 2.0)


def test_rss_is_root_of_squares():
    m = MemoryUncertainty(components=("rounding", "storage"), formula="rss", round_step=2.0, page_size=6.0)
    res = m.evaluate(np.array([7.0]))
    assert res.left[0] == pytest.approx(math.sqrt(1.0**2 + 3.0**2))


def test_components_subset_is_respected_and_reported():
    res = MemoryUncertainty(components=("instrument", "float")).evaluate(np.array([1e6]))
    assert set(res.components) == {"instrument", "float"}


def test_default_uses_all_components():
    res = MemoryUncertainty().evaluate(np.array([1e9, 1e9 + 1e6]), timestamp=np.array([0.0, 1.0]))
    assert set(res.components) == set(COMPONENTS)
    assert np.all(res.left > 0)


def test_result_bounds_and_to_dict():
    res = MemoryUncertainty(components=("rounding",), round_step=4.0).evaluate(np.array([10.0]))
    assert res.lower[0] == pytest.approx(8.0)
    assert res.upper[0] == pytest.approx(12.0)
    d = res.to_dict()
    assert d["formula"] == "linear"
    assert d["value"] == [10.0]
