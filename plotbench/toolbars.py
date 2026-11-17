"""PlotBench toolbars on all four sides, drawn icons, and the light/dark theme switch.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Icons are drawn with QPainter at start-up, so no image files are shipped.
"""
from PySide6.QtCore import Qt, QPointF, QRectF, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QBrush, QPolygonF, QPalette, QFont, QAction
from PySide6.QtWidgets import QToolBar, QStyle, QApplication, QCheckBox

INK = {"light": QColor(40, 40, 40), "dark": QColor(225, 225, 225)}
C = [QColor("#1f77b4"), QColor("#ff7f0e"), QColor("#2ca02c"), QColor("#d62728"), QColor("#9467bd")]


def _icon(draw, theme="light", size=24):
    pm = QPixmap(size, size); pm.fill(Qt.transparent); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    draw(p, size, INK[theme]); p.end(); return QIcon(pm)


def _axes(p, s, ink):
    p.setPen(QPen(ink, 1.4)); p.drawLine(3, 3, 3, s - 3); p.drawLine(3, s - 3, s - 3, s - 3)


def _poly(p, pts, color, w=1.8):
    p.setPen(QPen(color, w)); p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))


def _dots(p, pts, color, r=1.8):
    p.setPen(QPen(color, 1.2)); p.setBrush(QBrush(color))
    for x, y in pts: p.drawEllipse(QPointF(x, y), r, r)


PTS = [(5, 17), (8, 12), (11, 14), (14, 8), (17, 10), (20, 5)]


def draw_plot(kind):
    """Small glyph for a plot type."""
    def d(p, s, ink):
        if kind in ("Pie",):
            p.setPen(QPen(ink, 1)); p.setBrush(C[0]); p.drawPie(QRectF(3, 3, 18, 18), 0, 120 * 16)
            p.setBrush(C[1]); p.drawPie(QRectF(3, 3, 18, 18), 120 * 16, 150 * 16); p.setBrush(C[2]); p.drawPie(QRectF(3, 3, 18, 18), 270 * 16, 90 * 16); return
        if kind == "Ternary":
            p.setPen(QPen(ink, 1.4)); p.setBrush(Qt.NoBrush); p.drawPolygon(QPolygonF([QPointF(3, 20), QPointF(21, 20), QPointF(12, 4)]))
            _dots(p, [(10, 15), (13, 12), (15, 16)], C[0], 1.5); return
        if kind in ("Polar (theta deg, r)", "Radar / Spider", "Wind Rose"):
            p.setPen(QPen(ink, 1)); p.setBrush(Qt.NoBrush); p.drawEllipse(QRectF(3, 3, 18, 18)); p.drawEllipse(QRectF(8, 8, 8, 8))
            _poly(p, [(12, 4), (19, 12), (12, 17), (6, 12), (12, 4)], C[0]); return
        _axes(p, s, ink)
        if kind in ("Line", "Step", "Semi-log Y (Line + Symbol)", "Waterfall (offset curves)", "Stacked Panels (shared X)", "Step (post, survival)"):
            _poly(p, PTS, C[0]); _poly(p, [(5, 20), (9, 17), (13, 18), (17, 14), (21, 13)], C[1]) if kind != "Line" else None
        elif kind in ("Scatter", "Bubble", "Color-mapped Scatter", "3D Scatter", "Q-Q Plot", "Bland-Altman"):
            _dots(p, PTS, C[0]); _dots(p, [(7, 19), (12, 17), (18, 13)], C[1])
        elif kind in ("Line + Symbol", "Error Bar", "Double-Y"):
            _poly(p, PTS, C[0], 1.4); _dots(p, PTS, C[0])
        elif kind in ("Column", "Stacked Column", "Pareto Chart", "Column + Error Bars", "Histogram", "Histogram + Normal Curve"):
            for i, h in enumerate((8, 13, 6, 16, 10)):
                p.fillRect(QRectF(5 + i * 3.4, s - 3 - h, 2.6, h), C[0] if kind != "Stacked Column" else C[i % 2])
            if "Normal" in kind or "Pareto" in kind: _poly(p, [(5, 15), (9, 9), (12, 5), (16, 9), (20, 15)], C[3], 1.4)
        elif kind == "Bar (horizontal)":
            for i, w in enumerate((12, 7, 16, 10)): p.fillRect(QRectF(4, 4 + i * 4, w, 3), C[0])
        elif kind in ("Area", "Stacked Area"):
            p.setPen(Qt.NoPen); p.setBrush(QColor(C[0].red(), C[0].green(), C[0].blue(), 150))
            p.drawPolygon(QPolygonF([QPointF(4, 20)] + [QPointF(x, y) for x, y in PTS] + [QPointF(20, 20)]))
        elif kind in ("Box", "Violin", "Box + Data Points"):
            p.setPen(QPen(C[0], 1.4)); p.setBrush(Qt.NoBrush)
            for cx, lo, hi in ((9, 8, 15), (16, 5, 12)): p.drawRect(QRectF(cx - 2.5, lo, 5, hi - lo)); p.drawLine(cx, lo - 3, cx, lo); p.drawLine(cx, hi, cx, hi + 3)
        elif kind in ("Contour (XYZ)", "Heat Map", "3D Surface", "2D Kernel Density", "Ternary Contour"):
            for i, col in enumerate((QColor("#440154"), QColor("#31688e"), QColor("#35b779"), QColor("#fde725"))):
                p.setPen(QPen(col, 1.6)); p.setBrush(Qt.NoBrush); p.drawEllipse(QPointF(13, 11), 8 - 2 * i, 6 - 1.5 * i)
        elif kind == "Piper Diagram":
            p.setPen(QPen(ink, 1.1)); p.setBrush(Qt.NoBrush)
            p.drawPolygon(QPolygonF([QPointF(3, 21), QPointF(10, 21), QPointF(6.5, 15)])); p.drawPolygon(QPolygonF([QPointF(14, 21), QPointF(21, 21), QPointF(17.5, 15)]))
            p.drawPolygon(QPolygonF([QPointF(12, 18), QPointF(16, 11), QPointF(12, 4), QPointF(8, 11)]))
        else: _poly(p, PTS, C[2])
    return d


