"""Screenshots and example figures for the PlotBench website (docs/). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import os, sys, tempfile
os.environ["APPDATA"] = tempfile.mkdtemp()
# render off screen at 2x, so the window screenshot is sharp and laid out like a normal 1440 x 900 desktop
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("QT_SCALE_FACTOR", "2")
if os.name == "nt": os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:Windows"), "Fonts"))
from pathlib import Path
from PySide6.QtWidgets import QApplication
from plotbench import app as M, examples as EX

OUT = Path(__file__).parent / "docs" / "img"; OUT.mkdir(parents=True, exist_ok=True)
FIGS = [("oxides", "TAS (SiO2 vs Na2O+K2O)", "tas"), ("zircon", "Concordia (Wetherill)", "concordia"),
        ("trace", "Spider: REE / CI Chondrite", "spider"), ("oxides", "PCA Biplot (scores + loadings)", "pca"),
        ("raman", "Line", "raman"), ("ternary", None, "ternary"), ("basalts", "Pearce 2008: Th/Yb vs Nb/Yb", "pearce"),
        ("detrital", "Detrital Age KDE + PDP", "detrital")]


def main():
    qa = QApplication(sys.argv[:1]); w = M.Main(); w.resize(1440, 880); w.show(); qa.processEvents()
    g = EX.open_example(w, "oxides", "TAS (SiO2 vs Na2O+K2O)"); qa.processEvents()
    g.parentWidget().showMaximized(); qa.processEvents(); w.mdi.setActiveSubWindow(g.parentWidget()); qa.processEvents()
    w.grab().save(str(OUT / "window.png"))
    w.set_theme("dark"); qa.processEvents(); w.grab().save(str(OUT / "window_dark.png")); w.set_theme("light")
    for key, kind, name in FIGS:
        g = EX.open_example(w, key, kind); qa.processEvents()
        g.export(str(OUT / f"{name}.png"), dpi=110)
    w.dirty = False; w._bulk_close = True; w.close(); print("site images:", OUT)


if __name__ == "__main__":
    main()
