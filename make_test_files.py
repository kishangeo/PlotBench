"""Write one sample file for every import route of PlotBench, with a README saying how to open each and what to expect.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
Usage:  python make_test_files.py [folder]          (default: test_data/import_formats)
        python make_test_files.py [folder] --xls    (only the legacy .xls file; needs the xlwt package)
All data are synthetic test values, not measurements.
"""
import sqlite3
import sys
from pathlib import Path

import numpy as np

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path(__file__).parent / "test_data" / "import_formats"
r = np.random.default_rng(7)
x = np.linspace(100, 1200, 221)                                                   # Raman shift, cm-1
spec = 200 + 0.05 * x + 900 * np.exp(-0.5 * ((x - 465) / 9) ** 2) + 400 * np.exp(-0.5 * ((x - 820) / 14) ** 2) + r.normal(0, 8, x.size)
oxides = {"Sample": ["B-1", "B-2", "A-1", "D-1", "R-1"], "SiO2": [49.1, 50.3, 57.8, 64.2, 73.4], "TiO2": [1.8, 1.6, 1.0, 0.6, 0.2],
          "Al2O3": [15.2, 15.6, 16.8, 16.1, 13.5], "FeOt": [11.0, 10.4, 7.2, 4.6, 1.9], "MgO": [7.9, 7.1, 3.9, 1.9, 0.3],
          "CaO": [10.9, 10.2, 7.0, 4.6, 1.2], "Na2O": [2.6, 2.9, 3.6, 4.0, 3.9], "K2O": [0.4, 0.6, 1.5, 2.5, 4.8]}
NAMES = list(oxides)
README = []


def note(fn, how, expect):
    README.append(f"{fn}\n    Open with: {how}\n    Expect:    {expect}\n")


def rows():
    return [[oxides[k][i] for k in NAMES] for i in range(5)]


def text_files():
    with open(OUT / "oxides_comma.csv", "w", encoding="utf-8") as f:
        f.write(",".join(NAMES) + "\n"); [f.write(",".join(map(str, rw)) + "\n") for rw in rows()]
    note("oxides_comma.csv", "File > Quick Import CSV / TXT, Import Wizard, or drag onto the window",
         "5 rows x 9 columns: Sample, SiO2 ... K2O (SiO2 of B-1 = 49.1)")
    with open(OUT / "oxides_semicolon_decimal_comma.csv", "w", encoding="utf-8") as f:
        f.write(";".join(NAMES) + "\n")
        for rw in rows(): f.write(";".join(str(v).replace(".", ",") for v in rw) + "\n")
    note("oxides_semicolon_decimal_comma.csv", "File > Import Wizard: Delimiter = Semicolon, Decimal separator = ','",
         "same table as oxides_comma.csv (European style: 49,1 becomes 49.1)")
    with open(OUT / "spectrum_tab.tsv", "w", encoding="utf-8") as f:
        f.write("Raman shift\tIntensity\n"); [f.write(f"{a:.2f}\t{b:.3f}\n") for a, b in zip(x, spec)]
    note("spectrum_tab.tsv", "Quick Import or Import Wizard (Tab)", "221 rows, X 100-1200 cm-1, peaks near 465 and 820 cm-1")
    with open(OUT / "spectrum_whitespace.txt", "w", encoding="utf-8") as f:
        f.write("shift   counts\n"); [f.write(f"{a:10.2f}   {b:10.3f}\n") for a, b in zip(x, spec)]
    note("spectrum_whitespace.txt", "Quick Import, or Import Wizard with 'Space(s) / whitespace'", "same spectrum, two columns")
    with open(OUT / "spectrum_with_header.dat", "w", encoding="utf-8") as f:
        f.write("# Instrument: synthetic Raman, 532 nm\n# Date: test file\n# Operator: PlotBench\n")
        f.write("Raman shift,Intensity\ncm-1,counts\nwavenumber,baseline not removed\n")
        [f.write(f"{a:.2f},{b:.3f}\n") for a, b in zip(x, spec)]
    note("spectrum_with_header.dat", "File > Import Wizard: Skip lines at top = 3, names line 1, units line 2, comments line 3",
         "221 rows; the column units (cm-1, counts) and comments go to the Units and Comments header rows")
    with open(OUT / "oxides_pipe.txt", "w", encoding="utf-8") as f:
        f.write("|".join(NAMES) + "\n"); [f.write("|".join(map(str, rw)) + "\n") for rw in rows()]
    note("oxides_pipe.txt", "File > Import Wizard: Delimiter = Pipe |", "same table as oxides_comma.csv")
    for ext in ("prn", "asc"):
        with open(OUT / f"spectrum.{ext}", "w", encoding="utf-8") as f:
            f.write("X Y\n"); [f.write(f"{a:.2f} {b:.3f}\n") for a, b in zip(x[::4], spec[::4])]
        note(f"spectrum.{ext}", "drag onto the window (or Quick Import with 'All files')", "56 rows, two columns X and Y")
    with open(OUT / "detection_limits.csv", "w", encoding="utf-8") as f:
        f.write("Sample,La,Ce,Tm,Lu\nS1,32.1,64.0,<0.05,0.31\nS2,28.4,55.2,0.21,0.29\nS3,n.d.,49.8,0.18,bdl\n")
    note("detection_limits.csv", "Quick Import", "text cells such as '<0.05', 'n.d.' and 'bdl' are kept as text; plotted as censored values in spider plots")


