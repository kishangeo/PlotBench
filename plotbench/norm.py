"""CIPW norm (Cross, Iddings, Pirsson & Washington 1902) from whole-rock major oxides in wt%.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
The steps follow the standard sequence (Johannsen 1931; Kelsey 1965): accessory minerals first (apatite, chromite, ilmenite, titanite,
rutile), then feldspars, acmite, anorthite and corundum, magnetite and hematite, diopside, wollastonite and hypersthene. Any silica left
is quartz; a silica deficit is made up, in order, by hypersthene -> olivine, titanite -> perovskite, albite -> nepheline,
orthoclase -> leucite, wollastonite -> dicalcium silicate, diopside -> dicalcium silicate + olivine and leucite -> kaliophilite.
All amounts are molecular proportions (wt% / molar mass) until the end, when each mineral is weighed with its own molar mass;
Fe-Mg minerals are weighed with the Mg/(Mg+Fe) ratio of the rock. MnO is counted with FeO.
"""
import numpy as np

MW = {"SiO2": 60.0843, "TiO2": 79.8658, "Al2O3": 101.9613, "Fe2O3": 159.6882, "FeO": 71.8444, "MnO": 70.9374, "MgO": 40.3044,
      "CaO": 56.0774, "Na2O": 61.9789, "K2O": 94.1960, "P2O5": 141.9445, "Cr2O3": 151.9904}
OXIDES = list(MW)

# molar mass of each normative mineral as written in oxide units (e.g. Or = K2O.Al2O3.6SiO2)
_m = MW
MASS = {
    "Q": _m["SiO2"], "C": _m["Al2O3"], "Or": _m["K2O"] + _m["Al2O3"] + 6 * _m["SiO2"], "Ab": _m["Na2O"] + _m["Al2O3"] + 6 * _m["SiO2"],
    "An": _m["CaO"] + _m["Al2O3"] + 2 * _m["SiO2"], "Ne": _m["Na2O"] + _m["Al2O3"] + 2 * _m["SiO2"],
    "Lc": _m["K2O"] + _m["Al2O3"] + 4 * _m["SiO2"], "Kp": _m["K2O"] + _m["Al2O3"] + 2 * _m["SiO2"],
    "Ac": _m["Na2O"] + _m["Fe2O3"] + 4 * _m["SiO2"], "Ns": _m["Na2O"] + _m["SiO2"], "Ks": _m["K2O"] + _m["SiO2"],
    "Wo": _m["CaO"] + _m["SiO2"], "Cs": 2 * _m["CaO"] + _m["SiO2"], "Mt": _m["FeO"] + _m["Fe2O3"], "Hm": _m["Fe2O3"],
    "Il": _m["FeO"] + _m["TiO2"], "Tn": _m["CaO"] + _m["TiO2"] + _m["SiO2"], "Pf": _m["CaO"] + _m["TiO2"], "Ru": _m["TiO2"],
    "Ap": 10 / 3 * _m["CaO"] + _m["P2O5"], "Cm": _m["FeO"] + _m["Cr2O3"],
}
NAMES = {"Q": "quartz", "C": "corundum", "Or": "orthoclase", "Ab": "albite", "An": "anorthite", "Ne": "nepheline", "Lc": "leucite",
         "Kp": "kaliophilite", "Ac": "acmite", "Ns": "sodium metasilicate", "Ks": "potassium metasilicate", "Di": "diopside",
         "Wo": "wollastonite", "Cs": "dicalcium silicate", "Hy": "hypersthene", "Ol": "olivine", "Mt": "magnetite", "Hm": "hematite",
         "Il": "ilmenite", "Tn": "titanite", "Pf": "perovskite", "Ru": "rutile", "Ap": "apatite", "Cm": "chromite"}
ORDER = ["Q", "C", "Or", "Ab", "An", "Lc", "Ne", "Kp", "Ac", "Ns", "Ks", "Di", "Wo", "Cs", "Hy", "Ol", "Mt", "Hm", "Il", "Cm", "Tn", "Pf",
         "Ru", "Ap"]


