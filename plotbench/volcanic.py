"""Mineral-melt and single-clinopyroxene thermobarometry for volcanic and mantle rocks.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Putirka (2008, Rev Mineral Geochem 69, 61-120): liquid cation fractions (Table 1), clinopyroxene components (Table 3), olivine-liquid
(Eqs 19-22, Beattie 1993), plagioclase-liquid thermometer and hygrometer (Eqs 24a, 25b), clinopyroxene-liquid barometers and
thermometer (Eqs 30, 31, 33), clinopyroxene-only barometer and thermometer (Eqs 32a, 32d), glass thermometers (Eqs 13, 15) and
equilibrium tests. Nimis & Taylor (2000, Contrib Mineral Petrol 139, 541-554): Cr-in-cpx barometer (Eqs 9, 10) and enstatite-in-cpx
thermometer (Eqs 15, 17). Inputs are wt% oxides (arrays allowed); P in kbar unless stated; T in deg C out.
"""
import numpy as np

K0 = 273.15
# molecular weights of Putirka (2008) Table 1 (liquid, single-cation units) and Table 3 (pyroxene)
LIQ_MW = {"SiO2": 60.08, "TiO2": 79.9, "Al2O3": 50.98, "FeO": 71.85, "MnO": 70.94, "MgO": 40.3, "CaO": 56.08, "Na2O": 30.99, "K2O": 47.1,
          "Cr2O3": 76.0, "P2O5": 70.97}
LIQ_N = {"Al2O3": "AlO1.5", "Na2O": "NaO0.5", "K2O": "KO0.5", "Cr2O3": "CrO1.5", "P2O5": "PO2.5"}
PX_MW = {"SiO2": 60.08, "TiO2": 79.9, "Al2O3": 101.96, "FeO": 71.85, "MnO": 70.94, "MgO": 40.3, "CaO": 56.08, "Na2O": 61.98, "K2O": 94.2,
         "Cr2O3": 152.0}
PX_O = {"SiO2": 2, "TiO2": 2, "Al2O3": 3, "FeO": 1, "MnO": 1, "MgO": 1, "CaO": 1, "Na2O": 1, "K2O": 1, "Cr2O3": 3}
PX_CAT = {"SiO2": ("Si", 1), "TiO2": ("Ti", 1), "Al2O3": ("Al", 2), "FeO": ("Fe", 1), "MnO": ("Mn", 1), "MgO": ("Mg", 1), "CaO": ("Ca", 1),
          "Na2O": ("Na", 2), "K2O": ("K", 2), "Cr2O3": ("Cr", 2)}


def _g(ox, k): return np.nan_to_num(np.asarray(ox.get(k, ox.get(k + "t", ox.get(k + "T", 0.0))), float))  # FeOt / FeOT stand in for FeO


def liquid(ox):
    """Anhydrous cation fractions of a liquid (Table 1): keys SiO2, TiO2, AlO1.5, FeO, MnO, MgO, CaO, NaO0.5, KO0.5 ..., plus the Beattie
    (1993) components C_NM (network modifiers), C_SiO2 and NF = 7/2 ln(1 - X_AlO1.5) + 7 ln(1 - X_TiO2), and Mg# (molar, from wt%).
    Total iron goes in as FeO; water is not part of the sum."""
    prop = {LIQ_N.get(k, k): _g(ox, k) / mw for k, mw in LIQ_MW.items()}
    tot = sum(prop.values())
    with np.errstate(all="ignore"):
        X = {k: v / tot for k, v in prop.items()}
        X["C_NM"] = X["FeO"] + X["MnO"] + X["MgO"] + X["CaO"]
        X["C_SiO2"] = X["SiO2"]; X["NF"] = 3.5 * np.log(1 - X["AlO1.5"]) + 7 * np.log(1 - X["TiO2"])
        X["Mg#"] = (_g(ox, "MgO") / 40.3) / (_g(ox, "MgO") / 40.3 + _g(ox, "FeO") / 71.85)
    return X


