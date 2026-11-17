"""PlotBench geochemistry plots: normalised multi-element (spider) diagrams, TAS and QAP classification diagrams.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Reference values and field boundaries are in geodata.py, with their sources.
"""
import re

import numpy as np
import matplotlib
from matplotlib.patches import Polygon

from . import plots as P
from .geodata import REFERENCES, REE, SPIDER_ORDER, TAS_FIELDS, QAP_FIELDS, SOIL_FIELDS, FELDSPAR_FIELDS, PYROXENE_FIELDS, ULTRAMAFIC_FIELDS, AFM_BOUNDARY, PEARCE_GRANITE


def element_of(name):
    """'La', 'La (ppm)', 'La_ppm', 'La ICP-MS' -> 'La'; None if the column is not an element symbol."""
    m = re.match(r"\s*([A-Z][a-z]?)(?![a-z])", str(name))
    return m.group(1) if m else None


def _short(ref): return ref.split(" (")[0]


def spider(fig, x, ys, names, xname, extra, ref="CI Chondrite (McDonough & Sun 1995)", ree=False):
    """Each worksheet row is a sample; each Y column an element (ppm). Plots sample / reference on a log axis.
    Missing or below-detection values (blank, '<0.1', 'bdl') leave a gap that the line bridges with a dotted segment."""
    ref = extra.get("reference", ref); R = REFERENCES[ref]; order = REE if ree else SPIDER_ORDER
    cols = [(i, element_of(n)) for i, n in enumerate(names)]
    cols = [(i, e) for i, e in cols if e in R and (e in order or not ree)]
    if not cols: raise ValueError(f"No Y column is named after an element in {_short(ref)} (e.g. La, Ce, Nd ... in ppm).")
    cols.sort(key=lambda t: order.index(t[1]) if t[1] in order else len(order))
    els = [e for _, e in cols]; data = np.array([np.asarray(ys[i], float) / R[e] for i, e in cols]).T  # samples x elements
    raw = extra.get("raw"); cens = np.zeros_like(data, bool)
    if raw is not None and extra.get("censored", "half") == "half":  # '<0.05' -> 0.5 x detection limit, drawn with an open triangle
        for j, (i, e) in enumerate(cols):
            for k, v in enumerate(raw[i]):
                m_ = re.match(r"\s*<\s*([0-9.eE+-]+)", str(v)) if not np.isfinite(data[k, j]) else None
                if m_:
                    try: data[k, j] = 0.5 * float(m_.group(1)) / R[e]; cens[k, j] = True
                    except ValueError: pass
    ax = P._ax(fig); pos = np.arange(len(els)); labels = [str(v) for v in x] if x is not None and len(x) == len(data) else None
    for k, row in enumerate(data):
        ok = np.isfinite(row) & (row > 0)
        if not ok.any(): continue
        c = f"C{k % 10}"; lab = labels[k] if labels else f"Sample {k + 1}"
        ax.plot(pos[ok], row[ok], ":", color=c, lw=0.8, label="_gap")  # bridges missing elements
        seg = np.where(ok & ~cens[k], row, np.nan); ax.plot(pos, seg, "-o", color=c, ms=4, lw=1.2, label=lab)
        if cens[k].any(): ax.plot(pos[cens[k]], row[cens[k]], "v", ms=7, mfc="none", mec=c, mew=1.3, label="_censored")
    ax.set_yscale("log"); ax.set_xticks(pos); ax.set_xticklabels(els, fontsize=9 if len(els) < 20 else 7.5); ax.set_xlim(-0.5, len(els) - 0.5)
    ax.set_ylabel(f"Sample / {_short(ref)}"); ax.set_xlabel("")
    if len(data) <= 20: ax.legend(fontsize=8, ncol=2 if len(data) > 8 else 1)
    note = "; open triangles: below detection, drawn at half the limit" if cens.any() else ""
    ax.text(0.99, 0.01, f"Normalised to {ref}{note}", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="0.45", in_layout=False)


GROUP_MARKERS = "osD^v<>ph*"


def _samples(ax, px, py, extra, label="Samples", ok=None, ms=6, legend=True):
    """Sample points: one series, or one colour and symbol per group when extra['groups'] gives each row's group."""
    px, py = np.asarray(px, float), np.asarray(py, float)
    ok = np.ones(px.shape, bool) if ok is None else np.asarray(ok, bool)
    g = extra.get("groups")
    if g is None or len(g) != len(px):
        ax.plot(px[ok], py[ok], "o", ms=ms, mfc="C0", mec="k", zorder=4, label=label); return
    g = np.array(["" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v) for v in g], object)
    styles = extra.get("group_styles") or {}
    for i, lev in enumerate(dict.fromkeys(g)):  # groups in the order they first appear in the sheet
        m = ok & (g == lev)
        if m.any():
            gs = styles.get(lev or "(no group)", {})  # set by double-clicking the group in the legend
            ln, = ax.plot(px[m], py[m], gs.get("marker", GROUP_MARKERS[i % len(GROUP_MARKERS)]), ms=float(gs.get("ms", ms)),
                          mfc=gs.get("color", f"C{i % 10}"), mec="k", mew=0.6, ls="none", zorder=4, label=gs.get("label") or lev or "(no group)")
            ln.set_gid("pbgroup:" + (lev or "(no group)"))
    if not legend: ax._pb_custom_legend = True  # other Harker panels: no legend of their own, curves still editable
    if legend:  # outside the diagram so it never hides field names; still draggable
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8, frameon=False, borderaxespad=0); ax._pb_custom_legend = True


