"""PlotBench self-check, part 2: run `python test_analysis2.py`. Author: Kishan Tiwari."""
import numpy as np
from plotbench import analysis as A, analysis2 as B

rng = np.random.default_rng(7)
x = np.linspace(0.5, 10, 150)

# every added 1-D model fits its own curve
for name in B.MORE_MODELS:
    xx = np.linspace(0.05, 0.35, 80) if name.startswith("BET") else np.linspace(10, 20, 80) if name.startswith("Birch") \
        else np.linspace(250, 400, 80) if name.startswith("Vogel") else x
    p = A.initial_guess(name, xx, np.exp(-xx / xx.max()) + 1)
    y = A.MODELS[name][0](xx, *[v * 1.05 if v else 0.2 for v in p])
    if not np.all(np.isfinite(y)) or np.ptp(y) == 0: continue
    try: r2 = A.fit_model(xx, y, name)["R2"]
    except RuntimeError: r2 = 0
    assert r2 > 0.99, (name, r2)

# generalised multi-peak with every shape, metrics and areas
for shape in B.PEAK_SHAPES:
    f = B.PEAK_SHAPES[shape][0]; extra = {"PseudoVoigt": [0.4], "Voigt": [0.6]}.get(shape, [])
    y = 0.5 + f(x, 3, 0.8, 4, *extra) + f(x, 7, 1.2, 6, *extra) + rng.normal(0, 0.005, x.size)
    r = B.fit_peaks(x, y, [3.2, 6.8], shape)
    assert r["R2"] > 0.999, (shape, r["R2"]); c = sorted(p["Center"] for p in r["peaks"])
    assert abs(c[0] - 3) < 0.05 and abs(c[1] - 7) < 0.05 and abs(sum(p["Area %"] for p in r["peaks"]) - 100) < 1e-6
g = B.fit_peaks(x, B.PEAK_SHAPES["Gaussian"][0](x, 5, 1.0, 2.0), [5], "Gaussian")
assert abs(g["peaks"][0]["Area"] - 2.0) < 0.01 and abs(g["peaks"][0]["FWHM"] - 1.0 * np.sqrt(np.log(2) / 2) * 2) < 0.01
fixed = B.fit_peaks(x, B.PEAK_SHAPES["Gaussian"][0](x, 5, 1.0, 2.0), [5.3], "Gaussian", fix_centers=True)
assert abs(fixed["params"]["xc1"] - 5.3) < 1e-6

# surface fits
X, Y = rng.uniform(-2, 2, 400), rng.uniform(-2, 2, 400)
for name, truth in (("Plane", (1, 2, -3)), ("Gaussian 2D", (0.1, 3, 0.5, -0.3, 0.7, 1.1))):
    Z = B.SURFACE_MODELS[name][0](np.vstack([X, Y]), *truth); r = B.fit_surface(X, Y, Z, name)
    assert r["R2"] > 0.9999 and np.allclose(list(r["params"].values()), truth, atol=1e-4), (name, r["params"])
ru = B.fit_surface(X, Y, 2 * X * Y + 1, "User", "a*x*y + b", ["a", "b"]); assert abs(ru["params"]["a"] - 2) < 1e-6

# ODR with x and y errors
xt = np.linspace(0, 10, 40); xo = xt + rng.normal(0, 0.2, 40); yo = 2 * xt + 1 + rng.normal(0, 0.2, 40)
od = B.fit_odr(xo, yo, "Line (a+b*x)", sx=np.full(40, 0.2), sy=np.full(40, 0.2)); assert abs(od["params"]["b"] - 2) < 0.1

# global fit: shared decay time, separate amplitudes
ds = [(x, A.MODELS["ExpDec1"][0](x, 0.5, a, 2.0) + rng.normal(0, 0.01, x.size)) for a in (3, 5, 8)]
gf = B.fit_global(ds, "ExpDec1", ["t1"]); t1 = [r for r in gf["rows"] if r[0] == "t1"][0][2]
assert abs(t1 - 2) < 0.02 and len(gf["funcs"]) == 3 and gf["R2"] > 0.999

# filters, STFT, CWT, correlation, envelope, coherence
fs = 100.0; t = np.arange(0, 4, 1 / fs); sig = np.sin(2 * np.pi * 2 * t) + 0.5 * np.sin(2 * np.pi * 30 * t)
for kind in ("Butterworth", "Chebyshev I", "Bessel", "Elliptic", "FIR (window)"):
    lp = B.apply_filter(sig, B.design_filter(kind, "lowpass", 4, (8,), fs))
    assert np.corrcoef(lp[50:-50], np.sin(2 * np.pi * 2 * t)[50:-50])[0, 1] > 0.98, kind
