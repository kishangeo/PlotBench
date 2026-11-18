# PlotBench tutorials

Author: Kishan Tiwari (kishantiwari@iitkgp.ac.in)

Five short how-to guides for typical tasks. Each uses an example data set that ships with the program (**Help > Example Data**), so
you can follow them without your own data. The full reference is the user manual (**Help > User Manual**, F1, or
`docs/PlotBench_User_Manual.pdf`).

## 1. Classify volcanic rocks on a TAS diagram

1. **Help > Example Data > Major oxides (TAS, AFM, Harker)**. A workbook opens with oxides in wt% and a finished TAS diagram.
2. To do it with your own data: **File > Import Wizard**, **File > Import Excel**, or paste from Excel. Name the columns `SiO2`, `Na2O`, `K2O` and so on; a unit in
   brackets, such as `SiO2 (wt%)`, is fine.
3. Click the `SiO2` header, Ctrl-click `Na2O` and `K2O`, then **Plot > Geochemistry > TAS**.
4. To leave an analysis out, select its cells and press Ctrl+M (**Column > Mask Selected Cells**). The masked point turns into a red cross on every graph of that sheet.
5. **File > Export Graph / Layout**: choose a journal column width and a format (PDF, SVG, TIFF or PNG).

Input: oxide columns in wt%. Output: a graph window, redrawn whenever the sheet or its masks change.

## 2. Temperature from Ti in zircon, with calibration check and uncertainty

1. Enter Ti concentrations in a column named `Ti (ppm)`.
2. **Analysis > Petrology / Thermobarometry > Thermobarometry...** and choose **Ti-in-zircon (Ferry & Watson 2007)**.
3. The dialog shows the equation, the reference and the calibration range (580 to 1070 °C). Set the activities of SiO2 and TiO2.
4. Tick **Monte Carlo uncertainty**, give the relative analytical error (for example 5 %) and the number of draws.
5. Click OK. Three columns are added: the temperature, `... in calibration range` (yes or no for each row) and `1s ...` (the Monte
   Carlo standard deviation, which is drawn as error bars when you plot the temperature).
6. Hover over the new column header to see how it was calculated: method, equation, inputs and reference.

The 1σ column holds the analytical part of the uncertainty only. Combine it with the calibration error given in the method notes.

## 3. Pressure and temperature together (coupled solver)

1. Open `validation/data/cpx_liquid_example.csv` (**File > Quick Import CSV / TXT**): the liquid and clinopyroxene of the worked example
   of Putirka (2008, Tables 1 and 3). In your own sheet, name the clinopyroxene columns `Cpx SiO2`, `Cpx Al2O3`, ... and the liquid
   (glass or whole rock) columns `SiO2`, `Al2O3`, ...
2. **Analysis > Petrology / Thermobarometry > Coupled P-T Solver...**
3. Choose a thermometer that needs P and a barometer that needs T, for example Putirka (2008) Eq 33 with Eq 31.
4. Click OK. PlotBench iterates T = f(P), P = f(T) from 10 kbar until P changes by less than 0.01 kbar. Rows that do not converge are
   left blank.
5. Check equilibrium first with **Clinopyroxene-liquid KD(Fe-Mg) equilibrium test**: it adds an `in equilibrium` column.

## 4. U-Pb concordia age with a discordance filter

1. **Help > Example Data > Zircon U-Pb (concordia)**. Columns hold the ratios, their 1σ errors and the error correlation.
2. **Analysis > Geochronology > U-Pb Ages and Discordance of Each Analysis** adds the three ages and the discordance.
3. **Analysis > Geochronology > Discordance Filter...**: choose how discordance is measured (Auto switches at 1000 Ma) and a limit.
   Discordant analyses are masked, not deleted.
4. **Plot > Geochronology > Concordia (Wetherill)**. The concordia age and weighted mean now use the concordant analyses only.
5. For common Pb, **Analysis > Geochronology > Common-Pb Correction...** (204Pb, 207Pb or 208Pb method).

## 5. Fit peaks in a Raman spectrum

1. **Help > Example Data > Raman spectrum (peaks and baseline)**.
2. **Analysis > Peak Analyzer...** Choose a baseline, find peaks, pick a shape for each peak and fit.
3. The fitted centres, heights, widths and areas are written to a report and the fitted curves to new columns.

## Reproducing the numbers in the PlotBench paper

From the repository root, with the packages in `requirements.txt` installed:

```bash
python validation/validate.py
```

```bash
python validation/paper_figures.py
```

The first writes `VALIDATION.md` (the benchmark table) and exits with an error if any graded benchmark fails. The second writes the
validation and Monte Carlo figures and `facts.json` (recovery statistics and timings) to `validation/paper/`. The experimental
compositions used are in `validation/data/` and inside `plotbench/thermobaro.py` (`BREY_RUNS`), each with its literature source.

```bash
python -m unittest discover -s tests -v
```

runs the regression tests.
