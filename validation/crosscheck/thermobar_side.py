"""Thermobar side of the cross-check: Putirka (2008) clinopyroxene equations on the Putirka (2008) calibration set shipped with
Thermobar, at the experimental P or T. Writes thermobar.csv (inputs with PlotBench column names, run P-T, Thermobar results).
Run in an environment with Thermobar:  python validation/crosscheck/thermobar_side.py
Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>"""
from pathlib import Path
import pandas as pd, Thermobar as pt

d = pd.read_csv(Path(pt.__file__).parent / "Putirka2008_Cali_input.csv"); d["Fe3Fet_Liq"] = 0.0  # all iron as FeO in both programs
liq = d[[c for c in d.columns if c.endswith("_Liq") and "frac" not in c and "Number" not in c and "Sample" not in c]]
cpx = d[[c for c in d.columns if c.endswith("_Cpx") and c.split("_")[0] in ("SiO2", "TiO2", "Al2O3", "FeOt", "MnO", "MgO", "CaO", "Na2O", "K2O", "Cr2O3")]]
P, T = d["P_kbar"], d["T_K"]
out = pd.DataFrame({**{c.split("_")[0].replace("FeOt", "FeO"): liq[c] for c in liq.columns if c.split("_")[0] in
                       ("SiO2", "TiO2", "Al2O3", "FeOt", "MnO", "MgO", "CaO", "Na2O", "K2O", "Cr2O3", "P2O5", "H2O")},
                    **{"Cpx " + c.split("_")[0].replace("FeOt", "FeO"): cpx[c] for c in cpx.columns}, "P_kbar": P, "T_C": T - 273.15})
out["TB eq33 T_C"] = pt.calculate_cpx_liq_temp(liq_comps=liq, cpx_comps=cpx, equationT="T_Put2008_eq33", P=P, H2O_Liq=liq["H2O_Liq"]) - 273.15
out["TB eq30 P_kbar"] = pt.calculate_cpx_liq_press(liq_comps=liq, cpx_comps=cpx, equationP="P_Put2008_eq30", T=T, H2O_Liq=liq["H2O_Liq"])
out["TB eq31 P_kbar"] = pt.calculate_cpx_liq_press(liq_comps=liq, cpx_comps=cpx, equationP="P_Put2008_eq31", T=T, H2O_Liq=liq["H2O_Liq"])
out["TB eq32a P_kbar"] = pt.calculate_cpx_only_press(cpx_comps=cpx, equationP="P_Put2008_eq32a", T=T)
out["TB eq32d T_C"] = pt.calculate_cpx_only_temp(cpx_comps=cpx, equationT="T_Put2008_eq32d", P=P) - 273.15
out.to_csv(Path(__file__).with_name("thermobar.csv"), index=False); print(out.shape, pt.__version__)

# Brey & Kohler (1990) two-pyroxene T and Al-in-opx P(BKN), solved together, for the 13 garnet peridotites of Tappe et al. (2021,
# J Petrol 62(8), egab046) as distributed with the Thermobar examples (tappe2021_xenoliths.csv)
x = pd.read_csv(Path(__file__).with_name("tappe2021_xenoliths.csv"))
ph = lambda s: x[[c for c in x.columns if c.endswith("_" + s)]].copy()
opx, cpx2, gt = ph("Opx"), ph("Cpx"), ph("Gt")
r = pt.calculate_pyroxenes_garnet_press_temp(opx_comps=opx, cpx_comps=cpx2, gt_comps=gt, equationP="P_Brey1990", equationT="T_Brey1990", T_K_guess=1300)
pd.DataFrame({"SampleID": x["SampleID"], "TB T_C": r["T_K_calc"] - 273.15, "TB P_kbar": r["P_kbar_calc"]}).to_csv(Path(__file__).with_name("thermobar_tappe.csv"), index=False)
print(r[["P_kbar_calc", "T_K_calc"]].head())
