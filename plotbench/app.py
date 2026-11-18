"""PlotBench: a light worksheet, plotting and data-analysis desktop app.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import json
import sys
import zipfile
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("QtAgg")
from PySide6.QtCore import Qt, QCoreApplication, QEvent, QTimer
from PySide6.QtGui import QAction, QKeySequence, QCursor
from PySide6.QtWidgets import (QLabel, 
    QApplication, QMainWindow, QMdiArea, QFileDialog, QInputDialog, QMessageBox, QTextEdit, QDialog, QFormLayout,
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QDialogButtonBox, QCheckBox, QDockWidget, QTreeWidget,
    QTreeWidgetItem, QMenu, QToolBar, QListWidget, QListWidgetItem, QVBoxLayout, QAbstractItemView, QWidget)

from . import analysis as A
from . import plots as P
from .sheets import Workbook, ImportWizard, DESIG, fmt, read_with_options
from .tools import FitDialog, BatchFilesDialog, run_fit
from .matrixui import MatrixBook
from . import matrix as MX
from .console import ConsoleWidget
from . import analysis2 as B
from . import analysis3 as C
from . import analysis4 as D
from . import analysis5 as E
from . import analysis6 as F
from . import analysis7 as G7
from . import analysis8 as H8
from .startpage import StartPage, make_template, app_icon, asset
from . import plots2  # noqa: F401  (registers more plot types)
from .ui3 import Digitizer
import html as _html
import os
import tempfile
from . import formats as FM
from .ui2 import PeakAnalyzer, DatasetDialog
import uuid
from . import sheets as SH
from .graphs import (GraphWindow, StyleDialog, LayoutWindow, LayoutDialog, save_template, choose_template,
                     set_default_theme, user_dir)

APP = "PlotBench"
VERSION = "1.30.3"


class ReportWindow(QTextEdit):
    kind = "report"

    def __init__(self, title, html):
        super().__init__(); self.setWindowTitle(title); self.setReadOnly(True)
        if "pb-header" not in html:  # small PlotBench header on new reports (kept when a project is reopened)
            logo = Path(asset("logo32.png")).as_uri()
            html = (f"<p class='pb-header' style='color:#16325c'><img src='{logo}' width='20' height='20' style='vertical-align:middle'> "
                    f"<b>PlotBench</b> <span style='color:gray'>report</span></p>") + html
        self.setHtml(html)

    @property
    def name(self): return self.windowTitle()

    def state(self): return {"kind": "report", "name": self.name, "html": self.toHtml()}


def table_html(title, rows, header=("Quantity", "Value")):
    esc = lambda v: _html.escape(fmt(v))  # data from files must not inject markup into reports
    body = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in r) + "</tr>" for r in rows)
    head = "".join(f"<th>{_html.escape(str(h))}</th>" for h in header)
    title = _html.escape(str(title))
    return (f"<h3>{title}</h3><table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse'>"
            f"<tr style='background:#e8eef7'>{head}</tr>{body}</table><br>")


def dict_html(title, d): return table_html(title, list(d.items()))


class FormDialog(QDialog):
    def __init__(self, parent, title, fields):
        super().__init__(parent); self.setWindowTitle(title); lay = QFormLayout(self); self.w = {}
        for label, widget in fields: lay.addRow(label, widget); self.w[label] = widget
        self.bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb.accepted.connect(self.accept); self.bb.rejected.connect(self.reject); lay.addRow(self.bb)

    def live_graph(self, graph, mutate):
        """Show mutate(graph, self) on the graph while the dialog is open; OK or Apply keeps it as one undo step, Cancel undoes it."""
        from .live import graph_live, add_pane
        self.bb.hide(); lp = graph_live(self, graph, lambda g: mutate(g, self))
        self.layout().insertRow(0, add_pane(lp, graph)); self.layout().addRow(lp.bar()); lp.start(); lp.run(); self._live = lp; return self

    def live_on(self, graph, make_item):
        """Preview make_item(self) as an annotation on graph while the dialog is open; the caller adds it for real after OK."""
        if graph is None: return self
        from .live import graph_live, add_pane
        self.bb.hide(); lp = graph_live(self, graph, lambda g: g.spec.setdefault("annotations", []).append(make_item(self)), commit=False)
        self.layout().insertRow(0, add_pane(lp, graph)); self.layout().addRow(lp.bar()); lp.start(); lp.run(); self._live = lp; return self

    def val(self, label):
        w = self.w[label]
        if isinstance(w, QComboBox): return w.currentText()
        if isinstance(w, (QSpinBox, QDoubleSpinBox)): return w.value()
        if isinstance(w, QCheckBox): return w.isChecked()
        return w.text()


def read_text_table(fn):
    """Text table with the delimiter found automatically. Columns lined up with spaces are read as one separator per gap
    (a single-space delimiter would give empty columns for every extra space)."""
    import csv
    with open(fn, encoding="utf-8", errors="replace") as f:
        lines = [l for l in f.read(50000).splitlines() if l.strip() and not l.lstrip().startswith("#")]
    try: sep = csv.Sniffer().sniff("\n".join(lines[:50]), delimiters=",;\t| ").delimiter
    except csv.Error: sep = None
    if sep == " " or (sep is None and lines and len(lines[0].split()) > 1): sep = r"\s+"
    return pd.read_csv(fn, sep=sep, engine="python", comment="#")


def combo(items, current=None):
    c = QComboBox(); c.addItems([str(i) for i in items])
    if current is not None: c.setCurrentText(str(current))
    return c


def spin(lo, hi, v, dbl=False):
    s = QDoubleSpinBox() if dbl else QSpinBox(); s.setRange(lo, hi); s.setValue(v)
    if dbl: s.setDecimals(6)
    return s


KIND_LABEL = {"book": "Workbooks", "matrix": "Matrixbooks", "graph": "Graphs", "layout": "Layouts", "report": "Reports"}
SHEETED = ("book", "matrix")


def load_settings():
    try: return {**SH.PREFS, "recent": [], **json.loads((user_dir() / "settings.json").read_text())}
    except (OSError, ValueError): return {**SH.PREFS, "recent": []}


def save_settings(st):
    try: (user_dir() / "settings.json").write_text(json.dumps(st, indent=1))
    except OSError: pass


def _num_or_text(v):
    """'1.5' -> 1.5; text that would change as a number ('001', '1e3') stays text, and so do 'nan', 'inf' and the like."""
    try: f = float(v)
    except ValueError: return v
    if not np.isfinite(f): return v
    return f if repr(f) == v or f"{f:.17g}" == v else v


PROJECT_LIMITS = dict(total=4 * 2**30, meta=16 * 2**20, members=10000)  # uncompressed bytes, project.json bytes, parts


def read_project(fn):
    """Open a .pbp project and decode all of it: (meta, {csv name: DataFrame}, {npy name: array}). Raises ValueError for a damaged
    or oversized file before the caller touches the open windows. Text columns keep labels such as NA or NULL as text."""
    import io as _io
    with zipfile.ZipFile(fn) as z:
        info = z.infolist(); names = [i.filename for i in info]
        if len(info) > PROJECT_LIMITS["members"]: raise ValueError("Project file has too many parts.")
        if len(set(names)) != len(names): raise ValueError("Project file is damaged (duplicate parts).")
        if sum(i.file_size for i in info) > PROJECT_LIMITS["total"]: raise ValueError("Project file is too large to open (over 4 GB of data).")
        if "project.json" not in names: raise ValueError("Not a PlotBench project file.")
        if z.getinfo("project.json").file_size > PROJECT_LIMITS["meta"]: raise ValueError("Project file is damaged (project.json too large).")
        try: meta = json.loads(z.read("project.json"))
        except (ValueError, UnicodeDecodeError) as e: raise ValueError(f"Project file is damaged ({e}).") from None
        if not isinstance(meta, dict) or not isinstance(meta.get("windows"), list) or \
                not all(isinstance(w, dict) and "kind" in w and "name" in w for w in meta["windows"]):
            raise ValueError("Not a PlotBench project file.")
        frames, arrays = {}, {}
        try:
            for st in meta["windows"]:
                if st["kind"] == "book":
                    for sst in st.get("sheets") or [{**st, "name": "Sheet1"}]:
                        n = sst["csv"]
                        if n not in names: raise ValueError(f"Project file is damaged (missing {n}).")
                        tc = [c for c in sst.get("text_cols", [])]; text = z.read(n).decode()
                        if tc:  # text columns: only a blank cell is missing, so labels like NA, NULL or nan stay text
                            df = pd.read_csv(StringIO(text), dtype={c: str for c in tc}, keep_default_na=False, na_values={c: [""] for c in tc})
                            for c in df.columns:
                                if c not in tc and df[c].dtype == object: df[c] = pd.read_csv(StringIO(text), usecols=[c])[c]
                            for c in tc:  # plain numbers back to floats, any other text kept exactly
                                if c in df.columns: df[c] = df[c].map(lambda v: _num_or_text(v) if isinstance(v, str) else v).astype(object)
                        else: df = pd.read_csv(StringIO(text))
                        frames[n] = df
                elif st["kind"] == "matrix":
                    for sst in st["sheets"]:
                        n = sst["npy"]
                        if n not in names: raise ValueError(f"Project file is damaged (missing {n}).")
                        arrays[n] = np.load(_io.BytesIO(z.read(n)), allow_pickle=False); sst["extent"]
        except ValueError: raise
        except Exception as e: raise ValueError(f"Project file is damaged ({type(e).__name__}: {e}).") from None
    return meta, frames, arrays


class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f"{APP} {VERSION}"); self.resize(1400, 860)
        self.setWindowIcon(app_icon())
        self.mdi = QMdiArea(); self.mdi.setViewMode(QMdiArea.TabbedView); self.mdi.setTabsClosable(True)
        self.mdi.setTabsMovable(True); self.setCentralWidget(self.mdi); self.project_path = None; self.counter = {}
        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self.explorer_open)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu); self.tree.customContextMenuRequested.connect(self.explorer_menu)
        dock = QDockWidget("Project Explorer", self); dock.setWidget(self.tree); self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.explorer_dock = dock
        self.mdi.subWindowActivated.connect(lambda _: self.refresh_explorer())
        self.mdi.subWindowActivated.connect(lambda w: w is not None and getattr(self, "_start_page", None) is not None and self._start_page.reject())
        self.settings = load_settings(); SH.PREFS.update({k: self.settings[k] for k in SH.PREFS})
        self.console = ConsoleWidget(self)
        cd = QDockWidget("Python Console", self); cd.setWidget(self.console); self.addDockWidget(Qt.BottomDockWidgetArea, cd)
        cd.hide(); self.console_dock = cd
        self.folders = []; self.pending_ops = []
        self.op_timer = QTimer(self); self.op_timer.setSingleShot(True); self.op_timer.setInterval(250); self.op_timer.timeout.connect(self.run_ops)
        self.script_bar = QToolBar("User scripts", self); self.script_bar.setObjectName("userscripts"); self.addToolBar(self.script_bar)
        self.graph_timer = QTimer(self); self.graph_timer.setSingleShot(True); self.graph_timer.setInterval(300)
        self.graph_timer.timeout.connect(self.flush_graphs); self.pending_graphs = []; self._bulk_close = False
        self.setAcceptDrops(True)
        self.build_menus(); self.set_theme(self.settings.get("theme", "light"), save=False)
        self.new_book(); self.dirty = False; self.statusBar().showMessage("Ready")

    # ---- window bookkeeping
    def uniq(self, prefix):
        names = {w.name for w in self.windows()}
        while True:
            self.counter[prefix] = self.counter.get(prefix, 0) + 1; n = f"{prefix}{self.counter[prefix]}"
            if n not in names: return n

    def kind_icon(self, kind):
        from .toolbars import _icon, draw_tool, draw_plot
        theme = getattr(self, "_theme", "light")
        return {"book": lambda: _icon(draw_tool("addcol"), theme), "matrix": lambda: _icon(draw_tool("matrix"), theme),
                "graph": lambda: _icon(draw_plot("Line + Symbol"), theme), "layout": lambda: _icon(draw_tool("layout"), theme),
                "report": lambda: _icon(draw_tool("stats"), theme)}.get(kind, app_icon)()

    def add_win(self, w):
        sub = self.mdi.addSubWindow(w); sub.resize(760, 540); sub.setWindowIcon(self.kind_icon(getattr(w, "kind", ""))); w.show(); self.mdi.setActiveSubWindow(sub)
        sub.installEventFilter(self); sub.destroyed.connect(lambda *_: self.refresh_explorer()); self.refresh_explorer(); self.mark_dirty()
        return w

    def mark_dirty(self):
        self.dirty = True
        t = self.windowTitle()
        if not t.endswith(" *"): self.setWindowTitle(t + " *")

    def clear_dirty(self):
        self.dirty = False; self.setWindowTitle(self.windowTitle().rstrip(" *"))

    def schedule_graphs(self, sheet):
        self.mark_dirty()
        if sheet not in self.pending_graphs: self.pending_graphs.append(sheet)
        self.graph_timer.start()

    def flush_graphs(self):
        sheets, self.pending_graphs = self.pending_graphs, []
        for sh in sheets:
            try: self.refresh_graphs(sh)
            except RuntimeError: pass  # sheet was closed meanwhile

    def eventFilter(self, obj, ev):
        """Ask before closing a workbook or matrixbook window: its data would be lost from the project."""
        if ev.type() == QEvent.Close and not self._bulk_close and hasattr(obj, "widget") and obj.widget() is not None \
                and getattr(obj.widget(), "kind", "") in SHEETED:
            w = obj.widget()
            if QMessageBox.question(self, APP, f"Close {w.name}? Its data will be removed from the project "
                                    "(graphs made from it will show that their data is gone).") != QMessageBox.Yes:
                ev.ignore(); return True
            self.mark_dirty()
        return False

    def confirm_discard(self, action="closing"):
        """Save / Discard / Cancel when there is unsaved work. True means go ahead (saved or discarded)."""
        if not (self.dirty and self.windows()): return True
        r = QMessageBox.question(self, APP, f"Save changes to the project before {action}?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Cancel: return False
        if r == QMessageBox.Save:
            self.safe(self.save_project)
            return not self.dirty  # save was cancelled or failed: keep the work
        return True

    def closeEvent(self, ev):
        if not self.confirm_discard("closing"): return ev.ignore()
        self._bulk_close = True; ev.accept()

    def dragEnterEvent(self, ev):
        from .sheets import COLUMNS_MIME
        if ev.mimeData().hasUrls() or ev.mimeData().hasFormat(COLUMNS_MIME): ev.acceptProposedAction()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, ev):
        from .sheets import COLUMNS_MIME
        if ev.mimeData().hasFormat(COLUMNS_MIME):  # columns dropped on empty space: a new graph of them
            import json
            d = json.loads(bytes(ev.mimeData().data(COLUMNS_MIME)).decode())
            return self.safe(lambda: self.new_graph(self.sheet_ref(d["book"], d["sheet"]), "Line + Symbol", d["x"], d["ys"]))
        for url in ev.mimeData().urls(): self.safe(lambda f=url.toLocalFile(): self.open_any(f))

    def open_any(self, fn):
        """Open a dropped file by type. Python scripts are never run from a drop."""
        ext = Path(fn).suffix.lower()
        if ext == ".pbp": return self.open_project(fn)
        if ext in (".csv", ".txt", ".dat", ".tsv", ".prn", ".asc"): return self.new_book(read_text_table(fn), Path(fn).stem)
        if ext in (".xlsx", ".xls"): return self.import_excel(fn)
        if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"): return self.import_image(fn, "Grayscale")
        if ext in (".h5", ".hdf5", ".he5", ".nc", ".nc4", ".cdf", ".mat"): return self.import_arrays(fn)
        if ext in (".jdx", ".dx", ".jcamp"): return self.import_jcamp(fn)
        if ext in (".db", ".sqlite", ".sqlite3"): return self.import_sqlite(fn)
        QMessageBox.information(self, APP, f"PlotBench does not open {ext or 'this kind of'} files.")

    def windows(self):
        return [s.widget() for s in self.mdi.subWindowList() if s.widget() is not None]

    def win(self, name): return next((w for w in self.windows() if w.name == name), None)

    def book_by_name(self, n): return next(w for w in self.windows() if w.kind == "book" and w.name == n)

    def sheet_ref(self, book, sheet=None): return self.book_by_name(book).sheet(sheet)

    def matrix_ref(self, book, sheet=None):
        return next(w for w in self.windows() if w.kind == "matrix" and w.name == book).sheet(sheet)

    def need_matrix(self):
        m = self.active("matrix")
        if m is None: QMessageBox.warning(self, APP, "Open or create a matrixbook first."); return None
        return m.current()

    def new_matrix(self, M=None, name=None, extent=None):
        return self.add_win(MatrixBook(self, name or self.uniq("MBook"), M, extent))

    def new_matrix_graph(self, ms, kind):
        g = self.add_win(GraphWindow(self, self.uniq("Graph"), {"source": "matrix", "type": kind, "book": ms.book.name,
                                                               "sheet": ms.name, "x": None, "ys": [], "extra": {}}))
        g.draw(); return g

    def refresh_matrix_graphs(self, ms):
        for w in self.windows():
            if w.kind == "graph" and w.spec.get("source") == "matrix" and w.spec.get("book") == ms.book.name \
                    and w.spec.get("sheet", ms.name) == ms.name:
                try: w.draw()
                except Exception as e: self.statusBar().showMessage(f"{w.name}: {e}", 6000)

    def active(self, kind):
        s = self.mdi.activeSubWindow(); w = s.widget() if s else None
        if w is not None and w.kind == kind: return w
        same = [x for x in self.windows() if x.kind == kind]
        return same[-1] if same else None

    def need_book(self):
        """Active sheet of the active workbook."""
        b = self.active("book")
        if b is None: QMessageBox.warning(self, APP, "Open or create a workbook first."); return None
        return b.current()

    def report(self, title, html):
        names = {w.name for w in self.windows()}; t, k = title, 2
        while t in names: t = f"{title} ({k})"; k += 1
        return self.add_win(ReportWindow(t, html))

    def act(self, menu, text, slot, shortcut=None):
        a = QAction(text, self); a.triggered.connect(lambda checked=False: self.run_command(text, slot))
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        menu.addAction(a); return a

    def run_command(self, text, slot):
        if text not in ("Undo", "Redo", "Repeat Last Command"): self.last_command = (text, slot)
        self.current_command = text.rstrip(".")  # columns made by this command record it (formula bar, header tooltip)
        try: self.safe(slot)
        finally: self.current_command = None

    def repeat_last(self):
        lc = getattr(self, "last_command", None)
        if lc: self.statusBar().showMessage(f"Repeat: {lc[0]}", 3000); self.safe(lc[1])

    def show_shortcuts(self):
        from .keys import SHORTCUTS
        rows = "".join(f"<tr><td colspan='2' style='padding-top:8px'><b>{_html.escape(k)}</b></td></tr>" if not a else
                       f"<tr><td style='padding-right:18px'><code>{_html.escape(k)}</code></td><td>{_html.escape(a)}</td></tr>" for k, a in SHORTCUTS)
        d = QDialog(self); d.setWindowTitle("Keyboard Shortcuts"); d.resize(640, 720); t = QTextEdit(); t.setReadOnly(True)
        t.setHtml(f"<h3>PlotBench keyboard shortcuts</h3><table>{rows}</table>"); lay = QFormLayout(d); lay.addRow(t)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(d.reject); lay.addRow(bb); d.exec()

    def safe(self, slot):
        try: slot()
        except Exception as e: QMessageBox.critical(self, APP, f"{type(e).__name__}: {e}")

    # ---- project explorer
    def refresh_explorer(self):
        if not hasattr(self, "tree"): return
        try: self.tree.clear(); wins = self.windows()
        except RuntimeError: return  # app shutting down
        groups = {}
        for k, lab in KIND_LABEL.items():
            groups[k] = QTreeWidgetItem(self.tree, [lab]); groups[k].setExpanded(True)
        fitems = {}
        for f in getattr(self, "folders", []):
            fi = QTreeWidgetItem(self.tree, [f"[Folder] {f}"]); fi.setData(0, Qt.UserRole, ("__folder__", f)); fi.setExpanded(True); fitems[f] = fi
        for w in wins:
            folder = getattr(w, "folder", "")
            parent = fitems.get(folder) or groups[w.kind]
            it = QTreeWidgetItem(parent, [w.name if parent is groups.get(w.kind) else f"{w.name}  ({KIND_LABEL[w.kind][:-1].lower()})"])
            it.setData(0, Qt.UserRole, (w.name, None))
            if w.kind in SHEETED:
                for sh in w.sheets:
                    s = QTreeWidgetItem(it, [sh.name]); s.setData(0, Qt.UserRole, (w.name, sh.name))
                it.setExpanded(True)

    def explorer_open(self, item, _col=0):
        ref = item.data(0, Qt.UserRole)
        if not ref or ref[0] == "__folder__": return
        w = self.win(ref[0])
        if w is None: return
        for s in self.mdi.subWindowList():
            if s.widget() is w: self.mdi.setActiveSubWindow(s)
        if ref[1] and w.kind in SHEETED: w.tabs.setCurrentWidget(w.sheet(ref[1]))

    def explorer_menu(self, pos):
        item = self.tree.itemAt(pos); ref = item.data(0, Qt.UserRole) if item else None
        m = QMenu(self)
        if ref and ref[0] == "__folder__":
            m.addAction("Rename folder...", lambda: self.safe(lambda: self.rename_folder(ref[1])))
            m.addAction("Delete folder (contents move to the top level)", lambda: self.safe(lambda: self.delete_folder(ref[1])))
        elif ref and not ref[1]:
            m.addAction("Open", lambda: self.explorer_open(item))
            m.addAction("Rename...", lambda: self.safe(lambda: self.rename_window(ref[0])))
            m.addAction("Move to folder...", lambda: self.safe(lambda: self.move_to_folder(ref[0])))
            m.addAction("Delete", lambda: self.safe(lambda: self.delete_window(ref[0])))
        m.addSeparator(); m.addAction("New folder...", lambda: self.safe(self.new_folder))
        m.exec(self.tree.mapToGlobal(pos))

    def new_folder(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New folder", "Folder name:")
            if not ok: return
        name = name.strip()
        if name and name not in self.folders: self.folders.append(name); self.refresh_explorer()
        return name

    def move_to_folder(self, wname, folder=None):
        if folder is None:
            folder, ok = QInputDialog.getItem(self, "Move to folder", "Folder (type a new name to create one):",
                                              ["(top level)"] + self.folders, 0, True)
            if not ok: return
        folder = "" if folder in ("", "(top level)") else self.new_folder(folder) or folder
        self.win(wname).folder = folder; self.refresh_explorer()

    def rename_folder(self, old):
        n, ok = QInputDialog.getText(self, "Rename folder", "New name:", text=old)
        if not ok or not n.strip() or n in self.folders: return
        self.folders[self.folders.index(old)] = n
        for w in self.windows():
            if getattr(w, "folder", "") == old: w.folder = n
        self.refresh_explorer()

    def delete_folder(self, name):
        for w in self.windows():
            if getattr(w, "folder", "") == name: w.folder = ""
        self.folders.remove(name); self.refresh_explorer()

    def rename_window(self, old):
        w = self.win(old)
        n, ok = QInputDialog.getText(self, "Rename", "New name:", text=old)
        if not ok or not n or n == old: return
        if self.win(n): raise ValueError(f"'{n}' already exists")
        if w.kind in SHEETED:
            for g in self.windows():
                if g.kind == "graph" and g.spec.get("book") == old and (g.spec.get("source") == "matrix") == (w.kind == "matrix"):
                    g.spec["book"] = n
        if w.kind == "graph":
            for L in self.windows():
                if L.kind == "layout": L.spec["graphs"] = [n if x == old else x for x in L.spec["graphs"]]
                if L.kind == "graph":
                    for ins in L.spec.get("insets", []):
                        if ins.get("graph") == old: ins["graph"] = n
        if w.kind == "book":
            for g in self.windows():
                if g.kind == "graph":
                    for a in g.spec.get("annotations", []):
                        if a.get("book") == old: a["book"] = n
        w.setWindowTitle(n); self.refresh_explorer()

    def rename_refs(self, book, sheet, new_book, new_sheet):
        for g in self.windows():
            if g.kind != "graph": continue
            if g.spec.get("book") == book and g.spec.get("sheet") == sheet: g.spec["book"], g.spec["sheet"] = new_book, new_sheet
            for a in g.spec.get("annotations", []):
                if a.get("book") == book and a.get("sheet") == sheet: a["book"], a["sheet"] = new_book, new_sheet

    def rename_column_refs(self, sh, old, new):
        """A column was renamed: follow it in graphs, cross-sheet series and auto-recalculating fits."""
        for g in self.windows():
            if g.kind != "graph": continue
            if g.spec.get("book") == sh.book.name and g.spec.get("sheet", sh.name) == sh.name:
                if g.spec.get("x") == old: g.spec["x"] = new
                g.spec["ys"] = [new if y == old else y for y in g.spec.get("ys", [])]
            for a in g.spec.get("annotations", []):
                if a.get("book") == sh.book.name and a.get("sheet") == sh.name:
                    for k in ("x", "y"):
                        if a.get(k) == old: a[k] = new
        for op in sh.ops:
            for k in ("x", "y", "fit_col", "res_col"):
                if op.get(k) == old: op[k] = new
            if (op.get("cfg") or {}).get("weight_col") == old: op["cfg"]["weight_col"] = new

    def delete_window(self, name):
        w = self.win(name)
        if QMessageBox.question(self, APP, f"Delete {name}? This cannot be undone.") != QMessageBox.Yes: return
        for s in self.mdi.subWindowList():
            if s.widget() is w: s.close()
        self.refresh_explorer()

    # ---- menus
    def build_menus(self):
        mb = self.menuBar()
        f = mb.addMenu("&File")
        self.act(f, "New Workbook", self.new_book, "Ctrl+N")
        self.act(f, "Open Project...", self.open_project, "Ctrl+O")
        self.act(f, "Save Project", self.save_project, "Ctrl+S")
        self.act(f, "Save Project As...", lambda: self.save_project(True))
        f.addSeparator()
        self.act(f, "Import Wizard (text files)...", self.import_wizard, "Ctrl+I")
        self.act(f, "Quick Import CSV / TXT...", self.import_text)
        self.act(f, "Import Excel...", self.import_excel)
        self.act(f, "Import Image as Matrix...", self.import_image)
        self.act(f, "Import HDF5 / NetCDF / MATLAB (.h5 .nc .mat)...", self.import_arrays)
        self.act(f, "Import JCAMP-DX Spectrum (.jdx .dx)...", self.import_jcamp)
        self.act(f, "Import from SQLite Database...", self.import_sqlite)
        self.act(f, "Export Worksheet (CSV)...", self.export_csv)
        self.act(f, "Export Workbook to Excel (all sheets)...", self.export_excel)
        self.act(f, "Export Worksheet as LaTeX Table (booktabs)...", self.export_latex)
        self.act(f, "Export All Graphs and Layouts...", self.export_all_graphs)
        self.act(f, "Export All Graphs to One Multi-page PDF...", self.export_pdf_book)
        self.act(f, "Export Report (HTML or PDF)...", self.export_report)
        self.act(f, "Export Graph / Layout (PNG/SVG/PDF/TIFF/EPS)...", self.export_graph, "Ctrl+E")
        f.addSeparator()
        self.act(f, "Run Python Script...", self.run_script)
        self.recent_menu = f.addMenu("Recent Projects"); self.fill_recent()
        f.addSeparator(); self.act(f, "Exit", self.close)

        e = mb.addMenu("&Edit")
        self.act(e, "Undo", self.undo, "Ctrl+Z"); self.act(e, "Redo", self.redo, "Ctrl+Y")
        self.act(e, "Repeat Last Command", self.repeat_last, "F4")
        e.addSeparator()
        self.act(e, "Copy Cells (Ctrl+C in a sheet)", lambda: self.need_book() and self.need_book().copy())
        self.act(e, "Paste Cells (Ctrl+V in a sheet)", lambda: self.need_book() and self.need_book().paste())
        self.act(e, "Clear Selected Cells (Delete)", lambda: self.need_book() and self.need_book().clear_cells())
        self.act(e, "Copy Graph to Clipboard", self.copy_graph, "Ctrl+Shift+C")
        e.addSeparator(); self.act(e, "Preferences...", self.preferences)

        v = mb.addMenu("&View")
        v.addAction(self.explorer_dock.toggleViewAction())
        pc = self.console_dock.toggleViewAction(); pc.setShortcut(QKeySequence("Ctrl+Shift+P")); v.addAction(pc)
        v.addSeparator(); self.dark_action = QAction("Dark Theme", self); self.dark_action.setCheckable(True); self.dark_action.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.dark_action.toggled.connect(lambda on: self.set_theme("dark" if on else "light")); v.addAction(self.dark_action)
        self.toolbar_menu = v.addMenu("Toolbars")
        rb = QAction("Ribbon Toolbar Layout (tabs at the top; untick for the classic side bars)", self); rb.setCheckable(True)
        rb.setChecked(self.settings.get("toolbar_layout", "ribbon") == "ribbon"); rb.toggled.connect(self.set_ribbon); v.addAction(rb)
        gp = QAction("Graph Side Panel (curves and shortcuts)", self); gp.setCheckable(True); gp.setChecked(self.settings.get("graph_panel", True))
        gp.toggled.connect(self.set_graph_panel); v.addAction(gp)
        v.addSeparator()
        self.act(v, "Zoom In (active graph)", lambda: self.need_graph() and self.need_graph().zoom_by(0.8), "Ctrl+=")
        self.act(v, "Zoom Out (active graph)", lambda: self.need_graph() and self.need_graph().zoom_by(1.25), "Ctrl+-")
        self.act(v, "Reset Graph View (undo zoom and pan)", lambda: self.need_graph() and self.need_graph().reset_view(), "Ctrl+0")

        ws = mb.addMenu("&Worksheet")
        for text, fn in (("Transpose Sheet", self.ws_transpose), ("Stack Columns...", self.ws_stack), ("Unstack Column by Group...", self.ws_unstack),
                         ("Pivot Table...", self.ws_pivot), ("Remove Duplicate Rows", self.ws_dedupe), ("Extract Rows by Condition...", self.ws_extract),
                         ("Split Sheet by Column Value...", self.ws_split), ("Join with Another Sheet by Key...", self.ws_join),
                         ("Find and Replace...", self.ws_replace), ("Sort by Several Columns...", self.ws_sort),
                         ("Reduce Rows (combine every N)...", self.ws_reduce), ("Fill Missing Values...", self.ws_fill),
                         ("Fill Column with Sequence...", self.ws_sequence), ("Row Statistics", self.ws_rowstats),
                         ("Frequency Counts...", self.ws_freq), ("Colour Cells by Value (toggle)", self.ws_heat),
                         ("Insert Rows...", self.ws_insert_rows), ("Delete Selected Rows", self.ws_delete_rows)):
            self.act(ws, text, fn)

        c = mb.addMenu("&Column")
        self.act(c, "Add Column", lambda: self.need_book() and self.need_book().add_column())
        self.act(c, "Add 100 Rows", lambda: self.need_book() and self.need_book().add_rows(100))
        self.act(c, "Add Sheet to Workbook", lambda: self.active("book") and self.active("book").add_sheet())
        self.act(c, "Set Column Values (formula)...", self.col_formula, "Ctrl+Q")
        self.act(c, "Column Properties (long name, units, comments)...", self.col_props)
        self.act(c, "Convert Ions mg/L to meq/L (for Piper diagrams)", self.ions_to_meq)
        self.act(c, "Mineral Formula from Oxides (apfu)...", self.mineral_formula)
        self.act(c, "Normalise Major Oxides to 100% (Volatile-Free)", self.volatile_free)
        self.act(c, "CIPW Norm (from major oxides)...", self.cipw_norm)
        self.act(c, "Thermobarometry (T and P from mineral and rock data)...", self.thermobarometry)
        self.act(c, "Coupled P-T Solver (thermometer + barometer together)...", self.pt_solver)
        self.act(c, "Fe-Ti Oxide Thermometer / Oxybarometer (Ghiorso & Evans 2008)...", self.fe_ti_oxides)
        for d in DESIG: self.act(c, f"Set as {d}", lambda d=d: self.set_desig(d))
        c.addSeparator()
        self.act(c, "Mask Selected Cells", lambda: self.need_book() and self.need_book().set_mask(self.need_book().selected_cells(), True), "Ctrl+M")
        self.act(c, "Unmask Selected Cells", lambda: self.need_book() and self.need_book().set_mask(self.need_book().selected_cells(), False))
        self.act(c, "Unmask All Cells in Sheet", lambda: self.need_book() and self.need_book().set_mask(set(self.need_book().mask), False))

        p = mb.addMenu("&Plot")
        self.act(p, "Plot Gallery...", self.show_gallery, "Ctrl+Shift+G"); p.addSeparator()
        from .gallery import categories, MATRIX_KINDS
        for cat, kinds in categories():  # one submenu per category; preview icons load the first time it opens
            sub = p.addMenu(cat)
            for k in kinds:
                fn = (lambda n=k: self.need_matrix() and self.new_matrix_graph(self.need_matrix(), n)) if k in MATRIX_KINDS else (lambda n=k: self.plot(n))
                a = self.act(sub, k, fn); a.setData(k)
            sub.aboutToShow.connect(lambda m=sub: self._menu_icons(m))

        mx = mb.addMenu("&Matrix")
        self.act(mx, "New Matrixbook...", self.new_matrix_dialog)
        self.act(mx, "Add Matrix Object", lambda: self.active("matrix") and self.active("matrix").add_sheet())
        self.act(mx, "Set Values (formula in x, y, i, j)...", lambda: self.need_matrix() and self.need_matrix().set_formula())
        self.act(mx, "Dimensions and Coordinates...", lambda: self.need_matrix() and self.need_matrix().dimensions())
        tr = mx.addMenu("Transform")
        for op in MX.TRANSFORMS: self.act(tr, op, lambda op=op: self.mat_transform(op))
        self.act(mx, "Resample (change rows and columns)...", self.mat_resample)
        self.act(mx, "Smooth (Gaussian, median, mean)...", self.mat_smooth)
        self.act(mx, "2D FFT (amplitude spectrum)", self.mat_fft)
        self.act(mx, "Line Profile (row or column) to Worksheet...", self.mat_profile)
        self.act(mx, "Matrix Statistics", self.mat_stats)
        mx.addSeparator()
        self.act(mx, "Convert Matrix to XYZ Worksheet", self.mat_to_xyz)
        self.act(mx, "Convert Worksheet XYZ to Matrix (gridding)...", self.xyz_to_mat)
        mx.addSeparator()
        flt = mx.addMenu("Image Filters")
        for op in MX.FILTERS: self.act(flt, op, lambda op=op: self.mat_filter(op))
        self.act(mx, "Matrix Arithmetic (A op B or number)...", self.mat_arith)
        self.act(mx, "Crop Matrix...", self.mat_crop)

        g = mb.addMenu("&Graph")
        self.act(g, "Graph Properties (titles, axes, colours, fonts)...", self.graph_props, "Ctrl+G")
        self.act(g, "Edit Plot (type, columns, groups, panels)...", self.edit_plot, "Ctrl+Shift+E")
        self.act(g, "Apply Template / Theme...", self.apply_template)
        self.act(g, "Save Graph Format as Template...", lambda: self.need_graph() and save_template(self, self.need_graph().spec["style"]))
        self.act(g, "Set Default Theme for New Graphs...", self.default_theme)
        self.act(g, "Duplicate Graph", self.dup_graph)
        self.act(g, "Plot Details (show / hide curves, line, symbol, fill)...", self.plot_details, "Ctrl+Shift+T")
        dr = g.addMenu("Draw")
        for kind, label in (("line", "Line"), ("arrow2", "Arrow"), ("rect", "Rectangle"), ("circle", "Circle / Ellipse"), ("polygon", "Polygon"),
                            ("region", "Region (freehand)")):
            self.act(dr, label, lambda k=kind: self.draw_shape(k))
        self.act(g, "Copy Format to All Graphs", self.copy_format_all)
        g.addSeparator()
        self.act(g, "Split into Panels (one per Y column)...", self.split_panels)
        self.act(g, "New Layout Page (several graphs on one page)...", self.new_layout, "Ctrl+L")
        self.act(g, "Edit Layout Page...", self.edit_layout)
        self.act(g, "Add Inset Graph...", self.add_inset)
        self.act(g, "Add Zoom Inset (drag a rectangle on the graph)", self.zoom_inset)
        self.act(g, "Repeat Graph for Every Sheet of the Workbook", self.clone_graph_sheets)
        an = g.addMenu("Annotations")
        self.act(an, "Add Reference Line...", self.add_refline)
        self.act(an, "Add Text...", self.add_text)
        self.act(an, "Add Arrow...", self.add_arrow)
        self.act(an, "Add Confidence Ellipse...", self.add_ellipse)
        self.act(an, "Add Data from Another Sheet...", self.add_series)
        self.act(an, "Group Samples By Column...", self.group_samples)
        self.act(an, "Remove All Annotations", lambda: self.need_graph() and (self.need_graph().spec.pop("annotations", None), self.need_graph().draw()))
        self.act(g, "Remove Insets and Zoom Insets", lambda: self.need_graph() and (self.need_graph().spec.pop("insets", None),
                                                                                  self.need_graph().spec.pop("zooms", None), self.need_graph().draw()))
        self.act(g, "Clear Fitted Curves", self.clear_fits)
        self.act(g, "Refresh Graphs and Layouts", self.refresh_all, "F5")

        a = mb.addMenu("&Analysis")
        fit = a.addMenu("Fitting")
        self.act(fit, "Linear Fit", lambda: self.fit_poly(1))
        self.act(fit, "Polynomial Fit...", lambda: self.fit_poly(None))
        self.act(fit, "Nonlinear Curve Fit (function library, fixed parameters, bounds, weights)...", self.fit_nl, "Ctrl+F")
        self.act(fit, "User-defined Function Fit...", self.fit_user)
        self.act(fit, "Multiple Peak Fit...", self.fit_peaks)
        self.act(fit, "Multiple Linear Regression...", self.mlr)
        self.act(fit, "Surface Fit z = f(x, y)...", self.surface_fit)
        self.act(fit, "Orthogonal Distance Regression (errors in X and Y)...", self.odr_fit)
        self.act(fit, "Global Fit (shared parameters across columns)...", self.global_fit)
        self.act(a, "Peak Analyzer (baseline, find, fit peaks)...", self.peak_analyzer, "Ctrl+Shift+K")
        bt = a.addMenu("Batch Processing")
        self.act(bt, "Fit Each Selected Column (same function)...", self.batch_columns)
        self.act(bt, "Batch Process Files (import + analyse many files)...", self.batch_files)
        m = a.addMenu("Mathematics")
        self.act(m, "Differentiate", lambda: self.xy_op("d/dx", A.derivative))
        self.act(m, "Derivative (Savitzky-Golay, 1st to 4th order)...", self.savgol_deriv)
        self.act(m, "Integrate (cumulative + area)", self.integ)
        self.act(m, "Interpolate...", self.interp)
        self.act(m, "Normalize...", self.norm)
        self.act(m, "Average Selected Curves", self.avg_curves)
        self.act(m, "Subtract Straight Line...", self.sub_line)
        self.act(m, "Subtract Reference Curve...", self.sub_ref)
        self.act(m, "Curve Intersections (two selected columns)", self.curve_intersect)
        self.act(m, "Find X at Given Y...", self.find_x)
        self.act(m, "Rise Time (10-90%)", self.rise)
        self.act(m, "Polygon Area and Centroid", self.poly_area)
        s = a.addMenu("Signal Processing")
        self.act(s, "Smooth...", self.smooth)
        self.act(s, "FFT", self.fft)
        self.act(s, "FFT Low-pass Filter...", self.fft_filter)
        self.act(s, "IIR / FIR Filter Design and Apply...", self.filter_design)
        self.act(s, "Short-time FFT (spectrogram)...", self.stft)
        self.act(s, "Continuous Wavelet Transform (scalogram)", self.cwt)
        self.act(s, "Wavelet Denoise...", self.wavelet_denoise)
        self.act(s, "Discrete Wavelet Decomposition...", self.dwt)
        self.act(s, "Correlation / Convolution of Two Columns...", self.correlate)
        self.act(s, "Envelope (Hilbert)", self.envelope)
        self.act(s, "Coherence of Two Columns", self.coherence)
        sp = a.addMenu("Spectroscopy")
        self.act(sp, "Peak Fitting / Deconvolution (Peak Analyzer)...", self.peak_analyzer)
        self.act(sp, "Baseline (ALS) and Subtract...", self.baseline)
        self.act(sp, "Shirley Background (XPS) and Subtract", self.shirley)
        self.act(sp, "Find Peaks...", self.peaks)
        gc = a.addMenu("Geochronology")
        self.act(gc, "Isochron Age (York regression)...", self.isochron_report)
        self.act(gc, "Weighted Mean with MSWD", self.weighted_mean_report)
        self.act(gc, "U-Pb Ages and Discordance of Each Analysis", self.upb_ages)
        self.act(gc, "Common-Pb Correction (204Pb, 207Pb or 208Pb; Stacey & Kramers 1975)...", self.common_pb)
        self.act(gc, "Discordance Filter (mask discordant analyses)...", self.discordance_filter)
        pt = a.addMenu("Petrology / Thermobarometry")
        self.act(pt, "Thermobarometry (T and P from mineral and rock data)...", self.thermobarometry)
        self.act(pt, "Coupled P-T Solver (thermometer + barometer together)...", self.pt_solver)
        self.act(pt, "Fe-Ti Oxide Thermometer / Oxybarometer (Ghiorso & Evans 2008)...", self.fe_ti_oxides)
        self.act(pt, "Mineral Formula from Oxides (apfu)...", self.mineral_formula)
        self.act(pt, "CIPW Norm", self.cipw_norm)

        st = mb.addMenu("&Statistics"); st.setToolTipsVisible(True)

        def sub(menu, title):
            m = menu.addMenu(title); m.setToolTipsVisible(True); return m

        def head(menu, text):  # grey group heading (QMenu.addSection shows only a line on Windows)
            if menu.actions(): menu.addSeparator()
            h = menu.addAction(text.upper()); h.setEnabled(False); f = h.font(); f.setPointSizeF(f.pointSizeF() * 0.85); f.setBold(True); h.setFont(f)

        def add(menu, text, slot, tip):  # short label in the menu; when to use it in the tooltip and status bar
            ac = self.act(menu, text, slot); ac.setToolTip(tip); ac.setStatusTip(tip); return ac

        add(st, "Descriptive Statistics", self.desc, "Mean, SD, median, quartiles, skewness and more for the selected columns")
        c = sub(st, "Correlation")
        add(c, "Correlation Matrix", self.corr, "Pearson and Spearman correlation between the selected columns")
        add(c, "Partial Correlation", self.pcorr, "Correlation of two columns with the others held constant")
        nd = sub(st, "Normality and Distributions")
        add(nd, "Normality Test", self.normality, "Shapiro-Wilk, Kolmogorov-Smirnov and Anderson-Darling: is the column normally distributed?")
        add(nd, "Distribution Fit...", self.distfit, "Fit normal, lognormal, Weibull, gamma and exponential; ranked by AIC")
        add(nd, "Grubbs Outlier Test...", self.grubbs, "Find (and optionally mask) outliers in a normal sample")
        st.addSeparator()
        two = sub(st, "Compare Two Groups")
        head(two, "Parametric (t-tests)")
        add(two, "One-sample t-test...", self.t1, "Is the mean of one column different from a given value?")
        add(two, "Two-sample t-test...", self.t2, "Do two independent groups (two columns) have different means? Student or Welch")
        add(two, "Paired t-test", self.tpair, "Same subjects measured twice (two columns, row by row)")
        head(two, "Nonparametric")
        add(two, "Mann-Whitney / Kolmogorov-Smirnov", self.np2, "Two independent groups without assuming normality")
        add(two, "Wilcoxon Signed-rank (paired)", self.wilcoxon, "Paired measurements without assuming normality")
        many = sub(st, "Compare Several Groups (ANOVA)")
        head(many, "Independent groups")
        add(many, "One-way ANOVA", self.anova1, "Each column a group; with Tukey/Bonferroni post-hoc and Levene test")
        add(many, "Two-way ANOVA...", self.anova2, "Two factors and their interaction")
        add(many, "ANCOVA...", self.ancova, "One factor plus covariates; adjusted means")
        head(many, "Repeated measures")
        add(many, "One-way Repeated-measures ANOVA", self.rmanova, "Same subjects under several conditions (columns); with Friedman test")
        add(many, "Two-way Repeated-measures ANOVA...", self.rm2, "Two within-subject factors")
        add(many, "Mixed-design ANOVA...", self.mixed, "One between-subjects and one within-subjects factor")
        head(many, "Nonparametric")
        add(many, "Kruskal-Wallis", self.kruskal, "Several independent groups without assuming normality")
        add(many, "Dunn Post-hoc Test", self.dunn, "Which groups differ, after a Kruskal-Wallis test")
        cpv = sub(st, "Counts, Proportions and Variances")
        head(cpv, "Counts and proportions")
        add(cpv, "Chi-square Test of Independence...", self.chisq, "Are two categorical variables related? (contingency table)")
        add(cpv, "Fisher Exact / McNemar (2 x 2)...", self.fisher, "Small 2 x 2 tables, or paired yes/no data")
        add(cpv, "Proportion Test...", self.proportion, "One proportion against a value, or two proportions")
        head(cpv, "Variances")
        add(cpv, "Two-sample F Test", self.var2, "Do two selected columns have equal variances?")
        add(cpv, "One-sample Chi-square Test of Variance...", self.var1, "Is a column's variance equal to a given value?")
        st.addSeparator()
        rg = sub(st, "Regression and Models")
        add(rg, "Logistic Regression...", self.logit, "Yes/no outcome from one or more predictors; odds ratios")
        add(rg, "Generalized Linear Model...", self.glm, "Gaussian, binomial, Poisson, gamma ... with any link")
        add(rg, "PLS Regression...", self.pls, "Many correlated predictors (e.g. spectra); VIP scores")
        head(rg, "Mixed-effects models")
        add(rg, "Linear Mixed Model...", self.lmm, "Random intercepts and slopes for grouped or repeated data")
        add(rg, "Crossed or Nested Random Effects...", self.lmm_crossed, "Several random-effect terms, e.g. subject and item, or site and core")
        add(rg, "Generalized Linear Mixed Model...", self.glmm, "Binomial or Poisson outcomes with random effects")
        mv = sub(st, "Multivariate and Clustering")
        add(mv, "Principal Component Analysis", self.pca, "Reduce many correlated columns to a few components")
        add(mv, "MANOVA...", self.manova, "Compare groups on several response columns at once")
        add(mv, "MANCOVA...", self.mancova, "MANOVA with covariates")
        add(mv, "Discriminant Analysis...", self.discriminant, "Classify samples into groups (LDA or QDA)")
        head(mv, "Clustering")
        add(mv, "K-means Clustering...", self.kmeans, "Split samples into k groups")
        add(mv, "Hierarchical Clustering...", self.hcluster, "Tree of similar samples (dendrogram)")
        sd = sub(st, "Survival, Diagnostics and Reliability")
        add(sd, "Kaplan-Meier Survival...", self.km, "Survival curves with log-rank test")
        add(sd, "Cox Proportional Hazards...", self.cox, "Hazard ratios for predictors of survival")
        add(sd, "ROC Curve...", self.roc, "How well a score separates two classes; AUC and best cut-off")
        add(sd, "Bland-Altman Agreement", self.bland, "Agreement between two measurement methods (two columns)")
        add(sd, "Cronbach Alpha", self.cronbach, "Internal consistency of several items (columns)")
        st.addSeparator()
        add(st, "Power and Sample Size...", self.power, "How many samples you need, or the power you have")

        w = mb.addMenu("&Window")
        self.act(w, "Tile", self.mdi.tileSubWindows); self.act(w, "Cascade", self.mdi.cascadeSubWindows)
        self.act(w, "Toggle Tabbed / Free windows", lambda: self.mdi.setViewMode(
            QMdiArea.SubWindowView if self.mdi.viewMode() == QMdiArea.TabbedView else QMdiArea.TabbedView))
        tl = mb.addMenu("&Tools")
        self.act(tl, "Digitizer (data from a graph image)...", self.digitize)
        self.act(tl, "Add Python Script to Menu and Toolbar...", self.add_user_script)
        self.act(tl, "Remove Script from Menu...", self.remove_user_script)
        tl.addSeparator(); self.user_menu = tl; self.user_actions = []; self.fill_user_scripts()
        h = mb.addMenu("&Help")
        self.act(h, "Search Commands...", self.search_commands, "Ctrl+Shift+F").setShortcuts([QKeySequence("Ctrl+K"), QKeySequence("Ctrl+Shift+F")])
        self.act(h, "User Manual", self.show_manual, "F1")
        self.act(h, "Save User Manual as PDF...", self.manual_pdf)
        ex = h.addMenu("Example Data")
        from .examples import EXAMPLES
        for key, e in EXAMPLES.items(): self.act(ex, e[0], lambda k=key: self.open_example(k)).setStatusTip(e[2])
        ex.addSeparator(); self.act(ex, "Save All Example Files to a Folder...", self.save_examples)
        h.addSeparator()
        self.act(h, "Start Page...", self.show_start, "Ctrl+Shift+S")
        self.act(h, "Keyboard Shortcuts...", self.show_shortcuts, "Ctrl+/")
        h.addSeparator()
        self.act(h, "Send Feedback...", self.feedback)
        self.act(h, "About", self.about)
        self._about_text = lambda: ( f"<b>{APP} {VERSION}</b><br>Light worksheet, plotting and "
                 "analysis tool.<br>Author: Kishan Tiwari (kishantiwari@iitkgp.ac.in)<br><br>Tips: the grey rows at the top of a "
                 "sheet hold long name, units and comments (used for axis titles). Right-click a column header for X/Y, formulas "
                 "and properties; right-click the sheet tabs to add sheets. Select Y columns, then choose a plot. Graph menu: "
                 "properties, templates, themes and multi-panel layout pages.")
        self._describe_menus()

    def commands(self):
        """Every enabled menu command as (menu path, label, description, action)."""
        from PySide6.QtWidgets import QMenu
        out = []

        def walk(menu, path):
            for a in menu.actions():
                if a.isSeparator() or not a.isEnabled(): continue
                label = a.text().replace("&", "")
                if a.menu() is not None and a.menu() in subs: walk(a.menu(), path + [label]); continue
                if label: out.append((" > ".join(path), label, a.statusTip(), a))
        subs = set(self.menuBar().findChildren(QMenu))
        for top in self.menuBar().actions():
            if top.menu() is not None: walk(top.menu(), [top.text().replace("&", "")])
        return out

    def search_commands(self, query=None):
        """Type words (e.g. 'deconvolution', 'baseline', 'ternary'); Enter runs the highlighted command."""
        from .cmdhelp import KEYWORDS
        cmds = self.commands()

        def matches(q):
            words = q.lower().split()
            return [c for c in cmds if all(w in f"{c[0]} {c[1]} {c[2]} {KEYWORDS.get(c[1].rstrip('.').strip(), '')}".lower() for w in words)]
        if query is not None: return matches(query)
        d = QDialog(self); d.setWindowTitle("Search Commands"); d.resize(720, 460)
        box = QLineEdit(); box.setPlaceholderText("What do you want to do? e.g. deconvolution, baseline, smooth, ternary, export")
        lst = QListWidget(); info = QLabel(""); info.setWordWrap(True)

        def fill(q):
            lst.clear()
            for path, label, tip, a in matches(q)[:200]:
                it = QListWidgetItem(f"{label}    ({path})"); it.setToolTip(tip); it.setData(Qt.UserRole, a); lst.addItem(it)
            if lst.count(): lst.setCurrentRow(0)
        lst.currentItemChanged.connect(lambda it, _: info.setText(it.toolTip() if it else ""))

        def run(*_):
            it = lst.currentItem()
            if it: d.accept(); it.data(Qt.UserRole).trigger()
        box.textChanged.connect(fill); box.returnPressed.connect(run); lst.itemActivated.connect(run)
        from PySide6.QtCore import QObject

        class Arrows(QObject):  # Up / Down in the search box move through the list
            def eventFilter(self, o, e):
                if e.type() == e.Type.KeyPress and e.key() in (Qt.Key_Down, Qt.Key_Up):
                    lst.setCurrentRow(max(0, min(lst.count() - 1, lst.currentRow() + (1 if e.key() == Qt.Key_Down else -1)))); return True
                return False
        d._arrows = Arrows(d); box.installEventFilter(d._arrows)
        lay = QVBoxLayout(d); lay.addWidget(box); lay.addWidget(lst, 1); lay.addWidget(info)
        fill(""); d.exec()

    def _describe_menus(self):
        """Status-bar text and tooltips for every menu command that has no description yet.
        (Uses findChildren: wrapping QAction.menu() results in PySide can delete the menus.)"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        from .cmdhelp import describe
        for m in self.menuBar().findChildren(QMenu): m.setToolTipsVisible(True)
        for a in self.findChildren(QAction):
            label = a.text().replace("&", "")
            if a.statusTip() or not label: continue
            d = describe(label)
            if d: a.setStatusTip(d); a.setToolTip(d)

    # ---- undo
    def undo(self):
        s = self.mdi.activeSubWindow(); w = s.widget() if s else None
        if w is None: return
        if w.kind in SHEETED: w.current().undo()
        elif w.kind == "graph": w.undo()

    def redo(self):
        s = self.mdi.activeSubWindow(); w = s.widget() if s else None
        if w is None: return
        if w.kind in SHEETED: w.current().redo()
        elif w.kind == "graph": w.redo()

    # ---- file
    def new_book(self, df=None, name=None, meta=None):
        b = self.add_win(Workbook(self, name or self.uniq("Book"), df))
        if meta: b.current().meta.update(meta); b.current().model.refresh()
        return b

    def import_wizard(self):
        wiz = ImportWizard(self)
        if not wiz.exec() or not wiz.path.text(): return
        df, meta = wiz.result_data(); stem = Path(wiz.path.text()).stem
        target = wiz.target.currentText(); book = self.active("book")
        if target == "New workbook" or book is None:
            self.new_book(df, stem, meta)
        elif target.startswith("New sheet"):
            sh = book.add_sheet(stem, df); sh.meta.update(meta); sh.model.refresh()
        else:
            sh = book.current(); sh.snap(); sh.df = df; sh.desig = {c: "Y" for c in df.columns}
            sh.desig[df.columns[0]] = "X"; sh.formulas = {}; sh.meta = meta; sh.model.refresh()

    def import_text(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Import text", "", "Text data (*.csv *.txt *.dat *.tsv);;All (*.*)")
        if fn: return self.new_book(read_text_table(fn), Path(fn).stem)

    def import_excel(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Import Excel", "", "Excel (*.xlsx *.xls)")
            if not fn: return
        sheets = pd.read_excel(fn, sheet_name=None); b = None
        for sname, df in sheets.items():  # one workbook, one sheet per Excel sheet
            if b is None: b = self.new_book(df, Path(fn).stem); b.current().name = sname; b.tabs.setTabText(0, sname)
            else: b.add_sheet(sname, df)
        self.refresh_explorer(); return b

    def export_csv(self):
        b = self.need_book()
        if not b: return
        fn, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"{b.book.name}_{b.name}.csv", "CSV (*.csv)")
        if fn: b.df.dropna(how="all").to_csv(fn, index=False)

    def export_latex(self, fn=None, digits=4):
        """The sheet as a LaTeX booktabs table (numbers to 4 significant figures), with chemical formulae typeset (SiO$_2$, Fe$^{3+}$, $^{206}$Pb/$^{238}$U)."""
        import re
        b = self.need_book()
        if not b: return
        if fn is None:
            fn, _ = QFileDialog.getSaveFileName(self, "Export LaTeX table", f"{b.book.name}_{b.name}.tex", "LaTeX (*.tex)")
            if not fn: return
        esc = lambda t: re.sub(r"([&%#_$])", r"\\\1", str(t))

        el = r"(?:[A-Z][a-z]?)"
        def chem(t):
            t = esc(t); t = re.sub(r"\b(\d{2,3})(?=[A-Z][a-z]?)", r"$^{\1}$", t)  # isotope mass numbers: 206Pb
            t = re.sub(r"(?:(?<=[A-Z])|(?<=[A-Z][a-z]))(\d?[+-])(?=$|[\s,/)])", r"$^{\1}$", t)  # charges after an element: Fe3+, O2- (not 'yErr-')
            # stoichiometry only inside a formula-like word (SiO2, Al2O3, H2O), not in labels such as SpotA1 or Sample12
            return re.sub(rf"\b(?:{el}\d*)*{el}\d+(?:{el}\d*)*\b",
                          lambda m: m.group(0) if not re.fullmatch(rf"(?:{el}\d*)+", m.group(0)) or re.search(r"[a-z]{2}", m.group(0))
                          else re.sub(r"(?<=[A-Za-z])(\d+)", r"$_{\1}$", m.group(0)), t)

        def cell(v):
            if v is None or (isinstance(v, (float, np.floating)) and not np.isfinite(v)): return ""
            if isinstance(v, (bool, np.bool_)): return str(bool(v))
            if isinstance(v, (int, np.integer)): return str(int(v))
            if isinstance(v, (float, np.floating)):
                av = abs(float(v))
                if av == 0: return "0"
                if float(v).is_integer() and av < 1e6: return str(int(v))  # 5, not 5.000
                if 1e-3 <= av < 1e6:  # plain notation in the usual range: 12450, not 1.245e+04
                    dec = max(0, digits - 1 - int(np.floor(np.log10(av)))); rv = round(float(v), dec)
                    if rv != 0 and int(np.floor(np.log10(abs(rv)))) != int(np.floor(np.log10(av))):  # 999.96 rounds to 1000.0: one decimal fewer
                        dec = max(0, digits - 1 - int(np.floor(np.log10(abs(rv)))))
                    return f"{rv:.{dec}f}"
                return f"{v:.{digits - 1}e}"
            return esc(v)
        df = b.df.copy()  # masked (rejected) values stay out of a publication table; only the masked cells are blanked
        for c_, r_ in getattr(b, "mask", set()):
            if c_ in df.columns and 0 <= r_ < len(df): df.iat[r_, df.columns.get_loc(c_)] = np.nan
        df = df.dropna(how="all")
        num = [np.issubdtype(df[c].dtype, np.number) for c in df.columns]
        lines = [r"% requires \usepackage{booktabs}", r"\begin{table}", r"\centering", r"\caption{" + esc(b.name) + "}",
                 r"\begin{tabular}{" + "".join("r" if n else "l" for n in num) + "}", r"\toprule",
                 " & ".join(chem(c) for c in df.columns) + r" \\", r"\midrule"]
        lines += [" & ".join(cell(v) for v in row) + r" \\" for row in df.itertuples(index=False)]
        lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
        with open(fn, "w", encoding="utf-8") as h: h.write("\n".join(lines) + "\n")
        self.statusBar().showMessage(f"LaTeX table written: {fn}", 8000); return fn

    def export_graph(self):
        s = self.mdi.activeSubWindow(); g = s.widget() if s else None
        if g is None or g.kind not in ("graph", "layout"): g = self.active("graph")
        if not g: return QMessageBox.warning(self, APP, "No graph open.")
        fn, _ = QFileDialog.getSaveFileName(self, "Export", f"{g.name}.png",
                                            "PNG (*.png);;TIFF (*.tif);;JPEG (*.jpg);;SVG (*.svg);;PDF (*.pdf);;EPS (*.eps)")
        if not fn: return
        opts = self.export_options(g, fn)
        if opts is None: return
        g.export(fn, **opts); self.statusBar().showMessage(f"Saved {fn} at {opts['dpi']:g} dpi", 6000); return fn

    def export_options(self, g, fn=None, many=False):
        """Ask for DPI, size and transparency; remembers the last choice. Returns kwargs for export(), or None if cancelled."""
        from .export_dialog import ExportDialog
        d = ExportDialog(self, g.export_defaults() if g is not None else {"dpi": 600, "width_in": 6, "height_in": 4.5},
                         self.settings.get("export_opts", {}), fn, many, graph=g)
        if not d.exec(): return None
        opts = d.value(); keep = self.settings.get("export_opts", {}).get("use_graph_size", True)
        self.settings["export_opts"] = {"dpi": opts["dpi"], "transparent": opts["transparent"], "editable_text": opts["editable_text"],
                                        "use_graph_size": d.use_graph_size() if many else keep}  # only Export All sets this
        save_settings(self.settings)
        if many and d.use_graph_size(): opts.pop("width_in"); opts.pop("height_in")
        return opts

    def save_project(self, as_new=False):
        if as_new or not self.project_path:
            fn, _ = QFileDialog.getSaveFileName(self, "Save project", "project.pbp", f"{APP} project (*.pbp)")
            if not fn: return
            self.project_path = fn
        meta = {"app": APP, "version": VERSION, "author": "Kishan Tiwari", "windows": []}
        fd, tmp = tempfile.mkstemp(suffix=".pbp.tmp", dir=str(Path(self.project_path).resolve().parent)); os.close(fd)
        try: self._write_project(tmp, meta); os.replace(tmp, self.project_path)  # the old file is only replaced once the new one is complete
        except BaseException:
            try: os.remove(tmp)
            except OSError: pass
            raise
        self.setWindowTitle(f"{APP} {VERSION} - {Path(self.project_path).name}"); self.add_recent(self.project_path); self.clear_dirty()

    def _write_project(self, target, meta):
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for i, w in enumerate(self.windows()):
                st = w.state()
                if w.kind == "book":
                    for j, (sh, sst) in enumerate(zip(w.sheets, st["sheets"])):
                        sst["csv"] = f"book{i}_sheet{j}.csv"; z.writestr(sst["csv"], sh.df.to_csv(index=False, float_format="%.17g"))
                        sst["text_cols"] = [str(c) for c in sh.df.columns if sh.df[c].dtype == object]
                if w.kind == "matrix":
                    import io as _io
                    for j, (ms, sst) in enumerate(zip(w.sheets, st["sheets"])):
                        buf = _io.BytesIO(); np.save(buf, ms.M); sst["npy"] = f"matrix{i}_{j}.npy"; z.writestr(sst["npy"], buf.getvalue())
                st["folder"] = getattr(w, "folder", ""); meta["windows"].append(st)
            meta["folders"] = self.folders
            z.writestr("project.json", json.dumps(meta, default=float, indent=1))

    def open_project(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Open project", "", f"{APP} project (*.pbp)")
            if not fn: return
        meta, frames, arrays = read_project(fn)  # read, check and decode everything before closing anything
        if not self.confirm_discard("opening another project"): return
        # all or nothing: the current session is kept in a temporary project, and put back if building the new one fails part way
        backup = None
        if self.windows():
            fd, backup = tempfile.mkstemp(suffix=".pbp"); os.close(fd)
            try: self._write_project(backup, {"app": APP, "version": VERSION, "author": "Kishan Tiwari", "windows": []})
            except Exception: os.remove(backup); raise
        state = (self.project_path, self.dirty, self.windowTitle())
        try:
            self._close_all(); self._build_project(meta, frames, arrays)
        except Exception:
            self._close_all()
            if backup:
                self._build_project(*read_project(backup))
            self.project_path = state[0]; self.setWindowTitle(state[2]); self.dirty = state[1]; self.refresh_explorer()
            raise
        finally:
            if backup and os.path.exists(backup): os.remove(backup)
        self.refresh_explorer()
        self.project_path = fn; self.setWindowTitle(f"{APP} {VERSION} - {Path(fn).name}"); self.add_recent(fn); self.clear_dirty()

    def _close_all(self):
        for w in self.windows():  # a redraw still queued for a graph must not run after its canvas is deleted
            c = getattr(w, "canvas", None)
            if c is not None and getattr(c, "_draw_pending", False): c._draw_pending = False; c.draw()
        QCoreApplication.processEvents()
        self._bulk_close = True
        try:
            self.mdi.closeAllSubWindows(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)  # really remove closed windows now
        finally: self._bulk_close = False

    def _build_project(self, meta, frames, arrays):
        """Windows from a decoded project (see read_project)."""
        if True:
            for st in meta["windows"]:
                if st["kind"] != "book": continue
                sheets = st.get("sheets") or [{**st, "name": "Sheet1"}]  # 1.0 projects had one sheet per book
                b = None
                for sst in sheets:
                    df = frames[sst["csv"]]
                    if b is None:
                        b = self.add_win(Workbook(self, st["name"], df, sst["name"])); sh = b.current()
                    else: sh = b.add_sheet(sst["name"], df)
                    sh.desig.update(sst["desig"]); sh.formulas.update(sst["formulas"]); sh.meta.update(sst.get("meta", {}))
                    sh.mask = {(c, int(r)) for c, r in sst.get("mask", [])}
                    sh.cell_formulas = {(c, int(r)): t for c, r, t in sst.get("cells", []) if c in sh.df.columns}; sh.eval_cells()
                    sh.model.refresh()
                for s in b.sheets: s.eval_cells(); s.model.refresh()  # again, now that every sheet a formula may read is loaded
            for st in meta["windows"]:
                if st["kind"] != "matrix": continue
                mb = None
                for sst in st["sheets"]:
                    M = arrays[sst["npy"]]
                    if mb is None: mb = self.add_win(MatrixBook(self, st["name"], M, sst["extent"], sst["name"])); ms = mb.current()
                    else: ms = mb.add_sheet(sst["name"], M, sst["extent"])
                    ms.formula, ms.zlabel = sst.get("formula", ""), sst.get("zlabel", sst["name"])
        for st in meta["windows"]:
            if st["kind"] == "graph":
                g = self.add_win(GraphWindow(self, st["name"], st["spec"])); g.fits = st["fits"]; g.draw()
            elif st["kind"] == "report": self.report(st["name"], st["html"])
        for st in meta["windows"]:
            if st["kind"] == "layout": self.add_win(LayoutWindow(self, st["name"], st["spec"])).draw()
        self.folders = list(meta.get("folders", []))
        for st in meta["windows"]:
            w = self.win(st["name"])
            if w is not None: w.folder = st.get("folder", "")
        for w in self.windows():
            if w.kind == "book":
                for sh in w.sheets:
                    sst = next((x for st in meta["windows"] if st.get("name") == w.name for x in st.get("sheets", []) if x["name"] == sh.name), {})
                    sh.ops = list(sst.get("ops", []))

    # ---- column
    def col_formula(self):
        b = self.need_book()
        if b: b.set_formula((b.selected_cols() or [b.add_column()])[0])

    def col_props(self):
        b = self.need_book()
        if b and b.selected_cols(): b.properties(b.selected_cols()[0])

    def set_desig(self, d):
        b = self.need_book()
        if b: b.set_desig(b.selected_cols(), d)

    # ---- plotting
    ERR_ROLES = {"yErr": "y", "yErr+": "+", "yErr-": "-", "xErr": "x"}

    @staticmethod
    def bind_errors(sh, ys):
        """{Y column: errors} for each Y followed (to its right) by error columns. A plain yErr gives the column name; yErr+, yErr-
        (asymmetric) and xErr give {'y': .., '+': .., '-': .., 'x': ..}. Error columns are not plotted as Y."""
        cols = list(sh.df.columns); out = {}; key = Main.ERR_ROLES
        for y in ys:
            if y not in cols or sh.desig.get(y) in key: continue
            found = {}
            for c in cols[cols.index(y) + 1:]:
                d = sh.desig.get(c)
                if d in key:
                    found.setdefault(key[d], str(c))
                elif d in ("Y", "X"): break
            if found: out[str(y)] = found["y"] if list(found) == ["y"] else found
        return out

    def thermobarometry(self, sh=None, method=None, inputs=None, mc=None):
        """Temperature or pressure from a published calibration, as a new column. inputs: {input label: column name or number}.
        mc: None, or {"rel": relative 1-sigma of the analyses (0.02 = 2 %), "n": draws, "P (kbar)": absolute 1-sigma ...} for a Monte Carlo
        1-sigma column. Methods with a recorded calibration range also get a column flagging rows outside it."""
        from . import thermobaro as TB, mineral as MN
        sh = sh or self.need_book()
        if not sh: return
        cols = [str(c) for c in sh.df.columns]

        def oxides(prefix=False):
            return TB.phase_oxides(sh.df.columns, sh.arr, prefix)
        if method is None:
            d = QDialog(self); d.setWindowTitle("Thermobarometry"); d.resize(720, 560)
            pick = QComboBox(); pick.addItems(list(TB.METHODS)); pick.setMaxVisibleItems(20)
            info = QLabel(); info.setWordWrap(True); info.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form_box = QWidget(); form = QFormLayout(form_box); widgets = {}

            def build(name):
                while form.rowCount(): form.removeRow(0)
                widgets.clear(); m = TB.METHODS[name]
                info.setText(f"<b>{m['eq']}</b><br>{m['ref']}<br><span style='color:gray'>{m.get('note', '')}</span>"
                             + (f"<br><b>{'Equilibrium window' if TB.VALID[name].get('kind') else 'Calibration range'}:</b> {TB.VALID[name]['ref']} "
                                "(rows outside it are flagged in a new column)" if name in TB.VALID else ""))
                for kind, label, extra in m["inputs"]:
                    w_ = self._tb_widget(kind, extra, cols, oxides); form.addRow(label, w_); widgets[label] = (kind, w_)
            pick.currentTextChanged.connect(build); build(pick.currentText())
            from PySide6.QtWidgets import QCheckBox, QSpinBox, QHBoxLayout
            mc_on = QCheckBox("Monte Carlo uncertainty (1σ column)"); mc_rel = QDoubleSpinBox(); mc_rel.setRange(0.1, 50); mc_rel.setValue(2.0)
            mc_rel.setSuffix(" % per analysis"); mc_n = QSpinBox(); mc_n.setRange(50, 5000); mc_n.setValue(500); mc_n.setSuffix(" draws")
            mc_p = QDoubleSpinBox(); mc_p.setRange(0, 20); mc_p.setValue(0.0); mc_p.setPrefix("P ± "); mc_p.setSuffix(" kbar")
            mc_t = QDoubleSpinBox(); mc_t.setRange(0, 300); mc_t.setValue(0.0); mc_t.setPrefix("T ± "); mc_t.setSuffix(" °C")
            mc_p.setToolTip("Absolute 1σ of the pressure you give (used only by methods that take P)")
            mc_t.setToolTip("Absolute 1σ of the temperature, number or column (used only by methods that take T)")
            mc_row = QHBoxLayout(); [mc_row.addWidget(x) for x in (mc_on, mc_rel, mc_n, mc_p, mc_t)]
            mc_on.setToolTip("Every measured value (columns and oxide analyses) is varied by the relative 1σ error, independently, and the "
                             "method rerun; the column holds the standard deviation of the results. The equation's own calibration error comes on top.")
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            lay = QVBoxLayout(d); lay.addWidget(QLabel("Method")); lay.addWidget(pick); lay.addWidget(info); lay.addWidget(form_box, 1); lay.addLayout(mc_row); lay.addWidget(bb)
            if not d.exec(): return
            method = pick.currentText(); inputs = self._tb_values(widgets)
            if mc_on.isChecked(): mc = {"rel": mc_rel.value() / 100, "n": mc_n.value(), "P (kbar)": mc_p.value(), "T (C), if no column": mc_t.value()}
            d.deleteLater()  # the dialog and its widgets are not needed any more
        m = TB.METHODS[method]
        real = {str(c): c for c in sh.df.columns}
        vals = TB.compute(method, {k: (real.get(v, v) if isinstance(v, str) else v) for k, v in (inputs or {}).items()}, sh.arr, oxides, len(sh.df))
        used = "; ".join(f"{k} = {v}" for k, v in (inputs or {}).items())
        name = sh.add_column(f"{m['out']} ({m['unit'].replace('deg C', 'C')})", vals, units=m["unit"].replace("deg C", "°C"),
                             formula=f"{method}: {m['eq']}; inputs {used}. {m['ref']}")
        cols_in = {k: (real.get(v, v) if isinstance(v, str) else v) for k, v in (inputs or {}).items()}
        extra = ""
        if method in TB.VALID:
            given = {k: (sh.arr(v) if isinstance(v, str) else v) for k, v in cols_in.items() if v is not None}  # columns as their values
            rng = TB.VALID[method]; flag = TB.in_range(method, vals, given, len(sh.df))
            word = "in equilibrium" if rng.get("kind") == "equilibrium" else "in calibration range"
            sh.add_column(f"{m['out']} {word}", np.where(np.isnan(flag), None, np.where(flag == 1, "yes", "no")).astype(object),
                          formula=f"{method}: {rng['ref']}", snap=False)
            nout = int(np.nansum(flag == 0))
            if nout: extra = f"; {nout} rows {'not in equilibrium' if rng.get('kind') == 'equilibrium' else 'outside the calibration range'} ({rng['ref']})"
        if mc:
            labels = {i[1] for i in m["inputs"]}  # errors on P or T only for methods that take them
            num_sd = {k: v for k, v in mc.items() if k not in ("rel", "n") and v and k in labels}
            sd = TB.monte_carlo(method, cols_in, sh.arr, oxides, len(sh.df), rel=mc["rel"], n=mc.get("n", 500), num_sd=num_sd)
            sh.add_column(f"1s {m['out']} ({m['unit'].replace('deg C', 'C')})", sd, units=m["unit"].replace("deg C", "°C"),
                          formula=f"Monte Carlo, {mc.get('n', 500)} draws, {100 * mc['rel']:g} % relative 1-sigma on each measured input"
                                  + "".join(f", {k.replace(', if no column', '')} ± {v:g}" for k, v in num_sd.items()), snap=False, desig="yErr")
        sh.model.refresh(); sh.changed(); self.mark_dirty()
        ok = np.isfinite(vals)
        self.statusBar().showMessage(f"{method}: {ok.sum()} values in column {name}" + (f" ({(~ok).sum()} rows blank: inputs missing or outside the calibration, e.g. negative site occupancy)" if (~ok).any() else "") + extra, 12000)
        return name

    @staticmethod
    def _tb_widget(kind, extra, cols, oxides):
        """Input widget of a thermobarometry method: a column list, a number, or the oxide columns found."""
        from . import thermobaro as TB
        if kind in ("col", "colopt"):
            w_ = QComboBox(); w_.addItems([("(none: 0)" if kind == "colopt" else "(choose)")] + cols); g_ = TB.guess_column(cols, extra)
            if g_: w_.setCurrentText(g_)
            return w_
        if kind == "num":
            w_ = QDoubleSpinBox(); w_.setDecimals(3); w_.setRange(0, 1000); w_.setValue(float(extra)); w_.setSingleStep(0.05 if extra <= 1 else 1); return w_
        found = list(oxides() if kind == "oxides" else oxides(extra))
        return QLabel(", ".join(found) if found else "<span style='color:firebrick'>no oxide columns found</span>")

    @staticmethod
    def _tb_values(widgets):
        out = {}
        for label, (kind, w_) in widgets.items():
            if kind in ("col", "colopt"): out[label] = None if w_.currentText().startswith("(") else w_.currentText()
            elif kind == "num": out[label] = w_.value()
        return out

    def fe_ti_oxides(self, sh=None, p_bar=None):
        """Temperature, log fO2 and delta NNO of every row with a titanomagnetite and an ilmenite analysis (wt% oxides), from the
        two-oxide model of Ghiorso & Evans (2008): Fe2+Ti - Fe3+2 exchange for T and magnetite oxidation for fO2."""
        from . import fetioxide as FT, thermobaro as TB
        sh = sh or self.need_book()
        if not sh: return
        MT, IL = r"(?<![a-z])(mt|mag|magnetite|tmt|titanomagnetite|usp|ulvospinel)(?![a-z])", r"(?<![a-z])(ilm|ilmenite|hem|rhm|ilm-hem)(?![a-z])"
        from PySide6.QtWidgets import QProgressDialog
        cols = list(sh.df.columns); bh = False
        if p_bar is None:
            got = self._fe_ti_dialog(sh, MT, IL)
            if got is None: return
            spn_all, ilm_all, p_bar, bh = got
        else: spn_all, ilm_all = TB.phase_oxides(cols, sh.arr, MT), TB.phase_oxides(cols, sh.arr, IL)
        for name, d in (("titanomagnetite", spn_all), ("ilmenite", ilm_all)):
            if "TiO2" not in d or "FeO" not in d:
                raise RuntimeError(f"No {name} analysis found: name the columns e.g. 'Mt TiO2', 'Mt FeO' ... and 'Ilm TiO2', 'Ilm FeO' ... (wt%).")
        n = len(sh.df); T, F, N, LM, LI, DV = (np.full(n, np.nan) for _ in range(6)); PASS = np.full(n, "", object)
        prog = QProgressDialog("Solving the Ghiorso & Evans (2008) two-oxide model...", "Cancel", 0, n, self)
        prog.setWindowTitle("Fe-Ti oxides"); prog.setWindowModality(Qt.WindowModal); prog.setMinimumDuration(300); stopped = False
        try:
            for i in range(n):
                prog.setValue(i); prog.setLabelText(f"Fe-Ti oxides: row {i + 1} of {n}"); QApplication.processEvents()
                if prog.wasCanceled(): stopped = True; break
                sp = {k: float(v[i]) for k, v in spn_all.items() if np.isfinite(v[i])}; il = {k: float(v[i]) for k, v in ilm_all.items() if np.isfinite(v[i])}
                if not {"TiO2", "FeO"} <= set(sp) or not {"TiO2", "FeO"} <= set(il): continue
                try: T[i], F[i], N[i] = FT.two_oxide_wt(sp, il, p_bar)
                except (ValueError, FloatingPointError): pass
                if bh:
                    LM[i], LI[i], DV[i], ok = FT.mg_mn_test(sp, il); PASS[i] = ("yes" if ok else "no") if np.isfinite(DV[i]) else ""
        finally: prog.setValue(n); prog.close()
        how = (f"Ghiorso & Evans (2008) two-oxide geothermometer/oxygen barometer at {p_bar:g} bar: rhombohedral oxide model with cation order "
               "and short-range order, spinel of Sack & Ghiorso (1991a), end-members of Berman (1988)")
        a = sh.add_column("T Fe-Ti oxides (C)", T, units="°C", formula=how)
        b = sh.add_column("log fO2 Fe-Ti oxides", F, formula=how, snap=False)
        c = sh.add_column("dNNO Fe-Ti oxides", N, formula=how + "; relative to Ni-NiO of O'Neill & Pownceby (1993)", snap=False)
        if bh and np.isfinite(DV).any():
            bhow = (f"Bacon & Hirschmann (1988) Am Mineral 73, 57-61: log(Mg/Mn)Mt = {FT.BH88[0]} log(Mg/Mn)Ilm {FT.BH88[1]:+g} (atomic); "
                    "'yes' = inside their 2 sigma envelope (Table 1: 0.9430x + 0.0124 to 0.9213x - 0.1696); for fresh volcanic rocks only")
            sh.add_column("log(Mg/Mn) Mt", LM, formula=bhow, snap=False); sh.add_column("log(Mg/Mn) Ilm", LI, formula=bhow, snap=False)
            sh.add_column("Mg/Mn deviation (B&H 1988)", DV, formula=bhow, snap=False); sh.add_column("Mg/Mn equilibrium (B&H 1988)", PASS, formula=bhow, snap=False)
        sh.model.refresh(); sh.changed(); self.mark_dirty(); ok = np.isfinite(T)
        self.statusBar().showMessage(("Stopped: " if stopped else "") + f"Fe-Ti oxides: {ok.sum()} rows solved"
                                     + (f", {(~ok).sum()} blank (no analysis pair, no solution or not reached)" if (~ok).any() else ""), 10000)
        return a, b, c

    def _fe_ti_dialog(self, sh, MT, IL):
        """Which column holds each oxide of the titanomagnetite and the ilmenite (guessed from 'Mt TiO2', 'Ilm FeO' ... and editable),
        the pressure in kbar, and the Mg/Mn equilibrium test. Returns (spinel {oxide: values}, ilmenite {...}, P in bar, test) or None."""
        import re
        from PySide6.QtWidgets import QTableWidget, QDoubleSpinBox, QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox, QFormLayout, QHeaderView
        from . import fetioxide as FT
        num = [str(c) for c in sh.df.columns if pd.to_numeric(sh.df[c], errors="coerce").notna().any()]

        def guess(rx, ox):
            return next((c for c in num if re.search(rx, c, re.I) and re.search(rf"(?<![A-Za-z0-9]){re.escape(ox)}(?![0-9])", c, re.I)), "")
        d = QDialog(self); d.setWindowTitle("Fe-Ti oxide thermometer / oxybarometer (Ghiorso & Evans 2008)"); d.resize(620, 560); lay = QVBoxLayout(d)
        lay.addWidget(QLabel("Columns found for each oxide (wt%) of the two minerals; change any that are wrong. Total iron as FeO is "
                             "split into FeO and Fe<sub>2</sub>O<sub>3</sub> by charge balance.")); lay.itemAt(0).widget().setWordWrap(True)
        oxides = list(FT.OX); t = QTableWidget(len(oxides), 2); t.setHorizontalHeaderLabels(["Titanomagnetite column", "Ilmenite column"])
        t.setVerticalHeaderLabels(oxides); t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); boxes = []
        for r, ox in enumerate(oxides):
            row = []
            for k, rx in enumerate((MT, IL)):
                cb = QComboBox(); cb.addItems(["(none)"] + num); g = guess(rx, ox); cb.setCurrentText(g or "(none)"); t.setCellWidget(r, k, cb); row.append(cb)
            boxes.append(row)
        lay.addWidget(t, 1); f = QFormLayout(); lay.addLayout(f)
        p = QDoubleSpinBox(); p.setRange(0.001, 20.0); p.setDecimals(3); p.setValue(1.0); p.setSuffix(" kbar")
        p.setToolTip("1 kbar = 1000 bar; the result changes little with pressure (about 1-2 deg C per kbar)"); f.addRow("Pressure", p)
        bh = QCheckBox("Test each pair for equilibrium with Mg/Mn (Bacon & Hirschmann 1988)"); bh.setChecked(True); f.addRow("", bh)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); lay.addWidget(bb)
        if not d.exec(): return None
        pick = lambda k: {ox: sh.arr(boxes[r][k].currentText()) for r, ox in enumerate(oxides) if boxes[r][k].currentText() != "(none)"}
        return pick(0), pick(1), p.value() * 1000.0, bh.isChecked()

    def common_pb(self, sh=None, method=None, t0=None):
        """Common-Pb correction of 206Pb/238U ages: 204Pb (measured 206/204), 207Pb (measured 207/206; for young zircon) or 208Pb
        (measured 208/206 and Th/U), with common Pb of Stacey & Kramers (1975) at the age of each analysis."""
        import re
        from . import geochron as GC
        sh = sh or self.need_book()
        if not sh: return
        bad = r"(err|sig|^s\b|1s|2s|%|age|corr)"
        find = lambda a, b: next((c for c in sh.df.columns if re.search(rf"{a}\D*{b}", str(c).replace(" ", ""), re.I) and not re.search(bad, str(c), re.I)), None)
        c68, c76, c64, c86 = find("206", "238"), find("207", "206"), find("206", "204"), find("208", "206")
        cthu = next((c for c in sh.df.columns if re.fullmatch(r"\s*th\s*/\s*u\s*", str(c), re.I)), None)
        if c68 is None: raise RuntimeError("Name the ratio column 206Pb/238U (and 207Pb/206Pb, 206Pb/204Pb or 208Pb/206Pb + Th/U).")
        if method is None:
            opts = [m for m, ok in (("204Pb (measured 206Pb/204Pb)", c64), ("207Pb (measured 207Pb/206Pb)", c76), ("208Pb (measured 208Pb/206Pb and Th/U)", c86 and cthu)) if ok]
            if not opts: raise RuntimeError("Needs a 206Pb/204Pb column, a 207Pb/206Pb column, or 208Pb/206Pb with Th/U.")
            d = FormDialog(self, "Common-Pb correction", [("Correction", combo(opts, opts[0])), ("Age of common Pb (Ma; 0 = the age of each analysis)", spin(0, 4500, 0, dbl=True))])
            if not d.exec(): return
            method = d.val("Correction")[:3]; t0 = d.val("Age of common Pb (Ma; 0 = the age of each analysis)") or None
        r, t, f = GC.common_pb(method, sh.arr(c68), r76=sh.arr(c76) if c76 else None, r64=sh.arr(c64) if c64 else None,
                               r86=sh.arr(c86) if c86 else None, th_u=sh.arr(cthu) if cthu else None, t0=t0)
        how = f"{method}Pb correction, common Pb of Stacey & Kramers (1975)" + (f" at {t0:g} Ma" if t0 else " at the age of each analysis")
        a = sh.add_column(f"f206 ({method}) (%)", 100 * f, units="%", formula=how)
        r = np.where(r > 0, r, np.nan)
        b = sh.add_column(f"206Pb*/238U ({method}-corr)", r, formula=how, snap=False)
        c = sh.add_column(f"Age 206Pb/238U {method}-corr (Ma)", t, units="Ma", formula=how, snap=False)
        errc = lambda x, y: next((k for k in sh.df.columns if re.search(rf"{x}\D*{y}", str(k).replace(" ", ""), re.I)
                                  and re.search(r"(err|sig|1s|2s|\bs\b)", str(k), re.I) and not re.search(r"(age|corr)", str(k), re.I)), None)
        s68 = errc("206", "238")
        if s68: sh.add_column(f"{s68} ({method}-corr)", sh.arr(s68) * r / np.where(sh.arr(c68) > 0, sh.arr(c68), np.nan), formula=how, snap=False)
        c75 = find("207", "235")
        if c75 and method in ("204", "208"):  # the 207Pb method puts each analysis on concordia by definition: no independent 207/235
            # 207Pb*/235U = measured 207/235 minus common 207 (common 206 x (207/206)c x 238/235), so corrected points plot on concordia
            pa, pb, _ = GC.stacey_kramers(np.full_like(t, float(t0)) if t0 else t)
            r75 = sh.arr(c75) - f * sh.arr(c68) * (pb / pa) * GC.U85; r75 = np.where(r75 > 0, r75, np.nan)
            sh.add_column(f"207Pb*/235U ({method}-corr)", r75, formula=how, snap=False)
            s75 = errc("207", "235")
            if s75: sh.add_column(f"{s75} ({method}-corr)", sh.arr(s75) * r75 / np.where(sh.arr(c75) > 0, sh.arr(c75), np.nan), formula=how, snap=False)
        sh.model.refresh(); sh.changed(); self.mark_dirty(); return a, b, c

    def discordance_filter(self, sh=None, limit=None, mode=None):
        """Mask the analyses whose discordance is beyond a limit, so ages, KDE/PDP, weighted means and concordia ages use the
        concordant ones only (Edit > Undo or unmasking brings them back). Discordance against 207Pb/206Pb suits Precambrian grains,
        against 207Pb/235U young (Phanerozoic) ones, where 207Pb/206Pb ages scatter; Auto switches at 1000 Ma (206Pb/238U age)."""
        import re
        from . import geochron as GC
        sh = sh or self.need_book()
        if not sh: return
        find = lambda a, b: next((c for c in sh.df.columns if re.search(rf"{a}\D*{b}", str(c).replace(" ", ""), re.I) and not re.search(r"(err|sig|^s\b|1s|2s|%|age|corr)", str(c), re.I)), None)
        c68, c75, c76 = find("206", "238"), find("207", "235"), find("207", "206")
        if c68 is None or (c75 is None and c76 is None): raise RuntimeError("Discordance needs 206Pb/238U and 207Pb/206Pb or 207Pb/235U columns.")
        modes = ["Auto (207Pb/235U below 1000 Ma, 207Pb/206Pb above)", "206Pb/238U vs 207Pb/206Pb (Precambrian)", "206Pb/238U vs 207Pb/235U (Phanerozoic)"]
        if limit is None:
            d = FormDialog(self, "Discordance filter", [("Discordance between", combo(modes, modes[0])), ("Mask analyses with |discordance| above (%)", spin(0, 100, 10, dbl=True))])
            if not d.exec(): return
            mode = ["auto", "76", "75"][modes.index(d.val("Discordance between"))]; limit = d.val("Mask analyses with |discordance| above (%)")
        mode = mode or "auto"; t68 = GC.age68(sh.arr(c68))
        t76 = GC.age76(sh.arr(c76)) if c76 else np.full_like(t68, np.nan); t75 = GC.age75(sh.arr(c75)) if c75 else np.full_like(t68, np.nan)
        ref = t76 if mode == "76" or (mode == "auto" and c75 is None) else t75 if mode == "75" or c76 is None else np.where(t68 < 1000, t75, t76)
        with np.errstate(divide="ignore", invalid="ignore"): dsc = 100 * (1 - t68 / ref)
        rows = [int(i) for i in np.where(np.isfinite(dsc) & (np.abs(dsc) > limit))[0]]
        if rows: sh.set_mask([(c, r) for c in sh.df.columns for r in rows], True)
        self.statusBar().showMessage(f"Discordance filter: {len(rows)} of {int(np.isfinite(dsc).sum())} analyses masked (|D| > {limit:g}%)", 10000)
        return rows

    def pt_solver(self, sh=None, tmethod=None, pmethod=None, inputs=None, p0=10.0):
        """T and P solved together, row by row, from a thermometer that needs P and a barometer that needs T (or not)."""
        from PySide6.QtWidgets import QScrollArea
        from . import thermobaro as TB, mineral as MN
        sh = sh or self.need_book()
        if not sh: return
        cols = [str(c) for c in sh.df.columns]; th, ba = TB.coupled_pairs()
        oxides = lambda prefix=False: TB.phase_oxides(sh.df.columns, sh.arr, prefix)
        if tmethod is None:
            d = QDialog(self); d.setWindowTitle("Coupled P-T solver"); d.resize(760, 680)
            tp, pp = QComboBox(), QComboBox(); tp.addItems(th); pp.addItems(ba); tp.setMaxVisibleItems(20); pp.setMaxVisibleItems(20)
            box = QWidget(); form = QFormLayout(box); widgets = {}; info = QLabel(); info.setWordWrap(True)
            start = QDoubleSpinBox(); start.setRange(0, 100); start.setValue(p0)

            def build(*_):
                while form.rowCount(): form.removeRow(0)
                widgets.clear()
                for name in (tp.currentText(), pp.currentText()):
                    for kind, label, extra in TB.METHODS[name]["inputs"]:
                        if label in widgets or label in ("P (kbar)", "T (C) column", "T (C), if no column"): continue
                        w_ = self._tb_widget(kind, extra, cols, oxides); form.addRow(label, w_); widgets[label] = (kind, w_)
                info.setText(f"<b>T:</b> {TB.METHODS[tp.currentText()]['eq']}<br>{TB.METHODS[tp.currentText()]['ref']}<br>"
                             f"<b>P:</b> {TB.METHODS[pp.currentText()]['eq']}<br>{TB.METHODS[pp.currentText()]['ref']}<br><span style='color:gray'>"
                             "Each row is solved by iteration: T from the thermometer at the current P, then P from the barometer at that T, "
                             "until P changes by less than 0.01 kbar. Rows that do not settle are left blank.</span>")
            tp.currentTextChanged.connect(build); pp.currentTextChanged.connect(build); build()
            sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(box)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
            lay = QVBoxLayout(d)
            for w_ in (QLabel("Thermometer (depends on P)"), tp, QLabel("Barometer (may depend on T)"), pp, info): lay.addWidget(w_)
            f2 = QFormLayout(); f2.addRow("Starting P (kbar)", start); lay.addLayout(f2); lay.addWidget(sc, 1); lay.addWidget(bb)
            if not d.exec(): return
            tmethod, pmethod, p0, inputs = tp.currentText(), pp.currentText(), start.value(), self._tb_values(widgets); d.deleteLater()
        real = {str(c): c for c in sh.df.columns}
        T, P, it = TB.solve_pt(tmethod, pmethod, {k: (real.get(v, v) if isinstance(v, str) else v) for k, v in (inputs or {}).items()},
                               sh.arr, oxides, p0)
        tm, pm = TB.METHODS[tmethod], TB.METHODS[pmethod]; used = "; ".join(f"{k} = {v}" for k, v in (inputs or {}).items())
        how = f"Coupled P-T solver: {tmethod} ({tm['ref']}) with {pmethod} ({pm['ref']}); inputs {used}"
        nt = sh.add_column(f"{tm['out']} P-T (C)", T, units="°C", formula=how)
        npr = sh.add_column(f"{pm['out']} P-T (kbar)", P, units="kbar", formula=how, snap=False)
        sh.model.refresh(); sh.changed(); self.mark_dirty(); ok = np.isfinite(T) & np.isfinite(P)
        self.statusBar().showMessage(f"P and T solved for {ok.sum()} rows ({it} iterations)" + (f"; {(~ok).sum()} rows blank" if (~ok).any() else ""), 8000)
        return nt, npr

    # ---- geochronology
    def isochron_report(self, sh=None, system=None):
        """York (2004) regression isochron of the selected columns: parent ratio (X), daughter ratio, 1-sigma errors of X and Y, rho."""
        from . import geochron as GC
        sh = sh or self.need_book()
        if not sh: return
        x, ys = sh.xy_for_plot()
        if not x or len(ys) < 3: raise RuntimeError("Set the parent ratio column as X and select the daughter ratio, the 1-sigma errors of X and Y and (optional) rho.")
        if system is None:
            system, ok = QInputDialog.getItem(self, "Isochron", "Decay system:", list(GC.SYSTEMS), 0, False)
            if not ok: return
        a = [sh.arr(c) for c in ys[:4]]; f = GC.york(sh.arr(x), a[1], a[0], a[2], a[3] if len(a) > 3 else None); r = GC.isochron_age(f, system)
        lam, xn, yn, ref = GC.SYSTEMS[system]
        self.report(f"Isochron {system}", dict_html(f"{system} isochron, York et al. (2004) regression", {
            "Age (Ma)": r["age"], "± 2σ (Ma)": r["age_2s"], "± 2σ × √MSWD (Ma)": r["age_2s_mswd"], f"Initial {yn}": r["initial"],
            "Initial ± 2σ": r["initial_2s"], "Slope": f["slope"], "Slope ± 1σ": f["s_slope"], "MSWD": f["mswd"], "p (χ²)": f["p"], "n": f["n"],
            "Decay constant (1/yr)": f"{lam:.5e} ({ref})"}))
        self.new_graph(sh, "Isochron (York regression)", x, ys[:4], {"system": system}); return r

    def weighted_mean_report(self, sh=None):
        """Weighted mean with MSWD of the first selected column, its 1-sigma errors in the next one."""
        from . import geochron as GC
        sh = sh or self.need_book()
        if not sh: return
        x, ys = sh.xy_for_plot()
        if len(ys) < 2: raise RuntimeError("Select the values (e.g. ages) and their 1-sigma errors.")
        w = GC.weighted_mean(sh.arr(ys[0]), sh.arr(ys[1])); k = np.sqrt(w["mswd"]) if w["mswd"] > 1 else 1.0
        self.report(f"Weighted mean {ys[0]}", dict_html(f"Weighted mean of {ys[0]}", {
            "Mean": w["mean"], "± 2σ": 2 * w["s_mean"], "± 2σ × √MSWD": 2 * w["s_mean"] * k, "MSWD": w["mswd"], "p (χ²)": w["p"], "n": w["n"]}))
        self.new_graph(sh, "Weighted Mean (ages)", x, ys[:2]); return w

    def upb_ages(self, sh=None):
        """206Pb/238U, 207Pb/235U and 207Pb/206Pb ages and the discordance of each analysis, from columns named after the ratios."""
        import re
        from . import geochron as GC
        sh = sh or self.need_book()
        if not sh: return
        find = lambda a, b: next((c for c in sh.df.columns if re.search(rf"{a}\D*{b}", str(c).replace(" ", ""), re.I) and not re.search(r"(err|sig|^s\b|1s|2s|%)", str(c), re.I)), None)
        c68, c75, c76 = find("206", "238"), find("207", "235"), find("207", "206")
        if not (c68 or c75 or c76): raise RuntimeError("Name the ratio columns 206Pb/238U, 207Pb/235U and 207Pb/206Pb.")
        made = []; snap = True
        for col, fn, name in ((c68, GC.age68, "Age 206Pb/238U (Ma)"), (c75, GC.age75, "Age 207Pb/235U (Ma)"), (c76, GC.age76, "Age 207Pb/206Pb (Ma)")):
            if col is not None:
                made.append(sh.add_column(name, fn(sh.arr(col)), units="Ma", snap=snap, formula=f"{name[4:-5]} age of {col}; λ238 = {GC.L238}, λ235 = {GC.L235} (Jaffey et al. 1971)"))
                snap = False
        if c68 is not None and c76 is not None:
            t68, t76 = GC.age68(sh.arr(c68)), GC.age76(sh.arr(c76))
            with np.errstate(divide="ignore", invalid="ignore"): disc = 100 * (1 - t68 / t76)
            made.append(sh.add_column("Discordance (%)", disc, units="%", snap=False, formula="100 (1 - t206/238 / t207/206)"))
        sh.model.refresh(); sh.changed(); self.mark_dirty(); return made

    def savgol_deriv(self):
        b, xn, yn, x, y = self.first_xy()
        d = FormDialog(self, "Savitzky-Golay derivative", [("Derivative order", spin(1, 4, 1)), ("Window (points, odd)", spin(5, 9999, 11)),
                                                           ("Polynomial order", spin(2, 10, 3))])
        if d.exec():
            k = d.val("Derivative order")
            b.add_column(f"d{k}_{yn}", A.savgol_derivative(x, y, k, d.val("Window (points, odd)"), d.val("Polynomial order")))

    def shirley(self):
        b, xn, yn, x, y = self.first_xy(); z = A.baseline_shirley(x, y)
        b.add_column(f"Shirley_{yn}", z); b.add_column(f"Corr_{yn}", y - z)
        self.graph_for(b, yn, "Line").add_curve(x, z, "Shirley background", "k--")

    # ---- graphs
    def plot_details(self, g=None):
        g = g or self.need_graph()
        if not g: return
        from .plotdetails import PlotDetailsDialog
        PlotDetailsDialog(g).exec()

    def draw_shape(self, kind):
        g = self.need_graph()
        if g: g.start_draw(kind)

    def copy_format_all(self):
        """The active graph's look (Graph Properties: fonts, axes, colours, sizes) given to every other graph; titles and ranges stay."""
        g = self.need_graph()
        if not g: return
        keep = ("title", "xlabel", "ylabel", "xmin", "xmax", "ymin", "ymax", "texts", "points", "series", "legend_pos", "xbreak", "ybreak")
        look = {k: v for k, v in g.spec["style"].items() if k not in keep}; n = 0
        for w in self.windows():
            if w.kind == "graph" and w is not g: w.snapshot(); w.spec["style"] = {**w.spec["style"], **look}; w.draw(); n += 1
        self.statusBar().showMessage(f"Format copied to {n} graphs (Undo in each graph puts it back)", 6000); return n

    def zoom_inset(self):
        g = self.need_graph()
        if g and g.start_zoom(): self.statusBar().showMessage("Drag a rectangle around the region to magnify; the inset goes in the opposite corner.", 10000)
        elif g: QMessageBox.warning(self, APP, "Zoom insets need an X-Y graph.")

    def clone_graph_sheets(self, g=None):
        """The graph repeated, with the same format, for every other sheet of its workbook that has the same columns."""
        g = g or self.need_graph()
        if not g: return
        s = g.spec; book = next((w for w in self.windows() if w.kind == "book" and w.name == s.get("book")), None)
        if book is None: return QMessageBox.warning(self, APP, "This graph is not drawn from a workbook.")
        need = [c for c in [s.get("x")] + list(s.get("ys", [])) if c]; here = s.get("sheet") or book.sheets[0].name; made = []
        for sh in book.sheets:
            if sh.name == here or not all(c in sh.df.columns for c in need): continue
            spec = json.loads(json.dumps(s)); spec["sheet"] = sh.name
            n = self.add_win(GraphWindow(self, self.uniq(f"{g.name} - {sh.name}"), spec)); n.draw(); made.append(n.name)
        self.statusBar().showMessage(f"{len(made)} graphs made" if made else "No other sheet has the same columns", 8000); return made

    def export_pdf_book(self, fn=None):
        """Every graph and layout as one page of a single PDF, each at its own export size."""
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.figure import Figure
        wins = [w for w in self.windows() if w.kind in ("graph", "layout")]
        if not wins: return QMessageBox.warning(self, APP, "There are no graphs to export.")
        if fn is None:
            fn, _ = QFileDialog.getSaveFileName(self, "Export all graphs to one PDF", "graphs.pdf", "PDF (*.pdf)")
            if not fn: return
        with matplotlib.rc_context({"pdf.fonttype": 42}), PdfPages(fn, metadata={"Author": "Kishan Tiwari", "Creator": f"{APP} {VERSION}",
                                                                                 "Title": Path(fn).stem}) as pdf:
            for w in wins:
                d = w.export_defaults(); fig = Figure(figsize=(d["width_in"], d["height_in"]), layout="constrained" if w.kind == "graph" else None)
                w.render(fig); pdf.savefig(fig)
        self.statusBar().showMessage(f"{len(wins)} pages written to {fn}", 8000); return fn

    def cipw_norm(self, sh=None, fe3_ratio="ask", anhydrous=True):
        """CIPW norm of every analysis: a new sheet with the sample names and the normative minerals in wt%, their sum, the
        differentiation index and the normative plagioclase An. fe3_ratio: Fe2O3/FeO by weight used when only total iron is given
        (None = use FeO and Fe2O3 as they are)."""
        from . import mineral as MN, norm as NM
        sh = sh or self.need_book()
        if not sh: return
        ox = MN.collect_oxides(sh.selected_cols() or list(sh.df.columns), sh.arr, keep=NM.MW)
        missing = [k for k in ("SiO2", "Al2O3", "CaO", "Na2O", "K2O") if k not in ox]
        if missing: raise RuntimeError("The CIPW norm needs columns named after the major oxides; missing: " + ", ".join(missing))
        only_total = "Fe2O3" not in ox
        if fe3_ratio == "ask":
            d = FormDialog(self, "CIPW norm", [("Iron", combo(["Split total iron by the Fe2O3/FeO ratio below", "Use FeO and Fe2O3 as given"],
                                                              "Split total iron by the Fe2O3/FeO ratio below" if only_total else "Use FeO and Fe2O3 as given")),
                                               ("Fe2O3/FeO (by weight)", spin(0, 2, 0.15, True)), ("Recalculate to 100% volatile-free first", QCheckBox())])
            d.w["Fe2O3/FeO (by weight)"].setDecimals(2); d.w["Fe2O3/FeO (by weight)"].setSingleStep(0.05)
            d.w["Recalculate to 100% volatile-free first"].setChecked(True)
            note = QLabel("Oxides found: " + ", ".join(ox) + ". With total iron only (FeOt or Fe2O3t), part of it must be Fe2O3 for "
                          "magnetite: Middlemost (1989) suggests Fe2O3/FeO = 0.15 for basalts and picrites, 0.20-0.30 for andesites and "
                          "trachytes, 0.40-0.50 for dacites and rhyolites.")
            note.setWordWrap(True); d.layout().insertRow(0, note)
            if not d.exec(): return
            fe3_ratio = d.val("Fe2O3/FeO (by weight)") if d.val("Iron").startswith("Split") else None
            anhydrous = d.val("Recalculate to 100% volatile-free first")
        res = NM.cipw(ox, fe3_ratio=fe3_ratio, anhydrous=anhydrous)
        df = pd.DataFrame({c: sh.df[c] for c in sh.df.columns if sh.desig.get(c) in ("Label", "X") or
                           (sh.df[c].dtype == object and pd.to_numeric(sh.df[c], errors="coerce").isna().all())})
        keep = [m for m in NM.ORDER if np.nansum(res[m]) > 0]
        for m in keep + ["Sum", "DI", "Plag An", "Plag An (mol%)"]: df[m] = res[m]
        new = sh.book.add_sheet(f"{sh.name} CIPW", df.reset_index(drop=True))
        new.desig = {c: ("Label" if c not in keep + ["Sum", "DI", "Plag An", "Plag An (mol%)"] else "Y") for c in df.columns}
        iron = (f"total iron split with Fe2O3/FeO = {fe3_ratio:g}" if fe3_ratio is not None else "FeO and Fe2O3 as given")
        basis = f"CIPW norm, wt%; {iron}; {'recalculated volatile-free' if anhydrous else 'as analysed'}"
        for m in keep: new.meta[m] = {"Long Name": NM.NAMES[m], "Units": "wt%", "Formula": f"normative {NM.NAMES[m]} ({basis})"}
        new.meta["Sum"] = {"Units": "wt%", "Formula": "sum of the normative minerals"}
        new.meta["DI"] = {"Long Name": "Differentiation index", "Formula": "Q + Or + Ab + Ne + Lc + Kp (Thornton & Tuttle 1960)"}
        new.meta["Plag An"] = {"Long Name": "Normative plagioclase An", "Formula": "100 An / (An + Ab), normative wt%"}
        new.meta["Plag An (mol%)"] = {"Long Name": "Normative plagioclase An, molar", "Formula": "100 n(CaAl2Si2O8) / [n(CaAl2Si2O8) + n(NaAlSi3O8)]"}
        new.model.refresh(); self.mark_dirty()
        self.statusBar().showMessage(f"CIPW norm of {len(df)} analyses in sheet '{new.name}'" +
                                     ("; all iron counted as FeO, so no magnetite" if only_total and fe3_ratio is None else ""), 8000)
        return new

    def volatile_free(self, sh=None):
        """New sheet with the oxide columns recalculated to 100% (LOI, H2O, CO2 and other non-oxide columns are not summed);
        other columns (sample names, trace elements) are copied unchanged. Use it before TAS, Harker and Frost diagrams."""
        from . import mineral as MN
        sh = sh or self.need_book()
        if not sh: return
        cols = [c for c in (sh.selected_cols() or list(sh.df.columns)) if MN.oxide_of(c)]
        if len(cols) < 3: raise RuntimeError("Select the major-oxide columns (SiO2, TiO2, Al2O3, FeOt, MgO, CaO, Na2O, K2O ...).")
        df = sh.df.copy(); vals = np.column_stack([pd.to_numeric(df[c], errors="coerce").to_numpy(float) for c in cols])
        total = np.nansum(vals, axis=1); total[total <= 0] = np.nan
        for i, c in enumerate(cols): df[c] = 100 * vals[:, i] / total
        df["Original total"] = np.nansum(vals, axis=1)
        new = sh.book.add_sheet(f"{sh.name} volatile-free", df)
        new.desig = {c: sh.desig.get(c, "Y") for c in df.columns}; new.desig["Original total"] = "Y"
        new.meta = {c: dict(m) for c, m in sh.meta.items() if c in df.columns}
        for c in cols: new.meta.setdefault(c, {})["Formula"] = f"100 x {c} / ({' + '.join(map(str, cols))}) of sheet {sh.name}"
        new.meta.setdefault("Original total", {})["Formula"] = f"{' + '.join(map(str, cols))} before normalising"
        new.model.refresh(); self.mark_dirty()
        self.statusBar().showMessage(f"{len(cols)} oxides recalculated to 100% in sheet '{new.name}'", 6000); return new

    def mineral_formula(self, sh=None, mineral=None, oxygens=None, cation_total=None):
        """Oxide wt% columns -> cations per formula unit (apfu) on an oxygen basis, Fe3+ by charge balance (Droop 1987),
        and end-members (Fo, Wo-En-Fs, An-Ab-Or, Mg#). One undo step."""
        from . import mineral as MN
        sh = sh or self.need_book()
        if not sh: return
        ox = MN.collect_oxides(sh.selected_cols() or list(sh.df.columns), sh.arr)
        if not ox: raise RuntimeError("No column is named after an oxide (SiO2, TiO2, Al2O3, FeO or FeOt, MgO, CaO, Na2O, K2O ...).")
        if mineral is None:
            names = list(MN.MINERALS)
            d = FormDialog(self, "Mineral formula from oxides", [("Mineral", combo(names, "Pyroxene")), ("Oxygens", spin(1, 100, 6, dbl=True)),
                                                                 ("Fe3+ estimate", combo(list(MN.FE3_METHODS), "Charge balance (Droop 1987)")),
                                                                 ("Cations for Fe3+ (0 = all Fe as Fe2+)", spin(0, 100, 4)),
                                                                 ("Fe3+ / total Fe", spin(0, 1, 0.3, dbl=True))])
            d.w["Oxygens"].setDecimals(1); d.w["Fe3+ / total Fe"].setDecimals(3); d.w["Fe3+ / total Fe"].setSingleStep(0.05)
            def preset(m):
                o, t = MN.MINERALS[m]
                if o: d.w["Oxygens"].setValue(o)
                d.w["Fe3+ estimate"].setCurrentText(MN.method_name(t))
                d.w["Cations for Fe3+ (0 = all Fe as Fe2+)"].setValue(t if isinstance(t, (int, float)) and t else 0)
            def method(name):
                d.w["Cations for Fe3+ (0 = all Fe as Fe2+)"].setEnabled(MN.FE3_METHODS[name] == "droop")
                d.w["Fe3+ / total Fe"].setEnabled(MN.FE3_METHODS[name] == "ratio")
            d.w["Mineral"].currentTextChanged.connect(preset); d.w["Fe3+ estimate"].currentTextChanged.connect(method); preset("Pyroxene")
            used = QLabel("Oxides found: " + ", ".join(ox) + ". Fe3+ is estimated by charge balance (Droop 1987) when a cation total is given.")
            used.setWordWrap(True); d.layout().insertRow(0, used)
            if not d.exec(): return
            mineral, oxygens = d.val("Mineral"), d.val("Oxygens"); how = MN.FE3_METHODS[d.val("Fe3+ estimate")]
            cation_total = (d.val("Cations for Fe3+ (0 = all Fe as Fe2+)") if how == "droop" else f"ratio:{d.val('Fe3+ / total Fe')}"
                            if how == "ratio" else (how if how != "none" else 0))
        o, t = MN.MINERALS.get(mineral, (None, None))
        oxygens = oxygens or o; cation_total = (t if cation_total is None else cation_total) or None
        if mineral not in ("Custom",) and isinstance(cation_total, str) and cation_total.startswith("amphibole") and mineral != "Amphibole":
            raise RuntimeError("The 13eCNK/15eNK estimate is for amphiboles; choose another Fe3+ estimate for this mineral.")
        ap = MN.formula(ox, float(oxygens), cation_total); em = MN.end_members(mineral, ap)
        sh.snap(); made = []
        basis = MN.basis_text(oxygens, cation_total)
        for c, v in ap.items():
            made.append(sh.add_column(f"{c} (apfu)" if c != "Sum" else "Cation sum", v, units=f"apfu, {oxygens:g} O", snap=False,
                                      formula=MN.apfu_text(c, basis)))
        for k, v in em.items():
            made.append(sh.add_column(k, v, units=MN.unit_of(k), desig="Label" if np.asarray(v).dtype.kind in "OUS" else "Y", snap=False,
                                      formula=MN.FORMULA_TEXT.get(k, "")))
        sh.model.refresh(); sh.changed()
        self.statusBar().showMessage(f"{mineral} formula on {oxygens:g} oxygens: {len(made)} columns added", 8000); return made

    def clear_fits(self):
        """Remove fit curves, bands and fit parameter boxes from the active graph (one undo step)."""
        g = self.need_graph()
        if not g: return
        g.snapshot(); g.fits = []
        g.spec["annotations"] = [a for a in g.spec.get("annotations", []) if not (a.get("kind") == "text" and " fit\n" in a.get("text", ""))]
        g.draw(); self.mark_dirty()

    def ions_to_meq(self, sh=None):
        """meq/L columns for the ion columns (selected, or all named after a major ion). With Ca, Mg, Na, Cl, SO4 and HCO3 or CO3
        present, also the six Piper columns in plot order (Ca as X; Na+K and HCO3+CO3 summed), and the mg/L columns set to Ignore.
        One undo step."""
        from .plots4 import ion_of, mg_to_meq, EQUIV_WEIGHT
        sh = sh or self.need_book()
        if not sh: return
        cols = [c for c in (sh.selected_cols() or list(sh.df.columns)) if ion_of(c) and "meq" not in str(c)]
        if not cols: raise RuntimeError("No column is named after a major ion (Ca, Mg, Na, K, HCO3, CO3, Cl, SO4, NO3, F).")
        meq = {}
        for c in cols: meq.setdefault(ion_of(c), mg_to_meq(c, sh.arr(c, raw=True)))
        sh.snap(); made = []
        zero = lambda k: meq.get(k, np.zeros(len(sh.df)))
        piper = all(k in meq for k in ("Ca", "Mg", "Na", "Cl", "SO4")) and ("HCO3" in meq or "CO3" in meq)
        if piper:
            for name, v in (("Ca (meq/L)", meq["Ca"]), ("Mg (meq/L)", meq["Mg"]), ("Na+K (meq/L)", meq["Na"] + np.nan_to_num(zero("K"))),
                            ("Cl (meq/L)", meq["Cl"]), ("SO4 (meq/L)", meq["SO4"]),
                            ("HCO3+CO3 (meq/L)", np.where(np.isnan(zero("HCO3")) & np.isnan(zero("CO3")), np.nan,
                                                          np.nan_to_num(zero("HCO3")) + np.nan_to_num(zero("CO3"))))):
                made.append(sh.add_column(name, v, desig="X" if name.startswith("Ca") else "Y", units="meq/L", snap=False,
                                          formula=f"{name.split(' ')[0]} in meq/L = mg/L / equivalent weight (" + ", ".join(
                                              f"{k} {EQUIV_WEIGHT[k]}" for k in name.split(" ")[0].split("+") if k in EQUIV_WEIGHT) + " g/eq)"))
            for c in cols: sh.desig[c] = "Ignore"
            for c in sh.df.columns:  # only one X column: the old one becomes Ignore so Ca (meq/L) is used
                if sh.desig.get(c) == "X" and c != made[0]: sh.desig[c] = "Ignore"
        else:
            for c in cols: made.append(sh.add_column(f"{ion_of(c)} (meq/L)", meq[ion_of(c)], desig=sh.desig.get(c, "Y"), units="meq/L", snap=False,
                                                     formula=f"{c} / {EQUIV_WEIGHT[ion_of(c)]} (equivalent weight of {ion_of(c)}, g/eq)"))
        sh.model.refresh(); sh.changed()
        self.statusBar().showMessage(f"Added {', '.join(made)}" + (" (Piper diagram columns; select the Y columns and plot)" if piper else ""), 10000)
        return made

    def ions_water_example(self, sh):
        """Example water chemistry: the same conversion as Column > Convert Ions."""
        sh.view.selectionModel().clearSelection() if hasattr(sh, "view") else None
        self.ions_to_meq(sh)

    def new_graph(self, sh, ptype, x, ys, extra=None):
        spec = {"type": ptype, "book": sh.book.name, "sheet": sh.name, "x": x, "ys": ys, "extra": extra or {}}
        if ptype in GraphWindow.ERRBAR_TYPES:
            emap = self.bind_errors(sh, ys)
            if emap: spec["yerr"] = emap; spec["ys"] = [y for y in ys if sh.desig.get(y) not in self.ERR_ROLES] or ys
        g = self.add_win(GraphWindow(self, self.uniq("Graph"), spec)); g.draw(); return g

    def _thumb_dir(self):
        return str(user_dir() / "thumbs" / VERSION)

    def _menu_icons(self, menu):
        if menu.property("iconsDone"): return
        from .gallery import thumbnail
        for a in menu.actions():
            if a.data(): a.setIcon(thumbnail(a.data(), self._thumb_dir()))
        menu.setProperty("iconsDone", True)

    def show_gallery(self):
        from .gallery import PlotGallery, MATRIX_KINDS
        b = self.active("book"); hint = ""
        if b is not None:
            x, ys = b.current().xy_for_plot(); hint = f"Will plot from {b.name}/{b.current().name}: X = {x or 'row number'}; Y = {', '.join(map(str, ys)) or '(select columns)'}"
        d = PlotGallery(self, self._thumb_dir(), hint)
        if not d.exec() or not d.choice: return
        if isinstance(d.choice, tuple) and d.choice[0] == "example":
            from .examples import for_plot
            return self.open_example(for_plot(d.choice[1]), d.choice[1])
        if d.choice in MATRIX_KINDS: return self.need_matrix() and self.new_matrix_graph(self.need_matrix(), d.choice)
        return self.plot(d.choice)

    def plot(self, ptype):
        b = self.need_book()
        if not b: return
        if ptype in ("Color-mapped Scatter", "Bubble + Color", "Color-mapped Line", "Ternary + Color"):
            from .cmapdlg import ColorMapDialog
            d = ColorMapDialog(self, b, ptype, self.settings.get("cmap_opts"))
            if not d.exec(): return
            x, ys = d.columns(); opts = d.options(); self.settings["cmap_opts"] = {k: v for k, v in opts.items() if k not in ("group", "label", "size")}
            save_settings(self.settings); return self.new_graph(b, ptype, x, ys, opts)
        x, ys = b.xy_for_plot()
        if not ys: return QMessageBox.warning(self, APP, "Select one or more Y columns (click the column headers).")
        extra = {}
        if ptype == "Isochron (York regression)":
            from .geochron import SYSTEMS
            s_, ok = QInputDialog.getItem(self, "Isochron", "Decay system:", list(SYSTEMS), 0, False)
            if not ok: return
            extra["system"] = s_
        if ptype == "Sankey (flows)":
            cols = [str(c) for c in b.df.columns]
            d = FormDialog(self, "Sankey diagram", [("Source column", combo(cols)), ("Target column", combo(cols, cols[min(1, len(cols) - 1)])),
                                                    ("Value column", combo(cols, cols[-1]))])
            if not d.exec(): return
            extra = {"src": d.val("Source column"), "dst": d.val("Target column"), "val": d.val("Value column")}
            return self.new_graph(b, ptype, extra["src"], [extra["val"]], extra)
        if ptype == "Dendrogram (cluster rows)":
            m, ok = QInputDialog.getItem(self, "Dendrogram", "Linkage:", ["ward", "average", "complete", "single"], 0, False)
            if not ok: return
            extra["method"] = m
        if ptype == "Q-Q Plot":
            dist, ok = QInputDialog.getItem(self, "Q-Q plot", "Distribution:", ["norm", "lognorm", "expon", "weibull_min", "gamma"], 0, False)
            if not ok: return
            extra["dist"] = dist
        if ptype == "Histogram":
            n, ok = QInputDialog.getInt(self, "Histogram", "Number of bins (0 = automatic):", 0, 0, 1000)
            if not ok: return
            if n: extra["bins"] = n
        self.new_graph(b, ptype, x, ys, extra)

    def need_graph(self):
        g = self.active("graph")
        if g is None: QMessageBox.warning(self, APP, "Open a graph first.")
        return g

    def edit_plot(self):
        g = self.need_graph()
        if g: g.fmt.reopen()

    def split_panels(self, rows=None, cols=None):
        """One panel per Y column in a rows x columns grid (0 = automatic); rows=0, cols=-1 turns panels off."""
        g = self.need_graph()
        if not g: return
        if rows is None:
            if len(g.spec.get("ys", [])) < 2: raise RuntimeError("Panels need two or more Y columns (Edit plot... adds columns).")
            p = g.spec.get("panels") or {}
            d = FormDialog(self, "Split into panels", [("Rows (0 = automatic)", spin(0, 12, p.get("rows", 0))),
                                                       ("Columns (0 = automatic)", spin(0, 12, p.get("cols", 0))), ("One panel per Y column", QCheckBox())])
            d.w["One panel per Y column"].setChecked(True)

            def mutate(g_, d_):
                if d_.val("One panel per Y column"): g_.spec["panels"] = {"rows": d_.val("Rows (0 = automatic)"), "cols": d_.val("Columns (0 = automatic)")}
                else: g_.spec.pop("panels", None)
            d.live_graph(g, mutate); d.exec(); return g
        g.snapshot()
        if cols == -1: g.spec.pop("panels", None)
        else:
            if len(g.spec.get("ys", [])) < 2: raise RuntimeError("Panels need two or more Y columns (Edit plot... adds columns).")
            g.spec["panels"] = {"rows": int(rows), "cols": int(cols)}
        g.draw(); self.mark_dirty(); return g

    def graph_props(self):
        g = self.need_graph()
        if not g: return
        StyleDialog(self, g.spec["style"] or {}, graph=g).exec()  # live preview; OK/Apply keep the changes

    def apply_template(self):
        g = self.need_graph()
        if not g: return
        from .graphs import template_names, load_template
        d = FormDialog(self, "Apply template / theme", [("Template", combo(template_names()))])
        d.live_graph(g, lambda g_, d_: g_.spec.__setitem__("style", {**g_.spec["style"], **load_template(d_.val("Template"))}))
        d.exec(); return g

    def default_theme(self):
        if set_default_theme(self): self.refresh_all()

    def dup_graph(self):
        g = self.need_graph()
        if not g: return
        n = self.add_win(GraphWindow(self, self.uniq("Graph"), json.loads(json.dumps(g.spec)))); n.fits = list(g.fits); n.draw()

    def refresh_graphs(self, sheet):
        for w in self.windows():
            if w.kind == "graph" and w.spec.get("book") == sheet.book.name and w.spec.get("sheet", sheet.name) == sheet.name:
                try: w.draw()
                except Exception as e: self.statusBar().showMessage(f"{w.name}: {e}", 6000)

    def refresh_all(self):
        for w in self.windows():
            if w.kind in ("graph", "layout"): w.draw()

    def new_layout(self):
        names = [w.name for w in self.windows() if w.kind == "graph"]
        if not names: return QMessageBox.warning(self, APP, "Make some graphs first.")
        d = LayoutDialog(self, names)
        if d.exec():
            spec = d.value()
            if spec["graphs"]: self.add_win(LayoutWindow(self, self.uniq("Layout"), spec)).draw()

    def edit_layout(self):
        L = self.active("layout")
        if not L: return QMessageBox.warning(self, APP, "Open a layout page first.")
        d = LayoutDialog(self, [w.name for w in self.windows() if w.kind == "graph"], L.spec)
        if d.exec(): L.spec = d.value(); L.draw()

    # ---- analysis helpers
    def first_xy(self):
        b = self.need_book()
        if not b: raise RuntimeError("no workbook")
        x, ys = b.xy_for_plot()
        if not ys: raise RuntimeError("Select a Y column first.")
        xv = b.arr(x) if x else np.arange(1.0, len(b.df) + 1)
        yv = b.arr(ys[0]); m = np.isfinite(xv) & np.isfinite(yv)
        return b, x or "Row", ys[0], xv[m], yv[m]

    def graph_for(self, b, ycol, ptype="Scatter"):
        g = self.active("graph")
        if g and g.spec.get("book") == b.book.name and g.spec.get("sheet") == b.name and ycol in g.spec.get("ys", []): return g
        return self.new_graph(b, ptype, b.x_col(), [ycol])

    def fit_html(self, b, xname, yname, lo_x, hi_x, r, auto=False):
        gof = {k: r[k] for k in ("N", "DOF", "R2", "Adj_R2", "Reduced_ChiSq", "RMSE", "ChiSq_weighted", "Pearson_r", "p_slope") if k in r}
        note = "<p><i>Recalculates automatically when the data change.</i></p>" if auto else ""
        return note + table_html(f"{r['model']} fit of {yname} vs {xname} ({b.book.name}/{b.name}), X from {lo_x:.6g} to {hi_x:.6g}",
                                 A.param_table(r), ("Parameter", "Value", "Std. Error", "t", "p", "95% lower", "95% upper", "")) \
            + dict_html("Goodness of fit", gof)

    def fit_curves(self, g, r, opts, lo_x, hi_x, op=None):
        xs = np.linspace(lo_x, hi_x, 400)
        for key, label, color in (("pred", "95% prediction", "gray"), ("conf", "95% confidence", "red")):
            if opts.get(key) and f"{key}_band" in r:
                lo, hi = r[f"{key}_band"](xs)
                g.fits.append({"band": True, "x": list(map(float, xs)), "y": list(map(float, lo)), "y2": list(map(float, hi)),
                               "label": label, "color": color, "op": op})
        g.fits.append({"x": list(map(float, xs)), "y": list(map(float, r["func"](xs))), "label": f"{r['model']} fit", "style": "r-", "op": op})

    def fit_report(self, b, xname, yname, xv, yv, r, opts=None):
        opts = opts or {"conf": True}
        lo_x = opts.get("xfrom") if opts.get("xfrom") is not None else np.nanmin(xv)
        hi_x = opts.get("xto") if opts.get("xto") is not None else np.nanmax(xv)
        op = uuid.uuid4().hex[:8] if opts.get("auto") else None
        rw = self.report(f"Fit: {r['model']}", self.fit_html(b, xname, yname, lo_x, hi_x, r, bool(op)))
        g = self.graph_for(b, yname); g.snapshot(); self.fit_curves(g, r, opts, lo_x, hi_x, op); g.draw()
        if opts.get("param_box") and g.fig.axes and g.fig.axes[0].name == "rectilinear":  # draggable box with the result
            ax = g.fig.axes[0]; (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
            lines = [f"{r['model']} fit", f"R\u00b2 = {r['R2']:.5f}"] + [f"{k} = {v:.5g} \u00b1 {r['errors'].get(k, np.nan):.2g}" for k, v in r["params"].items()]
            g.spec.setdefault("annotations", []).append({"kind": "text", "x": x0 + 0.03 * (x1 - x0), "y": y1 - 0.06 * (y1 - y0),
                                                         "text": "\n".join(lines), "size": 8}); g.draw()
        full_x = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        fitc = b.add_column(f"Fit_{yname}", r["func"](full_x)); res = b.add_column(f"Resid_{yname}", b.arr(yname) - r["func"](full_x))
        if op:
            cfg = {k: v for k, v in opts.items() if k not in ("p0",)}
            b.ops.append({"id": op, "kind": "fit", "cfg": cfg, "x": b.x_col(), "y": yname, "fit_col": fitc, "res_col": res,
                          "graph": g.name, "report": rw.name, "xname": xname})
        for comp_i, comp in enumerate(r.get("components", []), 1):
            b.add_column(f"Peak{comp_i}_{yname}", comp(full_x))
        if opts.get("resid"):
            rg = self.new_graph(b, "Scatter", b.x_col(), [res]); rg.spec["style"] = {"title": f"Residuals of {yname}"}
            rg.fits.append({"x": [float(np.nanmin(full_x)), float(np.nanmax(full_x))], "y": [0.0, 0.0], "label": "zero", "style": "k--"})
            rg.draw()

    def fit_poly(self, order):
        b, xn, yn, x, y = self.first_xy()
        if order is None:
            order, ok = QInputDialog.getInt(self, "Polynomial fit", "Order:", 2, 1, 9)
            if not ok: return
        self.fit_report(b, xn, yn, x, y, A.fit_polynomial(x, y, order))

    def fit_nl(self, user=False):
        b, xn, yn, x, y = self.first_xy()
        last = dict(getattr(self, "last_fit", None) or {})
        if user: last["model"] = "User-defined..."
        d = FitDialog(self, x, y, [str(c) for c in b.df.columns], last, weights={str(c): b.arr(c) for c in b.df.columns})
        if not d.exec(): return
        cfg = d.value(); self.last_fit = {**cfg, "model": d.func.currentText()}
        xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        r = run_fit(cfg, xf, b.arr(yn), b.arr(cfg["weight_col"]) if cfg["weight_col"] else None)
        self.fit_report(b, xn, yn, x, y, r, cfg)

    def fit_user(self): self.fit_nl(user=True)

    def mlr(self):
        b = self.need_book()
        if not b: return
        from PySide6.QtWidgets import QListWidget, QAbstractItemView
        cols = [str(c) for c in b.df.columns]; lst = QListWidget(); lst.addItems(cols)
        lst.setSelectionMode(QAbstractItemView.MultiSelection)
        d = FormDialog(self, "Multiple linear regression", [("Dependent (Y) column", combo(cols, cols[-1])), ("Independent (X) columns", lst)])
        if not d.exec(): return
        self.run_mlr(b, d.val("Dependent (Y) column"), [i.text() for i in lst.selectedItems()])

    def run_mlr(self, b, ycol, xcols):
        xcols = [c for c in xcols if c != ycol]
        if not xcols: raise RuntimeError("Choose at least one independent column.")
        r = A.multiple_regression(b.arr(ycol), np.column_stack([b.arr(c) for c in xcols]), xcols)
        self.report("Multiple regression", table_html(f"Multiple linear regression of {ycol} ({b.book.name}/{b.name})", r["coef"],
                    ["Term", "Coefficient", "Std. Error", "t", "p", "95% lower", "95% upper", "VIF"])
                    + table_html("ANOVA", r["anova"], ["Source", "SS", "df", "MS", "F", "p"]) + dict_html("Statistics", r["stats"]))
        fit = np.full(len(b.df), np.nan); res = np.full(len(b.df), np.nan); idx = np.nonzero(r["mask"])[0]
        fit[idx] = r["fitted"]; res[idx] = r["residuals"]
        b.add_column(f"MLR_fit_{ycol}", fit); b.add_column(f"MLR_resid_{ycol}", res)
        return r

    def fit_peaks(self):
        b, xn, yn, x, y = self.first_xy()
        found = ", ".join(f"{p['X']:.4g}" for p in A.find_peaks(x, y))
        d = FormDialog(self, "Multiple peak fit", [("Peak centres (comma)", QLineEdit(found)),
                                                    ("Shape", combo(["Gaussian", "Lorentzian"]))])
        if not d.exec(): return
        centers = [float(s) for s in d.val("Peak centres (comma)").split(",") if s.strip()]
        self.fit_report(b, xn, yn, x, y, A.fit_multipeak(x, y, centers, d.val("Shape")))

    def xy_op(self, tag, fn):
        b, xn, yn, x, y = self.first_xy(); b.add_column(f"{tag}_{yn}", fn(x, y))

    def integ(self):
        b, xn, yn, x, y = self.first_xy(); b.add_column(f"Int_{yn}", A.integrate_cum(x, y))
        self.report("Integration", dict_html(f"Area under {yn}", {"Area (trapezoid)": A.area(x, y), "x from": x.min(), "x to": x.max()}))

    def interp(self):
        b, xn, yn, x, y = self.first_xy()
        d = FormDialog(self, "Interpolate", [("Points", spin(3, 1000000, 200)), ("Method", combo(["linear", "quadratic", "cubic"], "cubic"))])
        if d.exec():
            xi, yi = A.interpolate_xy(x, y, d.val("Points"), d.val("Method"))
            b.book.add_sheet(f"Interp_{yn}", pd.DataFrame({f"{xn}_i": xi, f"{yn}_i": yi}))

    def norm(self):
        b, xn, yn, x, y = self.first_xy()
        m, ok = QInputDialog.getItem(self, "Normalize", "Method:", ["0-1", "Z-score", "Divide by max"], 0, False)
        if ok: b.add_column(f"Norm_{yn}", A.normalize(b.arr(yn), m))

    def smooth(self):
        b, xn, yn, x, y = self.first_xy()
        d = FormDialog(self, "Smooth", [("Method", combo(["Savitzky-Golay", "Adjacent average", "Median"])),
                                        ("Window (points)", spin(3, 9999, 7)), ("Polynomial order", spin(0, 10, 2))])
        if d.exec():
            ys = A.smooth(y, d.val("Method"), d.val("Window (points)"), d.val("Polynomial order"))
            b.add_column(f"Smooth_{yn}", ys); self.graph_for(b, yn, "Line").add_curve(x, ys, "Smoothed")

    def fft(self):
        b, xn, yn, x, y = self.first_xy(); fq, amp, ph = A.fft(x, y)
        sh = b.book.add_sheet(f"FFT_{yn}", pd.DataFrame({"Frequency": fq, "Amplitude": amp, "Phase": ph}))
        sh.desig["Phase"] = "Ignore"; self.new_graph(sh, "Line", "Frequency", ["Amplitude"])

    def fft_filter(self):
        b, xn, yn, x, y = self.first_xy()
        c, ok = QInputDialog.getDouble(self, "FFT low-pass", "Cut-off frequency (1/x units):", 1.0, 0, 1e12, 6)
        if ok:
            yf = A.fft_lowpass(x, y, c); b.add_column(f"LowPass_{yn}", yf); self.graph_for(b, yn, "Line").add_curve(x, yf, "Low-pass")

    def baseline(self):
        b, xn, yn, x, y = self.first_xy()
        d = FormDialog(self, "ALS baseline", [("Smoothness (lambda)", spin(1, 1e12, 1e5, True)), ("Asymmetry p", spin(0.0001, 0.5, 0.01, True))])
        if d.exec():
            z = A.baseline_als(y, d.val("Smoothness (lambda)"), d.val("Asymmetry p"))
            b.add_column(f"Base_{yn}", z); b.add_column(f"Corr_{yn}", y - z)
            self.graph_for(b, yn, "Line").add_curve(x, z, "Baseline", "k--")

    def peaks(self):
        b, xn, yn, x, y = self.first_xy()
        prom, ok = QInputDialog.getDouble(self, "Find peaks", "Minimum prominence (0 = 5% of range):", 0, 0, 1e15, 6)
        if not ok: return
        pk = A.find_peaks(x, y, prom or None)
        self.report("Peaks", table_html(f"{len(pk)} peaks in {yn}", [list(p.values()) for p in pk], list(pk[0]) if pk else ["-"]))
        if pk: self.graph_for(b, yn, "Line").add_curve([p["X"] for p in pk], [p["Y"] for p in pk], "Peaks", "rv")

    # ---- statistics
    def sel_arrays(self, minimum=1):
        b = self.need_book()
        if not b: raise RuntimeError("no workbook")
        cols = [c for c in (b.selected_cols() or [c for c in b.df.columns if b.desig.get(c) == "Y"])
                if pd.to_numeric(b.df[c], errors="coerce").notna().any()]
        if len(cols) < minimum: raise RuntimeError(f"Select at least {minimum} numeric column(s).")
        return b, cols, {c: b.arr(c) for c in cols}

    def desc(self):
        b, cols, d = self.sel_arrays(); stats = {c: A.descriptive(v) for c, v in d.items()}
        keys = list(stats[cols[0]])
        self.report("Descriptive statistics", table_html(f"Descriptive statistics ({b.book.name}/{b.name})",
                    [[k] + [stats[c].get(k) for c in cols] for k in keys], ["Statistic"] + [str(c) for c in cols]))

    def corr(self):
        b, cols, d = self.sel_arrays(2); names, pr, sr = A.correlation(d)
        self.report("Correlation", table_html("Pearson r", [[n] + list(r) for n, r in zip(names, pr)], [""] + names)
                    + table_html("Spearman rho", [[n] + list(r) for n, r in zip(names, sr)], [""] + names))

    def normality(self):
        b, cols, d = self.sel_arrays()
        self.report("Normality", "".join(dict_html(c, {**A.normality(v), **{f"Anderson-Darling {k}": x for k, x in D.anderson_darling(v).items()}})
                                         for c, v in d.items()))

    def t1(self):
        b, cols, d = self.sel_arrays()
        mu, ok = QInputDialog.getDouble(self, "One-sample t-test", "Test mean:", 0, -1e15, 1e15, 6)
        if ok: self.report("t-test", "".join(dict_html(f"One-sample t-test: {c}", A.ttest_one(v, mu)) for c, v in d.items()))

    def t2(self):
        b, cols, d = self.sel_arrays(2)
        eq = QMessageBox.question(self, "Two-sample t-test", "Assume equal variances?\n(No = Welch test)") == QMessageBox.Yes
        self.report("t-test", dict_html(f"Two-sample t-test: {cols[0]} vs {cols[1]}", A.ttest_two(d[cols[0]], d[cols[1]], eq)))

    def tpair(self):
        b, cols, d = self.sel_arrays(2)
        self.report("t-test", dict_html(f"Paired t-test: {cols[0]} vs {cols[1]}", A.ttest_paired(d[cols[0]], d[cols[1]])))

    def np2(self):
        b, cols, d = self.sel_arrays(2)
        self.report("Nonparametric", dict_html(f"{cols[0]} vs {cols[1]}", A.nonparam(d[cols[0]], d[cols[1]])))

    def anova1(self):
        b, cols, d = self.sel_arrays(2)
        d = {str(k): v for k, v in d.items()}
        self.report("ANOVA", dict_html(f"One-way ANOVA: {', '.join(d)}", A.anova_oneway(*d.values()))
                    + table_html("Group means", [[c, A.descriptive(v)["N"], A.descriptive(v)["Mean"], A.descriptive(v)["SD"]]
                                                 for c, v in d.items()], ["Group", "N", "Mean", "SD"])
                    + dict_html("Homogeneity of variance", A.homogeneity(d))
                    + table_html("Tukey HSD post-hoc", A.tukey(d), ["Pair", "Mean diff", "95% lower", "95% upper", "p", "Significant (0.05)"])
                    + table_html("Bonferroni pairwise t-tests", A.bonferroni(d),
                                 ["Pair", "Mean diff", "t", "p", "p (Bonferroni)", "Significant (0.05)"]))

    def anova2(self):
        b = self.need_book()
        if not b: return
        cols = [str(c) for c in b.df.columns]
        d = FormDialog(self, "Two-way ANOVA (long format)", [("Response column", combo(cols)), ("Factor A column", combo(cols)),
                                                              ("Factor B column", combo(cols))])
        if not d.exec(): return
        sub = b.df[[d.val("Response column"), d.val("Factor A column"), d.val("Factor B column")]].dropna()
        res = A.anova_twoway(pd.to_numeric(sub.iloc[:, 0], errors="coerce"), sub.iloc[:, 1], sub.iloc[:, 2])
        self.report("Two-way ANOVA", table_html("Two-way ANOVA", [[k, v.get("SS"), v.get("df"), v.get("F", ""), v.get("p", "")]
                                                                   for k, v in res.items()], ["Source", "SS", "df", "F", "p"]))

    def rmanova(self):
        b, cols, d = self.sel_arrays(2)
        self.report("RM ANOVA", dict_html(f"Repeated-measures ANOVA, conditions: {', '.join(map(str, cols))}",
                                          A.rm_anova(np.column_stack(list(d.values())))))

    def kruskal(self):
        b, cols, d = self.sel_arrays(2)
        self.report("Kruskal-Wallis", dict_html(f"Kruskal-Wallis: {', '.join(map(str, cols))}", A.kruskal(d)))

    def wilcoxon(self):
        b, cols, d = self.sel_arrays(2)
        self.report("Wilcoxon", dict_html(f"Wilcoxon signed-rank: {cols[0]} vs {cols[1]}", A.wilcoxon(d[cols[0]], d[cols[1]])))

    def chisq(self):
        b = self.need_book()
        if not b: return
        cols = [str(c) for c in b.df.columns]
        dlg = FormDialog(self, "Chi-square test", [("Category column A", combo(cols)),
                                                    ("Category column B", combo(cols, cols[min(1, len(cols) - 1)]))])
        if not dlg.exec(): return
        sub = b.df[[dlg.val("Category column A"), dlg.val("Category column B")]].dropna()
        tab, res = A.chi_square(sub.iloc[:, 0].astype(str).to_numpy(), sub.iloc[:, 1].astype(str).to_numpy())
        self.report("Chi-square", table_html("Contingency table", [[i] + list(r) for i, r in zip(tab.index, tab.values)],
                                             [""] + list(map(str, tab.columns))) + dict_html("Chi-square test of independence", res))

    def grubbs(self):
        b, cols, d = self.sel_arrays()
        alpha, ok = QInputDialog.getDouble(self, "Grubbs test", "Significance level:", 0.05, 0.001, 0.5, 3)
        if not ok: return
        html, cells = "", []
        for c, v in d.items():
            out = A.grubbs(v, alpha)
            html += table_html(f"Grubbs outliers in {c} (alpha = {alpha})", [list(o.values()) for o in out] or [["none", "", ""]],
                               ["Value", "G", "G critical"])
            raw = b.arr(c); cells += [(c, int(i)) for o in out for i in np.nonzero(raw == o["Value"])[0]]
        self.report("Outliers", html)
        if cells and QMessageBox.question(self, APP, f"Mask the {len(cells)} outlier cell(s)?") == QMessageBox.Yes:
            b.set_mask(cells, True)

    def distfit(self):
        b, cols, d = self.sel_arrays()
        self.report("Distribution fit", "".join(table_html(f"Distribution fit: {c} (best first, by AIC)", A.distribution_fit(v),
                    ["Distribution", "Parameters (scipy order)", "Log-likelihood", "AIC", "KS D", "KS p"]) for c, v in d.items()))

    # ---- gadgets
    GADGETS = (("Quick linear fit", "lin"), ("Quick fit with function...", "fit"), ("Statistics", "stats"),
               ("Integrate (area)", "area"), ("FFT of region", "fft"), ("Find peaks", "peaks"),
               ("Mask points in region", "mask"), ("Unmask points in region", "unmask"))

    def gadget_menu(self, g, lo, hi):
        m = QMenu(self); m.addSection(f"X from {lo:.6g} to {hi:.6g}")
        for text, fn in self.GADGETS:
            m.addAction(text, lambda fn=fn: self.safe(lambda: self.gadget(g, fn, lo, hi)))
        m.exec(QCursor.pos())

    def gadget(self, g, what, lo, hi):
        sh, x, ys = g.data(); x = np.asarray(x, float); col = g.spec["ys"][0]
        if what in ("mask", "unmask"):
            xr = sh.arr(g.spec["x"], raw=True) if g.spec.get("x") else np.arange(1.0, len(sh.df) + 1)
            rows = np.nonzero((xr >= lo) & (xr <= hi))[0]
            return sh.set_mask([(c, int(r)) for c in g.spec["ys"] for r in rows], what == "mask")
        m = (x >= lo) & (x <= hi) & np.isfinite(ys[0]); xs, yv = x[m], ys[0][m]
        if m.sum() < 2: raise RuntimeError("Fewer than two points in the region.")
        tag = f"{col}, X {lo:.4g} to {hi:.4g}"
        if what in ("lin", "fit"):
            if what == "lin": r = A.fit_polynomial(xs, yv, 1)
            else:
                name, ok = QInputDialog.getItem(self, "Quick fit", "Function:", list(A.MODELS), 0, False)
                if not ok: return
                r = A.fit_model(xs, yv, name)
            t = np.linspace(xs.min(), xs.max(), 200); g.add_curve(t, r["func"](t), f"{r['model']} ({lo:.3g}-{hi:.3g})")
            gof = {k: r[k] for k in ("N", "R2", "Adj_R2", "RMSE") if k in r}
            self.report("Region fit", table_html(f"{r['model']} fit: {tag}", A.param_table(r),
                        ("Parameter", "Value", "Std. Error", "t", "p", "95% lower", "95% upper", "")) + dict_html("Goodness of fit", gof))
            return r
        if what == "stats":
            return self.report("Region statistics", dict_html(f"Statistics: {tag}", A.descriptive(yv)))
        if what == "area":
            return self.report("Region area", dict_html(f"Integration: {tag}", {"Area": A.area(xs, yv), "Points": len(xs),
                               "Y max": yv.max(), "X at Y max": xs[np.argmax(yv)], "Mean Y": yv.mean()}))
        if what == "fft":
            fq, amp, ph = A.fft(xs, yv)
            new = sh.book.add_sheet(f"FFT_region_{col}", pd.DataFrame({"Frequency": fq, "Amplitude": amp, "Phase": ph}))
            new.desig["Phase"] = "Ignore"; return self.new_graph(new, "Line", "Frequency", ["Amplitude"])
        if what == "peaks":
            pk = A.find_peaks(xs, yv)
            self.report("Region peaks", table_html(f"{len(pk)} peaks: {tag}", [list(p.values()) for p in pk], list(pk[0]) if pk else ["-"]))
            if pk: g.add_curve([p["X"] for p in pk], [p["Y"] for p in pk], "Peaks", "rv")
            return pk

    # ---- batch
    def batch_columns(self, cfg=None):
        b = self.need_book()
        if not b: return
        x, ys = b.xy_for_plot()
        if not ys: raise RuntimeError("Select the Y columns to fit.")
        xf = b.arr(x) if x else np.arange(1.0, len(b.df) + 1)
        if cfg is None:
            d = FitDialog(self, xf, b.arr(ys[0]), [str(c) for c in b.df.columns], getattr(self, "last_fit", None))
            d.setWindowTitle("Batch fit: set up the function (initial values are re-guessed for each column)")
            if not d.exec(): return
            cfg = d.value()
        rows = []; g = self.new_graph(b, "Scatter", x, ys)
        for c in ys:
            try:
                r = run_fit(cfg, xf, b.arr(c), use_p0=cfg["model"] == "User")
                rows.append({"Column": str(c), **r["params"], **{f"SE_{k}": v for k, v in r["errors"].items()},
                             "R2": r["R2"], "Adj_R2": r["Adj_R2"], "RMSE": r["RMSE"], "N": r["N"], "Error": ""})
                t = np.linspace(np.nanmin(xf), np.nanmax(xf), 300)
                g.fits.append({"x": list(map(float, t)), "y": list(map(float, r["func"](t))), "label": f"fit {c}", "style": "-"})
            except Exception as e:
                rows.append({"Column": str(c), "Error": str(e)})
        g.draw(); return b.book.add_sheet(f"BatchFit_{cfg['model'][:12]}", pd.DataFrame(rows))

    def batch_files(self, plan=None):
        """plan (for scripting/tests): dict(opts, paths, x, y, op, keep, cfg)."""
        if plan is None:
            wiz = ImportWizard(self); wiz.setWindowTitle("Batch: choose a sample file and the import settings for all files")
            if not wiz.exec() or not wiz.path.text(): return
            opts = wiz.options(); first, _ = read_with_options(wiz.path.text(), **opts)
            d = BatchFilesDialog(self, list(first.columns)); d.files.addItem(wiz.path.text())
            if not d.exec() or not d.paths(): return
            plan = {"opts": opts, "paths": d.paths(), "x": d.xcol.currentText(), "y": d.ycol.currentText(),
                    "op": d.op.currentText(), "keep": d.keep.isChecked(), "cfg": None}
            if plan["op"].startswith("Nonlinear"):
                fd = FitDialog(self, pd.to_numeric(first[plan["x"]], errors="coerce").to_numpy(float),
                               pd.to_numeric(first[plan["y"]], errors="coerce").to_numpy(float), list(first.columns),
                               getattr(self, "last_fit", None))
                if not fd.exec(): return
                plan["cfg"] = fd.value()
        xc, yc, op, cfg = plan["x"], plan["y"], plan["op"], plan.get("cfg")
        rows, frames = [], []
        for path in plan["paths"]:
            row = {"File": Path(path).name}
            try:
                df, meta = read_with_options(path, **plan["opts"]); frames.append((Path(path).stem, df, meta))
                x = pd.to_numeric(df[xc], errors="coerce").to_numpy(float); y = pd.to_numeric(df[yc], errors="coerce").to_numpy(float)
                if op == "Linear fit":
                    r = A.fit_polynomial(x, y, 1)
                    row.update(Intercept=r["params"]["B0"], Slope=r["params"]["B1"], SE_Slope=r["errors"]["B1"], R2=r["R2"], N=r["N"])
                elif cfg is not None:
                    r = run_fit(cfg, x, y, use_p0=cfg["model"] == "User")
                    row.update(**r["params"], **{f"SE_{k}": v for k, v in r["errors"].items()}, R2=r["R2"], N=r["N"])
                elif op.startswith("Descriptive"):
                    row.update(A.descriptive(y))
                elif op.startswith("Area"):
                    row.update(Area=A.area(x, y), N=int(np.isfinite(y).sum()))
                else:
                    pk = A.find_peaks(*A._clean(x, y)); top = max(pk, key=lambda p: p["Y"]) if pk else {}
                    row.update(Peaks=len(pk), Largest_X=top.get("X"), Largest_Y=top.get("Y"), Largest_FWHM=top.get("FWHM"))
                row["Error"] = ""
            except Exception as e:
                row["Error"] = f"{type(e).__name__}: {e}"
            rows.append(row)
        summary = pd.DataFrame(rows)
        book = self.new_book(summary, self.uniq("Batch")); sh = book.current(); sh.name = "Summary"; book.tabs.setTabText(0, "Summary")
        sh.desig = {c: ("Label" if c == "File" else "Y") for c in summary.columns}
        if plan.get("keep"):
            for stem, df, meta in frames:
                new = book.add_sheet(stem, df); new.meta.update(meta); new.model.refresh()
        book.tabs.setCurrentIndex(0); sh.model.refresh(); self.refresh_explorer(); return book

    def show_manual(self, anchor=None):
        from .helpwin import ManualWindow, MANUAL
        if not MANUAL.exists(): raise RuntimeError("The user manual is not installed.")
        self._manual = ManualWindow(self, anchor); self._manual.show(); return self._manual

    def manual_pdf(self, fn=None):
        from .helpwin import save_manual_pdf
        if fn is None:
            fn, _ = QFileDialog.getSaveFileName(self, "Save user manual as PDF", "PlotBench_User_Manual.pdf", "PDF (*.pdf)")
            if not fn: return
        save_manual_pdf(fn); self.statusBar().showMessage(f"Saved {fn}", 6000); return fn

    def feedback(self):
        from .helpwin import FeedbackDialog
        FeedbackDialog(self, VERSION).exec()

    def open_example(self, key, kind=None):
        from .examples import open_example
        return open_example(self, key, kind)

    def save_examples(self, folder=None):
        import shutil
        from .examples import FOLDER
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the example files")
            if not folder: return
        out = Path(folder) / "PlotBench examples"; out.mkdir(exist_ok=True)
        for f in FOLDER.glob("*.csv"): shutil.copy2(f, out / f.name)
        self.statusBar().showMessage(f"Example files saved in {out}", 8000); return out

    def about(self):
        box = QMessageBox(self); box.setWindowTitle(f"About {APP}"); box.setText(self._about_text())
        from PySide6.QtGui import QPixmap
        pm = QPixmap(asset("logo.png"))
        if not pm.isNull(): box.setIconPixmap(pm.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        box.exec()

    def show_start(self):
        """Start page (templates, recent projects, quick actions). It does not block the window: work can start behind it, and it
        closes by itself when a sheet, graph or project opens."""
        if getattr(self, "_start_page", None) is not None: self._start_page.raise_(); self._start_page.activateWindow(); return
        d = StartPage(self); d.setModal(False); self._start_page = d

        def finished(r):
            self._start_page = None
            if not r or not d.choice: return
            kind, val = d.choice
            if kind == "template": return self.safe(lambda: make_template(self, val))
            if kind == "recent": return self.safe(lambda: self.open_project(val))
            if val == "show_console": return self.console_dock.show()
            return self.safe(getattr(self, val))
        d.finished.connect(finished); d.show(); return d

    def set_ribbon(self, on):
        """View > Ribbon Toolbar Layout: the top, bottom and right bars become four tabs (Home, Plot, Analysis, Petrology & Geochem)."""
        from .toolbars import build_toolbars
        self.settings["toolbar_layout"] = "ribbon" if on else "classic"; save_settings(self.settings)
        build_toolbars(self, getattr(self, "_theme", "light") or "light")
        if hasattr(self, "toolbar_menu"):
            self.toolbar_menu.clear()
            for tb in self.side_bars + [self.script_bar]: self.toolbar_menu.addAction(tb.toggleViewAction())

    def set_graph_panel(self, on):
        self.settings["graph_panel"] = bool(on); save_settings(self.settings)
        for w in self.windows():
            if getattr(w, "kind", "") == "graph" and hasattr(w, "host"): w.host.relayout()

    # ---- theme and toolbars
    def set_theme(self, theme, save=True):
        from .toolbars import apply_theme, build_toolbars
        if getattr(self, "_theme", None) == theme and getattr(self, "side_bars", None): return
        self._theme = theme; SH.PREFS["theme"] = theme; apply_theme(QApplication.instance(), theme)
        build_toolbars(self, theme)
        for a in (getattr(self, "dark_action", None), getattr(self, "theme_switch", None)):
            if a is not None and a.isChecked() != (theme == "dark"): a.blockSignals(True); a.setChecked(theme == "dark"); a.blockSignals(False)
        if hasattr(self, "toolbar_menu"):
            self.toolbar_menu.clear()
            for tb in self.side_bars + [self.script_bar]: self.toolbar_menu.addAction(tb.toggleViewAction())
        from PySide6.QtWidgets import QToolButton
        from PySide6.QtGui import QIcon
        from .ui_style import arrows
        ar = arrows(theme)
        for btn in self.findChildren(QToolButton):  # fold arrows on graph side panels follow the theme
            if btn.property("fold_header"): btn.setIcon(QIcon(ar["down" if btn.isChecked() else "right"]))
        for w in self.windows():  # repaint sheet colours for the new theme
            if w.kind in SHEETED:
                for sh in w.sheets: sh.model.refresh()
        if save: self.settings["theme"] = theme; save_settings(self.settings)

    # ---- recent projects, preferences, scripting
    def add_recent(self, fn):
        fn = str(Path(fn).resolve()); rec = [fn] + [r for r in self.settings.get("recent", []) if r != fn]
        self.settings["recent"] = rec[:10]; save_settings(self.settings); self.fill_recent()

    def fill_recent(self):
        self.recent_menu.clear()
        for r in self.settings.get("recent", []):
            self.recent_menu.addAction(r, lambda r=r: self.safe(lambda: self.open_project(r)))
        if not self.settings.get("recent"): self.recent_menu.addAction("(none)").setEnabled(False)

    def preferences(self):
        d = FormDialog(self, "Preferences", [("Significant digits shown in worksheets", spin(2, 17, self.settings["digits"])),
                                             ("Undo levels per sheet", spin(1, 500, self.settings["undo_levels"])),
                                             ("Show Python console at start-up", QCheckBox())])
        d.w["Show Python console at start-up"].setChecked(self.settings.get("console_at_start", False))
        if not d.exec(): return
        self.settings.update(digits=d.val("Significant digits shown in worksheets"), undo_levels=d.val("Undo levels per sheet"),
                             console_at_start=d.val("Show Python console at start-up"))
        SH.PREFS.update({k: self.settings[k] for k in SH.PREFS}); save_settings(self.settings)
        for w in self.windows():
            if w.kind in SHEETED:
                for sh in w.sheets: sh.model.refresh()

    def run_script(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Run Python script", "", "Python (*.py)")
            if not fn: return
        self.console_dock.show()
        return self.console.exec_source(Path(fn).read_text(encoding="utf-8"), fn)

    # ---- matrices
    def new_matrix_dialog(self):
        d = FormDialog(self, "New matrixbook", [("Rows", spin(1, 20000, 50)), ("Columns", spin(1, 20000, 50)),
                                                ("X from", spin(-1e12, 1e12, -5, True)), ("X to", spin(-1e12, 1e12, 5, True)),
                                                ("Y from", spin(-1e12, 1e12, -5, True)), ("Y to", spin(-1e12, 1e12, 5, True)),
                                                ("Values (formula, optional)", QLineEdit("exp(-(x**2 + y**2)/8) * cos(x)"))])
        if not d.exec(): return
        r, c = d.val("Rows"), d.val("Columns"); ext = [d.val("X from"), d.val("X to"), d.val("Y from"), d.val("Y to")]
        expr = d.val("Values (formula, optional)").strip()
        M = MX.from_formula(expr, r, c, ext) if expr else np.full((r, c), np.nan)
        ms = self.new_matrix(M, None, ext).current(); ms.formula = expr; return ms

    def import_image(self, fn=None, mode=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Import image", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif)")
            if not fn: return
        if mode is None:
            mode, ok = QInputDialog.getItem(self, "Import image", "Values from:", ["Grayscale", "Red", "Green", "Blue"], 0, False)
            if not ok: return
        M, ext = MX.image_to_matrix(fn, mode); b = self.new_matrix(M, Path(fn).stem, ext)
        self.new_matrix_graph(b.current(), "Image / Heat Map"); return b

    def mat_transform(self, op):
        ms = self.need_matrix()
        if ms: ms.set(*MX.transform(ms.M, ms.extent, op))

    def mat_resample(self):
        ms = self.need_matrix()
        if not ms: return
        d = FormDialog(self, "Resample matrix", [("Rows", spin(1, 20000, ms.M.shape[0] * 2)), ("Columns", spin(1, 20000, ms.M.shape[1] * 2)),
                                                 ("Interpolation", combo(["Nearest (0)", "Linear (1)", "Cubic (3)"], "Linear (1)"))])
        if d.exec(): ms.set(MX.resample(ms.M, d.val("Rows"), d.val("Columns"), int(d.val("Interpolation")[-2])))

    def mat_smooth(self):
        ms = self.need_matrix()
        if not ms: return
        d = FormDialog(self, "Smooth matrix", [("Method", combo(["Gaussian", "Median", "Mean"])), ("Size (sigma or window)", spin(0.1, 500, 2, True))])
        if d.exec():
            out = ms.book.add_sheet(f"{ms.name}_smooth", MX.smooth2d(ms.M, d.val("Method"), d.val("Size (sigma or window)")), ms.extent)
            self.new_matrix_graph(out, "Image / Heat Map")

    def mat_fft(self):
        ms = self.need_matrix()
        if not ms: return
        F = MX.fft2_magnitude(ms.M); ny, nx = F.shape
        out = ms.book.add_sheet(f"{ms.name}_FFT", F, [-nx // 2, nx - nx // 2 - 1, -ny // 2, ny - ny // 2 - 1]); out.zlabel = "log10(1+|F|)"
        self.new_matrix_graph(out, "Image / Heat Map")

    def mat_profile(self):
        ms = self.need_matrix()
        if not ms: return
        d = FormDialog(self, "Line profile", [("Along", combo(["row (constant Y)", "column (constant X)"])), ("At Y or X =", spin(-1e15, 1e15, 0, True))])
        if not d.exec(): return
        along = "row" if d.val("Along").startswith("row") else "col"; pos, vals = MX.profile(ms.M, ms.extent, along, d.val("At Y or X ="))
        sh = self.new_book(pd.DataFrame({"X" if along == "row" else "Y": pos, ms.label: vals}), self.uniq("Profile")).current()
        self.new_graph(sh, "Line", sh.df.columns[0], [sh.df.columns[1]])

    def mat_stats(self):
        ms = self.need_matrix()
        if ms: self.report("Matrix statistics", dict_html(f"Statistics of {ms.book.name}/{ms.name} ({ms.M.shape[0]} x {ms.M.shape[1]})",
                                                        A.descriptive(ms.M.ravel())))

    def mat_to_xyz(self):
        ms = self.need_matrix()
        if not ms: return
        x, y, z = MX.matrix_to_xyz(ms.M, ms.extent)
        b = self.new_book(pd.DataFrame({"X": x, "Y": y, "Z": z}), f"{ms.book.name}_XYZ"); sh = b.current()
        sh.desig.update({"X": "X", "Y": "Y", "Z": "Z"}); sh.model.refresh(); return sh

    def xyz_to_mat(self, method=None, n=None):
        b = self.need_book()
        if not b: return
        sel = b.selected_cols()
        cols = sel if len(sel) == 3 else [next((c for c in b.df.columns if b.desig.get(c) == d), None) for d in ("X", "Y", "Z")]
        if None in cols or len(cols) != 3: raise RuntimeError("Select three columns (X, Y, Z) or set column designations to X, Y and Z.")
        if method is None:
            d = FormDialog(self, "XYZ to matrix", [("Grid columns (X)", spin(2, 5000, 100)), ("Grid rows (Y)", spin(2, 5000, 100)),
                                                   ("Method", combo(["linear", "cubic", "nearest", "Shepard (inverse distance)", "Thin-plate spline"]))])
            if not d.exec(): return
            method, n = d.val("Method"), (d.val("Grid columns (X)"), d.val("Grid rows (Y)"))
        xyz = (b.arr(cols[0]), b.arr(cols[1]), b.arr(cols[2]))
        if method.startswith("Shepard"): M, ext = D.grid_idw(*xyz, n[0], n[1])
        elif method.startswith("Thin"): M, ext = D.grid_tps(*xyz, n[0], n[1])
        else: M, ext = MX.xyz_to_matrix(*xyz, n[0], n[1], method)
        mb = self.new_matrix(M, f"{b.book.name}_grid", ext); mb.current().zlabel = b.label(cols[2])
        self.new_matrix_graph(mb.current(), "Filled Contour"); return mb

    # ---- auto-recalculating analyses
    def schedule_ops(self, sheet):
        if sheet not in self.pending_ops: self.pending_ops.append(sheet)
        self.op_timer.start()

    def run_ops(self):
        sheets, self.pending_ops = self.pending_ops, []
        for sh in sheets:
            for op in list(sh.ops):
                try: self.rerun_fit(sh, op)
                except Exception as e: self.statusBar().showMessage(f"Auto-recalculation of {op.get('y')} failed: {e}", 8000)

    def rerun_fit(self, sh, op):
        cfg = op["cfg"]; xc = op["x"]
        if op["y"] not in sh.df.columns or (xc and xc not in sh.df.columns): return
        xf = sh.arr(xc) if xc else np.arange(1.0, len(sh.df) + 1)
        wc = cfg.get("weight_col"); r = run_fit(cfg, xf, sh.arr(op["y"]), sh.arr(wc) if wc and wc in sh.df.columns else None, use_p0=False)
        m = np.isfinite(xf) & np.isfinite(sh.arr(op["y"]))
        lo_x = cfg.get("xfrom") if cfg.get("xfrom") is not None else np.nanmin(xf[m])
        hi_x = cfg.get("xto") if cfg.get("xto") is not None else np.nanmax(xf[m])
        if op["fit_col"] in sh.df.columns: sh.df[op["fit_col"]] = r["func"](xf)
        if op["res_col"] in sh.df.columns: sh.df[op["res_col"]] = sh.arr(op["y"]) - r["func"](xf)
        sh.model.refresh()
        g = self.win(op["graph"])
        if g is not None and g.kind == "graph":
            g.fits = [f for f in g.fits if f.get("op") != op["id"]]; self.fit_curves(g, r, cfg, lo_x, hi_x, op["id"])
        self.refresh_graphs(sh)
        rw = self.win(op["report"])
        if rw is not None and rw.kind == "report": rw.setHtml(self.fit_html(sh, op.get("xname", xc), op["y"], lo_x, hi_x, r, True))
        self.statusBar().showMessage(f"Recalculated {r['model']} fit of {op['y']}", 4000)

    # ---- user scripts in menu and toolbar
    def fill_user_scripts(self):
        for a in self.user_actions: self.user_menu.removeAction(a)
        self.script_bar.clear(); self.user_actions = []
        for sc in self.settings.get("user_scripts", []):
            a = QAction(sc["name"], self); a.setToolTip(sc["path"])
            a.triggered.connect(lambda checked=False, p=sc["path"]: self.safe(lambda: self.run_script(p)))
            self.user_menu.addAction(a); self.user_actions.append(a)
            if sc.get("toolbar", True): self.script_bar.addAction(a)
        self.script_bar.setVisible(bool(self.settings.get("user_scripts")))

    def add_user_script(self, path=None, name=None, toolbar=True):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Python script", "", "Python (*.py)")
            if not path: return
            name, ok = QInputDialog.getText(self, "Menu name", "Name shown in the Tools menu and toolbar:", text=Path(path).stem)
            if not ok or not name.strip(): return
        self.settings.setdefault("user_scripts", []).append({"name": name.strip(), "path": str(path), "toolbar": toolbar})
        save_settings(self.settings); self.fill_user_scripts()

    def remove_user_script(self):
        names = [sc["name"] for sc in self.settings.get("user_scripts", [])]
        if not names: return QMessageBox.information(self, APP, "No scripts have been added.")
        n, ok = QInputDialog.getItem(self, "Remove script", "Script:", names, 0, False)
        if ok:
            self.settings["user_scripts"] = [sc for sc in self.settings["user_scripts"] if sc["name"] != n]
            save_settings(self.settings); self.fill_user_scripts()

    # ---- import / export
    def import_arrays(self, fn=None, names=None, as_matrix=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Import arrays", "", "HDF5 / NetCDF / MATLAB (*.h5 *.hdf5 *.he5 *.nc *.nc4 *.cdf *.mat);;All (*.*)")
            if not fn: return
        if names is None:
            d = DatasetDialog(self, fn)
            if not d.exec() or not d.names(): return
            names, as_matrix = d.names(), d.as_matrix.isChecked()
        stem = Path(fn).stem
        if as_matrix:
            mb = self.new_matrix(FM.dataset_to_matrix(fn, names[0]), f"{stem}_{names[0].split('/')[-1]}")
            for n in names[1:]: mb.add_sheet(n.split("/")[-1], FM.dataset_to_matrix(fn, n))
            self.new_matrix_graph(mb.sheets[0], "Image / Heat Map"); return mb
        return self.new_book(FM.datasets_to_frame(fn, names), stem)

    def import_jcamp(self, fn=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Import JCAMP-DX", "", "JCAMP-DX (*.jdx *.dx *.jcamp);;All (*.*)")
            if not fn: return
        df, hdr = FM.read_jcamp(fn)
        b = self.new_book(df, Path(fn).stem, {"X": {"Long Name": "X", "Units": hdr["X units"]}, "Y": {"Long Name": hdr["title"], "Units": hdr["Y units"]}})
        self.new_graph(b.current(), "Line", "X", ["Y"]); return b

    def import_sqlite(self, fn=None, table=None, sql=None):
        if not fn:
            fn, _ = QFileDialog.getOpenFileName(self, "Import from SQLite", "", "SQLite (*.db *.sqlite *.sqlite3);;All (*.*)")
            if not fn: return
        if table is None and sql is None:
            d = DatasetDialog(self, fn)
            if not d.exec(): return
            sql = d.sql.text().strip() or None; table = (d.names() or [None])[0]
            if not sql and not table: return
        df = FM.sqlite_query(fn, sql) if sql else FM.sqlite_table(fn, table)
        return self.new_book(df, f"{Path(fn).stem}_{table or 'query'}")

    def export_excel(self, fn=None):
        b = self.active("book")
        if b is None: return QMessageBox.warning(self, APP, "Open a workbook first.")
        if not fn:
            fn, _ = QFileDialog.getSaveFileName(self, "Export to Excel", f"{b.name}.xlsx", "Excel (*.xlsx)")
            if not fn: return
        with pd.ExcelWriter(fn, engine="openpyxl") as xw:
            for sh in b.sheets: sh.df.dropna(how="all").to_excel(xw, sheet_name=sh.name[:31], index=False)
            xw.book.properties.creator = "Kishan Tiwari"; xw.book.properties.lastModifiedBy = "Kishan Tiwari"
            for ws in xw.book.worksheets:  # text like "=HYPERLINK(...)" from imported data must stay text, not become a live formula
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.data_type == "f": cell.data_type = "s"
        self.statusBar().showMessage(f"Saved {fn}", 5000); return fn

    # ---- graph insets
    def add_inset(self, other=None, corner=None, size=None):
        g = self.need_graph()
        if not g: return
        if other is None:
            names = [w.name for w in self.windows() if w.kind == "graph" and w is not g]
            if not names: return QMessageBox.warning(self, APP, "Make another graph first; it will be drawn as the inset.")
            d = FormDialog(self, "Add inset graph", [("Graph to show as inset", combo(names)),
                                                    ("Corner", combo(["upper right", "upper left", "lower right", "lower left"])),
                                                    ("Size (fraction of the graph)", spin(0.1, 0.8, 0.35, True))])
            d.w["Size (fraction of the graph)"].setDecimals(2); d.w["Size (fraction of the graph)"].setSingleStep(0.05)

            def mutate(g_, d_):
                sz = d_.val("Size (fraction of the graph)"); c = d_.val("Corner")
                g_.spec.setdefault("insets", []).append({"graph": d_.val("Graph to show as inset"),
                                                         "pos": [0.9 - sz if "right" in c else 0.15, 0.88 - sz if "upper" in c else 0.15, sz, sz]})
            d.live_graph(g, mutate); d.exec(); return g
        sz = size or 0.35; x = 0.9 - sz if "right" in corner else 0.15; y = 0.88 - sz if "upper" in corner else 0.15
        g.spec.setdefault("insets", []).append({"graph": other, "pos": [x, y, sz, sz]}); g.draw(); return g

    # ---- more fitting
    def xyz_cols(self, b):
        sel = b.selected_cols()
        cols = sel if len(sel) == 3 else [next((c for c in b.df.columns if b.desig.get(c) == d), None) for d in ("X", "Y", "Z")]
        if None in cols or len(cols) != 3: raise RuntimeError("Select three columns (X, Y, Z) or set designations X, Y and Z.")
        return cols

    def surface_fit(self, name=None, expr=None, pnames=None):
        b = self.need_book()
        if not b: return
        cx, cy, cz = self.xyz_cols(b)
        if name is None:
            d = FormDialog(self, "Surface fit", [("Function", combo(list(B.SURFACE_MODELS) + ["User-defined"])),
                                                ("User z = (x, y)", QLineEdit("a + b*x + c*y**2")), ("User parameters", QLineEdit("a, b, c"))])
            if not d.exec(): return
            name = d.val("Function"); expr = d.val("User z = (x, y)"); pnames = [s.strip() for s in d.val("User parameters").split(",") if s.strip()]
        name = "User" if name == "User-defined" else name
        x, y, z = b.arr(cx), b.arr(cy), b.arr(cz); r = B.fit_surface(x, y, z, name, expr, pnames)
        self.report(f"Surface fit: {name}", table_html(f"Surface fit {name}: {cz} = f({cx}, {cy})", A.param_table(r),
                    ("Parameter", "Value", "Std. Error", "t", "p", "95% lower", "95% upper", ""))
                    + dict_html("Goodness of fit", {k: r[k] for k in ("N", "DOF", "R2", "Adj_R2", "RMSE")}))
        b.add_column(f"SurfFit_{cz}", r["func"](x, y)); b.add_column(f"SurfResid_{cz}", z - r["func"](x, y))
        m = np.isfinite(x) & np.isfinite(y); ext = [np.nanmin(x[m]), np.nanmax(x[m]), np.nanmin(y[m]), np.nanmax(y[m])]
        gx, gy = np.meshgrid(np.linspace(ext[0], ext[1], 60), np.linspace(ext[2], ext[3], 60))
        mb = self.new_matrix(r["func"](gx, gy), f"SurfaceFit_{cz}", ext); mb.current().zlabel = f"{cz} (fit)"
        self.new_matrix_graph(mb.current(), "Filled Contour"); return r

    def odr_fit(self, model=None, sx=None, sy=None):
        b, xn, yn, x, y = self.first_xy()
        if model is None:
            cols = ["(none)"] + [str(c) for c in b.df.columns]
            d = FormDialog(self, "Orthogonal distance regression", [("Function", combo(list(A.MODELS))), ("X error column", combo(cols)),
                                                                     ("Y error column", combo(cols))])
            if not d.exec(): return
            model = d.val("Function"); sx = None if d.val("X error column") == "(none)" else d.val("X error column")
            sy = None if d.val("Y error column") == "(none)" else d.val("Y error column")
        xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        r = B.fit_odr(xf, b.arr(yn), model, b.arr(sx) if sx else None, b.arr(sy) if sy else None)
        self.fit_report(b, xn, yn, x, y, r, {}); return r

    def global_fit(self, model=None, shared=None):
        b = self.need_book()
        if not b: return
        x, ys = b.xy_for_plot()
        if len(ys) < 2: raise RuntimeError("Select two or more Y columns to fit together.")
        if model is None:
            name, ok = QInputDialog.getItem(self, "Global fit", "Function:", list(A.MODELS), 0, False)
            if not ok: return
            lst = QListWidget(); lst.addItems(A.model_params(name)); lst.setSelectionMode(QAbstractItemView.MultiSelection)
            d = FormDialog(self, "Global fit: shared parameters", [("Parameters shared by all columns", lst)])
            if not d.exec(): return
            model, shared = name, [i.text() for i in lst.selectedItems()]
        xf = b.arr(x) if x else np.arange(1.0, len(b.df) + 1)
        r = B.fit_global([(xf, b.arr(c)) for c in ys], model, shared)
        rows = [[p, str(ys[int(scope.split()[-1]) - 1]) if scope != "all" else "all (shared)", v, e] for p, scope, v, e in r["rows"]]
        self.report(f"Global fit: {model}", table_html(f"Global {model} fit, shared: {', '.join(shared) or 'none'}", rows,
                    ["Parameter", "Column", "Value", "Std. Error"]) + dict_html("Goodness of fit", {k: r[k] for k in ("N", "DOF", "R2", "RMSE")}))
        g = self.new_graph(b, "Scatter", x, ys); t = np.linspace(np.nanmin(xf), np.nanmax(xf), 300)
        for c, fn in zip(ys, r["funcs"]): g.fits.append({"x": list(map(float, t)), "y": list(map(float, fn(t))), "label": f"global fit {c}", "style": "-"})
        g.draw(); return r

    def peak_analyzer(self):
        b, xn, yn, x, y = self.first_xy()
        xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        others = {c: (xf, b.arr(c)) for c in b.df.columns if c not in (b.x_col(), yn) and pd.to_numeric(b.df[c], errors="coerce").notna().sum() > 1}
        d = PeakAnalyzer(self, x, y, f"Peak Analyzer: {yn}", others)
        if not d.exec(): return
        goal = d.goal.currentIndex(); base = d.baseline(); bf = np.interp(xf, d.x, base)
        if goal == 0:
            if d.result is None and d.list_centers(): d.fit()
            if d.result is not None: self.peak_report(b, xn, yn, d.x, base, d.result)
            return
        if goal == 1:
            res = d.integ or d.integrate()
            if not res: return QMessageBox.warning(self, APP, "No peaks to integrate: find or click peaks first.")
            cols = ["Peak", "Centre", "Height", "FWHM", "Area", "Area %", "From", "To"]
            self.report("Integrated peaks", table_html(f"Integrated peaks of {yn} (area above the baseline, trapezoid rule)", [[p[c] for c in cols] for p in res], cols))
            ps = b.book.add_sheet(f"Integrated {yn}", pd.DataFrame(res)[cols]); ps.desig = {"Peak": "X", **{c: "Y" for c in cols[1:]}}; ps.model.refresh()
            b.book.tabs.setCurrentWidget(b); b.add_column(f"{yn}_Baseline", bf)
            g = self.graph_for(b, yn, "Line"); g.add_curve(d.x, base, "baseline", "k--"); return res
        if goal == 2:
            d.find() if not d.list_centers() else None
            dd = d.y - base; rows = [{"Peak": k + 1, "X": c, "Height above baseline": float(np.interp(c, d.x, dd))} for k, c in enumerate(sorted(d.list_centers()))]
            ps = b.book.add_sheet(f"Peaks found {yn}", pd.DataFrame(rows)); ps.desig = {"Peak": "Label", "X": "X", "Height above baseline": "Y"}; ps.model.refresh()
            b.book.tabs.setCurrentWidget(b); return rows
        if goal == 3:
            b.add_column(f"{yn}_Baseline", bf); self.graph_for(b, yn, "Line").add_curve(d.x, base, "baseline", "k--"); return bf
        b.add_column(f"{yn}_Baseline", bf)
        name = b.add_column(f"{yn}_Subtracted", b.arr(yn) - bf, snap=False); self.new_graph(b, "Line", b.x_col(), [name]); return name

    def peak_report(self, b, xn, yn, xs, base, r):
        self.report("Peak analysis", table_html(f"Peak analysis of {yn} ({r['model']}, R2 = {r['R2']:.6f})",
                    [[p["Peak"], p["Center"], p["Height"], p["FWHM"], p["Area"], p["Area %"]] for p in r["peaks"]],
                    ["Peak", "Centre", "Height", "FWHM", "Area", "Area %"]) + table_html("Fitted parameters", A.param_table(r),
                    ("Parameter", "Value", "Std. Error", "t", "p", "95% lower", "95% upper", "")))
        xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1); bf = np.interp(xf, xs, base)
        summary = pd.DataFrame([{"Peak": p["Peak"], "Shape": p.get("Shape", ""), "Centre": p["Center"], "Height": p["Height"], "FWHM": p["FWHM"],
                                 "Area": p["Area"], "Area %": p["Area %"]} for p in r["peaks"]])
        ps = b.book.add_sheet(f"Peaks {yn}", summary)  # one row per peak, ready to plot or copy
        ps.desig = {"Peak": "X", "Shape": "Label", **{c: "Y" for c in summary.columns[2:]}}
        ps.meta.update({"Centre": {"Units": b.meta.get(b.x_col(), {}).get("Units", "")}}); ps.model.refresh(); b.book.tabs.setCurrentWidget(b)
        b.add_column(f"Baseline_{yn}", bf); b.add_column(f"PeakFit_{yn}", bf + r["func"](xf))
        for k, comp in enumerate(r["components"], 1): b.add_column(f"Peak{k}_{yn}", bf + comp(xf))
        g = self.graph_for(b, yn); t = np.linspace(xs.min(), xs.max(), 600); bt = np.interp(t, xs, base)
        g.fits.append({"x": list(map(float, t)), "y": list(map(float, bt)), "label": "baseline", "style": "k--"})
        for k, comp in enumerate(r["components"], 1):
            g.fits.append({"x": list(map(float, t)), "y": list(map(float, bt + comp(t))), "label": f"peak {k}", "style": "-"})
        g.fits.append({"x": list(map(float, t)), "y": list(map(float, bt + r["func"](t))), "label": "cumulative fit", "style": "r-"}); g.draw()

    # ---- signal processing extras
    def filter_design(self, kind=None, btype=None, order=4, cut=None):
        b, xn, yn, x, y = self.first_xy(); fs = 1 / float(np.mean(np.diff(x)))
        if kind is None:
            d = FormDialog(self, f"Filter design (sampling rate {fs:.6g} from X)", [
                ("Filter", combo(["Butterworth", "Chebyshev I", "Bessel", "Elliptic", "FIR (window)"])),
                ("Type", combo(["lowpass", "highpass", "bandpass", "bandstop"])), ("Order (IIR)", spin(1, 20, 4)),
                ("Cut-off frequency (or low edge)", spin(0, 1e12, fs / 10, True)), ("High edge (band filters)", spin(0, 1e12, fs / 4, True))])
            if not d.exec(): return
            kind, btype, order = d.val("Filter"), d.val("Type"), d.val("Order (IIR)")
            cut = (d.val("Cut-off frequency (or low edge)"), d.val("High edge (band filters)"))
        des = B.design_filter(kind, btype, order, cut, fs); yf = B.apply_filter(y, des)
        full = np.full(len(b.df), np.nan); xr = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        m = np.isfinite(xr) & np.isfinite(b.arr(yn)); full[np.nonzero(m)[0]] = yf
        b.add_column(f"{btype}_{yn}", full); self.graph_for(b, yn, "Line").add_curve(x, yf, f"{kind} {btype}")
        w, H = B.freq_response(des, fs); sh = b.book.add_sheet(f"Response_{yn}", pd.DataFrame({"Frequency": w, "Gain dB": H}))
        self.new_graph(sh, "Line", "Frequency", ["Gain dB"]); return yf

    def stft(self, nperseg=None):
        b, xn, yn, x, y = self.first_xy()
        if nperseg is None:
            nperseg, ok = QInputDialog.getInt(self, "Short-time FFT", "Window length (points):", min(64, len(y)), 4, len(y))
            if not ok: return
        f, t, Z = B.stft(x, y, nperseg); mb = self.new_matrix(Z, f"STFT_{yn}", [t[0], t[-1], f[0], f[-1]]); mb.current().zlabel = "|STFT|"
        self.new_matrix_graph(mb.current(), "Image / Heat Map"); return mb

    def cwt(self):
        b, xn, yn, x, y = self.first_xy(); per, W = B.cwt_morlet(x, y)
        mb = self.new_matrix(W, f"CWT_{yn}", [x[0], x[-1], per[0], per[-1]]); mb.current().zlabel = "|W| (Morlet)"
        g = self.new_matrix_graph(mb.current(), "Image / Heat Map"); g.set_style({"ylabel": "Period", "xlabel": xn}); return mb

    def wavelet_denoise(self, wavelet=None):
        b, xn, yn, x, y = self.first_xy()
        if wavelet is None:
            wavelet, ok = QInputDialog.getItem(self, "Wavelet denoise", "Wavelet:", ["db4", "db8", "sym8", "coif3", "haar"], 0, False)
            if not ok: return
        yd = B.wavelet_denoise(y, wavelet); b.add_column(f"Denoised_{yn}", self._fill(b, yn, yd))
        self.graph_for(b, yn, "Line").add_curve(x, yd, f"denoised ({wavelet})"); return yd

    def _fill(self, b, yn, values):
        """Put values computed on the finite (x, y) rows back into a full-length column."""
        xr = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1); m = np.isfinite(xr) & np.isfinite(b.arr(yn))
        full = np.full(len(b.df), np.nan); full[np.nonzero(m)[0]] = values; return full

    def dwt(self, wavelet="db4", level=None):
        b, xn, yn, x, y = self.first_xy()
        co = B.dwt(y, wavelet, level); n = max(len(c) for c in co)
        cols = {("Approximation" if i == 0 else f"Detail {len(co) - i}"): np.r_[c, np.full(n - len(c), np.nan)] for i, c in enumerate(co)}
        return b.book.add_sheet(f"DWT_{yn}", pd.DataFrame(cols))

    def two_cols(self, b):
        cols = b.selected_cols() or [c for c in b.df.columns if b.desig.get(c) == "Y"]
        if len(cols) < 2: raise RuntimeError("Select two columns.")
        return cols[0], cols[1]

    def correlate(self, mode=None):
        b = self.need_book()
        if not b: return
        a, c = self.two_cols(b)
        if mode is None:
            mode, ok = QInputDialog.getItem(self, "Correlation", "Operation:", ["cross-correlation", "convolution", "auto-correlation"], 0, False)
            if not ok: return
        lags, out = B.correlate(b.arr(a), b.arr(a if mode == "auto-correlation" else c), "convolution" if mode == "convolution" else "corr")
        sh = b.book.add_sheet(f"{mode[:5]}_{a}", pd.DataFrame({"Lag": lags, mode: out})); self.new_graph(sh, "Line", "Lag", [mode]); return sh

    def envelope(self):
        b, xn, yn, x, y = self.first_xy(); e = B.envelope(y); b.add_column(f"Envelope_{yn}", self._fill(b, yn, e))
        self.graph_for(b, yn, "Line").add_curve(x, e, "envelope", "k-"); return e

    def coherence(self):
        b = self.need_book()
        if not b: return
        a, c = self.two_cols(b); xr = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        m = np.isfinite(xr) & np.isfinite(b.arr(a)) & np.isfinite(b.arr(c)); f, coh = B.coherence(xr[m], b.arr(a)[m], b.arr(c)[m])
        sh = b.book.add_sheet(f"Coherence_{a}_{c}", pd.DataFrame({"Frequency": f, "Coherence": coh})); self.new_graph(sh, "Line", "Frequency", ["Coherence"]); return sh

    # ---- statistics extras
    def pick_cols(self, b, title, fields):
        cols = [str(c) for c in b.df.columns]; widgets = []
        for label, kind in fields:
            if kind == "multi":
                w = QListWidget(); w.addItems(cols); w.setSelectionMode(QAbstractItemView.MultiSelection)
            else:
                w = combo((["(none)"] if kind == "optional" else []) + cols)
            widgets.append((label, w))
        d = FormDialog(self, title, widgets)
        if not d.exec(): return None
        out = []
        for (label, kind), (_, w) in zip(fields, widgets):
            if kind == "multi": out.append([i.text() for i in w.selectedItems()])
            else:
                v = w.currentText(); out.append(None if v == "(none)" else v)
        return out

    def rm2(self, cols=None):
        b = self.need_book()
        if not b: return
        cols = cols or self.pick_cols(b, "Two-way repeated-measures ANOVA (long format)", [("Response", "one"), ("Subject", "one"),
                                                                                             ("Factor A (within)", "one"), ("Factor B (within)", "one")])
        if not cols: return
        sub = b.df[cols].dropna(); rows = B.rm_anova_2way(pd.to_numeric(sub[cols[0]], errors="coerce"), sub[cols[1]], sub[cols[2]], sub[cols[3]])
        self.report("Two-way RM ANOVA", table_html(f"Two-way repeated-measures ANOVA of {cols[0]} (A = {cols[2]}, B = {cols[3]})", rows,
                                                    ["Source", "SS", "df", "MS", "F", "p"])); return rows

    def mixed(self, cols=None):
        b = self.need_book()
        if not b: return
        cols = cols or self.pick_cols(b, "Mixed-design ANOVA (long format)", [("Response", "one"), ("Subject", "one"),
                                                                             ("Between-subjects factor (group)", "one"), ("Within-subjects factor (condition)", "one")])
        if not cols: return
        sub = b.df[cols].dropna(); rows = C.mixed_anova(pd.to_numeric(sub[cols[0]], errors="coerce"), sub[cols[1]], sub[cols[2]], sub[cols[3]])
        rows[0][0] = f"Between subjects: {cols[2]}"; rows[2][0] = f"Within subjects: {cols[3]}"; rows[3][0] = f"{cols[2]} x {cols[3]}"
        cells = sub.groupby([cols[2], cols[3]])[cols[0]].agg(["count", "mean", "std"]).reset_index().values.tolist()
        self.report("Mixed ANOVA", table_html(f"Mixed-design ANOVA of {cols[0]}", rows, ["Source", "SS", "df", "MS", "F", "p"])
                    + table_html("Cell means", cells, [cols[2], cols[3], "N", "Mean", "SD"])); return rows

    def manova(self, cols=None):
        b = self.need_book()
        if not b: return
        cols = cols or self.pick_cols(b, "One-way MANOVA", [("Response columns (two or more)", "multi"), ("Group column", "one")])
        if not cols: return
        resp, gcol = [c for c in cols[0] if c != cols[1]], cols[1]
        if len(resp) < 1: raise RuntimeError("Choose at least one response column.")
        r = C.manova(np.column_stack([b.arr(c) for c in resp]), b.df[gcol].astype(str).to_numpy())
        means = [[g] + [float(np.nanmean(b.arr(c)[(b.df[gcol].astype(str) == g).to_numpy()])) for c in resp] for g in r["groups"]]
        self.report("MANOVA", table_html(f"One-way MANOVA: {', '.join(resp)} by {gcol} (N = {r['n']})", r["tests"],
                                         ["Test", "Value", "Approx. F", "df1", "df2", "p"])
                    + table_html("Group means", means, ["Group"] + resp)
                    + table_html("Univariate ANOVA for each response", [[c, *A.anova_oneway(*[b.arr(c)[(b.df[gcol].astype(str) == g).to_numpy()]
                                 for g in r["groups"]]).values()] for c in resp], ["Response", "F", "p", "df between", "df within"])); return r

    def discriminant(self, cols=None):
        b = self.need_book()
        if not b: return
        if cols is None:
            m, ok = QInputDialog.getItem(self, "Discriminant analysis", "Method:", ["Linear (LDA)", "Quadratic (QDA)"], 0, False)
            if not ok: return
            cols = self.pick_cols(b, "Discriminant analysis", [("Predictor columns", "multi"), ("Group column", "one")])
            if not cols: return
            if m.startswith("Quadratic"): return self.qda(cols)
        pred, gcol = [c for c in cols[0] if c != cols[1]], cols[1]
        if not pred: raise RuntimeError("Choose at least one predictor column.")
        r = C.lda(np.column_stack([b.arr(c) for c in pred]), b.df[gcol].astype(str).to_numpy(), pred); L = r["groups"]
        nf = r["canon"].shape[1]; lds = [f"LD{i + 1}" for i in range(nf)]
        self.report("Discriminant analysis", table_html(f"Linear discriminant analysis of {gcol} from {', '.join(pred)}",
                    [[f"{k}", e, q] for k, e, q in zip(lds, r["eigen"], r["eigen_pct"])], ["Function", "Eigenvalue", "% of variance"])
                    + table_html("Canonical discriminant function coefficients (unstandardised, unit within-group variance)", r["canonical"], ["Variable"] + lds)
                    + table_html("Classification function coefficients", r["classification"], ["Variable"] + L)
                    + table_html("Confusion matrix (rows: true group, columns: predicted)", r["confusion"], ["True / predicted"] + L)
                    + dict_html("Accuracy", {"Resubstitution": r["accuracy"], "Leave-one-out cross-validation": r["loo_accuracy"]}))
        idx = np.nonzero(r["mask"])[0]; predcol = np.full(len(b.df), None, dtype=object); predcol[idx] = r["pred"]
        b.add_column(f"LDA_pred_{gcol}", predcol, desig="Label")
        for j, g in enumerate(L):
            col = np.full(len(b.df), np.nan); col[idx] = r["post"][:, j]; b.add_column(f"P({g})", col)
        data = {"LD1": r["canon"][:, 0]}; true = b.df[gcol].astype(str).to_numpy()[idx]
        for g in L: data[g if g != "LD1" else "LD1 (group)"] = np.where(true == g, r["canon"][:, 1 if nf > 1 else 0], np.nan)
        sh = b.book.add_sheet("LDA_scores", pd.DataFrame(data)); g = self.new_graph(sh, "Scatter", "LD1", [c for c in data if c != "LD1"])
        g.spec["style"] = {"xlabel": "LD1", "ylabel": "LD2" if nf > 1 else "LD1", "title": f"Discriminant scores (LOO accuracy {r['loo_accuracy']:.1%})"}
        g.draw(); return r

    def km(self, cols=None):
        b = self.need_book()
        if not b: return
        cols = cols or self.pick_cols(b, "Kaplan-Meier", [("Time", "one"), ("Event (1 = event, 0 = censored)", "one"), ("Group (optional)", "optional")])
        if not cols: return
        tcol, ecol, gcol = cols; t, e = b.arr(tcol), b.arr(ecol)
        groups = [("all", np.ones(len(t), bool))] if not gcol else [(str(gv), (b.df[gcol].astype(str) == str(gv)).to_numpy()) for gv in sorted(b.df[gcol].dropna().astype(str).unique())]
        html, data = "", {}
        for name, m in groups:
            rows, med = B.kaplan_meier(t[m], e[m])
            html += table_html(f"Kaplan-Meier: {name} (median survival {med:.6g})", rows, ["Time", "At risk", "Events", "S(t)", "SE", "95% lower", "95% upper"])
            data[f"Time_{name}"] = [0.0] + [r[0] for r in rows]; data[f"S_{name}"] = [1.0] + [r[3] for r in rows]
        if gcol:
            ok = np.isfinite(t) & np.isfinite(e); lr = B.logrank(t[ok], e[ok], b.df[gcol].astype(str).to_numpy()[ok]); html += dict_html("Log-rank test", lr)
        self.report("Kaplan-Meier", html)
        n = max(len(v) for v in data.values()); df = pd.DataFrame({k: v + [np.nan] * (n - len(v)) for k, v in data.items()})
        sh = b.book.add_sheet("Survival", df); first = True
        for name, _ in groups:
            if first:
                g = self.new_graph(sh, "Step (post, survival)", f"Time_{name}", [f"S_{name}"]); first = False
            else:
                tt, ss = sh.arr(f"Time_{name}"), sh.arr(f"S_{name}"); k = np.isfinite(tt)
                xs = np.repeat(tt[k], 2)[1:]; ys = np.repeat(ss[k], 2)[:-1]
                g.fits.append({"x": list(map(float, xs)), "y": list(map(float, ys)), "label": f"S_{name}", "style": "-"})
        g.spec["style"] = {"ylabel": "Survival probability", "xlabel": tcol, "ymin": "0", "ymax": "1.05"}; g.draw(); return g

    def cox(self, cols=None):
        b = self.need_book()
        if not b: return
        cols = cols or self.pick_cols(b, "Cox proportional hazards", [("Time", "one"), ("Event (1 = event, 0 = censored)", "one"), ("Covariates", "multi")])
        if not cols or not cols[2]: return
        rows = B.cox_ph(b.arr(cols[0]), b.arr(cols[1]), np.column_stack([b.arr(c) for c in cols[2]]), cols[2])
        self.report("Cox PH", table_html("Cox proportional hazards", rows, ["Covariate", "Coefficient", "SE", "z", "p", "Hazard ratio", "HR 95% lower", "HR 95% upper"]))
        return rows

    def roc(self, cols=None):
        b = self.need_book()
        if not b: return
        cols = cols or self.pick_cols(b, "ROC curve", [("Score (test value)", "one"), ("True class (1 = positive, 0 = negative)", "one")])
        if not cols: return
        r = B.roc(b.arr(cols[0]), b.arr(cols[1]))
        self.report("ROC", dict_html(f"ROC analysis: {cols[0]} predicting {cols[1]}", {k: v for k, v in r.items() if not isinstance(v, np.ndarray)}))
        sh = b.book.add_sheet(f"ROC_{cols[0]}", pd.DataFrame({"FPR (1 - specificity)": r["fpr"], "TPR (sensitivity)": r["tpr"], "Threshold": r["thresholds"]}))
        sh.desig["Threshold"] = "Ignore"; g = self.new_graph(sh, "Line", "FPR (1 - specificity)", ["TPR (sensitivity)"])
        g.fits.append({"x": [0, 1], "y": [0, 1], "label": "chance", "style": "k:"}); g.spec["style"] = {"title": f"AUC = {r['AUC']:.4f}"}; g.draw(); return r

    def kmeans(self, k=None):
        b, cols, d = self.sel_arrays(2)
        if k is None:
            k, ok = QInputDialog.getInt(self, "K-means", "Number of clusters:", 3, 2, 50)
            if not ok: return
        X = np.column_stack(list(d.values())); ok = np.all(np.isfinite(X), axis=1); lab, cen, wss = B.kmeans(X[ok], k)
        full = np.full(len(b.df), np.nan); full[np.nonzero(ok)[0]] = lab + 1; b.add_column(f"Cluster_k{k}", full, desig="Label")
        self.report("K-means", table_html(f"K-means: {k} clusters (within-cluster SS {wss:.6g}, standardised)",
                    [[j + 1, int(np.sum(lab == j))] + list(c) for j, c in enumerate(cen)], ["Cluster", "N"] + [str(c) for c in cols])); return lab

    def hcluster(self, method=None, k=None):
        b, cols, d = self.sel_arrays(2)
        if method is None:
            dlg = FormDialog(self, "Hierarchical clustering", [("Linkage", combo(["ward", "average", "complete", "single"])), ("Clusters to cut", spin(2, 50, 3))])
            if not dlg.exec(): return
            method, k = dlg.val("Linkage"), dlg.val("Clusters to cut")
        X = np.column_stack(list(d.values())); ok = np.all(np.isfinite(X), axis=1); L, lab = B.hierarchical(X[ok], method, k)
        full = np.full(len(b.df), np.nan); full[np.nonzero(ok)[0]] = lab; b.add_column(f"HCluster_{method}{k}", full, desig="Label")
        g = self.new_graph(b, "Dendrogram (cluster rows)", b.x_col(), list(cols), {"method": method}); return g

    def power(self, test=None, solve=None, **kw):
        if test is None:
            d = FormDialog(self, "Power and sample size", [("Test", combo(["Two-sample t-test", "One-sample / paired t-test", "One-way ANOVA"])),
                ("Solve for", combo(["Sample size", "Power"])), ("Effect size (Cohen d, or f for ANOVA)", spin(0.01, 10, 0.5, True)),
                ("Sample size per group (when solving for power)", spin(2, 1e7, 20)), ("Target power (when solving for n)", spin(0.05, 0.999, 0.8, True)),
                ("Groups (ANOVA)", spin(2, 100, 3)), ("Significance level", spin(0.0001, 0.5, 0.05, True))])
            if not d.exec(): return
            test, solve = d.val("Test"), d.val("Solve for")
            kw = dict(es=d.val("Effect size (Cohen d, or f for ANOVA)"), n=d.val("Sample size per group (when solving for power)"),
                      power=d.val("Target power (when solving for n)"), k=d.val("Groups (ANOVA)"), alpha=d.val("Significance level"))
        if test == "One-way ANOVA":
            r = B.power_anova(f=kw["es"], k=kw["k"], n=kw["n"] if solve == "Power" else None, alpha=kw["alpha"], power=None if solve == "Power" else kw["power"])
        else:
            r = B.power_ttest(d=kw["es"], n=kw["n"] if solve == "Power" else None, alpha=kw["alpha"], power=None if solve == "Power" else kw["power"],
                              kind="two-sample" if test.startswith("Two") else "one-sample")
        self.report("Power", dict_html(f"{test}: solve for {solve.lower()}", r)); return r

    # ---- matrix extras
    def mat_filter(self, op):
        ms = self.need_matrix()
        if not ms: return
        val = None
        if op.startswith("Threshold"):
            val, ok = QInputDialog.getDouble(self, "Threshold", "Threshold value:", float(np.nanmean(ms.M)), -1e300, 1e300, 6)
            if not ok: return
        out = ms.book.add_sheet(f"{ms.name}_{op.split()[0].lower()}", MX.image_filter(ms.M, op, val), ms.extent)
        self.new_matrix_graph(out, "Image / Heat Map"); return out

    def mat_arith(self, op=None, other=None):
        ms = self.need_matrix()
        if not ms: return
        if op is None:
            objs = [f"{w.name}/{s.name}" for w in self.windows() if w.kind == "matrix" for s in w.sheets]
            d = FormDialog(self, f"Matrix arithmetic: {ms.book.name}/{ms.name} op B", [("Operation", combo(["+", "-", "*", "/", "^", "max", "min"])),
                                                                                       ("B: matrix", combo(["(use the number below)"] + objs)), ("B: number", spin(-1e300, 1e300, 1, True))])
            if not d.exec(): return
            op = d.val("Operation"); bm = d.val("B: matrix")
            other = d.val("B: number") if bm.startswith("(") else self.matrix_ref(*bm.split("/", 1)).M
        out = ms.book.add_sheet(f"{ms.name}_{'arith'}", MX.arithmetic(ms.M, op, other), ms.extent)
        self.new_matrix_graph(out, "Image / Heat Map"); return out

    # ================= worksheet tools
    def _sheet(self):
        sh = self.need_book()
        if sh is None: raise RuntimeError("Open a workbook first.")
        return sh

    def _new_sheet(self, sh, name, df):
        return sh.book.add_sheet(name, df.reset_index(drop=True) if isinstance(df, pd.DataFrame) else pd.DataFrame(df))

    def ws_transpose(self):
        sh = self._sheet(); df = sh.df.dropna(how="all"); t = df.T.reset_index(); t.columns = ["Column"] + [f"R{i + 1}" for i in range(len(df))]
        return self._new_sheet(sh, f"{sh.name}_T", t)

    def ws_stack(self, cols=None, ids=None):
        sh = self._sheet()
        if cols is None:
            got = self.pick_cols(sh, "Stack columns", [("Columns to stack", "multi"), ("Identifier columns to repeat", "multi")])
            if not got: return
            cols, ids = got
        return self._new_sheet(sh, f"{sh.name}_stacked", D.stack_columns(sh.df, cols, ids or []))

    def ws_unstack(self, cols=None):
        sh = self._sheet(); cols = cols or self.pick_cols(sh, "Unstack", [("Values column", "one"), ("Group column", "one")])
        if cols: return self._new_sheet(sh, f"{sh.name}_unstacked", D.unstack_column(sh.df, *cols))

    def ws_pivot(self, cols=None, agg=None):
        sh = self._sheet()
        if cols is None:
            cols = self.pick_cols(sh, "Pivot table", [("Rows", "one"), ("Columns", "one"), ("Values", "one")])
            if not cols: return
            agg, ok = QInputDialog.getItem(self, "Pivot table", "Combine values with:", ["mean", "sum", "count", "median", "min", "max", "std"], 0, False)
            if not ok: return
        return self._new_sheet(sh, f"{sh.name}_pivot", D.pivot(sh.df, *cols, agg or "mean"))

    def ws_dedupe(self):
        sh = self._sheet(); before = len(sh.df.dropna(how="all")); out = sh.df.dropna(how="all").drop_duplicates()
        self.statusBar().showMessage(f"Removed {before - len(out)} duplicate rows", 6000); return self._new_sheet(sh, f"{sh.name}_unique", out)

    def ws_extract(self, cond=None):
        """Rows where a condition (same rules as formulas, e.g. 'SiO2 > 45 and Class == "iron"') is true."""
        sh = self._sheet()
        if cond is None:
            cond, ok = QInputDialog.getText(self, "Extract rows", "Keep rows where (column names, numbers, text in quotes, and/or/not):")
            if not ok or not cond.strip(): return
        cols = {str(c): (sh.arr(c) if pd.api.types.is_numeric_dtype(sh.df[c]) else sh.df[c].astype(str).to_numpy()) for c in sh.df.columns}
        keep = A.eval_condition(cond, cols, len(sh.df))
        return self._new_sheet(sh, f"{sh.name}_subset", sh.df[keep])

    def ws_split(self, by=None):
        sh = self._sheet(); by = by or (self.pick_cols(sh, "Split sheet", [("Split by values of", "one")]) or [None])[0]
        if not by: return
        out = []
        for val, part in sh.df.dropna(subset=[by]).groupby(sh.df[by].astype(str)): out.append(self._new_sheet(sh, f"{by}={val}"[:30], part))
        return out

    def ws_join(self, other=None, keys=None, how="inner"):
        sh = self._sheet()
        if other is None:
            sheets = [f"{w.name}/{s.name}" for w in self.windows() if w.kind == "book" for s in w.sheets if s is not sh]
            d = FormDialog(self, "Join sheets", [("Other sheet", combo(sheets)), ("Key column here", combo([str(c) for c in sh.df.columns])),
                                                 ("Key column in other sheet", QLineEdit()), ("Join type", combo(["inner", "left", "outer"]))])
            if not d.exec(): return
            other = self.sheet_ref(*d.val("Other sheet").split("/", 1)); keys = (d.val("Key column here"), d.val("Key column in other sheet")); how = d.val("Join type")
        return self._new_sheet(sh, f"{sh.name}_joined", D.join_frames(sh.df.dropna(how="all"), other.df.dropna(how="all"), keys[0], keys[1], how))

    def ws_replace(self, find=None, repl=None):
        sh = self._sheet()
        if find is None:
            d = FormDialog(self, "Find and replace", [("Find", QLineEdit()), ("Replace with", QLineEdit()), ("Whole cell only", QCheckBox())])
            if not d.exec(): return
            find, repl, whole = d.val("Find"), d.val("Replace with"), d.val("Whole cell only")
        else: whole = False
        cols = sh.selected_cols() or list(sh.df.columns); sh.snap(); n = 0
        for c in cols:
            if c in sh.formulas: continue
            old = sh.df[c].astype(object)
            new = old.map(lambda v: (repl if str(v) == find else v) if whole else (str(v).replace(find, repl) if isinstance(v, str) and find in v else
                          (repl if fmt(v) == find else v)))
            n += int((old.astype(str) != new.astype(str)).sum())
            conv = pd.to_numeric(new, errors="coerce"); sh.df[c] = conv if conv.notna().sum() == new.notna().sum() else new
        sh.model.refresh(); sh.changed(); self.statusBar().showMessage(f"{n} cells changed", 6000); return n

    def ws_sort(self, cols=None, asc=True):
        sh = self._sheet()
        if cols is None:
            got = self.pick_cols(sh, "Sort by several columns", [("Sort keys, in order (select in order)", "multi")])
            if not got or not got[0]: return
            cols = got[0]; asc = QMessageBox.question(self, APP, "Ascending order?") == QMessageBox.Yes
        sh.snap(); sh.df = sh.df.sort_values(list(cols), ascending=asc, na_position="last", ignore_index=True); sh.mask = set()
        sh.model.refresh(); sh.changed()

    def ws_reduce(self, n=None, how="mean"):
        sh = self._sheet()
        if n is None:
            d = FormDialog(self, "Reduce rows", [("Combine every N rows", spin(2, 1000000, 10)), ("Using", combo(["mean", "median", "sum", "min", "max", "first"]))])
            if not d.exec(): return
            n, how = d.val("Combine every N rows"), d.val("Using")
        return self._new_sheet(sh, f"{sh.name}_reduced{n}", D.reduce_rows(sh.df.dropna(how="all"), n, how))

    def ws_fill(self, method=None):
        sh = self._sheet(); cols = [c for c in (sh.selected_cols() or list(sh.df.columns)) if pd.api.types.is_numeric_dtype(sh.df[c])]
        if method is None:
            method, ok = QInputDialog.getItem(self, "Fill missing values", "Method:", ["linear", "forward", "backward", "mean"], 0, False)
            if not ok: return
        sh.snap(); x = sh.arr(sh.x_col(), raw=True) if sh.x_col() and method == "linear" else None
        if x is not None and np.isfinite(x).sum() < 2: x = None  # text X column (e.g. sample names): interpolate by row instead
        last = sh.df.dropna(how="all").index.max(); last = -1 if pd.isna(last) else int(last)
        for c in cols:
            if c == sh.x_col() or c in sh.formulas: continue
            col = sh.df[c].to_numpy(float).copy(); seg = slice(0, last + 1)
            col[seg] = D.fill_missing(col[seg], None if x is None else x[seg], method); sh.df[c] = col
        sh.model.refresh(); sh.changed()

    def ws_sequence(self, start=None, step=1.0, kind="arithmetic", repeat=1):
        sh = self._sheet(); col = (sh.selected_cols() or [None])[0]
        if start is None:
            d = FormDialog(self, "Fill with sequence", [("Start", spin(-1e15, 1e15, 1, True)), ("Step (or ratio)", spin(-1e15, 1e15, 1, True)),
                                                       ("Kind", combo(["arithmetic", "geometric"])), ("Repeat each value", spin(1, 100000, 1)),
                                                       ("Rows", spin(1, 10000000, len(sh.df)))])
            if not d.exec(): return
            start, step, kind, repeat, n = d.val("Start"), d.val("Step (or ratio)"), d.val("Kind"), d.val("Repeat each value"), d.val("Rows")
        else: n = len(sh.df)
        vals = D.sequence(n, start, step, kind, repeat)
        if col is None or col in sh.formulas: return sh.add_column("Seq", vals)
        sh.snap()
        if n > len(sh.df): sh.add_rows(n - len(sh.df), snap=False)
        a = np.full(len(sh.df), np.nan); a[:n] = vals; sh.df[col] = a; sh.model.refresh(); sh.changed(); return col

    def ws_rowstats(self):
        sh = self._sheet(); cols = [c for c in (sh.selected_cols() or [c for c in sh.df.columns if sh.desig.get(c) == "Y"])]
        rs = D.row_stats(sh.df, cols)
        for c in rs.columns: sh.add_column(c, rs[c].to_numpy())
        return rs

    def ws_freq(self, bins=None):
        sh = self._sheet(); c = (sh.selected_cols() or [None])[0]
        if c is None: raise RuntimeError("Select a column.")
        if bins is None and pd.api.types.is_numeric_dtype(sh.df[c]):
            bins, ok = QInputDialog.getInt(self, "Frequency counts", "Number of bins (0 = count each distinct value):", 10, 0, 10000)
            if not ok: return
        fc = D.frequency_counts(sh.df[c], bins or None); return self._new_sheet(sh, f"Freq_{c}", fc)

    def ws_heat(self):
        sh = self._sheet(); cols = [c for c in (sh.selected_cols() or list(sh.df.columns)) if pd.api.types.is_numeric_dtype(sh.df[c])]
        on = not any(c in sh.heat for c in cols); sh.set_heat(cols, on); return on

    def ws_insert_rows(self, at=None, n=None):
        sh = self._sheet()
        if at is None:
            cur = sh.view.currentIndex(); at = max(cur.row() - SH.HEAD, 0) if cur.isValid() else 0
            n, ok = QInputDialog.getInt(self, "Insert rows", f"Rows to insert above row {at + 1}:", 1, 1, 1000000)
            if not ok: return
        sh.insert_rows(at, n)

    def ws_delete_rows(self):
        sh = self._sheet(); sh.delete_rows({r for _, r in sh.selected_cells()})

    # ================= curve tools
    def avg_curves(self):
        b = self._sheet(); x, ys = b.xy_for_plot()
        if len(ys) < 2: raise RuntimeError("Select two or more Y columns.")
        xf = b.arr(x) if x else np.arange(1.0, len(b.df) + 1)
        xs, mean, sd, k = D.average_curves([(xf, b.arr(c)) for c in ys])
        sh = self._new_sheet(b, "Average", pd.DataFrame({"X": xs, "Mean": mean, "SD": sd})); sh.desig["SD"] = "yErr"
        g = self.new_graph(sh, "Error Bar", "X", ["Mean", "SD"]); return sh

    def sub_line(self, x1=None, x2=None):
        b, xn, yn, x, y = self.first_xy()
        if x1 is None:
            d = FormDialog(self, "Subtract straight line", [("Line through X =", spin(-1e300, 1e300, float(x.min()), True)),
                                                           ("and X =", spin(-1e300, 1e300, float(x.max()), True))])
            if not d.exec(): return
            x1, x2 = d.val("Line through X ="), d.val("and X =")
        xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        return b.add_column(f"LineSub_{yn}", D.subtract_line(xf, b.arr(yn), x1, x2))

    def sub_ref(self, ref=None):
        b, xn, yn, x, y = self.first_xy()
        if ref is None:
            refs = [str(c) for c in b.df.columns if c not in (yn, b.x_col())]
            r, ok = QInputDialog.getItem(self, "Subtract reference", "Reference column (same X column):", refs, 0, False)
            if not ok: return
            ref = r
        xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1); m = np.isfinite(xf) & np.isfinite(b.arr(ref))
        return b.add_column(f"{yn}-{ref}", D.subtract_reference(xf, b.arr(yn), xf[m], b.arr(ref)[m]))

    def curve_intersect(self):
        b = self._sheet(); a, c = self.two_cols(b); xf = b.arr(b.x_col()) if b.x_col() else np.arange(1.0, len(b.df) + 1)
        ma, mc = np.isfinite(xf) & np.isfinite(b.arr(a)), np.isfinite(xf) & np.isfinite(b.arr(c))
        pts = D.intersections(xf[ma], b.arr(a)[ma], xf[mc], b.arr(c)[mc])
        self.report("Intersections", table_html(f"{len(pts)} intersection(s) of {a} and {c}", pts or [["none", ""]], ["X", "Y"])); return pts

    def find_x(self, y0=None):
        b, xn, yn, x, y = self.first_xy()
        if y0 is None:
            y0, ok = QInputDialog.getDouble(self, "Find X", f"Y value on {yn}:", float(np.median(y)), -1e300, 1e300, 8)
            if not ok: return
        xs = D.x_at_y(x, y, y0); self.report("Find X", table_html(f"X where {yn} = {y0:.6g}", [[v] for v in xs] or [["none"]], ["X"])); return xs

    def rise(self):
        b, xn, yn, x, y = self.first_xy(); o = np.argsort(x); r = D.rise_time(x[o], y[o]); self.report("Rise time", dict_html(f"Rise time of {yn}", r)); return r

    def poly_area(self):
        b, xn, yn, x, y = self.first_xy(); r = D.polygon_area(x, y); self.report("Polygon", dict_html(f"Polygon {xn}, {yn}", r)); return r

    # ================= graph annotations, clipboard, export
    def _annot(self, item):
        g = self.need_graph()
        if g: g.spec.setdefault("annotations", []).append(item); g.draw(); self.mark_dirty()
        return g

    @staticmethod
    def _axes_limits(g):
        ax = g.fig.axes[0] if g.fig.axes else None
        return (ax.get_xlim(), ax.get_ylim()) if ax is not None and ax.name == "rectilinear" else ((0.0, 1.0), (0.0, 1.0))

    def _axes_centre(self, g):
        (x0, x1), (y0, y1) = self._axes_limits(g); return (x0 + x1) / 2, (y0 + y1) / 2

    def add_refline(self, axis=None, value=None, label=""):
        if axis is None:
            g = self.need_graph()
            if not g: return
            cx, cy = self._axes_centre(g)
            d = FormDialog(self, "Reference line", [("Direction", combo(["horizontal (Y =)", "vertical (X =)"])), ("Value", spin(-1e300, 1e300, cy, True)),
                                                    ("Label (optional)", QLineEdit())])
            d.live_on(g, lambda d: {"kind": "hline" if d.val("Direction").startswith("h") else "vline",
                                    ("y" if d.val("Direction").startswith("h") else "x"): d.val("Value"), "label": d.val("Label (optional)")})
            if not d.exec(): return
            axis, value, label = ("y" if d.val("Direction").startswith("h") else "x"), d.val("Value"), d.val("Label (optional)")
        return self._annot({"kind": "hline" if axis == "y" else "vline", "y" if axis == "y" else "x": value, "label": label})

    def add_text(self, x=None, y=None, text=None):
        if text is None:
            g = self.need_graph()
            if not g: return
            cx, cy = self._axes_centre(g)
            d = FormDialog(self, "Add text", [("Text", QLineEdit("Text")), ("X (data units)", spin(-1e300, 1e300, cx, True)),
                                              ("Y (data units)", spin(-1e300, 1e300, cy, True))])
            d.live_on(g, lambda d: {"kind": "text", "x": d.val("X (data units)"), "y": d.val("Y (data units)"), "text": d.val("Text")})
            if not d.exec(): return
            text, x, y = d.val("Text"), d.val("X (data units)"), d.val("Y (data units)")
        return self._annot({"kind": "text", "x": x, "y": y, "text": text})

    def add_arrow(self, x1=None, y1=None, x2=None, y2=None, text=""):
        if x1 is None:
            g = self.need_graph()
            if not g: return
            (x0, x1_), (y0, y1_) = self._axes_limits(g)
            d = FormDialog(self, "Add arrow", [("From X", spin(-1e300, 1e300, x0 + 0.25 * (x1_ - x0), True)), ("From Y", spin(-1e300, 1e300, y0 + 0.75 * (y1_ - y0), True)),
                                               ("To X", spin(-1e300, 1e300, x0 + 0.5 * (x1_ - x0), True)), ("To Y", spin(-1e300, 1e300, y0 + 0.5 * (y1_ - y0), True)),
                                               ("Text at start", QLineEdit())])
            d.live_on(g, lambda d: {"kind": "arrow", **{k: d.val(lab) for k, lab in (("x1", "From X"), ("y1", "From Y"), ("x2", "To X"), ("y2", "To Y"))},
                                    "text": d.val("Text at start")})
            if not d.exec(): return
            x1, y1, x2, y2, text = (d.val(k) for k in ("From X", "From Y", "To X", "To Y", "Text at start"))
        return self._annot({"kind": "arrow", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "text": text})

    def add_ellipse(self, level=None):
        if level is None:
            level, ok = QInputDialog.getDouble(self, "Confidence ellipse", "Confidence level:", 0.95, 0.5, 0.999, 3)
            if not ok: return
        return self._annot({"kind": "ellipse", "level": level})

    def group_samples(self, column=None):
        """Colour and symbol per group (rock suite, setting ...) on geochemistry diagrams. column: 'auto', '' (none) or a column name."""
        from . import plots4
        g = self.need_graph()
        if not g: return
        if g.spec.get("type") not in plots4.GROUPABLE: raise RuntimeError("Groups work on the geochemistry diagrams (TAS, AFM, Pearce, Shand, Frost ...).")
        sh = self.sheet_ref(g.spec["book"], g.spec.get("sheet"))
        if column is None:
            text = [c for c in sh.df.columns if pd.to_numeric(sh.df[c].dropna(), errors="coerce").isna().all() and sh.df[c].notna().any()]
            auto = plots4.group_column(sh.df)
            items = [f"Automatic ({auto or 'no group column found'})", "None (one colour)"] + text
            cur = g.spec.get("extra", {}).get("group", "auto")
            i = 0 if cur == "auto" else 1 if cur == "" else (items.index(cur) if cur in items else 0)
            conv = lambda item: "auto" if item.startswith("Automatic") else "" if item.startswith("None") else item
            d = FormDialog(self, "Group samples", [("Colour and symbol by", combo(items, items[i]))])
            d.live_graph(g, lambda g_, d_: g_.spec.setdefault("extra", {}).__setitem__("group", conv(d_.val("Colour and symbol by"))))
            d.exec(); return g
        g.snapshot(); g.spec.setdefault("extra", {})["group"] = column; g.draw(); self.mark_dirty(); return g

    def add_series(self, book=None, sheet=None, x=None, y=None, style="-"):
        if book is None:
            refs = [f"{w.name}/{s.name}" for w in self.windows() if w.kind == "book" for s in w.sheets]
            d = FormDialog(self, "Add data to graph", [("Sheet", combo(refs)), ("X column (blank = row number)", QLineEdit()), ("Y column", QLineEdit()),
                                                       ("Style", combo(["-", "o", "-o", "--", "s", "^"]))])
            if not d.exec(): return
            book, sheet = d.val("Sheet").split("/", 1); x, y, style = d.val("X column (blank = row number)") or None, d.val("Y column"), d.val("Style")
        sh = self.sheet_ref(book, sheet)
        if y not in sh.df.columns or (x and x not in sh.df.columns): raise RuntimeError("Column not found in that sheet.")
        return self._annot({"kind": "series", "book": book, "sheet": sheet, "x": x, "y": y, "style": style})

    def copy_graph(self):
        s = self.mdi.activeSubWindow(); g = s.widget() if s else None
        if g is None or g.kind not in ("graph", "layout"): g = self.need_graph()
        if not g: return
        import io
        from PySide6.QtGui import QImage
        dpi = min(float(self.settings.get("export_opts", {}).get("dpi", 200)), 600)  # clipboard images above 600 dpi get unwieldy
        buf = io.BytesIO(); g.fig.savefig(buf, format="png", dpi=dpi); img = QImage.fromData(buf.getvalue(), "PNG")
        QApplication.clipboard().setImage(img); self.statusBar().showMessage("Graph copied: paste it into Word or PowerPoint", 6000); return img

    def export_all_graphs(self, folder=None, ext=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the exported graphs")
            if not folder: return
            ext, ok = QInputDialog.getItem(self, "Format", "Format:", ["png", "tif", "jpg", "svg", "pdf", "eps"], 0, False)
            if not ok: return
            opts = self.export_options(self.active("graph"), f"x.{ext}", many=True)
            if opts is None: return
        else: opts = {}
        out = []
        for w in self.windows():
            if w.kind in ("graph", "layout"):
                safe = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in w.name); fn = str(Path(folder) / f"{safe}.{ext}")
                w.export(fn, **opts); out.append(fn)
        self.statusBar().showMessage(f"Exported {len(out)} graphs to {folder}", 8000); return out

    def export_report(self, fn=None):
        s = self.mdi.activeSubWindow(); r = s.widget() if s else None
        if r is None or r.kind != "report": r = self.active("report")
        if r is None: return QMessageBox.warning(self, APP, "Open a report window first.")
        if not fn:
            fn, _ = QFileDialog.getSaveFileName(self, "Export report", f"{r.name}.html", "HTML (*.html);;PDF (*.pdf)")
            if not fn: return
        if fn.lower().endswith(".pdf"):
            from PySide6.QtGui import QPdfWriter, QPageSize
            wr = QPdfWriter(fn); wr.setPageSize(QPageSize(QPageSize.A4)); wr.setTitle(r.name); wr.setCreator("Kishan Tiwari")
            r.document().print_(wr)
        else:
            Path(fn).write_text(r.toHtml().replace("<head>", '<head><meta name="author" content="Kishan Tiwari">', 1), encoding="utf-8")
        return fn

    def digitize(self, path=None):
        d = Digitizer(self, path)
        if not d.exec(): return
        df = d.data()
        if not len(df): return
        sh = self.new_book(df, self.uniq("Digitized")).current(); g = self.new_graph(sh, "Scatter", "X", ["Y"])
        st = dict(g.spec["style"])
        if d.logx.isChecked(): st["xscale"] = "log"
        if d.logy.isChecked(): st["yscale"] = "log"
        g.spec["style"] = st; g.draw()
        sw = g.parentWidget(); sw.showNormal(); self.mdi.setActiveSubWindow(sw)
        self.statusBar().showMessage(f"{len(df)} digitized points: worksheet {sh.book.name} and graph {g.name}", 10000); return sh

    def mat_crop(self, r0=None, r1=None, c0=None, c1=None):
        ms = self.need_matrix()
        if not ms: return
        R, Cn = ms.M.shape
        if r0 is None:
            d = FormDialog(self, "Crop matrix", [("First row", spin(1, R, 1)), ("Last row", spin(1, R, R)), ("First column", spin(1, Cn, 1)), ("Last column", spin(1, Cn, Cn))])
            if not d.exec(): return
            r0, r1, c0, c1 = d.val("First row") - 1, d.val("Last row"), d.val("First column") - 1, d.val("Last column")
        xs, ys = MX.axes_of(ms.M, ms.extent); out = ms.book.add_sheet(f"{ms.name}_crop", ms.M[r0:r1, c0:c1], [xs[c0], xs[c1 - 1], ys[r0], ys[r1 - 1]])
        self.new_matrix_graph(out, "Image / Heat Map"); return out

    # ================= more statistics
    def qda(self, cols):
        b = self._sheet(); pred, gcol = [c for c in cols[0] if c != cols[1]], cols[1]
        r = D.qda(np.column_stack([b.arr(c) for c in pred]), b.df[gcol].astype(str).to_numpy(), pred); L = r["groups"]
        self.report("Quadratic discriminant analysis", table_html(f"Quadratic discriminant analysis of {gcol} from {', '.join(pred)}", r["means"], ["Group"] + pred)
                    + table_html("Log determinant of each group covariance", r["logdet"], ["Group", "log |S|"])
                    + dict_html("Box M test (equal covariances; small p favours QDA over LDA)", r["box_m"])
                    + table_html("Confusion matrix (rows: true group, columns: predicted)", r["confusion"], ["True / predicted"] + L)
                    + dict_html("Accuracy", {"Resubstitution": r["accuracy"], "Leave-one-out cross-validation": r["loo_accuracy"]}))
        idx = np.nonzero(r["mask"])[0]; pc = np.full(len(b.df), None, dtype=object); pc[idx] = r["pred"]; b.add_column(f"QDA_pred_{gcol}", pc, desig="Label")
        for j, g in enumerate(L):
            col = np.full(len(b.df), np.nan); col[idx] = r["post"][:, j]; b.add_column(f"QDA P({g})", col)
        return r

    def _cov_dialog(self, b, title, multi_resp):
        return self.pick_cols(b, title, [("Response column(s)" if multi_resp else "Response column", "multi" if multi_resp else "one"),
                                         ("Group column", "one"), ("Covariate column(s)", "multi")])

    def ancova(self, cols=None):
        b = self._sheet(); cols = cols or self._cov_dialog(b, "ANCOVA", False)
        if not cols or not cols[2]: return
        y, g, cv = cols; r = D.ancova(b.arr(y), b.df[g].astype(str).to_numpy(), np.column_stack([b.arr(c) for c in cv]), cv)
        self.report("ANCOVA", table_html(f"ANCOVA of {y}: factor {g}, covariates {', '.join(cv)} (error df {r['dfe']})", r["table"], ["Effect", "F", "df1", "df2", "p"])
                    + table_html("Adjusted means (at the covariate means)", r["adjusted_means"], ["Group", "N", y])
                    + table_html("Common slopes", r["slopes"], ["Covariate", y])); return r

    def mancova(self, cols=None):
        b = self._sheet(); cols = cols or self._cov_dialog(b, "MANCOVA", True)
        if not cols or not cols[2] or len(cols[0]) < 1: return
        ys, g, cv = cols; r = D.mancova(np.column_stack([b.arr(c) for c in ys]), b.df[g].astype(str).to_numpy(), np.column_stack([b.arr(c) for c in cv]), cv)
        html = "".join(table_html(f"MANCOVA effect: {k} (adjusted for the other terms)", v, ["Test", "Value", "Approx. F", "df1", "df2", "p"]) for k, v in r["tests"].items())
        self.report("MANCOVA", html + table_html("Adjusted means (at the covariate means)", r["adjusted_means"], ["Group", "N"] + list(ys))
                    + table_html("Common slopes", r["slopes"], ["Covariate"] + list(ys))); return r

    def dunn(self):
        b, cols, d = self.sel_arrays(2); d = {str(k): v for k, v in d.items()}
        self.report("Dunn", dict_html("Kruskal-Wallis", A.kruskal(d)) + table_html("Dunn post-hoc (Holm adjusted)", D.dunn(d),
                    ["Pair", "Mean rank difference", "z", "p", "p (Holm)", "Significant (0.05)"]))

    def fisher(self, table=None):
        if table is None:
            d = FormDialog(self, "2 x 2 table", [("Row 1, column 1", spin(0, 1e9, 0)), ("Row 1, column 2", spin(0, 1e9, 0)),
                                                 ("Row 2, column 1", spin(0, 1e9, 0)), ("Row 2, column 2", spin(0, 1e9, 0))])
            if not d.exec(): return
            table = [[d.val("Row 1, column 1"), d.val("Row 1, column 2")], [d.val("Row 2, column 1"), d.val("Row 2, column 2")]]
        r = {**D.fisher_exact(table), **{f"McNemar {k}": v for k, v in D.mcnemar(table).items()}}
        self.report("2 x 2 tests", table_html("Table", table, ["", ""]) + dict_html("Fisher exact and McNemar tests", r)); return r

    def proportion(self, x1=None, n1=None, x2=None, n2=None, p0=0.5):
        if x1 is None:
            d = FormDialog(self, "Proportion test", [("Successes, sample 1", spin(0, 1e9, 0)), ("Trials, sample 1", spin(1, 1e9, 10)),
                                                     ("Successes, sample 2 (0 trials = one-sample test)", spin(0, 1e9, 0)), ("Trials, sample 2", spin(0, 1e9, 0)),
                                                     ("Test proportion (one-sample)", spin(0.0001, 0.9999, 0.5, True))])
            if not d.exec(): return
            x1, n1, x2, n2, p0 = (d.val(k) for k in ("Successes, sample 1", "Trials, sample 1", "Successes, sample 2 (0 trials = one-sample test)", "Trials, sample 2", "Test proportion (one-sample)"))
        r = D.proportion_test(x1, n1, x2 if n2 else None, n2 or None, p0); self.report("Proportion test", dict_html("Proportion test", r)); return r

    def var2(self):
        b, cols, d = self.sel_arrays(2); r = D.var_test_two(d[cols[0]], d[cols[1]])
        self.report("F test", dict_html(f"Two-sample F test of variances: {cols[0]} vs {cols[1]}", r)); return r

    def var1(self, sigma2=None):
        b, cols, d = self.sel_arrays()
        if sigma2 is None:
            sigma2, ok = QInputDialog.getDouble(self, "Variance test", "Hypothesised variance:", 1.0, 1e-300, 1e300, 8)
            if not ok: return
        self.report("Variance test", "".join(dict_html(f"Chi-square test of variance: {c}", D.var_test_one(v, sigma2)) for c, v in d.items()))

    def pcorr(self):
        b, cols, d = self.sel_arrays(3); names = [str(c) for c in cols]; R, pv = D.partial_correlation(np.column_stack(list(d.values())), names)
        self.report("Partial correlation", table_html("Partial correlation (each pair controlling for all other selected columns)",
                    [[n] + list(r) for n, r in zip(names, R)], [""] + names) + table_html("p values", [[n] + list(r) for n, r in zip(names, pv)], [""] + names))
        return R

    def logit(self, cols=None):
        b = self._sheet(); cols = cols or self.pick_cols(b, "Logistic regression", [("Response (0 / 1)", "one"), ("Predictors", "multi")])
        if not cols or not cols[1]: return
        y, xs = cols; r = D.logistic_regression(b.arr(y), np.column_stack([b.arr(c) for c in xs]), xs)
        self.report("Logistic regression", table_html(f"Logistic regression of {y}", r["coef"], ["Term", "Coefficient", "SE", "z", "p", "Odds ratio", "OR 95% lower", "OR 95% upper"])
                    + dict_html("Model", r["stats"]))
        pc = np.full(len(b.df), np.nan); pc[np.nonzero(r["mask"])[0]] = r["prob"]; b.add_column(f"P({y}=1)", pc); return r

    def pls(self, cols=None, ncomp=None):
        b = self._sheet()
        if cols is None:
            cols = self.pick_cols(b, "PLS regression", [("Response column(s)", "multi"), ("Predictor columns", "multi")])
            if not cols or not cols[0] or not cols[1]: return
            ncomp, ok = QInputDialog.getInt(self, "PLS", "Number of components:", min(2, len(cols[1])), 1, len(cols[1]))
            if not ok: return
        ys, xs = cols; r = D.pls(np.column_stack([b.arr(c) for c in xs]), np.column_stack([b.arr(c) for c in ys]), ncomp)
        self.report("PLS regression", table_html(f"PLS regression ({ncomp} components): coefficients in original units", [[x] + list(row) for x, row in zip(xs, r["B"])] +
                    [["Intercept"] + list(r["intercept"])], ["Predictor"] + list(ys))
                    + table_html("Cumulative variance explained", [[k + 1, a, c] for k, (a, c) in enumerate(zip(r["x_var_cum"], r["y_var_cum"]))], ["Components", "X", "Y"])
                    + table_html("Variable importance in projection (VIP > 1 = important)", [[x, v] for x, v in zip(xs, r["vip"])], ["Predictor", "VIP"]))
        idx = np.nonzero(r["mask"])[0]
        for j, y in enumerate(ys): col = np.full(len(b.df), np.nan); col[idx] = r["fitted"][:, j]; b.add_column(f"PLS_fit_{y}", col)
        return r

    def cronbach(self):
        b, cols, d = self.sel_arrays(2); r = D.cronbach_alpha(np.column_stack(list(d.values())))
        self.report("Cronbach alpha", dict_html(f"Reliability of {', '.join(map(str, cols))}", r)); return r

    def bland(self):
        b, cols, d = self.sel_arrays(2); r = D.bland_altman(d[cols[0]], d[cols[1]])
        self.report("Bland-Altman", dict_html(f"Bland-Altman agreement: {cols[0]} vs {cols[1]}", r))
        self.new_graph(b, "Bland-Altman", cols[0], [cols[1]]); return r

    def glm(self, resp=None, preds=None, family=None, link=None, weights=None, offset=None):
        b = self._sheet()
        if resp is None:
            cols = [str(c) for c in b.df.columns]; lst = QListWidget(); lst.addItems(cols); lst.setSelectionMode(QAbstractItemView.MultiSelection)
            fam = combo(list(E.FAMILIES)); lk = combo(["(default)"] + list(E.LINKS))
            d = FormDialog(self, "Generalized linear model", [("Response", combo(cols)), ("Predictors (text columns become dummies)", lst),
                           ("Family", fam), ("Link", lk), ("Weights / binomial trials (optional)", combo(["(none)"] + cols)),
                           ("Offset, e.g. log of exposure (optional)", combo(["(none)"] + cols))])
            if not d.exec(): return
            resp, preds, family = d.val("Response"), [i.text() for i in lst.selectedItems()], d.val("Family")
            link = None if d.val("Link") == "(default)" else d.val("Link")
            weights = None if d.val("Weights / binomial trials (optional)") == "(none)" else d.val("Weights / binomial trials (optional)")
            offset = None if d.val("Offset, e.g. log of exposure (optional)") == "(none)" else d.val("Offset, e.g. log of exposure (optional)")
        preds = [c for c in preds if c != resp]; X, names = E.design(b.df, preds)
        r = E.glm(b.arr(resp), X, names, family, link, b.arr(weights) if weights else None, b.arr(offset) if offset else None)
        head = ["Term", "Estimate", "SE", r["stat_name"], "p", "95% lower", "95% upper"] + ([r["exp_label"], "lower", "upper"] if r["exp_label"] else [])
        self.report("GLM", table_html(f"Generalized linear model: {resp} ~ {' + '.join(preds) or '1'} ({r['family']}, {r['link']} link)", r["coef"], head)
                    + dict_html("Model fit", r["stats"]))
        b.add_column(f"GLM_fit_{resp}", r["fitted"]); b.add_column(f"GLM_PearsonResid_{resp}", r["pearson"]); return r

    def lmm(self, resp=None, fixed=None, group=None, slope=None, method="REML"):
        b = self._sheet()
        if resp is None:
            cols = [str(c) for c in b.df.columns]; lst = QListWidget(); lst.addItems(cols); lst.setSelectionMode(QAbstractItemView.MultiSelection)
            d = FormDialog(self, "Linear mixed-effects model", [("Response", combo(cols)), ("Fixed effects (text columns become dummies)", lst),
                           ("Grouping factor (random effects per group)", combo(cols)), ("Random slope for (optional)", combo(["(none)"] + cols)),
                           ("Estimation", combo(["REML", "ML (use to compare fixed effects)"]))])
            if not d.exec(): return
            resp, fixed, group = d.val("Response"), [i.text() for i in lst.selectedItems()], d.val("Grouping factor (random effects per group)")
            slope = None if d.val("Random slope for (optional)") == "(none)" else d.val("Random slope for (optional)"); method = d.val("Estimation")[:4].strip()
        fixed = [c for c in fixed if c not in (resp, group)]; X, names = E.design(b.df, fixed)
        Z, rn = (np.column_stack([np.ones(len(b.df)), b.arr(slope)]), ("Intercept", slope)) if slope else (None, ("Intercept",))
        r = E.lmm(b.arr(resp), X, names, b.df[group].astype(str).to_numpy(), Z, rn, method)
        html = table_html(f"Linear mixed model: {resp} ~ {' + '.join(fixed) or '1'} + (1{' + ' + slope if slope else ''} | {group}), {r['stats']['Method']}",
                          r["fixed"], ["Term", "Estimate", "SE", "t", "df (approx.)", "p", "95% lower", "95% upper"])
        html += table_html("Random effects (variance components)", r["variance"], ["Component", "Variance", "SD"]) + dict_html("Model", r["stats"])
        if slope:
            ri = E.lmm(b.arr(resp), X, names, b.df[group].astype(str).to_numpy(), None, ("Intercept",), method)
            html += dict_html(f"Is the random slope for {slope} needed? (likelihood-ratio test vs random intercept only)", E.lmm_lrt(r, ri))
        html += table_html(f"Predicted random effects (BLUPs) for each {group}", r["blup"], [group] + list(rn))
        self.report("Mixed model", html); b.add_column(f"LMM_fit_{resp}", r["fitted"]); return r

    def _re_terms(self, b, factors, nested=False, slope=None, correlated=True):
        """Random-effect terms for analysis7: intercepts per factor (crossed or nested); the slope goes with the first factor."""
        terms, prev, prev_name, one = [], None, None, np.ones(len(b.df))
        for i, f_ in enumerate(factors):
            lab = b.df[f_].astype(str).to_numpy()
            if nested and prev is not None: lab = F.nested_labels(prev, lab); name = f"{prev_name}:{f_}"
            else: name = f_
            eff = [("Intercept", one)] + ([(slope, b.arr(slope))] if slope and i == 0 else [])
            terms.append(G7.term(lab, name, eff, correlated)); prev, prev_name = lab, name
        return terms

    @staticmethod
    def _formula(o):
        parts = []
        for i, f_ in enumerate(o["factors"]):
            nm = ":".join(o["factors"][:i + 1]) if o["nested"] else f_
            if i == 0 and o.get("slope"): parts.append(f"(1 + {o['slope']} | {nm})" if o.get("correlated", True) else f"(1 | {nm}) + (0 + {o['slope']} | {nm})")
            else: parts.append(f"(1 | {nm})")
        return " + ".join(parts)

    def _mixed_dialog(self, b, title, glmm=False):
        cols = [str(c) for c in b.df.columns]
        fx = QListWidget(); fx.addItems(cols); fx.setSelectionMode(QAbstractItemView.MultiSelection)
        rf = QListWidget(); rf.addItems(cols); rf.setSelectionMode(QAbstractItemView.MultiSelection)
        fields = [("Response", combo(cols)), ("Fixed effects (text columns become dummies)", fx),
                  ("Random-intercept factors (select one or more, in order)", rf), ("Nested: each factor sits inside the one before", QCheckBox()),
                  ("Random slope for (optional; applies to the first factor)", combo(["(none)"] + cols)),
                  ("Slope correlated with the intercept", QCheckBox())]
        if glmm: fields += [("Family", combo(["Binomial", "Poisson"])), ("Link", combo(["(default)", "logit", "probit", "cloglog", "log"])),
                            ("Integration", combo(["Laplace approximation", "Adaptive Gauss-Hermite quadrature"])), ("Quadrature points", spin(1, 50, 11)),
                            ("Binomial trials (optional)", combo(["(none)"] + cols)), ("Offset, e.g. log of exposure (optional)", combo(["(none)"] + cols))]
        else: fields += [("Estimation", combo(["REML", "ML (use to compare fixed effects)"])),
                         ("Kenward-Roger small-sample tests (REML)", QCheckBox())]
        d = FormDialog(self, title, fields); d.w["Slope correlated with the intercept"].setChecked(True)
        if not d.exec(): return None
        none = lambda v: None if v in ("(none)", "(default)") else v
        out = {"resp": d.val("Response"), "fixed": [i.text() for i in fx.selectedItems()], "factors": [i.text() for i in rf.selectedItems()],
               "nested": d.val("Nested: each factor sits inside the one before"), "slope": none(d.val("Random slope for (optional; applies to the first factor)")),
               "correlated": d.val("Slope correlated with the intercept")}
        if glmm: out.update(family=d.val("Family"), link=none(d.val("Link")), nagq=d.val("Quadrature points") if d.val("Integration").startswith("Adaptive") else 1, weights=none(d.val("Binomial trials (optional)")),
                            offset=none(d.val("Offset, e.g. log of exposure (optional)")))
        else: out["method"] = d.val("Estimation")[:4].strip(); out["kr"] = d.val("Kenward-Roger small-sample tests (REML)")
        if not out["factors"]: raise RuntimeError("Choose at least one random-intercept factor.")
        return out

    def _mixed_report(self, title, b, o, r, head, extra_html=""):
        html = table_html(title, r["fixed"], head)
        html += table_html("Random effects (independent variance components)", r["variance"],
                           ["Term", "Variance or correlation", "SD"] + (["Share of total"] if len(r["variance"][0]) > 3 else [])) + dict_html("Model", r["stats"]) + extra_html
        for item in r["blups"]:
            name, rows = item[0], item[1]; effs = item[2] if len(item) > 2 else ["Effect"]
            html += table_html(f"Predicted random effects for {name}", rows[:200] + ([["...", f"{len(rows) - 200} more"]] if len(rows) > 200 else []), [name] + list(effs))
        self.report(title.split(":")[0], html)

    def lmm_crossed(self, o=None):
        b = self._sheet(); o = o or self._mixed_dialog(b, "Mixed model: crossed or nested random effects")
        if not o: return
        fixed = [c for c in o["fixed"] if c not in [o["resp"]] + o["factors"]]; X, names = E.design(b.df, fixed)
        terms = self._re_terms(b, o["factors"], o["nested"], o.get("slope"), o.get("correlated", True))
        r = G7.lmm_general(b.arr(o["resp"]), X, names, terms, o.get("method", "REML")); form = self._formula(o)
        head = ["Term", "Estimate", "SE", "t", "df (approx.)", "p", "95% lower", "95% upper"]; extra = ""
        if o.get("kr"):
            if r["stats"]["Method"] != "REML": raise RuntimeError("Kenward-Roger needs REML estimation.")
            tab, ftab = H8.kr_tables(r, b.arr(o["resp"]), X, names, terms); r["fixed"] = tab
            head = ["Term", "Estimate", "SE (Kenward-Roger)", "t", "df (Kenward-Roger)", "p", "95% lower", "95% upper"]
            if ftab: extra = table_html("F tests for each predictor, Kenward-Roger (text predictors tested as a whole)", ftab, ["Predictor", "F", "num df", "den df", "p", "scale"])
        self._mixed_report(f"Linear mixed model: {o['resp']} ~ {' + '.join(fixed) or '1'} + {form}, {r['stats']['Method']}", b, o, r, head, extra)
        b.add_column(f"LMM_fit_{o['resp']}", r["fitted"]); return r

    def glmm(self, o=None):
        b = self._sheet(); o = o or self._mixed_dialog(b, "Generalized linear mixed model", glmm=True)
        if not o: return
        fixed = [c for c in o["fixed"] if c not in [o["resp"]] + o["factors"]]; X, names = E.design(b.df, fixed)
        wts = b.arr(o["weights"]) if o.get("weights") else None; off = b.arr(o["offset"]) if o.get("offset") else None
        if int(o.get("nagq", 1)) > 1:
            if len(o["factors"]) != 1:
                raise RuntimeError("Quadrature needs one grouping factor: with crossed or nested factors the likelihood does not split into "
                                   "separate group integrals, so it cannot be computed by quadrature. Use the Laplace approximation.")
            if o.get("link") not in (None, G7.CANONICAL[o["family"]]):
                raise RuntimeError(f"Adaptive quadrature uses the {G7.CANONICAL[o['family']]} link for the {o['family']} family.")
            labs = b.df[o["factors"][0]].astype(str).to_numpy()
            if o.get("slope"):
                eff = [("Intercept", np.ones(len(b.df))), (o["slope"], b.arr(o["slope"]))]
                r = H8.glmm_agq_multi(b.arr(o["resp"]), X, names, labs, o["factors"][0], eff, o["family"], int(o["nagq"]), wts, off)
                if not o.get("correlated", True): r["stats"]["Note"] = "Quadrature estimates the full covariance (the intercept-slope correlation is included)."
            else:
                r = G7.glmm_agq(b.arr(o["resp"]), X, names, labs, o["factors"][0], o["family"], int(o["nagq"]), wts, off)
        else:
            r = G7.glmm_general(b.arr(o["resp"]), X, names, self._re_terms(b, o["factors"], o["nested"], o.get("slope"), o.get("correlated", True)),
                                o["family"], o.get("link"), wts, off)
        form = self._formula(o)
        head = ["Term", "Estimate", "SE", "z", "p", "95% lower", "95% upper"] + ([r["exp_label"], "lower", "upper"] if r["exp_label"] else [])
        self._mixed_report(f"Generalized linear mixed model: {o['resp']} ~ {' + '.join(fixed) or '1'} + {form} ({r['family']}, {r['link']} link)", b, o, r, head)
        b.add_column(f"GLMM_fit_{o['resp']}", r["fitted"]); return r

    def pca(self):
        b, cols, d = self.sel_arrays(2); ev, pct, load, scores = A.pca(np.column_stack(list(d.values())))
        pcs = [f"PC{i + 1}" for i in range(len(ev))]
        self.report("PCA", table_html("Eigenvalues", [[p, e, q, c] for p, e, q, c in zip(pcs, ev, pct, np.cumsum(pct))],
                                      ["PC", "Eigenvalue", "% Variance", "Cumulative %"])
                    + table_html("Loadings", [[c] + list(r) for c, r in zip(cols, load)], ["Variable"] + pcs))
        b.book.add_sheet("PCA_Scores", pd.DataFrame(scores, columns=pcs))
        for kind in ("PCA Scree Plot", "PCA Biplot (scores + loadings)"):  # the graphs that make sense of many variables at once
            try: self.new_graph(b, kind, None, list(cols))
            except Exception as e: self.statusBar().showMessage(f"{kind}: {e}", 8000)


def export_selftest(folder):
    """Build check: export one graph in every supported format from the packaged program, plus the lazily loaded
    libraries, and write a report. Used by build.ps1 (PlotBench.exe --selftest <folder>)."""
    out, ok = Path(folder), True; out.mkdir(parents=True, exist_ok=True); lines = []
    from matplotlib.figure import Figure
    fig = Figure(figsize=(4, 3)); ax = fig.add_subplot(111); ax.plot([0, 1, 2], [0, 1, 4], "o-"); ax.set_title("PlotBench self-test")
    for ext in ("png", "svg", "pdf", "eps", "tif", "jpg"):
        try:
            fig.savefig(out / f"selftest.{ext}", dpi=150); size = (out / f"selftest.{ext}").stat().st_size
            lines.append(f"{ext}: ok {size} bytes"); ok &= size > 500
        except Exception as e: lines.append(f"{ext}: FAILED {type(e).__name__}: {e}"); ok = False
    for mod in ("pywt", "h5py", "scipy.odr", "scipy.io", "openpyxl", "xlrd", "PIL.TiffImagePlugin", "sqlite3"):
        try: __import__(mod); lines.append(f"import {mod}: ok")
        except Exception as e: lines.append(f"import {mod}: FAILED {e}"); ok = False
    try:  # the real window, an example graph, the manual and its PDF (catches files missing from the bundle)
        import os
        os.environ["APPDATA"] = str(out / "appdata")
        qa = QApplication.instance() or QApplication([])
        w = Main(); g = w.open_example("trace"); g.export(str(out / "example.png"))
        from .helpwin import save_manual_pdf, ManualWindow
        ManualWindow(w); save_manual_pdf(out / "manual.pdf"); lines.append(f"window, example, manual: ok {(out / 'manual.pdf').stat().st_size} bytes")
        ok &= (out / "manual.pdf").stat().st_size > 50000
        w.dirty = False; w.close()
    except Exception as e: lines.append(f"window, example, manual: FAILED {type(e).__name__}: {e}"); ok = False
    try:  # the newest plot types draw in the packaged program, and the bundled manual is this version's (not a stale one)
        from . import plots5, gallery
        from .helpwin import MANUAL
        for k in plots5.GEOCHRON + plots5.GEOCHRON_PCA + list(plots5.PEARCE08) + ["Raincloud (violin + box + points)"]:
            x, ys, names, extra = gallery._sample(k); P.PLOT_TYPES[k][0](Figure(), x if x is not None else np.arange(len(ys[0])), ys, names, "", extra)
        if f"PlotBench {VERSION}" not in MANUAL.read_text(encoding="utf-8"): raise RuntimeError(f"the manual is not the {VERSION} manual")
        lines.append(f"geochronology plots, manual {VERSION}: ok")
    except Exception as e: lines.append(f"new plots / manual version: FAILED {type(e).__name__}: {e}"); ok = False
    (out / "selftest.txt").write_text("\n".join(lines + ["RESULT: " + ("PASS" if ok else "FAIL")]), encoding="utf-8")
    return ok


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest": sys.exit(0 if export_selftest(sys.argv[2]) else 1)
    app = QApplication(sys.argv); app.setApplicationName(APP); app.setStyle("Fusion"); app.setWindowIcon(app_icon())
    from PySide6.QtWidgets import QSplashScreen
    from PySide6.QtGui import QPixmap, QPainter, QColor
    banner = QPixmap(asset("banner.png")); splash = None
    if not banner.isNull():
        pm = QPixmap(banner.width() + 40, banner.height() + 70); pm.fill(QColor("white")); p = QPainter(pm); p.drawPixmap(20, 20, banner)
        p.setPen(QColor("gray")); p.drawText(24, banner.height() + 50, f"Version {VERSION}  ·  Kishan Tiwari"); p.end()
        splash = QSplashScreen(pm.scaledToWidth(640)); splash.show(); app.processEvents()
    w = Main(); w.show()
    if splash: splash.finish(w)
    if w.settings.get("console_at_start"): w.console_dock.show()
    if w.settings.get("show_start", True) and not (len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pbp")): w.show_start()
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pbp"):
        w.safe(lambda: w.open_project(sys.argv[1]))  # opened via file association
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