def cpx(ox):
    """Clinopyroxene cations on 6 oxygens and components (Table 3): AlIV, AlVI, Fe3+ (Papike et al. 1974), Jd, CaTs, CaTi, CrCaTs,
    DiHd, EnFs. Total iron as FeO."""
    mol = {k: _g(ox, k) / mw for k, mw in PX_MW.items()}
    with np.errstate(all="ignore"):
        orf = 6 / sum(mol[k] * PX_O[k] for k in mol)
        c = {PX_CAT[k][0]: mol[k] * orf * PX_CAT[k][1] for k in mol}
        c["Sum"] = sum(c[PX_CAT[k][0]] for k in mol)
        c["AlIV"] = np.clip(2 - c["Si"], 0, None); c["AlVI"] = np.clip(c["Al"] - c["AlIV"], 0, None)
        c["Fe3"] = np.clip(c["Na"] + c["AlIV"] - c["AlVI"] - 2 * c["Ti"] - c["Cr"], 0.0, c["Fe"])  # never below 0 or above total Fe
        c["Jd"] = np.minimum(c["AlVI"], c["Na"]); c["CaTs"] = np.clip(c["AlVI"] - c["Jd"], 0, None)
        c["CaTi"] = np.where(c["AlIV"] > c["CaTs"], (c["AlIV"] - c["CaTs"]) / 2, 0.0); c["CrCaTs"] = c["Cr"] / 2
        c["DiHd"] = c["Ca"] - c["CaTi"] - c["CaTs"] - c["CrCaTs"]; c["EnFs"] = (c["Fe"] + c["Mg"] - c["DiHd"]) / 2
        for k in ("Jd", "DiHd", "EnFs", "AlVI"):  # these go into logarithms: zero or negative gives a blank, not -inf
            c[k] = np.where(np.asarray(c[k], float) > 0, c[k], np.nan)
    return c


def _pos(a): return np.where(np.asarray(a, float) > 0, a, np.nan)


def _gpa(p_kbar): return np.asarray(p_kbar, float) / 10.0


# ---------------------------------------------------------------- two pyroxenes (Putirka 2008 Eqs 36-39)
def _px_cations(ox):
    """Pyroxene cations on 6 oxygens (Putirka 2008 Table 2, rows 1-8); total iron as FeO."""
    mol = {k: _g(ox, k) / mw for k, mw in PX_MW.items()}
    with np.errstate(all="ignore"):
        orf = 6 / sum(mol[k] * PX_O[k] for k in mol); c = {PX_CAT[k][0]: mol[k] * orf * PX_CAT[k][1] for k in mol}
        c["AlIV"] = np.clip(2 - c["Si"], 0, None); c["AlVI"] = np.clip(c["Al"] - c["AlIV"], 0, None)
        c["Fe3"] = np.clip(c["Na"] + c["AlIV"] - c["AlVI"] - 2 * c["Ti"] - c["Cr"], 0.0, c["Fe"]); c["Fe2"] = c["Fe"] - c["Fe3"]  # Papike et al. (1974)
    return c


def opx(ox):
    """Orthopyroxene components of Putirka (2008) Table 2 (row 10): NaAlSi2O6 = lesser of AlVI and Na, FmTiAlSiO6 = Ti, CrAl2SiO6 = Cr,
    FmAl2SiO6 = AlVI - NaAlSi2O6 - CrAl2SiO6, CaFmSi2O6 = Ca, Fm2Si2O6 = (Fe + Mn + Mg - FmTiAlSiO6 - FmAl2SiO6 - CaFmSi2O6)/2;
    En and Di are Fm2Si2O6 and CaFmSi2O6 times Mg/(Mg + Fe + Mn); a(En) as in Wood & Banno (1973), text below Eq 38."""
    c = _px_cations(ox)
    with np.errstate(all="ignore"):
        c["NaAlSi2O6"] = np.minimum(c["AlVI"], c["Na"]); c["FmTiAlSiO6"] = c["Ti"]; c["CrAl2SiO6"] = c["Cr"]
        c["FmAl2SiO6"] = np.clip(c["AlVI"] - c["NaAlSi2O6"] - c["CrAl2SiO6"], 0, None); c["CaFmSi2O6"] = c["Ca"]
        c["Fm2Si2O6"] = (c["Fe"] + c["Mn"] + c["Mg"] - c["FmTiAlSiO6"] - c["FmAl2SiO6"] - c["CaFmSi2O6"]) / 2
        f = c["Mg"] / (c["Mg"] + c["Fe"] + c["Mn"]); c["En"] = c["Fm2Si2O6"] * f; c["Di"] = c["CaFmSi2O6"] * f; c["EnFs"] = _pos(c["Fm2Si2O6"])
        c["aEn"] = (0.5 * c["Mg"] / (c["Ca"] + 0.5 * c["Mg"] + 0.5 * c["Fe2"] + c["Mn"] + c["Na"])) *                    (0.5 * c["Mg"] / (0.5 * c["Fe2"] + c["Fe3"] + c["AlVI"] + c["Ti"] + c["Cr"] + 0.5 * c["Mg"]))
    return c


