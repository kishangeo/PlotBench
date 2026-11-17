"""PlotBench plot types, part 5: raincloud plots and geochronology (isochrons, U-Pb concordia, weighted mean, detrital ages).
Importing this module registers them in plots.PLOT_TYPES.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from matplotlib.ticker import MaxNLocator

from . import plots as P
from . import geochron as G


def _ax(fig): return P._ax(fig)


def _f(v): return np.asarray(v, float)


def raincloud(fig, x, ys, names, xname, extra):
    """Each Y column one group: half violin (density), narrow box plot and the jittered points, side by side."""
    from scipy.stats import gaussian_kde
    ax = _ax(fig); rng = np.random.default_rng(0)
    for i, (y, n) in enumerate(zip(ys, names)):
        v = _f(y); v = v[np.isfinite(v)]
        if not len(v): continue
        c = f"C{i % 10}"
        if len(v) > 2 and np.ptp(v) > 0:
            g = np.linspace(v.min() - 0.1 * np.ptp(v), v.max() + 0.1 * np.ptp(v), 200); d = gaussian_kde(v)(g); d = 0.38 * d / d.max()
            ax.fill_betweenx(g, i + 0.08, i + 0.08 + d, color=c, alpha=0.45, lw=0, label="_cloud")
        ax.boxplot([v], positions=[i], widths=0.1, showfliers=False, patch_artist=True, boxprops=dict(facecolor="white"), medianprops=dict(color=c))
        ax.plot(i - 0.22 + rng.uniform(-0.07, 0.07, len(v)), v, "o", ms=3.5, color=c, alpha=0.7, label=n)
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names); ax.set_xlim(-0.5, len(names) - 0.4)
    ax.set_ylabel(names[0] if len(names) == 1 else "")


def _errs(ys, need=3):
    """Y ratio, sigma X, sigma Y and (optional) rho from the selected columns, as in IsoplotR's input tables."""
    if len(ys) < need: raise ValueError("Select the Y ratio, then the 1-sigma error of X and of Y (and optionally their correlation rho).")
    rho = _f(ys[3]) if len(ys) > 3 else np.zeros(len(ys[0]))
    return _f(ys[0]), _f(ys[1]), _f(ys[2]), np.nan_to_num(rho)


def _ellipses(ax, x, y, sx, sy, rho, color="C0"):
    from matplotlib.patches import Polygon
    first = True
    for xi, yi, a, b, r in zip(x, y, sx, sy, rho):
        if not all(np.isfinite([xi, yi, a, b])): continue
        if a > 0 and b > 0:
            ex, ey = G.ellipse(xi, yi, a, b, float(np.clip(r, -0.999, 0.999)))
            ax.add_patch(Polygon(np.c_[ex, ey], closed=True, fc=color, ec="k", lw=0.6, alpha=0.35, label="data (95% ellipses)" if first else "_e"))
        else: ax.plot([xi], [yi], "o", color=color, ms=4, label="_p")
        first = False
    ax.plot(x, y, "none", label="_extent")  # lets autoscale see the points
    ax.autoscale_view()


