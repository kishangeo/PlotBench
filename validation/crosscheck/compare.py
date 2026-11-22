"""PlotBench against Thermobar and IsoplotR on identical inputs (thermobar.csv, isoplotr.json from the *_side scripts).
Run from the repository root:  python validation/crosscheck/compare.py     Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).parent; sys.path.insert(0, str(HERE.parents[1]))
from plotbench import thermobaro as TB  # noqa: E402

d = pd.read_csv(HERE / "thermobar.csv")
arr = lambda c: np.asarray(d[c] if not isinstance(c, (int, float)) else c, float)
ox = lambda prefix=False: TB.phase_oxides(d.columns, arr, prefix)
runs = {"Clinopyroxene-liquid T (Putirka 2008 Eq 33)": ("TB eq33 T_C", {"Liquid H2O (wt%)": "H2O", "P (kbar)": d["P_kbar"].values}),
        "Clinopyroxene-liquid P (Putirka 2008 Eq 30)": ("TB eq30 P_kbar", {"Liquid H2O (wt%)": "H2O", "T (C) column": "T_C"}),
        "Clinopyroxene-liquid P (Putirka 2008 Eq 31)": ("TB eq31 P_kbar", {"Liquid H2O (wt%)": "H2O", "T (C) column": "T_C"}),
        "Clinopyroxene-only P (Putirka 2008 Eq 32a)": ("TB eq32a P_kbar", {"T (C) column": "T_C"}),
        "Clinopyroxene-only T (Putirka 2008 Eq 32d)": ("TB eq32d T_C", {"P (kbar)": d["P_kbar"].values})}
from plotbench import volcanic as V  # noqa: E402
si = V.cpx({k.split()[1]: arr(k) for k in d.columns if k.startswith("Cpx ")})["Si"]
over = si > 2  # Thermobar lets AlIV = 2 - Si go negative (and AlVI exceed Al); PlotBench sets AlIV to 0
facts = {"thermobar_rows": len(d), "cpx_si_over_2": int(over.sum())}
for method, (ref, inp) in runs.items():
    pb = np.asarray(TB.compute(method, inp, arr, ox, len(d)), float); tb = arr(ref); ok = np.isfinite(pb) & np.isfinite(tb) & ~over
    a = np.abs(pb[ok] - tb[ok]); unit = ref.split()[-1]
    facts[method] = {"n": int(ok.sum()), "median": float(np.median(a)), "p99": float(np.percentile(a, 99)), "max": float(a.max()), "unit": unit,
                     "max_si_over_2": float(np.nanmax(np.abs(pb[over] - tb[over]))) if over.any() else None}
    print(f"{method:46s} n={ok.sum():4d}  median {np.median(a):.3f}  99% {np.percentile(a, 99):.3f}  max {a.max():.3f} {unit}"
          f"  (Si > 2: max {facts[method]['max_si_over_2']:.2f})")
iso = HERE / "isoplotr.json"
if iso.exists():
    from plotbench import geochron as G
    j = json.load(open(iso)); r, u = j["rbsr"], j["upb"]
    yf = G.york(*(np.array(r[k]) for k in ("x", "sx", "y", "sy", "rho"))); ca = G.concordia_age(*(np.array(u[k]) for k in ("x", "sx", "y", "sy", "rho")))
    rel = lambda a, b: abs(a / b - 1)
    facts["isoplotr"] = {"version": j["version"], "n_rbsr": len(r["x"]), "n_upb": len(u["x"]),
                         "york_rel": {k: rel(yf[k], j["york"][k]) for k in ("slope", "s_slope", "intercept", "s_intercept", "mswd")},
                         "concordia": {"pb": ca["age"], "iso": j["concordia"]["age"], "pb_1s": ca["age_2s"] / 2, "iso_1s": j["concordia"]["s_age"],
                                       "pb_mswd_conc": ca["mswd_conc"], "iso_mswd_conc": j["concordia"]["mswd_conc"]}}
    print(json.dumps(facts["isoplotr"], indent=1))
json.dump(facts, open(HERE / "facts.json", "w"), indent=1)
