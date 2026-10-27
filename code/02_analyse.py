"""Step 2. Analyse waste, value, setting and the long shadow; write results.json and the page data.

Usage:
    python3 code/02_analyse.py

Reads data/places.csv and data/domesday_entries.csv (step 1).
Writes:
  data/results.json          every number used on the page, in the README, paper, blog and collage
  data/county_waste.csv      waste and value by Domesday county (with Lancashire and north-east Wales split out)
  data/hundred_waste.csv     waste and value by hundred or wapentake, in the northern and midland study counties
  data/hexes.geojson         hexagons (8 km centre to corner): places, waste share, value 1086 against 1066
  data/geography_bands.csv   Yorkshire waste share by distance to York, height and distance to a Roman road
  data/long_shadow.csv       waste against today's outcomes: estimates with confidence intervals
  data/lancashire_places.csv Domesday places in Lancashire and the Ribble valley, with their status
  _work/site.json            compact data embedded in the page (temporary)
"""
import json
import os
import re

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pyproj import Transformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WORK = os.path.join(ROOT, "_work")
os.makedirs(WORK, exist_ok=True)
TO_WGS = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True).transform

P = pd.read_csv(os.path.join(DATA, "places.csv"), dtype={"placeId": str})
E = pd.read_csv(os.path.join(DATA, "domesday_entries.csv"), dtype={"entryId": str})
R = {}
STUDY = ["YKS", "CHS", "DBY", "NTT", "STS", "SHR"]   # the northern and north midland counties of the long-shadow test
NORTH_MAP = ["YKS", "CHS", "DBY", "NTT", "STS", "SHR", "LIN", "LEC", "HEF", "WOR", "WAR", "NTH", "RUT"]


def clean_hundred(h):
    if not isinstance(h, str):
        return ""
    m = re.search(r"\[([^\]]+)\]", h)
    if m:
        return m.group(1)
    h = h.strip("{}`'")
    return {"Land of Count Alan": "Land of Count Alan (Richmondshire)", "Amounderness": "Amounderness, Lonsdale and Furness"}.get(h, h)


def share(s):
    return float(np.mean(s)) if len(s) else None


# Entry region (for value sums): from the entry's hundred
E["hundred"] = E.hundredId.fillna("").str.split(":").str[1].fillna("")
RM = {"Blackburn", "Leyland", "Salford", "Warrington", "West Derby", "Newton"}
WALES = {"Ati's Cross", "Bistre", "Rhuddlan", "Tegeingl", "Maelor Cymraeg", "Deeside"}


def eregion(r):
    if r.county == "YKS":
        return "Lancashire north of the Ribble" if r.hundred == "Amounderness" else "Yorkshire"
    if r.county == "CHS":
        return "Lancashire between Ribble and Mersey" if r.hundred in RM else "North-east Wales" if r.hundred in WALES else "Cheshire"
    return r.countyName


E["region"] = E.apply(eregion, axis=1)
EP = E[E.pair != ""].copy()
EP = EP[EP.pair.notna()]

# ---------------- 1. headline counts
R["n_entries"] = int(len(E))
R["n_places"] = int(len(P))
R["n_places_direct"] = int((P.entries > 0).sum())
R["n_waste_entries"] = int(E.isWaste.sum())
R["n_waste_entries_yks"] = int(E[E.county == "YKS"].isWaste.sum())
R["n_waste_entries_study"] = int(E[E.county.isin(STUDY)].isWaste.sum())
R["share_waste_entries_in_study"] = R["n_waste_entries_study"] / R["n_waste_entries"]
R["share_waste_entries_in_yks"] = R["n_waste_entries_yks"] / R["n_waste_entries"]
R["n_counties_with_waste"] = int(E[E.isWaste == 1].county.nunique())

# ---------------- 2. county / region table
rows = []
for reg, g in P.groupby("region"):
    d = g[g.entries > 0]
    ep = EP[EP.region == reg]
    v66, v86 = ep.pair1066.astype(float).sum(), ep.pair1086.astype(float).sum()
    both = ep[ep.pair == "both"]
    ew = E[(E.region == reg) & (E.isWaste == 1)]
    rows.append({
        "region": reg, "county": g.county.iloc[0], "places": len(g), "places_direct": len(d),
        "waste_direct": share(d.any_waste), "waste_broad": share(g.waste_broad),
        "waste_1086_direct": share(d.any_waste_1086),
        "waste_entries": len(ew), "waste_entries_no_1086_value": int(ew.waste_no_value_1086.sum()),
        "paired_entries": len(ep), "value1066": v66, "value1086": v86,
        "value_ratio": v86 / v66 if v66 > 0 else None,
        "value_ratio_both_only": both.pair1086.astype(float).sum() / both.pair1066.astype(float).sum() if len(both) and both.pair1066.astype(float).sum() > 0 else None,
    })