def _cpx2(ox):
    """Clinopyroxene terms for Eqs 36-39: Table 3 components, Mg#, X(Di) = DiHd Mg/(Mg + Fe + Mn), a(Di) (text below Eq 39)."""
    c = cpx(ox); k = _px_cations(ox)
    with np.errstate(all="ignore"):
        c["Mg#"] = c["Mg"] / (c["Mg"] + c["Fe"]); c["Di"] = c["DiHd"] * c["Mg"] / (c["Mg"] + c["Fe"] + c["Mn"])
        c["aDi"] = c["Ca"] / (c["Ca"] + 0.5 * c["Mg"] + 0.5 * k["Fe2"] + c["Mn"] + c["Na"])
    return c


def two_px_t36(cpx_ox, opx_ox, p_kbar):
    """Putirka (2008) Eq 36, two-pyroxene T, all compositions (+-60 C)."""
    c, o = _cpx2(cpx_ox), opx(opx_ox); P = np.asarray(p_kbar, float)
    with np.errstate(all="ignore"):
        r = (11.2 - 1.96 * np.log(c["EnFs"] / o["EnFs"]) - 3.3 * c["Ca"] - 25.8 * c["CrCaTs"] + 33.2 * o["Mn"] - 23.6 * o["Na"]
             - 2.08 * o["En"] - 8.33 * o["Di"] - 0.05 * P)
        return 1e4 / r  # printed as 1e4/T(C); checked: agrees with Brey & Kohler (1990) within +-30 C, the K reading does not


def two_px_t37(cpx_ox, opx_ox, p_kbar):
    """Putirka (2008) Eq 37, two-pyroxene T for Mg# cpx > 0.75 (+-38 C)."""
    c, o = _cpx2(cpx_ox), opx(opx_ox); P = np.asarray(p_kbar, float)
    with np.errstate(all="ignore"):
        r = (13.4 - 3.4 * np.log(c["EnFs"] / o["EnFs"]) + 5.59 * np.log(_pos(c["Mg"])) - 8.8 * c["Mg#"] + 23.85 * o["Mn"] + 6.48 * o["FmAl2SiO6"]
             - 2.38 * c["Di"] - 0.044 * P)
        return 1e4 / r  # T in C, as printed


def two_px_p38(cpx_ox, opx_ox):
    """Putirka (2008) Eq 38, two-pyroxene P without T (Mercier et al. 1984 form; Mg# cpx > 0.75), +-3.7 kbar."""
    c, o = _cpx2(cpx_ox), opx(opx_ox)
    with np.errstate(all="ignore"):
        kf = _pos(o["Ca"] / _pos(1 - c["Ca"]))
        return (-279.8 + 293 * o["AlVI"] + 455 * o["Na"] + 229 * o["Cr"] + 519 * o["Fm2Si2O6"] - 563 * o["En"] + 371 * o["Di"]
                + 327 * o["aEn"] + 1.19 / kf)


def two_px_p39(cpx_ox, opx_ox, t_c):
    """Putirka (2008) Eq 39, two-pyroxene P with T (C) as input, +-2.8 kbar."""
    c, o = _cpx2(cpx_ox), opx(opx_ox); T = np.asarray(t_c, float)
    with np.errstate(all="ignore"):
        kf = _pos(o["Ca"] / _pos(1 - c["Ca"]))
        return (-94.25 + 0.045 * T + 187.7 * o["AlVI"] + 246.8 * o["Fm2Si2O6"] - 212.5 * o["En"] + 127.5 * o["aEn"] - 1.66 / kf
                - 69.4 * c["EnFs"] - 133.9 * c["aDi"])


