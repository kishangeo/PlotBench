"""Thermometers and barometers from published calibrations. Every function takes numbers or arrays and returns T in deg C or P in kbar.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Each entry of METHODS names its inputs, the equation (shown in the program) and the reference. Results outside the calibration range
are still returned; the method notes give the range to check against.
"""
import numpy as np

R = 8.3144626  # J mol-1 K-1
K0 = 273.15


def _a(x): return np.asarray(x, float)


def _ln(x):
    """Natural log that gives NaN, not -inf or a warning, for zero, negative or non-finite input (an empty cell, a zero site fraction)."""
    with np.errstate(all="ignore"): a = _a(x); return np.log(np.where((a > 0) & np.isfinite(a), a, np.nan))


def _log10(x):
    with np.errstate(all="ignore"): return np.log10(np.where(_a(x) > 0, _a(x), np.nan))


# ----------------------------------------------------------------------------- trace-element thermometers
def ti_in_zircon(ti_ppm, a_sio2=1.0, a_tio2=1.0):
    """Ferry & Watson (2007): log(Ti ppm) = 5.711 - 4800/T - log aSiO2 + log aTiO2 (T in K); with both activities 1 this is
    Watson et al. (2006)."""
    return 4800.0 / (5.711 - _log10(ti_ppm) - _log10(a_sio2) + _log10(a_tio2)) - K0


def zr_in_rutile(zr_ppm, a_sio2=1.0):
    """Ferry & Watson (2007): log(Zr ppm) = 7.420 - 4530/T - log aSiO2 (T in K)."""
    return 4530.0 / (7.420 - _log10(zr_ppm) - _log10(a_sio2)) - K0


def zr_in_rutile_watson2006(zr_ppm):
    """Watson et al. (2006): log(Zr ppm) = 7.36 - 4470/T."""
    return 4470.0 / (7.36 - _log10(zr_ppm)) - K0


def zr_in_titanite_hayden2008(zr_ppm, p_kbar, a_tio2=1.0, a_sio2=1.0):
    """Hayden, Watson & Wark (2008): log Zr(ppm) = 10.52 - 7708/T - 960 P/T - log aTiO2 - log aSiO2 (T in K, P in GPa)."""
    P = np.asarray(p_kbar, float) / 10.0
    return (7708.0 + 960.0 * P) / (10.52 - _log10(zr_ppm) - np.log10(np.asarray(a_tio2, float)) - np.log10(np.asarray(a_sio2, float))) - K0


def zircon_dfmq_loucks2020(ce_ppm, u_ppm, ti_ppm, age_ma=0.0):
    """Loucks, Fiorentini & Henriquez (2020): dFMQ = 3.998 log[Ce / sqrt(Ui Ti)] + 2.284, Ui = U at crystallisation
    (U e^(lambda238 t), t from the age in Ma)."""
    pos = lambda a: np.where(np.asarray(a, float) > 0, np.asarray(a, float), np.nan)  # blank, zero or negative: no result, not +-inf
    ui = pos(u_ppm) * np.exp(1.55125e-10 * np.maximum(np.asarray(age_ma, float), 0.0) * 1e6)
    with np.errstate(all="ignore"):
        return 3.998 * np.log10(pos(ce_ppm) / np.sqrt(ui * pos(ti_ppm))) + 2.284


def ti_in_quartz_wark2006(ti_ppm):
    """Wark & Watson (2006), TitaniQ at aTiO2 = 1: log(Ti ppm) = 5.69 - 3765/T."""
    return 3765.0 / (5.69 - _log10(ti_ppm)) - K0


def ti_in_quartz_thomas2010(ti_ppm, p_kbar, a_tio2=1.0):
    """Thomas et al. (2010): RT ln X(TiO2, qtz) = -60952 + 1.520 T - 1741 P(kbar) + RT ln aTiO2, X from Ti ppm by weight."""
    x = _a(ti_ppm) * 1e-6 * 60.0843 / 47.867
    with np.errstate(all="ignore"):
        return (-60952.0 - 1741.0 * _a(p_kbar)) / (R * _ln(x) - 1.520 - R * _ln(_a(a_tio2))) - K0


# ----------------------------------------------------------------------------- zircon saturation
_CAT = {"SiO2": (60.0843, 1), "TiO2": (79.8658, 1), "Al2O3": (101.9613, 2), "FeO": (71.8444, 1), "Fe2O3": (159.6882, 2), "MnO": (70.9374, 1),
        "MgO": (40.3044, 1), "CaO": (56.0774, 1), "Na2O": (61.9789, 2), "K2O": (94.1960, 2), "P2O5": (141.9445, 2)}


def m_factor(ox):
    """M = (Na + K + 2Ca) / (Al Si) in cation fractions (all major cations summed to 1), as defined by Watson & Harrison (1983)."""
    cat = {k: np.nan_to_num(_a(ox[k])) / m * n for k, (m, n) in _CAT.items() if k in ox}
    tot = sum(cat.values())
    f = {k: v / tot for k, v in cat.items()}
    g = lambda k: f.get(k, 0.0)
    with np.errstate(all="ignore"): return (g("Na2O") + g("K2O") + 2 * g("CaO")) / (g("Al2O3") * g("SiO2"))


def zircon_saturation(zr_melt_ppm, ox, calibration="Watson & Harrison 1983"):
    """T at which the melt is saturated in zircon. D = 497644 / Zr(melt, ppm) (Zr in stoichiometric zircon / Zr in melt).
    Watson & Harrison (1983): ln D = -3.80 - 0.85 (M - 1) + 12900/T.  Boehnke et al. (2013): ln D = 10108/T - 1.16 (M - 1) - 1.48."""
    M = m_factor(ox)
    with np.errstate(all="ignore"):
        lnD = _ln(497644.0 / _a(zr_melt_ppm))
        if calibration.startswith("Boehnke"): return 10108.0 / (lnD + 1.16 * (M - 1) + 1.48) - K0
        return 12900.0 / (lnD + 3.80 + 0.85 * (M - 1)) - K0


# ----------------------------------------------------------------------------- Fe-Mg exchange thermometers
def garnet_biotite(mg_grt, fe_grt, mg_bt, fe_bt, p_kbar):
    """Ferry & Spear (1978): T(K) = (2089 + 0.0096 P(bar)) / (0.782 - ln KD), KD = (Mg/Fe)garnet / (Mg/Fe)biotite."""
    with np.errstate(all="ignore"):
        kd = (_a(mg_grt) / _a(fe_grt)) / (_a(mg_bt) / _a(fe_bt))
        return (2089.0 + 0.0096 * 1000 * _a(p_kbar)) / (0.782 - _ln(kd)) - K0


def garnet_cpx(mg_grt, fe_grt, ca_grt, mn_grt, mg_cpx, fe_cpx, p_kbar):
    """Ellis & Green (1979): T(K) = (3104 XCa(grt) + 3030 + 10.86 P(kbar)) / (ln KD + 1.9034), KD = (Fe/Mg)garnet / (Fe/Mg)cpx,
    XCa = Ca / (Ca + Mg + Fe + Mn) in garnet."""
    with np.errstate(all="ignore"):
        kd = (_a(fe_grt) / _a(mg_grt)) / (_a(fe_cpx) / _a(mg_cpx))
        xca = _a(ca_grt) / (_a(ca_grt) + _a(mg_grt) + _a(fe_grt) + np.nan_to_num(_a(mn_grt)))
        return (3104.0 * xca + 3030.0 + 10.86 * _a(p_kbar)) / (_ln(kd) + 1.9034) - K0


# ----------------------------------------------------------------------------- pyroxene thermometers (apfu on 6 O)
def two_pyroxene_bk(ca_cpx, na_cpx, mg_cpx, fe_cpx, ca_opx, na_opx, mg_opx, fe_opx, p_kbar):
    """Brey & Kohler (1990) two-pyroxene (enstatite-diopside solvus) thermometer:
    T(K) = [23664 + (24.9 + 126.3 XFe(cpx)) P] / [13.38 + (ln K*)^2 + 11.59 XFe(opx)], K* = (1 - Ca*)cpx / (1 - Ca*)opx,
    Ca* = Ca / (1 - Na), XFe = Fe / (Fe + Mg), P in kbar."""
    with np.errstate(all="ignore"):
        cs_c = _a(ca_cpx) / (1 - np.nan_to_num(_a(na_cpx))); cs_o = _a(ca_opx) / (1 - np.nan_to_num(_a(na_opx)))
        k = (1 - cs_c) / (1 - cs_o)
        xfe_c = _a(fe_cpx) / (_a(fe_cpx) + _a(mg_cpx)); xfe_o = _a(fe_opx) / (_a(fe_opx) + _a(mg_opx))
        return (23664.0 + (24.9 + 126.3 * xfe_c) * _a(p_kbar)) / (13.38 + _ln(k) ** 2 + 11.59 * xfe_o) - K0


def a_enstatite(si, al, ti, cr, fe3, fe2, mg, mn, ca, na):
    """Activity of Mg2Si2O6 in a pyroxene (apfu on 6 O) with the ideal two-site model of Wood & Banno (1973): a = XMg(M1) XMg(M2).
    Ca, Na and Mn sit on M2; AlVI = Al - (2 - Si), Fe3+, Ti and Cr on M1; Fe2+ and Mg share the rest of each site in the ratio
    Mg/(Mg + Fe2+). Si left out counts as 2 (no AlIV)."""
    z = lambda v: np.nan_to_num(_a(v))
    si_ = np.where(np.isfinite(_a(si)) & (_a(si) > 0), _a(si), 2.0)  # Si left out (0 or blank): no AlIV
    alvi = np.clip(z(al) - np.clip(2 - _a(si_), 0, None), 0, None)
    with np.errstate(all="ignore"):
        xmg = z(mg) / (z(mg) + z(fe2))
        m2 = np.clip(1 - z(ca) - z(na) - z(mn), 0, None); m1 = np.clip(1 - alvi - z(fe3) - z(ti) - z(cr), 0, None)
        return (xmg * m1) * (xmg * m2)


def _px_k(c, o):
    """K = a(Mg2Si2O6, cpx) / a(Mg2Si2O6, opx) and XFe(opx) = Fe/(Fe + Mg) from two dicts of apfu."""
    k = a_enstatite(**c) / a_enstatite(**o)
    with np.errstate(all="ignore"): return k, np.nan_to_num(_a(o["fe2"])) / (np.nan_to_num(_a(o["fe2"])) + np.nan_to_num(_a(o["mg"])))


def two_pyroxene_wells(c, o):
    """Wells (1977): T(K) = 7341 / (3.355 + 2.44 XFe(opx) - ln K), K = a(En, cpx) / a(En, opx)."""
    k, xfe = _px_k(c, o)
    with np.errstate(all="ignore"): return 7341.0 / (3.355 + 2.44 * xfe - _ln(k)) - K0


def two_pyroxene_wood_banno(c, o):
    """Wood & Banno (1973): T(K) = -10202 / (ln K - 7.65 XFe(opx) + 3.88 XFe(opx)^2 - 4.6), K = a(En, cpx) / a(En, opx)."""
    k, xfe = _px_k(c, o)
    with np.errstate(all="ignore"): return -10202.0 / (_ln(k) - 7.65 * xfe + 3.88 * xfe ** 2 - 4.6) - K0


def ca_in_opx_bk(ca_opx, p_kbar):
    """Brey & Kohler (1990) Ca-in-orthopyroxene thermometer (opx coexisting with cpx): T(K) = (6425 + 26.4 P) / (-ln Ca(opx) + 1.843)."""
    with np.errstate(all="ignore"): return (6425.0 + 26.4 * _a(p_kbar)) / (-_ln(_a(ca_opx)) + 1.843) - K0


# ----------------------------------------------------------------------------- amphibole-plagioclase (Holland & Blundy 1994)
RKJ = R / 1000.0  # kJ mol-1 K-1


