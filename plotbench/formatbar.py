"""Quick graph formatting toolbar shown on every graph: series, colour, line, symbol, axes and legend.
Every change applies instantly and can be undone with Ctrl+Z. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
from PySide6.QtCore import Qt, QSize, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QPolygonF, QAction
from PySide6.QtWidgets import (QToolBar, QComboBox, QDoubleSpinBox, QToolButton, QMenu, QColorDialog, QWidgetAction, QWidget,
                               QGridLayout, QLabel)

SWATCHES = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
            "#000000", "#444444", "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628", "#0b3c5d", "#14a39a"]
SYMBOLS = [("No symbol", "None"), ("Circle", "o"), ("Square", "s"), ("Triangle up", "^"), ("Triangle down", "v"), ("Diamond", "D"),
           ("Plus", "P"), ("Cross", "X"), ("Star", "*"), ("Hexagon", "h"), ("Pentagon", "p"), ("Point", ".")]
LINES = [("Solid", "-"), ("Dashed", "--"), ("Dotted", ":"), ("Dash-dot", "-."), ("No line", "None")]


def _sym_icon(mk, color="#1f77b4", size=18):
    pm = QPixmap(size, size); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(30, 30, 30), 1.2)); p.setBrush(QBrush(QColor(color))); c, r = size / 2, size * 0.32
    shapes = {"o": lambda: p.drawEllipse(QPointF(c, c), r, r), "s": lambda: p.drawRect(int(c - r), int(c - r), int(2 * r), int(2 * r)),
              "^": lambda: p.drawPolygon(QPolygonF([QPointF(c, c - r), QPointF(c + r, c + r), QPointF(c - r, c + r)])),
              "v": lambda: p.drawPolygon(QPolygonF([QPointF(c, c + r), QPointF(c + r, c - r), QPointF(c - r, c - r)])),
              "D": lambda: p.drawPolygon(QPolygonF([QPointF(c, c - r), QPointF(c + r, c), QPointF(c, c + r), QPointF(c - r, c)])),
              ".": lambda: p.drawEllipse(QPointF(c, c), r / 2.5, r / 2.5)}
    if mk in shapes: shapes[mk]()
    elif mk in ("P", "X"):
        p.setPen(QPen(QColor(color), 3.5))
        if mk == "P": p.drawLine(QPointF(c, c - r), QPointF(c, c + r)); p.drawLine(QPointF(c - r, c), QPointF(c + r, c))
        else: p.drawLine(QPointF(c - r, c - r), QPointF(c + r, c + r)); p.drawLine(QPointF(c - r, c + r), QPointF(c + r, c - r))
    elif mk in ("*", "h", "p"):
        import math
        n, inner = {"*": (5, 0.45), "h": (6, 1.0), "p": (5, 1.0)}[mk]; pts = []
        for i in range(n * (2 if mk == "*" else 1)):
            ang = -math.pi / 2 + i * math.pi / (n if mk == "*" else n / 2); rr = r * (inner if mk == "*" and i % 2 else 1.1)
            pts.append(QPointF(c + rr * math.cos(ang), c + rr * math.sin(ang)))
        p.drawPolygon(QPolygonF(pts))
    p.end(); return QIcon(pm)


def _line_icon(ls, w=34, h=14):
    pm = QPixmap(w, h); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    style = {"-": Qt.SolidLine, "--": Qt.DashLine, ":": Qt.DotLine, "-.": Qt.DashDotLine}.get(ls)
    if style is not None: pen = QPen(QColor(60, 60, 60), 2); pen.setStyle(style); p.setPen(pen); p.drawLine(2, h // 2, w - 2, h // 2)
    else: p.setPen(QPen(QColor(150, 150, 150), 1)); p.drawText(0, 0, w, h, Qt.AlignCenter, "none")
    p.end(); return QIcon(pm)


def _swatch(color, size=16):
    pm = QPixmap(size, size); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(90, 90, 90), 1)); p.setBrush(QColor(color)); p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3); p.end(); return QIcon(pm)


class FormatBar(QToolBar):
    def __init__(self, graph):
        super().__init__("Format", graph); self.g = graph; self.setObjectName("formatBar"); self.setIconSize(QSize(18, 18)); self._busy = False
        self.series = QComboBox(); self.series.setMinimumWidth(130); self.series.setToolTip("Which curve the changes apply to")
        self.color_btn = QToolButton(); self.color_btn.setToolTip("Curve colour"); self.color_btn.setPopupMode(QToolButton.InstantPopup)
        self.color_btn.setIcon(_swatch("#1f77b4")); self.color_btn.setMenu(self._color_menu())
        self.lw = QDoubleSpinBox(); self.lw.setRange(0, 12); self.lw.setSingleStep(0.5); self.lw.setDecimals(1); self.lw.setPrefix("Line "); self.lw.setSuffix(" pt")
        self.lw.setToolTip("Line thickness")
        self.ls = QComboBox(); [self.ls.addItem(_line_icon(v), "", v) for _, v in LINES]; self.ls.setIconSize(QSize(34, 14)); self.ls.setToolTip("Line style")
        self.mk = QComboBox(); [self.mk.addItem(_sym_icon(v), "none" if v == "None" else "", v) for _, v in SYMBOLS]; self.mk.setToolTip("Symbol shape")
        self.ms = QDoubleSpinBox(); self.ms.setRange(0, 40); self.ms.setSingleStep(1); self.ms.setDecimals(1); self.ms.setPrefix("Size "); self.ms.setToolTip("Symbol size")
        self.hollow = self._toggle("Hollow", "Hollow symbols (no fill)")
        self.addWidget(QLabel(" Curve ")); self.addWidget(self.series); self.addWidget(self.color_btn)
        for w in (self.lw, self.ls, self.mk, self.ms): self.addWidget(w)
        self.addAction(self.hollow); self.addSeparator()
        self.logx = self._toggle("Log X", "Logarithmic X axis"); self.logy = self._toggle("Log Y", "Logarithmic Y axis")
        self.grid = self._toggle("Grid", "Grid lines"); self.legend = self._toggle("Legend", "Show the legend")
        self.font = QDoubleSpinBox(); self.font.setRange(5, 40); self.font.setDecimals(0); self.font.setPrefix("Font "); self.font.setSuffix(" pt")
        for a in (self.logx, self.logy, self.grid, self.legend): self.addAction(a)
        self.addWidget(self.font); self.addSeparator()
        self.edit_plot = QAction("Edit plot...", self)
        self.edit_plot.setToolTip("Change the plot type, X and Y columns, groups and panels (colour-mapped plots: map, range, symbols), with live preview")
        self.edit_plot.triggered.connect(self.reopen); self.addAction(self.edit_plot)
        curves = QAction("Curves...", self); curves.setToolTip("Plot Details: tick curves to show or hide them (data, baseline, peaks, fits), fill under a curve with colour and pattern")
        curves.triggered.connect(lambda: self.g.main.plot_details(self.g)); self.addAction(curves)
        reset = QAction("Reset", self); reset.setToolTip("Remove the quick formatting from this graph"); reset.triggered.connect(self.reset); self.addAction(reset)
        self.series.currentIndexChanged.connect(self.load)
        self.lw.valueChanged.connect(lambda v: self.set_series("lw", v)); self.ms.valueChanged.connect(lambda v: self.set_series("ms", v))
        self.ls.currentIndexChanged.connect(lambda i: self.set_series("ls", self.ls.itemData(i)))
        self.mk.currentIndexChanged.connect(lambda i: self.set_series("marker", self.mk.itemData(i)))
        self.hollow.toggled.connect(lambda on: self.set_series("hollow", on))
        self.logx.toggled.connect(lambda on: self.set_style("xscale", "log" if on else "linear"))
        self.logy.toggled.connect(lambda on: self.set_style("yscale", "log" if on else "linear"))
        self.grid.toggled.connect(lambda on: self.set_style("grid", on)); self.legend.toggled.connect(lambda on: self.set_style("legend", "best" if on else "none"))
        self.font.valueChanged.connect(lambda v: self.set_style("font_size", float(v)))

    def _toggle(self, text, tip):
        a = QAction(text, self); a.setCheckable(True); a.setToolTip(tip); return a

    def _color_menu(self):
        m = QMenu(self); w = QWidget(); grid = QGridLayout(w); grid.setSpacing(3); grid.setContentsMargins(6, 6, 6, 6)
        for i, col in enumerate(SWATCHES):
            b = QToolButton(); b.setIcon(_swatch(col, 18)); b.setAutoRaise(True); b.setToolTip(col)
            b.clicked.connect(lambda checked=False, c=col: (m.close(), self.set_series("color", c))); grid.addWidget(b, i // 10, i % 10)
        wa = QWidgetAction(m); wa.setDefaultWidget(w); m.addAction(wa); m.addSeparator()
        m.addAction("More colours...", self.pick_color); m.addAction("Automatic (palette)", lambda: self.set_series("color", None)); return m

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self._ov().get("color") or "#1f77b4"), self, "Curve colour")
        if c.isValid(): self.set_series("color", c.name())

    # ---- state
    def _key(self): return self.series.currentData() or "all"

    def _ov(self):
        ser = self.g.spec["style"].get("series", {}); return {**ser.get("all", {}), **ser.get(self._key(), {})}

    def refresh(self):
        """Fill the curve list and the controls from the graph (called after each redraw)."""
        from .graphs import full_style
        self._busy = True
        try:
            names = getattr(self.g, "series_names", []); keep = self._key()
            self.series.clear(); self.series.addItem("All curves", "all")
            for i, n in enumerate(names): self.series.addItem(f"{i + 1}: {n}", str(i))
            j = self.series.findData(keep); self.series.setCurrentIndex(j if j >= 0 else 0)
            has_curves = bool(names); cmap = self.g.spec.get("type") in ("Color-mapped Scatter", "Bubble + Color", "Color-mapped Line", "Ternary + Color")
            for w_ in (self.series, self.color_btn, self.lw, self.ls, self.mk, self.ms): w_.setEnabled(has_curves)
            self.hollow.setEnabled(has_curves); self.edit_plot.setVisible(self.g.spec.get("source") != "matrix")
            tip = "" if has_curves else "This graph type has no separate curves to format; use Edit plot... or Graph Properties."
            for w_ in (self.lw, self.ls, self.mk, self.ms): w_.setToolTip(tip or w_.toolTip())
            st = full_style(self.g.spec["style"]); self.logx.setChecked(st["xscale"] == "log"); self.logy.setChecked(st["yscale"] == "log")
            self.grid.setChecked(bool(st["grid"])); self.legend.setChecked(st["legend"] != "none"); self.font.setValue(float(st["font_size"]))
        finally: self._busy = False
        self.load()

    def load(self, *_):
        if self._busy and self.sender() is self.series: return
        from .graphs import full_style
        st = full_style(self.g.spec["style"]); ov = self._ov(); line = (getattr(self.g, "series_lines", []) or [None])[0]
        idx = self._key(); lines = getattr(self.g, "series_lines", [])
        if idx != "all" and int(idx) < len(lines): line = lines[int(idx)]
        art, line = line, (line if type(line).__name__ == "Line2D" else None)  # point and bar sets: style values, own colour
        busy, self._busy = self._busy, True
        try:
            self.lw.setValue(float(ov.get("lw", line.get_linewidth() if line is not None else st["line_width"])))
            self.ms.setValue(float(ov.get("ms", line.get_markersize() if line is not None else st["marker_size"])))
            ls = ov.get("ls", line.get_linestyle() if line is not None else "-"); ls = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}.get(ls, ls)
            self.ls.setCurrentIndex(max(self.ls.findData(ls if ls in [v for _, v in LINES] else "-"), 0))
            mk = ov.get("marker", line.get_marker() if line is not None else "None"); mk = "None" if mk in (None, "", "none") else mk
            self.mk.setCurrentIndex(max(self.mk.findData(mk), 0)); self.hollow.setChecked(bool(ov.get("hollow", False)))
            col = ov.get("color") or (matplotlib_color(art) if art is not None else "#1f77b4"); self.color_btn.setIcon(_swatch(col))
        finally: self._busy = busy

    # ---- changes
    def set_series(self, key, value):
        if self._busy: return
        st = dict(self.g.spec["style"]); ser = {k: dict(v) for k, v in st.get("series", {}).items()}; cur = ser.setdefault(self._key(), {})
        if value is None: cur.pop(key, None)
        else: cur[key] = value
        if self._key() == "all":  # an 'all curves' change overrides the same setting on single curves
            for k in ser:
                if k != "all": ser[k].pop(key, None)
        st["series"] = ser; self.g.set_style(st)

    def set_style(self, key, value):
        if self._busy: return
        st = dict(self.g.spec["style"]); st[key] = value; self.g.set_style(st)

    def reopen(self):
        """Reopen the colour-map builder with this graph's settings and apply the changes to the same graph."""
        from .cmapdlg import ColorMapDialog
        if self.g.spec.get("type") not in ("Color-mapped Scatter", "Bubble + Color", "Color-mapped Line", "Ternary + Color"):
            from .plotedit import PlotEditDialog
            return PlotEditDialog(self.g).exec()
        g = self.g; sh = g.main.sheet_ref(g.spec["book"], g.spec.get("sheet")); d = ColorMapDialog(g.main, sh, g.spec["type"], g.spec.get("extra", {}))
        d.x.setCurrentText(str(g.spec["x"]))
        for cb, c in zip((d.y, d.z, d.c4), g.spec["ys"]): cb.setCurrentText(str(c))
        d.preview()
        if not d.exec(): return
        x, ys = d.columns(); g.snapshot(); g.spec.update(x=x, ys=ys, extra=d.options()); g.draw(); g.main.mark_dirty()

    def reset(self):
        st = dict(self.g.spec["style"]); st.pop("series", None); self.g.set_style(st)


def matplotlib_color(art):
    """Colour of a line, point set or bar series."""
    from matplotlib.colors import to_hex
    try:
        kind = type(art).__name__
        if kind == "Line2D": return to_hex(art.get_color())
        if kind == "PathCollection": return to_hex(art.get_facecolor()[0])
        return to_hex(art.patches[0].get_facecolor())
    except Exception: return "#1f77b4"
