"""More functions for the curve-fit library: growth, peaks with a sloping baseline, rational forms, and equations of state and
kinetics used in the Earth and materials sciences. Each entry is (function, first guess from the data), as in analysis.MODELS.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from scipy import special as _sp

from . import analysis as A


def _expgro2(x, y0, A1, t1, A2, t2): return y0 + A1 * np.exp(x / t1) + A2 * np.exp(x / t2)
def _stretched(x, y0, A, tau, beta): return y0 + A * np.exp(-(np.abs(x) / tau) ** beta)
def _explin(x, y0, A, t, b): return y0 + A * np.exp(-x / t) + b * x
def _logistic3(x, L, k, x0): return L / (1 + np.exp(-k * (x - x0)))
def _richards(x, L, k, x0, nu): return L / (1 + nu * np.exp(-k * (x - x0))) ** (1 / nu)
def _bertalanffy(x, Linf, k, x0): return Linf * (1 - np.exp(-k * (x - x0)))
def _avrami(x, A, k, n): return A * (1 - np.exp(-(k * np.abs(x)) ** n))
def _gauss_line(x, a, b, xc, w, H): return a + b * x + H * np.exp(-0.5 * ((x - xc) / w) ** 2)
def _lorentz_line(x, a, b, xc, w, H): return a + b * x + H / (1 + ((x - xc) / w) ** 2)
def _pearson7(x, y0, xc, w, H, m): return y0 + H / (1 + ((x - xc) / w) ** 2 * (2 ** (1 / m) - 1)) ** m
def _emg(x, y0, xc, w, A, t0):
    u = (np.asarray(x, float) - xc) / w; z = (w / t0 - u) / np.sqrt(2)
    with np.errstate(over="ignore", invalid="ignore"):
        direct = np.exp(0.5 * (w / t0) ** 2 - u * w / t0) * _sp.erfc(z)  # fine for z <= 0
        scaled = np.exp(-0.5 * u * u) * _sp.erfcx(np.maximum(z, 0))       # the same for z > 0, without inf * 0
    return y0 + A / (2 * t0) * np.where(z > 0, scaled, direct)
def _bigauss(x, y0, xc, H, w1, w2): return y0 + H * np.exp(-0.5 * ((x - xc) / np.where(x < xc, w1, w2)) ** 2)
def _gauss2(x, y0, xc1, w1, H1, xc2, w2, H2): return y0 + H1 * np.exp(-0.5 * ((x - xc1) / w1) ** 2) + H2 * np.exp(-0.5 * ((x - xc2) / w2) ** 2)
def _lorentz2(x, y0, xc1, w1, H1, xc2, w2, H2): return y0 + H1 / (1 + ((x - xc1) / w1) ** 2) + H2 / (1 + ((x - xc2) / w2) ** 2)
def _bwf(x, y0, xc, w, H, q): s = (x - xc) / w; return y0 + H * (1 + s / q) ** 2 / (1 + s ** 2)
def _rational(x, a, b, c): return (a + b * x) / (1 + c * x)
def _hyperbola(x, a, b): return a + b / x
def _reciprocal(x, a, b): return 1 / (a + b * x)
def _freundlich(x, K, n): return K * np.abs(x) ** (1 / n)
def _twosite(x, B1, K1, B2, K2): return B1 * x / (K1 + x) + B2 * x / (K2 + x)
def _damped_sine(x, y0, A, t0, w, xc): return y0 + A * np.exp(-x / t0) * np.sin(np.pi * (x - xc) / w)
def _vft(x, A, B, C): return A + B / (x - C)
def _bm3(x, V0, K0, Kp): r = V0 / x; return 1.5 * K0 * (r ** (7 / 3) - r ** (5 / 3)) * (1 + 0.75 * (Kp - 4) * (r ** (2 / 3) - 1))
def _vinet(x, V0, K0, Kp): f = (x / V0) ** (1 / 3); return 3 * K0 * (1 - f) / f ** 2 * np.exp(1.5 * (Kp - 1) * (1 - f))
def _erfc_profile(x, C0, Cs, L): return C0 + (Cs - C0) * _sp.erfc(x / L)
def _quadratic(x, a, b, c): return a + b * x + c * x ** 2
def _cubic(x, a, b, c, d): return a + b * x + c * x ** 2 + d * x ** 3
def _sqrt(x, a, b): return a + b * np.sqrt(np.abs(x))


def _pk(x, y):
    """(baseline, centre, sigma-like width, height) of the largest peak."""
    i = int(np.argmax(y)); y0 = float(np.min(y)); h = float(y[i] - y0); lo = hi = i
    while lo > 0 and y[lo - 1] - y0 >= h / 2: lo -= 1  # the run of points above half height around the top (not a second peak)
    while hi < len(y) - 1 and y[hi + 1] - y0 >= h / 2: hi += 1
    fw = float(x[hi] - x[lo]) if hi > lo else float(np.ptp(x)) / 10
    return y0, float(x[i]), (fw / 2.355) or (float(np.ptp(x)) / 20 or 1.0), h or 1.0


def _two(x, y):
    y0, xc, w, h = _pk(x, y); far = np.abs(x - xc) > 2.5 * w
    x2 = float(x[far][np.argmax(y[far])]) if far.any() else xc + 3 * w
    h2 = float(np.max(y[far]) - y0) if far.any() else h / 2
    return y0, xc, w, h, x2, w, h2 or h / 2


def _eos(x, y):
    """V0 just above the largest volume; K0 from the slope of P against volume there."""
    i = np.argsort(x); v, p = x[i], y[i]; V0 = float(v[-1]) * (1.0 + 0.002 + max(float(p[-1]), 0) * 0)
    k = float(-np.polyfit(v, p, 1)[0] * np.mean(v)) if len(v) > 1 else 100.0
    return V0, (k if np.isfinite(k) and k > 0 else 100.0), 4.0


def _span(x): return float(np.ptp(x)) or 1.0


MORE = {
    "ExpGrow2": (_expgro2, lambda x, y: (float(y[0]), 1.0, _span(x) / 3, 1.0, _span(x) / 10)),
    "Stretched exponential (KWW)": (_stretched, lambda x, y: (float(y[-1]), float(y[0] - y[-1]), _span(x) / 3, 1.0)),
    "Exponential decay + line": (_explin, lambda x, y: (float(y[-1]), float(y[0] - y[-1]), _span(x) / 5, 0.0)),
    "Logistic growth (3 parameters)": (_logistic3, lambda x, y: (float(np.max(y)), 4.0 / _span(x), float(np.median(x)))),
    "Richards growth": (_richards, lambda x, y: (float(np.max(y)), 4.0 / _span(x), float(np.median(x)), 1.0)),
    "von Bertalanffy growth": (_bertalanffy, lambda x, y: (float(np.max(y)) * 1.1, 2.0 / _span(x), float(np.min(x)))),
    "Avrami (JMAK) transformation": (_avrami, lambda x, y: (float(np.max(y)), 1.0 / (float(np.median(np.abs(x))) or 1.0), 2.0)),
    "Gaussian + sloping baseline": (_gauss_line, lambda x, y: (lambda g: (g[0], 0.0, g[1], g[2], g[3]))(_pk(x, y))),
    "Lorentzian + sloping baseline": (_lorentz_line, lambda x, y: (lambda g: (g[0], 0.0, g[1], g[2] * 1.18, g[3]))(_pk(x, y))),
    "Pearson VII peak": (_pearson7, lambda x, y: (lambda g: (g[0], g[1], g[2] * 1.18, g[3], 2.0))(_pk(x, y))),
    "Exponentially modified Gaussian": (_emg, lambda x, y: (lambda g: (g[0], g[1] - g[2] / 2, g[2] * 0.7, g[3] * g[2] * 2.5, g[2]))(_pk(x, y))),
    "Bi-Gaussian (asymmetric peak)": (_bigauss, lambda x, y: (lambda g: (g[0], g[1], g[3], g[2], g[2]))(_pk(x, y))),
    "Two Gaussians": (_gauss2, _two),
    "Two Lorentzians": (_lorentz2, _two),
    "Breit-Wigner-Fano": (_bwf, lambda x, y: (lambda g: (g[0], g[1], g[2] * 1.18, g[3], -10.0))(_pk(x, y))),
    "Rational ((a+b*x)/(1+c*x))": (_rational, lambda x, y: (float(y[0]), 1.0, 0.1 / (float(np.max(np.abs(x))) or 1.0))),
    "Hyperbola (a + b/x)": (_hyperbola, lambda x, y: (float(y[-1]), 1.0)),
    "Reciprocal (1/(a+b*x))": (_reciprocal, lambda x, y: (1.0 / (float(y[0]) or 1.0), 0.1)),
    "Freundlich isotherm": (_freundlich, lambda x, y: (float(np.max(y)) / (float(np.max(np.abs(x))) ** 0.5 or 1.0), 2.0)),
    "Two-site binding": (_twosite, lambda x, y: (float(np.max(y)) / 2, float(np.median(x)) / 3 or 1.0, float(np.max(y)) / 2, float(np.median(x)) * 3 or 1.0)),
    "Damped sine": (_damped_sine, lambda x, y: (float(np.mean(y)), float(np.ptp(y)) / 2, _span(x) / 2, _span(x) / 6, float(np.min(x)))),
    "Vogel-Fulcher-Tammann (A + B/(x-C))": (_vft, lambda x, y: (float(np.min(y)) - 1.0, float(np.ptp(y)) * float(np.min(x)) / 2 or 1.0, float(np.min(x)) / 2)),
    "Birch-Murnaghan EoS, 3rd order (x = V, y = P)": (_bm3, _eos),
    "Vinet EoS (x = V, y = P)": (_vinet, _eos),
    "Diffusion profile (erfc)": (_erfc_profile, lambda x, y: (float(y[-1]), float(y[0]), _span(x) / 3)),
    "Quadratic (a+b*x+c*x^2)": (_quadratic, lambda x, y: (float(np.mean(y)), 0.0, 0.0)),
    "Cubic (a+b*x+c*x^2+d*x^3)": (_cubic, lambda x, y: (float(np.mean(y)), 0.0, 0.0, 0.0)),
    "Square root (a + b*sqrt(x))": (_sqrt, lambda x, y: (float(y[0]), 1.0)),
}
A.MODELS.update(MORE)

# true parameters and X range for the self-check: each function must recover them from its own noise-free curve
_CHECK = {
    "ExpGrow2": ((1, 2, 3, 0.5, 1), (0, 6)), "Stretched exponential (KWW)": ((1, 5, 2, 0.7), (0.01, 12)),
    "Exponential decay + line": ((1, 5, 1.5, 0.3), (0, 10)), "Logistic growth (3 parameters)": ((10, 1.2, 5), (0, 10)),
    "Richards growth": ((10, 1.0, 5, 0.6), (0, 12)), "von Bertalanffy growth": ((30, 0.3, -0.5), (0, 15)),
    "Avrami (JMAK) transformation": ((1, 0.2, 2.5), (0.01, 15)), "Gaussian + sloping baseline": ((2, 0.1, 5, 0.6, 8), (0, 10)),
    "Lorentzian + sloping baseline": ((2, 0.1, 5, 0.6, 8), (0, 10)), "Pearson VII peak": ((1, 5, 0.8, 6, 1.6), (0, 10)),
    "Exponentially modified Gaussian": ((1, 4, 0.5, 10, 1.2), (0, 12)), "Bi-Gaussian (asymmetric peak)": ((1, 5, 6, 0.5, 1.2), (0, 10)),
    "Two Gaussians": ((1, 3, 0.5, 6, 7, 0.7, 4), (0, 10)), "Two Lorentzians": ((1, 3, 0.4, 6, 7, 0.5, 4), (0, 10)),
    "Breit-Wigner-Fano": ((1, 5, 0.7, 6, -6), (0, 10)), "Rational ((a+b*x)/(1+c*x))": ((1, 2, 0.3), (0, 10)),
    "Hyperbola (a + b/x)": ((2, 5), (0.5, 10)), "Reciprocal (1/(a+b*x))": ((0.5, 0.2), (0, 10)),
    "Freundlich isotherm": ((3, 2.5), (0.1, 10)), "Two-site binding": ((4, 0.5, 6, 20), (0.05, 200)),
    "Damped sine": ((1, 4, 6, 1.5, 0.3), (0, 15)), "Vogel-Fulcher-Tammann (A + B/(x-C))": ((-4.5, 5000, 500), (900, 1500)),
    "Birch-Murnaghan EoS, 3rd order (x = V, y = P)": ((162.3, 260, 4.0), (125, 161)), "Vinet EoS (x = V, y = P)": ((162.3, 260, 4.0), (125, 161)),
    "Diffusion profile (erfc)": ((1, 9, 2.5), (0, 10)), "Quadratic (a+b*x+c*x^2)": ((1, -2, 0.5), (0, 10)),
    "Cubic (a+b*x+c*x^2+d*x^3)": ((1, -2, 0.5, 0.05), (0, 10)), "Square root (a + b*sqrt(x))": ((1, 2), (0, 10)),
}


def _demo():
    """Every added function is fitted to a curve made from known parameters and must return them."""
    assert set(_CHECK) == set(MORE), set(MORE) ^ set(_CHECK)
    # Birch-Murnaghan against a hand value: V0/V = 1.1, K0 = 260, K' = 4 -> P = 1.5*260*(1.1^(7/3) - 1.1^(5/3)) = 29.86 GPa
    assert abs(_bm3(100 / 1.1, 100.0, 260.0, 4.0) - 1.5 * 260 * (1.1 ** (7 / 3) - 1.1 ** (5 / 3))) < 1e-9
    # EMG of a nearly symmetric peak (w/t0 = 50) must stay finite and equal the Gaussian limit (audit 1.31.0-A)
    xs = np.linspace(0, 10, 201); g = _emg(xs, 0.0, 5.0, 1.0, 1.0, 0.02); assert np.isfinite(g).all()
    assert np.allclose(g, np.exp(-0.5 * ((xs - 5.0 - 0.02) / 1.0) ** 2) / np.sqrt(2 * np.pi), atol=2e-3), np.nanmax(np.abs(g))
    assert np.allclose(_emg(xs, 0.0, 5.0, 0.5, 10.0, 1.2), 10.0 / 2.4 * np.exp(0.5 * (0.5 / 1.2) ** 2 - (xs - 5.0) / 1.2) * _sp.erfc((0.5 / 1.2 - (xs - 5.0) / 0.5) / np.sqrt(2)))
    assert abs(_vinet(100.0, 100.0, 260.0, 4.0)) < 1e-12 and abs(_logistic3(5.0, 10, 1.2, 5.0) - 5.0) < 1e-12
    for name, (true, (lo, hi)) in _CHECK.items():
        x = np.linspace(lo, hi, 240 if name != "Two-site binding" else 400)
        if name == "Two-site binding": x = np.geomspace(lo, hi, 400)
        y = MORE[name][0](x, *true); r = A.fit_model(x, y, name)
        assert r["R2"] > 0.9999, (name, r["R2"])
        got = np.array([r["params"][k] for k in A.model_params(name)], float)
        if name not in ("Two-site binding", "ExpGrow2", "Two Gaussians", "Two Lorentzians"):  # terms that may swap or trade off
            assert np.allclose(got, true, rtol=2e-2, atol=2e-3), (name, got, true)
    print("fitlib ok:", len(MORE), "functions,", len(A.MODELS), "in the library")


if __name__ == "__main__":
    _demo()
