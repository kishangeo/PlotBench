"""PlotBench colour-mapped plots (a third variable as colour with a colour bar). Importing registers them.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
import matplotlib
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm, Normalize, BoundaryNorm
from matplotlib.lines import Line2D

from . import plots as P
from .plots import _ax

GROUP_MARKERS = ["D", "o", "s", "^", "v", "P", "X", "h", "<", ">"]
CMAPS = ["jet", "rainbow", "turbo", "viridis", "plasma", "inferno", "magma", "cividis", "coolwarm", "RdYlBu", "Spectral", "RdBu",
         "seismic", "terrain", "gnuplot", "nipy_spectral", "YlOrRd", "Blues", "Greens", "Greys"]
DEFAULTS = {"cmap": "jet", "reverse": True, "vmin": None, "vmax": None, "log": False, "levels": 0, "ms": 9.0, "edge": "black",
            "edge_w": 1.0, "cbar": "right", "cbar_label": "", "alpha": 1.0, "group": None, "label": None, "size": None, "label_size": 10.0,
            "legend_loc": "best", "hollow_legend": True, "lw": 2.5}


def _rows(extra, n):
    rows = extra.get("rows"); return np.arange(n) if rows is None else np.asarray(rows)


def _norm(z, o):
    z = np.asarray(z, float); fz = z[np.isfinite(z)]
    lo = o["vmin"] if o["vmin"] is not None else (np.nanmin(fz) if fz.size else 0); hi = o["vmax"] if o["vmax"] is not None else (np.nanmax(fz) if fz.size else 1)
    cmap = matplotlib.colormaps[o["cmap"] + ("_r" if o["reverse"] else "")]
    if o["levels"] and int(o["levels"]) > 1:
        edges = (np.geomspace(max(lo, 1e-300), hi, int(o["levels"]) + 1) if o["log"] else np.linspace(lo, hi, int(o["levels"]) + 1))
        return BoundaryNorm(edges, cmap.N), cmap
    if o["log"]: return LogNorm(vmin=max(lo, np.nanmin(fz[fz > 0]) if np.any(fz > 0) else 1e-3), vmax=hi), cmap
    return Normalize(vmin=lo, vmax=hi), cmap


def _colorbar(fig, ax, mappable, o, zname):
    if o["cbar"] == "none": return
    orient = "horizontal" if o["cbar"] in ("top", "bottom") else "vertical"
    cb = fig.colorbar(mappable, ax=ax, location=o["cbar"], orientation=orient, fraction=0.05, pad=0.04 if orient == "vertical" else 0.12, aspect=25)
    cb.set_label(o["cbar_label"] or zname)


def _groups_and_labels(extra, n):
    o = {**DEFAULTS, **extra}; frame, rows = extra.get("frame"), _rows(extra, n)
    groups = frame[o["group"]].astype(str).to_numpy()[rows] if frame is not None and o["group"] in getattr(frame, "columns", []) else None
    labels = frame[o["label"]].to_numpy()[rows] if frame is not None and o["label"] in getattr(frame, "columns", []) else None
    sizes = None
    if frame is not None and o["size"] in getattr(frame, "columns", []):
        import pandas as pd
        sizes = pd.to_numeric(frame[o["size"]], errors="coerce").to_numpy(float)[rows]
    return o, groups, labels, sizes


def _annotate(ax, x, y, labels, o):
    if labels is None: return
    for xi, yi, lab in zip(x, y, labels):
        if lab is None or (isinstance(lab, float) and np.isnan(lab)) or str(lab).strip() in ("", "nan"): continue
        ax.annotate(str(lab), (xi, yi), xytext=(6, 0), textcoords="offset points", va="center", fontsize=o["label_size"])


def cmap_scatter(fig, x, ys, names, xname, extra):
    """X + Y + colour column; optional group column (one symbol per group) and label column (text next to points)."""
    if len(ys) < 2: raise ValueError("Choose X, Y and a colour column.")
    ax = _ax(fig); x = np.asarray(x, float); y, z = np.asarray(ys[0], float), np.asarray(ys[1], float)
    o, groups, labels, sizes = _groups_and_labels(extra, len(x)); norm, cmap = _norm(z, o)
    s = np.full(len(x), o["ms"] ** 2) if sizes is None else 30 + 400 * (sizes - np.nanmin(sizes)) / (np.ptp(sizes[np.isfinite(sizes)]) or 1)
    kinds = [None] if groups is None else list(dict.fromkeys(groups)); handles = []
    for k, g in enumerate(kinds):
        m = np.ones(len(x), bool) if g is None else (groups == g); mk = GROUP_MARKERS[k % len(GROUP_MARKERS)]
        sc = ax.scatter(x[m], y[m], c=z[m], s=s[m], cmap=cmap, norm=norm, marker=mk, edgecolors=o["edge"] if o["edge"] != "none" else "face",
                        linewidths=o["edge_w"], alpha=o["alpha"], zorder=3)
        if g is not None:
            handles.append(Line2D([], [], marker=mk, ls="none", ms=min(o["ms"] * 1.2, 11), mfc="none" if o["hollow_legend"] else "0.6",
                                  mec="black", mew=1.0, label=str(g)))
    _annotate(ax, x, y, labels, o)
    if handles:
        if o["legend_loc"] == "outside top":
            ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.01), frameon=False, handletextpad=0.2, ncol=min(len(handles), 4))
        else: ax.legend(handles=handles, loc=o["legend_loc"], frameon=False, handletextpad=0.2, ncol=1)  # one column fits empty corners
        ax._pb_custom_legend = True  # styling must not rebuild this legend from the plotted items
    ax.set_xlabel(xname); ax.set_ylabel(names[0]); _colorbar(fig, ax, sc, o, names[1])


def bubble_color(fig, x, ys, names, xname, extra):
    """X + Y + colour column; bubble size from the 'size' column in the dialog."""
    cmap_scatter(fig, x, ys, names, xname, {**extra, "size": extra.get("size")})


def cmap_line(fig, x, ys, names, xname, extra):
    """A line coloured along its length by a third column (e.g. temperature along a path)."""
    if len(ys) < 2: raise ValueError("Choose X, Y and a colour column.")
    ax = _ax(fig); o = {**DEFAULTS, **extra}; x = np.asarray(x, float); y, z = np.asarray(ys[0], float), np.asarray(ys[1], float)
    m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z); x, y, z = x[m], y[m], z[m]; norm, cmap = _norm(z, o)
    seg = np.stack([np.column_stack([x[:-1], y[:-1]]), np.column_stack([x[1:], y[1:]])], axis=1)
    lc = LineCollection(seg, cmap=cmap, norm=norm, linewidths=o["lw"]); lc.set_array((z[:-1] + z[1:]) / 2); ax.add_collection(lc)
    ax.autoscale(); ax.set_xlabel(xname); ax.set_ylabel(names[0]); _colorbar(fig, ax, lc, o, names[1])


def cmap_ternary(fig, x, ys, names, xname, extra):
    """Ternary diagram (A = X, B, C) with points coloured by a fourth column."""
    if len(ys) < 3: raise ValueError("Choose A (X), B, C and a colour column.")
    P.ternary(fig, x, ys[:2], names[:2], xname, extra); ax = fig.axes[0]
    for ln in list(ax.lines)[-1:]: ln.remove()  # drop the plain points; redraw them coloured
    o = {**DEFAULTS, **extra}; px, py = P.ternary_xy(x, ys[0], ys[1]); z = np.asarray(ys[2], float); norm, cmap = _norm(z, o)
    sc = ax.scatter(px, py, c=z, cmap=cmap, norm=norm, s=o["ms"] ** 2, edgecolors=o["edge"] if o["edge"] != "none" else "face", linewidths=o["edge_w"], zorder=4)
    _colorbar(fig, ax, sc, o, names[2])


P.PLOT_TYPES.update({
    "Color-mapped Scatter": (cmap_scatter, True, "X + Y + colour (+ groups, labels)"),
    "Bubble + Color": (bubble_color, True, "X + Y + colour + size"),
    "Color-mapped Line": (cmap_line, True, "X + Y + colour along the line"),
    "Ternary + Color": (cmap_ternary, True, "A (X) + B + C + colour"),
})
FRAME_TYPES = {"Sankey (flows)", "Color-mapped Scatter", "Bubble + Color", "Color-mapped Line", "Ternary + Color"}
