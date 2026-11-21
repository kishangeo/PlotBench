"""Fixes and features from the PlotBench 1.32.0 rebuild review. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import unittest
from unittest import mock
import numpy as np
from plotbench import thermobaro as TB, petro_ui as PU, fetioxide as FT
from plotbench.ui3 import calibrate_2d


class Rebuild1320Tests(unittest.TestCase):
    def test_r1_pole_is_not_a_root(self):
        # g(p) = P(T(p)) - p = 1 / (p - 5): changes sign at the pole p = 5 but has no root; the row must stay blank
        def comp(m, cols, arr, ox, n=None):
            if m == "t": return np.asarray(cols["P (kbar)"], float) * np.ones(1)
            t = np.asarray(cols["T (C), if no column"], float)
            with np.errstate(all="ignore"): return t + 1.0 / (t - 5.0)
        with mock.patch.object(TB, "compute", comp):
            T, P, _ = TB.solve_pt("t", "p", {}, None, None, p0=np.array([7.0]))
        self.assertTrue(np.isnan(P[0]))

    def test_r2_trapz_available(self):
        import plotbench  # noqa: F401  (the package keeps np.trapz on NumPy 2)
        self.assertAlmostEqual(float(np.trapz([0, 1, 2], [0, 1, 2])), 2.0)

    def test_r3_envelope_from_fetioxide(self):
        c = PU.fe_ti_curves([900.0], [1.0]); x = c["log(Mg/Mn) Ilm (line)"]
        np.testing.assert_allclose(c["B&H 1988 +2s"], FT.BH88_UP[0] * x + FT.BH88_UP[1])
        self.assertGreaterEqual(PU.fe_ti_curves([-500.0])["Buffer T (C)"][0], -200.0)

    def test_r4_tilted_scan(self):
        a = np.radians(2.5); R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        px = lambda x, y: R @ np.array([100 + 8 * x, 500 - 4 * y])  # data -> pixels: scale, flip Y, rotate 2.5 degrees
        f = calibrate_2d([px(0, 0), px(50, 0), px(0, 0), px(0, 100)], [0, 50, 0, 100])
        X, Y = f([px(50, 100), px(10, 30)])
        np.testing.assert_allclose(X, [50, 10], atol=1e-9); np.testing.assert_allclose(Y, [100, 30], atol=1e-9)
        f = calibrate_2d([px(1, 1), px(100, 1), px(1, 1), px(1, 10)], [1, 100, 1, 10], logx=False, logy=False)
        self.assertAlmostEqual(float(f([px(50, 5)])[0][0]), 50.0)

    def test_pt_reference_lines(self):
        c = PU.pt_reference(900, 12)
        for r in ("Ky = And", "Ky = Sil", "And = Sil"):
            t, p = c[f"{r} T (C)"], c[f"{r} P (kbar)"]; ok = np.isfinite(t)
            self.assertAlmostEqual(t[ok][0], 550.0); self.assertAlmostEqual(p[ok][0], 4.5)
        t, p = c["Geotherm 20 C/km T (C)"], c["Geotherm 20 C/km P (kbar)"]; ok = np.isfinite(t) & (p > 0)
        np.testing.assert_allclose(t[ok] / (p[ok] / PU.RHO_G), 20.0)


if __name__ == "__main__":
    unittest.main()
