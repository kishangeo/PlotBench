"""Geochronology: York et al. (2004) regression with correlated errors for isochrons, U-Pb concordia (Wetherill and
Tera-Wasserburg) with error ellipses, weighted mean with MSWD, and detrital age KDE, PDP and cumulative distributions.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Errors are absolute 1 sigma everywhere; results are reported at 2 sigma.
"""
import numpy as np
from scipy import stats
from scipy.optimize import brentq

L238, L235, U85 = 1.55125e-10, 9.8485e-10, 137.818  # 1/yr, Jaffey et al. (1971); 238U/235U of Hiess et al. (2012)
SYSTEMS = {  # decay constant (1/yr), parent/daughter ratio names, reference for the constant
    "Rb-Sr": (1.3972e-11, "87Rb/86Sr", "87Sr/86Sr", "Villa et al. (2015)"),
    "Sm-Nd": (6.54e-12, "147Sm/144Nd", "143Nd/144Nd", "Lugmair & Marti (1978)"),
    "Lu-Hf": (1.867e-11, "176Lu/177Hf", "176Hf/177Hf", "Soderlund et al. (2004)"),
    "Re-Os": (1.666e-11, "187Re/188Os", "187Os/188Os", "Smoliar et al. (1996)"),
}


def _clean(*cols):
    a = [np.asarray(c, float) for c in cols]; ok = np.all([np.isfinite(c) for c in a], axis=0)
    return [c[ok] for c in a], ok


def york(x, sx, y, sy, rho=None, n_iter=500, tol=1e-15):
    """Straight line through points with errors in X and Y (1 sigma) and their correlation, York et al. (2004, Am J Phys 72, 367).
    Returns slope, intercept, their 1-sigma errors, MSWD, its probability p and n."""
    r = np.zeros(len(np.atleast_1d(x))) if rho is None else rho
    (x, sx, y, sy, r), _ = _clean(x, sx, y, sy, r)
    keep = (sx > 0) & (sy > 0); x, sx, y, sy, r = x[keep], sx[keep], y[keep], sy[keep], r[keep]
    n = len(x)
    if n < 2: raise ValueError("York regression needs at least two points with errors above zero.")
    wx, wy = 1 / sx ** 2, 1 / sy ** 2; al = np.sqrt(wx * wy)
    b = np.polyfit(x, y, 1)[0]

    def step(b):
        W = wx * wy / (wx + b * b * wy - 2 * b * r * al)
        X, Y = np.sum(W * x) / np.sum(W), np.sum(W * y) / np.sum(W); U, V = x - X, y - Y
        return W, X, Y, W * (U / wy + b * V / wx - (b * U + V) * r / al), U, V
    for _ in range(n_iter):
        W, X, Y, beta, U, V = step(b); bn = np.sum(W * beta * V) / np.sum(W * beta * U)
        done = abs(bn - b) <= tol * max(abs(bn), 1e-300); b = bn
        if done: break
    W, X, Y, beta, U, V = step(b); a = Y - b * X
    xa = X + beta; xb = np.sum(W * xa) / np.sum(W); u = xa - xb
    sb = np.sqrt(1 / np.sum(W * u ** 2)); sa = np.sqrt(1 / np.sum(W) + xb ** 2 * sb ** 2)
    mswd = np.sum(W * (y - b * x - a) ** 2) / (n - 2) if n > 2 else np.nan
    p = float(stats.chi2.sf(mswd * (n - 2), n - 2)) if n > 2 else np.nan
    return {"slope": float(b), "intercept": float(a), "s_slope": float(sb), "s_intercept": float(sa), "mswd": float(mswd), "p": p, "n": n}


def isochron_age(fit, system="Rb-Sr"):
    """Age (Ma) and its 2-sigma error from an isochron slope: t = ln(1 + slope) / lambda. When MSWD > 1 the errors are also given
    multiplied by sqrt(MSWD) (overdispersion)."""
    lam = SYSTEMS[system][0]; b, sb = fit["slope"], fit["s_slope"]
    t = np.log1p(b) / lam / 1e6; st = sb / (lam * (1 + b)) / 1e6
    k = np.sqrt(fit["mswd"]) if np.isfinite(fit["mswd"]) and fit["mswd"] > 1 else 1.0
    return {"age": t, "age_2s": 2 * st, "age_2s_mswd": 2 * st * k, "initial": fit["intercept"], "initial_2s": 2 * fit["s_intercept"],
            "initial_2s_mswd": 2 * fit["s_intercept"] * k}


# ---------------------------------------------------------------- U-Pb
def wetherill(t_ma):
    """(207Pb/235U, 206Pb/238U) on concordia at t (Ma)."""
    t = np.asarray(t_ma, float) * 1e6; return np.expm1(L235 * t), np.expm1(L238 * t)


