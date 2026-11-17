"""PlotBench file formats: HDF5, NetCDF (3 and 4), MATLAB .mat (v5 and v7.3), JCAMP-DX, SQLite. No GUI code.

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
"""
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


def kind_of(path):
    ext = Path(path).suffix.lower()
    if ext in (".h5", ".hdf5", ".he5", ".hdf", ".nc4"): return "hdf5"
    if ext in (".nc", ".cdf", ".netcdf"):
        with open(path, "rb") as fh: head = fh.read(4)
        return "netcdf3" if head[:3] == b"CDF" else "hdf5"  # NetCDF-4 files are HDF5 files
    if ext == ".mat":
        with open(path, "rb") as fh: head = fh.read(128)
        return "mat73" if b"MATLAB 7.3" in head or head[:4] == b"\x89HDF" else "mat"
    if ext in (".jdx", ".dx", ".jcamp"): return "jcamp"
    if ext in (".db", ".sqlite", ".sqlite3"): return "sqlite"
    raise ValueError(f"Unsupported file type: {ext}")


# ---------------------------------------------------------------- array containers
def list_datasets(path):
    """[(name, shape, dtype)] of numeric arrays in an HDF5/NetCDF/MATLAB file, or tables in SQLite."""
    k = kind_of(path); out = []
    if k in ("hdf5", "mat73"):
        import h5py
        with h5py.File(path, "r") as f:
            f.visititems(lambda n, o: out.append((n, o.shape, str(o.dtype))) if isinstance(o, h5py.Dataset) and o.dtype.kind in "iufb" else None)
    elif k == "netcdf3":
        from scipy.io import netcdf_file
        with netcdf_file(path, "r", mmap=False) as f:
            out = [(n, v.shape, str(v.data.dtype)) for n, v in f.variables.items() if v.data.dtype.kind in "iufb"]
    elif k == "mat":
        from scipy.io import loadmat
        out = [(n, np.shape(v), str(np.asarray(v).dtype)) for n, v in loadmat(path).items()
               if not n.startswith("__") and np.asarray(v).dtype.kind in "iufb"]
    elif k == "sqlite":
        c = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)  # read-only: listing never creates or changes the file
        try:
            for (t,) in c.execute("select name from sqlite_master where type in ('table','view') order by name"):
                n = c.execute('select count(*) from "{}"'.format(t.replace('"', '""'))).fetchone()[0]; out.append((t, (n,), "table"))
        finally: c.close()
    else: raise ValueError("No datasets in this file type")
    return out


def read_dataset(path, name):
    k = kind_of(path)
    if k in ("hdf5", "mat73"):
        import h5py
        with h5py.File(path, "r") as f:
            a = np.asarray(f[name][()], float)
            return a.T if k == "mat73" else a  # MATLAB stores column-major
    if k == "netcdf3":
        from scipy.io import netcdf_file
        with netcdf_file(path, "r", mmap=False) as f:
            v = f.variables[name]; a = np.asarray(v.data, float).copy()
            for att, op in (("scale_factor", np.multiply), ("add_offset", np.add)):
                if hasattr(v, att): a = op(a, float(getattr(v, att)))
            return a
    if k == "mat":
        from scipy.io import loadmat
        return np.asarray(loadmat(path, variable_names=[name])[name], float)
    raise ValueError("Not an array file")


def datasets_to_frame(path, names):
    """Combine 1-D datasets (and columns of 2-D ones) into one DataFrame (shorter columns padded with NaN)."""
    cols = {}
    for n in names:
        a = np.squeeze(read_dataset(path, n)); short = n.split("/")[-1]
        if a.ndim == 0: cols[short] = np.array([float(a)])
        elif a.ndim == 1: cols[short] = a
        elif a.ndim == 2:
            for j in range(a.shape[1]): cols[f"{short}[{j + 1}]"] = a[:, j]
        else: raise ValueError(f"{n} has {a.ndim} dimensions; import it as a matrix (first 2-D slice) instead")
    n = max(len(v) for v in cols.values())
    return pd.DataFrame({k: np.r_[v, np.full(n - len(v), np.nan)] for k, v in cols.items()})


def dataset_to_matrix(path, name):
    a = np.squeeze(read_dataset(path, name))
    while a.ndim > 2: a = a[0]  # first 2-D slice of higher-dimensional data
    if a.ndim == 1: a = a[None, :]
    return a