def draw_tool(name):
    def d(p, s, ink):
        pen = QPen(ink, 1.6); p.setPen(pen); p.setBrush(Qt.NoBrush)
        if name == "zoom": p.drawEllipse(QRectF(4, 4, 11, 11)); p.drawLine(13, 13, 20, 20)
        elif name == "pan": p.drawLine(12, 3, 12, 21); p.drawLine(3, 12, 21, 12); [p.drawLine(*l) for l in ((12, 3, 9, 6), (12, 3, 15, 6), (12, 21, 9, 18), (12, 21, 15, 18))]
        elif name == "reader": p.drawLine(12, 3, 12, 21); p.drawLine(3, 12, 21, 12); p.drawEllipse(QRectF(8, 8, 8, 8))
        elif name == "region": p.fillRect(QRectF(8, 3, 8, 18), QColor(31, 119, 180, 90)); _poly(p, PTS, C[0])
        elif name == "text": f = QFont("Arial", 13, QFont.Bold); p.setFont(f); p.drawText(QRectF(2, 2, 20, 20), Qt.AlignCenter, "T")
        elif name == "arrow": p.drawLine(4, 20, 19, 5); p.drawLine(19, 5, 13, 6); p.drawLine(19, 5, 18, 11)
        elif name == "hline": p.setPen(QPen(ink, 1.6, Qt.DashLine)); p.drawLine(3, 12, 21, 12)
        elif name == "ellipse": p.drawEllipse(QRectF(3, 7, 18, 10)); _dots(p, [(8, 12), (12, 10), (16, 13)], C[0], 1.2)
        elif name == "fit": _dots(p, PTS, C[0], 1.5); _poly(p, [(4, 19), (21, 4)], C[3], 1.6)
        elif name == "peaks": _poly(p, [(3, 20), (7, 19), (9, 6), (11, 19), (14, 19), (16, 11), (18, 19), (21, 20)], C[0], 1.5)
        elif name == "stats": f = QFont("Arial", 11, QFont.Bold); p.setFont(f); p.drawText(QRectF(1, 1, 22, 22), Qt.AlignCenter, "x̅")
        elif name == "fft": _poly(p, [(3, 20), (6, 20), (7, 6), (8, 20), (13, 20), (14, 12), (15, 20), (21, 20)], C[1], 1.5)
        elif name == "smooth": _poly(p, [(3, 14), (6, 9), (9, 15), (12, 8), (15, 15), (18, 9), (21, 13)], QColor(150, 150, 150), 1); _poly(p, [(3, 13), (8, 11), (13, 12), (21, 11)], C[0], 2)
        elif name == "mask": p.fillRect(QRectF(4, 4, 16, 16), QColor(255, 205, 205)); p.setPen(QPen(QColor(170, 0, 0), 2)); p.drawLine(7, 7, 17, 17); p.drawLine(17, 7, 7, 17)
        elif name == "formula": f = QFont("Times New Roman", 12); f.setItalic(True); p.setFont(f); p.drawText(QRectF(0, 0, 24, 24), Qt.AlignCenter, "f(x)")
        elif name == "addcol": p.drawRect(QRectF(4, 4, 10, 16)); p.drawLine(18, 8, 18, 16); p.drawLine(14, 12, 22, 12)
        elif name == "sort": p.drawLine(7, 4, 7, 20); p.drawLine(7, 20, 4, 16); p.drawLine(7, 20, 10, 16); [p.drawLine(13, y, 13 + w, y) for y, w in ((6, 8), (11, 6), (16, 4))]
        elif name == "layout": [p.drawRect(QRectF(x, y, 8, 8)) for x in (3, 13) for y in (3, 13)]
        elif name == "matrix": [p.drawRect(QRectF(3 + 6 * i, 3 + 6 * j, 5, 5)) for i in range(3) for j in range(3)]
        elif name == "console": p.drawRect(QRectF(2, 4, 20, 16)); p.drawLine(5, 9, 9, 12); p.drawLine(9, 12, 5, 15); p.drawLine(11, 16, 17, 16)
        elif name == "digitize": p.drawRect(QRectF(3, 3, 18, 18)); p.setPen(QPen(C[3], 2)); p.drawLine(12, 7, 12, 17); p.drawLine(7, 12, 17, 12)
        elif name == "explorer": [p.drawLine(4, y, 20, y) for y in (6, 12, 18)]; [p.drawRect(QRectF(3, y - 1.5, 3, 3)) for y in (6, 12, 18)]
        elif name == "line": p.drawLine(4, 19, 20, 5)
        elif name == "rectshape": p.setBrush(QColor(31, 119, 180, 70)); p.drawRect(QRectF(4, 6, 16, 12))
        elif name == "circle": p.setBrush(QColor(31, 119, 180, 70)); p.drawEllipse(QRectF(3, 5, 18, 14))
        elif name == "polygon": p.setBrush(QColor(31, 119, 180, 70)); p.drawPolygon(QPolygonF([QPointF(4, 18), QPointF(9, 5), QPointF(20, 8), QPointF(17, 20)]))
        elif name == "freehand":
            p.setBrush(QBrush(QColor(31, 119, 180), Qt.BDiagPattern)); p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in ((4, 14), (6, 6), (12, 4), (19, 7), (20, 14), (14, 20), (7, 19))]))
        elif name == "curves":
            _poly(p, PTS, C[0]); p.setPen(QPen(ink, 1.2)); p.drawRect(QRectF(13, 13, 8, 8)); p.drawLine(14, 17, 16, 19); p.drawLine(16, 19, 20, 14)
        elif _vector(name, p, s, ink): pass
        elif name.startswith("txt:"):  # a short word as the icon (for commands without a drawing)
            t = name[4:]; f = QFont("Arial", 9 if len(t) <= 2 else 7 if len(t) <= 3 else 6, QFont.Bold); p.setFont(f)
            p.drawRoundedRect(QRectF(1.5, 3.5, 21, 17), 3, 3); p.drawText(QRectF(1, 3, 22, 18), Qt.AlignCenter, t)
        elif name == "props": p.drawEllipse(QRectF(7, 7, 10, 10)); [p.drawLine(12, 2, 12, 6), p.drawLine(12, 18, 12, 22), p.drawLine(2, 12, 6, 12), p.drawLine(18, 12, 22, 12)]
    return d


