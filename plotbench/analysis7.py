"""PlotBench analysis, part 7: mixed models whose random-effect terms may each hold several correlated effects
(e.g. a random intercept and slope per subject, crossed with a random intercept per item), for Gaussian (REML/ML)
and binomial/Poisson (Laplace) responses; and adaptive Gauss-Hermite quadrature for a GLMM with one random intercept.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Method follows the relative-covariance-factor formulation used by lme4 (Bates et al. 2015): V* = I + Z L L' Z'.
"""
import numpy as np
from scipy import stats, optimize, special

from .analysis5 import FAMILIES, LINKS, _natural
from .analysis6 import _cond_loglik


def term(labels, name, effects, correlated=True):
    """A random-effect term: one grouping factor and its effects [(label, values), ...]. If correlated is False each
    effect becomes its own independent term (returned as a list)."""
    if not correlated and len(effects) > 1: return [term(labels, f"{name}: {e[0]}", [e]) for e in effects]
    return {"name": name, "labels": np.asarray(labels).astype(str), "effects": [(e, np.asarray(v, float)) for e, v in effects]}


def _flatten(terms):
    out = []
    for t in terms: out += t if isinstance(t, list) else [t]
    return out


def _build(terms, m):
    """Z blocks (n x levels*q, columns ordered level-major) and level lists, using rows m."""
    blocks = []
    for t in terms:
        lab = t["labels"][m]; L = sorted(set(lab) - {"nan"}, key=_natural); pos = {l: j for j, l in enumerate(L)}; q = len(t["effects"])
        Z = np.zeros((len(lab), len(L), q)); rows = np.array([pos.get(v, -1) for v in lab])
        for r, (_, x) in enumerate(t["effects"]):
            ok = rows >= 0; Z[np.nonzero(ok)[0], rows[ok], r] = x[m][ok]
        blocks.append({"name": t["name"], "levels": L, "q": q, "Z": Z, "effects": [e for e, _ in t["effects"]]})
    return blocks


