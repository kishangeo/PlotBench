"""PlotBench plot types, part 2. Importing this module registers them in plots.PLOT_TYPES.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from scipy import stats

from . import plots as P
from .plots import _ax, _label, ternary_xy, TERNARY_H


def _fin(y): y = np.asarray(y, float); return y[np.isfinite(y)]


def bland_altman_plot(fig, x, ys, names, xname, extra):
    """Two methods: X = method A, Y = method B. Mean on X, difference on Y, bias and 95% limits of agreement."""
    ax = _ax(fig); a, b = np.asarray(x, float), np.asarray(ys[0], float); m = np.isfinite(a) & np.isfinite(b); a, b = a[m], b[m]
    mean, d = (a + b) / 2, a - b; md, sd = d.mean(), d.std(ddof=1)
    ax.plot(mean, d, "o", mfc="none")
    for v, lab, ls in ((md, f"bias {md:.4g}", "-"), (md + 1.96 * sd, f"+1.96 SD {md + 1.96 * sd:.4g}", "--"), (md - 1.96 * sd, f"-1.96 SD {md - 1.96 * sd:.4g}", "--")):
        ax.axhline(v, color="k", ls=ls, lw=1); ax.text(mean.max(), v, f" {lab}", va="bottom", ha="right", fontsize=8)
    ax.set_xlabel(f"Mean of {xname} and {names[0]}"); ax.set_ylabel(f"{xname} - {names[0]}")


def qq_plot(fig, x, ys, names, xname, extra):
    """Quantile-quantile plot against a chosen distribution (fitted by maximum likelihood)."""
    ax = _ax(fig); dist = getattr(stats, extra.get("dist", "norm"))
    for y, n in zip(ys, names):
        y = np.sort(_fin(y)); par = dist.fit(y) if extra.get("dist", "norm") == "norm" else dist.fit(y, floc=0)
        q = dist.ppf((np.arange(1, len(y) + 1) - 0.5) / len(y), *par); ax.plot(q, y, "o", mfc="none", label=n)
    lo, hi = ax.get_xlim(); ax.plot([lo, hi], [lo, hi], "k--", lw=1); ax.set_xlabel(f"Theoretical quantiles ({extra.get('dist', 'norm')})")
    ax.set_ylabel("Sample quantiles"); _label(ax, ax.get_xlabel(), names, "Sample quantiles")


def pareto(fig, x, ys, names, xname, extra):
    """X = categories, Y = counts: bars sorted descending with cumulative percentage line."""
    ax = _ax(fig); v = np.nan_to_num(np.asarray(ys[0], float)); o = np.argsort(-v); v = v[o]; lab = [str(t) for t in np.asarray(x)[o]]
    ax.bar(range(len(v)), v, color="C0"); ax.set_xticks(range(len(v))); ax.set_xticklabels(lab, rotation=45, ha="right")
    ax2 = ax.twinx(); cum = 100 * np.cumsum(v) / v.sum(); ax2.plot(range(len(v)), cum, "C1-o", ms=4); ax2.set_ylim(0, 105)
    ax2.axhline(80, color="0.5", ls=":", lw=1); ax2.set_ylabel("Cumulative %"); ax.set_ylabel(names[0])


def box_points(fig, x, ys, names, xname, extra):
    ax = _ax(fig); data = [_fin(y) for y in ys]; ax.boxplot(data, labels=names, showfliers=False, widths=0.5)
    rng = np.random.default_rng(0)
    for k, d in enumerate(data, 1): ax.plot(k + rng.uniform(-0.15, 0.15, len(d)), d, "o", ms=3, alpha=0.6, color=f"C{(k - 1) % 10}")


def hist_normal(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for k, (y, n) in enumerate(zip(ys, names)):
        y = _fin(y); cnt, edges, _ = ax.hist(y, bins=extra.get("bins", "auto"), alpha=0.5, edgecolor="k", color=f"C{k}", label=n)
        mu, sd = y.mean(), y.std(ddof=1); t = np.linspace(edges[0], edges[-1], 300); w = edges[1] - edges[0]
        ax.plot(t, stats.norm.pdf(t, mu, sd) * len(y) * w, color=f"C{k}", lw=2, label=f"normal fit (mean {mu:.4g}, SD {sd:.4g})")
    ax.set_xlabel(names[0] if len(names) == 1 else "Value"); ax.set_ylabel("Count"); ax.legend(fontsize=8)


def marginal(fig, x, ys, names, xname, extra):
    """Scatter with histograms of X and Y on the margins."""
    fig.clear(); gs = fig.add_gridspec(4, 4); ax = fig.add_subplot(gs[1:, :3]); top = fig.add_subplot(gs[0, :3], sharex=ax)
    right = fig.add_subplot(gs[1:, 3], sharey=ax); xv = np.asarray(x, float)
    for k, (y, n) in enumerate(zip(ys, names)):
        m = np.isfinite(xv) & np.isfinite(y); ax.plot(xv[m], y[m], "o", ms=4, mfc="none", color=f"C{k}", label=n)
        right.hist(y[m], bins="auto", orientation="horizontal", alpha=0.5, color=f"C{k}")
    top.hist(xv[np.isfinite(xv)], bins="auto", color="0.6"); top.tick_params(labelbottom=False); right.tick_params(labelleft=False)
    ax.set_xlabel(xname); ax.set_ylabel(names[0] if len(names) == 1 else "")
    if len(names) > 1: ax.legend()


def kde2d(fig, x, ys, names, xname, extra):
    ax = _ax(fig); xv, yv = np.asarray(x, float), np.asarray(ys[0], float); m = np.isfinite(xv) & np.isfinite(yv); xv, yv = xv[m], yv[m]
    try: k = stats.gaussian_kde(np.vstack([xv, yv]))
    except np.linalg.LinAlgError: raise ValueError("The points lie on a line, so a 2-D density cannot be estimated.") from None
    X, Y = np.meshgrid(np.linspace(xv.min(), xv.max(), 120), np.linspace(yv.min(), yv.max(), 120))
    Z = k(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape); cs = ax.contourf(X, Y, Z, levels=15); ax.contour(X, Y, Z, levels=8, colors="k", linewidths=0.3)
    ax.plot(xv, yv, "k.", ms=1.5, alpha=0.4); fig.colorbar(cs, ax=ax, label="Density"); ax.set_xlabel(xname); ax.set_ylabel(names[0])


def ternary_contour(fig, x, ys, names, xname, extra):
    """A (X), B, C compositions plus a fourth column Z coloured as filled contours on the ternary diagram."""
    if len(ys) < 3: raise ValueError("Ternary contour needs A (X) plus B, C and Z columns.")
    P.ternary(fig, x, ys[:2], names[:2], xname, extra); ax = fig.axes[0]
    px, py = ternary_xy(x, ys[0], ys[1]); z = np.asarray(ys[2], float); m = np.isfinite(px) & np.isfinite(py) & np.isfinite(z)
    cs = ax.tricontourf(px[m], py[m], z[m], levels=12, alpha=0.85, zorder=0); fig.colorbar(cs, ax=ax, label=names[2], shrink=0.7)


def ternary_density(fig, x, ys, names, xname, extra):
    """A, B, C compositions with filled contours of their 2D kernel density: where the samples cluster on the triangle."""
    from scipy.stats import gaussian_kde
    if len(ys) < 2: raise ValueError("Ternary density needs A (X), B and C columns.")
    P.ternary(fig, x, ys[:2], names[:2], xname, extra); ax = fig.axes[0]
    px, py = ternary_xy(x, ys[0], ys[1]); m = np.isfinite(px) & np.isfinite(py)
    if m.sum() < 5: raise ValueError("Ternary density needs at least five complete rows.")
    k = gaussian_kde(np.vstack([px[m], py[m]])); gx, gy = np.meshgrid(np.linspace(0, 1, 160), np.linspace(0, np.sqrt(3) / 2, 140))
    z = k(np.vstack([gx.ravel(), gy.ravel()])).reshape(gx.shape)
    inside = (gy <= np.sqrt(3) * gx + 1e-9) & (gy <= np.sqrt(3) * (1 - gx) + 1e-9); z = np.where(inside, z, np.nan)
    cs = ax.contourf(gx, gy, z, levels=10, cmap=extra.get("cmap", "Blues"), alpha=0.75, zorder=0)
    ax.contour(gx, gy, z, levels=cs.levels[1:], colors="0.35", linewidths=0.5, zorder=0.5)
    fig.colorbar(cs, ax=ax, label="Relative density", shrink=0.7)


def cumulative_probability(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names):
        y = np.sort(_fin(y)); ax.step(y, 100 * np.arange(1, len(y) + 1) / len(y), where="post", label=n)
    ax.set_ylabel("Cumulative percent"); ax.set_xlabel(names[0] if len(names) == 1 else "Value")
    if len(names) > 1: ax.legend()


def grouped_bar_err(fig, x, ys, names, xname, extra):
    """Column chart with error bars: Y columns come in pairs (value, error)."""
    ax = _ax(fig); pairs = [(ys[k], ys[k + 1], names[k]) for k in range(0, len(ys) - 1, 2)]; n = len(pairs); w = 0.8 / max(n, 1); idx = np.arange(len(x))
    for j, (v, e, nm) in enumerate(pairs): ax.bar(idx - 0.4 + w * (j + 0.5), v, w, yerr=e, capsize=3, label=nm)
    ax.set_xticks(idx); ax.set_xticklabels([str(t) for t in x]); ax.set_xlabel(xname)
    if ax.get_legend_handles_labels()[1]: ax.legend()  # no empty legend box


P.PLOT_TYPES.update({
    "Bland-Altman": (bland_altman_plot, True, "Method A (X) + method B"), "Q-Q Plot": (qq_plot, False, "Y..."),
    "Pareto Chart": (pareto, True, "X (categories) + counts"), "Box + Data Points": (box_points, False, "Y..."),
    "Histogram + Normal Curve": (hist_normal, False, "Y..."), "Scatter + Marginal Histograms": (marginal, True, "X + Y..."),
    "2D Kernel Density": (kde2d, True, "X + Y"), "Ternary Contour": (ternary_contour, True, "A (X) + B + C + Z"),
    "Ternary Density (KDE contours)": (ternary_density, True, "A (X) + B + C"),
    "Cumulative Probability": (cumulative_probability, False, "Y..."), "Column + Error Bars": (grouped_bar_err, True, "X + Y, Err pairs"),
})
