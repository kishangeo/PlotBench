"""PlotBench file-format self-check: run `python test_formats.py`. Author: Kishan Tiwari."""
import os
import sqlite3
import tempfile

import numpy as np
from plotbench import formats as F

D = tempfile.mkdtemp(prefix="pb_formats_")

# JCAMP: compressed (SQZ, DIF, DUP) XYDATA, and a plain XYPOINTS table
assert F._decode_line("100 A0NK0") == [100, 10, 15, 35] and F._decode_line("100 A0J5") == [100, 10, 25]
assert F._decode_line("200 @J0T") == [200, 0, 10, 20]
assert F._decode_line("1 a5") == [1, -15]
p = os.path.join(D, "s.jdx")
open(p, "w").write("##TITLE=test spectrum\n##JCAMP-DX=4.24\n##XUNITS=1/CM\n##YUNITS=ABSORBANCE\n##XFACTOR=1\n##YFACTOR=0.01\n"
                   "##FIRSTX=100\n##LASTX=105\n##NPOINTS=6\n##XYDATA=(X++(Y..Y))\n100 A0NK0\n102 C5j5J0\n104 C0%\n##END=\n")
df, hdr = F.read_jcamp(p)
assert np.allclose(df["X"], [100, 101, 102, 103, 104, 105]), df
assert np.allclose(df["Y"], [0.10, 0.15, 0.35, 0.20, 0.30, 0.30]), df["Y"].tolist()   # DIF check value at line start dropped
assert hdr["X units"] == "1/CM" and hdr["title"] == "test spectrum"
p2 = os.path.join(D, "t.jdx"); open(p2, "w").write("##TITLE=peaks\n##XYPOINTS=(XY..XY)\n1.0, 5.0; 2.0, 7.5\n3, 2\n##END=\n")
df2, _ = F.read_jcamp(p2); assert df2["Y"].tolist() == [5.0, 7.5, 2.0]

# SQLite (read-only)
db = os.path.join(D, "d.sqlite")
with sqlite3.connect(db) as c:
    c.execute("create table samples (id integer, name text, mass real)"); c.executemany("insert into samples values (?,?,?)", [(1, "a", 2.5), (2, "b", 3.5)])
assert F.list_datasets(db) == [("samples", (2,), "table")]
assert F.sqlite_table(db, "samples")["mass"].sum() == 6.0
assert F.sqlite_query(db, "select avg(mass) m from samples")["m"][0] == 3.0
try:
    F.sqlite_query(db, "drop table samples"); raise AssertionError("write should fail")
except Exception as e:
    assert "readonly" in str(e).lower() or "read-only" in str(e).lower() or isinstance(e, sqlite3.OperationalError)

# MATLAB v5 and NetCDF-3
from scipy.io import savemat, netcdf_file
m = os.path.join(D, "a.mat"); savemat(m, {"t": np.arange(5.0), "M": np.arange(6.0).reshape(2, 3)})
names = {n for n, *_ in F.list_datasets(m)}; assert names == {"t", "M"}
fr = F.datasets_to_frame(m, ["t", "M"]); assert list(fr.columns) == ["t", "M[1]", "M[2]", "M[3]"] and len(fr) == 5
assert F.dataset_to_matrix(m, "M").shape == (2, 3)
nc = os.path.join(D, "a.nc")
with netcdf_file(nc, "w") as f:
    f.createDimension("x", 4); v = f.createVariable("temp", "f8", ("x",)); v[:] = [1, 2, 3, 4]; v.scale_factor = 10.0
assert F.kind_of(nc) == "netcdf3" and np.allclose(F.read_dataset(nc, "temp"), [10, 20, 30, 40])

try:
    import h5py
    h = os.path.join(D, "a.h5")
    with h5py.File(h, "w") as f:
        g = f.create_group("run1"); g["time"] = np.arange(10.0); g["signal"] = np.arange(10.0) ** 2; f["image"] = np.ones((4, 5))
    names = {n for n, *_ in F.list_datasets(h)}; assert names == {"run1/time", "run1/signal", "image"}, names
    assert F.datasets_to_frame(h, ["run1/time", "run1/signal"])["signal"].iloc[3] == 9 and F.dataset_to_matrix(h, "image").shape == (4, 5)
    nc4 = os.path.join(D, "b.nc")
    with h5py.File(nc4, "w") as f: f["v"] = np.arange(3.0)
    assert F.kind_of(nc4) == "hdf5" and F.read_dataset(nc4, "v").tolist() == [0, 1, 2]
except ImportError:
    print("(h5py not installed: HDF5 checks skipped)")
print("All PlotBench format checks passed.")
