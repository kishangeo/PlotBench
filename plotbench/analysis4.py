"""PlotBench analysis, part 4: QDA, MANCOVA/ANCOVA, more tests and models, curve tools, worksheet operations. No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
import pandas as pd
from scipy import stats, interpolate, optimize

from .analysis3 import lda


# ================================================================ quadratic discriminant analysis
def _qda_scores(X, mus, covs, pri):
    out = np.empty((len(X), len(mus)))
    for k, (mu, S) in enumerate(zip(mus, covs)):
        sign, logdet = np.linalg.slogdet(S); D = X - mu
        out[:, k] = -0.5 * logdet - 0.5 * np.einsum("ij,jk,ik->i", D, np.linalg.pinv(S), D) + np.log(pri[k])
    return out


def qda(X, groups, names, reg=0.0):
    """Quadratic discriminant analysis (one covariance matrix per group). reg shrinks each covariance toward its diagonal."""
    X = np.asarray(X, float); g = np.asarray(groups).astype(str); m = np.all(np.isfinite(X), axis=1) & (g != "nan"); X, g = X[m], g[m]
    L = sorted(set(g)); p = X.shape[1]
    if min(np.sum(g == c) for c in L) <= p: raise ValueError("Each group needs more members than there are predictors for QDA.")

    def fit(Xf, gf):
        mus = [Xf[gf == c].mean(0) for c in L]; pri = np.array([np.mean(gf == c) for c in L])
        covs = [np.cov(Xf[gf == c].T).reshape(p, p) for c in L]
        covs = [(1 - reg) * S + reg * np.diag(np.diag(S)) for S in covs]
        return mus, covs, pri

    mus, covs, pri = fit(X, g); sc = _qda_scores(X, mus, covs, pri)
    post = np.exp(sc - sc.max(1, keepdims=True)); post /= post.sum(1, keepdims=True); pred = np.array(L)[np.argmax(sc, 1)]
    hits = []
    for i in range(len(X)):
        keep = np.arange(len(X)) != i
        if min(np.sum(g[keep] == c) for c in L) <= p: continue
        hits.append(L[int(np.argmax(_qda_scores(X[i:i + 1], *fit(X[keep], g[keep]))))] == g[i])
    return {"groups": L, "names": list(names), "means": [[c] + list(mu) for c, mu in zip(L, mus)],
            "logdet": [[c, np.linalg.slogdet(S)[1]] for c, S in zip(L, covs)],
            "confusion": [[t] + [int(np.sum((g == t) & (pred == c))) for c in L] for t in L], "accuracy": float(np.mean(pred == g)),
            "loo_accuracy": float(np.mean(hits)) if hits else np.nan, "pred": pred, "post": post, "mask": m,
            "box_m": box_m(X, g)}


def box_m(X, g):
    """Box's M test for equality of covariance matrices (chi-square approximation)."""
    L = sorted(set(g)); k, p = len(L), X.shape[1]; ns = np.array([np.sum(g == c) for c in L]); N = ns.sum()
    covs = [np.cov(X[g == c].T).reshape(p, p) for c in L]; Sp = sum((n - 1) * S for n, S in zip(ns, covs)) / (N - k)
    M = (N - k) * np.linalg.slogdet(Sp)[1] - sum((n - 1) * np.linalg.slogdet(S)[1] for n, S in zip(ns, covs))
    c = (np.sum(1 / (ns - 1)) - 1 / (N - k)) * (2 * p * p + 3 * p - 1) / (6 * (p + 1) * (k - 1)); df = p * (p + 1) * (k - 1) / 2
    return {"Box M": M, "Chi-square": M * (1 - c), "df": df, "p": stats.chi2.sf(M * (1 - c), df)}


