# Changelog

## 1.30.1 (2026-11-18)

- Thermobarometry: methods with a published calibration domain add a column flagging rows outside it (or out of equilibrium, for the
  KD tests), and an optional Monte Carlo 1σ column propagates the analytical error of every measured input (and of P, if given).
- `VALIDATION.md` (from `validation/validate.py`) benchmarks the calculations against worked examples printed in the papers and against
  published experiments (Evans et al. 2006 Fe-Ti oxides; Brey et al. 1990 garnet peridotites).
- Opening a project is all or nothing: if any part of the new project fails to build, the previous session is put back as it was.
- LaTeX export: numbers from 0.001 to 1,000,000 in plain notation (12450, not 1.245e+04), masked rows left out, and labels such as
  SpotA1 or (yErr-) no longer typeset as formulae.
- Common-Pb correction: corrected 207Pb*/235U only for the 204Pb and 208Pb methods (the 207Pb method assumes concordance); negative
  corrected ratios are left blank.
- Zircon oxybarometer: zero or blank Ce, U or Ti gives a blank instead of infinity. Graph side-panel arrows follow a theme change.
- Opening a project now asks to save unsaved work first (Save / Discard / Cancel).
- A project file is fully read and checked before the open windows are closed, so a damaged file no longer costs the current session.
  Project files are limited to 4 GB of data and 10,000 parts.
- Text labels such as NA, NULL or nan in a text column stay text after saving and reopening.
- Importing datasets with the same name from different HDF5/NetCDF groups keeps all of them.
- FACT() refuses arguments above 170 (the float limit) instead of freezing; cell formulas are limited to 2,000 characters.
- Release builds run every analysis test and the new regression tests; a test workflow runs on every push.
- macOS app is ad-hoc signed and the disk image includes first-start instructions.
- Website: download links pinned to the release, skip link, keyboard focus, reduced-motion support, clearer install notes.
- Corrected the licence of the pyrolite reference data (MIT) and added THIRD_PARTY_NOTICES.md and SECURITY.md.

## 1.30.0 (2026-11-17)

First public release.