CT = pd.DataFrame(rows).sort_values("waste_direct", ascending=False)
CT.loc[CT.region == "Lancashire between Ribble and Mersey", ["value_ratio", "value_ratio_both_only"]] = None  # values not comparable
CT.to_csv(os.path.join(DATA, "county_waste.csv"), index=False, float_format="%.4f")
R["regions"] = {r["region"]: {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()} for r in CT.to_dict("records")}
big = CT[CT.places_direct >= 150].reset_index(drop=True)
R["county_rank"] = [{"region": r.region, "waste": r.waste_direct, "ratio": r.value_ratio} for r in big.itertuples()]
rest = P[(~P.county.isin(STUDY + ["HEF"])) & (P.entries > 0)]
R["rest_waste_direct"] = share(rest.any_waste)
ep_rest = EP[~EP.county.isin(STUDY + ["HEF"])]
R["rest_value_ratio"] = ep_rest.pair1086.astype(float).sum() / ep_rest.pair1066.astype(float).sum()
Y = R["regions"]["Yorkshire"]
R["yks"] = Y

# Yorkshire value pairing details
ey = E[(E.region == "Yorkshire")]
R["yks_entries"] = int(len(ey))
R["yks_entries_waste"] = int(ey.isWaste.sum())
R["yks_waste_no_value_1086"] = int(ey.waste_no_value_1086.sum())
R["yks_waste_no_value_share"] = R["yks_waste_no_value_1086"] / R["yks_entries_waste"]
R["yks_pairs_imputed"] = int((ey.pair == "waste, no 1086 value").sum())
R["yks_pairs_both"] = int((ey.pair == "both").sum())
R["yks_v66_no_v86_not_waste"] = int(((ey.value1066.notna()) & (ey.value1086.isna()) & (ey.isWaste == 0)).sum())

# Yorkshire without the city of York (urban entries)
eyr = EP[(EP.region == "Yorkshire") & (EP.kind != "urban")]
R["yks_rural_value_ratio"] = eyr.pair1086.astype(float).sum() / eyr.pair1066.astype(float).sum()
R["yks_rural_value1066"] = eyr.pair1066.astype(float).sum()
R["yks_rural_value1086"] = eyr.pair1086.astype(float).sum()
eyu = EP[(EP.region == "Yorkshire") & (EP.kind == "urban")]
R["york_city_value_ratio"] = eyu.pair1086.astype(float).sum() / eyu.pair1066.astype(float).sum()

# ---------------- 3. what the word means: the text, where the source has it
tx = E[(E.isWaste == 1) & (E.has_text == 1)]
tr = {}
for c in ["CHS", "SHR", "HEF", "DBY", "NTT", "STS", "LIN", "LEC"]:
    t = tx[tx.county == c]
    vc = t.text_reading.value_counts()
    tr[c] = {"n": int(len(t)), "now": int(vc.get("waste now", 0)), "was": int(vc.get("was waste", 0)),
             "pre": int(vc.get("waste before 1066", 0)), "part": int(vc.get("partly waste", 0)),
             "other": int(vc.get("other", 0) + vc.get("no waste word", 0)),
             "no_value_1086": int(t.waste_no_value_1086.sum())}
    tr[c]["was_share"] = tr[c]["was"] / tr[c]["n"] if tr[c]["n"] else None
    tr[c]["now_share"] = tr[c]["now"] / tr[c]["n"] if tr[c]["n"] else None
R["text_reading"] = tr
mid = tx[tx.county.isin(["DBY", "NTT", "STS"])]
R["mid_now_share"] = float((mid.text_reading == "waste now").mean())
R["mid_n"] = int(len(mid))
cs = tx[tx.county.isin(["CHS", "SHR"])]
R["chs_shr_n"] = int(len(cs))
R["chs_shr_was_share"] = float(cs.text_reading.isin(["was waste", "waste before 1066"]).mean())
R["chs_shr_now_share"] = float((cs.text_reading == "waste now").mean())
# agreement between the value rule and the text: waste entries with no 1086 value whose text says waste now
nv = tx[tx.waste_no_value_1086 == 1]
R["novalue_text_now_share"] = float((nv.text_reading == "waste now").mean())
R["novalue_text_n"] = int(len(nv))
wv = tx[tx.waste_no_value_1086 == 0]
R["valued_text_was_share"] = float(wv.text_reading.isin(["was waste", "waste before 1066", "partly waste"]).mean())
R["valued_text_n"] = int(len(wv))