def hb_sites(si, al, ti, fe3, fe2, mg, mn, ca, na, k):
    """Site fractions of Holland & Blundy (1994) from amphibole apfu on 23 O (cations as given; Fe3+ can be 0)."""
    si, al, ti, fe3, fe2, mg, mn, ca, na, k = (np.nan_to_num(_a(v)) for v in (si, al, ti, fe3, fe2, mg, mn, ca, na, k))
    cm = np.clip(si + al + ti + fe3 + fe2 + mg + mn - 13.0, 0, None)  # a C-site shortfall (T + C below 13 apfu) puts nothing on M4
    pos = lambda v: np.where(v > 0, v, np.nan)  # a site fraction at or below zero cannot enter a logarithm: blank, not a false T
    return {"XSiT1": pos((si - 4) / 4), "XAlT1": pos((8 - si) / 4), "XAlM2": np.clip((al + si - 8) / 2, 0, 1), "XKA": k, "XvA": pos(3 - ca - na - k - cm),
            "XNaA": pos(ca + na + cm - 2), "XNaM4": pos((2 - ca - cm) / 2), "XCaM4": ca / 2}


def _an_fraction(an):
    a = _a(an); return np.where(a > 1, a / 100.0, a)  # accepts An as a fraction or in %


def holland_blundy_a(si, al, ti, fe3, fe2, mg, mn, ca, na, k, an_plag, p_kbar):
    """Holland & Blundy (1994, p. 441) thermometer A, edenite + 4 quartz = tremolite + albite (quartz-bearing rocks):
    T(K) = [-76.95 + 0.79P + Yab + 39.4 XNa(A) + 22.4 XK(A) + (41.5 - 2.89P) XAl(M2)] /
           [-0.0650 - R ln(27 Xv(A) XSi(T1) XAb(plag) / (256 XNa(A) XAl(T1)))], P in kbar, energies in kJ;
    Yab = 0 for XAb > 0.5, otherwise 12.0 (1 - XAb)^2 - 3.0."""
    s = hb_sites(si, al, ti, fe3, fe2, mg, mn, ca, na, k); xan = _an_fraction(an_plag); xab = 1 - xan; P = _a(p_kbar)
    yab = np.where(xab > 0.5, 0.0, 12.0 * (1 - xab) ** 2 - 3.0)
    with np.errstate(all="ignore"):
        q = 27 * s["XvA"] * s["XSiT1"] * xab / (256 * s["XNaA"] * s["XAlT1"])  # albite is the product of reaction A
        return (-76.95 + 0.79 * P + yab + 39.4 * s["XNaA"] + 22.4 * s["XKA"] + (41.5 - 2.89 * P) * s["XAlM2"]) / \
            (-0.0650 - RKJ * _ln(q)) - K0


def holland_blundy_b(si, al, ti, fe3, fe2, mg, mn, ca, na, k, an_plag, p_kbar):
    """Holland & Blundy (1994) thermometer B, edenite + albite = richterite + anorthite (quartz-bearing or quartz-free):
    T(K) = [78.44 + Yab-an - 33.6 XNa(M4) - (66.8 - 2.92P) XAl(M2) + 78.5 XAl(T1) + 9.4 XNa(A)] /
           [0.0721 - R ln(27 XNa(M4) XSi(T1) XAn(plag) / (64 XCa(M4) XAl(T1) XAb(plag)))];
    Yab-an = 3.0 for XAb > 0.5, otherwise 12.0 (2 XAb - 1) + 3.0."""
    s = hb_sites(si, al, ti, fe3, fe2, mg, mn, ca, na, k); xan = _an_fraction(an_plag); xab = 1 - xan; P = _a(p_kbar)
    yaban = np.where(xab > 0.5, 3.0, 12.0 * (2 * xab - 1) + 3.0)
    with np.errstate(all="ignore"):
        q = 27 * s["XNaM4"] * s["XSiT1"] * xan / (64 * s["XCaM4"] * s["XAlT1"] * xab)
        return (78.44 + yaban - 33.6 * s["XNaM4"] - (66.8 - 2.92 * P) * s["XAlM2"] + 78.5 * s["XAlT1"] + 9.4 * s["XNaA"]) / \
            (0.0721 - RKJ * _ln(q)) - K0


# ----------------------------------------------------------------------------- garnet-orthopyroxene Al barometers
R_CAL = 1.9872  # cal mol-1 K-1


def _z(v): return np.nan_to_num(_a(v))


def gt_sites(ca, mg, fe, mn=0.0, al=0.0, cr=0.0, mn_in_sum=True):
    """Garnet mole fractions: XCa, XFe, XMg over Ca + Mg + Fe (+ Mn), XAl and XCr over Al + Cr."""
    s = _z(ca) + _z(mg) + _z(fe) + (_z(mn) if mn_in_sum else 0)
    with np.errstate(all="ignore"):
        alcr = _z(al) + _z(cr); xal = np.where(alcr > 0, _z(al) / np.where(alcr > 0, alcr, 1), 1.0)
        return _z(ca) / s, _z(fe) / s, _z(mg) / s, xal, 1 - xal


def harley_green_1982(al_opx, mg_opx, fe_opx, ca_gt, mg_gt, fe_gt, t_c):
    """Harley & Green (1982, Nature 300, eq. 5), P in kbar:
    P = (1/dV)[(R ln K - 2.93)T + 5650 + 5157(1 - XAl)(1 - 2XAl)XFe(opx) - 6300(XCa XFe + XCa^2)],
    K = XAl(1 - XAl)/(1 - XCa)^3, dV = -[183.3 + 178.98 XAl(1 - XAl)] cal/kbar, XAl = Al/2 (opx, 6 O), XFe(opx) = Fe/(Fe + Mg),
    XCa = Ca/(Ca + Mg + Fe) and XFe = Fe/(Ca + Mg + Fe) in garnet; R in cal."""
    T = _a(t_c) + K0; xal = _z(al_opx) / 2
    with np.errstate(all="ignore"):
        xfe_o = _z(fe_opx) / (_z(fe_opx) + _z(mg_opx)); xca, xfe, _, _, _ = gt_sites(ca_gt, mg_gt, fe_gt, mn_in_sum=False)
        k = xal * (1 - xal) / (1 - xca) ** 3; dv = -(183.3 + 178.98 * xal * (1 - xal))
        return ((R_CAL * _ln(k) - 2.93) * T + 5650 + 5157 * (1 - xal) * (1 - 2 * xal) * xfe_o - 6300 * (xca * xfe + xca ** 2)) / dv


def _opx_ng(al, cr, ti, na, ca, mn, mg, fe):
    """Orthopyroxene site fractions of Nickel & Green (1985), apfu on 6 O."""
    xal = (_z(al) - _z(cr) - 2 * _z(ti) + _z(na)) / 2
    m1 = 1 - xal - _z(cr) - _z(ti); m2 = 1 - _z(ca) - _z(na) - _z(mn)
    with np.errstate(all="ignore"): xmf = _z(mg) / (_z(mg) + _z(fe))
    return xal, m1, m2, m1 * xmf, m1 * (1 - xmf)


def nickel_green_1985(opx, gt, t_c):
    """Nickel & Green (1985, EPSL 73, eq. 5), P in kbar (R and energies in cal):
    P = -1/[183.3 + 178.98 XAl(1 - XAl)] {-RT ln[(1 - XCa)^3 XAl(gt)^2 / (XMgFe(M1) XMgFe(M2)^2 XAl(M1))] - 9000 XCa^2
        - 3400[2 XCr(gt)^2 - XMg(M1) XCr(M1)] - XCa XCr(90853 - 52.1T) - 7590 XFe XCa + 5157 XMg(M1) XFe(M1) + 6047 - 3.23T}."""
    T = _a(t_c) + K0
    xal, m1, m2, xmg1, xfe1 = _opx_ng(opx["al"], opx["cr"], opx["ti"], opx["na"], opx["ca"], opx["mn"], opx["mg"], opx["fe"])
    xca, xfe, _, xalg, xcrg = gt_sites(gt["ca"], gt["mg"], gt["fe"], gt["mn"], gt["al"], gt["cr"])
    with np.errstate(all="ignore"):
        lnk = _ln((1 - xca) ** 3 * xalg ** 2 / (m1 * m2 ** 2 * xal))
        brace = (-R_CAL * T * lnk - 9000 * xca ** 2 - 3400 * (2 * xcrg ** 2 - xmg1 * _z(opx["cr"])) - xca * xcrg * (90853 - 52.1 * T)
                 - 7590 * xfe * xca + 5157 * xmg1 * xfe1 + 6047 - 3.23 * T)
        return brace / -(183.3 + 178.98 * xal * (1 - xal))


def brey_kohler_1990_p(opx, gt, t_c):
    """Brey & Kohler (1990, J Petrol 31, Table 3) Al-in-opx barometer P(BKN) in kbar: P = [-C2 - sqrt(C2^2 + 4 C3 C1/1000)] / (2 C3),
    with C1, C2, C3 and the site occupancies exactly as in Table 3 (R = 8.3143 J/K mol)."""
    T = _a(t_c) + K0
    al, cr, ti, fe3, na, ca, mn, mg, fe = (_z(opx[k]) for k in ("al", "cr", "ti", "fe3", "na", "ca", "mn", "mg", "fe"))
    xal = (al + na - cr - fe3 - 2 * ti) / 2
    jd = na - cr - fe3 - 2 * ti
    xal_ts = np.where(jd < 0, (al + jd) / 2, (al - jd) / 2)
    m1 = 1 - xal - cr - fe3 - ti; m2 = 1 - ca - na - mn
    with np.errstate(all="ignore"):
        xmf = mg / (mg + fe); xmg1, xfe1 = m1 * xmf, m1 * (1 - xmf)
        xca, xfe, _, xalg, xcrg = gt_sites(gt["ca"], gt["mg"], gt["fe"], gt["mn"], gt["al"], gt["cr"])
        kd = (1 - xca) ** 3 * xalg ** 2 / (m1 * m2 ** 2 * xal_ts)
        c1 = (-R * T * _ln(kd) - 5510 + 88.91 * T - 19 * T ** 1.2 + 3 * xca ** 2 * 82458 + xmg1 * xfe1 * (80942 - 46.7 * T)
              - 3 * xfe * xca * 17793 - xca * xcrg * (1.164e6 - 420.4 * T) - xfe * xcrg * (-1.25e6 + 565 * T))
        c2 = -0.832 - 8.78e-5 * (T - 298) + 3 * xca ** 2 * 3.305 - xca * xcrg * 13.45 + xfe * xcrg * 10.5
        c3 = 16.6e-4
        return (-c2 - np.sqrt(c2 ** 2 + 4 * c3 * c1 / 1000)) / (2 * c3)


# ----------------------------------------------------------------------------- Al-in-hornblende barometers (Al total, apfu on 23 O)
AL_HBL = {
    "Hammarstrom & Zen 1986": (lambda al: -3.92 + 5.03 * al, "P = -3.92 + 5.03 Al"),
    "Hollister et al. 1987": (lambda al: -4.76 + 5.64 * al, "P = -4.76 + 5.64 Al"),
    "Johnson & Rutherford 1989": (lambda al: -3.46 + 4.23 * al, "P = -3.46 + 4.23 Al"),
    "Schmidt 1992": (lambda al: -3.01 + 4.76 * al, "P = -3.01 + 4.76 Al"),
    "Mutch et al. 2016": (lambda al: 0.5 + 0.331 * al + 0.995 * al ** 2, "P = 0.5 + 0.331 Al + 0.995 Al^2"),
}


def al_in_hornblende(al_tot, calibration="Schmidt 1992"):
    """Pressure in kbar from total Al (apfu, 23 O) of igneous hornblende in the buffering assemblage
    (hornblende + plagioclase + K-feldspar + quartz + biotite + titanite + Fe-Ti oxide)."""
    return AL_HBL[calibration][0](_a(al_tot))


