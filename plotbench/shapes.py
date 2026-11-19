"""Drawing objects on graphs, as in Origin's Rectangle, Circle, Polygon, Region, Line and Arrow tools: drawn with the mouse, kept
in data coordinates with the graph, filled with a colour and/or a hatch pattern, and reshaped on the graph with handles.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Each object is an annotation {kind: line | arrow2 | rect | circle | polygon | region, points: [[x, y], ...], ec, fc, fill, hatch,
lw, ls, alpha, head, z, angle, smooth}. points: the two ends of a line or arrow; two opposite corners of the box of a rectangle or
ellipse before rotation (angle, degrees counter-clockwise on screen, about the centre); the nodes of a polygon or region. smooth:
the boundary of a region is a closed curve through its nodes (Catmull-Rom) instead of straight segments.
"""
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Ellipse, Polygon, FancyArrowPatch
from matplotlib.transforms import Transform, IdentityTransform
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QPushButton, QDialogButtonBox, QColorDialog,
                               QHBoxLayout, QSpinBox, QApplication, QMenu)

KINDS = {"line": "Line", "arrow2": "Arrow", "rect": "Rectangle", "circle": "Circle / ellipse", "polygon": "Polygon", "region": "Region (curved outline)"}
HATCHES = [("None", ""), ("Diagonal /", "//"), ("Diagonal \\", "\\\\"), ("Cross-hatch x", "xx"), ("Grid +", "++"), ("Horizontal", "--"),
           ("Vertical", "||"), ("Dots", ".."), ("Small circles", "oo"), ("Large circles", "OO"), ("Stars", "**"), ("Dense /", "////")]
LINESTYLES = [("Solid", "-"), ("Dashed", "--"), ("Dotted", ":"), ("Dash-dot", "-.")]
HEADS = [("Simple ->", "->"), ("Filled -|>", "-|>"), ("Both ends <->", "<->"), ("Filled both <|-|>", "<|-|>"), ("Bar ]-[", "]-["),
         ("Fancy", "fancy"), ("Wedge", "wedge")]
DEFAULT = {"ec": "#000000", "fc": "#1f77b4", "fill": False, "hatch": "", "lw": 1.2, "ls": "-", "alpha": 0.35, "head": "-|>", "z": 4}
NODES = ("polygon", "region")  # shapes made of nodes
BOXES = ("rect", "circle")     # shapes with a box and an angle
SNAP_PX = 10                   # a click this close to the first node closes a polygon or region
PICK_PX = 8                    # a handle is caught within this distance
HANDLE = "#d62728"


class _Rotated(Transform):
    """Data to screen, then a turn about the screen position of a data point. The turn is made on screen, so a rotated rectangle
    stays a rectangle whatever the axis scales, and follows zoom and pan."""
    input_dims = output_dims = 2; is_separable = False; has_inverse = False

    def __init__(self, ax, centre, angle):
        super().__init__(); self.ax, self.c, self.ang = ax, tuple(map(float, centre)), np.radians(float(angle)); self.set_children(ax.transData)

    def transform_non_affine(self, pts):
        t = self.ax.transData; d = t.transform(np.asarray(pts, float)); c = t.transform(self.c); co, si = np.cos(self.ang), np.sin(self.ang)
        q = d - c; return np.column_stack([c[0] + co * q[:, 0] - si * q[:, 1], c[1] + si * q[:, 0] + co * q[:, 1]])


def _scale(ax):
    """(forward, inverse) per axis for curve fitting: log axes are smoothed in log space, so the curve looks the same on screen."""
    f = lambda s: (np.log10, lambda v: 10.0 ** v) if s == "log" else (lambda v: v, lambda v: v)
    return f(ax.get_xscale()), f(ax.get_yscale())


