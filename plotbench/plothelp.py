"""What each plot type shows and how to lay out the worksheet for it (shown in the Plot Gallery and the user manual).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Each entry: (what it shows, how to prepare the data, example columns as rows of a small table, tip or '').
Column roles (X, Y, yErr, Label) are set by right-clicking a column header, or Column > Set as ...
"""

_XY = ("Put the X values in one column set as X, and one or more Y columns next to it. Select the Y columns "
       "(or nothing, to use every Y column) and choose the plot.")
_XY_EX = [["Time (s)", "Signal A", "Signal B"], ["0", "1.02", "0.88"], ["1", "1.35", "0.97"], ["2", "1.61", "1.10"]]
_GROUPS = ("Each column is one group or sample: put the values of group 1 in the first column, group 2 in the next, and so on "
           "(columns can have different lengths). Select the columns to compare.")
_G_EX = [["Control", "Treatment A", "Treatment B"], ["10.2", "12.1", "13.0"], ["9.8", "11.7", "14.2"], ["10.9", "12.6", "13.4"]]
_TERN = ("Three columns with the three components (any units: wt%, mol% or counts; each row is normalised to 100%). "
         "Set the first component as X and the other two as Y; select all three.")
_TERN_EX = [["Olivine (X)", "Pyroxene", "Plagioclase"], ["62", "25", "13"], ["40", "35", "25"], ["15", "30", "55"]]
_MATRIX = ("Needs a matrixbook (a grid of Z values) rather than a worksheet. Make one with Matrix > New Matrixbook, "
           "import an image or grid file, or convert scattered XYZ data with Matrix > Gridding. Make the matrix window "
           "active, then choose the plot.")
_SPIDER = ("One row per sample. Put the sample names in a column set as X (or Label), and one column per element in ppm, "
           "named after the element: La, Ce, Nd ... ('La (ppm)' or 'La_ppm' also work). Columns can be in any order; "
           "they are sorted into the standard order. Text such as '<0.1' or 'bdl' leaves a gap, bridged by a dotted line.")
_SP_EX = [["Sample (X)", "La", "Ce", "Nd", "Sm", "Eu", "Yb"], ["MT-01", "23.1", "48.2", "21.0", "4.6", "1.3", "2.1"],
          ["MT-02", "8.4", "19.9", "11.2", "3.1", "<0.1", "2.4"]]


def _spider(ref, what): return (f"Each sample as a line of element concentrations divided by {ref}, on a log axis. {what}",
                                _SPIDER, _SP_EX, "Add Eu/Eu* or Ce/Ce* columns with the formulas eu_anomaly(Eu, Sm, Gd) and ce_anomaly(Ce, La, Pr).")


