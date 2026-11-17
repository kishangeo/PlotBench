"""Edit plot: change a graph's plot type, X and Y columns, sample groups and panel grid, with live preview.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QListWidget, QListWidgetItem, QCheckBox, QSpinBox, QHBoxLayout,
                               QLabel, QVBoxLayout, QWidget)

from . import plots as P
from . import plots4
from .live import graph_live, add_pane

ROW = "(row number)"


from .shapes import swatch  # noqa: E402


class GroupStyleDialog(QDialog):
    """One sample group of a geochemistry diagram: its name in the legend, colour, symbol and size, with live preview."""

    SYMBOLS = [("Circle", "o"), ("Square", "s"), ("Diamond", "D"), ("Triangle up", "^"), ("Triangle down", "v"), ("Left", "<"), ("Right", ">"),
               ("Pentagon", "p"), ("Hexagon", "h"), ("Star", "*"), ("Plus", "P"), ("Cross", "X")]

    def __init__(self, g, group):
        from PySide6.QtWidgets import QLineEdit, QPushButton, QDoubleSpinBox, QColorDialog
        from PySide6.QtGui import QColor
        import matplotlib
        super().__init__(g.main); self.g, self.group = g, group; self.setWindowTitle(f"Group: {group}")
        art = next((l for a in g.fig.axes for l in a.lines if l.get_gid() == "pbgroup:" + group), None)
        cur = (g.spec.get("extra", {}).get("group_styles") or {}).get(group, {})
        self.label = QLineEdit(cur.get("label") or group)
        self.colour = cur.get("color") or (matplotlib.colors.to_hex(art.get_markerfacecolor()) if art is not None else "#1f77b4")
        self.cbtn = QPushButton(); self._paint()
        self.cbtn.clicked.connect(lambda: self._pick(QColorDialog.getColor(QColor(self.colour), self, "Group colour")))
        self.marker = QComboBox(); [self.marker.addItem(n, v) for n, v in self.SYMBOLS]
        mk = cur.get("marker") or (art.get_marker() if art is not None else "o"); self.marker.setCurrentIndex(max(0, self.marker.findData(mk)))
        self.size = QDoubleSpinBox(); self.size.setRange(1, 40); self.size.setValue(float(cur.get("ms") or (art.get_markersize() if art is not None else 6)))
        f = QFormLayout(); f.addRow("Name in legend", self.label); f.addRow("Colour", self.cbtn); f.addRow("Symbol", self.marker); f.addRow("Size", self.size)
        self.lp = graph_live(self, g, self.apply_to)
        left = QVBoxLayout(); left.addLayout(f); left.addStretch(1); left.addWidget(self.lp.bar())
        lay = QHBoxLayout(self); lay.addLayout(left, 1); lay.addWidget(add_pane(self.lp, g), 2); self.resize(900, 460)
        self.lp.start(); self.cbtn.clicked.connect(self.lp.changed)

    def _paint(self): self.cbtn.setText(self.colour); self.cbtn.setStyleSheet(swatch(self.colour))

    def _pick(self, c):
        if c.isValid(): self.colour = c.name(); self._paint(); self.lp.changed()

    def apply_to(self, g):
        gs = g.spec.setdefault("extra", {}).setdefault("group_styles", {})
        gs[self.group] = {"label": self.label.text().strip() or self.group, "color": self.colour, "marker": self.marker.currentData(),
                          "ms": self.size.value()}


class PlotEditDialog(QDialog):
    """Every change shows on the graph straight away; OK keeps it (one undo step), Cancel puts the graph back."""

    def __init__(self, g):
        super().__init__(g.main); self.g = g; self.setWindowTitle(f"Edit plot: {g.name}"); self.resize(1060, 620)
        sh = g.main.sheet_ref(g.spec["book"], g.spec.get("sheet")); cols = [str(c) for c in sh.df.columns]
        self.type = QComboBox(); self.type.addItems(list(P.PLOT_TYPES)); self.type.setCurrentText(g.spec["type"]); self.type.setMaxVisibleItems(25)
        self.x = QComboBox(); self.x.addItems([ROW] + cols); self.x.setCurrentText(str(g.spec.get("x")) if g.spec.get("x") else ROW)
        self.ys = QListWidget(); self.ys.setToolTip("Tick the Y columns to plot")
        for c in cols:
            it = QListWidgetItem(c); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if c in map(str, g.spec.get("ys", [])) else Qt.Unchecked); self.ys.addItem(it)
        text = [c for c in cols if sh.df[c].dropna().map(lambda v: isinstance(v, str)).all() and sh.df[c].notna().any()]
        self.group = QComboBox(); self.group.addItems(["Automatic", "None"] + text)
        gc = g.spec.get("extra", {}).get("group", "auto"); self.group.setCurrentText("Automatic" if gc == "auto" else "None" if gc == "" else gc)
        p = g.spec.get("panels") or {}
        self.panels = QCheckBox("One panel per Y column"); self.panels.setChecked(bool(p))
        self.rows, self.cols = QSpinBox(), QSpinBox()
        for s, v in ((self.rows, p.get("rows", 0)), (self.cols, p.get("cols", 0))): s.setRange(0, 12); s.setSpecialValueText("auto"); s.setValue(int(v))
        grid = QWidget(); h = QHBoxLayout(grid); h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QLabel("Rows")); h.addWidget(self.rows); h.addWidget(QLabel("Columns")); h.addWidget(self.cols); h.addStretch(1)
        f = QFormLayout(); f.addRow("Plot type", self.type); f.addRow("X column", self.x); f.addRow("Y columns", self.ys)
        f.addRow("Group samples by", self.group); f.addRow("Panels", self.panels); f.addRow("", grid)
        note = QLabel("<span style='color:gray'>Panels: each Y column gets its own small graph on the same page, like the Harker "
                      "diagrams. To put different graphs on one page use Graph &gt; New Layout Page.</span>"); note.setWordWrap(True)
        self.lp = graph_live(self, g, self.apply_to)
        left = QVBoxLayout(); left.addLayout(f); left.addWidget(note); left.addWidget(self.lp.bar())
        lay = QHBoxLayout(self); lay.addLayout(left, 1); lay.addWidget(add_pane(self.lp, g), 2)
        self.type.currentTextChanged.connect(self._enable); self.panels.toggled.connect(self._enable); self._enable()
        self.lp.start(); self.ys.itemChanged.connect(self.lp.changed)

    def _enable(self, *_):
        self.group.setEnabled(self.type.currentText() in plots4.GROUPABLE)
        for w in (self.rows, self.cols): w.setEnabled(self.panels.isChecked())

    def values(self):
        ys = [self.ys.item(i).text() for i in range(self.ys.count()) if self.ys.item(i).checkState() == Qt.Checked]
        x = None if self.x.currentText() == ROW else self.x.currentText()
        return self.type.currentText(), x, [y for y in ys if y != x]

    def apply_to(self, g):
        """Write the dialog's values into g.spec (the live preview and OK both use this)."""
        t, x, ys = self.values()
        if not ys: raise ValueError("Tick at least one Y column.")
        sh = g.main.sheet_ref(g.spec["book"], g.spec.get("sheet"))
        cols = {str(c): c for c in sh.df.columns}
        extra = dict(g.spec.get("extra", {})) if t == g.spec["type"] else {}
        gr = self.group.currentText(); extra["group"] = "auto" if gr == "Automatic" else "" if gr == "None" else gr
        g.spec.update(type=t, x=cols.get(x) if x else None, ys=[cols[y] for y in ys], extra=extra)
        if self.panels.isChecked(): g.spec["panels"] = {"rows": self.rows.value(), "cols": self.cols.value()}
        else: g.spec.pop("panels", None)