# ----------------------------------------------------------------------------- the menu: inputs, equations and references
# input kinds: ("col", label, name pattern), ("num", label, default), ("choice", label, options)
METHODS = {
    "Ti-in-zircon (Ferry & Watson 2007)": {
        "out": "T Ti-in-Zrn", "unit": "deg C", "fn": lambda v: ti_in_zircon(v["Ti (ppm)"], v["a SiO2"], v["a TiO2"]),
        "inputs": [("col", "Ti (ppm)", r"Ti(?!O)"), ("num", "a SiO2", 1.0), ("num", "a TiO2", 1.0)],
        "eq": "log Ti(ppm) = 5.711 - 4800/T(K) - log aSiO2 + log aTiO2", "ref": "Ferry & Watson (2007) Contrib Mineral Petrol 154, 429-437; "
        "Watson et al. (2006) Contrib Mineral Petrol 151, 413-433", "note": "Zircon in equilibrium with rutile has aTiO2 = 1; typical "
        "granitic melts aTiO2 0.5-0.8, quartz-saturated aSiO2 = 1."},
    "Zr-in-rutile (Ferry & Watson 2007)": {
        "out": "T Zr-in-Rt", "unit": "deg C", "fn": lambda v: zr_in_rutile(v["Zr (ppm)"], v["a SiO2"]),
        "inputs": [("col", "Zr (ppm)", r"Zr(?!n|c|O)"), ("num", "a SiO2", 1.0)],
        "eq": "log Zr(ppm) = 7.420 - 4530/T(K) - log aSiO2", "ref": "Ferry & Watson (2007) Contrib Mineral Petrol 154, 429-437",
        "note": "For rutile with zircon and quartz. No pressure term (Tomkins et al. 2007 add one)."},
    "Zr-in-rutile (Watson et al. 2006)": {
        "out": "T Zr-in-Rt (W06)", "unit": "deg C", "fn": lambda v: zr_in_rutile_watson2006(v["Zr (ppm)"]),
        "inputs": [("col", "Zr (ppm)", r"Zr(?!n|c|O)")], "eq": "log Zr(ppm) = 7.36 - 4470/T(K)",
        "ref": "Watson et al. (2006) Contrib Mineral Petrol 151, 413-433", "note": "Rutile with zircon and quartz."},
    "Zr-in-titanite (Hayden et al. 2008)": {
        "out": "T Zr-in-Ttn", "unit": "deg C", "fn": lambda v: zr_in_titanite_hayden2008(v["Zr (ppm)"], v["P (kbar)"], v["a TiO2"], v["a SiO2"]),
        "inputs": [("col", "Zr (ppm)", r"Zr(?!n|c|O)"), ("num", "P (kbar)", 5.0), ("num", "a TiO2", 1.0), ("num", "a SiO2", 1.0)],
        "eq": "log Zr(ppm) = 10.52 - 7708/T(K) - 960 P(GPa)/T - log aTiO2 - log aSiO2",
        "ref": "Hayden, Watson & Wark (2008) Contrib Mineral Petrol 155, 529-540",
        "note": "Titanite with rutile and quartz (activities 1); otherwise give aTiO2 (often 0.6-0.9) and aSiO2. 1 kbar changes T by about 5 deg C."},
    "Ti-in-quartz (Thomas et al. 2010)": {
        "out": "T TitaniQ", "unit": "deg C", "fn": lambda v: ti_in_quartz_thomas2010(v["Ti (ppm)"], v["P (kbar)"], v["a TiO2"]),
        "inputs": [("col", "Ti (ppm)", r"Ti(?!O)"), ("num", "P (kbar)", 5.0), ("num", "a TiO2", 1.0)],
        "eq": "RT ln X(TiO2) = -60952 + 1.520 T - 1741 P(kbar) + RT ln aTiO2", "ref": "Thomas et al. (2010) Contrib Mineral Petrol 160, 743-759",
        "note": "Pressure must be known independently; 1 kbar changes T by about 20-25 deg C."},
    "Zircon oxybarometer dFMQ (Loucks et al. 2020)": {
        "out": "dFMQ zircon", "unit": "log units", "fn": lambda v: zircon_dfmq_loucks2020(v["Ce (ppm)"], v["U (ppm)"], v["Ti (ppm)"], v["Age (Ma)"]),
        "inputs": [("col", "Ce (ppm)", r"Ce(?![A-Za-z0-9])"), ("col", "U (ppm)", r"U(?![A-Za-z0-9])"), ("col", "Ti (ppm)", r"Ti(?!O)"), ("num", "Age (Ma)", 0.0)],
        "eq": "dFMQ = 3.998 log10[Ce / sqrt(Ui x Ti)] + 2.284", "ref": "Loucks, Fiorentini & Henriquez (2020) J Petrol 61, egaa034",
        "note": "Zircon Ce, U and Ti in ppm; the age turns measured U into U at crystallisation (0 for young zircon). Calibrated on zircon "
                "from intermediate to felsic magmas; see the paper for its uncertainty."},
    "Ti-in-quartz (Wark & Watson 2006)": {
        "out": "T TitaniQ (WW06)", "unit": "deg C", "fn": lambda v: ti_in_quartz_wark2006(v["Ti (ppm)"]),
        "inputs": [("col", "Ti (ppm)", r"Ti(?!O)")], "eq": "log Ti(ppm) = 5.69 - 3765/T(K)",
        "ref": "Wark & Watson (2006) Contrib Mineral Petrol 152, 743-754", "note": "No pressure term (about 10 kbar experiments); aTiO2 = 1."},
    "Zircon saturation (Watson & Harrison 1983)": {
        "out": "T Zr-sat", "unit": "deg C", "fn": lambda v: zircon_saturation(v["Zr (ppm)"], v["oxides"]),
        "inputs": [("col", "Zr (ppm)", r"Zr(?!n|c|O)"), ("oxides", "Major oxides (wt%)", None)],
        "eq": "ln D = -3.80 - 0.85 (M - 1) + 12900/T(K), D = 497644/Zr(melt), M = (Na + K + 2Ca)/(Al Si)",
        "ref": "Watson & Harrison (1983) Earth Planet Sci Lett 64, 295-304", "note": "Whole-rock Zr gives a maximum (inherited zircon) "
        "or minimum (undersaturated melt) temperature; calibrated for M = 0.9-1.7."},
    "Zircon saturation (Boehnke et al. 2013)": {
        "out": "T Zr-sat (B13)", "unit": "deg C", "fn": lambda v: zircon_saturation(v["Zr (ppm)"], v["oxides"], "Boehnke"),
        "inputs": [("col", "Zr (ppm)", r"Zr(?!n|c|O)"), ("oxides", "Major oxides (wt%)", None)],
        "eq": "ln D = 10108/T(K) - 1.16 (M - 1) - 1.48", "ref": "Boehnke et al. (2013) Chem Geol 351, 324-334", "note": "Recalibration of "
        "Watson & Harrison (1983)."},
    "Garnet-biotite Fe-Mg (Ferry & Spear 1978)": {
        "out": "T Grt-Bt", "unit": "deg C", "fn": lambda v: garnet_biotite(v["Garnet Mg"], v["Garnet Fe"], v["Biotite Mg"], v["Biotite Fe"], v["P (kbar)"]),
        "inputs": [("col", "Garnet Mg", r".*(grt|garnet).*mg|mg.*(grt|garnet)"), ("col", "Garnet Fe", r".*(grt|garnet).*fe|fe.*(grt|garnet)"),
                   ("col", "Biotite Mg", r".*(bt|biotite).*mg|mg.*(bt|biotite)"), ("col", "Biotite Fe", r".*(bt|biotite).*fe|fe.*(bt|biotite)"),
                   ("num", "P (kbar)", 5.0)],
        "eq": "T(K) = (2089 + 0.0096 P(bar)) / (0.782 - ln KD), KD = (Mg/Fe)Grt / (Mg/Fe)Bt", "ref": "Ferry & Spear (1978) Contrib Mineral "
        "Petrol 66, 113-117", "note": "Mg and Fe as apfu (or mol); for garnet poor in Ca and Mn and biotite poor in Ti and AlVI."},
    "Garnet-clinopyroxene Fe-Mg (Ellis & Green 1979)": {
        "out": "T Grt-Cpx", "unit": "deg C",
        "fn": lambda v: garnet_cpx(v["Garnet Mg"], v["Garnet Fe"], v["Garnet Ca"], v["Garnet Mn"], v["Cpx Mg"], v["Cpx Fe"], v["P (kbar)"]),
        "inputs": [("col", "Garnet Mg", r".*(grt|garnet).*mg|mg.*(grt|garnet)"), ("col", "Garnet Fe", r".*(grt|garnet).*fe|fe.*(grt|garnet)"),
                   ("col", "Garnet Ca", r".*(grt|garnet).*ca|ca.*(grt|garnet)"), ("col", "Garnet Mn", r".*(grt|garnet).*mn|mn.*(grt|garnet)"),
                   ("col", "Cpx Mg", r".*(cpx|pyroxene).*mg|mg.*(cpx|pyroxene)"), ("col", "Cpx Fe", r".*(cpx|pyroxene).*fe|fe.*(cpx|pyroxene)"),
                   ("num", "P (kbar)", 15.0)],
        "eq": "T(K) = (3104 XCa(Grt) + 3030 + 10.86 P(kbar)) / (ln KD + 1.9034), KD = (Fe/Mg)Grt / (Fe/Mg)Cpx",
        "ref": "Ellis & Green (1979) Contrib Mineral Petrol 71, 13-22", "note": "All Fe as Fe2+ (Fe3+ in cpx raises T); eclogites and granulites."},
}
_AMPH_IN = [("col", "Si (apfu)", r"^Si\s*\(apfu\)|^Si$"), ("col", "Al (apfu)", r"^Al\s*\(apfu\)|^Al$"),
                   ("colopt", "Ti (apfu)", r"^Ti\s*\(apfu\)"), ("colopt", "Fe3+ (apfu)", r"^Fe3\+\s*\(apfu\)"),
                   ("col", "Fe2+ (apfu)", r"^Fe2\+\s*\(apfu\)|^Fe\s*\(apfu\)"), ("col", "Mg (apfu)", r"^Mg\s*\(apfu\)|^Mg$"),
                   ("colopt", "Mn (apfu)", r"^Mn\s*\(apfu\)"), ("col", "Ca (apfu)", r"^Ca\s*\(apfu\)|^Ca$"),
                   ("col", "Na (apfu)", r"^Na\s*\(apfu\)|^Na$"), ("colopt", "K (apfu)", r"^K\s*\(apfu\)|^K$"),
                   ("col", "Plagioclase An (fraction or %)", r"^An\b|Plag.*An|An.*plag|^XAn"), ("num", "P (kbar)", 5.0)]
_hb = lambda f: (lambda v: f(v["Si (apfu)"], v["Al (apfu)"], v["Ti (apfu)"], v["Fe3+ (apfu)"], v["Fe2+ (apfu)"], v["Mg (apfu)"], v["Mn (apfu)"],
                             v["Ca (apfu)"], v["Na (apfu)"], v["K (apfu)"], v["Plagioclase An (fraction or %)"], v["P (kbar)"]))
_HB_NOTE = ("Amphibole apfu on 23 O (Mineral Formula from Oxides: Amphibole, with the Holland & Blundy (1994) Fe3+ scheme of their "
            "Appendix B, which the calibration was made with) and the An content of plagioclase touching it. Calibrated for 400-1000 deg C, 1-15 kbar, plagioclase An < 92, "
            "amphibole Si < 7.8; A and B normally agree within about 40 deg C.")
METHODS["Amphibole-plagioclase A, edenite-tremolite (Holland & Blundy 1994)"] = {
    "out": "T Hbl-Pl (A)", "unit": "deg C", "fn": _hb(holland_blundy_a), "inputs": _AMPH_IN,
    "eq": "T = [-76.95 + 0.79P + Yab + 39.4 XNa(A) + 22.4 XK(A) + (41.5 - 2.89P) XAl(M2)] / [-0.0650 - R ln(27 Xv(A) XSi(T1) XAb / (256 XNa(A) XAl(T1)))]",
    "ref": "Holland & Blundy (1994) Contrib Mineral Petrol 116, 433-447", "note": "Quartz-bearing rocks only. " + _HB_NOTE}
