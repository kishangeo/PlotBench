"""Excel-style keyboard handling for PlotBench worksheets.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import datetime

import numpy as np
from PySide6.QtCore import Qt, QEvent, QItemSelection, QItemSelectionModel, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QStyledItemDelegate, QTableView, QApplication

SHORTCUTS = [  # (keys, action) shown in Help > Keyboard Shortcuts
    ("Worksheet: moving", ""),
    ("Arrow keys", "Move one cell"), ("Ctrl+Arrow", "Jump to the edge of the data (next filled/empty boundary)"),
    ("Home / End", "First / last column of the row"), ("Ctrl+Home / Ctrl+End", "First cell / last used cell"),
    ("Page Up / Page Down", "Scroll one screen"), ("Enter / Shift+Enter", "Move down / up (also after typing in a cell)"),
    ("Tab / Shift+Tab", "Move right / left"), ("Ctrl+Page Down / Ctrl+Page Up", "Next / previous sheet in the workbook"),
    ("Worksheet: selecting", ""),
    ("Shift+Arrow", "Extend the selection by one cell"), ("Ctrl+Shift+Arrow", "Extend the selection to the edge of the data"),
    ("Ctrl+Shift+Home / Ctrl+Shift+End", "Extend the selection to the first cell / last used cell"),
    ("Ctrl+Space", "Select the whole column"), ("Shift+Space", "Select the whole row"), ("Ctrl+A", "Select all"),
    ("Worksheet: editing", ""),
    ("F2 or start typing", "Edit the cell"), ("Esc", "Cancel editing"),
    ("Ctrl+Enter (while editing)", "Put the typed value in every selected cell"), ("Alt+Enter (while editing)", "Same as Ctrl+Enter"),
    ("Ctrl+C / Ctrl+X / Ctrl+V", "Copy / cut / paste (paste grows the sheet as needed)"), ("Delete", "Clear the selected cells"),
    ("Ctrl+D / Ctrl+R", "Fill down / fill right from the first row / column of the selection (formulas move their references)"),
    ("Drag the fill handle", "The green square at the selection's corner: drag to fill formulas, series (1, 2 -> 3, 4) or copies"),
    ("Ctrl+;", "Insert today's date"), ("Ctrl+Shift+: ", "Insert the current time"),
    ("Ctrl+Shift++ / Ctrl+-", "Insert rows above / delete the selected rows"),
    ("Ctrl+Z / Ctrl+Y", "Undo / redo"), ("Ctrl+M", "Mask the selected cells"), ("Ctrl+Q", "Set column values (formula)"),
    ("Program", ""),
    ("F4", "Repeat the last menu command"), ("Ctrl+N / Ctrl+O / Ctrl+S", "New workbook / open / save project"),
    ("Ctrl+I", "Import Wizard"), ("Ctrl+E", "Export graph"), ("Ctrl+G", "Graph properties"), ("Ctrl+L", "Layout page"),
    ("Ctrl+F", "Nonlinear curve fit"), ("Ctrl+Shift+K", "Peak Analyzer"), ("Ctrl+Shift+C", "Copy graph to the clipboard"),
    ("F5", "Refresh graphs and layouts"), ("Ctrl+Shift+D", "Dark theme"), ("Ctrl+Shift+P", "Python console"),
    ("Ctrl+Shift+S", "Start page"),
]


def _filled(v):
    if v is None: return False
    if isinstance(v, (float, np.floating)): return not np.isnan(v)
    return str(v).strip() != ""


class EditDelegate(QStyledItemDelegate):
    """Enter/Shift+Enter commit and move; Ctrl+Enter or Alt+Enter fill the whole selection with the typed value."""

    def __init__(self, sheet): super().__init__(sheet.view); self.sh = sheet

    def eventFilter(self, editor, ev):
        if ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            mods = ev.modifiers()
            if mods & (Qt.ControlModifier | Qt.AltModifier):
                text = editor.text() if hasattr(editor, "text") else ""
                self.closeEditor.emit(editor, QStyledItemDelegate.RevertModelCache); QTimer.singleShot(0, lambda: self.sh.fill_selection(text)); return True
            self.commitData.emit(editor); self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)
            QTimer.singleShot(0, lambda up=bool(mods & Qt.ShiftModifier): move(self.sh, -1 if up else 1, 0)); return True
        return super().eventFilter(editor, ev)


def _cur(sh):
    i = sh.view.currentIndex(); m = sh.model
    return (i.row(), i.column()) if i.isValid() else (sh.HEAD, 0)


def _set(sh, r, c, extend=False):
    m = sh.model; r = max(0, min(r, m.rowCount() - 1)); c = max(0, min(c, m.columnCount() - 1)); idx = m.index(r, c); sm = sh.view.selectionModel()
    if extend:
        a = getattr(sh, "_anchor", None) or sh.view.currentIndex()
        sm.setCurrentIndex(idx, QItemSelectionModel.NoUpdate); sm.select(QItemSelection(a, idx), QItemSelectionModel.ClearAndSelect); sh._anchor = a
    else:
        sm.setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect); sh._anchor = idx
    sh.view.scrollTo(idx)


def move(sh, dr, dc, extend=False):
    r, c = _cur(sh); _set(sh, r + dr, c + dc, extend)


def _value(sh, r, c):
    return sh.df.iat[r - sh.HEAD, c] if r >= sh.HEAD and r - sh.HEAD < len(sh.df) else None


def edge(sh, r, c, dr, dc):
    """Excel's Ctrl+Arrow target from (r, c): end of the current filled run, else the next filled cell, else the sheet edge."""
    nr, nc = sh.model.rowCount(), sh.model.columnCount(); lo_r = sh.HEAD if r >= sh.HEAD else 0
    step = lambda rr, cc: (rr + dr, cc + dc)
    inside = lambda rr, cc: lo_r <= rr < nr and 0 <= cc < nc
    rr, cc = step(r, c)
    if not inside(rr, cc): return r, c
    if _filled(_value(sh, r, c)) and _filled(_value(sh, rr, cc)):  # walk to the end of this filled run
        while inside(*step(rr, cc)) and _filled(_value(sh, *step(rr, cc))): rr, cc = step(rr, cc)
        return rr, cc
    while inside(rr, cc) and not _filled(_value(sh, rr, cc)):  # skip blanks to the next filled cell
        if not inside(*step(rr, cc)): return rr, cc
        rr, cc = step(rr, cc)
    return rr, cc


