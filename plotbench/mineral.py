"""Mineral formulae from oxide analyses (electron microprobe): cations per formula unit on an oxygen basis, with Fe3+
estimated by charge balance (Droop 1987, Mineralogical Magazine 51, 431-435), and common end-member fractions.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import re

import numpy as np

# oxide: (molar mass g/mol, cations per oxide, oxygens per oxide, cation, charge)
OXIDES = {
    "SiO2": (60.0843, 1, 2, "Si", 4), "TiO2": (79.8658, 1, 2, "Ti", 4), "Al2O3": (101.9613, 2, 3, "Al", 3), "Cr2O3": (151.9904, 2, 3, "Cr", 3),
    "V2O3": (149.8812, 2, 3, "V", 3), "Fe2O3": (159.6882, 2, 3, "Fe3+", 3), "FeO": (71.8444, 1, 1, "Fe2+", 2), "MnO": (70.9374, 1, 1, "Mn", 2),
    "MgO": (40.3044, 1, 1, "Mg", 2), "CaO": (56.0774, 1, 1, "Ca", 2), "NiO": (74.6928, 1, 1, "Ni", 2), "ZnO": (81.3794, 1, 1, "Zn", 2),
    "BaO": (153.3264, 1, 1, "Ba", 2), "SrO": (103.6194, 1, 1, "Sr", 2), "Na2O": (61.9789, 2, 1, "Na", 1), "K2O": (94.1960, 2, 1, "K", 1),
    "P2O5": (141.9445, 2, 5, "P", 5),
}
# mineral: (oxygens, cations for Fe3+ by charge balance or None)
MINERALS = {"Olivine": (4, None), "Pyroxene": (6, 4), "Garnet": (12, 8), "Spinel": (4, 3), "Magnetite": (4, 3), "Feldspar": (8, "all3"),
            "Amphibole": (23, "amphibole_hb94"), "Mica": (22, None), "Ilmenite": (3, 2), "Hematite": (3, "all3"), "Epidote": (12.5, "all3"),
            "Chlorite": (28, None), "Cordierite": (18, None), "Staurolite": (46, None), "Titanite": (5, "all3"), "Custom": (None, None)}


def _bare(name):
    """A header without a leading unit, as some microprobe exports write it ('Wt% SiO2', 'Mass% FeO', 'wt.% MgO')."""
    return re.sub(r"^\s*(wt\.?\s*%|mass\s*%|oxide\s*%)\s*[_:\-]?\s*", "", str(name), flags=re.I).strip()


def oxide_of(name):
    """'SiO2', 'SiO2 (wt%)', 'feo', 'FeOt', 'FeO*', 'FeOT' -> oxide key; FeO total is treated as FeO. None if not an oxide."""
    s = _bare(name)
    if re.match(r"FeO(t|\*|tot|total)?(?![a-z0-9])", s, re.I): return "FeO"
    if re.match(r"Fe2O3(t|\*|tot|total)(?![a-z0-9])", s, re.I): return "FeO"  # total iron as Fe2O3: use as FeO (x to_feo)
    for k in sorted(OXIDES, key=len, reverse=True):
        if re.match(rf"{re.escape(k)}(?![a-z0-9])", s, re.I): return k
    return None


FE3_METHODS = {"None (all Fe as Fe2+)": "none", "Charge balance (Droop 1987)": "droop",
               "Amphibole: Holland & Blundy (1994) scheme": "amphibole_hb94", "Amphibole: mean of 13eCNK and 15eNK": "amphibole", "All Fe as Fe3+ (feldspar, epidote, hematite)": "all3",
               "Fixed Fe3+/total Fe ratio": "ratio"}


def method_name(t):
    if t == "amphibole_hb94": return "Amphibole: Holland & Blundy (1994) scheme"
    if t == "amphibole": return "Amphibole: mean of 13eCNK and 15eNK"
    if t == "all3": return "All Fe as Fe3+ (feldspar, epidote, hematite)"
    if isinstance(t, str) and t.startswith("ratio"): return "Fixed Fe3+/total Fe ratio"
    return "Charge balance (Droop 1987)" if t else "None (all Fe as Fe2+)"


def basis_text(oxygens, cation_total):
    t = cation_total
    fe = ("Fe3+ by the Holland & Blundy (1994, Appendix B) scheme (amphibole)" if t == "amphibole_hb94"
          else "Fe3+ from the mean of the 13eCNK and 15eNK normalisations (amphibole)" if t == "amphibole"
          else "all Fe as Fe3+" if t == "all3"
          else f"Fe3+/total Fe fixed at {float(t.split(':')[1]):g}" if isinstance(t, str) and t.startswith("ratio")
          else f"Fe3+ by charge balance to {t:g} cations (Droop 1987)" if t else "all Fe as Fe2+")
    return f"{oxygens:g} oxygens; {fe}"


FEO_TO_FE2O3 = 159.6882 / (2 * 71.8444)  # wt% FeO -> wt% Fe2O3 for the same iron (1.1113)


def _split_iron(wt, ratio):
    """Recast FeO (total iron) as Fe2O3 for a fraction 'ratio' of the iron, before the oxygen normalisation."""
    wt = dict(wt)
    if "FeO" in wt:
        fe = np.nan_to_num(np.asarray(wt.pop("FeO"), float))
        wt["Fe2O3"] = np.nan_to_num(np.asarray(wt.get("Fe2O3", 0.0), float)) + ratio * fe * FEO_TO_FE2O3
        if ratio < 1: wt["FeO"] = (1 - ratio) * fe
    return wt


def apfu_text(c, basis):
    if c == "Sum": return f"sum of the cations ({basis})"
    return f"{c} = moles of its oxide x cations per oxide x {basis.split(' ')[0]} / total oxygen of all oxides ({basis})"


FORMULA_TEXT = {
    "Mg#": "100 Mg / (Mg + Fe2+)", "Fo": "100 Mg / (Mg + Fe + Mn)", "Fa": "100 - Fo",
    "Wo": "100 Ca / (Ca + Mg + Fe + Mn)", "En": "100 Mg / (Ca + Mg + Fe + Mn)", "Fs": "100 (Fe + Mn) / (Ca + Mg + Fe + Mn)",
    "An": "100 Ca / (Ca + Na + K)", "Ab": "100 Na / (Ca + Na + K)", "Or": "100 K / (Ca + Na + K)",
    "Alm": "100 Fe2+ / (Fe2+ + Mg + Mn + Ca)", "Prp": "100 Mg / (Fe2+ + Mg + Mn + Ca)", "Sps": "100 Mn / (Fe2+ + Mg + Mn + Ca)",
    "Adr": "100 Ca / (Fe2+ + Mg + Mn + Ca) x Fe3+ / (Fe3+ + Al + Cr)", "Uv": "100 Ca / (Fe2+ + Mg + Mn + Ca) x Cr / (Fe3+ + Al + Cr)",
    "Grs": "100 Ca / (Fe2+ + Mg + Mn + Ca) - Adr - Uv", "Cr#": "100 Cr / (Cr + Al)", "Fe3+#": "100 Fe3+ / (Fe3+ + Cr + Al)",
    "Fe2+#": "100 Fe2+ / (Fe2+ + Mg)", "Ilm": "100 Fe2+ / (Fe2+ + Mg + Mn + Fe3+/2)", "Gk": "100 Mg / (Fe2+ + Mg + Mn + Fe3+/2)",
    "Pph": "100 Mn / (Fe2+ + Mg + Mn + Fe3+/2)", "Hem": "50 Fe3+ / (Fe2+ + Mg + Mn + Fe3+/2)",
    "T Si": "Si in the T site", "AlIV": "8 - Si (not more than Al)", "AlVI": "Al - AlIV", "C Ti": "Ti left after filling T to 8",
    "B Ca": "Ca in B after Mg, Fe2+, Mn left over from C (B = 2)", "B Na": "2 - B(Fe, Mg, Mn) - B Ca (not more than Na)",
    "A (Na+K)": "Na left after B + K", "Amphibole name": "Leake et al. (1997) calcic amphiboles from Si, A (Na+K) and Mg#",
    "Octahedral sum": "AlVI + Ti + Cr + Fe2+ + Fe3+ + Mn + Mg + Li", "Ann": "100 Fe / (Fe + Mg)", "Phl": "100 Mg / (Fe + Mg)",
    "Ms": "100 K / (K + Na + Ca + Ba)", "Pg": "100 Na / (K + Na + Ca + Ba)", "Mrg": "100 Ca / (K + Na + Ca + Ba)",
    "Mica group": "trioctahedral if octahedral sum >= 5, dioctahedral if <= 4.5",
}


def to_feo(name):
    """Factor that turns a column into FeO wt%: 0.8998 for total iron reported as Fe2O3 (Fe2O3t, Fe2O3*), else 1."""
    return 0.8998 if re.match(r"\s*Fe2O3(t|\*|tot|total)(?![a-z0-9])", str(name), re.I) else 1.0


def collect_oxides(cols, arr, keep=None):
    """{oxide: wt% array} from the columns. Measured FeO and Fe2O3 come first; a total-iron column (FeOt, FeO*, Fe2O3t) is used, as
    FeO, only when there is no measured FeO, and then a measured Fe2O3 is left out (it is already in the total)."""
    out, total = {}, None
    for c in cols:
        k = oxide_of(c)
        if not k or (keep is not None and k not in keep): continue
        if re.match(r"\s*Fe(O|2O3)(t|\*|tot|total)(?![a-z0-9])", _bare(c), re.I):
            if total is None: total = c
            continue
        if k not in out: out[k] = arr(c)
    if total is not None and "FeO" not in out: out["FeO"] = arr(total) * to_feo(total); out.pop("Fe2O3", None)
    return out


def formula(wt, oxygens, cation_total=None):
    """wt: {oxide: array of wt%}. Returns {cation: apfu array} plus 'Sum'. With cation_total, Fe3+ and Fe2+ are split by
    charge balance (Droop 1987): Fe3+ = 2 X (1 - T / S), with X oxygens, T the ideal and S the computed cation total."""
    n = len(next(iter(wt.values())))
    if cation_total == "all3": wt, cation_total = _split_iron(wt, 1.0), None
    elif isinstance(cation_total, str) and cation_total.startswith("ratio:"):
        wt, cation_total = _split_iron(wt, float(cation_total.split(":")[1])), None
    mol_o = np.zeros(n); cat = {}
    for ox, v in wt.items():
        M, nc, no, c, _ = OXIDES[ox]; mol = np.nan_to_num(np.asarray(v, float)) / M
        mol_o += mol * no; cat[c] = cat.get(c, 0) + mol * nc
    with np.errstate(all="ignore"): f = oxygens / mol_o
    out = {c: v * f for c, v in cat.items()}
    if cation_total == "amphibole_hb94":
        if "Fe2+" in out: out = _amphibole_fe3_hb94(out)
        cation_total = None
    if cation_total == "amphibole":
        if "Fe2+" in out: out = _amphibole_fe3(out, oxygens)
        cation_total = None
    if cation_total and "Fe2+" in out:
        S = sum(out.values())
        # Fe3+ on the X-oxygen basis before renormalising; each Fe2+ -> Fe3+ adds half an oxygen, so rescale to X oxygens again.
        # Equals Droop's T/S scaling and F = 2X(1 - T/S) when 0 < F < Fe; no rescaling when S <= T (cation-deficient analyses).
        fe3_raw = np.clip(2 * oxygens * (S / cation_total - 1.0), 0.0, out["Fe2+"])
        k = oxygens / (oxygens + 0.5 * fe3_raw)
        out = {c: v * k for c, v in out.items()}; fe3 = fe3_raw * k
        out["Fe3+"] = out.get("Fe3+", 0) + fe3; out["Fe2+"] = out["Fe2+"] - fe3
    out["Sum"] = sum(v for c, v in out.items())
    return out


UNITS = {"Mg#": "", "Cr#": "", "Fe3+#": "", "Fe2+#": "", "AlIV": "apfu", "AlVI": "apfu", "Octahedral sum": "apfu", "T Si": "apfu",
         "B Ca": "apfu", "B Na": "apfu", "A (Na+K)": "apfu", "C Ti": "apfu", "Mica group": "", "Amphibole name": ""}


def unit_of(key): return UNITS.get(key, "%")


def amphibole_sites(apfu):
    """Site allocation on 23 O (Leake et al. 1997): T = Si + Al (+Fe3+, Ti) to 8; C = rest of Al, Ti, Fe3+, Cr, Mg, Fe2+, Mn to 5;
    B = rest of Fe2+, Mn, Mg, then Ca, Na to 2; A = remaining Na + K. Names for calcic amphiboles (B Ca >= 1.5) from Si, A and Mg#
    (Fe3+ only if given as Fe2O3 or estimated)."""
    g = lambda c: np.asarray(apfu.get(c, 0.0), float) * 1.0
    n = len(np.atleast_1d(g("Si")))
    si, al, ti, fe3, cr, mg, fe2, mn, ca, na, k = (np.broadcast_to(g(c), n).astype(float) for c in
                                                   ("Si", "Al", "Ti", "Fe3+", "Cr", "Mg", "Fe2+", "Mn", "Ca", "Na", "K"))
    aliv = np.clip(8 - si, 0, al); left = 8 - si - aliv
    fe3_t = np.clip(left, 0, fe3); left -= fe3_t; ti_t = np.clip(left, 0, ti)
    alvi, ti_c, fe3_c = al - aliv, ti - ti_t, fe3 - fe3_t
    room = 5 - (alvi + ti_c + fe3_c + cr)
    mg_c = np.clip(room, 0, mg); room -= mg_c; fe_c = np.clip(room, 0, fe2); room -= fe_c; mn_c = np.clip(room, 0, mn)
    b_fm = (mg - mg_c) + (fe2 - fe_c) + (mn - mn_c); b_ca = np.minimum(ca, np.clip(2 - b_fm, 0, None))
    b_na = np.clip(2 - b_fm - b_ca, 0, na); a = (na - b_na) + k
    with np.errstate(all="ignore"): mgn = mg / (mg + fe2)
    name = np.full(n, "", object)
    for i in range(n):
        if b_ca[i] + b_na[i] >= 1 and b_na[i] < 0.5:  # calcic group: (Ca+Na)B >= 1 and NaB < 0.5 (Leake et al. 1997)
            hi = mgn[i] >= 0.5
            if a[i] < 0.5:
                name[i] = ("tremolite" if mgn[i] >= 0.9 else "actinolite" if hi else "ferro-actinolite") if si[i] >= 7.5 else \
                    ("magnesio-hornblende" if hi else "ferro-hornblende") if si[i] >= 6.5 else ("tschermakite" if hi else "ferrotschermakite")
            elif si[i] >= 6.5: name[i] = "edenite" if hi else "ferro-edenite"
            elif ti[i] >= 0.5: name[i] = "kaersutite"
            elif alvi[i] >= fe3[i]: name[i] = "pargasite" if hi else "ferropargasite"
            else: name[i] = "magnesiohastingsite" if hi else "hastingsite"
        elif b_na[i] >= 1.5: name[i] = "sodic amphibole"
        elif b_ca[i] + b_na[i] >= 1 and 0.5 <= b_na[i] < 1.5: name[i] = "sodic-calcic amphibole"
        else: name[i] = "Mg-Fe-Mn amphibole"
    return {"T Si": si, "AlIV": aliv, "AlVI": alvi, "C Ti": ti_c, "B Ca": b_ca, "B Na": b_na, "A (Na+K)": a, "Amphibole name": name}


def _amphibole_fe3_hb94(out):
    """Holland & Blundy (1994, Appendix B): on 23 O with all Fe as FeO (cation sum S), the renormalising factor f is the average of
    fA = min(16/S, 8/Si, 15/(S - Na - K), 2/Ca, 1) and fB = max(8/(Si + Al), 15/(S - K), 12.9/(S - Na - K - Ca), 36/(46 - Al - Si - Ti),
    1 - Fe/46); then every cation is multiplied by f and Fe3+ = 46(1 - f). (The paper prints f9 = 36/(46 + Al + Si + Ti); the
    constraint it stands for, Fe3+ <= 2 - AlVI - Ti, gives 36/(46 - Al - Si - Ti).)"""
    g = lambda c: np.asarray(out.get(c, 0.0), float) * 1.0
    S = sum(np.asarray(v, float) for v in out.values()); si, al, ti, na, k, ca, fe = g("Si"), g("Al"), g("Ti"), g("Na"), g("K"), g("Ca"), g("Fe2+")
    with np.errstate(all="ignore"):
        fa = np.minimum.reduce([np.minimum(16 / S, 1), np.minimum(8 / si, 1), np.minimum(15 / (S - na - k), 1), np.minimum(np.where(ca > 0, 2 / ca, 1), 1),
                                np.ones_like(S)])
        fb = np.maximum.reduce([8 / (si + al), 15 / (S - k), 12.9 / (S - na - k - ca), 36 / (46 - al - si - ti), 1 - fe / 46])
    f = (fa + fb) / 2  # (fB > fA: the analysis cannot be made stoichiometric; f is still the mean, and the Fe3+ is clipped below)
    new = {c: np.asarray(v, float) * f for c, v in out.items()}
    fe3 = np.clip(46 * (1 - f), 0, new["Fe2+"])
    new["Fe3+"] = new.get("Fe3+", 0) + fe3; new["Fe2+"] = new["Fe2+"] - fe3
    return new


def _amphibole_fe3(out, oxygens):
    """Amphibole Fe3+ as the mean of two normalisations: 13 cations without Ca, Na, K
    (13eCNK) and 15 without Na, K (15eNK). Scaling the cations by k leaves 2X(1 - k) charges to be made up by Fe2+ -> Fe3+."""
    g = lambda c: out.get(c, 0.0); S = sum(out.values())
    res = []
    for n, skip in ((13.0, ("Ca", "Na", "K")), (15.0, ("Na", "K"))):
        sub = S - sum(g(c) for c in skip); sub = np.where(sub > 0, sub, np.nan)
        # as in formula(): Fe3+ on the oxygen basis, then rescale by the oxygen it adds; no scaling up when there are too few cations
        fe3_raw = np.clip(2 * oxygens * (sub / n - 1.0), 0.0, out["Fe2+"])
        k = oxygens / (oxygens + 0.5 * fe3_raw)
        res.append(({c: v * k for c, v in out.items()}, fe3_raw * k))
    new = {c: (res[0][0][c] + res[1][0][c]) / 2 for c in out}; fe3 = (res[0][1] + res[1][1]) / 2
    new["Fe3+"] = new.get("Fe3+", 0) + fe3; new["Fe2+"] = new["Fe2+"] - fe3
    return new


def end_members(mineral, apfu):
    """Common end-member percentages: olivine Fo/Fa, pyroxene Wo/En/Fs (Morimoto 1988), feldspar An/Ab/Or, garnet Alm/Prp/Sps/Grs/Adr/Uv,
    spinel Cr#, Fe3+# and Fe2+#, ilmenite Ilm/Gk/Pph/Hem, amphibole sites and name (Leake et al. 1997), mica Ann/Phl, Ms/Pg/Mrg
    and group, plus Mg#."""
    g = lambda c: np.asarray(apfu.get(c, 0.0), float)
    fe = g("Fe2+") + g("Fe3+"); out = {}
    with np.errstate(all="ignore"):
        out["Mg#"] = 100 * g("Mg") / (g("Mg") + g("Fe2+"))
        if mineral == "Olivine": out["Fo"] = 100 * g("Mg") / (g("Mg") + fe + g("Mn")); out["Fa"] = 100 - out["Fo"]
        if mineral == "Pyroxene":
            s = g("Ca") + g("Mg") + fe + g("Mn")
            out["Wo"], out["En"], out["Fs"] = 100 * g("Ca") / s, 100 * g("Mg") / s, 100 * (fe + g("Mn")) / s
        if mineral == "Garnet":
            # X site (Fe2+, Mg, Mn, Ca) gives Alm, Prp, Sps and the calcic share; the calcic share is split between andradite
            # and uvarovite by Fe3+ and Cr in the Y site (Fe3+ + Al + Cr), the rest is grossular.
            x = g("Fe2+") + g("Mg") + g("Mn") + g("Ca"); y = g("Fe3+") + g("Al") + g("Cr")
            out["Alm"], out["Prp"], out["Sps"] = 100 * g("Fe2+") / x, 100 * g("Mg") / x, 100 * g("Mn") / x
            ca = 100 * g("Ca") / x; out["Adr"], out["Uv"] = ca * g("Fe3+") / y, ca * g("Cr") / y; out["Grs"] = ca - out["Adr"] - out["Uv"]
        if mineral == "Spinel":
            out["Cr#"] = 100 * g("Cr") / (g("Cr") + g("Al")); out["Fe3+#"] = 100 * g("Fe3+") / (g("Fe3+") + g("Cr") + g("Al"))
            out["Fe2+#"] = 100 * g("Fe2+") / (g("Fe2+") + g("Mg"))
        if mineral == "Ilmenite":  # FeTiO3, MgTiO3, MnTiO3 and Fe2O3 (two Fe3+ per hematite unit)
            s = g("Fe2+") + g("Mg") + g("Mn") + g("Fe3+") / 2
            out["Ilm"], out["Gk"], out["Pph"], out["Hem"] = 100 * g("Fe2+") / s, 100 * g("Mg") / s, 100 * g("Mn") / s, 50 * g("Fe3+") / s
        if mineral == "Amphibole":
            out.update(amphibole_sites(apfu))
        if mineral == "Mica":
            si, al = g("Si"), g("Al"); aliv = np.clip(8 - si, 0, al); oct_ = (al - aliv) + g("Ti") + g("Cr") + g("Fe2+") + g("Fe3+") + g("Mn") + g("Mg") + g("Li")
            out["AlIV"], out["AlVI"], out["Octahedral sum"] = aliv, al - aliv, oct_
            out["Ann"], out["Phl"] = 100 * (g("Fe2+") + g("Fe3+")) / (g("Fe2+") + g("Fe3+") + g("Mg")), 100 * g("Mg") / (g("Fe2+") + g("Fe3+") + g("Mg"))
            il = g("K") + g("Na") + g("Ca") + g("Ba"); out["Ms"], out["Pg"], out["Mrg"] = 100 * g("K") / il, 100 * g("Na") / il, 100 * g("Ca") / il
            out["Mica group"] = np.where(oct_ >= 5.0, "trioctahedral (biotite)", np.where(oct_ <= 4.5, "dioctahedral (white mica)", "intermediate")).astype(object)
        if mineral == "Feldspar":
            s = g("Ca") + g("Na") + g("K"); out["An"], out["Ab"], out["Or"] = 100 * g("Ca") / s, 100 * g("Na") / s, 100 * g("K") / s
    return out


