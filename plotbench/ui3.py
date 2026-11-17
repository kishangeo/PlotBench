"""PlotBench Digitizer: read data points off an image of a graph (e.g. a figure in a paper).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QInputDialog, QFileDialog,
                               QDialogButtonBox, QListWidget, QMessageBox)

from .analysis import parse_number

LOUPE_PX = 220   # size of the magnifier
LOUPE_ZOOM = 8   # image pixels are drawn this many times larger

STEPS = ["X axis point 1", "X axis point 2", "Y axis point 1", "Y axis point 2"]


def calibrate(px, val, log=False):
    """Map pixel coordinates to data values from two reference clicks (linear or log axis)."""
    (p1, p2), (v1, v2) = px, val
    if p1 == p2: raise ValueError("the two calibration clicks on this axis are at the same place; click two different ticks")
    if log and (v1 <= 0 or v2 <= 0): raise ValueError("a log axis needs positive calibration values; untick Log or use other ticks")
    if log: v1, v2 = np.log10(v1), np.log10(v2)
    def f(p):
        v = v1 + (np.asarray(p, float) - p1) * (v2 - v1) / (p2 - p1); return 10 ** v if log else v
    return f


class Digitizer(QDialog):
    def __init__(self, parent, path=None):
        super().__init__(parent); self.setWindowTitle("Digitizer"); self.resize(1100, 760)
        self.cal_px, self.cal_val, self.points = [], [], []
        self.fig = Figure(layout="constrained"); self.canvas = FigureCanvasQTAgg(self.fig); self.ax = self.fig.add_subplot(111)
        self.msg = QLabel(); self.logx, self.logy = QCheckBox("Log X axis"), QCheckBox("Log Y axis"); self.lst = QListWidget()
        load = QPushButton("Open image..."); undo = QPushButton("Remove last point"); reset = QPushButton("Restart calibration")
        load.clicked.connect(self.load); undo.clicked.connect(self.undo); reset.clicked.connect(self.reset)
        for c in (self.logx, self.logy): c.toggled.connect(self.refresh_list)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        self.msg.setWordWrap(True)
        self.loupe = QLabel(); self.loupe.setFixedSize(LOUPE_PX, LOUPE_PX); self.loupe.setStyleSheet("background: #f4f4f4; border: 1px solid #aaa")
        self.loupe.setToolTip("Magnifier: the image under the mouse, enlarged; the red cross is exactly where a click will go")
        self.where = QLabel(""); self.where.setStyleSheet("color: gray")
        side = QVBoxLayout(); [side.addWidget(w) for w in (load, self.msg, self.loupe, self.where, self.logx, self.logy, reset,
                                                           QLabel("Points (X, Y):"), self.lst, undo, bb)]
        left = QVBoxLayout(); left.addWidget(NavigationToolbar2QT(self.canvas, self)); left.addWidget(self.canvas)
        row = QHBoxLayout(self); row.addLayout(left, 3); row.addLayout(side, 1)
        self.canvas.mpl_connect("button_press_event", self.click); self.canvas.mpl_connect("motion_notify_event", self.magnify)
        self.img = None
        if path: self.load(path)
        self.update_msg()

    def load(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Graph image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif)")
            if not path: return
        from PIL import Image
        self.img = np.asarray(Image.open(path).convert("RGB")); self._padded = None; self.reset()

    def reset(self):
        self.cal_px, self.cal_val, self.points = [], [], []; self.redraw(); self.refresh_list()

    def update_msg(self):
        if self.img is None: self.msg.setText("Open an image of a graph to start.")
        elif len(self.cal_px) < 4: self.msg.setText(f"Step {len(self.cal_px) + 1} of 4: click {STEPS[len(self.cal_px)]} on a labelled tick, "
                                                    "then type its value. The magnifier shows exactly where the click goes.")
        elif getattr(self, "problem", ""): self.msg.setText(f"<span style='color:firebrick'>Calibration problem: {self.problem}.</span>")
        else: self.msg.setText(f"Calibrated. Click each data point ({len(self.points)} so far). OK puts them in a new worksheet and graph.")

    def click(self, ev):
        if self.img is None or ev.inaxes is not self.ax or ev.xdata is None or ev.button != 1: return
        if self.canvas.toolbar.mode:
            self.msg.setText("Zoom or pan is switched on in the toolbar: click its button again to switch it off, then click the points."); return
        x, y = float(ev.xdata), float(ev.ydata)
        if len(self.cal_px) < 4: QTimer.singleShot(0, lambda: self.ask_value(x, y))  # after the click has finished (no dialog inside it)
        else: self.points.append((x, y)); self.redraw(); self.refresh_list()

    def ask_value(self, x, y):
        """Ask for the axis value at a calibration click; accepts 2400, 1e-18, 10^-18, 2.5x10^3 ..."""
        step = STEPS[len(self.cal_px)]; text = ""
        while True:
            text, ok = QInputDialog.getText(self, "Calibration", f"Value at {step}:\n(e.g. 2400, 0.5, 1e-18, 10^-18, 2.5x10^3)", text=text)
            if not ok: return
            try: v = parse_number(text); break
            except ValueError as e: QMessageBox.warning(self, "Calibration", str(e))
        self.cal_px.append((x, y)); self.cal_val.append(v)
        for k, box, name in ((2, self.logx, "X"), (4, self.logy, "Y")):  # values over several decades: probably a log axis
            if len(self.cal_val) == k and not box.isChecked():
                a, b = self.cal_val[k - 2:k]
                if a > 0 and b > 0 and max(a, b) / min(a, b) >= 1000 and QMessageBox.question(
                        self, "Log axis?", f"{a:g} and {b:g} are {np.log10(max(a, b) / min(a, b)):.0f} decades apart. "
                                           f"Is the {name} axis logarithmic?") == QMessageBox.Yes:
                    box.setChecked(True)
        self.redraw(); self.refresh_list()

    def magnify(self, ev):
        """Show the image around the mouse enlarged, with a cross at the exact pixel a click would use."""
        if self.img is None or ev.inaxes is not self.ax or ev.xdata is None: return
        h, w = self.img.shape[:2]; half = LOUPE_PX // (2 * LOUPE_ZOOM)
        cx, cy = int(round(ev.xdata)), int(round(ev.ydata))
        if getattr(self, "_padded", None) is None:  # once per image, not on every mouse move
            self._padded = np.pad(self.img, ((half, half + 1), (half, half + 1), (0, 0)), constant_values=200)
        pad = self._padded
        crop = np.ascontiguousarray(np.repeat(np.repeat(pad[cy:cy + 2 * half + 1, cx:cx + 2 * half + 1], LOUPE_ZOOM, 0), LOUPE_ZOOM, 1))
        q = QImage(crop.data, crop.shape[1], crop.shape[0], 3 * crop.shape[1], QImage.Format_RGB888).copy()
        pm = QPixmap.fromImage(q); p = QPainter(pm); c = half * LOUPE_ZOOM + LOUPE_ZOOM // 2
        pen = QPen(QColor(230, 20, 20)); pen.setWidth(2); p.setPen(pen); p.drawLine(c, 0, c, pm.height()); p.drawLine(0, c, pm.width(), c)
        p.drawRect(c - LOUPE_ZOOM // 2, c - LOUPE_ZOOM // 2, LOUPE_ZOOM, LOUPE_ZOOM); p.end(); self.loupe.setPixmap(pm)
        t = self.transform(); txt = f"pixel {ev.xdata:.1f}, {ev.ydata:.1f}"
        if t is not None: txt += f"   ->   X = {float(t[0](ev.xdata)):.5g}, Y = {float(t[1](ev.ydata)):.5g}"
        self.where.setText(txt)

    def accept(self):
        if self.img is not None and not self.points:
            what = "click the data points" if len(self.cal_px) == 4 else "finish the four calibration clicks and then click the data points"
            if QMessageBox.question(self, "Digitizer", f"No data points yet: {what}.\nClose the digitizer anyway?") != QMessageBox.Yes: return
        super().accept()

    def undo(self):
        if self.points: self.points.pop()
        elif self.cal_px: self.cal_px.pop(); self.cal_val.pop()
        self.redraw(); self.refresh_list()

    def transform(self):
        if len(self.cal_px) < 4: return None
        try:
            fx = calibrate((self.cal_px[0][0], self.cal_px[1][0]), self.cal_val[0:2], self.logx.isChecked())
            fy = calibrate((self.cal_px[2][1], self.cal_px[3][1]), self.cal_val[2:4], self.logy.isChecked())
        except ValueError as e:
            self.problem = str(e); return None
        self.problem = ""; return fx, fy

    def data(self):
        t = self.transform()
        if t is None or not self.points: return pd.DataFrame({"X": [], "Y": []})
        p = np.array(self.points); return pd.DataFrame({"X": t[0](p[:, 0]), "Y": t[1](p[:, 1])}).sort_values("X", ignore_index=True)

    def refresh_list(self, *_):
        self.lst.clear(); d = self.data(); self.lst.addItems([f"{a:.6g}, {b:.6g}" for a, b in zip(d.X, d.Y)]); self.update_msg()

    def redraw(self):
        lim = (self.ax.get_xlim(), self.ax.get_ylim()) if self.img is not None and self.ax.images else None
        self.ax.clear()
        if self.img is not None:
            self.ax.imshow(self.img); self.ax.set_axis_off()
            for (x, y), lab, v in zip(self.cal_px, STEPS, self.cal_val):
                self.ax.plot(x, y, "b+", ms=14, mew=2); self.ax.text(x, y, f" {lab} = {v:g}", color="b", fontsize=8)
            if self.points: p = np.array(self.points); self.ax.plot(p[:, 0], p[:, 1], "ro", ms=5, mfc="none", mew=1.5)
            if lim: self.ax.set_xlim(lim[0]); self.ax.set_ylim(lim[1])
        self.canvas.draw_idle()
