"""Petrology dialogs and diagrams: the grouped, searchable method picker that shows which inputs the sheet has, the curves of the
coupled P-T diagram, and the Fe-Ti oxide diagrams (T - log fO2 with buffers; Mg/Mn equilibrium of Bacon & Hirschmann 1988).

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import numpy as np

from . import thermobaro as TB

GROUPS = [("Accessory minerals: zircon, rutile, titanite, quartz", ("zircon", "rutile", "titanite", "quartz")),
          ("Volcanic: mineral-liquid (Putirka 2008)", ("liquid", "putirka 2008 eq 3", "rhodes")),
          ("Mantle: single clinopyroxene (Nimis & Taylor 2000)", ("nimis",)),
          ("Two pyroxenes", ("two-pyroxene", "ca-in-orthopyroxene")),
          ("Metamorphic: garnet, amphibole, hornblende", ("garnet", "amphibole", "hornblende"))]


def group(name):
    n = name.lower()
    return next((g for g, keys in GROUPS if any(k in n for k in keys)), "Other")


def missing(name, cols, oxides):
    """Inputs of a method that the sheet does not seem to have (a required column not found, no oxide columns of a phase)."""
    out = []
    for kind, label, extra in TB.METHODS[name]["inputs"]:
        if kind == "col" and not TB.guess_column(cols, extra): out.append(label)
        elif kind == "oxides" and not oxides(): out.append(label)
        elif kind == "phase" and len(oxides(extra)) < 3: out.append(label)
    return out


def picker(names, cols, oxides, current=None):
    """(widget, combo): a search box over a list of methods grouped by mineral or assemblage; methods whose inputs are not all in
    the sheet are greyed (still selectable), and a line under the list says what is found or missing for the chosen one."""
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QComboBox, QLabel
    from PySide6.QtGui import QColor
    from PySide6.QtCore import Qt
    w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0, 0, 0, 0)
    search = QLineEdit(); search.setPlaceholderText("Search methods (mineral, author, equation)..."); search.setClearButtonEnabled(True)
    combo = QComboBox(); combo.setMaxVisibleItems(24); status = QLabel(); status.setWordWrap(True)
    lack = {n: missing(n, cols, oxides) for n in names}; w.nomatch = False
    dark = w.palette().window().color().lightness() < 128  # readable on both themes
    good, bad = ("#4ade80", "#f87171") if dark else ("#2e7d32", "#b91c1c")

    def fill(text=""):
        words = text.lower().split(); keep = combo.currentText() if combo.currentText() in names else current
        shown = [n for n in names if all(wd in f"{n} {group(n)}".lower() for wd in words)]
        w.nomatch = bool(words) and not shown; shown = shown or list(names)  # nothing matches: say so, keep the full list
        combo.blockSignals(True); combo.clear()
        for g in [g for g, _ in GROUPS] + ["Other"]:
            these = [n for n in shown if group(n) == g]
            if not these: continue
            combo.addItem(f"— {g} —"); combo.model().item(combo.count() - 1).setEnabled(False)
            for n in these:
                combo.addItem(n); i = combo.count() - 1
                if lack[n]:
                    combo.setItemData(i, QColor("#8a8f98"), Qt.ForegroundRole); combo.setItemData(i, "Not found in this sheet: " + ", ".join(lack[n]), Qt.ToolTipRole)
        combo.setCurrentText(keep) if keep in shown else combo.setCurrentIndex(next(i for i in range(combo.count()) if combo.itemText(i) in names))
        combo.blockSignals(False); combo.currentTextChanged.emit(combo.currentText())
        if w.nomatch: status.setText(f"<span style='color:{bad}'>No method matches '{text.strip()}'; showing all</span>")

    def show(n):
        if n not in lack: return
        status.setText(f"<span style='color:{good}'>✓ All inputs found in this sheet</span>" if not lack[n] else
                       f"<span style='color:{bad}'>Not found in this sheet: {', '.join(lack[n])}</span>")
    combo.currentTextChanged.connect(show); search.textChanged.connect(fill)
    lay.addWidget(search); lay.addWidget(combo); lay.addWidget(status); fill(); w.search = search; w.status = status
    return w, combo


def pt_curves(tmethod, pmethod, columns, sheet_arr, sheet_oxides, T, P, sdT=None, sdP=None, rows=12, n=60, rho=None):
    """Columns of the P-T diagram for up to `rows` solved samples, curves joined with blank rows: the thermometer's T at each P,
    the barometer's P at each T, and (with Monte Carlo) the 1-sigma ellipse around each solution, tilted by the T-P correlation rho."""
    T, P = np.asarray(T, float), np.asarray(P, float); idx = np.nonzero(np.isfinite(T) & np.isfinite(P))[0][:rows]
    if not len(idx): return None
    pg = np.linspace(max(0.0, np.nanmin(P[idx]) - 10), np.nanmax(P[idx]) + 10, n)
    tg = np.linspace(np.nanmin(T[idx]) - 200, np.nanmax(T[idx]) + 200, n)
    with np.errstate(all="ignore"):
        tc = np.array([np.broadcast_to(TB.compute(tmethod, {**columns, "P (kbar)": p}, sheet_arr, sheet_oxides), T.shape) for p in pg])
        pc = np.array([np.broadcast_to(TB.compute(pmethod, {**columns, "T (C) column": None, "T (C), if no column": t}, sheet_arr, sheet_oxides), T.shape)
                       for t in tg])
    gap = [np.nan]; cat = lambda parts: np.concatenate([np.r_[p, gap] for p in parts])
    out = {"Thermometer T (C)": cat([tc[:, i] for i in idx]), "Thermometer P (kbar)": cat([pg for _ in idx]),
           "Barometer T (C)": cat([tg for _ in idx]), "Barometer P (kbar)": cat([pc[:, i] for i in idx])}
    if sdT is not None and sdP is not None:
        a = np.linspace(0, 2 * np.pi, 41); r = np.zeros(len(T)) if rho is None else np.nan_to_num(np.asarray(rho, float))
        # 1-sigma contour of a correlated pair: T = sT cos a, P = sP (r cos a + sqrt(1 - r^2) sin a)
        out["1s ellipse T (C)"] = cat([T[i] + sdT[i] * np.cos(a) for i in idx])
        out["1s ellipse P (kbar)"] = cat([P[i] + sdP[i] * (r[i] * np.cos(a) + np.sqrt(max(0.0, 1 - r[i] ** 2)) * np.sin(a)) for i in idx])
    m = max(len(v) for v in out.values())
    return {k: np.r_[v, np.full(m - len(v), np.nan)] for k, v in out.items()}