# ---------------------------------------------------------------- liquid (glass) and olivine-liquid
def glass_t13(liq_ox):
    """Eq 13: T(C) = 26.3 MgO(liq) + 994.4 (olivine-saturated liquids)."""
    return 26.3 * _g(liq_ox, "MgO") + 994.4


def glass_t15(liq_ox, p_kbar, h2o=0.0):
    """Eq 15: T(C) = 815.3 + 265.5 Mg#(liq) + 15.37 MgO + 8.61 FeO + 6.646 (Na2O + K2O) + 39.16 P(GPa) - 12.83 H2O (wt%)."""
    X = liquid(liq_ox)
    return (815.3 + 265.5 * X["Mg#"] + 15.37 * _g(liq_ox, "MgO") + 8.61 * _g(liq_ox, "FeO") + 6.646 * (_g(liq_ox, "Na2O") + _g(liq_ox, "K2O"))
            + 39.16 * _gpa(p_kbar) - 12.83 * np.nan_to_num(np.asarray(h2o, float)))


def d_mg_beattie(liq_ox):
    """Eq 20: D(Mg) olivine/liquid predicted from the liquid alone (Beattie 1993), for the T at which the liquid saturates in olivine."""
    X = liquid(liq_ox)
    return (0.666 - (-0.049 * X["MnO"] + 0.027 * X["FeO"])) / (X["MgO"] + 0.259 * X["MnO"] + 0.299 * X["FeO"])


def d_mg_from_fo(liq_ox, fo):
    """D(Mg) = X_MgO(ol)/X_MgO(liq) in cation fractions; olivine X_MgO = (2/3) Fo, Fo as a fraction or % (Mn, Ca, Ni in olivine neglected)."""
    f = np.asarray(fo, float); f = np.where(f > 1, f / 100, f)
    return (2 / 3) * f / liquid(liq_ox)["MgO"]


def ol_beattie(liq_ox, p_kbar, fo=None):
    """Eq 19 (Beattie 1993): T(C) = [13603 + 4.943e-7 (P(GPa) 1e9 - 1e5)] / [6.26 + 2 ln D(Mg) + 2 ln(1.5 C_NM) + 2 ln(3 C_SiO2) - NF] - 273.15.
    D(Mg) from the olivine Fo, or from Eq 20 when no olivine is given (liquidus temperature). Best for anhydrous liquids."""
    X = liquid(liq_ox); d = d_mg_from_fo(liq_ox, fo) if fo is not None else d_mg_beattie(liq_ox)
    with np.errstate(all="ignore"):
        return ((13603 + 4.943e-7 * (_gpa(p_kbar) * 1e9 - 1e5)) /
                (6.26 + 2 * np.log(d) + 2 * np.log(1.5 * X["C_NM"]) + 2 * np.log(3 * X["C_SiO2"]) - X["NF"]) - K0)


def ol_putirka22(liq_ox, p_kbar, h2o=0.0, fo=None):
    """Eq 22 (Putirka et al. 2007): T(C) = [15294.6 + 1318.8 P + 2.4834 P^2] / [8.048 + 2.8352 ln D(Mg) + 2.097 ln(1.5 C_NM) + 2.575 ln(3 C_SiO2)
    - 1.41 NF + 0.222 H2O + 0.5 P], P in GPa, H2O in wt%. Best when the liquid holds water."""
    X = liquid(liq_ox); d = d_mg_from_fo(liq_ox, fo) if fo is not None else d_mg_beattie(liq_ox); P = _gpa(p_kbar)
    w = np.nan_to_num(np.asarray(h2o, float))
    with np.errstate(all="ignore"):
        return ((15294.6 + 1318.8 * P + 2.4834 * P ** 2) /
                (8.048 + 2.8352 * np.log(d) + 2.097 * np.log(1.5 * X["C_NM"]) + 2.575 * np.log(3 * X["C_SiO2"]) - 1.41 * X["NF"] + 0.222 * w + 0.5 * P))


def ol_kd(liq_ox, fo):
    """KD(Fe-Mg) olivine-liquid = (X_Fe/X_Mg)ol / (X_Fe/X_Mg)liq, all iron as Fe2+; equilibrium is 0.30 +- 0.03 (Roeder & Emslie 1970)."""
    f = np.asarray(fo, float); f = np.where(f > 1, f / 100, f); X = liquid(liq_ox)
    with np.errstate(all="ignore"): return ((1 - f) / f) / (X["FeO"] / X["MgO"])