def _ntheta(blocks): return [b["q"] * (b["q"] + 1) // 2 for b in blocks]


def _lambdas(theta, blocks):
    out, o = [], 0
    for b, k in zip(blocks, _ntheta(blocks)):
        Lc = np.zeros((b["q"], b["q"])); Lc[np.tril_indices(b["q"])] = theta[o:o + k]; o += k; out.append(Lc)
    return out


def _zt(blocks, lams):
    """Z times the relative covariance factor: concatenated n x Q matrix."""
    return np.hstack([(b["Z"] @ Lc).reshape(b["Z"].shape[0], -1) for b, Lc in zip(blocks, lams)])


def _theta0(blocks, scale=0.7):
    th = []
    for b in blocks:
        Lc = np.eye(b["q"]) * scale; th += list(Lc[np.tril_indices(b["q"])])
    return np.array(th)


def _vc_rows(blocks, lams, s2=1.0):
    rows = []
    for b, Lc in zip(blocks, lams):
        G = Lc @ Lc.T * s2
        for i, e in enumerate(b["effects"]): rows.append([f"{b['name']}: {e}", G[i, i], np.sqrt(max(G[i, i], 0))])
        for i in range(b["q"]):
            for j in range(i):
                den = np.sqrt(max(G[i, i] * G[j, j], 1e-300)); rows.append([f"{b['name']}: corr({b['effects'][j]}, {b['effects'][i]})", G[i, j] / den, ""])
    return rows


def _blups(blocks, lams, btil):
    out, o = [], 0
    for b, Lc in zip(blocks, lams):
        n = len(b["levels"]) * b["q"]; u = (btil[o:o + n].reshape(len(b["levels"]), b["q"]) @ Lc.T); o += n
        out.append((b["name"], [[l] + list(u[j]) for j, l in enumerate(b["levels"])], b["effects"]))
    return out


def _starts(blocks):
    return [_theta0(blocks, s) for s in (0.7, 0.2, 1.5)]


# ================================================================ Gaussian
def lmm_general(y, X, fixed_names, terms, method="REML"):
    terms = _flatten(terms); y = np.asarray(y, float); X = np.asarray(X, float); m = np.isfinite(y) & np.all(np.isfinite(X), 1)
    for t in terms:
        m &= t["labels"] != "nan"
        for _, x in t["effects"]: m &= np.isfinite(x)
    y, X = y[m], X[m]; blocks = _build(terms, m); n, p = X.shape; reml = method.upper() == "REML"; dof = n - p if reml else n

    def parts(th):
        lams = _lambdas(th, blocks); Zt = _zt(blocks, lams); cf = np.linalg.cholesky(np.eye(Zt.shape[1]) + Zt.T @ Zt)
        solve = lambda R: R - Zt @ np.linalg.solve(cf.T, np.linalg.solve(cf, Zt.T @ R))
        XtVX = X.T @ solve(X); beta = np.linalg.solve(XtVX, X.T @ solve(y[:, None])[:, 0]); r = y - X @ beta
        return lams, Zt, cf, beta, r, float(r @ solve(r[:, None])[:, 0]), 2 * np.sum(np.log(np.diag(cf))), XtVX

    def objective(th):
        try: _, _, _, _, _, rss, logdet, XtVX = parts(th)
        except np.linalg.LinAlgError: return 1e300
        v = logdet + dof * np.log(rss / dof) + (np.linalg.slogdet(XtVX)[1] if reml else 0.0)
        return v if np.isfinite(v) else 1e300

    best = None
    for s0 in _starts(blocks):
        r = optimize.minimize(objective, s0, method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 40000, "maxfev": 80000})
        r = optimize.minimize(objective, r.x, method="Powell", options={"xtol": 1e-9, "ftol": 1e-12, "maxiter": 20000})  # polish
        if best is None or r.fun < best.fun: best = r
    lams, Zt, cf, beta, r, rss, logdet, XtVX = parts(best.x); s2 = rss / dof
    se = np.sqrt(np.diag(np.linalg.inv(XtVX)) * s2); t = beta / se; df = max(n - p - len(best.x), 1)
    rows = [[nm, b, s, tt, df, 2 * stats.t.sf(abs(tt), df), b - stats.t.ppf(0.975, df) * s, b + stats.t.ppf(0.975, df) * s]
            for nm, b, s, tt in zip(fixed_names, beta, se, t)]
    btil = np.linalg.solve(cf.T, np.linalg.solve(cf, Zt.T @ r))
    ll = -0.5 * (best.fun + dof * (1 + np.log(2 * np.pi))); k = p + len(best.x) + 1
    fitted = np.full(len(m), np.nan); fitted[np.nonzero(m)[0]] = X @ beta + Zt @ btil
    return {"fixed": rows, "variance": _vc_rows(blocks, lams, s2) + [["Residual", s2, np.sqrt(s2)]], "blups": _blups(blocks, lams, btil),
            "beta": beta, "s2": s2, "G": [Lc @ Lc.T * s2 for Lc in lams], "fitted": fitted, "mask": m, "theta": best.x,
            "stats": {"Method": "REML" if reml else "ML", "Observations": n, **{f"Levels of {b['name']}": len(b["levels"]) for b in blocks},
                      ("REML log-likelihood" if reml else "Log-likelihood"): ll, "AIC": 2 * k - 2 * ll, "BIC": k * np.log(dof) - 2 * ll,
                      "Converged": bool(best.success)}}


# ================================================================ GLMM, Laplace
def _setup(y, X, terms, weights, offset, family):
    terms = _flatten(terms); y = np.asarray(y, float); X = np.asarray(X, float); n0 = len(y)
    w = np.ones(n0) if weights is None else np.asarray(weights, float); off = np.zeros(n0) if offset is None else np.asarray(offset, float)
    m = np.isfinite(y) & np.all(np.isfinite(X), 1) & np.isfinite(w) & np.isfinite(off) & (w > 0)
    for t in terms:
        m &= t["labels"] != "nan"
        for _, x in t["effects"]: m &= np.isfinite(x)
    if family == "Binomial" and (np.any(y[m] < 0) or np.any(y[m] > 1)): raise ValueError("Binomial response must be 0/1 or a proportion.")
    if family == "Poisson" and np.any(y[m] < 0): raise ValueError("Counts cannot be negative.")
    return terms, y[m], X[m], w[m], off[m], m, _build(terms, m)