# ================================================================ MANCOVA / ANCOVA
def _mv_tests(H, E, p, q, dfe):
    lam = np.clip(np.real(np.linalg.eigvals(np.linalg.solve(E, H))), 0, None)
    s, mm, nn = min(p, q), (abs(p - q) - 1) / 2, (dfe - p - 1) / 2
    wilks = float(np.prod(1 / (1 + lam))); pillai = float(np.sum(lam / (1 + lam))); hot = float(np.sum(lam)); roy = float(lam.max())
    t = np.sqrt((p ** 2 * q ** 2 - 4) / (p ** 2 + q ** 2 - 5)) if p ** 2 + q ** 2 - 5 > 0 else 1.0
    w = dfe + q - (p + q + 1) / 2; d1 = p * q; d2 = w * t - (p * q - 2) / 2; Fw = (1 - wilks ** (1 / t)) / wilks ** (1 / t) * d2 / d1
    p1, p2 = s * (2 * mm + s + 1), s * (2 * nn + s + 1); Fp = p2 / p1 * pillai / (s - pillai)
    h1, h2 = s * (2 * mm + s + 1), 2 * (s * nn + 1); Fh = h2 * hot / (s * h1)
    r = max(p, q); Fr = roy * (dfe - r + q) / r
    return [["Wilks lambda", wilks, Fw, d1, d2, stats.f.sf(Fw, d1, d2)], ["Pillai trace", pillai, Fp, p1, p2, stats.f.sf(Fp, p1, p2)],
            ["Hotelling-Lawley trace", hot, Fh, h1, h2, stats.f.sf(Fh, h1, h2)],
            ["Roy largest root (upper bound)", roy, Fr, r, dfe - r + q, stats.f.sf(Fr, r, dfe - r + q)]]


def mancova(Y, groups, C, cov_names):
    """Responses Y (n x p), one factor, covariates C (n x c). Factor and each covariate are tested adjusted for the rest
    (type III style, no factor x covariate interaction). Also returns adjusted means at the covariate means."""
    Y = np.atleast_2d(np.asarray(Y, float)); Y = Y.T if Y.shape[0] != len(groups) else Y
    C = np.atleast_2d(np.asarray(C, float)); C = C.T if C.shape[0] != len(groups) else C
    g = np.asarray(groups).astype(str); m = np.all(np.isfinite(Y), 1) & np.all(np.isfinite(C), 1) & (g != "nan"); Y, C, g = Y[m], C[m], g[m]
    L = sorted(set(g)); n, p = Y.shape; k, c = len(L), C.shape[1]
    D = np.column_stack([(g == l).astype(float) for l in L[1:]]) if k > 1 else np.empty((n, 0))

    def sse(X):
        X = np.column_stack([np.ones(n), X]); B = np.linalg.lstsq(X, Y, rcond=None)[0]; R = Y - X @ B; return R.T @ R, B

    E, Bfull = sse(np.column_stack([D, C])); dfe = n - 1 - (k - 1) - c
    rows = {"Group": _mv_tests(sse(C)[0] - E, E, p, k - 1, dfe)}
    for j, nm in enumerate(cov_names): rows[nm] = _mv_tests(sse(np.column_stack([D, np.delete(C, j, 1)]))[0] - E, E, p, 1, dfe)
    cm = C.mean(0); adj = []
    for i, l in enumerate(L):
        x = np.r_[1.0, [1.0 if l == L[j + 1] else 0.0 for j in range(k - 1)], cm]; adj.append([l, int(np.sum(g == l))] + list(x @ Bfull))
    slopes = [[nm] + list(Bfull[1 + (k - 1) + j]) for j, nm in enumerate(cov_names)]
    return {"tests": rows, "adjusted_means": adj, "slopes": slopes, "groups": L, "n": n, "dfe": dfe}


def ancova(y, groups, C, cov_names):
    """Univariate ANCOVA (one factor, covariates): exact F tests from the same model as MANCOVA with one response."""
    r = mancova(np.asarray(y, float)[:, None], groups, C, cov_names)
    table = [[name, t[0][2], t[0][3], t[0][4], t[0][5]] for name, t in r["tests"].items()]  # Wilks F is exact for p = 1
    return {**r, "table": table}