def excel():
    import pandas as pd
    with pd.ExcelWriter(OUT / "workbook_two_sheets.xlsx") as w:
        pd.DataFrame(oxides).to_excel(w, sheet_name="Oxides", index=False)
        pd.DataFrame({"Raman shift": x, "Intensity": spec}).to_excel(w, sheet_name="Spectrum", index=False)
    note("workbook_two_sheets.xlsx", "File > Import Excel (or drag)", "one workbook with two sheets, Oxides (5 x 9) and Spectrum (221 x 2)")


def xls():
    import xlwt
    wb = xlwt.Workbook(); ws = wb.add_sheet("Oxides")
    for j, k in enumerate(NAMES): ws.write(0, j, k)
    for i, rw in enumerate(rows(), 1):
        for j, v in enumerate(rw): ws.write(i, j, v)
    wb.save(str(OUT / "legacy_excel97.xls"))
    print("xls written")


def images():
    from PIL import Image
    yy, xx = np.mgrid[0:120, 0:160]
    z = (np.exp(-((xx - 60) ** 2 + (yy - 50) ** 2) / 600) * 200 + np.exp(-((xx - 120) ** 2 + (yy - 85) ** 2) / 300) * 120 + 20).astype(np.uint8)
    rgb = np.dstack([z, (z * 0.6).astype(np.uint8), (255 - z)])
    for ext in ("png", "jpg", "tif", "bmp", "gif"):
        Image.fromarray(rgb).save(OUT / f"two_spots.{ext}")
    note("two_spots.png / .jpg / .tif / .bmp / .gif", "File > Import Image as Matrix (or drag)",
         "a 120 x 160 matrix with two bright spots; the brightest is at column 60, 50 pixels from the top of the image (matrix row 70, as row 1 is at the bottom); JPG and GIF differ slightly (compression, palette)")


def digitizer_image():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tx = np.array([200, 400, 600, 800, 1000, 1200, 1400]); ty = np.array([1e-18, 3e-17, 2e-15, 5e-14, 1e-12, 4e-11, 2e-10])
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=150)
    ax.semilogy(tx, ty, "ko", ms=6); ax.set_xlim(0, 1600); ax.set_ylim(1e-19, 1e-9)
    ax.set_xlabel("Temperature (K)"); ax.set_ylabel("Diffusivity (m$^2$/s)"); ax.grid(False)
    fig.tight_layout(); fig.savefig(OUT / "graph_to_digitize_log_axis.png"); plt.close(fig)
    note("graph_to_digitize_log_axis.png", "Tools > Digitizer: calibrate X with 0 and 1600 (or two labelled ticks), Y with 10^-19 and 10^-9 "
         "(type them as 10^-19, 1e-9 ...); it will offer a log Y axis",
         "7 points: (200, 1e-18), (400, 3e-17), (600, 2e-15), (800, 5e-14), (1000, 1e-12), (1200, 4e-11), (1400, 2e-10)")


def arrays():
    import h5py
    from scipy.io import savemat, netcdf_file
    t = np.linspace(0, 10, 101); grid = np.outer(np.sin(np.linspace(0, 3, 40)), np.cos(np.linspace(0, 2, 60)))
    with h5py.File(OUT / "arrays.h5", "w") as f:
        g = f.create_group("run1"); g["time"] = t; g["signal"] = np.exp(-t / 3) * np.cos(4 * t); f["image"] = grid
    note("arrays.h5", "File > Import HDF5 / NetCDF / MATLAB", "datasets run1/time and run1/signal (101 values, a damped cosine) and image (40 x 60, as matrix)")
    with netcdf_file(OUT / "climate_classic.nc", "w") as f:
        f.createDimension("time", 24); f.createDimension("lat", 10); f.createDimension("lon", 12)
        v = f.createVariable("time", "f8", ("time",)); v[:] = np.arange(24.0)
        v = f.createVariable("temperature", "f8", ("time",)); v[:] = 15 + 8 * np.sin(np.arange(24) / 24 * 2 * np.pi)
        v = f.createVariable("field", "f8", ("lat", "lon")); v[:] = np.add.outer(np.arange(10.0), np.arange(12.0))
    note("climate_classic.nc", "File > Import HDF5 / NetCDF / MATLAB", "time and temperature (24 values, 7 to 23) and field (10 x 12, as matrix)")
    savemat(OUT / "matlab_v5.mat", {"wavelength": np.linspace(400, 700, 31), "absorbance": np.exp(-((np.linspace(400, 700, 31) - 520) / 40) ** 2),
                                    "M": grid})
    note("matlab_v5.mat", "File > Import HDF5 / NetCDF / MATLAB", "wavelength and absorbance (31 values, peak at 520 nm) and M (40 x 60)")
    with h5py.File(OUT / "matlab_v73.mat", "w", userblock_size=512) as f:
        f["wavelength"] = np.linspace(400, 700, 31)[None, :]; f["M"] = grid.T  # MATLAB stores column-major
    with open(OUT / "matlab_v73.mat", "r+b") as f:
        f.write(b"MATLAB 7.3 MAT-file, Platform: test, created by PlotBench make_test_files.py".ljust(116, b" "))
    note("matlab_v73.mat", "File > Import HDF5 / NetCDF / MATLAB", "MATLAB 7.3 (HDF5) file: wavelength (31 values) and M (40 x 60, same as matlab_v5.mat)")


