"""Regression tests for data safety (project open, imports, formulas). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Run: python -m unittest discover -s tests -v   (Qt runs off screen)."""
import os, sys, tempfile, unittest, zipfile, json
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["APPDATA"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np, pandas as pd
from PySide6.QtWidgets import QApplication, QMessageBox
from plotbench import app as M, formats as F, cellformula as CF

QA = QApplication.instance() or QApplication([])
TMP = Path(tempfile.mkdtemp())


def main_window():
    w = M.Main(); w.show(); QA.processEvents(); return w


def close(w): w.dirty = False; w._bulk_close = True; w.close()


class ProjectTests(unittest.TestCase):
    def test_text_labels_survive_save_and_open(self):
        w = main_window()
        df = pd.DataFrame({"Label": ["NA", "NULL", "nan", "x", "1.5"], "Value": [1.0, np.nan, 3.0, 4.0, 5.0]})
        w.new_book(df, "T"); fn = str(TMP / "labels.pbp"); w.project_path = fn; w.save_project(); close(w)
        w = main_window(); w.open_project(fn)
        sh = next(x for x in w.windows() if x.kind == "book" and x.name == "T").current()
        self.assertEqual(list(sh.df["Label"][:4]), ["NA", "NULL", "nan", "x"]); self.assertEqual(sh.df["Label"][4], 1.5)
        self.assertTrue(np.isnan(sh.df["Value"][1])); self.assertEqual(sh.df["Value"][4], 5.0); close(w)

    def _good_project(self):
        w = main_window(); w.new_book(pd.DataFrame({"A": [1.0, 2.0]}), "Keep"); fn = str(TMP / "good.pbp"); w.project_path = fn; w.save_project(); return w, fn

    def test_cancel_keeps_unsaved_work(self):
        w, fn = self._good_project(); w.new_book(pd.DataFrame({"B": [3.0]}), "Unsaved"); w.dirty = True
        orig = QMessageBox.question; QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Cancel)
        try: w.open_project(fn)
        finally: QMessageBox.question = orig
        self.assertIn("Unsaved", [x.name for x in w.windows()]); close(w)

    def test_discard_opens(self):
        w, fn = self._good_project(); w.new_book(pd.DataFrame({"B": [3.0]}), "Unsaved"); w.dirty = True
        orig = QMessageBox.question; QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Discard)
        try: w.open_project(fn)
        finally: QMessageBox.question = orig
        self.assertNotIn("Unsaved", [x.name for x in w.windows()]); close(w)

    def test_damaged_payload_leaves_windows_open(self):
        w, fn = self._good_project(); bad = str(TMP / "bad.pbp")
        with zipfile.ZipFile(fn) as z, zipfile.ZipFile(bad, "w") as o:
            meta = json.loads(z.read("project.json")); o.writestr("project.json", json.dumps(meta))
            for n in z.namelist():
                if n.endswith(".npy"): o.writestr(n, b"not an array")
        meta["windows"].append({"kind": "matrix", "name": "MBad", "sheets": [{"name": "M", "npy": "bad.npy", "extent": None}]})
        with zipfile.ZipFile(bad, "w") as o:
            o.writestr("project.json", json.dumps(meta)); o.writestr("bad.npy", b"garbage")
        n0 = len(w.windows())
        with self.assertRaises(ValueError): w.open_project(bad)
        self.assertEqual(len(w.windows()), n0); close(w)

    def test_failed_build_restores_session(self):
        """A project whose graph fails to draw leaves the previous session exactly as it was."""
        w = main_window(); w.new_book(pd.DataFrame({"A": [1.0, 2.0]}), "Other")
        g = w.new_graph(w.win("Other").current(), "Scatter", "A", ["A"]); fn = str(TMP / "withgraph.pbp"); w.project_path = fn; w.save_project(); close(w)
        w = main_window(); w.new_book(pd.DataFrame({"Mine": [7.0, 8.0, 9.0]}), "Current"); w.win("Current").current().mask = {("Mine", 1)}
        before = sorted(x.name for x in w.windows()); w.dirty = False
        orig = M.GraphWindow.draw

        def boom(self, *a, **k): raise RuntimeError("draw failed")
        M.GraphWindow.draw = boom
        try:
            with self.assertRaises(RuntimeError): w.open_project(fn)
        finally: M.GraphWindow.draw = orig
        self.assertEqual(sorted(x.name for x in w.windows()), before)
        sh = w.win("Current").current(); self.assertEqual(list(sh.df["Mine"]), [7.0, 8.0, 9.0]); self.assertIn(("Mine", 1), sh.mask)
        self.assertIsNone(w.project_path); close(w)

    def test_archive_limits(self):
        dup = str(TMP / "dup.pbp")
        with zipfile.ZipFile(dup, "w") as o:
            o.writestr("project.json", "{}")
            import warnings
            with warnings.catch_warnings(): warnings.simplefilter("ignore"); o.writestr("project.json", "{}")
        with self.assertRaises(ValueError): M.read_project(dup)
        big = str(TMP / "big.pbp"); old = dict(M.PROJECT_LIMITS)
        with zipfile.ZipFile(big, "w", zipfile.ZIP_DEFLATED) as o: o.writestr("project.json", json.dumps({"windows": []})); o.writestr("x.csv", "0" * 5000)
        M.PROJECT_LIMITS["total"] = 1000
        try:
            with self.assertRaises(ValueError): M.read_project(big)
        finally: M.PROJECT_LIMITS.update(old)
        notzip = str(TMP / "nojson.pbp")
        with zipfile.ZipFile(notzip, "w") as o: o.writestr("other.txt", "x")
        with self.assertRaises(ValueError): M.read_project(notzip)

    def test_num_or_text(self):
        self.assertEqual(M._num_or_text("1.5"), 1.5); self.assertEqual(M._num_or_text("nan"), "nan"); self.assertEqual(M._num_or_text("inf"), "inf")
        self.assertEqual(M._num_or_text("001"), "001")