METHODS["Amphibole-plagioclase B, edenite-richterite (Holland & Blundy 1994)"] = {
    "out": "T Hbl-Pl (B)", "unit": "deg C", "fn": _hb(holland_blundy_b), "inputs": _AMPH_IN,
    "eq": "T = [78.44 + Yab-an - 33.6 XNa(M4) - (66.8 - 2.92P) XAl(M2) + 78.5 XAl(T1) + 9.4 XNa(A)] / [0.0721 - R ln(27 XNa(M4) XSi(T1) XAn / (64 XCa(M4) XAl(T1) XAb))]",
    "ref": "Holland & Blundy (1994) Contrib Mineral Petrol 116, 433-447", "note": "Quartz-bearing or quartz-free rocks. " + _HB_NOTE}
_PX_IN = [("col", "Cpx Ca", r".*(cpx|clinopyroxene).*ca|^ca.*(cpx|clinopyroxene)"), ("colopt", "Cpx Na", r".*(cpx|clinopyroxene).*na|^na.*(cpx|clinopyroxene)"),
          ("col", "Cpx Mg", r".*(cpx|clinopyroxene).*mg|^mg.*(cpx|clinopyroxene)"), ("col", "Cpx Fe", r".*(cpx|clinopyroxene).*fe|^fe.*(cpx|clinopyroxene)"),
          ("col", "Opx Ca", r".*(opx|orthopyroxene).*ca|^ca.*(opx|orthopyroxene)"), ("colopt", "Opx Na", r".*(opx|orthopyroxene).*na|^na.*(opx|orthopyroxene)"),
          ("col", "Opx Mg", r".*(opx|orthopyroxene).*mg|^mg.*(opx|orthopyroxene)"), ("col", "Opx Fe", r".*(opx|orthopyroxene).*fe|^fe.*(opx|orthopyroxene)"),
          ("num", "P (kbar)", 15.0)]
METHODS["Two-pyroxene (Brey & Kohler 1990)"] = {
    "out": "T 2Px (BKN)", "unit": "deg C",
    "fn": lambda v: two_pyroxene_bk(v["Cpx Ca"], v["Cpx Na"], v["Cpx Mg"], v["Cpx Fe"], v["Opx Ca"], v["Opx Na"], v["Opx Mg"], v["Opx Fe"], v["P (kbar)"]),
    "inputs": _PX_IN, "eq": "T = [23664 + (24.9 + 126.3 XFe(cpx)) P] / [13.38 + (ln K*)^2 + 11.59 XFe(opx)], K* = (1 - Ca*)cpx/(1 - Ca*)opx, Ca* = Ca/(1 - Na)",
    "ref": "Brey & Kohler (1990) J Petrol 31, 1353-1378", "note": "Coexisting cpx and opx, apfu on 6 O (all Fe as Fe2+); calibrated on "
    "lherzolites at 900-1400 deg C and 10-60 kbar; also used for granulites."}
_SITES = [("Si", r"si"), ("Al", r"al"), ("Ti", r"ti"), ("Cr", r"cr"), ("Fe3+", r"fe3"), ("Fe", r"fe(?!3)"), ("Mg", r"mg"), ("Mn", r"mn"), ("Ca", r"ca"),
          ("Na", r"na")]
_OPT = {"Si", "Al", "Ti", "Cr", "Fe3+", "Mn", "Na"}
_PX_SITE_IN = [("colopt" if el in _OPT else "col", f"{px} {el}", rf".*({px.lower()}|{'clino' if px == 'Cpx' else 'ortho'}pyroxene).*\b{pat}|^{pat}.*({px.lower()})")
               for px in ("Cpx", "Opx") for el, pat in _SITES]
_KEYS = {"Si": "si", "Al": "al", "Ti": "ti", "Cr": "cr", "Fe3+": "fe3", "Fe": "fe2", "Mg": "mg", "Mn": "mn", "Ca": "ca", "Na": "na"}
_px = lambda f: (lambda v: f({_KEYS[el]: v[f"Cpx {el}"] for el, _ in _SITES}, {_KEYS[el]: v[f"Opx {el}"] for el, _ in _SITES}))
_WB_NOTE = ("Coexisting cpx and opx, apfu on 6 O. Activities from the ideal two-site model of Wood & Banno (1973): Ca, Na, Mn on M2; "
            "AlVI, Fe3+, Ti, Cr on M1; Fe2+ and Mg share the rest. Optional columns left out count as 0 (Si as 2). No pressure term. "
            "Wells (1977) usually gives higher temperatures than Brey & Kohler (1990).")
METHODS["Two-pyroxene (Wells 1977)"] = {
    "out": "T 2Px (Wells)", "unit": "deg C", "fn": _px(two_pyroxene_wells), "inputs": _PX_SITE_IN,
    "eq": "T = 7341 / (3.355 + 2.44 XFe(opx) - ln K), K = a(En)cpx / a(En)opx, a(En) = XMg(M1) XMg(M2)",
    "ref": "Wells (1977) Contrib Mineral Petrol 62, 129-139", "note": _WB_NOTE}
METHODS["Two-pyroxene (Wood & Banno 1973)"] = {
    "out": "T 2Px (W&B)", "unit": "deg C", "fn": _px(two_pyroxene_wood_banno), "inputs": _PX_SITE_IN,
    "eq": "T = -10202 / (ln K - 7.65 XFe(opx) + 3.88 XFe(opx)^2 - 4.6), K = a(En)cpx / a(En)opx",
    "ref": "Wood & Banno (1973) Contrib Mineral Petrol 42, 109-124", "note": _WB_NOTE}
METHODS["Ca-in-orthopyroxene (Brey & Kohler 1990)"] = {
    "out": "T Ca-in-Opx", "unit": "deg C", "fn": lambda v: ca_in_opx_bk(v["Opx Ca"], v["P (kbar)"]),
    "inputs": [("col", "Opx Ca", r".*(opx|orthopyroxene).*ca|^ca.*(opx|orthopyroxene)"), ("num", "P (kbar)", 15.0)],
    "eq": "T = (6425 + 26.4 P) / (-ln Ca(opx) + 1.843)", "ref": "Brey & Kohler (1990) J Petrol 31, 1353-1378",
    "note": "Orthopyroxene coexisting with clinopyroxene, Ca apfu on 6 O."}
_T_IN = [("colopt", "T (C) column", r"^T\b|temp"), ("num", "T (C), if no column", 900.0)]
_OPX_GT = [("col", "Opx Al", r".*(opx|orthopyroxene).*\bal|^al.*(opx|orthopyroxene)"), ("colopt", "Opx Cr", r".*(opx|orthopyroxene).*\bcr|^cr.*(opx|orthopyroxene)"),
           ("colopt", "Opx Ti", r".*(opx|orthopyroxene).*\bti|^ti.*(opx|orthopyroxene)"), ("colopt", "Opx Fe3+", r".*(opx|orthopyroxene).*fe3|^fe3.*(opx|orthopyroxene)"),
           ("colopt", "Opx Na", r".*(opx|orthopyroxene).*\bna|^na.*(opx|orthopyroxene)"), ("colopt", "Opx Ca", r".*(opx|orthopyroxene).*\bca|^ca.*(opx|orthopyroxene)"),
           ("colopt", "Opx Mn", r".*(opx|orthopyroxene).*\bmn|^mn.*(opx|orthopyroxene)"), ("col", "Opx Mg", r".*(opx|orthopyroxene).*\bmg|^mg.*(opx|orthopyroxene)"),
           ("col", "Opx Fe", r".*(opx|orthopyroxene).*\bfe(?!3)|^fe(?!3).*(opx|orthopyroxene)"),
           ("col", "Garnet Ca", r".*(grt|garnet|gt).*\bca|^ca.*(grt|garnet)"), ("col", "Garnet Mg", r".*(grt|garnet|gt).*\bmg|^mg.*(grt|garnet)"),
           ("col", "Garnet Fe", r".*(grt|garnet|gt).*\bfe(?!3)|^fe(?!3).*(grt|garnet)"), ("colopt", "Garnet Mn", r".*(grt|garnet|gt).*\bmn|^mn.*(grt|garnet)"),
           ("colopt", "Garnet Al", r".*(grt|garnet|gt).*\bal|^al.*(grt|garnet)"), ("colopt", "Garnet Cr", r".*(grt|garnet|gt).*\bcr|^cr.*(grt|garnet)")] + _T_IN


def _t(v):
    """Temperature from the T column, or the single value when no column was chosen (an optional column left out arrives as 0)."""
    t = v["T (C) column"]
    return v["T (C), if no column"] if np.ndim(t) == 0 and float(t) == 0.0 else t


def _og(v):
    opx = {k: v[f"Opx {n}"] for k, n in (("al", "Al"), ("cr", "Cr"), ("ti", "Ti"), ("fe3", "Fe3+"), ("na", "Na"), ("ca", "Ca"), ("mn", "Mn"), ("mg", "Mg"), ("fe", "Fe"))}
    gt = {k: v[f"Garnet {n}"] for k, n in (("ca", "Ca"), ("mg", "Mg"), ("fe", "Fe"), ("mn", "Mn"), ("al", "Al"), ("cr", "Cr"))}
    return opx, gt, _t(v)


_OG_NOTE = ("Orthopyroxene apfu on 6 O and garnet apfu on 12 O; the temperature comes from a column (e.g. one made with the two-pyroxene "
            "or Ca-in-opx thermometer) or one value for every row. Optional columns left out count as 0 (garnet Al with no Cr as Al only).")
METHODS["Garnet-orthopyroxene Al (Harley & Green 1982)"] = {
    "out": "P Grt-Opx (HG82)", "unit": "kbar",
    "fn": lambda v: harley_green_1982(v["Opx Al"], v["Opx Mg"], v["Opx Fe"], v["Garnet Ca"], v["Garnet Mg"], v["Garnet Fe"], _t(v)),
    "inputs": [i for i in _OPX_GT if i[1] in ("Opx Al", "Opx Mg", "Opx Fe", "Garnet Ca", "Garnet Mg", "Garnet Fe")] + _T_IN,
    "eq": "P = (1/dV)[(R ln K - 2.93)T + 5650 + 5157(1 - XAl)(1 - 2XAl)XFe(opx) - 6300(XCa XFe + XCa^2)], K = XAl(1 - XAl)/(1 - XCa)^3, "
          "dV = -[183.3 + 178.98 XAl(1 - XAl)] cal/kbar, XAl = Al(opx)/2",
    "ref": "Harley & Green (1982) Nature 300, 697-701", "note": "Granulites and low-Cr garnet peridotites; not for Fe3+-, Cr- or Mn-rich "
    "phases or very low Al in opx; dP/dT of the Al isopleths is about 4 kbar per 100 deg C, so T must be known well. " + _OG_NOTE}
METHODS["Garnet-orthopyroxene Al (Nickel & Green 1985)"] = {
    "out": "P Grt-Opx (NG85)", "unit": "kbar", "fn": lambda v: nickel_green_1985(*_og(v)), "inputs": _OPX_GT,
    "eq": "P = -1/[183.3 + 178.98 XAl(1 - XAl)] {-RT ln KD - 9000 XCa^2 - 3400[2 XCr(gt)^2 - XMg(M1) XCr(M1)] - XCa XCr(90853 - 52.1T) "
          "- 7590 XFe XCa + 5157 XMg(M1) XFe(M1) + 6047 - 3.23T}",
    "ref": "Nickel & Green (1985) Earth Planet Sci Lett 73, 158-170", "note": "Garnet peridotites, including Cr-bearing ones. " + _OG_NOTE}