def norm_one(ox):
    """One analysis {oxide: wt%} -> {mineral: wt%} (plus 'Di_Mg', 'Hy_Mg', 'Ol_Mg' = Mg/(Mg+Fe) used for the Fe-Mg minerals)."""
    p = {k: max(float(ox.get(k, 0.0) or 0.0), 0.0) / MW[k] for k in OXIDES}  # molecular proportions
    fe = p["FeO"] + p["MnO"]; fe3, mg, ca, na, k, al, ti, si = p["Fe2O3"], p["MgO"], p["CaO"], p["Na2O"], p["K2O"], p["Al2O3"], p["TiO2"], p["SiO2"]
    n = dict.fromkeys(MASS, 0.0); n.update(Di=0.0, Hy=0.0, Ol=0.0)
    # accessories
    n["Ap"] = min(p["P2O5"], max(ca, 0.0) * 0.3); ca -= 10 / 3 * n["Ap"]  # apatite cannot use more CaO than there is
    n["Cm"] = min(p["Cr2O3"], fe); fe -= n["Cm"]
    n["Il"] = min(fe, ti); fe -= n["Il"]; ti -= n["Il"]
    if ti > 0: n["Tn"] = min(ti, max(ca, 0)); ca -= n["Tn"]; ti -= n["Tn"]
    if ti > 0: n["Ru"] = ti
    # feldspars and the alkali excess
    n["Or"] = min(k, al); al -= n["Or"]; n["Ks"] = k - n["Or"]
    n["Ab"] = min(na, al); al -= n["Ab"]; na -= n["Ab"]
    if na > 0: n["Ac"] = min(na, fe3); fe3 -= n["Ac"]; na -= n["Ac"]; n["Ns"] = na
    if al > 0: n["An"] = min(al, max(ca, 0)); al -= n["An"]; ca -= n["An"]
    if al > 0: n["C"] = al
    # iron oxides
    n["Mt"] = min(fe3, fe); fe -= n["Mt"]; fe3 -= n["Mt"]; n["Hm"] = fe3
    # Ca-Mg-Fe silicates
    mf = mg + fe; xmg = mg / mf if mf > 0 else 1.0
    if ca > 0: n["Di"] = min(ca, mf); ca -= n["Di"]; mf -= n["Di"]
    if ca > 0: n["Wo"] = ca
    n["Hy"] = mf
    # silica balance
    used = (6 * n["Or"] + n["Ks"] + 6 * n["Ab"] + 4 * n["Ac"] + n["Ns"] + 2 * n["An"] + n["Tn"] + 2 * n["Di"] + n["Wo"] + n["Hy"])
    d = si - used
    if d >= 0: n["Q"] = d
    else:
        d = -d
        if d > 0 and n["Hy"] > 0:  # (Mg,Fe)O.SiO2 -> 2(Mg,Fe)O.SiO2 (counted per formula of olivine) frees SiO2
            x = min(d, n["Hy"] / 2); n["Ol"] = x; n["Hy"] -= 2 * x; d -= x
        if d > 0 and n["Tn"] > 0: x = min(d, n["Tn"]); n["Pf"] = x; n["Tn"] -= x; d -= x
        if d > 0 and n["Ab"] > 0: x = min(d / 4, n["Ab"]); n["Ne"] = x; n["Ab"] -= x; d -= 4 * x
        if d > 0 and n["Or"] > 0: x = min(d / 2, n["Or"]); n["Lc"] = x; n["Or"] -= x; d -= 2 * x
        if d > 0 and n["Wo"] > 0: x = min(d, n["Wo"] / 2); n["Cs"] = x; n["Wo"] -= 2 * x; d -= x
        if d > 0 and n["Di"] > 0:  # CaO.(Mg,Fe)O.2SiO2 -> 1/2 Cs + 1/2 Ol frees one SiO2 per Di
            x = min(d, n["Di"]); n["Cs"] += x / 2; n["Ol"] += x / 2; n["Di"] -= x; d -= x
        if d > 0 and n["Lc"] > 0: x = min(d / 2, n["Lc"]); n["Kp"] = x; n["Lc"] -= x; d -= 2 * x
        if d > 1e-9: n["Deficit"] = d  # not enough silica even for kaliophilite (very unusual)
    # weights
    out = {m: n[m] * MASS[m] for m in MASS}
    di_m = xmg * (_m["CaO"] + _m["MgO"] + 2 * _m["SiO2"]) + (1 - xmg) * (_m["CaO"] + _m["FeO"] + 2 * _m["SiO2"])
    hy_m = xmg * (_m["MgO"] + _m["SiO2"]) + (1 - xmg) * (_m["FeO"] + _m["SiO2"])
    ol_m = xmg * (2 * _m["MgO"] + _m["SiO2"]) + (1 - xmg) * (2 * _m["FeO"] + _m["SiO2"])
    out.update(Di=n["Di"] * di_m, Hy=n["Hy"] * hy_m, Ol=n["Ol"] * ol_m, Mg_number=100 * xmg)
    if "Deficit" in n: out["Deficit"] = n["Deficit"]
    return out


