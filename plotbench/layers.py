"""Layers: more data on the same graph, each with its own Y axis (right), its own X axis (top), both, or the graph's axes.

A layer is one entry of spec["layers"]:
    {"book", "sheet", "x" (None = row number), "ys": [...], "type": one of KINDS, "yaxis": "right" | "left",
     "xaxis": "bottom" | "top", "ylabel", "ymin", "ymax", "yscale", "xlabel", "xmin", "xmax", "xscale", "hide"}
"right" and "top" axes have their own scale and range; "left" and "bottom" share the graph's.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QListWidgetItem, QComboBox, QLineEdit,
                               QPushButton, QDialogButtonBox, QLabel, QAbstractItemView)

KINDS = {"Line": "-", "Scatter": "o", "Line + Symbol": "-o", "Step": "steps", "Column": "bar"}
DEFAULT = {"x": None, "ys": [], "type": "Line", "yaxis": "right", "xaxis": "bottom", "ylabel": "", "ymin": "", "ymax": "", "yscale": "linear",
           "xlabel": "", "xmin": "", "xmax": "", "xscale": "linear"}


def _num(v):
    try: return float(str(v).strip()) if str(v).strip() else None
    except ValueError: return None


def describe(L):
    own = [w for w, on in (("right Y axis", L.get("yaxis") == "right"), ("top X axis", L.get("xaxis") == "top")) if on]
    return f"{', '.join(map(str, L.get('ys', [])))} ({L.get('type', 'Line')}; {' and '.join(own) if own else 'on the graph axes'}) from {L.get('book')}/{L.get('sheet')}"


def draw_layers(g, fig):
    """Draw spec['layers'] over the first (rectilinear) axes of the figure. The main axes stay on top, so the mouse still reads
    the main axes' coordinates; layer curves join the main legend. A layer that cannot be drawn says so in a corner."""
    layers = [L for L in g.spec.get("layers", []) if not L.get("hide")]
    if not layers or not fig.axes or fig.axes[0].name != "rectilinear": return
    import matplotlib
    from cycler import cycler
    ax = fig.axes[0]; colors = matplotlib.rcParams["axes.prop_cycle"].by_key().get("color", ["C0"])
    used = len([ln for ln in ax.get_lines() if not ln.get_label().startswith("_")]) + len(ax.containers); n_right = 0; made = []
    for k, L in enumerate(layers):
        try:
            sh = g.main.sheet_ref(L["book"], L.get("sheet"))
            x = sh.arr(L["x"]) if L.get("x") else np.arange(1.0, len(sh.df) + 1)
            own_y, own_x = L.get("yaxis") == "right", L.get("xaxis") == "top"
            t1 = ax.twinx() if own_y else ax; a = t1.twiny() if own_x else t1  # t1 carries the Y axis, a the curves (and the X axis)
            for b in {t1, a} - {ax}: b._pb_layer = True; b._pb_layer_of = ax; made.append(b)
            if a is not ax:
                a.set_prop_cycle(cycler(color=colors[used % len(colors):] + colors[:used % len(colors)]))
            first = None
            for j, c in enumerate(L["ys"]):
                y = sh.arr(c); lab = sh.label(c); col = None if a is not ax else colors[(used + j) % len(colors)]
                kind = KINDS.get(L.get("type", "Line"), "-")
                if kind == "bar":  # width from the smallest gap between different X values (repeated X values give no gap)
                    gaps = np.diff(np.unique(x[np.isfinite(x)])); w = 0.8 * (float(gaps.min()) if gaps.size else 1.0) / max(len(L["ys"]), 1)
                    art = a.bar(x + (j - (len(L["ys"]) - 1) / 2) * w, y, w, label=lab, color=col, alpha=0.75).patches[0]
                elif kind == "steps": art = a.step(x, y, where="mid", label=lab, color=col)[0]
                else: art = a.plot(x, y, kind, label=lab, color=col, ms=4)[0]
                first = first or art
            used += len(L["ys"])
            if first is None: raise ValueError("no Y column chosen")  # said in the corner like any other skipped layer
            if a is ax: continue
            colr = first.get_facecolor() if hasattr(first, "get_facecolor") and not hasattr(first, "get_color") else first.get_color()
            if own_y:
                t1.set_ylabel(L.get("ylabel") or ", ".join(sh.label(c) for c in L["ys"]), color=colr); t1.tick_params(axis="y", colors=colr)
                if L.get("yscale", "linear") != "linear": t1.set_yscale(L["yscale"])
                lo, hi = _num(L.get("ymin", "")), _num(L.get("ymax", ""))
                if lo is not None or hi is not None: t1.set_ylim(lo, hi)
                t1.spines["right"].set_position(("outward", 58 * n_right)); n_right += 1  # a second, third ... right axis stands further out
                if a is not t1: a.spines["right"].set_visible(False)
            if own_x:
                a.set_xlabel(L.get("xlabel") or sh.label(L.get("x")), color=colr); a.tick_params(axis="x", colors=colr)
                if L.get("xscale", "linear") != "linear": a.set_xscale(L["xscale"])
                lo, hi = _num(L.get("xmin", "")), _num(L.get("xmax", ""))
                if lo is not None or hi is not None: a.set_xlim(lo, hi)
        except (KeyError, ValueError, StopIteration, IndexError) as e:
            ax.text(0.02, 0.96 - 0.05 * k, f"layer {k + 1} skipped: {e}", transform=ax.transAxes, fontsize=7, color="firebrick", va="top")
    if made:  # the main axes on top (mouse coordinates, shapes, picking); its background goes to the lowest layer
        ax.set_zorder(max(b.get_zorder() for b in made) + 1); made[0].patch.set_visible(True); made[0].patch.set_facecolor(ax.get_facecolor())
        for b in made[1:]: b.patch.set_visible(False)
        ax.patch.set_visible(False)


