"""Dialog for colour-mapped plots with a live preview. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QLineEdit, QDialogButtonBox,
                               QHBoxLayout, QVBoxLayout, QLabel, QGroupBox)

from . import plots as P
from .plots3 import CMAPS, DEFAULTS


def _cmap_combo(current):
    from PySide6.QtGui import QIcon, QPixmap, QImage
    import matplotlib
    c = QComboBox()
    for name in CMAPS:
        g = (matplotlib.colormaps[name](np.linspace(0, 1, 120))[:, :3] * 255).astype(np.uint8); img = np.repeat(g[None, :, :], 14, 0).copy()
        q = QImage(img.data, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888).copy(); c.addItem(QIcon(QPixmap.fromImage(q)), name)
    from PySide6.QtCore import QSize
    c.setIconSize(QSize(90, 14))
    c.setCurrentText(current); return c


class ColorMapDialog(QDialog):
    def __init__(self, parent, sheet, kind, last=None):
        super().__init__(parent); self.sh, self.kind = sheet, kind; self.setWindowTitle(f"{kind}"); self.resize(1050, 640)
        o = {**DEFAULTS, **(last or {})}; cols = [str(c) for c in sheet.df.columns]; num = [c for c in cols if pd.to_numeric(sheet.df[c], errors="coerce").notna().any()]
        sel = [str(c) for c in sheet.selected_cols()]; xdef = str(sheet.x_col()) if sheet.x_col() is not None else (num[0] if num else cols[0])
        ys = [c for c in sel if c != xdef] or [c for c in num if c != xdef]
        none = ["(none)"]
        self.x, self.y, self.z = QComboBox(), QComboBox(), QComboBox()
        for cb, d in ((self.x, xdef), (self.y, ys[0] if ys else xdef), (self.z, ys[1] if len(ys) > 1 else (ys[-1] if ys else xdef))): cb.addItems(num); cb.setCurrentText(d)
        self.c4 = QComboBox(); self.c4.addItems(num); self.c4.setCurrentText(ys[2] if len(ys) > 2 else self.z.currentText())  # ternary colour
        self.group, self.label, self.size = QComboBox(), QComboBox(), QComboBox()
        for cb, key in ((self.group, "group"), (self.label, "label"), (self.size, "size")):
            cb.addItems(none + cols); cb.setCurrentText(o[key] if o[key] in cols else "(none)")
        self.cmap = _cmap_combo(o["cmap"]); self.rev = QCheckBox("Reverse (e.g. red = low, blue = high)"); self.rev.setChecked(o["reverse"])
        self.auto = QCheckBox("Automatic range"); self.auto.setChecked(o["vmin"] is None and o["vmax"] is None)
        self.vmin, self.vmax = QDoubleSpinBox(), QDoubleSpinBox()
        for sp in (self.vmin, self.vmax): sp.setRange(-1e15, 1e15); sp.setDecimals(4)
        z = pd.to_numeric(sheet.df[self.z.currentText()], errors="coerce") if self.z.currentText() in sheet.df else pd.Series([0, 1])
        self.vmin.setValue(o["vmin"] if o["vmin"] is not None else float(np.nanmin(z) if z.notna().any() else 0))
        self.vmax.setValue(o["vmax"] if o["vmax"] is not None else float(np.nanmax(z) if z.notna().any() else 1))
        self.log = QCheckBox("Log colour scale"); self.log.setChecked(o["log"])
        self.levels = QSpinBox(); self.levels.setRange(0, 50); self.levels.setValue(int(o["levels"])); self.levels.setSpecialValueText("continuous")
        self.ms = QDoubleSpinBox(); self.ms.setRange(1, 40); self.ms.setValue(o["ms"])
        self.edge = QComboBox(); self.edge.addItems(["black", "white", "0.4", "none"]); self.edge.setCurrentText(o["edge"])
        self.edge_w = QDoubleSpinBox(); self.edge_w.setRange(0, 5); self.edge_w.setSingleStep(0.25); self.edge_w.setValue(o["edge_w"])
        self.alpha = QDoubleSpinBox(); self.alpha.setRange(0.05, 1); self.alpha.setSingleStep(0.05); self.alpha.setValue(o["alpha"])
        self.cbar = QComboBox(); self.cbar.addItems(["right", "left", "top", "bottom", "none"]); self.cbar.setCurrentText(o["cbar"])
        self.cbar_label = QLineEdit(o["cbar_label"]); self.cbar_label.setPlaceholderText("automatic: long name (units) of the colour column")
        self.legend_loc = QComboBox(); self.legend_loc.addItems(["best", "lower right", "lower left", "upper right", "upper left", "outside top"]); self.legend_loc.setCurrentText(o["legend_loc"])
        self.hollow = QCheckBox("Hollow symbols in the legend"); self.hollow.setChecked(o["hollow_legend"])
        self.lw = QDoubleSpinBox(); self.lw.setRange(0.2, 20); self.lw.setValue(o["lw"])

        data = QGroupBox("Data"); fd = QFormLayout(data); fd.addRow("X", self.x); fd.addRow("Y" if kind != "Ternary + Color" else "B", self.y)
        if kind == "Ternary + Color": fd.addRow("C", self.z); fd.addRow("Colour by", self.c4)
        else: fd.addRow("Colour by (Z)", self.z)
        if kind in ("Color-mapped Scatter", "Bubble + Color"):
            fd.addRow("Symbol per group (optional)", self.group); fd.addRow("Point labels (optional)", self.label)
        if kind == "Bubble + Color": fd.addRow("Bubble size", self.size)
        col = QGroupBox("Colour"); fc = QFormLayout(col); fc.addRow("Colour map", self.cmap); fc.addRow("", self.rev); fc.addRow("", self.auto)
        rng = QHBoxLayout(); rng.addWidget(self.vmin); rng.addWidget(QLabel("to")); rng.addWidget(self.vmax); fc.addRow("Range", rng)
        fc.addRow("", self.log); fc.addRow("Colour bands", self.levels); fc.addRow("Colour bar", self.cbar); fc.addRow("Colour bar title", self.cbar_label)
        sty = QGroupBox("Style"); fs = QFormLayout(sty)
        if kind == "Color-mapped Line": fs.addRow("Line width", self.lw)
        else:
            fs.addRow("Symbol size", self.ms); fs.addRow("Outline", self.edge); fs.addRow("Outline width", self.edge_w); fs.addRow("Opacity", self.alpha)
            if kind in ("Color-mapped Scatter", "Bubble + Color"): fs.addRow("Legend position", self.legend_loc); fs.addRow("", self.hollow)
        left = QVBoxLayout(); [left.addWidget(g) for g in (data, col, sty)]; left.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.button(QDialogButtonBox.Ok).setText("Create graph")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); left.addWidget(bb)
        self.fig = Figure(figsize=(6, 4.6), layout="constrained"); self.canvas = FigureCanvasQTAgg(self.fig)
        right = QVBoxLayout(); t = QLabel("Live preview"); t.setObjectName("sectionTitle"); right.addWidget(t); right.addWidget(self.canvas, 1)
        row = QHBoxLayout(self); row.addLayout(left, 0); row.addLayout(right, 1)
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(120); self.timer.timeout.connect(self.preview)
        for w in (self.x, self.y, self.z, self.c4, self.group, self.label, self.size, self.cmap, self.edge, self.cbar, self.legend_loc):
            w.currentTextChanged.connect(self.timer.start)
        for w in (self.vmin, self.vmax, self.ms, self.edge_w, self.alpha, self.levels, self.lw): w.valueChanged.connect(self.timer.start)
        for w in (self.rev, self.auto, self.log, self.hollow): w.toggled.connect(self.timer.start)
        self.cbar_label.textChanged.connect(self.timer.start); self.auto.toggled.connect(lambda on: (self.vmin.setEnabled(not on), self.vmax.setEnabled(not on)))
        self.vmin.setEnabled(not self.auto.isChecked()); self.vmax.setEnabled(not self.auto.isChecked()); self.preview()

    def columns(self):
        if self.kind == "Ternary + Color": return self.x.currentText(), [self.y.currentText(), self.z.currentText(), self.c4.currentText()]
        return self.x.currentText(), [self.y.currentText(), self.z.currentText()]

    def options(self):
        nn = lambda cb: None if cb.currentText() == "(none)" else cb.currentText()
        return {"cmap": self.cmap.currentText(), "reverse": self.rev.isChecked(), "vmin": None if self.auto.isChecked() else self.vmin.value(),
                "vmax": None if self.auto.isChecked() else self.vmax.value(), "log": self.log.isChecked(), "levels": self.levels.value(),
                "ms": self.ms.value(), "edge": self.edge.currentText(), "edge_w": self.edge_w.value(), "alpha": self.alpha.value(),
                "cbar": self.cbar.currentText(), "cbar_label": self.cbar_label.text(), "group": nn(self.group), "label": nn(self.label),
                "size": nn(self.size), "legend_loc": self.legend_loc.currentText(), "hollow_legend": self.hollow.isChecked(), "lw": self.lw.value()}

    def preview(self):
        x, ys = self.columns(); sh = self.sh
        try:
            xv = sh.arr(x); yv = [sh.arr(c) for c in ys]; keep = np.isfinite(xv) & np.all([np.isfinite(v) for v in yv], axis=0); rows = np.nonzero(keep)[0]
            extra = {**self.options(), "frame": sh.df, "rows": rows}
            import matplotlib
            with matplotlib.rc_context({"font.size": 9}):
                P.PLOT_TYPES[self.kind][0](self.fig, xv[keep], [v[keep] for v in yv], [sh.label(c) for c in ys], sh.label(x), extra)
        except Exception as e:
            self.fig.clear(); self.fig.text(0.5, 0.5, f"Cannot preview yet:\n{e}", ha="center", va="center", color="firebrick")
        self.canvas.draw_idle()