class ImportTests(unittest.TestCase):
    def test_same_named_datasets_kept(self):
        import h5py
        fn = str(TMP / "two.h5")
        with h5py.File(fn, "w") as h: h["group1/SiO2"] = [1.0, 2.0]; h["group2/SiO2"] = [3.0, 4.0, 5.0]
        df = F.datasets_to_frame(fn, ["group1/SiO2", "group2/SiO2"])
        self.assertEqual(len(df.columns), 2); self.assertEqual(list(df.iloc[:, 1]), [3.0, 4.0, 5.0]); self.assertEqual(df.iloc[1, 0], 2.0)
        with self.assertRaises(ValueError): F.datasets_to_frame(fn, [])


class FormulaTests(unittest.TestCase):
    def test_fact_bounds(self):
        self.assertEqual(CF._fact(5.0), 120.0)
        for v in (171.0, 1e9, -1.0, float("nan")):
            with self.assertRaises(CF.CellError): CF._fact(v)

    def test_formula_length(self):
        with self.assertRaises(CF.CellError): CF.compile_cell("1+" * 1500 + "1")


class ThermobaroTests(unittest.TestCase):
    def test_range_flag_and_monte_carlo(self):
        from plotbench import thermobaro as TB
        w = main_window(); sh = w.new_book(pd.DataFrame({"Ti (ppm)": [10.0, 1000.0]}), "Z").current()
        w.thermobarometry(sh, "Ti-in-zircon (Ferry & Watson 2007)", {"Ti (ppm)": "Ti (ppm)", "a SiO2": 1.0, "a TiO2": 1.0}, mc={"rel": 0.05, "n": 300})
        self.assertEqual(list(sh.df["T Ti-in-Zrn in calibration range"]), ["yes", "no"])
        sd = sh.df["1s T Ti-in-Zrn (C)"].astype(float)[0]
        self.assertAlmostEqual(sd, 4800 * 0.05 / np.log(10) / (5.711 - 1) ** 2, delta=0.8)  # linearised error of the equation
        self.assertTrue(np.isnan(TB.in_range("Ti-in-zircon (Ferry & Watson 2007)", [np.nan], {}, 1)[0]))
        close(w)

    def test_loucks_blank_inputs(self):
        from plotbench import thermobaro as TB
        self.assertTrue(np.all(np.isnan(TB.zircon_dfmq_loucks2020([0, np.nan], [200, 200], [10, 10]))))


