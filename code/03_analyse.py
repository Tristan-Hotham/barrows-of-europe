"""Step 3: densities, coverage, latitude profiles, types, periods and dates -> data/results.json.

Inputs : work/barrows.pkl, work/all_records.pkl, work/countries_geom.pkl (step 1), work/spd.json and
         data/barrow_dates.csv (step 2), the OSM pull again (for the megalith comparison).
Outputs: data/results.json   every number used on the page, in the paper, blog and collage
         data/countries.csv  one row per country: counts by source and type, area, density, coverage class
         data/cells_50km.csv one row per 50 km grid square (ETRS89-LAEA, EPSG:3035) with land in the study area
         data/latitude_profile.csv  one row per degree of latitude
         data/page.json      compact point data for the interactive map

Coverage class. A country is "register-fed" when Wikidata holds at least 250 barrow items for it
(before removing duplicates) and at least 1 per 1,000 km2: in practice, items created in bulk from a
national or regional heritage register. Elsewhere Wikidata has almost no barrows, and what we see
is what OpenStreetMap volunteers have mapped. Separately, a country is "OSM-dense" when OSM alone
gives more than 10 barrows per 1,000 km2.

Density: barrows per 1,000 km2 of land (Natural Earth 1:10m, clipped to the study area).
50 km squares: squares with less than 250 km2 of land are left out of density maps and ranks
(coastal slivers give silly densities); presence = the square holds at least one barrow.
"""
import json
import os
import pickle
import re
from collections import Counter

import numpy as np
import pandas as pd
import shapely
from shapely import STRtree
from shapely.geometry import box
from pyproj import Transformer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
D3 = os.environ.get("DATA3", os.path.join(ROOT, "..", "_data3"))
WORK = os.path.join(ROOT, "work")
T = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
TI = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
CELL = 50.0
KINDS = ["mound", "round", "long", "cairn", "kurgan"]
KIND_LABEL = {"mound": "Mound or tumulus", "round": "Round barrow", "long": "Long barrow or long cairn", "cairn": "Burial cairn",
              "kurgan": "Kurgan or mogila"}
PERIODS = ["neolithic", "bronze", "iron", "roman", "medieval", "prehistoric"]
PERIOD_LABEL = {"neolithic": "Neolithic or Copper Age", "bronze": "Bronze Age", "iron": "Iron Age", "roman": "Roman",
                "medieval": "Early medieval or Viking", "prehistoric": "Prehistoric, unspecified", "other": "Other", "": "No period"}
STEPPE_BOX = (28, 44, 50, 52)   # lon0, lat0, lon1, lat1: a simple box for the Pontic and Caspian steppe


def proj(g):
    return shapely.transform(g, lambda a: np.column_stack(T.transform(a[:, 0], a[:, 1])) / 1000)


def r3(x):
    return round(float(x), 3)