def _mu(fam, link, eta):
    mu = LINKS[link][1](eta); return np.clip(mu, 1e-10, 1 - 1e-10) if fam == "Binomial" else np.maximum(mu, 1e-10)


def _pirls(y, X, Zt, fam, link, w, off, start=None, iters=80):
    """Mode of (beta, spherical b) for given Zt; penalty b'b. Returns beta, b, mu, H (joint information), W."""
    var, unit_dev = FAMILIES[fam][0], FAMILIES[fam][1]; g, ginv, gp = LINKS[link]; p = X.shape[1]; q = Zt.shape[1]
    A = np.hstack([X, Zt]); pen = np.r_[np.zeros(p), np.ones(q)]
    if start is not None and len(start) == p + q: th = start.copy()
    else:
        th = np.zeros(p + q); mu0 = (y * w + 0.5) / (w + 1) if fam == "Binomial" else np.maximum(y, 0.5)
        th[:p] = np.linalg.lstsq(X, g(mu0) - off, rcond=None)[0]
    old = np.inf
    for _ in range(iters):
        mu = _mu(fam, link, A @ th + off); eta = A @ th + off; W = w / (var(mu) * gp(mu) ** 2); z = eta - off + (y - mu) * gp(mu)
        H = A.T @ (A * W[:, None]) + np.diag(pen); new = np.linalg.solve(H, A.T @ (W * z)); step = 1.0
        for _ in range(30):
            cand = th + step * (new - th); mc = _mu(fam, link, A @ cand + off); obj = np.sum(w * unit_dev(y, mc)) + np.sum(cand[p:] ** 2)
            if np.isfinite(obj) and obj <= old + 1e-10: break
            step /= 2
        th = cand
        if abs(old - obj) < 1e-11 * (abs(obj) + 1): break
        old = obj
    mu = _mu(fam, link, A @ th + off); W = w / (var(mu) * gp(mu) ** 2); H = A.T @ (A * W[:, None]) + np.diag(pen)
    return th, mu, H, W


def glmm_general(y, X, fixed_names, terms, family="Binomial", link=None, weights=None, offset=None):
    if family not in ("Binomial", "Poisson"): raise ValueError("GLMM supports the Binomial and Poisson families.")
    link = link or FAMILIES[family][2]; terms, y, X, w, off, m, blocks = _setup(y, X, terms, weights, offset, family); p = X.shape[1]
    memo = {"th": None}

    def laplace(theta):
        lams = _lambdas(theta, blocks); Zt = _zt(blocks, lams); th, mu, H, W = _pirls(y, X, Zt, family, link, w, off, memo["th"]); memo["th"] = th
        cf = np.linalg.cholesky(np.eye(Zt.shape[1]) + Zt.T @ (Zt * W[:, None]))
        return _cond_loglik(family, y, mu, w) - 0.5 * np.sum(th[p:] ** 2) - np.sum(np.log(np.diag(cf))), (lams, th, mu, H)

    best = None
    for s0 in _starts(blocks):
        memo["th"] = None
        r = optimize.minimize(lambda t: -laplace(t)[0], s0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-9, "maxiter": 8000})
        if best is None or r.fun < best.fun: best = r
    memo["th"] = None; ll, (lams, th, mu, H) = laplace(best.x); beta = th[:p]
    se = np.sqrt(np.diag(np.linalg.inv(H))[:p]); z = beta / se; expo = link in ("log", "logit")
    rows = [[nm, b, s, zz, 2 * stats.norm.sf(abs(zz)), b - 1.96 * s, b + 1.96 * s] + ([np.exp(b), np.exp(b - 1.96 * s), np.exp(b + 1.96 * s)] if expo else [])
            for nm, b, s, zz in zip(fixed_names, beta, se, z)]
    k = p + len(best.x); fitted = np.full(len(m), np.nan); fitted[np.nonzero(m)[0]] = mu
    return {"family": family, "link": link, "fixed": rows, "exp_label": ("Odds ratio" if link == "logit" else "Rate ratio exp(b)") if expo else None,
            "variance": _vc_rows(blocks, lams), "blups": _blups(blocks, lams, th[p:]), "beta": beta, "G": [Lc @ Lc.T for Lc in lams],
            "theta": best.x, "fitted": fitted, "mask": m,
            "stats": {"Method": "Laplace approximation", "Observations": int(m.sum()), **{f"Levels of {b['name']}": len(b["levels"]) for b in blocks},
                      "Log-likelihood": ll, "AIC": 2 * k - 2 * ll, "BIC": k * np.log(m.sum()) - 2 * ll, "Converged": bool(best.success)}}


