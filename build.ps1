# Build PlotBench.exe and the Windows installer. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
.\.venv\Scripts\python test_analysis.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis.py" }
.\.venv\Scripts\python test_analysis2.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis2.py" }
.\.venv\Scripts\python test_formats.py; if ($LASTEXITCODE) { throw "Build step failed: test_formats.py" }
.\.venv\Scripts\python test_analysis3.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis3.py" }
.\.venv\Scripts\python test_analysis4.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis4.py" }
.\.venv\Scripts\python test_analysis5.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis5.py" }
.\.venv\Scripts\python test_analysis6.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis6.py" }
.\.venv\Scripts\python test_analysis7.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis7.py" }
.\.venv\Scripts\python make_logo.py; if ($LASTEXITCODE) { throw "Build step failed: make_logo.py" }
.\.venv\Scripts\python test_analysis8.py; if ($LASTEXITCODE) { throw "Build step failed: test_analysis8.py" }
.\.venv\Scripts\python -c "from plotbench import plots4; plots4._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import plots4; plots4._demo()'" }
.\.venv\Scripts\python -c "from plotbench import mineral; mineral._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import mineral; mineral._demo()'" }
.\.venv\Scripts\python -c "from plotbench import cellformula; cellformula._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import cellformula; cellformula._demo()'" }
.\.venv\Scripts\python -c "from plotbench import norm; norm._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import norm; norm._demo()'" }
.\.venv\Scripts\python -c "from plotbench import thermobaro; thermobaro._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import thermobaro; thermobaro._demo()'" }
.\.venv\Scripts\python -c "from plotbench import fetioxide; fetioxide._demo()"; if ($LASTEXITCODE) { throw "Build step failed: fetioxide" }
.\.venv\Scripts\python -c "from plotbench import volcanic; volcanic._demo()"; if ($LASTEXITCODE) { throw "Build step failed: volcanic" }
.\.venv\Scripts\python -c "from plotbench import geochron; geochron._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import geochron; geochron._demo()'" }
.\.venv\Scripts\python -m unittest discover -s tests; if ($LASTEXITCODE) { throw "Build step failed: regression tests" }
.\.venv\Scripts\python make_examples.py; if ($LASTEXITCODE) { throw "Build step failed: make_examples.py" }
.\.venv\Scripts\python make_manual.py; if ($LASTEXITCODE) { throw "Build step failed: make_manual.py" }
.\.venv\Scripts\python -c "from plotbench import examples; examples._demo()"; if ($LASTEXITCODE) { throw "Build step failed: -c 'from plotbench import examples; examples._demo()'" }
.\.venv\Scripts\pyinstaller --noconfirm --windowed --name PlotBench --icon plotbench\assets\icon.ico `
  --add-data "plotbench\assets;plotbench\assets" --add-data "plotbench\examples;plotbench\examples" `
  --add-data "plotbench\manual;plotbench\manual" --add-data "CHANGELOG.md;." `
  --hidden-import matplotlib.backends.backend_pdf --hidden-import matplotlib.backends.backend_ps `
  --hidden-import matplotlib.backends.backend_svg --hidden-import matplotlib.backends.backend_pgf `
  --hidden-import PIL.TiffImagePlugin --hidden-import pywt --hidden-import h5py --hidden-import xlrd --hidden-import scipy.odr `
  --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.Qt3DCore `
  --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml --exclude-module PySide6.QtMultimedia `
  --exclude-module pyqtgraph run_plotbench.py
if ($LASTEXITCODE) { throw "PyInstaller failed" }
# Drop Qt parts PlotBench never loads (QML/Quick, PDF viewer, virtual keyboard, software OpenGL, Qt's own OpenSSL 3 and
# translations): about 50 MB unpacked. The self-test below starts the real window afterwards, so a needed file cannot go missing unnoticed.
$q = "dist\PlotBench\_internal\PySide6"
$drop = @("$q\opengl32sw.dll", "$q\Qt6Pdf.dll", "$q\Qt6Qml.dll", "$q\Qt6QmlMeta.dll", "$q\Qt6QmlModels.dll", "$q\Qt6QmlWorkerScript.dll",
          "$q\Qt6Quick.dll", "$q\Qt6VirtualKeyboard.dll", "$q\translations", "$q\plugins\imageformats\qpdf.dll",
          "$q\plugins\platforminputcontexts", "$q\plugins\tls\qopensslbackend.dll", "dist\PlotBench\_internal\libcrypto-3-x64.dll",
          "dist\PlotBench\_internal\libssl-3-x64.dll")
foreach ($f in $drop) { if (Test-Path $f) { Remove-Item -Recurse -Force $f } }
# Check the packaged program itself: every export format and the lazily loaded libraries must work in the bundle.
$st = Join-Path $env:TEMP "pb_selftest"; Remove-Item -Recurse -Force $st -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "dist\PlotBench\PlotBench.exe" -ArgumentList "--selftest", $st -Wait -PassThru
Get-Content (Join-Path $st "selftest.txt")
if ($p.ExitCode -ne 0) { throw "Packaged self-test failed (see above); the installer was not built." }
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
  # Compile into a temp folder (antivirus scanning in the project folder can corrupt the setup file), retry, then copy.
  $ver = (Select-String -Path installer.iss -Pattern '#define AppVersion "(.+)"').Matches[0].Groups[1].Value
  $name = "PlotBench-$ver-Setup.exe"; $out = Join-Path $env:TEMP "pb_setup_out"
  Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue; New-Item -ItemType Directory $out | Out-Null
  Remove-Item "dist\$name" -ErrorAction SilentlyContinue
  $ok = $false
  for ($i = 1; $i -le 3 -and -not $ok; $i++) {
    $ErrorActionPreference = "Continue"; & $iscc "/O$out" installer.iss; $ErrorActionPreference = "Stop"
    $ok = ($LASTEXITCODE -eq 0) -and (Test-Path (Join-Path $out $name))
    if (-not $ok) { Write-Host "Installer compile attempt $i failed; retrying"; Start-Sleep -Seconds 10 }
  }
  if (-not $ok) { throw "Installer compile failed 3 times. Exclude $out from antivirus scanning and rerun." }
  Copy-Item (Join-Path $out $name) "dist\$name" -Force; Write-Host "Installer: dist\$name"
}
else { Write-Host "Inno Setup 6 not found: install it (winget install JRSoftware.InnoSetup) and rerun, or use dist\PlotBench\PlotBench.exe directly." }
