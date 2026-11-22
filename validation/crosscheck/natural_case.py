"""Natural-rock example of the PlotBench paper (Fig. 5): 13 garnet peridotite xenoliths of Tappe et al. (2021, J Petrol 62(8),
egab046), oxides -> mineral formulae -> Brey & Kohler (1990) two-pyroxene T and Al-in-opx P(BKN) solved together -> calibration-range
flags -> Monte Carlo 1-sigma errors and T-P correlation; then one analysis masked and everything recomputed; compared with Thermobar.
Run from the repository root:  python validation/crosscheck/natural_case.py      Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent; ROOT = HERE.parents[1]; sys.path.insert(0, str(ROOT))
from plotbench import thermobaro as TB, mineral as MN  # noqa: E402

x = pd.read_csv(HERE / "tappe2021_xenoliths.csv"); n = len(x)
TM, PM = "Two-pyroxene (Brey & Kohler 1990)", "Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)"
PH = {"Opx": ("Opx", 6), "Cpx": ("Cpx", 6), "Gt": ("Garnet", 12)}


def cations(df):
    """Formulae on 6 (pyroxenes) and 12 (garnet) oxygens, all iron as Fe2+, as PlotBench's Mineral Formula command gives them."""
    out = {}
    for s, (name, o) in PH.items():
        wt = {c.split("_")[0].replace("FeOt", "FeO"): df[c].to_numpy(float) for c in df.columns if c.endswith("_" + s)}
        for k, v in MN.formula(wt, o).items(): out[f"{name} {k.replace('Fe2+', 'Fe')}"] = v
    return out


def solve(df, mc=True):
    c = cations(df); cols = {k: k for k in c}; arr = lambda k: np.asarray(c[k], float)
    T, P, it = TB.solve_pt(TM, PM, cols, arr, dict, n_iter=200, tol=1e-6)
    out = {"T": T, "P": P, "iterations": int(it)}
    fT = TB.in_range(TM, T, {"P (kbar)": P}, n); fP = TB.in_range(PM, P, {"T (C), if no column": T}, n)
    out["inside"] = (fT == 1) & (fP == 1)
    if mc: out["sT"], out["sP"], out["rho"] = TB.solve_pt_mc(TM, PM, cols, arr, dict, rel=0.02, n=2000, seed=5)
    return out


r = solve(x)
tb = pd.read_csv(HERE / "thermobar_tappe.csv")
m = x.copy(); k = int(np.nanargmax(r["T"])); m.loc[k, "Al2O3_Opx"] = np.nan  # masking one cell: PlotBench reads a masked cell as missing
rm = solve(m)
facts = {"n": n, "T_range": [float(np.nanmin(r["T"])), float(np.nanmax(r["T"]))], "P_range_GPa": [float(np.nanmin(r["P"]) / 10), float(np.nanmax(r["P"]) / 10)],
         "inside": int(np.sum(r["inside"])), "sT_range": [float(np.min(r["sT"])), float(np.max(r["sT"]))],
         "sP_range_GPa": [float(np.min(r["sP"]) / 10), float(np.max(r["sP"]) / 10)], "rho_range": [float(np.min(r["rho"])), float(np.max(r["rho"]))],
         "vs_thermobar_max_dT": float(np.nanmax(np.abs(r["T"] - tb["TB T_C"]))), "vs_thermobar_max_dP_kbar": float(np.nanmax(np.abs(r["P"] - tb["TB P_kbar"]))),
         "masked_sample": str(x["SampleID"][k]), "masked_row_blank": bool(np.isnan(rm["T"][k]) and np.isnan(rm["P"][k]) and np.isnan(rm["sT"][k])),
         "others_unchanged": bool(np.allclose(np.delete(rm["T"], k), np.delete(r["T"], k)))}
print(json.dumps(facts, indent=1))
json.dump(facts, open(HERE / "natural_facts.json", "w"), indent=1)

plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.linewidth": 0.8, "xtick.direction": "in", "ytick.direction": "in",
                     "xtick.top": True, "ytick.right": True, "legend.frameon": False, "pdf.fonttype": 42})
fig, a = plt.subplots(figsize=(3.6, 3.2), constrained_layout=True)
a.add_patch(plt.Rectangle((900, 1.0), 500, 5.0, color="#555555", alpha=0.12, lw=0, label="Calibration range"))
for i in range(n):
    ins = bool(r["inside"][i]); col = "#0072B2" if ins else "#D55E00"
    t = np.linspace(0, 2 * np.pi, 100); rho = r["rho"][i]  # 1-sigma ellipse of the correlated T and P errors
    a.plot(r["T"][i] + r["sT"][i] * np.cos(t), (r["P"][i] + r["sP"][i] * (rho * np.cos(t) + np.sqrt(1 - rho ** 2) * np.sin(t))) / 10, color=col, lw=0.8)
    a.plot(r["T"][i], r["P"][i] / 10, "o" if ins else "s", ms=4.5, mfc="none" if i == k else col, mec=col if i == k else "k", mew=0.8 if i == k else 0.5)
a.plot([], [], "o", color="#0072B2", mec="k", mew=0.5, label="Inside range"); a.plot([], [], "s", color="#D55E00", mec="k", mew=0.5, label="Outside range")
a.plot([], [], "s", mfc="none", mec="#D55E00", label="Masked (removed)")
a.set(xlabel="Temperature (°C)", ylabel="Pressure (GPa)", xlim=(1050, 1500), ylim=(4.3, 7.2)); a.invert_yaxis(); a.legend(fontsize=7, loc="lower left")
out = ROOT / "validation" / "paper"; fig.savefig(out / "Figure_5.pdf"); fig.savefig(out / "Figure_5.png", dpi=600)
