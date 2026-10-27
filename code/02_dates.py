"""Step 2: radiocarbon dates from barrows (p3k14c), calibrated with IntCal20.

Input : ../_data3/p3k14c/inst/p3k14c_scrubbed_fuzzed.csv  (Bird et al. 2022, CC BY 4.0)
        work/intcal/3Col_intcal20.14C  (IntCal20, Reimer et al. 2020; the copy shipped in the
        rintcal R package, https://github.com/Maarten14C/rintcal, inst/extdata)

Linking rule (by site name only; p3k14c coordinates are fuzzed, so proximity to a mapped barrow
is not reliable). A date is a "barrow date" if its SiteName contains one of the barrow words in
BARROW (whole words or word endings, in the languages seen) and none of the exclusions in NOT.
Words: barrow(s), tumulus/tumuli/túmulo/tümülüs, kurgan/kurhan/курган, mogila/mohyla,
kunhalom, halomsír, cairn(s), howe, Danish -høj/-høje, Swedish hög/gravhög/röse, German
Grabhügel/Hügelgrab, Dutch grafheuvel, Galician mámoa, burial mound.
Exclusions: burnt mounds (cooking sites), towns and streets named Barrow, Hilleshög (a parish),
the word 'mound' on its own, dolmens, cairnfields (field clearance), material described as under
or adjacent to barrows, and, after reading the full list of matches, eight names that are not
barrows: Kraków-Mogiła (a district), Kamennaja Mogila (a rock-art hill), a bog (mose), and the
Orkney settlement sites Howe, The Howe, Howe Farm, Saevar Howe and Birsay Evie Howe. The matched site names are written to data/barrow_dates.csv
so every link can be audited.

Second, looser rule ("near"): the date's site position lies within 100 m of a barrow mapped in step 1.
p3k14c fuzzes coordinates mainly for North America; most European positions are as published,
but some are only approximate, and a site near a barrow need not be the barrow (a henge or
settlement next to one). I report the strict (name) set as the main result and the wide set
(name or near) as a check.

Dates kept: Age > 0, Error <= 300 years, not marine shell (reservoir offsets).
Calibration: each date's probability over calendar years (1-year grid, 0 to 15,000 cal BP) is
proportional to the normal density of its 14C age around the IntCal20 curve, with the curve and
lab errors added in quadrature. Summary: the median and the 95% range (2.5 to 97.5 percentiles).
Summed probability (SPD): each site's dates share a total weight of one, so a site with forty
dates counts the same as a site with one.

Outputs: data/barrow_dates.csv (one row per linked date, with the rule that linked it), work/spd.json
"""
import json
import os
import re

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
D3 = os.environ.get("DATA3", os.path.join(ROOT, "..", "_data3"))
WORK = os.path.join(ROOT, "work")
T = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)
NEAR_M = 100

BARROW = re.compile(
    r"\bbarrows?\b|tumul|túmul|tümül|kurgan|kurhan|курган|\bmogil|\bmohyl|kunhalom|halomsír|"
    r"\bcairns?\b|\bhowe\b|h[øo]j(?:e|ene)?\b|h[øo]i(?:e|ene)?\b|\bhög\b|gravh[öo]g|\bröse|gravr[öo]s|"
    r"grabh[üu]gel|h[üu]gelgr[aä]b|grafheuvel|m[áa]moa|burial mound|grave mound|long barrow|long cairn", re.I)
NOT = re.compile(r"burnt mound|barrow[- ]in[- ]furness|barrow[- ]upon|barrow[- ]on|barrow street|hilleshög|dysse|dolmen|\bhøjbjerg\b|\bhøjby\b|højgård|"
                 r"cairn ?field|\bunder\b|adjacent to|kraków-mogila|kamennaja mogila|\bmose\b|^howe$|^the howe$|howe farm|saevar howe|birsay evie howe", re.I)

REGIONS = {
    "Britain and Ireland": ["United Kingdom", "Ireland", "Isle of Man"],
    "Scandinavia": ["Denmark", "Sweden", "Norway", "Finland"],
    "West and central Europe": ["Netherlands", "Belgium", "France", "Germany", "Switzerland", "Austria", "Luxembourg", "Spain", "Portugal", "Italy"],
    "East Europe and the steppe": ["Poland", "Czechia", "Czech Republic", "Slovakia", "Hungary", "Romania", "Bulgaria", "Serbia", "Ukraine",
                                   "Russian Federation", "Moldova", "Belarus", "Lithuania", "Latvia", "Estonia", "Greece", "Croatia", "Slovenia",
                                   "North Macedonia", "Bosnia and Herzegovina", "Albania", "Montenegro", "Kosovo"],
}
REGION_OF = {c: r for r, cs in REGIONS.items() for c in cs}
BINS = [("before 2500 BC", -1e9, -2500), ("2500 to 800 BC", -2500, -800), ("800 BC to AD 400", -800, 400),
        ("AD 400 to 1100", 400, 1100), ("after AD 1100", 1100, 1e9)]


def load_curve():
    c = np.loadtxt(os.path.join(WORK, "intcal", "3Col_intcal20.14C"))
    grid = np.arange(0, 15001)
    mu = np.interp(grid, c[:, 0], c[:, 1])
    sg = np.interp(grid, c[:, 0], c[:, 2])
    return grid, mu, sg