METHODS["Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)"] = {
    "out": "P Grt-Opx (BKN)", "unit": "kbar", "fn": lambda v: brey_kohler_1990_p(*_og(v)), "inputs": _OPX_GT,
    "eq": "P = [-C2 - sqrt(C2^2 + 4 C3 C1/1000)] / (2 C3), C1, C2, C3 and KD as in Table 3",
    "ref": "Brey & Kohler (1990) J Petrol 31, 1353-1378 (Table 3)", "note": "Four-phase garnet lherzolites; with TBKN it reproduces "
    "the experiments to +-20 deg C and +-3 kbar. " + _OG_NOTE}
for _cal, (_f, _eq) in AL_HBL.items():
    METHODS[f"Al-in-hornblende ({_cal})"] = {
        "out": f"P Al-in-Hbl ({_cal.split(' ')[0]})", "unit": "kbar", "fn": (lambda c: (lambda v: al_in_hornblende(v["Al total (apfu)"], c)))(_cal),
        "inputs": [("col", "Al total (apfu)", r"Al\s*\(apfu\)|Al(tot|_tot| tot)|^Al$")], "eq": _eq + " (Al total, apfu on 23 O)",
        "ref": {"Hammarstrom & Zen 1986": "Hammarstrom & Zen (1986) Am Mineral 71, 1297-1313", "Hollister et al. 1987": "Hollister et al. (1987) "
                "Am Mineral 72, 231-239", "Johnson & Rutherford 1989": "Johnson & Rutherford (1989) Geology 17, 837-841",
                "Schmidt 1992": "Schmidt (1992) Contrib Mineral Petrol 110, 304-310", "Mutch et al. 2016": "Mutch et al. (2016) Contrib "
                "Mineral Petrol 171, 85"}[_cal],
        "note": "Only for calc-alkaline granitoids with the full buffering assemblage (Hbl + Pl + Kfs + Qz + Bt + Ttn + Fe-Ti oxide), "
                "near-solidus rims; use the mineral formula command (Amphibole, 23 O) to get Al total."}


def guess_column(columns, pattern):
    """The first column whose name matches the input's pattern (any case), else None."""
    import re
    for c in columns:
        if re.match(pattern, str(c).strip(), re.I) or re.search(pattern, str(c), re.I) and "|" in pattern: return c
    return None


def compute(method, columns, sheet_arr, sheet_oxides, n_rows=None):
    """Run one method. columns: {input label: column name or number}; sheet_arr(name) -> numbers; sheet_oxides() -> {oxide: wt%}.
    Optional columns ('colopt') left out count as 0 (e.g. no Fe3+ or no Na)."""
    m = METHODS[method]; v = {}
    for kind, label, extra in m["inputs"]:
        if kind == "col":
            c = columns.get(label)
            if c is None: raise ValueError(f"Choose the column for {label}.")
            v[label] = sheet_arr(c)
        elif kind == "colopt":
            c = columns.get(label); v[label] = sheet_arr(c) if c is not None else 0.0
        elif kind == "num": v[label] = np.asarray(columns.get(label, extra), float)  # one number, or one per row from the P-T solver
        elif kind == "phase":  # all oxide columns of one phase (liquid, clinopyroxene), found by name
            v[label] = sheet_oxides(extra)
            if "SiO2" not in v[label]: raise ValueError(f"No {label.lower()} found: name the columns SiO2, Al2O3 ... (liquid) or Cpx SiO2, Cpx Al2O3 ...")
        elif kind == "oxides":
            v["oxides"] = sheet_oxides()
            if not {"SiO2", "Al2O3", "CaO", "Na2O", "K2O"} <= set(v["oxides"]): raise ValueError("Zircon saturation needs the major-oxide columns.")
    return np.asarray(m["fn"](v), float)


_MINERAL = r"(?<![a-z])(ol|olv|olivine|cpx|clinopyroxene|opx|orthopyroxene|pl|plg|plag|plagioclase|grt|garnet|gt|sp|spl|spinel|bt|biotite|hbl|amph|amphibole|mt|ilm|fsp)(?![a-z])"
_LIQUID = r"(?<![a-z])(liq|liquid|melt|glass|gl|wr|whole[- ]?rock|groundmass)(?![a-z])"
CPX = r"(?<![a-z])(cpx|clinopyroxene)(?![a-z])"
OPX = r"(?<![a-z])(opx|orthopyroxene)(?![a-z])"


def phase_oxides(cols, arr, prefix=False):
    """{oxide: wt%} of one phase. prefix False: every oxide column (whole rock). None: the liquid (glass, melt or whole rock): oxide
    columns that name no mineral ('SiO2', 'SiO2 glass', 'Liq MgO'). A regex such as CPX: the columns naming that mineral ('Cpx SiO2')."""
    import re
    from . import mineral as MN
    if prefix is False: return MN.collect_oxides(cols, arr)
    pick = {}
    for c in cols:
        s = str(c)
        if prefix:
            if not re.search(prefix, s, re.I): continue
            name = re.sub(prefix, " ", s, flags=re.I)
        else:
            if re.search(_MINERAL, s, re.I): continue
            name = re.sub(_LIQUID, " ", s, flags=re.I)
        pick.setdefault(name.strip(" _-:()[]"), c)
    if prefix and not pick and not any(re.search(_MINERAL, str(c), re.I) or re.search(_LIQUID, str(c), re.I) for c in cols):
        return MN.collect_oxides(cols, arr)  # a sheet of one mineral with plain headers (SiO2, TiO2 ...): those are its oxides
    return MN.collect_oxides(list(pick), lambda n: arr(pick[n]))


def _fo(v):
    f = v.get("Olivine Fo (blank = liquidus T)", 0.0)
    return None if np.ndim(f) == 0 and float(f) == 0.0 else f


_LIQ = ("phase", "Liquid oxides", None)
_CPX = ("phase", "Clinopyroxene oxides", CPX)
_OPX = ("phase", "Orthopyroxene oxides", OPX)
_H2O = ("colopt", "Liquid H2O (wt%)", r"^H2O(?!.*(cpx|ol|pl))")
_FO = ("colopt", "Olivine Fo (blank = liquidus T)", r"^Fo\b|forsterite|^ol.*\bfo\b|\bfo\b.*\bol")
_AN = ("col", "Plagioclase An (fraction or %)", r"^An\b|Plag.*An\b|An.*plag|^XAn")
_OR = ("colopt", "Plagioclase Or (fraction or %)", r"^Or\b|Plag.*\bOr\b")
_VNOTE = ("Liquid (glass, melt or whole rock) as wt% oxide columns named SiO2, TiO2, Al2O3, FeO or FeOt, MnO, MgO, CaO, Na2O, K2O (a word "
          "such as glass or liq may be added); mineral oxides as 'Cpx SiO2', 'Cpx Al2O3' ... Total iron is used as FeO. Liquid cation "
          "fractions as in Putirka (2008) Table 1, clinopyroxene components as in Table 3.")