def _vector(name, p, s, ink):
    """Line icons (1.6 px strokes) for commands that used to show a text badge. Returns False for names it does not draw."""
    pen = QPen(ink, 1.6); pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin); p.setPen(pen); p.setBrush(Qt.NoBrush)
    L = lambda *xy: p.drawPolyline(QPolygonF([QPointF(xy[k], xy[k + 1]) for k in range(0, len(xy), 2)]))
    blue, red, green = C[0], C[3], C[2]
    if name == "zoomin": p.drawEllipse(QRectF(3, 3, 13, 13)); L(14.5, 14.5, 21, 21); L(6.5, 9.5, 12.5, 9.5); L(9.5, 6.5, 9.5, 12.5)
    elif name == "zoomout": p.drawEllipse(QRectF(3, 3, 13, 13)); L(14.5, 14.5, 21, 21); L(6.5, 9.5, 12.5, 9.5)
    elif name == "fitview":
        for a, b, c, d in ((3, 8, 3, 3), (3, 3, 8, 3), (16, 3, 21, 3), (21, 3, 21, 8), (21, 16, 21, 21), (21, 21, 16, 21), (8, 21, 3, 21), (3, 21, 3, 16)): L(a, b, c, d)
        _poly(p, [(6, 17), (10, 11), (13, 13), (18, 7)], blue, 1.6)
    elif name == "draw_arrow": L(4, 20, 19, 5); p.setBrush(ink); p.drawPolygon(QPolygonF([QPointF(20, 4), QPointF(12, 7), QPointF(17, 12)]))
    elif name == "nlfit": _dots(p, [(4, 18), (8, 12), (12, 9), (16, 9), (20, 13)], C[0], 1.5); _poly(p, [(3, 20), (7, 12), (12, 8), (17, 9), (21, 15)], red, 1.6)
    elif name in ("copy", "clip"):
        p.drawRoundedRect(QRectF(8, 3, 12, 14), 2, 2); p.drawRoundedRect(QRectF(4, 7, 12, 14), 2, 2)
        if name == "clip": _poly(p, [(6, 18), (9, 14), (11, 16), (14, 11)], blue, 1.4)
    elif name == "paste":
        p.drawRoundedRect(QRectF(4, 5, 16, 17), 2, 2); p.setBrush(ink); p.drawRoundedRect(QRectF(8, 2.5, 8, 4), 1, 1); p.setBrush(Qt.NoBrush)
        L(8, 12, 16, 12); L(8, 16, 14, 16)
    elif name == "rows": p.drawRect(QRectF(3, 4, 13, 16)); [L(3, y, 16, y) for y in (8, 12, 16)]; L(19, 9, 19, 17); L(15, 13, 23, 13)
    elif name == "image":
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2, 2); p.drawEllipse(QPointF(8, 9.5), 1.6, 1.6); _poly(p, [(4, 18), (10, 12), (14, 15), (17, 12), (20, 15)], blue, 1.4)
    elif name == "search": p.drawEllipse(QRectF(4, 4, 11, 11)); L(13.5, 13.5, 20, 20)
    elif name == "dup": p.drawRect(QRectF(3, 7, 12, 12)); p.drawRect(QRectF(9, 3, 12, 12)); _poly(p, [(11, 12), (14, 8), (17, 10), (20, 5)], blue, 1.3)
    elif name == "pdf":
        L(5, 3, 15, 3, 19, 7, 19, 21, 5, 21, 5, 3); L(15, 3, 15, 7, 19, 7); p.setFont(QFont("Arial", 6, QFont.Bold)); p.setPen(red)
        p.drawText(QRectF(4, 10, 16, 9), Qt.AlignCenter, "PDF")
    elif name == "template": p.drawRect(QRectF(3, 3, 18, 18)); L(3, 8, 21, 8); L(9, 8, 9, 21); p.fillRect(QRectF(10, 10, 10, 10), QColor(31, 119, 180, 60))
    elif name == "brush": L(20, 4, 11, 13); p.setBrush(C[1]); p.drawEllipse(QRectF(5, 13, 7, 7))
    elif name == "group": _dots(p, [(6, 8), (9, 6), (8, 11)], C[0], 1.8); _dots(p, [(16, 15), (19, 18), (15, 19)], C[1], 1.8); _dots(p, [(17, 6), (20, 9)], C[2], 1.8)
    elif name == "panels": p.drawRect(QRectF(3, 3, 18, 18)); L(3, 12, 21, 12); _poly(p, [(5, 10), (9, 6), (13, 8), (19, 5)], blue, 1.3); _poly(p, [(5, 19), (9, 16), (14, 18), (19, 14)], C[1], 1.3)
    elif name == "edit": L(5, 19, 6, 15, 17, 4, 20, 7, 9, 18, 5, 19); L(15, 6, 18, 9)
    elif name == "inset": p.drawRect(QRectF(3, 3, 18, 18)); p.drawRect(QRectF(5, 13, 6, 6)); p.drawRect(QRectF(12, 5, 8, 8)); p.setPen(QPen(ink, 1, Qt.DotLine)); L(11, 13, 12, 13); L(11, 19, 20, 13)
    elif name == "corr":
        for i in range(3):
            for j in range(3): p.fillRect(QRectF(4 + 5.5 * i, 4 + 5.5 * j, 5, 5), QColor(214, 39, 40, 200) if i == j else QColor(31, 119, 180, 60 + 50 * abs(i - j)))
    elif name == "ttest": _poly(p, [(2, 19), (6, 17), (9, 7), (12, 17), (15, 19)], C[0], 1.5); _poly(p, [(9, 19), (13, 17), (16, 7), (19, 17), (22, 19)], C[1], 1.5)
    elif name == "anova":
        for k, (x, lo, hi) in enumerate(((6, 9, 17), (12, 6, 13), (18, 11, 19))): p.setPen(QPen(C[k], 1.6)); p.drawRect(QRectF(x - 2.5, lo, 5, hi - lo))
    elif name == "pca":
        _dots(p, [(7, 15), (10, 12), (13, 14), (15, 9), (9, 17)], QColor(150, 150, 150), 1.2); p.setPen(QPen(red, 1.6))
        L(12, 12, 20, 5); L(12, 12, 4, 6); L(20, 5, 16, 5.5); L(20, 5, 19, 9)
    elif name == "cluster":
        p.setPen(QPen(C[0], 1.2)); p.drawEllipse(QRectF(2, 3, 10, 10)); p.setPen(QPen(C[1], 1.2)); p.drawEllipse(QRectF(11, 11, 11, 10))
        _dots(p, [(5, 7), (8, 9), (7, 6)], C[0], 1.4); _dots(p, [(15, 15), (18, 17), (16, 18)], C[1], 1.4)
    elif name == "bell": _poly(p, [(2, 20), (6, 18), (9, 11), (12, 5), (15, 11), (18, 18), (22, 20)], C[0], 1.6); L(12, 5, 12, 20)
    elif name == "deriv": _poly(p, [(3, 18), (8, 14), (13, 12), (21, 4)], C[0], 1.5); p.setPen(QPen(red, 1.4)); L(5, 20, 20, 7)
    elif name == "integral":
        p.setPen(Qt.NoPen); p.setBrush(QColor(31, 119, 180, 90)); p.drawPolygon(QPolygonF([QPointF(5, 20), QPointF(5, 13), QPointF(10, 8), QPointF(15, 10), QPointF(20, 6), QPointF(20, 20)]))
        _poly(p, [(3, 15), (5, 13), (10, 8), (15, 10), (20, 6), (22, 5)], C[0], 1.5)
    elif name == "baseline": _poly(p, [(2, 17), (6, 16), (9, 5), (12, 15), (16, 14), (18, 9), (20, 14), (22, 13)], C[0], 1.4); p.setPen(QPen(red, 1.4, Qt.DashLine)); L(2, 18, 22, 14)
    elif name == "peakfind": _poly(p, [(2, 20), (7, 19), (9, 7), (11, 19), (14, 19), (16, 11), (18, 19), (22, 20)], C[0], 1.4); p.setPen(QPen(red, 1.4)); L(9, 2, 9, 5); L(16, 6, 16, 9)
    elif name == "crystal":
        p.setBrush(QColor(44, 160, 44, 60)); p.drawPolygon(QPolygonF([QPointF(12, 2), QPointF(19, 7), QPointF(19, 16), QPointF(12, 22), QPointF(5, 16), QPointF(5, 7)]))
        L(5, 7, 12, 11, 19, 7); L(12, 11, 12, 22)
    elif name == "norm":
        for k, (h, c) in enumerate(((13, C[0]), (8, C[1]), (5, C[2]), (3, C[3]))): p.fillRect(QRectF(4 + 4.5 * k, 20 - h, 3.5, h), c)
        L(3, 20, 21, 20)
    elif name == "hundred": p.drawEllipse(QRectF(3, 3, 18, 18)); p.setPen(Qt.NoPen); p.setBrush(C[0]); p.drawPie(QRectF(3, 3, 18, 18), 90 * 16, -250 * 16)
    elif name == "thermo":
        p.drawRoundedRect(QRectF(9.5, 2.5, 5, 14), 2.5, 2.5); p.setBrush(red); p.setPen(QPen(red, 1)); p.drawEllipse(QRectF(8, 14.5, 8, 8)); p.drawRect(QRectF(11, 8, 2, 8))
        p.setPen(QPen(ink, 1.2)); [L(16, y, 19, y) for y in (5, 8, 11)]
    elif name == "ptdiag": L(4, 3, 4, 20, 21, 20); _poly(p, [(5, 17), (11, 12), (20, 4)], red, 1.5); _poly(p, [(5, 6), (12, 11), (20, 18)], C[0], 1.5); _dots(p, [(11.5, 11.5)], ink, 2)
    elif name == "clock": p.drawEllipse(QRectF(3, 3, 18, 18)); L(12, 6, 12, 12, 16, 15)
    elif name == "feti":
        p.setBrush(QColor(60, 60, 60, 160)); p.drawPolygon(QPolygonF([QPointF(3, 12), QPointF(8, 4), QPointF(13, 12), QPointF(8, 20)]))
        p.setBrush(QColor(180, 90, 40, 140)); p.drawPolygon(QPolygonF([QPointF(11, 7), QPointF(21, 7), QPointF(21, 17), QPointF(11, 17)]))
    elif name == "tas":
        L(3, 3, 3, 21, 21, 21); p.setPen(QPen(ink, 1.1)); L(6, 21, 6, 15, 11, 12, 15, 8, 20, 4); L(11, 21, 11, 12); L(15, 21, 15, 8); _dots(p, [(9, 17), (13, 14)], C[0], 1.4)
    elif name == "harker": L(3, 3, 3, 21, 21, 21); _dots(p, [(6, 7), (10, 9), (14, 12), (18, 15)], C[0], 1.4); _dots(p, [(6, 17), (10, 15), (14, 14), (18, 11)], C[1], 1.4)
    elif name == "tern": p.drawPolygon(QPolygonF([QPointF(3, 20), QPointF(21, 20), QPointF(12, 4)])); p.setPen(QPen(ink, 0.9)); L(7.5, 12, 16.5, 12); L(12, 20, 12, 12)
    elif name == "spider": L(3, 3, 3, 21, 21, 21); _poly(p, [(5, 6), (8, 9), (10, 7), (13, 12), (15, 10), (17, 14), (20, 15)], C[0], 1.4); _poly(p, [(5, 11), (8, 13), (10, 12), (13, 16), (15, 15), (20, 18)], C[1], 1.4)
    elif name == "concordia": L(3, 3, 3, 21, 21, 21); _poly(p, [(4, 20), (8, 16), (12, 11), (16, 7), (20, 4)], red, 1.5); p.setPen(QPen(C[0], 1.2)); p.drawEllipse(QRectF(10, 10, 5, 3.5))
    elif name == "isochron": L(3, 3, 3, 21, 21, 21); _poly(p, [(4, 19), (21, 5)], red, 1.4); _dots(p, [(6, 17), (10, 14), (14, 11), (18, 7.5)], C[0], 1.6)
    elif name == "wmean":
        p.setPen(QPen(red, 1.2, Qt.DashLine)); L(2, 12, 22, 12); p.setPen(QPen(C[0], 2.4))
        for x, lo, hi in ((5, 7, 16), (9, 9, 15), (13, 8, 17), (17, 10, 14), (20, 6, 15)): L(x, lo, x, hi)
    elif name == "kde":
        p.setPen(Qt.NoPen); p.setBrush(QColor(31, 119, 180, 70))
        for x, h in ((5, 4), (8, 9), (11, 6), (15, 12), (18, 5)): p.drawRect(QRectF(x - 1.4, 20 - h, 2.8, h))
        _poly(p, [(2, 20), (5, 17), (8, 11), (11, 15), (15, 7), (18, 15), (22, 20)], red, 1.4)
    elif name == "smatrix":
        for i in range(2):
            for j in range(2): p.drawRect(QRectF(3 + 9.5 * i, 3 + 9.5 * j, 8.5, 8.5)); _dots(p, [(6 + 9.5 * i, 9 + 9.5 * j), (8 + 9.5 * i, 7 + 9.5 * j), (10 + 9.5 * i, 5 + 9.5 * j)], C[i + j], 1.0); p.setPen(pen)
    elif name == "discrim": L(3, 3, 3, 21, 21, 21); p.setPen(QPen(ink, 1.1)); L(4, 14, 12, 9, 21, 9); L(12, 9, 12, 3); _dots(p, [(7, 17), (15, 6), (17, 15)], C[0], 1.4)
    else: return False
    return True


