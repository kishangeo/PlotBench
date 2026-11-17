"""PlotBench analysis, part 8: Kenward-Roger small-sample inference for linear mixed models, and adaptive
Gauss-Hermite quadrature for GLMMs whose grouping factor carries several correlated random effects
(e.g. a random intercept and slope per subject).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
References: Kenward & Roger (1997) Biometrics 53:983-997; Halekoh & Hojsgaard (2014) J. Stat. Softw. 59(9) (pbkrtest);
Pinheiro & Bates (1995) J. Comput. Graph. Stat. 4:12-35 (adaptive Gaussian quadrature).
"""
import itertools
import numpy as np
from scipy import stats, optimize, special

from .analysis7 import _build, _flatten, _lambdas, _mu, glmm_general, term, CANONICAL
from .analysis6 import _cond_loglik

KR_MAX_N = 3000  # dense n x n matrices beyond this get slow; the app then reports the approximate df instead


# ================================================================ Kenward-Roger
def _vc_basis(blocks):
    """Linear covariance structure: V = sum_r sigma_r * G_r (one G per unique covariance entry, plus the residual)."""
    Gs, labels = [], []
    for b in blocks:
        Zb = b["Z"]; q = b["q"]
        for a in range(q):
            for c in range(a + 1):
                E = np.zeros((q, q)); E[a, c] = E[c, a] = 1.0
                Za = Zb.reshape(Zb.shape[0], -1); K = np.kron(np.eye(len(b["levels"])), E); Gs.append(Za @ K @ Za.T)
                labels.append(f"{b['name']}: {'var' if a == c else 'cov'}({b['effects'][c]}, {b['effects'][a]})")
    Gs.append(np.eye(blocks[0]["Z"].shape[0])); labels.append("Residual")
    return Gs, labels


def _sigma_values(blocks, G_list, s2):
    vals = []
    for b, G in zip(blocks, G_list):
        for a in range(b["q"]):
            for c in range(a + 1): vals.append(G[a, c])
    return np.array(vals + [s2])


def kenward_roger(fit, y, X, terms, contrasts):
    """fit: result of analysis7.lmm_general with REML. contrasts: list of (label, L) with L an (l x p) matrix.
    Returns rows (label, F*, num df, den df, p, scale lambda) and the adjusted covariance of the fixed effects."""
    terms = _flatten(terms); m = fit["mask"]; y = np.asarray(y, float)[m]; X = np.asarray(X, float)[m]; n, p = X.shape
    if n > KR_MAX_N: raise ValueError(f"Kenward-Roger is limited to {KR_MAX_N} observations here.")
    blocks = _build(terms, m); Gs, _ = _vc_basis(blocks); sig = _sigma_values(blocks, fit["G"], fit["s2"])
    V = sum(s * G for s, G in zip(sig, Gs)); Vi = np.linalg.inv(V); VX = Vi @ X; Phi = np.linalg.inv(X.T @ VX)
    Pm = Vi - VX @ Phi @ VX.T  # REML projection
    k = len(Gs); PG = [Pm @ G for G in Gs]; ViG = [Vi @ G for G in Gs]
    info = np.array([[0.5 * np.sum(PG[i] * PG[j].T) for j in range(k)] for i in range(k)])  # tr(P G_i P G_j)/2
    W = np.linalg.pinv(info)
    Pi = [-(VX.T @ G @ VX) for G in Gs]                       # d(X'V^-1X)/d sigma_i
    Q = [[VX.T @ ViG[i] @ G @ VX for G in Gs] for i in range(k)]  # X'V^-1 G_i V^-1 G_j V^-1 X
    adj = sum(W[i, j] * (Q[i][j] - Pi[i] @ Phi @ Pi[j]) for i in range(k) for j in range(k))
    PhiA = Phi + 2 * Phi @ adj @ Phi
    beta = fit["beta"]; out = []
    for label, L in contrasts:
        L = np.atleast_2d(np.asarray(L, float)); l = L.shape[0]
        Theta = L.T @ np.linalg.inv(L @ Phi @ L.T) @ L
        TPP = [Theta @ Phi @ Pi[i] @ Phi for i in range(k)]
        A1 = sum(W[i, j] * np.trace(TPP[i]) * np.trace(TPP[j]) for i in range(k) for j in range(k))
        A2 = sum(W[i, j] * np.trace(TPP[i] @ TPP[j]) for i in range(k) for j in range(k))
        Bv = (A1 + 6 * A2) / (2 * l); g = ((l + 1) * A1 - (l + 4) * A2) / ((l + 2) * A2) if A2 > 0 else 0.0
        den = 3 * l + 2 * (1 - g); c1, c2, c3 = g / den, (l - g) / den, (l + 2 - g) / den
        Es = 1 / (1 - A2 / l); Vs = 2 / l * (1 + c1 * Bv) / ((1 - c2 * Bv) ** 2 * (1 - c3 * Bv))
        rho = Vs / (2 * Es ** 2); mdf = 4 + (l + 2) / (l * rho - 1) if l * rho > 1 else np.inf; lam = mdf / (Es * (mdf - 2)) if np.isfinite(mdf) else 1.0
        Fw = float(beta @ L.T @ np.linalg.inv(L @ PhiA @ L.T) @ L @ beta) / l; Fs = lam * Fw
        out.append([label, Fs, l, mdf, stats.f.sf(Fs, l, mdf) if np.isfinite(mdf) else stats.chi2.sf(Fs * l, l), lam])
    return out, PhiA


