# API reference (iput-memerr 0.0.1)

## `MemoryUncertainty(components, formula, **parameters)`

| Parameter | Default | Meaning |
|---|---|---|
| `components` | all seven | components to include, a subset of `COMPONENTS` |
| `formula` | `"linear"` | `linear`, `rss` or `gum` |
| `instrument_rel` | `0.01` | relative accuracy of the measuring system (assumed, calibrate on a bench) |
| `normal_k` | `2.0` | divisor for normal components in `gum` (2 means 95 % coverage) |
| `page_size` | `4096.0` | bytes per memory page, granularity of the stored counter |
| `clock_jitter_s` | `0.001` | clock jitter in seconds (assumed) |
| `read_latency_s` | `0.0` | counter read time in seconds, contributes half of its value |
| `round_step` | `1.0` | rounding step of the stored value in bytes |
| `dtype` | `"float64"` | storage type: `float16`, `float32` or `float64` |
| `shared_fraction` | `0.0` | fraction of shared pages counted in the value |
| `sampling_factor` | `0.5` | share of the neighbour spread turned into the sampling bound |
| `coverage` | `1.0` | coverage factor for `gum` |

## `evaluate(value, *, timestamp=None, slope=None, neighbours=None)`

* `value`: number or 1-D vector of memory readings in bytes. Non-finite and negative values raise `ValueError`.
* `timestamp`: moments of readings in seconds, same shape, strictly increasing for a vector. Needed by `time` unless `slope` is given.
* `slope`: derivative of memory with respect to time in bytes per second, same shape.
* `neighbours`: pair `(previous, next)` of arrays of the same shape. For a vector the neighbours come from the series with the edges repeated. For a scalar they are required by `sampling`.

Returns `UncertaintyResult` with fields `value`, `left`, `right`, `components` (mapping from the name to `(left, right)`), `formula`, and properties `lower`, `upper`, `symmetric`, and method `to_dict()`.

## Errors

* `TypeError`: a non-numeric input or a boolean parameter.
* `ValueError`: wrong shape, negative or non-finite values, unknown component or formula, out-of-range parameter, missing timestamp or neighbours for an enabled component.