def _concordia(fig, x, ys, names, xname, extra, tw):
    ax = _ax(fig); X = _f(x); Y, sx, sy, rho = _errs(ys)
    ok = np.isfinite(X) & np.isfinite(Y)
    t = (G.age68(1 / X[ok]) if tw else G.age68(Y[ok])); t = t[np.isfinite(t) & (t > 0)]
    lo, hi = (max(t.min() * 0.85, 0.5), t.max() * 1.15) if len(t) else (1.0, 4500.0)
    tt = np.linspace(lo, hi, 400); cx, cy = (G.tera_wasserburg(tt) if tw else G.wetherill(tt))
    ax.plot(cx, cy, "-", color="0.25", lw=1.2, label="Concordia", zorder=1)
    ticks = [v for v in MaxNLocator(7).tick_values(lo, hi) if lo <= v <= hi and v > 0]
    px, py = (G.tera_wasserburg(ticks) if tw else G.wetherill(ticks))
    ax.plot(px, py, "o", color="0.25", ms=4, mfc="white", label="_ticks", zorder=2)
    for a, b, v in zip(px, py, ticks): ax.annotate(f"{v:g} Ma", (a, b), xytext=(4, -10 if tw else 4), textcoords="offset points", fontsize=8, color="0.3")
    _ellipses(ax, X, Y, sx, sy, rho)
    if tw: ax.set_xlabel(xname or "238U/206Pb"); ax.set_ylabel(names[0] if names else "207Pb/206Pb")
    else: ax.set_xlabel(xname or "207Pb/235U"); ax.set_ylabel(names[0] if names else "206Pb/238U")
    a68 = G.age68(1 / X[ok] if tw else Y[ok]); s68 = (sx[ok] / X[ok] if tw else sy[ok] / (1 + Y[ok])) / G.L238 / 1e6
    try:
        w = G.weighted_mean(a68, s68); txt = f"Weighted mean 206Pb/238U age\n{w['mean']:.1f} \u00b1 {2 * w['s_mean']:.1f} Ma (2\u03c3), MSWD = {w['mswd']:.2f}, n = {w['n']}"
        if not tw:  # Ludwig (1998) concordia age
            c = G.concordia_age(X[ok], sx[ok], Y[ok], sy[ok], rho[ok])
            txt += (f"\nConcordia age {c['age']:.1f} \u00b1 {c['age_2s']:.1f} Ma (2\u03c3)\nMSWD of concordance {c['mswd_conc']:.2f} (p = {c['p_conc']:.2f}), "
                    f"of equivalence {c['mswd_eq']:.2f}")
            cx_, cy_ = G.wetherill(c["age"]); ax.plot([cx_], [cy_], "*", ms=12, color="firebrick", mec="k", label="Concordia age")
        ax.text(0.03, 0.97, txt, transform=ax.transAxes, va="top", fontsize=8, bbox=dict(fc="white", ec="0.7"))
    except (ValueError, np.linalg.LinAlgError): pass
    ax.set_title("Tera-Wasserburg concordia" if tw else "Wetherill concordia")


def concordia_wetherill(fig, x, ys, names, xname, extra): _concordia(fig, x, ys, names, xname, extra, False)
def concordia_tw(fig, x, ys, names, xname, extra): _concordia(fig, x, ys, names, xname, extra, True)


def isochron(fig, x, ys, names, xname, extra):
    """York regression through parent/daughter ratios with their errors, with the age for the chosen decay system."""
    ax = _ax(fig); X = _f(x); Y, sx, sy, rho = _errs(ys); system = extra.get("system", "Rb-Sr")
    if system not in G.SYSTEMS: system = "Rb-Sr"
    _ellipses(ax, X, Y, sx, sy, rho)
    f = G.york(X, sx, Y, sy, rho); a = G.isochron_age(f, system)
    ok = np.isfinite(X); xs = np.linspace(min(0.0, np.nanmin(X[ok])), np.nanmax(X[ok]) * 1.05, 50)
    ax.plot(xs, f["intercept"] + f["slope"] * xs, "-", color="firebrick", lw=1.3, label="York fit")
    lam, xn, yn, ref = G.SYSTEMS[system]
    txt = (f"{system} isochron: {a['age']:.1f} ± {a['age_2s']:.1f} Ma (2σ)" + (f"; ± {a['age_2s_mswd']:.1f} with √MSWD" if f["mswd"] > 1 else "")
           + f"\nInitial {yn} = {a['initial']:.6f} ± {a['initial_2s']:.6f}\nMSWD = {f['mswd']:.2f}, p = {f['p']:.2f}, n = {f['n']}"
           + f"\nλ = {lam:.4e} /yr ({ref})")
    ax.text(0.03, 0.97, txt, transform=ax.transAxes, va="top", fontsize=8, bbox=dict(fc="white", ec="0.7"))
    ax.set_xlabel(xname or xn); ax.set_ylabel(names[0] if names else yn)


