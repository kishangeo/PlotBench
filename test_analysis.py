"""PlotBench self-check: run `python test_analysis.py`. Author: Kishan Tiwari."""
import numpy as np
from plotbench import analysis as A

rng = np.random.default_rng(1)
x = np.linspace(0, 10, 200)

# linear fit recovers slope/intercept
r = A.fit_polynomial(x, 3 + 2 * x + rng.normal(0, 0.01, x.size), 1)
assert abs(r["params"]["B1"] - 2) < 1e-2 and abs(r["params"]["B0"] - 3) < 1e-2 and r["R2"] > 0.999

# every built-in nonlinear model converges on its own synthetic data
truth = {"Gaussian": (1, 5, 1.5, 10), "Lorentzian": (1, 5, 1.5, 10), "ExpDec1": (1, 5, 2), "Boltzmann": (0, 10, 5, 0.8),
         "Allometric (a*x^b)": (2, 1.5), "Line (a+b*x)": (1, 2)}
for name, p in truth.items():
    y = A.MODELS[name][0](x + 0.01, *p)
    fit = A.fit_model(x + 0.01, y, name)
    assert fit["R2"] > 0.999, (name, fit["R2"])

# user-defined function
y = 4 * np.exp(-x / 2) + 1
fit = A.fit_model(x, y, "User", p0=[1, 1, 0], user_expr="a*exp(-x/t)+c", user_params=["a", "t", "c"])
assert abs(fit["params"]["t"] - 2) < 1e-4

# multipeak
y = A.MODELS["Gaussian"][0](x, 0, 3, 0.8, 2) + A.MODELS["Gaussian"][0](x, 0, 7, 1.0, 3)
fit = A.fit_multipeak(x, y, [3.2, 6.8])
assert fit["R2"] > 0.9999 and len(fit["components"]) == 2
assert [round(p["X"]) for p in A.find_peaks(x, y)] == [3, 7]

# statistics
assert A.descriptive([1, 2, 3, 4])["Mean"] == 2.5
assert A.ttest_two(rng.normal(0, 1, 50), rng.normal(3, 1, 50))["p"] < 1e-6
assert A.anova_oneway([1, 2, 3], [1, 2, 3])["p"] > 0.99
yv = np.array([1, 2, 3, 4, 10, 11, 12, 13], float)
aw = A.anova_twoway(yv, list("aabbaabb"), list("xxxxyyyy"))
assert aw["B"]["p"] < 0.001 and aw["A"]["p"] < 0.05
ev, pct, load, sc = A.pca(rng.normal(size=(50, 3)))
assert abs(pct.sum() - 100) < 1e-9

# signal / math
assert abs(A.area(x, np.ones_like(x)) - 10) < 1e-9
assert np.allclose(A.derivative(x, x ** 2)[5:-5], 2 * x[5:-5], atol=1e-6)
f, amp, _ = A.fft(x, np.sin(2 * np.pi * 2 * x))
assert abs(f[np.argmax(amp)] - 2) < 0.15
assert A.smooth(np.ones(20)).std() < 1e-12
assert np.allclose(A.eval_formula("A*2+sin(0)", {"A": np.arange(3.0)}, 3), [0, 2, 4])
assert np.allclose(A.normalize([2, 4, 6]), [0, 0.5, 1])

# ---- Phase 2: model library, fixed params, bounds, weights, bands
xx = np.linspace(0.5, 10, 120)
for name in A.MODELS:
    xx = np.linspace(300, 1000, 120) if name.startswith("Arrhenius") else np.linspace(0.5, 10, 120)
    p = A.initial_guess(name, xx, A.MODELS[name][0](xx, *A.initial_guess(name, xx, np.exp(-xx) + 1)))
    y = A.MODELS[name][0](xx, *[v * 1.1 if v else 0.3 for v in p])
    if not np.all(np.isfinite(y)): continue
    try: fit = A.fit_model(xx, y, name)
    except RuntimeError: fit = {"R2": 0}
    assert fit["R2"] > 0.99, (name, fit["R2"])