class TextFormatTests(unittest.TestCase):
    def test_one_text_formatted_alone(self):
        from plotbench import graphs as G, textfmt as TF
        self.assertEqual(TF.rich("SiO_{2}"), r"SiO$_{\mathregular{2}}$"); self.assertEqual(TF.rich("a_b"), "a_b")
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2, 3], "y": [1.0, 4, 9]}), "T").current()
        g = w.new_graph(sh, "Scatter", "x", ["y"]); QA.processEvents(); ax = g._plot_axes()[0]
        y0, t0 = ax.yaxis.label.get_fontsize(), [t.get_fontsize() for t in ax.get_xticklabels()]
        g._set_text("0|@xlabel", text="Fe^{3+}", size=17, bold=True, rotation=15)
        ax = g._plot_axes()[0]; lab = ax.xaxis.label
        self.assertEqual((lab.get_text(), lab.get_fontsize(), lab.get_fontweight(), lab.get_rotation()), (r"Fe$^{\mathregular{3+}}$", 17, "bold", 15))
        self.assertEqual(ax.yaxis.label.get_fontsize(), y0); self.assertEqual([t.get_fontsize() for t in ax.get_xticklabels()], t0)
        fn = str(TMP / "fmt.pbp"); w.project_path = fn; w.save_project(); w.dirty = False; w.open_project(fn)
        g2 = next(x for x in w.windows() if x.kind == "graph"); self.assertEqual(g2._plot_axes()[0].xaxis.label.get_fontsize(), 17)
        new = w.new_graph(w.win("T").current(), "Line", "x", ["y"]); QA.processEvents(); self.assertIsNotNone(new)  # used to crash
        close(w)


class LetterFormatTests(unittest.TestCase):
    def test_selected_letters_only(self):
        from PySide6.QtGui import QTextCursor
        from plotbench import textfmt as TF
        self.assertEqual(TF.markup(TF.parse(r"Ch_{\b{2}}^{\i{3}} \b{\i{x}}")), r"Ch_{\b{2}}^{\i{3}} \b{\i{x}}")
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2], "y": [1.0, 4]}), "T").current()
        g = w.new_graph(sh, "Scatter", "x", ["y"]); QA.processEvents(); g._set_text("0|@xlabel", text="Sample / CI Chondrite")
        g.select_text("0|@xlabel"); bar = g.tfmt; f = bar.field
        def sel(t):
            i = f.toPlainText().index(t); c = f.textCursor(); c.setPosition(i); c.setPosition(i + len(t), QTextCursor.KeepAnchor); f.setTextCursor(c)
        sel("CI"); bar.bold(); sel("le"); bar.sub(); sel("Chon"); bar.italic()
        self.assertEqual(bar.words(), r"Samp_{le} / \b{CI} \i{Chon}drite")
        self.assertEqual(g._plot_axes()[0].xaxis.label.get_text(), r"Samp$_{\mathregular{le}}$ / $\mathbf{CI}$ $\mathit{Chon}$drite")
        sel("CI"); bar.bold(); self.assertNotIn(r"\b{CI}", bar.words())
        close(w)