# ---------------- 4. hundreds and wapentakes
hrows = []
PS = P[P.county.isin(NORTH_MAP)]
for (cty, hun), g in PS.groupby(["county", "hundred"]):
    d = g[g.entries > 0]
    ep = EP[(EP.county == cty) & (EP.hundred == hun)]
    v66, v86 = ep.pair1066.astype(float).sum(), ep.pair1086.astype(float).sum()
    hrows.append({"county": cty, "countyName": g.countyName.iloc[0], "region": g.region.iloc[0], "hundred_source": hun,
                  "hundred": clean_hundred(hun), "places": len(g), "places_direct": len(d),
                  "waste_direct": share(d.any_waste) if len(d) else None, "waste_broad": share(g.waste_broad),
                  "paired_entries": len(ep), "value1066": v66, "value1086": v86,
                  "value_ratio": v86 / v66 if v66 > 0 and len(ep) >= 5 and hun not in RM else None,
                  "lat": g.lat.mean(), "lng": g.lng.mean(), "km_york": g.km_york.median()})
HT = pd.DataFrame(hrows).sort_values(["county", "hundred"])
HT.to_csv(os.path.join(DATA, "hundred_waste.csv"), index=False, float_format="%.4f")
hy = HT[(HT.county == "YKS") & (HT.places_direct >= 15)].sort_values("waste_broad", ascending=False)
R["yks_hundreds_n"] = int(len(hy))
R["yks_hundred_top"] = hy.head(5)[["hundred", "places", "waste_broad", "waste_direct", "value_ratio"]].to_dict("records")
R["yks_hundred_bottom"] = hy.tail(3)[["hundred", "places", "waste_broad", "waste_direct", "value_ratio"]].to_dict("records")
hv = HT[(HT.county == "YKS") & HT.value_ratio.notna() & (HT.places_direct >= 15)].sort_values("value_ratio")
R["yks_hundred_low_value"] = hv.head(3)[["hundred", "value_ratio", "value1066", "value1086"]].to_dict("records")
R["yks_hundred_high_value"] = hv.tail(3)[["hundred", "value_ratio", "value1066", "value1086"]].to_dict("records")
R["yks_hundred_ratio_range"] = [float(hv.value_ratio.min()), float(hv.value_ratio.max())]

# ---------------- 5. hexagons (pointy-top, 8 km centre to corner) in British National Grid
S = 8000.0


def hex_of(x, y):
    q = (np.sqrt(3) / 3 * x - y / 3) / S
    r = (2 / 3 * y) / S
    xq, zq = q, r
    yq = -xq - zq
    rx, ry, rz = np.round(xq), np.round(yq), np.round(zq)
    dx, dy, dz = np.abs(rx - xq), np.abs(ry - yq), np.abs(rz - zq)
    m1 = (dx > dy) & (dx > dz)
    rx[m1] = -ry[m1] - rz[m1]
    m2 = ~m1 & (dy > dz)
    ry[m2] = -rx[m2] - rz[m2]
    m3 = ~m1 & ~m2
    rz[m3] = -rx[m3] - ry[m3]
    return rx.astype(int), rz.astype(int)


P["hq"], P["hr"] = hex_of(P.x.values.astype(float), P.y.values.astype(float))
# values per place for the hex sums (direct places only)
pv = P.copy()
pv["v66"] = pd.to_numeric(pv.value1066_paired, errors="coerce")
pv["v86"] = pd.to_numeric(pv.value1086_paired, errors="coerce")
pv.loc[pv.region == "Lancashire between Ribble and Mersey", ["v66", "v86"]] = np.nan
feats, hexrows = [], []
for (q, r), g in pv.groupby(["hq", "hr"]):
    cx = S * np.sqrt(3) * (q + r / 2)
    cy = S * 1.5 * r
    v66, v86 = g.v66.sum(), g.v86.sum()
    d = g[g.entries > 0]
    rec = {"q": int(q), "r": int(r), "x": round(cx), "y": round(cy), "n": int(len(g)), "n_direct": int(len(d)),
           "waste_broad": int(g.waste_broad.sum()), "waste_direct": int(d.any_waste.sum()),
           "v66": round(float(v66)), "v86": round(float(v86)),
           "ratio": round(float(v86 / v66), 3) if v66 > 0 else None,
           "county": g.county.mode().iloc[0]}
    hexrows.append(rec)
    ring = []
    for i in range(7):
        a = np.radians(60 * (i % 6) + 30)
        lo, la = TO_WGS(cx + S * np.cos(a), cy + S * np.sin(a))
        ring.append([round(lo, 4), round(la, 4)])
    feats.append({"type": "Feature", "properties": {k: rec[k] for k in ["n", "n_direct", "waste_broad", "waste_direct", "v66", "v86", "ratio", "county"]},
                  "geometry": {"type": "Polygon", "coordinates": [ring]}})
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(DATA, "hexes.geojson"), "w"), separators=(",", ":"))
HX = pd.DataFrame(hexrows)
hn = HX[HX.n >= 5].copy()
hn["share"] = hn.waste_broad / hn.n
R["hex_size_km"] = S / 1000
R["hex_n"] = int(len(HX))
R["hex_n5"] = int(len(hn))
R["hex_over_half"] = int((hn.share >= 0.5).sum())
R["hex_over_half_yks_chs"] = int((hn[hn.share >= 0.5].county.isin(["YKS", "CHS"])).sum())
R["hex_all_waste"] = int((hn.share == 1).sum())

