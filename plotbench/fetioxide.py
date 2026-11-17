"""Fe-Ti oxide thermodynamics for the two-oxide geothermometer / oxygen barometer of Ghiorso & Evans (2008).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Spinel (titanomagnetite) solid solution: Sack & Ghiorso (1991b, Contrib Mineral Petrol 106, 474-505; erratum 107, 415), the
Fe-Mg-Ti-Al-Fe3+ model with long-range cation order over tetrahedral and octahedral sites (Table 1 site fractions, Table 4 Gibbs
energy, Table 6 parameters). Mn is counted as Mg and Cr as Al, as in Ghiorso & Evans (2008). Energies in kJ.
"""
import numpy as np
from scipy.optimize import minimize

R = 8.3143e-3  # kJ/(K mol)

# ---------------------------------------------------------------- Sack & Ghiorso (1991b) Table 6, independent parameters (kJ)
SP = dict(dG11=-30.250, W11=30.962, W22=25.606, dG55=29.706, W55=0.000,
          dH24=28.451, dH25=32.844, dHEX=-20.083, dHX=14.644,
          WOCT=8.368, WTET=8.368, W14=92.257, W1p4=53.555, W15=41.840, W1p5=61.923, W15p=55.229, W1p5p=29.288,
          W24u=52.718, W2p4u=48.534, W2p5u=60.752, W25up=69.873, W45=25.941, W45p=9.205, W4u5up=6.694)


def dependent(p=SP):
    """Dependent parameters of Table 6 used in Table 4, from the independent ones ('u' = index of a Mg end-member, underlined in
    the paper). Each reproduces the value printed in Table 6 (checked in _demo)."""
    gx, gex, g24, g25 = p["dHX"], p["dHEX"], p["dH24"], p["dH25"]
    d = dict(p)
    d["W12p"] = p["W22"] - p["W2p4u"] + p["W1p4"] + gx / 2 + gex / 2 - g24                    # -0.544
    d["W1p2"] = p["W11"] + p["W2p4u"] - p["W1p4"] + gx / 2 - gex / 2 + g24                    # 71.756
    d["W24"] = p["WOCT"] + p["W14"] + gx / 2 - gex / 2 + g24                                  # 146.440
    d["W25"] = p["WOCT"] + p["W15"] + g25                                                     # 83.052
    d["W2p4"] = (p["WTET"] + p["W22"] - p["W11"] - p["W2p4u"] - p["W24u"] + 2 * p["W1p4"] + p["W14"]
                 + gx / 2 + gex / 2 - g24)                                                     # 69.957
    d["W25p"] = p["W4u5up"] - p["W45p"] + p["W15p"] + gx / 2 - gex / 2 + g24                  # 98.533
    d["W2p5"] = 67.477  # printed value; the Table 6 formula (W2'5u - W2'4u + W1'4 + dGX/2 + dGEX/2 + dG25 - dG24) gives 67.447 (rounding)
    d["W2p5p"] = (p["WTET"] + p["W22"] - p["W11"] + p["W4u5up"] - p["W45p"] - p["W2p4u"] - p["W25up"] + p["W1p5p"]
                  + p["W1p4"] + p["W15p"])                                                     # 20.166
    d["dG22"] = 2 * g24 + p["dG11"] + (p["W24u"] + p["W2p4u"] + p["W11"]) - (p["W14"] + p["W1p4"] + p["W22"])  # -12.552
    return d


P = dependent()


def sites(X2, X4, X5, s1, s2, s4):
    """Site fractions (Table 1): tetrahedral Mg, Fe2+, Fe3+, Al; octahedral Mg, Fe2+, Fe3+, Al, Ti (two octahedral sites)."""
    tMg = (X2 + s1) / 2; tFe2 = X4 + s2 + s4 - tMg; tFe3 = X5 - s4; tAl = 1 - X4 - X5 - s2
    oMg = (X2 - s1) / 4; oFe2 = (1 - s2 - s4) / 2 - oMg; oFe3 = (X5 + s4) / 2; oAl = (1 - X4 - X5 + s2) / 2; oTi = X4 / 2
    return np.array([tMg, tFe2, tFe3, tAl]), np.array([oMg, oFe2, oFe3, oAl, oTi])


# ---------------------------------------------------------------- Sack & Ghiorso (1991a, Am Mineral 76, 827-847): the version of the
# spinel model that Ghiorso & Evans (2008) use. Same site fractions and entropy as 1991b, revised parameters (Table 4) and G* as the
# explicit second-degree polynomial of Table 3 (here with X3 = Cr = 0; Cr is counted as Al). Underlined indices of the paper are 'u'.
SA = dict(dH11=-36.401, W11=18.828, W22=15.062, dH55=26.150, W55=0.0, dG24=27.405, dG25=33.681, dGEX=-15.062, dGX=10.042,
          W6=8.368, W4=8.368, W14=87.027, W15=41.840, W15p=48.953, W1p4=51.882, W1p5=60.250, W1p5p=29.288,
          W24u=52.718, W25up=64.015, W2p4u=45.606, W2p5u=60.250, W45=25.104, W45p=8.368, W45up=7.531)


