"""r/dataisbeautiful collage: reddit/barrows_of_europe.png (2400 x 3000).
Run from anywhere: python3 reddit/collage.py. Every number is read from data/results.json."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "code"))
from mapdraw import R, fonts, draw_land, extent, load_barrows, xy  # noqa: E402

DISP, SER, MONO = fonts()
BG, FG, MUT, LAND = "#E7EBD5", "#33251A", "#66604C", "#D2DBB6"
OCH, DEEP = "#B5651D", "#7A3B12"
KC = dict(mound="#B5651D", round="#DDA42E", long="#3F5E22", cairn="#5B6C7E", kurgan="#8E2F22")
b = load_barrows()

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.967, "Is the barrow a European thing?", fontproperties=DISP, fontsize=46, color=FG, va="top")
fig.text(0.04, 0.917, f"Every burial mound and burial cairn in OpenStreetMap and Wikidata, from Ireland to the steppe:\n"
         f"{R['totals']['europe']:,} barrows in Europe, coloured by type, and {R['dates']['meta']['n_dates_name']} radiocarbon dates from them.",
         family=SER, fontsize=15, color=FG, va="top", linespacing=1.35)

# hero map
ax = fig.add_axes([0.01, 0.35, 0.60, 0.52], facecolor=BG)
draw_land(ax, fc=LAND)
lo0, la0, lo1, la1 = -11, 36, 46, 69
t = np.linspace(0, 1, 60)
fx, fy = xy(np.r_[lo0 + (lo1 - lo0) * t, np.full(60, lo1), lo1 - (lo1 - lo0) * t, np.full(60, lo0)],
            np.r_[np.full(60, la0), la0 + (la1 - la0) * t, np.full(60, la1), la1 - (la1 - la0) * t])
frame = matplotlib.patches.Polygon(np.c_[fx, fy], closed=True, fc="none", ec=MUT, lw=0.8, zorder=5)
ax.add_patch(frame)
for p in ax.patches:
    p.set_clip_path(frame)
for k in ["mound", "round", "long", "kurgan", "cairn"]:
    d = b[b.kind == k]
    sc = ax.scatter(d.x, d.y, s=0.9 if k in ("mound", "cairn") else 2.2, c=KC[k], lw=0, alpha=0.85, zorder=3, rasterized=True)
    sc.set_clip_path(frame)
ax.set_xlim(fx.min() - 20, fx.max() + 20); ax.set_ylim(fy.min() - 20, fy.max() + 20); ax.set_aspect("equal"); ax.axis("off")
lab = {"mound": "mound or tumulus", "round": "round barrow", "long": "long barrow", "cairn": "burial cairn", "kurgan": "kurgan or mogila"}
for i, k in enumerate(["mound", "cairn", "round", "kurgan", "long"]):
    y = 0.395 - i * 0.017
    fig.patches.append(matplotlib.patches.Circle((0.052, y + 0.004), 0.0055, transform=fig.transFigure, fc=KC[k], ec="none"))
    fig.text(0.066, y, f"{lab[k]}  {R['kinds'][k]['n']:,}", family=MONO, fontsize=11, color=FG, va="bottom")

# right column: big numbers
tx = fig.add_axes([0.63, 0.37, 0.35, 0.49]); tx.axis("off")
c = R["c"]
notes = [(f"{R['register_share'] * 100:.0f}%", f"of the mapped barrows are in eight\ncountries whose heritage registers\nwere imported in bulk ({R['register_land_share'] * 100:.0f}% of the land).\nThe 'barrow belt' is partly a belt of records."),
         (f"{c['France']['mound_share_osm'] * 100:.0f}% vs {c['Netherlands']['mound_share_osm'] * 100:.0f}%", "mounds among mapped mounds and\nmegaliths: France against the\nNetherlands. Stone on the Atlantic,\nearth from the North Sea to the steppe."),
         (f"{R['dates']['name']['All']['bins']['2500 to 800 BC'] * 100:.0f}%", f"of dated barrows fall between 2500\nand 800 BC. Long barrows are older:\nmedian {R['x']['long_median']}."),
         (f"{R['steppe']['per_1000km2']:.1f}", "barrows per 1,000 km² mapped on the\nPontic steppe, home of the kurgans.\nAgainst " + f"{c['Denmark']['per_1000km2']:,.0f} in Denmark.")]
for (big, small), y in zip(notes, [1.0, 0.75, 0.5, 0.27]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=OCH, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.072, small, family=SER, fontsize=12.2, color=FG, va="top", transform=tx.transAxes, linespacing=1.28)

# bottom row 1: dates as a mound
a1 = fig.add_axes([0.06, 0.115, 0.40, 0.17], facecolor=BG)
yrs = np.array(R["dates"]["year_grid"])
for i, (r, col) in enumerate([("Britain and Ireland", OCH), ("Scandinavia", "#5B6C7E")]):
    sp = np.array(R["dates"]["spd"]["name"][r])
    base = 0 if i == 0 else 1.15
    a1.fill_between(yrs, base, base + sp, color=col, alpha=0.55, lw=0)
    a1.plot(yrs, base + sp, color=col, lw=1.6)
    a1.text(-5900, base + 0.45, r.replace(" and ", " and\n") + f", {R['dates']['name'][r]['sites']} sites", family=MONO, fontsize=9.5, color=FG, va="bottom")
a1.axvspan(-2500, -800, color=FG, alpha=0.06, lw=0)
a1.set_xlim(-6000, 1000); a1.set_ylim(-0.05, 2.3); a1.set_yticks([])
a1.set_xticks([-6000, -4000, -2000, 0]); a1.set_xticklabels(["6000 BC", "4000 BC", "2000 BC", "AD 1"], family=MONO, fontsize=9.5, color=MUT)
for s in ["top", "right", "left"]:
    a1.spines[s].set_visible(False)
a1.spines["bottom"].set_color(MUT)
fig.text(0.06, 0.295, "WHEN: TWO WAVES OF BUILDING", family=MONO, fontsize=11, color=MUT)
a1.text(-1650, 2.22, "2500 to 800 BC", family=MONO, fontsize=9.5, color=MUT, ha="center", va="top")

# bottom row 2: earth or stone
a2 = fig.add_axes([0.58, 0.155, 0.38, 0.13], facecolor=BG)
C = pd.DataFrame(R["countries"])
pick = ["France", "Portugal", "Ireland", "Italy", "Spain", "United Kingdom", "Sweden", "Germany", "Poland", "Netherlands", "Hungary", "Ukraine"]
d = C[C.country.isin(pick)].set_index("country").loc[pick]
x = np.arange(len(d))
a2.bar(x, d.mound_share_osm * 100, color=OCH, width=0.62)
a2.bar(x, 100 - d.mound_share_osm * 100, bottom=d.mound_share_osm * 100, color="#9AA3A8", width=0.62)
a2.set_xticks(x); a2.set_xticklabels([s.replace("United Kingdom", "UK") for s in d.index], rotation=55, ha="right", family=MONO, fontsize=9.5, color=FG)
a2.set_yticks([0, 50, 100]); a2.set_yticklabels(["0%", "50%", "100%"], family=MONO, fontsize=9.5, color=MUT)
for s in ["top", "right"]:
    a2.spines[s].set_visible(False)
a2.spines["left"].set_color(MUT); a2.spines["bottom"].set_color(MUT); a2.set_ylim(0, 100)
fig.text(0.58, 0.295, "EARTH (OCHRE) OR STONE (GREY)", family=MONO, fontsize=11, color=MUT)

fig.text(0.04, 0.012, "Data: © OpenStreetMap contributors (ODbL 1.0), QLever pull 27 Oct 2026; Wikidata (CC0); p3k14c radiocarbon database, Bird et al. 2022 (CC BY 4.0),\n"
         "calibrated with IntCal20; Natural Earth (public domain). Records, not mounds: coverage depends on national registers and mappers.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib.", family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, "barrows_of_europe.png"), facecolor=BG, dpi=200)
print("ok")
