"""Step 1: build one table of barrows (burial mounds and burial cairns) for Europe.

Inputs (read in place, not copied):
  ../_data3/osm_monuments_europe.json   OpenStreetMap objects (ODbL 1.0), QLever pull of 27 Oct 2026
  ../_data3/wikidata_monuments.json     Wikidata items (CC0), classes tumulus Q34023 and cairn Q7321974
  ../_data3/ne/geojson/ne_10m_admin_0_countries.geojson   Natural Earth (public domain)

What counts as a barrow
  OpenStreetMap: archaeological_site=tumulus or cairn; or tomb=tumulus; or historic=tumulus; or
    megalith_type in long_barrow, round_barrow, barrow, chambered_cairn, ring_cairn, cairn.
    Megalithic tombs tagged only as megaliths (dolmens, passage graves) are left to the sister
    project on megaliths. Rows found only by the name search (query E) count only if their tags
    qualify, so streets, pubs and so on drop out.
  Wikidata: every item whose class is tumulus or a subclass (bowl barrow, kurgan and so on), and
    every item whose class is cairn or a subclass EXCEPT clearance cairns (field clearance, not burial).

Type (first rule that applies, from tags, Wikidata class and the name):
  long    long barrow / long cairn / Hünenbett / langdysse
  kurgan  name says kurgan, kurhan, курган, mogila, mohyla, kunhalom, halomsír
  cairn   a cairn tag or class, or a cairn word in the name (cairn, röse, røys, carn)
  round   round, bowl, bell, disc, saucer, pond or oval barrow
  mound   every other tumulus (høj, Grabhügel, mámoa, tumulus ...)
Period: from OSM historic:period / historic:civilization and Wikidata period (P2348) and
  archaeological culture (P2596), mapped to six broad bins (PERIOD_MAP below); most rows have none.
Group: the record names a whole barrow cemetery or group rather than one mound.

Duplicates: a Wikidata item is dropped when an OSM barrow carries its QID (wikidata tag) or lies
within 30 m of it. OSM objects within 5 m of another OSM barrow are dropped (node and way of one
mound).

Country: the Natural Earth 1:10m country containing the point, or the nearest within 10 km.
Study area: Natural Earth countries in Europe, clipped to 25 W to 60 E and 34 to 72 N (so Russia
up to the Urals). Turkey, Cyprus, Georgia, Armenia, Azerbaijan and Kazakhstan west of 60 E are kept as
"edge" countries: on the map and in the country table, but not in the European totals.

Outputs: work/barrows.pkl (all columns), data/barrows.csv, work/countries_geom.pkl
"""
import json
import os
import re
import pickle
from collections import Counter

import numpy as np
import pandas as pd
import shapely
from shapely import STRtree
from shapely.geometry import shape, box
from pyproj import Transformer
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
D3 = os.environ.get("DATA3", os.path.join(ROOT, "..", "_data3"))
WORK = os.path.join(ROOT, "work")
os.makedirs(WORK, exist_ok=True)
T = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
EDGE = {"TUR", "CYP", "GEO", "ARM", "AZE", "KAZ", "CYN"}
CLIP = box(-25, 34, 60, 72)

# ---------- names and periods ----------
RX = {
    "long": re.compile(r"long[\s-]?barrow|long[\s-]?cairn|long mound|langbett|h[üu]nenbett|langdysse|langdyssen|langh[üu]gel|langgrab|chambered long", re.I),
    "kurgan": re.compile(r"kurgan|kurhan|курган|kurgán|mogil|могил|mohyl|kunhalom|halomsír|halomsir", re.I),
    "cairn": re.compile(r"\bcairns?\b|r[öo]set?\b|r[öo]sen\b|gravr[öo]s|røys|\bcarn\b|\bkerne\b|raunio|hiidenkiu", re.I),
    "round": re.compile(r"(round|bowl|bell|disc|saucer|pond|oval)[\s-]?barrow", re.I),
}
GROUP_RX = re.compile(r"\bgroup\b|группа|групп|gräberfeld|grabhügelfeld|hügelgräberfeld|barrow cemetery|cemetery|cairnfield|pilkapyn|cmentarzysk|gravfält|могильник|tumuli group|necropol|nekropol|mohylník|pohřebiště|halomcsoport", re.I)

PERIOD_MAP = [
    ("medieval", re.compile(r"medieval|middle.?ages|viking|vikingian|slavic|anglo.?saxon|avar|early medieval|merovingian|C8|C9|C10|middle_age", re.I)),
    ("roman", re.compile(r"roman|principate|republic|gallo", re.I)),
    ("iron", re.compile(r"iron|hallstat|la t[eè]ne|celtic|etrusc|thrac|tracian|scythian|sarmat|illyr|urnfield|przewors|hunsr|phryg|classical|ancient_greek|vettones|samnit|sanniti", re.I)),
    ("bronze", re.compile(r"bronze|wessex|unetice|únětice|mycenae|minoan|tumulus culture|velatice", re.I)),
    ("neolithic", re.compile(r"neolith|stone.?age|chalcolith|copper|maykop|maikop|corded|funnel|baalberge|BCE2000|yamna|beaker", re.I)),
    ("prehistoric", re.compile(r"prehist|early metal age|undetermined", re.I)),
]
PERIODS = ["neolithic", "bronze", "iron", "roman", "medieval", "prehistoric"]


