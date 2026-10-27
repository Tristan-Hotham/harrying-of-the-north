"""Step 1. Extract Domesday entries and places, waste and values, and link places to today.

Usage:
    python3 code/01_extract.py

Reads (in place, never copied):
  /home/claude/hist/realm-domesday/reference/*.yml   Hull Domesday Project data via realm-domesday (CC BY-NC-SA)
  /home/claude/hist/lost-villages/data/domesday_places_status.csv
        setting of every located Domesday place (height, relief, distance to water and to Roman roads)
        and the Beresford lost-village flag, from the companion project The Villages That Vanished
  /home/claude/hist/domesday-destiny/data/domesday_places.csv
        Census 2021 residents of the civil parish of each place, from the companion project Is Domesday Destiny?
  /home/claude/hist/_data8/ons_geo.json               ONS Built-up Areas 2022 (OGL v3)
  /home/claude/hist/_data8/lsoa21_bua22_lookup.json   ONS LSOA 2021 to BUA 2022 best-fit lookup (OGL v3)
  /home/claude/hist/_data8/census/census2021-ts001-lsoa.csv   Census 2021 usual residents by LSOA (OGL v3)
  /home/claude/hist/_data8/ons_msoa_income_fye2023.xlsx       ONS small-area income estimates FYE 2023 (OGL v3)

Writes:
  data/domesday_entries.csv   one row per Domesday entry of the manor or urban kind (all counties),
                              with waste flag, waste reading from the text, values and hundred
  data/places.csv             one row per located Domesday place: waste, values 1066 and 1086, setting,
                              lost-village flag, today's built-up area, parish residents and income
"""
import csv
import glob
import json
import os
import re
from collections import defaultdict

import numpy as np
import openpyxl
import pandas as pd
import yaml
from pyproj import Transformer
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
HIST = "/home/claude/hist"
REF = os.path.join(HIST, "realm-domesday", "reference")
LV = os.path.join(HIST, "lost-villages", "data", "domesday_places_status.csv")
DD = os.path.join(HIST, "domesday-destiny", "data", "domesday_places.csv")
D8 = os.path.join(HIST, "_data8")
os.makedirs(DATA, exist_ok=True)
TO_BNG = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True).transform

# Hundreds of Domesday Cheshire that lie between the Ribble and the Mersey (south Lancashire)
RIBBLE_MERSEY = {"Blackburn", "Leyland", "Salford", "Warrington", "West Derby", "Newton"}
# Hundreds of Domesday Cheshire now in north-east Wales
CHS_WALES = {"Ati's Cross", "Bistre", "Rhuddlan", "Tegeingl", "Maelor Cymraeg", "Deeside"}


def region_of(county, hundred):
    if county == "YKS" and hundred == "Amounderness":
        return "Lancashire north of the Ribble"
    if county == "YKS":
        return "Yorkshire"
    if county == "CHS" and hundred in RIBBLE_MERSEY:
        return "Lancashire between Ribble and Mersey"
    if county == "CHS" and hundred in CHS_WALES:
        return "North-east Wales"
    return None


# ---------------- waste in the words of the text (counties with text; Yorkshire has none in the source)
R_NOW = re.compile(r"(?:\b(?:is|are|now|still)\s+(?:all\s+|wholly\s+|now\s+|still\s+)?waste|still is|was and is|is now waste|"
                   r"are now waste|it is waste|they are waste|waste now|lies waste|lie waste)", re.I)
R_PART = re.compile(r"partly waste|part(?: of it)? (?:is|was) waste|rest (?:is|are) waste|waste land", re.I)
R_WAS = re.compile(r"(?:was|were|been|found(?: it)?|found them)\s+(?:all\s+)?waste|found it so|waste when|"
                   r"waste before 1066", re.I)
R_PRE = re.compile(r"waste before 1066|waste in 1066|waste TRE", re.I)


def text_reading(t):
    if not t:
        return ""
    if not re.search(r"waste", t, re.I):
        return "no waste word"
    if R_NOW.search(t):
        return "waste now"
    if R_PART.search(t):
        return "partly waste"
    if R_PRE.search(t):
        return "waste before 1066"
    if R_WAS.search(t):
        return "was waste"
    return "other"


# ---------------- places
places = {}
for path in sorted(glob.glob(os.path.join(REF, "03-places-*.yml"))):
    for d in yaml.load(open(path, encoding="utf-8"), Loader=yaml.CSafeLoader) or []:
        p = d["data"]
        places[str(p["placeId"])] = p
print("places", len(places))

