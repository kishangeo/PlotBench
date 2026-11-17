"""PlotBench dialogs for fitting and batch processing.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton, QCheckBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QAbstractItemView, QFileDialog, QHeaderView)

from . import analysis as A

USER = "User-defined..."


def _f(text, default=None):
    try: return float(text)
    except (TypeError, ValueError): return default


class FitDialog(QDialog):
    """Nonlinear fit set-up: function, parameters (initial, fixed, bounds), weighting, range, outputs."""

    def __init__(self, parent, x, y, columns, last=None, weights=None):
        super().__init__(parent); self.setWindowTitle("Nonlinear Curve Fit"); self.resize(1120, 660)
        self.x, self.y = np.asarray(x, float), np.asarray(y, float); last = last or {}; self.fitted = None
        self.weights = weights or {}  # {column: errors}, same rows as x and y, for a weighted preview
        self.func = QComboBox(); self.func.addItems(list(A.MODELS) + [USER])
        self.expr = QLineEdit(last.get("expr", "a*exp(-x/t) + c")); self.pnames = QLineEdit(last.get("pnames", "a, t, c"))
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Parameter", "Initial value", "Fixed", "Lower bound", "Upper bound"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        guess = QPushButton("Re-guess initial values"); guess.clicked.connect(self.fill)
        self.weight = QComboBox(); self.weight.addItems(["No weighting"] + [f"Errors from column {c}" for c in columns])
        self.xfrom, self.xto = QLineEdit(), QLineEdit()
        self.conf, self.pred, self.resid = QCheckBox("95% confidence band"), QCheckBox("95% prediction band"), QCheckBox("Residual plot")
        self.auto = QCheckBox("Recalculate automatically when the data change"); self.auto.setChecked(last.get("auto", False))
        self.conf.setChecked(last.get("conf", True)); self.pred.setChecked(last.get("pred", False)); self.resid.setChecked(last.get("resid", False))
        self.box = QCheckBox("Paste parameter table on the graph"); self.box.setChecked(last.get("param_box", True))
        self.fitlive = QCheckBox("Fit while I edit"); self.fitlive.setChecked(last.get("fit_live", True))
        self.fitlive.setToolTip("Re-run the fit a moment after every change. Untick to see only the initial-guess curve.")
        use = QPushButton("Use fitted values as initial"); use.clicked.connect(self.use_fitted)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure
        self.fig = Figure(figsize=(6, 5), layout="constrained"); self.canvas = FigureCanvasQTAgg(self.fig)
        self.stats = QLabel(); self.stats.setWordWrap(True)
        f = QFormLayout(); f.addRow("Function", self.func); f.addRow("User function y =", self.expr); f.addRow("User parameters (comma)", self.pnames)
        f.addRow("Weighting", self.weight)
        rng = QHBoxLayout(); rng.addWidget(self.xfrom); rng.addWidget(QLabel("to")); rng.addWidget(self.xto); f.addRow("Fit X range (blank = all)", rng)
        from .live import LivePreview
        left = QVBoxLayout(); left.addLayout(f); left.addWidget(self.table)
        g2 = QHBoxLayout(); g2.addWidget(guess); g2.addWidget(use); left.addLayout(g2)
        outs = QHBoxLayout(); [outs.addWidget(w) for w in (self.conf, self.pred, self.resid)]; left.addLayout(outs)
        left.addWidget(self.box); left.addWidget(self.auto)
        right = QVBoxLayout(); right.addWidget(self.fitlive); right.addWidget(self.canvas, 1); right.addWidget(self.stats)
        top = QHBoxLayout(); top.addLayout(left, 5); top.addLayout(right, 6)
        self.live = LivePreview(self, self.preview); self.live.timer.setInterval(220)  # fits take longer than a redraw
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.live.bar())
        self.func.currentTextChanged.connect(self.fill); self.pnames.editingFinished.connect(self.fill)
        if last.get("model"): self.func.setCurrentText(last["model"])
        self.fill(); self.live.start(); self.live.run()

    def model(self): return "User" if self.func.currentText() == USER else self.func.currentText()

    def _curve(self, cfg, xs):
        """The model evaluated with the table's initial values."""
        names = self.names(); p = cfg["p0"]
        if cfg["model"] == "User": return A.eval_formula(cfg["expr"], dict(zip(names, p), x=xs), len(xs))
        return A.MODELS[cfg["model"]][0](xs, *p)

    def preview(self):
        """Data, initial-guess curve, live fit and residuals; problems are shown in the dialog."""
        cfg = self.value(); x, y = self.x, self.y; ok = np.isfinite(x) & np.isfinite(y); m = ok.copy()
        if cfg["xfrom"] is not None: m &= x >= cfg["xfrom"]
        if cfg["xto"] is not None: m &= x <= cfg["xto"]
        self.fig.clear(); gs = self.fig.add_gridspec(2, 1, height_ratios=[3, 1])
        ax = self.fig.add_subplot(gs[0]); rx = self.fig.add_subplot(gs[1], sharex=ax)
        if (ok & ~m).any(): ax.plot(x[ok & ~m], y[ok & ~m], "o", ms=4, color="0.75", mfc="none", label="outside range")
        ax.plot(x[m], y[m], "o", ms=4, mfc="none", color="C0", label="data")
        if m.sum() < 2: self.canvas.draw_idle(); raise ValueError("Not enough points in the fit range.")
        xs = np.linspace(np.nanmin(x[m]), np.nanmax(x[m]), 400); msg = []
        try: ax.plot(xs, self._curve(cfg, xs), "--", color="tab:orange", lw=1.2, label="initial guess")
        except Exception as e: msg.append(f"Initial guess cannot be drawn: {e}")
        self.fitted = None
        if self.fitlive.isChecked():
            try:
                we = self.weights.get(cfg["weight_col"]) if cfg["weight_col"] else None
                we = np.asarray(we, float) if we is not None and len(we) == len(x) else None
                r = run_fit(cfg, x, y, we); self.fitted = r
                ax.plot(xs, r["func"](xs), "r-", lw=1.6, label="fit")
                res = y[m] - r["func"](x[m]); rx.axhline(0, color="0.5", lw=0.8); rx.plot(x[m], res, "o", ms=3, color="C3")
                pars = ", ".join(f"{k} = {v:.5g} ± {r['errors'][k]:.2g}" for k, v in r["params"].items())
                msg.insert(0, f"<b>R² = {r['R2']:.6f}</b> &nbsp; reduced χ² = {r['Reduced_ChiSq']:.4g}<br>{pars}")
                if cfg["weight_col"] and we is None: msg.append("Preview is unweighted; OK fits with the chosen weights.")
            except Exception as e: msg.append(f"<span style='color:firebrick'>Fit did not converge: {e}</span>")
        ax.legend(fontsize=8); rx.set_ylabel("residual", fontsize=8); ax.tick_params(labelsize=8); rx.tick_params(labelsize=8)
        self.stats.setText("<br>".join(msg)); self.canvas.draw_idle()

    def use_fitted(self):
        """Copy the fitted values into the Initial value column (handy before fixing a parameter)."""
        if self.fitted is None: self.live.run()
        if self.fitted is None: return
        for i, n in enumerate(self.names()):
            if n in self.fitted["params"]: self.table.item(i, 1).setText(f"{self.fitted['params'][n]:.8g}")

    def names(self):
        return A.model_params("User", [s.strip() for s in self.pnames.text().split(",") if s.strip()]) if self.model() == "User" \
            else A.model_params(self.model())

    def fill(self, *_):
        user = self.model() == "User"; self.expr.setEnabled(user); self.pnames.setEnabled(user)
        names = self.names()
        try: p0 = [1.0] * len(names) if user else A.initial_guess(self.model(), self.x, self.y)
        except Exception: p0 = [1.0] * len(names)
        self.table.setRowCount(len(names))
        for i, (n, v) in enumerate(zip(names, p0)):
            it = QTableWidgetItem(n); it.setFlags(Qt.ItemIsEnabled); self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(f"{v:.6g}"))
            chk = QTableWidgetItem(); chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable); chk.setCheckState(Qt.Unchecked)
            self.table.setItem(i, 2, chk); self.table.setItem(i, 3, QTableWidgetItem("")); self.table.setItem(i, 4, QTableWidgetItem(""))

    def value(self):
        names = self.names(); p0, fixed, bounds = [], {}, {}
        for i, n in enumerate(names):
            v = _f(self.table.item(i, 1).text(), 1.0); p0.append(v)
            if self.table.item(i, 2).checkState() == Qt.Checked: fixed[n] = v
            lo, hi = _f(self.table.item(i, 3).text(), -np.inf), _f(self.table.item(i, 4).text(), np.inf)
            if np.isfinite(lo) or np.isfinite(hi): bounds[n] = (lo, hi)
        w = self.weight.currentText()
        return {"model": self.model(), "p0": p0, "fixed": fixed, "bounds": bounds, "expr": self.expr.text(),
                "pnames": self.pnames.text(), "user_params": names if self.model() == "User" else None,
                "weight_col": w[len("Errors from column "):] if w.startswith("Errors") else None,
                "xfrom": _f(self.xfrom.text()), "xto": _f(self.xto.text()),
                "conf": self.conf.isChecked(), "pred": self.pred.isChecked(), "resid": self.resid.isChecked(), "auto": self.auto.isChecked(),
                "param_box": self.box.isChecked(), "fit_live": self.fitlive.isChecked()}


