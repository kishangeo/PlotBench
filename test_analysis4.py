"""PlotBench self-check, part 4: run `python test_analysis4.py`. Author: Kishan Tiwari."""
import numpy as np
import pandas as pd
from scipy import stats
from plotbench import analysis4 as D, analysis3 as C

rng = np.random.default_rng(21)

# QDA: groups with very different covariances, where LDA is poor
Xa = rng.multivariate_normal([0, 0], [[1, 0], [0, 1]], 150); Xb = rng.multivariate_normal([0, 0], [[9, 0], [0, 0.1]], 150)
X = np.vstack([Xa, Xb]); g = np.repeat(["a", "b"], 150)
q = D.qda(X, g, ["x", "y"]); l = C.lda(X, g, ["x", "y"])
assert q["accuracy"] > 0.8 > l["accuracy"] and q["loo_accuracy"] > 0.75 and q["box_m"]["p"] < 1e-10, (q["accuracy"], l["accuracy"])
assert np.allclose(q["post"].sum(1), 1)

# MANCOVA / ANCOVA: group effect disappears once the covariate is accounted for
n = 60; cov = np.r_[rng.normal(0, 1, 30), rng.normal(2, 1, 30)]; grp = np.repeat(["c", "t"], 30)
y1 = 3 * cov + rng.normal(0, 0.5, n); y2 = -2 * cov + rng.normal(0, 0.5, n)
mc = D.mancova(np.column_stack([y1, y2]), grp, cov[:, None], ["age"])
assert mc["tests"]["Group"][0][5] > 0.01 and mc["tests"]["age"][0][5] < 1e-20, mc["tests"]
an = D.ancova(y1, grp, cov[:, None], ["age"]); raw = stats.f_oneway(y1[:30], y1[30:])
assert raw.pvalue < 1e-6 and an["table"][0][4] > 0.01
# ANCOVA F equals the nested-model F computed by hand
Xf = np.column_stack([np.ones(n), grp == "t", cov]); Xr = np.column_stack([np.ones(n), cov])
sse = lambda A: np.sum((y1 - A @ np.linalg.lstsq(A, y1, rcond=None)[0]) ** 2)
F = (sse(Xr) - sse(Xf)) / (sse(Xf) / (n - 3)); assert abs(an["table"][0][1] - F) < 1e-8
y3 = y1 + np.where(grp == "t", 4, 0); assert D.ancova(y3, grp, cov[:, None], ["age"])["table"][0][4] < 1e-10
assert abs(mc["slopes"][0][1] - 3) < 0.2

# other tests
gr = {"a": rng.normal(0, 1, 30), "b": rng.normal(0.1, 1, 30), "c": rng.normal(3, 1, 30)}
du = D.dunn(gr); assert du[0][4] > 0.05 and du[1][4] < 1e-5 and du[1][4] >= du[1][3]
assert abs(D.fisher_exact([[8, 2], [1, 5]])["p (two-sided)"] - stats.fisher_exact([[8, 2], [1, 5]])[1]) < 1e-12
assert D.mcnemar([[10, 15], [3, 12]])["p (exact binomial)"] < 0.01
pt = D.proportion_test(60, 100, p0=0.5); assert abs(pt["z"] - 2.0) < 1e-12
assert D.proportion_test(60, 100, 40, 100)["p"] < 0.01
assert D.var_test_two(rng.normal(0, 1, 50), rng.normal(0, 3, 50))["p (two-sided)"] < 1e-6
assert D.var_test_one(rng.normal(0, 2, 200), 4.0)["p (two-sided)"] > 0.01
assert D.anderson_darling(rng.normal(size=300))["p (D'Agostino approximation)"] > 0.01 and D.anderson_darling(rng.exponential(size=300))["p (D'Agostino approximation)"] < 1e-4
z = rng.normal(size=400); xa = z + rng.normal(0, .3, 400); xb = z + rng.normal(0, .3, 400)
R, pv = D.partial_correlation(np.column_stack([xa, xb, z]), ["a", "b", "z"]); assert abs(R[0, 1]) < 0.15 and np.corrcoef(xa, xb)[0, 1] > 0.8
xl = rng.normal(size=(500, 2)); pl = 1 / (1 + np.exp(-(0.5 + 2 * xl[:, 0] - xl[:, 1]))); yl = (rng.uniform(size=500) < pl).astype(float)
lg = D.logistic_regression(yl, xl, ["x1", "x2"]); assert abs(lg["coef"][1][1] - 2) < 0.5 and abs(lg["coef"][2][1] + 1) < 0.35 and lg["stats"]["p (LR test)"] < 1e-20
Xp = rng.normal(size=(100, 5)); Yp = Xp @ np.array([1, -2, 0, 0, 0.5]) + 3 + rng.normal(0, .05, 100)
pr = D.pls(Xp, Yp, 5); assert np.allclose(pr["B"][:, 0], [1, -2, 0, 0, 0.5], atol=0.03) and abs(pr["intercept"][0] - 3) < 0.03
assert pr["vip"][1] > pr["vip"][2] and pr["y_var_cum"][-1] > 0.99
items = z[:, None] + rng.normal(0, .5, (400, 4)); assert D.cronbach_alpha(items)["Cronbach alpha"] > 0.85
ba = D.bland_altman(z + 0.5, z + rng.normal(0, .1, 400)); assert abs(ba["Mean difference (bias)"] - 0.5) < 0.03

