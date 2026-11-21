"""Formula autocomplete and point-and-click references in the cell editor. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import unittest

import numpy as np
import pandas as pd

from plotbench import formula_edit as FE


class FormulaTextTests(unittest.TestCase):
    def test_logic(self):
        FE._demo()
        self.assertIn("AVERAGE", FE.suggest("av")[0]); self.assertEqual(FE.suggest("zz"), ([], []))


class FormulaEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        from plotbench import app as A
        cls.w = A.Main(); cls.w.show()

    def _sheet(self):
        self.w.new_book(pd.DataFrame({"A": [1.0, 2.0, 3.0, 4.0], "B": [10.0, 20.0, 30.0, 40.0], "C": [np.nan] * 4}))
        return self.w.active("book").current()

    def _edit(self, sh, r, c):
        from PySide6.QtWidgets import QLineEdit
        from plotbench.sheets import HEAD
        idx = sh.model.index(r + HEAD, c); sh.view.setCurrentIndex(idx); sh.view.edit(idx); self.app.processEvents()
        ed = [e for e in sh.view.viewport().findChildren(QLineEdit) if e.isVisible() and hasattr(e, "_assist") and not e._assist.closed][-1]
        ed.setText(""); ed.setFocus(); self.app.processEvents(); return ed

    def _mouse(self, sh, kind, r, c, ctrl=False):
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import Qt, QEvent, QPointF
        from plotbench.sheets import HEAD
        rect = sh.view.visualRect(sh.model.index(r + HEAD, c)); p = QPointF(rect.center())
        t = {"press": QEvent.MouseButtonPress, "move": QEvent.MouseMove, "release": QEvent.MouseButtonRelease}[kind]
        btn = Qt.LeftButton if kind != "move" else Qt.NoButton
        ev = QMouseEvent(t, p, sh.view.viewport().mapToGlobal(p), btn, Qt.LeftButton if kind != "release" else Qt.NoButton,
                         Qt.ControlModifier if ctrl else Qt.NoModifier)
        self.app.sendEvent(sh.view.viewport(), ev); self.app.processEvents()

    def test_popup_complete_pick_drag_f4_commit(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        sh = self._sheet(); ed = self._edit(sh, 0, 2)
        QTest.keyClicks(ed, "=av"); self.app.processEvents(); a = ed._assist
        self.assertTrue(a.popup.isVisible()); names = [a.popup.item(i).data(Qt.UserRole) for i in range(a.popup.count())]
        self.assertEqual(names[0], "AVERAGE")
        QTest.keyClick(ed, Qt.Key_Tab); self.assertEqual((ed.text(), ed.cursorPosition()), ("=AVERAGE(", 9)); self.assertFalse(a.popup.isVisible())
        self.assertTrue(a.tip.isVisible() and "<b>range</b>" in a.tip.text())
        self._mouse(sh, "press", 0, 0); self._mouse(sh, "release", 0, 0); self.assertEqual(ed.text(), "=AVERAGE(A1")
        self.assertTrue(a.tip.isVisible())  # the argument hint stays up while picking (review F2)
        from PySide6.QtGui import QGuiApplication
        g = (QGuiApplication.screenAt(a.tip.pos()) or QGuiApplication.primaryScreen()).availableGeometry(); self.assertTrue(g.contains(a.tip.geometry()))  # F1: on screen
        self._mouse(sh, "press", 1, 1); self._mouse(sh, "release", 1, 1); self.assertEqual(ed.text(), "=AVERAGE(B2")  # replaced
        self._mouse(sh, "press", 3, 0, ctrl=True); self._mouse(sh, "move", 1, 1); self._mouse(sh, "release", 1, 1)
        self.assertEqual(ed.text(), "=AVERAGE(B2,A2:B4")  # Ctrl adds; the drag is normalised
        self.assertTrue(any(h[5] for h in a.highlights(sh)))
        QTest.keyClick(ed, Qt.Key_F4); self.assertEqual(ed.text(), "=AVERAGE(B2,$A$2:$B$4")
        QTest.keyClick(ed, Qt.Key_Return); self.app.processEvents()
        self.assertEqual(sh.cell_formulas.get(("C", 0)), "=AVERAGE(B2,$A$2:$B$4)")
        self.assertAlmostEqual(float(sh.df.iat[0, 2]), np.mean([20, 2, 3, 4, 20, 30, 40]))
        self.w.undo(); self.app.processEvents(); self.assertNotIn(("C", 0), sh.cell_formulas)

    def test_complete_after_pick_appends(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        sh = self._sheet(); ed = self._edit(sh, 3, 2); QTest.keyClicks(ed, "=SUM(")
        self._mouse(sh, "press", 0, 0); self._mouse(sh, "release", 0, 0); QTest.keyClicks(ed, "+AB"); QTest.keyClick(ed, Qt.Key_Tab)
        self.assertIsNone(ed._assist.picker.span)  # F2: completing a function ends the picked reference
        QTest.keyClick(ed, Qt.Key_Escape); QTest.keyClick(ed, Qt.Key_Escape)

    def test_escape_and_plain_clicks(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        sh = self._sheet(); ed = self._edit(sh, 1, 2)
        QTest.keyClicks(ed, "=S"); a = ed._assist; self.assertTrue(a.popup.isVisible())
        QTest.keyClick(ed, Qt.Key_Escape); self.assertFalse(a.popup.isVisible()); self.assertTrue(ed.isVisible())  # first Esc: popup only
        QTest.keyClick(ed, Qt.Key_Escape); self.app.processEvents(); self.assertNotIn(("C", 1), sh.cell_formulas)
        self.assertIsNone(sh.view._assist())  # editor closed: clicks select cells again
        self._mouse(sh, "press", 2, 0); self._mouse(sh, "release", 2, 0)
        self.assertEqual(sh.view.currentIndex().column(), 0)

    def test_other_sheet_reference(self):
        sh = self._sheet(); book = sh.book; other = book.add_sheet("My data"); other.df = pd.DataFrame({"X": [5.0, 6.0]}); other.model.refresh()
        book.tabs.setCurrentWidget(sh); ed = self._edit(sh, 2, 2); ed.setText("=SUM("); ed.setCursorPosition(5)
        book.tabs.setCurrentWidget(other); self.app.processEvents()
        self._mouse(other, "press", 0, 0); self._mouse(other, "move", 1, 0); self._mouse(other, "release", 1, 0)
        self.assertEqual(ed.text(), "=SUM('My data'!A1:A2"); self.assertIs(book.tabs.currentWidget(), sh)
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        QTest.keyClick(ed, Qt.Key_Return); self.app.processEvents()
        self.assertEqual(sh.cell_formulas.get(("C", 2)), "=SUM('My data'!A1:A2)"); self.assertAlmostEqual(float(sh.df.iat[2, 2]), 11.0)


if __name__ == "__main__":
    unittest.main()