def cipw(table, fe3_ratio=None, anhydrous=True):
    """table: {oxide: array of wt%}. fe3_ratio: Fe2O3/FeO weight ratio used when only total iron (FeO) is given; None keeps FeO and
    Fe2O3 as they are. anhydrous: recalculate the oxides to 100% first (volatile-free), as the norm is defined for.
    Returns {column: array}: each mineral in wt%, the sum, the differentiation index (Q + Or + Ab + Ne + Lc + Kp, Thornton & Tuttle
    1960) and the normative plagioclase An = 100 An / (An + Ab)."""
    n = len(next(iter(table.values())))
    rows = []
    for i in range(n):
        ox = {k: float(np.nan_to_num(np.asarray(table[k], float)[i])) if k in table else 0.0 for k in OXIDES}
        if not np.isfinite(np.asarray(table.get("SiO2", [np.nan] * n), float)[i]): rows.append(None); continue
        if fe3_ratio is not None and ox["Fe2O3"] == 0 and ox["FeO"] > 0:  # split total iron (as FeO) into FeO and Fe2O3 by weight ratio
            feot = ox["FeO"]; feo = feot / (1 + fe3_ratio * 0.8998); ox["FeO"] = feo; ox["Fe2O3"] = fe3_ratio * feo
        if anhydrous:
            s = sum(ox.values())
            if s > 0: ox = {k: 100 * v / s for k, v in ox.items()}
        rows.append(norm_one(ox))
    cols = ORDER + ["Sum", "DI", "Plag An", "Plag An (mol%)"]
    out = {c: np.full(n, np.nan) for c in cols}
    for i, r in enumerate(rows):
        if r is None: continue
        for m in ORDER: out[m][i] = r[m]
        out["Sum"][i] = sum(r[m] for m in ORDER)
        out["DI"][i] = r["Q"] + r["Or"] + r["Ab"] + r["Ne"] + r["Lc"] + r["Kp"]
        out["Plag An"][i] = 100 * r["An"] / (r["An"] + r["Ab"]) if r["An"] + r["Ab"] > 0 else np.nan  # by weight, as is usual
        man, mab = r["An"] / MASS["An"], 2 * r["Ab"] / MASS["Ab"]  # moles of CaAl2Si2O8 and NaAlSi3O8 (the Ab unit holds two)
        out["Plag An (mol%)"][i] = 100 * man / (man + mab) if man + mab > 0 else np.nan
    return out


