"""Build the PlotBench user manual: screenshots of the real program plus the reference sections generated from the code
(menus, plot types, fit models, formula functions, shortcuts, modules), written to plotbench/manual/manual.html.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Run on a desktop (screenshots need a display): python make_manual.py [--pdf out.pdf]
"""
import ast
import hashlib
import html
import inspect
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ["APPDATA"] = tempfile.mkdtemp()  # clean settings: no recent files, light theme
# screenshots at 2x (sharp in the manual window on high-DPI screens and in the PDF), rendered off screen with the system fonts
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("QT_SCALE_FACTOR", "2")
if os.name == "nt": os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu  # noqa: E402

OUT = ROOT / "plotbench" / "manual"; IMG = OUT / "img"
if IMG.exists(): shutil.rmtree(IMG)
(IMG / "plots").mkdir(parents=True); (IMG / "icons").mkdir()

qa = QApplication(sys.argv); qa.setStyle("Fusion")
from plotbench import app as M, examples as EX, gallery as GL, plothelp as PH, cmdhelp as CH, analysis as A, keys as K  # noqa: E402
from plotbench import graphs as G, tools as TL, ui2, export_dialog as ED, sheets as SH, console as CON, helpwin as HW  # noqa: E402
from plotbench import geodata as GD  # noqa: E402

w = M.Main(); w.resize(1440, 900); w.show(); qa.processEvents()
SHOTS = {}


def esc(s): return html.escape(str(s))


def shot(widget, name, width=None, caption=""):
    """Grab a widget into img/name.png; returns an <img> block."""
    widget.show(); qa.processEvents(); qa.processEvents()
    pm = widget.grab(); pm.save(str(IMG / f"{name}.png")); r = pm.devicePixelRatio() or 1; SHOTS[name] = (round(pm.width() / r), round(pm.height() / r))
    return fig(name, width, caption)


def fig(name, width=None, caption=""):
    pw, ph = SHOTS[name]; wd = min(width or pw, 820)
    cap = f"<p class='cap'>Figure: {esc(caption)}</p>" if caption else ""
    return f"<p align='center'><img src='img/{name}.png' width='{wd}'></p>{cap}"


def close_all():
    w.dirty = False
    w._bulk_close = True
    for s in list(w.mdi.subWindowList()): s.close()
    w._bulk_close = False
    qa.processEvents()


# ------------------------------------------------------------------ screenshots of the real program
close_all()
gr = w.open_example("colour_map"); w.mdi.tileSubWindows(); qa.processEvents()
S_MAIN = shot(w, "main_window", caption="The main window: menus, the four toolbars, the Project Explorer (left), a worksheet and a colour-mapped graph.")
book = w.windows()[0]
S_SHEET = shot(book, "worksheet", 760, "A worksheet. The grey rows hold long name, units and comments; the next row shows a sparkline of each column.")
gwin = [x for x in w.windows() if x.kind == "graph"][0]
S_GRAPH = shot(gwin, "graph_window", 760, "A graph window: navigation toolbar, the format bar for quick styling, and the plot.")
S_FMT = shot(gwin.fmt, "format_bar", 820, "The format bar: curve, colour, line width and style, symbol, size, hollow, log axes, grid, legend, font.")
close_all()

from plotbench.startpage import StartPage  # noqa: E402
sp = StartPage(w); sp.resize(1000, 700); S_START = shot(sp, "start_page", 760, "The Start page: quick actions, templates and recent projects."); sp.close()

gd = GL.PlotGallery(w, w._thumb_dir(), "Will plot from Book1/Sheet1: X = A; Y = B"); gd.resize(1150, 760)
gd.side.setCurrentRow([c for c, _ in gd.cats].index("Geochemistry")); qa.processEvents()
while gd._pending: gd._render_next()
gd.grid.setCurrentRow(7); qa.processEvents()
S_GALLERY = shot(gd, "plot_gallery", 820, "The Plot Gallery: categories, thumbnails, the data guide for the selected type and 'Open example data'."); gd.close()

b = w.open_example("calibration"); sh = b.current() if hasattr(b, "current") else w.sheet_ref(b.spec["book"], b.spec["sheet"])
from plotbench.cmapdlg import ColorMapDialog  # noqa: E402
cb = w.open_example("colour_map", "Scatter") if False else None
bk = w.new_book(EX.load("colour_map"), "colourmap"); bk.current().desig = {c: EX.EXAMPLES["colour_map"][3].get(c, "Y") for c in bk.current().df.columns}
cm = ColorMapDialog(w, bk.current(), "Color-mapped Scatter", None); cm.resize(1100, 700)
S_CMAP = shot(cm, "colormap_dialog", 820, "The colour-map dialog with its live preview: columns, groups, labels, colour map, range, colour bar and symbols."); cm.close()

g = w.open_example("calibration", "Scatter")
sd = G.StyleDialog(w, g.spec["style"], graph=g); sd.w["title"].setText("Calibration"); sd.live.run()
S_STYLE = shot(sd, "graph_properties", 560, "Graph Properties with live preview: the graph changes as you type; OK keeps, Cancel undoes, Apply keeps and stays open."); sd.reject()

sp_ = EX.load("raman"); x, y = sp_.iloc[:, 0].to_numpy(float), sp_.iloc[:, 1].to_numpy(float)
xc = np.linspace(0, 10, 60); yc = 3 * np.exp(-((xc - 5) / 1.2) ** 2) + 0.2 + np.random.default_rng(1).normal(0, 0.05, 60)
fd = TL.FitDialog(w, xc, yc, ["X", "Y"]); fd.func.setCurrentText("Gaussian"); fd.live.run(); fd.resize(1150, 700)
S_FIT = shot(fd, "fit_dialog", 820, "The Nonlinear Curve Fit dialog: parameters with fixed values and bounds on the left, the live fit and residuals on the right."); fd.reject()
pa = ui2.PeakAnalyzer(w, x, y); pa.resize(1150, 720); pa.bmode.setCurrentIndex(2); pa.autofit.setChecked(False)
pa.set_peaks([{"center": 465, "shape": "Gaussian"}, {"center": 520, "shape": "Lorentzian"}, {"center": 820, "shape": "PseudoVoigt"}]); pa.fit()
S_PEAK = shot(pa, "peak_analyzer", 820, "The Peak Analyzer: ALS baseline, three peaks with different shapes, the fit and each component."); pa.reject()
ed = ED.ExportDialog(w, g.export_defaults(), {}, "figure.pdf", graph=g); ed.journal.setCurrentIndex(1); qa.processEvents(); ed._render()
S_EXPORT = shot(ed, "export_dialog", 820, "The export dialog: journal width, resolution, size, transparency, editable text and a true-size preview."); ed.reject()
fdl = SH.FormulaDialog(sh, sh.df.columns[-1]) if hasattr(sh, "df") else None
bw = w.new_book(EX.load("oxides"), "oxides"); s_ox = bw.current(); s_ox.add_column("Alkalis")
fdl = SH.FormulaDialog(s_ox, "Alkalis"); fdl.expr.setText("Na2O + K2O"); fdl.live.run(); fdl.resize(560, 470)
S_FORMULA = shot(fdl, "formula_dialog", 520, "Set Column Values: the first rows of the result are shown while you type."); fdl.reject()
iw = SH.ImportWizard(w, str(EX.FOLDER / "major_oxides_wt.csv")); iw.resize(900, 640)
S_IMPORT = shot(iw, "import_wizard", 760, "The Import Wizard: delimiter, header lines, units and comments rows, decimal comma and a live preview."); iw.reject()
fb = HW.FeedbackDialog(w, M.VERSION); fb.subject.setText("Example: legend position"); fb.text.setPlainText("Describe the problem or idea here.")
S_FEEDBACK = shot(fb, "feedback", 560, "Help > Send Feedback."); fb.reject()
gs = w.open_example("trace"); gs.resize(900, 560); S_SPIDER = shot(gs, "spider", 700, "Chondrite-normalised REE spider diagram of the trace-element example.")
gt = w.open_example("oxides"); gt.resize(900, 620); S_TAS = shot(gt, "tas", 700, "TAS diagram (Le Bas et al. 1986) of the major-oxide example.")
gq = w.open_example("qap"); gq.resize(900, 640); S_QAP = shot(gq, "qap", 640, "QAP diagram (Streckeisen 1976).")
gp = w.open_example("water"); gp.resize(900, 640); S_PIPER = shot(gp, "piper", 640, "Piper diagram of the water example after the mg/L to meq/L conversion.")
w.desc_target = None
bb = w.new_book(EX.load("groups"), "groups"); w.mdi.setActiveSubWindow([s for s in w.mdi.subWindowList() if s.widget() is bb][0])
bb.current().view.selectAll(); w.desc(); rep = [x for x in w.windows() if x.kind == "report"][-1]; rep.resize(760, 520)
S_REPORT = shot(rep, "report", 700, "A report window (descriptive statistics). Reports can be saved as HTML or PDF.")
w.console_dock.show(); w.console_dock.resize(900, 300); qa.processEvents()
S_CONSOLE = shot(w.console_dock, "console", 760, "The Python console (Ctrl+Shift+P)."); w.console_dock.hide()


def menu_shot(title, name, caption):
    for a in w.menuBar().actions():
        if a.text().replace("&", "") == title:
            m = [x for x in w.menuBar().findChildren(QMenu) if x.menuAction() is a][0]
            m.popup(w.mapToGlobal(w.rect().topLeft())); qa.processEvents()
            r = shot(m, name, None, caption); m.hide(); return r


S_MSTAT = menu_shot("Statistics", "menu_statistics", "The Statistics menu, grouped by question.")
S_MANAL = menu_shot("Analysis", "menu_analysis", "The Analysis menu.")
mw = HW.ManualWindow(w) if HW.MANUAL.exists() else None
close_all()

# plot thumbnails for the plot reference
for k in [k for _, ks in GL.categories() for k in ks]:
    src = Path(w._thumb_dir()) / f"{hashlib.md5(k.encode()).hexdigest()[:10]}.png"
    if not src.exists(): GL.thumbnail(k, w._thumb_dir())
    shutil.copy(src, IMG / "plots" / src.name)

# toolbar buttons with their icons
TOOLBARS = []
MENU_TIPS = {}
for a_ in w.findChildren(QAction):
    lab_ = a_.text().replace("&", "").rstrip(".")
    if a_.statusTip(): MENU_TIPS.setdefault(lab_, a_.statusTip())


def _same(a, b): return re.sub(r"[^a-z0-9]", "", a.lower()) == re.sub(r"[^a-z0-9]", "", b.lower())


def _tip(a):
    """A description that says more than the button's own name."""
    label = a.text().replace("&", "")
    for t in (a.toolTip(), a.statusTip(), CH.describe(label), MENU_TIPS.get(label.rstrip("."), ""),
              next((v for k, v in MENU_TIPS.items() if k.lower().startswith(label.lower().rstrip("."))), "")):
        t = (t or "").splitlines()[0] if t else ""
        if t and not _same(t, label): return t
    return ""
from PySide6.QtWidgets import QToolBar  # noqa: E402
for tb in w.findChildren(QToolBar):
    if tb.parent() is not w: continue
    rows = []
    for i, a in enumerate(tb.actions()):
        if a.isSeparator() or not a.text(): continue
        fn = f"{abs(hash((tb.windowTitle(), a.text()))) % 10**8}.png"
        if not a.icon().isNull(): a.icon().pixmap(48, 48).save(str(IMG / "icons" / fn))
        rows.append((fn if not a.icon().isNull() else None, a.text().replace("&", ""), _tip(a)))
    if rows: TOOLBARS.append((tb.windowTitle(), rows))


# ------------------------------------------------------------------ reference sections generated from the code
def menu_reference():
    menus = w.menuBar().findChildren(QMenu); by_action = {id(m.menuAction()): m for m in menus}
    out = []

    def walk(m, path):
        rows = []
        for a in m.actions():
            if a.isSeparator(): continue
            sub = next((x for x in menus if x.menuAction() is a), None)
            if sub is not None: walk(sub, path + [a.text().replace("&", "")]); continue
            if not a.isEnabled() or not a.text(): continue
            label = a.text().replace("&", ""); tip = _tip(a)
            sc = a.shortcut().toString()
            rows.append(f"<tr><td><b>{esc(label)}</b>{' <span class=k>' + esc(sc) + '</span>' if sc else ''}</td><td>{esc(tip)}</td></tr>")
        if rows: out.append(f"<h4>{esc(' > '.join(path))}</h4><table class='ref'>{''.join(rows)}</table>")
    for a in w.menuBar().actions():
        m = next((x for x in menus if x.menuAction() is a), None)
        if m is not None and a.text().replace("&", "") != "Plot": walk(m, [a.text().replace("&", "")])
    return "".join(out)


def plot_reference():
    out = []
    for cat, kinds in GL.categories():
        if cat == "Geochemistry": kinds = [k for k in kinds if k not in ("Ternary", "Piper Diagram")]
        out.append(f"<h3 id='plots-{re.sub('[^a-z]', '', cat.lower())}'>{esc(cat)}</h3>")
        for k in kinds:
            what, prep, ex, tip = PH.HELP[k]; img = f"img/plots/{hashlib.md5(k.encode()).hexdigest()[:10]}.png"
            table = ""
            if ex:
                table = "<table class='ex'>" + "".join("<tr>" + "".join(f"<td>{'<b>' + esc(c) + '</b>' if i == 0 else esc(c)}</td>" for c in row) + "</tr>"
                                                       for i, row in enumerate(ex)) + "</table>"
            exk = EX.for_plot(k); exs = f"<br><i>Example data:</i> Help > Example Data > {esc(EX.EXAMPLES[exk][0])}" if exk else ""
            out.append(f"<table class='plot'><tr><td width='160' valign='top'><img src='{img}' width='150'></td><td valign='top'>"
                       f"<b>{esc(k)}</b><br>{esc(what)}<br><i>Data:</i> {esc(prep)}{table}{('<i>Tip:</i> ' + esc(tip)) if tip else ''}{exs}</td></tr></table>")
    return "".join(out)


def fit_models():
    rows = []
    for name, (f, _) in A.MODELS.items():
        try:
            src = inspect.getsource(f).strip(); body = src.split("return", 1)[1] if "return" in src else src.split(":", 1)[1]
            body = re.sub(r"\s+", " ", body).strip()
        except (OSError, TypeError, IndexError): body = ""
        rows.append(f"<tr><td><b>{esc(name)}</b></td><td>{esc(', '.join(A.model_params(name)))}</td><td><code>y = {esc(body[:180])}</code></td></tr>")
    return "<table class='ref'><tr><th>Model</th><th>Parameters</th><th>Function (Python, as computed)</th></tr>" + "".join(rows) + "</table>"


def formula_functions():
    fns = sorted(k for k, v in A.SAFE_NS.items() if callable(v)); consts = sorted(k for k, v in A.SAFE_NS.items() if not callable(v))
    return f"<p><b>Functions:</b> {esc(', '.join(fns))}.</p><p><b>Constants:</b> {esc(', '.join(consts))}; <b>i</b> is the row number (1, 2, 3 ...).</p>"


def shortcuts():
    rows = []
    for k_, a in K.SHORTCUTS:
        rows.append(f"<tr><td colspan=2><h4>{esc(k_)}</h4></td></tr>" if not a else f"<tr><td class=k>{esc(k_)}</td><td>{esc(a)}</td></tr>")
    return "<table class='ref'>" + "".join(rows) + "</table>"


def modules():
    rows = []
    for p in sorted((ROOT / "plotbench").glob("*.py")):
        doc = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
        first = " ".join(l for l in doc.split("\n\n")[0].splitlines() if not l.startswith("Author")).strip()
        n = sum(1 for _ in p.open(encoding="utf-8"))
        rows.append(f"<tr><td><code>{p.name}</code></td><td>{n}</td><td>{esc(first)}</td></tr>")
    return "<table class='ref'><tr><th>Module</th><th>Lines</th><th>What it holds</th></tr>" + "".join(rows) + "</table>"


def toolbar_reference():
    out = []
    for title, rows in TOOLBARS:
        icon = lambda fn: f"<img src='img/icons/{fn}' width=24>" if fn else ""
        trs = "".join(f"<tr><td width=30>{icon(fn)}</td><td><b>{esc(t)}</b></td><td>{esc(d)}</td></tr>" for fn, t, d in rows)
        out.append(f"<h4>{esc(title)} toolbar</h4><table class='ref'>{trs}</table>")
    return "".join(out)