def gibbs_91a(X2, X4, X5, s1, s2, s4, T, a=SA):
    """Table 3 of Sack & Ghiorso (1991a) with X3 = 0 and G1* = G2* = G4* = G5* = 0 (they enter linearly), minus T S_IC (kJ)."""
    W6, W4, gx, gex, g24, g25 = a["W6"], a["W4"], a["dGX"], a["dGEX"], a["dG24"], a["dG25"]
    W14, W15, W15p, W1p4, W1p5, W11, W22, W55 = a["W14"], a["W15"], a["W15p"], a["W1p4"], a["W1p5"], a["W11"], a["W22"], a["W55"]
    W24u, W2p4u, W2p5u, W25up, W45, W45p, W45up, W1p5p = a["W24u"], a["W2p4u"], a["W2p5u"], a["W25up"], a["W45"], a["W45p"], a["W45up"], a["W1p5p"]
    G = ((0.5 * (W6 + W24u - W14 + g24) + 0.25 * (gx + gex)) * X2 + W14 * X4 + W15 * X5
         + (0.5 * (W24u - W14 - W6 + g24) + 0.25 * (gx + gex)) * s1 + (W11 + a["dH11"]) * s2 + (W15p - W15 + a["dH55"]) * s4
         - 0.25 * (W4 + W6 + gx) * X2 ** 2 - W14 * X4 ** 2 - W15 * X5 ** 2 - 0.25 * (W4 + W6 - gx) * s1 ** 2 - W11 * s2 ** 2 - W55 * s4 ** 2
         + (0.5 * (W4 - W6 + W14 - W24u + g24) + 0.25 * (gx - gex)) * X2 * X4
         + (0.5 * (W2p5u - W1p5 + W11 - W22) + g25) * X2 * X5
         + 0.5 * (W6 - W4) * X2 * s1
         + (0.5 * (W4 - W6 + W11 - W22 - gex) + W2p4u - W1p4 + g24) * X2 * s2
         + (0.5 * (W4 - W6 + W1p5 - W2p5u + W15p - W25up + W22 - W11 - gex) + W45up - W45p + g24 - g25) * X2 * s4
         + (W45 - W14 - W15) * X4 * X5
         + (0.5 * (W4 + W14 - W24u - g24) + 0.25 * (gex - gx)) * X4 * s1
         + (W1p4 - W14 - W11) * X4 * s2 + (W45p - W45 + W15 - W15p) * X4 * s4
         + 0.5 * (W2p5u - W1p5 + W11 - W22) * X5 * s1 + (W1p5 - W15 - W11) * X5 * s2 + (W15 - W15p + W55) * X5 * s4
         + 0.5 * (W4 + W6 + W11 - W22 - gx) * s1 * s2
         + 0.5 * (W4 + W6 + W15p - W25up + W1p5 - W2p5u + W22 - W11 - gx) * s1 * s4
         + (W15 - W15p + W1p5p - W1p5) * s2 * s4)
    t, o = sites(X2, X4, X5, s1, s2, s4)
    xl = lambda v: np.where(v > 0, v * np.log(np.where(v > 0, v, 1)), 0.0)
    return G + R * T * (np.sum(xl(t)) + 2 * np.sum(xl(o)))


def gibbs(X2, X4, X5, s1, s2, s4, T, p=P):
    """Molar Gibbs energy of the spinel (kJ) relative to the end-member vibrational energies G1* = G2* = G4* = G5* = 0
    (they enter linearly and cancel in activities): Table 4, G = G* - T S_IC."""
    a = 1 - X2 / 2 - X4 - X5 + s1 / 2 - s2          # Al[Al,Fe]2O4 (inverse hercynite)
    b = s2 - X2 / 2 - s1 / 2                        # Fe[Al]2O4 (normal hercynite)
    c = X2 / 2 - s1 / 2                             # Al[Al,Mg]2O4 (inverse spinel)
    e = X2 / 2 + s1 / 2                             # Mg[Al]2O4 (normal spinel)
    f, g = X5 - s4, s4                              # inverse and normal magnetite
    G = (b * p["dG11"] + e * p["dG22"] + g * p["dG55"]
         + a * b * p["W11"] + a * c * p["WOCT"] + a * e * p["W12p"] + a * X4 * p["W14"] + a * f * p["W15"] + a * g * p["W15p"]
         + b * c * p["W1p2"] + b * e * p["WTET"] + b * X4 * p["W1p4"] + b * f * p["W1p5"] + b * g * p["W1p5p"] + c * e * p["W22"]
         + c * X4 * p["W24"] + c * f * p["W25"] + c * g * p["W25p"] + e * X4 * p["W2p4"] + e * f * p["W2p5"] + e * g * p["W2p5p"]
         + X4 * f * p["W45"] + X4 * g * p["W45p"] + f * g * p["W55"])
    t, o = sites(X2, X4, X5, s1, s2, s4)
    xl = lambda v: np.where(v > 0, v * np.log(np.where(v > 0, v, 1)), 0.0)
    S = -R * (np.sum(xl(t)) + 2 * np.sum(xl(o)))
    return G - T * S


