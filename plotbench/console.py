"""PlotBench Python console and scripting API.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Scripts run locally with full Python, like any script the user runs themselves.
"""
import code
import contextlib
import io
import traceback

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit, QLabel, QHBoxLayout

from . import analysis as A
from . import matrix as MX
from .sheets import read_with_options

HELP = """PlotBench scripting (Python). Objects: pb (this API), np (numpy), pd (pandas), A (analysis), MX (matrix tools), app.
  pb.books(), pb.graphs()                         list window names
  pb.sheet(book=None, name=None)                  a worksheet (active one by default); .df is its pandas DataFrame
  pb.col("B")  /  pb.set_col("C", values)         read a column (masked cells = NaN) / add or replace a column
  pb.new_book({"x": [...], "y": [...]}, "Name")   new workbook from a dict or DataFrame
  pb.import_file(path, sep=",", skip=0, names_line=1, units_line=0)
  pb.plot("Scatter", "A", ["B", "C"])             any type from the Plot menu; returns the graph
  pb.style(graph, title="...", yscale="log")      change graph properties (same keys as the Graph Properties dialog)
  pb.fit("Gaussian", x, y, fixed={"y0": 0})       nonlinear fit; pb.fit_poly(x, y, order)
  pb.new_matrix(M, "Name", extent=[x0, x1, y0, y1]);  pb.matrix_plot("Filled Contour")
  pb.export(graph, "fig.png");  pb.save_project(path);  pb.open_project(path)
Example:  for c in ["B", "C"]: print(c, pb.fit("Gaussian", pb.col("A"), pb.col(c))["params"])"""


class ScriptAPI:
    def __init__(self, main): self.m = main

    def help(self): print(HELP)
    def books(self): return [w.name for w in self.m.windows() if w.kind == "book"]
    def graphs(self): return [w.name for w in self.m.windows() if w.kind == "graph"]

    def sheet(self, book=None, name=None):
        if book is None:
            b = self.m.active("book")
            if b is None: raise RuntimeError("No workbook open.")
            return b.current() if name is None else b.sheet(name)
        return self.m.sheet_ref(book, name)

    def matrix(self, book=None, name=None):
        if book is None:
            b = self.m.active("matrix")
            if b is None: raise RuntimeError("No matrixbook open.")
            return b.current()
        return self.m.matrix_ref(book, name)

    def col(self, name, book=None, sheet=None): return self.sheet(book, sheet).arr(name)

    def set_col(self, name, values, book=None, sheet=None):
        sh = self.sheet(book, sheet); values = np.asarray(values)
        if name in sh.df.columns:
            sh.snap()
            if len(values) > len(sh.df): sh.add_rows(len(values) - len(sh.df), snap=False)
            col = np.full(len(sh.df), np.nan, dtype=object if values.dtype == object else float); col[:len(values)] = values
            sh.df[name] = col; sh.model.refresh()
        else: sh.add_column(name, values)
        self.m.refresh_graphs(sh); return sh

    def new_book(self, data, name=None):
        return self.m.new_book(pd.DataFrame(data), name or self.m.uniq("Book")).current()

    def import_file(self, path, **opts):
        df, meta = read_with_options(path, **opts); import pathlib
        return self.m.new_book(df, pathlib.Path(path).stem, meta).current()

    def plot(self, kind, x, ys, book=None, sheet=None):
        sh = self.sheet(book, sheet); ys = [ys] if isinstance(ys, str) else list(ys)
        return self.m.new_graph(sh, kind, x, ys)

    def style(self, graph, **kw):
        g = graph if hasattr(graph, "spec") else self.m.win(graph); g.set_style({**g.spec["style"], **kw}); return g

    def fit(self, model, x, y, **kw): return A.fit_model(x, y, model, **kw)
    def fit_poly(self, x, y, order=1): return A.fit_polynomial(x, y, order)

    def new_matrix(self, M, name=None, extent=None): return self.m.new_matrix(np.asarray(M, float), name, extent).current()

    def matrix_plot(self, kind="Image / Heat Map", book=None, name=None):
        return self.m.new_matrix_graph(self.matrix(book, name), kind)

    def export(self, graph, path):
        g = graph if hasattr(graph, "export") else self.m.win(graph); g.export(path); return path

    def save_project(self, path): self.m.project_path = path; self.m.save_project(); return path
    def open_project(self, path): self.m.open_project(path)


class ConsoleWidget(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main; self.api = ScriptAPI(main)
        self.ns = {"pb": self.api, "np": np, "pd": pd, "A": A, "MX": MX, "app": main}
        self.interp = code.InteractiveConsole(self.ns); self.history = []; self.hpos = 0; self.more = False
        self.out = QPlainTextEdit(); self.out.setReadOnly(True); mono = QFont("Consolas"); mono.setStyleHint(QFont.Monospace)
        self.out.setFont(mono); self.inp = QLineEdit(); self.inp.setFont(mono); self.prompt = QLabel(">>>")
        self.inp.returnPressed.connect(self.enter); self.inp.installEventFilter(self)
        row = QHBoxLayout(); row.addWidget(self.prompt); row.addWidget(self.inp)
        lay = QVBoxLayout(self); lay.setContentsMargins(2, 2, 2, 2); lay.addWidget(self.out); lay.addLayout(row)
        self.write("PlotBench Python console. Type pb.help() for the scripting commands.\n")

    def write(self, text):
        self.out.moveCursor(QTextCursor.MoveOperation.End); self.out.insertPlainText(text); self.out.ensureCursorVisible()

    def run(self, fn):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try: result = fn()
            except SystemExit: result = None
            except Exception: traceback.print_exc(); result = None
        self.write(buf.getvalue()); return result

    def enter(self):
        line = self.inp.text(); self.inp.clear()
        if line.strip(): self.history.append(line)
        self.hpos = len(self.history)
        self.write(("... " if self.more else ">>> ") + line + "\n")
        self.more = bool(self.run(lambda: self.interp.push(line)))
        self.prompt.setText("..." if self.more else ">>>")

    def exec_source(self, source, filename="<script>"):
        self.write(f"# running {filename}\n")
        return self.run(lambda: exec(compile(source, filename, "exec"), self.ns))

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is self.inp and ev.type() == QEvent.KeyPress and self.history:
            if ev.key() == Qt.Key_Up: self.hpos = max(0, self.hpos - 1)
            elif ev.key() == Qt.Key_Down: self.hpos = min(len(self.history), self.hpos + 1)
            else: return False
            self.inp.setText(self.history[self.hpos] if self.hpos < len(self.history) else ""); return True
        return False
