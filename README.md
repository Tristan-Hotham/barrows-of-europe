# Is the Barrow a European Thing?

Burial mounds and burial cairns (long barrows, round barrows, tumuli, cairns, kurgans) mapped across Europe from OpenStreetMap and Wikidata, with density by country and by 50 km square, an explicit account of which countries' heritage registers fed the data, and radiocarbon dates from barrows (p3k14c, calibrated with IntCal20).

**Interactive version:** https://tristan-hotham.github.io/barrows-of-europe/

By Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349). Companion studies: [The Megalith Highway](https://tristan-hotham.github.io/megalith-highway/) and [Stone circles](https://tristan-hotham.github.io/stone-circles/). Blog: https://blog.tristanhotham.com/

## Headline results

- 99,049 barrows mapped in Europe (1,331 more in Turkey and the Caucasus), in 40 of 51 countries; 32% of 50 km squares hold at least one.
- Raw counts lean north: 83% lie north of 50° N (62% of the land), 75% between 50° and 60° N (38% of the land). All ten densest 50 km squares are in Denmark and Sweden.
- But 92% of the records come from eight register-fed countries (Sweden, Denmark, Germany, United Kingdom, Spain, Finland, Netherlands and Slovenia) covering 20% of the land: 46.2 barrows per 1,000 km² there against 0.99 elsewhere. Outside them the northern lean disappears (41% north of 50° N on 61% of the land).
- Mounds as a share of mapped mounds plus megaliths (OpenStreetMap, a ratio that cancels mapping effort): France 5%, Portugal 6%, Ireland 28%; Netherlands 97%, Poland 95%, Hungary 100%, Ukraine 100%. An earthen mound belt from the North Sea to the steppe, stone tombs on the Atlantic edge.
- The steppe (28° to 50° E, 44° to 52° N) has 2,587 mapped barrows, 2.2 per 1,000 km², 99.5% from OpenStreetMap, 359 of them records for whole groups: too thinly recorded to test whether it is the other heartland.
- Radiocarbon: 489 dates from 132 sites named as barrows. Site-weighted, 33% fall before 2500 BC and 59% between 2500 and 800 BC. Long barrows: median 3640 BC; other barrows: median 1830 BC. The wider set (386 sites, adding dates within 100 m of a mapped barrow) gives 32% and 55%.

## Files

- `index.html`: the interactive page (Leaflet map drawn on canvas tiles with type, period, country and source filters and a 50 km density view; charts). Built by `code/build_site.py` from `code/page_template.html`; every number in the text comes from `data/results.json`. Map data: `data/page.json`.
- `header.png`: social card.
- `data/barrows.csv.gz` (gzipped CSV): one row per barrow: source (osm or wikidata), OSM id or Wikidata QID, name, lon, lat, country, zone (europe or edge), type, group flag, class or tag, period bin and raw period tags.
- `data/countries.csv`: per country: land area, counts by source and type, Wikidata items before de-duplication, density, register-fed and OSM-dense flags, presence in 50 km squares, megaliths and mound share, period counts.
- `data/cells_50km.csv`: every 50 km square (EPSG:3035 grid) touching land: centre, main country, land area, counts by source, density and corner coordinates.
- `data/latitude_profile.csv`: one-degree bands: land, counts, densities and presence, with and without register-fed countries.
- `data/barrow_dates.csv`: every linked radiocarbon date: p3k14c fields, how it was linked (name or near), the word matched, distance to the nearest mapped barrow, calibrated median and 95% range, period bin and site weights.
- `data/results.json`: every number used on the page, in the paper, the blog and the collage.
- `code/`: Python scripts, run in order by `code/run_all.sh`: `01_build.py` (selection, types, periods, duplicates, countries), `02_dates.py` (linking and calibration), `03_analyse.py` (everything else), `build_site.py`, `05_header.py`; `mapdraw.py` holds the static map helpers.

## How to rerun

Inputs (not included, read in place from `../_data3/`): the OpenStreetMap pull (`osm_monuments_europe.json`, QLever OSM planet endpoint, 27 October 2026), the Wikidata export (`wikidata_monuments.json`), the p3k14c repository (https://github.com/people3k/p3k14c, `inst/p3k14c_scrubbed_fuzzed.csv`), Natural Earth admin 0 countries (1:10m and 1:50m). The IntCal20 curve is read from `work/intcal/3Col_intcal20.14C`, the copy in the rintcal package (https://github.com/Maarten14C/rintcal, `inst/extdata`).

```
sh code/run_all.sh
```

Python 3 with pandas, numpy, scipy, shapely 2 and pyproj; matplotlib for the figures.

## Method in brief

Barrows: OSM objects tagged archaeological_site=tumulus or cairn, tomb=tumulus, or megalith_type long_barrow, round_barrow, barrow, chambered_cairn, ring_cairn or cairn; Wikidata items of class tumulus or cairn and their subclasses, except clearance cairns. Wikidata items linked from, or within 30 m of, an OSM barrow are dropped as duplicates. Countries from Natural Earth; Europe is Natural Earth's European countries clipped at 60° E. A country is register-fed when Wikidata holds at least 250 barrows for it and at least one per 1,000 km². Radiocarbon dates are linked by site name (strict) or by lying within 100 m of a mapped barrow (wide), calibrated with IntCal20, and weighted so that each site counts once.

Caveats: these are records, not mounds; national registers dominate the counts; group records undercount; types and periods are what the records say; dates come from barrow sites, mostly British and Scandinavian, and later mounds are under-dated by radiocarbon; OSM areas are placed at the first vertex of their outline.

## Sources and licence

- OpenStreetMap: © OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright
- Wikidata: CC0, https://www.wikidata.org/
- p3k14c: Bird, D. and others (2022) p3k14c, a synthetic global database of archaeological radiocarbon dates. Scientific Data 9, 27. CC BY 4.0.
- IntCal20: Reimer, P. J. and others (2020) The IntCal20 Northern Hemisphere radiocarbon age calibration curve (0 to 55 cal kBP). Radiocarbon 62(4).
- Natural Earth (public domain), https://www.naturalearthdata.com/
- Base map on the page: tiles © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community.

The barrow data in `data/` derive from OpenStreetMap and are released under the Open Database Licence (ODbL 1.0). Text and figures are CC BY 4.0. Code is MIT (see `LICENSE`).

## Citation

Hotham, T. (2026) *Is the Barrow a European Thing? Mapping and dating Europe's burial mounds*. Zenodo. https://doi.org/10.5281/zenodo.23685258

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