def period_of(*vals):
    """Map free-text period/culture tags to one bin. Several different bins -> 'prehistoric'
    (uncertain) unless one of them is medieval or roman, which then wins (late reuse is explicit)."""
    txt = ";".join(v for v in vals if v)
    if not txt:
        return ""
    if re.search(r"stone-age / bronze-age undetermined|undetermined", txt):
        return "prehistoric"
    hits = []
    for part in re.split(r"[;,/]", txt):
        for k, rx in PERIOD_MAP:
            if rx.search(part):
                hits.append(k)
                break
    hits = set(hits)
    if not hits:
        return "other"
    if len(hits) == 1:
        return hits.pop()
    for k in ("medieval", "roman"):
        if k in hits:
            return k
    return "prehistoric"


def kind_of(name, tags):
    n = name or ""
    t = " ".join(x for x in tags if x)
    if RX["long"].search(n) or re.search(r"long_barrow|chambered long barrow|long cairn", t):
        return "long"
    if RX["kurgan"].search(n) or re.search(r"kurgan", t, re.I):
        return "kurgan"
    if re.search(r"\bcairn\b|ring_cairn|chambered_cairn|grave cairn|round cairn|Lapinraunio|platform cairn", t) or RX["cairn"].search(n):
        return "cairn"
    if RX["round"].search(n) or re.search(r"round_barrow|bowl barrow|bell barrow|disc barrow|round barrow|oval barrow|square barrow", t):
        return "round"
    return "mound"


