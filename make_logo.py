"""Draw the PlotBench logo and write assets/logo.svg, logo.png, icon.ico, banner.png and the installer images.
Author: Kishan Tiwari <kishantiwari@iitkgp.ac.in>. Run: python make_logo.py"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image

OUT = Path(__file__).parent / "plotbench" / "assets"; OUT.mkdir(exist_ok=True)
NAVY, TEAL, GOLD, WHITE = "#16325c", "#14a39a", "#f6b93b", "#ffffff"


def draw_mark(ax, bold=1.0):
    """The square mark: gradient tile, axes, bars, and a fitted curve through data points."""
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal"); ax.axis("off")
    grad = np.linspace(0, 1, 256)[None, :] * 0.6 + np.linspace(0, 1, 256)[:, None] * 0.4
    tile = FancyBboxPatch((0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0,rounding_size=0.2", fc="none", ec="none")
    ax.add_patch(tile)
    from matplotlib.colors import LinearSegmentedColormap
    im = ax.imshow(grad, extent=(0.02, 0.98, 0.02, 0.98), origin="lower", cmap=LinearSegmentedColormap.from_list("pb", [NAVY, TEAL]), zorder=0)
    im.set_clip_path(tile)
    ax.plot([0.2, 0.2, 0.84], [0.84, 0.2, 0.2], color=WHITE, lw=7 * bold, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    for x, h in ((0.31, 0.16), (0.45, 0.27), (0.59, 0.21), (0.73, 0.38)):
        ax.add_patch(FancyBboxPatch((x - 0.045, 0.25), 0.09, h, boxstyle="round,pad=0,rounding_size=0.015", fc=WHITE, ec="none", alpha=0.32, zorder=2))
    xs = np.linspace(0.26, 0.82, 100); ys = 0.27 + 0.5 / (1 + np.exp(-(xs - 0.55) * 14))
    ax.plot(xs, ys, color=GOLD, lw=6.5 * bold, solid_capstyle="round", zorder=4)
    for x in (0.31, 0.45, 0.59, 0.73):
        y = 0.27 + 0.5 / (1 + np.exp(-(x - 0.55) * 14)) + (0.02 if x in (0.45, 0.73) else -0.025)
        ax.plot(x, y, "o", ms=11 * bold ** 0.5, mfc=WHITE, mec=NAVY, mew=2.2 * bold, zorder=5)


def mark(size_px=512, path=None, bold=1.0):
    fig = plt.figure(figsize=(4, 4), dpi=size_px / 4); ax = fig.add_axes([0, 0, 1, 1]); draw_mark(ax, bold)  # line widths are in points: draw at 4 in
    fig.savefig(path, transparent=True); plt.close(fig)


def banner(path, w=1200, h=360, dark=False):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100); fig.patch.set_alpha(0)
    ax = fig.add_axes([0.02, 0.06, h * 0.88 / w, 0.88]); draw_mark(ax)
    fig.text(0.31, 0.60, "PlotBench", fontsize=74, fontweight="bold", color="#e8eef6" if dark else NAVY, family="DejaVu Sans", va="center")
    fig.text(0.315, 0.30, "Worksheets  ·  Graphs  ·  Fitting  ·  Statistics", fontsize=22, color="#9fb0c4" if dark else "#4a5a70",
             family="DejaVu Sans", va="center")
    fig.savefig(path, transparent=True); plt.close(fig)


if __name__ == "__main__":
    mark(512, OUT / "logo.png")
    fig = plt.figure(figsize=(4, 4)); ax = fig.add_axes([0, 0, 1, 1]); draw_mark(ax)
    fig.savefig(OUT / "logo.svg", transparent=True, metadata={"Creator": "Kishan Tiwari", "Title": "PlotBench logo"}); plt.close(fig)
    img = Image.open(OUT / "logo.png")
    mark(256, OUT / "_bold.png", bold=2.4); bold_img = Image.open(OUT / "_bold.png")
    frames = [(bold_img if s_ <= 48 else img).resize((s_, s_), Image.LANCZOS) for s_ in (16, 24, 32, 48, 64, 128, 256)]
    frames[-1].save(OUT / "icon.ico", sizes=[f.size for f in frames], append_images=frames[:-1])
    bold_img.resize((32, 32), Image.LANCZOS).save(OUT / "logo32.png"); (OUT / "_bold.png").unlink()
    banner(OUT / "banner.png"); banner(OUT / "banner_dark.png", dark=True)
    # Inno Setup wizard images (BMP, no transparency): large 164x314 side panel and 55x58 corner image
    side = Image.new("RGB", (164, 314), (22, 50, 92)); m = img.resize((132, 132), Image.LANCZOS); side.paste(m, (16, 40), m)
    side.save(OUT / "wizard_large.bmp")
    small = Image.new("RGB", (55, 58), (255, 255, 255)); m2 = img.resize((50, 50), Image.LANCZOS); small.paste(m2, (2, 4), m2); small.save(OUT / "wizard_small.bmp")
    print("wrote", sorted(p.name for p in OUT.iterdir()))