def examples_table():
    rows = "".join(f"<tr><td><b>{esc(e[0])}</b><br><code>{esc(e[1])}</code></td><td>{esc(e[2])}</td><td>{esc(', '.join(e[4]) or '(analysis only)')}</td></tr>"
                   for e in EX.EXAMPLES.values())
    return "<table class='ref'><tr><th>Example</th><th>What is in it</th><th>Plots it opens</th></tr>" + rows + "</table>"


def references():
    return "<ul>" + "".join(f"<li><b>{esc(k)}</b>: {esc(v)}</li>" for k, v in GD.CITATIONS.items()) + \
        "<li><b>TAS</b>: Le Bas, M.J., Le Maitre, R.W., Streckeisen, A., Zanettin, B. (1986). A chemical classification of volcanic rocks " \
        "based on the total alkali-silica diagram. Journal of Petrology 27, 745-750.</li><li><b>QAP</b>: Streckeisen, A. (1976). To each " \
        "plutonic rock its proper name. Earth-Science Reviews 12, 1-33.</li><li><b>Feldspars</b>: Deer, W.A., Howie, R.A., Zussman, J. (1992). An Introduction to the Rock-Forming Minerals, 2nd ed. Longman.</li><li><b>AFM</b>: Irvine, T.N., Baragar, W.R.A. (1971). A guide to the chemical classification of the common volcanic rocks. Canadian Journal of Earth Sciences 8, 523-548.</li>"         "<li><b>Granite classification</b>: Frost, B.R., Barnes, C.G., Collins, W.J., Arculus, R.J., Ellis, D.J., Frost, C.D. (2001). A geochemical classification for granitic rocks. Journal of Petrology 42, 2033-2048.</li>"         "<li><b>Alumina saturation</b>: Shand, S.J. (1943). Eruptive Rocks, 2nd ed. Wiley, New York. Maniar, P.D., Piccoli, P.M. (1989). Tectonic discrimination of granitoids. Geological Society of America Bulletin 101, 635-643. Chappell, B.W., White, A.J.R. (1974). Two contrasting granite types. Pacific Geology 8, 173-174.</li>"         "<li><b>Thermobarometry</b>: Watson, E.B., Wark, D.A., Thomas, J.B. (2006) Contrib Mineral Petrol 151, 413-433. Ferry, J.M., Watson, E.B. (2007) Contrib Mineral Petrol 154, 429-437. Wark, D.A., Watson, E.B. (2006) Contrib Mineral Petrol 152, 743-754. Thomas, J.B. et al. (2010) Contrib Mineral Petrol 160, 743-759. Watson, E.B., Harrison, T.M. (1983) Earth Planet Sci Lett 64, 295-304. Boehnke, P. et al. (2013) Chem Geol 351, 324-334. Ferry, J.M., Spear, F.S. (1978) Contrib Mineral Petrol 66, 113-117. Ellis, D.J., Green, D.H. (1979) Contrib Mineral Petrol 71, 13-22. Hammarstrom, J.M., Zen, E. (1986) Am Mineral 71, 1297-1313. Hollister, L.S. et al. (1987) Am Mineral 72, 231-239. Johnson, M.C., Rutherford, M.J. (1989) Geology 17, 837-841. Schmidt, M.W. (1992) Contrib Mineral Petrol 110, 304-310. Mutch, E.J.F. et al. (2016) Contrib Mineral Petrol 171, 85. Brey, G.P., Kohler, T. (1990) J Petrol 31, 1353-1378. Holland, T., Blundy, J. (1994) Contrib Mineral Petrol 116, 433-447. Wells, P.R.A. (1977) Contrib Mineral Petrol 62, 129-139. Wood, B.J., Banno, S. (1973) Contrib Mineral Petrol 42, 109-124. Harley, S.L., Green, D.H. (1982) Nature 300, 697-701. Nickel, K.G., Green, D.H. (1985) Earth Planet Sci Lett 73, 158-170. Brey, G.P., Kohler, T., Nickel, K.G. (1990) J Petrol 31, 1313-1352. Putirka, K.D. (2008) Rev Mineral Geochem 69, 61-120. Putirka, K.D. et al. (2007) Chem Geol 241, 177-206. Beattie, P. (1993) Contrib Mineral Petrol 115, 103-111. Roeder, P.L., Emslie, R.F. (1970) Contrib Mineral Petrol 29, 275-289. Nimis, P., Taylor, W.R. (2000) Contrib Mineral Petrol 139, 541-554. Ghiorso, M.S., Evans, B.W. (2008) Am J Sci 308, 957-1039. Sack, R.O., Ghiorso, M.S. (1991a) Am Mineral 76, 827-847. Sack, R.O., Ghiorso, M.S. (1991b) Contrib Mineral Petrol 106, 474-505. Berman, R.G. (1988) J Petrol 29, 445-522. Lattard, D. et al. (2005) Contrib Mineral Petrol 149, 735-754. Evans, B.W., Scaillet, B., Kuehner, S.M. (2006) Contrib Mineral Petrol 152, 149-167. O'Neill, H.St.C., Pownceby, M.I. (1993) Contrib Mineral Petrol 114, 296-314. Frost, B.R. (1991) Rev Mineral 25, 1-9.</li>"         "<li><b>CIPW norm</b>: Cross, W., Iddings, J.P., Pirsson, L.V., Washington, H.S. (1902). A quantitative chemico-mineralogical classification and nomenclature of igneous rocks. Journal of Geology 10, 555-690. Middlemost, E.A.K. (1989). Iron oxidation ratios, norms and the classification of volcanic rocks. Chemical Geology 77, 19-26. Thornton, C.P., Tuttle, O.F. (1960). Chemistry of igneous rocks I. Differentiation index. American Journal of Science 258, 664-684.</li>"         "<li><b>Geochronology</b>: York, D., Evensen, N.M., Lopez Martinez, M., De Basabe Delgado, J. (2004) Am J Phys 72, 367-375. Cantrell, C.A. (2008) Atmos Chem Phys 8, 5477-5487. Jaffey, A.H. et al. (1971) Phys Rev C 4, 1889-1906. Hiess, J. et al. (2012) Science 335, 1610-1614. Villa, I.M. et al. (2015) Geochim Cosmochim Acta 164, 382-385. Lugmair, G.W., Marti, K. (1978) Earth Planet Sci Lett 39, 349-357. Soderlund, U. et al. (2004) Earth Planet Sci Lett 219, 311-324. Smoliar, M.I., Walker, R.J., Morgan, J.W. (1996) Science 271, 1099-1102. Wetherill, G.W. (1956) Trans Am Geophys Union 37, 320-326. Tera, F., Wasserburg, G.J. (1972) Earth Planet Sci Lett 14, 281-304. Rudemo, M. (1982) Scand J Stat 9, 65-78. Bowman, A.W. (1984) Biometrika 71, 353-360. Vermeesch, P. (2018) Geosci Front 9, 1479-1493. Ludwig, K.R. (1998) Geochim Cosmochim Acta 62, 665-676.</li>"         "<li><b>Basalt discrimination</b>: Pearce, J.A. (2008) Lithos 100, 14-48.</li>"         "<li><b>Spectroscopy</b>: Shirley, D.A. (1972) Phys Rev B 5, 4709-4714. Savitzky, A., Golay, M.J.E. (1964) Anal Chem 36, 1627-1639.</li>"         "<li><b>Harker diagrams</b>: Harker, A. (1909). The Natural History of Igneous Rocks. Methuen, London.</li>"         "<li><b>Granite discrimination</b>: Pearce, J.A., Harris, N.B.W., Tindle, A.G. (1984). Trace element discrimination diagrams for the tectonic interpretation of granitic rocks. Journal of Petrology 25, 956-983.</li>"         "<li><b>GCDkit</b>: Janou&#353;ek, V., Farrow, C.M., Erban, V. (2006). Interpretation of whole-rock geochemical data in igneous geochemistry: introducing Geochemical Data Toolkit (GCDkit). Journal of Petrology 47, 1255-1259.</li>"         "<li><b>Pyroxenes</b>: Morimoto, N. (1988). Nomenclature of pyroxenes. Mineralogical Magazine 52, 535-550.</li>" \
        "<li><b>Ultramafic rocks</b>: Le Maitre, R.W. (ed.) (2002). Igneous Rocks: A Classification and Glossary of Terms, 2nd ed. Cambridge University Press.</li>" \
        "<li><b>Fe3+ estimation</b>: Droop, G.T.R. (1987). A general equation for estimating Fe3+ concentrations in ferromagnesian silicates and oxides " \
        "from microprobe analyses, using stoichiometric criteria. Mineralogical Magazine 51, 431-435.</li><li><b>Soil texture</b>: Soil Science Division Staff (2017). Soil Survey Manual. USDA Handbook 18.</li><li>Field polygons and reference compositions as compiled " \
        "in pyrolite (Williams et al. 2020, Journal of Open Source Software 5, 2314), MIT License.</li></ul>"


# ------------------------------------------------------------------ the manual text
V = M.VERSION
CSS = """<style>
body { font-family: 'Segoe UI', Arial; font-size: 10.5pt; color: #222; }
h1 { color: #16325c; font-size: 22pt; } h2 { color: #16325c; font-size: 16pt; border-bottom: 1px solid #ccd; margin-top: 26px; }
h3 { color: #1f8f86; font-size: 13pt; margin-top: 18px; } h4 { color: #333; font-size: 11pt; margin: 10px 0 4px 0; }
table.ref { border-collapse: collapse; width: 100%; } table.ref td, table.ref th { border: 1px solid #d5d9e0; padding: 3px 6px; vertical-align: top; }
table.ref th { background: #eef2f7; } table.ex td { border: 1px solid #ccc; padding: 1px 6px; font-size: 9pt; }
table.plot { width: 100%; margin: 6px 0; border-bottom: 1px solid #e3e6ea; } .cap { color: #555; font-size: 9pt; text-align: center; }
.k { font-family: Consolas, monospace; color: #1f5f99; } code { font-family: Consolas, monospace; font-size: 9.5pt; color: #444; }
.note { background: #eef7f6; border: 1px solid #b9dcd8; padding: 6px; }
</style>"""

TOC = [("start", "1. Getting started"), ("window", "2. The main window"), ("sheets", "3. Worksheets and data"), ("import", "4. Importing and exporting data"),
       ("matrix", "5. Matrixbooks"), ("graphs", "6. Making graphs"), ("plotref", "7. Plot type reference"), ("editing", "8. Editing graphs"),
       ("export", "9. Exporting figures"), ("fitting", "10. Curve fitting"), ("spectro", "11. Spectroscopy and peaks"),
       ("math", "12. Mathematics and signal processing"), ("stats", "13. Statistics"), ("methods", "13b. Methods guide: equations, when to use, examples"),
       ("geochem", "14. Geochemistry"),
       ("projects", "15. Projects, layouts and reports"), ("scripting", "16. Python console and scripting"),
       ("examples", "17. Example data"), ("help", "18. Help, feedback and settings"), ("inside", "19. How PlotBench works inside"),
       ("menuref", "20. Menu reference"), ("keys", "21. Keyboard shortcuts"), ("refs", "22. References")]

H = [f"<html><head><meta charset='utf-8'><title>PlotBench User Manual</title>{CSS}</head><body>",
     f"<p align='center'><img src='../assets/banner.png' width='520'></p><h1 align='center'>PlotBench {V} User Manual</h1>",
     "<p align='center'>Worksheets, graphs, fitting and statistics for scientific data<br>Author: Kishan Tiwari (kishantiwari@iitkgp.ac.in)</p>",
     "<h2 id='contents'>Contents</h2><ol>" + "".join(f"<li><a href='#{a}'>{esc(t.split('. ', 1)[1])}</a></li>" for a, t in TOC) + "</ol>"]

H.append(f"""
<h2 id='start'>1. Getting started</h2>
<p>PlotBench is a desktop program for scientific data: you type or import data into worksheets, plot it in more than 60
graph types, fit curves and peaks, run statistics, and export publication figures. It runs on Windows without Python
or any other software installed.</p>
<h3 id='install'>Installing and sharing</h3>
<p>Run <b>PlotBench-{V}-Setup.exe</b>. It installs for the current user, so it does not need administrator rights, and adds
PlotBench to the Start menu. Double-clicking a <code>.pbp</code> project file opens it in PlotBench. To give PlotBench to a
colleague, send the Setup file only; it contains everything. A newer Setup installs over an older version.</p>
<h3 id='first'>Your first graph in five steps</h3>
<ol><li>Start PlotBench. The <b>Start page</b> opens with three choices: <b>Open an example</b> (a finished graph with its data),
<b>Import my data</b> (a wizard for CSV, text and Excel files) and <b>Start empty</b> (a blank worksheet). The other tabs hold
templates and recent projects. Until you make your first graph, the status bar says how to make one.</li>
<li>Type or paste your data, or use <b>File > Import</b> (or drag a file onto the window). For a quick try, use
<b>Help > Example Data</b>: each example opens with its data and a finished graph.</li>
<li>Tell PlotBench which column is X: right-click the column header and choose <b>Set as X</b>. Other columns are Y.</li>
<li>Select the Y columns (click their headers) and choose a plot from the <b>Plot</b> menu, the bottom toolbar or the
<b>Plot Gallery</b> (top toolbar), which shows a picture and a data guide for every type.</li>
<li>Style the graph with the <b>format bar</b> above it or <b>Graph > Graph Properties</b>, then export it with
<b>File > Export Graph / Layout</b>.</li></ol>
{S_START}
<p class='note'><b>Live preview.</b> Dialogs that change a graph (Graph Properties, reference lines, text, arrows, fitting,
the Peak Analyzer, Set Column Values and export) show each change straight away. <b>OK</b> keeps it, <b>Cancel</b> puts everything
back, and <b>Apply</b> keeps it while the dialog stays open. Untick <b>Live preview</b> in a dialog to turn it off.</p>
""")

H.append(f"""
<h2 id='window'>2. The main window</h2>
{S_MAIN}
<p>The window has a menu bar, four toolbars (top, left, bottom and right), the <b>Project Explorer</b> on the left and the work
area, where workbooks, matrixbooks, graphs, layouts and reports open as windows (tabbed or free: <b>Window > Toggle Tabbed / Free
windows</b>). The status bar at the bottom shows hints for the command under the mouse and the result of the last action.</p>
<h3>Toolbars</h3><p>Each toolbar can be moved by its handle, and switched on or off under <b>View > Toolbars</b>. The buttons are:</p>
{toolbar_reference()}
<h3>Project Explorer</h3><p>Lists every window of the project, grouped in folders. Double-click to bring a window forward;
right-click to rename, delete or move it into a folder. Renaming keeps graph links intact.</p>
<h3>Light and dark theme</h3><p>Switch with the switch on the top toolbar, <b>View > Dark Theme</b> or <b>Ctrl+Shift+D</b>. The choice
is remembered. Graphs keep their own background (set in Graph Properties) so exported figures look the same in both themes.</p>
""")