def weighted_mean_plot(fig, x, ys, names, xname, extra):
    """Ages (or any values) with 2-sigma bars, the weighted mean and its 2-sigma band; values off the mean are red."""
    if len(ys) < 2: raise ValueError("Select the values (e.g. ages) and their 1-sigma errors.")
    ax = _ax(fig); v, s = _f(ys[0]), _f(ys[1]); w = G.weighted_mean(v, s); i = np.arange(1, len(v) + 1)
    out = np.abs(v - w["mean"]) > 2 * np.sqrt(s ** 2 + w["s_mean"] ** 2)
    ax.axhspan(w["mean"] - 2 * w["s_mean"], w["mean"] + 2 * w["s_mean"], color="C0", alpha=0.2, lw=0, label="_band")
    ax.axhline(w["mean"], color="C0", lw=1.2, label="Weighted mean")
    for k, bad in ((~out, False), (out, True)):
        ax.errorbar(i[k], v[k], yerr=2 * s[k], fmt="s", ms=4, color="firebrick" if bad else "k", capsize=2, label="Off the mean (> 2σ)" if bad else names[0])
    ax.text(0.03, 0.97, f"Mean = {w['mean']:.4g} ± {2 * w['s_mean']:.2g} (2σ)\nMSWD = {w['mswd']:.2f}, p = {w['p']:.2f}, n = {w['n']}",
            transform=ax.transAxes, va="top", fontsize=8, bbox=dict(fc="white", ec="0.7"))
    if x is not None and len(x) == len(v) and np.asarray(x).dtype.kind not in "fiu": ax.set_xticks(i); ax.set_xticklabels([str(t) for t in x], rotation=60, fontsize=7)
    ax.set_xlabel(xname or "Analysis"); ax.set_ylabel(names[0])


def age_kde(fig, x, ys, names, xname, extra):
    """Detrital ages: histogram, kernel density (KDE) and, with an error column, the probability density plot (PDP)."""
    ax = _ax(fig); a = _f(ys[0]); a = a[np.isfinite(a)]
    if not len(a): raise ValueError("No ages.")
    g = np.linspace(max(a.min() - 0.1 * np.ptp(a) - 10, 0), a.max() + 0.1 * np.ptp(a) + 10, 1000)
    ax.hist(a, bins=extra.get("bins", "auto"), density=True, color="0.85", ec="0.5", label="_hist")
    ax.plot(g, G.kde(a, g, extra.get("bandwidth")), "-", color="C0", lw=1.5, label="KDE")
    if len(ys) > 1: ax.plot(g, G.pdp(ys[0], ys[1], g), "--", color="C3", lw=1.2, label="PDP")
    ax.plot(a, np.zeros_like(a), "|", color="k", ms=10, label="_rug")
    ax.set_xlabel(names[0]); ax.set_ylabel("Density"); ax.set_title(f"n = {len(a)}")


def age_cad(fig, x, ys, names, xname, extra):
    """Cumulative age distribution of one or more samples (each Y column a sample), for comparing detrital populations."""
    ax = _ax(fig)
    for y, n in zip(ys, names):
        a = np.sort(_f(y)[np.isfinite(_f(y))])
        if len(a): ax.step(np.r_[a[0], a], np.r_[0, np.arange(1, len(a) + 1) / len(a)], where="post", label=n)
    ax.set_xlabel("Age (Ma)" if len(names) > 1 else names[0]); ax.set_ylabel("Cumulative fraction"); ax.set_ylim(0, 1.02)


P.PLOT_TYPES.update({
    "Raincloud (violin + box + points)": (raincloud, False, "Y... (each column a group)"),
    "Concordia (Wetherill)": (concordia_wetherill, True, "207Pb/235U (X) + 206Pb/238U, σX, σY, rho"),
    "Concordia (Tera-Wasserburg)": (concordia_tw, True, "238U/206Pb (X) + 207Pb/206Pb, σX, σY, rho"),
    "Isochron (York regression)": (isochron, True, "Parent ratio (X) + daughter ratio, σX, σY, rho"),
    "Weighted Mean (ages)": (weighted_mean_plot, True, "Labels (X) + value, 1σ error"),
    "Detrital Age KDE + PDP": (age_kde, False, "Ages (+ 1σ errors for the PDP)"),
    "Cumulative Age Distribution": (age_cad, False, "Ages, one column per sample"),
})
GEOCHRON = ["Concordia (Wetherill)", "Concordia (Tera-Wasserburg)", "Isochron (York regression)", "Weighted Mean (ages)",
            "Detrital Age KDE + PDP", "Cumulative Age Distribution"]


