"""PlotBench self-check, part 8 (Kenward-Roger, multivariate quadrature): run `python test_analysis8.py`. Author: Kishan Tiwari."""
import numpy as np
from scipy import integrate, special, stats
from plotbench import analysis3 as C, analysis5 as E, analysis7 as G, analysis8 as H

rng = np.random.default_rng(61)

# 1. KR reproduces the exact split-plot (mixed-design) ANOVA F tests in a balanced design
ns, nw = 16, 3; subj = np.repeat(np.arange(ns), nw); grp = np.where(subj < 8, "a", "b"); cond = np.tile(["c0", "c1", "c2"], ns)
y = np.where(grp == "a", 0, 1.0) + np.select([cond == "c1", cond == "c2"], [0.5, 1.2], 0) + rng.normal(0, 1, ns)[subj] + rng.normal(0, 0.5, ns * nw)
import pandas as pd
df = pd.DataFrame({"grp": grp, "cond": cond}); X, names = E.design(df, ["grp", "cond"])
terms = [G.term(subj, "subject", [("Intercept", np.ones(len(y)))])]
fit = G.lmm_general(y, X, names, terms, "REML"); tab, ftab = H.kr_tables(fit, y, X, names, terms)
exact = C.mixed_anova(y, subj, grp, cond)
fg = [r for r in ftab if r[0] == "grp"][0]; fc = [r for r in ftab if r[0] == "cond"][0]
assert abs(fg[1] - exact[0][4]) < 1e-5 and abs(fg[3] - exact[0][2] * 0 - 14) < 1e-5, (fg, exact[0])     # F(1, 14)
ss_b, ss_ab, ss_e = exact[2][1], exact[3][1], exact[4][1]   # additive model pools the interaction into error: F(2, 30)
assert abs(fc[1] - (ss_b / 2) / ((ss_e + ss_ab) / 30)) < 1e-5 and abs(fc[3] - 30) < 1e-4, (fc, exact)
# with the interaction in the model, KR's interaction test equals the exact F(2, 28)
for c in ("c1", "c2"): df[f"gx{c}"] = ((df.grp == "b") & (df.cond == c)).astype(float)
Xi, ni = E.design(df, ["grp", "cond", "gxc1", "gxc2"]); fi = G.lmm_general(y, Xi, ni, terms, "REML")
L = np.zeros((2, Xi.shape[1])); L[0, ni.index("gxc1")] = 1; L[1, ni.index("gxc2")] = 1
fint = H.kenward_roger(fi, y, Xi, terms, [("grp x cond", L)])[0][0]
assert abs(fint[1] - exact[3][4]) < 1e-5 and abs(fint[3] - 28) < 1e-4, (fint, exact[3])
# 2. balanced one-way random intercept: KR df for the intercept is k - 1 and its SE is unchanged
k, m = 10, 5; g = np.repeat(np.arange(k), m); yy = 3 + rng.normal(0, 1, k)[g] + rng.normal(0, 1, k * m); X1 = np.ones((k * m, 1))
t1 = [G.term(g, "g", [("Intercept", np.ones(k * m))])]; f1 = G.lmm_general(yy, X1, ["Intercept"], t1); tab1, _ = H.kr_tables(f1, yy, X1, ["Intercept"], t1)
assert abs(tab1[0][4] - (k - 1)) < 1e-4 and abs(tab1[0][2] - f1["fixed"][0][2]) < 1e-6, tab1
# 3. unbalanced data: KR SE >= model-based SE (the adjustment inflates the covariance)
gu = np.repeat(np.arange(12), rng.integers(2, 9, 12)); xu = rng.normal(size=len(gu)); yu = 1 + 0.5 * xu + rng.normal(0, 1, 12)[gu] + rng.normal(0, 1, len(gu))
Xu = np.column_stack([np.ones(len(gu)), xu]); tu = [G.term(gu, "g", [("Intercept", np.ones(len(gu)))])]
fu = G.lmm_general(yu, Xu, ["Intercept", "x"], tu); tabu, _ = H.kr_tables(fu, yu, Xu, ["Intercept", "x"], tu)
assert all(tabu[j][2] >= fu["fixed"][j][2] - 1e-9 for j in range(2)) and 1 < tabu[0][4] < len(gu)

# 4. multivariate quadrature: exact against 2-D brute-force integration of one group's likelihood
ng, per = 20, 8; gq = np.repeat(np.arange(ng), per); xq = rng.normal(size=ng * per)
b = rng.multivariate_normal([0, 0], [[1.0, 0.3], [0.3, 0.5]], ng); yq = (rng.uniform(size=ng * per) < special.expit(0.2 + 0.8 * xq + b[gq, 0] + b[gq, 1] * xq)).astype(float)
Xq = np.column_stack([np.ones(len(yq)), xq])
aq = H.glmm_agq_multi(yq, Xq, ["Intercept", "x"], gq, "g", [("Intercept", np.ones(len(yq))), ("x", xq)], "Binomial", nagq=12)
beta = aq["beta"]; Sig = aq["G"][0]; Si = np.linalg.inv(Sig); det = np.linalg.det(Sig); total = 0.0
for j in range(ng):
    yy_, xx_ = yq[gq == j], xq[gq == j]
    def f(u1, u0):
        e = beta[0] + beta[1] * xx_ + u0 + u1 * xx_; u = np.array([u0, u1])
        return np.exp(np.sum(yy_ * e - np.logaddexp(0, e)) - 0.5 * u @ Si @ u) / (2 * np.pi * np.sqrt(det))
    total += np.log(integrate.dblquad(f, -10, 10, -10, 10, epsabs=1e-13, epsrel=1e-10)[0])
assert abs(total - aq["stats"]["Log-likelihood"]) < 1e-4, (total, aq["stats"]["Log-likelihood"])
# one point per dimension = Laplace at the same parameters
ll1 = H.glmm_agq_multi(yq, Xq, ["Intercept", "x"], gq, "g", [("Intercept", np.ones(len(yq))), ("x", xq)], "Binomial", nagq=1)
lap = ll1["laplace"]; Lc = np.linalg.cholesky(lap["G"][0]); th = Lc.copy(); th[np.diag_indices(2)] = np.log(np.diag(Lc))
at_lap = ll1["loglik_fn"](np.r_[lap["beta"], th[np.tril_indices(2)]])
assert abs(at_lap - lap["stats"]["Log-likelihood"]) < 1e-6, (at_lap, lap["stats"]["Log-likelihood"])  # same formula, same parameters
assert ll1["stats"]["Log-likelihood"] >= at_lap - 1e-9  # optimising all parameters can only raise it
# single random intercept: agrees with the one-dimensional quadrature of part 7
a7 = G.glmm_agq(yq, Xq, ["Intercept", "x"], gq, "g", "Binomial", nagq=11)
a8 = H.glmm_agq_multi(yq, Xq, ["Intercept", "x"], gq, "g", [("Intercept", np.ones(len(yq)))], "Binomial", nagq=11)
assert abs(a7["stats"]["Log-likelihood"] - a8["stats"]["Log-likelihood"]) < 1e-4 and np.allclose(a7["beta"], a8["beta"], atol=2e-3)
try: H.glmm_agq_multi(yq, Xq, ["I", "x"], gq, "g", [("a", np.ones(len(yq))), ("b", xq), ("c", xq ** 2)], "Binomial", nagq=30); raise AssertionError
except ValueError: pass
print("All PlotBench analysis8 checks passed.")