def calibrate(age, err, grid, mu, sg):
    s2 = err ** 2 + sg ** 2
    p = np.exp(-0.5 * (age - mu) ** 2 / s2) / np.sqrt(s2)
    t = p.sum()
    return p / t if t > 0 else p


def main():
    d = pd.read_csv(os.path.join(D3, "p3k14c", "inst", "p3k14c_scrubbed_fuzzed.csv"), low_memory=False)
    e = d[(d.Long >= -32) & (d.Long <= 60) & (d.Lat >= 34) & (d.Lat <= 72)].copy()
    n_europe = len(e)
    nm = e.SiteName.fillna("")
    by_name = nm.apply(lambda s: bool(BARROW.search(s)) and not NOT.search(s))
    # distance from each date's site position to the nearest mapped barrow (step 1 table)
    b = pd.read_pickle(os.path.join(WORK, "barrows.pkl"))
    tree = cKDTree(np.c_[b.x.values * 1000, b.y.values * 1000])
    X, Y = T.transform(e.Long.values, e.Lat.values)
    dist, _ = tree.query(np.c_[X, Y])
    e["near_m"] = np.round(dist, 1)
    near = (e.near_m <= NEAR_M) & ~by_name
    e["link"] = np.where(by_name, "name", np.where(near, "near", ""))
    m = e[e.link != ""].copy()
    n_name, n_near = int(by_name.sum()), int(near.sum())
    mat = m.Material.fillna("").str.lower()
    bad_err = (m.Age <= 0) | (m.Error > 300)
    shell = mat.str.contains("shell|marine")
    m = m[~bad_err & ~shell].copy()
    m["region"] = m.Country.map(REGION_OF).fillna("Other")
    grid, mu, sg = load_curve()
    med, lo, hi = [], [], []
    P = np.zeros((len(m), len(grid)))
    for k, (a, s) in enumerate(zip(m.Age.values, m.Error.values)):
        p = calibrate(a, s, grid, mu, sg)
        P[k] = p
        cdf = np.cumsum(p)
        med.append(grid[np.searchsorted(cdf, 0.5)]); lo.append(grid[np.searchsorted(cdf, 0.025)]); hi.append(grid[np.searchsorted(cdf, 0.975)])
    m["cal_median_bp"] = med
    m["cal_lo_bp"] = lo
    m["cal_hi_bp"] = hi
    m["year_median"] = 1950 - m.cal_median_bp       # negative = BC (astronomical-style: -2499 = 2500 BC)
    m["site_key"] = m.SiteName.fillna("").str.strip() + "|" + m.Country.fillna("")
    m["bin"] = pd.cut(m.year_median, [x[1] for x in BINS] + [BINS[-1][2]], labels=[x[0] for x in BINS], right=False)
    m["matched_word"] = [(BARROW.search(s).group(0) if BARROW.search(s) else "") if l == "name" else "" for s, l in zip(m.SiteName.fillna(""), m.link)]
    # site weights within each linking set: strict (name) and wide (name or near)
    m["w_name"] = np.where(m.link == "name", 1.0 / m[m.link == "name"].groupby("site_key").Age.transform("size").reindex(m.index).fillna(1), 0)
    m["w_wide"] = 1.0 / m.groupby("site_key").Age.transform("size")
    cols = ["LabID", "Age", "Error", "Material", "Taxa", "SiteName", "Country", "region", "Long", "Lat", "LocAccuracy", "Source",
            "link", "matched_word", "near_m", "cal_median_bp", "cal_lo_bp", "cal_hi_bp", "year_median", "bin", "w_name", "w_wide"]
    m[cols].sort_values(["link", "region", "Country", "SiteName", "year_median"]).to_csv(os.path.join(ROOT, "data", "barrow_dates.csv"), index=False)

    # SPD per region, site weighted, calendar years 6000 BC to AD 1500
    years = 1950 - grid
    sel = (years >= -6000) & (years <= 1500)
    out = {"year": years[sel][::-1][::5].tolist()}
    for setname, wcol in (("name", "w_name"), ("wide", "w_wide")):
        out[setname] = {}
        for r in list(REGIONS) + ["All"]:
            idx = np.where((m[wcol].values > 0) & ((m.region.values == r) | (r == "All")))[0]
            ssum = (P[idx] * m[wcol].values[idx, None]).sum(0)[sel][::-1][::5] if len(idx) else np.zeros(int(sel.sum()))[::5]
            out[setname][r] = dict(spd=np.round(ssum / max(1e-12, ssum.max()), 4).tolist(),
                                   sites=int(m.iloc[idx].site_key.nunique()), dates=int(len(idx)),
                                   bins={x[0]: round(float(m.iloc[idx][m.iloc[idx].bin == x[0]][wcol].sum()), 3) for x in BINS})
    meta = dict(n_europe_dates=int(n_europe), n_name_matched=n_name, n_near_matched=n_near, n_kept=int(len(m)),
                n_dropped_error=int(bad_err.sum()), n_dropped_shell=int(shell.sum()), near_m=NEAR_M,
                n_sites_name=int(m[m.link == "name"].site_key.nunique()), n_dates_name=int((m.link == "name").sum()),
                n_sites_wide=int(m.site_key.nunique()), n_dates_wide=int(len(m)))
    out["meta"] = meta
    json.dump(out, open(os.path.join(WORK, "spd.json"), "w"))
    print(meta)
    for setname in ("name", "wide"):
        for r, v in out[setname].items():
            print(setname, r, v["sites"], v["dates"], v["bins"])


if __name__ == "__main__":
    main()