def fo_equilibrium(liq_ox, kd=0.30):
    """Forsterite (%) of olivine in equilibrium with the liquid for a given KD (the Rhodes diagram line)."""
    X = liquid(liq_ox)
    with np.errstate(all="ignore"): return 100 / (1 + kd * X["FeO"] / X["MgO"])


# ---------------------------------------------------------------- plagioclase-liquid
def _an_ab(an, orr=0.0):
    a = np.asarray(an, float); a = np.where(a > 1, a / 100, a); o = np.asarray(orr, float); o = np.where(o > 1, o / 100, o)
    return a, np.clip(1 - a - np.nan_to_num(o), 0, None)


def plag_t24a(liq_ox, an, p_kbar, h2o=0.0, orr=0.0):
    """Eq 24a: 10^4/T(K) = 6.4706 + 0.3128 ln[X_An/(X_CaO X_AlO1.5^2 X_SiO2^2)] - 8.103 X_SiO2 + 4.872 X_KO0.5 + 1.5346 X_Ab^2 + 8.661 X_SiO2^2
    - 3.341e-2 P(kbar) + 0.18047 H2O. X_An = Ca/(Ca + Na + K) of the plagioclase; liquid in anhydrous cation fractions."""
    X = liquid(liq_ox); xan, xab = _an_ab(an, orr); w = np.nan_to_num(np.asarray(h2o, float))
    with np.errstate(all="ignore"):
        r = (6.4706 + 0.3128 * np.log(xan / (X["CaO"] * X["AlO1.5"] ** 2 * X["SiO2"] ** 2)) - 8.103 * X["SiO2"] + 4.872 * X["KO0.5"]
             + 1.5346 * xab ** 2 + 8.661 * X["SiO2"] ** 2 - 3.341e-2 * np.asarray(p_kbar, float) + 0.18047 * w)
        return 1e4 / r - K0


def plag_h2o_25b(liq_ox, an, t_c, p_kbar, orr=0.0):
    """Eq 25b hygrometer: H2O (wt%) = 25.95 - 0.0032 T(C) ln[X_An/(X_CaO X_AlO1.5^2 X_SiO2^2)] - 18.9 X_KO0.5 + 14.5 X_MgO - 40.3 X_CaO
    + 5.7 X_An^2 + 0.108 P(kbar). Needs T known independently (e.g. olivine or clinopyroxene thermometry)."""
    X = liquid(liq_ox); xan, xab = _an_ab(an, orr)
    with np.errstate(all="ignore"):
        return (25.95 - 0.0032 * np.asarray(t_c, float) * np.log(xan / (X["CaO"] * X["AlO1.5"] ** 2 * X["SiO2"] ** 2)) - 18.9 * X["KO0.5"]
                + 14.5 * X["MgO"] - 40.3 * X["CaO"] + 5.7 * xan ** 2 + 0.108 * np.asarray(p_kbar, float))


def plag_kd(liq_ox, an, orr=0.0):
    """KD(An-Ab) plagioclase-liquid = X_Ab X_AlO1.5 X_CaO / (X_An X_NaO0.5 X_SiO2): 0.10 +- 0.05 below 1050 C, 0.27 +- 0.11 above."""
    X = liquid(liq_ox); xan, xab = _an_ab(an, orr)
    with np.errstate(all="ignore"): return xab * X["AlO1.5"] * X["CaO"] / (xan * X["NaO0.5"] * X["SiO2"])


# ---------------------------------------------------------------- clinopyroxene-liquid and clinopyroxene only
def cpx_p30(liq_ox, cpx_ox, t_c, h2o=0.0):
    """Eq 30: P(kbar) = -48.7 + 271 T/1e4 + 32 T/1e4 ln[X_Jd/(X_NaO0.5 X_AlO1.5 X_SiO2^2)] - 8.2 ln X_FeO + 4.6 ln X_MgO - 0.96 ln X_KO0.5
    - 2.2 ln X_DiHd - 31 Mg#(liq) + 56 (X_NaO0.5 + X_KO0.5) + 0.76 H2O, T in K."""
    X, c = liquid(liq_ox), cpx(cpx_ox); T = np.asarray(t_c, float) + K0; w = np.nan_to_num(np.asarray(h2o, float))
    with np.errstate(all="ignore"):
        return (-48.7 + 271 * T / 1e4 + 32 * T / 1e4 * np.log(c["Jd"] / (X["NaO0.5"] * X["AlO1.5"] * X["SiO2"] ** 2)) - 8.2 * np.log(X["FeO"])
                + 4.6 * np.log(X["MgO"]) - 0.96 * np.log(X["KO0.5"]) - 2.2 * np.log(c["DiHd"]) - 31 * X["Mg#"] + 56 * (X["NaO0.5"] + X["KO0.5"]) + 0.76 * w)