def layer_handles(ax):
    """(handles, labels) of the curves on the layer axes of ax, for the main legend."""
    h, l = [], []
    for b in ax.figure.axes:
        if getattr(b, "_pb_layer_of", None) is ax:
            hh, ll = b.get_legend_handles_labels(); h += hh; l += ll
    return h, l


class LayerEdit(QDialog):
    """One layer: where its data is, how it is drawn, and which axes it uses."""

    def __init__(self, main, layer=None):
        super().__init__(main); self.setWindowTitle("Layer"); self.main = main; L = {**DEFAULT, **(layer or {})}
        self.sheet = QComboBox(); self.sheet.addItems([f"{w.name}/{s.name}" for w in main.windows() if w.kind == "book" for s in w.sheets])
        if L.get("book"): self.sheet.setCurrentText(f"{L['book']}/{L.get('sheet')}")
        self.x = QComboBox(); self.ys = QListWidget(); self.ys.setSelectionMode(QAbstractItemView.NoSelection); self.ys.setMaximumHeight(150)
        self.kind = QComboBox(); self.kind.addItems(list(KINDS)); self.kind.setCurrentText(L["type"])
        self.yaxis = QComboBox(); self.yaxis.addItem("Its own Y axis, on the right", "right"); self.yaxis.addItem("The graph's Y axis (left)", "left")
        self.xaxis = QComboBox(); self.xaxis.addItem("The graph's X axis (bottom)", "bottom"); self.xaxis.addItem("Its own X axis, on the top", "top")
        self.yaxis.setCurrentIndex(self.yaxis.findData(L["yaxis"])); self.xaxis.setCurrentIndex(self.xaxis.findData(L["xaxis"]))
        self.ylabel, self.ymin, self.ymax = QLineEdit(L["ylabel"]), QLineEdit(str(L["ymin"])), QLineEdit(str(L["ymax"]))
        self.xlabel, self.xmin, self.xmax = QLineEdit(L["xlabel"]), QLineEdit(str(L["xmin"])), QLineEdit(str(L["xmax"]))
        self.yscale, self.xscale = QComboBox(), QComboBox()
        for c, v in ((self.yscale, L["yscale"]), (self.xscale, L["xscale"])): c.addItems(["linear", "log"]); c.setCurrentText(v)
        for e in (self.ymin, self.ymax, self.xmin, self.xmax): e.setPlaceholderText("auto"); e.setFixedWidth(90)
        for e in (self.ylabel, self.xlabel): e.setPlaceholderText("from the column names")
        yr = QHBoxLayout(); [yr.addWidget(w) for w in (QLabel("from"), self.ymin, QLabel("to"), self.ymax, self.yscale)]; yr.addStretch()
        xr = QHBoxLayout(); [xr.addWidget(w) for w in (QLabel("from"), self.xmin, QLabel("to"), self.xmax, self.xscale)]; xr.addStretch()
        f = QFormLayout(); f.addRow("Data from", self.sheet); f.addRow("X column", self.x); f.addRow("Y columns (tick)", self.ys); f.addRow("Draw as", self.kind)
        f.addRow("Y axis", self.yaxis); self.rows_y = [f.rowCount(), f.rowCount() + 1]; f.addRow("Y axis title", self.ylabel); f.addRow("Y range", yr)
        f.addRow("X axis", self.xaxis); self.rows_x = [f.rowCount(), f.rowCount() + 1]; f.addRow("X axis title", self.xlabel); f.addRow("X range", xr)
        self.form = f
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self._ok); bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self); lay.addLayout(f); lay.addWidget(bb)
        self._want = (L.get("x"), set(map(str, L.get("ys", [])))); self.sheet.currentTextChanged.connect(self._columns); self._columns()
        self.yaxis.currentIndexChanged.connect(self._own); self.xaxis.currentIndexChanged.connect(self._own); self._own()

    def _sheet(self):
        book, _, sheet = self.sheet.currentText().partition("/"); return self.main.sheet_ref(book, sheet)

    def _columns(self):
        self.x.clear(); self.ys.clear()
        if not self.sheet.currentText(): return
        sh = self._sheet(); self._cols = list(sh.df.columns); wx, wy = self._want
        self.x.addItem("(row number)", None)
        for c in self._cols: self.x.addItem(str(c), c)
        xc = wx if wx in self._cols else sh.x_col(); self.x.setCurrentIndex(max(self.x.findText(str(xc)), 0) if xc is not None else 0)
        for c in self._cols:
            it = QListWidgetItem(str(c)); it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setData(Qt.UserRole, c)
            it.setCheckState(Qt.Checked if str(c) in wy else Qt.Unchecked); self.ys.addItem(it)

    def _own(self):
        for rows, on in ((self.rows_y, self.yaxis.currentData() == "right"), (self.rows_x, self.xaxis.currentData() == "top")):
            for r in rows: self.form.setRowVisible(r, on)

    def _ok(self):
        from PySide6.QtWidgets import QMessageBox
        if not self.value()["ys"]: return QMessageBox.information(self, "Layer", "Tick at least one Y column to draw in this layer.")
        self.accept()

    def value(self):
        book, _, sheet = self.sheet.currentText().partition("/")
        ys = [self.ys.item(i).data(Qt.UserRole) for i in range(self.ys.count()) if self.ys.item(i).checkState() == Qt.Checked]
        return {"book": book, "sheet": sheet, "x": self.x.currentData(), "ys": [c for c in ys if c != self.x.currentData()], "type": self.kind.currentText(),
                "yaxis": self.yaxis.currentData(), "xaxis": self.xaxis.currentData(), "ylabel": self.ylabel.text().strip(),
                "ymin": self.ymin.text().strip(), "ymax": self.ymax.text().strip(), "yscale": self.yscale.currentText(),
                "xlabel": self.xlabel.text().strip(), "xmin": self.xmin.text().strip(), "xmax": self.xmax.text().strip(), "xscale": self.xscale.currentText()}