# ================================================================ adaptive Gauss-Hermite quadrature (one random intercept)
CANONICAL = {"Binomial": "logit", "Poisson": "log"}


def _agq_loglik(params, y, X, grp_idx, ngrp, w, off, family, nodes, weights_gh, return_modes=False):
    """Marginal log-likelihood with nAGQ-point adaptive quadrature. params = (beta..., log sigma)."""
    beta, sigma = params[:-1], np.exp(params[-1]); eta0 = X @ beta + off; u = np.zeros(ngrp)
    sw = lambda v: np.bincount(grp_idx, v, minlength=ngrp)
    for _ in range(50):  # Newton for each group's mode, all groups at once
        mu = _mu(family, CANONICAL[family], eta0 + u[grp_idx])
        g1 = sw(w * (y - mu)) - u / sigma ** 2; g2 = -sw(w * (mu * (1 - mu) if family == "Binomial" else mu)) - 1 / sigma ** 2
        step = g1 / g2; u -= step
        if np.max(np.abs(step)) < 1e-12: break
    mu = _mu(family, CANONICAL[family], eta0 + u[grp_idx]); h = sw(w * (mu * (1 - mu) if family == "Binomial" else mu)) + 1 / sigma ** 2
    s = 1 / np.sqrt(h); const = _cond_loglik_terms(family, y, w)

    def f(uv):  # log of integrand for each group, at a random-effect value per group
        e = eta0 + uv[grp_idx]
        lp = (sw(w * y * e - w * np.log1p(np.exp(e))) if family == "Binomial" else sw(y * e - np.exp(e)))
        return lp - uv ** 2 / (2 * sigma ** 2) - 0.5 * np.log(2 * np.pi * sigma ** 2)

    vals = np.array([f(u + np.sqrt(2) * s * z) + z ** 2 for z in nodes])  # nAGQ x groups
    logint = special.logsumexp(vals, axis=0, b=weights_gh[:, None]) + np.log(np.sqrt(2) * s)
    ll = float(np.sum(logint) + const)
    return (ll, u, s) if return_modes else ll


def _cond_loglik_terms(family, y, w):
    """Parts of the log-likelihood that do not depend on the parameters (binomial coefficients, log y!)."""
    if family == "Binomial":
        k = np.round(y * w); return float(np.sum(special.gammaln(w + 1) - special.gammaln(k + 1) - special.gammaln(w - k + 1)))
    return float(-np.sum(special.gammaln(y + 1)))