def jcamp():
    xs = np.arange(4000.0, 399.0, -8.0); ys = 0.02 + 0.6 * np.exp(-0.5 * ((xs - 1650) / 25) ** 2) + 0.4 * np.exp(-0.5 * ((xs - 2920) / 30) ** 2)
    lines = ["##TITLE=Synthetic FTIR test spectrum", "##JCAMP-DX=4.24", "##DATA TYPE=INFRARED SPECTRUM", "##XUNITS=1/CM",
             "##YUNITS=ABSORBANCE", f"##FIRSTX={xs[0]:.1f}", f"##LASTX={xs[-1]:.1f}", "##XFACTOR=1", "##YFACTOR=0.0001",
             f"##NPOINTS={xs.size}", "##XYDATA=(X++(Y..Y))"]
    yi = np.round(ys / 0.0001).astype(int)
    for i in range(0, xs.size, 8): lines.append(f"{xs[i]:.1f} " + " ".join(str(v) for v in yi[i:i + 8]))
    lines.append("##END=")
    (OUT / "ftir_xydata.jdx").write_text("\n".join(lines) + "\n", encoding="ascii")
    note("ftir_xydata.jdx", "File > Import JCAMP-DX Spectrum", f"{xs.size} points from 4000 to 400 1/cm, bands at 1650 and 2920 1/cm (absorbance up to about 0.62)")
    pk = ["##TITLE=Peak table test", "##JCAMP-DX=4.24", "##XUNITS=1/CM", "##YUNITS=ABSORBANCE", "##PEAK TABLE=(XY..XY)",
          "1650.0, 0.62; 2920.0, 0.42; 3400.0, 0.15", "##END="]
    (OUT / "peaks_table.dx").write_text("\n".join(pk) + "\n", encoding="ascii")
    note("peaks_table.dx", "File > Import JCAMP-DX Spectrum", "3 points: (1650, 0.62), (2920, 0.42), (3400, 0.15)")


def sqlite():
    fn = OUT / "samples.db"
    if fn.exists(): fn.unlink()
    with sqlite3.connect(fn) as con:
        con.execute("CREATE TABLE oxides (Sample TEXT, SiO2 REAL, MgO REAL, K2O REAL)")
        con.executemany("INSERT INTO oxides VALUES (?, ?, ?, ?)", [(oxides["Sample"][i], oxides["SiO2"][i], oxides["MgO"][i], oxides["K2O"][i]) for i in range(5)])
        con.execute("CREATE TABLE sites (Site TEXT, Lat REAL, Lon REAL)")
        con.executemany("INSERT INTO sites VALUES (?, ?, ?)", [("Kharagpur", 22.31, 87.31), ("Ahmedabad", 23.03, 72.58)])
    note("samples.db", "File > Import from SQLite Database: pick a table, or type SQL such as SELECT * FROM oxides WHERE SiO2 > 55",
         "tables oxides (5 rows) and sites (2 rows); the SQL example returns 3 rows")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if "--xls" in sys.argv: xls(); sys.exit()
    for f in (text_files, excel, images, digitizer_image, arrays, jcamp, sqlite): f()
    note("legacy_excel97.xls", "File > Import Excel", "the Oxides table (5 x 9) in the old Excel 97-2003 format")
    (OUT / "README.txt").write_text(
        "PlotBench import test files (synthetic data, made by make_test_files.py; author Kishan Tiwari)\n"
        "Every file can also be dragged onto the PlotBench window.\n\n" + "\n".join(README), encoding="utf-8")
    print(f"{len(list(OUT.iterdir()))} files in {OUT}")