H.append(f"""
<h2 id='sheets'>3. Worksheets and data</h2>
{S_SHEET}
<h3>Layout of a sheet</h3>
<p>The first three grey rows hold the <b>Long Name</b>, <b>Units</b> and <b>Comments</b> of each column; long name and units become
the axis titles of graphs. The next row shows a <b>sparkline</b>, a tiny plot of the column. Data start below. A workbook can have
several sheets: right-click the sheet tabs at the bottom to add, rename, duplicate or delete a sheet (deleting asks first).</p>
<h3>Column roles</h3>
<p>Right-click a column header (or use the Column menu) to set its role, shown in the header as [X], [Y] and so on:</p>
<table class='ref'><tr><td><b>X</b></td><td>The horizontal axis. If a column set as X holds any text (e.g. sample names), it is used as labels.</td></tr>
<tr><td><b>Y</b></td><td>Values to plot or analyse.</td></tr><tr><td><b>Z</b></td><td>Third variable for contour and 3-D plots.</td></tr>
<tr><td><b>yErr</b></td><td>The error of the Y column to its left. Scatter and line plots draw error bars automatically, and fits can use it as weights.</td></tr>
<tr><td><b>yErr+ / yErr-</b></td><td>Asymmetric Y errors: the bar above and the bar below the point (e.g. 10th-90th percentiles).</td></tr>
<tr><td><b>xErr</b></td><td>The error of the X values, drawn as horizontal bars.</td></tr>
<tr><td><b>Label</b></td><td>Text such as sample names or groups; used by the colour-map dialog for groups and labels.</td></tr>
<tr><td><b>Ignore</b></td><td>Left out of plots.</td></tr></table>
<h3>Editing</h3>
<p>Type in a cell and press Enter (down) or Tab (right). The cell editor and Ctrl+C always use the full stored value, even though
the sheet shows 6 significant digits (change this in Preferences). Paste (Ctrl+V) takes tab-separated text from Excel, Origin or
another sheet and adds rows and columns as needed; commas stay inside a cell, so decimal commas and text are safe. Undo and redo
(Ctrl+Z, Ctrl+Y) cover every change. Excel-style keys work: Ctrl+Arrow jumps to the edge of the data, Shift extends the selection,
Ctrl+D and Ctrl+R fill down and right, Ctrl+; inserts today's date (see <a href='#keys'>Keyboard shortcuts</a>).</p>
<h3>Masking</h3><p>Select cells and press <b>Ctrl+M</b> to mask them: they turn red, appear as red crosses on graphs and are left
out of every analysis, but stay in the sheet. Unmask with Column > Unmask.</p>
<h3 id='formulas'>Column formulas</h3>
{S_FORMULA}
<p><b>Column > Set Column Values</b> (Ctrl+Q) fills a column from a formula of other columns, for example <code>A*2 + sin(B)</code>,
<code>log10(Sr/Y)</code>, <code>where(SiO2 > 63, 'Felsic', 'Mafic')</code> (text results are allowed) or <code>eu_anomaly(Eu, Sm, Gd)</code>.
The dialog shows the first rows of the result while you type, and any error in red. Formula columns recalculate when their inputs
change, in dependency order (a formula may use another formula column; a circular reference is reported). Use column names as
they appear in the header; <code>i</code> is the row number.</p>
{formula_functions()}
<p><b>Geochemical anomalies:</b> <code>eu_anomaly(Eu, Sm, Gd)</code> gives Eu/Eu* = Eu<sub>N</sub>/&radic;(Sm<sub>N</sub>&middot;Gd<sub>N</sub>) and
<code>ce_anomaly(Ce, La, Pr)</code> gives Ce/Ce* = Ce<sub>N</sub>/&radic;(La<sub>N</sub>&middot;Pr<sub>N</sub>), with N = CI chondrite
normalised (McDonough &amp; Sun 1995); inputs in ppm.</p>
<p class='note'><b>How formulas are kept safe.</b> A formula is parsed, and only arithmetic, comparisons, column names and the
functions listed above are accepted; attributes, imports, indexing and other Python are refused before anything runs. This is
what lets you open project files from others without risk.</p>
<h3>Worksheet tools</h3><p>The Worksheet menu holds transpose, stack and unstack, pivot table, remove duplicates, extract rows by
a condition (e.g. <code>SiO2 > 45 and Class == "iron"</code>), split by a column's values, join sheets on a key, find and replace,
multi-column sort, reduce rows, fill missing values, fill a sequence, row statistics, frequency counts and colouring cells by value.</p>
""")

H.append(f"""
<h2 id='import'>4. Importing and exporting data</h2>
{S_IMPORT}
<p><b>File > Import Wizard (text files)</b> reads text files (CSV, TXT, DAT, TSV) with control over the delimiter, lines to skip, the lines that
hold column names, units and comments, decimal comma and comment character, with a live preview. Data can go into a new workbook,
a new sheet or the active sheet. Other formats: Excel (every sheet), HDF5 and NetCDF (pick arrays from a tree), MATLAB .mat (v5 and
v7.3), JCAMP-DX spectra (including compressed forms) and SQLite databases (a table or your own SQL query, opened read-only).
Drag a file onto the window to import it. Worksheets export to CSV and Excel.</p>
""")

H.append("""
<h2 id='matrix'>5. Matrixbooks</h2>
<p>A matrixbook holds grids of Z values with X and Y coordinates (images, maps, gridded surfaces). Create one with <b>Matrix > New
Matrixbook</b>, import an image (PNG, JPG, TIFF, BMP), convert scattered XYZ data with <b>Matrix > Convert Worksheet XYZ to Matrix (gridding)</b> (linear, cubic,
nearest, Shepard or thin-plate spline), or fill it from a formula in x, y, i and j. Matrix tools: transpose, flip, rotate, inverse,
resample, smoothing (Gaussian, median, mean), 2-D FFT, row and column profiles, statistics, crop, arithmetic between matrices,
and image filters (edges, Laplacian, threshold, invert, log, normalise, gradient). Matrix plots are image/heat map, filled
contour, contour lines, 3-D colour-map surface and wireframe.</p>
""")

H.append(f"""
<h2 id='graphs'>6. Making graphs</h2>
<p>Select the Y columns of a sheet (or nothing, to use every Y column) and choose a plot type from the <b>Plot</b> menu, the bottom
toolbar or the <b>Plot Gallery</b>. The X column is the one set as X; without one, the row number is used.</p>
{S_GALLERY}
<p>The gallery groups the plot types by purpose. Click a thumbnail to read what it shows and how to lay out the data (with an
example table); double-click or press <b>Plot</b> to draw it from your selection, or <b>Open example data for this plot</b> to see it
with ready-made data. Type in the search box to find a type by name or column role.</p>
<h3>Colour-mapped plots (three variables in two dimensions)</h3>
{S_CMAP}
<p>Colour-mapped scatter, bubble + colour, colour-mapped line and ternary + colour open a dialog with a live preview. Choose X, Y
and the colour column; optionally a <b>group</b> column (a different symbol per group, with a legend), a <b>label</b> column (text next
to each point) and a <b>size</b> column. Set the colour map (with a gradient preview), reverse it, fix its range or use a log scale,
split it into discrete bands, choose the colour bar position and title, and the symbol size, edge and transparency. <b>Edit plot...</b>
on the format bar reopens this dialog later.</p>
<h3>Edit plot, panels and single points</h3>
<p><b>Edit plot...</b> on the format bar above every graph (also <b>Graph > Edit Plot</b>, Ctrl+Shift+E) changes the plot type, the X and
Y columns, the sample groups and the panels, with live preview: OK keeps the change as one undo step, Cancel puts the graph back.
Colour-mapped graphs open their colour-map builder instead.</p>
<p><b>Panels</b>: tick <i>One panel per Y column</i> (or use <b>Graph > Split into Panels</b>) to draw each Y column as its own small graph
on the same page, in the number of rows and columns you choose (0 = automatic), like the Harker diagrams. To put different graphs on one
page, use <b>Graph > New Layout Page</b>; double-click a panel of a layout page to open its graph, and every change there shows on the
page. In multi-panel graphs the format bar's curve list names each curve with its panel, so every panel's curves can be styled on their
own.</p>
<p><b>Moving and layering texts.</b> Every text a plot draws (field names such as <i>Basaltic Andesite</i>, labels, captions) can be
dragged with the mouse to a free spot; the new place is saved with the graph and kept when the data change (Ctrl+Z undoes a move).
Right-click a text to edit its words, font size or colour, to put it in front of the data points, between the field lines and the points,
or behind everything, to hide it, or to reset it. Right-click empty space to show hidden texts again or reset all of them. Right-click a
data point and choose <i>Bring this curve to front</i> or <i>Send this curve to back</i> to change the layer of a whole curve or group.</p>
<p><b>Sample groups</b>: double-click a group's name in the legend of a geochemistry diagram to change its colour, symbol, size and
the name shown in the legend, with live preview.</p>
<p>Live preview with OK, Apply and Cancel is also in Graph Properties, Apply Template, Group Samples By Column, Split into Panels and
Add Inset Graph.</p>
<p><b>Single points</b>: right-click a data point to give just that point its own colour, symbol or size, label it with its value, or hide
it; <i>Reset this point</i> and <i>Reset all points</i> undo that. Point formats are saved with the graph and follow templates.</p>
<h3>Cell formulas and the formula bar</h3>
<p>Type <b>=</b> in any data cell to calculate it as in Excel: <code>=A1/B1</code>, <code>=A2-B2</code>, <code>=A1*2+C3^2</code>,
<code>=SUM(B1:B10)</code>, <code>=AVERAGE(C:C)</code> (a whole column), <code>=IF(D2&gt;5, "high", "low")</code>,
<code>=COUNTIF(E1:E20, "Olivine")</code>, <code>=B2&amp;" ppm"</code> (joins text). Columns are referred to by their letter, which is shown
in front of the column name in the header (<i>B | SiO2</i>), and rows by their number; $ signs are accepted. Blank cells count as 0 in
arithmetic and are skipped by SUM, AVERAGE and the other statistics. Errors show in red, as in Excel: #DIV/0!, #NAME? (unknown function),
#REF! (no such cell), #VALUE!, #NUM! and #CIRC! (formulas that refer to each other in a circle). Formula cells are blue; their results
update whenever a cell they read changes, and they move with their rows when you sort, insert or delete rows. Inserting a column (right-click a header,
<b>Insert column before</b>) or deleting one moves the letters in existing formulas along, as in Excel; a reference to a deleted column
becomes #REF!.</p>
<p><b>Other sheets.</b> A formula can read another sheet of the same workbook: <code>=Sheet2!A1</code>,
<code>=SUM(Sheet2!B2:B20)</code>, <code>=AVERAGE(Data!C:C)</code>; put names with spaces or other characters in single quotes:
<code>='Raw data'!B2</code>. Sheet names are matched in any case. The formula updates when the other sheet changes; renaming the sheet
renames it in the formulas; a missing sheet gives #REF!. Inserting or deleting rows or columns, on the formula's sheet or on the sheet it
reads, moves the references along (as in Excel); the fill handle moves them too. Inserting or deleting rows also moves row numbers:
<code>=A5</code> becomes <code>=A6</code> when a row goes in above row 5.</p>
<p><b>Fill handle.</b> The small green square at the bottom-right corner of the selection works as in Excel: drag it down (or up,
right, left) to fill. A formula is copied with its references moved: <code>=A1*B1</code> in row 1 becomes <code>=A2*B2</code> in row 2.
Put $ in front of the part that must not move: <code>$A1</code> keeps the column, <code>A$1</code> the row, <code>$A$1</code> both
(e.g. <code>=A1/$B$1</code> divides every row by the same cell). Two or more numbers selected together continue as a straight-line
series (1, 2 gives 3, 4, 5 ...; 10, 20 gives 30, 40 ...); a single number is copied; text ending in a number counts on (Sample 1,
Sample 2 ...; S-009, S-010 keeps the zeros); other text is repeated. A reference pushed off the sheet becomes #REF!. The whole fill is one
undo step. <b>Ctrl+D</b> (fill down) and <b>Ctrl+R</b> (fill right) copy the first row or column of the selection the same way, without
series. Columns calculated by a column formula (Set Column Values) are left alone.</p>
<p><b>Double-click the fill handle</b> to fill down as far as the column beside the selection has data, as in Excel (useful for
long microprobe or LA-ICP-MS tables). <b>Copy and paste</b> moves the relative references of pasted formulas by the distance pasted, as in
Excel; references with $ stay. A duplicated sheet keeps its cell formulas; deleting a sheet turns formulas that read it into #REF!.</p>
<p><b>Typing formulas.</b> After =, a list of matching functions (and the names of the other sheets) pops up in the formula bar; Enter or a
click puts the name in with its opening bracket. <b>Lookups</b> join tables: <code>=VLOOKUP(A2, Standards!A1:D40, 3, FALSE)</code> finds A2
in the first column of the table and returns the third column of that row (FALSE = exact match; TRUE or left out = the largest value not
above A2, data sorted ascending); <code>=XLOOKUP(A2, Spots!A1:A500, Spots!F1:F500, "none")</code> looks in one range and returns from
another; <code>=INDEX(B1:D9, 3, 2)</code> and <code>=MATCH("Ol*", C1:C9, 0)</code> (text ignores case; * and ? are wildcards).
<code>=SUMIFS(B1:B99, C1:C99, "Olivine", D1:D99, "&gt;40")</code> adds the B values of rows that meet every condition; COUNTIFS,
AVERAGEIFS, MAXIFS and MINIFS work the same way. A value that is not found gives #N/A (wrap it in IFERROR to show something else).</p>
<p>Functions: SUM, AVERAGE (AVG, MEAN), MIN, MAX, COUNT, COUNTA, COUNTBLANK, PRODUCT, MEDIAN, MODE, STDEV (STDEV.S), STDEVP (STDEV.P),
VAR, VARP, GEOMEAN, HARMEAN, SUMSQ, SUMPRODUCT, LARGE, SMALL, PERCENTILE, QUARTILE, COUNTIF, SUMIF, AVERAGEIF, ABS, SQRT, EXP, LN, LOG,
LOG10, POWER, MOD, INT, TRUNC, ROUND, ROUNDUP, ROUNDDOWN, SIGN, FACT, PI, SIN, COS, TAN, ASIN, ACOS, ATAN, ATAN2, SINH, COSH, TANH,
DEGREES, RADIANS, IF (only the branch chosen is calculated, so =IF(B1=0, 0, A1/B1) gives 0), IFERROR, AND, OR, NOT, ISBLANK, ISNUMBER, ISTEXT, CONCAT, LEN, UPPER, LOWER, TRIM, LEFT, RIGHT, VALUE, TEXT, the lookups VLOOKUP, HLOOKUP, XLOOKUP, INDEX and MATCH, and SUMIFS, COUNTIFS, AVERAGEIFS, MAXIFS, MINIFS and IQR;
operators + - * / ^ &amp; = &lt;&gt; &lt; &gt; &lt;= &gt;= and percentages (50%).</p>
<p>The <b>formula bar</b> above each sheet shows the cell address, the cell's formula (or value) and, on the right, what lies behind
the cell: its result, its column formula (<b>Set Column Values</b>), or for columns made by a command, how they were calculated
(for example <i>Mg# = 100 Mg / (Mg + Fe2+)</i> or <i>made by Smooth</i>). Type in the bar and press Enter to change the cell. Hovering
over a column header shows the same information.</p>
<h3>Typing numbers</h3>
<p>Wherever a value is typed (axis limits in Graph Properties, digitizer calibration values), it can be written as 2400, 0.5, 1e-18,
1E-18, 10^-18, 10^(-18), 10**-18, 10&#8315;&#185;&#8312;, 2.5x10^3, 2.5&times;10^3, 1,5 (decimal comma), 1/3 or 50%.</p>
<h3>Digitizer</h3>
<p><b>Tools &gt; Digitizer</b> reads data off a picture of a graph. Open the image, then make the four calibration clicks (two labelled
ticks on X, two on Y), typing each tick's value (10^-18 and the other forms above work). The <b>magnifier</b> beside the image shows the
area under the mouse eight times larger with a red cross at the exact pixel a click will use, and below it the pixel position and, once
calibrated, the X and Y values. When two values on one axis are three or more decades apart, the digitizer asks whether the axis is
logarithmic. Switch the toolbar's zoom or pan off before clicking points. Then click the data points; OK puts them in a new worksheet and a
scatter graph (with log axes if you ticked them), which is brought to the front. OK without any data points asks before closing.</p>
<h3>Drag columns onto a graph</h3><p>As in Origin: select whole columns in a worksheet (click the column headers), then press inside
the selection and drag it onto a graph window. Columns from the graph's own sheet with the same X become more series of that plot; columns
from another sheet (or with another X) are overlaid as extra curves. Dropping on empty workspace makes a new Line + Symbol graph.
Each drop is one undo step (Ctrl+Z in the graph).</p>
<h3>Plotting from the sheet</h3><p>The <b>Plot</b> row above every worksheet draws the selected columns in one click: Scatter, Line,
Line + Symbol, Column, Histogram or Box. With nothing selected it plots all Y columns. <b>More...</b> opens the Plot Gallery; there,
plot types that need more columns than you selected are grey, and the note under the pictures says how many they need.</p>
<h3>Statistics of a selection</h3><p>Select cells or columns: the right end of the status bar shows the count, mean, standard
deviation, sum, minimum and maximum of the numbers in the selection.</p>
<h3>Filtering rows</h3><p>Right-click a column header and choose <b>Filter rows...</b>, then type a condition, for example
<code>SiO2 &gt; 45</code> or <code>Rock == "basalt"</code> or <code>MgO &gt; 5 and MgO &lt; 12</code>. Rows that fail are masked (shown
in red), not deleted: they leave every graph and analysis of the sheet. The Plot row shows the filter and how many rows it keeps;
<b>Clear</b> there, or <b>Clear filter</b> in the header menu, brings all rows back. A second filter is added to the first. The filter
is saved with the project and follows the data when values change.</p>
<h3>Format an axis or the legend by clicking it</h3><p>Click an axis (its numbers, or just outside the plot beside it): the format
row above the graph shows <b>From</b>, <b>To</b>, <b>Auto range</b>, <b>Scale</b> (linear or log), <b>Grid</b>, <b>Minor ticks</b>,
<b>Ticks inside</b>, <b>Ticks all round</b> and <b>Number font...</b>. Click the legend for <b>Show</b>, <b>Position</b>,
<b>Frame</b> and <b>Forget dragged position</b>. <b>More options...</b> opens Graph Properties; <b>Done</b>, or a click inside the
plot, returns to the curve format row. Every change is one undo step. Double-click the numbers of an axis to format their font.</p>
<h3>The Objects list</h3><p>The <b>Objects</b> section of the graph side panel lists everything drawn or added on the graph (shapes,
texts, reference lines, arrows, added data). Untick an object to hide it, press <b>Edit</b> to reshape a shape with its handles, or
<b>x</b> to delete it.</p>
<h3>Copy and paste a graph's format</h3><p><b>Graph > Copy / Paste Format > Copy Format</b> remembers the look of the active graph.
In another graph choose <b>Paste Format (everything)</b>, <b>Paste Colours Only</b> or <b>Paste Fonts Only</b>. Titles, axis ranges
and the settings of single curves are not changed.</p>
<h3>Results that follow the data</h3><p>A column made by <b>Thermobarometry</b> is recalculated, with its calibration-range column,
whenever its input values change; such columns carry the mark &#8635; in their header. A Monte Carlo uncertainty column is not
redrawn automatically: run the method again for a new one. Long Monte Carlo runs show a progress window with <b>Cancel</b>.</p>
<h3>Recovery after a crash</h3><p>Every three minutes PlotBench writes unsaved work to a recovery copy in its settings folder (never
over your project file). It is deleted when you save or exit normally. If PlotBench did not close normally, the next start offers to
open the recovered work as an unsaved project. When several PlotBench windows run at once, only the first keeps a recovery copy.</p>
<h3>Quick tour</h3><p><b>Help > Quick Tour (one minute)</b>, also on the Start page, shows five short notes, each beside the part of
the window it describes.</p>
<h3>Layers: more data with its own axes</h3><p><b>Graph > Layers (more data with its own axes)...</b> (also under Arrange in the
graph side panel) opens the layer manager. <b>Add layer...</b> asks where the data is (any worksheet), the X column and the Y columns,
how to draw them (line, scatter, line + symbol, step, column) and which axes to use: <b>its own Y axis on the right</b>, <b>its own
X axis on the top</b>, both, or the graph's axes. An axis of its own has its own title, range and linear or log scale, and is drawn
in the colour of its first curve; a second right axis stands further out. Layer curves appear in the graph's legend and in the
format row's curve list, so they are formatted like any other curve. In the manager, untick a layer to hide it, or edit, reorder
and remove layers; OK keeps everything as one undo step and Cancel puts the graph back. The graph redraws when a layer's sheet
changes. Layers are for X-Y graphs.</p>
<h3>One undo history</h3><p><b>Edit > Undo</b> (Ctrl+Z from the menu or toolbar) goes back through the changes in the order they
were made, in whichever sheet, matrix or graph each was made, and brings that window to the front; the status bar names it.
<b>Redo</b> goes forward the same way.</p>
<h3>Send graphs to Word or PowerPoint</h3><p><b>File > Send to Word / PowerPoint</b> writes the active graph, or every graph and
layout, into a new Word document (one per page, with the window name as caption) or a PowerPoint presentation (one per slide, with
the name as title) at 300 dpi, and opens it. Word or PowerPoint need not be installed to write the file.</p>
<h3>Export presets</h3><p>In the export dialog, <b>Save as preset...</b> stores the resolution, size, unit, transparency and
editable-text switches under a name; choose the name in <b>Preset</b> later to fill them all in. <b>Delete</b> removes the chosen
preset.</p>
<h3>Copy analyses to other sheets</h3><p><b>Worksheet > Copy Analyses to Other Sheets...</b> repeats the active sheet's column
formulas and thermobarometry columns in the sheets you tick. A calculation is skipped in a sheet that lacks its input columns.</p>
<h3>Large files</h3><p>Reading a text file larger than 5 MB (Import Wizard or Quick Import) shows a progress window with
<b>Cancel</b>; a cancelled import adds nothing.</p>
<h3>Commands and the window in front</h3><p>A graph command chosen while a worksheet is in front goes to the graph you used last,
which comes to the front; a worksheet command chosen while a graph is in front goes to the worksheet used last. When there is no
such window at all, the message offers the next step (New workbook, Open an example, Open the Plot Gallery).</p>
<h3>Simple menus</h3><p>A new installation starts with <b>View > Simple Menus</b> ticked: about 120 rarely used commands (the
Matrix menu, advanced statistics, signal processing, special imports and exports) are left out of the menus, so the common ones are
easy to find. Nothing is removed: <b>Search Commands</b> (Ctrl+K) still finds and runs every command, and each shortened menu ends in
<b>Show all commands</b>, which switches the full menus back on. Keyboard shortcuts work in both modes.</p>
<h3>Finding a command</h3><p><b>Help > Search Commands</b> (Ctrl+Shift+F) finds any menu command from what you type, including words
that are not in the menu text: for example <i>deconvolution</i> finds the Peak Analyzer. Enter runs the highlighted command. In the
manual window, type in the search box: every match is highlighted, Enter goes to the next and Shift+Enter to the previous.</p>
<h3>Error bars</h3><p>Set a column as <b>yErr</b> right after its Y column. Scatter, line, line + symbol and step plots then draw
error bars automatically. The Error Bar and Column + Error Bars types take explicit value/error column pairs.
For asymmetric bars set the columns after the Y column as <b>yErr+</b> (above) and <b>yErr-</b> (below); a side that is not given uses
yErr, or nothing. A column set as <b>xErr</b> adds horizontal bars. All of them belong to the Y column on their left, up to the next X or Y
column, and are not plotted as curves.</p>
""")