class ThemeSwitch(QCheckBox):
    """A labelled toggle in the toolbar: unchecked = light, checked = dark."""

    def __init__(self, parent=None):
        super().__init__("Dark", parent); self.setToolTip("Switch between the light and dark theme")


def apply_theme(app, theme):
    """Fusion palette for the whole window. Graphs keep their own (white, publication) background unless styled."""
    app.setStyle("Fusion")
    # Qt 6 follows the Windows light/dark setting by default; pin the scheme so our choice wins over the system's
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"): hints.setColorScheme(Qt.ColorScheme.Dark if theme == "dark" else Qt.ColorScheme.Light)
    dark = theme == "dark"
    c = (dict(window=(45, 45, 48), base=(30, 30, 32), alt=(40, 40, 44), text=(225, 225, 225), button=(52, 52, 56), tip=(30, 30, 32),
              disabled=(125, 125, 125), placeholder=(140, 140, 140), link=(90, 170, 255), grid="#55575c", header=(58, 58, 62))
         if dark else
         dict(window=(243, 243, 243), base=(255, 255, 255), alt=(246, 248, 252), text=(20, 20, 20), button=(240, 240, 240), tip=(255, 255, 220),
              disabled=(150, 150, 150), placeholder=(130, 130, 130), link=(0, 90, 200), grid="#c9ccd1", header=(236, 238, 242)))
    pal = QPalette(); col = lambda k: QColor(*c[k])
    for role, key in ((QPalette.Window, "window"), (QPalette.WindowText, "text"), (QPalette.Base, "base"), (QPalette.AlternateBase, "alt"),
                      (QPalette.ToolTipBase, "tip"), (QPalette.ToolTipText, "text"), (QPalette.Text, "text"), (QPalette.Button, "button"),
                      (QPalette.ButtonText, "text"), (QPalette.Link, "link"), (QPalette.PlaceholderText, "placeholder")):
        pal.setColor(role, col(key))
    pal.setColor(QPalette.BrightText, QColor(255, 80, 80)); pal.setColor(QPalette.Highlight, QColor(42, 130, 218))
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText): pal.setColor(QPalette.Disabled, role, col("disabled"))
    app.setPalette(pal)
    h = "rgb({},{},{})".format(*c["header"])
    from .ui_style import qss
    app.setStyleSheet(qss(theme))  # modern widgets; also gives the tables visible grid lines in both themes