def main():
    b = pd.read_pickle(os.path.join(WORK, "barrows.pkl"))
    allr = pd.read_pickle(os.path.join(WORK, "all_records.pkl"))
    G = pickle.load(open(os.path.join(WORK, "countries_geom.pkl"), "rb"))
    meta = json.load(open(os.path.join(WORK, "build_meta.json")))
    R = {"build": meta}
    eu = b[b.zone == "europe"]

    # ---------- country areas ----------
    pg = [proj(g) for g in G["geoms"]]
    area = {}
    for iso, g in zip(G["iso"], pg):
        area[iso] = area.get(iso, 0) + g.area
    name_of = dict(zip(G["iso"], G["names"]))
    zone_of = dict(zip(G["iso"], G["cont"]))
    land_eu = sum(a for i, a in area.items() if zone_of[i] == "europe")

    # ---------- megaliths in the same OSM pull (for the mound share) ----------
    osm = json.load(open(os.path.join(D3, "osm_monuments_europe.json")))
    barrow_ids = set(b.id[b.src == "osm"])
    meg = [(r["lon"], r["lat"]) for r in osm if r.get("as") == "megalith" and r["o"] not in barrow_ids and (r.get("mt") or "") not in ("nuraghe",)]
    mx = np.array(meg)
    st = STRtree(G["geoms"])
    pi, gi = st.query(shapely.points(mx[:, 0], mx[:, 1]), predicate="within")
    meg_iso = Counter(G["iso"][g] for g in gi)

    # ---------- country table ----------
    wd_raw = allr[allr.src == "wikidata"].groupby("iso").size()
    wd_unl = allr[(allr.src == "wikidata")].assign(unl=lambda d: d.name.fillna("").eq("") | d.name.fillna("").str.contains(r"^Cultural heritage|^Q\d+$"))
    wd_unl = wd_unl.groupby("iso").unl.mean()
    rows = []
    for iso in sorted(area, key=lambda i: -area[i]):
        d = b[b.iso == iso]
        osm_n = int((d.src == "osm").sum()); wd_n = int((d.src == "wikidata").sum())
        a = area[iso]
        wr = int(wd_raw.get(iso, 0))
        row = dict(iso=iso, country=name_of[iso], zone=zone_of[iso], land_km2=round(a), n=len(d), n_osm=osm_n, n_wikidata=wd_n,
                   n_wikidata_before_dedupe=wr, wikidata_unlabelled_share=r3(wd_unl.get(iso, 0)) if wr else None,
                   per_1000km2=r3(len(d) / a * 1000), osm_per_1000km2=r3(osm_n / a * 1000), wikidata_raw_per_1000km2=r3(wr / a * 1000),
                   register_fed=bool(wr >= 250 and wr / a * 1000 >= 1.0), osm_dense=bool(osm_n / a * 1000 > 10),
                   n_megaliths_osm=int(meg_iso.get(iso, 0)), n_group_records=int(d.group.sum()))
        row["mound_share_osm"] = r3(osm_n / (osm_n + row["n_megaliths_osm"])) if osm_n + row["n_megaliths_osm"] >= 50 else None
        for k in KINDS:
            row["n_" + k] = int((d.kind == k).sum())
        for p in PERIODS:
            row["n_period_" + p] = int((d.period == p).sum())
        rows.append(row)
    C = pd.DataFrame(rows)

    # ---------- 50 km cells ----------
    cty_proj = list(zip(G["iso"], pg))
    stp = STRtree(pg)
    x0, x1 = np.floor(b.x.min() / CELL) * CELL - CELL, np.ceil(b.x.max() / CELL) * CELL + CELL
    allx = np.concatenate([np.array(g.bounds)[[0, 2]] for g in pg]); ally = np.concatenate([np.array(g.bounds)[[1, 3]] for g in pg])
    X0, X1 = np.floor(allx.min() / CELL) * CELL, np.ceil(allx.max() / CELL) * CELL
    Y0, Y1 = np.floor(ally.min() / CELL) * CELL, np.ceil(ally.max() / CELL) * CELL
    cells = []
    for cx in np.arange(X0, X1, CELL):
        for cy in np.arange(Y0, Y1, CELL):
            bx = box(cx, cy, cx + CELL, cy + CELL)
            hits = stp.query(bx, predicate="intersects")
            if not len(hits):
                continue
            parts = {}
            for h in hits:
                ar = pg[h].intersection(bx).area
                if ar > 0:
                    parts[G["iso"][h]] = parts.get(G["iso"][h], 0) + ar
            if not parts:
                continue
            land = sum(parts.values())
            main_iso = max(parts, key=parts.get)
            cells.append(dict(i=int(cx // CELL), j=int(cy // CELL), x=cx, y=cy, land_km2=land, iso=main_iso, zone=zone_of[main_iso]))
    cells = pd.DataFrame(cells)
    b["ci"] = np.floor(b.x / CELL).astype(int); b["cj"] = np.floor(b.y / CELL).astype(int)
    cnt = b.groupby(["ci", "cj"]).size().rename("n")
    cnt_o = b[b.src == "osm"].groupby(["ci", "cj"]).size().rename("n_osm")
    cnt_w = b[b.src == "wikidata"].groupby(["ci", "cj"]).size().rename("n_wikidata")
    cells = cells.merge(cnt, left_on=["i", "j"], right_index=True, how="left").merge(cnt_o, left_on=["i", "j"], right_index=True, how="left") \
                 .merge(cnt_w, left_on=["i", "j"], right_index=True, how="left").fillna({"n": 0, "n_osm": 0, "n_wikidata": 0})
    for k in ("n", "n_osm", "n_wikidata"):
        cells[k] = cells[k].astype(int)
    cells["per_1000km2"] = cells.n / cells.land_km2 * 1000
    cx = cells.x.values + CELL / 2; cy = cells.y.values + CELL / 2
    lo, la = TI.transform(cx * 1000, cy * 1000)
    cells["lon"], cells["lat"] = np.round(lo, 4), np.round(la, 4)
    full = cells[cells.land_km2 >= 250].copy()
    full["register_fed"] = full.iso.map(dict(zip(C.iso, C.register_fed)))
    # presence by country (squares mostly in that country)
    pres = full.groupby("iso").agg(cells=("n", "size"), with_barrow=("n", lambda s: int((s > 0).sum())))
    C = C.merge(pres, left_on="iso", right_index=True, how="left")
    C["presence_share"] = (C.with_barrow / C.cells).round(3)
    C.to_csv(os.path.join(ROOT, "data", "countries.csv"), index=False)
    cout = cells.copy()
    corners = []
    for x, y in zip(cout.x.values, cout.y.values):
        xs = np.array([x, x + CELL, x + CELL, x]) * 1000; ys = np.array([y, y, y + CELL, y + CELL]) * 1000
        lo4, la4 = TI.transform(xs, ys)
        corners.append(";".join(f"{a:.4f},{c:.4f}" for a, c in zip(lo4, la4)))
    cout["corners_lonlat"] = corners
    cout[["i", "j", "lon", "lat", "iso", "zone", "land_km2", "n", "n_osm", "n_wikidata", "per_1000km2", "corners_lonlat"]] \
        .round({"land_km2": 1, "per_1000km2": 3}).to_csv(os.path.join(ROOT, "data", "cells_50km.csv"), index=False)

    # ---------- headline totals ----------
    R["totals"] = dict(all=len(b), europe=len(eu), edge=int((b.zone == "edge").sum()), osm=int((b.src == "osm").sum()),
                       wikidata=int((b.src == "wikidata").sum()), europe_osm=int((eu.src == "osm").sum()), europe_wikidata=int((eu.src == "wikidata").sum()),
                       europe_land_km2=round(land_eu), europe_per_1000km2=r3(len(eu) / land_eu * 1000),
                       countries_with_any=int((C[C.zone == "europe"].n > 0).sum()), countries_europe=int((C.zone == "europe").sum()),
                       group_records=int(eu.group.sum()), named=int(eu.name.fillna("").ne("").sum()))
    top = C[C.zone == "europe"].sort_values("n", ascending=False)
    R["top5_share"] = r3(top.n.head(5).sum() / len(eu))
    R["top5"] = top.country.head(5).tolist()
    reg = C[(C.zone == "europe") & C.register_fed]
    R["register_countries"] = reg.sort_values("n", ascending=False).country.tolist()
    R["register_share"] = r3(reg.n.sum() / len(eu))
    R["register_land_share"] = r3(reg.land_km2.sum() / land_eu)
    R["osm_dense_countries"] = C[(C.zone == "europe") & C.osm_dense].sort_values("n_osm", ascending=False).country.tolist()
    nonreg = C[(C.zone == "europe") & ~C.register_fed]
    R["nonregister"] = dict(n=int(nonreg.n.sum()), land_km2=round(nonreg.land_km2.sum()), per_1000km2=r3(nonreg.n.sum() / nonreg.land_km2.sum() * 1000))
    R["regfed"] = dict(n=int(reg.n.sum()), land_km2=round(reg.land_km2.sum()), per_1000km2=r3(reg.n.sum() / reg.land_km2.sum() * 1000))

    # country records for the page (all with n >= 1, plus a few big empty ones)
    ccols = ["iso", "country", "zone", "land_km2", "n", "n_osm", "n_wikidata", "n_wikidata_before_dedupe", "wikidata_unlabelled_share", "per_1000km2", "osm_per_1000km2",
             "register_fed", "osm_dense", "presence_share", "cells", "with_barrow", "mound_share_osm", "n_megaliths_osm", "n_group_records"] + ["n_" + k for k in KINDS] + ["n_period_" + p for p in PERIODS]
    R["countries"] = json.loads(C[ccols].sort_values("n", ascending=False).to_json(orient="records"))
    R["c"] = {r["country"]: r for r in R["countries"]}

    # ---------- types ----------
    R["kinds"] = {k: dict(n=int((eu.kind == k).sum()), share=r3((eu.kind == k).mean()), label=KIND_LABEL[k]) for k in KINDS}
    R["kind_order"] = KINDS
    R["kind_label"] = KIND_LABEL
    # where are the named kurgans and long barrows?
    for k in ("kurgan", "long", "round", "cairn"):
        s = b[b.kind == k].country.value_counts()
        R["kinds"][k]["top"] = [[c, int(n)] for c, n in s.head(6).items()]
    kur = b[b.kind == "kurgan"]
    R["kurgan_lon_east_of_20_share"] = r3((kur.lon > 20).mean())

    # ---------- periods (tags) ----------
    pe = eu[eu.period.isin(PERIODS)]
    R["periods"] = dict(n_tagged=int(len(pe)), share_tagged=r3(len(pe) / len(eu)),
                        counts={p: int((pe.period == p).sum()) for p in PERIODS}, label=PERIOD_LABEL, order=PERIODS)
    by_c = pe.groupby("country").size().sort_values(ascending=False)
    R["periods"]["top_countries"] = [[c, int(n)] for c, n in by_c.head(8).items()]
    known = pe[pe.period != "prehistoric"]
    R["periods"]["known_specific"] = int(len(known))
    R["periods"]["specific_shares"] = {p: r3((known.period == p).mean()) for p in PERIODS if p != "prehistoric"}
    R["periods"]["by_country"] = {c: {p: int(((pe.country == c) & (pe.period == p)).sum()) for p in PERIODS} for c in by_c.head(8).index}

    # ---------- latitude profile ----------
    lat_rows = []
    feu = full[full.zone == "europe"]
    for lat0 in range(34, 72):
        d = eu[(eu.lat >= lat0) & (eu.lat < lat0 + 1)]
        c = feu[(feu.lat >= lat0) & (feu.lat < lat0 + 1)]
        land = c.land_km2.sum()
        cr = c[~c.register_fed.astype(bool)]
        dn = d[~d.iso.map(dict(zip(C.iso, C.register_fed))).astype(bool)]
        lat_rows.append(dict(lat=lat0, land_km2=round(land), n=len(d), n_osm=int((d.src == "osm").sum()), n_wikidata=int((d.src == "wikidata").sum()),
                             n_nonregister=len(dn), land_nonregister_km2=round(cr.land_km2.sum()),
                             per_1000km2=r3(len(d) / land * 1000) if land else None,
                             per_1000km2_nonregister=r3(len(dn) / cr.land_km2.sum() * 1000) if cr.land_km2.sum() > 20000 else None,
                             presence=r3((c.n > 0).mean()) if len(c) else None,
                             presence_nonregister=r3((cr.n > 0).mean()) if len(cr) >= 10 else None, cells=len(c)))
    L = pd.DataFrame(lat_rows)
    L.to_csv(os.path.join(ROOT, "data", "latitude_profile.csv"), index=False)
    R["latitude"] = json.loads(L.to_json(orient="records"))

    def north(df, col, landcol, th=50):
        return r3(df[df.lat >= th][col].sum() / df[col].sum()), r3(df[df.lat >= th][landcol].sum() / df[landcol].sum())
    R["north50"] = dict(share_all=north(L, "n", "land_km2")[0], land_share=north(L, "n", "land_km2")[1],
                        share_osm=north(L, "n_osm", "land_km2")[0], share_wikidata=north(L, "n_wikidata", "land_km2")[0],
                        share_nonregister=north(L, "n_nonregister", "land_nonregister_km2")[0], land_share_nonregister=north(L, "n_nonregister", "land_nonregister_km2")[1])
    # band 50 to 60 N vs rest
    band = L[(L.lat >= 50) & (L.lat < 60)]
    R["belt"] = dict(share_n=r3(band.n.sum() / L.n.sum()), share_land=r3(band.land_km2.sum() / L.land_km2.sum()),
                     share_n_nonregister=r3(band.n_nonregister.sum() / L.n_nonregister.sum()), share_land_nonregister=r3(band.land_nonregister_km2.sum() / L.land_nonregister_km2.sum()),
                     presence_band=r3((feu[(feu.lat >= 50) & (feu.lat < 60)].n > 0).mean()), presence_south=r3((feu[feu.lat < 50].n > 0).mean()),
                     presence_north=r3((feu[feu.lat >= 60].n > 0).mean()))
    fnr = feu[~feu.register_fed.astype(bool)]
    R["belt"]["presence_band_nonregister"] = r3((fnr[(fnr.lat >= 50) & (fnr.lat < 60)].n > 0).mean())
    R["belt"]["presence_south_nonregister"] = r3((fnr[fnr.lat < 50].n > 0).mean())
    R["belt"]["presence_north_nonregister"] = r3((fnr[fnr.lat >= 60].n > 0).mean())
    R["cells"] = dict(n_cells=len(full[full.zone == "europe"]), with_barrow=int((feu.n > 0).sum()), presence=r3((feu.n > 0).mean()),
                      max_per_1000km2=r3(feu.per_1000km2.max()), median_nonzero=r3(feu[feu.n > 0].per_1000km2.median()))
    topc = feu.sort_values("per_1000km2", ascending=False).head(10)
    R["cells"]["top10"] = [dict(iso=r.iso, country=name_of[r.iso], lon=r.lon, lat=r.lat, n=int(r.n), per_1000km2=r3(r.per_1000km2)) for r in topc.itertuples()]
    R["cells"]["top10_countries"] = Counter(name_of[i] for i in topc.iso).most_common()
    # share of all barrows in the densest 5% of squares
    srt = feu.sort_values("n", ascending=False)
    k5 = max(1, int(round(len(feu) * 0.05)))
    R["cells"]["top5pct_squares"] = k5
    R["cells"]["top5pct_share"] = r3(srt.n.head(k5).sum() / feu.n.sum())

    # ---------- steppe ----------
    s0 = STEPPE_BOX
    stp_b = eu[(eu.lon >= s0[0]) & (eu.lon < s0[2]) & (eu.lat >= s0[1]) & (eu.lat < s0[3])]
    stp_c = feu[(feu.lon >= s0[0]) & (feu.lon < s0[2]) & (feu.lat >= s0[1]) & (feu.lat < s0[3])]
    R["steppe"] = dict(box=s0, n=len(stp_b), land_km2=round(stp_c.land_km2.sum()), per_1000km2=r3(len(stp_b) / stp_c.land_km2.sum() * 1000),
                       presence=r3((stp_c.n > 0).mean()), cells=len(stp_c), kurgan_named=int((stp_b.kind == "kurgan").sum()),
                       group_records=int(stp_b.group.sum()), osm_share=r3((stp_b.src == "osm").mean()))
    nw = eu[eu.iso.isin(["GBR", "IRL", "DNK", "NLD", "DEU", "SWE", "IMN"])]
    R["kurgans_ru_ua"] = int(b[b.iso.isin(["RUS", "UKR"])].shape[0])

    # ---------- dates ----------
    S = json.load(open(os.path.join(WORK, "spd.json")))
    dts = pd.read_csv(os.path.join(ROOT, "data", "barrow_dates.csv"))
    R["dates"] = dict(meta=S["meta"])
    BINS = ["before 2500 BC", "2500 to 800 BC", "800 BC to AD 400", "AD 400 to 1100", "after AD 1100"]
    R["dates"]["bins"] = BINS
    for setname in ("name", "wide"):
        out = {}
        for r, v in S[setname].items():
            tot = sum(v["bins"].values())
            out[r] = dict(sites=v["sites"], dates=v["dates"], bins={k: r3(v["bins"][k] / tot) if tot else 0 for k in BINS})
            yrs = np.array(S["year"]); sp = np.array(v["spd"])
            if len(sp) and sp.max() > 0:
                out[r]["peak_year"] = int(yrs[sp.argmax()])
                # main peak in each half: before and after 2500 BC
                pre = yrs < -2500
                out[r]["peak_neolithic"] = int(yrs[pre][sp[pre].argmax()]) if sp[pre].max() > 0 else None
                out[r]["peak_later"] = int(yrs[~pre][sp[~pre].argmax()]) if sp[~pre].max() > 0 else None
        R["dates"][setname] = out
    nm = dts[dts.link == "name"]
    longd = nm[nm.matched_word.fillna("").str.lower().str.contains("long")]
    other = nm[~nm.matched_word.fillna("").str.lower().str.contains("long")]
    def wmed(d, w):
        o = d.sort_values("year_median"); c = o[w].cumsum() / o[w].sum()
        return int(o.year_median.values[np.searchsorted(c.values, 0.5)])
    R["dates"]["long_named"] = dict(dates=len(longd), sites=int(longd.SiteName.nunique()), median_year=wmed(longd, "w_name"),
                                    share_before_2500=r3((longd.year_median < -2500).mean()))
    R["dates"]["other_named"] = dict(dates=len(other), sites=int(other.SiteName.nunique()), median_year=wmed(other, "w_name"),
                                     share_before_2500=r3((other.year_median < -2500).mean()))
    R["dates"]["region_median"] = {r: wmed(dts[dts.region == r], "w_wide") for r in ["Britain and Ireland", "Scandinavia", "West and central Europe", "East Europe and the steppe"]}
    R["dates"]["region_order"] = ["Britain and Ireland", "Scandinavia", "West and central Europe", "East Europe and the steppe"]
    R["dates"]["year_grid"] = S["year"]
    R["dates"]["spd"] = {s: {r: S[s][r]["spd"] for r in S[s]} for s in ("name", "wide")}

    # ---------- Wikidata beyond Europe, and the Danish double record ----------
    wdj = json.load(open(os.path.join(D3, "wikidata_monuments.json")))
    world = {}
    for klass in ("tumulus", "cairn"):
        for r in wdj[klass]:
            if r.get("tLabel") == "clearance cairn":
                continue
            m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", r.get("c", ""))
            if m:
                world[r["i"]] = (float(m[1]), float(m[2]), (r.get("tLabel") or "").lower())
    wl = np.array([[v[0], v[1]] for v in world.values()])
    inbox = (wl[:, 0] >= -32) & (wl[:, 0] <= 60) & (wl[:, 1] >= 34) & (wl[:, 1] <= 72)
    R["wikidata_world"] = dict(items=len(world), in_box=int(inbox.sum()), share_in_box=r3(inbox.mean()),
                               kofun=int(sum(1 for v in world.values() if "fun" in v[2] or "kofun" in v[2])))
    o = b[b.src == "osm"]
    from scipy.spatial import cKDTree
    tr = cKDTree(np.c_[o.x.values * 1000, o.y.values * 1000])
    dkq = set(allr[(allr.src == "wikidata") & (allr.iso == "DNK")].id)
    dk = [(v[0], v[1]) for q, v in world.items() if q in dkq]
    X, Y = T.transform(np.array(dk)[:, 0], np.array(dk)[:, 1])
    dd, _ = tr.query(np.c_[X, Y])
    R["denmark_double"] = dict(items=len(dk), within_30m=r3((dd <= 30).mean()), median_m=round(float(np.median(dd)), 1))

    # ---------- provenance signals of the Wikidata imports ----------
    wa = allr[allr.src == "wikidata"].copy()
    wa["unl"] = wa.name.fillna("").eq("")
    wb = b[b.src == "wikidata"]
    R["provenance"] = dict(
        sweden_unlabelled=r3(wa[wa.iso == "SWE"].unl.mean()), denmark_unlabelled=r3(wa[wa.iso == "DNK"].unl.mean()),
        germany_bavarian_label=r3(wa[wa.iso == "DEU"].name.fillna("").str.startswith("Cultural heritage D-").mean()),
        germany_in_bavaria_box=r3(((wb.iso == "DEU") & (wb.lat > 47.2) & (wb.lat < 50.6) & (wb.lon > 8.9) & (wb.lon < 13.9)).sum() / (wb.iso == "DEU").sum()),
        spain_in_basque_box=r3(((wb.iso == "ESP") & (wb.lat > 42.4) & (wb.lat < 43.5) & (wb.lon > -3.5) & (wb.lon < -1.6)).sum() / (wb.iso == "ESP").sum()))

    # ---------- derived values written as text on the page ----------
    def era(y):
        y = int(round(y / 10.0) * 10)
        return f"{-y} BC" if y < 0 else f"AD {y}"
    dn = R["dates"]["name"]
    R["x"] = dict(long_median=era(R["dates"]["long_named"]["median_year"]), other_median=era(R["dates"]["other_named"]["median_year"]),
                  bi_neo_peak=era(dn["Britain and Ireland"]["peak_neolithic"]), bi_later_peak=era(dn["Britain and Ireland"]["peak_later"]),
                  after_800bc=r3(sum(dn["All"]["bins"][k] for k in BINS[2:])),
                  near_sites=R["dates"]["meta"]["n_sites_wide"] - R["dates"]["meta"]["n_sites_name"],
                  register_list=", ".join(R["register_countries"][:-1]) + " and " + R["register_countries"][-1],
                  n_nonreg_countries=int(((C.zone == "europe") & ~C.register_fed).sum()), osm_pull=len(osm))

    # ---------- page data ----------
    kinds_i = {k: i for i, k in enumerate(KINDS)}
    per_list = PERIODS + ["other", ""]
    per_i = {p: i for i, p in enumerate(per_list)}
    isos = sorted(b.iso.unique())
    iso_i = {k: i for i, k in enumerate(isos)}
    # a few source names contain en or em dashes; show them as hyphens on the page
    names = [n.replace("\u2013", "-").replace("\u2014", "-") for n in b.name.fillna("")]
    P = dict(lat=np.round(b.lat.values * 1e4).astype(int).tolist(), lon=np.round(b.lon.values * 1e4).astype(int).tolist(),
             k=[kinds_i[k] for k in b.kind], p=[per_i.get(p, len(per_list) - 1) for p in b.period], c=[iso_i[i] for i in b.iso],
             s=[0 if s == "osm" else 1 for s in b.src], g=[1 if g else 0 for g in b.group],
             id=[(i.replace("node/", "n").replace("way/", "w").replace("relation/", "r") if s == "osm" else i) for i, s in zip(b.id, b.src)],
             nm=names, kinds=KINDS, periods=per_list, isos=isos, cnames=[name_of.get(i, i) for i in isos])
    # dates for the timeline (strict and wide), compact
    P["dates"] = dict(y=dts.year_median.astype(int).tolist(), lo=(1950 - dts.cal_hi_bp).astype(int).tolist(), hi=(1950 - dts.cal_lo_bp).astype(int).tolist(),
                      r=[R["dates"]["region_order"].index(r) if r in R["dates"]["region_order"] else -1 for r in dts.region],
                      l=[0 if l == "name" else 1 for l in dts.link], site=dts.SiteName.fillna("").tolist(), lab=dts.LabID.fillna("").tolist(),
                      age=dts.Age.astype(int).tolist(), err=dts.Error.astype(int).tolist(), cty=dts.Country.fillna("").tolist())
    cidx = {(i, j): n for n, (i, j) in enumerate(zip(cout.i, cout.j))}
    P["ci"] = [cidx.get((i, j), -1) for i, j in zip(b.ci, b.cj)]
    P["cells"] = dict(c=cout.corners_lonlat.tolist(), n=cout.n.tolist(), land=cout.land_km2.round(0).astype(int).tolist(), iso=cout.iso.tolist())
    json.dump(P, open(os.path.join(ROOT, "data", "page.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    R["page_bytes"] = os.path.getsize(os.path.join(ROOT, "data", "page.json"))

    json.dump(R, open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({k: R[k] for k in ["totals", "top5", "top5_share", "register_countries", "register_share", "register_land_share", "osm_dense_countries",
                                         "nonregister", "regfed", "north50", "belt", "steppe", "cells"]}, indent=1, default=str))
    print(C[C.zone == "europe"].sort_values("n", ascending=False)[["country", "n", "n_osm", "n_wikidata", "n_wikidata_before_dedupe", "per_1000km2", "osm_per_1000km2",
                                                                   "register_fed", "presence_share", "mound_share_osm"]].head(30).to_string())
    print(json.dumps(R["dates"]["name"], indent=0)[:3000]); print(R["dates"]["long_named"], R["dates"]["other_named"], R["dates"]["region_median"])
    print(R["periods"])


if __name__ == "__main__":
    main()
