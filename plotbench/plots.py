"""PlotBench plot types, drawn with matplotlib.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Each function takes (fig, x, ys, names, xname, extra) where ys is a list of arrays.
"""
import numpy as np
import matplotlib
from matplotlib import tri

PUB_STYLE = {"font.family": "Arial", "font.size": 11, "axes.linewidth": 1.0,
             "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
             "legend.frameon": False, "savefig.dpi": 600, "figure.dpi": 100}


def _ax(fig, **kw):
    fig.clear(); return fig.add_subplot(111, **kw)


def _label(ax, xname, names, ylabel=None):
    ax.set_xlabel(xname or "")
    ax.set_ylabel(ylabel if ylabel is not None else (names[0] if len(names) == 1 else ""))
    if len(names) > 1: ax.legend()


def line(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names): ax.plot(x, y, label=n)
    _label(ax, xname, names)


def scatter(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names): ax.plot(x, y, "o", ms=5, mfc="none", label=n)
    _label(ax, xname, names)


def line_symbol(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names): ax.plot(x, y, "-o", ms=4, label=n)
    _label(ax, xname, names)


def step(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names): ax.step(x, y, where="mid", label=n)
    _label(ax, xname, names)


def drop_line(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for j, (y, n) in enumerate(zip(ys, names)): ax.stem(x, y, linefmt=f"C{j}-", markerfmt=f"C{j}o", basefmt="k-", label=n)
    _label(ax, xname, names)


def column(fig, x, ys, names, xname, extra, horizontal=False):
    ax = _ax(fig); k = len(ys); idx = np.arange(len(x)); w = 0.8 / k
    for j, (y, n) in enumerate(zip(ys, names)):
        pos = idx - 0.4 + w * (j + 0.5)
        (ax.barh if horizontal else ax.bar)(pos, y, w, label=n)
    (ax.set_yticks if horizontal else ax.set_xticks)(idx)
    (ax.set_yticklabels if horizontal else ax.set_xticklabels)([str(v) for v in x])
    _label(ax, xname, names)


def bar(fig, x, ys, names, xname, extra): column(fig, x, ys, names, xname, extra, horizontal=True)


def stacked_column(fig, x, ys, names, xname, extra):
    ax = _ax(fig); idx = np.arange(len(x)); bottom = np.zeros(len(x))
    for y, n in zip(ys, names):
        y = np.nan_to_num(np.asarray(y, float)); ax.bar(idx, y, 0.7, bottom=bottom, label=n); bottom += y
    ax.set_xticks(idx); ax.set_xticklabels([str(v) for v in x]); _label(ax, xname, names); ax.legend()


def area(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names): ax.fill_between(x, y, alpha=0.4, label=n); ax.plot(x, y)
    _label(ax, xname, names)


def stacked_area(fig, x, ys, names, xname, extra):
    ax = _ax(fig); ax.stackplot(x, *[np.nan_to_num(y) for y in ys], labels=names); _label(ax, xname, names); ax.legend()


def histogram(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    for y, n in zip(ys, names):
        y = np.asarray(y, float); ax.hist(y[np.isfinite(y)], bins=extra.get("bins", "auto"), alpha=0.6, edgecolor="k", label=n)
    _label(ax, names[0] if len(names) == 1 else "Value", names, "Count")


def box(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    ax.boxplot([np.asarray(y, float)[np.isfinite(y)] for y in ys], labels=names, showmeans=True)


def violin(fig, x, ys, names, xname, extra):
    ax = _ax(fig)
    ax.violinplot([np.asarray(y, float)[np.isfinite(y)] for y in ys], showmedians=True)
    ax.set_xticks(range(1, len(names) + 1)); ax.set_xticklabels(names)


def pie(fig, x, ys, names, xname, extra):
    ax = _ax(fig); ax.pie(np.nan_to_num(ys[0]), labels=[str(v) for v in x], autopct="%1.1f%%"); ax.set_title(names[0])


def errorbar(fig, x, ys, names, xname, extra):
    """Pairs of columns: Y1, Err1, Y2, Err2 ..."""
    ax = _ax(fig)
    for k in range(0, len(ys) - 1, 2):
        ax.errorbar(x, ys[k], yerr=ys[k + 1], fmt="o-", capsize=3, label=names[k])
    _label(ax, xname, names[::2])


def double_y(fig, x, ys, names, xname, extra):
    ax = _ax(fig); ax.plot(x, ys[0], "C0-o", ms=3, label=names[0]); ax.set_ylabel(names[0], color="C0"); ax.set_xlabel(xname or "")
    if len(ys) > 1:
        ax2 = ax.twinx(); ax2.plot(x, ys[1], "C1-s", ms=3, label=names[1]); ax2.set_ylabel(names[1], color="C1")


def bubble(fig, x, ys, names, xname, extra):
    ax = _ax(fig); s = np.asarray(ys[1], float) if len(ys) > 1 else np.ones(len(x))
    ax.scatter(x, ys[0], s=300 * s / np.nanmax(s), alpha=0.5, edgecolors="k"); _label(ax, xname, names[:1])


def color_scatter(fig, x, ys, names, xname, extra):
    ax = _ax(fig); c = ys[1] if len(ys) > 1 else ys[0]
    sc = ax.scatter(x, ys[0], c=c); fig.colorbar(sc, ax=ax, label=names[-1]); _label(ax, xname, names[:1])


def polar(fig, x, ys, names, xname, extra):
    """X = angle in degrees, Y = radius."""
    ax = _ax(fig, projection="polar")
    for y, n in zip(ys, names): ax.plot(np.radians(np.asarray(x, float)), y, label=n)
    if len(names) > 1: ax.legend()


def _xyz(x, ys):
    x = np.asarray(x, float); y = np.asarray(ys[0], float); z = np.asarray(ys[1], float)
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z); return x[m], y[m], z[m]


def contour(fig, x, ys, names, xname, extra):
    """X, Y, Z columns (scattered points, Delaunay triangulation)."""
    ax = _ax(fig); X, Y, Z = _xyz(x, ys)
    cs = ax.tricontourf(X, Y, Z, levels=extra.get("levels", 15))
    ax.tricontour(X, Y, Z, levels=extra.get("levels", 15), colors="k", linewidths=0.4)
    fig.colorbar(cs, ax=ax, label=names[1]); ax.set_xlabel(xname); ax.set_ylabel(names[0])


def heatmap(fig, x, ys, names, xname, extra):
    """Each selected Y column becomes one heat-map column; rows labelled by X."""
    ax = _ax(fig); M = np.column_stack([np.asarray(y, float) for y in ys])
    im = ax.imshow(M, aspect="auto", origin="lower")
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticks(range(len(x))); ax.set_yticklabels([str(v) for v in x]); fig.colorbar(im, ax=ax)


def scatter3d(fig, x, ys, names, xname, extra):
    ax = _ax(fig, projection="3d"); X, Y, Z = _xyz(x, ys)
    ax.scatter(X, Y, Z, c=Z); ax.set_xlabel(xname); ax.set_ylabel(names[0]); ax.set_zlabel(names[1])


def surface3d(fig, x, ys, names, xname, extra):
    ax = _ax(fig, projection="3d"); X, Y, Z = _xyz(x, ys)
    ax.plot_trisurf(X, Y, Z, edgecolor="none"); ax.set_xlabel(xname); ax.set_ylabel(names[0]); ax.set_zlabel(names[1])


def line3d(fig, x, ys, names, xname, extra):
    """A path through X, Y, Z points in row order (trajectory, P-T-t path, drill-hole trace)."""
    ax = _ax(fig, projection="3d"); X, Y, Z = _xyz(x, ys)
    ax.plot(X, Y, Z, "-o", ms=3); ax.set_xlabel(xname); ax.set_ylabel(names[0]); ax.set_zlabel(names[1])


def bars3d(fig, x, ys, names, xname, extra):
    """A bar at every (X, Y) position, as high as Z; coloured by height."""
    import matplotlib
    ax = _ax(fig, projection="3d"); X, Y, Z = _xyz(x, ys)
    if not X.size: raise ValueError("No rows with numbers in X, Y and Z.")
    def step(v): u = np.unique(v); return 0.6 * (float(np.min(np.diff(u))) if u.size > 1 else 1.0)
    dx, dy = step(X), step(Y); span = float(np.ptp(Z)) or 1.0
    cols = matplotlib.colormaps[matplotlib.rcParams["image.cmap"]]((Z - Z.min()) / span)
    ax.bar3d(X - dx / 2, Y - dy / 2, np.zeros_like(Z), dx, dy, Z, color=cols, shade=True)
    ax.set_xlabel(xname); ax.set_ylabel(names[0]); ax.set_zlabel(names[1])


def vectors3d(fig, x, ys, names, xname, extra):
    """Arrows from (X, Y, Z) with components (U, V, W): five columns besides X."""
    if len(ys) < 5: raise ValueError("3D Vectors needs X and five more columns: Y, Z, then the components U, V, W.")
    a = [np.asarray(v, float) for v in [x] + list(ys[:5])]; m = np.all(np.isfinite(a), axis=0); X, Y, Z, U, V, W = (v[m] for v in a)
    ax = _ax(fig, projection="3d"); size = float(max(np.ptp(X), np.ptp(Y), np.ptp(Z))) or 1.0; big = float(np.max(np.sqrt(U ** 2 + V ** 2 + W ** 2))) or 1.0
    ax.quiver(X, Y, Z, U, V, W, length=0.15 * size / big, arrow_length_ratio=0.25, lw=1)
    ax.set_xlabel(xname); ax.set_ylabel(names[0]); ax.set_zlabel(names[1])


TERNARY_H = np.sqrt(3) / 2


def ternary_xy(a, b, c):
    """Normalise to a+b+c=1 and project: A at bottom-left, B at bottom-right, C at top."""
    a, b, c = (np.asarray(v, float) for v in (a, b, c)); s = a + b + c
    return (b + c / 2) / s, c * TERNARY_H / s


def ternary(fig, x, ys, names, xname, extra):
    """X, Y, Z columns are components A, B, C (any units, normalised to 100%)."""
    from .plots4 import ternary_frame
    ax = _ax(fig); ternary_frame(ax, [xname] + list(names[:2]), ticks=extra.get("ticks", True))
    px, py = ternary_xy(x, ys[0], ys[1])
    ax.plot(px, py, "o", ms=6, mfc="C0", mec="k", label=extra.get("series_label", "Samples"))


def probability(fig, x, ys, names, xname, extra):
    from scipy import stats
    ax = _ax(fig)
    for y, n in zip(ys, names):
        y = np.asarray(y, float); stats.probplot(y[np.isfinite(y)], dist="norm", plot=ax)
    ax.set_title("Normal probability plot")


def scatter_matrix(fig, x, ys, names, xname, extra):
    fig.clear(); k = len(ys)
    for i in range(k):
        for j in range(k):
            ax = fig.add_subplot(k, k, i * k + j + 1)
            if i == j: ax.hist(np.asarray(ys[i], float)[np.isfinite(ys[i])], color="0.6")
            else: ax.plot(ys[j], ys[i], ".", ms=3)
            if i == k - 1: ax.set_xlabel(names[j])
            if j == 0: ax.set_ylabel(names[i])


def log_line(fig, x, ys, names, xname, extra):
    """Semi-log Y line+symbol (e.g. chondrite-normalised REE patterns)."""
    line_symbol(fig, x, ys, names, xname, extra); fig.axes[0].set_yscale("log")


# name -> (function, needs-X, description of columns)
PLOT_TYPES = {
    "Line": (line, True, "X + Y..."), "Scatter": (scatter, True, "X + Y..."),
    "Line + Symbol": (line_symbol, True, "X + Y..."), "Step": (step, True, "X + Y..."),
    "Drop Line (Stem)": (drop_line, True, "X + Y..."), "Semi-log Y (Line + Symbol)": (log_line, True, "X + Y..."),
    "Column": (column, True, "X (categories) + Y..."), "Bar (horizontal)": (bar, True, "X (categories) + Y..."),
    "Stacked Column": (stacked_column, True, "X + Y..."), "Area": (area, True, "X + Y..."),
    "Stacked Area": (stacked_area, True, "X + Y..."), "Histogram": (histogram, False, "Y..."),
    "Box": (box, False, "Y..."), "Violin": (violin, False, "Y..."), "Pie": (pie, True, "X labels + one Y"),
    "Error Bar": (errorbar, True, "X + Y, Err pairs"), "Double-Y": (double_y, True, "X + Y1 + Y2"),
    "Bubble": (bubble, True, "X + Y + Size"), "Color-mapped Scatter": (color_scatter, True, "X + Y + Color"),
    "Polar (theta deg, r)": (polar, True, "X (deg) + R..."), "Contour (XYZ)": (contour, True, "X + Y + Z"),
    "Heat Map": (heatmap, True, "X (row labels) + Y..."), "3D Scatter": (scatter3d, True, "X + Y + Z"),
    "3D Surface": (surface3d, True, "X + Y + Z"), "3D Line (path)": (line3d, True, "X + Y + Z"),
    "3D Bars": (bars3d, True, "X + Y + Z"), "3D Vectors": (vectors3d, True, "X + Y + Z + U + V + W"), "Ternary": (ternary, True, "A (X) + B + C"),
    "Normal Probability": (probability, False, "Y..."), "Scatter Matrix": (scatter_matrix, False, "Y..."),
}


# ---------------------------------------------------------------- matrix plots: fn(fig, M, extent, zlabel, extra)
def _grid(M, extent):
    ny, nx = M.shape; x0, x1, y0, y1 = extent
    return np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny))