def run_fit(cfg, x, y, yerr=None, use_p0=True):
    """Run a fit from a FitDialog config (also used by batch and gadgets)."""
    m = np.isfinite(x) & np.isfinite(y)
    if cfg.get("xfrom") is not None: m &= x >= cfg["xfrom"]
    if cfg.get("xto") is not None: m &= x <= cfg["xto"]
    return A.fit_model(x[m], y[m], cfg["model"], p0=cfg["p0"] if use_p0 else None, user_expr=cfg.get("expr"),
                       user_params=cfg.get("user_params"), fixed=cfg.get("fixed"), bounds=cfg.get("bounds"),
                       yerr=None if yerr is None else yerr[m])


class BatchFilesDialog(QDialog):
    """Pick files, the X/Y columns (by name) and the operation to run on each."""
    OPS = ["Linear fit", "Nonlinear fit (set up next)", "Descriptive statistics of Y", "Area under curve", "Peaks (count and largest)"]

    def __init__(self, parent, columns):
        super().__init__(parent); self.setWindowTitle("Batch process files"); self.resize(560, 520)
        self.files = QListWidget(); self.files.setSelectionMode(QAbstractItemView.ExtendedSelection)
        add = QPushButton("Add files..."); add.clicked.connect(self.add_files)
        rem = QPushButton("Remove selected"); rem.clicked.connect(lambda: [self.files.takeItem(self.files.row(i)) for i in self.files.selectedItems()])
        self.xcol, self.ycol = QComboBox(), QComboBox()
        for c in (self.xcol, self.ycol): c.setEditable(True); c.addItems([str(v) for v in columns])
        if len(columns) > 1: self.ycol.setCurrentIndex(1)
        self.op = QComboBox(); self.op.addItems(self.OPS)
        self.keep = QCheckBox("Also import each file as a sheet"); self.keep.setChecked(True)
        lay = QVBoxLayout(self); lay.addWidget(QLabel("Files (all are read with the Import Wizard settings you just chose):"))
        lay.addWidget(self.files); row = QHBoxLayout(); row.addWidget(add); row.addWidget(rem); lay.addLayout(row)
        f = QFormLayout(); f.addRow("X column", self.xcol); f.addRow("Y column", self.ycol); f.addRow("Operation", self.op); f.addRow(self.keep)
        lay.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def add_files(self):
        fns, _ = QFileDialog.getOpenFileNames(self, "Files to process", "", "Text data (*.csv *.txt *.dat *.tsv *.prn *.asc);;All (*.*)")
        have = {self.files.item(i).text() for i in range(self.files.count())}
        self.files.addItems([f for f in fns if f not in have])

    def paths(self): return [self.files.item(i).text() for i in range(self.files.count())]