_P08 = "Putirka (2008) Rev Mineral Geochem 69, 61-120"
from . import volcanic as VO  # noqa: E402
METHODS.update({
    "Liquid T from MgO (Putirka 2008 Eq 13)": {"out": "T glass Eq13", "unit": "deg C", "fn": lambda v: VO.glass_t13(v["Liquid oxides"]), "inputs": [_LIQ],
        "eq": "T = 26.3 MgO(liq) + 994.4", "ref": _P08, "note": "Olivine-saturated liquids (+-71 C). " + _VNOTE},
    "Liquid T (Putirka 2008 Eq 15)": {"out": "T glass Eq15", "unit": "deg C", "inputs": [_LIQ, _H2O, ("num", "P (kbar)", 1.0)],
        "fn": lambda v: VO.glass_t15(v["Liquid oxides"], v["P (kbar)"], v["Liquid H2O (wt%)"]),
        "eq": "T = 815.3 + 265.5 Mg# + 15.37 MgO + 8.61 FeO + 6.646 (Na2O + K2O) + 39.16 P(GPa) - 12.83 H2O", "ref": _P08,
        "note": "Olivine-saturated liquids, +-60 C. " + _VNOTE},
    "Olivine-liquid (Beattie 1993; Putirka 2008 Eq 19)": {"out": "T Ol-Liq B93", "unit": "deg C", "inputs": [_LIQ, _FO, ("num", "P (kbar)", 1.0)],
        "fn": lambda v: VO.ol_beattie(v["Liquid oxides"], v["P (kbar)"], _fo(v)),
        "eq": "T = [13603 + 4.943e-7 (P 1e9 - 1e5)] / [6.26 + 2 ln D(Mg) + 2 ln(1.5 C_NM) + 2 ln(3 C_SiO2) - NF] - 273.15 (P in GPa)",
        "ref": "Beattie (1993) Contrib Mineral Petrol 115, 103-111; " + _P08,
        "note": "Best for dry liquids. With an olivine Fo column, D(Mg) = (2/3) Fo / X_MgO(liq); without, D(Mg) from the liquid (Eq 20) gives the "
                "olivine liquidus. " + _VNOTE},
    "Olivine-liquid, hydrous (Putirka 2008 Eq 22)": {"out": "T Ol-Liq Eq22", "unit": "deg C", "inputs": [_LIQ, _FO, _H2O, ("num", "P (kbar)", 1.0)],
        "fn": lambda v: VO.ol_putirka22(v["Liquid oxides"], v["P (kbar)"], v["Liquid H2O (wt%)"], _fo(v)),
        "eq": "T = [15294.6 + 1318.8 P + 2.4834 P^2] / [8.048 + 2.8352 ln D(Mg) + 2.097 ln(1.5 C_NM) + 2.575 ln(3 C_SiO2) - 1.41 NF + 0.222 H2O + 0.5 P]",
        "ref": "Putirka et al. (2007) Chem Geol 241, 177-206; " + _P08, "note": "Use when the liquid holds water (P in GPa in the equation). " + _VNOTE},
    "Olivine-liquid KD(Fe-Mg) equilibrium test": {"out": "KD Ol-Liq", "unit": "ratio", "inputs": [_LIQ, ("col", "Olivine Fo", _FO[2])],
        "fn": lambda v: VO.ol_kd(v["Liquid oxides"], v["Olivine Fo"]), "eq": "KD = (X_Fe/X_Mg)ol / (X_Fe/X_Mg)liq; equilibrium 0.30 +- 0.03",
        "ref": "Roeder & Emslie (1970) Contrib Mineral Petrol 29, 275-289; " + _P08,
        "note": "Values outside 0.27-0.33 mean the olivine and liquid are not in equilibrium. " + _VNOTE},
    "Olivine Fo in equilibrium with the liquid (Rhodes diagram)": {"out": "Fo eq KD0.30", "unit": "%", "inputs": [_LIQ],
        "fn": lambda v: VO.fo_equilibrium(v["Liquid oxides"]), "eq": "Fo = 100 / (1 + 0.30 X_FeO/X_MgO (liq))", "ref": _P08,
        "note": "Compare with the measured Fo: higher measured Fo suggests olivine accumulation or mixing, lower suggests later growth. " + _VNOTE},
    "Plagioclase-liquid (Putirka 2008 Eq 24a)": {"out": "T Pl-Liq", "unit": "deg C", "inputs": [_LIQ, _AN, _OR, _H2O, ("num", "P (kbar)", 1.0)],
        "fn": lambda v: VO.plag_t24a(v["Liquid oxides"], v["Plagioclase An (fraction or %)"], v["P (kbar)"], v["Liquid H2O (wt%)"], v["Plagioclase Or (fraction or %)"]),
        "eq": "1e4/T(K) = 6.4706 + 0.3128 ln[X_An/(X_CaO X_AlO1.5^2 X_SiO2^2)] - 8.103 X_SiO2 + 4.872 X_KO0.5 + 1.5346 X_Ab^2 + 8.661 X_SiO2^2 - 0.03341 P + 0.18047 H2O",
        "ref": _P08, "note": "+-36 C. Check equilibrium: KD(An-Ab) = 0.10 +- 0.05 below 1050 C, 0.27 +- 0.11 above. " + _VNOTE},
    "Plagioclase-liquid hygrometer, H2O (Putirka 2008 Eq 25b)": {"out": "H2O Pl-Liq", "unit": "wt%", "inputs": [_LIQ, _AN, _OR, ("num", "P (kbar)", 1.0)] + _T_IN,
        "fn": lambda v: VO.plag_h2o_25b(v["Liquid oxides"], v["Plagioclase An (fraction or %)"], _t(v), v["P (kbar)"], v["Plagioclase Or (fraction or %)"]),
        "eq": "H2O = 25.95 - 0.0032 T(C) ln[X_An/(X_CaO X_AlO1.5^2 X_SiO2^2)] - 18.9 X_KO0.5 + 14.5 X_MgO - 40.3 X_CaO + 5.7 X_An^2 + 0.108 P",
        "ref": _P08, "note": "+-1.1 wt% H2O when T is known independently (olivine or clinopyroxene thermometry). " + _VNOTE},
    "Clinopyroxene-liquid T (Putirka 2008 Eq 33)": {"out": "T Cpx-Liq", "unit": "deg C", "inputs": [_LIQ, _CPX, _H2O, ("num", "P (kbar)", 5.0)],
        "fn": lambda v: VO.cpx_t33(v["Liquid oxides"], v["Clinopyroxene oxides"], v["P (kbar)"], v["Liquid H2O (wt%)"]),
        "eq": "1e4/T = 7.53 - 0.14 ln[Jd X_CaO X_Fm/(DiHd X_Na X_Al)] + 0.07 H2O - 14.9 X_CaO X_SiO2 - 0.08 ln X_TiO2 - 3.62 (X_Na + X_K) - 1.1 Mg# - 0.18 ln EnFs - 0.027 P",
        "ref": _P08, "note": "+-45 C. Pair with Eq 30 or 31 in the Coupled P-T Solver. Check KD(Fe-Mg) = 0.28 +- 0.08. " + _VNOTE},
    "Clinopyroxene-liquid P (Putirka 2008 Eq 30)": {"out": "P Cpx-Liq Eq30", "unit": "kbar", "inputs": [_LIQ, _CPX, _H2O] + _T_IN,
        "fn": lambda v: VO.cpx_p30(v["Liquid oxides"], v["Clinopyroxene oxides"], _t(v), v["Liquid H2O (wt%)"]),
        "eq": "P = -48.7 + 271 T/1e4 + 32 T/1e4 ln[Jd/(X_Na X_Al X_SiO2^2)] - 8.2 ln X_FeO + 4.6 ln X_MgO - 0.96 ln X_K - 2.2 ln DiHd - 31 Mg# + 56 (X_Na + X_K) + 0.76 H2O",
        "ref": _P08, "note": "+-1.6 kbar for the calibration data, +-3 kbar in tests. " + _VNOTE},
    "Clinopyroxene-liquid P (Putirka 2008 Eq 31)": {"out": "P Cpx-Liq Eq31", "unit": "kbar", "inputs": [_LIQ, _CPX, _H2O] + _T_IN,
        "fn": lambda v: VO.cpx_p31(v["Liquid oxides"], v["Clinopyroxene oxides"], _t(v), v["Liquid H2O (wt%)"]),
        "eq": "P = -40.73 + 358 T/1e4 + 21.69 T/1e4 ln[Jd/(X_Na X_Al X_SiO2^2)] - 105.7 X_CaO - 165.5 (X_Na + X_K)^2 - 50.15 X_SiO2 (X_FeO + X_MgO) - 3.178 ln DiHd - 2.205 ln EnFs + 0.864 ln Al(cpx) + 0.3962 H2O",
        "ref": _P08, "note": "Global calibration, +-2.9 kbar. " + _VNOTE},
    "Clinopyroxene-liquid KD(Fe-Mg) equilibrium test": {"out": "KD Cpx-Liq", "unit": "ratio", "inputs": [_LIQ, _CPX],
        "fn": lambda v: VO.cpx_kd(v["Liquid oxides"], v["Clinopyroxene oxides"]), "eq": "KD = (Fe/Mg)cpx / (Fe/Mg)liq; 0.28 +- 0.08",
        "ref": _P08, "note": "Expected value at T: ln KD = -0.107 - 1719/T(K) (Eq 35). " + _VNOTE},
    "Two-pyroxene T (Putirka 2008 Eq 36)": {"out": "T 2px Eq36", "unit": "deg C", "inputs": [_CPX, _OPX, ("num", "P (kbar)", 10.0)],
        "fn": lambda v: VO.two_px_t36(v["Clinopyroxene oxides"], v["Orthopyroxene oxides"], v["P (kbar)"]),
        "eq": "1e4/T(C) = 11.2 - 1.96 ln(EnFs cpx/EnFs opx) - 3.3 Ca(cpx) - 25.8 CrCaTs(cpx) + 33.2 Mn(opx) - 23.6 Na(opx) - 2.08 En(opx) - 8.33 Di(opx) - 0.05 P",
        "ref": _P08, "note": "Any composition, +-60 C. Columns 'Cpx SiO2' ... and 'Opx SiO2' ...; orthopyroxene components as in Table 2. " + _VNOTE},
    "Two-pyroxene T, Mg-rich (Putirka 2008 Eq 37)": {"out": "T 2px Eq37", "unit": "deg C", "inputs": [_CPX, _OPX, ("num", "P (kbar)", 10.0)],
        "fn": lambda v: VO.two_px_t37(v["Clinopyroxene oxides"], v["Orthopyroxene oxides"], v["P (kbar)"]),
        "eq": "1e4/T(C) = 13.4 - 3.4 ln(EnFs cpx/EnFs opx) + 5.59 ln Mg(cpx) - 8.8 Mg#(cpx) + 23.85 Mn(opx) + 6.48 FmAl2SiO6(opx) - 2.38 Di(cpx) - 0.044 P",
        "ref": _P08, "note": "For Mg# cpx > 0.75, +-38 C. Di(cpx) taken as DiHd Mg/(Mg + Fe + Mn), as for orthopyroxene. " + _VNOTE},
    "Two-pyroxene P (Putirka 2008 Eq 38)": {"out": "P 2px Eq38", "unit": "kbar", "inputs": [_CPX, _OPX],
        "fn": lambda v: VO.two_px_p38(v["Clinopyroxene oxides"], v["Orthopyroxene oxides"]),
        "eq": "P = -279.8 + 293 AlVI(opx) + 455 Na(opx) + 229 Cr(opx) + 519 Fm2Si2O6(opx) - 563 En(opx) + 371 Di(opx) + 327 a(En, opx) + 1.19/Kf; Kf = Ca(opx)/(1 - Ca(cpx))",
        "ref": _P08, "note": "Needs no T; Mg# cpx > 0.75, +-3.7 kbar. " + _VNOTE},
    "Two-pyroxene P (Putirka 2008 Eq 39)": {"out": "P 2px Eq39", "unit": "kbar", "inputs": [_CPX, _OPX] + _T_IN,
        "fn": lambda v: VO.two_px_p39(v["Clinopyroxene oxides"], v["Orthopyroxene oxides"], _t(v)),
        "eq": "P = -94.25 + 0.045 T(C) + 187.7 AlVI(opx) + 246.8 Fm2Si2O6(opx) - 212.5 En(opx) + 127.5 a(En, opx) - 1.66/Kf - 69.4 EnFs(cpx) - 133.9 a(Di, cpx)",
        "ref": _P08, "note": "With T from Eq 36 or 37 (Coupled P-T Solver), +-2.8 kbar. " + _VNOTE},
    "Clinopyroxene-only P (Putirka 2008 Eq 32a)": {"out": "P Cpx Eq32a", "unit": "kbar", "inputs": [_CPX] + _T_IN,
        "fn": lambda v: VO.cpx_p32a(v["Clinopyroxene oxides"], _t(v)),
        "eq": "P = 3205 + 0.384 T - 518 ln T - 5.62 Mg + 83.2 Na + 68.2 DiHd + 2.52 ln AlVI - 51.1 DiHd^2 + 34.8 EnFs^2 (T in K, cations on 6 O)",
        "ref": _P08, "note": "No liquid needed; reads low for hydrous magmas. " + _VNOTE},
    "Clinopyroxene-only T (Putirka 2008 Eq 32d)": {"out": "T Cpx Eq32d", "unit": "deg C", "inputs": [_CPX, ("num", "P (kbar)", 5.0)],
        "fn": lambda v: VO.cpx_t32d(v["Clinopyroxene oxides"], v["P (kbar)"]),
        "eq": "T(K) = (93100 + 544 P) / [61.1 + 36.6 Ti + 10.9 Fe - 0.95 (Al + Cr - Na - K) + 0.395 (ln a_En)^2], a_En = (1 - Ca - Na - K)(1 - (Al + Cr + Na + K)/2)",
        "ref": _P08, "note": "+-58 C for anhydrous systems. " + _VNOTE},
    "Cr-in-clinopyroxene P (Nimis & Taylor 2000)": {"out": "P Cr-in-Cpx", "unit": "kbar", "inputs": [_CPX] + _T_IN,
        "fn": lambda v: VO.nimis_taylor_p(v["Clinopyroxene oxides"], _t(v)),
        "eq": "P = -T/126.9 ln a_CaCrTs + 15.483 ln(Cr#/T) + T/71.38 + 107.8, a_CaCrTs = Cr - 0.81 Cr# Na, Cr# = Cr/(Cr + Al), T in K",
        "ref": "Nimis & Taylor (2000) Contrib Mineral Petrol 139, 541-554",
        "note": "Clinopyroxene in equilibrium with garnet in peridotite (mantle xenoliths, xenocrysts); +-2.3 kbar. Pair with the En-in-Cpx thermometer in the Coupled P-T Solver. " + _VNOTE},
    "En-in-clinopyroxene T (Nimis & Taylor 2000)": {"out": "T En-in-Cpx", "unit": "deg C", "inputs": [_CPX, ("num", "P (kbar)", 40.0)],
        "fn": lambda v: VO.nimis_taylor_t(v["Clinopyroxene oxides"], v["P (kbar)"]),
        "eq": "T(K) = (23166 + 39.28 P) / [13.25 + 15.35 Ti + 4.50 Fe - 1.55 (Al + Cr - Na) + (ln a_en)^2], a_en = (1 - Ca - Na)(1 - (Al + Cr + Na)/2)",
        "ref": "Nimis & Taylor (2000) Contrib Mineral Petrol 139, 541-554", "note": "Peridotite clinopyroxene coexisting with orthopyroxene; +-30 C. " + _VNOTE},
})


