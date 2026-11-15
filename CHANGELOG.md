# Changelog

## 0.0.3 (2026-11-16)

Version 0.0.2 was tagged on GitHub with the 0.0.1 version number inside the package; 0.0.3 aligns the tag, the package and PyPI.


- Formula `gum_shift`: gum with the mean shift b/2 and variance b^2/12 of the one-sided definition component. Existing formulas are unchanged. Three tests added (40 in total).

## 0.0.1 (2026-11-13)

- First release. Seven uncertainty components (instrument, storage, time, sampling, rounding, float, definition).
- Combination formulas `linear`, `rss`, `gum` as a parameter.
- Asymmetric left and right half-widths for each point.
- Input validators for types, shapes, signs, ranges and names.
- Tests for Python 3.11 to 3.14, bilingual README and docs.
