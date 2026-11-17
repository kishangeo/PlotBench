#!/bin/sh
# Adds PlotBench to the applications menu of the current user. Run from the unpacked PlotBench folder. Author: Kishan Tiwari
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.local/share/applications" "$HOME/.local/bin"
ln -sf "$DIR/PlotBench" "$HOME/.local/bin/plotbench"
cat > "$HOME/.local/share/applications/plotbench.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=PlotBench
Comment=Scientific graphing, petrology, thermobarometry and geochronology
Exec=$DIR/PlotBench %f
Icon=$DIR/plotbench.png
Categories=Science;Education;DataVisualization;
Terminal=false
DESK
echo "PlotBench added to your applications menu (command: plotbench)."