bp = B.apply_filter(sig, B.design_filter("Butterworth", "bandpass", 4, (20, 40), fs))
assert np.corrcoef(bp[50:-50], 0.5 * np.sin(2 * np.pi * 30 * t)[50:-50])[0, 1] > 0.98
w, H = B.freq_response(B.design_filter("Butterworth", "lowpass", 4, (8,), fs), fs); assert H[w < 4].min() > -1 and H[w > 30].max() < -40
f, tt, Z = B.stft(t, sig, 64); assert abs(f[np.argmax(Z.mean(1))] - 2) < 2
per, W = B.cwt_morlet(t, np.sin(2 * np.pi * 2 * t)); assert abs(per[np.argmax(W[:, 200])] - 0.5) < 0.1
lags, cc = B.correlate(np.r_[np.zeros(10), np.ones(5), np.zeros(10)], np.r_[np.zeros(13), np.ones(5), np.zeros(7)])
assert lags[np.argmax(cc)] == -3
assert np.allclose(B.correlate([1, 2], [1, 1], "convolution")[1], [1, 3, 2])
env = B.envelope(np.sin(2 * np.pi * 10 * t) * 2); assert abs(np.median(env) - 2) < 0.05
fc, coh = B.coherence(t, sig, sig + rng.normal(0, 0.01, t.size))
assert coh[np.argmin(np.abs(fc - 30))] > 0.99 and coh[np.argmin(np.abs(fc - 2))] > 0.99

# survival
time = np.array([5, 8, 12, 12, 15, 20, 22, 30, 35, 40.]); ev = np.array([1, 1, 1, 0, 1, 1, 0, 1, 0, 1])
rows, med = B.kaplan_meier(time, ev); assert abs(rows[0][3] - 0.9) < 1e-12 and rows[0][1] == 10 and med == 20
grp = np.r_[np.zeros(30), np.ones(30)]; tt2 = np.r_[rng.exponential(5, 30), rng.exponential(20, 30)]
lr = B.logrank(tt2, np.ones(60), grp); assert lr["p"] < 0.01
cx = B.cox_ph(tt2, np.ones(60), grp[:, None], ["group"]); assert cx[0][1] < 0 and cx[0][4] < 0.01  # group 1 lives longer

# ROC, clustering, power
lab = np.r_[np.zeros(100), np.ones(100)]; score = np.r_[rng.normal(0, 1, 100), rng.normal(2, 1, 100)]
ro = B.roc(score, lab); assert 0.88 < ro["AUC"] < 0.97 and ro["fpr"][0] == 0 and ro["tpr"][-1] == 1
Xc = np.vstack([rng.normal(0, .3, (40, 2)), rng.normal(4, .3, (40, 2)), rng.normal([0, 4], .3, (40, 2))])
labk, cen, wss = B.kmeans(Xc, 3); assert len(set(labk[:40])) == 1 and len(set(labk)) == 3
L, labh = B.hierarchical(Xc, "ward", 3); assert len(set(labh[:40])) == 1 and len(set(labh)) == 3
p = B.power_ttest(d=0.5, n=64)["power"]; assert abs(p - 0.80) < 0.01   # textbook: d = 0.5, n = 64 per group -> 0.80
assert B.power_ttest(d=0.5, power=0.8)["n per group"] == 64
assert abs(B.power_anova(f=0.25, k=3, power=0.8)["n per group"] - 53) <= 1  # Cohen: f = 0.25, 3 groups -> 52-53 per group

# two-way RM ANOVA: effect of A only
subj, fa, fb, yy = [], [], [], []
for s in range(8):
    base = rng.normal(0, 1)
    for a in range(2):
        for b in range(3): subj.append(s); fa.append(a); fb.append(b); yy.append(base + 3 * a + rng.normal(0, 0.3))
rm = B.rm_anova_2way(yy, subj, fa, fb); pA = rm[0][5]; pB = rm[2][5]; assert pA < 1e-6 and pB > 0.01, rm

try:
    import pywt  # noqa: F401
    noisy = np.sin(2 * np.pi * t) + rng.normal(0, 0.3, t.size); den = B.wavelet_denoise(noisy)
    assert np.std(den - np.sin(2 * np.pi * t)) < 0.6 * np.std(noisy - np.sin(2 * np.pi * t))
    assert len(B.dwt(noisy, "db4", 3)) == 4
except ImportError:
    print("(PyWavelets not installed: wavelet checks skipped)")
print("All PlotBench analysis2 checks passed.")