def build_toolbars(main, theme="light"):
    """Top: file/edit/export. Left: graph tools. Bottom: plot types. Right: worksheet, analysis and window tools."""
    for tb in getattr(main, "side_bars", []): main.removeToolBar(tb); tb.deleteLater()
    st = main.style(); bars = []

    def bar(title, area, name):
        tb = QToolBar(title, main); tb.setObjectName(name); tb.setIconSize(QSize(22, 22)); tb.setMovable(True)
        main.addToolBar(area, tb); bars.append(tb); return tb

    def add(tb, icon, tip, slot):
        a = QAction(icon, tip, main); a.setToolTip(tip); a.triggered.connect(lambda checked=False: main.safe(slot)); tb.addAction(a); return a

    top = bar("File and edit", Qt.TopToolBarArea, "tb_top")
    from .startpage import app_icon
    add(top, app_icon(), "Start page", main.show_start)
    g = add(top, _icon(draw_plot("Scatter"), theme), "Plot Gallery: all plot types with previews (Ctrl+Shift+G)", main.show_gallery)
    g.setText("Plot"); top.addSeparator()
    for sp, tip, slot in ((QStyle.SP_FileIcon, "New workbook", main.new_book), (QStyle.SP_DirOpenIcon, "Open project", main.open_project),
                          (QStyle.SP_DialogSaveButton, "Save project", main.save_project), (QStyle.SP_ArrowDown, "Import Wizard", main.import_wizard),
                          (QStyle.SP_DriveFDIcon, "Export graph", main.export_graph), (QStyle.SP_ArrowBack, "Undo", main.undo),
                          (QStyle.SP_ArrowForward, "Redo", main.redo), (QStyle.SP_BrowserReload, "Refresh graphs", main.refresh_all)):
        add(top, st.standardIcon(sp), tip, slot)
    top.addSeparator(); add(top, _icon(draw_tool("matrix"), theme), "New matrixbook", main.new_matrix_dialog)
    add(top, _icon(draw_tool("layout"), theme), "New layout page", main.new_layout)
    add(top, _icon(draw_tool("console"), theme), "Python console", lambda: main.console_dock.setVisible(not main.console_dock.isVisible()))
    add(top, _icon(draw_tool("explorer"), theme), "Project Explorer", lambda: main.explorer_dock.setVisible(not main.explorer_dock.isVisible()))
    top.addSeparator()
    for ic, tip, slot in (("copy", "Copy cells", lambda: main.need_book() and main.need_book().copy()),
                          ("paste", "Paste cells", lambda: main.need_book() and main.need_book().paste()),
                          ("addcol", "Add column", lambda: main.need_book() and main.need_book().add_column()),
                          ("rows", "Add 100 rows", lambda: main.need_book() and main.need_book().add_rows(100)),
                          ("formula", "Set column values (formula)", main.col_formula), ("curves", "Plot details: show / hide curves, fill", main.plot_details),
                          ("props", "Graph properties", main.graph_props), ("image", "Export graph image", main.export_graph),
                          ("clip", "Copy graph to clipboard", main.copy_graph), ("search", "Search commands (Ctrl+K)", main.search_commands)):
        add(top, _icon(draw_tool(ic), theme), tip, slot)
    top.addSeparator(); top.addWidget(_search_box(main))
    top.addSeparator(); sw = ThemeSwitch(main); sw.setChecked(theme == "dark"); sw.toggled.connect(lambda on: main.set_theme("dark" if on else "light"))
    top.addWidget(sw); main.theme_switch = sw

    left = bar("Graph tools", Qt.LeftToolBarArea, "tb_left")

    def graph_toggle(attr):
        g = main.need_graph()
        if g: getattr(g, attr).toggle()

    def nav(mode):
        g = main.need_graph()
        if g:
            tb = getattr(g, "nav", None); getattr(tb, mode)() if tb is not None and hasattr(tb, mode) else None

    for ic, tip, slot in (("zoom", "Zoom (on the active graph)", lambda: nav("zoom")), ("pan", "Pan (on the active graph)", lambda: nav("pan")),
                          ("reader", "Data reader", lambda: graph_toggle("act_reader")), ("region", "Region tools: drag an X range", lambda: graph_toggle("act_region")),
                          ("text", "Add text", main.add_text), ("arrow", "Add arrow", main.add_arrow), ("hline", "Add reference line", main.add_refline),
                          ("ellipse", "Add confidence ellipse", main.add_ellipse), ("props", "Graph properties", main.graph_props),
                          ("digitize", "Digitizer", main.digitize), ("edit", "Edit plot (type, columns, groups, panels)", main.edit_plot),
                          ("inset", "Add zoom inset (drag a rectangle)", main.zoom_inset), ("group", "Group samples by a column", main.group_samples),
                          ("panels", "Split into panels", main.split_panels), ("template", "Apply template / theme", main.apply_template),
                          ("dup", "Duplicate graph", main.dup_graph), ("pdf", "Export all graphs to one PDF", main.export_pdf_book), ("brush", "Copy this graph's format to all graphs", main.copy_format_all)):
        add(left, _icon(draw_tool(ic), theme), tip, slot)
    left.addSeparator()
    for ic, tip, kind in (("line", "Draw a line", "line"), ("draw_arrow", "Draw an arrow (head, colour and width editable)", "arrow2"), ("rectshape", "Draw a rectangle", "rect"),
                          ("circle", "Draw a circle / ellipse", "circle"), ("polygon", "Draw a polygon (click corners, double-click to finish)", "polygon"),
                          ("freehand", "Draw a freehand region", "region")):
        add(left, _icon(draw_tool(ic), theme), tip, lambda k=kind: main.draw_shape(k))

    bottom = bar("Plot types", Qt.BottomToolBarArea, "tb_bottom")
    add(bottom, _icon(draw_plot("Contour (XYZ)"), theme), "Colour-mapped scatter (third column as colour, with a colour bar)", lambda: main.plot("Color-mapped Scatter"))
    for kind in ("Line", "Scatter", "Line + Symbol", "Column", "Bar (horizontal)", "Stacked Column", "Area", "Histogram", "Box", "Violin", "Pie",
                 "Error Bar", "Double-Y", "Bubble", "Polar (theta deg, r)", "Contour (XYZ)", "Heat Map", "3D Scatter", "3D Surface", "Ternary",
                 "Piper Diagram", "Radar / Spider", "Waterfall (offset curves)", "Q-Q Plot", "Bland-Altman", "Box + Data Points"):
        add(bottom, _icon(draw_plot(kind), theme), f"Plot: {kind}", lambda k=kind: main.plot(k))
    bottom.addSeparator()
    for ic, kind in (("tas", "TAS (SiO2 vs Na2O+K2O)"), ("harker", "Harker Diagrams (oxides vs SiO2)"), ("tern", "AFM (Irvine & Baragar)"),
                     ("spider", "Spider: REE / CI Chondrite"), ("spider", "Spider: Multi-element / Primitive Mantle"), ("tern", "QAP (Streckeisen)"),
                     ("discrim", "Shand A/CNK vs A/NK"), ("discrim", "Frost: Fe-number vs SiO2"), ("tern", "Pyroxene Quadrilateral (Wo-En-Fs)"),
                     ("tern", "Feldspar Ternary (An-Ab-Or)"), ("discrim", "Pearce Granite: Rb vs Y+Nb"), ("concordia", "Concordia (Wetherill)"),
                     ("isochron", "Isochron (York regression)"), ("wmean", "Weighted Mean (ages)"), ("kde", "Detrital Age KDE + PDP"),
                     ("txt:Rc", "Raincloud (violin + box + points)"), ("pca", "PCA Biplot (scores + loadings)"), ("smatrix", "Scatter Matrix")):
        add(bottom, _icon(draw_plot("Violin") if ic == "txt:Rc" else draw_tool(ic), theme), f"Plot: {kind}", lambda k=kind: main.plot(k))

    right = bar("Worksheet and analysis", Qt.RightToolBarArea, "tb_right")
    for ic, tip, slot in (("addcol", "Add column", lambda: main.need_book() and main.need_book().add_column()),
                          ("formula", "Set column values (formula)", main.col_formula), ("sort", "Sort by several columns", main.ws_sort),
                          ("mask", "Mask selected cells", lambda: main.need_book() and main.need_book().set_mask(main.need_book().selected_cells(), True)),
                          ("stats", "Descriptive statistics", main.desc), ("fit", "Linear fit", lambda: main.fit_poly(1)),
                          ("nlfit", "Nonlinear curve fit", main.fit_nl), ("peaks", "Peak Analyzer", main.peak_analyzer),
                          ("smooth", "Smooth", main.smooth), ("fft", "FFT", main.fft),
                          ("corr", "Correlation matrix", main.corr), ("ttest", "Two-sample t-test", main.t2), ("anova", "One-way ANOVA", main.anova1),
                          ("pca", "Principal component analysis (with score, loading and biplot graphs)", main.pca),
                          ("cluster", "K-means clustering", main.kmeans), ("bell", "Normality test", main.normality),
                          ("deriv", "Differentiate", lambda: main.xy_op("d/dx", __import__("plotbench.analysis", fromlist=["derivative"]).derivative)),
                          ("integral", "Integrate", main.integ), ("baseline", "Baseline (ALS) and subtract", main.baseline),
                          ("peakfind", "Find peaks", main.peaks), ("crystal", "Mineral formula from oxides", main.mineral_formula),
                          ("norm", "CIPW norm", main.cipw_norm), ("hundred", "Normalise oxides to 100% (volatile-free)", main.volatile_free),
                          ("thermo", "Thermobarometry", main.thermobarometry), ("ptdiag", "Coupled P-T solver", main.pt_solver),
                          ("feti", "Fe-Ti oxide thermometer / oxybarometer (Ghiorso & Evans 2008)", main.fe_ti_oxides),
                          ("clock", "U-Pb ages and discordance of each analysis", main.upb_ages),
                          ("isochron", "Isochron age (York regression)", main.isochron_report)):
        add(right, _icon(draw_tool(ic), theme), tip, slot)
    for tb in bars: _customisable(main, tb, theme)
    if (getattr(main, "settings", None) or {}).get("toolbar_layout", "ribbon") == "ribbon": bars.append(_ribbon(main, bars, theme))
    main.side_bars = bars
    return bars


