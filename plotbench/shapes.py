"""Drawing objects on graphs, as in Origin's Rectangle, Circle, Polygon, Region, Line and Arrow tools: drawn with the mouse, kept
in data coordinates with the graph, filled with a colour and/or a hatch pattern, and edited by double-clicking.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Each object is an annotation {kind: line | arrow2 | rect | circle | polygon | region, points: [[x, y], ...], ec, fc, fill, hatch,
lw, ls, alpha, head, z}.
"""
import numpy as np
from matplotlib.patches import Rectangle, Ellipse, Polygon, FancyArrowPatch
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QColorDialog,
                               QHBoxLayout, QSpinBox)

KINDS = {"line": "Line", "arrow2": "Arrow", "rect": "Rectangle", "circle": "Circle / ellipse", "polygon": "Polygon", "region": "Region (freehand)"}
HATCHES = [("None", ""), ("Diagonal /", "//"), ("Diagonal \\", "\\\\"), ("Cross-hatch x", "xx"), ("Grid +", "++"), ("Horizontal", "--"),
           ("Vertical", "||"), ("Dots", ".."), ("Small circles", "oo"), ("Large circles", "OO"), ("Stars", "**"), ("Dense /", "////")]
LINESTYLES = [("Solid", "-"), ("Dashed", "--"), ("Dotted", ":"), ("Dash-dot", "-.")]
HEADS = [("Simple ->", "->"), ("Filled -|>", "-|>"), ("Both ends <->", "<->"), ("Filled both <|-|>", "<|-|>"), ("Bar ]-[", "]-["),
         ("Fancy", "fancy"), ("Wedge", "wedge")]
DEFAULT = {"ec": "#000000", "fc": "#1f77b4", "fill": False, "hatch": "", "lw": 1.2, "ls": "-", "alpha": 0.35, "head": "-|>", "z": 4}


def draw(ax, a, ai):
    """Draw one object into axes ax; the artist gets gid 'pbann:<index>' so a double-click finds it."""
    p = np.asarray(a.get("points", []), float)
    if len(p) < 2: return None
    k = a["kind"]; gid = f"pbann:{ai}"; ec, lw, ls, z = a.get("ec", "#000"), float(a.get("lw", 1.2)), a.get("ls", "-"), float(a.get("z", 4))
    fill = bool(a.get("fill")) or bool(a.get("hatch")); fc = a.get("fc", "#1f77b4") if a.get("fill") else "none"
    style = dict(edgecolor=ec, facecolor=fc, lw=lw, ls=ls, alpha=None, zorder=z, hatch=a.get("hatch") or None, fill=fill, gid=gid)
    if k == "line":
        art, = ax.plot(p[:, 0], p[:, 1], ls=ls, lw=lw, color=ec, zorder=z, label="_shape", gid=gid)
        return art
    if k == "arrow2":
        art = FancyArrowPatch(tuple(p[0]), tuple(p[-1]), arrowstyle=a.get("head", "-|>"), mutation_scale=12 + 4 * lw, color=ec, lw=lw, ls=ls,
                              zorder=z, gid=gid)
        ax.add_patch(art); return art
    if k == "rect":
        (x0, y0), (x1, y1) = p[0], p[-1]; art = Rectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0), **style)
    elif k == "circle":
        (x0, y0), (x1, y1) = p[0], p[-1]; art = Ellipse(((x0 + x1) / 2, (y0 + y1) / 2), abs(x1 - x0), abs(y1 - y0), **style)
    else:  # polygon or freehand region
        art = Polygon(p, closed=True, **style)
    if a.get("fill"): art.set_facecolor(_rgba(a.get("fc", "#1f77b4"), float(a.get("alpha", 0.35))))
    ax.add_patch(art); return art


def swatch(colour):
    """Style sheet for a colour button: the colour as background, dark or white text, whichever can be read on it."""
    q = QColor(colour); dark = (0.299 * q.red() + 0.587 * q.green() + 0.114 * q.blue()) > 150
    return f"background: {q.name()}; color: {'#0f172a' if dark else '#ffffff'}"


def _rgba(c, alpha):
    q = QColor(c); return (q.redF(), q.greenF(), q.blueF(), alpha)