def group_column(df):
    """A text column that groups the rows (2 to 12 different values, some repeated), e.g. Rock, Setting, Suite; None if there is none."""
    import pandas as pd
    for c in df.columns:
        v = df[c].dropna()
        if v.empty or pd.to_numeric(v, errors="coerce").notna().any(): continue
        u = v.astype(str).nunique()
        if 2 <= u <= 12 and u < len(v): return c
    return None


def _area(p): x, y = p[:, 0], p[:, 1]; return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def _fields(ax, polys, project=lambda p: p, label=True, fontsize=7, min_area=0.0, short=None):
    """Field outlines; names go in fields with room for them (narrow fields get the short name, or none)."""
    ink = matplotlib.rcParams["axes.edgecolor"]
    for name, poly in polys.items():
        pts = np.array([project(p) for p in poly], float)
        ax.add_patch(Polygon(pts, closed=True, fill=False, ec=ink, lw=0.6, alpha=0.7, zorder=1))
        if not label: continue
        text = name if _area(pts) >= min_area else (short or {}).get(name)
        if not text: continue
        if len(text) > 12 and "\n" not in text: text = text.replace(" ", "\n", 1)
        c = pts.mean(axis=0); ax.text(c[0], c[1], text, ha="center", va="center", fontsize=fontsize, color="0.45", zorder=1)


TAS_NAMES = {"Tephrite": "Tephrite /\nBasanite", "Foidite": "Foidite", "Alkalic Basalt": "Basalt\n(alkalic)", "Subalkalic Basalt": "Basalt"}


def tas(fig, x, ys, names, xname, extra):
    """Total alkali-silica (Le Bas et al. 1986). X = SiO2 wt%; Y = Na2O + K2O, or two Y columns Na2O and K2O that are summed."""
    ax = P._ax(fig); si = np.asarray(x, float)
    alk = np.asarray(ys[0], float) if len(ys) == 1 else np.nansum([np.asarray(y, float) for y in ys[:2]], axis=0)
    _fields(ax, {TAS_NAMES.get(k, k): v for k, v in TAS_FIELDS.items()})
    _samples(ax, si, alk, extra, " + ".join(names[:2]) if len(ys) > 1 else names[0])
    ax.set_xlim(35, 80); ax.set_ylim(0, 16); ax.set_xlabel("SiO$_2$ (wt%)"); ax.set_ylabel("Na$_2$O + K$_2$O (wt%)")
    ax.text(0.99, 0.99, "Le Bas et al. (1986)", transform=ax.transAxes, ha="right", va="top", fontsize=7, color="0.45", in_layout=False)


def ternary_frame(ax, labels, ticks=True):
    """Triangle, 10% grid, tick marks with 0-100% labels on all three edges, and corner labels (A left, B right, C top)."""
    ink = matplotlib.rcParams["axes.edgecolor"]; H = P.TERNARY_H; xy = P.ternary_xy
    ax.set_aspect("equal"); ax.axis("off"); ax.plot([0, 1, 0.5, 0], [0, 0, H, 0], "-", color=ink, lw=1)
    for f in np.arange(0.1, 1.0, 0.1):
        for p, q in (((f, 1 - f, 0), (f, 0, 1 - f)), ((0, f, 1 - f), (1 - f, f, 0)), ((1 - f, 0, f), (0, 1 - f, f))):
            gx, gy = xy(*zip(p, q)); ax.plot(gx, gy, color="0.85", lw=0.5, zorder=0)
    if ticks:
        for f in np.arange(0.2, 0.81, 0.2):  # B along the bottom, C up the right edge, A down the left edge
            for (a, b, c), (dx, dy), ha in (((1 - f, f, 0), (0, -0.035), "center"), ((0, 1 - f, f), (0.03, 0.0), "left"),
                                            ((f, 0, 1 - f), (-0.03, 0.0), "right")):
                tx, ty = xy([a], [b], [c]); ax.plot([tx[0], tx[0] + dx * 0.4], [ty[0], ty[0] + dy * 0.4], color=ink, lw=0.8)
                ax.text(tx[0] + dx, ty[0] + dy, f"{f * 100:.0f}", ha=ha, va="center", fontsize=7, color="0.35")
    for (tx, ty), lab, ha in zip(((0, 0), (1, 0), (0.5, H)), labels, ("right", "left", "center")):
        ax.text(tx - (0.03 if ha == "right" else 0) + (0.03 if ha == "left" else 0), ty + (0.045 if ty else -0.06), lab, ha=ha, va="center",
                fontsize=12, fontweight="bold")
    ax.set_xlim(-0.12, 1.12); ax.set_ylim(-0.12, H + 0.09)


QAP_SHORT = {  # field numbers of Streckeisen (1976), used where a field is too narrow for its name
    "Quartzolite": "1a", "Quartz-rich Granitoid": "1b",
    "Alkali Feldspar Granite": "2", "Syenogranite": "3a", "Monzogranite": "3b", "Granodiorite": "4", "Tonalite": "5",
    "Quartz Alkali Feldspar Syenite": "6*", "Quartz Syenite": "7*", "Quartz Monzonite": "8*",
    "Quartz Monzodiorite/Monzogabbro": "9*", "Quartz Diorite/Gabbro/Anorthosite": "10*", "Alkali Feldspar Syenite": "6",
    "Syenite": "7", "Monzonite": "8", "Monzodiorite/Monzogabbro": "9", "Diorite/Gabbro/Anorthosite": "10"}