# Calibration domains stated by the authors (or in the method notes): the result, and numeric inputs such as P, outside these
# ranges are flagged. Equilibrium tests use the accepted equilibrium window instead. Methods not listed have no recorded range.
VALID = {
    "Ti-in-zircon (Ferry & Watson 2007)": {"out": (580, 1070), "ref": "experiments and natural zircon, 580-1070 C"},
    "Ti-in-quartz (Wark & Watson 2006)": {"out": (600, 1000), "ref": "experiments at 600-1000 C, 10 kbar"},
    "Ti-in-quartz (Thomas et al. 2010)": {"out": (700, 940), "P (kbar)": (5, 20), "ref": "experiments at 700-940 C, 5-20 kbar"},
    "Zr-in-titanite (Hayden et al. 2008)": {"out": (800, 1000), "P (kbar)": (10, 24), "ref": "experiments at 800-1000 C, 1-2.4 GPa"},
    "Zircon saturation (Watson & Harrison 1983)": {"out": (750, 1020), "ref": "experiments at 750-1020 C, M = 0.9-1.7"},
    "Garnet-biotite Fe-Mg (Ferry & Spear 1978)": {"out": (550, 800), "ref": "experiments at 550-800 C, 2.07 kbar"},
    "Amphibole-plagioclase A, edenite-tremolite (Holland & Blundy 1994)": {"out": (400, 1000), "P (kbar)": (1, 15), "ref": "400-1000 C, 1-15 kbar"},
    "Amphibole-plagioclase B, edenite-richterite (Holland & Blundy 1994)": {"out": (400, 1000), "P (kbar)": (1, 15), "ref": "400-1000 C, 1-15 kbar"},
    "Two-pyroxene (Brey & Kohler 1990)": {"out": (900, 1400), "P (kbar)": (10, 60), "ref": "experiments at 900-1400 C, 10-60 kbar"},
    "Ca-in-orthopyroxene (Brey & Kohler 1990)": {"out": (900, 1400), "P (kbar)": (10, 60), "ref": "experiments at 900-1400 C, 10-60 kbar"},
    "Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)": {"out": (10, 60), "T (C), if no column": (900, 1400), "ref": "experiments at 900-1400 C, 10-60 kbar"},
    "Al-in-hornblende (Schmidt 1992)": {"out": (2.5, 13), "ref": "experiments at 2.5-13 kbar"},
    "Al-in-hornblende (Mutch et al. 2016)": {"out": (0.8, 10), "ref": "experiments at 0.8-10 kbar"},
    "Al-in-hornblende (Johnson & Rutherford 1989)": {"out": (2, 8), "ref": "experiments at 2-8 kbar"},
    "Olivine-liquid KD(Fe-Mg) equilibrium test": {"out": (0.27, 0.33), "ref": "equilibrium KD 0.30 +- 0.03 (Roeder & Emslie 1970)", "kind": "equilibrium"},
    "Clinopyroxene-liquid KD(Fe-Mg) equilibrium test": {"out": (0.20, 0.36), "ref": "equilibrium KD 0.28 +- 0.08 (Putirka 2008)", "kind": "equilibrium"},
}


def in_range(method, values, inputs, n_rows):
    """Per row: 1.0 inside the method's calibration domain (or equilibrium window), 0.0 outside, NaN when there is no result or no
    recorded range. inputs: the numbers or per-row arrays given to the method (e.g. P); a temperature column, when one is used,
    stands for the single temperature value."""
    rng = VALID.get(method); vals = np.asarray(values, float); inputs = dict(inputs)
    tc = inputs.get("T (C) column")
    if isinstance(tc, (np.ndarray, list, tuple)) and np.size(tc) > 0: inputs["T (C), if no column"] = tc  # also a one-row sheet
    if rng is None: return np.full(len(vals), np.nan)
    ok = np.isfinite(vals) & (vals >= rng["out"][0]) & (vals <= rng["out"][1])
    for label, (lo, hi) in ((k, v) for k, v in rng.items() if isinstance(v, tuple) and k != "out"):
        x = inputs.get(label)
        if isinstance(x, (int, float, np.ndarray, list)): x = np.broadcast_to(np.asarray(x, float), vals.shape); ok &= (x >= lo) & (x <= hi)
    return np.where(np.isfinite(vals), ok.astype(float), np.nan)


def monte_carlo(method, columns, sheet_arr, sheet_oxides, n_rows=None, rel=0.02, n=500, num_sd=None, seed=1):
    """Standard deviation (per row) of a method's result when every measured input (columns, oxide analyses) carries a relative
    1-sigma error rel (0.02 = 2 %), drawn n times independently; num_sd: {numeric input: absolute 1-sigma}, e.g. {"P (kbar)": 1}.
    Inputs are perturbed independently (no covariance between oxides or phases), so this is a first estimate of the analytical part
    of the uncertainty; the calibration error of the equation (in the method notes) comes on top."""
    rs = np.random.default_rng(seed); num_sd = num_sd or {}; out = []
    base_ox = {}
    # state variables given as columns (a temperature column) carry an absolute error, as the numbers do, never a relative one
    absolute = {columns[k]: sd for k, sd in num_sd.items() if isinstance(columns.get(k), str)}
    if isinstance(columns.get("T (C) column"), str): absolute[columns["T (C) column"]] = num_sd.get("T (C), if no column", 0.0)

    def noisy(a): a = np.asarray(a, float); return a * (1 + rel * rs.standard_normal(a.shape))

    def column(c):
        a = np.asarray(sheet_arr(c), float)
        return a + absolute[c] * rs.standard_normal(a.shape) if c in absolute else noisy(a)
    for _ in range(int(n)):
        arr = column

        def ox(prefix=False):
            key = repr(prefix)
            if key not in base_ox: base_ox[key] = sheet_oxides(prefix)
            return {k: noisy(v) for k, v in base_ox[key].items()}
        cols = dict(columns)
        for label, sd in num_sd.items():
            if sd and label in cols and isinstance(cols[label], (int, float)) and not isinstance(cols[label], bool):
                cols[label] = cols[label] + sd * rs.standard_normal(n_rows or 1)
        with np.errstate(all="ignore"): out.append(np.asarray(compute(method, cols, arr, ox, n_rows), float))
    out = np.array(out)
    with np.errstate(all="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore"); return np.nanstd(out, axis=0, ddof=1)


def coupled_pairs():
    """(thermometers that take P, barometers) that the coupled P-T solver can combine."""
    th = [k for k, m in METHODS.items() if m["unit"] == "deg C" and any(i[1] == "P (kbar)" for i in m["inputs"])]
    return th, [k for k, m in METHODS.items() if m["unit"] == "kbar"]


def solve_pt(tmethod, pmethod, columns, sheet_arr, sheet_oxides, p0=10.0, n_iter=60, tol=0.01):
    """T and P that satisfy a thermometer and a barometer together, row by row, by fixed-point iteration from P = p0 kbar:
    T = fT(P), then P = fP(T), until P moves by less than tol kbar. Returns (T in C, P in kbar, iterations); rows that do not
    settle are left blank."""
    P = np.asarray(p0, float); it = 0
    tcols = lambda T: {**columns, "T (C) column": None, "T (C), if no column": T}
    for it in range(1, n_iter + 1):
        T = compute(tmethod, {**columns, "P (kbar)": P}, sheet_arr, sheet_oxides)
        Pn = compute(pmethod, tcols(T), sheet_arr, sheet_oxides); Pn = np.broadcast_to(Pn, np.broadcast(Pn, T).shape).astype(float)
        with np.errstate(invalid="ignore"): d = np.abs(Pn - P)
        P = Pn
        if np.all(~np.isfinite(d) | (d < tol)): break
    T = compute(tmethod, {**columns, "P (kbar)": P}, sheet_arr, sheet_oxides)
    with np.errstate(invalid="ignore"): off = ~(np.abs(compute(pmethod, tcols(T), sheet_arr, sheet_oxides) - P) < 10 * tol)
    T, P = np.array(T, float), np.array(np.broadcast_to(P, T.shape), float); T[off] = np.nan; P[off] = np.nan
    return T, P, it


# Brey, Kohler & Nickel (1990, J Petrol 31, 1313, Table 2): garnet-lherzolite runs (run, P kbar, T C, opx Ca Al Cr Na Mg#, garnet XCa Al
# Cr XMn Mg#). Midpoints of the experimental brackets; garnet Ca and Mn are mole fractions, Mg# for the Nor (or J4, SC-1) composition.
BREY_RUNS = [("466", 30, 1200, (.045, .130, .017, 0, 91.0), (.140, 1.87, .125, .019, 85.2)),
             ("467", 30, 1300, (.065, .162, .020, .010, 91.8), (.137, 1.85, .120, .015, 86.6)),
             ("472", 30, 1000, (.021, .067, .010, 0, 90.0), (.139, 1.868, .125, .024, 78.5)),
             ("458", 30, 1100, (.030, .104, .014, 0, 91.5), (.148, 1.855, .125, .018, 82.1)),
             ("P21", 31, 900, (.015, .052, .008, 0, 91.8), (.155, 1.788, .125, .030, 82.7)),
             ("500", 40, 900, (.010, .020, .003, 0, 92.1), (.143, 1.825, .125, 0, 80.5)),
             ("463", 40, 1000, (.018, .042, .006, 0, 90.2), (.141, 1.860, .130, .025, 77.8)),
             ("406", 40, 1200, (.040, .057, .008, 0, 91.5), (.129, 1.854, .135, .015, 83.3)),
             ("459", 40, 1300, (.057, .095, .017, 0, 90.4), (.127, 1.864, .123, .018, 83.2)),
             ("451", 41.8, 1100, (.025, .042, .0064, 0, 92.1), (.135, 1.843, .130, .021, 84.0)),
             ("347", 50, 900, (.011, .016, .004, .0016, 91.5), (.150, 1.805, .125, .016, 79.0)),
             ("462", 50, 1000, (.014, .025, .004, 0, 92.3), (.135, 1.850, .130, .020, 82.8))]


def brey_runs():
    """[(run, P, T, P_BKN, P_NG, P_HG)] for the Brey et al. (1990) runs at their run temperatures."""
    out = []
    for name, p, t, (oca, oal, ocr, ona, omg), (xca, gal, gcr, xmn, gmg) in BREY_RUNS:
        mf = 2 - oca - ona; opx = dict(al=oal, cr=ocr, ti=0, fe3=0, na=ona, ca=oca, mn=0, mg=mf * omg / 100, fe=mf * (1 - omg / 100))
        ca, mn = 3 * xca, 3 * xmn; rest = 3 - ca - mn; gt = dict(ca=ca, mn=mn, mg=rest * gmg / 100, fe=rest * (1 - gmg / 100), al=gal, cr=gcr)
        out.append((name, p, t, float(brey_kohler_1990_p(opx, gt, t)), float(nickel_green_1985(opx, gt, t)),
                    float(harley_green_1982(oal, opx["mg"], opx["fe"], ca, gt["mg"], gt["fe"], t))))
    return out