def tera_wasserburg(t_ma):
    """(238U/206Pb, 207Pb/206Pb radiogenic) on concordia at t (Ma)."""
    t = np.asarray(t_ma, float) * 1e6; e8 = np.expm1(L238 * t)
    with np.errstate(divide="ignore", invalid="ignore"): return 1 / e8, np.expm1(L235 * t) / (U85 * e8)


L232 = 4.9475e-11  # 1/yr, Le Roux & Glendenin (1963)


def stacey_kramers(t_ma):
    """Common-Pb composition of the two-stage model of Stacey & Kramers (1975) at t (Ma): (206/204, 207/204, 208/204)."""
    t = np.asarray(t_ma, float) * 1e6; T = 3.7e9
    a = 11.152 + 9.735 * (np.exp(L238 * T) - np.exp(L238 * t)); b = 12.998 + 9.735 / U85 * (np.exp(L235 * T) - np.exp(L235 * t))
    c = 31.23 + 36.84 * (np.exp(L232 * T) - np.exp(L232 * t)); return a, b, c


def common_pb(method, r68, r76=None, r64=None, r86=None, th_u=None, t0=None, it=30):
    """Common-Pb corrected 206Pb*/238U and its age (Ma), and f206 (fraction of 206Pb that is common).
    method '204': f206 = (206/204)c / (206/204)m. '207': the measured 207/206 is a mix of radiogenic (on concordia at the 206/238
    age) and common Pb. '208': as '207' with 208/206 and the sample's Th/U. Common Pb from Stacey & Kramers (1975) at the age,
    iterated; t0 (Ma) fixes the age of the common Pb instead."""
    r68 = np.asarray(r68, float); t = age68(r68); f = np.zeros_like(r68)
    for _ in range(it):
        tc = t if t0 is None else np.full_like(t, float(t0)); a, b, c = stacey_kramers(tc)
        with np.errstate(divide="ignore", invalid="ignore"):
            if method == "204": f = a / np.asarray(r64, float)
            elif method == "207":
                tt = t * 1e6; star = (np.expm1(L235 * tt) / U85) / np.expm1(L238 * tt)  # radiogenic 207/206 at t
                f = (np.asarray(r76, float) - star) / (b / a - star)
            else:
                tt = t * 1e6; star = np.asarray(th_u, float) * np.expm1(L232 * tt) / np.expm1(L238 * tt)  # radiogenic 208/206
                f = (np.asarray(r86, float) - star) / (c / a - star)
            f = np.clip(f, 0.0, 1.0); new = age68(r68 * (1 - f))
        if np.nanmax(np.abs(new - t), initial=0) < 1e-4: t = new; break
        t = new
    return r68 * (1 - f), t, f


def age68(r): return np.log1p(np.asarray(r, float)) / L238 / 1e6
def age75(r): return np.log1p(np.asarray(r, float)) / L235 / 1e6


def age76(r):
    """207Pb/206Pb age (Ma) of radiogenic Pb, solved numerically."""
    def one(v):
        if not np.isfinite(v) or v <= 0.0461: return np.nan  # 0.0461 is the ratio at t -> 0
        return brentq(lambda t: tera_wasserburg(t)[1] - v, 1e-3, 6000.0)
    return np.array([one(v) for v in np.atleast_1d(np.asarray(r, float))])


def ellipse(x, y, sx, sy, rho=0.0, conf=0.95, n=72):
    """Points of the error ellipse (1-sigma inputs) at the given confidence for two dimensions."""
    cov = np.array([[sx * sx, rho * sx * sy], [rho * sx * sy, sy * sy]]); val, vec = np.linalg.eigh(cov)
    k = np.sqrt(stats.chi2.ppf(conf, 2)); t = np.linspace(0, 2 * np.pi, n)
    pts = (vec @ (np.sqrt(np.clip(val, 0, None))[:, None] * np.vstack([np.cos(t), np.sin(t)]))) * k
    return x + pts[0], y + pts[1]


# ---------------------------------------------------------------- weighted mean and age spectra
def weighted_mean(v, s):
    """Inverse-variance weighted mean with its 1-sigma error, MSWD and probability (s: 1-sigma errors)."""
    (v, s), _ = _clean(v, s); keep = s > 0; v, s = v[keep], s[keep]; n = len(v)
    if n < 1: raise ValueError("No values with errors above zero.")
    w = 1 / s ** 2; m = np.sum(w * v) / np.sum(w); sm = np.sqrt(1 / np.sum(w))
    mswd = np.sum(w * (v - m) ** 2) / (n - 1) if n > 1 else np.nan
    p = float(stats.chi2.sf(mswd * (n - 1), n - 1)) if n > 1 else np.nan
    return {"mean": float(m), "s_mean": float(sm), "mswd": float(mswd), "p": p, "n": n}