def cpx_p31(liq_ox, cpx_ox, t_c, h2o=0.0):
    """Eq 31: P(kbar) = -40.73 + 358 T/1e4 + 21.69 T/1e4 ln[X_Jd/(X_NaO0.5 X_AlO1.5 X_SiO2^2)] - 105.7 X_CaO - 165.5 (X_NaO0.5 + X_KO0.5)^2
    - 50.15 X_SiO2 (X_FeO + X_MgO) - 3.178 ln X_DiHd - 2.205 ln X_EnFs + 0.864 ln X_Al(cpx) + 0.3962 H2O, T in K."""
    X, c = liquid(liq_ox), cpx(cpx_ox); T = np.asarray(t_c, float) + K0; w = np.nan_to_num(np.asarray(h2o, float))
    with np.errstate(all="ignore"):
        return (-40.73 + 358 * T / 1e4 + 21.69 * T / 1e4 * np.log(c["Jd"] / (X["NaO0.5"] * X["AlO1.5"] * X["SiO2"] ** 2)) - 105.7 * X["CaO"]
                - 165.5 * (X["NaO0.5"] + X["KO0.5"]) ** 2 - 50.15 * X["SiO2"] * (X["FeO"] + X["MgO"]) - 3.178 * np.log(c["DiHd"])
                - 2.205 * np.log(c["EnFs"]) + 0.864 * np.log(c["Al"]) + 0.3962 * w)


def cpx_t33(liq_ox, cpx_ox, p_kbar, h2o=0.0):
    """Eq 33: 10^4/T(K) = 7.53 - 0.14 ln[X_Jd X_CaO X_Fm/(X_DiHd X_Na X_Al)] + 0.07 H2O - 14.9 X_CaO X_SiO2 - 0.08 ln X_TiO2 - 3.62 (X_NaO0.5 + X_KO0.5)
    - 1.1 Mg#(liq) - 0.18 ln X_EnFs - 0.027 P(kbar); X_Fm = X_FeO + X_MgO, X_Na = X_NaO0.5, X_Al = X_AlO1.5 of the liquid."""
    X, c = liquid(liq_ox), cpx(cpx_ox); w = np.nan_to_num(np.asarray(h2o, float))
    with np.errstate(all="ignore"):
        r = (7.53 - 0.14 * np.log(c["Jd"] * X["CaO"] * (X["FeO"] + X["MgO"]) / (c["DiHd"] * X["NaO0.5"] * X["AlO1.5"])) + 0.07 * w
             - 14.9 * X["CaO"] * X["SiO2"] - 0.08 * np.log(X["TiO2"]) - 3.62 * (X["NaO0.5"] + X["KO0.5"]) - 1.1 * X["Mg#"]
             - 0.18 * np.log(c["EnFs"]) - 0.027 * np.asarray(p_kbar, float))
        return 1e4 / r - K0


def cpx_kd(liq_ox, cpx_ox):
    """KD(Fe-Mg) clinopyroxene-liquid = (Fe/Mg)cpx/(Fe/Mg)liq, total Fe; 0.28 +- 0.08 at equilibrium (Putirka 2008)."""
    X, c = liquid(liq_ox), cpx(cpx_ox)
    with np.errstate(all="ignore"): return (c["Fe"] / c["Mg"]) / (X["FeO"] / X["MgO"])


def cpx_kd_expected(t_c):
    """Eq 35: ln KD(Fe-Mg)cpx-liq = -0.107 - 1719/T(K)."""
    return np.exp(-0.107 - 1719 / (np.asarray(t_c, float) + K0))