# ================================================================ more tests
def dunn(groups):
    """Dunn's post-hoc test after Kruskal-Wallis (tie-corrected), Holm-adjusted p values."""
    names = list(groups); data = [np.asarray(groups[n], float)[np.isfinite(groups[n])] for n in names]
    allv = np.concatenate(data); ranks = stats.rankdata(allv); N = len(allv); idx = np.cumsum([0] + [len(d) for d in data])
    R = [ranks[idx[i]:idx[i + 1]].mean() for i in range(len(data))]; _, tc = np.unique(allv, return_counts=True)
    tie = np.sum(tc ** 3 - tc) / (12 * (N - 1)); rows = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            se = np.sqrt((N * (N + 1) / 12 - tie) * (1 / len(data[i]) + 1 / len(data[j]))); z = (R[i] - R[j]) / se
            rows.append([f"{names[i]} - {names[j]}", R[i] - R[j], z, 2 * stats.norm.sf(abs(z))])
    order = np.argsort([r[3] for r in rows]); m = len(rows); running = 0
    for rank, o in enumerate(order):  # Holm step-down
        running = max(running, min(1, rows[o][3] * (m - rank))); rows[o] += [running, "yes" if running < 0.05 else "no"]
    return rows


def fisher_exact(table):
    t = np.asarray(table, int); odds, p = stats.fisher_exact(t); return {"Odds ratio": odds, "p (two-sided)": p}


def mcnemar(table):
    t = np.asarray(table, float); b, c = t[0, 1], t[1, 0]; chi = (abs(b - c) - 1) ** 2 / (b + c) if b + c else 0.0
    exact = stats.binomtest(int(min(b, c)), int(b + c), 0.5).pvalue if b + c else 1.0
    return {"Discordant b": b, "Discordant c": c, "Chi-square (continuity corrected)": chi, "p (chi-square)": stats.chi2.sf(chi, 1),
            "p (exact binomial)": exact}


def proportion_test(x1, n1, x2=None, n2=None, p0=0.5):
    if x2 is None:
        ph = x1 / n1; z = (ph - p0) / np.sqrt(p0 * (1 - p0) / n1); ex = stats.binomtest(int(x1), int(n1), p0).pvalue
        ci = stats.binomtest(int(x1), int(n1)).proportion_ci(); return {"Proportion": ph, "z": z, "p (normal)": 2 * stats.norm.sf(abs(z)),
                                                                        "p (exact)": ex, "95% CI low": ci.low, "95% CI high": ci.high}
    p1, p2 = x1 / n1, x2 / n2; pp = (x1 + x2) / (n1 + n2); z = (p1 - p2) / np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {"p1": p1, "p2": p2, "Difference": p1 - p2, "z": z, "p": 2 * stats.norm.sf(abs(z)), "95% CI low": p1 - p2 - 1.96 * se,
            "95% CI high": p1 - p2 + 1.96 * se}


def var_test_two(a, b):
    a, b = (np.asarray(v, float)[np.isfinite(v)] for v in (a, b)); F = a.var(ddof=1) / b.var(ddof=1); d1, d2 = len(a) - 1, len(b) - 1
    return {"Variance 1": a.var(ddof=1), "Variance 2": b.var(ddof=1), "F": F, "df1": d1, "df2": d2,
            "p (two-sided)": 2 * min(stats.f.cdf(F, d1, d2), stats.f.sf(F, d1, d2))}


def var_test_one(a, sigma2):
    a = np.asarray(a, float)[np.isfinite(a)]; df = len(a) - 1; chi = df * a.var(ddof=1) / sigma2
    return {"Variance": a.var(ddof=1), "Chi-square": chi, "df": df, "p (two-sided)": 2 * min(stats.chi2.cdf(chi, df), stats.chi2.sf(chi, df))}


def anderson_darling(a):
    a = np.asarray(a, float)[np.isfinite(a)]; r = stats.anderson(a, "norm"); n = len(a); A2 = r.statistic * (1 + 0.75 / n + 2.25 / n ** 2)
    p = (np.exp(1.2937 - 5.709 * A2 + 0.0186 * A2 ** 2) if A2 >= 0.6 else np.exp(0.9177 - 4.279 * A2 - 1.38 * A2 ** 2) if A2 >= 0.34
         else 1 - np.exp(-8.318 + 42.796 * A2 - 59.938 * A2 ** 2) if A2 >= 0.2 else 1 - np.exp(-13.436 + 101.14 * A2 - 223.73 * A2 ** 2))
    return {"A2": r.statistic, "A2 adjusted": A2, "p (D'Agostino approximation)": float(min(max(p, 0), 1))}