def _search_box(main):
    """'Search commands (Ctrl+K)' field: type a few words, Enter opens the command search with them."""
    from PySide6.QtWidgets import QLineEdit
    e = QLineEdit(); e.setPlaceholderText("Search commands, plots, thermometers (Ctrl+K)"); e.setClearButtonEnabled(True); e.setMaximumWidth(300)
    e.setMinimumWidth(200); e.setToolTip("Type e.g. 'baseline', 'ternary', 'titanite', then Enter")
    e.returnPressed.connect(lambda: (main.safe(lambda: main.search_commands(e.text().strip() or None)), e.clear())); main.search_box = e
    return e


PETRO = ("mineral", "cipw", "oxide", "thermo", "p-t", "fe-ti", "isochron", "u-pb", "age")


def _ribbon(main, bars, theme):
    """Ribbon layout (the default; View > Ribbon Toolbar Layout): the top, bottom and right bars become four tabs, Home, Plot,
    Analysis and Petrology & Geochem, with short labels under the icons; the canvas tools stay on the left bar."""
    from PySide6.QtWidgets import QTabWidget, QWidgetAction, QWidget, QHBoxLayout
    top, left, bottom, right = bars[:4]
    rib = QToolBar("Ribbon", main); rib.setObjectName("tb_ribbon"); rib.setMovable(False); main.addToolBar(Qt.TopToolBarArea, rib)
    tabs = QTabWidget(); tabs.setDocumentMode(True)
    acts = lambda tb: [a for a in tb.actions() if not isinstance(a, QWidgetAction)]
    petro = [a for a in acts(right) if any(k in (a.toolTip() or "").lower() for k in PETRO)]
    pages = (("Home", acts(top)), ("Plot", acts(bottom)), ("Analysis", [a for a in acts(right) if a not in petro]),
             ("Petrology && Geochem", petro))
    for title, al in pages:
        page = QToolBar(); page.setIconSize(QSize(24, 24)); page.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        for a in al:
            if not a.iconText() or a.iconText() == a.text() and len(a.text()) > 12: a.setIconText(_short(a.toolTip() or a.text()))
        page.addActions(al); tabs.addTab(page, title)
    corner = QWidget(); h = QHBoxLayout(corner); h.setContentsMargins(0, 0, 6, 0); h.addWidget(_search_box(main))
    sw = ThemeSwitch(main); sw.setChecked(theme == "dark"); sw.toggled.connect(lambda on: main.set_theme("dark" if on else "light")); h.addWidget(sw)
    main.theme_switch = sw; tabs.setCornerWidget(corner)
    i = int((main.settings or {}).get("ribbon_tab", 0)); tabs.setCurrentIndex(i if 0 <= i < tabs.count() else 0)
    tabs.currentChanged.connect(lambda k: main.settings.__setitem__("ribbon_tab", k))
    rib.addWidget(tabs)
    for tb in (top, bottom, right): tb.setVisible(False)  # the canvas tools (zoom, pan, shapes) stay on the left on every tab
    return rib


