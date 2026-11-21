"""Workspace helpers: the system font for the interface, a dark graph canvas on screen (exports stay white), the graph tools bar
that follows the active window, side-by-side windows, and the Graph Inspector dock (live style of the active graph).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
from matplotlib.colors import to_rgba

UI_FONTS = ["Segoe UI", "SF Pro Text", ".AppleSystemUIFont", "Helvetica Neue", "Inter", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans", "Arial"]
CANVAS_BG, AXES_BG, INK = "#202124", "#2a2b2f", "#e6e6e6"


def ui_font():
    """The first installed of the usual system interface fonts (Segoe UI on Windows, SF Pro on macOS, Noto/Ubuntu on Linux)."""
    from PySide6.QtGui import QFontDatabase
    have = set(QFontDatabase.families())
    return next((f for f in UI_FONTS if f in have), "Arial")


def _dark(c):
    try: r, g, b, a = to_rgba(c)
    except (ValueError, TypeError): return False
    return a > 0 and r + g + b < 0.6  # black and near-black ink


def _white(c):
    try: r, g, b, a = to_rgba(c)
    except (ValueError, TypeError): return False
    return a > 0 and min(r, g, b) > 0.94


def dark_canvas(fig):
    """Recolour a drawn figure for a dark screen: white backgrounds dark, black text, axes, ticks and black curves light. Only the
    window's figure is changed; exports draw a fresh figure, so files stay as styled (white)."""
    from matplotlib.text import Text
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    if _white(fig.patch.get_facecolor()): fig.patch.set_facecolor(CANVAS_BG)
    for ax in fig.axes:
        if _white(ax.get_facecolor()): ax.set_facecolor(AXES_BG)
        for s in ax.spines.values():
            if _dark(s.get_edgecolor()): s.set_edgecolor(INK)
        ax.tick_params(which="both", colors=INK)
        leg = ax.get_legend()
        if leg is not None and _white(leg.get_frame().get_facecolor()): leg.get_frame().set_facecolor(AXES_BG)
    for t in fig.findobj(Text):
        if _dark(t.get_color()): t.set_color(INK)
    for ln in fig.findobj(Line2D):
        if _dark(ln.get_color()): ln.set_color(INK)
        if _dark(ln.get_markeredgecolor()): ln.set_markeredgecolor(INK)
    for p in fig.findobj(Patch):
        if p is not fig.patch and _dark(p.get_edgecolor()) and p.get_linewidth(): p.set_edgecolor(INK)
    from matplotlib.collections import PathCollection
    for pc in fig.findobj(PathCollection):  # scatter points: a single dark colour becomes light (colour-mapped points keep theirs)
        if pc.get_array() is None and len(pc.get_facecolor()) == 1 and _dark(pc.get_facecolor()[0]): pc.set_facecolor(INK)
        if len(pc.get_edgecolor()) == 1 and _dark(pc.get_edgecolor()[0]): pc.set_edgecolor(INK)


def follow(main, sub):
    """Contextual tools: the graph tools bar is shown while a graph or layout is in front, hidden for sheets and matrices."""
    if not (getattr(main, "settings", None) or {}).get("contextual_bars", True) or sub is None: return
    bars = getattr(main, "side_bars", None) or []
    left = next((b for b in bars if b.objectName() == "tb_left"), None)
    w = sub.widget() if hasattr(sub, "widget") else sub
    if left is not None: left.setVisible(getattr(w, "kind", None) in ("graph", "layout"))


