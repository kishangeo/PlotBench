"""Fixes from the PlotBench 1.31.0 comprehensive review (R1-R5). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import unittest
from unittest import mock
import numpy as np
from plotbench import fetioxide as FT, thermobaro as TB, whatsnew


class Review1310Tests(unittest.TestCase):
    def test_r1_nan_node_skipped(self):
        # NaN at the cold end used to make brentq fail; the sign change on the warm side must still be found
        f = lambda spn, rhm, T, P, s: np.nan if T < 900 else T - 1200.0
        with mock.patch.object(FT, "exchange_dG", f), mock.patch.object(FT, "log_fo2", lambda *a: -10.0):
            T, lf, _ = FT.two_oxide(None, None)
        self.assertAlmostEqual(T, 1200 - 273.15, places=1)

    def test_r2_steep_pair_converges(self):
        # T = 1000 + 30 P, P = 40 - 0.04 T: cross-slope 1.2, undamped iteration diverges
        def comp(m, cols, arr, ox, n=None):
            return 1000 + 30 * np.asarray(cols["P (kbar)"], float) if m == "t" else 40 - 0.04 * np.asarray(cols["T (C), if no column"], float)
        with mock.patch.object(TB, "compute", comp):
            T, P, _ = TB.solve_pt("t", "p", {}, None, None, p0=np.array([10.0]))
        self.assertTrue(np.isfinite(P).all()); self.assertAlmostEqual(float(P[0]), 0 + (40 - 40) / 2.2 + 0.0, delta=0.05)

    def test_r4_absolute_sd_widens(self):
        def comp(m, cols, arr, ox, n=None):
            if m == "t": return 1000 + 30 * np.asarray(arr("H2O"), float) + 0 * np.asarray(cols["P (kbar)"], float)
            return np.full(np.shape(cols["T (C), if no column"]), 5.0)
        arr = lambda c: np.array([2.0, 2.0])
        with mock.patch.object(TB, "compute", comp):
            a = TB.solve_pt_mc("t", "p", {"Liquid H2O (wt%)": "H2O"}, arr, lambda p=False: {}, n=60)
            b = TB.solve_pt_mc("t", "p", {"Liquid H2O (wt%)": "H2O"}, arr, lambda p=False: {}, n=60, num_sd={"Liquid H2O (wt%)": 1.0})
        self.assertGreater(b[0][0], 5 * a[0][0])

    def test_r5_changelog_found(self):
        self.assertIsNotNone(whatsnew.changelog_path())


if __name__ == "__main__":
    unittest.main()
