"""PlotBench analysis, part 2: more fit functions, surface/ODR/global fits, signal processing, survival, ROC,
clustering, power analysis, two-way repeated-measures ANOVA, generalised multi-peak fitting. No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
from scipy import optimize, signal, stats, special

from . import analysis as A
from .analysis import FitResult, _gof, _clean, _fin, _peak_guess, eval_formula


# ================================================================ more 1-D fit functions
def _gaussamp(x, y0, xc, w, A): return y0 + A * np.exp(-(x - xc) ** 2 / (2 * w ** 2))
def _lorentzamp(x, y0, xc, w, A): return y0 + A / (1 + 4 * ((x - xc) / w) ** 2)
def _pearson7(x, y0, xc, w, A, m): return y0 + A / (1 + ((x - xc) / w) ** 2 * (2 ** (1 / m) - 1)) ** m
def _bwf(x, y0, xc, w, A, q): e = 2 * (x - xc) / w; return y0 + A * (1 + e / q) ** 2 / (1 + e ** 2)
def _doniach(x, y0, xc, A, g, a):
    e = x - xc; return y0 + A * np.cos(np.pi * a / 2 + (1 - a) * np.arctan(e / g)) / (e ** 2 + g ** 2) ** ((1 - a) / 2)
def _bigauss(x, y0, xc, A, w1, w2): w = np.where(x < xc, w1, w2); return y0 + A * np.exp(-(x - xc) ** 2 / (2 * w ** 2))
def _logistic5(x, A, D, C, B, E): return D + (A - D) / (1 + (np.abs(x) / C) ** B) ** E
def _tanh(x, y0, A, xc, w): return y0 + A * np.tanh((x - xc) / w)
def _sinedamp(x, y0, A, t0, w, xc): return y0 + A * np.exp(-x / t0) * np.sin(np.pi * (x - xc) / w)
def _sinc(x, y0, A, xc, w): return y0 + A * np.sinc((x - xc) / w)
def _avrami(x, A, k, n): return A * (1 - np.exp(-k * np.abs(x) ** n))
def _bet(x, vm, c): return vm * c * x / ((1 - x) * (1 - x + c * x))
def _freundlich(x, K, n): return K * np.abs(x) ** (1 / n)
def _birch_murnaghan(V, V0, K0, K0p, E0):
    eta = (V0 / V) ** (2 / 3); return E0 + 9 * V0 * K0 / 16 * ((eta - 1) ** 3 * K0p + (eta - 1) ** 2 * (6 - 4 * eta))
def _bm_pressure(V, V0, K0, K0p):
    r = (V0 / V); return 1.5 * K0 * (r ** (7 / 3) - r ** (5 / 3)) * (1 + 0.75 * (K0p - 4) * (r ** (2 / 3) - 1))
def _vogel(x, A, B, T0): return A * np.exp(B / (x - T0))
def _rational(x, a, b, c): return (a + b * x) / (1 + c * x)
def _exp_lin(x, y0, A, t, k): return y0 + A * np.exp(-x / t) + k * x
def _cos2(x, y0, A, xc, w): return y0 + A * np.cos(np.pi * (x - xc) / w) ** 2
def _bidose(x, A1, A2, LOG1, LOG2, h1, h2, p):
    span = A2 - A1
    return A1 + span * (p / (1 + 10 ** ((LOG1 - x) * h1)) + (1 - p) / (1 + 10 ** ((LOG2 - x) * h2)))


def _pk(x, y):
    y0, xc, w, area = _peak_guess(x, y); return y0, xc, w, float(np.max(y) - y0)


MORE_MODELS = {
    "GaussAmp (height form)": (_gaussamp, lambda x, y: (lambda g: (g[0], g[1], g[2] / 2.355, g[3]))(_pk(x, y))),
    "LorentzAmp (height form)": (_lorentzamp, lambda x, y: _pk(x, y)),
    "Pearson VII": (_pearson7, lambda x, y: (*_pk(x, y), 1.5)),
    "Breit-Wigner-Fano": (_bwf, lambda x, y: (*_pk(x, y), -20.0)),
    "Doniach-Sunjic (XPS)": (_doniach, lambda x, y: (lambda g: (g[0], g[1], g[3] * (g[2] / 2), g[2] / 2, 0.1))(_pk(x, y))),
    "BiGaussian (asymmetric)": (_bigauss, lambda x, y: (lambda g: (g[0], g[1], g[3], g[2] / 2.355, g[2] / 2.355))(_pk(x, y))),
    "Logistic 5-parameter": (_logistic5, lambda x, y: (float(y[0]), float(y[-1]), float(np.median(np.abs(x))) or 1.0, 2.0, 1.0)),
    "Tanh step": (_tanh, lambda x, y: (float(np.mean(y)), float(y[-1] - y[0]) / 2, float(np.median(x)), float(np.ptp(x)) / 10 or 1.0)),
    "Damped sine": (_sinedamp, lambda x, y: (float(np.mean(y)), float(np.ptp(y)) / 2, float(np.ptp(x)) or 1.0, float(np.ptp(x)) / 6 or 1.0, 0.0)),
    "Sinc": (_sinc, lambda x, y: (lambda g: (g[0], g[3], g[1], g[2]))(_pk(x, y))),
    "Avrami (JMAK)": (_avrami, lambda x, y: (float(np.max(y)), 1.0 / (float(np.median(np.abs(x))) or 1.0) ** 2, 2.0)),
    "BET isotherm (x = P/P0)": (_bet, lambda x, y: (float(np.median(y)), 50.0)),
    "Freundlich isotherm": (_freundlich, lambda x, y: (float(np.median(y)) or 1.0, 2.0)),
    "Birch-Murnaghan E(V)": (_birch_murnaghan, lambda x, y: (float(x[np.argmin(y)]), 0.5, 4.0, float(np.min(y)))),
    "Birch-Murnaghan P(V)": (_bm_pressure, lambda x, y: (float(np.max(x)) * 1.01, 100.0, 4.0)),
    "Vogel-Fulcher-Tammann": (_vogel, lambda x, y: (float(np.min(y)) or 1.0, 100.0, float(np.min(x)) * 0.8)),
    "Rational (a+bx)/(1+cx)": (_rational, lambda x, y: (float(y[0]), 1.0, 0.1)),
    "Exponential + linear": (_exp_lin, lambda x, y: (float(y[-1]), float(y[0] - y[-1]), float(np.ptp(x)) / 3 or 1.0, 0.0)),
    "Cos squared (Malus)": (_cos2, lambda x, y: (float(np.min(y)), float(np.ptp(y)), 0.0, 180.0)),
    "Biphasic dose-response": (_bidose, lambda x, y: (float(y[0]), float(y[-1]), float(np.percentile(x, 30)), float(np.percentile(x, 70)), 1.0, 1.0, 0.5)),
}
A.MODELS.update(MORE_MODELS)


# ================================================================ generalised multi-peak fitting
PEAK_SHAPES = {  # name: (f(x, xc, w, A, *extra), extra names, extra initial values); A is area for G/L, height otherwise
    "Gaussian": (lambda x, xc, w, A: A / (w * np.sqrt(np.pi / 2)) * np.exp(-2 * ((x - xc) / w) ** 2), [], []),
    "Lorentzian": (lambda x, xc, w, A: 2 * A / np.pi * w / (4 * (x - xc) ** 2 + w ** 2), [], []),
    "PseudoVoigt": (lambda x, xc, w, A, mu: A * (mu * 2 / np.pi * w / (4 * (x - xc) ** 2 + w ** 2) + (1 - mu) * np.sqrt(4 * np.log(2))
                                              / (np.sqrt(np.pi) * w) * np.exp(-4 * np.log(2) / w ** 2 * (x - xc) ** 2)), ["mu"], [0.5]),
    "Voigt": (lambda x, xc, w, A, wl: A * special.voigt_profile(x - xc, np.abs(w) / 2.355, np.abs(wl) / 2), ["wL"], [None]),
}


def peak_metrics(x, comp):
    """Numerical centre, height, FWHM and area of one peak component curve."""
    xs = np.linspace(np.min(x), np.max(x), 4000); ys = comp(xs); i = int(np.argmax(np.abs(ys))); h = ys[i]
    above = np.nonzero(np.abs(ys) >= abs(h) / 2)[0]
    return {"Center": xs[i], "Height": h, "FWHM": xs[above[-1]] - xs[above[0]] if above.size > 1 else np.nan,
            "Area": float(np.trapz(ys, xs))}


def fit_peaks(x, y, centers, shape="Gaussian", baseline=None, widths=None, fix_centers=False, center_bounds=None, fix_widths=None):
    """Sum of peaks on a (pre-subtracted) baseline. baseline: array same length as y, or None (constant fitted).
    shape: one name for every peak, or a list with one shape per peak (e.g. Gaussian + Lorentzian + PseudoVoigt).
    fix_centers: bool for all peaks, or a list of bools. center_bounds: list of (lo, hi) per peak (None = free).
    widths: starting width (FWHM-like w) per peak, None = automatic; fix_widths: list of bools holding those widths fixed."""
    x = np.asarray(x, float); y = np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    base = np.zeros_like(y) if baseline is None else np.asarray(baseline, float)[m]
    n = len(centers); shapes = [shape] * n if isinstance(shape, str) else list(shape)
    fixes = [bool(fix_centers)] * n if isinstance(fix_centers, bool) else [bool(v) for v in fix_centers]
    cb = list(center_bounds or [None] * n); yc = y - base
    w0 = float(np.ptp(x)) / (10 * max(1, n)); y00 = 0.0 if baseline is not None else float(np.min(yc))
    p0, lo, hi, slices = [y00], [-np.inf], [np.inf], []
    for k, c in enumerate(centers):
        f, extra, extra0 = PEAK_SHAPES[shapes[k]]; w = (widths or [None] * n)[k] or w0; h = float(np.interp(c, x, yc) - y00)
        start = len(p0)
        p0 += [c, w, h * w * (1.06 if shapes[k] == "Gaussian" else 1.57 if shapes[k] == "Lorentzian" else 1.3)] + [w if v is None else v for v in extra0]
        clo, chi = cb[k] if cb[k] else (-np.inf, np.inf)
        if fixes[k]: clo, chi = c - 1e-9 * (abs(c) + 1), c + 1e-9 * (abs(c) + 1)
        wlo, whi = (w * (1 - 1e-9), w * (1 + 1e-9)) if (fix_widths or [False] * n)[k] else (1e-12, np.inf)
        lo += [clo, wlo, -np.inf] + [0.0 if shapes[k] == "PseudoVoigt" else 1e-12 for _ in extra]
        hi += [chi, whi, np.inf] + [1.0 if shapes[k] == "PseudoVoigt" else np.inf for _ in extra]
        slices.append((f, slice(start, len(p0)), extra))

    def model(t, *p):
        out = np.full_like(t, p[0], dtype=float)
        for f, sl, _ in slices: out += f(t, *p[sl])
        return out

    p0 = [min(max(v, l + 1e-12), h - 1e-12) if np.isfinite(l) or np.isfinite(h) else v for v, l, h in zip(p0, lo, hi)]
    popt, pcov = optimize.curve_fit(model, x, yc, p0=p0, bounds=(lo, hi), maxfev=40000)
    err = np.sqrt(np.abs(np.diag(pcov))) if np.all(np.isfinite(pcov)) else np.full(len(popt), np.nan)
    names = ["y0"] + [f"{nm}{j + 1}" for j, (_, _, extra) in enumerate(slices) for nm in ["xc", "w", "A"] + extra]
    comps = [(lambda t, f=f, q=popt[sl]: f(np.asarray(t, float), *q)) for f, sl, _ in slices]
    label = f"{n} x {shapes[0]}" if len(set(shapes)) == 1 else " + ".join(shapes)
    r = FitResult(model=label, params=dict(zip(names, popt)), errors=dict(zip(names, err)),
                  func=lambda t, p=popt: model(np.asarray(t, float), *p), components=comps, fixed={})
    r.update(_gof(yc, model(x, *popt), len(popt)))
    r["peaks"] = [{"Peak": j + 1, "Shape": shapes[j], **peak_metrics(x, c)} for j, c in enumerate(comps)]
    total = sum(abs(p["Area"]) for p in r["peaks"]) or 1
    for p in r["peaks"]: p["Area %"] = 100 * abs(p["Area"]) / total
    return r


# ================================================================ surface (z = f(x, y)) fitting
def _plane(xy, a, b, c): return a + b * xy[0] + c * xy[1]
def _parab(xy, a, b, c, d, e, f): x, y = xy; return a + b * x + c * y + d * x * x + e * y * y + f * x * y
def _gauss2d(xy, z0, A, xc, yc, w1, w2):
    x, y = xy; return z0 + A * np.exp(-0.5 * ((x - xc) / w1) ** 2 - 0.5 * ((y - yc) / w2) ** 2)
def _lorentz2d(xy, z0, A, xc, yc, w1, w2):
    x, y = xy; return z0 + A / (1 + ((x - xc) / w1) ** 2 + ((y - yc) / w2) ** 2)


def _sg(x, y, z):
    i = int(np.argmax(z)); return float(np.min(z)), float(np.ptp(z)), float(x[i]), float(y[i]), float(np.ptp(x)) / 6 or 1.0, float(np.ptp(y)) / 6 or 1.0


SURFACE_MODELS = {"Plane": (_plane, lambda x, y, z: (float(np.mean(z)), 0.0, 0.0)),
                  "Paraboloid (quadratic)": (_parab, lambda x, y, z: (float(np.mean(z)), 0, 0, 0, 0, 0)),
                  "Gaussian 2D": (_gauss2d, _sg), "Lorentzian 2D": (_lorentz2d, _sg)}


def fit_surface(x, y, z, name, user_expr=None, user_params=None, p0=None):
    x, y, z = (np.asarray(v, float) for v in (x, y, z)); m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z); x, y, z = x[m], y[m], z[m]
    if name == "User":
        pn = list(user_params)
        def f(xy, *p): return eval_formula(user_expr, dict(zip(pn, p), x=xy[0], y=xy[1]), xy.shape[1])
        p0 = p0 or [1.0] * len(pn)
    else:
        f, guess = SURFACE_MODELS[name]; pn = list(f.__code__.co_varnames[1:f.__code__.co_argcount]); p0 = p0 or guess(x, y, z)
    popt, pcov = optimize.curve_fit(f, np.vstack([x, y]), z, p0=p0, maxfev=20000)
    err = np.sqrt(np.abs(np.diag(pcov))) if np.all(np.isfinite(pcov)) else np.full(len(popt), np.nan)
    r = FitResult(model=name, params=dict(zip(pn, popt)), errors=dict(zip(pn, err)), fixed={},
                  func=lambda X, Y, p=popt: f(np.vstack([np.ravel(X), np.ravel(Y)]), *p).reshape(np.shape(X)))
    r.update(_gof(z, f(np.vstack([x, y]), *popt), len(popt))); return r


# ================================================================ orthogonal distance regression (errors in x and y)
def fit_odr(x, y, name, sx=None, sy=None, p0=None):
    from scipy import odr
    x = np.asarray(x, float); y = np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y)
    for e in (sx, sy):
        if e is not None: m &= np.isfinite(e) & (np.asarray(e, float) > 0)
    f = A.MODELS[name][0]; pn = A.model_params(name); p0 = p0 or A.initial_guess(name, x[m], y[m])
    data = odr.RealData(x[m], y[m], sx=None if sx is None else np.asarray(sx, float)[m], sy=None if sy is None else np.asarray(sy, float)[m])
    out = odr.ODR(data, odr.Model(lambda b, t: f(t, *b)), beta0=p0).run()
    r = FitResult(model=f"{name} (ODR)", params=dict(zip(pn, out.beta)), errors=dict(zip(pn, out.sd_beta)), fixed={},
                  func=lambda t, b=out.beta: f(np.asarray(t, float), *b))
    r.update(_gof(y[m], f(x[m], *out.beta), len(pn))); r["ODR info"] = "; ".join(out.stopreason); return r


# ================================================================ global fit with shared parameters
def fit_global(datasets, name, shared):
    """datasets: list of (x, y). shared: parameter names common to all datasets; the rest are fitted per dataset."""
    f = A.MODELS[name][0]; pn = A.model_params(name); local = [p for p in pn if p not in shared]
    clean = [_clean(x, y) for x, y in datasets]; guesses = [A.initial_guess(name, x, y) for x, y in clean]
    g0 = np.mean(guesses, axis=0)
    p0 = [g0[pn.index(s)] for s in shared] + [g[pn.index(l)] for g in guesses for l in local]

    def unpack(p, k):
        d = dict(zip(shared, p[:len(shared)])); off = len(shared) + k * len(local)
        d.update(zip(local, p[off:off + len(local)])); return [d[n] for n in pn]

    def resid(p): return np.concatenate([f(x, *unpack(p, k)) - y for k, (x, y) in enumerate(clean)])
    sol = optimize.least_squares(resid, p0, max_nfev=40000)
    J = sol.jac; n = sum(len(x) for x, _ in clean); dof = max(n - len(p0), 1); s2 = float(sol.fun @ sol.fun) / dof
    try: cov = np.linalg.inv(J.T @ J) * s2; se = np.sqrt(np.abs(np.diag(cov)))
    except np.linalg.LinAlgError: se = np.full(len(p0), np.nan)
    rows = [[s, "all", sol.x[i], se[i]] for i, s in enumerate(shared)]
    funcs = []
    for k in range(len(clean)):
        prm = unpack(sol.x, k); funcs.append(lambda t, prm=prm: f(np.asarray(t, float), *prm))
        off = len(shared) + k * len(local)
        rows += [[l, f"dataset {k + 1}", sol.x[off + j], se[off + j]] for j, l in enumerate(local)]
    yall = np.concatenate([y for _, y in clean]); fit = np.concatenate([fn(x) for fn, (x, _) in zip(funcs, clean)])
    return {"rows": rows, "funcs": funcs, **_gof(yall, fit, len(p0))}


# ================================================================ signal processing
def design_filter(kind="Butterworth", btype="lowpass", order=4, cutoff=(0.1,), fs=1.0, ripple=1.0, numtaps=101):
    """Returns ('sos', sos) for IIR or ('fir', taps)."""
    wn = cutoff[0] if btype in ("lowpass", "highpass") else list(cutoff[:2])
    if kind == "FIR (window)":
        return "fir", signal.firwin(numtaps | 1, wn, fs=fs, pass_zero=btype in ("lowpass", "bandstop"))
    if kind == "Butterworth": sos = signal.butter(order, wn, btype=btype, fs=fs, output="sos")
    elif kind == "Chebyshev I": sos = signal.cheby1(order, ripple, wn, btype=btype, fs=fs, output="sos")
    elif kind == "Bessel": sos = signal.bessel(order, wn, btype=btype, fs=fs, output="sos")
    elif kind == "Elliptic": sos = signal.ellip(order, ripple, 40, wn, btype=btype, fs=fs, output="sos")
    else: raise ValueError(kind)
    return "sos", sos


def apply_filter(y, design, zero_phase=True):
    kind, h = design; y = np.asarray(y, float)
    if kind == "sos": return signal.sosfiltfilt(h, y) if zero_phase else signal.sosfilt(h, y)
    return signal.filtfilt(h, [1.0], y) if zero_phase else signal.lfilter(h, [1.0], y)


def freq_response(design, fs=1.0, n=512):
    kind, h = design
    w, H = signal.sosfreqz(h, worN=n, fs=fs) if kind == "sos" else signal.freqz(h, worN=n, fs=fs)
    return w, 20 * np.log10(np.maximum(np.abs(H), 1e-12))


def stft(x, y, nperseg=64):
    fs = 1 / float(np.mean(np.diff(x))); f, t, Z = signal.stft(np.asarray(y, float), fs=fs, nperseg=min(nperseg, len(y)))
    return f, t + float(x[0]), np.abs(Z)


def cwt_morlet(x, y, n_scales=64, w0=6.0):
    """Continuous wavelet transform with a Morlet wavelet (FFT based). Returns periods, |W| (scales x time)."""
    y = np.asarray(y, float) - np.nanmean(y); n = len(y); dt = float(np.mean(np.diff(x)))
    scales = np.geomspace(2 * dt, n * dt / 2, n_scales); k = 2 * np.pi * np.fft.fftfreq(n, dt); Y = np.fft.fft(y)
    W = np.array([np.fft.ifft(Y * np.sqrt(2 * np.pi * s / dt) * np.pi ** -0.25 * np.exp(-(s * k - w0) ** 2 / 2) * (k > 0)) for s in scales])
    return scales * 4 * np.pi / (w0 + np.sqrt(2 + w0 ** 2)), np.abs(W)


def wavelet_denoise(y, wavelet="db4", level=None, mode="soft"):
    import pywt
    y = np.asarray(y, float); coeffs = pywt.wavedec(y, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745; thr = sigma * np.sqrt(2 * np.log(len(y)))
    coeffs[1:] = [pywt.threshold(c, thr, mode=mode) for c in coeffs[1:]]
    return pywt.waverec(coeffs, wavelet)[:len(y)]


def dwt(y, wavelet="db4", level=None):
    import pywt
    return pywt.wavedec(np.asarray(y, float), wavelet, level=level)


def correlate(a, b, mode="cross-correlation", normalise=True):
    a = np.nan_to_num(np.asarray(a, float)); b = np.nan_to_num(np.asarray(b, float))
    if mode == "convolution": out = np.convolve(a, b, mode="full")
    else:
        a2, b2 = (a - a.mean(), b - b.mean()) if normalise else (a, b); out = signal.correlate(a2, b2, mode="full")
        if normalise: out = out / (np.sqrt(np.sum(a2 ** 2) * np.sum(b2 ** 2)) or 1)
    return np.arange(-(len(b) - 1), len(a)), out


def envelope(y): return np.abs(signal.hilbert(np.nan_to_num(np.asarray(y, float))))


def coherence(x, a, b, nperseg=64):
    fs = 1 / float(np.mean(np.diff(x))); return signal.coherence(np.asarray(a, float), np.asarray(b, float), fs=fs, nperseg=min(nperseg, len(a)))


# ================================================================ survival analysis
def kaplan_meier(time, event):
    """event: 1 = event observed, 0 = censored. Returns rows of (time, at risk, events, S, SE, 95% lo, hi), median."""
    t = np.asarray(time, float); e = np.asarray(event, float); m = np.isfinite(t) & np.isfinite(e); t, e = t[m], e[m] > 0
    rows, S, var = [], 1.0, 0.0
    for ut in np.unique(t[e]):
        n = int(np.sum(t >= ut)); d = int(np.sum((t == ut) & e)); S *= 1 - d / n
        var += d / (n * (n - d)) if n > d else 0; se = S * np.sqrt(var)
        lo, hi = (S ** np.exp(1.96 * np.sqrt(var) / np.log(S)), S ** np.exp(-1.96 * np.sqrt(var) / np.log(S))) if 0 < S < 1 else (S, S)
        rows.append([ut, n, d, S, se, lo, hi])
    med = next((r[0] for r in rows if r[3] <= 0.5), np.nan)
    return rows, med


def logrank(time, event, group):
    t = np.asarray(time, float); e = np.asarray(event, float) > 0; g = np.asarray(group).astype(str)
    levels = sorted(set(g)); O = np.zeros(len(levels)); E = np.zeros(len(levels)); V = np.zeros((len(levels), len(levels)))
    for ut in np.unique(t[e]):
        at = t >= ut; n = at.sum(); d = ((t == ut) & e).sum()
        nk = np.array([(at & (g == L)).sum() for L in levels]); dk = np.array([((t == ut) & e & (g == L)).sum() for L in levels])
        O += dk; E += d * nk / n
        if n > 1: V += d * (n - d) / (n - 1) * (np.diag(nk / n) - np.outer(nk / n, nk / n))
    k = len(levels) - 1; diff = (O - E)[:k]; chi2 = float(diff @ np.linalg.pinv(V[:k, :k]) @ diff)
    return {"Groups": ", ".join(levels), "Observed": list(O), "Expected": [round(v, 4) for v in E], "Chi-square": chi2, "df": k,
            "p": stats.chi2.sf(chi2, k)}


def cox_ph(time, event, X, names, iters=50):
    """Cox proportional hazards (Breslow ties) by Newton-Raphson. Returns rows: name, coef, SE, z, p, HR, HR lo, HR hi."""
    t = np.asarray(time, float); e = np.asarray(event, float) > 0; X = np.atleast_2d(np.asarray(X, float))
    if X.shape[0] != len(t): X = X.T
    m = np.isfinite(t) & np.all(np.isfinite(X), axis=1); t, e, X = t[m], e[m], X[m]
    o = np.argsort(-t); t, e, X = t[o], e[o], X[o]; beta = np.zeros(X.shape[1])
    for _ in range(iters):
        r = np.exp(X @ beta); cr = np.cumsum(r); cx = np.cumsum(r[:, None] * X, axis=0)
        cxx = np.cumsum(r[:, None, None] * X[:, :, None] * X[:, None, :], axis=0)
        g = np.zeros_like(beta); H = np.zeros((len(beta), len(beta)))
        for i in np.nonzero(e)[0]:
            j = np.nonzero(t >= t[i])[0][-1]  # risk set = rows 0..j (sorted descending)
            mu = cx[j] / cr[j]; g += X[i] - mu; H -= cxx[j] / cr[j] - np.outer(mu, mu)
        step = np.linalg.solve(H, g); beta -= step
        if np.max(np.abs(step)) < 1e-9: break
    se = np.sqrt(np.diag(np.linalg.inv(-H))); z = beta / se
    return [[n, b, s, zz, 2 * stats.norm.sf(abs(zz)), np.exp(b), np.exp(b - 1.96 * s), np.exp(b + 1.96 * s)]
            for n, b, s, zz in zip(names, beta, se, z)]


# ================================================================ ROC
def roc(score, label):
    s = np.asarray(score, float); y = np.asarray(label).astype(float) > 0; m = np.isfinite(s); s, y = s[m], y[m]
    thr = np.r_[np.inf, np.unique(s)[::-1]]
    tpr = np.array([np.mean(s[y] >= t) for t in thr]); fpr = np.array([np.mean(s[~y] >= t) for t in thr])
    auc = float(np.trapz(tpr, fpr)); P, N = y.sum(), (~y).sum()
    q1, q2 = auc / (2 - auc), 2 * auc ** 2 / (1 + auc)  # Hanley-McNeil standard error
    se = np.sqrt((auc * (1 - auc) + (P - 1) * (q1 - auc ** 2) + (N - 1) * (q2 - auc ** 2)) / (P * N))
    j = int(np.argmax(tpr - fpr))
    return {"fpr": fpr, "tpr": tpr, "thresholds": thr, "AUC": auc, "AUC SE": se, "AUC 95% lo": auc - 1.96 * se,
            "AUC 95% hi": auc + 1.96 * se, "Best cut-off (Youden)": thr[j], "Sensitivity at cut-off": tpr[j],
            "Specificity at cut-off": 1 - fpr[j]}


# ================================================================ clustering
def kmeans(X, k, seed=0, standardise=True):
    from scipy.cluster.vq import kmeans2
    X = np.asarray(X, float); Z = (X - X.mean(0)) / X.std(0, ddof=1) if standardise else X
    best = None
    for s in range(10):  # several starts, keep the lowest within-cluster sum of squares
        c, lab = kmeans2(Z, k, seed=seed + s, minit="++"); wss = float(sum(((Z[lab == j] - c[j]) ** 2).sum() for j in range(k)))
        if best is None or wss < best[2]: best = (c, lab, wss)
    c, lab, wss = best; centres = np.array([X[lab == j].mean(0) if np.any(lab == j) else np.full(X.shape[1], np.nan) for j in range(k)])
    return lab, centres, wss


def hierarchical(X, method="ward", k=3, standardise=True):
    from scipy.cluster import hierarchy as H
    X = np.asarray(X, float); Z = (X - X.mean(0)) / X.std(0, ddof=1) if standardise else X
    L = H.linkage(Z, method=method); return L, H.fcluster(L, k, criterion="maxclust")


# ================================================================ power and sample size
def power_ttest(d=None, n=None, alpha=0.05, power=None, kind="two-sample"):
    """Give any two of effect size d, n (per group), power; the missing one is solved."""
    def pw(d_, n_):
        df = 2 * n_ - 2 if kind == "two-sample" else n_ - 1; nc = d_ * np.sqrt(n_ / 2 if kind == "two-sample" else n_)
        tc = stats.t.ppf(1 - alpha / 2, df); return stats.nct.sf(tc, df, nc) + stats.nct.cdf(-tc, df, nc)
    if power is None: return {"effect size d": d, "n per group": n, "alpha": alpha, "power": pw(d, n)}
    if n is None:
        nn = optimize.brentq(lambda v: pw(d, v) - power, 2.0001, 1e7); return {"effect size d": d, "n per group (exact)": nn,
                                                                            "n per group": int(np.ceil(nn)), "alpha": alpha, "power": power}
    dd = optimize.brentq(lambda v: pw(v, n) - power, 1e-6, 50); return {"effect size d": dd, "n per group": n, "alpha": alpha, "power": power}


def power_anova(f=None, k=3, n=None, alpha=0.05, power=None):
    """One-way ANOVA, Cohen's f, n per group."""
    def pw(n_):
        df1, df2 = k - 1, k * (n_ - 1); return stats.ncf.sf(stats.f.ppf(1 - alpha, df1, df2), df1, df2, f ** 2 * k * n_)
    if power is None: return {"Cohen f": f, "groups": k, "n per group": n, "alpha": alpha, "power": pw(n)}
    nn = optimize.brentq(lambda v: pw(v) - power, 2.0001, 1e7)
    return {"Cohen f": f, "groups": k, "n per group": int(np.ceil(nn)), "alpha": alpha, "power": power}