def side_by_side(main):
    """The two windows used last next to each other (e.g. the sheet on the left and its graph on the right)."""
    from PySide6.QtWidgets import QMdiArea
    subs = main.mdi.subWindowList(QMdiArea.ActivationHistoryOrder)[-2:]
    if len(subs) < 2: return False
    main.mdi.setViewMode(QMdiArea.SubWindowView); r = main.mdi.viewport().rect(); half = r.width() // 2
    left, right = subs[-2], subs[-1]  # the one in front goes right
    for s_, x in ((left, r.x()), (right, r.x() + half)): s_.showNormal(); s_.setGeometry(x, r.y(), half, r.height())
    from PySide6.QtCore import QObject, QEvent

    class Divider(QObject):  # dragging the inner edge of either window moves the other one with it, like a split handle
        busy = False

        def eventFilter(self, o, e):
            if e.type() == QEvent.Resize and not self.busy and main.mdi.viewMode() == QMdiArea.SubWindowView:
                self.busy = True
                try:
                    full = main.mdi.viewport().rect()
                    if o is left and right.isVisible(): right.setGeometry(left.geometry().right() + 1, right.y(), max(80, full.right() - left.geometry().right()), right.height())
                    elif o is right and left.isVisible(): left.setGeometry(left.x(), left.y(), max(80, right.x() - left.x()), left.height())
                finally: self.busy = False
            return False
    for s_ in getattr(main, "_split_pair", ()):
        try: s_.removeEventFilter(main._divider)
        except RuntimeError: pass
    main._divider = Divider(main); main._split_pair = (left, right)
    for s_ in (left, right): s_.installEventFilter(main._divider)
    return True


SECTIONS = [("Labels", [("title", "Title", "text"), ("xlabel", "X label", "text"), ("ylabel", "Y label", "text")]),
            ("Axes and limits", [("xmin", "X from", "limit"), ("xmax", "X to", "limit"), ("ymin", "Y from", "limit"), ("ymax", "Y to", "limit"),
                                 ("xscale", "X scale", ["linear", "log"]), ("yscale", "Y scale", ["linear", "log"]), ("minor_ticks", "Minor ticks", "bool")]),
            ("Look", [("font_size", "Font size", (4, 40)), ("line_width", "Line width", (0.1, 10)), ("marker_size", "Marker size", (0.5, 30)),
                      ("grid", "Grid", "bool"), ("ticks_in", "Ticks inside", "bool"), ("legend_frame", "Legend frame", "bool")])]
FIELDS = [f for _, fs in SECTIONS for f in fs]


