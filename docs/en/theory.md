# Model of the measurement uncertainty

Let `x_i` be the reading of memory of a virtual machine at moment `t_i`. For each reading the library gives a left half-width `L_i` and a right half-width `R_i`, so that the true value of the quantity lies in `[x_i - L_i, x_i + R_i]` under the assumptions of the components.

## Components

1. **instrument**. The reader of the counter has a relative accuracy `r`. Half-width `r·x_i`, normal distribution with coverage `k`.
2. **storage**. The counter is kept in memory pages of size `P`. A partly used page can be counted either way, so the half-width is `P/2`, uniform distribution.
3. **time**. The reading is attached to the moment `t_i`. A clock jitter `δ` and half of the read latency `τ` shift the moment by `δ + τ/2`. Half-width `|s_i|·(δ + τ/2)`, where `s_i` is the slope `dx/dt` (central differences of the series or a given slope).
4. **sampling**. The sample may miss a local peak or trough. With neighbours `p_i` and `n_i` the one-sided bounds are `L_i = c·max(0, x_i - min(p_i, n_i))` and `R_i = c·max(0, max(p_i, n_i) - x_i)`, where `c` is `sampling_factor`. A local peak gets a left bound, a local trough a right bound.
5. **rounding**. The value is written with step `q`, half-width `q/2`, uniform distribution.
6. **float**. The stored value has a relative error at most the unit roundoff `u` of the type: `2^-11` for float16, `2^-24` for float32, `2^-53` for float64. Half-width `u·x_i`, uniform distribution.
7. **definition**. If a part `f` of the value is shared memory, the private part lies in `[x_i·(1 - f), x_i]`. Left half-width `f·x_i`, right half-width zero.

## Combination

Let `L_i^(j)` and `R_i^(j)` be the bounds of component `j` and `d_j` the divisor of its distribution (`√3` for uniform, `k` for normal):

* `linear`: `L_i = Σ_j L_i^(j)`, `R_i = Σ_j R_i^(j)`;
* `rss`: `L_i = sqrt(Σ_j (L_i^(j))²)`, `R_i = sqrt(Σ_j (R_i^(j))²)`;
* `gum`: `L_i = c_cov·sqrt(Σ_j (L_i^(j)/d_j)²)`, same for `R_i`, with `c_cov` the coverage factor.

The default values of `instrument_rel` and `clock_jitter_s` are placeholders and must be replaced by values calibrated on the test bench.