def sample(kind, r=np.random.default_rng(1)):
    """Small data for the gallery thumbnails and tests: (x, ys, names, extra)."""
    if kind.startswith("Concordia"):
        t = r.uniform(480, 520, 8); x75, y68 = G.wetherill(t); x75 *= 1 + r.normal(0, 0.004, 8); y68 *= 1 + r.normal(0, 0.003, 8)
        if "Tera" in kind:
            X = 1 / y68; Y = x75 / (G.U85 * y68); return X, [Y, X * 0.008, Y * 0.01, np.full(8, 0.2)], ["207Pb/206Pb", "s X", "s Y", "rho"], {}
        return x75, [y68, x75 * 0.01, y68 * 0.008, np.full(8, 0.8)], ["206Pb/238U", "s X", "s Y", "rho"], {}
    if kind == "Isochron (York regression)":
        rb = np.array([0.2, 0.9, 1.6, 2.4, 3.3, 4.1]); sr = 0.7045 + rb * np.expm1(G.SYSTEMS["Rb-Sr"][0] * 1.2e9) + r.normal(0, 2e-5, 6)
        return rb, [sr, rb * 0.01, np.full(6, 3e-5)], ["87Sr/86Sr", "s X", "s Y"], {"system": "Rb-Sr"}
    if kind == "Weighted Mean (ages)": return np.array([f"z{i}" for i in range(10)]), [r.normal(1850, 6, 10), np.full(10, 5.0)], ["Age (Ma)", "1s"], {}
    if kind == "Detrital Age KDE + PDP":
        a = np.r_[r.normal(550, 30, 40), r.normal(1100, 50, 30), r.normal(2500, 60, 20)]; return None, [a, a * 0.02], ["Age (Ma)", "1s"], {}
    if kind == "Cumulative Age Distribution": return None, [np.r_[r.normal(550, 30, 40), r.normal(1100, 50, 30)], r.normal(900, 300, 60)], ["Sample A", "Sample B"], {}
    if kind.startswith("Raincloud"): return None, [r.normal(0, 1, 60), r.normal(1, 0.7, 60), r.gamma(2, 1, 60)], ["a", "b", "c"], {}
    return None