def bandwidth_lscv(a):
    """Kernel bandwidth by least-squares cross-validation (Rudemo 1982, Bowman 1984): unlike Silverman's rule it does not
    oversmooth age spectra with several peaks. Searched between 1/500 of the range and Silverman's value."""
    a = np.sort(np.asarray(a, float)[np.isfinite(a)]); n = len(a)
    hs = 0.9 * min(np.std(a, ddof=1), stats.iqr(a) / 1.34 or np.std(a, ddof=1)) * n ** -0.2
    d = (a[:, None] - a[None, :]) ** 2

    def score(h):  # integral of the squared estimate minus twice the mean leave-one-out density (Gaussian kernel, closed form)
        k2 = np.exp(-d / (4 * h * h)).sum() / (n * n * 2 * h * np.sqrt(np.pi))
        k1 = (np.exp(-d / (2 * h * h)).sum() - n) / (n * (n - 1) * h * np.sqrt(2 * np.pi))
        return k2 - 2 * k1
    grid = np.geomspace(max(np.ptp(a) / 500, 1e-12), max(hs, np.ptp(a) / 400), 60)
    return float(grid[np.argmin([score(h) for h in grid])])


def kde(ages, grid, bandwidth=None):
    """Gaussian kernel density of ages on the grid; bandwidth in age units (None: least-squares cross-validation)."""
    a = np.asarray(ages, float); a = a[np.isfinite(a)]
    if len(a) < 2 or np.ptp(a) == 0: return np.zeros_like(grid, float)
    bw = float(bandwidth) if bandwidth else bandwidth_lscv(a)
    return stats.gaussian_kde(a, bw_method=bw / np.std(a, ddof=1))(grid)


def pdp(ages, s, grid):
    """Probability density plot: the mean of one normal curve per age with its own 1-sigma error."""
    (a, s), _ = _clean(ages, s); keep = s > 0; a, s = a[keep], s[keep]
    if not len(a): return np.zeros_like(grid, float)
    return np.mean(stats.norm.pdf(np.asarray(grid, float)[:, None], a[None, :], s[None, :]), axis=1)


def concordia_age(x, sx, y, sy, rho=None):
    """Concordia age of Ludwig (1998, Geochim Cosmochim Acta 62, 665-676) in Wetherill space (x = 207Pb/235U, y = 206Pb/238U, 1-sigma errors):
    the error-weighted mean point of all analyses, then the age t that minimises S(t) = R' W R, R = mean - concordia(t), W = the summed
    inverse covariances. The age error is from the curvature of S (variance = 2 / S''); decay-constant errors are not included.
    Returns age (Ma), 2-sigma, MSWD and p of concordance (1 df), of equivalence (2n - 2 df) and combined (2n - 1 df), and n."""
    r = np.zeros(len(np.atleast_1d(x))) if rho is None else rho
    (x, sx, y, sy, r), _ = _clean(x, sx, y, sy, r); keep = (sx > 0) & (sy > 0); x, sx, y, sy, r = x[keep], sx[keep], y[keep], sy[keep], r[keep]
    n = len(x)
    if n < 1: raise ValueError("No analyses with errors.")
    Ws = [np.linalg.inv(np.array([[a * a, c * a * b], [c * a * b, b * b]])) for a, b, c in zip(sx, sy, r)]
    W = sum(Ws); m = np.linalg.solve(W, sum(Wi @ np.array([xi, yi]) for Wi, xi, yi in zip(Ws, x, y)))
    s_eq = float(sum((np.array([xi, yi]) - m) @ Wi @ (np.array([xi, yi]) - m) for Wi, xi, yi in zip(Ws, x, y)))

    def S(t):
        d = m - np.array(wetherill(t)); return float(d @ W @ d)
    from scipy.optimize import minimize_scalar
    t0 = float(age68(m[1])); res = minimize_scalar(S, bounds=(max(t0 * 0.5, 1e-3), t0 * 1.5 + 10), method="bounded", options={"xatol": 1e-7})
    t = float(res.x); h = max(t * 1e-4, 1e-4); d2 = (S(t + h) - 2 * S(t) + S(t - h)) / h ** 2
    st = np.sqrt(2 / d2) if d2 > 0 else np.nan; sc = S(t); dfe = 2 * n - 2
    return {"age": t, "age_2s": 2 * st, "mswd_conc": sc, "p_conc": float(stats.chi2.sf(sc, 1)),
            "mswd_eq": s_eq / dfe if dfe else np.nan, "p_eq": float(stats.chi2.sf(s_eq, dfe)) if dfe else np.nan,
            "mswd_all": (s_eq + sc) / (dfe + 1), "p_all": float(stats.chi2.sf(s_eq + sc, dfe + 1)), "n": n}


