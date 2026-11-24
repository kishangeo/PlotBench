# Submitting PlotBench to the Microsoft Store

Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>

PlotBench goes to the Store as an **MSIX** package. Microsoft signs it during certification, so no paid code-signing certificate is needed.

## One-time setup (Partner Center)
1. Register as an individual developer at https://storedeveloper.microsoft.com (free for individuals).
2. In Partner Center, go to **Apps and games > New product > MSIX or PWA app** and reserve the name **PlotBench**.
3. Open **Product management > Product identity** and copy the three values into `packaging/msix/identity.json`:
   - `Package/Identity/Name` goes in `Name`
   - `Package/Identity/Publisher` goes in `Publisher` (`CN=...`)
   - `Package/Properties/PublisherDisplayName` goes in `PublisherDisplayName`

## Building the package (each release)
```
powershell -File build.ps1
powershell -File packaging\msix\make_msix.ps1
```
This creates `dist\PlotBench-<version>.0.msix`. The Store needs a four-part version ending in `.0`, and every upload must have a higher version than the last one.
To test locally, add `-TestSign`, or run `Add-AppxPackage -Register build\msix\AppxManifest.xml` with Developer Mode on.

## Submission form
- **Pricing and availability:** Free, all markets.
- **Properties:**
  - Primary category: Productivity. Secondary category: Education.
  - Privacy policy URL: required because of the runFullTrust capability. Use a page stating that the app collects no personal data, https://plotbench.vercel.app/privacy.
- **Age ratings:** complete the IARC questionnaire (no user interaction, no data sharing, so the result is 3+).
- **Packages:** upload the `.msix`.
- **Store listing (English):**
  - Description: take it from README.md.
  - Screenshots: `docs/img/window.png` and `window_dark.png` (2880x1760; they must be at least 1366x768), plus figure screenshots.
  - Store logo: 300x300 PNG from `plotbench/assets/logo.png`.
- **Submission options > Restricted capabilities:** justify `runFullTrust`: "Desktop scientific application (Python/Qt) packaged with the Desktop Bridge; it reads and writes user-chosen data files."

Certification usually takes 1 to 3 business days.