# ---------------- 6. geography of destruction, Yorkshire (places with their own entries)
Yd = P[(P.region == "Yorkshire") & (P.entries > 0) & (P.placeId != "73831")].copy()   # the city of York itself left out
Yb = P[(P.region == "Yorkshire") & (P.placeId != "73831")].copy()
for T in (Yd, Yb):
    T["roman_km"] = T.roman_m / 1000
    T["river_km"] = T.river_named_m / 1000
R["geo_n_direct"] = int(len(Yd))
R["geo_n_broad"] = int(len(Yb))


def bands(T, col, edges, labels, ycol):
    out = []
    cut = pd.cut(T[col], edges, labels=labels, right=False)
    for lab in labels:
        g = T[cut == lab]
        out.append({"band": lab, "n": int(len(g)), "waste": share(g[ycol]) if len(g) else None})
    return out


GB = {}
GB["york"] = bands(Yd, "km_york", [0, 15, 30, 45, 60, 80, 999], ["0 to 15", "15 to 30", "30 to 45", "45 to 60", "60 to 80", "80+"], "any_waste")
GB["elev"] = bands(Yd, "elev_m", [-50, 25, 50, 100, 200, 9999], ["under 25", "25 to 50", "50 to 100", "100 to 200", "200+"], "any_waste")
GB["roman"] = bands(Yd, "roman_km", [0, 2, 5, 10, 999], ["under 2", "2 to 5", "5 to 10", "10+"], "any_waste")
GB["river"] = bands(Yd, "river_km", [0, 0.5, 1, 2, 999], ["under 0.5", "0.5 to 1", "1 to 2", "2+"], "any_waste")
GB["york_broad"] = bands(Yb, "km_york", [0, 15, 30, 45, 60, 80, 999], ["0 to 15", "15 to 30", "30 to 45", "45 to 60", "60 to 80", "80+"], "waste_broad")
GB["elev_broad"] = bands(Yb, "elev_m", [-50, 25, 50, 100, 200, 9999], ["under 25", "25 to 50", "50 to 100", "100 to 200", "200+"], "waste_broad")
R["geo_bands"] = GB
rows = []
for k, v in GB.items():
    for b in v:
        rows.append({"measure": k, **b})
pd.DataFrame(rows).to_csv(os.path.join(DATA, "geography_bands.csv"), index=False, float_format="%.4f")
# value by distance band (entries paired, Yorkshire, by the described place's distance)
Yv = Yd.copy()
Yv["v66"] = pd.to_numeric(Yv.value1066_paired, errors="coerce")
Yv["v86"] = pd.to_numeric(Yv.value1086_paired, errors="coerce")
vb = []
for lab, g in Yv.groupby(pd.cut(Yv.km_york, [0, 15, 30, 45, 60, 80, 999], labels=["0 to 15", "15 to 30", "30 to 45", "45 to 60", "60 to 80", "80+"], right=False), observed=False):
    vb.append({"band": str(lab), "ratio": float(g.v86.sum() / g.v66.sum()) if g.v66.sum() > 0 else None, "n": int(g.v66.notna().sum())})
R["geo_value_york"] = vb
# medians, waste against not
med = {}
for col in ["km_york", "elev_m", "relief_m", "roman_km", "river_km"]:
    med[col] = {"waste": float(Yd[Yd.any_waste == 1][col].median()), "not": float(Yd[Yd.any_waste == 0][col].median())}