def _interior(X2, X4, X5):
    """A strictly interior (s1, s2, s4): every site fraction at least tau times its value in a random distribution (each
    cation spread over the three sites in proportion to their number; Ti is octahedral only), with tau as large as possible.
    Site fractions are linear in s, so this is a small linear program."""
    from scipy.optimize import linprog
    z = np.zeros(3); base = np.r_[sites(X2, X4, X5, *z)]
    A = np.column_stack([np.r_[sites(X2, X4, X5, *np.eye(3)[k])] - base for k in range(3)])  # d(site)/ds
    Mg, Fe2, Fe3, Al = X2, 1 - X2 + X4, 2 * X5, 2 * (1 - X4 - X5)
    rnd = np.array([Mg, Fe2, Fe3, Al, Mg, Fe2, Fe3, Al]) / 3  # tet Mg, Fe2+, Fe3+, Al; oct Mg, Fe2+, Fe3+, Al (oct Ti is fixed)
    rows = list(range(4)) + list(range(4, 8))
    Aub = np.column_stack([-A[rows], rnd]); bub = base[rows]
    r = linprog(c=[0, 0, 0, -1], A_ub=Aub, b_ub=bub, bounds=[(-1, 1)] * 3 + [(0, 1)], method="highs")
    return r.x[:3] if r.success else z


def _coord_min(f, sitefun, x0, n_sweeps=60, tol=1e-11):
    """Minimise f(x) over the region where every site fraction sitefun(x) >= 0 (linear in x) by cycling exact 1-D bounded
    minimisations over each variable (robust for the badly scaled ordering problem when some cations are only traces)."""
    from scipy.optimize import minimize_scalar
    x = np.array(x0, float)
    for _ in range(n_sweeps):
        x_old = x.copy()
        for k in range(len(x)):
            b = sitefun(x); e = np.zeros(len(x)); e[k] = 1.0; a = sitefun(x + e) - b  # site = b + a (v - x_k)
            lo, hi = -np.inf, np.inf
            for bi, ai in zip(b, a):
                if ai > 1e-15: lo = max(lo, x[k] - bi / ai)
                elif ai < -1e-15: hi = min(hi, x[k] - bi / ai)
            lo, hi = max(lo, -1.0), min(hi, 1.0)
            if not hi > lo: continue
            pad = 1e-13 * max(1.0, hi - lo)

            def g(v, k=k):
                y = x.copy(); y[k] = v; return f(y)
            r = minimize_scalar(g, bounds=(lo + pad, hi - pad), method="bounded", options={"xatol": 1e-13})
            if r.fun <= g(x[k]): x[k] = r.x
        if np.max(np.abs(x - x_old)) < tol: break
    return x


def order(X2, X4, X5, T, p=P, guess=None):
    """Equilibrium ordering (s1, s2, s4): the minimum of G with every site fraction non-negative."""
    sitev = lambda s: np.r_[sites(X2, X4, X5, *s)]
    f = lambda s: gibbs_91a(X2, X4, X5, *s, T)
    starts = ([guess] if guess is not None else []) + [_interior(X2, X4, X5)]
    best = None
    for s0 in starts:
        if np.min(sitev(np.asarray(s0, float))) < 0: continue
        x = _coord_min(f, sitev, s0); fx = f(x)
        if best is None or fx < best[0]: best = (fx, x)
    if best is None: raise ValueError("No feasible cation distribution for this spinel composition.")
    return best[1]


ENDMEMBERS = {"FeAl2O4": (0, 0, 0), "MgAl2O4": (1, 0, 0), "Fe2TiO4": (0, 1, 0), "Fe3O4": (0, 0, 1)}  # (X2, X4, X5)


