"""PlotBench Start page: logo, quick actions, templates with preview thumbnails, recent projects.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import io
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QListWidget, QListWidgetItem, QCheckBox,
                               QPushButton, QWidget, QListView, QStyle)

ASSETS = Path(__file__).parent / "assets"


def asset(name): return str(ASSETS / name)


def app_icon(): return QIcon(asset("icon.ico")) if (ASSETS / "icon.ico").exists() else QIcon()


# ---------------------------------------------------------------- templates: sample data that shows what each layout is for
def _tpl_blank():
    return pd.DataFrame({"A": [np.nan] * 32, "B": [np.nan] * 32}), {"A": "X", "B": "Y"}, None, {}


def _tpl_calibration():
    c = np.array([0, 1, 2, 5, 10, 20, 50.0]); s = 0.02 + 0.051 * c + np.random.default_rng(1).normal(0, 0.01, c.size)
    return (pd.DataFrame({"Concentration": c, "Signal": s}), {"Concentration": "X", "Signal": "Y"}, ("Scatter", "Concentration", ["Signal"]),
            {"Concentration": {"Long Name": "Concentration", "Units": "ppm"}, "Signal": {"Long Name": "Absorbance", "Units": "a.u."}})


def _tpl_spectrum():
    x = np.linspace(200, 1200, 600); y = (30 * np.exp(-((x - 465) / 18) ** 2) + 55 * np.exp(-((x - 520) / 12) ** 2) + 20 * np.exp(-((x - 850) / 30) ** 2)
                                         + 0.01 * x + np.random.default_rng(2).normal(0, 0.8, x.size))
    return (pd.DataFrame({"Raman shift": x, "Intensity": y}), {"Raman shift": "X", "Intensity": "Y"}, ("Line", "Raman shift", ["Intensity"]),
            {"Raman shift": {"Units": "cm^-1"}, "Intensity": {"Units": "counts"}})


def _tpl_ternary():
    r = np.random.default_rng(3); a = r.dirichlet([4, 2, 1.5], 25)
    return (pd.DataFrame({"Olivine": a[:, 0] * 100, "Pyroxene": a[:, 1] * 100, "Plagioclase": a[:, 2] * 100}),
            {"Olivine": "X", "Pyroxene": "Y", "Plagioclase": "Y"}, ("Ternary", "Olivine", ["Pyroxene", "Plagioclase"]), {})


def _tpl_timeseries():
    t = np.arange(0, 120.0); r = np.random.default_rng(4)
    return (pd.DataFrame({"Time": t, "Temperature": 20 + 5 * np.sin(t / 10) + r.normal(0, 0.5, t.size), "Humidity": 60 - 8 * np.sin(t / 10 + 1) + r.normal(0, 1, t.size)}),
            {"Time": "X", "Temperature": "Y", "Humidity": "Y"}, ("Double-Y", "Time", ["Temperature", "Humidity"]),
            {"Time": {"Units": "min"}, "Temperature": {"Units": "°C"}, "Humidity": {"Units": "%"}})


def _tpl_groups():
    r = np.random.default_rng(5)
    return (pd.DataFrame({"Control": r.normal(10, 1.5, 12), "Treatment A": r.normal(12, 1.5, 12), "Treatment B": r.normal(13.5, 1.5, 12)}),
            {"Control": "Y", "Treatment A": "Y", "Treatment B": "Y"}, ("Box + Data Points", None, ["Control", "Treatment A", "Treatment B"]), {})


def _tpl_repeated():
    r = np.random.default_rng(6); rows = []
    for s in range(10):
        b = r.normal(0, 2)
        for t in (0, 1, 2, 3): rows.append((f"S{s + 1}", "drug" if s >= 5 else "placebo", t, 50 + b + (3 if s >= 5 else 1) * t + r.normal(0, 1)))
    df = pd.DataFrame(rows, columns=["Subject", "Group", "Week", "Score"])
    return df, {"Subject": "Label", "Group": "Label", "Week": "X", "Score": "Y"}, ("Scatter", "Week", ["Score"]), {}


def _tpl_piper():
    r = np.random.default_rng(7); n = 8
    df = pd.DataFrame({"Ca": r.uniform(1, 5, n), "Mg": r.uniform(0.5, 3, n), "Na+K": r.uniform(0.5, 4, n), "Cl": r.uniform(0.5, 4, n),
                       "SO4": r.uniform(0.2, 2, n), "HCO3+CO3": r.uniform(1, 5, n), "Sample": [f"W{i + 1}" for i in range(n)]})
    return df, {"Ca": "X", "Sample": "Label"}, ("Piper Diagram", "Ca", ["Mg", "Na+K", "Cl", "SO4", "HCO3+CO3"]), {c: {"Units": "meq/L"} for c in df.columns[:6]}


def _tpl_surface():
    r = np.random.default_rng(8); x, y = r.uniform(-3, 3, 300), r.uniform(-3, 3, 300)
    return (pd.DataFrame({"X": x, "Y": y, "Z": np.exp(-(x ** 2 + y ** 2) / 4) * np.cos(x)}), {"X": "X", "Y": "Y", "Z": "Z"},
            ("Contour (XYZ)", "X", ["Y", "Z"]), {})


TEMPLATES = {"Blank Workbook": _tpl_blank, "Calibration Curve": _tpl_calibration, "Spectrum with Peaks": _tpl_spectrum,
             "Ternary Composition": _tpl_ternary, "Time Series (two Y axes)": _tpl_timeseries, "Grouped Measurements": _tpl_groups,
             "Repeated Measures (long format)": _tpl_repeated, "Water Chemistry (Piper)": _tpl_piper, "Scattered XYZ (contour)": _tpl_surface}


def _thumb(name, w=200, h=150):
    """Small preview: the template's sheet (blank) or its graph."""
    from . import plots as P
    df, desig, plot, meta = TEMPLATES[name]()
    fig = Figure(figsize=(w / 50, h / 50), dpi=50, layout="constrained"); FigureCanvasAgg(fig)
    if plot is None:
        ax = fig.add_subplot(111); ax.axis("off"); ax.set_xlim(0, 4); ax.set_ylim(0, 6)
        for i in range(5): ax.plot([0, 4], [i + 0.5] * 2, color="0.8", lw=1)
        for j in range(1, 4): ax.plot([j, j], [0.5, 5.5], color="0.8", lw=1)
        ax.fill_between([0, 4], 4.5, 5.5, color="#e8eef7"); ax.text(1.5, 5, "A(X)", ha="center", va="center", fontsize=12); ax.text(2.5, 5, "B(Y)", ha="center", va="center", fontsize=12)
    else:
        kind, x, ys = plot
        with matplotlib.rc_context({"font.size": 8, "lines.markersize": 3}):
            xv = df[x].to_numpy() if x else np.arange(len(df)); P.PLOT_TYPES[kind][0](fig, xv, [pd.to_numeric(df[c], errors="coerce").to_numpy(float) for c in ys], ys, x or "", {})
        for a in fig.axes:
            a.set_xlabel(""); a.set_ylabel(""); a.tick_params(labelsize=0, length=0)
            leg = a.get_legend()
            if leg: leg.remove()
    buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor="white"); return QIcon(QPixmap.fromImage(QImage.fromData(buf.getvalue(), "PNG")))