H.append(f"<h2 id='plotref'>7. Plot type reference</h2><p>Every plot type, what it shows and how to prepare the data.</p>{plot_reference()}")

H.append(f"""
<h2 id='editing'>8. Editing graphs</h2>
{S_GRAPH}
<h3>Format bar</h3>{S_FMT}
<p>Above every graph. Pick a curve (or All series), then set its colour (swatches or any colour), line width, line style, symbol,
symbol size and hollow symbols; switch log X or log Y, grid, legend, and the font. <b>Edit plot...</b> reopens the set-up dialog
of colour-mapped plots; <b>Reset</b> removes the format-bar changes. Every change can be undone with Ctrl+Z.</p>
<h3>Graph Properties (live preview)</h3>{S_STYLE}
<p><b>Graph > Graph Properties</b> has four tabs: <b>Titles &amp; legend</b> (title, axis titles, legend position and frame),
<b>Axes</b> (linear, log, symlog or logit scales, axis ranges, tick direction, ticks on all sides, minor ticks, grid), <b>Lines &amp; colours</b>
(palette, colour map, line width and style, symbol and size, background) and <b>Fonts &amp; size</b> (font, font size, export size
and DPI). Changes show on the graph as you make them.</p>
<h3>Double-click to edit</h3><p>Double-click a <b>text or arrow</b> to edit its text, a <b>curve</b> to select it in the format bar,
the <b>title, an axis title or the legend</b> to open Graph Properties at the titles tab, and the <b>axes or tick labels</b> to open it at
the axes tab.</p>
<h3>Moving things with the mouse</h3><p>Drag the <b>legend</b>, a <b>text</b> label or an <b>arrow</b> to a new place. The position is
saved in the graph and Ctrl+Z puts it back. A legend that was dragged stays there until you choose another legend position in
Graph Properties.</p>
<h3>Annotations</h3><p><b>Graph > Annotations</b> adds reference lines (horizontal or vertical, with a label), text, arrows,
confidence ellipses, and data from other sheets in the same graph. The dialogs start in the middle of the current axes and show the
item on the graph while you set it.</p>
<h3>Navigation and tools</h3><p>The toolbar above each graph pans and zooms (and Home resets). <b>Data reader</b>: click near a
point to read its X, Y and row. <b>Region tools</b>: drag across an X range for a quick fit, statistics, area, FFT, peaks or to mask
that range.</p>
<h3>Templates, themes, insets and layouts</h3><p>Save the look of a graph as a template and apply it to others; six built-in
themes are included and one can be the default for new graphs. <b>Graph > Add Inset Graph</b> draws another graph in a corner.
<b>Graph > New Layout Page</b> arranges several graphs on one page with (a), (b) ... labels for multi-panel figures.</p>
<p><b>Zoom insets.</b> <b>Graph > Add Zoom Inset</b>, then drag a rectangle around a crowded part of the graph: a magnified copy of that
region appears in the opposite corner, joined to it by connector lines (Undo removes it; <b>Remove Insets and Zoom Insets</b> removes
all). <b>Axis breaks.</b> In Graph Properties > Axes, type two values in <b>Y axis break</b> (or X) such as <code>20, 80</code>: the range
between them is left out and the axis is drawn in two parts joined by // marks, for data with a few very large values.
<b>Graph > Repeat Graph for Every Sheet</b> makes the same graph, with the same format, for every other sheet of the workbook that has
the same columns. <b>File > Export All Graphs to One Multi-page PDF</b> writes every graph and layout as a page of one PDF, each at its
own export size.</p>
<p><b>Graph shape and the shortcut panel.</b> A graph window keeps the shape of the exported figure (Graph Properties &gt; Fonts &amp; size &gt;
<i>Shape on screen</i>: same as export size, 4:3, 1:1, 3:2, 16:9 or fill the window), so plots are not stretched by a wide window. The spare
width on the right holds a panel of shortcuts for the graph (format, add, arrange, analyse, output), in as many columns as fit.
<b>Copy Format to All Graphs</b> gives every other graph the active graph's fonts, sizes and colours. Every dialog with live preview
(Edit Plot, Graph Properties, group styles, annotations, insets, templates) shows a copy of the graph inside the dialog, so you see each
change even when the dialog covers the graph window.</p>
""")

H.append(f"""
<h2 id='export'>9. Exporting figures</h2>
{S_EXPORT}
<p><b>File > Export Graph / Layout</b> saves PNG, TIFF, JPEG, SVG, PDF or EPS. The dialog sets:</p>
<ul><li><b>Journal size</b>: column widths of Elsevier (90, 140, 190 mm), Springer (84, 174 mm), Nature (89, 183 mm) and Wiley/AGU
(85, 178 mm). The height keeps the graph's shape.</li>
<li><b>Resolution</b>: presets from 72 to 1200 dpi or any value from 10 to 4800; stored in PNG, TIFF and JPEG files so Word and
journals see the right print size.</li><li><b>Size</b> in inches, cm or mm, with the pixel size shown.</li>
<li><b>Transparent background</b> (not for JPEG).</li>
<li><b>Editable text in PDF / EPS / SVG</b>: text is stored as text with embedded TrueType fonts, so labels stay editable in
Illustrator or Inkscape.</li></ul>
<p>The preview shows the figure at the exported size with the real text size; a warning appears if any text is below 6 pt, the
minimum most journals accept. <b>File > Export All Graphs and Layouts</b> saves every graph at once; <b>Edit > Copy Graph to Clipboard</b> puts it on the
clipboard for Word or PowerPoint.</p>
""")

H.append(f"""
<h2 id='fitting'>10. Curve fitting</h2>
{S_FIT}
<p><b>Analysis > Fitting</b> holds linear and polynomial fits, the nonlinear fit (Ctrl+F), user-defined functions, multiple-peak
fits, surface fits z = f(x, y), orthogonal distance regression (errors in X and Y), global fits with shared parameters, and batch
fits of many columns.</p>
<h3>The fit dialog</h3><ul>
<li><b>Function</b>: one of {len(A.MODELS)} built-in models (table below) or <b>User-defined</b>: type <code>y = </code> a formula in x and
your parameter names.</li>
<li><b>Parameters</b>: initial value, <b>Fixed</b> (held constant), lower and upper bounds. <b>Re-guess</b> recomputes initial values from
the data; <b>Use fitted values as initial</b> copies the result into the table.</li>
<li><b>Weighting</b> by an error column (1/&sigma;<sup>2</sup>); parameter errors then use the given errors as absolute.</li>
<li><b>Fit X range</b> to fit part of the data.</li>
<li>Outputs: 95% confidence and prediction bands, a residual plot, fitted and residual columns, and a parameter table pasted on
the graph (a draggable text box). <b>Recalculate automatically</b> re-runs the fit when the data change.</li></ul>
<p>The right side shows the data, the initial-guess curve (orange, dashed), the fit (red) and the residuals, updated a moment after
every change, with R&sup2;, reduced &chi;&sup2; and the parameters.</p>
<h3>How the fit is computed</h3><p>Nonlinear least squares with SciPy <code>curve_fit</code> (trust-region reflective when bounds are
set, Levenberg-Marquardt otherwise). Fixed parameters are removed from the problem. Standard errors are the square roots of the
covariance diagonal, scaled by the reduced &chi;&sup2; unless the fit is weighted; t, p and 95% limits use the residual degrees of
freedom. R&sup2; = 1 - SS<sub>res</sub>/SS<sub>tot</sub>; reduced &chi;&sup2; = SS<sub>res</sub>/(n - p). Confidence bands use the delta method;
prediction bands add the residual variance.</p>
<h3>Built-in models</h3>{fit_models()}
""")

H.append(f"""
<h2 id='spectro'>11. Spectroscopy and peaks</h2>
{S_PEAK}
<p><b>Peak fitting and deconvolution.</b> To separate overlapping peaks (deconvolution of Raman, FTIR, XRD or XPS bands), use
<b>Analysis > Spectroscopy > Peak Fitting / Deconvolution (Peak Analyzer)</b> (also <b>Analysis > Peak Analyzer</b>, Ctrl+Shift+K).
Each fitted peak is reported with its centre, height, FWHM and area, and the components are drawn under the fit.</p>
<p><b>Analysis > Spectroscopy > Peak Analyzer</b> works in four steps: choose a baseline (none, constant, straight line between the
end points, or asymmetric least squares), find peaks automatically or click the graph to add them (right-click removes the nearest),
set each peak's shape (Gaussian, Lorentzian, pseudo-Voigt or Voigt), whether its centre is fixed, its centre limits, and optionally a
starting width that can be fixed, then fit. For a baseline through chosen points, pick <b>Anchor points</b> and Shift+click the spectrum
where there is no peak (Shift+right-click removes one); each anchor takes the median of the five nearest data points, joined by a
smooth shape-preserving curve or straight segments.
With <b>Fit while I edit</b> the fit updates after every change. The report gives centre, height, FWHM, area and area % for each peak,
and adds baseline, fit and component columns to the sheet, plus a separate sheet listing every peak (shape, centre, height, FWHM,
area and area %).</p>
<p><b>Asymmetric least squares baseline</b> (Eilers &amp; Boelens 2005): a smooth curve z minimises
&Sigma; w<sub>i</sub>(y<sub>i</sub> - z<sub>i</sub>)&sup2; + &lambda; &Sigma; (&Delta;&sup2;z<sub>i</sub>)&sup2;, with weights p for points above z and 1 - p below, iterated ten times;
&lambda; sets the smoothness and p the asymmetry. It uses sparse matrices, so long spectra are fast.</p>
<p><b>Shirley background</b> (XPS; Shirley 1972): in the Peak Analyzer's Baseline list, or <b>Analysis > Spectroscopy > Shirley
Background</b>. The background rises from the intensity at one end of the region to the intensity at the other in proportion to the
peak area lying beyond each point, recalculated until it settles. Choose the region (the X range of the sheet) so that both ends are on
flat background. Checked by building a peak on a known Shirley step and recovering the step to 0.05 counts in 100.</p>
""")

H.append("""
<h2 id='math'>12. Mathematics and signal processing</h2>
<p><b>Analysis > Mathematics</b>: differentiate, integrate (cumulative and area), interpolate (linear, quadratic, cubic), normalise,
average curves, subtract a line or a reference curve, curve intersections, X at a given Y, rise time and polygon area. <b>Derivative (Savitzky-Golay)</b> gives the first to fourth derivative from a local polynomial (Savitzky &amp; Golay 1964), which brings out hidden shoulders before peak fitting; unevenly spaced data are put on an even grid first.
<b>Analysis > Signal Processing</b>: Savitzky-Golay, adjacent-average and median smoothing; FFT; FFT low-pass filter; IIR
(Butterworth, Chebyshev, Bessel, elliptic) and FIR filter design with zero-phase filtering; spectrogram; continuous wavelet
scalogram, wavelet denoising and decomposition; correlation and convolution; Hilbert envelope; coherence. Each command is
listed with a description in the <a href='#menuref'>Menu reference</a>.</p>
""")