def last_used(sh):
    filled = [i for i in range(len(sh.df)) if any(_filled(v) for v in sh.df.iloc[i].tolist())]
    return (sh.HEAD + (filled[-1] if filled else 0), sh.df.shape[1] - 1)


ARROWS = {Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0), Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1)}


def handle_key(sh, obj, ev):
    """Return True when the key was handled."""
    if obj is not sh.view or ev.type() != QEvent.KeyPress or sh.view.state() == QTableView.EditingState: return False
    k, mods = ev.key(), ev.modifiers(); ctrl, shift, alt = bool(mods & Qt.ControlModifier), bool(mods & Qt.ShiftModifier), bool(mods & Qt.AltModifier)
    if ev.matches(QKeySequence.Copy): sh.copy(); return True
    if ev.matches(QKeySequence.Paste): sh.paste(); return True
    if ev.matches(QKeySequence.Cut): sh.copy(); sh.clear_cells(); return True
    if k == Qt.Key_Delete: sh.clear_cells(); return True
    if k in ARROWS and ctrl:
        r, c = _cur(sh); _set(sh, *edge(sh, r, c, *ARROWS[k]), extend=shift); return True
    if k in ARROWS and shift and not getattr(sh, "_anchor", None): sh._anchor = sh.view.currentIndex()
    if k in ARROWS and not shift: sh._anchor = None
    if k == Qt.Key_End and ctrl: _set(sh, *last_used(sh), extend=shift); return True
    if k == Qt.Key_Home and ctrl: _set(sh, sh.HEAD, 0, extend=shift); return True
    if k == Qt.Key_Home: _set(sh, _cur(sh)[0], 0, extend=shift); return True
    if k == Qt.Key_End: _set(sh, _cur(sh)[0], sh.model.columnCount() - 1, extend=shift); return True
    if k in (Qt.Key_Return, Qt.Key_Enter) and not (ctrl or alt): move(sh, -1 if shift else 1, 0); return True
    if k == Qt.Key_Tab: move(sh, 0, 1); return True
    if k == Qt.Key_Backtab: move(sh, 0, -1); return True
    if k == Qt.Key_Space and ctrl and not shift:
        cols = sorted({i.column() for i in sh.view.selectionModel().selectedIndexes()} | {_cur(sh)[1]})
        sm = sh.view.selectionModel(); sm.clearSelection()
        for c in cols: sm.select(sh.model.index(0, c), QItemSelectionModel.Select | QItemSelectionModel.Columns)
        return True
    if k == Qt.Key_Space and shift and not ctrl:
        rows = sorted({i.row() for i in sh.view.selectionModel().selectedIndexes()} | {_cur(sh)[0]})
        sm = sh.view.selectionModel(); sm.clearSelection()
        for r in rows: sm.select(sh.model.index(r, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
        return True
    if ctrl and k == Qt.Key_D: sh.fill_down(); return True
    if ctrl and k == Qt.Key_R: sh.fill_right(); return True
    if ctrl and k == Qt.Key_Semicolon: sh.put_text(datetime.date.today().isoformat()); return True
    if ctrl and shift and k in (Qt.Key_Colon,): sh.put_text(datetime.datetime.now().strftime("%H:%M:%S")); return True
    if ctrl and k in (Qt.Key_Plus, Qt.Key_Equal):
        rows = sorted({i.row() - sh.HEAD for i in sh.view.selectionModel().selectedIndexes() if i.row() >= sh.HEAD}) or [max(_cur(sh)[0] - sh.HEAD, 0)]
        sh.insert_rows(rows[0], len(rows)); return True
    if ctrl and k == Qt.Key_Minus:
        sh.delete_rows({i.row() - sh.HEAD for i in sh.view.selectionModel().selectedIndexes() if i.row() >= sh.HEAD}); return True
    if ctrl and k in (Qt.Key_PageDown, Qt.Key_PageUp):
        tabs = sh.book.tabs; n = tabs.count(); tabs.setCurrentIndex((tabs.currentIndex() + (1 if k == Qt.Key_PageDown else -1)) % n)
        nxt = tabs.currentWidget(); QTimer.singleShot(0, nxt.view.setFocus); return True
    return False
