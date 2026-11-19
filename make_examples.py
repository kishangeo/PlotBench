"""Write the example data files in plotbench/examples/. All values are synthetic (made up to look realistic), for learning
the program; they are not measurements. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>. Run: python make_examples.py"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "plotbench" / "examples"; OUT.mkdir(exist_ok=True)
r = np.random.default_rng(2024)


def save(name, df, note):
    with open(OUT / name, "w", encoding="utf-8", newline="") as f:
        f.write(f"# {note} Synthetic example data for PlotBench (not measurements).\n")
        df.to_csv(f, index=False, float_format="%.6g")


# 1 colour-mapped scatter: bridgmanite-like Fe3+/ΣFe against unit-cell volume, coloured by Al
n = 24; al = np.round(r.uniform(0.0, 0.16, n), 3); fe3 = np.clip(0.18 + 2.6 * al + r.normal(0, 0.03, n), 0.05, 0.95)
vol = 162.3 + 4.2 * al + 0.9 * fe3 + r.normal(0, 0.05, n)
save("bridgmanite_colour_map.csv", pd.DataFrame({"Sample": [f"BM-{i + 1:02d}" for i in range(n)], "Volume (A3)": vol, "Fe3+/SumFe": fe3,
                                                  "Al (pfu)": al, "Run": r.choice(["H4590", "H4612", "S7311"], n), "Fe3+ error": r.uniform(0.02, 0.05, n)}),
     "Colour-mapped scatter: unit-cell volume vs Fe3+/SumFe coloured by Al.")

# 2 Raman spectrum with three peaks on a sloping background
x = np.linspace(150, 1200, 1050)
y = (55 * np.exp(-((x - 465) / 9) ** 2) + 18 / (1 + ((x - 520) / 7) ** 2) + 26 * np.exp(-((x - 820) / 14) ** 2) + 0.012 * x + 3
     + r.normal(0, 0.6, x.size))
save("raman_spectrum.csv", pd.DataFrame({"Raman shift (cm-1)": x, "Intensity (counts)": y}), "Raman spectrum for the Peak Analyzer and baselines.")

# 3 Raman spectra at several temperatures (peak softens and broadens)
cols = {"Raman shift (cm-1)": x}
for T in (25, 200, 400, 600, 800):
    c = 465 - 0.012 * T; w = 9 + 0.01 * T
    cols[f"{T} C"] = 50 * np.exp(-((x - c) / w) ** 2) + 20 * np.exp(-((x - (820 - 0.02 * T)) / (14 + 0.01 * T)) ** 2) + 2 + r.normal(0, 0.5, x.size)
save("raman_temperature_series.csv", pd.DataFrame(cols), "Spectra at five temperatures for waterfall and stacked panels.")

# 4 trace elements (ppm) for six basalts and two granites
ci = {"La": 0.237, "Ce": 0.613, "Pr": 0.0928, "Nd": 0.457, "Sm": 0.148, "Eu": 0.0563, "Gd": 0.199, "Tb": 0.0361, "Dy": 0.246, "Ho": 0.0546,
      "Er": 0.16, "Tm": 0.0247, "Yb": 0.161, "Lu": 0.0246}
pm = {"Rb": 0.6, "Ba": 6.6, "Th": 0.0795, "U": 0.0203, "Nb": 0.658, "Ta": 0.037, "Sr": 19.9, "Zr": 10.5, "Hf": 0.283, "Y": 4.3}
rows = []
for i, (kind, slope, level, eu) in enumerate([("Basalt", 1.4, 30, 1.0)] * 4 + [("Basalt", 0.3, 12, 1.0)] * 2 + [("Granite", 2.2, 90, 0.35)] * 2):
    ree = list(ci); row = {"Sample": f"{kind[:2].upper()}-{i + 1:02d}", "Rock": kind}
    for j, e in enumerate(ree):
        f = level * np.exp(slope * (1 - j / (len(ree) - 1))) / np.exp(slope / 2) * r.uniform(0.92, 1.08)
        if e == "Eu": f *= eu
        row[e] = round(ci[e] * f, 3)
    for j, e in enumerate(pm):
        row[e] = round(pm[e] * level * (2.5 if kind == "Granite" else 1) * np.exp(0.06 * (len(pm) - j)) * r.uniform(0.85, 1.15), 3)
    rows.append(row)
df = pd.DataFrame(rows); df = df.astype(object); df.loc[5, "Tm"] = "<0.05"  # below detection: shown as a gap
save("trace_elements_ppm.csv", df, "Trace elements in ppm for spider diagrams (one row per sample).")

# 5 major oxides (wt%) of a volcanic series for TAS
si = np.sort(r.uniform(44, 75, 22)); alk = np.clip(0.95 + 0.135 * (si - 44) + r.normal(0, 0.6, si.size), 0.5, None)
k2o = alk * np.clip(0.15 + 0.012 * (si - 44), 0.1, 0.5); na2o = alk - k2o
save("major_oxides_wt.csv", pd.DataFrame({"Sample": [f"V-{i + 1:02d}" for i in range(si.size)], "SiO2": si, "TiO2": np.clip(2.2 - 0.06 * (si - 44), 0.1, None),
                                           "Al2O3": 15 + r.normal(0, 0.8, si.size), "FeOt": np.clip(12 - 0.33 * (si - 44), 0.8, None),
                                           "MgO": np.clip(9 - 0.28 * (si - 44), 0.1, None), "CaO": np.clip(11 - 0.32 * (si - 44), 0.3, None),
                                           "Na2O": na2o, "K2O": k2o}), "Major oxides (wt%) for the TAS diagram.")

# 6 modal Q, A, P of granitoids
q = r.uniform(5, 55, 18); a = r.uniform(5, 60, 18); p = r.uniform(5, 60, 18)
save("qap_modes.csv", pd.DataFrame({"Sample": [f"G-{i + 1:02d}" for i in range(18)], "Q": q, "A": a, "P": p}), "Modal quartz, alkali feldspar, plagioclase.")

# 7 mineral modes for ternary diagrams, with MgO for colour
d = r.dirichlet([4, 2.5, 1.8], 30) * 100
save("ternary_mineral_modes.csv", pd.DataFrame({"Olivine": d[:, 0], "Pyroxene": d[:, 1], "Plagioclase": d[:, 2], "MgO (wt%)": 6 + 0.3 * d[:, 0]}),
     "Mineral modes (vol%) for ternary diagrams.")

# 8 groundwater in mg/L for the Piper diagram (converted to meq/L when opened)
m = 10
save("water_chemistry_mgL.csv", pd.DataFrame({"Sample": [f"W-{i + 1:02d}" for i in range(m)], "Ca": r.uniform(20, 120, m), "Mg": r.uniform(5, 40, m),
                                              "Na": r.uniform(10, 150, m), "K": r.uniform(1, 10, m), "HCO3": r.uniform(100, 400, m),
                                              "CO3": r.uniform(0, 12, m), "Cl": r.uniform(10, 200, m), "SO4": r.uniform(10, 150, m)}),
     "Major ions in mg/L; open to convert to meq/L and plot a Piper diagram.")

# 9 calibration with standard deviations
c = np.array([0, 0.5, 1, 2, 5, 10, 20, 50.0]); s = 0.003 + 0.0512 * c + r.normal(0, 0.004, c.size)
save("calibration_with_errors.csv", pd.DataFrame({"Concentration (ppm)": c, "Absorbance": s, "Absorbance SD": 0.004 + 0.01 * s}),
     "Calibration curve; the SD column is set as yErr so error bars appear.")

# 10 three groups (different sizes) for box plots and ANOVA
g = {"Control": r.normal(10, 1.4, 14), "Treatment A": r.normal(11.6, 1.5, 12), "Treatment B": r.normal(13.1, 1.6, 15)}
save("groups_three_samples.csv", pd.DataFrame({k: pd.Series(v) for k, v in g.items()}), "Three groups of different size: box, violin, ANOVA.")

# 11 time series with two quantities
t = np.arange(0, 120.0)
save("time_series_two_quantities.csv", pd.DataFrame({"Time (min)": t, "Temperature (C)": 20 + 5 * np.sin(t / 10) + r.normal(0, 0.4, t.size),
                                                     "Humidity (%)": 60 - 8 * np.sin(t / 10 + 1) + r.normal(0, 1, t.size)}),
     "Two quantities against time: line, step, area, double-Y.")

# 12 scattered XYZ
xx, yy = r.uniform(-3, 3, 400), r.uniform(-3, 3, 400)
save("scattered_xyz.csv", pd.DataFrame({"X": xx, "Y": yy, "Z": np.exp(-(xx ** 2 + yy ** 2) / 4) * np.cos(xx) + r.normal(0, 0.02, 400)}),
     "Scattered X, Y, Z for contour, density and 3-D plots.")

# 12b a path in 3-D, and a grid with heights and vectors
tt = np.linspace(0, 4 * np.pi, 80)
save("path_3d.csv", pd.DataFrame({"X": np.cos(tt), "Y": np.sin(tt), "Z": tt / (4 * np.pi) * 10}), "A spiral path for the 3D Line plot.")
gx, gy = (v.ravel() for v in np.meshgrid(np.arange(1.0, 6), np.arange(1.0, 5)))
save("grid_heights_vectors.csv", pd.DataFrame({"X": gx, "Y": gy, "Z": np.round(2 + np.sin(gx) + 0.5 * gy, 3), "U": np.round(-(gy - 2.5), 3),
                                               "V": np.round(gx - 3, 3), "W": np.full(gx.size, 0.5)}),
     "A 5 x 4 grid with a height Z and a vector (U, V, W) at each point, for 3D Bars and 3D Vectors.")

# 13 categories with errors
save("categories_with_errors.csv", pd.DataFrame({"Site": ["North", "East", "South", "West", "Centre"], "2023": [12, 8, 15, 6, 10.0],
                                                 "SD 2023": [1.1, 0.8, 1.6, 0.7, 0.9], "2024": [15, 9, 13, 8, 12.0], "SD 2024": [1.4, 0.9, 1.2, 0.8, 1.1]}),
     "Categories for columns, bars, pie and Pareto.")

# 14 repeated measures in long format
rows = []
for sbj in range(12):
    b0 = r.normal(0, 2)
    for wk in range(5): rows.append((f"S{sbj + 1:02d}", "drug" if sbj >= 6 else "placebo", wk, 50 + b0 + (2.5 if sbj >= 6 else 0.8) * wk + r.normal(0, 1)))
save("repeated_measures_long.csv", pd.DataFrame(rows, columns=["Subject", "Group", "Week", "Score"]), "Long format for mixed models.")

# 15 survival
tt = np.round(r.exponential(20, 40), 1); ev = (r.uniform(size=40) < 0.75).astype(int)
save("survival_times.csv", pd.DataFrame({"Time (months)": tt, "Event (1=yes)": ev, "Group": np.repeat(["A", "B"], 20)}), "Survival times with censoring.")

# 16 wind
dirs = (r.vonmises(np.radians(250) - np.pi, 2, 400) + np.pi) * 180 / np.pi % 360
save("wind_direction_speed.csv", pd.DataFrame({"Direction (deg)": dirs, "Speed (m/s)": r.gamma(2.2, 2.0, 400)}), "Wind observations.")

# 17 flows
save("sankey_flows.csv", pd.DataFrame({"From": ["Mine", "Mine", "Mill", "Mill", "Smelter", "Smelter"], "To": ["Mill", "Waste rock", "Smelter", "Tailings", "Metal", "Slag"],
                                       "Amount (kt)": [100, 40, 62, 38, 49, 13.0]}), "Material flows for a Sankey diagram.")

# 18 two methods
true = r.uniform(0.5, 5, 30)
save("method_comparison.csv", pd.DataFrame({"Method A": true + r.normal(0, 0.08, 30), "Method B": true * 1.02 + 0.03 + r.normal(0, 0.1, 30)}),
     "Same samples measured by two methods.")
# 19 soil texture (%)
d = r.dirichlet([2.5, 3, 1.6], 20) * 100
save("soil_texture.csv", pd.DataFrame({"Sample": [f"SO-{i + 1:02d}" for i in range(20)], "Sand (%)": d[:, 0], "Silt (%)": d[:, 1], "Clay (%)": d[:, 2]}),
     "Grain-size fractions for the USDA soil texture triangle.")

# 20 feldspar end-members (mol%): a plagioclase series and some alkali feldspars
an = np.linspace(5, 88, 12) + r.normal(0, 2, 12); orp = r.uniform(0.3, 3, 12)
alk_or = r.uniform(40, 92, 6); alk_an = r.uniform(0, 2.5, 6)
fsp = pd.DataFrame({"Analysis": [f"Pl-{i + 1:02d}" for i in range(12)] + [f"Kfs-{i + 1}" for i in range(6)],
                    "Ab": np.r_[100 - an - orp, 100 - alk_or - alk_an], "Or": np.r_[orp, alk_or], "An": np.r_[an, alk_an]})
save("feldspar_compositions.csv", fsp, "Feldspar end-members in mol% for the An-Ab-Or ternary.")

# 21 pyroxene microprobe analyses (oxide wt%): augites, pigeonites and orthopyroxenes made from end-member mixtures
M = {"SiO2": 60.0843, "TiO2": 79.8658, "Al2O3": 101.9613, "FeO": 71.8444, "MnO": 70.9374, "MgO": 40.3044, "CaO": 56.0774, "Na2O": 61.9789}
rows = []
for kind, n, wo_rng in (("Aug", 8, (36, 46)), ("Pgt", 4, (6, 14)), ("Opx", 6, (1, 4))):
    for i in range(n):
        wo = r.uniform(*wo_rng) / 100; mg = r.uniform(0.55, 0.88); en = (1 - wo) * mg; fs = (1 - wo) * (1 - mg)
        al = r.uniform(0.04, 0.2); cat = {"SiO2": 2 - al / 2, "TiO2": r.uniform(0, 0.02), "Al2O3": al / 2, "FeO": 2 * fs * 0.97, "MnO": 2 * fs * 0.03,
                                          "MgO": 2 * en, "CaO": 2 * wo, "Na2O": r.uniform(0, 0.01)}
        wt = {k: v * M[k] for k, v in cat.items()}; tot = sum(wt.values()); f = r.uniform(99.0, 100.6) / tot
        rows.append({"Analysis": f"{kind}-{i + 1:02d}", **{k: round(v * f, 2) for k, v in wt.items()}})
save("pyroxene_epma_oxides.csv", pd.DataFrame(rows), "Pyroxene microprobe analyses in oxide wt% (FeO = total Fe).")

# 22 ultramafic modes
d = np.vstack([r.dirichlet([20, 2, 1], 6), r.dirichlet([8, 4, 2], 8), r.dirichlet([2, 4, 4], 6), r.dirichlet([0.5, 3, 3], 4)]) * 100
save("ultramafic_modes.csv", pd.DataFrame({"Sample": [f"UM-{i + 1:02d}" for i in range(len(d))], "Ol": d[:, 0], "Opx": d[:, 1], "Cpx": d[:, 2]}),
     "Modal olivine, orthopyroxene and clinopyroxene of ultramafic rocks.")

# 23 granite trace elements (ppm) for the Pearce et al. (1984) diagrams: typical ranges of each setting
rows = []
for setting, n, rb, y, nb_y, ta_nb in (("volcanic arc", 6, (40, 150), (10, 35), (0.2, 0.5), (0.06, 0.1)),
                                       ("syn-collisional", 5, (250, 600), (8, 30), (0.4, 0.8), (0.1, 0.2)),
                                       ("within-plate", 6, (150, 400), (60, 150), (0.6, 1.5), (0.06, 0.09)),
                                       ("ocean ridge", 4, (2, 20), (60, 200), (0.1, 0.3), (0.06, 0.08))):
    for i in range(n):
        yy = r.uniform(*y); nb = yy * r.uniform(*nb_y)
        rows.append({"Sample": f"{setting[:2].upper()}-{i + 1}", "Setting": setting, "Rb": round(r.uniform(*rb), 1), "Y": round(yy, 1),
                     "Nb": round(nb, 1), "Yb": round(yy / r.uniform(7, 10), 2), "Ta": round(nb * r.uniform(*ta_nb), 2)})
save("granite_trace_elements.csv", pd.DataFrame(rows), "Granite trace elements in ppm for the Pearce et al. (1984) diagrams.")

# oceanic and arc basalts (Th, Nb, Yb ppm; TiO2 wt%) for the Pearce (2008) diagrams: typical ranges of each setting
rows = []
for setting, n, nbyb, thnb, tiyb in (("N-MORB", 6, (0.5, 1.2), (0.05, 0.07), (0.38, 0.6)), ("E-MORB", 5, (1.8, 5), (0.06, 0.09), (0.35, 0.6)),
                                     ("OIB", 6, (10, 35), (0.07, 0.1), (1.0, 2.0)), ("Volcanic arc", 6, (0.5, 3), (0.3, 1.0), (0.25, 0.5))):
    for i in range(n):
        yb = r.uniform(1.5, 3.5); nb = yb * r.uniform(*nbyb)
        rows.append({"Sample": f"{setting[:3].upper()}-{i + 1}", "Setting": setting, "TiO2": round(yb * r.uniform(*tiyb), 2), "Nb": round(nb, 2),
                     "Th": round(nb * r.uniform(*thnb), 3), "Yb": round(yb, 2)})
save("basalt_th_nb_yb.csv", pd.DataFrame(rows), "Oceanic and arc basalts (Th, Nb, Yb in ppm, TiO2 in wt%) for the Pearce (2008) diagrams.")

# geochronology: a Rb-Sr whole-rock isochron (1200 Ma), zircon U-Pb (about 500 Ma) and two detrital zircon samples
import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent))
from plotbench import geochron as GC
rb = np.array([0.15, 0.62, 1.10, 1.71, 2.36, 3.05, 3.80]); sr = 0.7045 + rb * np.expm1(GC.SYSTEMS["Rb-Sr"][0] * 1.2e9) + r.normal(0, 2e-5, 7)
save("rbsr_isochron.csv", pd.DataFrame({"Sample": [f"WR-{i + 1}" for i in range(7)], "87Rb/86Sr": rb, "87Sr/86Sr": sr, "1s 87Rb/86Sr": rb * 0.005,
     "1s 87Sr/86Sr": np.full(7, 2e-5)}), "Whole-rock Rb-Sr data, 1-sigma absolute errors (synthetic, 1200 Ma, initial 0.7045).")
t = r.normal(500, 3, 12); x75, y68 = GC.wetherill(t); x75 = x75 * (1 + r.normal(0, 0.004, 12)); y68 = y68 * (1 + r.normal(0, 0.003, 12))
save("zircon_upb.csv", pd.DataFrame({"Spot": [f"z{i + 1}" for i in range(12)], "207Pb/235U": x75, "206Pb/238U": y68, "1s 207/235": x75 * 0.008,
     "1s 206/238": y68 * 0.006, "rho": np.full(12, 0.75), "238U/206Pb": 1 / y68, "207Pb/206Pb": x75 / (GC.U85 * y68), "1s 238/206": 0.006 / y68, "1s 207/206": x75 / (GC.U85 * y68) * 0.01, "Age 206/238 (Ma)": GC.age68(y68), "1s age (Ma)": GC.age68(y68) * 0.006}),
     "Zircon U-Pb ratios with 1-sigma absolute errors (synthetic, about 500 Ma).")
a = np.r_[r.normal(560, 25, 45), r.normal(1050, 40, 35), r.normal(2500, 50, 20)]; b = np.r_[r.normal(600, 30, 50), r.normal(1800, 60, 50)]
save("detrital_zircon_ages.csv", pd.DataFrame({"Sample A (Ma)": pd.Series(a), "1s A (Ma)": pd.Series(a * 0.02), "Sample B (Ma)": pd.Series(b)}),
     "Detrital zircon ages of two samples (synthetic).")

print("wrote", len(list(OUT.glob("*.csv"))), "files")