def smooth_closed(p, ax=None, per=16):
    """Closed Catmull-Rom curve through the nodes p (n x 2): per points for each node-to-node span, in order from node 0."""
    p = np.asarray(p, float); n = len(p)
    if n < 3: return p
    (fx, ix), (fy, iy) = _scale(ax) if ax is not None else ((lambda v: v, lambda v: v),) * 2
    with np.errstate(all="ignore"): q = np.column_stack([fx(p[:, 0]), fy(p[:, 1])])
    if not np.all(np.isfinite(q)): return p
    t = np.linspace(0, 1, per, endpoint=False)[:, None]; out = []
    for k in range(n):
        p0, p1, p2, p3 = q[k - 1], q[k], q[(k + 1) % n], q[(k + 2) % n]
        out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    c = np.vstack(out); return np.column_stack([ix(c[:, 0]), iy(c[:, 1])])


def outline(a, ax=None):
    """Boundary points (data coordinates) of a polygon or region as it is drawn."""
    p = np.asarray(a.get("points", []), float)
    return smooth_closed(p, ax) if a.get("smooth") and len(p) >= 3 else p


def draw(ax, a, ai):
    """Draw one object into axes ax; the artist gets gid 'pbann:<index>' so a click finds it."""
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
    if k in BOXES:
        (x0, y0), (x1, y1) = p[0], p[-1]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        art = (Rectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0), **style) if k == "rect" else
               Ellipse((cx, cy), abs(x1 - x0), abs(y1 - y0), **style))
        if float(a.get("angle", 0) or 0): art.set_transform(_Rotated(ax, (cx, cy), a["angle"]))
    else:  # polygon or region
        art = Polygon(outline(a, ax), closed=True, **style)
    if a.get("fill"): art.set_facecolor(_rgba(a.get("fc", "#1f77b4"), float(a.get("alpha", 0.35))))
    ax.add_patch(art); return art


def swatch(colour):
    """Style sheet for a colour button: the colour as background, dark or white text, whichever can be read on it."""
    q = QColor(colour); dark = (0.299 * q.red() + 0.587 * q.green() + 0.114 * q.blue()) > 150
    return f"background: {q.name()}; color: {'#0f172a' if dark else '#ffffff'}"


def _rgba(c, alpha):
    q = QColor(c); return (q.redF(), q.greenF(), q.blueF(), alpha)


def _shift(ev):
    """Shift held: from the event (tests) or the keyboard."""
    if "shift" in str(getattr(ev, "key", "") or ""): return True
    try: return bool(QApplication.keyboardModifiers() & Qt.ShiftModifier)
    except Exception: return False


def _ctrl(ev):
    if "control" in str(getattr(ev, "key", "") or "") or "ctrl" in str(getattr(ev, "key", "") or ""): return True
    try: return bool(QApplication.keyboardModifiers() & Qt.ControlModifier)
    except Exception: return False


def _marks(fig, pts, big=None, ring=None):
    """Temporary handles drawn on the figure in screen pixels (never part of the graph's own contents, so never exported)."""
    out = []
    if len(pts):
        p = np.asarray(pts, float)
        out.append(Line2D(p[:, 0], p[:, 1], ls="", marker="s", ms=6.5, mfc="white", mec=HANDLE, mew=1.3, transform=IdentityTransform(), zorder=1e6))
    if big is not None: out.append(Line2D([big[0]], [big[1]], ls="", marker="s", ms=9, mfc=HANDLE, mec=HANDLE, transform=IdentityTransform(), zorder=1e6 + 1))
    if ring is not None: out.append(Line2D([ring[0]], [ring[1]], ls="", marker="o", ms=8, mfc="white", mec=HANDLE, mew=1.5, transform=IdentityTransform(), zorder=1e6))
    for m in out: fig.add_artist(m); m._pb_mark = True
    return out


def _unmark(marks):
    for m in marks:
        try: m.remove()
        except (ValueError, AttributeError, NotImplementedError): pass
    marks.clear()


