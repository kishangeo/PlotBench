"""PlotBench self-check, part 3 (mixed ANOVA, MANOVA, LDA): run `python test_analysis3.py`. Author: Kishan Tiwari."""
import numpy as np
from scipy import stats
from plotbench import analysis3 as C

rng = np.random.default_rng(11)

# mixed ANOVA: group effect, condition effect, no interaction
rows = []
for s in range(12):
    grp = "ctl" if s < 6 else "trt"; base = rng.normal(0, 1)
    for w in range(3): rows.append((s, grp, w, base + (2.0 if grp == "trt" else 0) + 1.5 * w + rng.normal(0, 0.3)))
S_, G_, W_, Y_ = (np.array(v) for v in zip(*rows))
mx = C.mixed_anova(Y_.astype(float), S_, G_, W_); ss = [r[1] for r in mx]
assert abs(sum(ss[:5]) - ss[5]) < 1e-9 and mx[2][5] < 1e-6 and mx[3][5] > 0.01, mx
means = Y_.astype(float).reshape(12, 3).mean(1); fa = stats.f_oneway(means[:6], means[6:])
assert abs(fa.statistic - mx[0][4]) < 1e-9  # between-subjects test equals one-way ANOVA on subject means
try:
    C.mixed_anova([1, 2, 3, 4], ["s1", "s1", "s2", "s2"], ["a", "b", "a", "a"], [1, 2, 1, 2]); raise AssertionError("should reject")
except ValueError: pass

# MANOVA
Yv = np.vstack([rng.normal([0, 0], 1, (30, 2)), rng.normal([1.5, 0], 1, (30, 2)), rng.normal([0, 1.5], 1, (30, 2))]); gv = np.repeat(["a", "b", "c"], 30)
mv = C.manova(Yv, gv); assert all(r[5] < 1e-4 for r in mv["tests"]) and 0 < mv["tests"][0][1] < 1
one = C.manova(Yv[:, :1], gv); an = stats.f_oneway(*[Yv[gv == c, 0] for c in "abc"])
for r in one["tests"][:3]: assert abs(r[2] - an.statistic) < 1e-8, r  # one response: every test reduces to the ANOVA F
null = C.manova(rng.normal(size=(90, 3)), gv); assert null["tests"][0][5] > 0.001
two = C.manova(Yv[:60], gv[:60]); assert abs(two["tests"][0][2] - two["tests"][1][2]) < 1e-8  # two groups: Wilks F == Pillai F (Hotelling T2)

# LDA
Xl = np.vstack([rng.normal([0, 0, 0], .5, (40, 3)), rng.normal([3, 0, 1], .5, (40, 3)), rng.normal([0, 3, -1], .5, (40, 3))])
gl = np.repeat(["p", "q", "r"], 40); ld = C.lda(Xl, gl, ["x1", "x2", "x3"])
assert ld["accuracy"] > 0.97 and ld["loo_accuracy"] > 0.95 and abs(sum(ld["eigen_pct"]) - 100) < 1e-9 and ld["canon"].shape == (120, 2)
assert np.allclose(ld["post"].sum(1), 1) and sum(sum(r[1:]) for r in ld["confusion"]) == 120
wv = np.mean([ld["canon"][gl == c, 0].var(ddof=1) for c in "pqr"]); assert abs(wv - 1) < 0.05, wv
print("All PlotBench analysis3 checks passed.")