def inspector(main):
    """Graph Inspector dock: the graph in front in collapsible sections (Labels; Axes and limits; Look; Curves with colour swatches;
    Layers and more), applied as they are changed; it follows undo, redo and every redraw."""
    from PySide6.QtWidgets import (QDockWidget, QWidget, QFormLayout, QLineEdit, QDoubleSpinBox, QCheckBox, QLabel, QPushButton,
                                   QToolBox, QVBoxLayout, QComboBox, QColorDialog, QScrollArea)
    from PySide6.QtGui import QColor
    from PySide6.QtCore import Qt
    dock = QDockWidget("Graph Inspector", main); dock.setObjectName("graph_inspector"); outer = QWidget(); lay = QVBoxLayout(outer)
    head = QLabel("No graph in front"); head.setWordWrap(True); lay.addWidget(head)
    tb = QToolBox(); lay.addWidget(tb, 1); w = {}
    for title, fields in SECTIONS:
        page = QWidget(); f = QFormLayout(page)
        for key, label, kind in fields:
            if kind in ("text", "limit"):
                e = QLineEdit(); e.setPlaceholderText("auto" if kind == "limit" else "")
                e.editingFinished.connect(lambda k=key, e=e, lim=(kind == "limit"): put(k, e.text().strip(), lim))
            elif kind == "bool": e = QCheckBox(); e.toggled.connect(lambda on, k=key: put(k, bool(on)))
            elif isinstance(kind, list): e = QComboBox(); e.addItems(kind); e.currentTextChanged.connect(lambda v, k=key: put(k, v))
            else:
                e = QDoubleSpinBox(); e.setRange(*kind); e.setDecimals(1); e.setSingleStep(0.5); e.setKeyboardTracking(False)
                e.valueChanged.connect(lambda v, k=key: put(k, float(v)))
            w[key] = e; f.addRow(label, e)
        tb.addItem(page, title)
    curves = QWidget(); cl = QFormLayout(curves); sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(curves); tb.addItem(sc, "Curves and colours")
    more = QWidget(); ml = QVBoxLayout(more)
    for text, fn in (("Layers (extra axes)...", "layers"), ("Copy format to other graphs...", "copy_format"), ("All settings (Graph Properties)...", "graph_props")):
        b = QPushButton(text); b.clicked.connect(lambda _=False, fn=fn: getattr(main, fn)() if hasattr(main, fn) else None); ml.addWidget(b)
    ml.addStretch(); tb.addItem(more, "Layers and more")
    dock.setWidget(outer); dock.loading = False; dock.sections = tb

    def graph():
        g = main.active("graph") if hasattr(main, "active") else None
        return g if g is not None and hasattr(g, "spec") else None

    def put(key, value, limit=False):
        g = graph()
        if dock.loading or g is None: return
        if limit and value:
            try: float(value)
            except ValueError: main.statusBar().showMessage(f"'{value}' is not a number: leave it empty for automatic.", 6000); return load()
        from .graphs import full_style
        if str(full_style(g.spec.get("style")).get(key)) == str(value): return
        g.set_style({**g.spec.get("style", {}), key: value}); main.mark_dirty()

    def colour(i):
        g = graph()
        if g is None: return
        st = dict(g.spec.get("style", {})); ser = {k: dict(v) for k, v in (st.get("series") or {}).items()}
        c = QColorDialog.getColor(QColor(ser.get(str(i), {}).get("color") or "#1f77b4"), main, "Curve colour")
        if c.isValid(): ser.setdefault(str(i), {})["color"] = c.name(); st["series"] = ser; g.set_style(st); main.mark_dirty()

    def swatch(col):
        from PySide6.QtGui import QPixmap, QIcon
        pm = QPixmap(18, 18); pm.fill(QColor(col)); return QIcon(pm)

    def load(*_):
        g = graph(); outer.setEnabled(g is not None); head.setText(f"<b>{g.name}</b>" if g is not None else "No graph in front")
        if g is None: return
        from .graphs import full_style
        st = full_style(g.spec.get("style")); dock.loading = True
        try:
            for key, _l, kind in FIELDS:
                e = w[key]
                if kind in ("text", "limit"): e.setText(str(st.get(key, "") or ""))
                elif kind == "bool": e.setChecked(bool(st.get(key)))
                elif isinstance(kind, list): e.setCurrentText(str(st.get(key) or kind[0]))
                else: e.setValue(float(st.get(key) or 0))
            while cl.rowCount(): cl.removeRow(0)
            ser = st.get("series") or {}
            for i, (name, art) in enumerate(zip(getattr(g, "series_names", []), getattr(g, "series_lines", []))):
                col = (ser.get(str(i)) or {}).get("color")
                if not col:
                    try:
                        from matplotlib.colors import to_hex
                        col = to_hex(art.get_color() if hasattr(art, "get_color") else art.get_facecolor()[0])
                    except (ValueError, TypeError, IndexError): col = "#888888"
                b = QPushButton(); b.setIcon(swatch(col)); b.setToolTip("Choose this curve's colour"); b.setFixedWidth(36)
                b.clicked.connect(lambda _=False, i=i: colour(i)); cl.addRow(QLabel(str(name)[:40]), b)
        finally: dock.loading = False
    dock.load = load; main.addDockWidget(Qt.RightDockWidgetArea, dock); main.mdi.subWindowActivated.connect(load); load()
    return dock


def _demo():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(); ax.plot([0, 1], [0, 1], "k-"); ax.plot([0, 1], [1, 0], color="tab:red"); ax.set_title("t")
    dark_canvas(fig)
    assert to_rgba(fig.patch.get_facecolor())[:3] == to_rgba(CANVAS_BG)[:3]
    assert to_rgba(ax.lines[0].get_color()) == to_rgba(INK) and to_rgba(ax.lines[1].get_color()) == to_rgba("tab:red")
    assert to_rgba(ax.title.get_color()) == to_rgba(INK)
    print("workspace ok")


if __name__ == "__main__":
    _demo()
