"""One-minute tour: five short notes, each beside the part of the window it describes.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRubberBand


def steps(main):
    """[(widget to point at, or None for the whole window, text)]"""
    b = main.active("book"); sh = b.current() if b is not None else None
    ribbon = getattr(main, "ribbon", None) or (main.side_bars[0] if getattr(main, "side_bars", None) else None)
    return [
        (sh.view if sh is not None else main.mdi, "<b>1. The worksheet</b><br>Type or paste your numbers here, or bring in a file with "
         "<b>File &gt; Import Wizard</b>. Click a column header (A, B ...) to select a column."),
        (sh.strip_sel.parentWidget() if sh is not None else main.mdi, "<b>2. Make a graph</b><br>The <b>Plot</b> row above the sheet draws the selected columns "
         "in one click. <b>More...</b> opens the gallery of every plot type."),
        (main.mdi, "<b>3. Format by clicking</b><br>On a graph, click a curve, a text, an axis or the legend: its settings appear in the row "
         "above the graph. Double-click a drawn shape to move or reshape it."),
        (ribbon, "<b>4. Analysis</b><br>Fitting, peaks, statistics, and the petrology and geochronology tools are on these tabs and in the "
         "<b>Analysis</b> and <b>Statistics</b> menus."),
        (getattr(main, "search_box", None), "<b>5. Find anything</b><br>Type a few words here, or press <b>Ctrl+K</b>: every command is found, "
         "also those that Simple Menus leaves out. <b>Ctrl+E</b> exports the graph."),
    ]


class Tour(QDialog):
    def __init__(self, main):
        super().__init__(main, Qt.Tool | Qt.FramelessWindowHint); self.main = main; self.items = steps(main); self.i = -1; self.band = None
        from .ui_style import ACCENT, palette
        self.setStyleSheet(f"QDialog {{ border: 2px solid {ACCENT}; border-radius: 8px; }}")
        self.text = QLabel(); self.text.setWordWrap(True); self.text.setMinimumWidth(330); self.text.setMaximumWidth(380)
        self.count = QLabel(); self.count.setStyleSheet(f"color: {palette(getattr(main, '_theme', 'light'))['muted']}")
        self.back = QPushButton("Back"); self.next = QPushButton("Next"); skip = QPushButton("Close"); self.next.setDefault(True)
        self.back.clicked.connect(lambda: self.go(self.i - 1)); self.next.clicked.connect(lambda: self.go(self.i + 1)); skip.clicked.connect(self.reject)
        row = QHBoxLayout(); row.addWidget(self.count); row.addStretch(); row.addWidget(skip); row.addWidget(self.back); row.addWidget(self.next)
        lay = QVBoxLayout(self); lay.setContentsMargins(14, 12, 14, 10); lay.addWidget(self.text); lay.addLayout(row); self.go(0)

    def go(self, i):
        if i >= len(self.items): return self.accept()
        self.i = max(0, i); w, html = self.items[self.i]; w = w if w is not None and w.isVisible() else self.main
        self.text.setText(html); self.count.setText(f"{self.i + 1} of {len(self.items)}"); self.back.setEnabled(self.i > 0)
        self.next.setText("Finish" if self.i == len(self.items) - 1 else "Next"); self.adjustSize()
        if self.band is not None: self.band.hide(); self.band.deleteLater()
        self.band = QRubberBand(QRubberBand.Rectangle, self.main); tl = w.mapTo(self.main, QPoint(0, 0)) if w is not self.main else QPoint(0, 0)
        self.band.setGeometry(tl.x(), tl.y(), w.width(), w.height()); self.band.show()
        g = w.mapToGlobal(QPoint(0, 0)); x = g.x() + min(40, max(0, w.width() - self.width())); y = g.y() + min(w.height(), 90)
        scr = self.main.screen().availableGeometry() if self.main.screen() else None
        if scr is not None: x = max(scr.left(), min(x, scr.right() - self.width())); y = max(scr.top(), min(y, scr.bottom() - self.height()))
        self.move(x, y)

    def done(self, r):
        if self.band is not None: self.band.hide(); self.band.deleteLater(); self.band = None
        super().done(r)
