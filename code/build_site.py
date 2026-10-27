"""Step 4: build ../index.html and ../README.md from page_template.html and README_template.md.

Every number in the text is a placeholder like {{c.Denmark.n|int}} filled from ../data/results.json.
The results needed by the charts are embedded as `const R = ...`; the per-barrow map data are
loaded by the page from data/page.json. Formats: int, pct0, pct1, f0, f1, f2, raw.
"""
import json
import os
import re
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct0": return f"{int(Decimal(str(v * 100)).quantize(Decimal('1'), ROUND_HALF_UP))}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f0": return f"{v:,.0f}"
    if f == "f1": return f"{v:.1f}"
    if f == "f2": return f"{v:.2f}"
    return str(v)


def fill(text):
    return re.sub(r"\{\{([^{}|]+?)(?:\|(\w+))?\}\}", lambda m: fmt(get(m.group(1).strip()), m.group(2) or "raw"), text)


if __name__ == "__main__":
    t = fill(open(os.path.join(HERE, "page_template.html")).read())
    keep = {k: R[k] for k in ["countries", "kinds", "kind_order", "kind_label", "periods", "latitude", "dates"]}
    keep["countries"] = [{k: v for k, v in c.items() if not k.startswith("n_period_")} for c in keep["countries"]]
    t = t.replace("/*DATA*/", "const R = " + json.dumps(keep, separators=(",", ":"), ensure_ascii=False) + ";")
    open(os.path.join(ROOT, "index.html"), "w").write(t)
    print("index.html", len(t.encode()) // 1024, "KB")
    p = os.path.join(HERE, "README_template.md")
    if os.path.exists(p):
        open(os.path.join(ROOT, "README.md"), "w").write(fill(open(p).read()))
        print("README.md")