xx = np.linspace(0.5, 10, 120)
y = A.MODELS["Gaussian"][0](xx, 1, 5, 1.5, 10) + rng.normal(0, 0.05, xx.size)
fx = A.fit_model(xx, y, "Gaussian", fixed={"y0": 1.0})
assert fx["params"]["y0"] == 1.0 and fx["errors"]["y0"] == 0 and abs(fx["params"]["xc"] - 5) < 0.05 and fx["DOF"] == xx.size - 3
fb = A.fit_model(xx, y, "Gaussian", bounds={"xc": (6, 7)}); assert 6 <= fb["params"]["xc"] <= 7
fw = A.fit_model(xx, y, "Gaussian", yerr=np.full(xx.size, 0.05)); assert 0.5 < fw["ChiSq_weighted"] / fw["DOF"] < 1.6
lo, hi = fx["conf_band"](xx); plo, phi = fx["pred_band"](xx)
assert np.all(lo <= hi) and np.all(phi - plo > hi - lo)
inside = np.mean((y >= plo) & (y <= phi)); assert 0.85 < inside <= 1.0, inside
rows = A.param_table(fx); assert rows[0][-1] == "fixed" and rows[1][4] < 1e-10
assert "conf_band" in A.fit_polynomial(xx, 2 * xx + rng.normal(0, .1, xx.size), 2)
# regression
X = rng.normal(size=(80, 2)); yy = 1 + 2 * X[:, 0] - 3 * X[:, 1] + rng.normal(0, 0.1, 80)
mr = A.multiple_regression(yy, X, ["x1", "x2"])
assert abs(mr["coef"][1][1] - 2) < 0.05 and abs(mr["coef"][2][1] + 3) < 0.05 and mr["stats"]["R2"] > 0.99 and mr["anova"][0][5] < 1e-10
lr = A.fit_polynomial(X[:, 0], yy, 1); m1 = A.multiple_regression(yy, X[:, :1], ["x1"])
assert abs(lr["params"]["B1"] - m1["coef"][1][1]) < 1e-9
# post-hoc and more tests
grp = {"a": rng.normal(0, 1, 30), "b": rng.normal(0.1, 1, 30), "c": rng.normal(3, 1, 30)}
tk = A.tukey(grp); assert tk[0][4] > 0.05 and tk[1][4] < 1e-6 and len(tk) == 3
assert len(A.bonferroni(grp)) == 3 and A.homogeneity(grp)["Levene p"] > 0.01 and A.kruskal(grp)["p"] < 1e-6
M = np.column_stack([np.arange(10.0), np.arange(10.0) + 1, np.arange(10.0) + 2 + rng.normal(0, .1, 10)])
assert A.rm_anova(M)["p"] < 1e-6
assert A.wilcoxon(M[:, 0], M[:, 2])["p"] < 0.01
tab, cs = A.chi_square(list("aaaabbbb") * 5, list("xxxxyyyy") * 5); assert cs["p"] < 0.001
out = A.grubbs(np.r_[rng.normal(0, 1, 30), 15.0]); assert len(out) == 1 and out[0]["Value"] == 15.0
df_ = A.distribution_fit(rng.lognormal(0, 0.5, 300)); assert df_[0][0] == "Lognormal"

# ---- Phase 3: matrices
from plotbench import matrix as MX
Mf = MX.from_formula("x*10 + y", 3, 4, [0, 3, 0, 2]); assert Mf.shape == (3, 4) and Mf[2, 3] == 32 and Mf[0, 0] == 0
X, Y, Z = MX.matrix_to_xyz(Mf, [0, 3, 0, 2]); Mb, ext = MX.xyz_to_matrix(X, Y, Z); assert np.allclose(Mb, Mf) and ext == [0, 3, 0, 2]
sx, sy = rng.uniform(0, 1, 400), rng.uniform(0, 1, 400)
Mg, ext = MX.xyz_to_matrix(sx, sy, sx + 2 * sy, 20, 20); gx, gy = MX.axes_of(Mg, ext)
GX, GY = np.meshgrid(gx, gy); ok = np.isfinite(Mg); assert ok.mean() > 0.8 and np.allclose(Mg[ok], (GX + 2 * GY)[ok], atol=1e-6)
assert MX.resample(Mf, 6, 8).shape == (6, 8) and MX.smooth2d(np.ones((9, 9))).std() < 1e-12
ff = MX.fft2_magnitude(np.sin(2 * np.pi * np.arange(64) / 8)[None, :].repeat(64, 0)); assert ff.shape == (64, 64)
px, pv = MX.profile(Mf, [0, 3, 0, 2], "row", 2); assert np.allclose(pv, [2, 12, 22, 32])
Mt, et = MX.transform(Mf, [0, 3, 0, 2], "Transpose"); assert Mt.shape == (4, 3) and et == [0, 2, 0, 3]
assert np.allclose(MX.transform(np.array([[2.0, 0], [0, 4]]), [0, 1, 0, 1], "Inverse (square matrix)")[0], [[0.5, 0], [0, 0.25]])
import os, tempfile
from PIL import Image
pth = os.path.join(tempfile.gettempdir(), "pb_img_test.png"); Image.fromarray(np.array([[0, 255], [128, 64]], np.uint8)).convert("RGB").save(pth)
Mi, ei = MX.image_to_matrix(pth); assert Mi.shape == (2, 2) and abs(Mi[1, 1] - 255) < 1 and abs(Mi[0, 0] - 128) < 1  # row 0 = image bottom
print("All PlotBench analysis checks passed.")
