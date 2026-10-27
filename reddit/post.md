# Reddit post

## Title

[OC] Is the barrow a European thing? 99,049 burial mounds and cairns mapped from Ireland to the steppe (OpenStreetMap and Wikidata), with radiocarbon dates. The northern "barrow belt" is mostly a belt of heritage registers

## Body

I mapped every burial mound and burial cairn in OpenStreetMap and Wikidata across Europe: 99,049 after removing duplicates. Raw counts lean hard to the north (83% north of 50° N), but 92% of the records come from eight countries that imported their heritage registers in bulk, on 20% of the land. A fairer measure, mounds as a share of mapped mounds plus megaliths, splits Europe in two: 5% in France, 97% in the Netherlands, almost 100% from Poland to Ukraine. Of 489 radiocarbon dates from sites named as barrows, 59% fall between 2500 and 800 BC. Caveat: these are records, not mounds; the steppe's kurgans are badly under-mapped.

Interactive version: https://tristan-hotham.github.io/barrows-of-europe/

## Source comment

Source: OpenStreetMap (© OpenStreetMap contributors, ODbL 1.0), objects tagged archaeological_site=tumulus or cairn and related tags, queried through QLever on 27 October 2026; Wikidata items of class tumulus (Q34023) and cairn (Q7321974) with subclasses (CC0); p3k14c global radiocarbon database, Bird et al. 2022, Scientific Data (CC BY 4.0), calibrated with the IntCal20 curve (Reimer et al. 2020); Natural Earth 1:10m and 1:50m countries (public domain).

Tools: Python (pandas, numpy, scipy, shapely, pyproj, matplotlib).

Interactive version: https://tristan-hotham.github.io/barrows-of-europe/
Blog post: https://blog.tristanhotham.com/2026/10/27/barrows-of-europe/
Paper: https://doi.org/10.5281/zenodo.23685258
