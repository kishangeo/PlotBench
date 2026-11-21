"""PlotBench. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
import numpy as _np

if not hasattr(_np, "trapz"): _np.trapz = _np.trapezoid  # NumPy 2 removed trapz; every caller keeps working