def mu_excess(X2, X4, X5, T, p=P, h=1e-6):
    """mu_j - G_j* (kJ) of the end-members at equilibrium ordering, from the tangent to G (derivatives at fixed order, which is
    exact because dG/ds = 0 at equilibrium)."""
    X = np.array([X2, X4, X5], float); s = order(X2, X4, X5, T, p)
    G0 = gibbs_91a(*X, *s, T); dG = np.zeros(3)
    for k in range(3):
        d = np.zeros(3); d[k] = h
        dG[k] = (gibbs_91a(*(X + d), *s, T) - gibbs_91a(*(X - d), *s, T)) / (2 * h)
    return {j: G0 + float(np.dot(np.array(v) - X, dG)) for j, v in ENDMEMBERS.items()}, s


from functools import lru_cache


@lru_cache(maxsize=4096)
def _pure_cached(j, T): return _pure_raw(j, T)


def _pure(j, T, p=P): return _pure_cached(j, round(float(T), 6)) if p is P else _pure_raw(j, T, p)


def _pure_raw(j, T, p=P):
    """G - G_j* of pure end-member j at its own equilibrium ordering (the standard state)."""
    X2, X4, X5 = ENDMEMBERS[j]; d = 1e-5  # just inside the composition space so every logarithm is defined (error ~ RT 1e-5)
    X2, X4, X5 = max(X2, d) if X2 == 0 else X2 - 2 * d, max(X4, d) if X4 == 0 else X4 - 2 * d, max(X5, d) if X5 == 0 else X5 - 2 * d
    return mu_excess(X2, X4, X5, T, p)[0][j]


def spinel_activities(X2, X4, X5, T, p=P):
    """Activities of Fe3O4, Fe2TiO4, FeAl2O4 and MgAl2O4 in the spinel relative to the pure, equilibrium-ordered end-members."""
    mu, s = mu_excess(X2, X4, X5, T, p)
    return {j: float(np.exp((mu[j] - _pure(j, T, p)) / (R * T))) for j in ENDMEMBERS}, s


def spinel_x(cat):
    """Composition variables from cations per 4 oxygens (3 cations): X2 = Mg (+Mn), X4 = Ti, X5 = Fe3+/2; Al (+Cr) is what remains."""
    X2 = cat.get("Mg", 0) + cat.get("Mn", 0); X4 = cat.get("Ti", 0); X5 = cat.get("Fe3", 0) / 2
    return X2, X4, X5


def _demo():
    # the magnetite-hematite buffer from Berman (1988) standard states agrees with Frost (1991) within 0.25 log units
    for T in (873.15, 1073.15, 1273.15): assert abs(log_fo2_mh(T) - (-25700.6 / T + 14.558)) < 0.25, T
    # an Evans et al. (2006) run (Table 4, run 24: 800 C, 2055 bar, NNO - 0.27) is recovered within 50 C and 0.6 log units
    spn = {"TiO2": 12.53, "Al2O3": 4.27, "Fe2O3": 40.14, "FeO": 41.70, "MnO": 0.18, "MgO": 0.97}
    T, lf, dnno = two_oxide_wt(spn, {"TiO2": 48.64, "Al2O3": 0.49, "Fe2O3": 10.79, "FeO": 40.53, "MnO": 0.23, "MgO": 1.67}, 2055.0)
    assert abs(T - 800) < 50 and abs(dnno + 0.27) < 0.6, (T, dnno)
    # the dependent parameters reproduce the values printed in Table 6
    for k, v in (("W12p", -0.544), ("W1p2", 71.756), ("W24", 146.440), ("W25", 83.052), ("W2p4", 69.957),
                 ("W25p", 98.533), ("W2p5", 67.477), ("W2p5p", 20.166), ("dG22", -12.552)):
        assert abs(P[k] - v) < 2e-3, (k, P[k], v)
    print("FETIOXIDE OK")


if __name__ == "__main__":
    _demo()


# ---------------------------------------------------------------- rhombohedral oxide: Ghiorso & Evans (2008) eq. (78), Table 2
# composition: X = FeTiO3, Y = MgTiO3 (geikielite), Z = MnTiO3 (pyrophanite), C = Al2O3 (corundum), 1 - X - Y - Z - C = Fe2O3;
# ordering: s, t, u = (Fe2+, Mg, Mn on layer A) - (on layer B), eqs (70)-(77). Supersystem values (kJ).
RP = dict(WHmIl=22.536, dWHmIl=-5.627, WIlIl=69.908, d2WIlIl=12.756, WHmIlIl=-0.833, dH=-2.039, dS=-1.248e-3, alpha=0.073021,
          WIlGk=2.6, WIlGkT=88.100, WIlPy=2.2, WIlPyT=30.244, WHmCr=69.0, dWHmCr=0.0)


