"""PlotBench analysis, part 6: mixed models with several (crossed or nested) random-effect terms, and
generalised linear mixed models (binomial and Poisson, Laplace approximation). No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Random-effect terms are independent variance components: random intercepts for any number of grouping factors
(crossed, e.g. subject and item; or nested, e.g. site and site:sample) and uncorrelated random slopes.
"""
import numpy as np
import pandas as pd
from scipy import stats, optimize, special

from .analysis5 import FAMILIES, LINKS, _natural


def intercept_term(labels, name):
    """Indicator matrix (n x levels) for a random intercept of a grouping factor."""
    g = np.asarray(labels).astype(str); L = sorted(set(g) - {"nan"}, key=_natural)
    Z = np.zeros((len(g), len(L))); pos = {l: j for j, l in enumerate(L)}
    for i, v in enumerate(g):
        if v in pos: Z[i, pos[v]] = 1.0
    return {"name": name, "Z": Z, "levels": L, "kind": "intercept"}


def slope_term(labels, x, name):
    t = intercept_term(labels, name); t["Z"] = t["Z"] * np.asarray(x, float)[:, None]; t["kind"] = "slope"; return t


def nested_labels(outer, inner):
    return np.array([f"{a}:{b}" for a, b in zip(np.asarray(outer).astype(str), np.asarray(inner).astype(str))])


def _woodbury(Z, d):
    """For V* = I + Z diag(d) Z': returns (apply V*^-1 to a matrix, log|V*|). d > 0."""
    M = np.diag(1 / d) + Z.T @ Z; cf = np.linalg.cholesky(M)
    logdet = np.sum(np.log(d)) + 2 * np.sum(np.log(np.diag(cf)))

    def solve(R):
        tmp = np.linalg.solve(cf.T, np.linalg.solve(cf, Z.T @ R)); return R - Z @ tmp
    return solve, logdet, cf


def lmm_terms(y, X, fixed_names, terms, method="REML"):
    """Gaussian mixed model with independent variance components (one per term). Exact (Woodbury), any crossing."""
    y = np.asarray(y, float); X = np.asarray(X, float); m = np.isfinite(y) & np.all(np.isfinite(X), 1)
    for t in terms: m &= np.all(np.isfinite(t["Z"]), 1) & (t["Z"] != 0).any(1) | (t["kind"] == "slope")
    y, X = y[m], X[m]; Zs = [t["Z"][m] for t in terms]; keep = [z.any(0) for z in Zs]; Zs = [z[:, k] for z, k in zip(Zs, keep)]
    levels = [list(np.array(t["levels"])[k]) for t, k in zip(terms, keep)]
    Z = np.hstack(Zs); sizes = [z.shape[1] for z in Zs]; n, p = X.shape; reml = method.upper() == "REML"; dof = n - p if reml else n

    def parts(lt):
        d = np.repeat(np.exp(2 * np.asarray(lt)), sizes) + 1e-12; solve, logdet, cf = _woodbury(Z, d)
        VX, Vy = solve(X), solve(y[:, None])[:, 0]; XtVX = X.T @ VX; beta = np.linalg.solve(XtVX, X.T @ Vy); r = y - X @ beta
        return d, beta, float(r @ solve(r[:, None])[:, 0]), logdet, XtVX, solve, r

    def objective(lt):
        try: d, beta, rss, logdet, XtVX, _, _ = parts(lt)
        except np.linalg.LinAlgError: return 1e300
        return logdet + dof * np.log(rss / dof) + (np.linalg.slogdet(XtVX)[1] if reml else 0.0)

    best = None
    for s0 in (0.0, -1.5, 1.0):
        r = optimize.minimize(objective, np.full(len(terms), s0), method="Nelder-Mead",
                              options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 20000, "maxfev": 40000})
        if best is None or r.fun < best.fun: best = r
    d, beta, rss, logdet, XtVX, solve, r = parts(best.x); s2 = rss / dof; var = np.exp(2 * best.x) * s2
    se = np.sqrt(np.diag(np.linalg.inv(XtVX)) * s2); t = beta / se; df = max(n - p - len(terms), 1)
    rows = [[nm, b, s, tt, df, 2 * stats.t.sf(abs(tt), df), b - stats.t.ppf(0.975, df) * s, b + stats.t.ppf(0.975, df) * s]
            for nm, b, s, tt in zip(fixed_names, beta, se, t)]
    u = (d * (Z.T @ solve(r[:, None])[:, 0]))  # BLUPs (relative scale cancels: u = D Z' V*^-1 r)
    blups, off = [], 0
    for term, lv, sz in zip(terms, levels, sizes): blups.append((term["name"], [[l, u[off + j]] for j, l in enumerate(lv)])); off += sz
    ll = -0.5 * (best.fun + dof * (1 + np.log(2 * np.pi))); k = p + len(terms) + 1
    fitted = np.full(len(m), np.nan); fitted[np.nonzero(m)[0]] = X @ beta + Z @ u
    tot = var.sum() + s2
    return {"fixed": rows, "variance": [[tm["name"], v, np.sqrt(v), v / tot] for tm, v in zip(terms, var)] + [["Residual", s2, np.sqrt(s2), s2 / tot]],
            "blups": blups, "beta": beta, "var": var, "s2": s2, "fitted": fitted, "mask": m,
            "stats": {"Method": "REML" if reml else "ML", "Observations": n, **{f"Levels of {tm['name']}": sz for tm, sz in zip(terms, sizes)},
                      ("REML log-likelihood" if reml else "Log-likelihood"): ll, "AIC": 2 * k - 2 * ll, "BIC": k * np.log(n - p if reml else n) - 2 * ll,
                      "Converged": bool(best.success)}}