# ---------------------------------------------------------------- SQLite
def sqlite_query(path, sql):
    uri = Path(path).resolve().as_uri() + "?mode=ro"  # proper file URI, so '#', '%' or '?' in a path cannot break it
    c = sqlite3.connect(uri, uri=True)  # read-only: an import never changes the database
    try: return pd.read_sql_query(sql, c)
    finally: c.close()  # 'with' only commits; it does not close the file


def sqlite_table(path, table):
    return sqlite_query(path, 'select * from "{}"'.format(str(table).replace('"', '""')))  # quoted identifier


# ---------------------------------------------------------------- JCAMP-DX
def _signed_digit(c, pos, neg, zero):
    """Map a compression character to (sign, first digit)."""
    if c == zero: return 1, "0"
    if c in pos: return 1, str(pos.index(c) + 1)
    return -1, str(neg.index(c) + 1)


def _decode_line(line):
    """Decode one (X++(Y..Y)) data line with ASDF compression (SQZ, DIF, DUP). Returns [x, y1, y2, ...]."""
    toks = re.findall(r"[@A-Ia-i%J-Rj-rS-Zs][0-9.]*|[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?", line.replace(",", " "))
    vals, last_dif = [], False
    for t in toks:
        c, rest = t[0], t[1:]
        if c in "@ABCDEFGHIabcdefghi":  # SQZ: absolute value
            s, d = _signed_digit(c, "ABCDEFGHI", "abcdefghi", "@"); vals.append(s * float(d + rest)); last_dif = False
        elif c in "%JKLMNOPQRjklmnopqr":  # DIF: difference from previous value
            s, d = _signed_digit(c, "JKLMNOPQR", "jklmnopqr", "%"); vals.append(vals[-1] + s * float(d + rest)); last_dif = True
        elif c in "STUVWXYZs":  # DUP: repeat the previous token (value or difference) n-1 more times
            n = int(str("STUVWXYZs".index(c) + 1) + rest); step = (vals[-1] - vals[-2]) if last_dif and len(vals) > 1 else 0.0
            for _ in range(n - 1): vals.append(vals[-1] + step)
        else: vals.append(float(t)); last_dif = False
    return vals


def read_jcamp(path):
    """Returns (DataFrame with X and Y, header dict). Handles XYDATA=(X++(Y..Y)) and XYPOINTS/PEAK TABLE=(XY..XY)."""
    hdr, xs, ys, mode = {}, [], [], None
    for raw in Path(path).read_text(errors="replace").splitlines():
        line = raw.split("$$")[0].strip()
        if not line: continue
        if line.startswith("##"):
            key, _, val = line[2:].partition("="); key = key.strip().upper(); val = val.strip(); hdr[key] = val
            mode = ("xyy" if "X++" in val.replace(" ", "") else "xy") if key in ("XYDATA", "XYPOINTS", "PEAK TABLE", "PEAKTABLE") else None
            if key == "END": break
            continue
        if mode == "xyy":
            v = _decode_line(line)
            if len(v) > 1: xs.append(v[0]); ys.append(v[1:])
        elif mode == "xy":
            nums = [float(t) for t in re.findall(r"[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?", line)]
            for i in range(0, len(nums) - 1, 2): xs.append(nums[i]); ys.append([nums[i + 1]])
    if not xs: raise ValueError("No spectrum data found in JCAMP file")
    xf = float(hdr.get("XFACTOR", 1) or 1); yf = float(hdr.get("YFACTOR", 1) or 1)
    if mode == "xyy" or any(len(y) > 1 for y in ys):
        first, last = float(hdr.get("FIRSTX", xs[0] * xf)), float(hdr.get("LASTX", 0))
        npts = int(float(hdr.get("NPOINTS", sum(len(y) for y in ys)))); yv = np.concatenate([np.asarray(y, float) for y in ys])
        # a DIF line repeats the last Y of the previous line as a check value: drop duplicates where X restarts
        if len(yv) > npts:
            yv2 = [ys[0]]
            for prev, cur in zip(ys, ys[1:]): yv2.append(cur[1:] if len(cur) > 1 and np.isclose(cur[0], prev[-1]) else cur)
            yv = np.concatenate([np.asarray(y, float) for y in yv2])
        yv = yv[:npts] * yf; x = np.linspace(first, last if "LASTX" in hdr else first + (len(yv) - 1) * float(hdr.get("DELTAX", 1)), len(yv))
    else:
        x = np.asarray(xs) * xf; yv = np.asarray([y[0] for y in ys]) * yf
    xl, yl = hdr.get("XUNITS", "X"), hdr.get("YUNITS", "Y")
    return pd.DataFrame({"X": x, "Y": yv}), {"title": hdr.get("TITLE", Path(path).stem), "X units": xl, "Y units": yl}