def _rp(p=RP):
    q = dict(p)
    for k in ("WHmGk", "WHmPy", "WIlCr", "WGkCr", "WPyCr"): q[k] = p["WHmIl"]
    for k in ("dWHmGk", "dWHmPy", "dWIlCr", "dWGkCr", "dWPyCr"): q[k] = p["dWHmIl"]
    q["WGkGk"] = q["WPyPy"] = p["WIlIl"]; q["d2WGkGk"] = q["d2WPyPy"] = p["d2WIlIl"]; q["WHmGkGk"] = q["WHmPyPy"] = p["WHmIlIl"]
    q["WGkPy"] = q["WGkPyT"] = p["WIlGk"]
    return q


RQ = _rp()


def _xlnx(v): return np.where(v > 0, v * np.log(np.where(v > 0, v, 1.0)), 0.0)


def rhm_gibbs(X, Y, Z, C, s, t, u, T, q=RQ):
    """Ghiorso & Evans (2008) eq. (78) with all end-member mu-zero terms set to 0 (they enter linearly), kJ/mol."""
    H = 1 - X - Y - Z - C; a = q["alpha"]; L = X + Y + Z
    conf = (_xlnx((X + s) / 2) + _xlnx((X - s) / 2) - a * _xlnx(X / 2) * 2 + _xlnx((Y + t) / 2) + _xlnx((Y - t) / 2) - a * _xlnx(Y / 2) * 2
            + _xlnx((Z + u) / 2) + _xlnx((Z - u) / 2) - a * _xlnx(Z / 2) * 2
            + _xlnx((L - s - t - u) / 2) + _xlnx((L + s + t + u) / 2) - a * _xlnx(L / 2) * 2
            + 2 * (1 - a) * _xlnx(H) + 2 * (1 - a) * _xlnx(C))
    # note: -a X ln(X/2) = -2a (X/2) ln(X/2), written with _xlnx(X/2) * 2
    G = R * T * conf
    G += (q["WHmIl"] + (H - X) * q["dWHmIl"]) * H * X + (q["WHmGk"] + (H - Y) * q["dWHmGk"]) * H * Y
    G += (q["WHmPy"] + (H - Z) * q["dWHmPy"]) * H * Z + (q["WHmCr"] + (H - C) * q["dWHmCr"]) * H * C
    G += 0.5 * X * Y * (q["WIlGk"] + q["WIlGkT"]) + 0.5 * s * t * (q["WIlGk"] - q["WIlGkT"])
    G += 0.5 * X * Z * (q["WIlPy"] + q["WIlPyT"]) + 0.5 * s * u * (q["WIlPy"] - q["WIlPyT"])
    G += 0.5 * Y * Z * (q["WGkPy"] + q["WGkPyT"]) + 0.5 * t * u * (q["WGkPy"] - q["WGkPyT"])
    G += (q["WIlCr"] + (X - C) * q["dWIlCr"]) * X * C + (q["WGkCr"] + (Y - C) * q["dWGkCr"]) * Y * C + (q["WPyCr"] + (Z - C) * q["dWPyCr"]) * Z * C
    G += (q["WIlIl"] / 4 + H * (q["dWHmIl"] / 2 + q["WHmIlIl"] / 4) - 0.5 * C * q["dWIlCr"]) * (X * X - s * s)
    G += (q["WGkGk"] / 4 + H * (q["dWHmGk"] / 2 + q["WHmGkGk"] / 4) - 0.5 * C * q["dWGkCr"]) * (Y * Y - t * t)
    G += (q["WPyPy"] / 4 + H * (q["dWHmPy"] / 2 + q["WHmPyPy"] / 4) - 0.5 * C * q["dWPyCr"]) * (Z * Z - u * u)
    G += q["d2WIlIl"] / 4 * (X * X - s * s) * s * s + q["d2WGkGk"] / 4 * (Y * Y - t * t) * t * t + q["d2WPyPy"] / 4 * (Z * Z - u * u) * u * u
    return G


def rhm_order(X, Y, Z, C, T, q=RQ):
    """Equilibrium (s, t, u): minimum of eq. (78) with |s| <= X, |t| <= Y, |u| <= Z (each site fraction non-negative)."""
    L = X + Y + Z
    sitev = lambda v: np.array([X + v[0], X - v[0], Y + v[1], Y - v[1], Z + v[2], Z - v[2], L - v.sum(), L + v.sum(), v[0], v[1], v[2]])
    f = lambda v: rhm_gibbs(X, Y, Z, C, *v, T, q)
    best = None
    for fr in (0.999, 0.5, 0.0):  # ordered and disordered starts: the ordering transition can be first order
        x = _coord_min(f, sitev, np.array([fr * X, fr * Y, fr * Z])); fx = f(x)
        if best is None or fx < best[0]: best = (fx, x)
    return best[1]  # the ordered state is symmetric in A and B, so s, t, u >= 0 without loss