def m_image(fig, M, extent, z, extra):
    ax = _ax(fig); x0, x1, y0, y1 = extent
    dx = (x1 - x0) / max(M.shape[1] - 1, 1) / 2; dy = (y1 - y0) / max(M.shape[0] - 1, 1) / 2
    im = ax.imshow(M, origin="lower", aspect="auto", extent=[x0 - dx, x1 + dx, y0 - dy, y1 + dy], interpolation="nearest")
    fig.colorbar(im, ax=ax, label=z); ax.set_xlabel("X"); ax.set_ylabel("Y")


def m_contour(fig, M, extent, z, extra):
    ax = _ax(fig); X, Y = _grid(M, extent); lv = extra.get("levels", 15)
    cs = ax.contourf(X, Y, M, levels=lv); ax.contour(X, Y, M, levels=lv, colors="k", linewidths=0.4)
    fig.colorbar(cs, ax=ax, label=z); ax.set_xlabel("X"); ax.set_ylabel("Y")


def m_contour_lines(fig, M, extent, z, extra):
    ax = _ax(fig); X, Y = _grid(M, extent); cs = ax.contour(X, Y, M, levels=extra.get("levels", 12))
    ax.clabel(cs, fontsize=8); ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_title(z)


def m_surface(fig, M, extent, z, extra):
    ax = _ax(fig, projection="3d"); X, Y = _grid(M, extent)
    step = max(1, max(M.shape) // 120)  # keep big matrices responsive
    s = ax.plot_surface(X, Y, np.ma.masked_invalid(M), cmap=matplotlib_cmap(), edgecolor="none", rstride=step, cstride=step)
    fig.colorbar(s, ax=ax, shrink=0.6, label=z); ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel(z)


def m_wireframe(fig, M, extent, z, extra):
    ax = _ax(fig, projection="3d"); X, Y = _grid(M, extent)
    step = max(1, max(M.shape) // 40)
    ax.plot_wireframe(X, Y, M, rstride=step, cstride=step, linewidth=0.6); ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel(z)


def matplotlib_cmap():
    import matplotlib
    return matplotlib.rcParams["image.cmap"]


MATRIX_PLOT_TYPES = {"Image / Heat Map": m_image, "Filled Contour": m_contour, "Contour Lines": m_contour_lines,
                     "3D Colour-map Surface": m_surface, "3D Wireframe": m_wireframe}


# ================================================================ more plot types
def piper(fig, x, ys, names, xname, extra):
    """Columns (meq/L): Ca (X), Mg, Na+K, Cl, SO4, HCO3+CO3."""
    if len(ys) < 5: raise ValueError("Piper needs Ca (X) plus Mg, Na+K, Cl, SO4, HCO3+CO3 columns.")
    ax = _ax(fig); ax.set_aspect("equal"); ax.axis("off"); h = TERNARY_H
    ca, mg, na = (np.asarray(v, float) for v in (x, ys[0], ys[1])); cl, so4, hco3 = (np.asarray(v, float) for v in ys[2:5])
    sc, sa = ca + mg + na, cl + so4 + hco3
    xc, yc = (na + mg / 2) / sc, mg * h / sc                    # cation triangle: Ca left, Na+K right, Mg top
    xa, ya = 1.2 + (cl + so4 / 2) / sa, so4 * h / sa            # anion triangle: HCO3 left, Cl right, SO4 top
    s = (xa - xc) + (ya - yc) / (2 * h); xd, yd = xc + 0.5 * s, yc + h * s   # projection into the diamond
    k = "0.25"
    for ox in (0, 1.2):
        ax.plot([ox, ox + 1, ox + 0.5, ox], [0, 0, h, 0], "-", color=matplotlib.rcParams["axes.edgecolor"], lw=1)
        for f in np.arange(0.2, 1.0, 0.2):
            ax.plot([ox + f / 2, ox + 1 - f / 2], [f * h, f * h], color=k, lw=0.3)
            ax.plot([ox + f, ox + 0.5 + f / 2], [0, h * (1 - f)], color=k, lw=0.3)
            ax.plot([ox + f, ox + f / 2], [0, f * h], color=k, lw=0.3)
    ax.plot([1.1, 1.6, 1.1, 0.6, 1.1], [0.2 * h, 1.2 * h, 2.2 * h, 1.2 * h, 0.2 * h], "-", color=matplotlib.rcParams["axes.edgecolor"], lw=1)
    for f in np.arange(0.2, 1.0, 0.2):
        ax.plot([1.1 - 0.5 * f, 1.6 - 0.5 * f], [0.2 * h + f * h, 1.2 * h + f * h], color=k, lw=0.3)
        ax.plot([1.1 + 0.5 * f, 0.6 + 0.5 * f], [0.2 * h + f * h, 1.2 * h + f * h], color=k, lw=0.3)
    for tx, ty, t in ((0, -0.07, "Ca"), (0.9, -0.07, "Na+K"), (0.5, h + 0.05, "Mg"), (1.36, -0.07, "HCO$_3$+CO$_3$"), (2.2, -0.07, "Cl"),
                      (1.7, h + 0.05, "SO$_4$"), (0.65, 1.75 * h, "SO$_4$+Cl"), (1.6, 1.75 * h, "Ca+Mg")):
        ax.text(tx, ty, t, ha="center", va="center", fontsize=10)
    for j in range(len(xc)):
        c = f"C{j % 10}"; lab = str(extra.get("labels", [None] * len(xc))[j]) if extra.get("labels") else None
        ax.plot([xc[j], xa[j], xd[j]], [yc[j], ya[j], yd[j]], "o", color=c, mec="k", ms=6, ls="none", label=lab)
    if extra.get("labels"): ax.legend(loc="upper left", fontsize=8)
    ax.set_xlim(-0.1, 2.3); ax.set_ylim(-0.15, 2.3 * h)


def windrose(fig, x, ys, names, xname, extra):
    """X = direction (degrees from north), Y = speed. 16 sectors, stacked by speed class."""
    ax = _ax(fig, projection="polar"); ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    d = np.mod(np.asarray(x, float), 360); v = np.asarray(ys[0], float); m = np.isfinite(d) & np.isfinite(v); d, v = d[m], v[m]
    sec = np.floor(((d + 11.25) % 360) / 22.5).astype(int); edges = np.unique(np.percentile(v, [0, 25, 50, 75, 100]))
    bottom = np.zeros(16); th = np.radians(np.arange(16) * 22.5)
    for i in range(len(edges) - 1):
        sel = (v >= edges[i]) & ((v < edges[i + 1]) | (i == len(edges) - 2))
        cnt = np.bincount(sec[sel], minlength=16) / max(len(v), 1) * 100
        ax.bar(th, cnt, width=np.radians(22.5) * 0.95, bottom=bottom, label=f"{edges[i]:.3g}-{edges[i + 1]:.3g}", edgecolor="k", lw=0.3)
        bottom += cnt
    ax.legend(title=names[0], loc="lower left", bbox_to_anchor=(1.05, 0), fontsize=8); ax.set_title("Frequency (%)", fontsize=9)


def radar(fig, x, ys, names, xname, extra):
    """X = axis labels (one per row); each Y column is one polygon."""
    ax = _ax(fig, projection="polar"); n = len(x); th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for y, nm in zip(ys, names):
        y = np.nan_to_num(np.asarray(y, float)); ax.plot(np.r_[th, th[0]], np.r_[y, y[0]], "-o", ms=3, label=nm)
        ax.fill(np.r_[th, th[0]], np.r_[y, y[0]], alpha=0.15)
    ax.set_xticks(th); ax.set_xticklabels([str(v) for v in x])
    if len(names) > 1: ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))