def _demo():
    d = {"Fe2O3t": 10.0, "FeO": 6.0, "Fe2O3": 3.0, "SiO2": 50.0}; g = lambda c: d[c]
    assert collect_oxides(list(d), g) == {"FeO": 6.0, "Fe2O3": 3.0, "SiO2": 50.0}  # measured iron wins over the total
    d2 = {"FeOt": 8.0, "Fe2O3": 3.0}; assert collect_oxides(list(d2), d2.get) == {"FeO": 8.0}  # total only: Fe2O3 is inside it
    d3 = {"Fe2O3t": 10.0}; assert abs(collect_oxides(list(d3), d3.get)["FeO"] - 8.998) < 1e-9
    """Forsterite, magnetite (Fe3+ by charge balance), albite, diopside, garnet, chromite and ilmenite."""
    # pyrope60 almandine30 grossular10 (Mg1.8 Fe0.9 Ca0.3 Al2 Si3 O12) from its oxide wt%
    M = {"SiO2": 60.08, "Al2O3": 101.96, "MgO": 40.30, "FeO": 71.84, "CaO": 56.08}
    mol = {"SiO2": 3, "Al2O3": 1, "MgO": 1.8, "FeO": 0.9, "CaO": 0.3}; tot = sum(mol[k] * M[k] for k in M)
    gt = formula({k: [100 * mol[k] * M[k] / tot] for k in M}, 12, 8); e = end_members("Garnet", gt)
    assert abs(e["Prp"][0] - 60) < 0.1 and abs(e["Alm"][0] - 30) < 0.1 and abs(e["Grs"][0] - 10) < 0.1 and abs(e["Adr"][0]) < 0.1, e
    sp = end_members("Spinel", {"Cr": np.array([1.2]), "Al": np.array([0.6]), "Fe3+": np.array([0.2]), "Fe2+": np.array([0.5]), "Mg": np.array([0.5])})
    assert abs(sp["Cr#"][0] - 66.667) < 0.01 and abs(sp["Fe3+#"][0] - 10) < 0.01 and abs(sp["Fe2+#"][0] - 50) < 0.01
    # tremolite Ca2Mg5Si8O22(OH)2 and pargasite NaCa2(Mg4Al)(Si6Al2)O22(OH)2 on 23 O
    tr = end_members("Amphibole", {"Si": np.array([8.0]), "Mg": np.array([5.0]), "Ca": np.array([2.0])})
    assert tr["Amphibole name"][0] == "tremolite" and abs(tr["B Ca"][0] - 2) < 1e-9 and abs(tr["A (Na+K)"][0]) < 1e-9
    pg = end_members("Amphibole", {"Si": np.array([6.0]), "Al": np.array([3.0]), "Mg": np.array([4.0]), "Ca": np.array([2.0]), "Na": np.array([1.0])})
    assert pg["Amphibole name"][0] == "pargasite" and abs(pg["AlIV"][0] - 2) < 1e-9 and abs(pg["A (Na+K)"][0] - 1) < 1e-9, pg
    # magnesiohastingsite NaCa2(Mg4Fe3+)(Si6Al2)O22(OH)2 analysed with all Fe as FeO: both normalisations give Fe3+ = 1
    M = {"SiO2": 60.08, "Al2O3": 101.96, "MgO": 40.30, "FeO": 71.84, "CaO": 56.08, "Na2O": 61.98}
    mol = {"SiO2": 6, "Al2O3": 1, "MgO": 4, "FeO": 1, "CaO": 2, "Na2O": 0.5}; tot = sum(mol[k] * M[k] for k in M)
    hs = formula({k: [100 * mol[k] * M[k] / tot] for k in M}, 23, "amphibole")
    assert abs(hs["Fe3+"][0] - 1) < 0.01 and abs(hs["Fe2+"][0]) < 0.01 and abs(hs["Si"][0] - 6) < 0.01, hs
    ep = formula({"FeO": [10.0], "SiO2": [38.0], "Al2O3": [24.0], "CaO": [23.0]}, 12.5, "all3")
    assert np.allclose(ep.get("Fe2+", 0), 0) and ep["Fe3+"][0] > 0.5, ep
    half = formula({"FeO": [20.0], "MgO": [20.0], "SiO2": [50.0]}, 6, "ratio:0.25")
    assert abs(half["Fe3+"][0] / (half["Fe3+"][0] + half["Fe2+"][0]) - 0.25) < 1e-9
    lo = formula({"SiO2": [50.0], "Al2O3": [8.0], "FeO": [8.0], "MgO": [14.0], "CaO": [12.0], "Na2O": [1.0]}, 23, "amphibole")
    base = formula({"SiO2": [50.0], "Al2O3": [8.0], "FeO": [8.0], "MgO": [14.0], "CaO": [12.0], "Na2O": [1.0]}, 23)
    assert np.allclose(lo["Fe3+"], 0) and abs(lo["Sum"][0] - base["Sum"][0]) < 1e-9, (lo["Sum"], base["Sum"])  # no scaling up
    sc = amphibole_sites({"Si": np.array([7.5]), "Mg": np.array([4.5]), "Fe2+": np.array([1.2]), "Ca": np.array([1.3]), "Na": np.array([0.3])})
    assert sc["Amphibole name"][0] == "actinolite", sc  # B Ca 1.3: still calcic
    # Holland & Blundy (1994) scheme: the magnesiohastingsite above (Fe3+ = 1 when recalculated) and a tremolite without Fe
    hs2 = formula({k: [100 * mol[k] * M[k] / tot] for k in M}, 23, "amphibole_hb94")
    assert 0.5 < hs2["Fe3+"][0] <= 1.0 + 1e-9 and abs(hs2["Fe2+"][0] + hs2["Fe3+"][0] - 1.0) < 0.05, hs2
    trm = formula({"SiO2": [59.17], "MgO": [24.81], "CaO": [13.81]}, 23, "amphibole_hb94")
    assert abs(trm["Si"][0] - 8) < 0.02 and np.allclose(trm.get("Fe3+", 0), 0)
    hb = end_members("Amphibole", {"Si": np.array([7.0]), "Al": np.array([1.2]), "Mg": np.array([3.5]), "Fe2+": np.array([1.3]), "Ca": np.array([1.9]),
                                   "Na": np.array([0.3]), "K": np.array([0.05])})
    assert hb["Amphibole name"][0] == "magnesio-hornblende", hb
    # phlogopite K2Mg6Al2Si6O20(OH)4 and muscovite K2Al4Al2Si6O20(OH)4 on 22 O
    ph = end_members("Mica", {"Si": np.array([6.0]), "Al": np.array([2.0]), "Mg": np.array([6.0]), "K": np.array([2.0])})
    ms = end_members("Mica", {"Si": np.array([6.0]), "Al": np.array([6.0]), "K": np.array([2.0])})
    assert ph["Mica group"][0].startswith("tri") and abs(ph["Phl"][0] - 100) < 1e-9 and ms["Mica group"][0].startswith("di") and abs(ms["Ms"][0] - 100) < 1e-9
    il = end_members("Ilmenite", {"Fe2+": np.array([0.8]), "Mg": np.array([0.1]), "Mn": np.array([0.0]), "Fe3+": np.array([0.2])})
    assert abs(il["Ilm"][0] - 80) < 0.01 and abs(il["Hem"][0] - 10) < 0.01 and abs(il["Gk"][0] - 10) < 0.01
    a = formula({"SiO2": [42.70], "MgO": [57.30]}, 4, 3); assert abs(a["Mg"][0] - 2) < 0.01 and abs(a["Si"][0] - 1) < 0.01
    fe_t = 3 * OXIDES["FeO"][0] / (3 * 55.845 + 4 * 15.999) * 100  # Fe3O4 analysed as FeO total
    m = formula({"FeO": [fe_t]}, 4, 3); assert abs(m["Fe3+"][0] - 2) < 0.01 and abs(m["Fe2+"][0] - 1) < 0.01, m
    ab = formula({"SiO2": [68.74], "Al2O3": [19.44], "Na2O": [11.82]}, 8); e = end_members("Feldspar", ab)
    assert abs(ab["Si"][0] - 3) < 0.01 and abs(e["Ab"][0] - 100) < 0.1
    di = formula({"SiO2": [55.49], "MgO": [18.61], "CaO": [25.90]}, 6, 4); e = end_members("Pyroxene", di)
    assert abs(e["Wo"][0] - 50) < 0.3 and abs(e["En"][0] - 50) < 0.3
    assert oxide_of("Fe2O3t") == "FeO" and to_feo("Fe2O3T") == 0.8998 and to_feo("Fe2O3") == 1.0 and oxide_of("feo") == "FeO"
    lo = formula({"SiO2": [44.0], "MgO": [46.0], "FeO": [9.0]}, 4, 3)  # cation-deficient (S < 3): no Fe3+, oxygen basis kept
    assert np.allclose(lo["Fe3+"], 0) and lo["Sum"][0] < 3
    assert oxide_of("FeOt") == "FeO" and oxide_of("Al2O3 (wt%)") == "Al2O3" and oxide_of("Mg#") is None and oxide_of("Fe2O3") == "Fe2O3"
    print("MINERAL OK")


if __name__ == "__main__": _demo()