def _demo():
    near = lambda a, b, tol: abs(a - b) <= tol
    # Pearson (1901) data with York (1966) weights: the benchmark of York et al. (2004), a = 5.4799, b = -0.48053
    x = [0, 0.9, 1.8, 2.6, 3.3, 4.4, 5.2, 6.1, 6.5, 7.4]; y = [5.9, 5.4, 4.4, 4.6, 3.5, 3.7, 2.8, 2.8, 2.4, 1.5]
    wx = np.array([1000, 1000, 500, 800, 200, 80, 60, 20, 1.8, 1.0]); wy = np.array([1, 1.8, 4, 8, 20, 20, 70, 70, 100, 500.])
    f = york(x, 1 / np.sqrt(wx), y, 1 / np.sqrt(wy))
    assert near(f["slope"], -0.48053, 5e-5) and near(f["intercept"], 5.4799, 5e-4), f
    assert near(f["s_slope"], 0.0580, 5e-4) and near(f["s_intercept"], 0.2950, 5e-4), f  # Cantrell (2008) Table: 0.0580, 0.2950
    assert near(f["s_slope"] * np.sqrt(f["mswd"]), 0.0706, 5e-4)  # scaled by sqrt(MSWD)
    # a perfect 1000 Ma Rb-Sr isochron with Sr0 = 0.7045 returns 1000 Ma, MSWD about 0 and the initial ratio
    lam = SYSTEMS["Rb-Sr"][0]; rb = np.array([0.1, 0.5, 1.2, 2.0, 3.5]); sr = 0.7045 + rb * np.expm1(lam * 1e9)
    a = isochron_age(york(rb, rb * 0.005, sr, sr * 2e-5), "Rb-Sr")
    assert near(a["age"], 1000.0, 1e-6) and near(a["initial"], 0.7045, 1e-9), a
    # concordia: both ages of a point on the curve agree; 207/206 age solved back
    for t in (100.0, 1000.0, 3000.0):
        x75, y68 = wetherill(t); assert near(age75(x75), t, 1e-6) and near(age68(y68), t, 1e-6)
        assert near(age76(tera_wasserburg(t)[1])[0], t, 1e-4)
    assert near(tera_wasserburg(1000.0)[1], 0.07253, 2e-5)  # 207Pb/206Pb at 1 Ga
    w = weighted_mean([100, 102, 98, 101], [1, 1, 1, 1]); assert near(w["mean"], 100.25, 1e-9) and near(w["s_mean"], 0.5, 1e-12)
    assert near(w["mswd"], (0.0625 + 3.0625 + 5.0625 + 0.5625) / 3, 1e-9)
    ex, ey = ellipse(0, 0, 1, 2, 0.0); k = np.sqrt(stats.chi2.ppf(0.95, 2)); assert near(ex.max(), k, 1e-3) and near(ey.max(), 2 * k, 1e-2)
    g = np.linspace(0, 200, 2001); d = pdp([50, 150], [5, 5], g); assert near(np.trapz(d, g), 1.0, 1e-3) and near(g[np.argmax(d)], 50, 0.2)
    assert near(np.trapz(kde([90, 100, 110, 105, 95], g), g), 1.0, 2e-2)
    rng = np.random.default_rng(5); two = np.r_[rng.normal(500, 20, 60), rng.normal(1500, 20, 60)]; h = bandwidth_lscv(two)
    assert 5 < h < 60, h  # finds the narrow peaks (Silverman's rule gives about 300)
    gg = np.linspace(0, 2000, 4001); dd = kde(two, gg); assert dd[np.argmin(np.abs(gg - 1000))] < 0.02 * dd.max()  # a clear gap between the peaks
    # concordia age: one exactly concordant 500 Ma analysis gives 500 Ma with MSWD 0; scattered analyses about it give 500 Ma, MSWD near 1
    x5, y5 = wetherill(500.0); ca = concordia_age([x5], [x5 * 0.005], [y5], [y5 * 0.004], [0.8])
    assert near(ca["age"], 500.0, 1e-3) and ca["mswd_conc"] < 1e-8 and 0 < ca["age_2s"] < 10, ca
    rng = np.random.default_rng(2); xs = x5 * (1 + rng.normal(0, 0.003, 30)); ys_ = y5 * (1 + rng.normal(0, 0.003, 30))
    cb = concordia_age(xs, xs * 0.003, ys_, ys_ * 0.003); assert abs(cb["age"] - 500) < 3 and 0.3 < cb["mswd_eq"] < 2, cb
    print("GEOCHRON OK")


if __name__ == "__main__":
    _demo()