def partial_correlation(X, names):
    X = np.asarray(X, float); X = X[np.all(np.isfinite(X), 1)]; P = np.linalg.pinv(np.cov(X.T))
    d = np.sqrt(np.diag(P)); R = -P / np.outer(d, d); np.fill_diagonal(R, 1.0); n, k = X.shape
    t = R * np.sqrt((n - k) / np.maximum(1 - R ** 2, 1e-300)); pv = 2 * stats.t.sf(np.abs(t), n - k); np.fill_diagonal(pv, 0)
    return R, pv


def logistic_regression(y, X, names, iters=100):
    """Binary logistic regression by Newton-Raphson (IRLS). y: 0/1."""
    y = np.asarray(y, float); X = np.atleast_2d(np.asarray(X, float)); X = X.T if X.shape[0] != len(y) else X
    m = np.isfinite(y) & np.all(np.isfinite(X), 1); y, X = y[m], X[m]
    if not set(np.unique(y)) <= {0.0, 1.0}: raise ValueError("The response must be coded 0 and 1.")
    D = np.column_stack([np.ones(len(y)), X]); b = np.zeros(D.shape[1])
    for _ in range(iters):
        pr = 1 / (1 + np.exp(-np.clip(D @ b, -30, 30))); W = pr * (1 - pr) + 1e-12; H = D.T @ (D * W[:, None])
        step = np.linalg.solve(H, D.T @ (y - pr)); b += step
        if np.max(np.abs(step)) < 1e-10: break
    pr = 1 / (1 + np.exp(-np.clip(D @ b, -30, 30))); se = np.sqrt(np.diag(np.linalg.inv(D.T @ (D * (pr * (1 - pr))[:, None]))))
    ll = np.sum(y * np.log(pr + 1e-300) + (1 - y) * np.log(1 - pr + 1e-300)); p0 = y.mean()
    ll0 = len(y) * (p0 * np.log(p0) + (1 - p0) * np.log(1 - p0)); z = b / se
    rows = [[nm, bb, s, zz, 2 * stats.norm.sf(abs(zz)), np.exp(bb), np.exp(bb - 1.96 * s), np.exp(bb + 1.96 * s)]
            for nm, bb, s, zz in zip(["Intercept"] + list(names), b, se, z)]
    return {"coef": rows, "stats": {"N": len(y), "Log-likelihood": ll, "LR chi-square": 2 * (ll - ll0), "df": len(names),
                                    "p (LR test)": stats.chi2.sf(2 * (ll - ll0), len(names)), "McFadden R2": 1 - ll / ll0,
                                    "Accuracy (cut 0.5)": float(np.mean((pr >= 0.5) == (y > 0.5)))}, "prob": pr, "mask": m}


def pls(X, Y, ncomp=2):
    """PLS regression (NIPALS, standardised X and Y). Returns coefficients (original units), explained variance, VIP, fitted values."""
    X = np.asarray(X, float); Y = np.asarray(Y, float); Y = Y[:, None] if Y.ndim == 1 else Y
    m = np.all(np.isfinite(X), 1) & np.all(np.isfinite(Y), 1); X, Y = X[m], Y[m]
    xm, xs, ym, ys = X.mean(0), X.std(0, ddof=1), Y.mean(0), Y.std(0, ddof=1); xs[xs == 0] = 1; ys[ys == 0] = 1
    E, F = (X - xm) / xs, (Y - ym) / ys; T, P, Wt, Q = [], [], [], []; ssx, ssy = (E ** 2).sum(), (F ** 2).sum(); xv, yv = [], []
    for _ in range(min(ncomp, X.shape[1])):
        u = F[:, [int(np.argmax(F.var(0)))]]
        for _ in range(500):
            w = E.T @ u; w /= np.linalg.norm(w); t = E @ w; q = F.T @ t / (t.T @ t); u_new = F @ q / (q.T @ q)
            if np.linalg.norm(u_new - u) < 1e-12: break
            u = u_new
        p_ = E.T @ t / (t.T @ t); E = E - t @ p_.T; F = F - t @ q.T
        T.append(t); P.append(p_); Wt.append(w); Q.append(q); xv.append(1 - (E ** 2).sum() / ssx); yv.append(1 - (F ** 2).sum() / ssy)
    W, Pm, Qm, Tm = (np.hstack(v) for v in (Wt, P, Q, T)); Bs = W @ np.linalg.pinv(Pm.T @ W) @ Qm.T
    B = Bs * ys[None, :] / xs[:, None]; b0 = ym - xm @ B; fitted = X @ B + b0
    ssa = np.array([(Tm[:, a] ** 2).sum() * (Qm[:, a] ** 2).sum() for a in range(Tm.shape[1])])
    vip = np.sqrt(X.shape[1] * ((W / np.linalg.norm(W, axis=0)) ** 2 @ ssa) / ssa.sum())
    return {"B": B, "intercept": b0, "x_var_cum": np.array(xv), "y_var_cum": np.array(yv), "vip": vip, "fitted": fitted, "mask": m,
            "scores": Tm}


