# iput-memerr

Asymmetric uncertainty estimates for memory consumption measurements of virtual machines.

Русская версия: [README.ru.md](README.ru.md). Documentation: [docs/en](docs/en/api.md), [docs/ru](docs/ru/api.md).

## What it does

The library takes a number or a vector of memory readings (bytes) and returns, for each reading, a left and a right half-width of its uncertainty. The left and right parts can differ. Seven components of the measurement uncertainty are modelled separately, each with its justification in the docs:

| Component | Source of error | Shape of the bound |
|---|---|---|
| `instrument` | accuracy of the measuring system (reader of the counter) | symmetric, relative |
| `storage` | granularity of the stored counter (memory pages) | symmetric, absolute |
| `time` | clock jitter and read latency, times the local slope | symmetric, depends on slope |
| `sampling` | the sample may miss a peak or a trough of the series | asymmetric, from neighbours |
| `rounding` | rounding of the value at writing | symmetric, absolute |
| `float` | floating-point representation (float16, float32, float64) | symmetric, relative |
| `definition` | shared pages counted in the value but not owned by the VM | one-sided |

Parameters choose the components to include (`components`) and the rule that combines them (`formula`): `linear` (sum of bounds), `rss` (root of sum of squares) and `gum` (root of sum of standard uncertainties, JCGM 100). Components can be switched on and off one by one to study their contribution.

## Installation

```bash
pip install iput-memerr
```

Requires Python 3.11 to 3.14 and NumPy 2.0 or newer.

## Quick start

```python
import numpy as np
from iput_memerr import MemoryUncertainty

values = np.array([512e6, 530e6, 498e6])          # bytes
times = np.array([0.0, 1.0, 2.0])                 # seconds

model = MemoryUncertainty(components=("instrument", "sampling", "float"), formula="rss")
res = model.evaluate(values, timestamp=times)
print(res.lower, res.upper)                       # bounds per point
print(res.symmetric)                              # False where left != right
```

A scalar works the same way; the sampling component then needs the neighbours of the reading:

```python
res = MemoryUncertainty(components=("sampling",)).evaluate(512e6, neighbours=(500e6, 520e6))
```

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

The package has no continuous integration. Tests were run locally on Python 3.11 to 3.14.

## Citation

See [CITATION.cff](CITATION.cff). Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Authors

- Oleg D. Kazakov, Bryansk State University of Engineering and Technology (author).
- Andrey O. Ferubko, Bryansk State University of Engineering and Technology (contributor).

## License

MIT, see [LICENSE](LICENSE).
