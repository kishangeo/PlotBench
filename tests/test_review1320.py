"""Fixes from the PlotBench 1.32.0 comprehensive review. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import unittest
from unittest import mock
import numpy as np
from plotbench import thermobaro as TB, petro_ui as PU, workspace as WS


class Review1320Tests(unittest.TestCase):
    def test_b_bisection_rescue(self):
        # P(T(p)) = 2p - 5 near the root p = 5: slope 2, so fixed-point iteration runs away; the rescue must find p = 5
        def comp(m, cols, arr, ox, n=None):
            if m == "t": return 1000 + 10 * np.asarray(cols["P (kbar)"], float) * np.ones(2)
            return (np.asarray(cols["T (C), if no column"], float) - 1000) / 5 - 5
        with mock.patch.object(TB, "compute", comp):
            T, P, _ = TB.solve_pt("t", "p", {}, None, None, p0=np.array([7.0, 7.0]))
        np.testing.assert_allclose(P, [5.0, 5.0], atol=1e-3); np.testing.assert_allclose(T, [1050.0, 1050.0], atol=0.05)

    def test_c_correlation_returned_and_tilts_ellipse(self):
        def comp(m, cols, arr, ox, n=None):
            if m == "t": return np.asarray(arr("X"), float) * 100 + 5 * np.asarray(cols["P (kbar)"], float)
            return np.asarray(arr("X"), float) * 2 + 0 * np.asarray(cols["T (C), if no column"], float)
        with mock.patch.object(TB, "compute", comp):
            sT, sP, rho = TB.solve_pt_mc("t", "p", {}, lambda c: np.array([10.0]), lambda p=False: {}, n=80)
        self.assertGreater(rho[0], 0.95)
        orig = TB.compute; TB.compute = lambda m, c, a, o, n=None: np.array([0.0])
        try: cur = PU.pt_curves("t", "p", {}, None, None, [1000.0], [20.0], [10.0], [1.0], rho=[0.9])
        finally: TB.compute = orig
        t, p = cur["1s ellipse T (C)"], cur["1s ellipse P (kbar)"]; ok = np.isfinite(t)
        self.assertGreater(np.corrcoef(t[ok], p[ok])[0, 1], 0.8)

    def test_d_dark_scatter(self):
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import to_rgba
        fig, ax = plt.subplots(); pc = ax.scatter([0, 1], [0, 1], c="k"); WS.dark_canvas(fig)
        self.assertEqual(tuple(pc.get_facecolor()[0]), to_rgba(WS.INK))


if __name__ == "__main__":
    unittest.main()
