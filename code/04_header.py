"""Step 4. Make header.png, the 1200 by 630 social card, with matplotlib.

Usage:
    python3 code/04_header.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager as fm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf"]:
    if os.path.exists(FONTS + f):
        fm.fontManager.addfont(FONTS + f)
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
P = pd.read_csv(os.path.join(ROOT, "data", "places.csv"))
P = P[(P.lat > 52.3) & P.county.isin(["YKS", "CHS", "DBY", "NTT", "STS", "SHR", "LIN", "LEC", "HEF", "WOR", "WAR", "NTH", "RUT"])]
BG, FG, HOT, AMB, NONE, MUT = "#EEF1F4", "#1A1F25", "#B8321D", "#D9822B", "#A9B4BF", "#5B6570"
fig = plt.figure(figsize=(6, 3.15), dpi=200, facecolor=BG)
ax = fig.add_axes([0.55, 0.02, 0.44, 0.96])
ax.set_facecolor(BG)
ax.axis("off")
n = P[(P.any_waste == 0) & (P.included_waste == 0)]
ax.scatter(n.x, n.y, s=.9, c=NONE, lw=0)
a = P[(P.any_waste == 1) & (P.any_waste_1086 == 0)]
ax.scatter(a.x, a.y, s=2.2, c=AMB, lw=0)
m = P[(P.included_waste == 1) & (P.any_waste == 0)]
ax.scatter(m.x, m.y, s=2.2, facecolors="none", edgecolors=HOT, lw=.35)
w = P[P.any_waste_1086 == 1]
ax.scatter(w.x, w.y, s=2.6, c=HOT, lw=0)
ax.set_aspect("equal")
fig.text(.05, .86, "DATA STUDY  ·  HISTORY × DATA", family="IBM Plex Mono", fontsize=7, color=MUT)
fig.text(.05, .80, "Laid waste", family="Fraunces", fontweight="black", fontsize=34, color=FG, va="top")
fig.text(.05, .62, "The Harrying of the North in Domesday Book", family="Source Serif 4", fontsize=10.5, color=HOT, va="top")
fig.text(.05, .47, f"In 1086 Yorkshire was worth {R['yks']['value_ratio']*100:.0f}% of its 1066\nvalue. Waste climbed with the hills, not\nwith the roads to York, and its mark on\ntoday's towns is faint.",
         family="Source Serif 4", fontsize=8.6, color=FG, va="top", linespacing=1.4)
fig.text(.05, .07, "DR TRISTAN HOTHAM  ·  INDEPENDENT RESEARCHER", family="IBM Plex Mono", fontsize=6, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=200, facecolor=BG)
print("header.png")
