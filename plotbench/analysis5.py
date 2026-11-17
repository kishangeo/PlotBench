"""PlotBench analysis, part 5: generalised linear models and linear mixed-effects models. No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
import pandas as pd
from scipy import stats, optimize, special


# ================================================================ design matrices (text columns become dummy variables)
def design(df, cols, intercept=True):
    """Numeric columns as they are; text columns as 0/1 dummies (first level is the reference)."""
    parts, names = [], []
    for c in cols:
        s = df[c]; num = pd.to_numeric(s, errors="coerce")
        if num.notna().sum() >= 0.9 * s.notna().sum() and s.notna().any():
            parts.append(num.to_numpy(float)[:, None]); names.append(str(c))
        else:
            lv = sorted(s.dropna().astype(str).unique())
            for l in lv[1:]:
                col = np.where(s.isna(), np.nan, (s.astype(str) == l).astype(float)); parts.append(col[:, None]); names.append(f"{c}[{l}]")
    X = np.hstack(parts) if parts else np.empty((len(df), 0))
    if intercept: X = np.column_stack([np.ones(len(df)), X]); names = ["Intercept"] + names
    return X, names


# ================================================================ generalised linear models
LINKS = {
    "identity": (lambda m: m, lambda e: e, lambda m: np.ones_like(m)),
    "log": (np.log, np.exp, lambda m: 1 / m),
    "logit": (special.logit, special.expit, lambda m: 1 / (m * (1 - m))),
    "probit": (stats.norm.ppf, stats.norm.cdf, lambda m: 1 / stats.norm.pdf(stats.norm.ppf(m))),
    "cloglog": (lambda m: np.log(-np.log1p(-m)), lambda e: -np.expm1(-np.exp(e)), lambda m: 1 / ((m - 1) * np.log1p(-m))),
    "inverse": (lambda m: 1 / m, lambda e: 1 / e, lambda m: -1 / m ** 2),
    "sqrt": (np.sqrt, lambda e: e ** 2, lambda m: 0.5 / np.sqrt(m)),
}

FAMILIES = {  # variance function, unit deviance, default link, allowed links, dispersion fixed at 1?
    "Gaussian": (lambda m: np.ones_like(m), lambda y, m: (y - m) ** 2, "identity", ["identity", "log", "inverse"], False),
    "Binomial": (lambda m: m * (1 - m), lambda y, m: 2 * (special.xlogy(y, y / m) + special.xlogy(1 - y, (1 - y) / (1 - m))), "logit",
                 ["logit", "probit", "cloglog", "log"], True),
    "Poisson": (lambda m: m, lambda y, m: 2 * (special.xlogy(y, y / m) - (y - m)), "log", ["log", "identity", "sqrt"], True),
    "Quasi-Poisson": (lambda m: m, lambda y, m: 2 * (special.xlogy(y, y / m) - (y - m)), "log", ["log", "identity", "sqrt"], False),
    "Gamma": (lambda m: m ** 2, lambda y, m: 2 * (-np.log(y / m) + (y - m) / m), "inverse", ["inverse", "log", "identity"], False),
    "Inverse Gaussian": (lambda m: m ** 3, lambda y, m: (y - m) ** 2 / (y * m ** 2), "log", ["log", "inverse", "identity"], False),
}


def _clip_mu(fam, m):
    if fam == "Binomial": return np.clip(m, 1e-10, 1 - 1e-10)
    if fam in ("Poisson", "Quasi-Poisson", "Gamma", "Inverse Gaussian"): return np.maximum(m, 1e-10)
    return m


def glm(y, X, names, family="Gaussian", link=None, weights=None, offset=None, max_iter=100, _null=True):
    """IRLS fit. Binomial y may be 0/1 or proportions with 'weights' = number of trials.
    Returns coefficient table, deviance, AIC, dispersion, likelihood-ratio test, fitted means and Pearson residuals."""
    var, unit_dev, dlink, allowed, fixed_phi = FAMILIES[family]; link = link or dlink
    if link not in allowed: raise ValueError(f"Link '{link}' is not available for the {family} family.")
    g, ginv, gprime = LINKS[link]
    y = np.asarray(y, float); X = np.asarray(X, float); n0 = len(y)
    w = np.ones(n0) if weights is None else np.asarray(weights, float); off = np.zeros(n0) if offset is None else np.asarray(offset, float)
    m = np.isfinite(y) & np.all(np.isfinite(X), 1) & np.isfinite(w) & np.isfinite(off) & (w > 0); y, X, w, off = y[m], X[m], w[m], off[m]
    if family == "Binomial" and (np.any(y < 0) or np.any(y > 1)): raise ValueError("Binomial response must be 0/1 or a proportion between 0 and 1.")
    if family in ("Poisson", "Quasi-Poisson") and np.any(y < 0): raise ValueError("Counts cannot be negative.")
    if family in ("Gamma", "Inverse Gaussian") and np.any(y <= 0): raise ValueError(f"The {family} family needs a positive response.")
    n, p = X.shape
    mu = _clip_mu(family, (y * w + 0.5) / (w + 1) if family == "Binomial" else np.maximum(y, 0.1) if family != "Gaussian" else y.copy())
    eta = g(mu); dev_old = np.inf
    for it in range(max_iter):
        z = eta - off + (y - mu) * gprime(mu); W = w / (var(mu) * gprime(mu) ** 2)
        WX = X * W[:, None]; beta = np.linalg.solve(X.T @ WX, WX.T @ z)
        eta_new = X @ beta + off; step = 1.0
        for _ in range(30):  # step halving keeps the mean inside the valid range
            mu_new = ginv(eta_new) if step == 1 else ginv(eta + step * (eta_new - eta))
            if np.all(np.isfinite(mu_new)) and (family == "Gaussian" or np.all(mu_new > 0)) and (family != "Binomial" or np.all(mu_new < 1)): break
            step /= 2
        eta = eta + step * (eta_new - eta); mu = _clip_mu(family, ginv(eta)); dev = float(np.sum(w * unit_dev(y, mu)))
        if abs(dev - dev_old) < 1e-10 * (abs(dev) + 0.1): break
        dev_old = dev
    W = w / (var(mu) * gprime(mu) ** 2); cov_u = np.linalg.inv(X.T @ (X * W[:, None]))
    pearson = (y - mu) * np.sqrt(w / var(mu)); dfr = n - p
    phi = 1.0 if fixed_phi else float(np.sum(pearson ** 2) / dfr)
    se = np.sqrt(np.diag(cov_u) * phi); zt = beta / se
    pv = 2 * (stats.norm.sf(np.abs(zt)) if fixed_phi else stats.t.sf(np.abs(zt), dfr)); crit = stats.norm.ppf(0.975) if fixed_phi else stats.t.ppf(0.975, dfr)
    # null model (intercept + offset only)
    if "Intercept" in names and _null:
        mu0 = _clip_mu(family, np.full(n, np.average(y, weights=w))) if offset is None else None
        if mu0 is None:
            r0 = glm(y, np.ones((n, 1)), ["Intercept"], family, link, w, off, _null=False); mu0 = r0["fitted_valid"]
        null_dev = float(np.sum(w * unit_dev(y, mu0))); df_null = n - 1
    else: null_dev, df_null = np.nan, n
    ll = _loglik(family, y, mu, w, phi, dev, n)
    k = p + (0 if fixed_phi else 1); lr = (null_dev - dev) / (phi if not fixed_phi else 1)
    expo = link in ("log", "logit")
    rows = [[nm, b, s, t, pp, b - crit * s, b + crit * s] + ([np.exp(b), np.exp(b - crit * s), np.exp(b + crit * s)] if expo else [])
            for nm, b, s, t, pp in zip(names, beta, se, zt, pv)]
    fitted = np.full(n0, np.nan); fitted[np.nonzero(m)[0]] = mu; resid = np.full(n0, np.nan); resid[np.nonzero(m)[0]] = pearson
    return {"family": family, "link": link, "coef": rows, "exp_label": ("Odds ratio" if link == "logit" else "Rate/ratio exp(b)") if expo else None,
            "stat_name": "z" if fixed_phi else "t", "fitted": fitted, "fitted_valid": mu, "pearson": resid, "mask": m, "beta": beta,
            "stats": {"N": n, "Iterations": it + 1, "Deviance": dev, "Residual df": dfr, "Null deviance": null_dev, "Null df": df_null,
                      "Dispersion": phi, "Pearson chi-square": float(np.sum(pearson ** 2)), "Log-likelihood": ll,
                      "AIC": 2 * k - 2 * ll if np.isfinite(ll) else np.nan,
                      "LR chi-square (vs null)" if fixed_phi else "F (vs null)": lr if fixed_phi else lr / max(p - 1, 1),
                      "p (vs null)": stats.chi2.sf(lr, p - 1) if fixed_phi else stats.f.sf(lr / max(p - 1, 1), max(p - 1, 1), dfr),
                      "Deviance explained": 1 - dev / null_dev if null_dev else np.nan}}


def _loglik(family, y, mu, w, phi, dev, n):
    if family == "Gaussian": return -0.5 * (n * np.log(2 * np.pi * dev / n) + n)
    if family == "Binomial":
        k = np.round(y * w); return float(np.sum(special.gammaln(w + 1) - special.gammaln(k + 1) - special.gammaln(w - k + 1) + special.xlogy(k, mu) + special.xlogy(w - k, 1 - mu)))
    if family == "Poisson": return float(np.sum(special.xlogy(y, mu) - mu - special.gammaln(y + 1)))
    if family == "Gamma":
        nu = 1 / phi; return float(np.sum(stats.gamma.logpdf(y, nu, scale=mu / nu)))
    if family == "Inverse Gaussian": return float(np.sum(stats.invgauss.logpdf(y, mu * phi, scale=1 / phi)))
    return np.nan  # quasi families have no likelihood


def _natural(v):
    """Sort group labels as numbers when they are numbers (2 before 10)."""
    try: return (0, float(v), "")
    except ValueError: return (1, 0.0, v)


# ================================================================ linear mixed-effects model (REML or ML)
def lmm(y, X, fixed_names, groups, Z=None, random_names=("Intercept",), method="REML"):
    """y = X b + Z u + e, with u ~ N(0, G) independently for each group and e ~ N(0, s2 I).
    Z: n x q random-effects design (default: random intercept). G is unstructured (q x q).
    Returns fixed effects, variance components, ICC, group predictions (BLUPs), log-likelihood, AIC, BIC."""
    y = np.asarray(y, float); X = np.asarray(X, float); g = np.asarray(groups).astype(str)
    Z = np.ones((len(y), 1)) if Z is None else np.asarray(Z, float)
    m = np.isfinite(y) & np.all(np.isfinite(X), 1) & np.all(np.isfinite(Z), 1) & (g != "nan"); y, X, Z, g = y[m], X[m], Z[m], g[m]
    L = sorted(set(g), key=_natural); idx = [np.nonzero(g == l)[0] for l in L]; n, p = X.shape; q = Z.shape[1]
    if len(L) < 2: raise ValueError("Need at least two groups.")
    reml = method.upper() == "REML"; tri = np.tril_indices(q)

    def unpack(th):
        Lc = np.zeros((q, q)); Lc[tri] = th; return Lc @ Lc.T  # G relative to s2

    def parts(th):
        Gr = unpack(th); XtVX = np.zeros((p, p)); XtVy = np.zeros(p); logdet = 0.0; Vis = []
        for ii in idx:
            Zi = Z[ii]; Vi = Zi @ Gr @ Zi.T + np.eye(len(ii)); c, lw = np.linalg.slogdet(Vi); Vinv = np.linalg.inv(Vi)
            logdet += lw; Vis.append(Vinv); XtVX += X[ii].T @ Vinv @ X[ii]; XtVy += X[ii].T @ Vinv @ y[ii]
        beta = np.linalg.solve(XtVX, XtVy); rss = sum(float((y[ii] - X[ii] @ beta) @ Vi @ (y[ii] - X[ii] @ beta)) for ii, Vi in zip(idx, Vis))
        return Gr, beta, rss, logdet, XtVX, Vis

    def objective(th):
        try: Gr, beta, rss, logdet, XtVX, _ = parts(th)
        except np.linalg.LinAlgError: return 1e300
        dof = n - p if reml else n; s2 = rss / dof
        val = logdet + dof * np.log(s2) + (np.linalg.slogdet(XtVX)[1] if reml else 0.0)
        return val if np.isfinite(val) else 1e300

    th0 = np.eye(q)[tri] * 0.7; best = None
    for start in (th0, th0 * 0.2, th0 * 2.0):  # a few starts guard against a local optimum at the boundary
        r = optimize.minimize(objective, start, method="Nelder-Mead", options={"xatol": 1e-9, "fatol": 1e-11, "maxiter": 20000, "maxfev": 40000})
        if best is None or r.fun < best.fun: best = r
    Gr, beta, rss, logdet, XtVX, Vis = parts(best.x); dof = n - p if reml else n; s2 = rss / dof; G = Gr * s2
    cov_b = np.linalg.inv(XtVX) * s2; se = np.sqrt(np.diag(cov_b)); t = beta / se
    df = max(len(L) - np.linalg.matrix_rank(X[[ii[0] for ii in idx]]), 1)  # conservative 'between-groups' df for fixed effects
    df_within = n - len(L) - (p - 1)
    rows = []
    for j, nm in enumerate(fixed_names):  # predictors that vary within groups get within-group df
        within = any(np.ptp(X[ii, j]) > 0 for ii in idx); d = max(df_within, 1) if within else df
        rows.append([nm, beta[j], se[j], t[j], d, 2 * stats.t.sf(abs(t[j]), d), beta[j] - stats.t.ppf(0.975, d) * se[j], beta[j] + stats.t.ppf(0.975, d) * se[j]])
    blup = [[l] + list(G @ Z[ii].T @ Vi @ (y[ii] - X[ii] @ beta) / s2) for l, ii, Vi in zip(L, idx, Vis)]
    ll = -0.5 * (objective(best.x) + dof * (1 + np.log(2 * np.pi)))
    k = p + q * (q + 1) // 2 + 1; nobs = n - p if reml else n
    vc = [[f"Group: {random_names[i]}", G[i, i], np.sqrt(max(G[i, i], 0))] for i in range(q)]
    if q == 2: vc.append([f"Correlation {random_names[0]}, {random_names[1]}", G[0, 1] / np.sqrt(max(G[0, 0] * G[1, 1], 1e-300)), ""])
    vc.append(["Residual", s2, np.sqrt(s2)])
    fitted = np.full(len(m), np.nan); u = {r[0]: np.array(r[1:]) for r in blup}; fv = X @ beta + np.array([Z[i] @ u[g[i]] for i in range(n)])
    fitted[np.nonzero(m)[0]] = fv
    return {"fixed": rows, "variance": vc, "blup": blup, "groups": L, "G": G, "s2": s2, "beta": beta, "fitted": fitted, "mask": m,
            "stats": {"Method": "REML" if reml else "ML", "Observations": n, "Groups": len(L),
                      "Log-likelihood" if not reml else "REML log-likelihood": ll, "AIC": 2 * k - 2 * ll, "BIC": k * np.log(nobs) - 2 * ll,
                      "ICC (random intercept)": G[0, 0] / (G[0, 0] + s2), "Converged": bool(best.success)}}


def lmm_lrt(full, reduced):
    """Likelihood-ratio test between two nested ML fits (fixed effects) or REML fits with the same fixed effects."""
    key = "Log-likelihood" if "Log-likelihood" in full["stats"] else "REML log-likelihood"
    d = 2 * (full["stats"][key] - reduced["stats"][key]); k = len(full["beta"]) - len(reduced["beta"]) + \
        (full["G"].size - reduced["G"].size) // 2 + (1 if full["G"].shape != reduced["G"].shape else 0)
    k = max(k, 1); return {"LR chi-square": d, "df": k, "p": stats.chi2.sf(max(d, 0), k)}
