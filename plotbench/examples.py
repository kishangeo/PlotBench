"""Example data sets (Help > Example Data, and 'Open example data' in the Plot Gallery).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Each example: a CSV in plotbench/examples (synthetic values), the column roles to set, units, and the plot types it shows,
with the columns each plot uses. open_example() loads it into a new workbook and draws the chosen plot.
"""
from pathlib import Path

import numpy as np
import pandas as pd

FOLDER = Path(__file__).parent / "examples"
CMAP = {"cmap": "jet", "reverse": False, "vmin": None, "vmax": None, "log": False, "levels": 0, "ms": 9.0, "edge": "black", "edge_w": 1.0,
        "alpha": 1.0, "cbar": "right", "legend_loc": "best", "hollow_legend": True, "lw": 2.5, "label": None, "size": None, "group": None}

# key: (title, file, description, roles {column: role}, plots {plot type: (x, [ys], extra)}, default plot)
EXAMPLES = {
    "colour_map": ("Colour-mapped scatter (3 variables)", "bridgmanite_colour_map.csv",
                   "Unit-cell volume against Fe3+/ΣFe, coloured by Al content, with a symbol per experimental run.",
                   {"Sample": "Label", "Volume (A3)": "X", "Fe3+/SumFe": "Y", "Al (pfu)": "Y", "Run": "Label", "Fe3+ error": "yErr"},
                   {"Color-mapped Scatter": ("Volume (A3)", ["Fe3+/SumFe", "Al (pfu)"], {**CMAP, "group": "Run", "cbar_label": "Al (pfu)"}),
                    "Bubble + Color": ("Volume (A3)", ["Fe3+/SumFe", "Al (pfu)"], {**CMAP, "size": "Fe3+ error", "cbar_label": "Al (pfu)"}),
                    "Color-mapped Line": ("Volume (A3)", ["Fe3+/SumFe", "Al (pfu)"], {**CMAP, "cbar_label": "Al (pfu)"}),
                    "Bubble": ("Volume (A3)", ["Fe3+/SumFe", "Al (pfu)"], {})}, "Color-mapped Scatter"),
    "raman": ("Raman spectrum (peaks and baseline)", "raman_spectrum.csv",
              "One spectrum with three peaks on a sloping background: try Spectroscopy > Peak Analyzer and the baselines.",
              {"Raman shift (cm-1)": "X", "Intensity (counts)": "Y"},
              {"Line": ("Raman shift (cm-1)", ["Intensity (counts)"], {}), "Drop Line (Stem)": ("Raman shift (cm-1)", ["Intensity (counts)"], {})}, "Line"),
    "raman_T": ("Spectra at several temperatures", "raman_temperature_series.csv",
                "Five spectra sharing one X column: waterfall and stacked panels.",
                {"Raman shift (cm-1)": "X"}, {"Waterfall (offset curves)": ("Raman shift (cm-1)", None, {}),
                                              "Stacked Panels (shared X)": ("Raman shift (cm-1)", None, {})}, "Waterfall (offset curves)"),
    "trace": ("Trace elements for spider diagrams", "trace_elements_ppm.csv",
              "Eight samples (rows) with REE and other trace elements in ppm (columns named after the elements). One Tm value is '<0.05'.",
              {"Sample": "X", "Rock": "Label"}, {k: ("Sample", None, {}) for k in (
                  "Spider: REE / CI Chondrite", "Spider: REE / Primitive Mantle", "Spider: Multi-element / Primitive Mantle",
                  "Spider: Multi-element / N-MORB", "Spider: Multi-element / CI Chondrite", "Spider: REE / PAAS (sediments)")},
              "Spider: REE / CI Chondrite"),
    "oxides": ("Major oxides (TAS, AFM, Harker)", "major_oxides_wt.csv", "A volcanic series from basalt to rhyolite, oxides in wt%.",
               {"Sample": "X"}, {"TAS (SiO2 vs Na2O+K2O)": ("SiO2", ["Na2O", "K2O"], {}),
                                 "AFM (Irvine & Baragar)": (None, ["Na2O", "K2O", "FeOt", "MgO"], {}),
                                 "Frost: Fe-number vs SiO2": (None, ["SiO2", "FeOt", "MgO"], {}),
                                 "Frost: MALI vs SiO2": (None, ["SiO2", "Na2O", "K2O", "CaO"], {}),
                                 "Shand A/CNK vs A/NK": (None, ["Al2O3", "CaO", "Na2O", "K2O"], {}),
                                 "Harker Diagrams (oxides vs SiO2)": ("SiO2", ["TiO2", "Al2O3", "FeOt", "MgO", "CaO", "Na2O", "K2O"], {}),
                                 "Heat Map": ("Sample", ["TiO2", "FeOt", "MgO", "CaO", "Na2O", "K2O"], {}),
                                 **{k: (None, ["SiO2", "TiO2", "Al2O3", "FeOt", "MgO", "CaO", "Na2O", "K2O"], {}) for k in ("PCA Biplot (scores + loadings)",
                                    "PCA Scores (samples)", "PCA Loadings (correlation circle)", "PCA Scree Plot")},
                                 "Scatter Matrix": (None, ["SiO2", "MgO", "CaO", "K2O"], {}),
                                 "Dendrogram (cluster rows)": ("Sample", ["SiO2", "MgO", "CaO", "Na2O", "K2O"], {"method": "ward"})},
               "TAS (SiO2 vs Na2O+K2O)"),
    "qap": ("Modal Q-A-P (Streckeisen)", "qap_modes.csv", "Modal quartz, alkali feldspar and plagioclase of granitoids.",
            {"Sample": "Label", "Q": "X"}, {"QAP (Streckeisen)": ("Q", ["A", "P"], {})}, "QAP (Streckeisen)"),
    "feldspar": ("Feldspar compositions (An-Ab-Or)", "feldspar_compositions.csv", "Plagioclase and alkali-feldspar analyses in mol% end-members.",
                 {"Analysis": "Label", "Ab": "X"}, {"Feldspar Ternary (An-Ab-Or)": ("Ab", ["Or", "An"], {})}, "Feldspar Ternary (An-Ab-Or)"),
    "granite": ("Granite trace elements (Pearce diagrams)", "granite_trace_elements.csv",
                "Rb, Y, Nb, Yb and Ta (ppm) of granites from different settings, for the four Pearce et al. (1984) diagrams.",
                {"Sample": "Label", "Setting": "Label"},
                {k: (None, ["Rb", "Y", "Nb", "Yb", "Ta"], {}) for k in ("Pearce Granite: Rb vs Y+Nb", "Pearce Granite: Nb vs Y",
                                                                       "Pearce Granite: Rb vs Yb+Ta", "Pearce Granite: Ta vs Yb")},
                "Pearce Granite: Rb vs Y+Nb"),
    "pyroxene": ("Pyroxene microprobe analyses (Wo-En-Fs)", "pyroxene_epma_oxides.csv",
                 "Oxide wt% of augites, pigeonites and orthopyroxenes. Opening it runs Column > Mineral Formula (pyroxene, 6 O, Fe3+ by "
                 "charge balance) and plots Wo-En-Fs on the quadrilateral.",
                 {"Analysis": "Label"}, {"Pyroxene Quadrilateral (Wo-En-Fs)": ("Wo", ["En", "Fs"], {})}, "Pyroxene Quadrilateral (Wo-En-Fs)"),
    "ultramafic": ("Ultramafic rock modes (Ol-Opx-Cpx)", "ultramafic_modes.csv", "Modal olivine, orthopyroxene and clinopyroxene in %.",
                   {"Sample": "Label", "Ol": "X"}, {"Ultramafic Ol-Opx-Cpx (IUGS)": ("Ol", ["Opx", "Cpx"], {})}, "Ultramafic Ol-Opx-Cpx (IUGS)"),
    "soil": ("Soil texture (USDA)", "soil_texture.csv", "Sand, silt and clay percentages of soil samples.",
             {"Sample": "Label", "Sand (%)": "X"}, {"Soil Texture (USDA)": ("Sand (%)", ["Silt (%)", "Clay (%)"], {})}, "Soil Texture (USDA)"),
    "ternary": ("Mineral modes (ternary)", "ternary_mineral_modes.csv", "Olivine, pyroxene and plagioclase modes, with MgO for colour.",
                {"Olivine": "X"}, {"Ternary": ("Olivine", ["Pyroxene", "Plagioclase"], {}),
                                   "Ternary + Color": ("Olivine", ["Pyroxene", "Plagioclase", "MgO (wt%)"], {**CMAP, "cbar_label": "MgO (wt%)"}),
                                   "Ternary Contour": ("Olivine", ["Pyroxene", "Plagioclase", "MgO (wt%)"], {}),
                                   "Ternary Density (KDE contours)": ("Olivine", ["Pyroxene", "Plagioclase"], {})}, "Ternary"),
    "water": ("Water chemistry (Piper)", "water_chemistry_mgL.csv",
              "Major ions in mg/L. Opening it converts them to meq/L (Column > Convert Ions) and draws the Piper diagram.",
              {"Sample": "Label"}, {"Piper Diagram": ("Ca (meq/L)", ["Mg (meq/L)", "Na+K (meq/L)", "Cl (meq/L)", "SO4 (meq/L)", "HCO3+CO3 (meq/L)"], {})},
              "Piper Diagram"),
    "calibration": ("Calibration with error bars", "calibration_with_errors.csv",
                    "Standards with their SD set as yErr, so scatter plots show error bars. Try Analysis > Fitting.",
                    {"Concentration (ppm)": "X", "Absorbance": "Y", "Absorbance SD": "yErr"},
                    {"Scatter": ("Concentration (ppm)", ["Absorbance"], {}), "Line + Symbol": ("Concentration (ppm)", ["Absorbance"], {}),
                     "Error Bar": ("Concentration (ppm)", ["Absorbance", "Absorbance SD"], {}),
                     "Semi-log Y (Line + Symbol)": ("Concentration (ppm)", ["Absorbance"], {}),
                     "Scatter + Marginal Histograms": ("Concentration (ppm)", ["Absorbance"], {})}, "Scatter"),
    "groups": ("Three groups (box plots, ANOVA)", "groups_three_samples.csv", "Three groups of different sizes, one column each.",
               {}, {k: (None, None, extra) for k, extra in (("Box", {}), ("Box + Data Points", {}), ("Violin", {}), ("Histogram", {}),
                                                            ("Histogram + Normal Curve", {}), ("Q-Q Plot", {"dist": "norm"}),
                                                            ("Normal Probability", {}), ("Cumulative Probability", {}))}, "Box + Data Points"),
    "time": ("Time series (two quantities)", "time_series_two_quantities.csv", "Temperature and humidity every minute.",
             {"Time (min)": "X"}, {k: ("Time (min)", None, {}) for k in ("Line", "Step", "Step (post, survival)", "Area", "Stacked Area",
                                                                         "Double-Y", "Stacked Panels (shared X)")}, "Double-Y"),
    "xyz": ("Scattered X, Y, Z", "scattered_xyz.csv", "400 scattered points of a smooth surface.",
            {"X": "X"}, {"Contour (XYZ)": ("X", ["Y", "Z"], {}), "3D Scatter": ("X", ["Y", "Z"], {}), "3D Surface": ("X", ["Y", "Z"], {}),
                         "2D Kernel Density": ("X", ["Y"], {})}, "Contour (XYZ)"),
    "path3d": ("Path in 3-D", "path_3d.csv", "A spiral of 80 points in row order.", {"X": "X"}, {"3D Line (path)": ("X", ["Y", "Z"], {})}, "3D Line (path)"),
    "grid3d": ("Grid with heights and vectors (3-D)", "grid_heights_vectors.csv", "A 5 x 4 grid: height Z and a vector (U, V, W) at each point.",
               {"X": "X"}, {"3D Bars": ("X", ["Y", "Z"], {}), "3D Vectors": ("X", ["Y", "Z", "U", "V", "W"], {})}, "3D Bars"),
    "categories": ("Categories (columns, bars, pie)", "categories_with_errors.csv", "Five sites, two years, with standard deviations.",
                   {"Site": "X", "SD 2023": "yErr", "SD 2024": "yErr"},
                   {"Column": ("Site", ["2023", "2024"], {}), "Bar (horizontal)": ("Site", ["2023", "2024"], {}),
                    "Stacked Column": ("Site", ["2023", "2024"], {}), "Column + Error Bars": ("Site", ["2023", "SD 2023", "2024", "SD 2024"], {}),
                    "Pareto Chart": ("Site", ["2023"], {}), "Pie": ("Site", ["2024"], {}), "Radar / Spider": ("Site", ["2023", "2024"], {})}, "Column"),
    "repeated": ("Repeated measures (mixed models)", "repeated_measures_long.csv",
                 "Long format: one row per subject per week. Use Statistics > Regression and Models > Linear Mixed Model.",
                 {"Subject": "Label", "Group": "Label", "Week": "X", "Score": "Y"}, {"Scatter": ("Week", ["Score"], {})}, "Scatter"),
    "survival": ("Survival times", "survival_times.csv", "Times with an event flag (0 = censored). Use Statistics > Survival > Kaplan-Meier.",
                 {"Group": "Label"}, {}, None),
    "wind": ("Wind direction and speed", "wind_direction_speed.csv", "400 observations.", {"Direction (deg)": "X", "Speed (m/s)": "Y"},
             {"Wind Rose": ("Direction (deg)", ["Speed (m/s)"], {}), "Polar (theta deg, r)": ("Direction (deg)", ["Speed (m/s)"], {})}, "Wind Rose"),
    "flows": ("Material flows (Sankey)", "sankey_flows.csv", "From, To and Amount columns.", {"From": "Label", "To": "Label"},
              {"Sankey (flows)": ("From", ["Amount (kt)"], {"src": "From", "dst": "To", "val": "Amount (kt)"})}, "Sankey (flows)"),
    "methods": ("Two methods (Bland-Altman)", "method_comparison.csv", "The same 30 samples measured by two methods.",
                {"Method A": "X", "Method B": "Y"}, {"Bland-Altman": ("Method A", ["Method B"], {})}, "Bland-Altman"),
    "basalts": ("Oceanic and arc basalts (Pearce 2008)", "basalt_th_nb_yb.csv", "Th, Nb, Yb (ppm) and TiO2 (wt%) of MORB, OIB and arc basalts.",
                {"Sample": "X", "Setting": "Label"}, {"Pearce 2008: Th/Yb vs Nb/Yb": ("Sample", ["TiO2", "Nb", "Th", "Yb"], {}),
                                                     "Pearce 2008: TiO2/Yb vs Nb/Yb": ("Sample", ["TiO2", "Nb", "Th", "Yb"], {})}, "Pearce 2008: Th/Yb vs Nb/Yb"),
    "isochron": ("Rb-Sr isochron (geochronology)", "rbsr_isochron.csv", "Whole-rock ratios with 1-sigma errors. Also try Analysis > Geochronology > Isochron Age.",
                 {"Sample": "Label", "87Rb/86Sr": "X"}, {"Isochron (York regression)": ("87Rb/86Sr", ["87Sr/86Sr", "1s 87Rb/86Sr", "1s 87Sr/86Sr"], {"system": "Rb-Sr"})},
                 "Isochron (York regression)"),
    "zircon": ("Zircon U-Pb (concordia)", "zircon_upb.csv", "U-Pb ratios with 1-sigma errors and rho; Analysis > Geochronology > U-Pb Ages adds the ages.",
               {"Spot": "Label", "207Pb/235U": "X"}, {"Concordia (Wetherill)": ("207Pb/235U", ["206Pb/238U", "1s 207/235", "1s 206/238", "rho"], {}),
                                                     "Concordia (Tera-Wasserburg)": ("238U/206Pb", ["207Pb/206Pb", "1s 238/206", "1s 207/206"], {}),
                                                     "Weighted Mean (ages)": ("Spot", ["Age 206/238 (Ma)", "1s age (Ma)"], {})}, "Concordia (Wetherill)"),
    "detrital": ("Detrital zircon ages", "detrital_zircon_ages.csv", "Two samples of detrital ages for density and cumulative plots.", {},
                 {"Detrital Age KDE + PDP": (None, ["Sample A (Ma)", "1s A (Ma)"], {}), "Cumulative Age Distribution": (None, ["Sample A (Ma)", "Sample B (Ma)"], {}),
                  "Raincloud (violin + box + points)": (None, ["Sample A (Ma)", "Sample B (Ma)"], {})}, "Detrital Age KDE + PDP"),
}