HELP = {
    "Raincloud (violin + box + points)": ("Each group's distribution three ways: a half violin (density), a box plot and every point.",
                                          "Each column is one group; select the columns to compare.", [["Group A", "Group B"], ["10.2", "12.1"], ["9.8", "11.7"]], ""),
    "Concordia (Wetherill)": ("U-Pb analyses as 95% error ellipses on the Wetherill concordia, with the weighted mean 206Pb/238U age.",
                              "207Pb/235U as X, then 206Pb/238U, the 1-sigma absolute errors of X and Y, and optionally rho. Select the four or five columns.",
                              [["207/235 (X)", "206/238", "s 207/235", "s 206/238", "rho"], ["0.640", "0.0809", "0.0064", "0.00065", "0.8"]],
                              "Decay constants of Jaffey et al. (1971); 238U/235U = 137.818 (Hiess et al. 2012). Errors as percentages: convert with a column formula first."),
    "Concordia (Tera-Wasserburg)": ("U-Pb analyses on the Tera-Wasserburg concordia (good for young or common-Pb-bearing zircon).",
                                    "238U/206Pb as X, then 207Pb/206Pb, the 1-sigma absolute errors and optionally rho.",
                                    [["238/206 (X)", "207/206", "s X", "s Y", "rho"], ["12.36", "0.0573", "0.10", "0.0006", "0.2"]], ""),
    "Isochron (York regression)": ("Isochron age from the York et al. (2004) regression with errors in both ratios and their correlation.",
                                   "Parent ratio (87Rb/86Sr, 147Sm/144Nd, 176Lu/177Hf or 187Re/188Os) as X, then the daughter ratio, the 1-sigma "
                                   "absolute errors of X and Y and optionally rho. Choose the decay system in Edit Plot (extra 'system').",
                                   [["87Rb/86Sr (X)", "87Sr/86Sr", "s X", "s Y"], ["0.90", "0.72027", "0.009", "0.00003"]],
                                   "Analysis > Geochronology gives the same result as a report."),
    "Weighted Mean (ages)": ("Values with 2-sigma bars, the inverse-variance weighted mean with its 2-sigma band, MSWD and p.",
                             "Sample or spot labels as X, then the values and their 1-sigma errors.", [["Spot (X)", "Age (Ma)", "1s"], ["z1", "1851", "5"]], ""),
    "Detrital Age KDE + PDP": ("Detrital ages as a histogram, a kernel density estimate (bandwidth by least-squares cross-validation) and, with errors, a probability density plot.",
                               "One column of ages; add a 1-sigma error column next to it for the PDP.", [["Age (Ma)", "1s"], ["552", "11"], ["1103", "22"]], ""),
    "Cumulative Age Distribution": ("Cumulative age distributions of several samples, to compare detrital populations.",
                                    "One column of ages per sample.", [["Sample A", "Sample B"], ["552", "910"], ["1103", "870"]], ""),
}

from . import plothelp as _PH  # noqa: E402  (the gallery and the manual show these too)
_PH.HELP.update(HELP)


# ---------------------------------------------------------------- principal component analysis graphs
def _pca(ys, extra):
    """Standardised PCA of the selected columns (rows with a gap are left out). Returns scores, loadings, % variance, row mask."""
    X = np.column_stack([_f(y) for y in ys]); ok = np.all(np.isfinite(X), axis=1)
    if X.shape[1] < 2 or ok.sum() < 3: raise ValueError("PCA needs at least two variable columns and three complete rows.")
    Z = X[ok]; sd = Z.std(0, ddof=1); sd[sd == 0] = 1; Z = (Z - Z.mean(0)) / sd
    u, s, vt = np.linalg.svd(Z, full_matrices=False); ev = s ** 2 / (len(Z) - 1)
    load = vt.T * np.sqrt(ev)  # correlation of each variable with each component
    return Z @ vt.T, load, ev / ev.sum() * 100, ev, ok


def _pcs(extra, n):
    a, b = (int(v) - 1 for v in extra.get("pcs", (1, 2)))
    return (min(max(a, 0), n - 1), min(max(b, 0), n - 1))


def _groups_of(extra, ok, n):
    g = extra.get("groups")
    return np.asarray(g, object)[ok] if g is not None and len(g) == len(ok) else np.full(n, None, object)


def _score_points(ax, S, i, j, groups, ellipses=True):
    from scipy import stats
    kinds = [k for k in dict.fromkeys(groups) if k is not None and not (isinstance(k, float) and np.isnan(k))]
    if not kinds: ax.plot(S[:, i], S[:, j], "o", ms=5, color="C0", mec="k", mew=0.4, label="Samples"); return
    for c, k in enumerate(kinds):
        m = np.array([gg == k for gg in groups]); col = f"C{c % 10}"
        ax.plot(S[m, i], S[m, j], "o", ms=5, color=col, mec="k", mew=0.4, label=str(k), gid=f"pbgroup:{k}")
        if ellipses and m.sum() > 2:  # 95% ellipse of the group's scores
            cov = np.cov(S[m, i], S[m, j]); val, vec = np.linalg.eigh(cov); t = np.linspace(0, 2 * np.pi, 80)
            e = vec @ (np.sqrt(np.clip(val, 0, None) * stats.chi2.ppf(0.95, 2))[:, None] * np.vstack([np.cos(t), np.sin(t)]))
            ax.plot(S[m, i].mean() + e[0], S[m, j].mean() + e[1], "-", color=col, lw=0.8, label="_ell")