class Audit1302Tests(unittest.TestCase):
    def test_annotation_words_reset_and_one_undo_step(self):  # 1.30.2-B
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2], "y": [1.0, 4]}), "T").current()
        g = w.new_graph(sh, "Scatter", "x", ["y"]); g.spec["annotations"] = [{"kind": "text", "x": 1.5, "y": 2.0, "text": "old"}]; g.draw()
        n = len(g.history); g._set_text("@ann|0", text="new", size=14); self.assertEqual(len(g.history), n + 1)
        self.assertEqual(g.spec["annotations"][0]["text"], "old")  # the annotation keeps its own words
        t = lambda: next(x for x in g._plot_axes()[0].texts if str(x.get_gid()).startswith("pbann:"))
        self.assertEqual(t().get_text(), "new"); g._set_text("@ann|0", reset=True); self.assertEqual(t().get_text(), "old"); close(w)

    def test_title_bar_and_graph_properties_agree(self):  # 1.30.2-C
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2], "y": [1.0, 4]}), "T").current()
        g = w.new_graph(sh, "Scatter", "x", ["y"]); g._set_text("0|@xlabel", text="SiO_{2}")
        self.assertEqual(g.spec["style"]["xlabel"], "SiO_{2}"); self.assertEqual(g._plot_axes()[0].get_xlabel(), r"SiO$_{\mathregular{2}}$")
        st = dict(g.spec["style"]); st["xlabel"] = "Silica"; g.set_style(st); self.assertEqual(g._plot_axes()[0].get_xlabel(), "Silica")
        g._set_text("0|@xlabel", reset=True); self.assertEqual(g.spec["style"]["xlabel"], ""); close(w)

    def test_one_row_temperature_column(self):  # 1.30.2-E
        from plotbench import thermobaro as TB
        m = "Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)"
        f = TB.in_range(m, np.array([30.0]), {"T (C) column": np.array([700.0]), "T (C), if no column": 1000.0}, 1)
        self.assertEqual(f[0], 0.0)  # 700 C is below the 900-1400 C calibration, whatever the number box says


class ShapeEditTests(unittest.TestCase):
    """Drawn shapes: click-to-place regions and on-canvas editing with handles."""

    def test_region_nodes_and_handle_editing(self):
        from plotbench import shapes as S
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": np.linspace(0, 10, 11), "y": np.linspace(0, 100, 11)}), "T").current()
        g = w.new_graph(sh, "Scatter", "x", ["y"]); QA.processEvents()

        class Ev:
            def __init__(s, x, y, button=1, dbl=False, key=None):
                s.x, s.y, s.button, s.dblclick, s.key = float(x), float(y), button, dbl, key; ax = g._plot_axes()[0]; s.inaxes = ax
                s.xdata, s.ydata = ax.transData.inverted().transform((x, y)); s.guiEvent = None; s.canvas = g.canvas

        def px(x, y): g.canvas.draw(); return g._plot_axes()[0].transData.transform((x, y))
        g.start_draw("region"); t = g._drawing
        for q in ((2, 20), (5, 80), (8, 20), (9, 90)): t.press(Ev(*px(*q)))
        t.key(Ev(0, 0, key="backspace")); self.assertEqual(len(t.pts), 3)
        t.press(Ev(*px(2.02, 20.3))); a = g.spec["annotations"][0]  # a click on the first node closes the region
        self.assertEqual((a["kind"], a["smooth"], len(a["points"])), ("region", True, 3)); self.assertIsNone(g._drawing)
        n = len(g.history); g.edit_handles(0); e = g._drawing
        e.press(Ev(*px(5, 80))); e.move(Ev(*px(5, 95))); e.release(Ev(0, 0)); self.assertAlmostEqual(a["points"][1][1], 95, delta=0.5)
        mid = g._plot_axes()[0].transData.transform(S.smooth_closed(a["points"], g._plot_axes()[0]))[8]
        e.press(Ev(*mid, dbl=True)); e.release(Ev(0, 0)); self.assertEqual(len(a["points"]), 4)
        e.key(Ev(0, 0, key="delete")); self.assertEqual(len(a["points"]), 3)
        e.key(Ev(0, 0, key="enter")); self.assertIsNone(g._drawing); self.assertEqual(len(g.history), n + 1)  # one undo step
        g.spec["annotations"].append({"kind": "rect", "points": [[2.0, 40.0], [6.0, 60.0]], **S.DEFAULT}); g.draw(); g.edit_handles(1); e = g._drawing
        hs = {k: (x, y) for k, x, y in e.handles()}; self.assertEqual(len(hs), 9)
        e.press(Ev(*hs[("box", 1, 1)])); e.move(Ev(*px(8, 70))); e.release(Ev(0, 0))
        p = np.array(g.spec["annotations"][1]["points"]); self.assertTrue(np.allclose([p[:, 0].max(), p[:, 1].max()], [8, 70], atol=0.3))
        c = e._box()[0]; rot = {k: (x, y) for k, x, y in e.handles()}[("rot",)]; e.press(Ev(*rot)); e.move(Ev(c[0] - 50, c[1] + 50)); e.release(Ev(0, 0))
        self.assertAlmostEqual(g.spec["annotations"][1]["angle"], 45, delta=1); e.stop(); close(w)