class DrawTool:
    """Mouse handler for drawing one object on a graph window: drag for line, arrow, rectangle, circle and region; click points
    for a polygon and double-click (or right-click) to finish. Esc cancels."""

    def __init__(self, g, kind, props=None):
        self.g, self.kind, self.props = g, kind, {**DEFAULT, **(props or {})}; self.pts = []; self.preview = None; self.down = False
        c = g.canvas; self.cids = [c.mpl_connect("button_press_event", self.press), c.mpl_connect("motion_notify_event", self.move),
                                   c.mpl_connect("button_release_event", self.release), c.mpl_connect("key_press_event", self.key)]
        g.canvas.setCursor(Qt.CrossCursor); g._drawing = self
        g.main.statusBar().showMessage(f"{KINDS[kind]}: " + ("click the corners, double-click to finish" if kind == "polygon" else "drag on the graph")
                                       + " (Esc cancels)", 15000)

    def _ax(self):
        ax = [a for a in self.g._plot_axes() if a.name == "rectilinear"]; return ax[0] if ax else None

    def press(self, ev):
        if ev.inaxes is None or ev.xdata is None: return
        if self.kind == "polygon":
            if ev.button == 3 or ev.dblclick: return self.finish()
            self.pts.append([ev.xdata, ev.ydata]); self._show(); return
        self.down = True; self.pts = [[ev.xdata, ev.ydata], [ev.xdata, ev.ydata]]

    def move(self, ev):
        if ev.xdata is None: return
        if self.kind == "polygon" and self.pts: self._show(extra=[ev.xdata, ev.ydata]); return
        if not self.down: return
        if self.kind == "region": self.pts.append([ev.xdata, ev.ydata])
        else: self.pts[-1] = [ev.xdata, ev.ydata]
        self._show()

    def release(self, ev):
        if self.kind == "polygon" or not self.down: return
        self.down = False; self.finish()

    def key(self, ev):
        if ev.key == "escape": self.stop(); self.g.draw()

    def _show(self, extra=None):
        ax = self._ax()
        if ax is None: return
        if self.preview is not None:
            try: self.preview.remove()
            except (ValueError, AttributeError): pass
        p = self.pts + ([extra] if extra else [])
        if len(p) >= 2: self.preview = draw(ax, {"kind": self.kind, "points": p, **self.props}, -1)
        self.g.canvas.draw_idle()

    def finish(self):
        pts = [list(map(float, q)) for q in self.pts]; self.stop()
        if len(pts) < 2 or (self.kind == "polygon" and len(pts) < 3): self.g.draw(); return
        if self.kind not in ("polygon", "region") and np.allclose(pts[0], pts[-1]): self.g.draw(); return
        self.g.snapshot(); self.g.spec.setdefault("annotations", []).append({"kind": self.kind, "points": pts, **self.props})
        self.g.draw(); self.g.main.mark_dirty()
        self.g.main.statusBar().showMessage(f"{KINDS[self.kind]} added: double-click it to change colours, fill and pattern, or to delete it", 8000)

    def stop(self):
        for c in self.cids: self.g.canvas.mpl_disconnect(c)
        self.g.canvas.unsetCursor(); self.g._drawing = None


class ShapeDialog(QDialog):
    """Line colour, width and style, fill colour, transparency and hatch pattern, arrow head and layer of one drawn object."""

    def __init__(self, parent, a, arrow=False, closed=True, index=None):
        super().__init__(parent); self.a = dict(a); self.setWindowTitle(KINDS.get(a.get("kind"), "Object") + " properties"); self.deleted = False
        self.g, self.index = (parent, index) if index is not None and hasattr(parent, "spec") else (None, None)
        f = QFormLayout(self)
        self.ec = self._colour_button("ec"); f.addRow("Line colour", self.ec)
        self.lw = QDoubleSpinBox(); self.lw.setRange(0, 20); self.lw.setSingleStep(0.5); self.lw.setValue(float(self.a.get("lw", 1.2))); f.addRow("Line width (pt)", self.lw)
        self.ls = QComboBox(); [self.ls.addItem(n, v) for n, v in LINESTYLES]; self.ls.setCurrentIndex(max(0, self.ls.findData(self.a.get("ls", "-")))); f.addRow("Line style", self.ls)
        if arrow:
            self.head = QComboBox(); [self.head.addItem(n, v) for n, v in HEADS]; self.head.setCurrentIndex(max(0, self.head.findData(self.a.get("head", "-|>"))))
            f.addRow("Arrow head", self.head)
        if closed:
            self.fill = QCheckBox("Fill with colour"); self.fill.setChecked(bool(self.a.get("fill"))); f.addRow("", self.fill)
            self.fc = self._colour_button("fc"); f.addRow("Fill colour", self.fc)
            self.alpha = QSpinBox(); self.alpha.setRange(0, 100); self.alpha.setSuffix(" % opaque"); self.alpha.setValue(int(100 * float(self.a.get("alpha", 0.35)))); f.addRow("Opacity", self.alpha)
            self.hatch = QComboBox(); [self.hatch.addItem(n, v) for n, v in HATCHES]; self.hatch.setCurrentIndex(max(0, self.hatch.findData(self.a.get("hatch", ""))))
            f.addRow("Pattern", self.hatch)
        self.z = QComboBox(); self.z.addItems(["In front of the data", "Behind the data"]); self.z.setCurrentIndex(0 if float(self.a.get("z", 4)) > 2 else 1)
        f.addRow("Layer", self.z)
        row = QHBoxLayout(); dele = QPushButton("Delete object"); dele.clicked.connect(self._delete); row.addWidget(dele); row.addStretch(1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); row.addWidget(bb)
        f.addRow(row)
        if self.g is not None:  # each change shows on the graph at once; Cancel puts the object back
            from .live import watch
            self._orig = dict(self.g.spec["annotations"][self.index]); watch(self, self._preview)
            self.rejected.connect(self._restore)

    def _preview(self, *_):
        try: self.g.spec["annotations"][self.index] = self.value(); self.g.draw()
        except (IndexError, ValueError): pass

    def _restore(self):
        try: self.g.spec["annotations"][self.index] = self._orig; self.g.draw()
        except IndexError: pass

    def _colour_button(self, key):
        b = QPushButton(self.a.get(key, "#000000")); b.setStyleSheet(swatch(self.a.get(key, '#000000')))

        def pick():
            c = QColorDialog.getColor(QColor(self.a.get(key, "#000000")), self, "Colour")
            if c.isValid():
                self.a[key] = c.name(); b.setText(c.name()); b.setStyleSheet(swatch(c.name()))
                if getattr(self, "g", None) is not None: self._preview()
        b.clicked.connect(pick); return b

    def _delete(self): self.deleted = True; self.accept()

    def value(self):
        a = dict(self.a); a.update(lw=self.lw.value(), ls=self.ls.currentData(), z=4 if self.z.currentIndex() == 0 else 0.6)
        if hasattr(self, "head"): a["head"] = self.head.currentData()
        if hasattr(self, "fill"): a.update(fill=self.fill.isChecked(), alpha=self.alpha.value() / 100, hatch=self.hatch.currentData())
        return a
