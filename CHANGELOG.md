# Changelog

## 1.30.3 (2026-11-18)

- The words box of the text format bar shows formatting as it will look (bold, italic, subscript, superscript) instead of codes.
  Select any letters in it and press B, I, superscript, subscript or stacked to format only those letters; press again to undo it.
  With nothing selected, B and I act on the whole text.
- Stacked sub- and superscript: select e.g. "2,3+" (or two characters); the first part becomes the subscript, the second the
  superscript.
- The Greek button is now a symbol picker (Ω) with 464 symbols in 11 groups: Greek, maths, relations, arrows, superscript and
  subscript digits, units, chemistry, shapes, numbers and fractions, accented letters, punctuation. Ctrl+G still turns selected
  Latin letters into Greek.
- Bold and italic parts of a text use the graph's font; symbols missing from that font are taken from DejaVu Sans or STIX.
- The Curves list of the graph side panel no longer squeezes its rows when a graph has many curves.
- Fixes from the 1.30.2 audit: the Edit text prompt showed a box instead of ; words typed for a text annotation are kept as an edit
  of the graph (so Reset brings back the original words) and count as one undo step; the graph title and axis titles typed in the text
  bar and in Graph Properties are the same field, so neither hides the other; the selection outline follows a dragged text; the
  calibration-range check uses a temperature column on a one-row sheet too.

## 1.30.2 (2026-11-18)

- Every text of a graph can be formatted on its own: title, axis titles, tick labels (per axis), legend title and entries, field
  names and other plot texts, annotations, colour-bar titles. Click a text to select it (red outline), then use the new text format
  bar under the curve bar: words, font, size, bold, italic, superscript, subscript, stacked sub- and superscript, Greek letters,
  larger and smaller, colour, orientation (angle) and reset. Double-click a text to edit its words. Keys in the words field:
  Ctrl+B, Ctrl+I, Ctrl+= (subscript), Ctrl+Shift+= (superscript), Ctrl+- (stacked), Ctrl+G (Greek), Ctrl+Shift+> and < (size).
  Formats are saved with the project, undoable, and kept in exported figures.
- The left (graph tools) toolbar fits in one column: the drawing tools (line, arrow, rectangle, circle, polygon, freehand) share one
  button, and so do the add-to-graph tools (text, arrow, reference line, confidence ellipse, zoom inset). A click repeats the last
  tool used; the small arrow beside the button lists the others. Icons on that bar are slightly smaller.
- Thermobarometers return a blank instead of -273 C or infinity when an input that goes into a logarithm is zero.
- LaTeX export blanks only masked cells, not whole rows, and writes 5 rather than 5.000 for whole numbers.
- Calibration-range flags use the temperature column when one is chosen; Monte Carlo treats a temperature column as an absolute
  error in degrees (new T +- input) and lists only the P or T errors that the method uses.
- Cell formulas: powers are computed in floating point, so =10^(1000+1) gives #NUM! at once; FACT(TRUE) gives #NUM!.
- Opening a project right after a graph redraw no longer crashes.

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