def cronbach_alpha(X):
    X = np.asarray(X, float); X = X[np.all(np.isfinite(X), 1)]; k = X.shape[1]
    a = k / (k - 1) * (1 - X.var(0, ddof=1).sum() / X.sum(1).var(ddof=1)); out = {"Items": k, "N": len(X), "Cronbach alpha": a}
    for j in range(k):
        Z = np.delete(X, j, 1); out[f"alpha if item {j + 1} dropped"] = (k - 1) / (k - 2) * (1 - Z.var(0, ddof=1).sum() / Z.sum(1).var(ddof=1)) if k > 2 else np.nan
    return out


def bland_altman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float); m = np.isfinite(a) & np.isfinite(b); a, b = a[m], b[m]
    d = a - b; md, sd = d.mean(), d.std(ddof=1); n = len(d); se_l = np.sqrt(3 * sd ** 2 / n); t = stats.t.ppf(0.975, n - 1)
    return {"N": n, "Mean difference (bias)": md, "SD of differences": sd, "Lower limit of agreement": md - 1.96 * sd,
            "Upper limit of agreement": md + 1.96 * sd, "Bias 95% CI": f"{md - t * sd / np.sqrt(n):.6g} to {md + t * sd / np.sqrt(n):.6g}",
            "Limits 95% CI half-width": t * se_l, "p (bias = 0)": stats.ttest_1samp(d, 0).pvalue}


# ================================================================ curve tools
def average_curves(curves, n=None):
    """curves: list of (x, y). Interpolate onto a common X over the overlapping range; return x, mean, SD, count."""
    cl = [(np.asarray(x, float), np.asarray(y, float)) for x, y in curves]
    cl = [(x[np.isfinite(x) & np.isfinite(y)], y[np.isfinite(x) & np.isfinite(y)]) for x, y in cl]
    lo, hi = max(x.min() for x, _ in cl), min(x.max() for x, _ in cl)
    if lo >= hi: raise ValueError("The curves do not overlap in X.")
    xs = np.linspace(lo, hi, n or max(len(x) for x, _ in cl))
    Ys = np.array([np.interp(xs, x[np.argsort(x)], y[np.argsort(x)]) for x, y in cl])
    return xs, Ys.mean(0), Ys.std(0, ddof=1) if len(cl) > 1 else np.zeros_like(xs), len(cl)


def subtract_line(x, y, x1, x2):
    """Subtract the straight line through the curve's values at x1 and x2."""
    x, y = np.asarray(x, float), np.asarray(y, float); o = np.argsort(x); y1, y2 = np.interp([x1, x2], x[o], y[o])
    return y - (y1 + (y2 - y1) * (x - x1) / (x2 - x1))


def subtract_reference(x, y, xr, yr):
    o = np.argsort(xr); return np.asarray(y, float) - np.interp(np.asarray(x, float), np.asarray(xr, float)[o], np.asarray(yr, float)[o])