# ---------------- entries
erows = []
agg = defaultdict(lambda: defaultdict(float))
for path in sorted(glob.glob(os.path.join(REF, "05-entries-*.yml"))):
    for e in yaml.load(open(path, encoding="utf-8"), Loader=yaml.CSafeLoader) or []:
        d = e["data"]
        if d.get("kind") not in ("manor", "urban"):
            continue  # summaries, claims, fief headings, rubrics and indexes repeat or carry no holding
        rel = e.get("relations", [])
        desc = [str(r["to"]["placeId"]) for r in rel if r["predicate"] == "DESCRIBES"]
        incl = [str(r["to"]["placeId"]) for r in rel if r["predicate"] == "INCLUDES" and str(r["to"]["placeId"]) not in desc]
        hun = [r["to"]["hundredId"] for r in rel if r["predicate"] == "IN_HUNDRED"]
        waste = bool(d.get("isWaste"))
        v66 = d.get("value1066")
        v86 = d.get("value1086")
        vl = d.get("valueLater")
        # pairing rule: an entry with a 1066 value is paired with its 1086 value; a waste entry with no
        # 1086 value counts as worth nothing in 1086; other entries without a 1086 value are left out
        if v66 is not None and v86 is not None:
            pair = "both"
            p66, p86 = float(v66), float(v86)
        elif v66 is not None and waste:
            pair = "waste, no 1086 value"
            p66, p86 = float(v66), 0.0
        else:
            pair = ""
            p66 = p86 = None
        waste_1086 = waste and (v86 is None or float(v86) == 0)
        row = {
            "entryId": d["entryId"], "ref": d["ref"], "county": d["county"], "countyName": d["countyName"],
            "kind": d.get("kind"), "hundredId": hun[0] if hun else "", "n_places": len(desc),
            "placeIds": ";".join(desc), "n_included": len(incl), "includedPlaceIds": ";".join(incl), "isWaste": int(waste), "waste_no_value_1086": int(waste_1086),
            "text_reading": text_reading(d.get("text", "")) if waste else "",
            "has_text": int(bool(d.get("text"))),
            "value1066": v66 if v66 is not None else "", "valueLater": vl if vl is not None else "",
            "value1086": v86 if v86 is not None else "", "pair": pair,
            "pair1066": p66 if p66 is not None else "", "pair1086": p86 if p86 is not None else "",
            "ploughlands": d.get("ploughlands", ""), "ploughTeams": d.get("ploughTeams", ""),
            "households": d.get("households", ""), "geldUnits": d.get("geldUnits", ""),
        }
        erows.append(row)
        for pid in incl:
            a = agg[pid]
            a["incl"] += 1
            a["incl_waste"] += waste
            a["incl_waste1086"] += waste_1086
        k = len(desc)
        for pid in desc:
            a = agg[pid]
            a["entries"] += 1
            a["waste"] += waste
            a["waste1086"] += waste_1086
            a["waste_past"] += (waste and not waste_1086)
            if d.get("households") is not None:
                a["hh"] += float(d["households"]) / k
            if d.get("ploughlands") is not None:
                a["pl"] += float(d["ploughlands"]) / k
                a["n_pl"] += 1
            if p66 is not None:
                a["v66"] += p66 / k
                a["v86"] += p86 / k
                a["nv"] += 1
            if v66 is not None:
                a["v66_any"] += float(v66) / k
                a["n66"] += 1

