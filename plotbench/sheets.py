"""PlotBench workbooks: multi-sheet books, column metadata, undo/redo, Import Wizard.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (QAbstractItemView, 
    QWidget, QVBoxLayout, QTableView, QInputDialog, QMenu, QTabWidget, QDialog, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QPlainTextEdit, QDialogButtonBox, QPushButton, QFileDialog, QHBoxLayout, QLabel,
    QCheckBox, QTableWidget, QTableWidgetItem)

from . import analysis as A
from . import cellformula as CF

DESIG = ["X", "Y", "Z", "yErr", "yErr+", "yErr-", "xErr", "Label", "Ignore"]
META = ["Long Name", "Units", "Comments"]
SPARK = len(META)          # view row that shows the sparkline
HEAD = len(META) + 1       # rows above the first data row
PREFS = {"digits": 6, "undo_levels": 30, "theme": "light"}  # overwritten from user settings by the main window


def col_letter(i):
    s = ""; i += 1
    while i:
        i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def full(v):
    """Exact text of a cell for editing and copying (repr round-trips float64)."""
    if isinstance(v, (float, np.floating)):
        if np.isnan(v): return ""
        t = repr(float(v)); return t[:-2] if t.endswith(".0") else t
    return "" if v is None else str(v)


def fmt(v):
    if isinstance(v, (float, np.floating)):
        return "" if np.isnan(v) else f"{v:.{PREFS['digits']}g}"
    return "" if v is None else str(v)


class FrameModel(QAbstractTableModel):
    """Rows 0..2 are metadata (long name, units, comments), row 3 is the sparkline, data follows (HEAD rows in all)."""

    def __init__(self, sheet):
        super().__init__(); self.sh = sheet

    @property
    def df(self): return self.sh.df

    def rowCount(self, p=QModelIndex()): return len(self.df) + HEAD
    def columnCount(self, p=QModelIndex()): return self.df.shape[1]

    def data(self, idx, role=Qt.DisplayRole):
        r, c = idx.row(), idx.column(); col = self.df.columns[c]
        if r < len(META):
            if role in (Qt.DisplayRole, Qt.EditRole): return self.sh.meta.get(col, {}).get(META[r], "")
            if role == Qt.BackgroundRole:
                from PySide6.QtGui import QColor; return QColor(238, 242, 250) if PREFS.get("theme") != "dark" else QColor(52, 56, 66)
            return None
        if r == SPARK: return None  # drawn by SparklineDelegate
        if role == Qt.DisplayRole: return fmt(self.df.iat[r - HEAD, c])
        if role == Qt.EditRole: return self.sh.cell_formulas.get((col, r - HEAD)) or full(self.df.iat[r - HEAD, c])
        if role == Qt.ToolTipRole and (col, r - HEAD) in self.sh.cell_formulas: return self.sh.cell_formulas[(col, r - HEAD)]
        if role == Qt.ForegroundRole and (col, r - HEAD) in self.sh.cell_formulas and (col, r - HEAD) not in self.sh.mask:
            from PySide6.QtGui import QColor
            v = self.df.iat[r - HEAD, c]
            return QColor(200, 0, 0) if isinstance(v, str) and v in CF.ERRORS else QColor(0, 90, 170) if PREFS.get("theme") != "dark" else QColor(120, 180, 255)
        if role == Qt.BackgroundRole and col in self.sh.heat and (col, r - HEAD) not in self.sh.mask:
            v = self.df.iat[r - HEAD, c]; lo, hi = self.sh.heat[col]
            if isinstance(v, (int, float, np.floating)) and np.isfinite(v) and hi > lo:
                from PySide6.QtGui import QColor
                f = (float(v) - lo) / (hi - lo)
                if PREFS.get("theme") == "dark": return QColor(int(40 + 10 * f), int(40 + 110 * f), int(45 + 120 * f))  # dark -> teal
                return QColor(int(255 - 150 * f), int(255 - 60 * f), int(255 - 20 * f))  # white -> teal
        if role in (Qt.BackgroundRole, Qt.ForegroundRole) and (col, r - HEAD) in self.sh.mask:
            from PySide6.QtGui import QColor
            dark = PREFS.get("theme") == "dark"
            if role == Qt.BackgroundRole: return QColor(110, 30, 30) if dark else QColor(255, 205, 205)
            return QColor(255, 170, 170) if dark else QColor(170, 0, 0)
        if role == Qt.TextAlignmentRole: return int(Qt.AlignRight | Qt.AlignVCenter)

    def setData(self, idx, value, role=Qt.EditRole):
        if role != Qt.EditRole: return False
        r, c = idx.row(), idx.column(); col = self.df.columns[c]
        if r == SPARK: return False
        if r < len(META):
            self.sh.snap(); self.sh.meta.setdefault(col, {})[META[r]] = value
            self.headerDataChanged.emit(Qt.Horizontal, c, c); self.sh.changed(); return True
        r -= HEAD
        if isinstance(value, str) and value.strip().startswith("=") and len(value.strip()) > 1:  # an Excel-style formula
            if col in self.sh.formulas:
                self.sh.main.statusBar().showMessage(f"Column {col} is calculated by its column formula; put cell formulas in another column", 8000)
                return False
            self.sh.snap(); self.sh.cell_formulas[(col, r)] = value.strip()
            if r == len(self.df) - 1: self.sh.add_rows(10, snap=False)
            self.sh.recalc(); self.refresh(); self.sh.changed(); return True
        try: v = float(value) if value.strip() != "" else np.nan
        except ValueError: v = value
        simple = (isinstance(v, float) and self.df[col].dtype != object and r < len(self.df) - 1 and not self.sh.formulas
                  and not self.sh.cell_formulas)
        if simple:  # common case: one number into a numeric column; undo stores just this cell
            self.sh.push_undo(("cell", col, r, self.df.iat[r, c])); self.df.iat[r, c] = v; self.dataChanged.emit(idx, idx)
        else:
            self.sh.snap(); self.sh.cell_formulas.pop((col, r), None)  # a plain value replaces the cell's formula (undo brings it back)
            if not isinstance(v, float) and self.df[col].dtype != object: self.df[col] = self.df[col].astype(object)
            self.df.iat[r, c] = v
            if r == len(self.df) - 1: self.sh.add_rows(10, snap=False)
            self.sh.recalc(); self.refresh()
        self.sh.changed(); return True

    def flags(self, idx):
        if idx.row() == SPARK: return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        f = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        sm = getattr(getattr(self.sh, "view", None), "selectionModel", lambda: None)()
        if sm is not None:  # only whole selected columns drag (isColumnSelected would call flags() again)
            c, last = idx.column(), self.rowCount() - 1
            if any(r.left() <= c <= r.right() and r.top() == 0 and r.bottom() == last for r in sm.selection()): f |= Qt.ItemIsDragEnabled
        return f

    def headerData(self, s, orient, role=Qt.DisplayRole):
        if orient == Qt.Horizontal and role == Qt.ToolTipRole:
            c = self.df.columns[s]; m = self.sh.meta.get(c, {})
            if c in self.sh.formulas: return f"Column formula: {c} = {self.sh.formulas[c]}"
            return f"Calculated: {m['Formula']}" if m.get("Formula") else f"Column {col_letter(s)} in cell formulas (e.g. ={col_letter(s)}1)"
        if role != Qt.DisplayRole: return None
        if orient == Qt.Horizontal:
            c = self.df.columns[s]; f = " =" if c in self.sh.formulas else ""; L = col_letter(s)
            return f"{c} ({self.sh.desig.get(c, 'Y')}){f}" if str(c) == L else f"{L} | {c} ({self.sh.desig.get(c, 'Y')}){f}"
        return META[s] if s < len(META) else "Sparkline" if s == SPARK else str(s - HEAD + 1)

    def refresh(self):
        """Reset the view but keep the cursor and selection where they were (a reset normally clears both)."""
        v = getattr(self.sh, "view", None); cur, ranges = None, []
        if v is not None and v.selectionModel() is not None:
            ci = v.currentIndex(); cur = (ci.row(), ci.column()) if ci.isValid() else None
            ranges = [(r.top(), r.left(), r.bottom(), r.right()) for r in v.selectionModel().selection()]
        self.beginResetModel(); self.endResetModel()
        if v is None or v.selectionModel() is None: return
        from PySide6.QtCore import QItemSelection, QItemSelectionModel
        nr, nc = self.rowCount(), self.columnCount(); sel = QItemSelection()
        for t, l, b, r in ranges:
            if nr and nc: sel.select(self.index(min(t, nr - 1), min(l, nc - 1)), self.index(min(b, nr - 1), min(r, nc - 1)))
        sm = v.selectionModel()
        if cur and nr and nc: sm.setCurrentIndex(self.index(min(cur[0], nr - 1), min(cur[1], nc - 1)), QItemSelectionModel.NoUpdate)
        if ranges: sm.select(sel, QItemSelectionModel.ClearAndSelect)


COLUMNS_MIME = "application/x-plotbench-columns"


class SheetView(QTableView):
    """Worksheet table. Select whole columns, then drag them (press inside the selection) onto a graph to add them, as in Origin."""

    def __init__(self, sheet):
        super().__init__(); self.sheet = sheet
        self.setDragEnabled(True); self.setDragDropMode(QAbstractItemView.DragOnly)
        self._fill_src = None; self._fill_to = None; self.viewport().setMouseTracking(True)

    # ---- fill handle: the small square at the bottom-right corner of the selection, as in Excel
    def _block(self):
        """(top, left, bottom, right) of a single selected block of data cells, in view rows; None otherwise."""
        sm = self.selectionModel()
        if sm is None: return None
        rs = sm.selection()
        if len(rs) != 1 or rs[0].top() < HEAD: return None
        r = rs[0]; return r.top(), r.left(), r.bottom(), r.right()

    def _handle_rect(self):
        from PySide6.QtCore import QRect
        b = self._block()
        if b is None: return None
        br = self.visualRect(self.model().index(b[2], b[3])).bottomRight()
        return QRect(br.x() - 3, br.y() - 3, 7, 7)

    def paintEvent(self, e):
        super().paintEvent(e)
        from PySide6.QtGui import QPainter, QColor, QPen
        from PySide6.QtCore import Qt as _Qt
        hr = self._handle_rect()
        if hr is None: return
        p = QPainter(self.viewport()); green = QColor(16, 124, 65)
        p.fillRect(hr.adjusted(-1, -1, 1, 1), QColor("white")); p.fillRect(hr, green)
        if self._fill_src and self._fill_to:
            t, l, b, r = self._fill_src; axis, end = self._fill_to
            if axis == 0: t2, b2, l2, r2 = min(t, end), max(b, end), l, r
            else: t2, b2, l2, r2 = t, b, min(l, end), max(r, end)
            m = self.model(); rect = self.visualRect(m.index(t2, l2)).united(self.visualRect(m.index(b2, r2)))
            pen = QPen(green, 2, _Qt.DashLine); p.setPen(pen); p.drawRect(rect.adjusted(0, 0, -1, -1))
        p.end()

    def mousePressEvent(self, e):
        from PySide6.QtCore import Qt as _Qt
        hr = self._handle_rect()
        if e.button() == _Qt.LeftButton and hr is not None and hr.adjusted(-3, -3, 3, 3).contains(e.position().toPoint()):
            self._fill_src = self._block(); self._fill_to = None; e.accept(); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        from PySide6.QtCore import Qt as _Qt
        pos = e.position().toPoint()
        if self._fill_src:
            t, l, b, r = self._fill_src
            if pos.y() > self.viewport().height() - 12: self.verticalScrollBar().setValue(self.verticalScrollBar().value() + 1)
            if pos.x() > self.viewport().width() - 12: self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + 1)
            idx = self.indexAt(pos)
            if idx.isValid():
                down = idx.row() - b if idx.row() > b else (idx.row() - t if idx.row() < t else 0)
                right = idx.column() - r if idx.column() > r else (idx.column() - l if idx.column() < l else 0)
                if abs(down) >= abs(right) and down: self._fill_to = (0, max(idx.row(), HEAD))
                elif right: self._fill_to = (1, idx.column())
                else: self._fill_to = None
                self.viewport().update()
            e.accept(); return
        hr = self._handle_rect()
        over = hr is not None and hr.adjusted(-3, -3, 3, 3).contains(pos) and not e.buttons()
        self.viewport().setCursor(_Qt.CrossCursor if over else _Qt.ArrowCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._fill_src:
            src, to = self._fill_src, self._fill_to; self._fill_src = self._fill_to = None; self.viewport().update()
            if to:
                t, l, b, r = src; axis, end = to
                n = self.sheet.fill(t - HEAD, l, b - HEAD, r, axis, end - HEAD if axis == 0 else end)
                m = self.model()
                if axis == 0: sel = (min(t, end), l, max(b, end), r)
                else: sel = (t, min(l, end), b, max(r, end))
                from PySide6.QtCore import QItemSelection, QItemSelectionModel
                self.selectionModel().select(QItemSelection(m.index(sel[0], sel[1]), m.index(sel[2], sel[3])), QItemSelectionModel.ClearAndSelect)
                if n and hasattr(self.sheet.main, "statusBar"):
                    self.sheet.main.statusBar().showMessage(f"Filled {n} {'rows' if axis == 0 else 'columns'}", 4000)
            e.accept(); return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        """Double-click the fill handle: fill down as far as the column next to the selection has data (as in Excel)."""
        hr = self._handle_rect()
        if hr is not None and hr.adjusted(-3, -3, 3, 3).contains(e.position().toPoint()):
            self._fill_src = None; t, l, b, r = self._block(); sh = self.sheet; end = None
            for c in (l - 1, r + 1):
                if 0 <= c < sh.df.shape[1]:
                    col = sh.df.iloc[:, c]; filled = np.flatnonzero(col.notna().to_numpy() & (col.astype(str).str.strip() != "").to_numpy())
                    if len(filled) and filled[-1] > b - HEAD: end = int(filled[-1]); break
            if end is not None:
                n = sh.fill(t - HEAD, l, b - HEAD, r, 0, end); m = self.model()
                from PySide6.QtCore import QItemSelection, QItemSelectionModel
                self.selectionModel().select(QItemSelection(m.index(t, l), m.index(end + HEAD, r)), QItemSelectionModel.ClearAndSelect)
                if n and hasattr(sh.main, "statusBar"): sh.main.statusBar().showMessage(f"Filled {n} rows (as far as the next column goes)", 4000)
            e.accept(); return
        super().mouseDoubleClickEvent(e)

    def startDrag(self, actions):
        import json
        from PySide6.QtCore import QMimeData
        from PySide6.QtGui import QDrag
        sh = self.sheet; x, ys = sh.xy_for_plot()
        if not ys: return
        md = QMimeData(); md.setData(COLUMNS_MIME, json.dumps({"book": sh.book.name, "sheet": sh.name, "x": x, "ys": ys}).encode())
        md.setText(", ".join(ys)); d = QDrag(self); d.setMimeData(md); d.exec(Qt.CopyAction)


class Sheet(QWidget):
    kind = "book"

    def __init__(self, book, name, df=None):
        super().__init__(); self.book = book; self.name = name
        self.df = df if df is not None else pd.DataFrame({"A": [np.nan] * 32, "B": [np.nan] * 32})
        self.desig = {c: "Y" for c in self.df.columns}; self.desig[self.df.columns[0]] = "X"
        self.formulas = {}; self.meta = {}; self.mask = set(); self.heat = {}; self.undo_stack = []; self.redo_stack = []
        self.cell_formulas = {}  # (column, row) -> '=SUM(A1:A5)' typed into single cells, as in Excel
        self.view = SheetView(self); self.model = FrameModel(self); self.view.setModel(self.model)
        from .ui2 import SparklineDelegate
        self.view.setItemDelegateForRow(SPARK, SparklineDelegate(self, SPARK)); self.view.verticalHeader().resizeSection(SPARK, 34)
        self.ops = []  # analyses that re-run when the data changes
        hh = self.view.horizontalHeader(); hh.setContextMenuPolicy(Qt.CustomContextMenu)
        hh.customContextMenuRequested.connect(self.header_menu)
        vh = self.view.verticalHeader(); vh.setContextMenuPolicy(Qt.CustomContextMenu); vh.customContextMenuRequested.connect(self.row_menu)
        self.view.installEventFilter(self)
        from .keys import EditDelegate
        self.view.setItemDelegate(EditDelegate(self)); self.view.setTabKeyNavigation(False)  # Tab and Enter are handled like Excel
        self.addr, self.fx, self.fxinfo = QLabel("A1"), QLineEdit(), QLabel("")
        self.addr.setMinimumWidth(52); self.addr.setStyleSheet("font-weight: bold"); self.addr.setToolTip("Cell address for formulas (column letter, row)")
        self.fx.setPlaceholderText("Value or formula of the selected cell: type = to calculate, e.g. =A1/B1, =SUM(B1:B10), =AVERAGE(C:C)")
        self.fx.setToolTip("Formula bar. Enter writes it into the cell. Functions: " + ", ".join(sorted(CF.FUNCS)))
        self.fx.returnPressed.connect(self._fx_enter); self.fxinfo.setStyleSheet("color: gray"); self._fx_completer()
        bar = QHBoxLayout(); bar.setContentsMargins(4, 2, 4, 2); bar.addWidget(self.addr); bar.addWidget(QLabel("<i>fx</i>")); bar.addWidget(self.fx, 3)
        bar.addWidget(self.fxinfo, 2)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0); lay.addLayout(bar); lay.addWidget(self.view)
        self.view.selectionModel().currentChanged.connect(lambda cur, _prev: self.show_formula(cur))

    # ---- formula bar
    def show_formula(self, cur=None):
        """Show what is behind the current cell: its own formula, its column formula, or how a command calculated it."""
        cur = cur if cur is not None else self.view.currentIndex()
        if not cur.isValid() or cur.column() >= self.df.shape[1]: return
        r, c = cur.row(), cur.column(); col = self.df.columns[c]; info = ""
        if r < len(META):
            self.addr.setText(META[r]); txt = self.meta.get(col, {}).get(META[r], "")
        elif r == SPARK: self.addr.setText(""); txt = ""
        else:
            r0 = r - HEAD; self.addr.setText(f"{col_letter(c)}{r0 + 1}")
            txt = self.cell_formulas.get((col, r0)) or (full(self.df.iat[r0, c]) if r0 < len(self.df) else "")
            if (col, r0) in self.cell_formulas: info = f"= {full(self.df.iat[r0, c])}"
            elif col in self.formulas: info = f"Column formula: {col} = {self.formulas[col]}"
            elif self.meta.get(col, {}).get("Formula"): info = f"Calculated: {self.meta[col]['Formula']}"
        self.fx.setText(txt); self.fxinfo.setText(info); self.fxinfo.setToolTip(info)

    def _fx_completer(self):
        """While a formula is typed in the formula bar, a list of matching functions (and sheet names) pops up; Enter or a click
        puts it in with its opening bracket."""
        import re
        from PySide6.QtWidgets import QCompleter
        from PySide6.QtCore import QStringListModel
        comp = QCompleter(self); comp.setCaseSensitivity(Qt.CaseInsensitive); comp.setWidget(self.fx)
        comp.setCompletionMode(QCompleter.PopupCompletion); model = QStringListModel(comp); comp.setModel(model)

        def token():
            t, p = self.fx.text(), self.fx.cursorPosition(); m = re.search(r"[A-Za-z_][A-Za-z0-9_.]*$", t[:p])
            if not t.startswith("=") or not m or t[:p].count('"') % 2: return None, p  # only in formulas, not inside "text"
            return m.group(0), m.start()

        def edited(_):
            tok, _s = token()
            if not tok or re.match(r"[A-Za-z]{1,3}\d+$", tok): comp.popup().hide(); return  # a cell address such as B12
            names = sorted(CF.FUNCS) + [s.name + "!" for s in getattr(self.book, "sheets", []) if s is not self and re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", s.name)]
            model.setStringList(names); comp.setCompletionPrefix(tok)
            if comp.completionCount() and comp.currentCompletion().upper() != tok.upper(): comp.complete()
            else: comp.popup().hide()

        def insert(name):
            tok, s = token()
            if tok is None: return
            t, p = self.fx.text(), self.fx.cursorPosition(); add = name if name.endswith("!") else name + "("
            self.fx.setText(t[:s] + add + t[p:]); self.fx.setCursorPosition(s + len(add))
        self.fx.textEdited.connect(edited); comp.activated[str].connect(insert); self._comp, self._comp_insert = comp, insert

    def _fx_enter(self):
        cur = self.view.currentIndex()
        if cur.isValid() and cur.row() != SPARK: self.model.setData(cur, self.fx.text(), Qt.EditRole); self.show_formula(cur)
        self.view.setFocus()

    def _sheet_source(self, name):
        """(get, rows, columns) of the sheet of this workbook called name (any case), for Sheet2!A1 references."""
        s = next((x for x in getattr(self.book, "sheets", []) if x.name.casefold() == name.casefold()), None)
        if s is None: return None

        def get(c, r):
            v = s.df.iat[r, c]
            return float(v) if isinstance(v, (np.floating, np.integer)) else v
        return get, len(s.df), s.df.shape[1]

    def update_links(self):
        """This sheet changed: recalculate the other sheets of the workbook whose cell formulas read sheets by name."""
        book = self.book
        if getattr(book, "_linking", False): return
        book._linking = True
        try:
            for _ in range(2):  # twice, so a chain Sheet3 -> Sheet2 -> Sheet1 settles
                for s in getattr(book, "sheets", []):
                    if s is not self and any("!" in t for t in s.cell_formulas.values()):
                        s.recalc(); s._spark = {}; s.model.refresh()  # column formulas that read those cells too
                        if hasattr(s.main, "schedule_graphs"): s.main.schedule_graphs(s)
        finally: book._linking = False

    def eval_cells(self):
        """Recalculate the cell formulas (several passes, so a formula can read another; a loop gives #CIRC!)."""
        if not self.cell_formulas: return
        cols = list(self.df.columns); n, m = len(self.df), len(cols)

        def get(c, r):
            v = self.df.iat[r, c]
            if isinstance(v, (np.floating, np.integer)): return float(v)
            return v

        def put(key, v):
            col, r = key
            if isinstance(v, str) and self.df[col].dtype != object: self.df[col] = self.df[col].astype(object)
            self.df.at[r, col] = v
        live = {k: t for k, t in self.cell_formulas.items() if k[0] in self.df.columns and k[1] < n}
        changed = set(live)
        for _ in range(len(live) + 1):
            changed = set()
            for key, t in live.items():
                v = CF.evaluate(t, get, n, m, self._sheet_source); old = self.df.at[key[1], key[0]]
                same = (v == old) or (isinstance(v, float) and isinstance(old, float) and np.isnan(v) and np.isnan(old))
                if not same: put(key, v); changed.add(key)
            if not changed: break
        for key in changed: put(key, "#CIRC!")  # still changing after every pass: the formulas refer to each other in a circle

    # ---- formulas follow their rows and columns
    def _move_cell_formulas(self, mapping):
        """mapping: old row -> new row (rows missing from it lost their formulas)."""
        self.cell_formulas = {(c, mapping[r]): t for (c, r), t in self.cell_formulas.items() if r in mapping}

    @property
    def main(self): return self.book.main

    # ---- undo / redo (snapshots; ponytail: whole-sheet copies, switch to diffs if sheets get huge)
    def _state(self): return (self.df.copy(), dict(self.desig), dict(self.formulas), {k: dict(v) for k, v in self.meta.items()},
                              set(self.mask), dict(self.cell_formulas))

    def _restore(self, st):
        self._spark = {}; self.df, self.desig, self.formulas, self.meta, self.mask = st[:5]
        self.cell_formulas = dict(st[5]) if len(st) > 5 else {}; self.model.refresh(); self.show_formula(); self.main.refresh_graphs(self); self.notify()
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def notify(self):
        """Data changed: re-run any auto-recalculating analyses on this sheet."""
        if self.ops and hasattr(self.main, "schedule_ops"): self.main.schedule_ops(self)

    def set_heat(self, cols, on=True):
        """Shade cells by value (light to blue-green) in the given columns."""
        for c in cols:
            if on:
                a = self.arr(c, raw=True); a = a[np.isfinite(a)]
                if a.size: self.heat[c] = (float(a.min()), float(a.max()))
            else: self.heat.pop(c, None)
        self.model.refresh()

    def changed(self):
        """After an edit: mark the project modified, redraw this sheet's graphs (debounced) and re-run auto analyses."""
        self._spark = {}
        if self.heat: self.set_heat(list(self.heat))
        if hasattr(self.main, "schedule_graphs"): self.main.schedule_graphs(self)
        self.notify(); self.update_links()

    def push_undo(self, item):
        self.undo_stack.append(item); self.redo_stack.clear(); del self.undo_stack[:-max(1, PREFS["undo_levels"])]
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def snap(self): self.push_undo(self._state())

    def _apply(self, item, into):
        if isinstance(item[0], str) and item[0] == "cell":  # swap one cell's value, so the same entry can be redone
            _, col, r, old = item
            if col in self.df.columns and r < len(self.df):
                into.append(("cell", col, r, self.df.at[r, col])); self.df.at[r, col] = old
            self.recalc(); self.model.refresh(); self.changed()
        else:
            into.append(self._state()); self._restore(item)

    def undo(self):
        if self.undo_stack: self._apply(self.undo_stack.pop(), self.redo_stack)

    def redo(self):
        if self.redo_stack: self._apply(self.redo_stack.pop(), self.undo_stack)

    # ---- clipboard and keyboard
    HEAD = HEAD  # rows above the first data row (for the keyboard module)

    def eventFilter(self, obj, ev):
        from .keys import handle_key
        return handle_key(self, obj, ev)

    def _sel_data(self):
        """Selected data cells as {(row, col_index)} in data coordinates."""
        return {(i.row() - HEAD, i.column()) for i in self.view.selectionModel().selectedIndexes() if i.row() >= HEAD}

    def _put(self, r, c, val):
        col = self.df.columns[c]
        if col in self.formulas: return
        if r >= len(self.df): self.add_rows(r - len(self.df) + 10, snap=False)
        try: v = float(val) if str(val).strip() != "" else np.nan
        except (TypeError, ValueError):
            v = val
            if self.df[col].dtype != object: self.df[col] = self.df[col].astype(object)
        self.df.iat[r, c] = v

    def fill_selection(self, text):
        cells = self._sel_data() or {(self.view.currentIndex().row() - HEAD, self.view.currentIndex().column())}
        self.snap()
        for r, c in cells:
            if r >= 0: self._put(r, c, text)
        self.recalc(); self.model.refresh(); self.changed()

    def fill_down(self):
        """Ctrl+D: copy the top row of the selection into the rest (or, for one row, the row above); formulas shift as in Excel."""
        cells = self._sel_data()
        if not cells: return
        rows = sorted({r for r, _ in cells}); cols = sorted({c for _, c in cells})
        src = rows[0] if len(rows) > 1 else rows[0] - 1  # one row selected: copy from the cell above, as in Excel
        if src < 0: return
        self.fill(src, cols[0], src, cols[-1], 0, rows[-1], series=False)

    def fill_right(self):
        cells = self._sel_data()
        if not cells: return
        rows = sorted({r for r, _ in cells}); cols = sorted({c for _, c in cells})
        src = cols[0] if len(cols) > 1 else cols[0] - 1
        if src < 0: return
        self.fill(rows[0], src, rows[-1], src, 1, cols[-1], series=False)

    def fill(self, r0, c0, r1, c1, axis, end, series=True):
        """Excel fill from the block rows r0..r1, columns c0..c1 (data coordinates) to row 'end' (axis 0, down or up) or column 'end'
        (axis 1, right or left). Formulas are copied with relative references moved; two or more numbers continue as a linear series
        (1, 2 -> 3, 4 ...); a single text ending in a number counts on (Sample 1 -> Sample 2); anything else is repeated. One undo step."""
        import re as _re
        lo, hi = (r0, r1) if axis == 0 else (c0, c1)
        targets = list(range(hi + 1, end + 1)) if end > hi else list(range(end, lo)) if end < lo else []
        if not targets: return 0
        self.snap(); n = hi - lo + 1
        lines = range(c0, c1 + 1) if axis == 0 else range(r0, r1 + 1)
        for line in lines:
            def at(p): return (p, line) if axis == 0 else (line, p)  # (row, col)
            src = []
            for p in range(lo, hi + 1):
                r, c = at(p); col = self.df.columns[c]
                src.append((self.cell_formulas.get((col, r)), self.df.iat[r, c] if r < len(self.df) else np.nan))
            nums = [v for f, v in src if f is None and isinstance(v, (int, float, np.floating)) and not np.isnan(v)]
            linear = series and n >= 2 and len(nums) == n
            if linear: slope, icpt = np.polyfit(np.arange(n), np.array(nums, float), 1)
            for t in targets:
                r, c = at(t); col = self.df.columns[c]
                if col in self.formulas: continue  # column formulas fill themselves
                k = (t - lo) % n; f, v = src[k]; step = t - (lo + k)
                if r >= len(self.df): self.add_rows(r - len(self.df) + 10, snap=False)
                if f is not None:
                    self.cell_formulas[(col, r)] = CF.shift_formula(f, step, 0) if axis == 0 else CF.shift_formula(f, 0, step); continue
                self.cell_formulas.pop((col, r), None)
                if linear: v = float(f"{icpt + slope * (t - lo):.12g}")  # 3, not 2.9999999999999996
                elif series and n == 1 and isinstance(v, str) and _re.search(r"\d+$", v):
                    m = _re.search(r"(\d+)$", v); num = int(m.group(1)) + (t - lo)
                    v = v[:m.start()] + (str(num).zfill(len(m.group(1))) if num >= 0 else str(num))
                self._put(r, c, v)
        self.recalc(); self.model.refresh(); self.changed(); return len(targets)

    def put_text(self, text):
        i = self.view.currentIndex()
        if i.isValid() and i.row() >= HEAD: self.snap(); self._put(i.row() - HEAD, i.column(), text); self.recalc(); self.model.refresh(); self.changed()

    def selection_block(self):
        idx = self.view.selectionModel().selectedIndexes()
        if not idx: return None
        rows = sorted({i.row() for i in idx}); cols = sorted({i.column() for i in idx}); return rows, cols

    def copy(self):
        from PySide6.QtWidgets import QApplication
        blk = self.selection_block()
        if not blk: return
        rows, cols = blk; m = self.model
        text = "\n".join("\t".join(str(m.data(m.index(r, c), Qt.EditRole) or "") for c in cols) for r in rows if r != SPARK)
        self.book._clip = (text, rows[0] - HEAD, cols[0]) if rows[0] >= HEAD else None  # where it came from: pasted formulas move
        QApplication.clipboard().setText(text)

    def paste(self, text=None):
        """Paste tab-separated (spreadsheet) or whitespace-separated text at the current cell; rows and columns are added as needed.
        Commas stay inside cells (decimal commas, text); comma-separated files go through the Import Wizard."""
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text() if text is None else text
        lines = [l for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        while lines and not lines[-1].strip(): lines.pop()
        if not lines: return
        sep = "\t" if any("\t" in l for l in lines) else None
        grid = [(l.split(sep) if sep else l.split()) for l in lines]
        cur = self.view.currentIndex(); r0 = max(cur.row(), HEAD) - HEAD if cur.isValid() else 0; c0 = max(cur.column(), 0)
        self.snap(); skipped = set()
        clip = getattr(self.book, "_clip", None); same = lambda a, b: a.replace("\r\n", "\n").strip("\n") == b.replace("\r\n", "\n").strip("\n")
        dr, dc = (r0 - clip[1], c0 - clip[2]) if clip and same(clip[0], text) else (0, 0)  # as in Excel, relative references follow the paste
        need_r = r0 + len(grid) + 1 - len(self.df)
        if need_r > 0: self.df = pd.concat([self.df, pd.DataFrame(np.nan, index=range(need_r), columns=self.df.columns)], ignore_index=True)
        while c0 + max(len(g) for g in grid) > self.df.shape[1]:
            nm = col_letter(self.df.shape[1])
            while nm in self.df.columns: nm += "_"
            self.df[nm] = np.nan; self.desig[nm] = "Y"
        for i, row in enumerate(grid):
            for j, val in enumerate(row):
                col = self.df.columns[c0 + j]; val = val.strip()
                if col in self.formulas: skipped.add(col); continue
                if val.startswith("=") and len(val) > 1: self.cell_formulas[(col, r0 + i)] = CF.shift_formula(val, dr, dc) if dr or dc else val; continue
                self.cell_formulas.pop((col, r0 + i), None)
                try: v = float(val) if val else np.nan
                except ValueError:
                    v = val
                    if self.df[col].dtype != object: self.df[col] = self.df[col].astype(object)
                self.df.iat[r0 + i, c0 + j] = v
        if skipped and hasattr(self.main, "statusBar"):
            self.main.statusBar().showMessage(f"Not pasted into formula column(s) {', '.join(map(str, skipped))}: clear the formula first.", 8000)
        self.recalc(); self.model.refresh(); self.changed()

    def clear_cells(self):
        cells = [(c, r) for c, r in self.selected_cells() if r < len(self.df)]
        if not cells: return
        self.snap()
        for c, r in cells:
            if c not in self.formulas: self.df.at[r, c] = np.nan; self.cell_formulas.pop((c, r), None)
        self.recalc(); self.model.refresh(); self.changed()

    def insert_rows(self, at, n=1):
        self.snap(); top, bot = self.df.iloc[:at], self.df.iloc[at:]
        self.df = pd.concat([top, pd.DataFrame(np.nan, index=range(n), columns=self.df.columns), bot], ignore_index=True)
        self.mask = {(c, r + n if r >= at else r) for c, r in self.mask}
        self._move_cell_formulas({r: (r + n if r >= at else r) for r in range(len(self.df))})
        for _ in range(n): self._shift_formula_columns(at + 1, 1, axis=0)  # =A5 becomes =A6 when a row goes in above it
        self.recalc(); self.model.refresh(); self.changed()

    def delete_rows(self, rows):
        rows = sorted({r for r in rows if 0 <= r < len(self.df)})
        if not rows: return
        self.snap(); keep = np.setdiff1d(np.arange(len(self.df)), rows); new = {old: i for i, old in enumerate(keep)}
        self.df = self.df.iloc[keep].reset_index(drop=True); self.mask = {(c, new[r]) for c, r in self.mask if r in new}
        self._move_cell_formulas(new)
        for r in reversed(rows): self._shift_formula_columns(r + 1, -1, axis=0)  # bottom first, so the row numbers stay right
        self.recalc(); self.model.refresh(); self.changed()

    def row_menu(self, pos):
        r = self.view.verticalHeader().logicalIndexAt(pos) - HEAD
        if r < 0: return
        sel = sorted({i.row() - HEAD for i in self.view.selectionModel().selectedIndexes() if i.row() >= HEAD}) or [r]
        m = QMenu(self)
        m.addAction("Insert row above", lambda: self.insert_rows(r))
        m.addAction(f"Delete {len(sel)} selected row(s)", lambda: self.delete_rows(sel))
        m.exec(self.view.verticalHeader().mapToGlobal(pos))

    # ---- column helpers
    def label(self, c):
        """Axis label from long name and units, falling back to the short name."""
        if c is None: return "Row"
        m = self.meta.get(c, {}); ln = m.get("Long Name") or str(c); u = m.get("Units")
        return f"{ln} ({u})" if u else ln

    def selected_cols(self):
        cols = sorted({i.column() for i in self.view.selectionModel().selectedIndexes()})
        return [self.df.columns[c] for c in cols]

    def x_col(self): return next((c for c in self.df.columns if self.desig.get(c) == "X"), None)
    def arr(self, c, raw=False):
        """Numeric column; masked cells become NaN unless raw=True."""
        a = pd.to_numeric(self.df[c], errors="coerce").to_numpy(float)
        if not raw and self.mask:
            rows = [r for (cc, r) in self.mask if cc == c and r < len(a)]
            if rows: a = a.copy(); a[rows] = np.nan
        return a

    def masked_rows(self, c): return sorted(r for (cc, r) in self.mask if cc == c)

    def set_mask(self, cells, on=True):
        """cells: iterable of (column, row)."""
        self.snap()
        if on: self.mask |= set(cells)
        else: self.mask -= set(cells)
        self.model.refresh(); self.main.refresh_graphs(self); self.notify()

    def selected_cells(self):
        n = HEAD
        return [(self.df.columns[i.column()], i.row() - n) for i in self.view.selectionModel().selectedIndexes() if i.row() >= n]

    def xy_for_plot(self):
        sel = self.selected_cols() or [c for c in self.df.columns if self.desig.get(c) == "Y"]
        x = self.x_col()
        return x, [c for c in sel if c != x and self.desig.get(c) not in ("Ignore", "Label")]

    def add_rows(self, n, snap=True):
        if snap: self.snap()
        self.df = pd.concat([self.df, pd.DataFrame(np.nan, index=range(n), columns=self.df.columns)], ignore_index=True)
        self.model.refresh()

    def add_column(self, name=None, values=None, desig="Y", long_name=None, units=None, snap=True, formula=None):
        if snap: self.snap()
        name = name or col_letter(self.df.shape[1])
        while name in self.df.columns: name += "_"
        if values is not None and len(values) > len(self.df):
            self.df = pd.concat([self.df, pd.DataFrame(np.nan, index=range(len(values) - len(self.df)), columns=self.df.columns)],
                                ignore_index=True)
        obj = values is not None and np.asarray(values).dtype == object
        col = np.full(len(self.df), np.nan, dtype=object if obj else float)
        if values is not None: col[:len(values)] = values
        self.df[name] = col; self.desig[name] = desig
        if long_name or units: self.meta[name] = {"Long Name": long_name or "", "Units": units or ""}
        cmd = getattr(self.main, "current_command", None) if values is not None else None
        if formula or cmd:  # shown in the formula bar and the header tooltip
            self.meta.setdefault(name, {})["Formula"] = formula or f"made by {cmd}"
        self.model.refresh(); return name

    def _formula_order(self):
        """Formula columns sorted so each runs after the formula columns it reads; raises CycleError on a loop."""
        import ast
        from graphlib import TopologicalSorter
        names = {str(c): c for c in self.formulas}; deps = {}
        for c, expr in self.formulas.items():
            try: used = {n.id for n in ast.walk(ast.parse(expr, mode="eval")) if isinstance(n, ast.Name)}
            except SyntaxError: used = set()
            deps[c] = {names[u] for u in used if u in names and names[u] != c}
        return list(TopologicalSorter(deps).static_order())

    def _formula_input(self, c):
        """Numbers for numeric columns; text columns stay text so where(Sample == "Olivine", ...) works."""
        s = self.df[c]
        if s.dtype == object and s.notna().any() and pd.to_numeric(s, errors="coerce").isna().all(): return s.to_numpy(object)
        return self.arr(c, raw=True)

    def recalc(self):
        from graphlib import CycleError
        if self.formulas: self.eval_cells()  # cell formulas first, so column formulas read their current values; again at the end
        cols = {str(c): self._formula_input(c) for c in self.df.columns}
        try: order = self._formula_order()
        except CycleError as e:
            self.main.statusBar().showMessage(f"Formulas refer to each other in a circle: {', '.join(map(str, e.args[1]))}", 8000); return
        for c in order:
            expr = self.formulas[c]
            try:
                out = A.eval_formula(expr, cols, len(self.df)); self.df[c] = out
                cols[str(c)] = out if out.dtype == object else self.df[c].to_numpy(float)
            except Exception as e:
                self.main.statusBar().showMessage(f"Formula error in {c}: {e}", 8000)
        self.eval_cells()

    def header_menu(self, pos):
        c = self.df.columns[self.view.horizontalHeader().logicalIndexAt(pos)]
        m = QMenu(self)
        for d in DESIG: m.addAction(f"Set as {d}", lambda d=d: self.set_desig([c], d))
        m.addSeparator()
        m.addAction("Set column values (formula)...", lambda: self.set_formula(c))
        m.addAction("Column properties...", lambda: self.properties(c))
        m.addAction("Mask selected cells", lambda: self.set_mask(self.selected_cells(), True))
        m.addAction("Unmask selected cells", lambda: self.set_mask(self.selected_cells(), False))
        m.addAction("Sort ascending", lambda: self.sort(c, True)); m.addAction("Sort descending", lambda: self.sort(c, False))
        m.addAction("Insert column before", lambda: self.insert_column(c))
        m.addAction("Delete column", lambda: self.delete(c))
        m.exec(self.view.horizontalHeader().mapToGlobal(pos))

    def set_desig(self, cols, d):
        self.snap()
        for c in cols: self.desig[c] = d
        self.model.refresh(); self.changed()

    def formula_preview(self, c, expr, n=12):
        """First n values the formula would give (raises with a readable message if it cannot run)."""
        cols = {str(k): self._formula_input(k) for k in self.df.columns}
        if self.formulas:
            for k in self._formula_order():
                if k != c:
                    try: cols[str(k)] = A.eval_formula(self.formulas[k], cols, len(self.df))
                    except Exception: pass
        return A.eval_formula(expr, cols, len(self.df))[:n]

    def set_formula(self, c, expr=None):
        if expr is None:
            d = FormulaDialog(self, c)
            if not d.exec(): return
            expr = d.expr.text()
        self.snap()
        if expr.strip(): self.formulas[c] = expr.strip(); self.recalc()
        else: self.formulas.pop(c, None)
        self.model.refresh(); self.changed()

    def properties(self, c):
        m = self.meta.get(c, {})
        name, ln, un, cm = QLineEdit(str(c)), QLineEdit(m.get("Long Name", "")), QLineEdit(m.get("Units", "")), QLineEdit(m.get("Comments", ""))
        des = QComboBox(); des.addItems(DESIG); des.setCurrentText(self.desig.get(c, "Y"))
        d = QDialog(self); d.setWindowTitle(f"Column properties: {c}"); f = QFormLayout(d)
        for lab, w in (("Short name", name), ("Long name", ln), ("Units", un), ("Comments", cm), ("Plot designation", des)): f.addRow(lab, w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if not d.exec(): return
        self.snap()
        new = name.text().strip() or c
        if new != c and new not in self.df.columns:
            self.df.rename(columns={c: new}, inplace=True)
            for dct in (self.desig, self.formulas, self.meta):
                if c in dct: dct[new] = dct.pop(c)
            self.cell_formulas = {((new if cc == c else cc), r): t for (cc, r), t in self.cell_formulas.items()}
            self.mask = {(new if cc == c else cc, r) for cc, r in self.mask}
            if c in self.heat: self.heat[new] = self.heat.pop(c)
            if hasattr(self.main, "rename_column_refs"): self.main.rename_column_refs(self, c, new)
            c = new
        self.meta[c] = {"Long Name": ln.text(), "Units": un.text(), "Comments": cm.text()}
        self.desig[c] = des.currentText(); self.model.refresh(); self.changed()

    def sort(self, c, asc):
        self.snap()
        try: order = self.df.sort_values(c, ascending=asc, na_position="last").index.to_numpy()
        except TypeError:  # numbers mixed with text such as '<0.05': sort by the numbers, text rows last
            def key(v):  # numbers by value, then text alphabetically, blanks last
                if v is None or (isinstance(v, float) and np.isnan(v)): return (2, 0.0, "")
                try: return (0, float(v), "")
                except (TypeError, ValueError): return (1, 0.0, str(v))
            keys = self.df[c].map(key); order = sorted(range(len(keys)), key=lambda i: keys.iat[i], reverse=not asc)
            if not asc: order = [i for i in order if keys.iat[i][0] != 2] + [i for i in order if keys.iat[i][0] == 2]
            order = self.df.index.to_numpy()[order]
        new_pos = {old: new for new, old in enumerate(order)}  # masks follow their rows
        self.df = self.df.loc[order].reset_index(drop=True); self.mask = {(cc, new_pos[r]) for cc, r in self.mask if r in new_pos}
        self._move_cell_formulas(new_pos); self.recalc(); self.model.refresh()

    def _shift_formula_columns(self, at, delta, axis=1):
        """Cell formulas here, and Sheet!A1 references to this sheet elsewhere in the workbook, keep pointing at the same data when a
        column (axis 1, index 'at') or a row (axis 0, 1-based row 'at') is inserted or deleted."""
        self.cell_formulas = {k: CF.shift_refs(t, axis, at, delta, sheet=self.name, own=True) for k, t in self.cell_formulas.items()}
        for s in getattr(self.book, "sheets", []):
            if s is not self and s.cell_formulas:
                s.cell_formulas = {k: CF.shift_refs(t, axis, at, delta, sheet=self.name, own=False) for k, t in s.cell_formulas.items()}

    def insert_column(self, before, name=None):
        """New empty column in front of column 'before' (formula letters move along, as in Excel)."""
        at = list(self.df.columns).index(before); self.snap()
        name = name or col_letter(self.df.shape[1])
        while name in self.df.columns: name += "_"
        self.df.insert(at, name, np.nan); self.desig[name] = "Y"; self._shift_formula_columns(at, 1)
        self.recalc(); self.model.refresh(); self.changed(); return name

    def delete(self, c):
        at = list(self.df.columns).index(c)
        self.snap(); self.df.drop(columns=[c], inplace=True); self._shift_formula_columns(at, -1)
        for dct in (self.desig, self.formulas, self.meta): dct.pop(c, None)
        self.cell_formulas = {k: t for k, t in self.cell_formulas.items() if k[0] != c}
        self.mask = {m for m in self.mask if m[0] != c}; self.recalc(); self.model.refresh()

    def state(self): return {"name": self.name, "desig": self.desig, "formulas": self.formulas, "meta": self.meta,
                             "mask": sorted([str(c), int(r)] for c, r in self.mask), "ops": self.ops,
                             "cells": sorted([str(c), int(r), t] for (c, r), t in self.cell_formulas.items())}


class FormulaDialog(QDialog):
    """Set column values, with the first rows of the result shown live as you type."""

    def __init__(self, sheet, c):
        super().__init__(sheet); self.sh, self.c = sheet, c; self.setWindowTitle(f"Set column values: {c}"); self.resize(520, 460)
        from PySide6.QtWidgets import QTableWidget, QHeaderView, QLabel
        from .live import LivePreview
        self.expr = QLineEdit(sheet.formulas.get(c, "")); self.expr.setPlaceholderText("e.g. A*2 + sin(B), log10(C), where(S == 'Olivine', A, 0)")
        cols = ", ".join(map(str, sheet.df.columns))
        help_ = QLabel(f"<span style='color:gray'>Columns: {cols}. i = row number. Functions: sin, cos, exp, log, log10, sqrt, abs, where, ...</span>")
        help_.setWordWrap(True)
        self.table = QTableWidget(0, 3); self.table.setHorizontalHeaderLabels(["Row", "Now", "New"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.verticalHeader().hide(); self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.live = LivePreview(self, self.show_preview)
        f = QFormLayout(self); f.addRow(f"{c} =", self.expr); f.addRow(help_); f.addRow("Preview (first rows)", self.table); f.addRow(self.live.bar())
        self.live.start(); self.live.run()

    def show_preview(self):
        e = self.expr.text().strip(); now = self.sh.df[self.c].to_numpy()[:12]
        new = self.sh.formula_preview(self.c, e) if e else [None] * len(now)
        self.table.setRowCount(len(now))
        from PySide6.QtWidgets import QTableWidgetItem
        for r, (a, b) in enumerate(zip(now, new)):
            for k, v in enumerate((r + 1, fmt(a), "" if b is None else fmt(b))): self.table.setItem(r, k, QTableWidgetItem(str(v)))


class Workbook(QWidget):
    """A book holds one or more sheets (tabs at the bottom, like a spreadsheet)."""
    kind = "book"

    def __init__(self, main, name, df=None, sheet_name="Sheet1"):
        super().__init__(); self.main = main; self.setWindowTitle(name)
        self.tabs = QTabWidget(); self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self.tab_menu)
        self.tabs.currentChanged.connect(lambda _: self.main.refresh_explorer())
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(self.tabs)
        self.add_sheet(sheet_name, df)

    @property
    def name(self): return self.windowTitle()

    @property
    def sheets(self): return [self.tabs.widget(i) for i in range(self.tabs.count())]

    def current(self): return self.tabs.currentWidget()
    def sheet(self, name):
        if name is None: return self.sheets[0]  # graphs from 1.0 projects name no sheet
        return next(s for s in self.sheets if s.name == name)  # StopIteration: the sheet was deleted

    def add_sheet(self, name=None, df=None):
        names = {s.name for s in self.sheets}
        if not name or name in names:
            k = len(names) + 1
            while f"Sheet{k}" in names: k += 1
            name = f"Sheet{k}"
        sh = Sheet(self, name, df); self.tabs.addTab(sh, name); self.tabs.setCurrentWidget(sh)
        self.main.refresh_explorer(); return sh

    def tab_menu(self, pos):
        i = self.tabs.tabBar().tabAt(pos); m = QMenu(self)
        m.addAction("Add sheet", lambda: self.add_sheet())
        if i >= 0:
            sh = self.tabs.widget(i)
            m.addAction("Rename sheet...", lambda: self.rename_sheet(sh))
            m.addAction("Duplicate sheet", lambda: self.dup_sheet(sh))
            if self.tabs.count() > 1: m.addAction("Delete sheet", lambda: self.delete_sheet(sh))
        m.exec(self.tabs.tabBar().mapToGlobal(pos))

    def rename_sheet(self, sh):
        n, ok = QInputDialog.getText(self, "Rename sheet", "Name:", text=sh.name)
        if ok and n and n not in {s.name for s in self.sheets}:
            self.main.rename_refs(self.name, sh.name, self.name, n)
            for s in self.sheets: s.cell_formulas = {k: CF.rename_sheet(t, sh.name, n) for k, t in s.cell_formulas.items()}
            sh.name = n; self.tabs.setTabText(self.tabs.indexOf(sh), n); self.main.refresh_explorer()

    def dup_sheet(self, sh):
        new = self.add_sheet(f"{sh.name}_copy", sh.df.copy())
        new.desig, new.formulas, new.meta = dict(sh.desig), dict(sh.formulas), {k: dict(v) for k, v in sh.meta.items()}
        new.mask, new.heat = set(sh.mask), dict(sh.heat)
        new.cell_formulas = dict(sh.cell_formulas)  # cell formulas stay formulas in the copy
        new.model.refresh()
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def rename(self, sh, n):
        """Rename a sheet without a dialog (scripts and tests)."""
        old = sh.name
        self.main.rename_refs(self.name, old, self.name, n)
        for s in self.sheets: s.cell_formulas = {k: CF.rename_sheet(t, old, n) for k, t in s.cell_formulas.items()}
        sh.name = n; self.tabs.setTabText(self.tabs.indexOf(sh), n)

    def delete_sheet(self, sh):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Delete sheet", f"Delete sheet '{sh.name}'? This cannot be undone.") != QMessageBox.Yes: return
        self.tabs.removeTab(self.tabs.indexOf(sh)); sh.deleteLater(); self.main.refresh_explorer()
        for s in self.sheets:  # formulas that read the deleted sheet now show #REF!
            if any("!" in t for t in s.cell_formulas.values()): s.recalc(); s.model.refresh()
        for g in self.main.windows():
            if g.kind == "graph" and g.spec.get("book") == self.name and g.spec.get("sheet") == sh.name:
                try: g.draw()
                except Exception: pass
        if hasattr(self.main, "mark_dirty"): self.main.mark_dirty()

    def state(self): return {"kind": "book", "name": self.name, "sheets": [s.state() for s in self.sheets]}


# ---------------------------------------------------------------- Import Wizard
SEPS = {"Auto-detect": None, "Comma": ",", "Tab": "\t", "Semicolon": ";", "Space(s) / whitespace": r"\s+", "Pipe |": "|"}


def read_with_options(path, sep=None, skip=0, names_line=1, units_line=0, comments_line=0, comment_char="", decimal=".",
                      max_rows=None):
    """Parse a delimited text file. Line numbers are 1-based and counted after `skip` lines; 0 = none.
    Returns (DataFrame, meta dict)."""
    raw = pd.read_csv(path, sep=sep, engine="python" if sep is None else "c", header=None, skiprows=skip,
                      comment=comment_char or None, decimal=decimal, dtype=str, nrows=max_rows, skip_blank_lines=True,
                      on_bad_lines="skip")  # the C parser is ~10x faster; only delimiter sniffing needs the Python one
    hdr = [l for l in (names_line, units_line, comments_line) if l]
    first_data = max(hdr) if hdr else 0
    names = [str(v).strip() if isinstance(v, str) and v.strip() else None for v in raw.iloc[names_line - 1]] if names_line else [None] * raw.shape[1]
    names = [n or col_letter(i) for i, n in enumerate(names)]
    seen = {}
    for i, n in enumerate(names):  # make unique
        if n in seen: seen[n] += 1; names[i] = f"{n}_{seen[n]}"
        else: seen[n] = 0
    data = raw.iloc[first_data:].reset_index(drop=True); data.columns = names
    for c in names:  # cells are read as text, so the decimal separator is applied here
        txt = data[c].str.replace(decimal, ".", regex=False) if decimal != "." else data[c]
        num = pd.to_numeric(txt, errors="coerce")
        if num.notna().sum() >= max(1, data[c].notna().sum() * 0.8): data[c] = num  # mostly numeric -> numeric
    meta = {}
    for line, key in ((units_line, "Units"), (comments_line, "Comments")):
        if line:
            for c, v in zip(names, raw.iloc[line - 1]):
                if isinstance(v, str) and v.strip(): meta.setdefault(c, {})[key] = v.strip()
    return data, meta


class ImportWizard(QDialog):
    def __init__(self, parent, path=None):
        super().__init__(parent); self.setWindowTitle("Import Wizard"); self.resize(900, 640)
        self.path = QLineEdit(path or ""); browse = QPushButton("Browse..."); browse.clicked.connect(self.browse)
        self.sep = QComboBox(); self.sep.addItems(SEPS)
        self.skip, self.names_line, self.units_line, self.comm_line = (QSpinBox() for _ in range(4))
        for s in (self.skip, self.names_line, self.units_line, self.comm_line): s.setRange(0, 10000)
        self.names_line.setValue(1)
        self.comment = QLineEdit("#"); self.decimal = QComboBox(); self.decimal.addItems([".", ","])
        self.target = QComboBox(); self.target.addItems(["New workbook", "New sheet in active workbook", "Replace active sheet"])
        self.raw = QPlainTextEdit(); self.raw.setReadOnly(True); self.raw.setMaximumHeight(160)
        self.preview = QTableWidget(); self.msg = QLabel()
        f = QFormLayout(); row = QHBoxLayout(); row.addWidget(self.path); row.addWidget(browse); f.addRow("File", row)
        f.addRow("Delimiter", self.sep); f.addRow("Skip lines at top", self.skip)
        f.addRow("Column names on line (0 = none)", self.names_line); f.addRow("Units on line (0 = none)", self.units_line)
        f.addRow("Comments on line (0 = none)", self.comm_line); f.addRow("Comment character", self.comment)
        f.addRow("Decimal separator", self.decimal); f.addRow("Import into", self.target)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self); lay.addLayout(f); lay.addWidget(QLabel("File start:")); lay.addWidget(self.raw)
        lay.addWidget(QLabel("Preview:")); lay.addWidget(self.preview); lay.addWidget(self.msg); lay.addWidget(bb)
        for w in (self.sep, self.decimal): w.currentIndexChanged.connect(self.update_preview)
        for w in (self.skip, self.names_line, self.units_line, self.comm_line): w.valueChanged.connect(self.update_preview)
        self.comment.textChanged.connect(self.update_preview); self.path.editingFinished.connect(self.update_preview)
        self.update_preview()

    def browse(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Import", "", "Text data (*.csv *.txt *.dat *.tsv *.prn *.asc);;All (*.*)")
        if fn: self.path.setText(fn); self.update_preview()

    def options(self):
        return dict(sep=SEPS[self.sep.currentText()], skip=self.skip.value(), names_line=self.names_line.value(),
                    units_line=self.units_line.value(), comments_line=self.comm_line.value(),
                    comment_char=self.comment.text()[:1], decimal=self.decimal.currentText())

    def update_preview(self):
        p = self.path.text()
        if not p or not Path(p).is_file(): return
        with open(p, errors="replace") as fh: self.raw.setPlainText("".join(fh.readline() for _ in range(15)))
        try:
            df, meta = read_with_options(p, max_rows=60, **self.options())
        except Exception as e:
            self.msg.setText(f"Cannot parse with these settings: {e}"); return
        self.msg.setText(f"{df.shape[1]} columns detected.")
        show = df.head(30); self.preview.setColumnCount(show.shape[1]); self.preview.setRowCount(len(show))
        self.preview.setHorizontalHeaderLabels([f"{c}\n{meta.get(c, {}).get('Units', '')}" for c in show.columns])
        for i in range(len(show)):
            for j in range(show.shape[1]): self.preview.setItem(i, j, QTableWidgetItem(fmt(show.iat[i, j])))

    def result_data(self):
        return read_with_options(self.path.text(), **self.options())