def _pc_axes(ax, pct, i, j):
    ax.axhline(0, color="0.75", lw=0.7, zorder=0, label="_z"); ax.axvline(0, color="0.75", lw=0.7, zorder=0, label="_z")
    ax.set_xlabel(f"PC{i + 1} ({pct[i]:.1f}% of variance)"); ax.set_ylabel(f"PC{j + 1} ({pct[j]:.1f}% of variance)")


def _arrow_labels(ax, xs, ys, names, color):
    """Names at the arrow tips, set on the outer side of each tip; tips closer than 7% of the plot size share one stacked label,
    so names of variables pointing the same way never print on top of each other."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float); span = max(np.ptp(np.r_[xs, 0]), np.ptp(np.r_[ys, 0]), 1e-12)
    left = list(np.argsort(-np.hypot(xs, ys)))
    while left:
        a = left.pop(0); grp = [a] + [b for b in left if np.hypot(xs[b] - xs[a], ys[b] - ys[a]) < 0.07 * span]
        left = [b for b in left if b not in grp]
        ang = np.arctan2(ys[a], xs[a]); c, s_ = np.cos(ang), np.sin(ang)
        ax.annotate("\n".join(str(names[g]) for g in grp), (xs[a], ys[a]), xytext=(6 * c, 6 * s_), textcoords="offset points",
                    color=color, fontsize=8, ha="left" if c > 0.35 else "right" if c < -0.35 else "center",
                    va="bottom" if s_ > 0.35 else "top" if s_ < -0.35 else "center", annotation_clip=False)


def pca_biplot(fig, x, ys, names, xname, extra):
    """Scores of the samples (points, coloured by group) and loadings of the variables (arrows) on two principal components."""
    ax = _ax(fig); S, L, pct, ev, ok = _pca(ys, extra); i, j = _pcs(extra, S.shape[1])
    _score_points(ax, S, i, j, _groups_of(extra, ok, len(S)))
    k = 0.85 * np.max(np.abs(S[:, [i, j]])) / max(np.max(np.abs(L[:, [i, j]])), 1e-12)  # arrows scaled to the score cloud
    for v, n in zip(L, names):
        ax.annotate("", (v[i] * k, v[j] * k), (0, 0), arrowprops=dict(arrowstyle="->", color="firebrick", lw=1.1), annotation_clip=False)
    _arrow_labels(ax, L[:, i] * k, L[:, j] * k, names, "firebrick")
    ax.plot(L[:, i] * k * 1.15, L[:, j] * k * 1.15, "none", label="_tips")  # the axes take in every arrow and its name
    _pc_axes(ax, pct, i, j); ax.set_title("PCA biplot (standardised variables)")


def pca_scores(fig, x, ys, names, xname, extra):
    """Sample scores on two components with a 95% ellipse for each group: which samples are alike."""
    ax = _ax(fig); S, L, pct, ev, ok = _pca(ys, extra); i, j = _pcs(extra, S.shape[1])
    _score_points(ax, S, i, j, _groups_of(extra, ok, len(S))); _pc_axes(ax, pct, i, j); ax.set_title("PCA scores")


def pca_loadings(fig, x, ys, names, xname, extra):
    """Correlation circle: each variable's correlation with two components; near the circle = well represented."""
    ax = _ax(fig); S, L, pct, ev, ok = _pca(ys, extra); i, j = _pcs(extra, S.shape[1]); t = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(t), np.sin(t), "-", color="0.5", lw=0.8, label="_c"); ax.plot(0.5 * np.cos(t), 0.5 * np.sin(t), ":", color="0.7", lw=0.7, label="_c")
    for v, n in zip(L, names):
        ax.annotate("", (v[i], v[j]), (0, 0), arrowprops=dict(arrowstyle="->", color="C0", lw=1.2), annotation_clip=False)
    _arrow_labels(ax, L[:, i], L[:, j], names, "black")
    ax.set_xlim(-1.15, 1.15); ax.set_ylim(-1.15, 1.15); ax.set_aspect("equal"); _pc_axes(ax, pct, i, j); ax.set_title("PCA loadings (correlation circle)")


