"""PlotBench self-check, part 6 (crossed random effects, GLMM): run `python test_analysis6.py`. Author: Kishan Tiwari."""
import numpy as np
from plotbench import analysis5 as E, analysis6 as F

rng = np.random.default_rng(41)

# one random-intercept term must reproduce the existing mixed model exactly
k, m = 12, 6; grp = np.repeat(np.arange(k), m); y = 5 + rng.normal(0, 2, k)[grp] + rng.normal(0, 1, k * m); X = np.ones((k * m, 1))
a = E.lmm(y, X, ["Intercept"], grp); b = F.lmm_terms(y, X, ["Intercept"], [F.intercept_term(grp, "group")])
assert abs(a["s2"] - b["s2"]) < 1e-6 * a["s2"] and abs(a["G"][0, 0] - b["var"][0]) < 1e-6 * a["G"][0, 0] and abs(a["fixed"][0][2] - b["fixed"][0][2]) < 1e-6
assert abs(a["stats"]["REML log-likelihood"] - b["stats"]["REML log-likelihood"]) < 1e-6
assert np.allclose([r[1] for r in a["blup"]], [r[1] for r in b["blups"][0][1]], atol=1e-6)

# crossed subjects x items: both variance components recovered
ns, ni = 40, 30; S = np.repeat(np.arange(ns), ni); I = np.tile(np.arange(ni), ns); x = rng.normal(size=ns * ni)
yc = 2 + 0.5 * x + rng.normal(0, 1.5, ns)[S] + rng.normal(0, 0.8, ni)[I] + rng.normal(0, 0.5, ns * ni)
Xc = np.column_stack([np.ones(len(yc)), x])
cr = F.lmm_terms(yc, Xc, ["Intercept", "x"], [F.intercept_term(S, "subject"), F.intercept_term(I, "item")])
assert abs(cr["beta"][1] - 0.5) < 0.05 and 1.2 < np.sqrt(cr["var"][0]) < 1.9 and 0.5 < np.sqrt(cr["var"][1]) < 1.15 and abs(np.sqrt(cr["s2"]) - 0.5) < 0.05, cr["variance"]
only_s = F.lmm_terms(yc, Xc, ["Intercept", "x"], [F.intercept_term(S, "subject")])
assert cr["stats"]["REML log-likelihood"] > only_s["stats"]["REML log-likelihood"] + 50  # the item term is clearly needed
# nested: sites containing samples
site = np.repeat(np.arange(10), 20); samp = np.tile(np.repeat(np.arange(4), 5), 10)
yn = rng.normal(0, 2, 10)[site] + rng.normal(0, 1, 40)[site * 4 + samp] + rng.normal(0, 0.3, 200)
nr = F.lmm_terms(yn, np.ones((200, 1)), ["Intercept"], [F.intercept_term(site, "site"), F.intercept_term(F.nested_labels(site, samp), "site:sample")])
assert nr["stats"]["Levels of site:sample"] == 40 and 0.6 < np.sqrt(nr["var"][1]) < 1.4 and abs(np.sqrt(nr["s2"]) - 0.3) < 0.06, nr["variance"]
# uncorrelated random slope term
tt = np.tile(np.arange(8.0), 30); gg = np.repeat(np.arange(30), 8)
ys = 1 + np.repeat(rng.normal(0, 1, 30), 8) + (2 + np.repeat(rng.normal(0, 0.6, 30), 8)) * tt + rng.normal(0, 0.4, 240)
sr = F.lmm_terms(ys, np.column_stack([np.ones(240), tt]), ["Intercept", "t"], [F.intercept_term(gg, "g"), F.slope_term(gg, tt, "g: t")])
assert abs(sr["beta"][1] - 2) < 0.35 and 0.35 < np.sqrt(sr["var"][1]) < 0.9

# GLMM: with no real random effect, the fit approaches the GLM
n = 600; g2 = np.repeat(np.arange(30), 20); xx = rng.normal(size=n); Xg = np.column_stack([np.ones(n), xx])
yp0 = rng.poisson(np.exp(0.3 + 0.5 * xx)); gm0 = F.glmm(yp0, Xg, ["Intercept", "x"], [F.intercept_term(g2, "g")], "Poisson")
gl0 = E.glm(yp0, Xg, ["Intercept", "x"], "Poisson")
assert np.sqrt(gm0["var"][0]) < 0.15 and np.allclose(gm0["beta"], [r[1] for r in gl0["coef"]], atol=0.03)
# Poisson GLMM recovers the fixed slope and the random SD
yp = rng.poisson(np.exp(0.3 + 0.5 * xx + rng.normal(0, 0.7, 30)[g2])); gp = F.glmm(yp, Xg, ["Intercept", "x"], [F.intercept_term(g2, "g")], "Poisson")
assert abs(gp["beta"][1] - 0.5) < 0.07 and 0.45 < np.sqrt(gp["var"][0]) < 1.0 and gp["exp_label"].startswith("Rate"), gp["variance"]
# binomial GLMM (logit) with crossed random intercepts
s3, i3 = np.repeat(np.arange(30), 20), np.tile(np.arange(20), 30); x3 = rng.normal(size=600)
eta = -0.2 + 1.0 * x3 + rng.normal(0, 1.0, 30)[s3] + rng.normal(0, 0.6, 20)[i3]; yb = (rng.uniform(size=600) < 1 / (1 + np.exp(-eta))).astype(float)
gb = F.glmm(yb, np.column_stack([np.ones(600), x3]), ["Intercept", "x"], [F.intercept_term(s3, "subject"), F.intercept_term(i3, "item")], "Binomial")
assert abs(gb["beta"][1] - 1.0) < 0.25 and 0.5 < np.sqrt(gb["var"][0]) < 1.6 and gb["stats"]["Converged"], (gb["beta"], gb["variance"])
# Laplace log-likelihood at (almost) zero variance equals the GLM log-likelihood
d0 = np.full(30, 1e-10); beta, u, eta_, mu, H, W = F._pirls(yp0.astype(float), Xg, F.intercept_term(g2, "g")["Z"], d0, "Poisson", "log", np.ones(n), np.zeros(n))
assert abs(F._cond_loglik("Poisson", yp0.astype(float), mu, np.ones(n)) - gl0["stats"]["Log-likelihood"]) < 1e-4
print("All PlotBench analysis6 checks passed.")
