"""PlotBench matrixbooks: windows holding one or more matrix objects.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableView, QTabWidget, QMenu, QInputDialog, QDialog, QFormLayout,
                               QSpinBox, QLineEdit, QDialogButtonBox)

from . import matrix as MX
from .sheets import full, fmt


class MatrixModel(QAbstractTableModel):
    def __init__(self, ms):
        super().__init__(); self.ms = ms

    def rowCount(self, p=QModelIndex()): return self.ms.M.shape[0]
    def columnCount(self, p=QModelIndex()): return self.ms.M.shape[1]

    def data(self, idx, role=Qt.DisplayRole):
        if role == Qt.DisplayRole: return fmt(self.ms.M[idx.row(), idx.column()])
        if role == Qt.EditRole: return full(self.ms.M[idx.row(), idx.column()])
        if role == Qt.TextAlignmentRole: return int(Qt.AlignRight | Qt.AlignVCenter)

    def setData(self, idx, value, role=Qt.EditRole):
        if role != Qt.EditRole: return False
        try: v = float(value) if value.strip() else np.nan
        except ValueError: return False
        self.ms.snap(); self.ms.M[idx.row(), idx.column()] = v; self.dataChanged.emit(idx, idx); self.ms.changed(); return True

    def flags(self, idx): return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def headerData(self, s, orient, role=Qt.DisplayRole):
        if role != Qt.DisplayRole: return None
        xs, ys = MX.axes_of(self.ms.M, self.ms.extent)
        return f"{s + 1}\n{xs[s]:.4g}" if orient == Qt.Horizontal else f"{s + 1}  ({ys[s]:.4g})"

    def refresh(self): self.beginResetModel(); self.endResetModel()


class MatrixSheet(QWidget):
    def __init__(self, book, name, M=None, extent=None):
        super().__init__(); self.book = book; self.name = name
        self.M = np.asarray(M if M is not None else np.full((32, 32), np.nan), float).copy()
        self.extent = list(map(float, extent or [1, self.M.shape[1], 1, self.M.shape[0]]))
        self.formula = ""; self.zlabel = name; self.redo_stack = []
        from .sheets import UndoList
        self.undo_stack = UndoList(self)
        self.view = QTableView(); self.model = MatrixModel(self); self.view.setModel(self.model)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(self.view)

    @property
    def main(self): return self.book.main

    @property
    def label(self): return self.zlabel or self.name

    def snap(self):
        self.undo_stack.append((self.M.copy(), list(self.extent))); del self.undo_stack[:-15]; self.redo_stack.clear()

    def undo(self):
        if self.undo_stack: self.redo_stack.append((self.M.copy(), list(self.extent))); self.M, self.extent = self.undo_stack.pop(); self.changed()

    def redo(self):
        if self.redo_stack: self.undo_stack.append((self.M.copy(), list(self.extent))); self.M, self.extent = self.redo_stack.pop(); self.changed()

    def set(self, M, extent=None):
        self.snap(); self.M = np.asarray(M, float); self.extent = list(map(float, extent or self.extent)); self.changed()

    def changed(self):
        self.model.refresh(); self.main.refresh_matrix_graphs(self)

    def set_formula(self):
        expr, ok = QInputDialog.getText(self, "Set matrix values", "Value = (use x, y from the dimensions, i = row, j = column, numpy "
                                        "functions e.g. sin(x)*cos(y), exp(-(x**2+y**2)))", text=self.formula or "sin(x)*cos(y)")
        if ok and expr.strip():
            self.formula = expr.strip(); self.set(MX.from_formula(self.formula, *self.M.shape, self.extent))

    def dimensions(self):
        d = QDialog(self); d.setWindowTitle("Matrix dimensions and coordinates"); f = QFormLayout(d)
        rows, cols = QSpinBox(), QSpinBox()
        for s, v in ((rows, self.M.shape[0]), (cols, self.M.shape[1])): s.setRange(1, 20000); s.setValue(v)
        ex = [QLineEdit(f"{v:.10g}") for v in self.extent]; zl = QLineEdit(self.zlabel)
        for lab, w in (("Rows (Y)", rows), ("Columns (X)", cols), ("X from (first column)", ex[0]), ("X to (last column)", ex[1]),
                       ("Y from (first row)", ex[2]), ("Y to (last row)", ex[3]), ("Z label (long name, units)", zl)): f.addRow(lab, w)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if not d.exec(): return
        r, c = rows.value(), cols.value()
        M = self.M if (r, c) == self.M.shape else MX.resample(self.M, r, c) if np.isfinite(self.M).any() else np.full((r, c), np.nan)
        self.zlabel = zl.text(); self.set(M, [float(e.text()) for e in ex])

    def state(self): return {"name": self.name, "extent": self.extent, "formula": self.formula, "zlabel": self.zlabel}


class MatrixBook(QWidget):
    kind = "matrix"

    def __init__(self, main, name, M=None, extent=None, sheet_name="MSheet1"):
        super().__init__(); self.main = main; self.setWindowTitle(name)
        self.tabs = QTabWidget(); self.tabs.setTabPosition(QTabWidget.South)
        self.tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu); self.tabs.tabBar().customContextMenuRequested.connect(self.tab_menu)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(self.tabs)
        self.add_sheet(sheet_name, M, extent)

    @property
    def name(self): return self.windowTitle()

    @property
    def sheets(self): return [self.tabs.widget(i) for i in range(self.tabs.count())]

    def current(self): return self.tabs.currentWidget()
    def sheet(self, name): return next((s for s in self.sheets if s.name == name), self.sheets[0])

    def add_sheet(self, name=None, M=None, extent=None):
        names = {s.name for s in self.sheets}
        if not name or name in names:
            k = len(names) + 1
            while f"MSheet{k}" in names: k += 1
            name = f"MSheet{k}" if not name else f"{name}_{k}"
        ms = MatrixSheet(self, name, M, extent); self.tabs.addTab(ms, name); self.tabs.setCurrentWidget(ms)
        self.main.refresh_explorer(); return ms

    def tab_menu(self, pos):
        i = self.tabs.tabBar().tabAt(pos); m = QMenu(self); m.addAction("Add matrix object", lambda: self.add_sheet())
        if i >= 0 and self.tabs.count() > 1: m.addAction("Delete matrix object", lambda: (self.tabs.removeTab(i), self.main.refresh_explorer()))
        m.exec(self.tabs.tabBar().mapToGlobal(pos))

    def state(self): return {"kind": "matrix", "name": self.name, "sheets": [s.state() for s in self.sheets]}