def cpx_p32a(cpx_ox, t_c):
    """Eq 32a (clinopyroxene only): P(kbar) = 3205 + 0.384 T - 518 ln T - 5.62 X_Mg + 83.2 X_Na + 68.2 X_DiHd + 2.52 ln X_AlVI - 51.1 X_DiHd^2
    + 34.8 X_EnFs^2, T in K, cations on 6 O. Tends to read low for hydrous magmas."""
    c = cpx(cpx_ox); T = np.asarray(t_c, float) + K0
    with np.errstate(all="ignore"):
        return (3205 + 0.384 * T - 518 * np.log(T) - 5.62 * c["Mg"] + 83.2 * c["Na"] + 68.2 * c["DiHd"] + 2.52 * np.log(c["AlVI"])
                - 51.1 * c["DiHd"] ** 2 + 34.8 * c["EnFs"] ** 2)


def cpx_t32d(cpx_ox, p_kbar):
    """Eq 32d (clinopyroxene only): T(K) = (93100 + 544 P) / [61.1 + 36.6 X_Ti + 10.9 X_Fe - 0.95 (X_Al + X_Cr - X_Na - X_K) + 0.395 (ln a_En)^2],
    a_En = (1 - Ca - Na - K)(1 - 0.5 (Al + Cr + Na + K)), cations on 6 O."""
    c = cpx(cpx_ox); a = (1 - c["Ca"] - c["Na"] - c["K"]) * (1 - 0.5 * (c["Al"] + c["Cr"] + c["Na"] + c["K"]))
    with np.errstate(all="ignore"):
        return (93100 + 544 * np.asarray(p_kbar, float)) / (61.1 + 36.6 * c["Ti"] + 10.9 * c["Fe"] - 0.95 * (c["Al"] + c["Cr"] - c["Na"] - c["K"])
                                                           + 0.395 * np.log(a) ** 2) - K0


def nimis_taylor_p(cpx_ox, t_c):
    """Nimis & Taylor (2000) Cr-in-clinopyroxene barometer, Eqs 9-10, for garnet peridotite cpx (cations on 6 O):
    P(kbar) = -T/126.9 ln a_CaCrTs + 15.483 ln(Cr#/T) + T/71.38 + 107.8, a_CaCrTs = Cr - 0.81 Cr# Na, Cr# = Cr/(Cr + Al), T in K."""
    c = cpx(cpx_ox); T = np.asarray(t_c, float) + K0
    with np.errstate(all="ignore"):
        crn = c["Cr"] / (c["Cr"] + c["Al"]); a = c["Cr"] - 0.81 * crn * c["Na"]
        return -T / 126.9 * np.log(a) + 15.483 * np.log(crn / T) + T / 71.38 + 107.8


def nimis_taylor_t(cpx_ox, p_kbar):
    """Nimis & Taylor (2000) enstatite-in-clinopyroxene thermometer, Eqs 15 and 17:
    T(K) = (23166 + 39.28 P) / [13.25 + 15.35 Ti + 4.50 Fe - 1.55 (Al + Cr - Na) + (ln a_en)^2], a_en = (1 - Ca - Na)(1 - 0.5 (Al + Cr + Na))."""
    c = cpx(cpx_ox); a = (1 - c["Ca"] - c["Na"]) * (1 - 0.5 * (c["Al"] + c["Cr"] + c["Na"]))
    with np.errstate(all="ignore"):
        return (23166 + 39.28 * np.asarray(p_kbar, float)) / (13.25 + 15.35 * c["Ti"] + 4.50 * c["Fe"] - 1.55 * (c["Al"] + c["Cr"] - c["Na"]) + np.log(a) ** 2) - K0