def main():
    # ---------- OSM ----------
    osm = json.load(open(os.path.join(D3, "osm_monuments_europe.json")))
    MT = {"long_barrow", "round_barrow", "barrow", "chambered_cairn", "ring_cairn", "cairn"}
    rows = []
    for r in osm:
        a = r.get("as") or ""
        ok = (a in ("tumulus", "cairn") or "tumulus" in a.split(";") or r.get("tomb") == "tumulus"
              or r.get("hist") == "tumulus" or (r.get("mt") or "") in MT)
        if not ok:
            continue
        cl = "cairn" if a == "cairn" else ""
        rows.append(dict(src="osm", id=r["o"], lon=r["lon"], lat=r["lat"], name=r.get("name", ""),
                         kind=kind_of(r.get("name"), [r.get("mt"), cl, r.get("tomb") if r.get("tomb") != "tumulus" else ""]),
                         period=period_of(r.get("per"), r.get("civ")), per_raw=";".join(x for x in [r.get("per"), r.get("civ")] if x),
                         cls=(r.get("mt") or a or r.get("tomb") or ""), wd=(r.get("wd") or "").rsplit("/", 1)[-1]))
    o = pd.DataFrame(rows)
    n_osm_raw = len(o)
    # drop OSM near-duplicates (node + way of one mound): within 5 m
    X, Y = T.transform(o.lon.values, o.lat.values)
    tree = cKDTree(np.c_[X, Y])
    pairs = tree.query_pairs(5.0)
    drop = set()
    for i, j in sorted(pairs):
        if i not in drop:
            drop.add(j)
    o = o.drop(index=sorted(drop)).reset_index(drop=True)
    print("OSM barrows", n_osm_raw, "after 5 m dedupe", len(o))

    # ---------- Wikidata ----------
    wd = json.load(open(os.path.join(D3, "wikidata_monuments.json")))
    seen = {}
    for klass in ("tumulus", "cairn"):
        for r in wd[klass]:
            if r.get("tLabel") == "clearance cairn":
                continue
            m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", r.get("c", ""))
            if not m:
                continue
            lon, lat = float(m[1]), float(m[2])
            if not (-32 <= lon <= 60 and 34 <= lat <= 72):
                continue
            q = r["i"]
            if q in seen:   # rows repeat through joins: keep first coordinate, collect periods
                s = seen[q]
                for k in ("perLabel", "culLabel"):
                    if r.get(k) and r[k] not in s[k]:
                        s[k].append(r[k])
                continue
            label = r.get("iLabel", "")
            seen[q] = dict(src="wikidata", id=q, lon=lon, lat=lat, name="" if re.fullmatch(r"Q\d+", label or "") else label,
                           tl=r.get("tLabel", ""), klass=klass, perLabel=[r["perLabel"]] if r.get("perLabel") else [],
                           culLabel=[r["culLabel"]] if r.get("culLabel") else [], wcountry=r.get("country", ""))
    w = []
    for q, s in seen.items():
        tl = s["tl"]
        tags = [tl if not re.fullmatch(r"Q\d+", tl or "") else "", "cairn" if s["klass"] == "cairn" else ""]
        w.append(dict(src="wikidata", id=q, lon=s["lon"], lat=s["lat"], name=s["name"],
                      kind=kind_of(s["name"], tags), period=period_of(*(s["perLabel"] + s["culLabel"])),
                      per_raw=";".join(s["perLabel"] + s["culLabel"]), cls=tl, wd=q, wcountry=s["wcountry"]))
    w = pd.DataFrame(w)
    n_wd_raw = len(w)
    # drop Wikidata items already in OSM: same QID, or an OSM barrow within 30 m
    in_osm_qid = set(o.wd[o.wd != ""])
    dup_q = w.id.isin(in_osm_qid)
    WX, WY = T.transform(w.lon.values, w.lat.values)
    dist, _ = tree.query(np.c_[WX, WY], k=1)   # tree still holds all raw OSM barrows, which is what we want here
    dup_near = dist <= 30
    w["dup"] = np.where(dup_q, "qid", np.where(dup_near, "near", ""))
    print("Wikidata barrows", n_wd_raw, "same QID in OSM", int(dup_q.sum()), "within 30 m", int((dup_near & ~dup_q).sum()))
    b = pd.concat([o.assign(wcountry="", dup=""), w], ignore_index=True)
    b["group"] = [(bool(GROUP_RX.search(n or "")) and not re.search(r"part of|: cairn|cairn [ivx]+$", n or "", re.I)) or (c == "tumuli group") for n, c in zip(b.name, b.cls)]

    # ---------- country ----------
    ne = json.load(open(os.path.join(D3, "ne", "geojson", "ne_10m_admin_0_countries.geojson")))
    geoms, names, iso, cont = [], [], [], []
    for f in ne["features"]:
        p = f["properties"]
        g = shape(f["geometry"])
        if not g.intersects(CLIP):
            continue
        a3 = p["ADM0_A3"]
        if p["CONTINENT"] != "Europe" and a3 not in EDGE:
            continue
        g = g.intersection(CLIP)
        if g.is_empty:
            continue
        geoms.append(g); names.append(p["ADMIN"] if a3 != "SRB" else "Serbia"); iso.append(a3)
        cont.append("edge" if a3 in EDGE else "europe")
    st = STRtree(geoms)
    pts = shapely.points(b.lon.values, b.lat.values)
    idx_pt, idx_g = st.query(pts, predicate="within")
    ci = np.full(len(b), -1)
    ci[idx_pt] = idx_g
    miss = np.where(ci < 0)[0]
    if len(miss):
        near, d = st.query_nearest(pts[miss], return_distance=True, all_matches=False)
        # d is in degrees; accept within ~10 km (0.12 deg is a loose bound; check in km below)
        for k, (pi, gi) in enumerate(zip(near[0], near[1])):
            i = miss[pi]
            p1 = shapely.ops.nearest_points(geoms[gi], pts[i])[0]
            x1, y1 = T.transform(p1.x, p1.y); x2, y2 = T.transform(pts[i].x, pts[i].y)
            if np.hypot(x1 - x2, y1 - y2) <= 10000:
                ci[i] = gi
    b["iso"] = [iso[i] if i >= 0 else "" for i in ci]
    b["country"] = [names[i] if i >= 0 else "" for i in ci]
    b["zone"] = [cont[i] if i >= 0 else "outside" for i in ci]
    print("zone", Counter(b.zone))
    X, Y = T.transform(b.lon.values, b.lat.values)
    b["x"], b["y"] = np.round(np.asarray(X) / 1000, 3), np.round(np.asarray(Y) / 1000, 3)
    b[["src", "id", "iso", "zone", "dup", "name"]].to_pickle(os.path.join(WORK, "all_records.pkl"))   # incl. Wikidata duplicates, for coverage checks
    n_outside = int(((b.zone == "outside") & (b.dup == "")).sum())
    b = b[(b.zone != "outside") & (b.dup == "")].drop(columns=["dup"]).reset_index(drop=True)
    b.to_pickle(os.path.join(WORK, "barrows.pkl"))
    cols = ["src", "id", "name", "lon", "lat", "country", "iso", "zone", "kind", "group", "cls", "period", "per_raw", "wd"]
    out = b[cols].copy()
    out["lon"] = out.lon.round(6); out["lat"] = out.lat.round(6)
    out.to_csv(os.path.join(ROOT, "data", "barrows.csv"), index=False)
    pickle.dump(dict(geoms=geoms, names=names, iso=iso, cont=cont), open(os.path.join(WORK, "countries_geom.pkl"), "wb"))
    meta = dict(n_osm_raw=n_osm_raw, n_osm=len(o), n_osm_near_dupes=len(drop), n_wd_raw=n_wd_raw,
                n_wd_dup_qid=int(dup_q.sum()), n_wd_dup_near=int((dup_near & ~dup_q).sum()), n_wd_kept=int((w.dup == "").sum()),
                n_outside=n_outside, n_total=len(b))
    json.dump(meta, open(os.path.join(WORK, "build_meta.json"), "w"), indent=1)
    print(meta)
    print(Counter(b.kind)); print(Counter(b.period)); print(b.groupby(["zone", "src"]).size())


if __name__ == "__main__":
    import shapely.ops
    main()
