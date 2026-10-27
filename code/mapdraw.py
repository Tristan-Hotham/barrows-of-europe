"""Shared helpers for the static maps (header, paper, blog, collage).

Projection: ETRS89 Lambert azimuthal equal-area (EPSG:3035), in km.
Land: Natural Earth 1:50m admin 0 countries (public domain), read in place from ../_data3/ne/.
"""
import json
import os

import numpy as np
import pandas as pd
from matplotlib.patches import Polygon
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
D3 = os.environ.get("DATA3", os.path.join(ROOT, "..", "_data3"))
T = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
FONTS = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
KINDS = R["kind_order"]
KL = R["kind_label"]
# light-theme colours, as on the page
PAL = dict(bg="#F3EDE0", panel="#E9E0CC", fg="#2E2216", muted="#6B5D4A", rule="#DACDB3", card="#FBF7EE", hot="#A35A17",
           land="#E6DCC6", sea="#F3EDE0", blue="#3E6C8C", green="#55702F", red="#8E2F22")
KC = dict(mound="#B5651D", round="#D9A030", long="#4E6E2A", cairn="#5F7186", kurgan="#8E2F22")
RC = ["#A35A17", "#3E6C8C", "#55702F", "#8E2F22"]


def fonts():
    from matplotlib import font_manager as fm
    for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf",
              "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
        p = os.path.join(FONTS, f)
        if os.path.exists(p):
            fm.fontManager.addfont(p)
    p = os.path.join(FONTS, "FrauncesVar.ttf")
    disp = fm.FontProperties(fname=p, weight=900) if os.path.exists(p) else fm.FontProperties(family="serif", weight="bold")
    return disp, "Source Serif 4", "IBM Plex Mono"


def xy(lon, lat):
    x, y = T.transform(np.asarray(lon, float), np.asarray(lat, float))
    return np.asarray(x) / 1000, np.asarray(y) / 1000


_LAND = None


def land_polys():
    global _LAND
    if _LAND is None:
        g = json.load(open(os.path.join(D3, "ne", "geojson", "ne_50m_admin_0_countries.geojson")))
        out = []
        for f in g["features"]:
            geom = f["geometry"]
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for poly in polys:
                ring = np.array(poly[0])
                if len(ring) < 3 or ring[:, 0].max() < -35 or ring[:, 0].min() > 75 or ring[:, 1].max() < 28 or ring[:, 1].min() > 80:
                    continue
                X, Y = xy(np.clip(ring[:, 0], -60, 90), np.clip(ring[:, 1], 20, 85))
                out.append(np.c_[X, Y])
        _LAND = out
    return _LAND


def draw_land(ax, fc=PAL["land"], ec="none", lw=0.4, z=1):
    for p in land_polys():
        ax.add_patch(Polygon(p, closed=True, fc=fc, ec=ec, lw=lw, zorder=z))


def extent(ax, lon0=-11, lat0=35, lon1=50, lat1=70):
    lo = np.linspace(lon0, lon1, 30); la = np.linspace(lat0, lat1, 30)
    X1, Y1 = xy(np.r_[lo, lo, np.full(30, lon0), np.full(30, lon1)], np.r_[np.full(30, lat0), np.full(30, lat1), la, la])
    ax.set_xlim(X1.min(), X1.max()); ax.set_ylim(Y1.min(), Y1.max()); ax.set_aspect("equal"); ax.axis("off")


def load_barrows():
    b = pd.read_csv(os.path.join(ROOT, "data", "barrows.csv"), keep_default_na=False, low_memory=False)
    b["x"], b["y"] = xy(b.lon.values, b.lat.values)
    return b


def load_cells():
    c = pd.read_csv(os.path.join(ROOT, "data", "cells_50km.csv"), keep_default_na=False)
    c["x"] = c.i * 50.0; c["y"] = c.j * 50.0
    return c