class DrawTool:
    """Mouse handler for drawing one object on a graph window. Line, arrow, rectangle and circle: drag. Polygon and region: click
    to place each node; a line follows the mouse; click the first node again, double-click or press Enter to close the shape;
    Backspace or a right-click takes the last node back. Esc cancels and leaves the graph as it was."""

    def __init__(self, g, kind, props=None):
        self.g, self.kind, self.props = g, kind, {**DEFAULT, **(props or {})}; self.pts = []; self.preview = None; self.down = False; self.marks = []
        self.props.pop("angle", None); self.props.pop("smooth", None)
        if kind == "region": self.props["smooth"] = True
        c = g.canvas; self.cids = [c.mpl_connect("button_press_event", self.press), c.mpl_connect("motion_notify_event", self.move),
                                   c.mpl_connect("button_release_event", self.release), c.mpl_connect("key_press_event", self.key)]
        c.setFocusPolicy(Qt.StrongFocus); c.setFocus(); c.setCursor(Qt.CrossCursor); g._drawing = self
        g.main.statusBar().showMessage(f"{KINDS[kind]}: " + ("click to place each node; click the first node, double-click or press Enter to finish; "
                                       "Backspace removes the last node" if kind in NODES else "drag on the graph") + " (Esc cancels)", 20000)

    def _ax(self):
        ax = [a for a in self.g._plot_axes() if a.name == "rectilinear"]; return ax[0] if ax else None

    def _near_start(self, ev):
        ax = self._ax()
        if ax is None or len(self.pts) < 3 or ev.x is None: return False
        s = ax.transData.transform(self.pts[0]); return np.hypot(s[0] - ev.x, s[1] - ev.y) <= SNAP_PX

    def press(self, ev):
        if self.kind in NODES:
            if ev.button == 3: return self.back()
            if ev.dblclick or self._near_start(ev): return self.finish()
            if ev.inaxes is None or ev.xdata is None or ev.button != 1: return
            self.pts.append([ev.xdata, ev.ydata]); self._show(); return
        if ev.button == 3: self.stop(); self.g.draw(); return  # right-click: put the tool down, as Esc does
        if ev.inaxes is None or ev.xdata is None or ev.button != 1: return
        self.down = True; self.pts = [[ev.xdata, ev.ydata], [ev.xdata, ev.ydata]]

    def move(self, ev):
        if self.kind in NODES:
            if self.pts and ev.xdata is not None: self._show(extra=[ev.xdata, ev.ydata], snap=self._near_start(ev))
            return
        if ev.xdata is None or not self.down: return
        self.pts[-1] = [ev.xdata, ev.ydata]; self._show()

    def release(self, ev):
        if self.kind in NODES or not self.down: return
        self.down = False; self.finish()

    def back(self):
        """Take the last node back."""
        if self.pts: self.pts.pop(); self._show()

    def key(self, ev):
        if ev.key == "escape": self.stop(); self.g.draw()
        elif ev.key in ("enter", "return") and self.kind in NODES: self.finish()
        elif ev.key in ("backspace", "delete") and self.kind in NODES: self.back()

    def _show(self, extra=None, snap=False):
        ax = self._ax()
        if ax is None: return
        if self.preview is not None:
            try: self.preview.remove()
            except (ValueError, AttributeError): pass
            self.preview = None
        _unmark(self.marks)
        p = self.pts + ([extra] if extra and not snap else [])
        if self.kind in NODES:  # while placing nodes: straight lines through the clicks to the cursor; the curve appears on finishing
            if len(p) >= 2:
                q = np.asarray(p + ([self.pts[0]] if snap else []), float)
                self.preview = ax.plot(q[:, 0], q[:, 1], color=self.props.get("ec", "#000000"), lw=self.props.get("lw", 1.2),
                                       ls="-", zorder=1e5, gid="pbann:-1", label="_drawing")[0]
        elif len(p) >= 2: self.preview = draw(ax, {"kind": self.kind, "points": p, **self.props}, -1)
        if self.kind in NODES and self.pts:
            px = ax.transData.transform(np.asarray(self.pts, float))
            self.marks = _marks(self.g.fig, px, big=px[0] if snap else None)  # the first node lights up when a click would close the shape
        self.g.canvas.draw_idle()

    def finish(self):
        pts = [list(map(float, q)) for q in self.pts]; self.stop()
        if self.kind in NODES:  # nodes placed twice on the same spot (the two clicks of a double-click) count once
            ax = self._ax(); keep = []
            for q in pts:
                if not keep or ax is None or np.hypot(*(ax.transData.transform(q) - ax.transData.transform(keep[-1]))) > 2: keep.append(q)
            pts = keep
        if len(pts) < 2 or (self.kind in NODES and len(pts) < 3): self.g.draw(); return
        if self.kind not in NODES and np.allclose(pts[0], pts[-1]): self.g.draw(); return
        self.g.snapshot(); self.g.spec.setdefault("annotations", []).append({"kind": self.kind, "points": pts, **self.props})
        self.g.draw(); self.g.main.mark_dirty()
        self.g.main.statusBar().showMessage(f"{KINDS[self.kind]} added: double-click it to move, resize, reshape or turn it; right-click for colours and fill", 9000)

    def stop(self):
        for c in self.cids: self.g.canvas.mpl_disconnect(c)
        _unmark(self.marks)
        if self.preview is not None:
            try: self.preview.remove()
            except (ValueError, AttributeError): pass
        self.g.canvas.unsetCursor(); self.g._drawing = None