H.append(f"""
<h2 id='stats'>13. Statistics</h2>
<table width='100%'><tr><td valign='top'>{S_MSTAT}</td><td valign='top'>
<p>The Statistics menu is grouped by the question you are asking. Hover over a command to see when to use it.</p>
<ul><li><b>Describe</b>: descriptive statistics, correlation, normality and distribution fits, outliers.</li>
<li><b>Compare two groups</b>: t-tests (one-sample, two-sample Student or Welch, paired) or the nonparametric Mann-Whitney and Wilcoxon tests.</li>
<li><b>Compare several groups</b>: one- and two-way ANOVA, ANCOVA, repeated-measures and mixed-design ANOVA, Kruskal-Wallis and Dunn.</li>
<li><b>Counts, proportions and variances</b>: chi-square, Fisher exact, McNemar, proportion tests, F and chi-square variance tests.</li>
<li><b>Regression and models</b>: logistic, generalised linear models, PLS, linear and generalised linear mixed models.</li>
<li><b>Multivariate</b>: PCA, MANOVA, MANCOVA, discriminant analysis (LDA, QDA), k-means and hierarchical clustering.</li>
<li><b>Survival and diagnostics</b>: Kaplan-Meier, Cox regression, ROC curves, Bland-Altman, Cronbach's alpha.</li>
<li><b>Power and sample size</b>.</li></ul></td></tr></table>
<h3>Choosing a test</h3>
<table class='ref'><tr><th>Your question</th><th>Data layout</th><th>Use</th></tr>
<tr><td>Is the mean different from a value?</td><td>One column</td><td>One-sample t-test</td></tr>
<tr><td>Do two independent groups differ?</td><td>Two columns</td><td>Two-sample t-test (normal) or Mann-Whitney</td></tr>
<tr><td>Did the same samples change?</td><td>Two columns, paired by row</td><td>Paired t-test or Wilcoxon</td></tr>
<tr><td>Do three or more groups differ?</td><td>One column per group</td><td>One-way ANOVA (+ Tukey) or Kruskal-Wallis (+ Dunn)</td></tr>
<tr><td>Two factors?</td><td>Long format: factor columns + value</td><td>Two-way ANOVA</td></tr>
<tr><td>Repeated measurements of subjects?</td><td>Long format: subject, time, value</td><td>Repeated-measures ANOVA or a linear mixed model</td></tr>
<tr><td>Are two variables related?</td><td>Two columns</td><td>Correlation, linear fit</td></tr>
<tr><td>Are two categorical variables related?</td><td>Two text columns or a table</td><td>Chi-square or Fisher exact</td></tr>
<tr><td>Which samples group together?</td><td>One row per sample</td><td>PCA, clustering, discriminant analysis</td></tr>
<tr><td>Do two methods agree?</td><td>Two columns</td><td>Bland-Altman</td></tr></table>
<h3>Reports</h3>{S_REPORT}
<p>Results open in a report window with tables of statistics, p-values and confidence intervals; some analyses add columns
(fitted values, residuals, scores, group predictions) or graphs. Reports are saved in the project and can be exported as HTML or PDF.</p>
<h3>Methods</h3><p>Classical tests use SciPy's implementations. Mixed models are fitted by REML or ML with the profiled likelihood of
the lme4 formulation; generalised linear mixed models use the Laplace approximation or adaptive Gauss-Hermite quadrature; small-sample
tests of fixed effects can use the Kenward-Roger adjustment. Each report states the method used.</p>
""")

import manual_methods  # noqa: E402  (equations, when to use each tool, worked examples calculated at build time)
H.append(manual_methods.chapter())

