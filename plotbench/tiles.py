"""Uniform picture tiles for icon grids (Plot Gallery, Start page). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Every tile has the same size; the picture is centred in a fixed frame, the caption wraps to at most two lines, and the
hover/selection highlight is a rounded rectangle drawn inside the tile, so nothing spills into its neighbours."""
from PySide6.QtCore import Qt, QSize, QRect, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFontMetrics, QTextOption
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QListView, QListWidget

ACCENT = QColor("#1f8f86")


class TileDelegate(QStyledItemDelegate):
    def __init__(self, parent, picture=QSize(150, 112), caption_lines=2):
        super().__init__(parent); self.pic = picture; self.lines = caption_lines

    def tile_size(self, fm=None):
        """Room for the picture plus the caption in the largest font it is drawn with (bold, style-sheet size)."""
        from PySide6.QtGui import QFont
        f = QFont("Segoe UI"); f.setPointSizeF(10.5); f.setBold(True); fm = QFontMetrics(f)
        return QSize(self.pic.width() + 34, self.pic.height() + 30 + fm.lineSpacing() * self.lines + 12)

    def sizeHint(self, option, index): return self.tile_size()

    def paint(self, p, option, index):
        p.save(); p.setRenderHint(QPainter.Antialiasing)
        pal = option.palette; dark = pal.window().color().lightness() < 128
        r = QRectF(option.rect).adjusted(5, 5, -5, -5)
        selected, hover = bool(option.state & QStyle.State_Selected), bool(option.state & QStyle.State_MouseOver)
        if selected or hover:
            fill = QColor(ACCENT); fill.setAlpha(60 if selected else 22)
            p.setPen(QPen(ACCENT if selected else QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), 90), 1.6 if selected else 1))
            p.setBrush(fill); p.drawRoundedRect(r, 9, 9)
        frame = QRectF(r.center().x() - self.pic.width() / 2 - 3, r.top() + 8, self.pic.width() + 6, self.pic.height() + 6)
        p.setPen(QPen(QColor("#3d4046") if dark else QColor("#dfe2e7"), 1)); p.setBrush(QColor("white")); p.drawRoundedRect(frame, 6, 6)
        icon = index.data(Qt.DecorationRole)
        if icon is not None and not icon.isNull():
            dpr = p.device().devicePixelRatioF() if p.device() else 1.0  # sharp and full size on high-DPI screens
            pm = icon.pixmap(self.pic, dpr).scaled(self.pic * dpr, Qt.KeepAspectRatio, Qt.SmoothTransformation); pm.setDevicePixelRatio(dpr)
            sz = pm.deviceIndependentSize()
            p.drawPixmap(int(frame.center().x() - sz.width() / 2), int(frame.center().y() - sz.height() / 2), pm)
        text_rect = QRectF(r.left() + 4, frame.bottom() + 6, r.width() - 8, r.bottom() - frame.bottom() - 8)
        fm = QFontMetrics(option.font); words = str(index.data(Qt.DisplayRole) or ""); text = self._two_lines(words, fm, int(text_rect.width()))
        fg = index.data(Qt.ForegroundRole)  # greyed tiles (e.g. plot types the selection cannot make)
        p.setPen(fg.color() if fg is not None and hasattr(fg, "color") else pal.text().color()); f = option.font
        if selected: f.setBold(True)
        p.setFont(f); opt = QTextOption(Qt.AlignHCenter | Qt.AlignTop); opt.setWrapMode(QTextOption.WordWrap); p.drawText(text_rect, text, opt)
        p.restore()

    def _two_lines(self, text, fm, width):
        """Wrap to at most self.lines lines; elide the last one if needed."""
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if fm.horizontalAdvance(trial) <= width or not cur: cur = trial
            else: lines.append(cur); cur = w
        if cur: lines.append(cur)
        if len(lines) > self.lines: lines = lines[:self.lines - 1] + [fm.elidedText(" ".join(lines[self.lines - 1:]), Qt.ElideRight, width)]
        return "\n".join(fm.elidedText(l, Qt.ElideRight, width) for l in lines)


def make_tile_grid(picture=QSize(150, 112), lines=2):
    """A QListWidget in icon mode with uniform tiles."""
    g = QListWidget(); g.setViewMode(QListView.IconMode); g.setMovement(QListView.Static); g.setResizeMode(QListView.Adjust)
    g.setUniformItemSizes(True); g.setSpacing(0); g.setMouseTracking(True); g.setSelectionRectVisible(False)
    d = TileDelegate(g, picture, lines); g.setItemDelegate(d); g.setIconSize(picture); g.setGridSize(d.tile_size())
    g.setStyleSheet("QListWidget::item, QListWidget::item:hover, QListWidget::item:selected { background: transparent; border: none; }")
    return g