def qap(fig, x, ys, names, xname, extra):
    """Streckeisen QAP for plutonic rocks. X = Q, Y1 = A (alkali feldspar), Y2 = P (plagioclase); any units, normalised."""
    if len(ys) < 2: raise ValueError("Choose Q (X), A and P columns.")
    ax = P._ax(fig); ternary_frame(ax, ["A", "P", "Q"], ticks=False)  # A bottom-left, P bottom-right, Q top
    proj = lambda p: np.ravel(P.ternary_xy([p[1]], [p[2]], [p[0]]))  # polygons are [Q, A, P]
    fields = {k: v for k, v in QAP_FIELDS.items() if k != "Granite"}  # 'Granite' is the union of fields 3a + 3b
    _fields(ax, fields, proj, fontsize=6, min_area=0.045, short=QAP_SHORT)
    px, py = P.ternary_xy(ys[0], ys[1], x); _samples(ax, px, py, extra, "Samples")
    ax.set_ylim(-0.26, P.TERNARY_H + 0.09); ax.text(0.5, -0.2, "Streckeisen (1976): 1a quartzolite, 1b quartz-rich granitoid, 2 alkali-fsp granite, 3a syeno-, 3b monzogranite,\n"
            "4 granodiorite, 5 tonalite, 6 alkali-fsp syenite, 7 syenite, 8 monzonite, 9 monzodiorite, 10 diorite/gabbro; * quartz-", ha="center", va="center", fontsize=6.5, color="0.45", in_layout=False)


def _by_name(x, ys, names, xname, wanted):
    """Columns for the three corners: matched by name when every corner name is found (e.g. 'Sand (%)', 'An mol%'),
    otherwise in the order X, Y1, Y2."""
    cols = [(xname, x)] + list(zip(names, ys))
    hit = {}
    for w in wanted:
        for n, v in cols:
            if re.match(rf"\s*{w}(?![a-z])", str(n), re.I) and w not in hit: hit[w] = v
    if len(hit) == 3: return [np.asarray(hit[w], float) for w in wanted]
    if len(ys) < 2: raise ValueError(f"Choose three columns: {', '.join(wanted)}.")
    return [np.asarray(v, float) for v in (x, ys[0], ys[1])]


SOIL_SHORT = {"Sand": "Sand", "Loamy Sand": "Lo. sand", "Silt": "Silt"}


def soil_texture(fig, x, ys, names, xname, extra):
    """USDA soil texture triangle. Sand, silt and clay in % (normalised to 100%); clay at the top, sand at the left, silt at the right."""
    sand, silt, clay = _by_name(x, ys, names, xname, ["Sand", "Silt", "Clay"])
    ax = P._ax(fig); ternary_frame(ax, ["Sand", "Silt", "Clay"])
    proj = lambda p: np.ravel(P.ternary_xy([p[1]], [p[2]], [p[0]]))  # polygons are [Clay, Sand, Silt]
    _fields(ax, SOIL_FIELDS, proj, fontsize=6.5, min_area=0.012, short=SOIL_SHORT)
    px, py = P.ternary_xy(sand, silt, clay); _samples(ax, px, py, extra, "Samples")
    ax.text(0.5, -0.17, "USDA soil texture classes (sand 2-0.05 mm, silt 0.05-0.002 mm, clay < 0.002 mm)", ha="center", fontsize=6.5,
            color="0.45", in_layout=False)


FSP_SHORT = {"Albite": "Ab", "Oligoclase": "Olig.", "Anorthoclase": "Ano.", "Anorthite": "An"}


def feldspar(fig, x, ys, names, xname, extra):
    """Feldspar ternary An-Ab-Or (mol%): anorthite at the top, albite at the left, orthoclase at the right, with the
    plagioclase and alkali-feldspar names."""
    ab, or_, an = _by_name(x, ys, names, xname, ["Ab", "Or", "An"])
    ax = P._ax(fig); ternary_frame(ax, ["Ab", "Or", "An"])
    proj = lambda p: np.ravel(P.ternary_xy([p[1]], [p[2]], [p[0]]))  # polygons are [An, Ab, Or]
    _fields(ax, FELDSPAR_FIELDS, proj, fontsize=6.5, min_area=0.02, short=FSP_SHORT)
    px, py = P.ternary_xy(ab, or_, an); _samples(ax, px, py, extra, "Analyses")
    ax.text(0.5, -0.17, "Feldspar names after Deer, Howie & Zussman (1992); compositions in the miscibility gap are not stable",
            ha="center", fontsize=6.5, color="0.45", in_layout=False)


