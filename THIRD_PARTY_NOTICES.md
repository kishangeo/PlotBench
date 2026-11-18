# Third-party notices

PlotBench is MIT-licensed (see `LICENSE`). It includes or is built with the components below.

## Data included in the source

**pyrolite** (https://github.com/morganjwilliams/pyrolite). The reference compositions (chondrite, primitive mantle, N-MORB, OIB,
continental crust, PAAS) and the TAS and QAP field polygons in `plotbench/geodata.py` were converted from pyrolite's data files by
`make_geodata.py`. The original values come from the publications cited in `plotbench/geodata.py`.

```
MIT License

Copyright (c) 2018 CSIRO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Libraries bundled in the installers

| Library | Licence |
|---|---|
| Qt for Python (PySide6) and Qt 6 | LGPL-3.0 |
| NumPy, SciPy, pandas | BSD-3-Clause |
| matplotlib | Matplotlib licence (PSF-based) |
| h5py | BSD-3-Clause |
| PyWavelets | MIT |
| openpyxl | MIT |
| xlrd | BSD |
| Pillow | MIT-CMU (HPND) |
| Python | PSF License |

The full licence texts ship inside each library's folder in the installed program, as provided by the packages.