class StartPage(QDialog):
    def __init__(self, main):
        super().__init__(main); self.main = main; self.setWindowTitle("PlotBench: Start"); self.resize(1000, 700); self.setWindowIcon(app_icon())
        self.choice = None
        from .sheets import PREFS
        head = QLabel(); pm = QPixmap(asset("banner_dark.png" if PREFS.get("theme") == "dark" else "banner.png"))
        if not pm.isNull(): head.setPixmap(pm.scaledToHeight(90, Qt.SmoothTransformation))
        head.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabs = QTabWidget()
        self.quick = self._grid(QSize(64, 64)); self.tpl = self._grid(QSize(200, 150)); self.recent = QListWidget()
        icon = lambda n: QIcon(asset(n)) if (ASSETS / n).exists() else QIcon()
        from .toolbars import _icon, draw_tool
        for text, key, ic in (("Blank Workbook", ("template", "Blank Workbook"), QIcon(asset("logo.png"))),
                              ("Import Data (Wizard)", ("action", "import_wizard"), self.style().standardIcon(QStyle.SP_ArrowDown)),
                              ("Open Project", ("action", "open_project"), self.style().standardIcon(QStyle.SP_DirOpenIcon)),
                              ("New Matrixbook", ("action", "new_matrix_dialog"), _icon(draw_tool("matrix"))),
                              ("Digitize a Graph Image", ("action", "digitize"), _icon(draw_tool("digitize"))),
                              ("Python Console", ("action", "show_console"), _icon(draw_tool("console")))):
            it = QListWidgetItem(ic, text); it.setData(Qt.UserRole, key); self.quick.addItem(it)
        for name in TEMPLATES:
            it = QListWidgetItem(_thumb(name), name); it.setData(Qt.UserRole, ("template", name)); self.tpl.addItem(it)
        for r in main.settings.get("recent", []):
            it = QListWidgetItem(self.style().standardIcon(QStyle.SP_FileIcon), r); it.setData(Qt.UserRole, ("recent", r)); self.recent.addItem(it)
        if not main.settings.get("recent"): self.recent.addItem("(no recent projects)")
        self.tabs.addTab(self.quick, "Start"); self.tabs.addTab(self.tpl, "Templates"); self.tabs.addTab(self.recent, "Recent Projects")
        for w in (self.quick, self.tpl, self.recent): w.itemDoubleClicked.connect(lambda *_: self.accept())
        self.show_box = QCheckBox("Show on startup"); self.show_box.setChecked(main.settings.get("show_start", True))
        ok, close = QPushButton("OK"), QPushButton("Close"); ok.setDefault(True); ok.clicked.connect(self.accept); close.clicked.connect(self.reject)
        about = QLabel(f"<span style='color:gray'>PlotBench by Kishan Tiwari</span>")
        bottom = QHBoxLayout(); bottom.addWidget(about); bottom.addStretch(); bottom.addWidget(self.show_box); bottom.addSpacing(20); bottom.addWidget(ok); bottom.addWidget(close)
        lay = QVBoxLayout(self); lay.addWidget(head); lay.addWidget(self.tabs); lay.addLayout(bottom)
        self.quick.setCurrentRow(0); self.tpl.setCurrentRow(0)

    def _grid(self, size):
        from .tiles import make_tile_grid
        return make_tile_grid(size)

    def selected(self):
        w = self.tabs.currentWidget(); it = w.currentItem() if w is not None else None
        return it.data(Qt.UserRole) if it is not None else None

    def done(self, r):
        self.main.settings["show_start"] = self.show_box.isChecked()
        from .app import save_settings
        save_settings(self.main.settings); self.choice = self.selected() if r == QDialog.Accepted else None
        super().done(r)


def make_template(main, name):
    df, desig, plot, meta = TEMPLATES[name]()
    b = main.new_book(df, name.split(" (")[0].replace(" ", ""), meta); sh = b.current(); sh.desig = {c: desig.get(c, "Y") for c in df.columns}; sh.model.refresh()
    if plot: kind, x, ys = plot; main.new_graph(sh, kind, x, ys)
    return b