def pyroxene(fig, x, ys, names, xname, extra):
    """Pyroxene quadrilateral (Morimoto 1988): the En-Fs-Di-Hd part (Wo <= 50) of the Wo-En-Fs triangle, in mol%."""
    wo, en, fs = _by_name(x, ys, names, xname, ["Wo", "En", "Fs"])
    ax = P._ax(fig); ax.set_aspect("equal"); ax.axis("off"); ink = matplotlib.rcParams["axes.edgecolor"]; H = P.TERNARY_H
    xy = lambda w, e, f: np.ravel(P.ternary_xy([e], [f], [w]))
    quad = np.array([xy(0, 100, 0), xy(0, 0, 100), xy(50, 0, 50), xy(50, 50, 0), xy(0, 100, 0)])
    for f in np.arange(0.1, 1.0, 0.1):  # 10% grid lines of En/Fs inside the quadrilateral
        a, b = xy(0, 100 * (1 - f), 100 * f), xy(50, 50 * (1 - f), 50 * f); ax.plot([a[0], b[0]], [a[1], b[1]], color="0.88", lw=0.5, zorder=0)
    for wv in (10, 30, 40):
        a, b = xy(wv, 100 - wv, 0), xy(wv, 0, 100 - wv); ax.plot([a[0], b[0]], [a[1], b[1]], color="0.88", lw=0.5, zorder=0)
    ax.plot(quad[:, 0], quad[:, 1], "-", color=ink, lw=1)
    _fields(ax, PYROXENE_FIELDS, lambda p: xy(*p), fontsize=7, min_area=0.02)  # the four corner strips are named by the bold labels
    for (tx, ty), lab, ha in ((xy(0, 100, 0), "En", "right"), (xy(0, 0, 100), "Fs", "left"), (xy(50, 50, 0), "Di", "right"), (xy(50, 0, 50), "Hd", "left")):
        ax.text(tx + (-0.02 if ha == "right" else 0.02), ty, lab, ha=ha, va="center", fontsize=12, fontweight="bold")
    for wv in (5, 20, 45):
        t = xy(wv, 0, 100 - wv); ax.text(t[0] + 0.015, t[1], f"Wo{wv}", fontsize=7, color="0.4", va="center")
    s = wo + en + fs; w2, e2, f2 = 100 * wo / s, 100 * en / s, 100 * fs / s
    px, py = P.ternary_xy(e2, f2, w2); _samples(ax, px, py, extra, "Analyses")
    ax.set_xlim(-0.1, 1.12); ax.set_ylim(-0.12, H / 2 + 0.08)
    ax.text(0.5, -0.09, "Morimoto (1988), mol% Wo + En + Fs = 100", ha="center", fontsize=6.5, color="0.45", in_layout=False)


UM_SHORT = {"Dunite": "Dunite", "Orthopyroxenite": "Opx-ite", "Clinopyroxenite": "Cpx-ite"}


def ultramafic(fig, x, ys, names, xname, extra):
    """IUGS ultramafic rocks: modal olivine (top), orthopyroxene (left) and clinopyroxene (right)."""
    ol, opx, cpx = _by_name(x, ys, names, xname, ["Ol", "Opx", "Cpx"])
    ax = P._ax(fig); ternary_frame(ax, ["Opx", "Cpx", "Ol"])
    proj = lambda p: np.ravel(P.ternary_xy([p[1]], [p[2]], [p[0]]))  # polygons are [Ol, Opx, Cpx]
    _fields(ax, ULTRAMAFIC_FIELDS, proj, fontsize=6.5, min_area=0.015, short=UM_SHORT)
    px, py = P.ternary_xy(opx, cpx, ol); _samples(ax, px, py, extra, "Samples")
    ax.text(0.5, -0.17, "IUGS (Streckeisen 1976; Le Maitre 2002), modal %", ha="center", fontsize=6.5, color="0.45", in_layout=False)


def _col(x, ys, names, xname, pattern):
    """The column whose name starts with pattern (e.g. 'Na2O', 'Rb'), as numbers; None if there is none."""
    for n, v in [(xname, x)] + list(zip(names, ys)):
        if re.match(rf"\s*(?:{pattern})(?![a-z0-9])", str(n), re.I): return np.asarray(v, float)
    return None


def _iron(x, ys, names, xname):
    """(FeO or FeO total column, Fe2O3 or Fe2O3 total column); either may be None."""
    return (_col(x, ys, names, xname, r"FeO(?:t|\*|tot|total)?"), _col(x, ys, names, xname, r"Fe2O3(?:t|\*|tot|total)?"))


def _feot(fe, fe3):
    """FeO total = FeO + 0.8998 Fe2O3, treating a blank in one of two iron columns as 0 but NaN when both are blank."""
    if fe is None: return 0.8998 * fe3
    if fe3 is None: return fe
    return np.where(np.isnan(fe) & np.isnan(fe3), np.nan, np.nan_to_num(fe) + 0.8998 * np.nan_to_num(fe3))


