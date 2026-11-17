"""PlotBench analysis, part 3: mixed-design ANOVA, one-way MANOVA, linear discriminant analysis. No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np
import pandas as pd
from scipy import stats


# ================================================================ mixed-design ANOVA (one between-subjects, one within-subjects factor)
def mixed_anova(y, subject, between, within):
    """Long format. Each subject is in one 'between' group and has a value at every level of 'within'.
    Subjects missing a level are dropped. Returns rows: source, SS, df, MS, F, p (exact for balanced designs)."""
    d = pd.DataFrame({"y": np.asarray(y, float), "s": np.asarray(subject).astype(str), "g": np.asarray(between).astype(str),
                      "w": np.asarray(within).astype(str)}).dropna()
    d = d.groupby(["s", "g", "w"], as_index=False)["y"].mean()
    if (d.groupby("s")["g"].nunique() > 1).any(): raise ValueError("A subject appears in more than one between-subjects group.")
    levels = sorted(d.w.unique()); b = len(levels)
    wide = d.pivot(index="s", columns="w", values="y")[levels].dropna()
    grp = d.groupby("s")["g"].first().loc[wide.index].to_numpy(); G = sorted(set(grp)); a = len(G)
    Y = wide.to_numpy(float); N = len(Y)
    if a < 2 or b < 2: raise ValueError("Need at least two groups and two within-subject levels.")
    gm = Y.mean(); ms = Y.mean(1); mw = Y.mean(0)
    ng = np.array([np.sum(grp == g) for g in G]); mg = np.array([Y[grp == g].mean() for g in G])
    mgw = np.array([Y[grp == g].mean(0) for g in G])
    ss_a = b * np.sum(ng * (mg - gm) ** 2)
    ss_subj = b * sum(np.sum((ms[grp == g] - mg[i]) ** 2) for i, g in enumerate(G))
    ss_b = N * np.sum((mw - gm) ** 2)
    ss_ab = sum(ng[i] * np.sum((mgw[i] - mg[i] - mw + gm) ** 2) for i in range(a))
    ss_tot = np.sum((Y - gm) ** 2); ss_err = ss_tot - ss_a - ss_subj - ss_b - ss_ab
    df_a, df_s, df_b, df_ab, df_e = a - 1, N - a, b - 1, (a - 1) * (b - 1), (b - 1) * (N - a)
    ms_s, ms_e = ss_subj / df_s, ss_err / df_e
    Fa, Fb, Fab = (ss_a / df_a) / ms_s, (ss_b / df_b) / ms_e, (ss_ab / df_ab) / ms_e
    return [["Between subjects: group", ss_a, df_a, ss_a / df_a, Fa, stats.f.sf(Fa, df_a, df_s)],
            ["Error (subjects within groups)", ss_subj, df_s, ms_s, "", ""],
            ["Within subjects: condition", ss_b, df_b, ss_b / df_b, Fb, stats.f.sf(Fb, df_b, df_e)],
            ["Group x condition", ss_ab, df_ab, ss_ab / df_ab, Fab, stats.f.sf(Fab, df_ab, df_e)],
            ["Error (within subjects)", ss_err, df_e, ms_e, "", ""],
            ["Total", ss_tot, N * b - 1, "", "", ""]]


# ================================================================ one-way MANOVA
def manova(Y, groups):
    """Y: n x p responses, groups: n labels. Returns the four multivariate tests with F approximations."""
    Y = np.asarray(Y, float); g = np.asarray(groups).astype(str); m = np.all(np.isfinite(Y), axis=1) & (g != "nan"); Y, g = Y[m], g[m]
    L = sorted(set(g)); k = len(L); n, p = Y.shape; mu = Y.mean(0)
    E = sum((Y[g == c] - Y[g == c].mean(0)).T @ (Y[g == c] - Y[g == c].mean(0)) for c in L)
    H = sum(np.sum(g == c) * np.outer(Y[g == c].mean(0) - mu, Y[g == c].mean(0) - mu) for c in L)
    lam = np.clip(np.real(np.linalg.eigvals(np.linalg.solve(E, H))), 0, None)
    q, dfe = k - 1, n - k; s, mm, nn = min(p, q), (abs(p - q) - 1) / 2, (dfe - p - 1) / 2
    wilks = float(np.prod(1 / (1 + lam))); pillai = float(np.sum(lam / (1 + lam))); hot = float(np.sum(lam)); roy = float(lam.max())
    t = np.sqrt((p ** 2 * q ** 2 - 4) / (p ** 2 + q ** 2 - 5)) if p ** 2 + q ** 2 - 5 > 0 else 1.0  # Rao's F for Wilks
    w = dfe + q - (p + q + 1) / 2; d1 = p * q; d2 = w * t - (p * q - 2) / 2
    Fw = (1 - wilks ** (1 / t)) / wilks ** (1 / t) * d2 / d1
    p1, p2 = s * (2 * mm + s + 1), s * (2 * nn + s + 1); Fp = p2 / p1 * pillai / (s - pillai)
    h1, h2 = s * (2 * mm + s + 1), 2 * (s * nn + 1); Fh = h2 * hot / (s * h1)
    r = max(p, q); r1, r2 = r, dfe - r + q; Fr = roy * r2 / r1
    tests = [["Wilks lambda", wilks, Fw, d1, d2, stats.f.sf(Fw, d1, d2)],
             ["Pillai trace", pillai, Fp, p1, p2, stats.f.sf(Fp, p1, p2)],
             ["Hotelling-Lawley trace", hot, Fh, h1, h2, stats.f.sf(Fh, h1, h2)],
             ["Roy largest root (upper bound)", roy, Fr, r1, r2, stats.f.sf(Fr, r1, r2)]]
    return {"tests": tests, "groups": L, "n": n, "p": p, "H": H, "E": E}


# ================================================================ linear discriminant analysis
def _lda_fit(X, g, L):
    pri = np.array([np.mean(g == c) for c in L]); mus = np.array([X[g == c].mean(0) for c in L])
    S = sum((X[g == c] - mus[i]).T @ (X[g == c] - mus[i]) for i, c in enumerate(L)) / (len(X) - len(L))
    W = mus @ np.linalg.pinv(S); b = -0.5 * np.einsum("ij,ij->i", W, mus) + np.log(pri)
    return W, b, S, mus


def lda(X, groups, names):
    """Fisher LDA: classification functions, canonical discriminant functions, confusion matrix,
    resubstitution and leave-one-out accuracy, canonical scores and posterior probabilities."""
    X = np.asarray(X, float); g = np.asarray(groups).astype(str); m = np.all(np.isfinite(X), axis=1) & (g != "nan"); X, g = X[m], g[m]
    L = sorted(set(g)); k = len(L); n, p = X.shape
    if k < 2: raise ValueError("Need at least two groups.")
    W, b, S, mus = _lda_fit(X, g, L)
    sc = X @ W.T + b; post = np.exp(sc - sc.max(1, keepdims=True)); post /= post.sum(1, keepdims=True)
    pred = np.array(L)[np.argmax(sc, 1)]
    hits = []
    for i in range(n):  # leave-one-out cross-validation
        keep = np.arange(n) != i
        if min(np.sum(g[keep] == c) for c in L) < 2: continue
        Wi, bi, _, _ = _lda_fit(X[keep], g[keep], L); hits.append(L[int(np.argmax(X[i] @ Wi.T + bi))] == g[i])
    mu = X.mean(0); Bm = sum(np.sum(g == c) * np.outer(mus[i] - mu, mus[i] - mu) for i, c in enumerate(L)) / (k - 1)
    ev, vec = np.linalg.eig(np.linalg.pinv(S) @ Bm); o = np.argsort(-np.real(ev)); nf = min(k - 1, p)
    ev, vec = np.real(ev[o][:nf]), np.real(vec[:, o][:, :nf])
    vec = vec / np.sqrt(np.einsum("ji,jk,ki->i", vec, S, vec))  # each function has unit pooled within-group variance
    return {"groups": L, "names": list(names),
            "classification": [[nm] + list(W[:, j]) for j, nm in enumerate(names)] + [["Constant"] + list(b)],
            "canonical": [[nm] + list(vec[j]) for j, nm in enumerate(names)], "eigen": ev, "eigen_pct": 100 * ev / ev.sum(),
            "confusion": [[t] + [int(np.sum((g == t) & (pred == c))) for c in L] for t in L],
            "accuracy": float(np.mean(pred == g)), "loo_accuracy": float(np.mean(hits)) if hits else np.nan,
            "pred": pred, "post": post, "canon": (X - mu) @ vec, "mask": m}
