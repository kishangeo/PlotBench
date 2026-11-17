"""PlotBench self-check, part 5 (GLM and mixed models): run `python test_analysis5.py`. Author: Kishan Tiwari."""
import numpy as np
import pandas as pd
from scipy import stats
from plotbench import analysis5 as E, analysis4 as D, analysis as A

rng = np.random.default_rng(31)
n = 400; x1 = rng.normal(size=n); x2 = rng.normal(size=n); X = np.column_stack([np.ones(n), x1, x2]); nm = ["Intercept", "x1", "x2"]

# Gaussian GLM equals ordinary least squares
y = 1 + 2 * x1 - x2 + rng.normal(0, 0.5, n); g = E.glm(y, X, nm)
mr = A.multiple_regression(y, X[:, 1:], ["x1", "x2"])
assert np.allclose([r[1] for r in g["coef"]], [r[1] for r in mr["coef"]]) and np.allclose([r[2] for r in g["coef"]], [r[2] for r in mr["coef"]])
# Binomial GLM equals the logistic regression already in the app
yb = (rng.uniform(size=n) < 1 / (1 + np.exp(-(0.3 + 1.5 * x1)))).astype(float)
gb = E.glm(yb, X[:, :2], nm[:2], "Binomial"); lg = D.logistic_regression(yb, x1[:, None], ["x1"])
assert np.allclose([r[1] for r in gb["coef"]], [r[1] for r in lg["coef"]], atol=1e-7) and gb["exp_label"] == "Odds ratio"
assert abs(gb["stats"]["Log-likelihood"] - lg["stats"]["Log-likelihood"]) < 1e-6
# probit and cloglog links converge
for link in ("probit", "cloglog"): assert E.glm(yb, X[:, :2], nm[:2], "Binomial", link)["stats"]["Iterations"] < 50
# grouped binomial (proportion + trials)
tr = rng.integers(5, 30, n); pr = 1 / (1 + np.exp(-(-0.5 + x1))); k = rng.binomial(tr, pr)
gg = E.glm(k / tr, X[:, :2], nm[:2], "Binomial", weights=tr); assert abs(gg["coef"][1][1] - 1) < 0.15
# Poisson recovers coefficients; offset (exposure) works; deviance matches the formula
yp = rng.poisson(np.exp(0.5 + 0.8 * x1 - 0.3 * x2)); gp = E.glm(yp, X, nm, "Poisson")
assert abs(gp["coef"][1][1] - 0.8) < 0.08 and abs(gp["coef"][2][1] + 0.3) < 0.08 and gp["stats"]["p (vs null)"] < 1e-20
expo = rng.uniform(1, 10, n); yo = rng.poisson(expo * np.exp(-1 + 0.5 * x1)); go = E.glm(yo, X[:, :2], nm[:2], "Poisson", offset=np.log(expo))
assert abs(go["coef"][0][1] + 1) < 0.1 and abs(go["coef"][1][1] - 0.5) < 0.06
# overdispersed counts: quasi-Poisson dispersion > 1 and larger SEs than Poisson
yod = rng.negative_binomial(2, 2 / (2 + np.exp(1 + 0.5 * x1)))
gq, gpp = E.glm(yod, X[:, :2], nm[:2], "Quasi-Poisson"), E.glm(yod, X[:, :2], nm[:2], "Poisson")
assert gq["stats"]["Dispersion"] > 1.5 and gq["coef"][1][2] > gpp["coef"][1][2] and np.allclose(gq["coef"][1][1], gpp["coef"][1][1])
# Gamma with log link
yg = rng.gamma(4, np.exp(1 + 0.4 * x1) / 4); gm = E.glm(yg, X[:, :2], nm[:2], "Gamma", "log")
assert abs(gm["coef"][1][1] - 0.4) < 0.06 and abs(gm["stats"]["Dispersion"] - 0.25) < 0.08
assert E.glm(rng.wald(np.exp(0.5 + 0.2 * x1), 5.0), X[:, :2], nm[:2], "Inverse Gaussian")["stats"]["Iterations"] < 60
try: E.glm(-yp - 1, X, nm, "Poisson"); raise AssertionError
except ValueError: pass
# design(): text columns become dummies
df = pd.DataFrame({"dose": [1., 2, 3, 4], "site": ["a", "b", "a", "c"]}); Xd, nd = E.design(df, ["dose", "site"])
assert nd == ["Intercept", "dose", "site[b]", "site[c]"] and Xd[:, 2].tolist() == [0, 1, 0, 0]

# ---- linear mixed model: balanced random intercept, REML equals the ANOVA estimator
k_, m_ = 12, 6; grp = np.repeat(np.arange(k_), m_); u = rng.normal(0, 2, k_); ym = 5 + u[grp] + rng.normal(0, 1, k_ * m_)
r = E.lmm(ym, np.ones((len(ym), 1)), ["Intercept"], grp)
means = ym.reshape(k_, m_).mean(1); msb = m_ * means.var(ddof=1); msw = ((ym.reshape(k_, m_) - means[:, None]) ** 2).sum() / (k_ * (m_ - 1))
assert abs(r["s2"] - msw) < 1e-5 * msw and abs(r["G"][0, 0] - (msb - msw) / m_) < 1e-5 * (msb - msw) / m_, (r["s2"], msw, r["G"][0, 0], (msb - msw) / m_)
assert abs(r["fixed"][0][2] - np.sqrt(msb / (k_ * m_))) < 1e-4  # SE of the mean = sqrt(MSB / N) in the balanced case
blup = np.array([b[1] for b in r["blup"]]); shrink = r["G"][0, 0] / (r["G"][0, 0] + r["s2"] / m_)
assert np.allclose(blup, shrink * (means - r["beta"][0]), atol=1e-6)  # BLUP = shrunken group deviation
# random intercept + slope recovers fixed slope and the slope variance
k2, m2 = 30, 10; grp2 = np.repeat(np.arange(k2), m2); xx = np.tile(np.linspace(0, 9, m2), k2)
b0, b1 = rng.normal(0, 2, k2), rng.normal(0, 0.5, k2); yy = 10 + b0[grp2] + (1.5 + b1[grp2]) * xx + rng.normal(0, 0.5, k2 * m2)
Xf = np.column_stack([np.ones(len(yy)), xx]); rs = E.lmm(yy, Xf, ["Intercept", "x"], grp2, Z=Xf, random_names=("Intercept", "x"))
assert abs(rs["beta"][1] - 1.5) < 0.25 and 0.1 < rs["G"][1, 1] < 0.6 and abs(rs["s2"] - 0.25) < 0.06, (rs["beta"], rs["G"], rs["s2"])
ri = E.lmm(yy, Xf, ["Intercept", "x"], grp2); lr = E.lmm_lrt(rs, ri); assert lr["p"] < 1e-10  # slope variance is clearly needed
ml = E.lmm(ym, np.ones((len(ym), 1)), ["Intercept"], grp, method="ML"); assert ml["G"][0, 0] < r["G"][0, 0]  # ML shrinks variances
assert rs["stats"]["Converged"]
print("All PlotBench analysis5 checks passed.")
