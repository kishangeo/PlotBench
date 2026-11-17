"""PlotBench dialogs: Peak Analyzer, dataset picker for HDF5/NetCDF/MATLAB/SQLite, worksheet sparklines.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QPen, QColor, QPolygonF
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox, QLineEdit, QPushButton,
                               QCheckBox, QLabel, QDialogButtonBox, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QRadioButton,
                               QPlainTextEdit, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox)

from . import analysis as A
from . import analysis2 as B
from . import formats as FM


class PeakAnalyzer(QDialog):
    """Baseline -> find peaks -> edit the peak list -> fit, with a live preview."""

    GOALS = ["Fit peaks (deconvolution)", "Integrate peaks", "Find peaks", "Create baseline", "Subtract baseline"]

    def __init__(self, parent, x, y, title="Peak Analyzer", columns=None):
        super().__init__(parent); self.setWindowTitle(title); self.resize(1080, 760)
        o = np.argsort(x); self.x, self.y = np.asarray(x, float)[o], np.asarray(y, float)[o]; self.result = None; self.base = None
        self.integ = []; self.found = []
        self.columns = {}  # other columns of the sheet, put on this X (for 'use an existing column as the baseline')
        for name, (cx, cy) in (columns or {}).items():
            cx, cy = np.asarray(cx, float), np.asarray(cy, float); m = np.isfinite(cx) & np.isfinite(cy)
            if m.sum() > 1: oo = np.argsort(cx[m]); self.columns[str(name)] = np.interp(self.x, cx[m][oo], cy[m][oo])
        self.fig = Figure(figsize=(7, 5), layout="constrained"); self.canvas = FigureCanvasQTAgg(self.fig)
        self.bmode = QComboBox(); self.bmode.addItems(["None", "Constant (minimum)", "Straight line between end points", "ALS (asymmetric least squares)",
                                                        "Anchor points: smooth curve (Shift+click)", "Anchor points: straight segments (Shift+click)",
                                                        "Shirley (XPS, iterative)", "Constant: maximum", "Constant: mean", "Constant: median",
                                                        "Constant: custom value", "End points weighted (straight line)",
                                                        "Anchor points: B-spline (smoothing)", "Automatic anchor points (lowest point in N segments)",
                                                        "Use an existing column"])
        self.bmode.setToolTip("Anchor points: Shift+click the spectrum where there is no peak; Shift+right-click removes the nearest anchor")
        self.anchors = []  # x positions of baseline anchor points
        self.goal = QComboBox(); self.goal.addItems(self.GOALS); self.goal.setToolTip("What OK produces, as in Origin's Peak Analyzer")
        self.const = QDoubleSpinBox(); self.const.setRange(-1e15, 1e15); self.const.setDecimals(6); self.const.setValue(float(np.nanmin(self.y)))
        self.nanch = QSpinBox(); self.nanch.setRange(2, 200); self.nanch.setValue(8); self.nanch.setToolTip("Number of automatic anchor points")
        self.basecol = QComboBox(); self.basecol.addItems(list(self.columns) or ["(no other column)"])
        self.direction = QComboBox(); self.direction.addItems(["Positive peaks", "Negative peaks", "Both"])
        self.minh = QDoubleSpinBox(); self.minh.setRange(0, 100); self.minh.setSuffix(" % of the highest"); self.minh.setToolTip("Keep only peaks at least this high (0 = all)")
        self.lam = QDoubleSpinBox(); self.lam.setRange(1, 1e12); self.lam.setDecimals(0); self.lam.setValue(1e5)
        self.asym = QDoubleSpinBox(); self.asym.setRange(0.0001, 0.5); self.asym.setDecimals(4); self.asym.setValue(0.01)
        self.prom = QDoubleSpinBox(); self.prom.setRange(0, 1e15); self.prom.setDecimals(6); self.prom.setValue(0)
        self.shape = QComboBox(); self.shape.addItems(list(B.PEAK_SHAPES)); self.shape.setToolTip("Shape for new peaks; change any peak in the table")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Centre", "Shape", "Fix centre", "Centre min", "Centre max", "Width (blank = auto)", "Fix width"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.table.verticalHeader().setVisible(True)
        self.table.itemChanged.connect(lambda *_: self.changed()); self.fix = QCheckBox("Fix all centres")
        self.fix.toggled.connect(lambda on: [self.table.item(r, 2).setCheckState(Qt.Checked if on else Qt.Unchecked) for r in range(self.table.rowCount())])
        self.autofit = QCheckBox("Fit while I edit"); self.autofit.setChecked(True)
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(250); self.timer.timeout.connect(self._auto)
        find = QPushButton("Find peaks"); fit = QPushButton("Fit peaks"); self.msg = QPlainTextEdit(); self.msg.setReadOnly(True)
        self.canvas.mpl_connect("button_press_event", self.click)
        f = QFormLayout(); f.addRow("Goal", self.goal); f.addRow("Baseline", self.bmode); f.addRow("ALS smoothness (lambda)", self.lam); f.addRow("ALS asymmetry p", self.asym)
        f.addRow("Custom constant", self.const); f.addRow("Automatic anchors", self.nanch); f.addRow("Baseline column", self.basecol)
        f.addRow("Minimum prominence (0 = auto)", self.prom); f.addRow("Direction", self.direction); f.addRow("Height filter", self.minh)
        f.addRow(find); f.addRow("Shape for new peaks", self.shape)
        f.addRow(QLabel("Peaks (click the graph to add, right-click to remove; set each peak's shape and limits):")); f.addRow(self.table)
        row2 = QHBoxLayout(); row2.addWidget(self.fix); row2.addWidget(self.autofit); f.addRow(row2)
        f.addRow(fit); f.addRow(QLabel("Results:")); f.addRow(self.msg)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        side = QVBoxLayout(); side.addLayout(f); side.addWidget(bb)
        row = QHBoxLayout(self); row.addWidget(self.canvas, 3); row.addLayout(side, 2)
        find.clicked.connect(self.find); fit.clicked.connect(self.fit)
        self.bmode.currentIndexChanged.connect(self.changed); self.goal.currentIndexChanged.connect(self.changed)
        for w in (self.lam, self.asym, self.const, self.nanch): w.valueChanged.connect(self.changed)
        self.basecol.currentIndexChanged.connect(self.changed)
        self.find()

    def baseline(self):
        m, y = self.bmode.currentIndex(), self.y
        if m == 0: return np.zeros_like(y)
        if m == 1: return np.full_like(y, np.nanmin(y))
        if m == 2: return np.interp(self.x, [self.x[0], self.x[-1]], [y[0], y[-1]])
        if m in (4, 5):  # through the anchor points (each takes the median of the nearest 5 data points, so noise does not matter)
            ax_, ay_ = self.anchor_xy()
            if len(ax_) < 2: return np.interp(self.x, [self.x[0], self.x[-1]], [y[0], y[-1]])
            if m == 4 and len(ax_) >= 3:
                from scipy.interpolate import PchipInterpolator  # smooth, no overshoot between anchors
                return PchipInterpolator(ax_, ay_, extrapolate=True)(self.x)
            return np.interp(self.x, ax_, ay_)
        if m == 6: return A.baseline_shirley(self.x, y)
        if m in (7, 8, 9, 10):
            v = {7: np.nanmax(y), 8: np.nanmean(y), 9: np.nanmedian(y), 10: self.const.value()}[m]; return np.full_like(y, v)
        if m == 11:  # straight line between the means of the first and last 5 % of the points
            k = max(2, len(y) // 20); return np.interp(self.x, [self.x[:k].mean(), self.x[-k:].mean()], [y[:k].mean(), y[-k:].mean()])
        if m == 12:  # smoothing B-spline through the anchor points
            ax_, ay_ = self.anchor_xy()
            if len(ax_) < 4: return np.interp(self.x, ax_, ay_) if len(ax_) > 1 else np.interp(self.x, [self.x[0], self.x[-1]], [y[0], y[-1]])
            from scipy.interpolate import UnivariateSpline
            return UnivariateSpline(ax_, ay_, k=3, s=len(ax_) * (0.02 * np.ptp(ay_) or 1e-12) ** 2)(self.x)
        if m == 13:  # automatic anchors: the lowest point of the (lightly smoothed) data in each of N equal segments, joined by lines
            ax_, ay_ = self.auto_anchors(); return np.interp(self.x, ax_, ay_)
        if m == 14: return self.columns.get(self.basecol.currentText(), np.zeros_like(y)).copy()
        return A.baseline_als(y, self.lam.value(), self.asym.value())

    def auto_anchors(self):
        n = self.nanch.value(); w = max(1, len(self.y) // 100); ys = np.convolve(self.y, np.ones(w) / w, mode="same") if w > 1 else self.y
        idx = [int(seg[np.argmin(ys[seg])]) for seg in np.array_split(np.arange(len(self.y)), n) if len(seg)]
        idx = sorted(set([0] + idx + [len(self.y) - 1])); return self.x[idx], ys[idx]

    def anchor_xy(self):
        xs = np.array(sorted(set(self.anchors)), float); ys = []
        if len(xs) > 1:  # anchors closer than 0.2% of the X range are one anchor (a double click must not kink the curve)
            xs = xs[np.r_[True, np.diff(xs) > 0.002 * np.ptp(self.x)]]
        for a in xs:
            i = np.argsort(np.abs(self.x - a))[:5]; ys.append(float(np.median(self.y[i])))
        return xs, np.array(ys)

    # ---- the peak table: one row per peak with its own shape, fixed flag and centre limits
    def peaks(self):
        out = []
        for r in range(self.table.rowCount()):
            try: c = float(self.table.item(r, 0).text())
            except (AttributeError, ValueError): continue
            lims = []
            for k in (3, 4):
                t = self.table.item(r, k).text().strip() if self.table.item(r, k) else ""
                try: lims.append(float(t))
                except ValueError: lims.append(-np.inf if k == 3 else np.inf)
            wt = self.table.item(r, 5).text().strip() if self.table.item(r, 5) else ""
            try: wv = float(wt) if wt else None
            except ValueError: wv = None
            out.append({"center": c, "shape": self.table.cellWidget(r, 1).currentText(), "fix": self.table.item(r, 2).checkState() == Qt.Checked,
                        "bounds": None if not np.isfinite(lims).any() else tuple(lims), "width": wv,
                        "fix_width": wv is not None and self.table.item(r, 6) is not None and self.table.item(r, 6).checkState() == Qt.Checked})
        return out

    def list_centers(self): return [p["center"] for p in self.peaks()]

    def set_peaks(self, peaks):
        self.table.blockSignals(True); self.table.setRowCount(0)
        for p in sorted(peaks, key=lambda p: p["center"]):
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(f"{p['center']:.6g}"))
            cb = QComboBox(); cb.addItems(list(B.PEAK_SHAPES)); cb.setCurrentText(p.get("shape") or self.shape.currentText())
            cb.currentIndexChanged.connect(lambda *_: self.changed()); self.table.setCellWidget(r, 1, cb)
            chk = QTableWidgetItem(); chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Checked if p.get("fix", self.fix.isChecked()) else Qt.Unchecked); self.table.setItem(r, 2, chk)
            b = p.get("bounds") or (None, None)
            for k, v in ((3, b[0]), (4, b[1])): self.table.setItem(r, k, QTableWidgetItem("" if v is None or not np.isfinite(v) else f"{v:.6g}"))
            self.table.setItem(r, 5, QTableWidgetItem("" if p.get("width") is None else f"{p['width']:.6g}"))
            fw = QTableWidgetItem(); fw.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            fw.setCheckState(Qt.Checked if p.get("fix_width") else Qt.Unchecked); self.table.setItem(r, 6, fw)
        self.table.blockSignals(False); self.changed()

    def changed(self, *_):
        self.result = None; self.preview()
        if self.autofit.isChecked() and self.table.rowCount(): self.timer.start()

    def _auto(self):
        if self.table.rowCount(): self.fit()

    def find(self):
        """Peaks of the data above the baseline (or below it, for negative peaks), filtered by height."""
        self.base = self.baseline(); d = self.y - self.base; out = []
        for sign in ((1,) if self.direction.currentIndex() == 0 else (-1,) if self.direction.currentIndex() == 1 else (1, -1)):
            for p in A.find_peaks(self.x, sign * d, self.prom.value() or None): out.append({"center": p["X"], "h": float(d[p["Index"]])})
        top = max([abs(p["h"]) for p in out] or [0]); keep = [p for p in out if abs(p["h"]) >= self.minh.value() / 100 * top]
        self.found = keep; self.set_peaks([{"center": p["center"]} for p in keep])

    def integrate(self):
        """Area of each peak above the baseline, integrated (trapezoid) between the valleys that separate neighbouring peaks."""
        self.base = self.baseline(); d = self.y - self.base; cs = sorted(self.list_centers()); x = self.x; out = []
        ic = [int(np.argmin(np.abs(x - c))) for c in cs]
        for k, i in enumerate(ic):
            sgn = 1 if d[i] >= 0 else -1
            lo = ic[k - 1] + int(np.argmin(sgn * d[ic[k - 1]:i + 1])) if k else 0
            hi = i + int(np.argmin(sgn * d[i:ic[k + 1] + 1])) if k + 1 < len(ic) else len(x) - 1
            if not k:  # first peak: go left until the signal returns to the baseline
                j = i
                while j > 0 and sgn * d[j] > 0.01 * abs(d[i]): j -= 1
                lo = j
            if k + 1 == len(ic):
                j = i
                while j < len(x) - 1 and sgn * d[j] > 0.01 * abs(d[i]): j += 1
                hi = j
            seg = slice(lo, hi + 1); area = float(np.trapz(d[seg], x[seg])); j = lo + int(np.argmax(sgn * d[seg])); h = float(d[j])
            above = np.flatnonzero(sgn * d[seg] >= abs(h) / 2) + lo; fw = np.nan
            if len(above) > 1:  # half-height crossings, interpolated between the points on either side
                a0, a1, half = above[0], above[-1], abs(h) / 2; v = sgn * d
                xl = np.interp(half, [v[a0 - 1], v[a0]], [x[a0 - 1], x[a0]]) if a0 > 0 and v[a0 - 1] < half else x[a0]
                xr = np.interp(half, [v[a1 + 1], v[a1]], [x[a1 + 1], x[a1]]) if a1 + 1 < len(x) and v[a1 + 1] < half else x[a1]
                fw = float(xr - xl)
            out.append({"Peak": k + 1, "Centre": float(x[j]), "Height": h, "FWHM": fw, "Area": area, "From": float(x[lo]), "To": float(x[hi])})
        tot = sum(abs(p["Area"]) for p in out) or 1.0
        for p in out: p["Area %"] = 100 * abs(p["Area"]) / tot
        self.integ = out
        self.msg.setPlainText("\n".join(f"Peak {p['Peak']}: centre {p['Centre']:.5g}, height {p['Height']:.4g}, FWHM {p['FWHM']:.4g}, area {p['Area']:.4g} "
                                        f"({p['Area %']:.1f}%), from {p['From']:.5g} to {p['To']:.5g}" for p in out) or "Add or find peaks first.")
        return out

    def click(self, ev):
        if ev.inaxes is None or ev.xdata is None: return
        if ev.key == "shift":  # baseline anchor points
            if ev.button == 3 and self.anchors: self.anchors.pop(int(np.argmin(np.abs(np.array(self.anchors) - ev.xdata))))
            elif ev.button == 1: self.anchors.append(float(ev.xdata))
            if self.bmode.currentIndex() not in (4, 5, 12): self.bmode.setCurrentIndex(4)
            return self.changed()
        pk = self.peaks()
        if ev.button == 3 and pk:  # right click removes the nearest peak
            pk.pop(int(np.argmin(np.abs(np.array([p["center"] for p in pk]) - ev.xdata))))
        elif ev.button == 1: pk.append({"center": float(ev.xdata)})
        self.set_peaks(pk)

    def fit(self):
        try:
            self.base = self.baseline(); pk = self.peaks()
            if not pk: raise ValueError("Add at least one peak.")
            self.result = B.fit_peaks(self.x, self.y, [p["center"] for p in pk], [p["shape"] for p in pk], baseline=self.base,
                                      fix_centers=[p["fix"] for p in pk], center_bounds=[p["bounds"] for p in pk],
                                      widths=[p["width"] for p in pk], fix_widths=[p["fix_width"] for p in pk])
            r = self.result; lines = [f"R2 = {r['R2']:.6f}   reduced chi2 = {r['Reduced_ChiSq']:.4g}"]
            lines += [f"Peak {p['Peak']} ({p['Shape']}): centre {p['Center']:.5g}, height {p['Height']:.4g}, FWHM {p['FWHM']:.4g}, "
                      f"area {p['Area']:.4g} ({p['Area %']:.1f}%)" for p in r["peaks"]]
            self.msg.setPlainText("\n".join(lines))
        except Exception as e:
            self.result = None; self.msg.setPlainText(f"Fit failed: {e}")
        self.preview()

    def preview(self, *_):
        self.base = self.baseline(); self.fig.clear(); ax = self.fig.add_subplot(111)
        ax.plot(self.x, self.y, "o", ms=3, mfc="none", color="0.3", label="data")
        if self.bmode.currentIndex(): ax.plot(self.x, self.base, "k--", lw=1, label="baseline")
        if self.bmode.currentIndex() in (4, 5, 12) and self.anchors:
            axx, ayy = self.anchor_xy(); ax.plot(axx, ayy, "s", ms=7, mfc="gold", mec="k", label="anchors", zorder=5)
        if self.bmode.currentIndex() == 13:
            axx, ayy = self.auto_anchors(); ax.plot(axx, ayy, "s", ms=6, mfc="gold", mec="k", label="automatic anchors", zorder=5)
        if self.goal.currentIndex() == 1 and self.list_centers():
            for k, p in enumerate(self.integrate()):
                m = (self.x >= p["From"]) & (self.x <= p["To"])
                ax.fill_between(self.x[m], self.base[m], self.y[m], alpha=0.3, color=f"C{(k + 1) % 10}", label=f"peak {p['Peak']} area")
        for c in self.list_centers(): ax.axvline(c, color="tab:orange", lw=0.8, alpha=0.6)
        if self.result:
            t = np.linspace(self.x[0], self.x[-1], 800); bt = np.interp(t, self.x, self.base)
            for k, comp in enumerate(self.result["components"]): ax.fill_between(t, bt, bt + comp(t), alpha=0.25, label=f"peak {k + 1}")
            ax.plot(t, bt + self.result["func"](t), "r-", lw=1.5, label="fit")
        ax.legend(fontsize=8); ax.set_title("Click: add peak   Right-click: remove peak   Shift+click: baseline anchor", fontsize=9); self.canvas.draw_idle()


class DatasetDialog(QDialog):
    """Pick arrays from an HDF5 / NetCDF / MATLAB file, or a table/query from SQLite."""

    def __init__(self, parent, path):
        super().__init__(parent); self.path = path; self.kind = FM.kind_of(path); self.setWindowTitle(f"Import: {path}"); self.resize(640, 520)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(["Name", "Shape", "Type"]); self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for n, shape, dt in FM.list_datasets(path):
            it = QTreeWidgetItem([n, " x ".join(map(str, shape)) or "scalar", dt]); it.setData(0, Qt.UserRole, n); self.tree.addTopLevelItem(it)
        self.as_sheet = QRadioButton("As worksheet columns (1-D arrays; 2-D arrays become one column per column)")
        self.as_matrix = QRadioButton("As matrix (one 2-D array; first slice of higher dimensions)"); self.as_sheet.setChecked(True)
        self.sql = QLineEdit(); self.sql.setPlaceholderText("Optional SQL query, e.g. select * from samples where mass > 2")
        lay = QVBoxLayout(self); lay.addWidget(self.tree)
        if self.kind == "sqlite": lay.addWidget(QLabel("Select a table, or type a query:")); lay.addWidget(self.sql)
        else: lay.addWidget(self.as_sheet); lay.addWidget(self.as_matrix)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def names(self): return [i.data(0, Qt.UserRole) for i in self.tree.selectedItems()]


class SparklineDelegate(QStyledItemDelegate):
    """Draws a small line plot of the column in the sparkline row of a worksheet."""

    def __init__(self, sheet, row): super().__init__(sheet.view); self.sh, self.row = sheet, row

    def paint(self, painter, option, index):
        if index.row() != self.row: return super().paint(painter, option, index)
        c = self.sh.df.columns[index.column()]; cache = self.sh.__dict__.setdefault("_spark", {})
        y = cache.get(c)
        if y is None:  # computed once per column until the sheet changes
            y = self.sh.arr(c); y = y[np.isfinite(y)]
            if y.size > 200: y = y[np.linspace(0, y.size - 1, 200).astype(int)]
            cache[c] = y
        from .sheets import PREFS
        dark = PREFS.get("theme") == "dark"
        painter.save(); painter.fillRect(option.rect, QColor(45, 45, 50) if dark else QColor(250, 250, 252))
        if y.size > 1:
            if y.size > 200: y = y[np.linspace(0, y.size - 1, 200).astype(int)]
            r = option.rect.adjusted(3, 3, -3, -3); lo, hi = float(y.min()), float(y.max()); span = (hi - lo) or 1.0
            pts = [QPointF(r.left() + r.width() * i / (y.size - 1), r.bottom() - r.height() * (v - lo) / span) for i, v in enumerate(y)]
            painter.setRenderHint(painter.RenderHint.Antialiasing); painter.setPen(QPen(QColor(100, 180, 255) if dark else QColor(31, 119, 180), 1.2))
            painter.drawPolyline(QPolygonF(pts))
        painter.restore()
