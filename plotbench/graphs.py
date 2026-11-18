"""PlotBench graphs: graph windows, customization dialog, themes, templates, multi-panel layouts.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
from cycler import cycler
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox, QDialogButtonBox,
    QTabWidget, QInputDialog, QMessageBox, QListWidget, QAbstractItemView, QSpinBox, QHBoxLayout)

from . import plots as P
from . import analysis as A
from . import plots3 as P3  # noqa: F401  (registers the colour-mapped plot types)
from . import plots4  # noqa: F401  (registers spider, TAS and QAP)
from . import plots5  # noqa: F401  (raincloud and geochronology)
from . import matrix as MX

PALETTES = {
    "Default (tab10)": list(matplotlib.colormaps["tab10"].colors),
    "Colour-blind safe (Okabe-Ito)": ["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"],
    "Bold (Set1)": list(matplotlib.colormaps["Set1"].colors),
    "Grayscale": ["#000000", "#555555", "#888888", "#aaaaaa", "#cccccc"],
}
CMAPS = ["viridis", "plasma", "inferno", "magma", "cividis", "jet", "rainbow", "coolwarm", "RdBu_r", "Spectral_r", "gray", "terrain"]
POINT_TYPES = {"Line", "Scatter", "Line + Symbol", "Step", "Drop Line (Stem)", "Semi-log Y (Line + Symbol)", "Area"}
LEGEND = ["best", "upper right", "upper left", "lower left", "lower right", "center right", "outside right", "none"]
FONTS = ["Arial", "Times New Roman", "Calibri", "Helvetica", "DejaVu Sans", "Courier New"]
MARKERS = {"keep": None, "circle": "o", "square": "s", "triangle": "^", "diamond": "D", "cross": "x", "plus": "+", "none": ""}
LINESTYLES = {"keep": None, "solid": "-", "dashed": "--", "dotted": ":", "dash-dot": "-.", "none": "None"}

DEFAULT_STYLE = {
    "title": "", "xlabel": "", "ylabel": "", "xscale": "linear", "yscale": "linear",
    "xmin": "", "xmax": "", "ymin": "", "ymax": "", "legend": "best", "legend_frame": False,
    "font": "Arial", "font_size": 11.0, "line_width": 1.5, "marker_size": 5.0, "marker": "keep", "linestyle": "keep",
    "palette": "Default (tab10)", "cmap": "viridis", "grid": False, "ticks_in": True, "mirror_ticks": True,
    "minor_ticks": False, "width_in": 6.0, "height_in": 4.5, "dpi": 600, "background": "#ffffff", "xbreak": "", "ybreak": "",
    "view_aspect": "Same as export size",
}
VIEW_ASPECTS = {"Same as export size": None, "4:3": 4 / 3, "1:1 (square)": 1.0, "3:2": 1.5, "16:9": 16 / 9, "Fill the window": 0}
THEMES = {
    "Publication (default)": {},
    "Classic grid": {"grid": True, "ticks_in": False, "mirror_ticks": False, "legend_frame": True},
    "Colour-blind safe": {"palette": "Colour-blind safe (Okabe-Ito)", "cmap": "cividis"},
    "Monochrome print": {"palette": "Grayscale", "cmap": "gray", "marker": "keep"},
    "Presentation (large)": {"font_size": 16.0, "line_width": 2.5, "marker_size": 8.0},
    "Journal single column (3.5 in)": {"width_in": 3.5, "height_in": 2.8, "font_size": 8.0, "line_width": 1.0, "marker_size": 3.5},
}


def user_dir():
    d = Path(os.environ.get("APPDATA", Path.home())) / "PlotBench"; (d / "templates").mkdir(parents=True, exist_ok=True); return d


def default_theme():
    f = user_dir() / "default_style.json"
    try: return json.loads(f.read_text())
    except (OSError, ValueError): return {}


def full_style(style): return {**DEFAULT_STYLE, **default_theme(), **(style or {})}


def rc_for(st):
    return {"font.family": st["font"], "font.size": st["font_size"], "axes.linewidth": 1.0,
            "lines.linewidth": st["line_width"], "lines.markersize": st["marker_size"], "image.cmap": st["cmap"],
            "axes.grid": st["grid"], "axes.prop_cycle": cycler(color=PALETTES.get(st["palette"], PALETTES["Default (tab10)"])),
            "xtick.direction": "in" if st["ticks_in"] else "out", "ytick.direction": "in" if st["ticks_in"] else "out",
            "xtick.top": st["mirror_ticks"], "ytick.right": st["mirror_ticks"], "legend.frameon": st["legend_frame"],
            "figure.facecolor": st["background"], "savefig.facecolor": st["background"]}


def _num(v):
    """Axis limits typed as 0.01, 1e-18, 10^-18, 2.5x10^3 ...; blank or unreadable -> automatic."""
    if v is None or str(v).strip() == "": return None
    try: return A.parse_number(v)
    except ValueError: return None


def apply_post(fig, st):
    axes = [a for a in fig.axes if a.get_label() != "<colorbar>" and not hasattr(a, "_colorbar")]
    if not axes: return
    ax = axes[0]
    if st["title"]: ax.set_title(st["title"])
    if st["xlabel"]:
        for a in ([b for b in axes if b.get_xlabel()] or [ax]): a.set_xlabel(st["xlabel"])  # bottom panels of Harker / stacked plots
    if st["ylabel"]: ax.set_ylabel(st["ylabel"])
    if ax.name == "rectilinear":
        for axis in ("x", "y"):
            sc = st[f"{axis}scale"]
            if sc != "linear":  # 'linear' is the default: leave log axes that a plot type sets itself (spider, semi-log) alone
                try: getattr(ax, f"set_{axis}scale")(sc)
                except ValueError: pass
            lo, hi = _num(st[f"{axis}min"]), _num(st[f"{axis}max"])
            if lo is not None or hi is not None: getattr(ax, f"set_{axis}lim")(lo, hi)
    if st["minor_ticks"]:
        for a in axes:
            if a.name == "rectilinear": a.minorticks_on()
    start = 0
    for ai, a in enumerate(axes):
        mk, ls = MARKERS.get(st["marker"]), LINESTYLES.get(st["linestyle"])
        for ln in a.get_lines():
            if ln.get_label().startswith("_"): continue  # grid/helper lines
            if mk is not None: ln.set_marker(mk or "None")
            if ls is not None: ln.set_linestyle(ls)
        _series_overrides(a, st, start); start += len(_data_artists(a))
        leg = a.get_legend()
        if st["legend"] == "none":
            if leg: leg.remove()
        elif getattr(a, "_pb_custom_legend", False):
            if leg is not None and st["legend"] != "best": leg.set_loc(st["legend"]) if hasattr(leg, "set_loc") else None
        elif (leg and a.get_legend_handles_labels()[1]) or len(a.get_legend_handles_labels()[1]) > 1:
            if st["legend"] == "outside right": _legend(a, loc="upper left", bbox_to_anchor=(1.02, 1))
            else: _legend(a, loc=st["legend"])
        pos = (st.get("legend_pos") or {}).get(str(ai)); leg = a.get_legend()
        if pos and leg is not None and st["legend"] != "none":  # where the user dragged it (lower-left corner, axes fraction)
            leg.set_bbox_to_anchor(None); leg.set_loc((float(pos[0]), float(pos[1])))
    _point_overrides(axes, st)
    _text_overrides(axes, st)


def _data_lines(ax): return [ln for ln in ax.get_lines() if not ln.get_label().startswith("_")]


def _data_artists(ax):
    """Everything the format bar can style on one axes, in a fixed order: labelled lines, then labelled point sets
    (scatter collections), then labelled bar series. Indices run on across these groups, so they never collide."""
    pts = [c for c in ax.collections if type(c).__name__ == "PathCollection" and not str(c.get_label()).startswith("_")]
    bars = [b for b in ax.containers if hasattr(b, "patches") and type(b).__name__ == "BarContainer" and not str(b.get_label()).startswith("_")]
    return _data_lines(ax) + pts + bars


def _series_overrides(ax, st, start=None):
    """Per-curve formatting from the format bar: style['series'] = {'all': {...}, '0': {...}, ...} by curve order across all
    panels of the graph (start = number of curves in the panels before this one)."""
    ser = st.get("series") or {}
    if not ser: return
    if start is None: axes = list(ax.figure.axes); start = sum(len(_data_artists(a)) for a in axes[:axes.index(ax)]) if ax in axes else 0
    arts = _data_artists(ax)
    for i, art in enumerate(arts, start):
        ov = {**ser.get("all", {}), **ser.get(str(i), {})}
        kind = type(art).__name__
        if ov.get("hide"): art.set_visible(False)
        elif ov.get("fill") and kind == "Line2D": _fill_under(ax, art, ov, arts, i - start)
        if "z" in ov:  # layer: in front of or behind other curves, fields and texts
            for a_ in (art.patches if hasattr(art, "patches") and kind not in ("Line2D", "PathCollection") else [art]): a_.set_zorder(float(ov["z"]))
        if kind == "Line2D":
            if "color" in ov: art.set_color(ov["color"]); art.set_markerfacecolor(ov["color"]); art.set_markeredgecolor(ov["color"])
            if "lw" in ov: art.set_linewidth(float(ov["lw"]))
            if "ls" in ov: art.set_linestyle(ov["ls"])
            if "marker" in ov: art.set_marker(ov["marker"])
            if "ms" in ov: art.set_markersize(float(ov["ms"]))
            if ov.get("hollow"): art.set_markerfacecolor("none")
            elif "hollow" in ov and "color" not in ov: art.set_markerfacecolor(art.get_color())
        elif kind == "PathCollection":
            if "color" in ov and art.get_array() is None: art.set_facecolor(ov["color"])  # colour-mapped points keep their map
            if "ms" in ov: art.set_sizes([float(ov["ms"]) ** 2])
            if ov.get("hollow") and art.get_array() is None: art.set_facecolor("none")
        else:  # bar series
            for p in art.patches:
                if "color" in ov: p.set_facecolor(ov["color"])
                if "lw" in ov: p.set_linewidth(float(ov["lw"]))
    leg = ax.get_legend()
    if leg is not None and not getattr(ax, "_pb_custom_legend", False):  # keep the legend in step with the new looks
        h, l = ax.get_legend_handles_labels()
        keep = [(hh, ll) for hh, ll in zip(h, l) if getattr(hh, "get_visible", lambda: True)()]  # hidden curves leave the legend
        if keep: ax.legend(*zip(*keep), loc=leg._loc if hasattr(leg, "_loc") else "best")
        else: leg.remove()


def _legend(ax, **kw):
    """Legend of the visible curves only (curves hidden in Plot Details are left out)."""
    h, l = ax.get_legend_handles_labels(); keep = [(hh, ll) for hh, ll in zip(h, l) if getattr(hh, "get_visible", lambda: True)()]
    if keep: return ax.legend(*zip(*keep), **kw)


def _fill_under(ax, art, ov, arts, i):
    """Fill the area under a line (Plot Details): to Y = 0, to the bottom of the axes, or to the next curve; colour, opacity, hatch."""
    from matplotlib.colors import to_rgba
    try: xd, yd = np.asarray(art.get_xdata(), float), np.asarray(art.get_ydata(), float)
    except (TypeError, ValueError): return
    lim = ax.get_ylim(); to = int(ov.get("fill_to", 0)); ref = 0.0
    if to == 1: ref = min(lim)
    elif to == 2:
        nxt = next((b for b in arts[i + 1:] if type(b).__name__ == "Line2D"), None)
        if nxt is not None:
            bx, by = np.asarray(nxt.get_xdata(), float), np.asarray(nxt.get_ydata(), float); o = np.argsort(bx); ref = np.interp(xd, bx[o], by[o])
    fc = to_rgba(ov.get("fillcolor", art.get_color()), float(ov.get("alpha", 0.3))); hatch = ov.get("hatch") or None
    ax.fill_between(xd, yd, ref, facecolor=fc, edgecolor=art.get_color() if hatch else "none", hatch=hatch, lw=0,
                    zorder=art.get_zorder() - 0.2, label="_fill")
    ax.set_ylim(lim)


def _plot_texts(ax):
    """Texts drawn by the plot itself (field names, labels, captions), not user annotations or point labels."""
    return [t for t in ax.texts if not str(t.get_gid() or "").startswith("pbann:") and t.get_label() != "_point" and t.get_text().strip()]


def _text_keys(ax, ai):
    """[(key, text)]: key = 'panel|text|n' (n counts repeats of the same words), stable from one redraw to the next."""
    seen, out = {}, []
    for t in _plot_texts(ax):
        key = getattr(t, "_pb_key", None)  # given once: a text whose words were edited keeps the key of its original words
        if key is None:
            s = t.get_text(); n = seen.get(s, 0); seen[s] = n + 1; key = t._pb_key = f"{ai}|{s}|{n}"
        out.append((key, t))
    return out


def _break(spec):
    """('x' or 'y', from, to) of an axis break typed in Graph Properties as 'from, to'; None when there is none."""
    st = spec.get("style") or {}
    for axis in ("y", "x"):
        parts = [p for p in str(st.get(f"{axis}break") or "").replace(";", ",").split(",") if p.strip()]
        if len(parts) == 2:
            a, b = _num(parts[0]), _num(parts[1])
            if a is not None and b is not None and a != b: return axis, min(a, b), max(a, b)
    return None


TEXT_Z = {"front": 10.0, "middle": 3.0, "back": 0.5}  # over points / above lines and fields, under points / under everything


def _text_overrides(axes, st):
    """Plot texts moved, restyled, re-layered or hidden by the user: style['texts'] = {key: {pos, z, size, color, text, hide}}."""
    tov = st.get("texts") or {}
    if not tov: return
    for ai, a in enumerate(axes):
        for key, t in _text_keys(a, ai):
            ov = tov.get(key)
            if not ov: continue
            if "pos" in ov: t.set_position(tuple(ov["pos"]))
            if "z" in ov: t.set_zorder(TEXT_Z.get(ov["z"], 3.0))
            if "size" in ov: t.set_fontsize(float(ov["size"]))
            if "color" in ov: t.set_color(ov["color"])
            if "text" in ov: t.set_text(ov["text"])
            if ov.get("hide"): t.set_visible(False)


def _point_overrides(axes, st):
    """Single points formatted by right-click: style['points'] = {'curve:point': {color, marker, ms, hide, label}}."""
    pts = st.get("points") or {}
    if not pts: return
    arts = [x for a in axes for x in _data_artists(a)]; hidden = {}
    for key, ov in pts.items():
        try: i, j = map(int, key.split(":")); art = arts[i]
        except (ValueError, IndexError): continue
        kind = type(art).__name__
        if kind == "Line2D":
            xd, yd = np.asarray(art.get_xdata()), np.asarray(art.get_ydata())
            if j >= len(xd): continue
            if ov.get("hide"): hidden.setdefault(id(art), (art, set()))[1].add(j); continue
            xy, ax, mk = (xd[j], yd[j]), art.axes, ov.get("marker", art.get_marker() if art.get_marker() not in (None, "None", "") else "o")
            ms, col = float(ov.get("ms", max(art.get_markersize(), 6))), ov.get("color", art.get_color())
        elif kind == "PathCollection":
            off = np.asarray(art.get_offsets())
            if j >= len(off): continue
            if ov.get("hide"):
                s = np.resize(art.get_sizes(), len(off)).astype(float); s[j] = 0; art.set_sizes(s); continue
            xy, ax, mk = tuple(off[j]), art.axes, ov.get("marker", "o")
            ms, col = float(ov.get("ms", np.sqrt(np.resize(art.get_sizes(), len(off))[j]))), ov.get("color", matplotlib.colors.to_hex(art.get_facecolor()[0]))
        else: continue
        ax.plot([xy[0]], [xy[1]], mk, ms=ms, mfc=col, mec="k", mew=0.8, ls="none", zorder=max(art.get_zorder(), 2) + 1, label="_point")
        if ov.get("label"):
            ax.annotate(f"{xy[1]:.4g}", xy, xytext=(5, 5), textcoords="offset points", fontsize=8, label="_point")
    for art, idx in hidden.values():
        if art.get_linestyle() in ("None", "none", ""):  # points only: blank the hidden ones (same length, so later indices stay right)
            try:
                xd, yd = np.array(art.get_xdata(), float), np.array(art.get_ydata(), float)
                xd[list(idx)] = np.nan; yd[list(idx)] = np.nan; art.set_data(xd, yd)
            except (TypeError, ValueError): art.set_markevery([k for k in range(len(art.get_xdata())) if k not in idx])
        else: art.set_markevery([k for k in range(len(art.get_xdata())) if k not in idx])  # a line keeps its path, loses the marker


def _save(fig, fn, dpi, transparent=False, editable_text=True):
    """Write a figure; DPI is stored in raster files (PNG/TIFF/JPG) so Word and journals see the right print size.
    editable_text: TrueType fonts in PDF/EPS and real text in SVG, so the labels stay editable in Illustrator or Inkscape."""
    import matplotlib
    kw = {"dpi": float(dpi)}
    if transparent and not str(fn).lower().endswith((".jpg", ".jpeg")):  # JPEG has no transparency
        kw["transparent"] = True
    rc = {"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"} if editable_text else {"pdf.fonttype": 3, "ps.fonttype": 3, "svg.fonttype": "path"}
    with matplotlib.rc_context(rc): fig.savefig(fn, **kw)


class _AxTarget:
    """Lets a graph draw into one inset Axes: plot functions see a 'figure' whose only subplot is that Axes."""

    def __init__(self, fig, ax): self.f, self.ax = fig, ax

    @property
    def axes(self): return [self.ax]

    def clear(self): self.ax.clear()
    def set_facecolor(self, c): self.ax.set_facecolor(c)
    def text(self, *a, **k): return self.ax.text(*a, transform=self.ax.transAxes, **k)
    def colorbar(self, *a, **k): return self.f.colorbar(*a, **k)

    def add_subplot(self, *a, **kw):
        if kw.get("projection") not in (None, "rectilinear") or (a and a[0] not in (111, (1, 1, 1))):
            raise ValueError("This graph type cannot be shown as an inset")
        return self.ax

    def subplots(self, *a, **k): raise ValueError("This graph type cannot be shown as an inset")


class _AspectHost(QWidget):
    """Holds the graph canvas at the graph's shape (Graph Properties > Fonts & size > Shape on screen, by default the export
    shape) so plots are not stretched to the window; the spare width on the right holds a panel of shortcuts."""

    def __init__(self, g):
        super().__init__(g); self.g = g; g.canvas.setParent(self)
        from PySide6.QtWidgets import QScrollArea
        self.panel = QScrollArea(self); self.panel.setWidgetResizable(True); self.panel.setFrameShape(QScrollArea.NoFrame)
        self.panel.setWidget(_shortcut_panel(g)); self.panel.hide()

    def ratio(self):
        st = full_style(self.g.spec.get("style"))
        r = VIEW_ASPECTS.get(st.get("view_aspect"), None)
        if r is None: r = float(st["width_in"]) / max(float(st["height_in"]), 0.1)
        return r

    def resizeEvent(self, ev):
        w, h = self.width(), self.height(); r = self.ratio(); cw = w
        if r and w > h * r + 150: cw = int(h * r)  # wide window: keep the shape, the rest is the shortcut panel
        self.g.canvas.setGeometry(0, 0, cw, h)
        if w - cw >= 150 and (getattr(self.g.main, "settings", None) or {}).get("graph_panel", True):
            self.panel.setGeometry(cw, 0, w - cw, h); self.panel.show()
        else: self.panel.hide()

    def relayout(self):
        from PySide6.QtGui import QResizeEvent
        self.resizeEvent(QResizeEvent(self.size(), self.size()))


GRAPH_SHORTCUTS = [  # (group, label, Main method or callable on the main window); the panel uses whatever width is spare
    ("View", "Zoom in", lambda m: m.need_graph() and m.need_graph().zoom_by(0.8)),
    ("View", "Zoom out", lambda m: m.need_graph() and m.need_graph().zoom_by(1.25)),
    ("View", "Reset view", lambda m: m.need_graph() and m.need_graph().reset_view()),
    ("View", "Pan (drag)", lambda m: m.need_graph() and m.need_graph().nav.pan()),
    ("Format", "Plot details (show / hide curves, fill)", "plot_details"),
    ("Format", "Graph properties", "graph_props"), ("Format", "Edit plot", "edit_plot"), ("Format", "Apply template", "apply_template"),
    ("Format", "Save as template", lambda m: m.need_graph() and save_template(m, m.need_graph().spec["style"])),
    ("Format", "Group samples", "group_samples"), ("Format", "Copy format to all graphs", "copy_format_all"),
    ("Draw", "Line", lambda m: m.draw_shape("line")), ("Draw", "Arrow", lambda m: m.draw_shape("arrow2")),
    ("Draw", "Rectangle", lambda m: m.draw_shape("rect")), ("Draw", "Circle / ellipse", lambda m: m.draw_shape("circle")),
    ("Draw", "Polygon", lambda m: m.draw_shape("polygon")), ("Draw", "Region (freehand)", lambda m: m.draw_shape("region")),
    ("Add", "Text", "add_text"), ("Add", "Arrow", "add_arrow"), ("Add", "Reference line", "add_refline"), ("Add", "Confidence ellipse", "add_ellipse"),
    ("Add", "Data from a sheet", "add_series"), ("Add", "Zoom inset", "zoom_inset"), ("Add", "Inset graph", "add_inset"),
    ("Arrange", "Split into panels", "split_panels"), ("Arrange", "Layout page", "new_layout"), ("Arrange", "Duplicate graph", "dup_graph"),
    ("Arrange", "Repeat for every sheet", "clone_graph_sheets"),
    ("Analyse", "Linear fit", lambda m: m.fit_poly(1)), ("Analyse", "Polynomial fit", lambda m: m.fit_poly(None)), ("Analyse", "Nonlinear fit", "fit_nl"),
    ("Analyse", "Peak analyzer", "peak_analyzer"), ("Analyse", "Smooth", "smooth"), ("Analyse", "Statistics", "desc"), ("Analyse", "Clear fits", "clear_fits"),
    ("Output", "Copy to clipboard", "copy_graph"), ("Output", "Export image", "export_graph"), ("Output", "All graphs to one PDF", "export_pdf_book"),
    ("Output", "Undo", "undo"), ("Output", "Redo", "redo"), ("Output", "Refresh", "refresh_all"),
]


def _shortcut_panel(g):
    """Side panel of the graph window: the curves (tick to show) and the shortcut buttons, in sections that fold up when their
    heading is clicked (the folded sections are remembered)."""
    from PySide6.QtWidgets import QGridLayout, QPushButton, QToolButton
    from PySide6.QtCore import Qt
    w = QWidget(); outer = QVBoxLayout(w); outer.setContentsMargins(6, 4, 6, 4); outer.setSpacing(2)
    settings = getattr(g.main, "settings", None); folded = set((settings or {}).get("panel_collapsed", []))
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QIcon
    from .ui_style import arrows
    ar = arrows(getattr(g.main, "_theme", None) or "light")

    def section(title):
        h = QToolButton(); h.setText(title); h.setCheckable(True); h.setChecked(title not in folded); h.setAutoRaise(True)
        h.setToolButtonStyle(Qt.ToolButtonTextBesideIcon); h.setIconSize(QSize(16, 16)); h.setIcon(QIcon(ar["down" if h.isChecked() else "right"]))
        h.setStyleSheet("font-weight: bold; font-size: 10pt; border: none; padding-top: 4px"); h.setToolTip(f"Show or fold the {title} section")
        body = QWidget(); body.setVisible(h.isChecked())

        def flip(on, t=title):
            body.setVisible(on); h.setIcon(QIcon(arrows(getattr(g.main, "_theme", None) or "light")["down" if on else "right"]))
            if settings is not None:
                f = set(settings.get("panel_collapsed", [])); (f.discard(t) if on else f.add(t)); settings["panel_collapsed"] = sorted(f)
        h.toggled.connect(flip); h.setProperty("fold_header", True); outer.addWidget(h); outer.addWidget(body); return body
    g._curve_box = QVBoxLayout(section("Curves")); g._curve_box.setContentsMargins(4, 0, 0, 0); g._curve_box.setSpacing(0)
    grid = None; last = None; row = col = 0
    for group, label, fn in GRAPH_SHORTCUTS:
        if group != last:
            grid = QGridLayout(section(group)); grid.setContentsMargins(0, 0, 0, 0); grid.setVerticalSpacing(3); last = group; row = col = 0
        b = QPushButton(label); b.setToolTip(label); b.setStyleSheet("text-align: left; padding: 3px 8px")
        slot = (lambda m=g.main, f=fn: f(m)) if callable(fn) else (lambda m=g.main, f=fn: getattr(m, f)())
        b.clicked.connect(lambda checked=False, s=slot, t=label: (g.main.mdi.setActiveSubWindow(g.parentWidget()) if hasattr(g.main, "mdi") and g.parentWidget() else None,
                                                                 g.main.run_command(t, s) if hasattr(g.main, "run_command") else s()))
        grid.addWidget(b, row, col); col += 1
        if col == 2: col = 0; row += 1
    outer.addStretch(1); return w


class GraphWindow(QWidget):
    kind = "graph"

    def __init__(self, main, name, spec=None):
        super().__init__(); self.main = main; self.setWindowTitle(name); self.spec = spec or {}
        self.spec.setdefault("style", {})
        self.fig = Figure(figsize=(6, 4.5), layout="constrained"); self.canvas = FigureCanvasQTAgg(self.fig)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        tb = NavigationToolbar2QT(self.canvas, self); tb.addSeparator()
        self.act_region = tb.addAction("Region tools"); self.act_region.setCheckable(True)
        self.act_region.setToolTip("Drag across the graph to fit, integrate, get statistics, FFT, find peaks or mask that X range")
        self.act_reader = tb.addAction("Data reader"); self.act_reader.setCheckable(True)
        self.act_reader.setToolTip("Click near a point to read its X, Y and row")
        self.act_region.toggled.connect(lambda on: (on and self.act_reader.setChecked(False), self.draw()))
        self.act_reader.toggled.connect(lambda on: on and self.act_region.setChecked(False))
        self.canvas.mpl_connect("button_press_event", self._click)
        self.canvas.mpl_connect("button_press_event", self._drag_press); self.canvas.mpl_connect("button_release_event", self._drag_release)
        self.canvas.mpl_connect("button_press_event", self._double_click)
        self.canvas.mpl_connect("button_press_event", self._point_menu)
        self.canvas.mpl_connect("motion_notify_event", self._text_drag_move); self._tdrag = None
        self._drags, self._pre = [], None
        self.nav = tb; self._trim_nav(tb)
        self.canvas.mpl_connect("scroll_event", self._wheel)
        from .formatbar import FormatBar
        self.fmt = FormatBar(self); self.series_lines, self.series_names = [], []
        self.host = _AspectHost(self); lay.addWidget(tb); lay.addWidget(self.fmt); lay.addWidget(self.host, 1)
        self.fits = []; self.history = []; self.redo_stack = []; self.span = None; self.rows = np.array([], int)
        self.setAcceptDrops(True)

    def _trim_nav(self, tb):
        """Matplotlib's bar keeps Home, Back, Forward, Pan and Zoom (its Subplots, Customize and Save repeat PlotBench commands);
        Zoom in, Zoom out and Reset view are added. The mouse wheel also zooms, about the cursor."""
        from PySide6.QtGui import QAction
        from .toolbars import _icon, draw_tool
        for a in list(tb.actions()):
            if a.text() in ("Subplots", "Customize", "Save"): tb.removeAction(a)
        theme = getattr(self.main, "_theme", "light") or "light"
        for ic, tip, fn in (("zoomin", "Zoom in (Ctrl+=, or the mouse wheel)", lambda: self.zoom_by(0.8)),
                            ("zoomout", "Zoom out (Ctrl+-, or the mouse wheel)", lambda: self.zoom_by(1.25)),
                            ("fitview", "Reset view: show the whole graph again (Ctrl+0)", self.reset_view)):
            a = QAction(_icon(draw_tool(ic), theme), tip, self); a.setToolTip(tip); a.triggered.connect(fn); tb.insertAction(self.act_region, a)
        tb.insertSeparator(self.act_region)

    def zoom_by(self, f, centre=None):
        """Scale every axis range by f (< 1 zooms in, > 1 out) about the middle, or about centre = (x, y, axes) from the mouse.
        Log axes zoom in log space. Back on the graph toolbar returns to the previous view."""
        axes = [a for a in self.fig.axes if a.name == "rectilinear" and a.get_navigate()]
        if not axes: return
        self.nav.push_current(); done = set()

        def scaled(lo, hi, c, log):
            log = log and lo > 0 and hi > 0
            if log: lo, hi, c = np.log10(lo), np.log10(hi), (np.log10(c) if c is not None and c > 0 else None)
            c = (lo + hi) / 2 if c is None else c; lo, hi = c + (lo - c) * f, c + (hi - c) * f
            return (10 ** lo, 10 ** hi) if log else (lo, hi)
        for ax in axes:
            mine = centre is not None and centre[2] is ax
            for axis, get, put, scale, c in (("x", ax.get_xlim, ax.set_xlim, ax.get_xscale(), centre[0] if mine else None),
                                             ("y", ax.get_ylim, ax.set_ylim, ax.get_yscale(), centre[1] if mine else None)):
                grp = (ax.get_shared_x_axes() if axis == "x" else ax.get_shared_y_axes()).get_siblings(ax)
                if any((axis, id(b)) in done for b in grp): continue  # shared axes (twin Y, linked panels) zoom once
                done.add((axis, id(ax))); put(*scaled(*get(), c, scale == "log"))
        self.canvas.draw_idle()

    def reset_view(self):
        """Back to the full view stored with the graph (undoes zooming and panning)."""
        self.draw()
        try: self.nav.update()  # clear the Back / Forward history
        except AttributeError: pass

    def _wheel(self, ev):
        if ev.inaxes is None or getattr(self, "_drawing", None): return
        self.zoom_by(0.85 if ev.button == "up" else 1 / 0.85, (ev.xdata, ev.ydata, ev.inaxes))

    def _refresh_curves(self):
        """Tick boxes for every curve in the side panel (Curves section): untick to hide a curve, as in Plot Details."""
        box = getattr(self, "_curve_box", None)
        if box is None: return
        from PySide6.QtWidgets import QCheckBox
        from PySide6.QtCore import QTimer
        while box.count():
            w = box.takeAt(0).widget()
            if w is not None: w.deleteLater()
        ser = (self.spec.get("style") or {}).get("series") or {}
        for i, n in enumerate(self.series_names):
            cb = QCheckBox(n if len(n) <= 38 else n[:36] + "..."); cb.setToolTip(f"{n}: untick to hide this curve (it also leaves the legend)")
            cb.setChecked(not (ser.get(str(i)) or {}).get("hide"))
            cb.toggled.connect(lambda on, i=i: QTimer.singleShot(0, lambda: self.set_curve_visible(i, on)))
            box.addWidget(cb)
        if not self.series_names:
            from PySide6.QtWidgets import QLabel
            lab = QLabel("(no curves)"); lab.setStyleSheet("color: gray"); box.addWidget(lab)

    def set_curve_visible(self, i, on):
        self.snapshot(); st = self.spec.setdefault("style", {}); ser = dict(st.get("series") or {}); o = dict(ser.get(str(i)) or {})
        if on: o.pop("hide", None)
        else: o["hide"] = True
        if o: ser[str(i)] = o
        else: ser.pop(str(i), None)
        st["series"] = ser; self.draw()
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    # ---- drop worksheet columns onto the graph (as in Origin)
    def dragEnterEvent(self, ev):
        from .sheets import COLUMNS_MIME
        if ev.mimeData().hasFormat(COLUMNS_MIME): ev.acceptProposedAction()
        else: ev.ignore()  # files go on to the main window

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, ev):
        from .sheets import COLUMNS_MIME
        d = json.loads(bytes(ev.mimeData().data(COLUMNS_MIME)).decode()); ev.acceptProposedAction()
        self.main.safe(lambda: self.add_columns(d["book"], d["sheet"], d["x"], d["ys"]))

    def add_columns(self, book, sheet, x, ys):
        """Add Y columns to this graph: same sheet and X -> more series of this plot; otherwise overlaid curves. One undo step."""
        s = self.spec
        if s.get("type") in P.MATRIX_PLOT_TYPES or not ys: return
        self.snapshot()
        if book == s.get("book") and sheet == s.get("sheet") and x == s.get("x"):
            s["ys"] = list(s.get("ys", [])) + [y for y in ys if y not in s.get("ys", [])]
        else:
            style = "o" if "Scatter" in str(s.get("type")) else "-"
            for y in ys: s.setdefault("annotations", []).append({"kind": "series", "book": book, "sheet": sheet, "x": x, "y": y, "style": style})
        self.draw(); self.main.mark_dirty()
        self.main.statusBar().showMessage(f"Added {', '.join(ys)} to {self.name}", 5000)

    @property
    def name(self): return self.windowTitle()

    def data(self):
        s = self.spec; sh = self.main.sheet_ref(s["book"], s.get("sheet"))
        x = sh.df[s["x"]].to_numpy() if s.get("x") else np.arange(1, len(sh.df) + 1)
        if s.get("x") and sh.desig.get(s["x"]) != "Label":
            raw = sh.df[s["x"]]; xn = pd.to_numeric(raw, errors="coerce")
            if xn.notna().any() and xn.notna().sum() == raw.notna().sum(): x = sh.arr(s["x"])  # masked X cells become NaN
        ys = [sh.arr(c) for c in self.cols(sh)]; self.rows = np.arange(len(x))
        if ys:
            x_ok = np.isfinite(x) if x.dtype.kind in "fiu" else pd.notna(x)
            keep = x_ok & np.any([np.isfinite(y) for y in ys], axis=0); x = x[keep]; ys = [y[keep] for y in ys]; self.rows = self.rows[keep]
        return sh, x, ys

    def cols(self, sh):
        """Y columns that still exist in the sheet (columns can be deleted or undone away)."""
        return [c for c in self.spec["ys"] if c in sh.df.columns]

    def render(self, fig, _depth=0):
        """Draw this graph into any Figure or SubFigure (used by the window and by layouts), then its insets."""
        brk = _break(self.spec) if _depth == 0 else None
        try:
            if brk: self._render_broken(fig, *brk)
            else: self._render_main(fig)
        except Exception as e:  # e.g. a plot type that needs more columns: say so in the graph instead of failing every redraw
            if _depth: raise ValueError(str(e))
            fig.clear(); fig.text(0.5, 0.5, f"{self.spec.get('type')} cannot be drawn:\n{e}", ha="center", va="center", color="firebrick", wrap=True)
            return
        if _depth > 2: return  # insets of insets stop here
        for ins in self.spec.get("insets", []):
            g = self.main.win(ins["graph"])
            if g is None or g is self or g.kind != "graph": continue
            ax = fig.add_axes(ins.get("pos", [0.6, 0.55, 0.32, 0.32]))
            try: g.render(_AxTarget(fig, ax), _depth + 1)
            except ValueError as e:
                ax.clear(); ax.set_xticks([]); ax.set_yticks([])
                ax.text(0.5, 0.5, f"{ins['graph']}:\n{e}", ha="center", va="center", fontsize=7, wrap=True, transform=ax.transAxes)
        if _depth == 0 and not brk: self._zooms(fig)

    def _render_broken(self, fig, axis, lo, hi):
        """Axis break: the graph drawn twice (one part above the other for Y, side by side for X), each showing one side of the
        gap, joined by // marks."""
        fig.clear()
        subs = fig.subfigures(2, 1, hspace=0.0) if axis == "y" else fig.subfigures(1, 2, wspace=0.0)
        for sf in subs: self._render_main(sf)
        pa, pb = ([a for a in sf.axes if a.name == "rectilinear" and a.get_label() != "<colorbar>" and not hasattr(a, "_colorbar")] for sf in subs)
        if not pa or not pb: return
        A, B = pa[0], pb[0]  # Y: A on top (above the gap), B below; X: A on the left (below the gap), B on the right
        kw = dict(markersize=10, linestyle="none", color="k", mec="k", mew=1, clip_on=False, label="_break")
        if axis == "y":
            full = sorted(A.get_ylim()); A.set_ylim(hi, max(full[1], hi)); B.set_ylim(min(full[0], lo), lo)
            A.spines["bottom"].set_visible(False); B.spines["top"].set_visible(False)
            A.tick_params(axis="x", which="both", bottom=False, labelbottom=False); B.tick_params(axis="x", which="both", top=False)
            A.set_xlabel(""); B.set_title(""); B.set_ylabel("")
            p, q = A.get_position(), B.get_position(); A.set_position([p.x0, 0.03, p.width, p.y1 - 0.03]); B.set_position([q.x0, q.y0, q.width, 0.97 - q.y0])
            A.plot([0, 1], [0, 0], transform=A.transAxes, marker=[(-1, -0.5), (1, 0.5)], **kw)
            B.plot([0, 1], [1, 1], transform=B.transAxes, marker=[(-1, -0.5), (1, 0.5)], **kw)
        else:
            full = sorted(A.get_xlim()); A.set_xlim(min(full[0], lo), lo); B.set_xlim(hi, max(full[1], hi))
            A.spines["right"].set_visible(False); B.spines["left"].set_visible(False)
            B.tick_params(axis="y", which="both", left=False, labelleft=False); A.tick_params(axis="y", which="both", right=False)
            B.set_ylabel(""); B.set_title("")
            p, q = A.get_position(), B.get_position(); x0 = max(p.x0, 0.22)  # half-width part: room for the Y label
            A.set_position([x0, p.y0, 0.97 - x0, p.height]); B.set_position([0.03, q.y0, q.x1 - 0.03, q.height])
            A.plot([1, 1], [0, 1], transform=A.transAxes, marker=[(-0.5, -1), (0.5, 1)], **kw)
            B.plot([0, 0], [0, 1], transform=B.transAxes, marker=[(-0.5, -1), (0.5, 1)], **kw)
        if B.get_legend() is not None and A.get_legend() is not None: B.get_legend().remove()
        for ax in (A, B):  # a text or arrow belongs to the part of the axis its point lies in, not to both
            for t in ax.texts:
                if str(t.get_gid() or "").startswith("pbann:"):
                    t.set_clip_on(True); ap = getattr(t, "arrow_patch", None); ap.set_clip_on(True) if ap is not None else None

    def _zooms(self, fig):
        """Magnified insets of the regions chosen with Graph > Add Zoom Inset, joined to the region by connector lines."""
        zs = self.spec.get("zooms") or []
        axes = [a for a in fig.axes if a.name == "rectilinear" and a.get_label() != "<colorbar>" and not hasattr(a, "_colorbar")]
        if not zs or not axes: return
        ax = axes[0]
        for z in zs:
            ins = ax.inset_axes(z.get("pos", [0.56, 0.56, 0.38, 0.38]))
            try: self._render_main(_AxTarget(fig, ins))
            except (ValueError, KeyError): ins.remove(); continue
            ins.set_xlim(*z["x"]); ins.set_ylim(*z["y"]); ins.set_title(""); ins.set_xlabel(""); ins.set_ylabel(""); ins.tick_params(labelsize=7)
            if ins.get_legend() is not None: ins.get_legend().remove()
            for t in ins.texts: t.set_clip_on(True)
            ax.indicate_inset_zoom(ins, edgecolor="0.35")

    def start_zoom(self):
        """Drag a rectangle on the graph; a magnified inset of it is added (Graph > Add Zoom Inset)."""
        from matplotlib.widgets import RectangleSelector
        axes = [a for a in self._plot_axes() if a.name == "rectilinear"]
        if not axes or self.spec.get("source") == "matrix": return False

        def done(e1, e2):
            self._zsel.set_active(False)
            if None in (e1.xdata, e2.xdata, e1.ydata, e2.ydata) or e1.xdata == e2.xdata or e1.ydata == e2.ydata: return
            self.add_zoom(sorted([e1.xdata, e2.xdata]), sorted([e1.ydata, e2.ydata]))
        self._zsel = RectangleSelector(axes[0], done, useblit=True, button=[1], interactive=False, props=dict(facecolor="tab:blue", alpha=0.15))
        return True

    def add_zoom(self, xr, yr, pos=None):
        """Add a zoom inset of the region xr x yr; by default in the corner farthest from it."""
        if pos is None:
            ax = [a for a in self._plot_axes() if a.name == "rectilinear"][0]
            cx, cy = ax.transAxes.inverted().transform(ax.transData.transform(((xr[0] + xr[1]) / 2, (yr[0] + yr[1]) / 2)))
            pos = [0.06 if cx > 0.5 else 0.56, 0.06 if cy > 0.5 else 0.56, 0.38, 0.38]
        self.snapshot(); self.spec.setdefault("zooms", []).append({"x": [float(v) for v in xr], "y": [float(v) for v in yr], "pos": list(pos)})
        self.draw()
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def _plot(self, fn, fig, x, ys, names, xname, extra):
        """Draw the plot, or one panel per Y column in a rows x columns grid when spec['panels'] is set (0 = automatic)."""
        p = self.spec.get("panels")
        if not p or len(ys) < 2: return fn(fig, x, ys, names, xname, extra)
        n = len(ys); r, c = int(p.get("rows") or 0), int(p.get("cols") or 0)
        if not c: c = -(-n // r) if r else min(n, 3 if n <= 9 else 4)
        if not r or r * c < n: r = -(-n // c)
        fig.clear(); subs = np.atleast_1d(fig.subfigures(r, c, squeeze=False)).ravel()
        for i, sf in enumerate(subs[:n]):
            e = dict(extra)
            if "raw" in e: e["raw"] = [extra["raw"][i]]
            try: fn(sf, x, [ys[i]], [names[i]], xname, e)
            except Exception as ex:  # a plot type that needs more columns: say so in that panel only
                sf.clear(); sf.text(0.5, 0.5, f"{names[i]}:\n{ex}", ha="center", va="center", color="firebrick", fontsize=8, wrap=True)

    def _render_main(self, fig):
        st = full_style(self.spec["style"])
        if self.spec.get("source") == "matrix":
            try: ms = self.main.matrix_ref(self.spec["book"], self.spec.get("sheet"))
            except StopIteration:
                fig.clear(); fig.text(0.5, 0.5, f"The matrix for this graph is gone: {self.spec['book']}", ha="center", color="0.4"); return
            with matplotlib.rc_context(rc_for(st)):
                fig.set_facecolor(st["background"])
                P.MATRIX_PLOT_TYPES[self.spec["type"]](fig, ms.M, ms.extent, ms.label, self.spec.get("extra", {}))
                apply_post(fig, st)
            return
        try: sh = self.main.sheet_ref(self.spec["book"], self.spec.get("sheet"))
        except StopIteration: sh = None
        x_ok = sh is not None and (not self.spec.get("x") or self.spec["x"] in sh.df.columns)
        if sh is None or not x_ok or not self.cols(sh):
            fig.clear(); fig.text(0.5, 0.5, f"The data for this graph is gone:\n{self.spec['book']} / {self.spec.get('sheet')} / "
                                  f"{', '.join(map(str, self.spec['ys']))}", ha="center", va="center", color="0.4"); return
        sh, x, ys = self.data()
        with matplotlib.rc_context(rc_for(st)):
            fig.set_facecolor(st["background"])
            fn = P.PLOT_TYPES[self.spec["type"]][0]
            names = [sh.label(c) for c in self.cols(sh)]
            extra = dict(self.spec.get("extra", {}))
            if self.spec["type"] in P3.FRAME_TYPES: extra["frame"] = sh.df; extra["rows"] = self.rows  # group / label / size columns
            lab = next((c for c in sh.df.columns if sh.desig.get(c) == "Label"), None)
            if self.spec["type"] == "Piper Diagram" and lab is not None: extra["labels"] = list(sh.df[lab].to_numpy()[self.rows])
            if self.spec["type"] in plots4.GROUPABLE:  # colour and symbol per group (Graph > Group Samples By)
                gc = extra.get("group", "auto"); gc = plots4.group_column(sh.df) if gc == "auto" else gc
                if gc and gc in sh.df.columns: extra["groups"] = sh.df[gc].to_numpy(object)[self.rows]
            if self.spec["type"].startswith("Spider:"): extra["raw"] = [sh.df[c].to_numpy(object)[self.rows] for c in self.cols(sh)]  # '<DL' text
            self._plot(fn, fig, x, ys, names, sh.label(self.spec.get("x")), extra)
            for f in self.fits:
                ax = fig.axes[0]
                if f.get("band"):
                    ax.fill_between(f["x"], f["y"], f["y2"], color=f.get("color", "red"), alpha=0.15, lw=0, label=f["label"])
                else: ax.plot(f["x"], f["y"], f.get("style", "r-"), lw=1.5, label=f["label"])
            if self.fits and fig.axes: fig.axes[0].legend()
            if self.spec["type"] in POINT_TYPES and fig.axes and self.spec.get("x"):  # masked points: red crosses
                xr = sh.arr(self.spec["x"], raw=True)
                for c in self.cols(sh):
                    rows = sh.masked_rows(c)
                    if rows: fig.axes[0].plot(xr[rows], sh.arr(c, raw=True)[rows], "x", color="red", ms=7, mew=1.5, label="_masked")
            self.draw_annotations(fig, sh, x, ys)
            apply_post(fig, st)
            self._error_bars(fig, sh, x)  # after the style: bars take the curve's final colour from the format bar

    def draw_annotations(self, fig, sh, x, ys):
        """Reference lines, text, arrows, confidence ellipses and extra data series from any sheet."""
        if not fig.axes or not self.spec.get("annotations"): return
        ax = fig.axes[0]; rect = ax.name == "rectilinear"
        for ai, a in enumerate(self.spec["annotations"]):
            k = a.get("kind")
            try:
                if k == "hline": ax.axhline(float(a["y"]), color=a.get("color", "0.3"), ls=a.get("ls", "--"), lw=1, label=a.get("label") or "_ref")
                elif k == "vline": ax.axvline(float(a["x"]), color=a.get("color", "0.3"), ls=a.get("ls", "--"), lw=1, label=a.get("label") or "_ref")
                elif k == "text": ax.annotate(a["text"], (float(a["x"]), float(a["y"])), fontsize=a.get("size", 10), color=a.get("color", "k"),
                                              gid=f"pbann:{ai}")
                elif k == "arrow":
                    ax.annotate(a.get("text", "") or " ", xy=(float(a["x2"]), float(a["y2"])), xytext=(float(a["x1"]), float(a["y1"])),
                                arrowprops=dict(arrowstyle="->", color=a.get("color", "k"), lw=1.2), fontsize=9, gid=f"pbann:{ai}")
                elif k == "ellipse" and rect:
                    from .analysis4 import confidence_ellipse
                    for c, y in zip(self.cols(sh), ys):
                        ex, ey = confidence_ellipse(np.asarray(x, float), y, float(a.get("level", 0.95)))
                        ax.plot(ex, ey, "-", lw=1, label=f"{float(a.get('level', 0.95)):.0%} ellipse {c}")
                elif k in ("line", "arrow2", "rect", "circle", "polygon", "region"):
                    from . import shapes
                    for axx in [b for b in fig.axes if b.name == "rectilinear"][:1]: shapes.draw(axx, a, ai)
                elif k == "series":
                    s2 = self.main.sheet_ref(a["book"], a.get("sheet"))
                    xs = s2.arr(a["x"]) if a.get("x") else np.arange(1.0, len(s2.df) + 1)
                    ax.plot(xs, s2.arr(a["y"]), a.get("style", "-"), label=a.get("label") or f"{a['book']}/{a['y']}")
            except (KeyError, ValueError, StopIteration) as e:
                ax.text(0.02, 0.02, f"annotation skipped: {e}", transform=ax.transAxes, fontsize=7, color="firebrick")
        if any(a.get("kind") in ("series", "ellipse") or a.get("label") for a in self.spec["annotations"]): ax.legend()

    def draw(self):
        if hasattr(self, "host"): self.host.relayout()
        self.render(self.fig)
        for L in (self.main.windows() if hasattr(self.main, "windows") else []):
            if L.kind == "layout" and self.name in L.spec.get("graphs", []): L.draw()
        arts, names = [], []
        multi = sum(1 for a in self.fig.axes if _data_artists(a)) > 1
        for k, a in enumerate(self.fig.axes):  # in multi-panel graphs each curve says which panel it is in
            for art in _data_artists(a):
                arts.append(art); names.append(f"[{a.get_ylabel() or f'panel {k + 1}'}] {art.get_label()}" if multi else str(art.get_label()))
        self.series_lines, self.series_names = arts, names
        self._refresh_curves()
        if hasattr(self, "fmt"): self.fmt.refresh()
        self._make_draggable()
        self.span = None
        if self.act_region.isChecked() and self.fig.axes and self.fig.axes[0].name == "rectilinear" and self.spec.get("source") != "matrix":
            from matplotlib.widgets import SpanSelector
            self.span = SpanSelector(self.fig.axes[0], lambda lo, hi: hi > lo and self.main.gadget_menu(self, lo, hi), "horizontal",
                                     useblit=True, interactive=False, props=dict(alpha=0.2, facecolor="tab:blue"))
        self.canvas.draw_idle()

    ERRBAR_TYPES = ("Scatter", "Line", "Line + Symbol", "Step", "Semi-log Y (Line + Symbol)")

    def _error_bars(self, fig, sh, x):
        """Vertical error bars for Y columns that have a yErr column bound to them (spec['yerr'] = {Y: yErr})."""
        emap = self.spec.get("yerr") or {}
        if not emap or self.spec["type"] not in self.ERRBAR_TYPES or not fig.axes: return
        ax = fig.axes[0]; lines = _data_lines(ax)
        try: xv = np.asarray(x, float)
        except (TypeError, ValueError): return
        def col(name): return np.abs(sh.arr(name)[self.rows]) if name and name in sh.df.columns else None
        for ln, c in zip(lines, self.cols(sh)):
            e = emap.get(str(c))
            if e is None: continue
            if isinstance(e, str): e = {"y": e}
            yv, up, dn, xe = col(e.get("y")), col(e.get("+")), col(e.get("-")), col(e.get("x"))
            if up is not None or dn is not None:  # asymmetric: yErr- below, yErr+ above; a side not given uses yErr, else 0
                z = yv if yv is not None else np.zeros(len(self.rows)); yv = np.vstack([dn if dn is not None else z, up if up is not None else z])
            if yv is None and xe is None: continue
            ax.errorbar(xv, sh.arr(c)[self.rows], yerr=yv, xerr=xe, fmt="none", ecolor=ln.get_color(),
                        elinewidth=0.9, capsize=2.5, label="_err", zorder=ln.get_zorder() - 0.1)

    # ---- drag legends and text/arrow annotations with the mouse; the new place is saved in the graph (and can be undone)
    def _make_draggable(self):
        self._drags = []
        axes = [a for a in self.fig.axes if a.get_label() != "<colorbar>" and not hasattr(a, "_colorbar")]
        for i, a in enumerate(axes):
            leg = a.get_legend()
            if leg is not None: leg.set_draggable(True); self._drags.append(("legend", i, leg, a))
            for t in a.texts:
                gid = str(t.get_gid() or "")
                if gid.startswith("pbann:"): t.draggable(True); self._drags.append(("ann", int(gid[6:]), t, a))

    def _nearest_point(self, ev, tol=10):
        """(curve index, point index) of the data point under the mouse, within tol pixels; None if there is none."""
        best = None
        for i, art in enumerate(self.series_lines):
            try:
                kind = type(art).__name__
                if kind == "Line2D":
                    if art.get_marker() in (None, "", "None", "none") and art.get_linestyle() in ("None", "none", ""): continue
                    xy = np.column_stack([np.asarray(art.get_xdata(), float), np.asarray(art.get_ydata(), float)]); px = art.axes.transData.transform(xy)
                elif kind == "PathCollection": px = art.get_offset_transform().transform(np.asarray(art.get_offsets(), float))
                else: continue
            except (TypeError, ValueError): continue
            d = np.hypot(px[:, 0] - ev.x, px[:, 1] - ev.y)
            if not len(d) or np.all(np.isnan(d)): continue
            j = int(np.nanargmin(d))
            if d[j] <= tol and (best is None or d[j] < best[0]): best = (d[j], i, j)
        return None if best is None else best[1:]

    def _set_text(self, key, **kw):
        """Change one plot text's override (one undo step). reset=True forgets it; reset_all / show_all act on every text."""
        st = dict(self.spec["style"]); tx = {k: dict(v) for k, v in st.get("texts", {}).items()}
        if kw.pop("reset_all", False): tx = {}
        elif kw.pop("show_all", False):
            for v in tx.values(): v.pop("hide", None)
        elif kw.pop("reset", False): tx.pop(key, None)
        else: tx.setdefault(key, {}).update(kw)
        st["texts"] = {k: v for k, v in tx.items() if v}; self.set_style(st); self.main.mark_dirty()

    def _text_menu(self, key, t):
        from PySide6.QtWidgets import QMenu, QColorDialog, QInputDialog
        from PySide6.QtGui import QCursor, QColor
        m = QMenu(self); m.addSection(f"Text: {t.get_text()[:30]}")

        def edit():
            s, ok = QInputDialog.getMultiLineText(self, "Edit text", "Text:", t.get_text())
            if ok: self._set_text(key, text=s)

        def size():
            v, ok = QInputDialog.getDouble(self, "Font size", "Size (pt):", float(t.get_fontsize()), 3, 72, 1)
            if ok: self._set_text(key, size=v)

        def colour():
            c = QColorDialog.getColor(QColor(matplotlib.colors.to_hex(t.get_color())), self, "Text colour")
            if c.isValid(): self._set_text(key, color=c.name())
        m.addAction("Edit text...", edit); m.addAction("Font size...", size); m.addAction("Colour...", colour); m.addSeparator()
        m.addAction("Bring to front (over the data points)", lambda: self._set_text(key, z="front"))
        m.addAction("Between: over lines and fields, under the points", lambda: self._set_text(key, z="middle"))
        m.addAction("Send to back (under lines and fields)", lambda: self._set_text(key, z="back")); m.addSeparator()
        m.addAction("Hide this text", lambda: self._set_text(key, hide=True))
        m.addAction("Reset this text (position and style)", lambda: self._set_text(key, reset=True)).setEnabled(key in self.spec["style"].get("texts", {}))
        m.addAction("Reset all texts", lambda: self._set_text(key, reset_all=True)).setEnabled(bool(self.spec["style"].get("texts")))
        m.addSeparator(); m.addAction("Tip: drag a text with the mouse to move it").setEnabled(False)
        m.exec(QCursor.pos())

    def start_draw(self, kind):
        """Draw a line, arrow, rectangle, circle, polygon or freehand region on the graph with the mouse."""
        from .shapes import DrawTool
        if getattr(self, "_drawing", None): self._drawing.stop()
        if self.nav.mode: getattr(self.nav, "zoom" if "zoom" in str(self.nav.mode).lower() else "pan")()  # leave zoom / pan mode
        DrawTool(self, kind, getattr(self.main, "shape_props", None))

    def _shape_at(self, ev):
        """(index, annotation) of a drawn object under the mouse, or None."""
        from . import shapes
        for ax in self.fig.axes:
            for art in list(ax.patches) + list(ax.lines):
                gid = str(art.get_gid() or "")
                if not gid.startswith("pbann:") or gid == "pbann:-1": continue
                try: hit = art.contains(ev)[0]
                except Exception: hit = False
                i = int(gid[6:]); anns = self.spec.get("annotations", [])
                if hit and i < len(anns) and anns[i].get("kind") in shapes.KINDS: return i, anns[i]
        return None

    def edit_shape(self, i):
        from . import shapes
        a = self.spec["annotations"][i]
        d = shapes.ShapeDialog(self, a, arrow=a["kind"] == "arrow2", closed=a["kind"] in ("rect", "circle", "polygon", "region"), index=i)
        if not d.exec(): return
        self.spec["annotations"][i] = d._orig if hasattr(d, "_orig") else a; self.snapshot()  # undo returns to the object before editing
        if d.deleted: self.spec["annotations"].pop(i)
        else: self.spec["annotations"][i] = d.value(); self.main.shape_props = {k: v for k, v in d.value().items() if k not in ("kind", "points")}
        self.draw(); self.main.mark_dirty()

    def _point_menu(self, ev):
        """Right-click a plot text (move, layer, style, hide), a data point (format that point, layer of its curve), or empty space
        (show hidden texts)."""
        if ev.button != 3 or self.act_region.isChecked() or self.act_reader.isChecked() or getattr(self, "_drawing", None): return
        sh = self._shape_at(ev)
        if sh is not None: return self.edit_shape(sh[0])
        th = self._text_at(ev)
        if th is not None: return self._text_menu(*th)
        hit = self._nearest_point(ev)
        if hit is None:
            tx = self.spec["style"].get("texts", {})
            if tx:
                from PySide6.QtWidgets import QMenu
                from PySide6.QtGui import QCursor
                m = QMenu(self); hidden = sum(1 for v in tx.values() if v.get("hide"))
                m.addAction(f"Show hidden texts ({hidden})", lambda: self._set_text(None, show_all=True)).setEnabled(hidden > 0)
                m.addAction("Reset all moved and styled texts", lambda: self._set_text(None, reset_all=True)); m.exec(QCursor.pos())
            return
        from PySide6.QtWidgets import QMenu, QColorDialog, QInputDialog
        from PySide6.QtGui import QCursor, QColor
        i, j = hit; key = f"{i}:{j}"; pts = self.spec["style"].get("points", {})

        def setp(**kw):
            st = dict(self.spec["style"]); p = {k: dict(v) for k, v in st.get("points", {}).items()}
            if kw.get("reset"): p.pop(key, None)
            elif kw.get("reset_all"): p = {}
            else: p.setdefault(key, {}).update(kw)
            st["points"] = p; self.set_style(st); self.main.mark_dirty()

        def colour():
            c = QColorDialog.getColor(QColor(pts.get(key, {}).get("color", "#d62728")), self, "Point colour")
            if c.isValid(): setp(color=c.name())

        def size():
            v, ok = QInputDialog.getDouble(self, "Point size", "Symbol size (pt):", float(pts.get(key, {}).get("ms", 10)), 1, 60, 1)
            if ok: setp(ms=v)
        m = QMenu(self); m.addSection(f"Point {j + 1} of {self.series_names[i]}")
        m.addAction("Colour...", colour); sm = m.addMenu("Symbol")
        for name, mk in (("Circle", "o"), ("Square", "s"), ("Diamond", "D"), ("Triangle up", "^"), ("Triangle down", "v"), ("Star", "*"),
                         ("Plus", "P"), ("Cross", "X"), ("Hexagon", "h")):
            sm.addAction(name, lambda mk=mk: setp(marker=mk))
        m.addAction("Size...", size); m.addAction("Label with its value", lambda: setp(label=True))
        m.addAction("Hide this point", lambda: setp(hide=True)); m.addSeparator()

        def layer(z):
            st = dict(self.spec["style"]); ser = {k: dict(v) for k, v in st.get("series", {}).items()}
            ser.setdefault(str(i), {})["z"] = z; st["series"] = ser; self.set_style(st)
        m.addAction("Bring this curve to front (over texts and other curves)", lambda: layer(12.0))
        m.addAction("Send this curve to back (under lines and texts)", lambda: layer(0.4)); m.addSeparator()
        m.addAction("Reset this point", lambda: setp(reset=True)).setEnabled(key in pts)
        m.addAction("Reset all points", lambda: setp(reset_all=True)).setEnabled(bool(pts))
        m.exec(QCursor.pos())

    def _double_click(self, ev):
        """Double-click to edit what is under the mouse: a text or arrow (its text), a curve (select it in the format bar),
        a title or axis title (Graph Properties, titles tab), the axes or tick labels (axes tab), the legend (titles tab)."""
        if not ev.dblclick or not self.fig.axes or getattr(self, "_drawing", None): return
        from PySide6.QtWidgets import QInputDialog
        sh = self._shape_at(ev)
        if sh is not None: return self.edit_shape(sh[0])
        for ax in self.fig.axes:
            for t in ax.texts:
                gid = str(t.get_gid() or "")
                if gid.startswith("pbann:") and t.contains(ev)[0]:
                    i = int(gid[6:]); a = self.spec["annotations"][i]
                    txt, ok = QInputDialog.getMultiLineText(self, "Edit text", "Text:", a.get("text", ""))
                    if ok: self.snapshot(); a["text"] = txt; self.draw(); self.main.mark_dirty()
                    return
        for a in self._plot_axes():  # a sample group in the legend of a geochemistry diagram
            leg = a.get_legend()
            if leg is None or "groups" not in (self.spec.get("extra") or {}) and not any(str(l.get_gid() or "").startswith("pbgroup:") for l in a.lines): continue
            for lt in leg.get_texts():
                if lt.contains(ev)[0]:
                    grp = next((str(l.get_gid())[8:] for l in a.lines if str(l.get_gid() or "").startswith("pbgroup:") and l.get_label() == lt.get_text()), None)
                    if grp is not None:
                        from .plotedit import GroupStyleDialog
                        GroupStyleDialog(self, grp).exec(); return
        for i, art in enumerate(self.series_lines):
            try: hit = art.contains(ev)[0]
            except Exception: hit = False
            if hit:
                j = self.fmt.series.findData(str(i))
                if j >= 0: self.fmt.series.setCurrentIndex(j)
                self.main.statusBar().showMessage(f"Selected curve {i + 1}: {self.series_names[i]} (format bar)", 5000); return
        ax = self.fig.axes[0]; tab = None
        if any(t.contains(ev)[0] for t in (ax.title, ax.xaxis.label, ax.yaxis.label)) or (ax.get_legend() is not None and ax.get_legend().contains(ev)[0]): tab = 0
        elif ev.inaxes is None or any(t.contains(ev)[0] for t in ax.get_xticklabels() + ax.get_yticklabels()): tab = 1
        if tab is not None: StyleDialog(self.main, self.spec["style"] or {}, graph=self, tab=tab).exec()

    def _drag_pos(self, kind, art, ax):
        if kind == "legend":
            bb = art.get_window_extent(); return tuple(map(float, ax.transAxes.inverted().transform((bb.x0, bb.y0))))
        return tuple(map(float, art.xyann))

    def _plot_axes(self):
        return [a for a in self.fig.axes if a.get_label() != "<colorbar>" and not hasattr(a, "_colorbar")]

    def _text_at(self, ev):
        """(key, text) of the plot text under the mouse, or None."""
        for ai, a in enumerate(self._plot_axes()):
            for key, t in _text_keys(a, ai):
                try:
                    if t.get_visible() and t.contains(ev)[0]: return key, t
                except Exception: pass
        return None

    def _text_drag_move(self, ev):
        if self._tdrag is None or ev.x is None: return
        key, t, off, before, start = self._tdrag
        t.set_position(tuple(t.get_transform().inverted().transform((ev.x + off[0], ev.y + off[1]))))
        self.canvas.draw_idle()

    def _drag_press(self, ev):
        import copy
        self._tdrag = None
        if getattr(self, "_drawing", None): self._pre = None; return
        if ev is not None and ev.button == 1 and not self.nav.mode and not self.act_region.isChecked() and not self.act_reader.isChecked() and not ev.dblclick:
            hit = self._text_at(ev)
            if hit is not None:  # drag a field name or other plot text; the drop is saved with the graph
                key, t = hit; p = t.get_transform().transform(t.get_position())
                self._tdrag = (key, t, (p[0] - ev.x, p[1] - ev.y), copy.deepcopy((self.spec, self.fits)), tuple(t.get_position()))
                self._pre = None; return
        if not self._drags: self._pre = None; return
        self._pre = (copy.deepcopy((self.spec, self.fits)), [self._drag_pos(k, art, ax) for k, _, art, ax in self._drags])

    def _drag_release(self, ev):
        if self._tdrag is not None:
            key, t, off, before, start = self._tdrag; self._tdrag = None; pos = tuple(map(float, t.get_position()))
            if max(abs(pos[0] - start[0]), abs(pos[1] - start[1])) > 1e-12 * (1 + abs(start[0]) + abs(start[1])):
                self.history.append(before); del self.history[:-30]; self.redo_stack = []
                self.spec.setdefault("style", {}).setdefault("texts", {}).setdefault(key, {})["pos"] = list(pos)
                if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()
            return
        if self._pre is None: return
        before, starts = self._pre; self._pre = None; moved = False; st = self.spec.setdefault("style", {})
        for (kind, i, art, ax), p0 in zip(self._drags, starts):
            p = self._drag_pos(kind, art, ax)
            if max(abs(p[0] - p0[0]), abs(p[1] - p0[1])) < 1e-9 * (1 + abs(p0[0]) + abs(p0[1])): continue
            if kind == "legend": st.setdefault("legend_pos", {})[str(i)] = list(p); moved = True
            elif i < len(self.spec.get("annotations", [])):
                a = self.spec["annotations"][i]
                if a.get("kind") == "arrow":  # move head and tail together
                    dx, dy = p[0] - p0[0], p[1] - p0[1]
                    for kx, ky in (("x1", "y1"), ("x2", "y2")): a[kx], a[ky] = float(a[kx]) + dx, float(a[ky]) + dy
                else: a["x"], a["y"] = p
                moved = True
        if moved:
            self.history.append(before); del self.history[:-30]; self.redo_stack = []
            if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def _click(self, ev):
        if not self.act_reader.isChecked() or ev.inaxes is None or ev.xdata is None: return
        if self.spec.get("source") == "matrix":  # read the cell under the cursor
            ms = self.main.matrix_ref(self.spec["book"], self.spec.get("sheet")); xs, ys = MX.axes_of(ms.M, ms.extent)
            j, i = int(np.argmin(np.abs(xs - ev.xdata))), int(np.argmin(np.abs(ys - ev.ydata)))
            return self.main.statusBar().showMessage(f"{ms.name}: row {i + 1}, column {j + 1}, X = {xs[j]:.6g}, Y = {ys[i]:.6g}, "
                                                     f"Z = {ms.M[i, j]:.6g}", 15000)
        sh, x, ys = self.data(); ax = ev.inaxes
        try: xv = np.asarray(x, float)
        except (TypeError, ValueError): return
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim(); best = None
        for c, y in zip(self.cols(sh), ys):  # nearest point in screen-normalised distance
            d = ((xv - ev.xdata) / (x1 - x0)) ** 2 + ((y - ev.ydata) / (y1 - y0)) ** 2
            if np.all(np.isnan(d)): continue
            i = int(np.nanargmin(d))
            if best is None or d[i] < best[0]: best = (d[i], c, xv[i], y[i], int(self.rows[i]))
        if best is None: return
        _, c, px, py, row = best
        for t in [t for t in ax.texts if t.get_gid() == "reader"]: t.remove()
        for l in [l for l in ax.lines if l.get_gid() == "reader"]: l.remove()
        ax.plot([px], [py], "s", ms=10, mfc="none", mec="magenta", mew=1.5, gid="reader")
        ax.annotate(f"{c}  row {row + 1}\nX = {px:.6g}\nY = {py:.6g}", (px, py), xytext=(12, 12), textcoords="offset points",
                    fontsize=9, bbox=dict(boxstyle="round", fc="lightyellow", ec="0.5"), gid="reader")
        self.main.statusBar().showMessage(f"{c}: row {row + 1}, X = {px:.8g}, Y = {py:.8g}", 15000); self.canvas.draw_idle()

    def snapshot(self):
        """Remember the whole graph (spec, fit curves, bands, annotations, insets) for Undo."""
        import copy
        self.history.append(copy.deepcopy((self.spec, self.fits))); del self.history[:-30]; self.redo_stack = []

    def add_curve(self, x, y, label, style="r-"):
        self.snapshot(); self.fits.append({"x": list(map(float, x)), "y": list(map(float, y)), "label": label, "style": style}); self.draw()

    def add_band(self, x, lo, hi, label, color="red"):
        self.snapshot(); self.fits.append({"band": True, "x": list(map(float, x)), "y": list(map(float, lo)), "y2": list(map(float, hi)),
                          "label": label, "color": color}); self.draw()

    def set_style(self, style):
        self.snapshot(); self.spec["style"] = style; self.draw()

    def _swap(self, src, dst):
        import copy
        if not src: return
        dst.append(copy.deepcopy((self.spec, self.fits))); self.spec, self.fits = src.pop(); self.draw()
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def undo(self): self._swap(self.history, self.redo_stack)
    def redo(self): self._swap(self.redo_stack, self.history)

    def export_defaults(self):
        st = full_style(self.spec["style"]); return {"dpi": st["dpi"], "width_in": st["width_in"], "height_in": st["height_in"]}

    def export(self, fn, dpi=None, width_in=None, height_in=None, transparent=False, editable_text=True):
        """Save the graph; dpi/size default to the graph's own export settings (Graph Properties)."""
        d = self.export_defaults()
        fig = Figure(figsize=(width_in or d["width_in"], height_in or d["height_in"]), layout="constrained")
        self.render(fig); _save(fig, fn, dpi or d["dpi"], transparent, editable_text)

    def state(self): return {"kind": "graph", "name": self.name, "spec": self.spec, "fits": self.fits}


# ---------------------------------------------------------------- customization dialog
class StyleDialog(QDialog):
    def __init__(self, parent, style, graph=None, tab=0):
        super().__init__(parent); self.setWindowTitle("Graph properties"); self.resize(540, 560)
        st = {**DEFAULT_STYLE, **style}; self.w = {}
        tabs = QTabWidget()

        def page(rows):
            p = QWidget(); f = QFormLayout(p)
            for key, label, widget in rows: f.addRow(label, widget); self.w[key] = widget
            tabs.addTab(p, ""); return p

        def le(k):
            e = QLineEdit(str(st[k]))
            if k in ("xmin", "xmax", "ymin", "ymax"): e.setPlaceholderText("auto"); e.setToolTip("A number such as 0.5, 1e-18, 10^-18 or 2.5x10^3; blank = automatic")
            if k in ("xbreak", "ybreak"): e.setPlaceholderText("none, e.g. 20, 80"); e.setToolTip("Leave out the range between these two values; the axis is drawn in two parts with // marks")
            return e
        def cb(k, items): c = QComboBox(); c.addItems(items); c.setCurrentText(str(st[k])); return c
        def ds(k, lo, hi, step=0.5): s = QDoubleSpinBox(); s.setRange(lo, hi); s.setSingleStep(step); s.setValue(float(st[k])); return s
        def ck(k): c = QCheckBox(); c.setChecked(bool(st[k])); return c

        page([("title", "Title", le("title")), ("xlabel", "X axis title (blank = auto)", le("xlabel")),
              ("ylabel", "Y axis title (blank = auto)", le("ylabel")), ("legend", "Legend", cb("legend", LEGEND)),
              ("legend_frame", "Legend frame", ck("legend_frame"))])
        page([("xscale", "X scale", cb("xscale", ["linear", "log", "symlog", "logit"])), ("xmin", "X from (blank = auto)", le("xmin")),
              ("xmax", "X to", le("xmax")), ("yscale", "Y scale", cb("yscale", ["linear", "log", "symlog", "logit"])),
              ("ymin", "Y from (blank = auto)", le("ymin")), ("ymax", "Y to", le("ymax")), ("ticks_in", "Ticks point inward", ck("ticks_in")),
              ("mirror_ticks", "Ticks on all four sides", ck("mirror_ticks")), ("minor_ticks", "Minor ticks", ck("minor_ticks")),
              ("grid", "Grid lines", ck("grid")), ("xbreak", "X axis break (from, to)", le("xbreak")), ("ybreak", "Y axis break (from, to)", le("ybreak"))])
        page([("palette", "Colour palette", cb("palette", list(PALETTES))), ("cmap", "Colour map (contour, heat map, 3D)", cb("cmap", CMAPS)),
              ("line_width", "Line width", ds("line_width", 0.1, 10, 0.25)), ("linestyle", "Line style", cb("linestyle", list(LINESTYLES))),
              ("marker", "Symbol", cb("marker", list(MARKERS))), ("marker_size", "Symbol size", ds("marker_size", 0.5, 30)),
              ("background", "Background colour", le("background"))])
        page([("font", "Font", cb("font", FONTS)), ("font_size", "Font size (pt)", ds("font_size", 4, 48)),
              ("view_aspect", "Shape on screen (width:height)", cb("view_aspect", list(VIEW_ASPECTS))),
              ("width_in", "Export width (in)", ds("width_in", 1, 30, 0.25)), ("height_in", "Export height (in)", ds("height_in", 1, 30, 0.25)),
              ("dpi", "Export DPI", ds("dpi", 72, 2400, 50))])
        for i, t in enumerate(("Titles && legend", "Axes", "Lines && colours", "Fonts && size")): tabs.setTabText(i, t)
        tabs.setCurrentIndex(tab); self.tabs = tabs
        self.font_box = self.w["font"]; self.font_box.setEditable(True)
        lay = QVBoxLayout(self); self.live = None
        if graph is None: lay.addWidget(tabs)
        if graph is not None:  # every change shows on the graph at once; Apply/OK keep it, Cancel puts it back
            from .live import graph_live, add_pane
            def mutate(g):
                new = {**g.spec["style"], **self.value()}
                if new.get("legend") != g.spec["style"].get("legend", DEFAULT_STYLE["legend"]): new.pop("legend_pos", None)
                g.spec["style"] = new
            self.live = graph_live(self, graph, mutate)
            row = QHBoxLayout(); row.addWidget(tabs, 1); row.addWidget(add_pane(self.live, graph), 1); lay.addLayout(row)
            lay.addWidget(self.live.bar()); self.live.start(); self.resize(1080, 600)
        else:
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
            lay.addWidget(bb)

    def value(self):
        out = {}
        for k, w in self.w.items():
            if isinstance(w, QComboBox): out[k] = w.currentText()
            elif isinstance(w, QDoubleSpinBox): out[k] = w.value()
            elif isinstance(w, QCheckBox): out[k] = w.isChecked()
            else: out[k] = w.text()
        out["dpi"] = int(out["dpi"]); return out


def save_template(parent, style):
    n, ok = QInputDialog.getText(parent, "Save graph template", "Template name:")
    if ok and n.strip():
        (user_dir() / "templates" / f"{n.strip()}.json").write_text(json.dumps(style, indent=1))


def template_names():
    return list(THEMES) + [p.stem for p in sorted((user_dir() / "templates").glob("*.json"))]


def load_template(n):
    if n in THEMES: return dict(THEMES[n])
    return json.loads((user_dir() / "templates" / f"{n}.json").read_text())


def choose_template(parent):
    n, ok = QInputDialog.getItem(parent, "Apply template / theme", "Template:", template_names(), 0, False)
    return load_template(n) if ok else None


def set_default_theme(parent):
    t = choose_template(parent)
    if t is not None:
        (user_dir() / "default_style.json").write_text(json.dumps(t, indent=1)); return True


# ---------------------------------------------------------------- layouts
class LayoutWindow(QWidget):
    """A page that arranges several graphs in a rows x columns grid, with panel labels (a), (b)..."""
    kind = "layout"

    def __init__(self, main, name, spec):
        super().__init__(); self.main = main; self.setWindowTitle(name); self.spec = spec
        self.fig = Figure(figsize=(spec.get("width_in", 10), spec.get("height_in", 7)))
        self.canvas = FigureCanvasQTAgg(self.fig)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(NavigationToolbar2QT(self.canvas, self)); lay.addWidget(self.canvas)
        self._panels = []; self.canvas.mpl_connect("button_press_event", self._open_panel)
        self.setToolTip("Double-click a panel to edit that graph; the page follows its changes")

    @property
    def name(self): return self.windowTitle()

    def _open_panel(self, ev):
        """Double-click a panel: bring its graph window forward to edit it (curves, points, Edit plot ...)."""
        if not ev.dblclick: return
        for sub, gname in self._panels:
            if sub.bbox.contains(ev.x, ev.y):
                g = next((w for w in self.main.windows() if w.kind == "graph" and w.name == gname), None)
                if g is not None:
                    sw = g.parentWidget(); sw.showNormal(); self.main.mdi.setActiveSubWindow(sw)
                    self.main.statusBar().showMessage(f"Editing {gname}: changes show on the layout page too", 6000)
                return

    def render(self, fig):
        fig.clear(); s = self.spec; area = fig; self._panels = []
        if s.get("title"):  # reserve a strip for the page title so it never overlaps panels
            top, area = fig.subfigures(2, 1, height_ratios=[1, 14]); top.suptitle(s["title"], fontsize=14, y=0.5, va="center")
        subs = np.atleast_1d(area.subfigures(s["rows"], s["cols"], wspace=0.02, hspace=0.02)).ravel()
        graphs = {g.name: g for g in self.main.windows() if g.kind == "graph"}
        for k, (sub, gname) in enumerate(zip(subs, s["graphs"])):
            g = graphs.get(gname)
            if g is None: continue
            g.render(sub); self._panels.append((sub, gname))
            if s.get("labels", True):
                sub.text(0.01, 0.99, f"({chr(97 + k)})", ha="left", va="top", fontsize=12, fontweight="bold")

    def draw(self): self.render(self.fig); self.canvas.draw_idle()

    def export_defaults(self):
        return {"dpi": self.spec.get("dpi", 600), "width_in": self.spec.get("width_in", 10), "height_in": self.spec.get("height_in", 7)}

    def export(self, fn, dpi=None, width_in=None, height_in=None, transparent=False, editable_text=True):
        d = self.export_defaults(); fig = Figure(figsize=(width_in or d["width_in"], height_in or d["height_in"]))
        self.render(fig); _save(fig, fn, dpi or d["dpi"], transparent, editable_text)

    def state(self): return {"kind": "layout", "name": self.name, "spec": self.spec}


class LayoutDialog(QDialog):
    def __init__(self, parent, graph_names, spec=None):
        super().__init__(parent); self.setWindowTitle("Layout page"); spec = spec or {}
        self.list = QListWidget(); self.list.addItems(graph_names); self.list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        for i in range(self.list.count()):
            if self.list.item(i).text() in spec.get("graphs", []): self.list.item(i).setSelected(True)
        self.rows, self.cols = QSpinBox(), QSpinBox()
        for s, v in ((self.rows, spec.get("rows", 0)), (self.cols, spec.get("cols", 0))): s.setRange(0, 10); s.setValue(v)
        self.title = QLineEdit(spec.get("title", "")); self.labels = QCheckBox(); self.labels.setChecked(spec.get("labels", True))
        self.wd, self.ht = QDoubleSpinBox(), QDoubleSpinBox()
        for s, v in ((self.wd, spec.get("width_in", 10)), (self.ht, spec.get("height_in", 7))): s.setRange(1, 40); s.setValue(v)
        f = QFormLayout(self); f.addRow("Graphs (select; drag to reorder)", self.list)
        f.addRow("Rows (0 = auto)", self.rows); f.addRow("Columns (0 = auto)", self.cols); f.addRow("Page title", self.title)
        f.addRow("Panel labels (a), (b)...", self.labels); f.addRow("Page width (in)", self.wd); f.addRow("Page height (in)", self.ht)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        f.addRow(bb)

    def value(self):
        sel = [self.list.item(i).text() for i in range(self.list.count()) if self.list.item(i).isSelected()]
        n = max(1, len(sel)); c = self.cols.value() or int(np.ceil(np.sqrt(n))); r = self.rows.value() or int(np.ceil(n / c))
        return {"graphs": sel, "rows": r, "cols": c, "title": self.title.text(), "labels": self.labels.isChecked(),
                "width_in": self.wd.value(), "height_in": self.ht.value()}