class ShapeEditor:
    """Reshape one drawn object on the graph with the mouse (double-click the object, or right-click > Edit handles / nodes).
    Line, arrow: drag an end to lengthen, shorten or turn it (Shift: steps of 15 degrees); drag the line to move it.
    Rectangle, ellipse: eight handles resize (Shift on a corner keeps the proportions); the round handle above turns the shape
    (Shift: 15 degree steps); drag inside to move.
    Polygon, region: drag a node; double-click or Ctrl+click the outline to add a node; Delete removes the selected node; the
    round handle turns the shape about its centre; drag inside to move.
    Enter, Esc or a click on empty space ends editing. All of it is one undo step."""

    def __init__(self, g, i):
        self.g, self.i = g, i; self.marks = []; self.drag = None; self.sel = None; self.changed = False
        if g.nav.mode: getattr(g.nav, "zoom" if "zoom" in str(g.nav.mode).lower() else "pan")()
        a = self.a
        if a["kind"] in NODES and len(a["points"]) > 40:  # an old freehand region: a few dozen nodes are enough to reshape it
            self._touch(); step = len(a["points"]) / 24.0; a["points"] = [a["points"][int(k * step)] for k in range(24)]; a["smooth"] = True
        c = g.canvas; self.cids = [c.mpl_connect("button_press_event", self.press), c.mpl_connect("motion_notify_event", self.move),
                                   c.mpl_connect("button_release_event", self.release), c.mpl_connect("key_press_event", self.key)]
        c.setFocusPolicy(Qt.StrongFocus); c.setFocus(); g._drawing = self
        tip = {"line": "drag an end or the line", "arrow2": "drag an end or the arrow", "rect": "drag a handle to resize, the round handle to turn",
               "circle": "drag a handle to resize, the round handle to turn"}.get(a["kind"], "drag a node; double-click the outline to add one; Delete removes one")
        g.main.statusBar().showMessage(f"Editing {KINDS[a['kind']].lower()}: {tip}. Enter or a click outside ends editing.", 20000)
        self._redraw(full=True)

    @property
    def a(self): return self.g.spec["annotations"][self.i]

    def _ax(self):
        ax = [b for b in self.g._plot_axes() if b.name == "rectilinear"]; return ax[0] if ax else None

    def _px(self, pts): return self._ax().transData.transform(np.asarray(pts, float))
    def _data(self, px): return [list(map(float, q)) for q in self._ax().transData.inverted().transform(np.asarray(px, float))]

    def _touch(self):
        if not self.changed: self.g.snapshot(); self.changed = True

    # ---- geometry on screen
    def _box(self):
        """Centre, half width, half height and the two axis directions of a rectangle or ellipse, in pixels."""
        p = self._px([self.a["points"][0], self.a["points"][-1]]); c = p.mean(0); hw, hh = abs(p[1, 0] - p[0, 0]) / 2, abs(p[1, 1] - p[0, 1]) / 2
        t = np.radians(float(self.a.get("angle", 0) or 0)); return c, hw, hh, np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])

    def handles(self):
        """[(name, x, y)] of the handles in pixels. Names: ('end', k), ('box', sx, sy), ('node', k), ('rot',)."""
        k = self.a["kind"]
        if k in ("line", "arrow2"):
            p = self._px([self.a["points"][0], self.a["points"][-1]]); return [(("end", 0), *p[0]), (("end", 1), *p[1])]
        if k in BOXES:
            c, hw, hh, u, v = self._box(); out = []
            for sx in (-1, 0, 1):
                for sy in (-1, 0, 1):
                    if sx or sy: q = c + sx * hw * u + sy * hh * v; out.append((("box", sx, sy), q[0], q[1]))
            q = c + (hh + 26) * v; out.append((("rot",), q[0], q[1])); return out
        p = self._px(self.a["points"]); out = [(("node", j), q[0], q[1]) for j, q in enumerate(p)]
        out.append((("rot",), p[:, 0].mean(), p[:, 1].max() + 26)); return out

    def _handle_at(self, ev):
        best = None
        for name, x, y in self.handles():
            d = np.hypot(x - ev.x, y - ev.y)
            if d <= PICK_PX + 2 and (best is None or d < best[0]): best = (d, name)
        return best[1] if best else None

    def _artist(self):
        ax = self._ax(); gid = f"pbann:{self.i}"
        return next((t for t in list(ax.patches) + list(ax.lines) if t.get_gid() == gid), None) if ax is not None else None

    def _on_shape(self, ev):
        art = self._artist()
        try: return art is not None and bool(art.contains(ev)[0])
        except Exception: return False

    def _span_at(self, ev, tol=7):
        """Index k of the node-to-node span of the outline under the mouse (a new node goes between k and k + 1), or None."""
        ax = self._ax(); n = len(self.a["points"])
        if self.a.get("smooth") and n >= 3:
            c = ax.transData.transform(smooth_closed(self.a["points"], ax, per=16)); d = np.hypot(c[:, 0] - ev.x, c[:, 1] - ev.y); j = int(np.argmin(d))
            return j // 16 if d[j] <= tol else None
        p = self._px(self.a["points"]); m = np.array([ev.x, ev.y], float); best = None
        for k in range(n):
            s, e = p[k], p[(k + 1) % n]; L = e - s; t = 0 if not L.any() else float(np.clip(np.dot(m - s, L) / np.dot(L, L), 0, 1)); d = np.hypot(*(m - (s + t * L)))
            if d <= tol and (best is None or d < best[0]): best = (d, k)
        return best[1] if best else None

    # ---- mouse and keys
    def press(self, ev):
        if ev.x is None: return
        h = self._handle_at(ev); nodes = self.a["kind"] in NODES
        if ev.button == 3: return self._menu(ev, h)
        if ev.button != 1: return
        span = self._span_at(ev) if nodes and h is None else None
        if nodes and span is not None and (ev.dblclick or _ctrl(ev)):  # a new node exactly where the outline was clicked
            self._touch(); self.a["points"].insert(span + 1, self._data([[ev.x, ev.y]])[0]); self.sel = span + 1
            self.drag = ("h", ("node", span + 1), None); return self._redraw()
        if ev.dblclick and h is None and not self._on_shape(ev): return self.stop()
        if h is not None:
            self.sel = h[1] if h[0] == "node" else None
            self.drag = ("h", h, {"pts": [list(q) for q in self.a["points"]], "angle": float(self.a.get("angle", 0) or 0), "m": (ev.x, ev.y)})
            return self._redraw()
        if self._on_shape(ev) or span is not None:
            self.drag = ("move", (ev.x, ev.y), self._px(self.a["points"])); return
        self.stop()  # a click on empty space ends editing

    def move(self, ev):
        if self.drag is None or ev.x is None: return
        self._touch(); a = self.a; m = np.array([ev.x, ev.y], float)
        if self.drag[0] == "move":
            _, (x0, y0), px = self.drag; a["points"] = self._data(px + (ev.x - x0, ev.y - y0)); return self._redraw()
        _, h, st = self.drag
        if h[0] == "end":
            other = self._px([a["points"][0], a["points"][-1]])[1 - h[1]]
            if _shift(ev):  # steps of 15 degrees about the other end, the length follows the mouse
                d = m - other; t = np.radians(round(np.degrees(np.arctan2(d[1], d[0])) / 15) * 15); m = other + np.hypot(*d) * np.array([np.cos(t), np.sin(t)])
            a["points"][0 if h[1] == 0 else -1] = self._data([m])[0]
        elif h[0] == "node": a["points"][h[1]] = self._data([m])[0]
        elif h[0] == "box":
            _, sx, sy = h; p = self._px([st["pts"][0], st["pts"][-1]]); c = p.mean(0); hw, hh = abs(p[1, 0] - p[0, 0]) / 2, abs(p[1, 1] - p[0, 1]) / 2
            t = np.radians(st["angle"]); u, v = np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])
            anchor = c - sx * hw * u - sy * hh * v; d = m - anchor; du, dv = float(np.dot(d, u)), float(np.dot(d, v))
            if sx and sy and _shift(ev) and hw > 0 and hh > 0:  # keep the proportions
                f = max(abs(du) / (2 * hw), abs(dv) / (2 * hh)); du, dv = np.sign(du or 1) * 2 * hw * f, np.sign(dv or 1) * 2 * hh * f
            nw, nh = (abs(du) / 2 if sx else hw), (abs(dv) / 2 if sy else hh)
            nc = anchor + (du / 2 if sx else 0) * u + (dv / 2 if sy else 0) * v
            a["points"] = self._data([nc - (nw, nh), nc + (nw, nh)])
        elif h[0] == "rot":
            if a["kind"] in BOXES:
                c = self._box()[0]; ang = np.degrees(np.arctan2(m[1] - c[1], m[0] - c[0])) - 90
                a["angle"] = float(round(ang / 15) * 15 if _shift(ev) else ang) % 360
            else:  # turn every node about the centre of the nodes
                px = self._px(st["pts"]); c = px.mean(0); m0 = np.array(st["m"], float)
                t = np.arctan2(m[1] - c[1], m[0] - c[0]) - np.arctan2(m0[1] - c[1], m0[0] - c[0])
                if _shift(ev): t = np.radians(round(np.degrees(t) / 15) * 15)
                q = px - c; co, si = np.cos(t), np.sin(t)
                a["points"] = self._data(np.column_stack([c[0] + co * q[:, 0] - si * q[:, 1], c[1] + si * q[:, 0] + co * q[:, 1]]))
        self._redraw()

    def release(self, ev):
        if self.drag is not None: self.drag = None; self._redraw()

    def key(self, ev):
        if ev.key in ("enter", "return", "escape"): self.stop()
        elif ev.key in ("delete", "backspace"): self.delete_node()

    def delete_node(self, k=None):
        k = self.sel if k is None else k
        if self.a["kind"] not in NODES or k is None or len(self.a["points"]) <= 3:
            if self.a["kind"] in NODES and k is not None: self.g.main.statusBar().showMessage("A polygon or region needs at least three nodes.", 5000)
            return
        self._touch(); self.a["points"].pop(k); self.sel = None; self._redraw()

    def add_node(self, ev):
        span = self._span_at(ev, tol=12)
        if span is not None: self._touch(); self.a["points"].insert(span + 1, self._data([[ev.x, ev.y]])[0]); self.sel = span + 1; self._redraw()

    def _menu(self, ev, h):
        from PySide6.QtGui import QCursor
        m = QMenu(self.g); nodes = self.a["kind"] in NODES
        if nodes and h is not None and h[0] == "node":
            m.addAction("Delete node", lambda: self.delete_node(h[1])).setEnabled(len(self.a["points"]) > 3)
        if nodes: m.addAction("Add node here", lambda: self.add_node(ev)).setEnabled(self._span_at(ev, tol=12) is not None)
        if nodes:
            sm = m.addAction("Smooth curve"); sm.setCheckable(True); sm.setChecked(bool(self.a.get("smooth")))
            sm.triggered.connect(lambda on: (self._touch(), self.a.__setitem__("smooth", bool(on)), self._redraw()))
        m.addSeparator(); m.addAction("Shape properties...", lambda: (self.stop(), self.g.edit_shape(self.i)))
        m.addAction("Finish editing (Enter)", self.stop); m.addSeparator(); m.addAction("Delete shape", self._delete)
        m.exec(QCursor.pos())

    def _delete(self):
        self._touch(); i = self.i; self.stop(draw=False); self.g.spec["annotations"].pop(i); self.g.draw(); self.g.main.mark_dirty()

    # ---- drawing
    def _redraw(self, full=False):
        """Redraw only this object (quick enough to follow the mouse) and its handles."""
        ax = self._ax()
        if ax is None: return
        if full: self.g.draw(); return  # draw() calls refresh() at its end
        art = self._artist()
        if art is not None:
            try: art.remove()
            except (ValueError, NotImplementedError): pass
        draw(ax, self.a, self.i); self.refresh()

    def refresh(self):
        """(Re)place the handles; called after every redraw of the graph."""
        _unmark(self.marks)
        if self._ax() is None: return
        hs = self.handles(); sq = [(x, y) for n, x, y in hs if n[0] != "rot"]; ring = next(((x, y) for n, x, y in hs if n[0] == "rot"), None)
        big = next(((x, y) for n, x, y in hs if n == ("node", self.sel)), None) if self.sel is not None else None
        self.marks = _marks(self.g.fig, sq, big=big, ring=ring)
        if ring is not None and self.a["kind"] in BOXES:  # a thin stalk from the shape to its turning handle
            c, hw, hh, u, v = self._box(); top = c + hh * v
            ln = Line2D([top[0], ring[0]], [top[1], ring[1]], color=HANDLE, lw=0.8, transform=IdentityTransform(), zorder=1e6 - 1)
            self.g.fig.add_artist(ln); ln._pb_mark = True; self.marks.append(ln)
        self.g.canvas.draw_idle()

    def stop(self, draw=True):
        for c in self.cids: self.g.canvas.mpl_disconnect(c)
        _unmark(self.marks); self.g._drawing = None
        if self.changed and hasattr(self.g.main, "mark_dirty"): self.g.main.mark_dirty()
        if draw: self.g.draw()
        self.g.main.statusBar().showMessage("Editing finished" + (" (Ctrl+Z undoes it)" if self.changed else ""), 5000)


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
        if a.get("kind") in NODES:
            self.smooth = QCheckBox("Smooth curve through the nodes (untick for straight segments)"); self.smooth.setChecked(bool(self.a.get("smooth"))); f.addRow("", self.smooth)
        if a.get("kind") in BOXES:
            self.angle = QDoubleSpinBox(); self.angle.setRange(-360, 360); self.angle.setDecimals(1); self.angle.setSingleStep(15); self.angle.setSuffix("°")
            self.angle.setValue(float(self.a.get("angle", 0) or 0)); f.addRow("Angle (counter-clockwise)", self.angle)
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
        if hasattr(self, "smooth"): a["smooth"] = self.smooth.isChecked()
        if hasattr(self, "angle"): a["angle"] = self.angle.value() % 360
        return a
