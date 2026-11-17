"""Live preview for dialogs: every edit shows on the graph (or a preview pane) a moment after you make it, before anything
is kept. Apply keeps the changes as one undo step and leaves the dialog open; OK keeps them and closes; Cancel puts
everything back exactly as it was when the dialog opened (or at the last Apply).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import copy

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QAbstractSpinBox, QLineEdit, QAbstractButton, QSlider, QTableWidget,
                               QListWidget, QPlainTextEdit, QHBoxLayout, QLabel, QWidget, QDialogButtonBox, QSizePolicy)

DELAY_MS = 80  # pause after the last keystroke/click before redrawing: fast enough to feel instant, slow enough not to stutter


def watch(root, slot, skip=()):
    """Call slot() whenever any input widget inside root changes."""
    for w in root.findChildren(QWidget):
        if w in skip: continue
        if isinstance(w, QLineEdit): w.textChanged.connect(slot)
        elif isinstance(w, QComboBox): w.currentIndexChanged.connect(slot); w.editTextChanged.connect(slot)
        elif isinstance(w, QAbstractSpinBox) and hasattr(w, "valueChanged"): w.valueChanged.connect(slot)
        elif isinstance(w, QAbstractButton) and w.isCheckable(): w.toggled.connect(slot)
        elif isinstance(w, QSlider): w.valueChanged.connect(slot)
        elif isinstance(w, QTableWidget): w.itemChanged.connect(slot)
        elif isinstance(w, QListWidget): w.itemSelectionChanged.connect(slot)
        elif isinstance(w, QPlainTextEdit): w.textChanged.connect(slot)


class LivePreview:
    """Attach to a dialog. preview() shows the dialog's current values; commit() makes the shown state permanent;
    revert() restores the last committed state. bar() returns the row with the 'Live preview' switch and the buttons."""

    def __init__(self, dlg, preview, commit=None, revert=None, buttons=None, on=True):
        self.dlg, self._preview, self._commit, self._revert = dlg, preview, commit, revert
        self.dirty = False; self.shown = False; self.panes = []  # small copies of the graph inside the dialog
        self.timer = QTimer(dlg); self.timer.setSingleShot(True); self.timer.setInterval(DELAY_MS); self.timer.timeout.connect(self.run)
        self.box = QCheckBox("Live preview"); self.box.setChecked(on); self.box.setToolTip("Show each change straight away. OK keeps it, Cancel undoes it.")
        self.box.toggled.connect(lambda v: self.run() if v else self.restore())
        self.status = QLabel(); self.status.setStyleSheet("color: gray")
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # long messages are cut, never the buttons
        self.bb = buttons or QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | (QDialogButtonBox.Apply if commit else QDialogButtonBox.NoButton))
        self.bb.accepted.connect(dlg.accept); self.bb.rejected.connect(dlg.reject)
        ap = self.bb.button(QDialogButtonBox.Apply)
        if ap is not None: ap.clicked.connect(self.apply); ap.setToolTip("Keep these changes and leave the dialog open")
        dlg.accepted.connect(self._on_ok); dlg.rejected.connect(self.restore)

    def bar(self):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.box); h.addWidget(self.status, 1); h.addWidget(self.bb); return w

    def start(self):
        """Begin watching the dialog's inputs (call after the dialog is built)."""
        watch(self.dlg, self.changed, skip=(self.box,))

    def changed(self, *_):
        self.dirty = True
        if self.box.isChecked(): self.timer.start()

    def run(self):
        self.timer.stop()
        try:
            self._preview(); self.shown = True
            for p in self.panes: p()
            self.status.setText("Previewing"); self.status.setToolTip("OK keeps the changes, Cancel undoes them")
        except Exception as e:  # half-typed values: say so, keep the last good picture
            self.status.setText(f"<span style='color:firebrick'>{str(e)[:90]}</span>"); self.status.setToolTip(str(e))

    def apply(self):
        self.run()
        if self._commit: self._commit()
        self.dirty = self.shown = False; self.status.setText("Applied")

    def restore(self):
        self.timer.stop()
        if self.shown and self._revert: self._revert()
        for p in self.panes: p()
        self.shown = False; self.status.setText("")

    def _on_ok(self):
        self.timer.stop()
        if self._commit and (self.dirty or self.shown): self.run(); self._commit()
        elif self.shown and self._revert and not self._commit: self._revert()  # caller does the real change after OK
        self.shown = False


class GraphSession:
    """Snapshot of a graph for preview/commit/revert: one undo step per Apply or OK."""

    def __init__(self, g): self.g = g; self.base = copy.deepcopy((g.spec, g.fits))

    def show(self, mutate):
        self.g.spec, self.g.fits = copy.deepcopy(self.base); mutate(self.g); self.g.draw()

    def commit(self):
        g = self.g; g.history.append(self.base); del g.history[:-30]; g.redo_stack = []
        self.base = copy.deepcopy((g.spec, g.fits))
        if hasattr(g.main, "mark_dirty"): g.main.mark_dirty()

    def revert(self): self.g.spec, self.g.fits = copy.deepcopy(self.base); self.g.draw()


def add_pane(lp, g, minimum=(400, 320)):
    """A copy of graph g drawn inside the dialog and redrawn with every preview, so each change is visible even when the dialog
    covers the graph window. Returns the widget to put in the dialog's layout."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    fig = Figure(figsize=(5, 3.9), layout="constrained"); cv = FigureCanvasQTAgg(fig); cv.setMinimumSize(*minimum)
    cv.setToolTip("Preview: how the graph looks with the values in this dialog")

    def refresh():
        try: g.render(fig)
        except Exception as e:
            fig.clear(); fig.text(0.5, 0.5, str(e)[:200], ha="center", va="center", color="firebrick", wrap=True)
        cv.draw_idle()
    lp.panes.append(refresh); refresh(); return cv


def graph_live(dlg, g, mutate, commit=True):
    """Live preview of a dialog on graph g. mutate(g) applies the dialog's values to g.spec / g.fits."""
    s = GraphSession(g)
    return LivePreview(dlg, lambda: s.show(mutate), s.commit if commit else None, s.revert)