H.append(f"""
<h2 id='geochem'>14. Geochemistry</h2>
<h3>Spider diagrams</h3>{S_SPIDER}
<p>One row per sample, one column per element in ppm, named after the element (La, Ce ... or 'La (ppm)'). Choose the reference
in the Plot menu: CI chondrite or primitive mantle (McDonough &amp; Sun 1995), N-MORB (Sun &amp; McDonough 1989) or PAAS (Taylor
&amp; McLennan 1985); REE in atomic order or the extended multi-element order of incompatibility. Values that are text (below detection,
e.g. '&lt;0.05') leave a gap bridged by a dotted line. The reference used is printed on the plot.</p>
<h3>TAS and QAP</h3>{S_TAS}{S_QAP}
<p><b>TAS</b>: SiO<sub>2</sub> as X and Na<sub>2</sub>O + K<sub>2</sub>O (one column, or two that are added), wt%, recalculated volatile-free.
<b>QAP</b>: modal Q, A and P (any total). Narrow QAP fields are numbered as in Streckeisen (1976), with a key below the triangle.</p>
<h3>Sample groups</h3>
<p>On the geochemistry diagrams (TAS, QAP, feldspar, pyroxene, ultramafic, soil, AFM, Harker, Shand, Frost and Pearce) samples are
coloured and given a different symbol per group, with a legend. By default the group column is found automatically: the first text column
with 2 to 12 different, repeated values (such as Rock, Suite or Setting); sample names, which are all different, are not used.
<b>Graph > Annotations > Group Samples By Column</b> picks another column or turns groups off. Each group is its own series, so its colour
and symbol can be changed on the format bar. Try Help &gt; Example Data &gt; Granite trace elements (grouped by Setting).</p>
<h3>Volatile-free recalculation</h3>
<p><b>Column > Normalise Major Oxides to 100% (Volatile-Free)</b> makes a new sheet in which the oxide columns (SiO<sub>2</sub> to
P<sub>2</sub>O<sub>5</sub>) add up to 100%, leaving out LOI, H<sub>2</sub>O and CO<sub>2</sub>; sample names and trace elements are copied
unchanged and the original total is kept in its own column. TAS (Le Bas et al. 1986), Harker and Frost diagrams expect volatile-free
analyses. On the Shand diagram, select P<sub>2</sub>O<sub>5</sub> too and CaO is corrected for apatite (CaO* = CaO &minus; 10/3 P<sub>2</sub>O<sub>5</sub>, molar).
Total iron reported as Fe2O3t (or Fe2O3T, Fe2O3*) is recognised and converted to FeO (&times; 0.8998) in AFM, Frost and mineral formulae. When a sheet has measured FeO (and Fe<sub>2</sub>O<sub>3</sub>) as well as a total-iron column, the CIPW norm, mineral formulae and thermobarometry use the measured values and ignore the total, so iron is never counted twice.
A missing value in a required column leaves that sample out instead of plotting it as zero.</p>
<h3>CIPW norm</h3>
<p><b>Column &gt; CIPW Norm</b> calculates the normative minerals of every analysis (Cross, Iddings, Pirsson &amp; Washington 1902) and
puts them in a new sheet with the sample names: quartz, corundum, orthoclase, albite, anorthite, nepheline, leucite, kaliophilite,
acmite, sodium and potassium metasilicate, diopside, wollastonite, dicalcium silicate, hypersthene, olivine, magnetite, hematite,
ilmenite, chromite, titanite, perovskite, rutile and apatite, in wt% (only the minerals present in some analysis get a column), with
their sum, the differentiation index DI = Q + Or + Ab + Ne + Lc + Kp (Thornton &amp; Tuttle 1960) and the normative plagioclase
An = 100 An/(An + Ab) by weight (Plag An) and by moles (Plag An (mol%)). The calculation follows the standard sequence: accessories first (apatite takes 10/3 CaO per P<sub>2</sub>O<sub>5</sub>, never more CaO than there is;
chromite, ilmenite, then titanite and rutile), feldspars, acmite and the alkali metasilicates in peralkaline rocks, anorthite and
corundum, magnetite and hematite, diopside, wollastonite and hypersthene; spare silica is quartz, and a silica deficit is made up in turn by
hypersthene &rarr; olivine, titanite &rarr; perovskite, albite &rarr; nepheline, orthoclase &rarr; leucite, wollastonite &rarr; dicalcium
silicate, diopside &rarr; dicalcium silicate + olivine and leucite &rarr; kaliophilite. MnO is counted as FeO, so the sum can differ from
100 by a few thousandths. The oxides are recalculated to 100% volatile-free first (can be turned off). When only total iron is given,
choose the Fe<sub>2</sub>O<sub>3</sub>/FeO ratio used to split it (Middlemost 1989 suggests 0.15 for basalts to 0.5 for rhyolites);
otherwise there is no normative magnetite. The method was checked by building rocks from known amounts of minerals (granite, olivine
tholeiite, basanite, leucite-bearing, peraluminous and peralkaline compositions) and recovering every mineral exactly.</p>
<h3>Thermobarometry</h3>
<p><b>Column &gt; Thermobarometry</b> adds a column of temperatures (&deg;C) or pressures (kbar) from a published calibration. Pick the
method; the dialog shows its equation, reference and where it can be used, and offers the sheet's columns for each input (guessed from
their names) and numbers for the others (activities, pressure). The new column's formula bar entry records the method, equation, inputs
and reference.</p>
<table border='1' cellspacing='0' cellpadding='3'>
<tr><th>Method</th><th>Equation (T in K)</th><th>Inputs</th></tr>
<tr><td>Ti-in-zircon (Ferry &amp; Watson 2007; Watson et al. 2006 with activities 1)</td><td>log Ti(ppm) = 5.711 &minus; 4800/T &minus; log a<sub>SiO2</sub> + log a<sub>TiO2</sub></td><td>Ti in zircon (ppm), a<sub>SiO2</sub>, a<sub>TiO2</sub></td></tr>
<tr><td>Zr-in-rutile (Ferry &amp; Watson 2007)</td><td>log Zr(ppm) = 7.420 &minus; 4530/T &minus; log a<sub>SiO2</sub></td><td>Zr in rutile (ppm), a<sub>SiO2</sub></td></tr>
<tr><td>Zr-in-rutile (Watson et al. 2006)</td><td>log Zr(ppm) = 7.36 &minus; 4470/T</td><td>Zr in rutile (ppm)</td></tr>
<tr><td>Ti-in-quartz (Thomas et al. 2010)</td><td>RT ln X<sub>TiO2</sub> = &minus;60952 + 1.520T &minus; 1741P(kbar) + RT ln a<sub>TiO2</sub></td><td>Ti in quartz (ppm), P, a<sub>TiO2</sub></td></tr>
<tr><td>Ti-in-quartz (Wark &amp; Watson 2006)</td><td>log Ti(ppm) = 5.69 &minus; 3765/T</td><td>Ti in quartz (ppm)</td></tr>
<tr><td>Zircon saturation (Watson &amp; Harrison 1983)</td><td>ln D = &minus;3.80 &minus; 0.85(M &minus; 1) + 12900/T, D = 497644/Zr<sub>melt</sub></td><td>whole-rock Zr (ppm) and major oxides (for M)</td></tr>
<tr><td>Zircon saturation (Boehnke et al. 2013)</td><td>ln D = 10108/T &minus; 1.16(M &minus; 1) &minus; 1.48</td><td>as above</td></tr>
<tr><td>Garnet&ndash;biotite (Ferry &amp; Spear 1978)</td><td>T = (2089 + 0.0096P(bar)) / (0.782 &minus; ln K<sub>D</sub>), K<sub>D</sub> = (Mg/Fe)<sub>Grt</sub>/(Mg/Fe)<sub>Bt</sub></td><td>Mg and Fe of garnet and biotite, P</td></tr>
<tr><td>Garnet&ndash;clinopyroxene (Ellis &amp; Green 1979)</td><td>T = (3104X<sub>Ca</sub><sup>Grt</sup> + 3030 + 10.86P(kbar)) / (ln K<sub>D</sub> + 1.9034), K<sub>D</sub> = (Fe/Mg)<sub>Grt</sub>/(Fe/Mg)<sub>Cpx</sub></td><td>Mg, Fe, Ca, Mn of garnet; Mg, Fe of cpx; P</td></tr>
<tr><td>Two-pyroxene (Brey &amp; K&ouml;hler 1990)</td><td>T = [23664 + (24.9 + 126.3X<sub>Fe</sub><sup>Cpx</sup>)P] / [13.38 + (ln K*)<sup>2</sup> + 11.59X<sub>Fe</sub><sup>Opx</sup>], K* = (1 &minus; Ca*)<sub>Cpx</sub>/(1 &minus; Ca*)<sub>Opx</sub>, Ca* = Ca/(1 &minus; Na)</td><td>Ca, Na, Mg, Fe of cpx and opx (apfu, 6 O), P</td></tr>
<tr><td>Two-pyroxene (Wells 1977)</td><td>T = 7341 / (3.355 + 2.44X<sub>Fe</sub><sup>Opx</sup> &minus; ln K), K = a<sub>En</sub><sup>Cpx</sup>/a<sub>En</sub><sup>Opx</sup></td><td>cpx and opx apfu (6 O): Ca, Mg, Fe and, if known, Si, Al, Ti, Cr, Fe<sup>3+</sup>, Mn, Na</td></tr>
<tr><td>Two-pyroxene (Wood &amp; Banno 1973)</td><td>T = &minus;10202 / (ln K &minus; 7.65X<sub>Fe</sub><sup>Opx</sup> + 3.88(X<sub>Fe</sub><sup>Opx</sup>)<sup>2</sup> &minus; 4.6)</td><td>as for Wells</td></tr>
<tr><td>Ca-in-orthopyroxene (Brey &amp; K&ouml;hler 1990)</td><td>T = (6425 + 26.4P) / (&minus;ln Ca<sub>Opx</sub> + 1.843)</td><td>Ca of opx (apfu, 6 O), P</td></tr>
<tr><td>Amphibole&ndash;plagioclase A, edenite&ndash;tremolite (Holland &amp; Blundy 1994)</td><td>T = [&minus;76.95 + 0.79P + Y<sub>ab</sub> + 39.4X<sub>Na</sub><sup>A</sup> + 22.4X<sub>K</sub><sup>A</sup> + (41.5 &minus; 2.89P)X<sub>Al</sub><sup>M2</sup>] / [&minus;0.0650 &minus; R ln(27X<sub>&#9633;</sub><sup>A</sup>X<sub>Si</sub><sup>T1</sup>X<sub>An</sub> / 256X<sub>Na</sub><sup>A</sup>X<sub>Al</sub><sup>T1</sup>)]</td><td>amphibole apfu (23 O), An of plagioclase, P; quartz-bearing rocks</td></tr>
<tr><td>Amphibole&ndash;plagioclase B, edenite&ndash;richterite (Holland &amp; Blundy 1994)</td><td>T = [78.44 + Y<sub>ab-an</sub> &minus; 33.6X<sub>Na</sub><sup>M4</sup> &minus; (66.8 &minus; 2.92P)X<sub>Al</sub><sup>M2</sup> + 78.5X<sub>Al</sub><sup>T1</sup> + 9.4X<sub>Na</sub><sup>A</sup>] / [0.0721 &minus; R ln(27X<sub>Na</sub><sup>M4</sup>X<sub>Si</sub><sup>T1</sup>X<sub>An</sub> / 64X<sub>Ca</sub><sup>M4</sup>X<sub>Al</sub><sup>T1</sup>X<sub>Ab</sub>)]</td><td>as above; with or without quartz</td></tr>
<tr><td>Garnet&ndash;orthopyroxene Al (Harley &amp; Green 1982, eq. 5)</td><td>P = (1/&Delta;V)[(R ln K &minus; 2.93)T + 5650 + 5157(1 &minus; X<sub>Al</sub>)(1 &minus; 2X<sub>Al</sub>)X<sub>Fe</sub><sup>Opx</sup> &minus; 6300(X<sub>Ca</sub>X<sub>Fe</sub> + X<sub>Ca</sub><sup>2</sup>)], K = X<sub>Al</sub>(1 &minus; X<sub>Al</sub>)/(1 &minus; X<sub>Ca</sub>)<sup>3</sup>, &Delta;V = &minus;[183.3 + 178.98X<sub>Al</sub>(1 &minus; X<sub>Al</sub>)] cal/kbar</td><td>opx Al, Mg, Fe; garnet Ca, Mg, Fe; T</td></tr>
<tr><td>Garnet&ndash;orthopyroxene Al (Nickel &amp; Green 1985, eq. 5)</td><td>P = &minus;{{&minus;RT ln K<sub>D</sub> &minus; 9000X<sub>Ca</sub><sup>2</sup> &minus; 3400[2(X<sub>Cr</sub><sup>gt</sup>)<sup>2</sup> &minus; X<sub>Mg</sub><sup>M1</sup>X<sub>Cr</sub><sup>M1</sup>] &minus; X<sub>Ca</sub>X<sub>Cr</sub>(90853 &minus; 52.1T) &minus; 7590X<sub>Fe</sub>X<sub>Ca</sub> + 5157X<sub>Mg</sub><sup>M1</sup>X<sub>Fe</sub><sup>M1</sup> + 6047 &minus; 3.23T}} / [183.3 + 178.98X<sub>Al</sub><sup>M1</sup>(1 &minus; X<sub>Al</sub><sup>M1</sup>)]</td><td>opx Al, Cr, Ti, Na, Ca, Mn, Mg, Fe; garnet Ca, Mg, Fe, Mn, Al, Cr; T</td></tr>
<tr><td>Garnet&ndash;orthopyroxene Al, P<sub>BKN</sub> (Brey &amp; K&ouml;hler 1990, Table 3)</td><td>P = [&minus;C<sub>2</sub> &minus; &radic;(C<sub>2</sub><sup>2</sup> + 4C<sub>3</sub>C<sub>1</sub>/1000)]/(2C<sub>3</sub>), C<sub>1</sub>, C<sub>2</sub>, C<sub>3</sub> and K<sub>D</sub> as in Table 3</td><td>as for Nickel &amp; Green, plus opx Fe<sup>3+</sup></td></tr>
<tr><td>Al-in-hornblende (Hammarstrom &amp; Zen 1986; Hollister et al. 1987; Johnson &amp; Rutherford 1989; Schmidt 1992; Mutch et al. 2016)</td><td>P(kbar) = &minus;3.92 + 5.03Al; &minus;4.76 + 5.64Al; &minus;3.46 + 4.23Al; &minus;3.01 + 4.76Al; 0.5 + 0.331Al + 0.995Al<sup>2</sup></td><td>total Al of hornblende, apfu on 23 O</td></tr>
</table>
<p>For the amphibole&ndash;plagioclase thermometers the site fractions are those of Holland &amp; Blundy (1994): cm = Si + Al + Ti +
Fe<sup>3+</sup> + Fe<sup>2+</sup> + Mg + Mn &minus; 13, X<sub>Si</sub><sup>T1</sup> = (Si &minus; 4)/4, X<sub>Al</sub><sup>T1</sup> = (8 &minus; Si)/4,
X<sub>Al</sub><sup>M2</sup> = (Al + Si &minus; 8)/2, X<sub>K</sub><sup>A</sup> = K, X<sub>&#9633;</sub><sup>A</sup> = 3 &minus; Ca &minus; Na &minus; K &minus; cm,
X<sub>Na</sub><sup>A</sup> = Ca + Na + cm &minus; 2, X<sub>Na</sub><sup>M4</sup> = (2 &minus; Ca &minus; cm)/2, X<sub>Ca</sub><sup>M4</sup> = Ca/2; Y<sub>ab</sub> = 0 for
X<sub>Ab</sub> &gt; 0.5, otherwise 12.01(1 &minus; X<sub>Ab</sub>)<sup>2</sup> &minus; 3.0 kJ; Y<sub>ab-an</sub> = 3.0 kJ for X<sub>Ab</sub> &gt; 0.5, otherwise
12.0(2X<sub>Ab</sub> &minus; 1) + 3.0; R in kJ. Calculate the amphibole formula with the 13eCNK/15eNK Fe<sup>3+</sup> estimate, as the authors did.
Plagioclase An can be given as a fraction or in %. Optional inputs (Ti, Fe<sup>3+</sup>, Mn, K, Na in pyroxene) count as 0 when left out.
Thermometer A has the albite fraction of plagioclase in its logarithm (reaction edenite + 4 quartz = tremolite + albite), as printed in
the paper (p. 441). The equations, constants and site fractions of every method above were checked against the original papers.</p>
<p>The garnet&ndash;orthopyroxene barometers use the temperature from a column (for example one made with a two-pyroxene or Ca-in-opx
thermometer) or one value for all rows. Their site fractions follow the papers: Harley &amp; Green (1982) X<sub>Al</sub> = Al/2 in opx and
X<sub>Ca</sub> = Ca/(Ca + Mg + Fe) in garnet; Nickel &amp; Green (1985) X<sub>Al</sub><sup>M1</sup> = (Al &minus; Cr &minus; 2Ti + Na)/2,
X<sub>MgFe</sub><sup>M1</sup> = 1 &minus; X<sub>Al</sub><sup>M1</sup> &minus; Cr &minus; Ti, X<sub>MgFe</sub><sup>M2</sup> = 1 &minus; Ca &minus; Na &minus; Mn; Brey &amp; K&ouml;hler (1990)
the same with Fe<sup>3+</sup> and the Tschermak Al X<sub>Al,TS</sub><sup>M1</sup> from jadeite = Na &minus; Cr &minus; Fe<sup>3+</sup> &minus; 2Ti. Checks: the Harley &amp;
Green barometer reproduces the Al isopleths of their Fig. 2 (2.5 % and 5 % Al in M1 at 1000 &deg;C near 27 and 19 kbar), and the Nickel &amp;
Green and Brey &amp; K&ouml;hler barometers agree within a few kbar for a typical garnet lherzolite.</p>
<p>For Wells and Wood &amp; Banno the enstatite activity is a<sub>En</sub> = X<sub>Mg</sub><sup>M1</sup>&middot;X<sub>Mg</sub><sup>M2</sup> in the
ideal two-site model of Wood &amp; Banno (1973): Ca, Na and Mn on M2; Al<sup>VI</sup> = Al &minus; (2 &minus; Si), Fe<sup>3+</sup>, Ti and Cr on M1;
Fe<sup>2+</sup> and Mg share what is left on each site in the ratio Mg/(Mg + Fe<sup>2+</sup>). A granulite pair (cpx Ca 0.85, Na 0.02,
X<sub>Fe</sub> 0.30; opx Ca 0.03, X<sub>Fe</sub> 0.40) gives 945 &deg;C (Wells), 895 &deg;C (Wood &amp; Banno) and 827 &deg;C (Brey &amp; K&ouml;hler at
8 kbar): Wells is usually the highest.</p>
<p>M = (Na + K + 2Ca)/(Al&middot;Si) in cation fractions of all major cations. Mineral Mg, Fe, Ca, Mn and Al come from <b>Mineral Formula
from Oxides</b>. Each calibration only holds for the assemblage and range it was made for (the dialog says which): Al-in-hornblende needs
the full buffering assemblage (hornblende, plagioclase, K-feldspar, quartz, biotite, titanite, Fe-Ti oxide); Ti-in-zircon and Zr-in-rutile need
the activities of TiO<sub>2</sub> and SiO<sub>2</sub>; whole-rock zircon saturation gives a maximum or minimum temperature depending on
inherited zircon. The equations were checked against hand-worked values (10 ppm Ti in zircon gives 745.7 &deg;C; 50 ppm Ti in quartz at
5 kbar gives about 577 &deg;C).</p>
<h3>Volcanic and mantle thermobarometry (Putirka 2008; Nimis &amp; Taylor 2000)</h3>
<p>The Thermobarometry dialog also holds mineral-melt and clinopyroxene methods. Put the liquid (glass, melt inclusion or whole rock) in wt%
oxide columns named SiO<sub>2</sub>, TiO<sub>2</sub>, Al<sub>2</sub>O<sub>3</sub>, FeO (or FeOt), MnO, MgO, CaO, Na<sub>2</sub>O, K<sub>2</sub>O
(a word such as <i>glass</i> or <i>liq</i> may be added) and the clinopyroxene in columns such as <i>Cpx SiO2</i>, <i>Cpx Al2O3</i>; the
dialog lists which columns it found for each phase. Liquid cation fractions follow Putirka (2008) Table 1 and clinopyroxene components his
Table 3 (both reproduced exactly by the self-test).</p>
<table class='ref'><tr><th>Method</th><th>Gives</th><th>Needs</th><th>Error</th></tr>
<tr><td>Liquid MgO, Eq 13; Eq 15</td><td>T of an olivine-saturated liquid</td><td>liquid (+ H<sub>2</sub>O, P)</td><td>&plusmn;71, &plusmn;60 &deg;C</td></tr>
<tr><td>Olivine-liquid, Beattie (1993), Eq 19</td><td>T (dry)</td><td>liquid, olivine Fo (or none: liquidus T), P</td><td>&plusmn;40-50 &deg;C</td></tr>
<tr><td>Olivine-liquid, Eq 22</td><td>T (hydrous)</td><td>liquid, Fo, H<sub>2</sub>O, P</td><td>&plusmn;45 &deg;C</td></tr>
<tr><td>Olivine K<sub>D</sub>(Fe-Mg) and equilibrium Fo</td><td>equilibrium test (Rhodes diagram)</td><td>liquid, Fo</td><td>0.30 &plusmn; 0.03</td></tr>
<tr><td>Plagioclase-liquid Eq 24a; hygrometer Eq 25b</td><td>T; H<sub>2</sub>O in the melt</td><td>liquid, An (Or), P (and T for 25b)</td><td>&plusmn;36 &deg;C; &plusmn;1.1 wt%</td></tr>
<tr><td>Clinopyroxene-liquid Eq 33; Eqs 30, 31</td><td>T; P</td><td>liquid, cpx, H<sub>2</sub>O</td><td>&plusmn;45 &deg;C; &plusmn;1.6-3 kbar</td></tr>
<tr><td>Clinopyroxene only, Eqs 32a, 32d</td><td>P; T</td><td>cpx</td><td>&plusmn;3 kbar; &plusmn;58 &deg;C</td></tr>
<tr><td>Nimis &amp; Taylor (2000) Cr-in-cpx; En-in-cpx</td><td>P; T of garnet peridotite</td><td>cpx (with Cr<sub>2</sub>O<sub>3</sub>)</td><td>&plusmn;2.3 kbar; &plusmn;30 &deg;C</td></tr></table>
<p>Most of these need each other: the clinopyroxene-liquid thermometer needs P and the barometer needs T. Use the <b>Coupled P-T Solver</b>
(e.g. Eq 33 with Eq 31, or En-in-Cpx with Cr-in-Cpx) to get both. Always test equilibrium first with the K<sub>D</sub> methods. In Putirka's
equations the plagioclase X<sub>An</sub> is printed as X<sub>CaO</sub>/(X<sub>CaO</sub> + X<sub>NaO0.5</sub>X<sub>KO0.5</sub>); PlotBench uses
Ca/(Ca + Na + K), as his text defines it. Ghiorso &amp; Evans (2008) Fe-Ti oxide thermo-oxybarometry needs their full thermodynamic solution
model (dozens of interaction parameters and an iterative Gibbs-energy minimisation) and is not included; the Winchester &amp; Floyd (1977)
diagrams are not included either, because the boundaries in the scanned figure cannot be read precisely enough.</p>
<h3>Zooming and the graph side panel</h3>
<p>Zoom with the mouse wheel (about the cursor), the magnifier buttons on the graph's own toolbar, <b>View &gt; Zoom In / Zoom Out</b>
(Ctrl+= and Ctrl+-) or the Zoom tool (drag a rectangle). <b>Reset view</b> (Ctrl+0, the corner-arrows button) shows the whole graph again;
Back and Forward step through earlier views. Log axes zoom in log space. The panel to the right of a wide graph has a <b>Curves</b> section
(untick a curve to hide it) and folding groups of shortcuts; click a heading to fold it. <b>View &gt; Graph Side Panel</b> hides the panel.</p>
<h3>Drawing shapes and editing them on the graph</h3>
<p><b>Drawing.</b> Line, arrow, rectangle and circle: choose the tool and drag on the graph. Polygon and region: click to place
each node. A straight line follows the mouse from the last node, so you can place the nodes in any shape; the smooth curve of a region appears when you finish; click the first node again (it lights up when you are close), double-click,
or press Enter to close the shape. Backspace or a right-click takes the last node back, and Esc cancels. A polygon has straight
sides; a region is a smooth closed curve through its nodes.</p>
<p><b>Editing.</b> Double-click a shape, or right-click it and choose <b>Edit handles / nodes</b>. Small red handles appear:</p>
<ul><li><b>Line, arrow</b>: drag an end to lengthen, shorten or turn it (hold Shift for steps of 15&deg;); drag the line itself to move it.</li>
<li><b>Rectangle, ellipse</b>: eight handles resize it (Shift on a corner keeps the proportions); the round handle above it turns it
(Shift: steps of 15&deg;); drag inside to move it.</li>
<li><b>Polygon, region</b>: drag a node; double-click or Ctrl+click the outline to add a node there; select a node and press Delete to
remove it (at least three stay); the round handle turns the whole shape about its centre; drag inside to move it. A right-click offers
Add node, Delete node and Smooth curve.</li></ul>
<p>Press Enter or Esc, or click on empty space, to finish. Everything done in one editing session is one undo step. Right-click a
shape at any time for <b>Shape properties</b> (colours, fill, pattern, line, arrow head, smooth or straight, angle), the layer, and
Delete. The handles are only on screen: they are never part of an exported figure.</p>
<h3>Drawing and annotation tools on the left toolbar</h3>
<p>The drawing tools (line, arrow, rectangle, circle or ellipse, polygon, freehand region) share one button at the bottom of the left
toolbar, and the tools that add to a graph (text, arrow, reference line, confidence ellipse, zoom inset) share the button above it,
so the toolbar fits in one column. Click a button to use the tool shown on it again; click the small arrow beside it to choose another
tool, which then becomes the one shown. The same tools are in the <b>Draw</b> and <b>Add</b> sections of the graph's side panel.</p>
<h3>Formatting single texts</h3>
<p>Every text in a graph can be formatted on its own, without changing the others: the title, each axis title, the tick labels of
each axis, the legend title and each legend entry, field names and other texts drawn by the plot, your own text annotations, and
colour-bar titles. Click a text to select it; a red dashed outline marks it (the outline is never exported). The <b>text format
bar</b>, under the curve format bar, then shows that text in its words box, formatted as it looks.</p>
<p><b>Formatting single letters.</b> Select letters in the words box, as in a word processor, and click <b>B</b> (bold),
<i>I</i> (italic), x&sup2; (superscript), x&#8322; (subscript) or the stacked button: only those letters change, in the box and on
the graph. Click the same button again to remove that format. With nothing selected, B and I act on the whole text. For a stacked
subscript and superscript (as in X<sub>2</sub><sup>3+</sup> written one above the other), type for example <code>2,3+</code>, select it
and click the stacked button. Keys in the words box: Ctrl+B, Ctrl+I, Ctrl+= (subscript), Ctrl+Shift+= (superscript), Ctrl+- (stacked),
Ctrl+G (turns the selected Latin letters into Greek), Ctrl+Shift+&gt; and Ctrl+Shift+&lt; (size), Enter (apply the words).</p>
<p><b>Symbols.</b> The &Omega; button opens a picker with 464 symbols in groups: Greek, maths, relations, arrows, superscript and
subscript digits, units, chemistry, shapes, numbers and fractions, accented letters and punctuation. A click inserts the symbol at
the cursor.</p>
<p><b>Whole text.</b> Font, size, colour (A), larger and smaller (A&#8314;, A&#8315;), orientation (&#8635;, the angle in degrees) and reset
(&#8634;) act on the whole selected text. Tick labels are formatted as a group for each axis and keep their format when you zoom. Each
change is one undo step, is saved with the project and appears in exported figures. Right-click a text for more (layer, hide, reset
all texts).</p>
<h3>New in 1.30.1: calibration ranges, uncertainties and validation</h3>
<p>Thermobarometry results now come with checks. A method whose authors state a calibration domain (for example Ti-in-zircon,
580&ndash;1070 &deg;C; Ti-in-quartz of Thomas et al. 2010, 700&ndash;940 &deg;C and 5&ndash;20 kbar) adds a column saying, for each row, whether the
result and the pressure given lie inside it; the olivine- and clinopyroxene-liquid K<sub>D</sub> tests add an <i>in equilibrium</i> column. Tick
<b>Monte Carlo uncertainty</b> in the Thermobarometry dialog for a 1&sigma; column: every measured value is varied by the relative error you
give (and P by its absolute error), independently, and the method rerun a few hundred times. This is the analytical part of the uncertainty;
the calibration error of the equation, given in the method notes, comes on top. The file <code>VALIDATION.md</code> in the source lists the
benchmarks against published worked examples and experiments. Opening a project is now all or nothing: if the new project cannot be built,
your previous windows come back unchanged.</p>
<h3>New in 1.30</h3>
<p><b>File &gt; Export Worksheet as LaTeX Table (booktabs)</b> writes the sheet as a <code>booktabs</code> table, with formulae in column names
typeset (SiO<sub>2</sub>, Fe<sup>3+</sup>, <sup>206</sup>Pb/<sup>238</sup>U) and numbers to four significant figures. The common-Pb correction now
also writes the corrected <sup>207</sup>Pb*/<sup>235</sup>U and corrected 1&sigma; columns, when the sheet has 207Pb/235U and error columns, so
corrected analyses plot straight onto concordia. The discordance filter offers discordance against <sup>207</sup>Pb/<sup>206</sup>Pb (Precambrian),
against <sup>207</sup>Pb/<sup>235</sup>U (Phanerozoic), or Auto, which switches at 1000 Ma. Thermobarometry adds the zircon oxybarometer of Loucks et
al. (2020), &Delta;FMQ = 3.998 log[Ce/&radic;(U<sub>i</sub> Ti)] + 2.284, with the age used to turn measured U into U at crystallisation. The two-pyroxene
equations accept FeOt for FeO and leave a blank instead of an error when an orthopyroxene has no Ca. Drop-down boxes and number boxes show clear
arrows, and the graph side panel uses larger fold arrows.</p>
<h3>Ribbon layout and command search</h3>
<p><b>View &gt; Ribbon Toolbar Layout</b> is the default: the top, bottom and right toolbars become one bar of four tabs (Home, Plot, Analysis,
Petrology &amp; Geochem) with a short label under each button, and the canvas tools (zoom, pan, shapes) stay on the left on every tab. Untick it
for the classic four side toolbars. Ctrl+K, or the search field at the top, finds any command, plot type or thermometer by a few words. The start
page no longer blocks the window and closes itself when a sheet, graph or project opens.</p>
<h3>Plot Details: show, hide and fill curves</h3>
<p><b>Graph &gt; Plot Details</b> (Ctrl+Shift+T, or <b>Curves...</b> on the format bar) lists every curve in the graph: data, baselines,
fitted peaks, cumulative fits and added series. Untick a curve to hide it (it also leaves the legend); tick it to show it again. Select a curve
to set its colour, line width and style, symbol and size, and to fill the area under it: to Y = 0, to the bottom of the graph or to the next
curve, with a fill colour, an opacity and a pattern (diagonal, cross-hatch, grid, horizontal, vertical, dots, circles, stars). The preview updates
as you change anything.</p>
<h3>Drawing tools</h3>
<p><b>Graph &gt; Draw</b> and the left toolbar draw a line, arrow, rectangle, circle or ellipse, polygon (click the corners, double-click or
right-click to finish) or freehand region (drag). Esc cancels. Objects are stored in data coordinates, so they move with zoom and are saved with
the project. Double-click or right-click an object to set its line colour, width and style, arrow head, fill colour, opacity, hatch pattern and
layer (in front of or behind the data), or to delete it.</p>
<h3>Customising toolbars</h3>
<p>Every toolbar (top, left, right, bottom) ends with a <b>&raquo;</b> button. <b>Add or Remove Buttons</b> ticks buttons on or off;
<b>Add a command as a button</b> turns any menu command into a toolbar button; <b>Remove an added button</b> and <b>Reset this toolbar</b>
undo the changes. The choice is remembered between sessions.</p>
<h3>Peak Analyzer goals</h3>
<p>The Peak Analyzer has five goals, as in Origin: <b>Fit peaks</b>; <b>Integrate peaks</b> (area between valleys by the trapezoid rule,
centre, height and interpolated FWHM, written to an <i>Integrated</i> sheet); <b>Find peaks</b> (positive, negative or both, with a
minimum height in % of the range); <b>Create baseline</b>; and <b>Subtract baseline</b> (new <i>Corrected_</i> column and graph). Baselines
can be a constant (minimum, maximum, mean, median or a value), end points, anchor points joined by lines or a B-spline, automatic anchors
(the lowest point in N segments), Shirley, asymmetric least squares, or an existing column.</p>
<h3>Common-Pb correction and discordance filter</h3>
<p><b>Analysis &gt; Geochronology &gt; Common-Pb Correction</b> gives f<sub>206</sub> (the fraction of <sup>206</sup>Pb that is common), the
corrected <sup>206</sup>Pb*/<sup>238</sup>U and its age. The 204Pb method uses f<sub>206</sub> = (<sup>206</sup>Pb/<sup>204</sup>Pb)<sub>c</sub> /
(<sup>206</sup>Pb/<sup>204</sup>Pb)<sub>m</sub>; the 207Pb method treats the measured <sup>207</sup>Pb/<sup>206</sup>Pb as a mix of radiogenic Pb on
concordia at the <sup>206</sup>Pb/<sup>238</sup>U age and common Pb; the 208Pb method does the same with <sup>208</sup>Pb/<sup>206</sup>Pb and the
Th/U of the analysis. Common Pb comes from the two-stage model of Stacey &amp; Kramers (1975) at the age of each analysis (iterated), or at an age
you give. <b>Discordance Filter</b> masks analyses beyond a discordance limit (default 10%), so KDE, weighted mean and concordia age use the
concordant ones; Undo brings them back.</p>
<h3>Two-pyroxene thermometers and barometers (Putirka 2008 Eqs 36-39)</h3>
<p>For coexisting clinopyroxene and orthopyroxene, with columns named <i>Cpx SiO2</i> ... and <i>Opx SiO2</i> ... (wt%). Orthopyroxene
components follow Putirka's Table 2 (NaAlSi<sub>2</sub>O<sub>6</sub>, FmTiAlSiO<sub>6</sub>, CrAl<sub>2</sub>SiO<sub>6</sub>,
FmAl<sub>2</sub>SiO<sub>6</sub>, CaFmSi<sub>2</sub>O<sub>6</sub>, Fm<sub>2</sub>Si<sub>2</sub>O<sub>6</sub>), clinopyroxene components Table 3.
Eq 36 (any composition, &plusmn;60 &deg;C) and Eq 37 (Mg# cpx &gt; 0.75, &plusmn;38 &deg;C) give T from 10<sup>4</sup>/T(&deg;C), as printed;
Eq 38 gives P without T (&plusmn;3.7 kbar) and Eq 39 P with T (&plusmn;2.8 kbar), with K<sub>f</sub> = X<sub>Ca</sub><sup>opx</sup>/(1 &minus;
X<sub>Ca</sub><sup>cpx</sup>), a<sub>En</sub><sup>opx</sup> after Wood &amp; Banno (1973) and a<sub>Di</sub><sup>cpx</sup> from the text below Eq 39.
Pair Eq 36 or 37 with Eq 39 in the Coupled P-T Solver. X<sub>Di</sub><sup>cpx</sup> in Eq 37 is taken as DiHd &times; Mg/(Mg + Fe + Mn), the same
definition the paper gives for orthopyroxene.</p>
<h3>Zr-in-titanite thermometer</h3>
<p>Hayden, Watson &amp; Wark (2008): log Zr(ppm) = 10.52 &minus; 7708/T &minus; 960 P/T &minus; log a<sub>TiO2</sub> &minus; log a<sub>SiO2</sub>,
T in K and P in GPa; in the Thermobarometry dialog with P in kbar and the activities (1 with rutile and quartz).</p>
<h3>Fe-Ti oxide thermometer and oxygen barometer (Ghiorso &amp; Evans 2008)</h3>
<p><b>Column &gt; Fe-Ti Oxide Thermometer / Oxybarometer</b> (also Analysis &gt; Petrology and the right toolbar) opens a dialog showing the column found for each oxide of the two minerals (change any), the pressure in kbar, and the Mg/Mn test of Bacon &amp; Hirschmann (1988): pairs in equilibrium lie on log(Mg/Mn)<sub>Mt</sub> = 0.9317 log(Mg/Mn)<sub>Ilm</sub> &minus; 0.0909 (atomic ratios); the deviation from that line and a yes/no column are added, yes meaning inside their 2&sigma; envelope (Table 1: upper 0.9430x + 0.0124, lower 0.9213x &minus; 0.1696). The test holds for homogeneous oxides of fresh volcanic rocks, not for exsolved, plutonic or metamorphic oxides, and passing it is necessary but not sufficient for equilibrium. Rows are solved with a progress bar and Cancel. It gives the temperature, log<sub>10</sub> fO<sub>2</sub> and &Delta;NNO of every row
that has a titanomagnetite and an ilmenite analysis in wt% oxides. Name the columns after the phase and the oxide: <i>Mt TiO2</i>,
<i>Mt Al2O3</i>, <i>Mt FeO</i> (or FeOt; Fe<sub>2</sub>O<sub>3</sub> if analysed), <i>Mt MnO</i>, <i>Mt MgO</i>, and <i>Ilm TiO2</i>, <i>Ilm FeO</i> ...
(<i>Usp</i>, <i>Tmt</i>, <i>Hem</i> also work). With only total iron, Fe<sup>3+</sup> is calculated by charge balance (3 cations per 4 O for
the spinel, 2 per 3 O for the ilmenite).</p>
<p><b>How it works.</b> Temperature comes from the Fe<sup>2+</sup>Ti &ndash; Fe<sup>3+</sup><sub>2</sub> exchange
Fe<sub>2</sub>TiO<sub>4</sub> + Fe<sub>2</sub>O<sub>3</sub> = FeTiO<sub>3</sub> + Fe<sub>3</sub>O<sub>4</sub>, fO<sub>2</sub> from 4 Fe<sub>3</sub>O<sub>4</sub> + O<sub>2</sub>
= 6 Fe<sub>2</sub>O<sub>3</sub>. The ilmenite-hematite solid solution (with MgTiO<sub>3</sub>, MnTiO<sub>3</sub> and Al<sub>2</sub>O<sub>3</sub>) is the model of
Ghiorso &amp; Evans (2008, their eq. 78 and Table 2): Fe<sup>2+</sup>, Mg and Mn order against Ti over the two octahedral layers, the order is
solved at every temperature, and an empirical short-range-order term (&alpha; = 0.073) reduces the configurational entropy. The titanomagnetite
is the cation-ordered spinel model of Sack &amp; Ghiorso (1991a) (Mn counted as Mg, Cr as Al, as Ghiorso &amp; Evans did). End-member
properties are those of Berman (1988) for hematite, ilmenite and magnetite (with their magnetic &lambda;-transitions), the ulv&ouml;spinel
of Ghiorso &amp; Evans (enthalpy &minus;1490.417 kJ, entropy 184.199 J/K and their new heat capacity), and NIST-JANAF O<sub>2</sub>.
&Delta;NNO uses the Ni-NiO buffer of O'Neill &amp; Pownceby (1993).</p>
<p><b>Tests.</b> The magnetite-hematite buffer from these end-members agrees with Frost (1991) within 0.15-0.2 log units. On the
41 experimental oxide pairs of Evans et al. (2006, Tables 3 and 4), runs at 900 &deg;C are recovered as 902 &plusmn; 65 &deg;C (2 SD) and runs
at 800 &deg;C as 766 &plusmn; 163 &deg;C, with &Delta;NNO within +0.3 &plusmn; 0.6 log units (Ghiorso &amp; Evans report 936 &plusmn; 66 and 821 &plusmn; 80 &deg;C
for the same runs with their software). On the 1-bar Fe-Ti-O experiments of Lattard et al. (2005) at 1000-1300 &deg;C the exchange and
redox energies at the run temperature are within about &plusmn;2 kJ of zero for ilmenite contents 0.3-0.95, as in their Figs. 7-9.
Three things to know. (1) The Table 2 correction &Delta;H&deg;, &Delta;S&deg; to the exchange reaction is applied with the sign that recovers the
experiments; the paper does not state it explicitly. (2) Temperatures from oxidised pairs with hematite-rich, cation-disordered ilmenite
(&Delta;NNO above about +1.5) are uncertain by 100 &deg;C or more, as Ghiorso &amp; Evans warn, and at 1100-1300 &deg;C the exchange energy changes
slowly with temperature, so small analytical errors move T a lot; fO<sub>2</sub> is much more robust than T. (3) Near-end-member ilmenite
(X<sub>Ilm</sub> &gt; 0.97) and non-stoichiometric analyses may give no solution (blank). Check equilibrium with the Mg/Mn partitioning of
Bacon &amp; Hirschmann (1988) before trusting a pair. Each row takes a few seconds.</p>
<h3>Coupled P-T solver</h3>
<p>Many thermometers need the pressure and many barometers the temperature. <b>Column &gt; Coupled P-T Solver</b> takes one of each,
for example Holland &amp; Blundy hornblende-plagioclase with Al-in-hornblende, Ca-in-orthopyroxene or two-pyroxene with a garnet-orthopyroxene
barometer, and solves them together for every row: T from the thermometer at the current P, then P from the barometer at that T, until P
changes by less than 0.01 kbar (usually 3 to 6 rounds). Both results are added as columns; rows that do not settle are left blank.</p>
<h3>Tests against experiments</h3>
<p>The garnet-orthopyroxene barometers were run on the twelve garnet-lherzolite experiments of Brey, K&ouml;hler &amp; Nickel (1990,
Part I, Table 2) at 30 to 50 kbar and 900 to 1300 &deg;C, at the run temperatures. Against the run pressures, Brey &amp; K&ouml;hler's
P<sub>BKN</sub> gives +0.1 &plusmn; 2.6 kbar (mean and standard deviation), Nickel &amp; Green +0.2 &plusmn; 2.8 kbar and Harley &amp; Green
&minus;2.9 &plusmn; 2.7 kbar: the first two recover the experiments within the scatter Brey &amp; K&ouml;hler report, and Harley &amp; Green
reads about 3 kbar low in Cr-bearing lherzolite, as expected for a calibration made in Cr-free systems. This check runs with every build.</p>
<h3>Geochronology</h3>
<p>Plot types (<b>Plot &gt; Geochronology</b>) and <b>Analysis &gt; Geochronology</b> commands. Errors are absolute 1&sigma; inputs; results
are given at 2&sigma;, and also multiplied by &radic;MSWD when the scatter is larger than the errors allow (MSWD &gt; 1).</p>
<ul><li><b>Isochron (York regression)</b>: parent ratio as X (87Rb/86Sr, 147Sm/144Nd, 176Lu/177Hf or 187Re/188Os), then the daughter
ratio, the errors of X and Y and optionally their correlation. The line is the York et al. (2004) maximum-likelihood fit with errors in
both variables; age t = ln(1 + slope)/&lambda;, with the initial ratio, MSWD and its probability. Decay constants: Rb 1.3972&times;10<sup>&minus;11</sup>
(Villa et al. 2015), Sm 6.54&times;10<sup>&minus;12</sup> (Lugmair &amp; Marti 1978), Lu 1.867&times;10<sup>&minus;11</sup> (S&ouml;derlund et al. 2004),
Re 1.666&times;10<sup>&minus;11</sup> per year (Smoliar et al. 1996). Checked on the Pearson-York benchmark (slope &minus;0.48053, intercept
5.4799, errors 0.0580 and 0.2950 as in Cantrell 2008) and on exact isochrons.</li>
<li><b>Concordia (Wetherill</b> 207Pb/235U vs 206Pb/238U, or <b>Tera-Wasserburg</b> 238U/206Pb vs 207Pb/206Pb): each analysis as its 95%
error ellipse on the concordia curve, with age marks and the weighted mean 206Pb/238U age. &lambda;<sub>238</sub> = 1.55125&times;10<sup>&minus;10</sup>,
&lambda;<sub>235</sub> = 9.8485&times;10<sup>&minus;10</sup> per year (Jaffey et al. 1971), <sup>238</sup>U/<sup>235</sup>U = 137.818 (Hiess et al. 2012).
<b>U-Pb Ages and Discordance</b> adds the 206/238, 207/235 and 207/206 ages of every analysis from columns named after the ratios, and the
discordance 100(1 &minus; t<sub>6/8</sub>/t<sub>7/6</sub>).</li>
<li>The Wetherill plot also gives the <b>concordia age</b> of Ludwig (1998): the error-weighted mean point of all analyses is moved along concordia to the age t that minimises S(t) = R<sup>T</sup>&Omega;R, with the MSWD of concordance (1 df) and of equivalence (2n &minus; 2 df); decay-constant errors are not included.</li><li><b>Weighted Mean</b>: inverse-variance mean, its error, MSWD and p; analyses more than 2&sigma; from the mean are drawn in red.</li>
<li><b>Detrital Age KDE + PDP</b>: histogram, Gaussian kernel density with the bandwidth chosen by least-squares cross-validation (it
keeps separate age populations apart, where Silverman's rule smooths them together) and, with an error column, the probability density
plot. <b>Cumulative Age Distribution</b> compares several samples.</li></ul>
<h3>Pearce (2008) basalt diagrams</h3>
<p><b>Th/Yb vs Nb/Yb</b>: oceanic basalts lie in the diagonal MORB-OIB array (N-MORB, E-MORB, OIB along it); subduction-related and crustally
contaminated basalts plot above it, because Th is added while Nb is not. <b>TiO<sub>2</sub>/Yb vs Nb/Yb</b>: OIB (deep melting with garnet in the
residue) have high TiO<sub>2</sub>/Yb, MORB low; Nb/Yb = 1.45 divides N- from E-MORB, and the dashed line tholeiitic from alkalic OIB. Th, Nb, Ti
and Yb stay put during alteration and low-grade metamorphism, so the diagrams work for ophiolites and Archean greenstones. The boundary
lines were digitised from Pearce (2008) Fig. 2. Example: Help &gt; Example Data &gt; Oceanic and arc basalts.</p>
<h3>Harker diagrams</h3>
<p><b>Harker Diagrams (oxides vs SiO<sub>2</sub>)</b>: every selected oxide (or trace element) is plotted against SiO<sub>2</sub> in its own
panel, three or four panels per row with a shared SiO<sub>2</sub> axis (Harker 1909). SiO<sub>2</sub> is found by name among the selected
columns; otherwise X is used. Recalculate analyses volatile-free first. Try Help &gt; Example Data &gt; Major oxides.</p>
<h3>Frost et al. granite classification</h3>
<p>Frost et al. (2001) classify granitoids in three steps. <b>Frost: Fe-number vs SiO<sub>2</sub></b>: FeOt/(FeOt + MgO) against
SiO<sub>2</sub>; the line 0.486 + 0.0046 &times; SiO<sub>2</sub> separates ferroan from magnesian rocks (Fe<sub>2</sub>O<sub>3</sub> is
added as 0.8998 &times; Fe<sub>2</sub>O<sub>3</sub>). <b>Frost: MALI vs SiO<sub>2</sub></b>: the modified alkali-lime index
Na<sub>2</sub>O + K<sub>2</sub>O &minus; CaO against SiO<sub>2</sub>, with the three quadratic boundaries separating alkalic, alkali-calcic,
calc-alkalic and calcic rocks. Boundaries are drawn for SiO<sub>2</sub> 50-77 wt%, with the equations used in GCDkit. The third step,
alumina saturation, is the Shand diagram below.</p>
<h3>Shand alumina saturation diagram</h3>
<p><b>Shand A/CNK vs A/NK</b>: molar A/CNK = Al<sub>2</sub>O<sub>3</sub>/(CaO + Na<sub>2</sub>O + K<sub>2</sub>O) against
A/NK = Al<sub>2</sub>O<sub>3</sub>/(Na<sub>2</sub>O + K<sub>2</sub>O), calculated from wt% columns named Al2O3, CaO, Na2O and K2O
(molar masses 101.96, 56.08, 61.98 and 94.20). Lines at A/CNK = 1 and A/NK = 1 separate metaluminous, peraluminous and peralkaline rocks
(Shand 1943; Maniar &amp; Piccoli 1989); the dashed line at A/CNK = 1.1 separates I- and S-type granites (Chappell &amp; White 1974).
If the indices are already calculated, give A/CNK as X and A/NK as Y. CaO is not corrected for apatite.</p>
<h3>AFM and tectonic discrimination diagrams</h3>
<p><b>AFM (Irvine &amp; Baragar)</b>: A = Na<sub>2</sub>O + K<sub>2</sub>O, F = FeO total (Fe<sub>2</sub>O<sub>3</sub> is added as 0.8998 &times; Fe<sub>2</sub>O<sub>3</sub>),
M = MgO, in wt%, with the tholeiitic / calc-alkaline boundary tabulated by Irvine &amp; Baragar (1971, p. 547). Columns named Na2O, K2O,
FeOt (FeO*, FeO), Fe2O3 and MgO are found by name. Use it for subalkaline rocks. <b>Pearce Granite</b>: the four diagrams of Pearce et al.
(1984), Rb against Y+Nb, Nb against Y, Rb against Yb+Ta and Ta against Yb, on log axes in ppm, separating syn-collisional (syn-COLG),
volcanic-arc (VAG), within-plate (WPG) and ocean-ridge (ORG) granites; dashed lines bound anomalous ridge granites. Select the Rb, Y, Nb,
Yb and Ta columns; the sums are formed for you. Boundaries as used in GCDkit (Janou&#353;ek et al. 2006), except that the first Nb vs Y line starts at Nb = 2000 at Y = 1, as in GeoPyTool (GCDkit has 200).</p>
<h3>Pyroxene and ultramafic diagrams</h3>
<p><b>Pyroxene Quadrilateral (Wo-En-Fs)</b>: the En-Fs-Di-Hd part of the triangle with the Morimoto (1988) names (Wo 45, 20 and 5;
Di/Hd and En/Fs split at Mg/(Mg+Fe) = 0.5). <b>Ultramafic Ol-Opx-Cpx (IUGS)</b>: dunite, harzburgite, lherzolite, wehrlite and the
pyroxenites from modal olivine, orthopyroxene and clinopyroxene (Ol 90, 40 and 10; 5% and 90% pyroxene lines).</p>
<h3 id='mineralformula'>Mineral formulae from microprobe analyses</h3>
<p><b>Column > Mineral Formula from Oxides (apfu)</b> turns oxide wt% columns (SiO2, TiO2, Al2O3, Cr2O3, FeO or FeOt, Fe2O3, MnO, MgO,
CaO, Na2O, K2O, NiO, P2O5 ...) into cations per formula unit on an oxygen basis: olivine 4, pyroxene 6, garnet 12, spinel 4,
feldspar 8, amphibole 23, mica 22, ilmenite 3, or any number. Moles of each oxide are multiplied by the oxygen basis divided by the
total oxygen. The <b>Fe3+ estimate</b> can be: none (all Fe as Fe2+); charge balance
to a cation total (Droop 1987: pyroxene 4, garnet 8, spinel and magnetite 3, ilmenite 2, or any total for other minerals); all Fe as Fe3+
(the default for feldspar, epidote, hematite and titanite, where iron is ferric); a fixed Fe3+/total Fe ratio, for minerals whose
Fe3+ cannot be found by stoichiometry, such as micas and chlorite (enter a measured ratio, e.g. from Mossbauer or XANES); or, for
amphibole, the 13eCNK/15eNK mean below. FeO is recast as Fe2O3 for the ferric part before the oxygen normalisation. For amphibole the default <b>Fe3+ estimate</b> is the scheme of Holland &amp; Blundy (1994, Appendix B): on 23 O with all Fe as FeO
(cation sum &Sigma;), the factor f that renormalises the cations is the average of the smallest upper bound, f<sub>A</sub> =
min(16/&Sigma;, 8/Si, 15/(&Sigma; &minus; Na &minus; K), 2/Ca, 1), and the largest lower bound, f<sub>B</sub> = max(8/(Si + Al), 15/(&Sigma; &minus; K),
12.9/(&Sigma; &minus; Na &minus; K &minus; Ca), 36/(46 &minus; Al &minus; Si &minus; Ti), 1 &minus; Fe/46); every cation is multiplied by f and
Fe<sup>3+</sup> = 46(1 &minus; f). (The paper prints the ninth bound as 36/(46 + Al + Si + Ti); the constraint it stands for, Fe<sup>3+</sup>
&le; 2 &minus; Al<sup>VI</sup> &minus; Ti, gives the minus signs used here.) This is the recalculation the Holland &amp; Blundy thermometers were
calibrated with. The mean of the 13eCNK and 15eNK normalisations is also offered. When a cation total is given (pyroxene 4, garnet 8, spinel 3,
ilmenite 2; olivine has none by default because its Fe3+ is negligible), total Fe is split into Fe3+ and
Fe2+ by charge balance (Droop 1987): Fe3+ = 2X(1 - T/S), where X is the number of oxygens, T the ideal and S the calculated cation
total; an analysis with fewer cations than T gets no Fe3+ and stays on the oxygen basis. The command adds apfu columns, the cation sum, Mg# and end-members: Fo-Fa for olivine, Wo-En-Fs for pyroxene (Morimoto 1988)
An-Ab-Or for feldspar, Alm-Prp-Sps-Grs-Adr-Uv for garnet (the Ca share split by Fe3+ and Cr against Al in the Y site), Cr# = 100Cr/(Cr+Al), Fe3+# = 100Fe3+/(Fe3++Cr+Al) and Fe2+# for spinel, Ilm-Gk-Pph-Hem for ilmenite (hematite counted as two Fe3+), for amphibole the site allocation on 23 O (T Si, AlIV, AlVI, C Ti, B Ca, B Na, A Na+K) and the name of calcic amphiboles from Si, A-site occupancy and Mg# (Leake et al. 1997: tremolite, actinolite, magnesio-hornblende, tschermakite, edenite, pargasite, hastingsite, kaersutite and their Fe equivalents; sodic and sodic-calcic amphiboles are named by group only), and for mica AlIV, AlVI, the octahedral sum, Ann-Phl, Ms-Pg-Mrg (interlayer) and the group (trioctahedral biotite at 5 or more octahedral cations, dioctahedral white mica at 4.5 or fewer). Amphibole names use Fe3+ only if Fe2O3 is given; with all Fe as FeO, Mg# is a minimum. The results are ready for the pyroxene and feldspar diagrams. All columns are added as one undo step.</p>
<h3>Values below detection</h3>
<p>In spider diagrams, a cell such as '&lt;0.05' is drawn at half the detection limit with an open down-pointing triangle, and
the note on the plot says so. Text without a number (e.g. 'bdl', 'n.d.') still leaves a gap bridged by a dotted line.</p>
<h3>Feldspar and soil texture triangles</h3>
<p><b>Feldspar Ternary (An-Ab-Or)</b>: end-members in mol% (Ab = Na, Or = K, An = Ca on a cation basis), anorthite at the top. The fields
name the plagioclase series (albite, oligoclase, andesine, labradorite, bytownite, anorthite at An 10, 30, 50, 70 and 90) and the alkali
feldspars (anorthoclase, K-feldspar), after Deer, Howie &amp; Zussman (1992). <b>Soil Texture (USDA)</b>: sand, silt and clay in %, clay at
the top, with the twelve USDA texture classes. For both, columns named after the corners (Ab, Or, An; Sand, Silt, Clay) are found in
any order, and rows are normalised to 100%.</p>
<h3>Ternary and Piper diagrams</h3>{S_PIPER}
<p>Ternary diagrams normalise each row to 100% and show 0-100% ticks on every edge. The Piper diagram needs six columns in meq/L:
Ca (X), Mg, Na+K, Cl, SO4, HCO3+CO3. <b>Column > Convert Ions mg/L to meq/L</b> divides by the equivalent weights
(Ca 20.04, Mg 12.15, Na 22.99, K 39.10, HCO<sub>3</sub> 61.02, CO<sub>3</sub> 30.00, Cl 35.45, SO<sub>4</sub> 48.03, NO<sub>3</sub> 62.00, F 19.00).</p>
""")

