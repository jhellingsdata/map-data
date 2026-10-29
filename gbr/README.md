# UK boundaries: filtering to nations, regions and authorities

Charts often need only part of the UK, for example Wales, the North East or one Combined
Authority. There are three ways to get there, from simplest to most flexible:

1. [Use a pre-filtered nation file](#1-pre-filtered-nation-files)
2. [Filter by code in the chart](#2-filter-by-code-in-the-chart)
3. [Join a lookup table and filter by any parent area](#3-filter-by-parent-area-with-a-lookup)

All URLs below start with:
```
https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/
```

## How files are named

`gbr/{GEOGRAPHY}_{COVERAGE}_{YEAR}[_{MONTH}].json`. Change one part to get a different
file:

| Part | Values |
|---|---|
| GEOGRAPHY | `LAD` local authorities, `CAUTH` combined authorities, `SA` Strategic Authorities, `ELE_MP` Westminster constituencies, `LSOA`, `MSOA`, `ITL1`–`ITL3`, `NUTS1`–`NUTS3` |
| COVERAGE | `UK`, `GB`, `EW` (England & Wales), `ENG`, `WLS`, `SCT`, `NIR` |
| YEAR, MONTH | The ONS boundary version, e.g. `2025_12` = December 2025 |

Every file has the object key `geog`. Each area has `properties.id` (the official code, e.g.
`W06000015`) and `properties.name`.

## 1. Pre-filtered nation files

Each nation file contains exactly the same shapes as the UK/EW file, just fewer of them.

| Geography | England | Wales | Scotland | Northern Ireland |
|---|---|---|---|---|
| Local Authority Districts, May 2026 | [LAD_ENG_2026_05](LAD_ENG_2026_05.json) | [LAD_WLS_2026_05](LAD_WLS_2026_05.json) | [LAD_SCT_2026_05](LAD_SCT_2026_05.json) | [LAD_NIR_2026_05](LAD_NIR_2026_05.json) |
| Local Authority Districts, Dec 2025 | [LAD_ENG_2025_12](LAD_ENG_2025_12.json) | [LAD_WLS_2025_12](LAD_WLS_2025_12.json) | [LAD_SCT_2025_12](LAD_SCT_2025_12.json) | [LAD_NIR_2025_12](LAD_NIR_2025_12.json) |
| Westminster constituencies, Jul 2024 | [ELE_MP_ENG_2024_07](ELE_MP_ENG_2024_07.json) | [ELE_MP_WLS_2024_07](ELE_MP_WLS_2024_07.json) | [ELE_MP_SCT_2024_07](ELE_MP_SCT_2024_07.json) | [ELE_MP_NIR_2024_07](ELE_MP_NIR_2024_07.json) |
| MSOA 2021 | [MSOA_ENG_2021](MSOA_ENG_2021.json) | [MSOA_WLS_2021](MSOA_WLS_2021.json) | – | – |
| LSOA 2021 | [LSOA_ENG_2021](LSOA_ENG_2021.json) | [LSOA_WLS_2021](LSOA_WLS_2021.json) | – | – |

### Older local authority versions

Local authority codes change when councils merge or are reorganised. Data published for an
older set of codes needs a map from the same period. There is one nation file for each
distinct set of codes:

| Nation | File | Use for data published on... |
|---|---|---|
| England | [LAD_ENG_2026_05](LAD_ENG_2026_05.json) | May 2025 onwards (new Sheffield and Barnsley codes) |
| England | [LAD_ENG_2023_05](LAD_ENG_2023_05.json) | Apr 2023 – Apr 2025 (Cumberland, Westmorland and Furness, North Yorkshire, Somerset created) |
| England | [LAD_ENG_2021_05](LAD_ENG_2021_05.json) | Apr 2021 – Mar 2023 (North and West Northamptonshire), incl. most 2021 Census outputs |
| Scotland | [LAD_SCT_2026_05](LAD_SCT_2026_05.json) | 2019 onwards (new Glasgow City and North Lanarkshire codes) |
| Scotland | [LAD_SCT_2018_12](LAD_SCT_2018_12.json) | 2018 (new Fife and Perth and Kinross codes) |
| Scotland | [LAD_SCT_2016_12](LAD_SCT_2016_12.json) | before 2018 |
| Wales | [LAD_WLS_2026_05](LAD_WLS_2026_05.json) | any date: the 22 codes have not changed since at least 2011 |
| Northern Ireland | [LAD_NIR_2026_05](LAD_NIR_2026_05.json) | April 2015 onwards (the 11 current districts) |

To check, compare the codes in your data with the map's `properties.id`. Codes that don't
match usually mean the data and the map are from different versions.

```python
import altair as alt

url = "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/LAD_WLS_2025_12.json"
alt.Chart(alt.Data(url=url, format=alt.DataFormat(feature="geog", type="topojson"))).mark_geoshape(
    stroke="white"
).project("mercator")
```

## 2. Filter by code in the chart

The first letter of a UK code (GSS code) tells you the nation: **E** England, **W** Wales,
**S** Scotland, **N** Northern Ireland. You can use this to filter any UK file:

```python
alt.Chart(data).mark_geoshape().transform_filter(
    "indexof(datum.properties.id, 'W') == 0"      # Wales only
).project("mercator")
```

To pick out specific areas, pass a list of codes:

```python
alt.Chart(data).mark_geoshape().transform_filter(
    alt.FieldOneOfPredicate(field="properties.id", oneOf=["W06000015", "W06000022"])  # Cardiff, Newport
)
```

## 3. Filter by parent area with a lookup

The lookup tables in [`lookups/`](lookups/) list the larger areas that each small area
belongs to. Each one has the same name as the boundary file it matches:

| Lookup | One row per | Columns |
|---|---|---|
| [lookups/LAD_UK_2025_12.csv](lookups/LAD_UK_2025_12.csv) | Local authority (Dec 2025; codes also match May 2025 and May 2026. Combined authorities as of May 2025) | `lad_id`, `lad_name`, `ctry_*` country, `rgn_*` region (England only), `cauth_*` combined authority (England only), `itl1_*`, `itl2_*`, `itl3_*` |
| [lookups/LSOA_EW_2021.csv](lookups/LSOA_EW_2021.csv) | LSOA (2021) | `lsoa_*`, `msoa_*`, `lad_*` (LAD Dec 2025) |

Each `*` stands for `_id` and `_name`. The sources are official ONS lookups.

**In Python (pandas):** look up the codes, then filter the map. For example, the local
authorities in the North East ITL1 region:

```python
import pandas as pd

base = "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/"
lookup = pd.read_csv(base + "lookups/LAD_UK_2025_12.csv")
codes = lookup.loc[lookup["itl1_name"] == "North East (England)", "lad_id"].tolist()

alt.Chart(alt.Data(url=base + "LAD_UK_2025_12.json", format=alt.DataFormat(feature="geog", type="topojson"))
).mark_geoshape(stroke="white").transform_filter(
    alt.FieldOneOfPredicate(field="properties.id", oneOf=codes)
).project("mercator")
```

**In the chart (Altair / Vega-Lite only):** join the lookup onto the map, then filter on any
of its columns:

```python
alt.Chart(alt.Data(url=base + "LAD_UK_2025_12.json", format=alt.DataFormat(feature="geog", type="topojson"))
).mark_geoshape(stroke="white").transform_lookup(
    lookup="properties.id",
    from_=alt.LookupData(alt.Data(url=base + "lookups/LAD_UK_2025_12.csv"), key="lad_id",
                         fields=["cauth_name", "itl1_name"]),
).transform_filter(
    "datum.cauth_name == 'Greater Manchester'"
).encode(
    color="properties.name:N", tooltip=["properties.name:N", "cauth_name:N"]
).project("mercator")
```

Vega-Lite equivalent:
```json
{
  "data": {"url": "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/LAD_UK_2025_12.json",
           "format": {"type": "topojson", "feature": "geog"}},
  "transform": [
    {"lookup": "properties.id",
     "from": {"data": {"url": "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/lookups/LAD_UK_2025_12.csv"},
              "key": "lad_id", "fields": ["cauth_name", "itl1_name"]}},
    {"filter": "datum.cauth_name == 'Greater Manchester'"}
  ],
  "mark": {"type": "geoshape", "stroke": "white"},
  "projection": {"type": "mercator"}
}
```

## 4. Strategic Authorities, and drilling into one

England's 21 Strategic Authorities (SAs: mayoral and non-mayoral combined authorities,
plus the newer Devolution Priority Programme areas) are not an ONS geography yet, and
ONS's `CAUTH` file leaves out the areas that have no combined authority code. They are
built here by merging the published LAD boundaries, so their borders match
`LAD_UK_2025_12` exactly.

| File | What it is |
|---|---|
| [SA_ENG_2025_12](SA_ENG_2025_12.json) / [full](full/SA_ENG_2025_12.json) | The 21 SAs (full adds `area`, m²) |
| [lookups/SA_ENG_2025_12.csv](lookups/SA_ENG_2025_12.csv) | One row per SA, with parent and matching area names |
| `lookups/LAD_UK_2025_12.csv` | Now also has `sa_id` / `sa_name` for each member LAD |
| `sa/<slug>/SA.json`, `LAD.json`, `MSOA.json`, `LSOA.json` | One SA, its LADs, MSOAs and LSOAs (2021), e.g. `sa/msa016_cumbria/` |

SA properties: `id` (an `MSA001`–`MSA021` code, as SAs have no ONS code yet), `name`,
`short` (acronym), `cauth_id` (the ONS combined authority code, where the SA is one),
`rgn_id` / `itl1_id` (parent region; Greater Lincolnshire spans two, written
`E12000003;E12000004`), and `itl2_id` / `itl2_2021_id` (the ITL2 that is exactly the SA,
where one is). A blank means there is no such area.

The four files in an SA folder are all built from the same LSOAs, so their borders
overlay exactly. LSOAs carry `msoa_id` and `lad_id`, and MSOAs `lad_id`, for colouring
or highlighting by parent. Layer them to show small areas under their district and SA
borders:

```python
sa = base + "sa/msa016_cumbria/"
def layer(f): return alt.Data(url=sa + f, format=alt.DataFormat(feature="geog", type="topojson"))

alt.layer(
    alt.Chart(layer("LSOA.json")).mark_geoshape(fill="#e8eef5", stroke="#9fb3c8", strokeWidth=0.2),
    alt.Chart(layer("LAD.json")).mark_geoshape(filled=False, stroke="#c0392b", strokeWidth=1.4),
    alt.Chart(layer("SA.json")).mark_geoshape(filled=False, stroke="black", strokeWidth=1.8),
).project("mercator")
```

## Things to watch

- **Match versions.** Join data and lookups to the boundary version they were published
  for. Codes change when local authorities merge, e.g. Cumbria, North Yorkshire and
  Somerset in April 2023.
- **Regions (`rgn`) cover England only.** For a UK-wide set of regions that includes Wales,
  Scotland and Northern Ireland, use ITL1.
- **Combined Authorities are not the same as Strategic Authorities.** The ONS Combined
  Authority list (`cauth`) covers 15 of the 21 SAs (the six Devolution Priority Programme
  areas have no code yet), includes some without a mayor (Devon and Torbay, Lancashire) and
  leaves out the Greater London Authority. The `sa` files cover all 21.
- **North Ayrshire** is split between two ITL areas, because Arran and Cumbrae are in
  Highlands and Islands. The lookup assigns it to its mainland area, TLM93.
- **Side-by-side maps.** In `alt.hconcat` / `vconcat`, Vega-Lite shares one projection
  between charts with identical projection settings, so a filtered map can appear tiny.
  Use separate charts if each should zoom to its own area.
- **Need more detail when zoomed in?** Files in [`full/`](full/) are near full resolution.
  Methods 2 and 3 work on them too.
