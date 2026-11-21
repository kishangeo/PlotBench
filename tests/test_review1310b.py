"""Features from the 1.31.0 comprehensive review (sections 4 and 5). Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import unittest
import numpy as np
from plotbench import mineral as MN, thermobaro as TB, petro_ui as PU, workspace as WS, graphs as G


class ReviewFeatureTests(unittest.TestCase):
    def test_every_method_grouped(self):
        self.assertFalse([n for n in TB.METHODS if PU.group(n) == "Other"])

    def test_missing_inputs(self):
        cols = ["Zr (ppm)"]; ox = lambda p=False: {}
        self.assertEqual(PU.missing("Zr-in-rutile (Watson et al. 2006)", cols, ox), [])
        self.assertTrue(PU.missing("Ti-in-zircon (Ferry & Watson 2007)", cols, ox))

    def test_epma_headers(self):
        for h in ("Wt% SiO2", "SiO2(Mass%)", "SiO2 [wt.%]", "SiO2_Cpx"): self.assertEqual(MN.oxide_of(h), "SiO2", h)
        self.assertIn("FeO", MN.collect_oxides(["Wt% FeOt", "Wt% SiO2"], lambda c: np.array([1.0])))

    def test_pt_curves_cross_at_solution(self):
        comp = lambda m, cols, arr, ox, n=None: (1000 + 20 * np.asarray(cols["P (kbar)"], float) * np.ones(2) if m == "t"
                                                 else (np.asarray(cols["T (C), if no column"], float) - 900) / 10 * np.ones(2))
        orig = TB.compute; TB.compute = comp
        try: cur = PU.pt_curves("t", "p", {}, None, None, [1250.0, 1250.0], [12.5, 12.5], [10.0, 10.0], [1.0, 1.0])
        finally: TB.compute = orig
        self.assertEqual(set(cur), {"Thermometer T (C)", "Thermometer P (kbar)", "Barometer T (C)", "Barometer P (kbar)", "1s ellipse T (C)", "1s ellipse P (kbar)"})
        self.assertEqual(len({len(v) for v in cur.values()}), 1)

    def test_buffers_and_bh_band(self):
        c = PU.fe_ti_curves([850.0, 900.0], [0.8, 1.0])
        self.assertTrue(np.all(c["log fO2 MH"] > c["log fO2 NNO"]) and np.all(c["log fO2 NNO"] > c["log fO2 FMQ"]))
        self.assertTrue(np.all(c["B&H 1988 +2s"] > c["B&H 1988 equilibrium"]))

    def test_dark_canvas_and_templates(self):
        WS._demo()
        self.assertTrue(any(k.startswith("Journal: Nature") for k in G.THEMES))


if __name__ == "__main__":
    unittest.main()
