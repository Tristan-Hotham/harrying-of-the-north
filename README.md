# Laid Waste: the Harrying of the North

William the Conqueror's Harrying of the North (winter 1069 to 1070) as Domesday Book recorded it in 1086: where the "waste" fell, what the word means, whether it follows an army's routes, and whether the places it touched are smaller or poorer today.

**Interactive version:** https://tristan-hotham.github.io/harrying-of-the-north/

**Paper:** https://doi.org/10.5281/zenodo.23689581

This repository holds the interactive page, the datasets, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349). Companion studies: [The Conquest in Castles](https://tristan-hotham.github.io/norman-castles/), [Is Domesday Destiny?](https://tristan-hotham.github.io/domesday-destiny/) and [The Villages That Vanished](https://tristan-hotham.github.io/lost-villages/).

## Headline results

- Of 1,345 Domesday entries flagged as waste, 79% are in Yorkshire, Cheshire, Derbyshire, Nottinghamshire, Staffordshire and Shropshire. Outside these and Herefordshire only 2.1% of places have a waste entry, and recorded value rose to 110% of 1066.
- In Yorkshire, 37% of the 1,302 places with their own entries are called waste (50% of all 1,786 places once member vills of great estates are counted). Yorkshire's value in 1086 was 35% of 1066 (32% without the city of York).
- The word means different things. In Derbyshire, Nottinghamshire and Staffordshire 95% of waste entries say the land is waste in 1086; in Cheshire and Shropshire 70% say it was waste (around 1070) and had recovered. In Yorkshire, which has no text in the source, 83% of waste entries give no 1086 value.
- In Yorkshire, waste does not cluster near York (median distance 44 km for waste and other places alike) or along Roman roads. It climbs with height: each 100 m multiplies the odds of waste by 2.1 (95% interval 1.6 to 2.8).
- Value held up better near York: rural places within 15 km were worth 65% of 1066 in 1086, against about a third farther out.
- The long shadow is faint. Compared with places of similar 1066 value in the same county, places waste in 1086 are no less likely to be built up today (-1.4 points, interval -8.1 to +5.3); local household income is 2.5% lower (interval 0.5% to 4.4%); deserted villages differ by +4.3 points, not clearly different from zero. 195 places named in waste entries later became deserted villages.
- Lancashire: one entry names Preston and 61 vills of Amounderness, all coded waste. In the modern Ribble Valley district, 18 of 33 Domesday places are named in a waste entry; none of the places of Blackburn hundred is called waste, where settlers had been given three years free of dues.

## Files

- `index.html`: the interactive page (Leaflet map with waste, value, today and hexagon layers; charts; Lancashire map). Data embedded.
- `header.png`: social card (1200 by 630).
- `data/places.csv`: one row per located Domesday place (12,812) with waste flags, paired values for 1066 and 1086, setting (height, relief, distance to river and Roman road), distance from York and Chester, the Beresford lost-village flag, the matched Built-up Area 2022, parish residents 2021 and MSOA income.
- `data/domesday_entries.csv`: one row per Domesday entry of the manor or urban kind (20,195), with the waste flag, the reading of the text, values and hundred.
- `data/county_waste.csv`, `data/hundred_waste.csv`: waste and value by county (Lancashire and north-east Wales split out) and by hundred or wapentake.
- `data/hexes.geojson`: hexagons (8 km centre to corner) with places, waste and values.
- `data/geography_bands.csv`, `data/long_shadow.csv`, `data/lancashire_places.csv`: the tables behind sections 05 to 07.
- `data/results.json`: every number used on the page, in the paper, the blog post and the collage.
- `code/01_extract.py`, `code/02_analyse.py`, `code/03_build_page.py` (fills `code/page_template.html`), `code/04_header.py`.
- `release/`: figures, paper source and build script, blog post, Zenodo files. `reddit/`: collage.

## How to rerun

The scripts read shared inputs in place (paths at the top of `code/01_extract.py`): a clone of https://github.com/embabel-worlds/realm-domesday, the companion projects' data (`lost-villages/data/domesday_places_status.csv` for setting and lost-village flags; `domesday-destiny/data/domesday_places.csv` for parish residents), and ONS files (Built-up Areas 2022, LSOA to BUA lookup, Census 2021 TS001 by LSOA, small-area income FYE 2023).

```
python3 code/01_extract.py
python3 code/02_analyse.py
python3 code/03_build_page.py
python3 code/04_header.py
python3 release/make_figures.py
python3 release/paper/build_paper.py
python3 release/blog/build_post.py
python3 reddit/collage.py
```

It needs Python 3 with pandas, numpy, scipy, statsmodels, pyyaml, pyproj, openpyxl and matplotlib, and xelatex for the paper.

## Method in brief and known limits

- Entries of the manor and urban kinds only; Yorkshire's summary and claims sections, which repeat holdings, are left out. That is why the Yorkshire share here is higher than in The Conquest in Castles, which counted summary entries too.
- "Waste" is the Hull Project's flag. A place is waste (own entry) if an entry describing it is flagged, and named in a waste entry if it is also listed as a member vill of a flagged entry. Member lists overstate waste where only part of an estate was waste (as at Preston, where the text says sixteen vills had a few inhabitants).
- Values: a waste entry with a 1066 value and no 1086 value counts as worth nothing in 1086; other entries lacking a 1086 value are left out. With both values only, Yorkshire stood at 39% of 1066. Values for the land between the Ribble and the Mersey are left out because 1086 values there are mostly given for whole hundreds.
- Text readings (counties other than Yorkshire) use simple word patterns.
- Today: nearest ONS Built-up Area 2022 whose edge, treated as a circle of equal area, lies within 1 km; income for the MSOA containing the place's LSOA. Comparisons use county by 1066-value-tercile fixed effects plus log 1066 value, with robust standard errors. Associations, not causes.
- On the debate over what waste means, the page cites only works whose details I could check (Dalton 2002, Palmer 1998, Thomas 2008, Wightman 1975, and the Wikipedia overview); I did not read them in full here.

## Sources and licences

- Domesday data: Hull Domesday Project, Professor J.J.N. Palmer, George Slater and the University of Hull (CC BY-NC-SA), https://digitalcollections.hull.ac.uk/collections/3t945r28b, via the realm-domesday repository by embabel-worlds, https://github.com/embabel-worlds/realm-domesday
- Beresford's Lost Villages, University of Hull (CC BY-NC-SA 4.0), https://dmv.wordpress.hull.ac.uk/, via The Villages That Vanished.
- ONS Built-up Areas 2022, LSOA 2021 to BUA 2022 lookup, Census 2021 TS001 and income estimates for small areas FYE 2023: Office for National Statistics, Open Government Licence v3.0. Contains OS data © Crown copyright and database right 2026.
- OS Open Rivers and OS Open Names: contains OS data © Crown copyright and database right 2026 (OGL v3).
- Roman roads: Itiner-e, de Soto, P., Pažout, A., Brughmans, T. and others (2025), https://zenodo.org/records/17122148 (CC BY 4.0).
- Elevation: AWS Terrain Tiles by Mapzen/Tilezen (https://github.com/tilezen/joerd/blob/master/docs/attribution.md).
- Amounderness quotation: J. Porter (1876) History of the Fylde of Lancashire, Project Gutenberg eBook 65919.
- Coastline in static figures: Natural Earth (public domain). Base map tiles: © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community.

Because the Domesday and lost-village data are CC BY-NC-SA, the derived data (`data/`) and the page text are released under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/). The code (`code/`, `release/`, `reddit/`) is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026). *Laid Waste: The Harrying of the North in Domesday Book and Today*. Zenodo. https://doi.org/10.5281/zenodo.23689581

Dr Tristan Hotham, Independent researcher, ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