def pca_scree(fig, x, ys, names, xname, extra):
    """Variance explained by each component (bars), cumulative % (line) and the Kaiser line (eigenvalue 1)."""
    ax = _ax(fig); S, L, pct, ev, ok = _pca(ys, extra); k = np.arange(1, len(ev) + 1)
    ax.bar(k, ev, color="C0", label="Eigenvalue"); ax.axhline(1, color="firebrick", ls="--", lw=1, label="Kaiser criterion (eigenvalue 1)")
    ax.set_xlabel("Principal component"); ax.set_ylabel("Eigenvalue"); ax.set_xticks(k)
    a2 = ax.twinx(); a2.plot(k, np.cumsum(pct), "o-", color="C1", label="Cumulative %"); a2.set_ylabel("Cumulative variance (%)"); a2.set_ylim(0, 105)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, loc="center right", fontsize=8)
    ax._pb_custom_legend = True; ax.set_title("PCA scree plot")


PCA_TYPES = {"PCA Biplot (scores + loadings)": pca_biplot, "PCA Scores (samples)": pca_scores, "PCA Loadings (correlation circle)": pca_loadings,
             "PCA Scree Plot": pca_scree}
P.PLOT_TYPES.update({k: (v, False, "Two or more variable columns (+ a group column)") for k, v in PCA_TYPES.items()})
_PCA_HELP = ("Select two or more numeric columns (the variables, e.g. oxides or trace elements); each row is one sample. Variables are "
             "standardised (mean 0, SD 1) so units do not matter. A text column such as Rock type colours the samples (Graph > Group Samples By).",
             [["Sample", "SiO2", "MgO", "CaO", "Rb", "Rock type"], ["A1", "51.2", "7.1", "10.3", "12", "basalt"]])
_PH.HELP.update({
    "PCA Biplot (scores + loadings)": ("Samples (points) and variables (arrows) on the first two principal components. Samples near each other are "
                                       "alike; an arrow points to where samples rich in that variable lie; arrows close together are correlated.", *_PCA_HELP,
                                       "Analysis > Statistics > Principal Component Analysis gives the numbers."),
    "PCA Scores (samples)": ("Sample scores on two components with a 95% ellipse per group: separate clusters = different populations.", *_PCA_HELP, ""),
    "PCA Loadings (correlation circle)": ("Each variable's correlation with two components. Arrows near the circle are well shown by these two components; "
                                          "short arrows need other components.", *_PCA_HELP, ""),
    "PCA Scree Plot": ("Eigenvalue of each component and the cumulative % of variance: keep the components before the 'elbow', or those with "
                       "eigenvalue above 1 (Kaiser).", *_PCA_HELP, ""),
})
GEOCHRON_PCA = list(PCA_TYPES)
from . import plots4 as _P4  # noqa: E402
_P4.GROUPABLE.update(PCA_TYPES)  # colour the samples by a text column, as on the geochemistry diagrams


# ---------------------------------------------------------------- Pearce (2008) basalt projections (lines digitised from his Fig. 2)
PEARCE08 = {
    "Pearce 2008: Th/Yb vs Nb/Yb": {"y": "Th", "ylim": (0.01, 10), "ylabel": "Th/Yb", "scale": 1.0,
        "lines": [((0.1, 0.01), (72.8, 10.0)), ((0.39, 0.01), (100, 4.7))], "dashed": [((0.1, 1.23), (0.61, 10.0))],
        "labels": [(0.75, 0.042, "N-MORB"), (4.0, 0.27, "E-MORB"), (23, 1.9, "OIB"), (0.3, 3.5, "volcanic arc array"), (25, 0.6, "MORB-OIB array")]},
    "Pearce 2008: TiO2/Yb vs Nb/Yb": {"y": "TiO2", "ylim": (0.1, 10), "ylabel": "TiO2 (wt%)/Yb (ppm)", "scale": 1.0,
        "lines": [((0.1, 2.11), (100, 2.88)), ((0.1, 0.58), (100, 0.80)), ((0.1, 0.258), (100, 0.35))],
        "dashed": [((9.6, 2.44), (18.5, 0.79)), ((1.45, 0.29), (1.45, 0.64))],
        "labels": [(0.6, 1.3, "OIB array (deep melting)"), (8, 0.48, "MORB array (shallow melting)"), (6, 2.0, "Th"), (16, 2.0, "Alk"),
                   (1.15, 0.3, "N"), (1.9, 0.3, "E")]},
}