# ================================================================ two-way repeated measures ANOVA (both factors within subjects)
def rm_anova_2way(y, subject, fa, fb):
    """Long format; balanced, complete design. Returns rows: source, SS, df, MS, F, p."""
    import pandas as pd
    d = pd.DataFrame({"y": np.asarray(y, float), "s": np.asarray(subject).astype(str), "a": np.asarray(fa).astype(str),
                      "b": np.asarray(fb).astype(str)}).dropna()
    d = d.groupby(["s", "a", "b"], as_index=False)["y"].mean()
    S, Av, Bv = sorted(d.s.unique()), sorted(d.a.unique()), sorted(d.b.unique()); n, a, b = len(S), len(Av), len(Bv)
    if len(d) != n * a * b: raise ValueError("Each subject needs a value for every combination of the two factors.")
    Y = np.zeros((n, a, b))
    for r in d.itertuples(): Y[S.index(r.s), Av.index(r.a), Bv.index(r.b)] = r.y
    g = Y.mean(); ms, ma, mb = Y.mean((1, 2)), Y.mean((0, 2)), Y.mean((0, 1))
    msa, msb, mab = Y.mean(2), Y.mean(1), Y.mean(0)
    ss_a = n * b * ((ma - g) ** 2).sum(); ss_b = n * a * ((mb - g) ** 2).sum()
    ss_ab = n * ((mab - ma[:, None] - mb[None, :] + g) ** 2).sum()
    ss_as = b * ((msa - ms[:, None] - ma[None, :] + g) ** 2).sum(); ss_bs = a * ((msb - ms[:, None] - mb[None, :] + g) ** 2).sum()
    ss_s = a * b * ((ms - g) ** 2).sum(); ss_abs = ((Y - g) ** 2).sum() - ss_a - ss_b - ss_ab - ss_as - ss_bs - ss_s
    rows = []
    for nm, ss, df, sse, dfe in (("A", ss_a, a - 1, ss_as, (a - 1) * (n - 1)), ("B", ss_b, b - 1, ss_bs, (b - 1) * (n - 1)),
                                 ("A*B", ss_ab, (a - 1) * (b - 1), ss_abs, (a - 1) * (b - 1) * (n - 1))):
        F = (ss / df) / (sse / dfe); rows.append([nm, ss, df, ss / df, F, stats.f.sf(F, df, dfe)])
        rows.append([f"Error({nm} x Subject)", sse, dfe, sse / dfe, "", ""])
    rows.append(["Subjects", ss_s, n - 1, ss_s / (n - 1), "", ""]); return rows