def waterfall(fig, x, ys, names, xname, extra):
    """Each Y curve shifted up (and slightly right) so a series of spectra can be compared."""
    ax = _ax(fig); rng = max(np.nanmax(y) - np.nanmin(y) for y in ys) if ys else 1
    dy = extra.get("offset") or 0.6 * rng; dx = 0.02 * float(np.nanmax(x) - np.nanmin(x))
    for k in range(len(ys) - 1, -1, -1):
        xs, yv = np.asarray(x, float) + k * dx, ys[k] + k * dy
        ax.fill_between(xs, yv, np.nanmin(yv), color="white", zorder=2 * k)
        ax.plot(xs, yv, lw=1.2, zorder=2 * k + 1, label=names[k]); ax.text(xs[-1], yv[-1], f" {names[k]}", va="center", fontsize=8)
    ax.set_yticks([]); ax.set_xlabel(xname)


def stacked_panels(fig, x, ys, names, xname, extra):
    """One panel per Y column, sharing the X axis (Origin's stacked multi-layer graph)."""
    fig.clear(); axs = fig.subplots(len(ys), 1, sharex=True, squeeze=False)[:, 0]
    for k, (ax, y, nm) in enumerate(zip(axs, ys, names)):
        ax.plot(x, y, "-", color=f"C{k % 10}"); ax.set_ylabel(nm)
    axs[-1].set_xlabel(xname)