# --------------------------------------------------------------------------- self-check
_PURE = {  # end-member compositions as oxide mole numbers per formula unit used above
    "Q": {"SiO2": 1}, "Or": {"K2O": 1, "Al2O3": 1, "SiO2": 6}, "Ab": {"Na2O": 1, "Al2O3": 1, "SiO2": 6}, "An": {"CaO": 1, "Al2O3": 1, "SiO2": 2},
    "Ne": {"Na2O": 1, "Al2O3": 1, "SiO2": 2}, "Lc": {"K2O": 1, "Al2O3": 1, "SiO2": 4}, "DiMg": {"CaO": 1, "MgO": 1, "SiO2": 2},
    "En": {"MgO": 1, "SiO2": 1}, "Fo": {"MgO": 2, "SiO2": 1}, "Mt": {"FeO": 1, "Fe2O3": 1}, "Il": {"FeO": 1, "TiO2": 1},
    "Ap": {"CaO": 10 / 3, "P2O5": 1}, "C": {"Al2O3": 1}, "Wo": {"CaO": 1, "SiO2": 1}, "Ac": {"Na2O": 1, "Fe2O3": 1, "SiO2": 4},
}


def mix(weights):
    """Oxide wt% of a rock made of the given minerals in wt% (for testing)."""
    ox = dict.fromkeys(OXIDES, 0.0)
    for m, w in weights.items():
        comp = _PURE[m]; mass = sum(v * MW[k] for k, v in comp.items())
        for k, v in comp.items(): ox[k] += w * v * MW[k] / mass
    return ox


def _demo():
    def check(minerals, expect):
        r = norm_one(mix(minerals))
        for m, v in expect.items(): assert abs(r[m] - v) < 1e-6, (minerals, m, r[m], v)
        assert abs(sum(r[m] for m in ORDER) - sum(minerals.values())) < 1e-6, ("sum", minerals)
        return r
    check({"Q": 30, "Or": 30, "Ab": 30, "An": 10}, {"Q": 30, "Or": 30, "Ab": 30, "An": 10, "C": 0})          # granite
    check({"Ab": 25, "An": 25, "DiMg": 20, "En": 15, "Fo": 15}, {"Ab": 25, "An": 25, "Di": 20, "Hy": 15, "Ol": 15, "Q": 0})  # ol-tholeiite
    check({"Ne": 20, "An": 30, "DiMg": 30, "Fo": 20}, {"Ne": 20, "Ab": 0, "An": 30, "Di": 30, "Ol": 20, "Hy": 0})  # basanite (ne-normative)
    check({"Lc": 15, "Ne": 10, "An": 25, "DiMg": 30, "Fo": 20}, {"Lc": 15, "Or": 0, "Ne": 10, "Ol": 20})  # leucite-bearing
    check({"Q": 20, "Or": 30, "Ab": 30, "C": 5, "Ap": 1, "Il": 2, "Mt": 3, "En": 9}, {"C": 5, "Ap": 1, "Il": 2, "Mt": 3, "Hy": 9, "Q": 20})  # peraluminous
    check({"Ab": 40, "An": 20, "Q": 10, "DiMg": 15, "Wo": 15}, {"Wo": 15, "Di": 15, "Q": 10})  # excess Ca as wollastonite
    check({"Q": 30, "Or": 30, "Ab": 25, "Ac": 5, "En": 10}, {"Ac": 5, "Ab": 25, "Q": 30, "An": 0})  # peralkaline (comendite-like)
    # an analysis of a typical basalt: the norm sums to 100 % of the anhydrous oxides and is hypersthene-normative
    bas = {"SiO2": 49.2, "TiO2": 1.84, "Al2O3": 15.74, "Fe2O3": 3.79, "FeO": 7.13, "MnO": 0.2, "MgO": 6.73, "CaO": 9.47, "Na2O": 2.91,
           "K2O": 1.1, "P2O5": 0.35}
    t = cipw({k: [v] for k, v in bas.items()})
    assert abs(t["Sum"][0] - 100) < 0.01 and t["Hy"][0] > 0  # MnO is weighed as FeO, so the sum is 100.003 and t["Ne"][0] == 0 and 0 < t["Plag An"][0] < 100
    print("NORM OK")


if __name__ == "__main__":
    _demo()