def pearce08(kind):
    d = PEARCE08[kind]

    def draw(fig, x, ys, names, xname, extra):
        nb, yb, el = (_P4._col(x, ys, names, xname, e) for e in ("Nb", "Yb", d["y"]))
        if nb is None or yb is None or el is None: raise ValueError(f"Select columns named {d['y']}, Nb and Yb (ppm; TiO2 in wt%).")
        with np.errstate(all="ignore"): xv, yv = nb / yb, el / yb
        ax = _ax(fig); import matplotlib as _m; ink = _m.rcParams["axes.edgecolor"]
        if "Th" == d["y"]: ax.fill([0.1, 72.8, 100, 100, 0.39], [0.01, 10, 10, 4.7, 0.01], color="0.88", lw=0, zorder=0, label="_array")
        else: ax.fill([0.1, 100, 100, 0.1], [0.258, 0.35, 0.80, 0.58], color="0.88", lw=0, zorder=0, label="_array")
        for a, b in d["lines"]: ax.plot([a[0], b[0]], [a[1], b[1]], "-", color=ink, lw=1.1, label="_boundary")
        for a, b in d["dashed"]: ax.plot([a[0], b[0]], [a[1], b[1]], "--", color=ink, lw=1.0, label="_boundary")
        for lx, ly, t in d["labels"]: ax.text(lx, ly, t, ha="center", va="center", fontsize=8, color="0.4")
        ok = np.isfinite(xv) & np.isfinite(yv) & (xv > 0) & (yv > 0)
        _P4._samples(ax, xv, yv, extra, "Samples", ok)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.1, 100); ax.set_ylim(*d["ylim"])
        ax.set_xlabel("Nb/Yb"); ax.set_ylabel(d["ylabel"])
        ax.text(0.99, 0.01, "Pearce (2008)", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="0.45", in_layout=False)
    return draw


P.PLOT_TYPES.update({k: (pearce08(k), True, "Th or TiO2, Nb, Yb columns") for k in PEARCE08})
_P4.GROUPABLE.update(PEARCE08)
_PH.HELP.update({
    "Pearce 2008: Th/Yb vs Nb/Yb": ("Crustal input to basalts: oceanic basalts lie in the diagonal MORB-OIB array; arc basalts and crustally contaminated "
        "magmas plot above it (Th added by subduction or the crust). Th and Nb are immobile, so altered and metamorphosed basalts can be used.",
        "One row per basalt with Th, Nb and Yb in ppm in columns named after the elements; select them (a group column colours the samples).",
        [["Sample", "Th", "Nb", "Yb"], ["B-1", "0.12", "2.3", "3.1"]], "Lines digitised from Pearce (2008) Fig. 2a; N-MORB, E-MORB and OIB are marked."),
    "Pearce 2008: TiO2/Yb vs Nb/Yb": ("Melting depth: OIB (deep melting, garnet in the residue) have high TiO2/Yb, MORB low; Nb/Yb separates N- from "
        "E-MORB (1.45, the chondrite value) and tholeiitic from alkalic OIB (dashed line).",
        "One row per basalt with TiO2 (wt%), Nb and Yb (ppm), columns named after the elements.", [["Sample", "TiO2", "Nb", "Yb"], ["B-1", "1.5", "2.3", "3.1"]],
        "Lines digitised from Pearce (2008) Fig. 2b."),
})