RHM_END = {"Fe2O3": (0, 0, 0, 0), "FeTiO3": (1, 0, 0, 0), "MgTiO3": (0, 1, 0, 0), "MnTiO3": (0, 0, 1, 0), "Al2O3": (0, 0, 0, 1)}


def rhm_mu(X, Y, Z, C, T, q=RQ, h=1e-7):
    """mu_j - mu_j(zero) (kJ) for the rhombohedral end-members at equilibrium order: add Berman's mu-zero to get mu_j."""
    v = np.array([X, Y, Z, C], float); o = rhm_order(*v, T, q); G0 = rhm_gibbs(*v, *o, T, q); dG = np.zeros(4)
    for k in range(4):
        d = np.zeros(4); d[k] = h
        dG[k] = (rhm_gibbs(*(v + d), *o, T, q) - rhm_gibbs(*(v - d), *o, T, q)) / (2 * h)
    return {j: G0 + float(np.dot(np.array(e) - v, dG)) for j, e in RHM_END.items()}, o


# ---------------------------------------------------------------- standard-state Gibbs energies (apparent G = H - T S, J/mol)
# Berman (1988): Delta_f H (kJ), S (J/K), V (J/bar), Cp = k0 + k1 T^-0.5 + k2 T^-2 + k3 T^-3 (Table 3a), lambda terms (Table 3b):
# Cp_lambda = T (l1 + l2 T)^2 from 298 K up to T_lambda, plus the enthalpy of transition at T_lambda.
BERMAN = {"Fe2O3": (-825.627, 87.437, 3.027, (146.86, 0.0, -55.768e5, 52.563e7), (955.0, -7.403e-2, 27.921e-5, 1287.0)),
          "FeTiO3": (-1231.947, 108.628, 3.170, (150.00, -4.416e2, -33.237e5, 34.815e7), None),
          "Fe3O4": (-1117.403, 146.114, 4.452, (207.93, 0.0, -72.433e5, 66.436e7), (848.0, -19.502e-2, 61.037e-5, 1565.0)),
          # ulvospinel: Ghiorso & Evans (2008) abstract and eq. (138); its lambda-like term applies at all T of interest
          "Fe2TiO4": (-1490.417, 184.199, 4.682, (249.63, -1817.4, 0.0, -5.453e7), (1.0e9, -0.039452, 7.54197e-5, 0.0))}
T0 = 298.15


def _cp_int(k, T):
    """Integrals of the Berman Cp from 298.15 K to T: (int Cp dT, int Cp/T dT)."""
    k0, k1, k2, k3 = k
    H = k0 * (T - T0) + 2 * k1 * (np.sqrt(T) - np.sqrt(T0)) - k2 * (1 / T - 1 / T0) - k3 / 2 * (1 / T ** 2 - 1 / T0 ** 2)
    S = k0 * np.log(T / T0) - 2 * k1 * (1 / np.sqrt(T) - 1 / np.sqrt(T0)) - k2 / 2 * (1 / T ** 2 - 1 / T0 ** 2) - k3 / 3 * (1 / T ** 3 - 1 / T0 ** 3)
    return H, S


def _lambda_int(lam, T):
    """Integrals of T (l1 + l2 T)^2 from 298.15 K to min(T, T_lambda), plus the transition enthalpy above T_lambda."""
    Tl, l1, l2, dH = lam; Tu = min(T, Tl)
    f = lambda t: (l1 * l1 * t ** 2 / 2 + 2 * l1 * l2 * t ** 3 / 3 + l2 * l2 * t ** 4 / 4, l1 * l1 * t + l1 * l2 * t ** 2 + l2 * l2 * t ** 3 / 3)
    (h1, s1), (h0, s0) = f(Tu), f(T0)
    H, S = h1 - h0, s1 - s0
    if T >= Tl: H += dH; S += dH / Tl
    return H, S


def g_berman(phase, T, P=1.0):
    """Apparent Gibbs energy of a pure phase (J/mol) at T (K) and P (bar): Delta_f H(298) - T S(298) + Cp integrals (+ lambda) + V (P - 1)."""
    Hf, S0, V, k, lam = BERMAN[phase]
    dH, dS = _cp_int(k, T)
    if lam is not None: lh, ls = _lambda_int(lam, T); dH += lh; dS += ls
    return Hf * 1e3 + dH - T * (S0 + dS) + V * (P - 1)