def _short(tip):
    """One- or two-word label under a ribbon button, from its tooltip."""
    w = [x for x in tip.replace("&", "").split("(")[0].replace("...", "").replace("…", "").split() if x]
    return " ".join(w[:2]) if len(" ".join(w[:2])) <= 14 else w[0][:12]


def _all_commands(main):
    """{menu path: QAction} of every command in the menu bar (for adding buttons to toolbars)."""
    out = {}

    def walk(menu, path):
        for a in menu.actions():
            if a.menu() is not None: walk(a.menu(), path + [a.text().replace("&", "")])
            elif a.text() and not a.isSeparator() and a.isEnabled(): out[" > ".join(path + [a.text().replace("&", "")])] = a
    for a in main.menuBar().actions():
        if a.menu() is not None: walk(a.menu(), [a.text().replace("&", "")])
    return out


def _abbr(text):
    w = [x for x in text.replace("(", " ").replace("/", " ").split() if x[:1].isalpha()]
    return ("".join(x[0] for x in w[:3]).upper() or text[:3]) if len(w) > 1 else text[:4]


def _customisable(main, tb, theme):
    """Every toolbar ends in a menu, as in Origin: tick buttons to show or hide them, add any menu command as a button, reset.
    The choice is saved in the settings (toolbars -> name -> hidden / extra)."""
    from PySide6.QtWidgets import QToolButton, QMenu, QInputDialog, QWidgetAction
    name = tb.objectName(); allcfg = main.settings.setdefault("toolbars", {}); cfg = allcfg.setdefault(name, {"hidden": [], "extra": []})
    cmds = None
    for path in list(cfg.get("extra", [])):
        if cmds is None: cmds = _all_commands(main)
        a = cmds.get(path)
        if a is None: continue
        b = QAction(_icon(draw_tool("txt:" + _abbr(path.split(" > ")[-1])), theme), path.split(" > ")[-1], main)
        b.setToolTip(path); b.triggered.connect(a.trigger); tb.addAction(b)
    for a in tb.actions():
        if (a.toolTip() or a.text()) in cfg.get("hidden", []): a.setVisible(False)

    def save():
        from .app import save_settings
        save_settings(main.settings)

    def rebuild(): build_toolbars(main, theme)

    btn = QToolButton(tb); btn.setText("»"); btn.setToolTip("Add or Remove Buttons"); btn.setPopupMode(QToolButton.InstantPopup)
    menu = QMenu(btn); btn.setMenu(menu)

    def fill():
        menu.clear(); sub = menu.addMenu("Add or Remove Buttons")
        for a in tb.actions():
            if a.isSeparator() or isinstance(a, QWidgetAction): continue  # widgets (theme switch, this menu) stay
            label = a.toolTip() or a.text()
            if not label or a.text() == "»": continue
            t = sub.addAction(label); t.setCheckable(True); t.setChecked(a.isVisible())

            def flip(on, a=a, label=label):
                a.setVisible(on); h = cfg.setdefault("hidden", [])
                if on and label in h: h.remove(label)
                elif not on and label not in h: h.append(label)
                save()
            t.toggled.connect(flip)
        menu.addSeparator()

        def add_cmd():
            names = sorted(_all_commands(main))
            pick, ok = QInputDialog.getItem(main, "Add a button", f"Command to add to the '{tb.windowTitle()}' toolbar:", names, 0, True)
            if ok and pick in names: cfg.setdefault("extra", []).append(pick); save(); rebuild()
        menu.addAction("Add a command as a button...", add_cmd)
        if cfg.get("extra"):
            rm = menu.addMenu("Remove an added button")
            for path in list(cfg["extra"]):
                rm.addAction(path, lambda p=path: (cfg["extra"].remove(p), save(), rebuild()))
        menu.addSeparator()
        menu.addAction("Reset this toolbar", lambda: (allcfg.pop(name, None), save(), rebuild()))
    menu.aboutToShow.connect(fill); tb.addWidget(btn)
