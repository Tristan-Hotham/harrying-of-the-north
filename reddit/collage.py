"""Reddit collage for the Harrying of the North study. Run from the reddit/ folder: python3 collage.py
Every number comes from ../data/results.json and ../data/places.csv."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import transform

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "data")
F = "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(F + f)
DISP = fm.FontProperties(fname=F + "FrauncesVar.ttf", weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, LANDC, SEA = "#EEF2F5", "#18202A", "#5E6874", "#DDE4EB", "#EEF2F5"
EMB, EMB2, AMB, ASH = "#C2341B", "#F07A3A", "#E0A04E", "#AEB9C4"
R = json.load(open(os.path.join(D, "results.json")))
P = pd.read_csv(os.path.join(D, "places.csv"))
TO = Transformer.from_crs(4326, 27700, always_xy=True).transform
NORTH = ["YKS", "CHS", "DBY", "NTT", "STS", "SHR", "LIN", "LEC", "HEF", "WOR", "WAR", "NTH", "RUT"]
M = P[P.county.isin(NORTH) & (P.lat > 52.3)]

land = json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_land.geojson"))
LAND = []
for f in land["features"]:
    g = shape(f["geometry"])
    if g.intersects(box(-7, 51.5, 2, 56.5)):
        g = transform(TO, g.intersection(box(-7, 51.5, 2, 56.5)))
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and p.area > 2e7:
                LAND.append(np.array(p.exterior.coords))

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.967, "Did William really burn the North?", fontproperties=DISP, fontsize=44, color=FG, va="top")
fig.text(0.04, 0.917, "In the winter of 1069 to 1070 William the Conqueror harried the north of England. Sixteen years\nlater Domesday Book called hundreds of places \"waste\". Every Domesday place from the Midlands to the Tees:",
         family=SER, fontsize=15, color=FG, va="top", linespacing=1.35)

ax = fig.add_axes([0.0, 0.27, 0.6, 0.6])
ax.set_facecolor(BG)
for a in LAND:
    ax.add_patch(MPoly(a, closed=True, fc=LANDC, ec="none", zorder=0))
n = M[(M.any_waste == 0) & (M.included_waste == 0)]
ax.scatter(n.x, n.y, s=2.2, c=ASH, lw=0, alpha=.8, rasterized=True)
a = M[(M.any_waste == 1) & (M.any_waste_1086 == 0)]
ax.scatter(a.x, a.y, s=7, c=AMB, lw=0, rasterized=True)
m = M[(M.included_waste == 1) & (M.any_waste == 0)]
ax.scatter(m.x, m.y, s=6, facecolors="none", edgecolors=EMB, lw=.6, rasterized=True)
w = M[M.any_waste_1086 == 1]
ax.scatter(w.x, w.y, s=60, c=EMB2, lw=0, alpha=.10, rasterized=True)
ax.scatter(w.x, w.y, s=8, c=EMB, lw=0, rasterized=True)
for nm, lo, la, dx, dy in [("York", -1.08, 53.96, 5000, 4000), ("Chester", -2.89, 53.19, 4000, -9000), ("Preston", -2.70, 53.76, -6000, -11000),
                           ("Lincoln", -0.54, 53.23, 5000, 3000), ("Clitheroe", -2.387, 53.875, 4000, 3000)]:
    x, y = TO(lo, la)
    ax.scatter([x], [y], s=55, c=BG, edgecolors=FG, lw=1.6, zorder=5)
    ax.text(x + dx, y + dy, nm, family=MONO, fontsize=11.5, color=FG, zorder=6, fontweight="medium")
ax.set_xlim(305000, 555000)
ax.set_ylim(285000, 580000)
ax.set_aspect("equal")
ax.axis("off")
from matplotlib.lines import Line2D
lh = [Line2D([], [], marker="o", ls="", mfc=EMB, mec=EMB, ms=8, label="Waste in 1086, no value"),
      Line2D([], [], marker="o", ls="", mfc=AMB, mec=AMB, ms=8, label="Was waste, valued again by 1086"),
      Line2D([], [], marker="o", ls="", mfc=BG, mec=EMB, ms=8, label="Member vill of an estate called waste"),
      Line2D([], [], marker="o", ls="", mfc=ASH, mec=ASH, ms=8, label="No waste recorded")]
fig.legend(handles=lh, loc="upper left", bbox_to_anchor=(0.6, 0.86), frameon=False, prop={"family": MONO, "size": 11}, labelcolor=FG, labelspacing=.6, handletextpad=.4)

tx = fig.add_axes([0.62, 0.285, 0.36, 0.43])
tx.axis("off")
ls = R["ls"]["in_bua"]
notes = [(f"{R['yks']['value_ratio']*100:.0f}%", f"Yorkshire's value in 1086, as a share of\n1066. The rest of England: {R['rest_value_ratio']*100:.0f}%."),
         (f"{R['geo_logit']['elev100']['or']:.1f}×", "the odds of waste for every 100 m of\nheight. Distance from York and from\nRoman roads made no clear difference."),
         (f"{R['chs_shr_was_share']*100:.0f}%", "of waste entries in Cheshire and\nShropshire say the land WAS waste\n(about 1070) and had recovered by 1086."),
         (f"{ls['est']*100:+.1f} pts".replace("-", "−"), f"Waste places today vs similar places:\nno less likely to be a built-up area\n(95% interval {ls['lo']*100:.0f} to +{ls['hi']*100:.0f} points).")]
for (big, small), y in zip(notes, [1.0, 0.75, 0.48, 0.21]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=EMB, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=12.5, color=FG, va="top", transform=tx.transAxes, linespacing=1.3)

G = R["geo_bands"]
panels = [("york", "DISTANCE FROM YORK, KM"), ("elev", "HEIGHT ABOVE SEA, M"), ("roman", "DISTANCE TO A ROMAN ROAD, KM")]
fig.text(0.04, 0.268, "YORKSHIRE: SHARE OF PLACES CALLED WASTE", family=MONO, fontsize=11.5, color=MUT)
for i, (k, t) in enumerate(panels):
    b = fig.add_axes([0.05 + i * 0.32, 0.095, 0.27, 0.135], facecolor=BG)
    rows = G[k]
    v = [r["waste"] for r in rows]
    cols = [EMB if (k == "elev" and r["waste"] > .45) else "#D98A70" for r in rows]
    b.bar(range(len(rows)), v, color=cols, width=.74)
    for j, r in enumerate(rows):
        b.text(j, r["waste"] + .02, f"{r['waste']*100:.0f}%", ha="center", family=MONO, fontsize=10.5, color=FG)
    b.set_xticks(range(len(rows)))
    b.set_xticklabels([r["band"].replace(" to ", "-").replace("under ", "<") for r in rows], family=MONO, fontsize=9.5, color=FG)
    b.set_ylim(0, .7)
    b.set_yticks([])
    for s in ["top", "right", "left"]:
        b.spines[s].set_visible(False)
    b.spines["bottom"].set_color(MUT)
    b.tick_params(axis="x", length=0)
    b.set_title(t, family=MONO, fontsize=10.5, color=FG, loc="left", pad=6)
fig.text(0.04, 0.014, "Data: Hull Domesday Project (J.J.N. Palmer, G. Slater, University of Hull; CC BY-NC-SA) via realm-domesday; ONS Built-up Areas 2022 (OGL v3);\nItiner-e Roman roads (CC BY 4.0); AWS Terrain Tiles; Natural Earth. Waste = Hull's flag; \"waste\" may also mean reorganised or unvalued land.\nAnalysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, "laid_waste.png"), facecolor=BG, dpi=200)
print("ok")