H.append(f"""
<h2 id='projects'>15. Projects, layouts and reports</h2>
<p><b>File > Save Project</b> (Ctrl+S) stores everything in one <code>.pbp</code> file: workbooks (with column roles, units, formulas
and masks), matrixbooks, graphs (with their style, fits and annotations), layouts, reports and Project Explorer folders. The file is
a ZIP archive holding <code>project.json</code> (the structure), one CSV per sheet (numbers written with 17 significant digits; text
columns kept as text) and one NumPy file per matrix. It is first written to a temporary file and then swapped in, so a crash
while saving cannot damage the previous version. Files are checked before anything is closed when a project is opened.</p>
""")

H.append(f"""
<h2 id='scripting'>16. Python console and scripting</h2>
{S_CONSOLE}
<p><b>View > Python Console</b> (Ctrl+Shift+P) runs Python with access to your data. Type <code>pb.help()</code> for the list:</p>
<pre>{esc(CON.HELP)}</pre>
<p><b>File > Run Python Script</b> runs a script file; <b>Tools > Add Python Script to Menu and Toolbar</b> puts your own scripts on the Tools menu and the
user-scripts toolbar. Scripts run with full Python, like any program you run yourself.</p>
""")

H.append(f"<h2 id='examples'>17. Example data</h2><p><b>Help > Example Data</b> opens each example in a new workbook with its columns "
         f"set up and draws its main graph; the Plot Gallery's <b>Open example data for this plot</b> does the same for the selected type. "
         f"<b>Save All Example Files to a Folder</b> copies the CSV files so you can open them in Excel. All values are synthetic, "
         f"made up to look realistic for learning; they are not measurements.</p>{examples_table()}")

