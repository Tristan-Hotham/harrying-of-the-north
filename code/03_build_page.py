"""Step 3. Build index.html from code/page_template.html.

Every number in the text is a {{path|format}} token filled from data/results.json, so the page
cannot drift from the analysis. The map and chart data (_work/site.json from step 2) and a slim copy
of results.json are embedded so the page works as a single file.

Usage:
    python3 code/03_build_page.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json"), encoding="utf-8"))
SITE = open(os.path.join(ROOT, "_work", "site.json"), encoding="utf-8").read()
tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f is None or f == "raw":
        return str(v)
    if f == "int":
        return f"{round(v):,}"
    if f == "pct":
        return f"{round(v * 100)}%"
    if f == "pct1":
        return f"{v * 100:.1f}%"
    if f == "pctabs":
        return f"{abs(v) * 100:.1f}%"
    if f == "pp":
        return f"{v * 100:+.1f}".replace("+", "+")
    if f == "f2":
        return f"{v:.2f}"
    if f == "f1":
        return f"{v:.1f}"
    raise ValueError(f)


used = []


def sub(m):
    used.append(m.group(1))
    return fmt(get(m.group(1)), m.group(3))


html = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", sub, tpl)
slim = {k: R[k] for k in ["text_reading", "geo_logit", "hex_over_half"]}
html = html.replace("/*SITE*/", SITE).replace("/*RESULTS*/", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
assert "{{" not in html
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("index.html", len(html.encode()), "bytes;", len(used), "tokens filled")