def glmm_agq(y, X, fixed_names, labels, group_name, family="Binomial", nagq=11, weights=None, offset=None):
    """GLMM with one random intercept by adaptive Gauss-Hermite quadrature (canonical link). nagq = 1 gives Laplace."""
    if family not in CANONICAL: raise ValueError("Adaptive quadrature is available for the Binomial (logit) and Poisson (log) families.")
    t = term(labels, group_name, [("Intercept", np.ones(len(np.asarray(y))))])
    terms, y, X, w, off, m, blocks = _setup(y, X, [t], weights, offset, family)
    if family == "Binomial": y = np.round(y * w) / w  # keep proportions consistent with trials
    lab = t["labels"][m]; L = blocks[0]["levels"]; pos = {l: j for j, l in enumerate(L)}; gi = np.array([pos[v] for v in lab]); ng = len(L)
    nodes, wts = np.polynomial.hermite.hermgauss(int(nagq)); p = X.shape[1]
    lap = glmm_general(y, X, fixed_names, [term(lab, group_name, [("Intercept", np.ones(len(y)))])],
                       family, CANONICAL[family], w, off)  # starting values (and a comparison) from Laplace
    sd0 = max(np.sqrt(lap["G"][0][0, 0]), 0.05)
    start = np.r_[lap["beta"], np.log(sd0)]
    obj = lambda prm: -_agq_loglik(prm, y, X, gi, ng, w, off, family, nodes, wts)
    start[-1] = np.clip(start[-1], -7.0, 5.0); bounds = [(None, None)] * (len(start) - 1) + [(-7.0, 5.0)]  # log-SD kept finite
    r = optimize.minimize(obj, start, method="L-BFGS-B", bounds=bounds, options={"maxiter": 1000, "ftol": 1e-13, "gtol": 1e-7})
    if not r.success:
        r2 = optimize.minimize(obj, r.x, method="Nelder-Mead", bounds=bounds, options={"xatol": 1e-8, "fatol": 1e-10, "maxfev": 4000})
        if r2.fun <= r.fun: r = r2
    prm = r.x; ll, u, s = _agq_loglik(prm, y, X, gi, ng, w, off, family, nodes, wts, return_modes=True)
    Hn = _num_hessian(lambda v: -_agq_loglik(v, y, X, gi, ng, w, off, family, nodes, wts), prm)
    cov = np.linalg.pinv(Hn); se = np.sqrt(np.abs(np.diag(cov))); beta = prm[:p]; z = beta / se[:p]
    rows = [[nm, b, sv, zz, 2 * stats.norm.sf(abs(zz)), b - 1.96 * sv, b + 1.96 * sv, np.exp(b), np.exp(b - 1.96 * sv), np.exp(b + 1.96 * sv)]
            for nm, b, sv, zz in zip(fixed_names, beta, se[:p], z)]
    sd = np.exp(prm[-1]); sd_ci = np.exp(prm[-1] + np.array([-1.96, 1.96]) * se[-1]); k = p + 1
    fitted = np.full(len(m), np.nan); fitted[np.nonzero(m)[0]] = _mu(family, CANONICAL[family], X @ beta + off + u[gi])
    return {"family": family, "link": CANONICAL[family], "fixed": rows, "exp_label": "Odds ratio" if family == "Binomial" else "Rate ratio exp(b)",
            "variance": [[f"{group_name}: Intercept", sd ** 2, sd], [f"{group_name}: Intercept SD 95% interval", f"{sd_ci[0]:.4g} to {sd_ci[1]:.4g}", ""]],
            "blups": [(group_name, [[l, u[j]] for j, l in enumerate(L)], ["Intercept"])], "beta": beta, "sd": sd, "fitted": fitted, "mask": m,
            "laplace": lap,
            "stats": {"Method": f"Adaptive Gauss-Hermite quadrature, {int(nagq)} points", "Observations": int(m.sum()), f"Levels of {group_name}": ng,
                      "Log-likelihood": ll, "AIC": 2 * k - 2 * ll, "BIC": k * np.log(m.sum()) - 2 * ll,
                      "Laplace log-likelihood (for comparison)": lap["stats"]["Log-likelihood"], "Converged": bool(r.success)}}


def _num_hessian(f, x, h=1e-4):
    k = len(x); H = np.zeros((k, k)); f0 = f(x)
    for i in range(k):
        for j in range(i, k):
            ei, ej = np.eye(k)[i] * h, np.eye(k)[j] * h
            H[i, j] = H[j, i] = (f(x + ei + ej) - f(x + ei - ej) - f(x - ei + ej) + f(x - ei - ej)) / (4 * h * h) if i != j else (f(x + ei) - 2 * f0 + f(x - ei)) / (h * h)
    return H