def _demo():
    near = lambda a, b, tol: abs(float(a) - b) <= tol
    # Putirka (2008) Table 1: liquid cation fractions and Beattie components
    liq = {"SiO2": 47.05, "TiO2": 0.89, "Al2O3": 16.11, "FeO": 7.96, "MnO": 0.15, "MgO": 12.78, "CaO": 11.13, "Na2O": 2.18, "K2O": 0.04}
    X = liquid(liq)
    for k, v in (("SiO2", 0.4327), ("TiO2", 0.0062), ("AlO1.5", 0.1746), ("FeO", 0.0612), ("MgO", 0.1752), ("CaO", 0.1096), ("NaO0.5", 0.0389)):
        assert near(X[k], v, 6e-5), (k, X[k], v)
    assert near(X["C_NM"], 0.3472, 2e-4) and near(X["NF"], -0.7148, 6e-4), (X["C_NM"], X["NF"])
    # Putirka (2008) Table 3: clinopyroxene cations on 6 O and components
    cx = {"SiO2": 52.5, "TiO2": 0.33, "Al2O3": 1.58, "FeO": 9.89, "MnO": 0.24, "MgO": 13.29, "CaO": 22.5, "Na2O": 0.37, "K2O": 0, "Cr2O3": 0.05}
    c = cpx(cx)
    for k, v in (("Si", 1.9553), ("Al", 0.0694), ("Fe", 0.3080), ("Mg", 0.7379), ("Ca", 0.8978), ("Na", 0.0267), ("Sum", 4.0134), ("AlIV", 0.0447),
                 ("AlVI", 0.0247), ("Jd", 0.0247), ("CaTs", 0.0), ("CaTi", 0.0223), ("CrCaTs", 0.0007), ("DiHd", 0.8747), ("EnFs", 0.0856)):
        assert near(c[k], v, 2e-4), (k, c[k], v)
    # the Table 1 basalt: olivine liquidus near 1300 C at 1 atm (Beattie) and the glass thermometers agree within their errors
    tb = ol_beattie(liq, 0.001); t22 = ol_putirka22(liq, 0.001); t13 = glass_t13(liq)
    assert 1250 < tb < 1350 and abs(t22 - tb) < 60 and abs(t13 - tb) < 100, (tb, t22, t13)
    assert ol_beattie(liq, 10) > tb and ol_putirka22(liq, 0.001, h2o=3) < t22  # pressure raises, water lowers the liquidus
    fo = fo_equilibrium(liq); assert near(ol_kd(liq, fo), 0.30, 1e-9) and 88 < fo < 91, fo
    assert near(ol_beattie(liq, 0.001, fo=fo), ol_beattie(liq, 0.001, fo=float(d_mg_beattie(liq) * X["MgO"] * 1.5)), 5)
    # plagioclase: An75 with this basalt at 1 atm, dry, gives a basaltic temperature; water lowers it; the hygrometer inverts it
    tp = plag_t24a(liq, 75, 0.001); assert 1150 < tp < 1300, tp
    w = plag_h2o_25b(liq, 75, tp - 100, 1.0); assert w > plag_h2o_25b(liq, 75, tp, 1.0)  # colder for the same pair: wetter
    # clinopyroxene-liquid: T from Eq 33 and P from Eq 30 are consistent and sensible for the Table 1 liquid and Table 3 cpx
    t33 = cpx_t33(liq, cx, 5.0); p30 = cpx_p30(liq, cx, t33); assert 1050 < t33 < 1350 and -10 < p30 < 20, (t33, p30)
    assert cpx_t33(liq, cx, 15.0) > t33 and cpx_p30(liq, cx, t33 + 50) > p30  # higher P -> higher T, and the reverse
    # the two example analyses are not a natural pair: KD = (0.3080/0.7379)/(0.0612/0.1752) = 1.19, far from 0.28, so the test flags them
    assert near(cpx_kd(liq, cx), (0.3080 / 0.7379) / (X["FeO"] / X["MgO"]), 2e-3) and cpx_kd(liq, cx) > 0.28 + 3 * 0.08
    assert near(cpx_kd_expected(1200), np.exp(-0.107 - 1719 / 1473.15), 1e-12)
    # cpx-only: Eq 32d at the Eq 32a pressure; Nimis & Taylor on a garnet-lherzolite cpx (Cr2O3 1.5, Na2O 1.8)
    gl = {"SiO2": 54.5, "TiO2": 0.15, "Al2O3": 2.6, "Cr2O3": 1.5, "FeO": 2.4, "MnO": 0.08, "MgO": 16.5, "CaO": 20.0, "Na2O": 1.8}
    tn = nimis_taylor_t(gl, 40.0); pn = nimis_taylor_p(gl, tn); assert 900 < tn < 1300 and 20 < pn < 60, (tn, pn)
    assert nimis_taylor_p(gl, tn + 100) > pn  # Cr isopleths: higher T, higher P (about 2 kbar per 50 C)
    print("VOLCANIC OK")


if __name__ == "__main__":
    _demo()