def intersections(x1, y1, x2, y2):
    """Crossing points of two curves (linear interpolation on a merged X grid)."""
    x1, y1, x2, y2 = (np.asarray(v, float) for v in (x1, y1, x2, y2)); o1, o2 = np.argsort(x1), np.argsort(x2)
    xs = np.unique(np.r_[x1, x2]); xs = xs[(xs >= max(x1.min(), x2.min())) & (xs <= min(x1.max(), x2.max()))]
    d = np.interp(xs, x1[o1], y1[o1]) - np.interp(xs, x2[o2], y2[o2]); out = []
    for i in np.nonzero(np.sign(d[:-1]) * np.sign(d[1:]) <= 0)[0]:
        if d[i] == d[i + 1]: continue
        xc = xs[i] - d[i] * (xs[i + 1] - xs[i]) / (d[i + 1] - d[i])
        if out and abs(out[-1][0] - xc) < 1e-12: continue
        out.append((xc, float(np.interp(xc, x1[o1], y1[o1]))))
    return out


def x_at_y(x, y, y0):
    """All X where the curve crosses y = y0 (linear interpolation)."""
    x, y = np.asarray(x, float), np.asarray(y, float); d = y - y0; out = []
    for i in np.nonzero(np.sign(d[:-1]) * np.sign(d[1:]) <= 0)[0]:
        if d[i] != d[i + 1]: out.append(x[i] - d[i] * (x[i + 1] - x[i]) / (d[i + 1] - d[i]))
    return sorted(set(np.round(out, 12)))


def rise_time(x, y, lo=0.1, hi=0.9):
    """Time for a step to rise from lo to hi fraction of its range (first crossings after the minimum)."""
    x, y = np.asarray(x, float), np.asarray(y, float); y0, y1 = np.nanmin(y), np.nanmax(y); i0 = int(np.nanargmin(y))
    xs, ys = x[i0:], y[i0:]; a, b = x_at_y(xs, ys, y0 + lo * (y1 - y0)), x_at_y(xs, ys, y0 + hi * (y1 - y0))
    if not a or not b: raise ValueError("No rising edge found.")
    return {"Rise time": b[0] - a[0], f"X at {lo:.0%}": a[0], f"X at {hi:.0%}": b[0], "Low level": y0, "High level": y1}


def polygon_area(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    a = 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))); cx = np.sum((x + np.roll(x, -1)) * (x * np.roll(y, -1) - np.roll(x, -1) * y)) / (6 * a)
    cy = np.sum((y + np.roll(y, -1)) * (x * np.roll(y, -1) - np.roll(x, -1) * y)) / (6 * a)
    return {"Area": abs(a), "Signed area": a, "Perimeter": float(np.sum(np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]])))),
            "Centroid X": cx, "Centroid Y": cy}


def confidence_ellipse(x, y, level=0.95, n=200):
    x, y = np.asarray(x, float), np.asarray(y, float); m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    C = np.cov(x, y); ev, vec = np.linalg.eigh(C); r = np.sqrt(stats.chi2.ppf(level, 2) * ev); t = np.linspace(0, 2 * np.pi, n)
    pts = vec @ np.vstack([r[0] * np.cos(t), r[1] * np.sin(t)]); return x.mean() + pts[0], y.mean() + pts[1]


# ================================================================ gridding (extra methods)
def grid_idw(x, y, z, nx=100, ny=100, power=2.0):
    x, y, z = (np.asarray(v, float) for v in (x, y, z)); m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z); x, y, z = x[m], y[m], z[m]
    xs, ys = np.linspace(x.min(), x.max(), nx), np.linspace(y.min(), y.max(), ny); X, Y = np.meshgrid(xs, ys)
    out = np.empty(X.size); P = np.column_stack([X.ravel(), Y.ravel()])
    for s in range(0, len(P), 20000):  # chunks keep memory bounded
        d = np.hypot(P[s:s + 20000, :1] - x[None, :], P[s:s + 20000, 1:] - y[None, :]); w = 1 / np.maximum(d, 1e-12) ** power
        exact = d < 1e-12; w[exact.any(1)] = exact[exact.any(1)].astype(float); out[s:s + 20000] = (w @ z) / w.sum(1)
    return out.reshape(ny, nx), [xs[0], xs[-1], ys[0], ys[-1]]


