"""Screenshots and example figures for the PlotBench website (docs/). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import os, sys, tempfile
os.environ["APPDATA"] = tempfile.mkdtemp()
from pathlib import Path
from PySide6.QtWidgets import QApplication
from plotbench import app as M, examples as EX

OUT = Path(__file__).parent / "docs" / "img"; OUT.mkdir(parents=True, exist_ok=True)
FIGS = [("oxides", "TAS (SiO2 vs Na2O+K2O)", "tas"), ("zircon", "Concordia (Wetherill)", "concordia"),
        ("trace", "Spider: REE / CI Chondrite", "spider"), ("oxides", "PCA Biplot (scores + loadings)", "pca"),
        ("raman", "Line", "raman"), ("ternary", None, "ternary"), ("basalts", "Pearce 2008: Th/Yb vs Nb/Yb", "pearce"),
        ("detrital", "Detrital Age KDE + PDP", "detrital")]


def main():
    qa = QApplication(sys.argv[:1]); w = M.Main(); w.resize(1800, 1050); w.show(); qa.processEvents()
    for key, kind, name in FIGS:
        g = EX.open_example(w, key, kind); qa.processEvents()
        g.export(str(OUT / f"{name}.png"), dpi=110)
    g = EX.open_example(w, "oxides", "TAS (SiO2 vs Na2O+K2O)"); qa.processEvents()
    w.mdi.setActiveSubWindow(g.parentWidget()); g.parentWidget().showMaximized(); qa.processEvents()
    w.grab().save(str(OUT / "window.png"))
    w.set_theme("dark"); qa.processEvents(); w.grab().save(str(OUT / "window_dark.png"))
    w.dirty = False; w._bulk_close = True; w.close(); print("site images:", OUT)


if __name__ == "__main__":
    main()
