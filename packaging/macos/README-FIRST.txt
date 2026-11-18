PlotBench for macOS - first start
=================================

PlotBench is free, open-source software. This build is not notarised by Apple
(that needs a paid Apple Developer account), so macOS asks before opening it
the first time.

1. Drag PlotBench to the Applications folder.
2. Double-click PlotBench. When macOS says it "could not verify" PlotBench,
   click Done.
3. Open System Settings > Privacy & Security, scroll down to Security, and
   click "Open Anyway" next to the PlotBench message. Confirm with Touch ID
   or your password. PlotBench now opens normally every time.

Or, in Terminal, run this once:

    xattr -dr com.apple.quarantine /Applications/PlotBench.app

Only do this for a copy downloaded from the official page:
https://github.com/kishangeo/PlotBench/releases
You can check the download against the SHA-256 checksum shown there:

    shasum -a 256 ~/Downloads/PlotBench-*.dmg
