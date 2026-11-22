"""Figures 3 and 4 and the timing table of the PlotBench paper, from the validation data. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Run from the repository root:  python validation/paper_figures.py [output folder]   (default: validation/paper)"""
import json, sys, time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from plotbench import thermobaro as TB, fetioxide as FT  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "validation" / "paper"; OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.linewidth": 0.8, "xtick.direction": "in", "ytick.direction": "in",
                     "xtick.top": True, "ytick.right": True, "legend.frameon": False, "pdf.fonttype": 42})
BLUE, ORANGE, GREY = "#0072B2", "#D55E00", "#555555"  # colour-blind safe (Okabe-Ito)
facts = {}


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf"); fig.savefig(OUT / f"{name}.png", dpi=600); plt.close(fig)


# ---- Figure 3: experimental conditions recovered from run products
runs = np.array([r[1:] for r in TB.brey_runs()], float)  # P, T, P_BKN, P_NG, P_HG
ca = np.array([r[3][0] for r in TB.BREY_RUNS], float); t_ca = TB.ca_in_opx_bk(ca, runs[:, 0])
E = json.load(open(ROOT / "validation" / "data" / "evans2006_runs.json"))
cache = OUT / "fe_ti_T.json"  # 41 two-oxide solutions take several minutes: kept between runs
if cache.exists(): ft = np.array(json.load(open(cache)), float)
else:
    ft = np.array([(p["T"], FT.two_oxide_wt(p["spn"], p["rhm"], p["P"])[0], p["table"].strip() == "Table 4") for p in E], float)
    json.dump(ft.tolist(), open(cache, "w"))
fig, ax = plt.subplots(1, 3, figsize=(7.48, 2.75), constrained_layout=True)
a = ax[0]; a.plot([0.5, 6.5], [0.5, 6.5], color=GREY, lw=0.8); a.fill_between([0.5, 6.5], [0.2, 6.2], [0.8, 6.8], color=GREY, alpha=0.12, lw=0)
a.plot(runs[:, 0] / 10, runs[:, 2] / 10, "o", color=BLUE, ms=5, mec="k", mew=0.5, label="Brey and Köhler (1990)")
a.plot(runs[:, 0] / 10, runs[:, 3] / 10, "s", color=ORANGE, ms=4.5, mec="k", mew=0.5, label="Nickel and Green (1985)")
a.set(xlabel="Run pressure (GPa)", ylabel="Calculated pressure (GPa)", xlim=(0.5, 6.5), ylim=(0.5, 6.5)); a.legend(fontsize=7, loc="upper left")
a.set_title("(a)", loc="left", weight="bold", fontsize=9)
a = ax[1]; a.plot([850, 1450], [850, 1450], color=GREY, lw=0.8); a.fill_between([850, 1450], [820, 1420], [880, 1480], color=GREY, alpha=0.12, lw=0)
a.plot(runs[:, 1], t_ca, "o", color=BLUE, ms=5, mec="k", mew=0.5, label="Ca-in-orthopyroxene")
a.set(xlabel="Run temperature (°C)", ylabel="Calculated temperature (°C)", xlim=(850, 1450), ylim=(850, 1450)); a.legend(fontsize=7, loc="upper left")
a.set_title("(b)", loc="left", weight="bold", fontsize=9)
a = ax[2]; a.plot([550, 1000], [550, 1000], color=GREY, lw=0.8); a.fill_between([550, 1000], [500, 950], [600, 1050], color=GREY, alpha=0.12, lw=0)
k = ft[:, 2] == 1; jit = np.random.default_rng(3).uniform(-9, 9, len(ft))
a.plot(ft[k, 0] + jit[k], ft[k, 1], "o", color=BLUE, ms=5, mec="k", mew=0.5, label="Evans et al. (2006), Table 4")
a.plot(ft[~k, 0] + jit[~k], ft[~k, 1], "s", color=ORANGE, ms=4.5, mec="k", mew=0.5, label="Evans et al. (2006), Table 3")
a.set(xlabel="Run temperature (°C)", ylabel="Calculated temperature (°C)", xlim=(550, 1000), ylim=(550, 1000)); a.legend(fontsize=6.5, loc="upper left", handletextpad=0.2, borderaxespad=0.2)
a.set_title("(c)", loc="left", weight="bold", fontsize=9)
save(fig, "Figure_3")
facts["brey"] = {"n": len(runs), "PBKN_mean": float((runs[:, 2] - runs[:, 0]).mean()), "PBKN_sd": float((runs[:, 2] - runs[:, 0]).std(ddof=1)),
                 "NG_mean": float((runs[:, 3] - runs[:, 0]).mean()), "NG_sd": float((runs[:, 3] - runs[:, 0]).std(ddof=1)),
                 "TCa_mean": float((t_ca - runs[:, 1]).mean()), "TCa_sd": float((t_ca - runs[:, 1]).std(ddof=1))}