def for_plot(kind):
    """The example that demonstrates a plot type, or None."""
    return next((k for k, e in EXAMPLES.items() if kind in e[4]), None)


def load(key):
    title, fn, desc, roles, plots, default = EXAMPLES[key]
    df = pd.read_csv(FOLDER / fn, comment="#")
    for c in df.columns:  # mixed columns (a '<0.05' among numbers) keep the text, numbers stay numbers
        if df[c].dtype == object:
            num = pd.to_numeric(df[c], errors="coerce")
            if num.notna().sum() > df[c].notna().sum() / 2: df[c] = [v if pd.isna(n) else float(n) for v, n in zip(df[c], num)]
    return df


def open_example(main, key, kind=None):
    """New workbook with the example (roles and units set); draws kind (or the example's main plot). Returns the graph or book."""
    title, fn, desc, roles, plots, default = EXAMPLES[key]
    df = load(key); b = main.new_book(df, Path(fn).stem); sh = b.current()
    sh.desig = {c: roles.get(c, "Y") for c in df.columns}
    for c in df.columns:
        if "(" in str(c) and str(c).endswith(")"): sh.meta.setdefault(c, {})["Units"] = str(c)[str(c).rindex("(") + 1:-1]
    sh.meta.setdefault(df.columns[0], {})["Comments"] = desc
    if key == "water": main.ions_water_example(sh)
    if key == "pyroxene":
        main.mineral_formula(sh, "Pyroxene"); sh.desig.update({c: ("X" if c == "Wo" else "Y" if c in ("En", "Fs") else "Ignore") for c in sh.df.columns if c != "Analysis"})
    sh.model.refresh()
    kind = kind or default
    if not kind or kind not in plots: return b
    x, ys, extra = plots[kind]
    if ys is None: ys = [c for c in sh.df.columns if sh.desig.get(c) == "Y" and c != x]
    extra = dict(extra)
    return main.new_graph(sh, kind, x, ys, extra)


def _demo():
    """Every example file loads and every listed column exists."""
    for k, (title, fn, desc, roles, plots, default) in EXAMPLES.items():
        df = load(k); assert len(df) > 2, k
        for c in roles: assert c in df.columns, (k, c)
        for kind, (x, ys, extra) in plots.items():
            for c in [x] + list(ys or []):
                assert c is None or c in df.columns or "(meq/L)" in str(c) or k == "pyroxene", (k, kind, c)
    assert for_plot("QAP (Streckeisen)") == "qap" and for_plot("Image / Heat Map") is None
    print("EXAMPLES OK", len(EXAMPLES))


if __name__ == "__main__": _demo()
