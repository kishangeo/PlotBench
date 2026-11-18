"""Benchmark PlotBench's thermobarometry against published values and write VALIDATION.md.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Run from the repository root:  python validation/validate.py   (exit code 1 if any benchmark fails)

Three kinds of evidence, kept apart in the table:
  worked example  - the paper prints the intermediate or final numbers for a given input; PlotBench must reproduce them.
  experiments     - published experimental run conditions (T, P, fO2) recovered from the published phase compositions.
  equation check  - the result is recomputed independently from the printed equation (guards against coding slips only).
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from plotbench import thermobaro as TB, volcanic as VO, fetioxide as FT, geochron as GC  # noqa: E402

ROWS = []


def check(method, ref, kind, case, expected, got, tol, unit=""):
    ok = bool(np.all(np.abs(np.asarray(got, float) - np.asarray(expected, float)) <= tol))
    ROWS.append((method, ref, kind, case, expected, got, tol, unit, ok))


def stat(method, ref, case, resid, mean_tol, sd_tol, unit):
    """Experiments: mean and SD of (calculated - experimental) against a stated tolerance."""
    r = np.asarray(resid, float); r = r[np.isfinite(r)]
    ok = abs(r.mean()) <= mean_tol and r.std(ddof=1) <= sd_tol
    ROWS.append((method, ref, "experiments", f"{case} (n = {len(r)})", f"mean 0 ± {mean_tol}, SD ≤ {sd_tol}",
                 f"mean {r.mean():+.2f}, SD {r.std(ddof=1):.2f}", None, unit, ok))


P08 = "Putirka (2008) RiMG 69, 61-120"
# ---- worked examples printed in the papers
liq = {"SiO2": 47.05, "TiO2": 0.89, "Al2O3": 16.11, "FeO": 7.96, "MnO": 0.15, "MgO": 12.78, "CaO": 11.13, "Na2O": 2.18, "K2O": 0.04}
X = VO.liquid(liq)
for k, v in (("SiO2", 0.4327), ("AlO1.5", 0.1746), ("MgO", 0.1752), ("CaO", 0.1096), ("NaO0.5", 0.0389)):
    check("Liquid cation fractions", P08 + ", Table 1", "worked example", f"X {k}", v, float(X[k]), 6e-5)
cx = {"SiO2": 52.5, "TiO2": 0.33, "Al2O3": 1.58, "FeO": 9.89, "MnO": 0.24, "MgO": 13.29, "CaO": 22.5, "Na2O": 0.37, "K2O": 0, "Cr2O3": 0.05}
c = VO.cpx(cx)
for k, v in (("Si", 1.9553), ("AlIV", 0.0447), ("Jd", 0.0247), ("CaTi", 0.0223), ("DiHd", 0.8747), ("EnFs", 0.0856)):
    check("Clinopyroxene components", P08 + ", Table 3", "worked example", k, v, round(float(c[k]), 4), 2e-4, "apfu")
o = VO.opx({"SiO2": 55.7, "TiO2": 0.03, "Al2O3": 1.88, "FeO": 13.82, "MnO": 0, "MgO": 27.7, "CaO": 1.47, "Na2O": 0.44, "Cr2O3": 0})
for k, v in (("FmAl2SiO6", 0.0185), ("Fm2Si2O6", 0.8973)):
    check("Orthopyroxene components (two-pyroxene Eqs 36-39)", P08 + ", Table 2", "worked example", k, v, round(float(o[k]), 4), 2e-4, "apfu")
for k, v in (("W12p", -0.544), ("W1p2", 71.756), ("W24", 146.440), ("dG22", -12.552)):
    check("Fe-Ti oxides, spinel model parameters", "Ghiorso & Evans (2008) AJS 308, Table 6", "worked example", k, v, round(FT.P[k], 3), 2e-3, "kJ")

# ---- experiments
E = json.load(open(ROOT / "validation" / "data" / "evans2006_runs.json"))
dT, dN = [], []
for p in E:
    T, lf, dn = FT.two_oxide_wt(p["spn"], p["rhm"], p["P"]); dT.append(T - p["T"]); dN.append(dn - p["dNNO"])
dT, dN = np.array(dT), np.array(dN)
for tab in ("Table 3", "Table 4"):  # model performance, reported without a pass/fail: Ghiorso & Evans (2008, p. 985) note their model
    k = np.array([p["table"].strip() == tab for p in E])  # does not recover the low-T hydrothermal runs well (900 C reads high)
    for name, r, unit in (("T", dT[k], "°C"), ("ΔNNO", dN[k], "log units")):
        ROWS.append((f"Fe-Ti oxide {name} (Ghiorso & Evans 2008)", f"Evans et al. (2006) Contrib Mineral Petrol 152, 149-167, {tab}", "experiments (performance)",
                     f"run {'T' if name == 'T' else 'fO2'} recovered (n = {k.sum()})", "for information",
                     f"mean {r.mean():+.2f}, SD {r.std(ddof=1):.2f}", None, unit, None))
runs = np.array([r[1:] for r in TB.brey_runs()], float)  # P, T, P_BKN, P_NG, P_HG
B90 = "Brey et al. (1990) J Petrol 31, 1313-1352 (runs); Brey & Köhler (1990)"
stat("Garnet-opx Al barometer PBKN (Brey & Köhler 1990)", B90, "run P recovered at run T", runs[:, 2] - runs[:, 0], 1.0, 3.0, "kbar")
stat("Garnet-opx Al barometer (Nickel & Green 1985)", B90, "run P recovered at run T", runs[:, 3] - runs[:, 0], 1.0, 3.0, "kbar")
ca = np.array([r[3][0] for r in TB.BREY_RUNS], float)
stat("Ca-in-opx thermometer (Brey & Köhler 1990)", B90, "run T recovered at run P", TB.ca_in_opx_bk(ca, runs[:, 0]) - runs[:, 1], 30, 50, "°C")

# ---- equation checks (independent recomputation of the printed equation)
K0 = 273.15
check("Ti-in-zircon (Ferry & Watson 2007)", "Ferry & Watson (2007) CMP 154, 429-437", "equation check", "10 ppm Ti, aSiO2 = aTiO2 = 1",
      4800 / (5.711 - 1) - K0, TB.ti_in_zircon(10), 0.01, "°C")
check("Zr-in-rutile (Ferry & Watson 2007)", "Ferry & Watson (2007) CMP 154, 429-437", "equation check", "100 ppm Zr", 4530 / (7.420 - 2) - K0, TB.zr_in_rutile(100), 0.01, "°C")
check("Ti-in-quartz (Wark & Watson 2006)", "Wark & Watson (2006) CMP 152, 743-754", "equation check", "50 ppm Ti", 3765 / (5.69 - np.log10(50)) - K0,
      TB.ti_in_quartz_wark2006(50), 0.01, "°C")
xt = 50 * 60.08 / (47.867 * 1e6); R = 8.3145
check("Ti-in-quartz (Thomas et al. 2010)", "Thomas et al. (2010) CMP 160, 743-759", "equation check", "50 ppm Ti, 5 kbar",
      (-60952 - 1741 * 5) / (R * np.log(xt) - 1.520) - K0, TB.ti_in_quartz_thomas2010(50, 5.0), 1.0, "°C")
check("Zircon oxybarometer (Loucks et al. 2020)", "Loucks et al. (2020) J Petrol 61, egaa034", "equation check", "Ce 100, U 200, Ti 10 ppm",
      3.998 * np.log10(100 / np.sqrt(2000)) + 2.284, TB.zircon_dfmq_loucks2020(100, 200, 10), 1e-6, "ΔFMQ")
check("Al-in-hornblende (Schmidt 1992)", "Schmidt (1992) CMP 110, 304-310", "equation check", "Al 1.5 apfu", -3.01 + 4.76 * 1.5, TB.al_in_hornblende(1.5), 1e-9, "kbar")
check("U-Pb 206Pb/238U age", "Jaffey et al. (1971) decay constant", "equation check", "206/238 = 0.0807", np.log1p(0.0807) / 1.55125e-10 / 1e6,
      GC.age68(0.0807), 1e-6, "Ma")


def fmt(v):
    if isinstance(v, str): return v
    v = float(np.asarray(v, float).ravel()[0]); return f"{v:.4g}"


lines = ["# Validation of PlotBench calculations", "",
         "Generated by `python validation/validate.py`. Each row compares PlotBench with a published value. **Worked example**: numbers the "
         "paper prints for a given input. **Experiments**: experimental run conditions recovered from the run products (residual = "
         "PlotBench − experiment). **Equation check**: the printed equation recomputed independently (catches coding slips, not calibration "
         "errors).", "",
         "Methods not listed here are covered by the self-checks in each module (`_demo()`), which mostly recompute the equations by hand; "
         "they have not yet been benchmarked against independent published datasets.", "",
         "| Method | Source | Kind | Case | Expected | PlotBench | Tolerance | Unit | Pass |", "|---|---|---|---|---|---|---|---|---|"]
for m, ref, kind, case, exp, got, tol, unit, ok in ROWS:
    lines.append(f"| {m} | {ref} | {kind} | {case} | {fmt(exp)} | {fmt(got)} | {'' if tol is None else fmt(tol)} | {unit} | "
                 f"{'info' if ok is None else 'yes' if ok else '**NO**'} |")
graded = [r for r in ROWS if r[-1] is not None]; npass = sum(r[-1] for r in graded)
lines += ["", f"{npass} of {len(graded)} graded benchmarks pass. Rows marked *info* show how the published model itself performs on "
          "experiments it was (partly) calibrated on; they test the model, not this implementation. For the Fe-Ti oxide model, Ghiorso & Evans "
          "(2008, p. 985) report that it recovers the 900 °C experiments of Evans et al. (2006) systematically high and suggest some runs did "
          "not reach equilibrium; the run-by-run residuals are in `validation/data/evans2006_runs.json` with the inputs."]
(ROOT / "VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"VALIDATION: {npass}/{len(graded)} graded benchmarks pass")
for r in graded:
    if not r[-1]: print("FAIL:", ascii((r[0], r[3], r[4], r[5])))
sys.exit(0 if npass == len(graded) else 1)