R["geo_medians"] = med
# logistic model
Yd["york10"] = Yd.km_york / 10
Yd["elev100"] = Yd.elev_m / 100
Yd["relief50"] = Yd.relief_m / 50
Yd["roman5"] = Yd.roman_km / 5
Yd["lowland"] = (Yd.elev_m < 50).astype(int)
m = smf.logit("any_waste ~ york10 + elev100 + relief50 + roman5 + river_km", data=Yd).fit(disp=0)
lg = {}
for k in ["york10", "elev100", "relief50", "roman5", "river_km"]:
    lo, hi = m.conf_int().loc[k]
    lg[k] = {"or": float(np.exp(m.params[k])), "lo": float(np.exp(lo)), "hi": float(np.exp(hi)), "p": float(m.pvalues[k])}
R["geo_logit"] = lg
R["geo_logit_n"] = int(m.nobs)
R["geo_logit_pseudo_r2"] = float(m.prsquared)
# same with the broad measure
Yb["york10"] = Yb.km_york / 10
Yb["elev100"] = Yb.elev_m / 100
Yb["relief50"] = Yb.relief_m / 50
Yb["roman5"] = Yb.roman_km / 5
mb = smf.logit("waste_broad ~ york10 + elev100 + relief50 + roman5 + river_km", data=Yb).fit(disp=0)
R["geo_logit_broad"] = {k: {"or": float(np.exp(mb.params[k])), "p": float(mb.pvalues[k])} for k in ["york10", "elev100", "relief50", "roman5", "river_km"]}
# uplands: share of waste places above 150 m, and of all places
R["yks_share_places_above150"] = share(Yd.elev_m >= 150)
R["yks_share_waste_above150"] = share(Yd[Yd.any_waste == 1].elev_m >= 150)
R["yks_waste_above150"] = share(Yd[Yd.elev_m >= 150].any_waste)
R["yks_waste_below50"] = share(Yd[Yd.elev_m < 50].any_waste)
R["yks_waste_near_york"] = share(Yd[Yd.km_york < 15].any_waste)
R["yks_waste_far_york"] = share(Yd[Yd.km_york >= 60].any_waste)
# Cheshire: distance from Chester
Cd = P[(P.region == "Cheshire") & (P.entries > 0)]
R["chs_bands"] = bands(Cd, "km_chester", [0, 10, 20, 30, 999], ["0 to 10", "10 to 20", "20 to 30", "30+"], "any_waste")
Cd2 = Cd.copy()
Cd2["chester10"] = Cd2.km_chester / 10
Cd2["elev100"] = Cd2.elev_m / 100
mc = smf.logit("any_waste ~ chester10 + elev100", data=Cd2).fit(disp=0)
R["chs_logit"] = {k: {"or": float(np.exp(mc.params[k])), "p": float(mc.pvalues[k])} for k in ["chester10", "elev100"]}
# Across the north and midlands: waste share by distance from York
NM = P[P.county.isin(["YKS", "CHS", "DBY", "NTT", "STS", "SHR", "LIN", "LEC"]) & (P.entries > 0)]
dist_b = []
for lab, g in NM.groupby(pd.cut(NM.km_york, [0, 25, 50, 75, 100, 125, 150, 200, 999], labels=["0 to 25", "25 to 50", "50 to 75", "75 to 100", "100 to 125", "125 to 150", "150 to 200", "200+"], right=False), observed=False):
    dist_b.append({"band": str(lab), "n": int(len(g)), "waste": share(g.any_waste)})
R["north_dist_bands"] = dist_b

# ---------------- 7. the long shadow
LS = P[P.county.isin(STUDY) & (P.entries > 0)].copy()
LS["v66"] = pd.to_numeric(LS.value1066_paired, errors="coerce")
LS = LS[(LS.v66 > 0) & (LS.region != "Lancashire between Ribble and Mersey")]
LS["treat"] = np.where(LS.any_waste_1086 == 1, 1, np.where(LS.any_waste == 0, 0, -1))
R["ls_dropped_valued_waste"] = int((LS.treat == -1).sum())
LS = LS[LS.treat >= 0].copy()
LS["tercile"] = LS.groupby("region").v66.transform(lambda s: pd.qcut(s.rank(method="first"), 3, labels=False))
LS["stratum"] = LS.region + ":" + LS.tercile.astype(str)
LS["lv66"] = np.log(LS.v66)
LS["l_area"] = np.log(LS.bua_area_ha)
LS["l_par"] = np.log(LS.parishResidents2021)
LS["l_inc"] = np.log(LS.msoa_income_total)
R["ls_n"] = int(len(LS))
R["ls_n_waste"] = int(LS.treat.sum())
R["ls_n_not"] = int((LS.treat == 0).sum())
outs = [("in_bua", "Lies in a built-up area today", "pp"), ("l_area", "Size of that built-up area", "pct"),
        ("l_par", "Parish residents, 2021", "pct"), ("l_inc", "Household income of the area, 2023", "pct"),
        ("lost_beresford", "Became a deserted village", "pp")]