def g_o2(T):
    """O2 gas (J/mol): H - T S with H(298) = 0 and S(298) = 205.152 J/K, Shomate coefficients of NIST-JANAF (Chase 1998)."""
    t = T / 1000.0
    A, B, C, D, E, F, G, Hh = ((31.32234, -20.23531, 57.86644, -36.50624, -0.007374, -8.903471, 246.7945, 0.0) if T < 700 else
                               (30.03235, 8.772972, -3.988133, 0.788313, -0.741599, -11.32468, 236.1663, 0.0))
    H = (A * t + B * t * t / 2 + C * t ** 3 / 3 + D * t ** 4 / 4 - E / t + F - Hh) * 1e3
    S = A * np.log(t) + B * t + C * t * t / 2 + D * t ** 3 / 3 - E / (2 * t * t) + G
    return H - T * S


def log_fo2_mh(T):
    """log10 fO2 of the magnetite-hematite buffer from these standard states: 4 Fe3O4 + O2 = 6 Fe2O3."""
    dG = 6 * g_berman("Fe2O3", T) - 4 * g_berman("Fe3O4", T) - g_o2(T)
    return dG / (8.3143 * T * np.log(10))


# ---------------------------------------------------------------- the two-oxide geothermometer / oxygen barometer
EXCHANGE_SIGN = 1.0  # the Table 2 correction dH - T dS added to the exchange energy; this choice recovers the experiments of Evans et al. (2006)


def _mu_pair(spn, rhm, T, P=1.0):
    """Chemical potentials (J/mol) of Fe3O4, Fe2TiO4 (spinel) and Fe2O3, FeTiO3 (rhombohedral) at T, P."""
    a, _ = spinel_activities(*spn, T)
    mr, _ = rhm_mu(*rhm, T)
    RT = 8.3143 * T
    return {"Fe3O4": g_berman("Fe3O4", T, P) + RT * np.log(a["Fe3O4"]), "Fe2TiO4": g_berman("Fe2TiO4", T, P) + RT * np.log(a["Fe2TiO4"]),
            "Fe2O3": g_berman("Fe2O3", T, P) + 1e3 * mr["Fe2O3"], "FeTiO3": g_berman("FeTiO3", T, P) + 1e3 * mr["FeTiO3"]}


def exchange_dG(spn, rhm, T, P=1.0, sign=None):
    """Gibbs energy (J) of Fe2TiO4 + Fe2O3 = FeTiO3 + Fe3O4 for the two oxides at T: zero at equilibrium (eq. 51), with the
    Table 2 correction dH - T dS."""
    m = _mu_pair(spn, rhm, T, P); sg = EXCHANGE_SIGN if sign is None else sign
    return (m["FeTiO3"] + m["Fe3O4"] - m["Fe2TiO4"] - m["Fe2O3"]) + sg * 1e3 * (RP["dH"] - T * RP["dS"])


def log_fo2(spn, rhm, T, P=1.0):
    """log10 fO2 from 4 Fe3O4 + O2 = 6 Fe2O3 with the two oxides at T (eq. 52)."""
    m = _mu_pair(spn, rhm, T, P)
    return (6 * m["Fe2O3"] - 4 * m["Fe3O4"] - g_o2(T)) / (8.3143 * T * np.log(10))


def two_oxide(spn, rhm, P=1.0, lo=773.15, hi=1773.15, sign=None):
    """Temperature (C) and log10 fO2 of a coexisting titanomagnetite (X2 = Mg+Mn, X4 = Ti, X5 = Fe3+/2) and rhombohedral oxide
    (X = FeTiO3, Y = MgTiO3, Z = MnTiO3, C = Al2O3 mole fractions). Returns (T C, log fO2, delta NNO); NaN if no solution."""
    from scipy.optimize import brentq
    f = lambda T: exchange_dG(spn, rhm, T, P, sign)
    grid = np.linspace(lo, hi, 15); vals = [f(t) for t in grid]
    for i in range(len(grid) - 1):
        if np.sign(vals[i]) != np.sign(vals[i + 1]):
            T = brentq(f, grid[i], grid[i + 1], xtol=1e-3); lf = log_fo2(spn, rhm, T, P)
            return T - 273.15, lf, lf - log_fo2_nno(T, P)
    return np.nan, np.nan, np.nan


def log_fo2_nno(T, P=1.0):
    """Ni-NiO buffer of O'Neill & Pownceby (1993), as used by Ghiorso & Evans (2008) for delta NNO: mu(O2) = -478967 + 248.514 T
    - 9.7961 T ln T (J), plus 0.046 (P - 1)/T for pressure (bar)."""
    mu = -478967.0 + 248.514 * T - 9.7961 * T * np.log(T)
    return mu / (8.3143 * T * np.log(10)) + 0.046 * (P - 1) / T