with open(os.path.join(DATA, "domesday_entries.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(erows[0].keys()))
    w.writeheader()
    w.writerows(erows)
print("entries", len(erows))

# ---------------- place rows
York = places["73831"]
yx, yy = TO_BNG(York["lng"], York["lat"])
Chester = [p for p in places.values() if p.get("name") == "Chester" and p.get("county") == "CHS"][0]
cx, cy = TO_BNG(Chester["lng"], Chester["lat"])
prow = []
for pid, p in places.items():
    if p.get("lat") is None or pid not in agg:
        continue
    a = agg[pid]
    x, y = TO_BNG(p["lng"], p["lat"])
    if a["entries"] == 0 and a["incl"] == 0:
        continue
    prow.append({
        "placeId": pid, "name": p.get("name"), "county": p.get("county"), "countyName": p.get("countyName"),
        "hundred": p.get("hundred") or "", "region": region_of(p.get("county"), p.get("hundred")) or p.get("countyName"),
        "lat": p["lat"], "lng": p["lng"], "x": round(x), "y": round(y), "gridRef": p.get("gridRef") or "",
        "entries": int(a["entries"]), "included_in": int(a["incl"]),
        "included_waste": int(a["incl_waste"] > 0), "included_waste_1086": int(a["incl_waste1086"] > 0),
        "waste_broad": int(a["waste"] + a["incl_waste"] > 0), "waste_entries": int(a["waste"]), "any_waste": int(a["waste"] > 0),
        "waste_1086_entries": int(a["waste1086"]), "any_waste_1086": int(a["waste1086"] > 0),
        "waste_1086_broad": int(a["waste1086"] + a["incl_waste1086"] > 0),
        "all_waste_1086": int(a["entries"] > 0 and a["waste1086"] == a["entries"]),
        "waste_valued_entries": int(a["waste_past"]),
        "households1086": round(a["hh"], 2), "ploughlands": round(a["pl"], 2) if a["n_pl"] else "",
        "value1066_paired": round(a["v66"], 1) if a["nv"] else "",
        "value1086_paired": round(a["v86"], 1) if a["nv"] else "",
        "value1066_any": round(a["v66_any"], 1) if a["n66"] else "",
        "km_york": round(float(np.hypot(x - yx, y - yy)) / 1000, 2),
        "km_chester": round(float(np.hypot(x - cx, y - cy)) / 1000, 2),
        "ladName": p.get("ladName") or "", "lsoa21": p.get("lsoa21Code") or "",
        "parishName": p.get("parishName") or "", "modernPlaceName": p.get("modernPlaceName") or "",
        "likelyLost": int(bool(p.get("likelyLost"))), "openDomesdayPath": p.get("openDomesdayPath") or "",
    })
P = pd.DataFrame(prow)
print("located places with entries", len(P))

# ---------------- setting and lost-village flag (companion project)
lv = pd.read_csv(LV, dtype={"placeId": str})[["placeId", "elev_m", "relief_m", "river_m", "river_named_m", "roman_m", "lost_beresford"]]
P = P.merge(lv, on="placeId", how="left")
P["lost_beresford"] = P["lost_beresford"].fillna(False).astype(bool).astype(int)

# ---------------- parish residents 2021 (companion project)
dd = pd.read_csv(DD, dtype={"placeId": str})[["placeId", "parishResidents2021", "parishAreaHa", "parishDomesdayPlaces"]]
P = P.merge(dd, on="placeId", how="left")

# ---------------- Built-up Areas 2022
geo = json.load(open(os.path.join(D8, "ons_geo.json"), encoding="utf-8"))
bua = pd.DataFrame(geo["bua22_gb"])
bua = bua[bua.BUA22CD.str.startswith(("E", "W"))].reset_index(drop=True)
bua["r_eq"] = np.sqrt(bua.Shape__Area / np.pi)
lsoa_pop = {}
with open(os.path.join(D8, "census", "census2021-ts001-lsoa.csv"), encoding="utf-8") as f:
    rd = csv.reader(f)
    next(rd)
    lsoa_name = {}
    for r in rd:
        lsoa_pop[r[2]] = int(r[3])
        lsoa_name[r[2]] = r[1]
lk = json.load(open(os.path.join(D8, "lsoa21_bua22_lookup.json"), encoding="utf-8"))
bpop = defaultdict(int)
for r in lk:
    if r["BUA22CD"] and r["LSOA21CD"] in lsoa_pop:
        bpop[r["BUA22CD"]] += lsoa_pop[r["LSOA21CD"]]
bua["pop_lsoa"] = bua.BUA22CD.map(bpop).fillna(0).astype(int)
tree = cKDTree(np.c_[bua.BNG_E, bua.BNG_N])
SLACK = 1000.0  # metres: Domesday points sit at the centre of a 1 km grid square
cand = tree.query_ball_point(np.c_[P.x, P.y], r=float(bua.r_eq.max() + SLACK))
m_code, m_name, m_area, m_pop, m_d = [], [], [], [], []
for i, idx in enumerate(cand):
    best, bs = None, None
    for j in idx:
        dist = float(np.hypot(P.x[i] - bua.BNG_E[j], P.y[i] - bua.BNG_N[j]))
        s = dist - bua.r_eq[j]
        if s <= SLACK and (bs is None or s < bs):
            best, bs = j, s
    if best is None:
        m_code.append(""); m_name.append(""); m_area.append(np.nan); m_pop.append(np.nan); m_d.append(np.nan)
    else:
        m_code.append(bua.BUA22CD[best]); m_name.append(bua.BUA22NM[best])
        m_area.append(round(bua.Shape__Area[best] / 1e4, 1))
        m_pop.append(bua.pop_lsoa[best] if bua.pop_lsoa[best] > 0 else np.nan)
        m_d.append(round(float(np.hypot(P.x[i] - bua.BNG_E[best], P.y[i] - bua.BNG_N[best])) / 1000, 2))
P["bua22cd"] = m_code
P["bua22nm"] = m_name
P["bua_area_ha"] = m_area
P["bua_pop_lsoa"] = m_pop
P["bua_centroid_km"] = m_d
P["in_bua"] = (P.bua22cd != "").astype(int)

# ---------------- income: the place's LSOA -> its MSOA (LSOA names are the MSOA name plus a letter)
wb = openpyxl.load_workbook(os.path.join(D8, "ons_msoa_income_fye2023.xlsx"), read_only=True)
inc = {}
for i, r in enumerate(wb["Total annual income"].iter_rows(values_only=True)):
    if i >= 4 and r[0] and isinstance(r[6], (int, float)):
        inc[r[1]] = (r[0], r[6])
mso, mval = [], []
for c in P.lsoa21:
    nm = lsoa_name.get(c, "")
    key = nm[:-1] if nm else ""
    if key in inc:
        mso.append(inc[key][0]); mval.append(inc[key][1])
    else:
        mso.append(""); mval.append(np.nan)
P["msoa21"] = mso
P["msoa_income_total"] = mval
P.to_csv(os.path.join(DATA, "places.csv"), index=False)
print("places.csv", len(P), "in BUA", int(P.in_bua.sum()), "with income", int(P.msoa_income_total.notna().sum()),
      "with parish pop", int(P.parishResidents2021.notna().sum()))
print(P.groupby("region").agg(n=("placeId", "size"), direct=("entries", lambda v: (v > 0).sum()), waste=("any_waste", "mean"), broad=("waste_broad", "mean")).sort_values("waste").tail(12))