lsr = []
for col, lab, kind in outs:
    d = LS[LS[col].notna() & np.isfinite(LS[col])]
    f = smf.ols(f"{col} ~ treat + lv66 + C(stratum)", data=d).fit(cov_type="HC1")
    b, (lo, hi), p = f.params["treat"], f.conf_int().loc["treat"], f.pvalues["treat"]
    if kind == "pct":
        est, lo_, hi_ = np.exp(b) - 1, np.exp(lo) - 1, np.exp(hi) - 1
    else:
        est, lo_, hi_ = b, lo, hi
    raw_w = d[d.treat == 1][col]
    raw_n = d[d.treat == 0][col]
    lsr.append({"outcome": col, "label": lab, "kind": kind, "n": int(len(d)), "n_waste": int(d.treat.sum()),
                "est": float(est), "lo": float(lo_), "hi": float(hi_), "p": float(p),
                "raw_waste": float(np.exp(raw_w.median()) if kind == "pct" else raw_w.mean()),
                "raw_not": float(np.exp(raw_n.median()) if kind == "pct" else raw_n.mean())})
R["ls"] = {r["outcome"]: r for r in lsr}
# where do the built-up waste places sit? the biggest built-up areas holding a wasted place
bw = LS[(LS.treat == 1) & (LS.in_bua == 1)]
R["ls_waste_bua_top"] = bw.groupby("bua22nm").agg(n=("placeId", "size"), area=("bua_area_ha", "first")).sort_values("area", ascending=False).head(6).reset_index().to_dict("records")
R["ls_waste_bua_over1000ha"] = share(bw.bua_area_ha >= 1000)
bn = LS[(LS.treat == 0) & (LS.in_bua == 1)]
R["ls_not_bua_over1000ha"] = share(bn.bua_area_ha >= 1000)
WR = {"Agbrigg", "Morley", "Skyrack", "Staincross", "Strafforth", "Osgoldcross", "Barkston Ash"}
R["ls_waste_bua_westriding_share"] = share(bw.hundred.isin(WR))
R["ls_not_bua_westriding_share"] = share(bn.hundred.isin(WR))
pd.DataFrame(lsr).to_csv(os.path.join(DATA, "long_shadow.csv"), index=False, float_format="%.5f")
# Yorkshire only
LY = LS[LS.region == "Yorkshire"]
R["ls_yks"] = {}
for col, lab, kind in outs:
    d = LY[LY[col].notna() & np.isfinite(LY[col])]
    f = smf.ols(f"{col} ~ treat + lv66 + C(stratum)", data=d).fit(cov_type="HC1")
    b, (lo, hi), p = f.params["treat"], f.conf_int().loc["treat"], f.pvalues["treat"]
    if kind == "pct":
        b, lo, hi = np.exp(b) - 1, np.exp(lo) - 1, np.exp(hi) - 1
    R["ls_yks"][col] = {"est": float(b), "lo": float(lo), "hi": float(hi), "p": float(p), "n": int(len(d)), "n_waste": int(d.treat.sum())}
# broad comparison: any waste flag (including valued and member vills) against none, region strata only, all places
LB = P[P.county.isin(STUDY) & (P.region != "Lancashire between Ribble and Mersey")].copy()
LB["l_area"] = np.log(LB.bua_area_ha)
LB["l_inc"] = np.log(LB.msoa_income_total)
R["ls_broad"] = {}
for col in ["in_bua", "l_area", "l_inc", "lost_beresford"]:
    d = LB[LB[col].notna() & np.isfinite(LB[col])]
    f = smf.ols(f"{col} ~ waste_broad + C(region)", data=d).fit(cov_type="HC1")
    b, (lo, hi), p = f.params["waste_broad"], f.conf_int().loc["waste_broad"], f.pvalues["waste_broad"]
    if col.startswith("l_"):
        b, lo, hi = np.exp(b) - 1, np.exp(lo) - 1, np.exp(hi) - 1
    R["ls_broad"][col] = {"est": float(b), "lo": float(lo), "hi": float(hi), "p": float(p), "n": int(len(d))}
R["ls_broad_n"] = int(len(LB))