# Pattison (1992, J Geol 100, 423-446, doi:10.1086/629596): Al2SiO5 triple point 550 C, 4.5 kbar; slopes 11.5 (Ky = And) and
# 20.7 (Ky = Sil) bar/C from the experiments, -16.0 bar/C (And = Sil) through the Ballachulish aureole constraint.
AL2SIO5_TP = (550.0, 4.5)
AL2SIO5 = {"Ky = And": 11.5, "Ky = Sil": 20.7, "And = Sil": -16.0}
RHO_G = 0.27  # kbar per km: average crust of 2.75 g/cm3
PT_LINES = [("Ky = And T (C)", "Ky = And P (kbar)", "k-", "Ky = And (Pattison 1992)"),
            ("Ky = Sil T (C)", "Ky = Sil P (kbar)", "k-", "Ky = Sil"), ("And = Sil T (C)", "And = Sil P (kbar)", "k-", "And = Sil"),
            ("Geotherm 10 C/km T (C)", "Geotherm 10 C/km P (kbar)", "k:", "10 °C/km"),
            ("Geotherm 20 C/km T (C)", "Geotherm 20 C/km P (kbar)", "k-.", "20 °C/km"),
            ("Geotherm 30 C/km T (C)", "Geotherm 30 C/km P (kbar)", "k--", "30 °C/km")]