for name, m in (("FeTi_T4", k), ("FeTi_T3", ~k)):
    d = ft[m, 1] - ft[m, 0]; facts[name] = {"n": int(m.sum()), "mean": float(d.mean()), "sd": float(d.std(ddof=1))}

# ---- Figure 4: Monte Carlo propagation against the analytical (linearised) error, and its convergence with the number of draws
ti = np.geomspace(1, 60, 12); rel = 0.05; M = "Ti-in-zircon (Ferry & Watson 2007)"
cols = {"Ti (ppm)": "Ti", "a SiO2": 1.0, "a TiO2": 1.0}; arr = lambda c: ti
T = TB.compute(M, cols, arr, dict) + 273.15
lin = T ** 2 * rel / (4800 * np.log(10))  # dT = T^2 / (4800 ln 10) * dTi/Ti, from log Ti = 5.711 - 4800/T
mc = TB.monte_carlo(M, cols, arr, dict, len(ti), rel=rel, n=2000, seed=7)
ns = np.array([25, 50, 100, 200, 500, 1000, 2000, 5000]); one = lambda c: np.array([10.0])
spread = [np.std([TB.monte_carlo(M, cols, one, dict, 1, rel=rel, n=int(n), seed=s)[0] for s in range(40)], ddof=1) for n in ns]
sd10 = float(TB.monte_carlo(M, cols, one, dict, 1, rel=rel, n=5000, seed=1)[0])
fig, ax = plt.subplots(1, 2, figsize=(7.48, 2.9), constrained_layout=True)
a = ax[0]; a.plot(T - 273.15, lin, "-", color=GREY, lw=1, label="Analytical (first order)")
a.plot(T - 273.15, mc, "o", color=BLUE, ms=5, mec="k", mew=0.5, label="Monte Carlo, 2000 draws")
a.axvspan(580, 1070, color=BLUE, alpha=0.07, lw=0); a.text(0.03, 0.75, "calibration\nrange", transform=a.transAxes, fontsize=7, color=BLUE, va="top")
a.set(xlabel="Ti-in-zircon temperature (°C)", ylabel="1σ from 5 % error on Ti (°C)"); a.legend(fontsize=7, loc="lower right")
a.set_title("(a)", loc="left", weight="bold", fontsize=9)
a = ax[1]; a.loglog(ns, np.array(spread) / sd10 * 100, "o-", color=BLUE, ms=5, mec="k", mew=0.5, label="40 repeated runs")
a.loglog(ns, 100 / np.sqrt(2 * (ns - 1)), "--", color=GREY, lw=1, label=r"$1/\sqrt{2(N-1)}$")
a.set(xlabel="Number of draws, N", ylabel="Scatter of estimated 1σ (%)"); a.legend(fontsize=7); a.set_title("(b)", loc="left", weight="bold", fontsize=9)
save(fig, "Figure_4")
facts["mc"] = {"max_rel_diff_vs_linear_pct": float(np.max(np.abs(mc - lin) / lin) * 100), "scatter_pct_at_500": float(spread[4] / sd10 * 100)}

# ---- coupled solution for the Brey et al. (1990) runs: P and T found together, the run conditions are not given to the solver
o = {k: [] for k in ("Opx Ca", "Opx Al", "Opx Cr", "Opx Na", "Opx Mg", "Opx Fe", "Garnet Ca", "Garnet Mg", "Garnet Fe", "Garnet Mn", "Garnet Al", "Garnet Cr")}
for _, p_, t_, (oca, oal, ocr, ona, omg), (xca, gal, gcr, xmn, gmg) in TB.BREY_RUNS:
    mf = 2 - oca - ona; ca_, mn_ = 3 * xca, 3 * xmn; rest = 3 - ca_ - mn_
    for k_, v in zip(o, (oca, oal, ocr, ona, mf * omg / 100, mf * (1 - omg / 100), ca_, rest * gmg / 100, rest * (1 - gmg / 100), mn_, gal, gcr)): o[k_].append(v)
