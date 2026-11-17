"""PlotBench self-check, part 7 (correlated random slopes, adaptive quadrature): run `python test_analysis7.py`. Author: Kishan Tiwari."""
import numpy as np
from scipy import integrate, special
from plotbench import analysis5 as E, analysis6 as F, analysis7 as G

rng = np.random.default_rng(51)

# 1. one factor with correlated intercept + slope must equal the existing single-factor model
k, m = 30, 8; g = np.repeat(np.arange(k), m); t = np.tile(np.arange(m, dtype=float), k)
b = rng.multivariate_normal([0, 0], [[4, 0.6], [0.6, 0.25]], k); y = 10 + b[g, 0] + (1.5 + b[g, 1]) * t + rng.normal(0, 0.5, k * m)
X = np.column_stack([np.ones(len(y)), t])
old = E.lmm(y, X, ["Intercept", "t"], g, Z=X, random_names=("Intercept", "t"))
new = G.lmm_general(y, X, ["Intercept", "t"], [G.term(g, "g", [("Intercept", np.ones(len(y))), ("t", t)])])
assert abs(old["stats"]["REML log-likelihood"] - new["stats"]["REML log-likelihood"]) < 1e-5, (old["stats"], new["stats"])
assert np.allclose(old["G"], new["G"][0], rtol=1e-3, atol=1e-5) and abs(old["s2"] - new["s2"]) < 1e-5 and np.allclose(old["beta"], new["beta"], atol=1e-6)
# uncorrelated version equals the part-6 independent-terms model
u1 = G.lmm_general(y, X, ["Intercept", "t"], [G.term(g, "g", [("Intercept", np.ones(len(y))), ("t", t)], correlated=False)])
u2 = F.lmm_terms(y, X, ["Intercept", "t"], [F.intercept_term(g, "g"), F.slope_term(g, t, "g: t")])
assert abs(u1["stats"]["REML log-likelihood"] - u2["stats"]["REML log-likelihood"]) < 1e-5
assert new["stats"]["REML log-likelihood"] >= u1["stats"]["REML log-likelihood"] - 1e-6  # the correlated model nests the uncorrelated one

# 2. crossed: subjects with correlated intercept + slope, items with intercept
ns, ni = 30, 12; S = np.repeat(np.arange(ns), ni); I = np.tile(np.arange(ni), ns); x = rng.normal(size=ns * ni)
bs = rng.multivariate_normal([0, 0], [[1.0, 0.4], [0.4, 0.36]], ns); bi = rng.normal(0, 0.7, ni)
yc = 2 + 0.8 * x + bs[S, 0] + bs[S, 1] * x + bi[I] + rng.normal(0, 0.3, ns * ni); Xc = np.column_stack([np.ones(len(yc)), x])
cr = G.lmm_general(yc, Xc, ["Intercept", "x"], [G.term(S, "subject", [("Intercept", np.ones(len(yc))), ("x", x)]), G.term(I, "item", [("Intercept", np.ones(len(yc)))])])
Gs = cr["G"][0]; corr = Gs[0, 1] / np.sqrt(Gs[0, 0] * Gs[1, 1])
assert abs(cr["beta"][1] - 0.8) < 0.3 and 0.6 < np.sqrt(Gs[0, 0]) < 1.5 and 0.4 < np.sqrt(Gs[1, 1]) < 0.85 and corr > 0, (cr["variance"])
assert 0.35 < np.sqrt(cr["G"][1][0, 0]) < 1.1 and abs(np.sqrt(cr["s2"]) - 0.3) < 0.05
assert any("corr(Intercept, x)" in r[0] for r in cr["variance"]) and len(cr["blups"][0][1][0]) == 3

# 3. binomial GLMM with a correlated random slope
n = 1200; gb = np.repeat(np.arange(60), 20); xb = rng.normal(size=n); bb = rng.multivariate_normal([0, 0], [[1, 0.3], [0.3, 0.5]], 60)
yb = (rng.uniform(size=n) < special.expit(0.2 + 1.0 * xb + bb[gb, 0] + bb[gb, 1] * xb)).astype(float)
gl = G.glmm_general(yb, np.column_stack([np.ones(n), xb]), ["Intercept", "x"], [G.term(gb, "g", [("Intercept", np.ones(n)), ("x", xb)])], "Binomial")
assert abs(gl["beta"][1] - 1.0) < 0.3 and 0.4 < np.sqrt(gl["G"][0][1, 1]) < 1.1, gl["variance"]
# a single random intercept reproduces the part-6 GLMM
g6 = F.glmm(yb, np.column_stack([np.ones(n), xb]), ["Intercept", "x"], [F.intercept_term(gb, "g")], "Binomial")
g7 = G.glmm_general(yb, np.column_stack([np.ones(n), xb]), ["Intercept", "x"], [G.term(gb, "g", [("Intercept", np.ones(n))])], "Binomial")
assert abs(g6["stats"]["Log-likelihood"] - g7["stats"]["Log-likelihood"]) < 1e-3 and np.allclose(g6["beta"], g7["beta"], atol=2e-3)

# 4. adaptive quadrature: exact against brute-force integration, and nAGQ = 1 equals Laplace
ng, per = 25, 6; ga = np.repeat(np.arange(ng), per); xa = rng.normal(size=ng * per)
ya = (rng.uniform(size=ng * per) < special.expit(-0.3 + 0.9 * xa + rng.normal(0, 1.5, ng)[ga])).astype(float); Xa = np.column_stack([np.ones(len(ya)), xa])
aq = G.glmm_agq(ya, Xa, ["Intercept", "x"], ga, "g", "Binomial", nagq=25)
b0, b1 = aq["beta"]; sd = aq["sd"]; brute = 0.0
for j in range(ng):
    yy, xx = ya[ga == j], xa[ga == j]
    f = lambda u: np.exp(np.sum(yy * (b0 + b1 * xx + u) - np.log1p(np.exp(b0 + b1 * xx + u)))) * np.exp(-u * u / (2 * sd * sd)) / np.sqrt(2 * np.pi * sd * sd)
    brute += np.log(integrate.quad(f, -15 * sd - 10, 15 * sd + 10, limit=400, epsabs=0, epsrel=1e-12)[0])
assert abs(brute - aq["stats"]["Log-likelihood"]) < 1e-6, (brute, aq["stats"]["Log-likelihood"])
lap = aq["laplace"]; prm = np.r_[lap["beta"], 0.5 * np.log(lap["G"][0][0, 0])]
nodes, wts = np.polynomial.hermite.hermgauss(1)
ll1 = G._agq_loglik(prm, ya, Xa, ga, ng, np.ones(len(ya)), np.zeros(len(ya)), "Binomial", nodes, wts)
assert abs(ll1 - lap["stats"]["Log-likelihood"]) < 1e-4, (ll1, lap["stats"]["Log-likelihood"])
assert aq["stats"]["Log-likelihood"] >= ll1 - 1e-6 and aq["sd"] > 0  # small groups: quadrature is more accurate, so it differs from Laplace
# Poisson AGQ recovers parameters
gp = np.repeat(np.arange(40), 10); xp = rng.normal(size=400); yp = rng.poisson(np.exp(0.5 + 0.4 * xp + rng.normal(0, 0.6, 40)[gp]))
ap = G.glmm_agq(yp, np.column_stack([np.ones(400), xp]), ["Intercept", "x"], gp, "g", "Poisson", nagq=9)
assert abs(ap["beta"][1] - 0.4) < 0.08 and 0.35 < ap["sd"] < 0.9 and ap["stats"]["Converged"]
print("All PlotBench analysis7 checks passed.")