class LayerManager(QDialog):
    """The layers of a graph: add, edit, hide, reorder and remove them. Every change shows on the graph at once; Cancel undoes all."""

    def __init__(self, graph):
        import copy
        super().__init__(graph.main); self.setWindowTitle(f"Layers of {graph.name}"); self.resize(620, 360); self.g = graph
        self._before = copy.deepcopy((graph.spec, graph.fits)); self.changed = False
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(lambda *_: self.edit()); self.list.itemChanged.connect(self._ticked)
        note = QLabel("A layer puts more data on this graph, with its own Y axis on the right, its own X axis on the top, or on the graph's "
                      "axes. Untick a layer to hide it. The first line is the graph itself.")
        note.setWordWrap(True); note.setStyleSheet("color: gray")
        col = QVBoxLayout()
        for text, slot in (("Add layer...", self.add), ("Edit...", self.edit), ("Move up", lambda: self.move(-1)), ("Move down", lambda: self.move(1)), ("Remove", self.remove)):
            b = QPushButton(text); b.clicked.connect(slot); col.addWidget(b)
        col.addStretch(); row = QHBoxLayout(); row.addWidget(self.list, 1); row.addLayout(col)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self); lay.addWidget(note); lay.addLayout(row, 1); lay.addWidget(bb); self.fill()

    def layers(self): return self.g.spec.setdefault("layers", [])

    def fill(self, keep=None):
        self.list.blockSignals(True); self.list.clear()
        base = QListWidgetItem(f"Graph: {', '.join(map(str, self.g.spec.get('ys', [])))} ({self.g.spec.get('type')})"); base.setFlags(Qt.ItemIsEnabled); self.list.addItem(base)
        for i, L in enumerate(self.layers()):
            it = QListWidgetItem(f"Layer {i + 1}: {describe(L)}"); it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked if L.get("hide") else Qt.Checked); self.list.addItem(it)
        self.list.blockSignals(False)
        if keep is not None and self.list.count() > 1: self.list.setCurrentRow(max(1, min(keep + 1, self.list.count() - 1)))

    def _index(self): return self.list.currentRow() - 1 if self.list.currentRow() >= 1 else None

    def _apply(self, keep=None): self.changed = True; self.g.draw(); self.fill(keep)

    def _ticked(self, it):
        i = self.list.row(it) - 1
        if 0 <= i < len(self.layers()):
            if it.checkState() == Qt.Checked: self.layers()[i].pop("hide", None)
            else: self.layers()[i]["hide"] = True
            self.changed = True; self.g.draw()

    def add(self):
        d = LayerEdit(self.g.main)
        if d.exec(): self.layers().append(d.value()); self._apply(len(self.layers()) - 1)

    def edit(self):
        i = self._index()
        if i is None: return
        d = LayerEdit(self.g.main, self.layers()[i])
        if d.exec(): self.layers()[i] = {**d.value(), **({"hide": True} if self.layers()[i].get("hide") else {})}; self._apply(i)

    def move(self, step):
        i = self._index(); L = self.layers()
        if i is None or not 0 <= i + step < len(L): return
        L[i], L[i + step] = L[i + step], L[i]; self._apply(i + step)

    def remove(self):
        i = self._index()
        if i is not None: self.layers().pop(i); self._apply(i)

    def done(self, r):
        if r == QDialog.Accepted and self.changed:  # one undo step for everything done in the dialog
            self.g.history.append(self._before); del self.g.history[:-30]; self.g.redo_stack = []
            if hasattr(self.g.main, "mark_dirty"): self.g.main.mark_dirty()
        elif self.changed: self.g.spec, self.g.fits = self._before; self.g.draw()
        super().done(r)