def _demo():
    """Hand-worked values of each equation."""
    near = lambda a, b, tol=0.05: abs(float(a) - b) < tol
    assert near(ti_in_zircon(10), 4800 / (5.711 - 1) - K0)                        # 10 ppm Ti: 745.7 C
    assert near(ti_in_zircon(10), 745.74)
    assert near(ti_in_zircon(10, a_tio2=0.5), 4800 / (5.711 - 1 + np.log10(0.5)) - K0)  # lower aTiO2 -> higher T
    assert ti_in_zircon(10, a_tio2=0.5) > ti_in_zircon(10)
    assert near(zr_in_rutile(100), 4530 / (7.420 - 2) - K0) and near(zr_in_rutile_watson2006(100), 4470 / 5.36 - K0)
    assert near(ti_in_quartz_wark2006(50), 3765 / (5.69 - np.log10(50)) - K0)
    t = ti_in_quartz_thomas2010(50, 5.0); assert 570 < t < 585, t                  # 50 ppm Ti at 5 kbar: about 577 C
    assert ti_in_quartz_thomas2010(50, 10.0) > t                                   # higher P, higher T for the same Ti
    ox = {"SiO2": [72.0], "Al2O3": [14.0], "CaO": [1.5], "Na2O": [3.5], "K2O": [4.5], "FeO": [2.0], "MgO": [0.5], "TiO2": [0.3]}
    M = m_factor(ox)[0]; assert 1.0 < M < 1.6, M
    tw = zircon_saturation([150], ox)[0]; assert near(tw, 12900 / (_ln(497644 / 150) + 3.8 + 0.85 * (M - 1)) - K0) and 750 < tw < 820, tw
    tb = zircon_saturation([150], ox, "Boehnke")[0]; assert near(tb, 10108 / (_ln(497644 / 150) + 1.16 * (M - 1) + 1.48) - K0)
    kd = (0.4 / 2.2) / (1.2 / 1.3); tgb = garnet_biotite(0.4, 2.2, 1.2, 1.3, 5.0)
    assert near(tgb, (2089 + 48) / (0.782 - _ln(kd)) - K0) and 550 < tgb < 700, tgb
    tgc = garnet_cpx(0.9, 1.5, 0.6, 0.05, 0.8, 0.2, 15.0); kd = (1.5 / 0.9) / (0.2 / 0.8); xca = 0.6 / 3.05
    assert near(tgc, (3104 * xca + 3030 + 162.9) / (_ln(kd) + 1.9034) - K0) and 700 < tgc < 950, tgc
    assert near(al_in_hornblende(1.5), -3.01 + 4.76 * 1.5) and near(al_in_hornblende(1.5, "Mutch et al. 2016"), 0.5 + 0.4965 + 2.23875)
    for name, m in METHODS.items(): assert {"out", "unit", "fn", "inputs", "eq", "ref"} <= set(m), name
    cols = ["Sample", "TiO2", "Ti (ppm)", "Zr", "Grt Mg", "Grt Fe", "Bt Mg", "Bt Fe", "Al (apfu)"]
    assert guess_column(cols, r"Ti(?!O)") == "Ti (ppm)" and guess_column(cols, r"Zr(?!n|c|O)") == "Zr"
    assert guess_column(cols, METHODS["Garnet-biotite Fe-Mg (Ferry & Spear 1978)"]["inputs"][3][2]) == "Bt Fe"
    assert guess_column(cols, METHODS["Al-in-hornblende (Schmidt 1992)"]["inputs"][0][2]) == "Al (apfu)"
    # two pyroxenes of a granulite at 8 kbar (hand-worked: 827 C) and the amphibole-plagioclase pair of a tonalite at 5 kbar
    assert near(two_pyroxene_bk(0.85, 0.02, 0.6, 0.257, 0.03, 0.005, 1.1, 0.733, 8.0), 827.0, 1.5)
    assert two_pyroxene_bk(0.80, 0.02, 0.6, 0.257, 0.03, 0.005, 1.1, 0.733, 8.0) > two_pyroxene_bk(0.85, 0.02, 0.6, 0.257, 0.03, 0.005, 1.1, 0.733, 8.0)
    assert near(ca_in_opx_bk(0.03, 8.0), 6636.2 / (-_ln(0.03) + 1.843) - K0)
    cpx = dict(si=2.0, al=0, ti=0, cr=0, fe3=0, fe2=0.257, mg=0.6, mn=0, ca=0.85, na=0.02)
    opx = dict(si=2.0, al=0, ti=0, cr=0, fe3=0, fe2=0.733, mg=1.1, mn=0, ca=0.03, na=0.005)
    a_c = (0.6 / 0.857) ** 2 * (1 - 0.87); assert near(a_enstatite(**cpx), a_c, 1e-9)          # XMg(M1) XMg(M2) by hand
    tw, twb = two_pyroxene_wells(cpx, opx), two_pyroxene_wood_banno(cpx, opx)
    kk = a_c / ((1.1 / 1.833) ** 2 * (1 - 0.035)); xf = 0.733 / 1.833
    assert near(tw, 7341 / (3.355 + 2.44 * xf - _ln(kk)) - K0) and near(tw, 945.0, 1.5), tw   # hand-worked: about 945 C
    assert near(twb, -10202 / (_ln(kk) - 7.65 * xf + 3.88 * xf ** 2 - 4.6) - K0) and near(twb, 895.0, 1.5), twb  # about 895 C
    al_c = dict(cpx, si=1.9, al=0.2)  # 0.1 AlVI on M1 lowers a(En, cpx), so K and the Wells T change
    assert abs(a_enstatite(**al_c) - a_c * 0.9) < 1e-9 and two_pyroxene_wells(al_c, opx) != tw
    assert abs(a_enstatite(**dict(cpx, si=0, al=0.2)) - a_c * 0.8) < 1e-9  # no Si given: all Al on M1
    hb = dict(si=6.8, al=1.5, ti=0.15, fe3=0.4, fe2=1.5, mg=2.6, mn=0.05, ca=1.8, na=0.45, k=0.15)
    ta, tb_ = holland_blundy_a(**hb, an_plag=0.4, p_kbar=5.0), holland_blundy_b(**hb, an_plag=40, p_kbar=5.0)
    q_a = 27 * 0.6 * 0.7 * 0.6 / (256 * 0.25 * 0.3)  # X_ab = 0.6 in the logarithm (Holland & Blundy 1994, p. 441)
    num_a = -76.95 + 0.79 * 5 + 0 + 39.4 * 0.25 + 22.4 * 0.15 + (41.5 - 2.89 * 5) * 0.15
    assert near(ta, num_a / (-0.0650 - RKJ * _ln(q_a)) - K0) and near(tb_, 751.0, 1.5), (ta, tb_)
    assert near(holland_blundy_a(**hb, an_plag=0.6, p_kbar=5.0), (num_a - 76.95 * 0 + 12.0 * 0.6 ** 2 - 3.0) /
                (-0.0650 - RKJ * _ln(27 * 0.6 * 0.7 * 0.4 / (256 * 0.25 * 0.3))) - K0)  # X_ab 0.4 < 0.5: Yab = 12.0 (1 - X_ab)^2 - 3
    s = hb_sites(**hb); assert near(s["XvA"], 0.6, 1e-9) and near(s["XNaA"], 0.25, 1e-9) and near(s["XAlM2"], 0.15, 1e-9)
    # Harley & Green (1982) Fig. 2: Al isopleths for opx XMg = 0.50 with Fe-Mg garnet; 2.5 % and 5 % Al in M1 at 1000 C plot at about
    # 27 and 19 kbar
    assert 26 < harley_green_1982(0.05, 1, 1, 0, 1, 1, 1000.0) < 28.5 and 17.5 < harley_green_1982(0.10, 1, 1, 0, 1, 1, 1000.0) < 20.5
    assert harley_green_1982(0.10, 1, 1, 0, 1, 1, 1100.0) > harley_green_1982(0.10, 1, 1, 0, 1, 1, 1000.0)  # isopleths rise with T
    # a garnet lherzolite (Mg-rich, low Cr) at 1100 C: the two Al-in-opx barometers built on the same site scheme give similar pressures
    opx = dict(al=0.10, cr=0.01, ti=0.0, fe3=0.0, na=0.01, ca=0.03, mn=0.0, mg=1.75, fe=0.16)
    gt = dict(ca=0.40, mg=2.15, fe=0.45, mn=0.0, al=1.90, cr=0.10)
    p_ng, p_bk = float(nickel_green_1985(opx, gt, 1100.0)), float(brey_kohler_1990_p(opx, gt, 1100.0))
    assert 25 < p_ng < 60 and 25 < p_bk < 60 and abs(p_ng - p_bk) < 8, (p_ng, p_bk)
    assert float(brey_kohler_1990_p(dict(opx, al=0.14), gt, 1100.0)) < p_bk and float(nickel_green_1985(dict(opx, al=0.14), gt, 1100.0)) < p_ng
    r = compute("Ti-in-zircon (Ferry & Watson 2007)", {"Ti (ppm)": "Ti (ppm)", "a SiO2": 1, "a TiO2": 1}, lambda c: np.array([10.0]), dict)
    assert abs(r[0] - 745.74) < 0.05
    # the barometers against the experiments of Brey et al. (1990) Part I: P_BKN and Nickel & Green recover the run pressures
    # (mean offset within 1 kbar, scatter below 3 kbar as in Brey & Kohler 1990 Part II); Harley & Green reads about 3 kbar low
    runs = np.array([r[1:] for r in brey_runs()], float); dev = runs[:, 2:] - runs[:, [0]]
    assert abs(dev[:, 0].mean()) < 1 and dev[:, 0].std(ddof=1) < 3 and abs(dev[:, 1].mean()) < 1 and dev[:, 1].std(ddof=1) < 3, dev.mean(0)
    assert -4 < dev[:, 2].mean() < -2, dev[:, 2].mean()
    # coupled P-T: Ca-in-opx with P_BKN for run 466 (30 kbar, 1200 C); the answer satisfies both equations
    o = {"Opx Ca": [.045], "Opx Al": [.130], "Opx Cr": [.017], "Opx Na": [0.0], "Opx Mg": [1.955 * .91], "Opx Fe": [1.955 * .09],
         "Garnet Ca": [.42], "Garnet Mg": [2.523 * .852], "Garnet Fe": [2.523 * .148], "Garnet Mn": [.057], "Garnet Al": [1.87], "Garnet Cr": [.125]}
    cols = {k: k for k in o}; arr = lambda c: np.asarray(o[c], float)
    T, P, it = solve_pt("Ca-in-orthopyroxene (Brey & Kohler 1990)", "Garnet-orthopyroxene Al (Brey & Kohler 1990, PBKN)", cols, arr, dict)
    assert near(T[0], ca_in_opx_bk(0.045, P[0]), 0.01) and 1 < it < 20, (T, P, it)
    og = {"opx": {"al": .130, "cr": .017, "ti": 0, "fe3": 0, "na": 0, "ca": .045, "mn": 0, "mg": 1.955 * .91, "fe": 1.955 * .09},
          "gt": {"ca": .42, "mg": 2.523 * .852, "fe": 2.523 * .148, "mn": .057, "al": 1.87, "cr": .125}}
    assert near(P[0], brey_kohler_1990_p(og["opx"], og["gt"], T[0]), 0.02) and 20 < P[0] < 40 and 1000 < T[0] < 1400, (T, P)
    # the liquid and the clinopyroxene are told apart by the column names; the P-T solver pairs Eq 33 with Eq 31
    liq = {"SiO2": [47.05], "TiO2": [0.89], "Al2O3": [16.11], "FeO": [7.96], "MnO": [0.15], "MgO": [12.78], "CaO": [11.13], "Na2O": [2.18], "K2O": [0.04]}
    cx = {"Cpx SiO2": [52.5], "Cpx TiO2": [0.33], "Cpx Al2O3": [1.58], "Cpx FeO": [9.89], "Cpx MnO": [0.24], "Cpx MgO": [13.29], "Cpx CaO": [22.5],
          "Cpx Na2O": [0.37], "Cpx Cr2O3": [0.05], "Ol Fo": [89.0]}
    sheet = {**liq, **cx}; arr = lambda c: np.asarray(sheet[c], float); ph = lambda p=False: phase_oxides(list(sheet), arr, p)
    assert set(ph(None)) == set(liq) and float(ph(CPX)["SiO2"][0]) == 52.5 and float(ph(None)["SiO2"][0]) == 47.05
    t33 = compute("Clinopyroxene-liquid T (Putirka 2008 Eq 33)", {"P (kbar)": 5.0}, arr, ph)
    assert near(t33[0], VO.cpx_t33({k: v[0] for k, v in liq.items()}, {k[4:]: v[0] for k, v in cx.items() if k.startswith("Cpx")}, 5.0), 1e-6)
    T, P, it = solve_pt("Clinopyroxene-liquid T (Putirka 2008 Eq 33)", "Clinopyroxene-liquid P (Putirka 2008 Eq 31)", {}, arr, ph)
    assert np.isfinite(T[0]) and near(P[0], compute("Clinopyroxene-liquid P (Putirka 2008 Eq 31)", {"T (C), if no column": T}, arr, ph)[0], 0.02)
    tf = compute("Olivine-liquid (Beattie 1993; Putirka 2008 Eq 19)", {"Olivine Fo (blank = liquidus T)": "Ol Fo", "P (kbar)": 1.0}, arr, ph)
    tl = compute("Olivine-liquid (Beattie 1993; Putirka 2008 Eq 19)", {"P (kbar)": 1.0}, arr, ph); assert tf[0] < tl[0] + 60 and np.isfinite(tf[0])
    # both XNa(A) and Xv(A) negative used to give a positive ratio and a false temperature: now blank
    assert np.isnan(holland_blundy_a(7.6, 0.6, 0.05, 0.1, 1.5, 3.4, 0.05, 1.5, 0.05, 0.0, 0.4, 5.0)), "negative A-site fractions must give no T"
    print("THERMOBARO OK")


if __name__ == "__main__":
    _demo()