# curve tools
x = np.linspace(0, 10, 101)
xs, mean, sd, k = D.average_curves([(x, x), (x + 1, x + 1 + 2), (x, x + 1)]); assert k == 3 and np.allclose(mean, xs + 1) and xs[0] == 1
assert np.allclose(D.subtract_line(x, 2 * x + 1 + np.sin(x) * 0, 0, 10), 0)
assert np.allclose(D.subtract_reference(x, x ** 2, x, x ** 2), 0)
cr = D.intersections(x, x, x, 10 - x); assert len(cr) == 1 and abs(cr[0][0] - 5) < 1e-9
assert np.allclose(D.x_at_y(x, np.sin(x), 0), [0, np.pi, 2 * np.pi, 3 * np.pi], atol=0.01)
rt = D.rise_time(x, 1 / (1 + np.exp(-(x - 5) * 3))); assert abs(rt["Rise time"] - 2 * np.log(9) / 3) < 0.05
pa = D.polygon_area([0, 2, 2, 0], [0, 0, 1, 1]); assert pa["Area"] == 2 and pa["Centroid X"] == 1 and pa["Perimeter"] == 6
ex, ey = D.confidence_ellipse(rng.normal(size=2000), rng.normal(size=2000)); assert abs(np.ptp(ex) / 2 - np.sqrt(stats.chi2.ppf(.95, 2))) < 0.15
sx, sy = rng.uniform(0, 1, 300), rng.uniform(0, 1, 300)
for fn in (D.grid_idw, D.grid_tps):
    M, e = fn(sx, sy, sx + sy, 20, 20); assert M.shape == (20, 20) and abs(M[10, 10] - 1) < 0.15, fn.__name__

# worksheet operations
df = pd.DataFrame({"id": [1, 2, 3], "a": [1., 2, 3], "b": [4., 5, np.nan]})
st = D.stack_columns(df, ["a", "b"], ["id"]); assert len(st) == 5 and set(st.Column) == {"a", "b"}
un = D.unstack_column(st, "Value", "Column"); assert list(un.columns) == ["a", "b"] and un["a"].tolist() == [1, 2, 3]
lng = pd.DataFrame({"site": ["x", "x", "y", "y"], "yr": [1, 2, 1, 2], "v": [1., 2, 3, 4]})
pv_ = D.pivot(lng, "site", "yr", "v"); assert pv_.shape == (2, 3) and pv_["2"].tolist() == [2, 4]
fc = D.frequency_counts(["a", "b", "a"]); assert fc.set_index("Value").Count["a"] == 2
fn_ = D.frequency_counts(np.arange(10.), bins=5); assert fn_.Count.sum() == 10 and fn_.Cumulative.iloc[-1] == 10
rs = D.row_stats(df, ["a", "b"]); assert rs["Row mean"].tolist()[:2] == [2.5, 3.5] and rs["Row N"].iloc[2] == 1
assert D.reduce_rows(pd.DataFrame({"v": np.arange(6.)}), 2)["v"].tolist() == [0.5, 2.5, 4.5]
assert np.allclose(D.fill_missing([1, np.nan, 3]), [1, 2, 3]) and np.allclose(D.fill_missing([1, np.nan, 5], [0, 3, 4]), [1, 4, 5])
jn = D.join_frames(df, pd.DataFrame({"key": [1, 3], "c": ["p", "q"]}), "id", "key"); assert len(jn) == 2 and jn.c.tolist() == ["p", "q"]
assert D.sequence(5, 1, 2).tolist() == [1, 3, 5, 7, 9] and D.sequence(4, 1, 1, repeat=2).tolist() == [1, 1, 2, 2]
print("All PlotBench analysis4 checks passed.")
