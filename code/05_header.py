"""Step 5: ../header.png, the 1200 x 630 social card (matplotlib)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mapdraw import ROOT, R, PAL, KC, KINDS, fonts, draw_land, extent, load_barrows

DISP, SER, MONO = fonts()
b = load_barrows()
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=PAL["bg"])
ax = fig.add_axes([0.47, 0.0, 0.53, 1.0], facecolor=PAL["bg"])
draw_land(ax, fc=PAL["land"])
order = ["mound", "round", "long", "kurgan", "cairn"]
for k in order:
    d = b[b.kind == k]
    ax.scatter(d.x, d.y, s=0.9 if k in ("mound", "cairn") else 1.6, c=KC[k], lw=0, alpha=0.75, zorder=3, rasterized=True)
extent(ax, -11, 36, 46, 67)
fig.text(0.05, 0.86, "DATA STUDY", fontsize=13, family=MONO, color="white", va="center",
         bbox=dict(boxstyle="square,pad=0.45", fc=PAL["hot"], ec="none"))
fig.text(0.165, 0.86, "EUROPE'S BURIAL MOUNDS", fontsize=13, family=MONO, color=PAL["muted"], va="center")
fig.text(0.047, 0.77, "Is the barrow\na European\nthing?", fontproperties=DISP, fontsize=52, color=PAL["fg"], va="top", linespacing=0.92)
fig.text(0.05, 0.36, f"{R['totals']['europe']:,} mounds and cairns, from\nIreland to the steppe, mapped\nand dated with radiocarbon.",
         family=SER, fontsize=19, color=PAL["fg"], va="top", linespacing=1.15)
fig.text(0.05, 0.07, "Dr Tristan Hotham · Independent researcher", family=MONO, fontsize=12.5, color=PAL["muted"])
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=PAL["bg"])
print("header.png")