# lost villages
yb = P[P.region == "Yorkshire"]
R["lost_yks_waste"] = share(yb[yb.waste_broad == 1].lost_beresford)
R["lost_yks_not"] = share(yb[yb.waste_broad == 0].lost_beresford)
R["lost_yks_waste_n"] = int(yb[yb.waste_broad == 1].lost_beresford.sum())
R["lost_yks_not_n"] = int(yb[yb.waste_broad == 0].lost_beresford.sum())
st = P[P.county.isin(STUDY)]
R["lost_study_waste_n"] = int(st[st.waste_broad == 1].lost_beresford.sum())
R["lost_study_waste_share"] = share(st[st.waste_broad == 1].lost_beresford)
R["lost_study_not_share"] = share(st[st.waste_broad == 0].lost_beresford)
R["lost_study_n_waste_places"] = int(st.waste_broad.sum())
R["lost_all_n"] = int(P.lost_beresford.sum())
R["lost_all_waste_n"] = int(P[P.waste_broad == 1].lost_beresford.sum())
# today in a BUA: raw shares
R["bua_share_waste_yks"] = share(yb[yb.waste_broad == 1].in_bua)
R["bua_share_not_yks"] = share(yb[yb.waste_broad == 0].in_bua)
R["bua_match_share_all"] = share(P.in_bua)
R["bua_with_pop_share"] = share(P[P.in_bua == 1].bua_pop_lsoa.notna())

# ---------------- 8. Lancashire and the Ribble valley
LA = P[P.region.str.startswith("Lancashire") | P.ladName.isin(["Ribble Valley"])].copy()
LA["area"] = np.where(LA.region == "Lancashire north of the Ribble", "North of the Ribble (Domesday Yorkshire)",
                      np.where(LA.region == "Lancashire between Ribble and Mersey", "Between Ribble and Mersey (Domesday Cheshire)",
                               "Ribble valley in Craven (Domesday Yorkshire)"))
LA[["placeId", "name", "area", "region", "hundred", "ladName", "lat", "lng", "entries", "included_in", "any_waste", "waste_broad",
    "value1066_any", "value1086_paired", "bua22nm", "bua_area_ha", "msoa_income_total", "lost_beresford", "openDomesdayPath"]].sort_values(["area", "name"]).to_csv(
    os.path.join(DATA, "lancashire_places.csv"), index=False)
ln = P[P.region == "Lancashire north of the Ribble"]
R["lan_n_places"] = int(len(ln))
R["lan_n_direct"] = int((ln.entries > 0).sum())
R["lan_waste_broad"] = share(ln.waste_broad)
R["lan_waste_broad_n"] = int(ln.waste_broad.sum())
pre = E[E.ref == "Yorkshire 1L1"].iloc[0]
R["preston_included"] = int(pre.n_included)
R["preston_vills"] = int(pre.n_included) + 1   # Preston itself and its member vills
R["preston_located"] = int(P.placeId.isin([str(pre.placeIds)] + str(pre.includedPlaceIds).split(";")).sum())
R["preston_is_waste"] = int(pre.isWaste)
lw = E[E.region == "Lancashire north of the Ribble"]
R["lan_entries"] = int(len(lw))
R["lan_entries_waste"] = int(lw.isWaste.sum())
rm = P[P.region == "Lancashire between Ribble and Mersey"]
R["rm_n_places"] = int(len(rm))
R["rm_waste_n"] = int(rm.waste_broad.sum())
erm = E[E.region == "Lancashire between Ribble and Mersey"]
R["rm_entries"] = int(len(erm))
R["rm_entries_waste"] = int(erm.isWaste.sum())
R["rm_entries_v66"] = int(erm.value1066.notna().sum())
rv = P[P.ladName == "Ribble Valley"]
R["rv_n"] = int(len(rv))
R["rv_waste_broad_n"] = int(rv.waste_broad.sum())
R["rv_in_bua"] = int(rv.in_bua.sum())
R["rv_by_hundred"] = rv.groupby("hundred").agg(n=("placeId", "size"), waste=("waste_broad", "sum")).reset_index().to_dict("records")
R["rv_names_waste"] = sorted(rv[rv.waste_broad == 1].name.tolist())
R["rv_names_not"] = sorted(rv[rv.waste_broad == 0].name.tolist())
# within 15 km of Clitheroe (OS Open Names, Town, 374624 442152)
CLX, CLY = 374624, 442152
P["km_clitheroe"] = np.hypot(P.x - CLX, P.y - CLY) / 1000
cl = P[P.km_clitheroe <= 15]
R["cli_n"] = int(len(cl))
R["cli_waste_broad_n"] = int(cl.waste_broad.sum())
R["cli_direct_n"] = int((cl.entries > 0).sum())
R["cli_in_bua"] = int(cl.in_bua.sum())
R["cli_named_in_data"] = int((P.name == "Clitheroe").sum())
for hn, key in (("Craven", "craven"), ("Amounderness", "amd"), ("Blackburn", "blackburn")):
    g = cl[cl.hundred == hn]
    R[f"cli_{key}_n"] = int(len(g))
    R[f"cli_{key}_waste"] = int(g.waste_broad.sum())