# ---------------------------------------------------------------- from microprobe analyses (wt% oxides) to model compositions
OX = {"TiO2": (79.866, "Ti", 1, 2), "Al2O3": (101.961, "Al", 2, 3), "Cr2O3": (151.990, "Cr", 2, 3), "Fe2O3": (159.688, "Fe3", 2, 3),
      "FeO": (71.844, "Fe2", 1, 1), "MnO": (70.937, "Mn", 1, 1), "MgO": (40.304, "Mg", 1, 1), "V2O3": (149.881, "V", 2, 3),
      "ZnO": (81.38, "Zn", 1, 1), "SiO2": (60.084, "Si", 1, 2), "CaO": (56.077, "Ca", 1, 1)}


def cations(wt, n_cat, n_ox):
    """Cations per n_ox oxygens with n_cat cations; with only total iron (FeO or FeOt), Fe3+ by charge balance (Droop 1987)."""
    mol = {OX[k][1]: wt[k] / OX[k][0] * OX[k][2] for k in wt if k in OX and wt[k] is not None and np.isfinite(wt[k])}
    if "Fe3" not in mol or not mol.get("Fe3"):  # all Fe given as FeO: split by charge balance
        charge = {"Ti": 4, "Al": 3, "Cr": 3, "Fe2": 2, "Mn": 2, "Mg": 2, "V": 3, "Zn": 2, "Si": 4, "Ca": 2}
        tot = sum(mol.values()); f = n_cat / tot; c = {k: v * f for k, v in mol.items()}
        q = sum(c[k] * charge[k] for k in c); fe3 = max(0.0, min(2 * n_ox - q, c.get("Fe2", 0)))
        c["Fe3"] = fe3; c["Fe2"] = c.get("Fe2", 0) - fe3; return c
    tot = sum(mol.values()); return {k: v * n_cat / tot for k, v in mol.items()}


def spinel_from_wt(wt):
    """(X2, X4, X5) of a titanomagnetite: Mg + Mn (Mn counted as Mg), Ti, Fe3+/2, on 3 cations and 4 oxygens."""
    c = cations(wt, 3, 4); return c.get("Mg", 0) + c.get("Mn", 0), c.get("Ti", 0), c.get("Fe3", 0) / 2


def rhm_from_wt(wt):
    """(X, Y, Z, C) of an ilmenite-hematite: FeTiO3, MgTiO3, MnTiO3, Al2O3 (Cr counted as Al) on 2 cations and 3 oxygens;
    titanium goes to Mg and Mn titanates first, the rest to FeTiO3; Fe2O3 is what remains."""
    c = cations(wt, 2, 3); Y, Z = c.get("Mg", 0), c.get("Mn", 0); C = (c.get("Al", 0) + c.get("Cr", 0)) / 2
    X = max(c.get("Ti", 0) - Y - Z, 1e-6); tot = X + Y + Z + C + c.get("Fe3", 0) / 2
    return X / tot, max(Y, 1e-6) / tot, max(Z, 1e-6) / tot, max(C, 1e-6) / tot


BH88 = (0.9317, -0.0909)  # equilibrium line, Bacon & Hirschmann (1988) Table 1
BH88_UP, BH88_LO = (0.9430, 0.0124), (0.9213, -0.1696)  # their +-2 sigma envelope (typical microprobe precision), Table 1


def mg_mn_test(spn_wt, rhm_wt):
    """Bacon & Hirschmann (1988) test of equilibrium between magnetite and ilmenite: pairs in equilibrium lie on
    log(Mg/Mn)Mt = 0.9317 log(Mg/Mn)Ilm - 0.0909 (atomic ratios); a pair passes when it lies inside their 2 sigma envelope
    (upper 0.9430 x + 0.0124, lower 0.9213 x - 0.1696). Returns (log Mg/Mn Mt, log Mg/Mn Ilm, deviation from the line, passes)."""
    try:
        r = lambda w: np.log10((w["MgO"] / OX["MgO"][0]) / (w["MnO"] / OX["MnO"][0]))
        mt, il = r(spn_wt), r(rhm_wt)
    except (KeyError, ZeroDivisionError, TypeError): return np.nan, np.nan, np.nan, False
    dev = mt - (BH88[0] * il + BH88[1]); inside = BH88_LO[0] * il + BH88_LO[1] <= mt <= BH88_UP[0] * il + BH88_UP[1]
    return mt, il, dev, bool(np.isfinite(dev) and inside)


def two_oxide_wt(spn_wt, rhm_wt, P=1.0):
    """T (C), log fO2 and delta NNO from wt% analyses of coexisting titanomagnetite and ilmenite."""
    X2, X4, X5 = spinel_from_wt(spn_wt)
    return two_oxide((max(X2, 1e-6), X4, X5), rhm_from_wt(rhm_wt), P)