def pt_reference(tmax=900.0, pmax=12.0, which=("al2sio5", "geotherms"), n=40):
    """Columns of reference lines for a P-T graph (T in C, P in kbar): the three Al2SiO5 reactions from the triple point, each to
    P = 0 or to tmax, and geotherms of 10, 20 and 30 C/km (P from depth at 0.27 kbar/km), up to tmax or pmax."""
    t0, p0 = AL2SIO5_TP; out = {}
    if "al2sio5" in which:
        for r, s in AL2SIO5.items():
            k = s / 1000.0; t_end = tmax if r == "Ky = Sil" else t0 - p0 / k  # Ky = And towards low T, And = Sil towards high T, both to P = 0
            t = np.linspace(t0, t_end, n); out[f"{r} T (C)"] = t; out[f"{r} P (kbar)"] = p0 + k * (t - t0)
    if "geotherms" in which:
        for gr in (10, 20, 30):
            p = np.linspace(0, pmax, n); t = gr * p / RHO_G; keep = t <= tmax
            out[f"Geotherm {gr} C/km T (C)"] = t[keep]; out[f"Geotherm {gr} C/km P (kbar)"] = p[keep]
    m = max((len(v) for v in out.values()), default=0)
    return {k: np.r_[v, np.full(m - len(v), np.nan)] for k, v in out.items()}


# Frost (1991, Rev Mineral 25, 1-9) Table 1: log fO2 = A/T + B + C (P - 1)/T, T in K, P in bar
FROST = {"MH": (-25700.6, 14.558, 0.019), "FMQ": (-25096.3, 8.735, 0.110)}


def buffer(name, t_c, p_bar=1.0):
    """log10 fO2 of a buffer at T (C): MH and FMQ of Frost (1991); NNO of O'Neill & Pownceby (1993), as used for delta NNO."""
    from . import fetioxide as FT
    T = np.asarray(t_c, float) + 273.15
    if name == "NNO": return FT.log_fo2_nno(T, p_bar)
    A, B, C = FROST[name]; return A / T + B + C * (p_bar - 1) / T


def fe_ti_curves(t_c, x_ilm=None, p_bar=1.0, n=60):
    """Columns of the Fe-Ti oxide diagrams: buffer curves over the temperature range of the results and, given log(Mg/Mn) of the
    ilmenites, the Bacon & Hirschmann (1988) equilibrium line with its 2-sigma envelope (log(Mg/Mn) Mt against Ilm)."""
    from . import fetioxide as FT
    t = np.asarray(t_c, float); t = t[np.isfinite(t)]
    tg = np.linspace(max(-200.0, t.min() - 50), t.max() + 50, n) if len(t) else np.linspace(700, 1100, n)
    out = {"Buffer T (C)": tg, **{f"log fO2 {b}": buffer(b, tg, p_bar) for b in ("MH", "NNO", "FMQ")}}
    x = np.asarray(x_ilm if x_ilm is not None else [], float); x = x[np.isfinite(x)]
    if len(x):
        xg = np.linspace(min(x.min(), 0.0) - 0.2, x.max() + 0.2, n); out["log(Mg/Mn) Ilm (line)"] = xg
        out["B&H 1988 equilibrium"] = FT.BH88[0] * xg + FT.BH88[1]
        out["B&H 1988 +2s"] = FT.BH88_UP[0] * xg + FT.BH88_UP[1]; out["B&H 1988 -2s"] = FT.BH88_LO[0] * xg + FT.BH88_LO[1]
    return out


def _demo():
    assert group("Zr-in-rutile (Watson et al. 2006)").startswith("Accessory")
    assert group("Clinopyroxene-liquid P (Putirka 2008 Eq 30)").startswith("Volcanic")
    assert group("Garnet-orthopyroxene Al (Harley & Green 1982)").startswith("Metamorphic")
    assert all(group(n) != "Other" for n in TB.METHODS), [n for n in TB.METHODS if group(n) == "Other"]
    assert abs(buffer("FMQ", 1000.0) - (-25096.3 / 1273.15 + 8.735)) < 1e-9 and buffer("MH", 900) > buffer("NNO", 900) > buffer("FMQ", 900)
    print("petro_ui ok")


if __name__ == "__main__":
    _demo()