def afm(fig, x, ys, names, xname, extra):
    """AFM ternary: A = Na2O + K2O (left), F = FeO total (top), M = MgO (right), with the Irvine & Baragar (1971) boundary.
    Columns are found by name (Na2O, K2O, FeOt / FeO* / FeO, Fe2O3, MgO, wt%); otherwise A as X, then F and M."""
    na, k, mg = _col(x, ys, names, xname, "Na2O"), _col(x, ys, names, xname, "K2O"), _col(x, ys, names, xname, "MgO")
    fe, fe3 = _iron(x, ys, names, xname)
    if na is not None and k is not None and mg is not None and (fe is not None or fe3 is not None):
        A = na + k  # a missing Na2O or K2O leaves the sample out instead of plotting it at A = 0
        F = _feot(fe, fe3)
        M = mg
    else:
        if len(ys) < 2: raise ValueError("Choose Na2O, K2O, FeOt and MgO columns (or A, F and M).")
        A, F, M = (np.asarray(v, float) for v in (x, ys[0], ys[1]))
    ax = P._ax(fig); ternary_frame(ax, ["A", "M", "F"], ticks=False)
    pts = np.array([np.ravel(P.ternary_xy([a], [m], [f])) for a, f, m in AFM_BOUNDARY])
    ax.plot(pts[:, 0], pts[:, 1], "-", color=matplotlib.rcParams["axes.edgecolor"], lw=1.4, label="_boundary")
    ax.text(0.5, 0.52, "Tholeiitic", ha="center", fontsize=9, color="0.4"); ax.text(0.42, 0.12, "Calc-alkaline", ha="center", fontsize=9, color="0.4")
    px, py = P.ternary_xy(A, M, F); _samples(ax, px, py, extra, "Samples")
    ax.text(0.5, -0.17, "A = Na2O + K2O, F = FeO total, M = MgO (wt%); boundary of Irvine & Baragar (1971)", ha="center", fontsize=6.5,
            color="0.45", in_layout=False)


def pearce(which):
    """One of the four granite discrimination diagrams of Pearce et al. (1984), log-log, in ppm."""
    d = PEARCE_GRANITE[which]

    def draw(fig, x, ys, names, xname, extra):
        def val(expr):
            parts = [_col(x, ys, names, xname, el) for el in expr.split("+")]
            return None if any(p is None for p in parts) else sum(parts[1:], parts[0])  # a missing element leaves the sample out
        xv, yv = val(d["x"]), val(d["y"])
        if xv is None or yv is None:  # columns not named after the elements: X and the first Y as given
            if not ys: raise ValueError(f"Choose the columns for {d['x']} and {d['y']} (named after the elements, e.g. Rb, Y, Nb).")
            xv, yv = np.asarray(x, float), np.asarray(ys[0], float)
        ax = P._ax(fig); ink = matplotlib.rcParams["axes.edgecolor"]
        for seg in d["lines"]: ax.plot(*zip(*seg), "-", color=ink, lw=1.1, label="_boundary")
        for seg in d["dashed"]: ax.plot(*zip(*seg), "--", color=ink, lw=1.0, label="_boundary")
        for lx, ly, t in d["labels"]: ax.text(lx, ly, t, ha="center", va="center", fontsize=9, color="0.4")
        ok = (xv > 0) & (yv > 0)
        lab = extra.get("labels")
        _samples(ax, xv, yv, extra, "Samples", ok)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(*d["xlim"]); ax.set_ylim(*d["ylim"])
        ax.set_xlabel(f"{d['x']} (ppm)"); ax.set_ylabel(f"{d['y']} (ppm)")
        ax.text(0.99, 0.01, "Pearce et al. (1984)", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="0.45", in_layout=False)
    return draw