class SimpleMenuTests(unittest.TestCase):
    def test_hidden_commands_stay_searchable_and_come_back(self):
        w = main_window(); total = len(w.commands()); n = w.set_simple_menus(True, save=False); self.assertGreater(n, 100)
        self.assertEqual(len(w.commands()), total)  # hidden from the menus, not from the search
        hit = w.search_commands("pivot table"); self.assertTrue(hit and not hit[0][3].isVisible())
        self.assertTrue(all(c[3].isVisible() for c in w.commands() if not c[3].shortcut().isEmpty()))  # shortcuts keep working
        w.set_simple_menus(False, save=False); self.assertTrue(w.search_commands("pivot table")[0][3].isVisible()); close(w)


class UsabilityTests(unittest.TestCase):
    def test_filter_masks_rows_and_is_undone(self):
        w = main_window(); sh = w.new_book(pd.DataFrame({"a": [1.0, 2, 3, 4], "t": ["x", "y", "x", "y"]}), "F").current()
        sh.set_mask([("a", 3)], True); self.assertEqual(sh.set_filter('a > 1 and t == "x"'), 1)
        self.assertTrue(np.isnan(sh.arr("a")[[0, 1, 3]]).all()); self.assertRaises(Exception, sh.set_filter, "nope > 1")
        sh.clear_filter(); self.assertEqual(sh.mask, {("a", 3)}); sh.undo(); self.assertEqual(len(sh.filters), 1); close(w)

    def test_selection_statistics(self):
        from PySide6.QtCore import QItemSelection, QItemSelectionModel
        from plotbench.sheets import HEAD
        w = main_window(); sh = w.new_book(pd.DataFrame({"a": [1.0, 2, 3, 4], "t": ["x", "y", "x", "y"]}), "S").current(); m = sh.model
        sh.view.selectionModel().select(QItemSelection(m.index(HEAD, 0), m.index(HEAD + 3, 1)), QItemSelectionModel.ClearAndSelect)
        st = sh.selection_stats(); self.assertEqual((st["Count"], st["Sum"], st["Max"]), (4, 10.0, 4.0)); close(w)

    def test_axis_bar_sets_range_once_per_undo(self):
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2, 3], "y": [1.0, 4, 9]}), "A").current(); g = w.new_graph(sh, "Line", "x", ["y"])
        g.select_object("y"); n = len(g.history); g.obar.hi.setText("20"); g.obar.set_limit("max", g.obar.hi)
        self.assertEqual(g.spec["style"]["ymax"], "20"); self.assertEqual(len(g.history), n + 1); self.assertEqual(g.bars.currentIndex(), 2)
        g.obar.hi.setText("x"); g.obar.set_limit("max", g.obar.hi); self.assertEqual(g.spec["style"]["ymax"], "20")
        g.select_object("legend"); g.obar.show_leg.setChecked(False); self.assertEqual(g.spec["style"]["legend"], "none"); close(w)

    def test_thermobarometry_column_follows_its_input(self):
        w = main_window(); sh = w.new_book(pd.DataFrame({"Ti (ppm)": [5.0, 10.0]}), "Z").current()
        name = w.thermobarometry(sh, "Ti-in-zircon (Ferry & Watson 2007)", {"Ti (ppm)": "Ti (ppm)", "a SiO2": 1.0, "a TiO2": 1.0}); t0 = sh.arr(name).copy()
        sh.df.loc[0, "Ti (ppm)"] = 50.0; sh.changed(); w.run_ops(); self.assertGreater(sh.arr(name)[0], t0[0] + 50); self.assertAlmostEqual(sh.arr(name)[1], t0[1]); close(w)

    def test_recovery_copy_written_and_removed(self):
        w = main_window(); w.dirty = False; self.assertIsNone(w.autosave())
        if w._autosaves:  # another PlotBench on this machine may hold the recovery lock
            w.mark_dirty(); p = w.autosave(); self.assertTrue(p.exists()); w.drop_recovery(); self.assertFalse(p.exists())
        close(w)