# ================================================================ GLMM by the Laplace approximation
def _pirls(y, X, Z, d, fam, link, w, off, beta0=None, iters=60):
    """Penalised IRLS: mode of (beta, u) for fixed variance components d. Returns beta, u, eta, mu, H, loglik parts."""
    var, unit_dev = FAMILIES[fam][0], FAMILIES[fam][1]; g, ginv, gprime = LINKS[link]; n, p = X.shape; q = Z.shape[1]
    A = np.hstack([X, Z]); pen = np.r_[np.zeros(p), 1 / d]; theta = np.zeros(p + q)
    if beta0 is not None: theta[:p] = beta0
    else:
        mu0 = (y * w + 0.5) / (w + 1) if fam == "Binomial" else np.maximum(y, 0.5); theta[:p] = np.linalg.lstsq(X, g(mu0) - off, rcond=None)[0]
    obj_old = np.inf
    for _ in range(iters):
        eta = A @ theta + off; mu = ginv(eta); mu = np.clip(mu, 1e-10, 1 - 1e-10) if fam == "Binomial" else np.maximum(mu, 1e-10)
        W = w / (var(mu) * gprime(mu) ** 2); z = eta - off + (y - mu) * gprime(mu)
        H = A.T @ (A * W[:, None]) + np.diag(pen); new = np.linalg.solve(H, A.T @ (W * z))
        step = 1.0
        for _ in range(25):  # step halving on the penalised deviance
            th = theta + step * (new - theta); e2 = A @ th + off; m2 = ginv(e2)
            m2 = np.clip(m2, 1e-10, 1 - 1e-10) if fam == "Binomial" else np.maximum(m2, 1e-10)
            obj = np.sum(w * unit_dev(y, m2)) + np.sum(th[p:] ** 2 / d)
            if np.isfinite(obj) and obj <= obj_old + 1e-9: break
            step /= 2
        theta = th
        if abs(obj_old - obj) < 1e-10 * (abs(obj) + 1): break
        obj_old = obj
    eta = A @ theta + off; mu = ginv(eta); mu = np.clip(mu, 1e-10, 1 - 1e-10) if fam == "Binomial" else np.maximum(mu, 1e-10)
    W = w / (var(mu) * gprime(mu) ** 2); H = A.T @ (A * W[:, None]) + np.diag(pen)
    return theta[:p], theta[p:], eta, mu, H, W


def _cond_loglik(fam, y, mu, w):
    if fam == "Binomial":
        k = np.round(y * w); return float(np.sum(special.gammaln(w + 1) - special.gammaln(k + 1) - special.gammaln(w - k + 1)
                                                 + special.xlogy(k, mu) + special.xlogy(w - k, 1 - mu)))
    return float(np.sum(special.xlogy(y, mu) - mu - special.gammaln(y + 1)))