def harker(fig, x, ys, names, xname, extra):
    """Harker variation diagrams: every selected oxide (or element) against SiO2, one small panel each.
    SiO2 is found by name among the columns; otherwise X is used."""
    si = _col(x, ys, names, xname, "SiO2")
    cols = [(n, np.asarray(v, float)) for n, v in zip(names, ys) if not re.match(r"\s*SiO2(?![a-z0-9])", str(n), re.I)]
    if si is None: si = np.asarray(x, float)
    if not cols: raise ValueError("Choose SiO2 and at least one other oxide column (wt%).")
    n = len(cols); nc = min(n, 3 if n <= 9 else 4); nr = -(-n // nc)
    fig.clear(); axs = np.atleast_1d(fig.subplots(nr, nc, sharex=True, squeeze=False).ravel())
    for ax, (name, v) in zip(axs, cols):
        ok = np.isfinite(si) & np.isfinite(v)
        _samples(ax, si, v, extra, name, ok, ms=4, legend=ax is axs[0])
        ax.set_ylabel(name); ax.tick_params(labelsize=7)
    for ax in axs[n:]: ax.set_visible(False)
    for ax in axs[max(0, n - nc):n]: ax.set_xlabel("SiO2 (wt%)"); ax.xaxis.set_tick_params(labelbottom=True)


MOLAR = {"Al2O3": 101.96, "CaO": 56.08, "Na2O": 61.98, "K2O": 94.20, "P2O5": 141.94}


def shand_indices(al, ca, na, k, p=None):
    """Molar A/CNK = Al2O3/(CaO+Na2O+K2O) and A/NK = Al2O3/(Na2O+K2O) from wt% oxides.
    With P2O5, CaO is corrected for apatite: CaO* = CaO - 10/3 P2O5 (molar), not below 0."""
    a, c, n, kk = (np.asarray(v, float) / MOLAR[o] for v, o in zip((al, ca, na, k), ("Al2O3", "CaO", "Na2O", "K2O")))
    if p is not None: c = np.clip(c - 10 / 3 * np.nan_to_num(np.asarray(p, float) / MOLAR["P2O5"]), 0, None)
    return a / (c + n + kk), a / (n + kk)


def shand(fig, x, ys, names, xname, extra):
    """Shand (1943) alumina saturation diagram as drawn by Maniar & Piccoli (1989): molar A/CNK against A/NK."""
    cols = [_col(x, ys, names, xname, o) for o in ("Al2O3", "CaO", "Na2O", "K2O")]
    p2o5 = _col(x, ys, names, xname, "P2O5")
    if all(c is not None for c in cols): acnk, anks = shand_indices(*cols, p=p2o5)
    elif ys: acnk, anks = np.asarray(x, float), np.asarray(ys[0], float)  # indices already calculated
    else: raise ValueError("Choose Al2O3, CaO, Na2O and K2O columns (wt%), or A/CNK as X and A/NK as Y.")
    ax = P._ax(fig); ink = matplotlib.rcParams["axes.edgecolor"]
    ax.axvline(1, color=ink, lw=1.1); ax.axhline(1, color=ink, lw=1.1)
    ax.axvline(1.1, color=ink, lw=0.9, ls="--")
    ax.text(0.75, 2.6, "Metaluminous", ha="center", fontsize=9, color="0.4"); ax.text(1.3, 2.6, "Peraluminous", ha="center", fontsize=9, color="0.4")
    ax.text(0.75, 0.7, "Peralkaline", ha="center", fontsize=9, color="0.4")
    ax.text(1.12, 0.62, "I | S", ha="center", fontsize=7, color="0.45")
    ok = np.isfinite(acnk) & np.isfinite(anks)
    _samples(ax, acnk, anks, extra, "Samples", ok)
    ax.set_xlim(0.5, 1.5); ax.set_ylim(0.5, 3.0); ax.set_xlabel("A/CNK (molar, CaO corrected for apatite)" if p2o5 is not None and all(c is not None for c in cols) else "A/CNK (molar)")
    ax.set_ylabel("A/NK (molar)")
    ax.text(0.99, 0.01, "Shand (1943); Maniar & Piccoli (1989); dashed: I/S at 1.1 (Chappell & White 1974)", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=6.5, color="0.45", in_layout=False)


# Frost et al. (2001, J. Petrol. 42, 2033-2048) boundaries, as coded in GCDkit (Frost.r), valid for SiO2 50-77 wt%
FROST_FE_LINE = (0.486, 0.0046)        # FeOt/(FeOt+MgO) = 0.486 + 0.0046 SiO2 (0.446 + 0.0046 SiO2 if FeO only)
FROST_MALI = [("alkalic", "alkali-calcic", (-41.86, 1.112, -0.00572)), ("alkali-calcic", "calc-alkalic", (-44.72, 1.094, -0.00527)),
              ("calc-alkalic", "calcic", (-45.36, 1.0043, -0.00427))]


def frost_fe(fig, x, ys, names, xname, extra):
    """Frost et al. (2001) Fe-number FeOt/(FeOt+MgO) against SiO2: ferroan / magnesian."""
    si, mg = _col(x, ys, names, xname, "SiO2"), _col(x, ys, names, xname, "MgO")
    fe, fe3 = _iron(x, ys, names, xname)
    if si is None or mg is None or (fe is None and fe3 is None): raise ValueError("Choose SiO2, FeOt (or Fe2O3) and MgO columns (wt%).")
    F = _feot(fe, fe3)
    ax = P._ax(fig); s = np.linspace(50, 77, 60); a, b = FROST_FE_LINE
    ax.plot(s, a + b * s, "-", color=matplotlib.rcParams["axes.edgecolor"], lw=1.2, label="_boundary")
    ax.text(60, 0.9, "ferroan", ha="center", fontsize=9, color="0.4"); ax.text(60, 0.6, "magnesian", ha="center", fontsize=9, color="0.4")
    _samples(ax, si, F / (F + mg), extra, "Samples")
    ax.set_xlim(50, 80); ax.set_ylim(0, 1); ax.set_xlabel("SiO2 (wt%)"); ax.set_ylabel("FeOt/(FeOt+MgO)")
    ax.text(0.99, 0.01, "Frost et al. (2001)", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="0.45", in_layout=False)


def frost_mali(fig, x, ys, names, xname, extra):
    """Frost et al. (2001) modified alkali-lime index Na2O+K2O-CaO against SiO2."""
    si, na, k, ca = (_col(x, ys, names, xname, o) for o in ("SiO2", "Na2O", "K2O", "CaO"))
    if any(v is None for v in (si, na, k, ca)): raise ValueError("Choose SiO2, Na2O, K2O and CaO columns (wt%).")
    ax = P._ax(fig); s = np.linspace(50, 77, 60); ink = matplotlib.rcParams["axes.edgecolor"]
    for _, _, (c0, c1, c2) in FROST_MALI: ax.plot(s, c0 + c1 * s + c2 * s * s, "-", color=ink, lw=1.1, label="_boundary")
    for t, (sx, sy) in {"alkalic": (55, 9), "alkali-calcic": (53.5, -0.8), "calc-alkalic": (53.5, -3.3), "calcic": (70, -3)}.items():
        ax.text(sx, sy, t, ha="center", fontsize=8.5, color="0.4")
    _samples(ax, si, na + k - ca, extra, "Samples")
    ax.set_xlim(50, 80); ax.set_ylim(-8, 12); ax.set_xlabel("SiO2 (wt%)"); ax.set_ylabel("Na2O+K2O-CaO (wt%)")
    ax.text(0.99, 0.01, "Frost et al. (2001)", transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="0.45", in_layout=False)


def _spider(ref, ree):
    return lambda fig, x, ys, names, xname, extra: spider(fig, x, ys, names, xname, extra, ref, ree)


SPIDERS = {
    "Spider: REE / CI Chondrite": ("CI Chondrite (McDonough & Sun 1995)", True),
    "Spider: REE / Primitive Mantle": ("Primitive Mantle (McDonough & Sun 1995)", True),
    "Spider: Multi-element / Primitive Mantle": ("Primitive Mantle (McDonough & Sun 1995)", False),
    "Spider: Multi-element / N-MORB": ("N-MORB (Sun & McDonough 1989)", False),
    "Spider: Multi-element / CI Chondrite": ("CI Chondrite (McDonough & Sun 1995)", False),
    "Spider: REE / PAAS (sediments)": ("PAAS (Taylor & McLennan 1985)", True),
}
P.PLOT_TYPES.update({k: (_spider(*v), True, "Sample labels (X) + element columns in ppm (La, Ce, ...)") for k, v in SPIDERS.items()})
P.PLOT_TYPES.update({"TAS (SiO2 vs Na2O+K2O)": (tas, True, "SiO2 (X) + Na2O+K2O, or Na2O + K2O"),
                     "QAP (Streckeisen)": (qap, True, "Q (X) + A + P"),
                     "Feldspar Ternary (An-Ab-Or)": (feldspar, True, "Ab (X) + Or + An, mol%"),
                     "Soil Texture (USDA)": (soil_texture, True, "Sand (X) + Silt + Clay, %"),
                     "Pyroxene Quadrilateral (Wo-En-Fs)": (pyroxene, True, "Wo (X) + En + Fs, mol%"),
                     "Ultramafic Ol-Opx-Cpx (IUGS)": (ultramafic, True, "Ol (X) + Opx + Cpx, modal %"),
                     "AFM (Irvine & Baragar)": (afm, True, "Na2O, K2O, FeOt, MgO (wt%)"),
                     "Harker Diagrams (oxides vs SiO2)": (harker, True, "SiO2 + oxide columns (wt%)"),
                     "Shand A/CNK vs A/NK": (shand, True, "Al2O3, CaO, Na2O, K2O (wt%)"),
                     "Frost: Fe-number vs SiO2": (frost_fe, True, "SiO2, FeOt, MgO (wt%)"),
                     "Frost: MALI vs SiO2": (frost_mali, True, "SiO2, Na2O, K2O, CaO (wt%)")})
PEARCE_TYPES = {f"Pearce Granite: {k}": pearce(k) for k in PEARCE_GRANITE}
P.PLOT_TYPES.update({k: (v, True, "Rb, Y, Nb, Yb, Ta columns (ppm)") for k, v in PEARCE_TYPES.items()})
# diagrams whose sample points can be coloured by group (Graph > Group Samples By)
GROUPABLE = {"TAS (SiO2 vs Na2O+K2O)", "QAP (Streckeisen)", "Feldspar Ternary (An-Ab-Or)", "Soil Texture (USDA)", "Pyroxene Quadrilateral (Wo-En-Fs)",
             "Ultramafic Ol-Opx-Cpx (IUGS)", "AFM (Irvine & Baragar)", "Harker Diagrams (oxides vs SiO2)", "Shand A/CNK vs A/NK",
             "Frost: Fe-number vs SiO2", "Frost: MALI vs SiO2", *PEARCE_TYPES}


# Equivalent weights (g per equivalent = molar mass / |charge|) for converting mg/L to meq/L
EQUIV_WEIGHT = {"Ca": 20.04, "Mg": 12.15, "Na": 22.99, "K": 39.10, "HCO3": 61.02, "CO3": 30.00, "Cl": 35.45, "SO4": 48.03,
                "NO3": 62.00, "F": 19.00}


def ion_of(name):
    """'Ca', 'Ca (mg/L)', 'HCO3_mgL', 'SO4 ppm' -> ion symbol; None if the column is not a major ion."""
    m = re.match(r"\s*(HCO3|CO3|SO4|NO3|Ca|Mg|Na|Cl|K|F)(?![a-z])", str(name))
    return m.group(1) if m else None


def mg_to_meq(name, values):
    """mg/L (or ppm in dilute water) -> meq/L."""
    return np.asarray(values, float) / EQUIV_WEIGHT[ion_of(name)]


def _demo():
    """Self-check: element parsing, normalisation and field polygons."""
    from matplotlib.figure import Figure
    f = Figure(); si = np.array([48., 55, 63, 72])
    harker(f, np.array(["a", "b", "c", "d"]), [si, si / 10, 80 - si], ["SiO2", "TiO2", "MgO"], "Sample", {})
    vis = [a for a in f.axes if a.get_visible()]
    assert len(vis) == 2 and vis[1].get_ylabel() == "MgO" and np.allclose(vis[1].lines[0].get_xdata(), si), "harker"
    harker(f, si, [si / 10] * 5, list("ABCDE"), "SiO2", {}); assert sum(a.get_visible() for a in f.axes) == 5
    c0, c1, c2 = FROST_MALI[0][2]; assert abs(c0 + c1 * 60 + c2 * 3600 - 4.268) < 1e-6, "MALI"  # alkalic line at SiO2 60
    frost_fe(f, None, [np.array([65.]), np.array([4.]), np.array([1.])], ["SiO2", "FeOt", "MgO"], "", {})
    assert np.isclose(f.axes[0].lines[-1].get_ydata()[0], 0.8)
    frost_mali(f, None, [np.array([65.]), np.array([4.]), np.array([4.]), np.array([2.])], ["SiO2", "Na2O", "K2O", "CaO"], "", {})
    import pandas as pd
    assert group_column(pd.DataFrame({"S": ["a", "b", "c"], "R": ["x", "y", "x"], "V": [1, 2, 3]})) == "R"
    assert group_column(pd.DataFrame({"S": ["a", "b", "c"]})) is None
    f2 = Figure(); shand(f2, None, [np.array([15., 14, 16]), np.array([5., 2, 1]), np.array([3.5, 3, 4]), np.array([3., 4, 5])],
                         ["Al2O3", "CaO", "Na2O", "K2O"], "", {"groups": np.array(["I", "S", "I"], object)})
    assert sorted(l.get_label() for l in f2.axes[0].lines if not l.get_label().startswith("_")) == ["I", "S"], "groups"
    acnk, ank = shand_indices([101.96], [56.08], [61.98], [0.0])  # 1 mol Al2O3, 1 CaO, 1 Na2O
    assert np.allclose([acnk[0], ank[0]], [0.5, 1.0]), "shand"
    ac2, _ = shand_indices([101.96], [56.08 * 2], [61.98], [0.0], p=[141.94 * 0.3])  # 2 CaO - 1 in apatite = 1 CaO*
    assert np.isclose(ac2[0], 0.5), "apatite"
    from matplotlib.figure import Figure as _F
    g = _F(); afm(g, None, [np.array([3., np.nan]), np.array([1., 1.]), np.array([8., 8.]), np.array([5., 5.])], ["Na2O", "K2O", "Fe2O3t", "MgO"], "", {})
    assert np.isfinite(g.axes[0].lines[-1].get_xdata()).sum() == 1, "missing Na2O must drop the sample"
    shand(f, None, [np.array([15.]), np.array([5.]), np.array([3.5]), np.array([3.0])], ["Al2O3", "CaO", "Na2O", "K2O"], "", {})
    assert element_of("La (ppm)") == "La" and element_of("Nd_ppm") == "Nd" and element_of("Sample") is None and element_of("Ce") == "Ce"
    from matplotlib.figure import Figure
    fig = Figure(); R = REFERENCES["CI Chondrite (McDonough & Sun 1995)"]
    spider(fig, np.array(["s1"]), [np.array([R["La"] * 100]), np.array([R["Lu"] * 10])], ["La", "Lu"], "", {}, ree=True)
    ln = [l for l in fig.axes[0].lines if l.get_label() == "s1"][0]; assert np.allclose(ln.get_ydata(), [100, 10])
    tas(Figure(), np.array([50.0]), [np.array([3.0]), np.array([1.0])], ["Na2O", "K2O"], "SiO2", {})
    qap(Figure(), np.array([30.0]), [np.array([35.0]), np.array([35.0])], ["A", "P"], "Q", {})
    assert len(TAS_FIELDS) >= 15 and len(QAP_FIELDS) >= 15 and len(SOIL_FIELDS) == 12 and len(FELDSPAR_FIELDS) == 8
    for polys in (SOIL_FIELDS, FELDSPAR_FIELDS):
        for poly in polys.values(): assert all(abs(sum(p) - 100) < 1e-3 for p in poly)
    # loam (40 sand, 40 silt, 20 clay) must fall inside the Loam field; by name, in any column order
    from matplotlib.path import Path as MPath
    loam = MPath([np.ravel(P.ternary_xy([p[1]], [p[2]], [p[0]])) for p in SOIL_FIELDS["Loam"]])
    assert loam.contains_point(np.ravel(P.ternary_xy([40], [40], [20])))
    f = Figure(); soil_texture(f, np.array([20.0]), [np.array([40.0]), np.array([40.0])], ["Silt", "Sand"], "Clay", {})
    pt = [l for l in f.axes[0].lines if l.get_label() == "Samples"][0]
    assert np.allclose([pt.get_xdata()[0], pt.get_ydata()[0]], np.ravel(P.ternary_xy([40], [40], [20])))
    feldspar(Figure(), np.array([60.0]), [np.array([5.0]), np.array([35.0])], ["Or", "An"], "Ab", {})
    assert all(abs(sum(p) - 100) < 1e-6 for p in AFM_BOUNDARY)
    f = Figure(); afm(f, np.array([50.0]), [np.array([3.0]), np.array([1.0]), np.array([10.0]), np.array([6.0])], ["Na2O", "K2O", "FeOt", "MgO"], "SiO2", {})
    pt = [l for l in f.axes[0].lines if l.get_label() == "Samples"][0]  # A 4, F 10, M 6 of 20
    assert np.allclose([pt.get_xdata()[0], pt.get_ydata()[0]], np.ravel(P.ternary_xy([20], [30], [50])))
    f = Figure(); pearce("Rb vs Y+Nb")(f, np.array(["g1"]), [np.array([150.0]), np.array([30.0]), np.array([12.0])], ["Rb", "Y", "Nb"], "Sample", {})
    pt = [l for l in f.axes[0].lines if l.get_label() == "Samples"][0]; assert pt.get_xdata()[0] == 42 and pt.get_ydata()[0] == 150
    assert ion_of("HCO3 (mg/L)") == "HCO3" and ion_of("CO3") == "CO3" and ion_of("Cl_mgL") == "Cl" and ion_of("Calcite") is None
    assert abs(mg_to_meq("Ca", [40.08])[0] - 2.0) < 0.01
    print("PLOTS4 OK")


if __name__ == "__main__": _demo()