H.append(f"""
<h2 id='help'>18. Help, feedback and settings</h2>
<p><b>Help > User Manual</b> (F1) opens this manual with a table of contents and search; <b>Save User Manual as PDF</b> writes it as
a PDF. <b>Help > Keyboard Shortcuts</b> (Ctrl+/) lists the keys. <b>Help > Start Page</b> reopens the Start page.</p>
<h3>Send Feedback</h3>{S_FEEDBACK}
<p>Choose the type (bug, feature request, question ...), write a subject and message, and optionally your e-mail for a reply and
the program and system versions. <b>Send by e-mail</b> opens your e-mail program with the message addressed to the author, ready
for you to read and send; <b>Copy</b> and <b>Save as file</b> are alternatives. PlotBench never sends anything by itself.</p>
<h3>Preferences</h3><p><b>Edit > Preferences</b>: digits shown in sheets, undo levels, and whether the console opens at start.</p>
""")

H.append(f"""
<h2 id='inside'>19. How PlotBench works inside</h2>
<p>PlotBench is written in Python 3. The window and dialogs use Qt (PySide6); graphs are drawn with Matplotlib; calculations use
NumPy, SciPy and pandas. The installer bundles Python and these libraries with PyInstaller, so nothing else needs to be installed.</p>
<h3>Data flow</h3><ol><li><b>Worksheet</b> (<code>sheets.Sheet</code>): a pandas DataFrame plus column roles, metadata, formulas and masks. A Qt
table model shows it; edits go through the model, which records undo steps (a single cell, or a snapshot of the sheet).</li>
<li><b>Change notification</b>: after an edit the sheet recalculates its formula columns in dependency order and asks the main
window to redraw the graphs that use it. Redraws are collected for a short moment so typing does not redraw on every key.</li>
<li><b>Graph</b> (<code>graphs.GraphWindow</code>): a small description (the 'spec': plot type, book, sheet, X, Y columns, style,
annotations) plus fit curves. Drawing reads the current data, calls the plot-type function, adds fits, error bars and annotations,
then applies the style. Because the spec refers to columns rather than copies, graphs always show the current data, and the same
spec is what is saved in projects.</li>
<li><b>Live preview</b> (<code>live.py</code>): dialogs watch their inputs; 80 ms after the last change they apply the values to a copy
of the graph's spec and redraw. OK or Apply stores the state before the dialog as one undo step; Cancel restores it.</li></ol>
<h3>Undo</h3><p>Sheets keep a stack of snapshots (or single-cell changes); graphs keep snapshots of their spec and fits, so styling,
fits, annotations and dragged positions can be undone and redone. The number of levels is set in Preferences.</p>
<h3>Numbers and precision</h3><p>Values are stored as 64-bit floating point. The sheet shows 6 significant digits, but editing,
copying and saving use the full value; projects store 17 significant digits, which reproduce every double exactly.</p>
<h3>Security</h3><p>Formulas, conditions and user fit functions are checked against a whitelist of syntax and functions before
they run (see <a href='#formulas'>Column formulas</a>). Projects contain only data and settings, never code. Projects are saved
atomically (temporary file, then rename).</p>
<h3>Modules</h3>{modules()}
<h3>Testing and build</h3><p>Every analysis module has a self-test with known answers, run before each build; the packaged program
then runs its own self-test (every export format, the libraries that load late, the main window, an example graph and the PDF
manual) before the installer is made with Inno Setup.</p>
""")

H.append(f"<h2 id='menuref'>20. Menu reference</h2><p>Every menu command (the Plot menu is described in the <a href='#plotref'>Plot type reference</a>).</p>{menu_reference()}")
H.append(f"<h2 id='keys'>21. Keyboard shortcuts</h2>{shortcuts()}")
H.append(f"<h2 id='refs'>22. References</h2>{references()}<p align='center' style='color:gray'>PlotBench {V}. Manual by Kishan Tiwari.</p></body></html>")

(OUT / "manual.html").write_text("\n".join(H), encoding="utf-8")
print("manual:", OUT / "manual.html", len(SHOTS), "screenshots,", len(list((IMG / "plots").glob("*.png"))), "plot thumbnails")
if "--pdf" in sys.argv:
    out = sys.argv[sys.argv.index("--pdf") + 1]; HW.save_manual_pdf(out); print("pdf:", out)
w.dirty = False; w.close()
