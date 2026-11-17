"""Plot Details, as in Origin: every curve of the graph (data, baselines, fitted peaks, fits, added series) in one list with a tick box
to show or hide it, and line, symbol and fill settings for the selected curve, with live preview.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Settings go to graph.spec['style']['series'][index] (the same store as the format bar): hide, color, lw, ls, marker, ms, fill,
fillcolor, hatch, alpha, fill_to.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QListWidget, QListWidgetItem, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QPushButton,
                               QHBoxLayout, QVBoxLayout, QWidget, QColorDialog, QLabel, QSpinBox)
from .live import graph_live, add_pane
from .shapes import HATCHES, LINESTYLES, swatch

MARKERS = [("Keep", None), ("None", "None"), ("Circle", "o"), ("Square", "s"), ("Triangle", "^"), ("Diamond", "D"), ("Star", "*"),
           ("Plus", "P"), ("Cross", "X"), ("Point", ".")]


class PlotDetailsDialog(QDialog):
    def __init__(self, g):
        super().__init__(g.main); self.g = g; self.setWindowTitle(f"Plot Details: {g.name}"); self.resize(1120, 600)
        g.draw(); self.names = list(g.series_names); self.ov = {k: dict(v) for k, v in (g.spec.get("style", {}).get("series") or {}).items()}
        self.list = QListWidget(); self.list.setToolTip("Tick to show a curve, untick to hide it; select one to change how it looks")
        for i, n in enumerate(self.names):
            it = QListWidgetItem(f"{i + 1}. {n}"); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked if self.ov.get(str(i), {}).get("hide") else Qt.Checked); self.list.addItem(it)
        allb, noneb = QPushButton("Show all"), QPushButton("Hide all")
        allb.clicked.connect(lambda: self._all(Qt.Checked)); noneb.clicked.connect(lambda: self._all(Qt.Unchecked))
        left = QVBoxLayout(); left.addWidget(QLabel("<b>Curves</b> (tick = shown)")); left.addWidget(self.list, 1)
        r = QHBoxLayout(); r.addWidget(allb); r.addWidget(noneb); left.addLayout(r)
        self.form = QWidget(); f = QFormLayout(self.form)
        self.color = QPushButton("auto"); self.color.clicked.connect(lambda: self._pick("color", self.color))
        self.lw = QDoubleSpinBox(); self.lw.setRange(0, 12); self.lw.setSingleStep(0.25); self.lw.setSpecialValueText("auto")
        self.ls = QComboBox(); self.ls.addItem("auto", None); [self.ls.addItem(n, v) for n, v in LINESTYLES]; self.ls.addItem("No line", "None")
        self.mk = QComboBox(); [self.mk.addItem(n, v) for n, v in MARKERS]
        self.ms = QDoubleSpinBox(); self.ms.setRange(0, 40); self.ms.setSpecialValueText("auto")
        self.fill = QCheckBox("Fill area under curve")
        self.fill_to = QComboBox(); self.fill_to.addItems(["to Y = 0", "to the bottom of the graph", "to the next curve in the list"])
        self.fcol = QPushButton("same as line"); self.fcol.clicked.connect(lambda: self._pick("fillcolor", self.fcol))
        self.hatch = QComboBox(); [self.hatch.addItem(n, v) for n, v in HATCHES]
        self.alpha = QSpinBox(); self.alpha.setRange(0, 100); self.alpha.setSuffix(" % opaque"); self.alpha.setValue(30)
        for lab, w in (("Colour", self.color), ("Line width (pt)", self.lw), ("Line style", self.ls), ("Symbol", self.mk), ("Symbol size", self.ms),
                       ("", self.fill), ("Fill", self.fill_to), ("Fill colour", self.fcol), ("Pattern", self.hatch), ("Fill opacity", self.alpha)):
            f.addRow(lab, w)
        mid = QVBoxLayout(); mid.addWidget(QLabel("<b>Selected curve</b>")); mid.addWidget(self.form); mid.addStretch(1)
        self.lp = graph_live(self, g, self.apply_to)
        body = QHBoxLayout(); body.addLayout(left, 2); body.addLayout(mid, 2); body.addWidget(add_pane(self.lp, g), 4)
        lay = QVBoxLayout(self); lay.addLayout(body, 1); lay.addWidget(self.lp.bar())
        self.list.currentRowChanged.connect(self._load); self.list.itemChanged.connect(self._ticked)
        for w in (self.lw, self.ms): w.valueChanged.connect(self._store)
        for w in (self.ls, self.mk, self.fill_to, self.hatch): w.currentIndexChanged.connect(self._store)
        self.fill.toggled.connect(self._store); self.alpha.valueChanged.connect(self._store)
        self._loading = False
        if self.names: self.list.setCurrentRow(0)

    def _cur(self): return str(self.list.currentRow())

    def _all(self, state):
        for i in range(self.list.count()): self.list.item(i).setCheckState(state)

    def _ticked(self, it):
        o = self.ov.setdefault(str(self.list.row(it)), {})
        if it.checkState() == Qt.Checked: o.pop("hide", None)
        else: o["hide"] = True
        self.lp.changed()

    def _pick(self, key, btn):
        o = self.ov.setdefault(self._cur(), {}); c = QColorDialog.getColor(QColor(o.get(key, "#1f77b4")), self, "Colour")
        if c.isValid(): o[key] = c.name(); btn.setText(c.name()); btn.setStyleSheet(swatch(c.name())); self.lp.changed()

    def _load(self, row):
        if row < 0: return
        self._loading = True; o = self.ov.get(str(row), {})
        for key, btn, auto in (("color", self.color, "auto"), ("fillcolor", self.fcol, "same as line")):
            btn.setText(o.get(key, auto)); btn.setStyleSheet(swatch(o[key]) if key in o else "")
        self.lw.setValue(float(o.get("lw", 0))); self.ms.setValue(float(o.get("ms", 0)))
        self.ls.setCurrentIndex(max(0, self.ls.findData(o.get("ls")))); self.mk.setCurrentIndex(max(0, self.mk.findData(o.get("marker"))))
        self.fill.setChecked(bool(o.get("fill"))); self.fill_to.setCurrentIndex(int(o.get("fill_to", 0)))
        self.hatch.setCurrentIndex(max(0, self.hatch.findData(o.get("hatch", "")))); self.alpha.setValue(int(100 * float(o.get("alpha", 0.3))))
        self._loading = False

    def _store(self, *_):
        if self._loading or self.list.currentRow() < 0: return
        o = self.ov.setdefault(self._cur(), {})
        for key, val, empty in (("lw", self.lw.value(), 0), ("ms", self.ms.value(), 0), ("ls", self.ls.currentData(), None),
                                ("marker", self.mk.currentData(), None)):
            if val == empty: o.pop(key, None)
            else: o[key] = val
        if self.fill.isChecked():
            o.update(fill=True, fill_to=self.fill_to.currentIndex(), hatch=self.hatch.currentData(), alpha=self.alpha.value() / 100)
        else:
            for k in ("fill", "fill_to", "hatch", "alpha"): o.pop(k, None)
        self.lp.changed()

    def apply_to(self, g):
        st = g.spec.setdefault("style", {}); ser = dict(st.get("series") or {})
        for k, v in self.ov.items():
            if v: ser[k] = dict(v)
            else: ser.pop(k, None)
        st["series"] = ser