cr = P[(P.hundred == "Craven")]
R["craven_n"] = int(len(cr))
R["craven_waste_broad"] = share(cr.waste_broad)

# ---------------- 9. site data
site = {}
MP = P[P.county.isin(NORTH_MAP)].copy()
MP = MP[MP.lat >= 52.0]
reg_names = sorted(MP.region.unique())
site["regions"] = reg_names


def num(v, nd=0):
    return None if pd.isna(v) else (round(float(v), nd) if nd else int(round(float(v))))


pts = []
for r in MP.itertuples():
    # status: 3 waste in 1086 (no value), 2 waste flag but valued in 1086 (past or partial), 1 member of a waste entry only, 0 none
    st_ = 3 if r.any_waste_1086 else 2 if r.any_waste else 1 if r.included_waste else 0
    v66 = num(pd.to_numeric(r.value1066_paired, errors="coerce"))
    v86 = num(pd.to_numeric(r.value1086_paired, errors="coerce"))
    if r.region == "Lancashire between Ribble and Mersey":
        v66 = v86 = None
    pts.append([round(r.lat, 4), round(r.lng, 4), r.name, reg_names.index(r.region), st_, v66, v86,
                num(r.bua_area_ha), r.bua22nm if isinstance(r.bua22nm, str) else "", int(r.lost_beresford),
                r.openDomesdayPath if isinstance(r.openDomesdayPath, str) else "", clean_hundred(r.hundred),
                num(r.elev_m), num(r.msoa_income_total)])
site["p"] = pts
site["hex"] = [f for f in feats if f["properties"]["county"] in NORTH_MAP]
site["county"] = [[r["region"], r["places_direct"], r["waste_direct"], r["waste_broad"], r["value_ratio"]] for r in CT[CT.places_direct >= 60].to_dict("records")]
site["hund"] = [[r["hundred"], r["county"], r["places"], r["waste_broad"], r["waste_direct"], r["value_ratio"], round(r["lat"], 3), round(r["lng"], 3)]
                for r in HT[(HT.county == "YKS") & (HT.places_direct >= 15)].sort_values("waste_broad", ascending=False).to_dict("records")]
site["york"] = [float(P[P.placeId == "73831"].lat.iloc[0]), float(P[P.placeId == "73831"].lng.iloc[0])]
site["ls"] = lsr
site["geo"] = GB
site["distn"] = dist_b
site["vyork"] = vb
site["lan"] = [[round(r.lat, 4), round(r.lng, 4), r.name, r.area, int(r.waste_broad), int(r.entries > 0), r.bua22nm if isinstance(r.bua22nm, str) else ""]
               for r in LA.itertuples()]


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else float(o)
    return o


# a few counts for the text
yd_all = P[(P.region == "Yorkshire") & (P.entries > 0)]
R["yks_waste_direct_n"] = int(yd_all.any_waste.sum())
R["yks_waste_broad_n"] = int(P[P.region == "Yorkshire"].waste_broad.sum())
R["yks_places_broad"] = int((P.region == "Yorkshire").sum())
R["chs_waste_direct_n"] = int(P[(P.region == "Cheshire") & (P.entries > 0)].any_waste.sum())
R["study_waste_broad_n"] = int(P[P.county.isin(STUDY)].waste_broad.sum())
R["all_waste_broad_n"] = int(P.waste_broad.sum())
R["map_points"] = len(pts)
R = clean(R)
json.dump(clean(site), open(os.path.join(WORK, "site.json"), "w"), separators=(",", ":"), allow_nan=False, default=lambda o: None)
json.dump(R, open(os.path.join(DATA, "results.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: R[k] for k in ["yks", "rest_waste_direct", "rest_value_ratio", "yks_waste_no_value_share", "chs_shr_was_share", "mid_now_share",
                                    "novalue_text_now_share", "valued_text_was_share", "geo_medians", "geo_logit", "ls", "ls_yks", "ls_broad",
                                    "lost_yks_waste", "lost_yks_not", "lan_n_places", "lan_waste_broad", "preston_included", "rv_n", "rv_waste_broad_n",
                                    "county_rank", "hex_over_half", "geo_bands", "north_dist_bands", "geo_value_york", "chs_bands", "chs_logit",
                                    "yks_hundred_top", "yks_hundred_low_value", "yks_hundred_high_value"]}, indent=0, default=str)[:12000])