def kr_tables(fit, y, X, names, terms):
    """Per-coefficient t tests and per-factor F tests (text predictors grouped) with Kenward-Roger df and SEs."""
    p = len(names); coef = [(nm, np.eye(p)[[j]]) for j, nm in enumerate(names)]
    rows, PhiA = kenward_roger(fit, y, X, terms, coef); se = np.sqrt(np.diag(PhiA)); beta = fit["beta"]; tab = []
    for j, (nm, r) in enumerate(zip(names, rows)):
        d = r[3]; t = beta[j] / se[j]; q = stats.t.ppf(0.975, d) if np.isfinite(d) else 1.96
        tab.append([nm, beta[j], se[j], t, d, 2 * (stats.t.sf(abs(t), d) if np.isfinite(d) else stats.norm.sf(abs(t))), beta[j] - q * se[j], beta[j] + q * se[j]])
    groups = {}
    for j, nm in enumerate(names):
        if nm != "Intercept": groups.setdefault(nm.split("[")[0], []).append(j)
    multi = [(f, np.eye(p)[idx]) for f, idx in groups.items()]
    ftab = kenward_roger(fit, y, X, terms, multi)[0] if multi else []
    return tab, ftab


# ================================================================ multivariate adaptive Gauss-Hermite quadrature
def glmm_agq_multi(y, X, fixed_names, labels, group_name, effects, family="Binomial", nagq=5, weights=None, offset=None):
    """GLMM with q correlated random effects for one grouping factor, by adaptive (tensor-product) Gauss-Hermite
    quadrature: nagq**q points per group. Canonical link. effects: [(label, values), ...], first usually the intercept."""
    if family not in CANONICAL: raise ValueError("Quadrature is available for the Binomial (logit) and Poisson (log) families.")
    q = len(effects)
    if nagq ** q > 20000: raise ValueError(f"{nagq} points in {q} dimensions is {nagq ** q} points per group; use fewer points.")
    y = np.asarray(y, float); X = np.asarray(X, float); n0 = len(y)
    w = np.ones(n0) if weights is None else np.asarray(weights, float); off = np.zeros(n0) if offset is None else np.asarray(offset, float)
    lab = np.asarray(labels).astype(str); Zv = np.column_stack([np.asarray(v, float) for _, v in effects])
    m = np.isfinite(y) & np.all(np.isfinite(X), 1) & np.all(np.isfinite(Zv), 1) & np.isfinite(w) & np.isfinite(off) & (w > 0) & (lab != "nan")
    y, X, w, off, lab, Zv = y[m], X[m], w[m], off[m], lab[m], Zv[m]
    if family == "Binomial": y = np.round(y * w) / w
    lap = glmm_general(y, X, fixed_names, [term(lab, group_name, list(zip([e for e, _ in effects], Zv.T)))], family, CANONICAL[family], w, off)
    L = [r[0] for r in lap["blups"][0][1]]; pos = {l: j for j, l in enumerate(L)}; gi = np.array([pos[v] for v in lab]); ng = len(L); p = X.shape[1]
    z1, w1 = np.polynomial.hermite.hermgauss(int(nagq)); Zg = np.array(list(itertools.product(z1, repeat=q)))
    Wg = np.prod(np.array(list(itertools.product(w1, repeat=q))), 1); tri = np.tril_indices(q)
    const = (float(np.sum(special.gammaln(w + 1) - special.gammaln(np.round(y * w) + 1) - special.gammaln(w - np.round(y * w) + 1)))
             if family == "Binomial" else float(-np.sum(special.gammaln(y + 1))))

    def unpack(prm):
        beta = prm[:p]; Lc = np.zeros((q, q)); Lc[tri] = prm[p:]; Lc[np.diag_indices(q)] = np.exp(np.diag(Lc)); return beta, Lc

    warm = {'U': np.zeros((ng, q))}

    def loglik(prm, modes=False):
        beta, Lc = unpack(prm); Sig = Lc @ Lc.T + 1e-12 * np.eye(q); Si = np.linalg.inv(Sig); _, ld = np.linalg.slogdet(Sig)
        eta0 = X @ beta + off; U = warm['U'].copy()  # start from the previous modes: far fewer Newton steps
        for _ in range(60):  # Newton for each group's mode (vectorised over groups)
            mu = _mu(family, CANONICAL[family], eta0 + np.sum(Zv * U[gi], 1)); r = w * (y - mu); v = w * (mu * (1 - mu) if family == "Binomial" else mu)
            g1 = np.zeros((ng, q)); np.add.at(g1, gi, r[:, None] * Zv); g1 -= U @ Si
            Hs = np.zeros((ng, q, q)); np.add.at(Hs, gi, v[:, None, None] * Zv[:, :, None] * Zv[:, None, :]); Hs += Si
            step = np.linalg.solve(Hs, g1[:, :, None])[:, :, 0]; U += step
            if np.max(np.abs(step)) < 1e-11: break
        if np.all(np.isfinite(U)): warm['U'] = U
        Cs = np.linalg.cholesky(np.linalg.inv(Hs))  # per-group scale of the quadrature grid
        logw = np.log(Wg) + np.sum(Zg ** 2, 1)
        vals = np.empty((len(Zg), ng))
        for k, zk in enumerate(Zg):
            Uk = U + np.sqrt(2) * (Cs @ zk); e = eta0 + np.sum(Zv * Uk[gi], 1)
            lp = (w * y * e - w * np.logaddexp(0, e)) if family == "Binomial" else (y * e - np.exp(e))
            vals[k] = np.bincount(gi, lp, minlength=ng) - 0.5 * np.einsum("ij,jk,ik->i", Uk, Si, Uk) - 0.5 * (q * np.log(2 * np.pi) + ld) + logw[k]
        logdetC = np.sum(np.log(np.abs(np.diagonal(Cs, axis1=1, axis2=2))), 1)
        ll = float(np.sum(special.logsumexp(vals, axis=0) + logdetC + 0.5 * q * np.log(2))) + const
        return (ll, U) if modes else ll

    Lc0 = np.linalg.cholesky(lap["G"][0] + 1e-6 * np.eye(q)); th0 = Lc0.copy(); th0[np.diag_indices(q)] = np.log(np.diag(Lc0))
    diag = set(int(i * (i + 1) / 2 + i) for i in range(q))  # positions of the log-SDs within the packed lower triangle
    th0[np.diag_indices(q)] = np.clip(np.diag(th0), -6.0, 4.0)
    start = np.r_[lap["beta"], th0[tri]]; obj = lambda v: -loglik(v)
    # bounds keep a variance that is truly ~0 from being chased towards log(0) for ever (seen with tiny groups)
    bounds = [(None, None)] * p + [((-7.0, 5.0) if j in diag else (-50.0, 50.0)) for j in range(len(tri[0]))]
    r = optimize.minimize(obj, start, method="L-BFGS-B", bounds=bounds, options={"maxiter": 600, "ftol": 1e-12, "gtol": 1e-6})
    if not r.success:
        r2 = optimize.minimize(obj, r.x, method="Nelder-Mead", bounds=bounds, options={"xatol": 1e-6, "fatol": 1e-8, "maxfev": 3000})
        if r2.fun <= r.fun: r = r2
    ll, U = loglik(r.x, True); beta, Lc = unpack(r.x); Sig = Lc @ Lc.T
    H = _hess(obj, r.x); cov = np.linalg.pinv(H); se = np.sqrt(np.abs(np.diag(cov)))[:p]; z = beta / se; expo = True
    rows = [[nm, b, s, zz, 2 * stats.norm.sf(abs(zz)), b - 1.96 * s, b + 1.96 * s, np.exp(b), np.exp(b - 1.96 * s), np.exp(b + 1.96 * s)]
            for nm, b, s, zz in zip(fixed_names, beta, se, z)]
    names = [e for e, _ in effects]; vc = [[f"{group_name}: {e}", Sig[i, i], np.sqrt(Sig[i, i])] for i, e in enumerate(names)]
    for i in range(q):
        for j in range(i): vc.append([f"{group_name}: corr({names[j]}, {names[i]})", Sig[i, j] / np.sqrt(Sig[i, i] * Sig[j, j]), ""])
    k = p + len(tri[0]); fitted = np.full(n0, np.nan); fitted[np.nonzero(m)[0]] = _mu(family, CANONICAL[family], X @ beta + off + np.sum(Zv * U[gi], 1))
    return {"family": family, "link": CANONICAL[family], "fixed": rows, "exp_label": "Odds ratio" if family == "Binomial" else "Rate ratio exp(b)",
            "variance": vc, "blups": [(group_name, [[l] + list(U[j]) for j, l in enumerate(L)], names)], "beta": beta, "G": [Sig], "fitted": fitted,
            "mask": m, "laplace": lap, "loglik_fn": loglik, "params": r.x,
            "stats": {"Method": f"Adaptive Gauss-Hermite quadrature, {int(nagq)} points per dimension ({int(nagq) ** q} per group)",
                      "Observations": int(m.sum()), f"Levels of {group_name}": ng, "Log-likelihood": ll, "AIC": 2 * k - 2 * ll,
                      "BIC": k * np.log(m.sum()) - 2 * ll, "Laplace log-likelihood (for comparison)": lap["stats"]["Log-likelihood"],
                      "Converged": bool(r.success)}}


def _hess(f, x, h=1e-4):
    k = len(x); H = np.zeros((k, k)); f0 = f(x); E = np.eye(k) * h
    for i in range(k):
        H[i, i] = (f(x + E[i]) - 2 * f0 + f(x - E[i])) / h ** 2
        for j in range(i):
            H[i, j] = H[j, i] = (f(x + E[i] + E[j]) - f(x + E[i] - E[j]) - f(x - E[i] + E[j]) + f(x - E[i] - E[j])) / (4 * h * h)
    return H