HELP = {
    "Line": ("Y against X joined by lines: spectra, time series, profiles.", _XY, _XY_EX, "Several Y columns give several lines with a legend."),
    "Scatter": ("Points without lines: measurements, correlations, calibration data.", _XY, _XY_EX,
                "Set a column as yErr right after a Y column and the error bars are drawn automatically."),
    "Line + Symbol": ("Points joined by lines.", _XY, _XY_EX, "Set a column as yErr right after a Y column for error bars."),
    "Step": ("A staircase line (each value holds until the next X): counts per bin, digital signals.", _XY, _XY_EX, ""),
    "Step (post, survival)": ("A staircase that steps after each X: survival or cumulative curves.", _XY, _XY_EX,
                              "Statistics > Survival > Kaplan-Meier makes this graph for you."),
    "Drop Line (Stem)": ("A vertical line from zero to each point: stick spectra, mass spectra, impulse responses.", _XY,
                         [["m/z (X)", "Intensity"], ["28", "100"], ["32", "27"], ["44", "6"]], ""),
    "Area": ("A line with the area under it filled.", _XY, _XY_EX, ""),
    "Stacked Area": ("Areas stacked on each other, so the top edge is the total: compositions through time or depth.", _XY,
                     [["Depth (X)", "Quartz", "Feldspar", "Clay"], ["0", "40", "35", "25"], ["5", "45", "30", "25"]], ""),
    "Error Bar": ("Points with vertical error bars.",
                  "X column, then pairs of columns: a Y column followed by its error column (Y1, Err1, Y2, Err2 ...). Select the pairs.",
                  [["T (X)", "Rate", "Rate error"], ["300", "1.2", "0.1"], ["350", "2.9", "0.2"], ["400", "6.1", "0.4"]],
                  "Or set the error column as yErr and use Scatter: the bars are attached automatically."),
    "Semi-log Y (Line + Symbol)": ("Line + symbol with a logarithmic Y axis: decay curves, concentrations spanning decades.", _XY, _XY_EX,
                                   "Y values must be positive; zeros and negatives are left out."),
    "Color-mapped Scatter": ("X against Y with each point coloured by a third column (and a colour bar): 3 variables in 2-D, e.g. "
                             "Fe3+/ΣFe against unit-cell volume coloured by Al content.",
                             "X column, a Y column and the colour column; select Y and the colour column. The dialog that opens lets you "
                             "pick the colour map, its range, log scale, symbols per group (from a text column), point labels and the colour-bar title.",
                             [["V (Å³) (X)", "Fe3+/ΣFe", "Al (pfu)", "Run"], ["162.3", "0.42", "0.08", "A"], ["162.9", "0.55", "0.12", "B"]],
                             "Edit plot... on the format bar reopens the dialog later."),
    "Bubble + Color": ("Points sized by one column and coloured by another: 4 variables in one plot.",
                       "X, Y, a colour column and a size column. The dialog asks which column is which.",
                       [["X", "Y", "Colour", "Size"], ["1", "3.2", "0.1", "5"], ["2", "4.1", "0.4", "12"]], ""),
    "Color-mapped Line": ("A line whose colour changes with a third column, e.g. a P-T path coloured by time.",
                          "X, Y and the colour column, in the order the line should be drawn.",
                          [["T (°C) (X)", "P (GPa)", "Time (Ma)"], ["600", "0.8", "0"], ["700", "1.1", "5"]], ""),
    "Bubble": ("Points with size from a third column.", "X column, a Y column, then the size column; select Y and size.",
               [["X", "Y", "Size"], ["1", "2.0", "3"], ["2", "3.5", "8"]], ""),
    "Ternary + Color": ("A ternary diagram with points coloured by a fourth column.", _TERN + " Add a fourth column for the colour and select it too.",
                        [["A (X)", "B", "C", "Colour"], ["60", "30", "10", "1.2"], ["30", "40", "30", "3.4"]], ""),
    "Heat Map": ("A grid of coloured cells: one row per X label, one column per Y column.",
                 "Row labels in the X column and one column per variable. Values are coloured, not plotted as lines.",
                 [["Sample (X)", "SiO2", "MgO", "FeO"], ["A", "48", "9", "11"], ["B", "52", "6", "9"]], ""),
    "Contour (XYZ)": ("Contours of Z over X-Y from scattered points (gridded for you).", "Three columns: X, Y and Z; select Y and Z.",
                      [["X", "Y", "Z"], ["0.1", "2.3", "14"], ["1.4", "0.7", "9"]], "For data already on a regular grid, use a matrixbook."),
    "2D Kernel Density": ("Where points cluster: a smoothed density of X-Y points.", "X and Y columns; select Y.", _XY_EX[:1] + [["0.1", "2.3", ""]], ""),
    "Ternary Density (KDE contours)": ("Where the samples cluster on a ternary diagram: filled contours of their 2D kernel density "
                                       "(Gaussian, Scott bandwidth) behind the points; useful when hundreds of analyses overlap.", _TERN,
                                       [["A", "B", "C"], ["60", "25", "15"]], "Density is computed in the plotted triangle coordinates."),
    "Ternary Contour": ("Contours of a value over a ternary diagram.", _TERN + " A fourth column holds the value to contour.",
                        [["A (X)", "B", "C", "Z"], ["60", "30", "10", "1.2"], ["30", "40", "30", "3.4"]], ""),
    "Column": ("Vertical bars per category; several Y columns give grouped bars.",
               "Category names in the X column (text), values in Y columns.",
               [["Site (X)", "2023", "2024"], ["North", "12", "15"], ["South", "8", "11"]], ""),
    "Bar (horizontal)": ("Horizontal bars per category.", "Category names in X, values in Y columns.",
                         [["Mineral (X)", "Modal %"], ["Olivine", "55"], ["Pyroxene", "30"]], ""),
    "Stacked Column": ("Bars stacked on each other, so the height is the total.", "Categories in X, one Y column per part.",
                       [["Sample (X)", "Qz", "Fsp", "Lith"], ["S1", "60", "25", "15"], ["S2", "45", "30", "25"]], ""),
    "Column + Error Bars": ("Bars with error bars.", "Categories in X, then pairs: value column followed by its error column.",
                            [["Group (X)", "Mean", "SD"], ["A", "4.1", "0.3"], ["B", "5.6", "0.5"]], ""),
    "Pareto Chart": ("Bars sorted from largest to smallest with the cumulative percentage line.", "Categories in X and one column of counts.",
                     [["Defect (X)", "Count"], ["Crack", "42"], ["Void", "17"]], ""),
    "Pie": ("Shares of a whole.", "Labels in X and one Y column of values.", [["Phase (X)", "wt%"], ["Bridgmanite", "75"], ["Ferropericlase", "18"]], ""),
    "Double-Y": ("Two Y columns on separate left and right axes against one X.", "X column and two Y columns; select both Y columns.",
                 [["Time (X)", "Temperature (°C)", "Pressure (GPa)"], ["0", "25", "0.1"], ["10", "800", "5.2"]], ""),
    "Stacked Panels (shared X)": ("One panel per Y column, stacked vertically with a shared X axis.", _XY, _XY_EX, ""),
    "Waterfall (offset curves)": ("Curves shifted upward one after another, e.g. spectra at several temperatures.",
                                  "Shared X (e.g. Raman shift) and one Y column per spectrum.",
                                  [["Shift (cm⁻¹) (X)", "25 °C", "200 °C", "400 °C"], ["200", "12", "14", "15"], ["201", "13", "14", "16"]], ""),
    "Scatter Matrix": ("Every selected column plotted against every other one: quick look at correlations.", "Select three or more numeric columns.",
                       [["SiO2", "MgO", "FeO", "CaO"], ["48", "9", "11", "10"], ["52", "6", "9", "8"]], ""),
    "Scatter + Marginal Histograms": ("A scatter plot with the distribution of X and Y on its edges.", "X column and one Y column.", _XY_EX, ""),
    "Histogram": ("The distribution of values in each column.", "One column per sample; select the columns.", _G_EX,
                  "Bins are chosen automatically; Graph Properties sets the style."),
    "Histogram + Normal Curve": ("Histogram with the fitted normal curve.", "One column of values.", _G_EX, ""),
    "Box": ("Median, quartiles and range of each group side by side.", _GROUPS, _G_EX, ""),
    "Box + Data Points": ("Box plot with every point drawn on top.", _GROUPS, _G_EX, ""),
    "Violin": ("The shape of each group's distribution.", _GROUPS, _G_EX, ""),
    "Q-Q Plot": ("Sample quantiles against a theoretical distribution: points on the line mean the distribution fits.", "One column of values.", _G_EX, ""),
    "Normal Probability": ("Values on a normal probability scale.", "One column of values.", _G_EX, ""),
    "Cumulative Probability": ("The empirical cumulative distribution of each column.", "One column per sample.", _G_EX, ""),
    "Bland-Altman": ("Difference between two methods against their mean, with the bias and limits of agreement.",
                     "Method A in a column set as X, method B in a Y column; one row per sample measured both ways.",
                     [["EPMA (X)", "LA-ICP-MS"], ["1.20", "1.25"], ["2.31", "2.20"]], ""),
    "Dendrogram (cluster rows)": ("A tree that groups similar rows (samples).", "Row labels in X and one column per variable.",
                                  [["Sample (X)", "SiO2", "MgO"], ["A", "48", "9"], ["B", "52", "6"]], ""),
    "Ternary": ("Three components on a triangle, with 0-100% ticks on every edge.", _TERN, _TERN_EX, ""),
    "Piper Diagram": ("Water types: cation and anion triangles and the central diamond.",
                      "Six columns in meq/L, in this order: Ca (set as X), Mg, Na+K, Cl, SO4, HCO3+CO3. A Label column names the samples. "
                      "If your data are in mg/L, use Column > Convert Ions mg/L to meq/L first.",
                      [["Ca (X)", "Mg", "Na+K", "Cl", "SO4", "HCO3+CO3"], ["3.1", "1.2", "0.8", "0.6", "0.9", "3.6"]], ""),
    "Polar (theta deg, r)": ("Radius against angle.", "Angle in degrees as X, radius columns as Y.", [["Angle (X)", "r"], ["0", "1.0"], ["30", "1.4"]], ""),
    "Radar / Spider": ("Each row or column as a polygon across several axes (not the geochemical spider).",
                       "Axis labels in X and one Y column per series.", [["Property (X)", "Sample 1", "Sample 2"], ["Hardness", "6", "4"]], ""),
    "Wind Rose": ("How often each direction and speed occur.", "Direction in degrees as X and speed as Y; one row per observation.",
                  [["Direction (X)", "Speed (m/s)"], ["270", "5.2"], ["250", "3.8"]], ""),
    "Sankey (flows)": ("Flows between stages; band width shows the amount.", "Three columns: source, target and value. The dialog asks which is which.",
                       [["From", "To", "Amount"], ["Mine", "Mill", "100"], ["Mill", "Tailings", "35"]], ""),
    "Spider: REE / CI Chondrite": _spider("CI chondrite (McDonough & Sun 1995)", "Rare earth elements La to Lu."),
    "Spider: REE / Primitive Mantle": _spider("primitive mantle (McDonough & Sun 1995)", "Rare earth elements La to Lu."),
    "Spider: Multi-element / Primitive Mantle": _spider("primitive mantle (McDonough & Sun 1995)", "Trace elements in order of incompatibility (Cs ... Lu)."),
    "Spider: Multi-element / N-MORB": _spider("N-MORB (Sun & McDonough 1989)", "Trace elements in order of incompatibility."),
    "Spider: Multi-element / CI Chondrite": _spider("CI chondrite (McDonough & Sun 1995)", "Trace elements in order of incompatibility."),
    "Spider: REE / PAAS (sediments)": _spider("Post-Archean Australian Shale (Taylor & McLennan 1985)", "For sediments and soils."),
    "TAS (SiO2 vs Na2O+K2O)": ("Total alkali-silica classification of volcanic rocks (Le Bas et al. 1986) with the field names.",
                               "SiO2 in wt% as X, and either one column with Na2O+K2O or two columns Na2O and K2O (they are added). "
                               "Use analyses recalculated to 100% volatile-free.",
                               [["SiO2 (X)", "Na2O", "K2O"], ["49.8", "2.9", "0.6"], ["63.2", "4.1", "2.3"]], ""),
    "QAP (Streckeisen)": ("Classification of plutonic rocks from modal quartz (Q), alkali feldspar (A) and plagioclase (P).",
                          "Q as X, then A and P (modal %, any total; normalised to 100%). Narrow fields are numbered; the key is under the plot.",
                          [["Q (X)", "A", "P"], ["30", "35", "35"], ["5", "60", "35"]], "Only valid when mafic minerals are below 90%."),
    "Feldspar Ternary (An-Ab-Or)": ("Feldspar compositions on the An-Ab-Or triangle with the plagioclase (albite to anorthite) and "
                                    "alkali-feldspar (anorthoclase, K-feldspar) names.",
                                    "Three columns in mol%: Ab, Or and An (from microprobe analyses: Ab = Na, Or = K, An = Ca on a cation basis). "
                                    "Columns named Ab, Or and An are found in any order; otherwise use Ab as X, then Or and An.",
                                    [["Ab (X)", "Or", "An"], ["68.2", "1.1", "30.7"], ["31.5", "62.0", "6.5"]],
                                    "Calculate end-members with a formula, e.g. An = 100*Ca/(Ca + Na + K)."),
    "Pyroxene Quadrilateral (Wo-En-Fs)": ("Ca-Mg-Fe pyroxene compositions on the En-Fs-Di-Hd quadrilateral with the names of Morimoto (1988): "
                                          "diopside, hedenbergite, augite, pigeonite, enstatite, ferrosilite.",
                                          "Three columns in mol%: Wo, En and Fs (Ca, Mg and Fe2+ + Fe3+ + Mn on a cation basis; Column > Mineral "
                                          "Formula gives them from oxide wt%). Named columns are found in any order; otherwise Wo as X, then En and Fs.",
                                          [["Wo (X)", "En", "Fs"], ["44.1", "42.3", "13.6"], ["9.5", "60.2", "30.3"]], ""),
    "Ultramafic Ol-Opx-Cpx (IUGS)": ("IUGS names of ultramafic rocks (dunite, harzburgite, lherzolite, wehrlite, pyroxenites) from modal olivine, "
                                     "orthopyroxene and clinopyroxene.",
                                     "Three columns of modal %: Ol, Opx and Cpx (any total; normalised). Named columns are found in any order; "
                                     "otherwise Ol as X, then Opx and Cpx.", [["Ol (X)", "Opx", "Cpx"], ["72", "20", "8"], ["15", "40", "45"]],
                                     "Valid for rocks with more than 90% mafic minerals."),
    "Harker Diagrams (oxides vs SiO2)": ("Harker variation diagrams: each oxide against SiO2 in its own small panel, to follow fractionation "
                                         "trends through a magma series.",
                                         "One row per sample with oxides in wt% in columns (SiO2, TiO2, Al2O3, FeOt, MgO, CaO, Na2O, K2O, or trace "
                                         "elements). Select SiO2 and the columns to show; SiO2 is found by name, otherwise X is used. One panel per column.",
                                         [["Sample", "SiO2", "TiO2", "MgO", "K2O"], ["B-1", "49.2", "1.6", "8.1", "0.4"], ["R-3", "73.5", "0.2", "0.3", "4.6"]],
                                         "Recalculate the analyses to 100% volatile-free first so the trends are comparable."),
    "Frost: Fe-number vs SiO2": ("Frost et al. (2001) granite classification, step 1: FeOt/(FeOt+MgO) against SiO2 separates ferroan from "
                                 "magnesian granitoids (line 0.486 + 0.0046 SiO2).", "Oxides in wt% in columns named SiO2, FeOt (or FeO*, FeO; Fe2O3 is added as FeO), MgO, Na2O, K2O and CaO (any order); select them. The same selection works for both Frost diagrams.",
                                 [["Sample", "SiO2", "FeOt", "MgO", "Na2O", "K2O", "CaO"], ["G-1", "71.2", "2.4", "0.5", "3.6", "4.8", "1.1"]],
                                 "Step 3 (alumina saturation) is the Shand A/CNK vs A/NK diagram."),
    "Frost: MALI vs SiO2": ("Frost et al. (2001) granite classification, step 2: the modified alkali-lime index Na2O+K2O-CaO against SiO2 "
                            "(alkalic, alkali-calcic, calc-alkalic, calcic).", "Oxides in wt% in columns named SiO2, FeOt (or FeO*, FeO; Fe2O3 is added as FeO), MgO, Na2O, K2O and CaO (any order); select them. The same selection works for both Frost diagrams.",
                            [["Sample", "SiO2", "FeOt", "MgO", "Na2O", "K2O", "CaO"], ["G-1", "71.2", "2.4", "0.5", "3.6", "4.8", "1.1"]],
                            "The boundaries are defined for SiO2 50-77 wt%."),
    "Shand A/CNK vs A/NK": ("Alumina saturation (Shand 1943; Maniar & Piccoli 1989): metaluminous, peraluminous or peralkaline, from "
                            "molar A/CNK = Al2O3/(CaO+Na2O+K2O) and A/NK = Al2O3/(Na2O+K2O). The dashed line at A/CNK 1.1 separates "
                            "I- and S-type granites (Chappell & White 1974).",
                            "Oxides in wt% in columns named Al2O3, CaO, Na2O and K2O (any order); select them all and the molar ratios are "
                            "calculated. Or give A/CNK as X and A/NK as Y if you have them already.",
                            [["Sample", "Al2O3", "CaO", "Na2O", "K2O"], ["G-1", "14.2", "1.8", "3.4", "4.6"]],
                            "CaO should strictly exclude the Ca in apatite; correct it first if P2O5 is high."),
    "AFM (Irvine & Baragar)": ("AFM ternary (A = Na2O + K2O, F = FeO total, M = MgO) with the tholeiitic / calc-alkaline boundary of "
                               "Irvine & Baragar (1971), for subalkaline volcanic rocks.",
                               "Oxides in wt% in columns named Na2O, K2O, FeOt (or FeO*, FeO; Fe2O3 is added as FeO), MgO; select them all. "
                               "Or give A, F and M directly as X, then two Y columns.",
                               [["Sample", "Na2O", "K2O", "FeOt", "MgO"], ["B-1", "2.6", "0.4", "11.2", "8.1"], ["A-2", "4.0", "1.9", "5.8", "2.0"]],
                               "Use it for subalkaline rocks only (check with TAS first)."),
    "Pearce Granite: Rb vs Y+Nb": ("Granite tectonic setting (Pearce et al. 1984): syn-collisional, volcanic-arc, within-plate and ocean-ridge granites.",
                                   "One row per granite sample with Rb, Y, Nb, Yb and Ta in ppm, in columns named after the elements (any order; 'Rb (ppm)' works). "
                         "Select all the element columns; the sums (Y+Nb, Yb+Ta) are formed for you.", [["Sample", "Rb", "Y", "Nb", "Yb", "Ta"], ["G-1", "185", "28", "14", "2.9", "1.4"]], ""),
    "Pearce Granite: Nb vs Y": ("Granite tectonic setting from Nb and Y (Pearce et al. 1984); the dashed line bounds anomalous ridge granites.",
                                "One row per granite sample with Rb, Y, Nb, Yb and Ta in ppm, in columns named after the elements (any order; 'Rb (ppm)' works). "
                         "Select all the element columns; the sums (Y+Nb, Yb+Ta) are formed for you.", [["Sample", "Rb", "Y", "Nb", "Yb", "Ta"], ["G-1", "185", "28", "14", "2.9", "1.4"]], ""),
    "Pearce Granite: Rb vs Yb+Ta": ("Granite tectonic setting from Rb against Yb + Ta (Pearce et al. 1984).",
                                    "One row per granite sample with Rb, Y, Nb, Yb and Ta in ppm, in columns named after the elements (any order; 'Rb (ppm)' works). "
                         "Select all the element columns; the sums (Y+Nb, Yb+Ta) are formed for you.", [["Sample", "Rb", "Y", "Nb", "Yb", "Ta"], ["G-1", "185", "28", "14", "2.9", "1.4"]], ""),
    "Pearce Granite: Ta vs Yb": ("Granite tectonic setting from Ta and Yb (Pearce et al. 1984); the dashed line bounds anomalous ridge granites.",
                                 "One row per granite sample with Rb, Y, Nb, Yb and Ta in ppm, in columns named after the elements (any order; 'Rb (ppm)' works). "
                         "Select all the element columns; the sums (Y+Nb, Yb+Ta) are formed for you.", [["Sample", "Rb", "Y", "Nb", "Yb", "Ta"], ["G-1", "185", "28", "14", "2.9", "1.4"]], ""),
    "Soil Texture (USDA)": ("Soil or sediment texture on the USDA triangle with the twelve texture classes (sand, loam, silty clay ...).",
                            "Three columns in %: Sand, Silt and Clay (grain sizes 2-0.05, 0.05-0.002 and below 0.002 mm). "
                            "Columns named Sand, Silt and Clay are found in any order; otherwise use Sand as X, then Silt and Clay.",
                            [["Sand (X)", "Silt", "Clay"], ["40", "40", "20"], ["10", "60", "30"]], "Rows need not add to exactly 100; they are normalised."),
    "3D Scatter": ("Points in 3-D; drag to rotate.", "X, Y and Z columns; select Y and Z.", [["X", "Y", "Z"], ["1", "2", "3"]], ""),
    "3D Surface": ("A surface through scattered X-Y-Z points.", "X, Y and Z columns; select Y and Z.", [["X", "Y", "Z"], ["1", "2", "3"]], ""),
    "Image / Heat Map": ("The matrix as an image with a colour bar.", _MATRIX, None, ""),
    "Filled Contour": ("Filled contours of the matrix.", _MATRIX, None, ""),
    "Contour Lines": ("Labelled contour lines of the matrix.", _MATRIX, None, ""),
    "3D Colour-map Surface": ("The matrix as a coloured 3-D surface.", _MATRIX, None, ""),
    "3D Wireframe": ("The matrix as a 3-D wire mesh.", _MATRIX, None, ""),
}


def html(kind, short=False):
    """Rich text for the gallery's help panel."""
    if kind not in HELP: return f"<b>{kind}</b>"
    what, prep, ex, tip = HELP[kind]
    out = f"<b>{kind}</b>: {what}<br><span style='color:gray'>How to prepare the data:</span> {prep}"
    if ex and not short:
        cells = "".join("<tr>" + "".join(f"<td style='padding:1px 8px;{'font-weight:bold' if i == 0 else ''}'>{c}</td>" for c in row) + "</tr>"
                        for i, row in enumerate(ex))
        out += f"<br><span style='color:gray'>Example:</span><table style='border:1px solid #bbb' cellspacing=0>{cells}</table>"
    if tip: out += f"<span style='color:gray'>Tip:</span> {tip}"
    return out