def sankey(fig, x, ys, names, xname, extra):
    """Flows from a frame with source, target and value columns (set in the plot dialog)."""
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    df = extra["frame"]; src, dst, val = extra["src"], extra["dst"], extra["val"]
    d = df[[src, dst, val]].dropna(); d = d[d[val].astype(float) > 0]
    flows = [(str(a), str(b), float(v)) for a, b, v in d.itertuples(index=False)]
    nodes = list(dict.fromkeys([f[0] for f in flows] + [f[1] for f in flows])); level = {n: 0 for n in nodes}
    for _ in nodes:  # longest-path layering
        for a, b, _v in flows: level[b] = max(level[b], level[a] + 1)
    size = {n: max(sum(v for a, _, v in flows if a == n), sum(v for _, b, v in flows if b == n)) for n in nodes}
    total = max(sum(size[n] for n in nodes if level[n] == L) for L in set(level.values())); gap = 0.03 * total
    pos = {}
    for L in sorted(set(level.values())):
        y = 0.0
        for n in [n for n in nodes if level[n] == L]: pos[n] = (L, y, y + size[n]); y += size[n] + gap
    ax = _ax(fig); ax.axis("off"); out_off = {n: pos[n][1] for n in nodes}; in_off = {n: pos[n][1] for n in nodes}
    colors = {n: f"C{i % 10}" for i, n in enumerate(nodes)}
    for a, b, v in flows:
        x0, x1 = pos[a][0] + 0.06, pos[b][0] - 0.06; y0, y1 = out_off[a], in_off[b]; out_off[a] += v; in_off[b] += v; xm = (x0 + x1) / 2
        verts = [(x0, y0), (xm, y0), (xm, y1), (x1, y1), (x1, y1 + v), (xm, y1 + v), (xm, y0 + v), (x0, y0 + v), (x0, y0)]
        codes = [MPath.MOVETO] + [MPath.CURVE4] * 3 + [MPath.LINETO] + [MPath.CURVE4] * 3 + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), fc=colors[a], alpha=0.45, lw=0))
    for n, (L, y0, y1) in pos.items():
        ax.add_patch(matplotlib_rect(L - 0.06, y0, 0.12, y1 - y0, colors[n]))
        ax.text(L + (0.09 if L < max(level.values()) else -0.09), (y0 + y1) / 2, f"{n}\n{size[n]:.4g}", va="center",
                ha="left" if L < max(level.values()) else "right", fontsize=9)
    ax.set_xlim(-0.3, max(level.values()) + 0.3); ax.set_ylim(-gap, total + gap * len(nodes)); ax.invert_yaxis()