def glmm(y, X, fixed_names, terms, family="Binomial", link=None, weights=None, offset=None):
    """Binomial or Poisson GLMM with independent random-effect terms (crossed or nested), Laplace approximation."""
    if family not in ("Binomial", "Poisson"): raise ValueError("GLMM supports the Binomial and Poisson families.")
    link = link or FAMILIES[family][2]
    y = np.asarray(y, float); X = np.asarray(X, float); n0 = len(y)
    w = np.ones(n0) if weights is None else np.asarray(weights, float); off = np.zeros(n0) if offset is None else np.asarray(offset, float)
    m = np.isfinite(y) & np.all(np.isfinite(X), 1) & np.isfinite(w) & np.isfinite(off) & (w > 0)
    for t in terms: m &= np.all(np.isfinite(t["Z"]), 1)
    y, X, w, off = y[m], X[m], w[m], off[m]; Zs = [t["Z"][m] for t in terms]; keep = [z.any(0) for z in Zs]; Zs = [z[:, k] for z, k in zip(Zs, keep)]
    levels = [list(np.array(t["levels"])[k]) for t, k in zip(terms, keep)]; Z = np.hstack(Zs); sizes = [z.shape[1] for z in Zs]; p = X.shape[1]
    if family == "Binomial" and (np.any(y < 0) or np.any(y > 1)): raise ValueError("Binomial response must be 0/1 or a proportion.")
    if family == "Poisson" and np.any(y < 0): raise ValueError("Counts cannot be negative.")
    cache = {"beta": None}

    def laplace(ls):
        d = np.repeat(np.exp(2 * np.asarray(ls)), sizes) + 1e-10
        beta, u, eta, mu, H, W = _pirls(y, X, Z, d, family, link, w, off, cache["beta"]); cache["beta"] = beta
        L = np.linalg.cholesky(np.eye(Z.shape[1]) + (np.sqrt(d)[:, None] * (Z.T @ (Z * W[:, None]))) * np.sqrt(d)[None, :])
        return _cond_loglik(family, y, mu, w) - 0.5 * np.sum(u ** 2 / d) - np.sum(np.log(np.diag(L))), (beta, u, mu, H, d)

    best = None
    for s0 in (-0.5, -2.0, 0.5):
        cache["beta"] = None
        r = optimize.minimize(lambda ls: -laplace(ls)[0], np.full(len(terms), s0), method="Nelder-Mead",
                              options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
        if best is None or r.fun < best.fun: best = r
    ll, (beta, u, mu, H, d) = laplace(best.x); var = np.exp(2 * best.x)
    cov = np.linalg.inv(H)[:p, :p]; se = np.sqrt(np.diag(cov)); z = beta / se; expo = link in ("log", "logit")
    rows = [[nm, b, s, zz, 2 * stats.norm.sf(abs(zz)), b - 1.96 * s, b + 1.96 * s] + ([np.exp(b), np.exp(b - 1.96 * s), np.exp(b + 1.96 * s)] if expo else [])
            for nm, b, s, zz in zip(fixed_names, beta, se, z)]
    blups, o = [], 0
    for term, lv, sz in zip(terms, levels, sizes): blups.append((term["name"], [[l, u[o + j]] for j, l in enumerate(lv)])); o += sz
    k = p + len(terms); fitted = np.full(n0, np.nan); fitted[np.nonzero(m)[0]] = mu
    return {"family": family, "link": link, "fixed": rows, "exp_label": ("Odds ratio" if link == "logit" else "Rate ratio exp(b)") if expo else None,
            "variance": [[t["name"], v, np.sqrt(v)] for t, v in zip(terms, var)], "blups": blups, "beta": beta, "var": var,
            "fitted": fitted, "mask": m,
            "stats": {"Method": "Laplace approximation", "Observations": int(m.sum()), **{f"Levels of {t['name']}": sz for t, sz in zip(terms, sizes)},
                      "Log-likelihood": ll, "AIC": 2 * k - 2 * ll, "BIC": k * np.log(m.sum()) - 2 * ll, "Converged": bool(best.success)}}
