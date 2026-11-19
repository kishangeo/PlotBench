"""Plot Gallery: plot types grouped into categories with preview thumbnails (like Origin's Plot menu).
Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QPushButton, QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QListView, QLabel, QLineEdit,
                               QDialogButtonBox)

from . import plots as P
from . import plots2  # noqa: F401
from . import plots3  # noqa: F401
from . import plots4  # noqa: F401
from . import plots5
from . import plothelp as PH

CATEGORIES = [
    ("Basic 2D", ["Line", "Scatter", "Line + Symbol", "Step", "Step (post, survival)", "Drop Line (Stem)", "Area", "Stacked Area",
                  "Error Bar", "Semi-log Y (Line + Symbol)"]),
    ("Color-mapped (3 variables)", ["Color-mapped Scatter", "Bubble + Color", "Color-mapped Line", "Bubble", "Ternary + Color",
                                    "Heat Map", "Contour (XYZ)", "2D Kernel Density", "Ternary Contour", "Ternary Density (KDE contours)"]),
    ("Columns, Bars and Pie", ["Column", "Bar (horizontal)", "Stacked Column", "Column + Error Bars", "Pareto Chart", "Pie"]),
    ("Multi-Panel and Multi-Axis", ["Double-Y", "Stacked Panels (shared X)", "Waterfall (offset curves)", "Scatter Matrix",
                                    "Scatter + Marginal Histograms"]),
    ("Statistical", ["Histogram", "Histogram + Normal Curve", "Box", "Box + Data Points", "Violin", "Raincloud (violin + box + points)", "Q-Q Plot", "Normal Probability",
                     "Cumulative Probability", "Bland-Altman", "Dendrogram (cluster rows)"]),
    ("Specialized and Geoscience", ["Ternary", "Piper Diagram", "Polar (theta deg, r)", "Radar / Spider", "Wind Rose", "Sankey (flows)"]),
    ("Geochemistry", ["Spider: REE / CI Chondrite", "Spider: REE / Primitive Mantle", "Spider: Multi-element / Primitive Mantle",
                      "Spider: Multi-element / N-MORB", "Spider: Multi-element / CI Chondrite", "Spider: REE / PAAS (sediments)",
                      "TAS (SiO2 vs Na2O+K2O)", "QAP (Streckeisen)", "Feldspar Ternary (An-Ab-Or)", "Pyroxene Quadrilateral (Wo-En-Fs)",
                      "Ultramafic Ol-Opx-Cpx (IUGS)", "Soil Texture (USDA)", "Harker Diagrams (oxides vs SiO2)", "Shand A/CNK vs A/NK", "Frost: Fe-number vs SiO2", "Frost: MALI vs SiO2", "AFM (Irvine & Baragar)",
                      "Pearce Granite: Rb vs Y+Nb", "Pearce Granite: Nb vs Y", "Pearce Granite: Rb vs Yb+Ta", "Pearce Granite: Ta vs Yb", "Pearce 2008: Th/Yb vs Nb/Yb", "Pearce 2008: TiO2/Yb vs Nb/Yb",
                      "Ternary", "Piper Diagram"]),
    ("Geochronology", plots5.GEOCHRON),
    ("Multivariate (PCA)", plots5.GEOCHRON_PCA),
    ("3D", ["3D Scatter", "3D Surface", "3D Line (path)", "3D Bars", "3D Vectors"]),
    ("Matrix (from a matrixbook)", ["Image / Heat Map", "Filled Contour", "Contour Lines", "3D Colour-map Surface", "3D Wireframe"]),
]
MATRIX_KINDS = set(CATEGORIES[-1][1])
FAILED = {}  # thumbnails that could not be drawn (kind -> error), for tests and diagnostics
HINTS = {k: v[2] for k, v in P.PLOT_TYPES.items()}
HINTS.update({k: "Active matrixbook" for k in MATRIX_KINDS})


def min_ys(kind):
    """Fewest data columns besides X that a plot type needs, read from its data hint; None when it is not a matter of counting
    (diagrams that find their columns by name, plots that ask in a dialog)."""
    h = HINTS.get(kind, "")
    if any(w in h for w in ("wt%", "ppm", "source", "colour", "Na2O")) or not h: return None
    if h.startswith("Ca (X)"): return 5
    parts = [p for p in h.split("+") if p.strip()]; xfirst = h.startswith("X") or "(X)" in parts[0]
    return max(1, len(parts) - (1 if xfirst else 0))


def categories():
    """Category list, with any plot type not placed above added under 'Other'."""
    placed = {k for _, ks in CATEGORIES for k in ks}; rest = [k for k in P.PLOT_TYPES if k not in placed]
    cats = [(c, [k for k in ks if k in P.PLOT_TYPES or k in MATRIX_KINDS]) for c, ks in CATEGORIES]
    return cats + ([("Other", rest)] if rest else [])


def _sample(kind, r=np.random.default_rng(0)):
    """Small sample data that makes each plot type recognisable."""
    if kind.startswith("Pearce 2008"):
        yb = r.uniform(1.5, 3.5, 20); nb = yb * np.exp(r.uniform(np.log(0.5), np.log(30), 20))
        return np.arange(20), [nb * r.uniform(0.05, 0.1, 20), nb, yb, yb * r.uniform(0.3, 1.5, 20)], ["Th", "Nb", "Yb", "TiO2"], {}
    if kind.startswith("PCA"):
        b = r.normal(size=(40, 1)); X = np.hstack([b + r.normal(0, 0.3, (40, 1)) for _ in range(3)] + [r.normal(size=(40, 2))])
        return None, list(X.T), ["SiO2", "Al2O3", "Na2O", "MgO", "CaO"], {"groups": np.where(b[:, 0] > 0, "felsic", "mafic")}
    s5 = plots5.sample(kind)
    if s5 is not None: return s5
    x = np.linspace(0, 10, 25)
    y1, y2, y3 = np.sin(x / 2) * 3 + 5, np.cos(x / 2) * 2 + 4, 0.4 * x + 1
    cats = np.array(["A", "B", "C", "D", "E"]); bars = [np.array([5, 8, 3, 9, 6.]), np.array([3, 5, 6, 4, 7.])]
    if kind in ("Column", "Bar (horizontal)", "Stacked Column", "Pareto Chart", "Pie", "Radar / Spider"): return cats, bars, ["a", "b"], {}
    if kind == "Column + Error Bars": return cats, [bars[0], np.full(5, 0.8), bars[1], np.full(5, 0.6)], ["a", "e", "b", "e2"], {}
    if kind in ("Histogram", "Histogram + Normal Curve", "Box", "Box + Data Points", "Violin", "Q-Q Plot", "Normal Probability", "Cumulative Probability"):
        return None, [r.normal(0, 1, 120), r.normal(1, 0.7, 120)], ["a", "b"], {}
    if kind in ("Color-mapped Scatter", "Bubble + Color", "Bubble", "Color-mapped Line"):
        xs = np.sort(r.uniform(0, 1, 30)); ys = xs * 3 + r.normal(0, 0.3, 30); z = xs + r.normal(0, 0.2, 30)
        if kind == "Color-mapped Line": t = np.linspace(0, 6, 80); return t, [np.sin(t), t], ["y", "z"], {}
        return xs, [ys, z], ["y", "z"], ({"ms": 6.5} if kind != "Bubble + Color" else {"frame": pd.DataFrame({"s": r.uniform(1, 5, 30)}), "size": "s"})
    if kind in ("Heat Map",): return np.arange(6), [r.uniform(0, 1, 6) for _ in range(5)], list("abcde"), {}
    if kind == "3D Line (path)": t = np.linspace(0, 12, 120); return np.cos(t), [np.sin(t), t], ["y", "z"], {}
    if kind == "3D Bars": a, b = np.meshgrid(np.arange(5.0), np.arange(4.0)); return a.ravel(), [b.ravel(), (a + 1.5 * b).ravel() + 1], ["y", "z"], {}
    if kind == "3D Vectors":
        a, b, c = (v.ravel() for v in np.meshgrid(np.arange(3.0), np.arange(3.0), np.arange(3.0)))
        return a, [b, c, -b + 1, a - 1, np.full(a.size, 0.6)], ["y", "z", "u", "v", "w"], {}
    if kind in ("Contour (XYZ)", "3D Scatter", "3D Surface", "2D Kernel Density"):
        a, b = r.uniform(-2, 2, 250), r.uniform(-2, 2, 250); return a, [b, np.exp(-(a ** 2 + b ** 2) / 2)], ["y", "z"], {}
    if kind in ("Ternary", "Ternary + Color", "Ternary Contour", "Ternary Density (KDE contours)"):
        d = r.dirichlet([3, 2, 2], 40); return d[:, 0], [d[:, 1], d[:, 2], d[:, 0] * 2], ["b", "c", "z"], {}
    if kind.startswith("Spider"):
        from .geodata import REFERENCES, REE, SPIDER_ORDER
        ref = REFERENCES[plots4.SPIDERS[kind][0]]; els = [e for e in (REE if plots4.SPIDERS[kind][1] else SPIDER_ORDER) if e in ref]
        slope = np.linspace(2.2, 0.6, len(els))  # three samples, LREE-enriched
        return np.array(["s1", "s2", "s3"]), [np.array([ref[e] * 10 ** (slope[i] + 0.3 * k - 0.3) for k in range(3)]) for i, e in enumerate(els)], els, {}
    if kind == "TAS (SiO2 vs Na2O+K2O)": si = r.uniform(44, 74, 25); return si, [0.18 * (si - 40) + r.normal(0, 0.8, 25)], ["Na2O+K2O"], {}
    if kind == "QAP (Streckeisen)": d = r.dirichlet([3, 3, 3], 20) * 100; return d[:, 0], [d[:, 1], d[:, 2]], ["A", "P"], {}
    if kind == "Pyroxene Quadrilateral (Wo-En-Fs)":
        wo = np.r_[r.uniform(38, 48, 10), r.uniform(6, 14, 5), r.uniform(1, 4, 5)]; mg = r.uniform(0.45, 0.9, 20)
        return wo, [(100 - wo) * mg, (100 - wo) * (1 - mg)], ["En", "Fs"], {}
    if kind == "Ultramafic Ol-Opx-Cpx (IUGS)": d = r.dirichlet([4, 2, 1.5], 25) * 100; return d[:, 0], [d[:, 1], d[:, 2]], ["Opx", "Cpx"], {}
    if kind == "Harker Diagrams (oxides vs SiO2)":
        si = r.uniform(46, 74, 20); return si, [1.6 - 0.02 * si, 18 - 0.06 * si, 25 - 0.3 * si, 22 - 0.28 * si + r.normal(0, 0.5, 20),
                                                0.03 * si + 1.5, 0.12 * si - 4.5], ["TiO2", "Al2O3", "FeOt", "MgO", "Na2O", "K2O"], {}
    if kind.startswith("Frost:"):
        si = r.uniform(55, 76, 20)
        return None, [si, r.uniform(0.5, 6, 20), r.uniform(0.1, 3, 20), r.uniform(2.5, 4.5, 20), r.uniform(1, 5.5, 20), 12 - 0.15 * si + r.uniform(-1, 1, 20)], \
            ["SiO2", "FeOt", "MgO", "Na2O", "K2O", "CaO"], {}
    if kind == "Shand A/CNK vs A/NK":
        return None, [r.uniform(13, 17, 20), r.uniform(0.5, 9, 20), r.uniform(2.5, 4.5, 20), r.uniform(0.5, 5, 20)], ["Al2O3", "CaO", "Na2O", "K2O"], {}
    if kind == "AFM (Irvine & Baragar)":
        t = np.linspace(0, 1, 18); return None, [2 + 6 * t, 0.5 + 2 * t, 10 - 3 * t + 4 * np.sin(3 * t), 8 * (1 - t) + 0.3], ["Na2O", "K2O", "FeOt", "MgO"], {}
    if kind.startswith("Pearce Granite"):
        n = 16; rb = np.exp(r.uniform(np.log(20), np.log(600), n)); y = np.exp(r.uniform(np.log(5), np.log(150), n))
        return np.array([f"g{i}" for i in range(n)]), [rb, y, y * r.uniform(0.3, 1.5, n), y / 8, y * r.uniform(0.02, 0.15, n)], ["Rb", "Y", "Nb", "Yb", "Ta"], {}
    if kind == "Soil Texture (USDA)": d = r.dirichlet([3, 3, 1.5], 25) * 100; return d[:, 0], [d[:, 1], d[:, 2]], ["Silt", "Clay"], {}
    if kind == "Feldspar Ternary (An-Ab-Or)":
        an = r.uniform(0, 90, 15); return np.r_[100 - an, r.uniform(5, 60, 6)], [np.r_[r.uniform(0, 4, 15), r.uniform(35, 90, 6)], np.r_[an, r.uniform(0, 3, 6)]], ["Or", "An"], {}
    if kind == "Piper Diagram": return r.uniform(1, 5, 6), [r.uniform(0.5, 3, 6) for _ in range(5)], list("abcde"), {}
    if kind == "Wind Rose": return r.uniform(0, 360, 300), [r.gamma(2, 3, 300)], ["speed"], {}
    if kind == "Polar (theta deg, r)": t = np.linspace(0, 360, 60); return t, [1 + 0.5 * np.sin(np.radians(t) * 3)], ["r"], {}
    if kind == "Sankey (flows)":
        f = pd.DataFrame({"s": ["A", "A", "B", "C", "C"], "t": ["C", "D", "C", "E", "F"], "v": [5, 3, 4, 6, 3.]})
        return f["s"].to_numpy(), [f["v"].to_numpy()], ["v"], {"frame": f, "src": "s", "dst": "t", "val": "v"}
    if kind == "Error Bar": return x[::3], [y1[::3], np.full(9, 0.4)], ["y", "e"], {}
    if kind == "Bland-Altman": a = r.normal(10, 2, 40); return a, [a + r.normal(0.3, 0.5, 40)], ["b"], {}
    if kind == "Dendrogram (cluster rows)": return np.arange(12), [r.normal(size=12), r.normal(size=12)], ["a", "b"], {}
    if kind in ("Scatter", "Scatter Matrix", "Scatter + Marginal Histograms"): return r.normal(size=60), [r.normal(size=60), r.normal(size=60)], ["a", "b"], {}
    if kind == "Semi-log Y (Line + Symbol)": return np.arange(1, 11.), [np.exp(np.arange(1, 11.) / 2), np.exp(np.arange(1, 11.) / 3)], ["a", "b"], {}
    return x, [y1, y2, y3], ["a", "b", "c"], {}


def _matrix_thumb(fig, kind):
    from . import matrix as MX
    M = MX.from_formula("exp(-(x**2+y**2)/3)*cos(x)", 40, 40, [-3, 3, -3, 3])
    P.MATRIX_PLOT_TYPES[kind](fig, M, [-3, 3, -3, 3], "z", {})


def thumbnail(kind, cache_dir, size=(150, 112)):
    key = hashlib.md5(kind.encode()).hexdigest()[:10]; path = Path(cache_dir) / f"{key}.png"
    if not path.exists():
        fig = Figure(figsize=(size[0] / 50, size[1] / 50), dpi=100, layout="constrained"); FigureCanvasAgg(fig)
        try:
            with matplotlib.rc_context({"font.size": 6, "lines.markersize": 3.5, "lines.linewidth": 1.6, "axes.linewidth": 0.8,
                                        "xtick.labelsize": 0, "ytick.labelsize": 0, "xtick.major.size": 0, "ytick.major.size": 0}):
                if kind in MATRIX_KINDS: _matrix_thumb(fig, kind)
                else:
                    x, ys, names, extra = _sample(kind); P.PLOT_TYPES[kind][0](fig, x if x is not None else np.arange(len(ys[0])), ys, names, "", extra)
            for a in fig.axes:
                a.set_xlabel(""); a.set_ylabel(""); a.set_title("")
                if a.get_legend(): a.get_legend().remove()
                if hasattr(a, "set_zlabel"): a.set_zlabel("")
                a.tick_params(labelbottom=False, labelleft=False, labeltop=False, labelright=False)
                for t in list(a.texts):  # a thumbnail is ~150 px wide: keep only big labels (ternary corners), drop the rest
                    if t.get_fontsize() < 9: t.remove()
                    else: t.set_fontsize(8)
            for t in list(fig.texts): t.remove()
        except Exception as e:
            FAILED[kind] = repr(e); fig.clear(); fig.text(0.5, 0.5, kind, ha="center", va="center", fontsize=8)
        fig.savefig(path, facecolor="white")
    return QIcon(QPixmap(str(path)))


class PlotGallery(QDialog):
    """Categories on the left, thumbnails on the right; double-click (or OK) to plot the selected columns."""

    def __init__(self, parent, cache_dir, selection_hint="", n_ys=None):
        super().__init__(parent); self.setWindowTitle("Plot Gallery"); self.resize(1080, 700); self.choice = None
        self.n_ys = n_ys  # data columns that would be plotted: plot types that need more are greyed, with the reason
        Path(cache_dir).mkdir(parents=True, exist_ok=True); self.cache = cache_dir; self.cats = categories()
        self.search = QLineEdit(); self.search.setPlaceholderText("Search plot types (e.g. contour, ternary, error)")
        self.side = QListWidget(); self.side.setIconSize(QSize(40, 30)); self.side.setFixedWidth(270)
        from .tiles import make_tile_grid
        self.grid = make_tile_grid(QSize(150, 112))  # uniform tiles; highlight stays inside each tile
        from PySide6.QtWidgets import QTextBrowser
        self.hint = QTextBrowser(); self.hint.setFixedHeight(170); self.hint.setOpenLinks(False)
        self.example = QPushButton("Open example data for this plot"); self.example.clicked.connect(self._open_example)
        self.example.setToolTip("Opens a sample worksheet laid out for this plot type, then plots it")
        self.sel = QLabel(selection_hint); self.sel.setWordWrap(True); self.sel.setStyleSheet("color: gray")
        for name, kinds in self.cats:
            it = QListWidgetItem(name); it.setData(Qt.UserRole, kinds); self.side.addItem(it)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Plot")
        bb.accepted.connect(self._accept); bb.rejected.connect(self.reject)
        foot = QHBoxLayout(); foot.addWidget(self.sel, 1); foot.addWidget(self.example); foot.addWidget(bb)
        right = QVBoxLayout(); right.addWidget(self.search); right.addWidget(self.grid, 1); right.addWidget(self.hint); right.addLayout(foot)
        row = QHBoxLayout(self); row.addWidget(self.side); row.addLayout(right, 1)
        self.side.currentRowChanged.connect(self.show_category); self.search.textChanged.connect(self.filter)
        self.grid.currentItemChanged.connect(self._describe); self.grid.itemDoubleClicked.connect(lambda *_: self._accept())
        self._pending = []; self.timer = QTimer(self); self.timer.setInterval(0); self.timer.timeout.connect(self._render_next)
        QTimer.singleShot(0, self._category_icons); self.side.setCurrentRow(0)

    def _category_icons(self):
        for i in range(self.side.count()):
            kinds = self.side.item(i).data(Qt.UserRole)
            if kinds: self.side.item(i).setIcon(thumbnail(kinds[0], self.cache))

    def _fill(self, kinds):
        self.grid.clear(); self._pending = []
        for k in kinds:
            it = QListWidgetItem(k); it.setData(Qt.UserRole, k); it.setToolTip(f"<p style='max-width:420px'>{PH.html(k, short=True)}</p>")
            why = self.short_of(k)
            if why:
                from PySide6.QtGui import QBrush, QColor
                it.setForeground(QBrush(QColor("#a0a4aa"))); it.setToolTip(f"<p style='max-width:420px'><b>{why}</b><br>{PH.html(k, short=True)}</p>")
            self.grid.addItem(it); self._pending.append(it)
        self.timer.start()  # thumbnails render one by one, so the window stays responsive
        if self.grid.count(): self.grid.setCurrentRow(0)

    def short_of(self, kind):
        """Why the selected columns cannot make this plot ('' if they can, or if it cannot be told)."""
        need = min_ys(kind)
        if self.n_ys is None or need is None or kind in MATRIX_KINDS or self.n_ys >= need: return ""
        return f"Needs {need} data columns besides X ({HINTS[kind]}); {self.n_ys} selected."

    def _render_next(self):
        if not self._pending: return self.timer.stop()
        it = self._pending.pop(0)
        try: it.setIcon(thumbnail(it.data(Qt.UserRole), self.cache))
        except RuntimeError: self._pending = []

    def show_category(self, row):
        if row >= 0 and not self.search.text(): self._fill(self.side.item(row).data(Qt.UserRole))

    def filter(self, text):
        t = text.strip().lower()
        if not t: return self.show_category(self.side.currentRow())
        self._fill(list(dict.fromkeys(k for _, ks in self.cats for k in ks if t in k.lower() or t in HINTS.get(k, "").lower())))  # once each

    def _describe(self, cur, _prev=None):
        if cur is None: return
        from .examples import for_plot
        k = cur.data(Qt.UserRole); why = self.short_of(k)
        self.hint.setHtml((f"<p style='color:#b45309'><b>{why}</b> Select more columns, or open the example data.</p>" if why else "") + PH.html(k))
        self.example.setEnabled(for_plot(k) is not None)

    def _open_example(self):
        """Load the example worksheet for the selected plot type and plot it (the gallery closes)."""
        it = self.grid.currentItem()
        if it is None: return
        self.choice = ("example", it.data(Qt.UserRole)); self.accept()

    def _accept(self):
        it = self.grid.currentItem()
        if it is not None: self.choice = it.data(Qt.UserRole); self.accept()
