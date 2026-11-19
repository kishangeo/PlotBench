"""PlotBench export options: DPI, size and transparency, with a live pixel-size readout.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import io

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QDoubleSpinBox, QCheckBox, QLabel, QDialogButtonBox, QHBoxLayout,
                               QVBoxLayout, QPushButton, QInputDialog)

PRESETS = [("72 dpi (screen)", 72), ("150 dpi (draft)", 150), ("300 dpi (print, most journals)", 300),
           ("600 dpi (line art, high quality)", 600), ("1200 dpi (fine line art)", 1200)]
UNITS = {"in": 1.0, "cm": 2.54, "mm": 25.4}
VECTOR = (".svg", ".pdf", ".eps")
# Figure widths from the publishers' artwork guides (mm). Height keeps the graph's proportions.
JOURNALS = [("Custom size", None), ("Elsevier: single column (90 mm)", 90), ("Elsevier: 1.5 column (140 mm)", 140),
            ("Elsevier: full width (190 mm)", 190), ("Springer: single column (84 mm)", 84), ("Springer: double column (174 mm)", 174),
            ("Nature: single column (89 mm)", 89), ("Nature: double column (183 mm)", 183),
            ("Wiley / AGU: single column (85 mm)", 85), ("Wiley / AGU: double column (178 mm)", 178)]
MIN_PT = 6.0  # smallest text most journals accept at final size


class ExportDialog(QDialog):
    def __init__(self, parent, graph_defaults, last, fn=None, many=False, graph=None):
        super().__init__(parent); self.setWindowTitle("Export options"); self.many = many; self.graph = graph
        self.aspect = float(graph_defaults["height_in"]) / float(graph_defaults["width_in"])
        self.journal = QComboBox(); [self.journal.addItem(t, v) for t, v in JOURNALS]
        self.journal.setToolTip("Sets the width to the journal's column; the height keeps the graph's shape")
        dpi0 = float(last.get("dpi", graph_defaults["dpi"]))
        self.dpi = QComboBox(); self.dpi.setEditable(True)
        for label, v in PRESETS: self.dpi.addItem(label, v)
        match = [i for i, (_, v) in enumerate(PRESETS) if v == dpi0]
        if match: self.dpi.setCurrentIndex(match[0])
        else: self.dpi.setEditText(f"{dpi0:g}")
        self.unit = QComboBox(); self.unit.addItems(list(UNITS))
        self.w, self.h = QDoubleSpinBox(), QDoubleSpinBox()
        for sp, v in ((self.w, graph_defaults["width_in"]), (self.h, graph_defaults["height_in"])):
            sp.setRange(0.2, 400); sp.setDecimals(2); sp.setSingleStep(0.25); sp.setValue(float(v))
        self._unit = "in"; self.unit.currentTextChanged.connect(self._convert)
        self.keep = QCheckBox("Keep each graph's own size"); self.keep.setChecked(last.get("use_graph_size", True))
        self.trans = QCheckBox("Transparent background (not for JPEG)"); self.trans.setChecked(bool(last.get("transparent", False)))
        self.editable = QCheckBox("Editable text in PDF / EPS / SVG (Illustrator, Inkscape)"); self.editable.setChecked(bool(last.get("editable_text", True)))
        self.info = QLabel(); self.info.setWordWrap(True)
        self.pic = QLabel(); self.pic.setAlignment(Qt.AlignCenter); self.pic.setMinimumSize(380, 300)
        self.pic.setStyleSheet("background: #8a8f98; border-radius: 6px")
        size = QHBoxLayout(); size.addWidget(self.w); size.addWidget(QLabel("x")); size.addWidget(self.h); size.addWidget(self.unit)
        # named presets (kept in the settings): resolution, size, unit and the two switches under one name
        self.presets = (getattr(parent, "settings", None) or {}).setdefault("export_presets", {}) if hasattr(parent, "settings") else {}
        self.preset = QComboBox(); self.preset.setToolTip("Your saved export settings. Choose one to fill in everything below.")
        save_p, del_p = QPushButton("Save as preset..."), QPushButton("Delete"); save_p.clicked.connect(self.save_preset); del_p.clicked.connect(self.delete_preset)
        prow = QHBoxLayout(); prow.addWidget(self.preset, 1); prow.addWidget(save_p); prow.addWidget(del_p); self._fill_presets()
        self.preset.activated.connect(lambda *_: self.apply_preset(self.preset.currentText()))
        f = QFormLayout(); f.addRow("Preset", prow); f.addRow("Journal size", self.journal); f.addRow("Resolution", self.dpi); f.addRow("Size (width x height)", size)
        if many: f.addRow("", self.keep); self.keep.toggled.connect(self._update)
        f.addRow("", self.trans); f.addRow("", self.editable); f.addRow(self.info)
        self.vector = bool(fn) and str(fn).lower().endswith(VECTOR)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); bb.accepted.connect(self._ok); bb.rejected.connect(self.reject)
        row = QHBoxLayout(); row.addLayout(f, 1)
        if graph is not None:
            side = QVBoxLayout(); side.addWidget(QLabel("Preview at the exported size (true proportions and text size):")); side.addWidget(self.pic, 1)
            row.addLayout(side, 1)
        lay = QVBoxLayout(self); lay.addLayout(row); lay.addWidget(bb)
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(120); self.timer.timeout.connect(self._render)
        self.journal.currentIndexChanged.connect(self._journal)
        for sig in (self.dpi.currentTextChanged, self.w.valueChanged, self.h.valueChanged): sig.connect(self._update)
        self.small = None; self._update()

    def _fill_presets(self, current=None):
        self.preset.clear(); self.preset.addItem("(none)"); self.preset.addItems(sorted(self.presets))
        if current: self.preset.setCurrentText(current)

    def preset_value(self):
        return {"dpi": self.dpi_value(), "w": self.w.value(), "h": self.h.value(), "unit": self.unit.currentText(),
                "transparent": self.trans.isChecked(), "editable_text": self.editable.isChecked()}

    def save_preset(self, name=None):
        if not name:
            name, ok = QInputDialog.getText(self, "Save preset", "Name for these export settings (e.g. 'Elsevier single column, 600 dpi'):")
            if not ok or not name.strip(): return
        if self.dpi_value() is None: return
        self.presets[name.strip()] = self.preset_value(); self._fill_presets(name.strip()); self._store()

    def delete_preset(self):
        if self.presets.pop(self.preset.currentText(), None) is not None: self._fill_presets(); self._store()

    def _store(self):
        p = self.parent()
        if hasattr(p, "settings"):
            from .app import save_settings
            p.settings["export_presets"] = self.presets; save_settings(p.settings)

    def apply_preset(self, name):
        v = self.presets.get(name)
        if not v: return
        self.journal.setCurrentIndex(0); self.unit.setCurrentText(v.get("unit", "in")); self.w.setValue(float(v["w"])); self.h.setValue(float(v["h"]))
        match = [i for i, (_, d) in enumerate(PRESETS) if d == v["dpi"]]
        if match: self.dpi.setCurrentIndex(match[0])
        else: self.dpi.setEditText(f"{v['dpi']:g}")
        self.trans.setChecked(bool(v.get("transparent"))); self.editable.setChecked(bool(v.get("editable_text", True))); self._update()

    def _journal(self):
        mm = self.journal.currentData()
        if mm is None: return
        if self.unit.currentText() != "mm": self.unit.setCurrentText("mm")  # journals give widths in mm: keep them exact
        self.w.setValue(mm); self.h.setValue(round(mm * self.aspect, 1))

    def _render(self):
        """Draw the graph at the export size, scaled to the preview box, and find the smallest text."""
        if self.graph is None or self.use_graph_size(): return
        from matplotlib.figure import Figure
        from matplotlib.text import Text
        wi, hi = self.inches(); box = self.pic.size(); dpi = max(20.0, min((box.width() - 12) / wi, (box.height() - 12) / hi))
        fig = Figure(figsize=(wi, hi), layout="constrained")
        try: self.graph.render(fig)
        except Exception as e: self.pic.setText(f"Preview failed: {e}"); return
        buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor(), transparent=self.trans.isChecked())
        pm = QPixmap(); pm.loadFromData(buf.getvalue())
        self.pic.setPixmap(pm)
        sizes = [t.get_fontsize() for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]
        self.small = min(sizes) if sizes else None; self._update(render=False)

    def dpi_value(self):
        i = self.dpi.currentIndex(); text = self.dpi.currentText()
        if i >= 0 and text == self.dpi.itemText(i): return float(self.dpi.itemData(i))
        try: return float(text.split()[0])
        except (ValueError, IndexError): return None

    def inches(self):
        k = UNITS[self.unit.currentText()]; return self.w.value() / k, self.h.value() / k

    def use_graph_size(self): return self.many and self.keep.isChecked()

    def _convert(self, new):
        old = self._unit; f = UNITS[new] / UNITS[old]
        for sp in (self.w, self.h): sp.blockSignals(True); sp.setValue(sp.value() * f); sp.blockSignals(False)
        self._unit = new; self._update()

    def _update(self, *_, render=True):
        if render and self.graph is not None: self.timer.start()
        d = self.dpi_value(); wi, hi = self.inches()
        for sp in (self.w, self.h, self.unit): sp.setEnabled(not self.use_graph_size())
        if d is None or not (10 <= d <= 4800): self.info.setText("<span style='color:firebrick'>Enter a DPI between 10 and 4800.</span>"); return
        px = f"{round(wi * d):,} x {round(hi * d):,} pixels" if not self.use_graph_size() else "each graph at its own size"
        note = " SVG, PDF and EPS are vector files: lines and text stay sharp at any size; DPI only affects shaded or image parts." if self.vector else ""
        big = " This is a very large image." if not self.use_graph_size() and wi * hi * d * d > 1.5e8 else ""
        warn = (f"<br><span style='color:firebrick'>Smallest text is {self.small:.1f} pt; most journals ask for at least {MIN_PT:g} pt at "
                f"final size. Increase the font size in Graph Properties.</span>") if self.small and self.small < MIN_PT else ""
        self.info.setText(f"Output: {px} at {d:g} dpi.{big}{note}{warn}")

    def _ok(self):
        if self.dpi_value() is None or not (10 <= self.dpi_value() <= 4800): return
        self.accept()

    def value(self):
        wi, hi = self.inches(); return {"dpi": self.dpi_value(), "width_in": wi, "height_in": hi, "transparent": self.trans.isChecked(),
                                        "editable_text": self.editable.isChecked()}