def matplotlib_rect(x, y, w, h, c):
    from matplotlib.patches import Rectangle
    return Rectangle((x, y), w, h, fc=c, ec="k", lw=0.5)


PLOT_TYPES.update({
    "Piper Diagram": (piper, True, "Ca (X) + Mg, Na+K, Cl, SO4, HCO3+CO3"), "Wind Rose": (windrose, True, "Direction (X) + Speed"),
    "Radar / Spider": (radar, True, "X (axis labels) + Y..."), "Waterfall (offset curves)": (waterfall, True, "X + Y..."),
    "Stacked Panels (shared X)": (stacked_panels, True, "X + Y..."), "Sankey (flows)": (sankey, False, "source, target, value"),
})


def step_post(fig, x, ys, names, xname, extra):
    """Right-continuous steps (survival curves, cumulative counts)."""
    ax = _ax(fig)
    for y, n in zip(ys, names):
        m = np.isfinite(y); ax.step(np.asarray(x, float)[m], y[m], where="post", label=n)
    _label(ax, xname, names)


def dendrogram(fig, x, ys, names, xname, extra):
    """Hierarchical clustering of the rows, using the selected Y columns as variables (standardised)."""
    from scipy.cluster import hierarchy as H
    ax = _ax(fig); X = np.column_stack([np.asarray(y, float) for y in ys]); ok = np.all(np.isfinite(X), axis=1)
    X = X[ok]; Z = (X - X.mean(0)) / np.where(X.std(0, ddof=1) > 0, X.std(0, ddof=1), 1)
    labels = [str(v) for v in np.asarray(x)[ok]]
    H.dendrogram(H.linkage(Z, method=extra.get("method", "ward")), ax=ax, labels=labels, leaf_font_size=8, color_threshold=None)
    ax.set_ylabel("Distance"); ax.set_title(f"{extra.get('method', 'ward').title()} linkage")


PLOT_TYPES.update({"Step (post, survival)": (step_post, True, "X + Y..."),
                   "Dendrogram (cluster rows)": (dendrogram, True, "X (row labels) + Y variables")})
