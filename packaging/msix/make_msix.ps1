# Package dist\PlotBench (made by build.ps1) as an MSIX for the Microsoft Store. Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>
# Usage: powershell -File packaging\msix\make_msix.ps1 [-TestSign]
# The Store signs the uploaded package itself; -TestSign adds a self-signed signature for a local install test only.
param([switch]$TestSign)
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."; Set-Location $root
$app = "dist\PlotBench"; if (-not (Test-Path "$app\PlotBench.exe")) { throw "Run build.ps1 first: $app\PlotBench.exe is missing." }
$id = Get-Content "$PSScriptRoot\identity.json" -Raw | ConvertFrom-Json
# The Store needs a four-part version whose last part is 0.
$ver = (Select-String -Path installer.iss -Pattern '#define AppVersion "(.+)"').Matches[0].Groups[1].Value + ".0"

# makeappx/signtool: Windows SDK if installed, else Microsoft's SDK BuildTools package from nuget.org (cached in build\).
$kit = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" -ErrorAction SilentlyContinue | Select-Object -Last 1
if (-not $kit) {
  $bt = "build\sdkbt"
  if (-not (Test-Path $bt)) {
    New-Item -ItemType Directory $bt | Out-Null
    Invoke-WebRequest "https://www.nuget.org/api/v2/package/Microsoft.Windows.SDK.BuildTools" -OutFile "$bt\bt.zip"
    Expand-Archive "$bt\bt.zip" "$bt\x"
  }
  $kit = Get-ChildItem "$bt\x\bin\*\x64\makeappx.exe" | Select-Object -Last 1
}
$makeappx = $kit.FullName; $signtool = Join-Path $kit.DirectoryName "signtool.exe"

# Stage: the app plus the manifest and tile images.
$stage = "build\msix"; Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
Copy-Item -Recurse $app $stage; New-Item -ItemType Directory "$stage\Assets" | Out-Null
(Get-Content "$PSScriptRoot\AppxManifest.xml" -Raw).Replace("@NAME@", $id.Name).Replace("@PUBLISHER@", $id.Publisher).
  Replace("@PUBDISPLAY@", $id.PublisherDisplayName).Replace("@DISPLAY@", $id.DisplayName).Replace("@VERSION@", $ver) | Set-Content "$stage\AppxManifest.xml" -Encoding utf8
.\.venv\Scripts\python -c @"
from PIL import Image
src = Image.open(r'plotbench\assets\logo.png').convert('RGBA')
def tile(name, w, h, frac):
    s = int(min(w, h) * frac); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); lg = src.resize((s, s), Image.LANCZOS)
    im.paste(lg, ((w - s) // 2, (h - s) // 2), lg); im.save(rf'$stage\Assets\{name}.png')
for n, w, h, f in (('StoreLogo', 50, 50, 1), ('Square44x44Logo', 44, 44, 1), ('Square150x150Logo', 150, 150, .66),
                   ('Wide310x150Logo', 310, 150, .66)): tile(n, w, h, f)
for z in (16, 24, 32, 48, 256): tile(f'Square44x44Logo.targetsize-{z}_altform-unplated', z, z, 1)
"@
if ($LASTEXITCODE) { throw "Tile images failed" }

$out = "dist\PlotBench-$ver.msix"; Remove-Item $out -ErrorAction SilentlyContinue
& $makeappx pack /d $stage /p $out /o; if ($LASTEXITCODE) { throw "makeappx failed" }
if ($TestSign) {
  $cert = New-SelfSignedCertificate -Type Custom -Subject $id.Publisher -KeyUsage DigitalSignature -FriendlyName "PlotBench MSIX test" `
    -CertStoreLocation Cert:\CurrentUser\My -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
  & $signtool sign /fd SHA256 /sha1 $cert.Thumbprint $out; if ($LASTEXITCODE) { throw "signtool failed" }
  Export-Certificate -Cert $cert -FilePath "dist\PlotBench-msix-test.cer" | Out-Null
  Write-Host "Test install: import dist\PlotBench-msix-test.cer into Local Machine > Trusted People (admin), then double-click the .msix."
}
Write-Host "MSIX: $out"