class SecondRoundTests(unittest.TestCase):
    def test_layer_has_its_own_axis_and_joins_the_legend(self):
        w = main_window(); t = np.arange(10.0); sh = w.new_book(pd.DataFrame({"t": t, "a": t, "b": 1000 - t}), "L").current()
        g = w.new_graph(sh, "Line", "t", ["a"]); w.mdi.setActiveSubWindow(g.parentWidget()); w.layers(add={"book": "L", "sheet": "Sheet1", "x": "t", "ys": ["b"]}); g.canvas.draw()
        lay = [a for a in g.fig.axes if getattr(a, "_pb_layer", False)]; self.assertEqual(len(lay), 1); self.assertGreater(lay[0].get_ylim()[0], 900)
        self.assertEqual([x.get_text() for x in g.fig.axes[0].get_legend().get_texts()], ["a", "b"]); g.undo(); self.assertFalse(g.spec.get("layers")); close(w)

    def test_undo_follows_the_order_of_changes_across_windows(self):
        w = main_window(); a = w.new_book(pd.DataFrame({"x": [1.0], "y": [1.0]}), "A").current(); b = w.new_book(pd.DataFrame({"x": [1.0], "y": [5.0]}), "B").current()
        a.snap(); a.df.loc[0, "y"] = 100.0; b.snap(); b.df.loc[0, "y"] = 200.0; w.mdi.setActiveSubWindow(a.book.parentWidget())
        w.undo(); self.assertEqual((a.df.loc[0, "y"], b.df.loc[0, "y"]), (100.0, 5.0)); w.undo(); self.assertEqual(a.df.loc[0, "y"], 1.0)
        w.redo(); w.redo(); self.assertEqual((a.df.loc[0, "y"], b.df.loc[0, "y"]), (100.0, 200.0)); close(w)

    def test_office_files_are_well_formed(self):
        import zipfile
        import xml.dom.minidom as MD
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2], "y": [1.0, 4]}), "O").current(); w.new_graph(sh, "Line", "x", ["y"])
        for kind in ("docx", "pptx"):
            with zipfile.ZipFile(w.send_office(kind, True, str(TMP / f"o.{kind}"))) as z:
                self.assertIsNone(z.testzip()); [MD.parseString(z.read(n)) for n in z.namelist() if n.endswith((".xml", ".rels"))]
                self.assertEqual(len([n for n in z.namelist() if n.endswith(".png")]), 1)
        close(w)

    def test_fit_library_and_new_ranges(self):
        from plotbench import fitlib, thermobaro as TB, analysis as A
        fitlib._demo(); self.assertGreaterEqual(len(A.MODELS), 72)
        self.assertEqual(list(TB.in_range("Zr-in-rutile (Watson et al. 2006)", [400.0, 800.0, 1500.0], {}, 3)), [0.0, 1.0, 0.0])
        self.assertEqual(list(TB.in_range("En-in-clinopyroxene T (Nimis & Taylor 2000)", [1000.0, 1000.0], {"P (kbar)": np.array([30.0, 70.0])}, 2)), [1.0, 0.0])
        self.assertEqual(list(TB.in_range("Al-in-hornblende (Hollister et al. 1987)", [1.0, 5.0], {}, 2)), [0.0, 1.0])