cols_ = {k_: k_ for k_ in o}; arr_ = lambda c: np.asarray(o[c], float); facts["coupled"] = {}
for start in (1.0, 10.0, 60.0):
    Tc, Pc, itc = TB.solve_pt("Ca-in-orthopyroxene (Brey & Kohler 1990)", "Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)", cols_, arr_, dict, p0=start)
    facts["coupled"][f"start_{start:g}_kbar"] = {"iterations": int(itc), "converged": int(np.isfinite(Tc).sum()), "dT_mean": float(np.mean(Tc - runs[:, 1])),
        "dT_sd": float(np.std(Tc - runs[:, 1], ddof=1)), "dP_mean_GPa": float(np.mean(Pc - runs[:, 0]) / 10), "dP_sd_GPa": float(np.std(Pc - runs[:, 0], ddof=1) / 10)}

# ---- coupled Monte Carlo against first-order propagation through the coupled solution (central differences, 2 % on every input)
TM_, PM_ = "Ca-in-orthopyroxene (Brey & Kohler 1990)", "Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)"
solve_ = lambda src: TB.solve_pt(TM_, PM_, cols_, lambda c: np.asarray(src[c], float), dict, n_iter=400, tol=1e-8)[:2]
J = np.zeros((2, len(TB.BREY_RUNS), len(o)))
for j, k_ in enumerate(o):
    x_ = np.asarray(o[k_], float); (Tu, Pu), (Td, Pd) = solve_({**o, k_: x_ * (1 + 1e-5)}), solve_({**o, k_: x_ * (1 - 1e-5)})
    J[0, :, j], J[1, :, j] = (Tu - Td) / 2e-5 * 0.02, (Pu - Pd) / 2e-5 * 0.02
cv = np.einsum("ain,bin->abi", J, J); sTl, sPl = np.sqrt(cv[0, 0]), np.sqrt(cv[1, 1])
sT_, sP_, r_ = TB.solve_pt_mc(TM_, PM_, cols_, arr_, dict, rel=0.02, n=5000, seed=3)
facts["coupled_mc"] = {"draws": 5000, "max_rel_diff_sT_pct": float(np.max(np.abs(sT_ / sTl - 1)) * 100),
                       "max_rel_diff_sP_pct": float(np.max(np.abs(sP_ / sPl - 1)) * 100), "max_abs_diff_rho": float(np.max(np.abs(r_ - cv[0, 1] / sTl / sPl))),
                       "rho_range": [float(np.min(r_)), float(np.max(r_))], "sT_range": [float(np.min(sT_)), float(np.max(sT_))],
                       "sP_range_GPa": [float(np.min(sP_) / 10), float(np.max(sP_) / 10)]}

# ---- timings (one core)
n = 1000; rs = np.random.default_rng(0)
liq = {"SiO2": 47.05, "TiO2": 0.89, "Al2O3": 16.11, "FeO": 7.96, "MnO": 0.15, "MgO": 12.78, "CaO": 11.13, "Na2O": 2.18, "K2O": 0.04}
cx = {"SiO2": 52.5, "TiO2": 0.33, "Al2O3": 1.58, "FeO": 9.89, "MnO": 0.24, "MgO": 13.29, "CaO": 22.5, "Na2O": 0.37, "Cr2O3": 0.05}
sheet = {**{k: v * (1 + 0.01 * rs.standard_normal(n)) for k, v in liq.items()}, **{f"Cpx {k}": v * (1 + 0.01 * rs.standard_normal(n)) for k, v in cx.items()}}
arr = lambda c: np.asarray(sheet[c], float); ph = lambda p=False: TB.phase_oxides(list(sheet), arr, p)
t0 = time.perf_counter(); Tt, Pp, it = TB.solve_pt("Clinopyroxene-liquid T (Putirka 2008 Eq 33)", "Clinopyroxene-liquid P (Putirka 2008 Eq 31)", {}, arr, ph)
facts["solve_pt_1000_rows_s"] = time.perf_counter() - t0; facts["solve_pt_iterations"] = int(it); facts["solve_pt_converged"] = int(np.isfinite(Tt).sum())
t0 = time.perf_counter(); TB.monte_carlo("Clinopyroxene-liquid T (Putirka 2008 Eq 33)", {"P (kbar)": 5.0}, arr, ph, n, rel=0.02, n=500)
facts["mc_500x1000_s"] = time.perf_counter() - t0
p = E[22]; t0 = time.perf_counter(); FT.two_oxide_wt(p["spn"], p["rhm"], p["P"]); facts["fe_ti_one_pair_s"] = time.perf_counter() - t0
facts["methods"] = len(TB.METHODS); th, ba = TB.coupled_pairs(); facts["pairs"] = [len(th), len(ba), len(th) * len(ba)]; facts["ranges"] = len(TB.VALID)
json.dump(facts, open(OUT / "facts.json", "w"), indent=1); print(json.dumps(facts, indent=1))