def grid_tps(x, y, z, nx=100, ny=100, smoothing=0.0):
    x, y, z = (np.asarray(v, float) for v in (x, y, z)); m = np.isfinite(x) & np.isfinite(y) & np.isfinite(z); x, y, z = x[m], y[m], z[m]
    if len(x) > 3000: raise ValueError("Thin-plate spline is limited to 3000 points; use linear or Shepard gridding.")
    f = interpolate.RBFInterpolator(np.column_stack([x, y]), z, kernel="thin_plate_spline", smoothing=smoothing)
    xs, ys = np.linspace(x.min(), x.max(), nx), np.linspace(y.min(), y.max(), ny); X, Y = np.meshgrid(xs, ys)
    return f(np.column_stack([X.ravel(), Y.ravel()])).reshape(ny, nx), [xs[0], xs[-1], ys[0], ys[-1]]


# ================================================================ worksheet operations (pure pandas)
def stack_columns(df, cols, id_cols=()):
    return df.melt(id_vars=list(id_cols), value_vars=list(cols), var_name="Column", value_name="Value").dropna(subset=["Value"])


def unstack_column(df, value_col, by_col):
    g = {str(k): v[value_col].reset_index(drop=True) for k, v in df.groupby(df[by_col].astype(str), sort=True)}
    return pd.DataFrame(g)


def pivot(df, rows, cols, values, agg="mean"):
    t = pd.pivot_table(df, index=rows, columns=cols, values=values, aggfunc=agg)
    t.columns = [str(c) for c in t.columns]; return t.reset_index()


def frequency_counts(a, bins=None):
    a = pd.Series(a).dropna()
    if bins is None or not pd.api.types.is_numeric_dtype(a):
        v = a.astype(str).value_counts().sort_index(); return pd.DataFrame({"Value": v.index, "Count": v.values, "Percent": 100 * v.values / v.sum()})
    cnt, edges = np.histogram(a.astype(float), bins=bins)
    return pd.DataFrame({"Bin start": edges[:-1], "Bin end": edges[1:], "Bin centre": (edges[:-1] + edges[1:]) / 2, "Count": cnt,
                         "Cumulative": np.cumsum(cnt), "Percent": 100 * cnt / max(cnt.sum(), 1)})


def row_stats(df, cols):
    X = df[list(cols)].apply(pd.to_numeric, errors="coerce")
    return pd.DataFrame({"Row mean": X.mean(1), "Row SD": X.std(1), "Row min": X.min(1), "Row max": X.max(1), "Row sum": X.sum(1, min_count=1),
                         "Row N": X.count(1)})


def reduce_rows(df, n, how="mean"):
    num = df.apply(pd.to_numeric, errors="coerce"); grp = np.arange(len(df)) // int(n)
    return getattr(num.groupby(grp), how)().reset_index(drop=True)


def fill_missing(y, x=None, method="linear"):
    y = np.asarray(y, float); s = pd.Series(y)
    if method in ("forward", "backward"): return (s.ffill() if method == "forward" else s.bfill()).to_numpy()
    if method == "mean": return s.fillna(s.mean()).to_numpy()
    if x is None: return s.interpolate(limit_area="inside").to_numpy()
    x = np.asarray(x, float); out = y.copy(); hasx = np.isfinite(x); known = hasx & np.isfinite(y); gap = hasx & ~np.isfinite(y)
    if known.sum() >= 2:  # interpolate against X, only inside the known range and only where X itself is present
        o = np.argsort(x[known]); xk, yk = x[known][o], y[known][o]; inside = gap & (x >= xk[0]) & (x <= xk[-1])
        out[inside] = np.interp(x[inside], xk, yk)
    return out


def join_frames(left, right, key_left, key_right, how="inner"):
    return left.merge(right, left_on=key_left, right_on=key_right, how=how, suffixes=("", "_2"))


def sequence(n, start=1.0, step=1.0, kind="arithmetic", repeat=1):
    if kind == "geometric": base = start * step ** np.arange(int(np.ceil(n / repeat)))
    else: base = start + step * np.arange(int(np.ceil(n / repeat)))
    return np.repeat(base, repeat)[:n]