class Audit1310Tests(unittest.TestCase):
    def test_emg_stays_finite_for_nearly_symmetric_peaks(self):
        from plotbench import fitlib
        y = fitlib._emg(np.linspace(0, 10, 50), 0.0, 5.0, 1.0, 1.0, 0.02); self.assertTrue(np.isfinite(y).all()); self.assertAlmostEqual(float(y.max()), 0.3989, places=2)

    def test_layer_without_y_and_bars_on_repeated_x(self):
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0, 4.0]}), "L").current()
        g = w.new_graph(sh, "Line", "x", ["y"]); w.mdi.setActiveSubWindow(g.parentWidget())
        w.layers(add={"book": "L", "sheet": "Sheet1", "x": "x", "ys": []}); g.canvas.draw()  # no crash; said in the corner
        self.assertTrue(any("skipped" in t.get_text() for t in g.fig.axes[0].texts))
        g.spec["layers"] = [{"book": "L", "sheet": "Sheet1", "x": "x", "ys": ["y"], "type": "Column", "yaxis": "right", "xaxis": "bottom"}]; g.draw()
        bars = [p for a in g.fig.axes if getattr(a, "_pb_layer", False) for p in a.patches]; self.assertTrue(bars and min(p.get_width() for p in bars) > 0.5)
        close(w)

    def test_office_and_clipboard_images_carry_no_selection_marks(self):
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [1.0, 2], "y": [1.0, 4]}), "O").current(); g = w.new_graph(sh, "Line", "x", ["y"]); g.canvas.draw()
        clean = w.clean_png(g, 100)[0]; g.select_text("0|@xlabel"); self.assertTrue(g._tsel_marks)
        self.assertEqual(w.clean_png(g, 100)[0], clean)  # the red outline of the selected text is not in it
        locked = TMP / "locked.docx"; locked.mkdir(exist_ok=True)  # a folder in the way stands for a file Word holds open
        from unittest import mock
        with mock.patch.object(M.QMessageBox, "warning") as warn: self.assertIsNone(w.send_office("docx", False, str(locked)))
        warn.assert_called_once(); close(w)

    def test_right_click_does_not_start_a_drag_shape(self):
        w = main_window(); sh = w.new_book(pd.DataFrame({"x": [0.0, 10], "y": [0.0, 10]}), "R").current(); g = w.new_graph(sh, "Line", "x", ["y"]); g.canvas.draw()
        w.mdi.setActiveSubWindow(g.parentWidget()); w.draw_shape("rect"); t = g._drawing; ax = g._plot_axes()[0]

        class E:
            inaxes, xdata, ydata, dblclick, key = ax, 2.0, 2.0, False, None
            def __init__(s, b): s.button = b
        t.press(E(2)); self.assertFalse(t.down); t.press(E(3)); self.assertIsNone(g._drawing); self.assertFalse(g.spec.get("annotations")); close(w)


class ExportTests(unittest.TestCase):
    def test_latex_numbers_masks_labels(self):
        w = main_window()
        sh = w.new_book(pd.DataFrame({"Spot": ["SpotA1", "B"], "Ti (ppm)": [12450.0, 3.0], "s (yErr-)": [1.0, 2.0]}), "L").current()
        sh.mask = {("Ti (ppm)", 1)}
        with open(w.export_latex(str(TMP / "t.tex"))) as fh: t = fh.read()
        self.assertIn("12450", t); self.assertNotIn("e+04", t); self.assertIn("SpotA1", t); self.assertNotIn("SpotA$", t)
        self.assertIn("(yErr-)", t); self.assertIn("\nB &  & 2", t); close(w)  # only the masked cell is blanked


if __name__ == "__main__":
    unittest.main()
