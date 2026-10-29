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
| GEOGRAPHY | `LAD` local authorities, `CAUTH` combined authorities, `ELE_MP` Westminster constituencies, `LSOA`, `MSOA`, `ITL1`–`ITL3`, `NUTS1`–`NUTS3` |
| COVERAGE | `UK`, `GB`, `EW` (England & Wales), `ENG`, `WLS`, `SCT`, `NIR` |
| YEAR, MONTH | The ONS boundary version, e.g. `2025_12` = December 2025 |

Every file has the object key `geog`. Each area has `properties.id` (the official code, e.g.
`W06000015`) and `properties.name`.

## 1. Pre-filtered nation files

Each nation file contains exactly the same shapes as the UK/EW file, just fewer of them.

| Geography | England | Wales | Scotland | Northern Ireland |
|---|---|---|---|---|
| Local Authority Districts, Dec 2025 | [LAD_ENG_2025_12](LAD_ENG_2025_12.json) | [LAD_WLS_2025_12](LAD_WLS_2025_12.json) | [LAD_SCT_2025_12](LAD_SCT_2025_12.json) | [LAD_NIR_2025_12](LAD_NIR_2025_12.json) |
| Westminster constituencies, Jul 2024 | [ELE_MP_ENG_2024_07](ELE_MP_ENG_2024_07.json) | [ELE_MP_WLS_2024_07](ELE_MP_WLS_2024_07.json) | [ELE_MP_SCT_2024_07](ELE_MP_SCT_2024_07.json) | [ELE_MP_NIR_2024_07](ELE_MP_NIR_2024_07.json) |
| MSOA 2021 | [MSOA_ENG_2021](MSOA_ENG_2021.json) | [MSOA_WLS_2021](MSOA_WLS_2021.json) | – | – |
| LSOA 2021 | [LSOA_ENG_2021](LSOA_ENG_2021.json) | [LSOA_WLS_2021](LSOA_WLS_2021.json) | – | – |

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
| [lookups/LAD_UK_2025_12.csv](lookups/LAD_UK_2025_12.csv) | Local authority (Dec 2025, also valid for May 2025) | `lad_id`, `lad_name`, `ctry_*` country, `rgn_*` region (England only), `cauth_*` combined authority (England only), `itl1_*`, `itl2_*`, `itl3_*` |
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

## Things to watch

- **Match versions.** Join data and lookups to the boundary version they were published
  for. Codes change when local authorities merge, e.g. Cumbria, North Yorkshire and
  Somerset in April 2023.
- **Regions (`rgn`) cover England only.** For a UK-wide set of regions that includes Wales,
  Scotland and Northern Ireland, use ITL1.
- **Combined Authorities are not the same as Mayoral Strategic Authorities.** The ONS
  Combined Authority list (`cauth`) includes some authorities without a mayor (e.g. Devon and
  Torbay, Lancashire) and leaves out the Greater London Authority.
- **North Ayrshire** is split between two ITL areas, because Arran and Cumbrae are in
  Highlands and Islands. The lookup assigns it to its mainland area, TLM93.
- **Side-by-side maps.** In `alt.hconcat` / `vconcat`, Vega-Lite shares one projection
  between charts with identical projection settings, so a filtered map can appear tiny.
  Use separate charts if each should zoom to its own area.
- **Need more detail when zoomed in?** Files in [`full/`](full/) are near full resolution.
  Methods 2 and 3 work on them too.
