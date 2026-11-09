# UK boundaries: filtering to nations, regions and authorities

Charts often need only part of the UK, for example Wales, the North East or one Combined
Authority. There are three ways to get there, from simplest to most flexible:

1. [Use a pre-filtered nation file](#1-pre-filtered-nation-files)
2. [Filter by code in the chart](#2-filter-by-code-in-the-chart)
3. [Join a lookup table and filter by any parent area](#3-filter-by-parent-area-with-a-lookup)

For one local authority on its own, use the [one-file-per-area folder](#6-one-area-per-file-areas).

All URLs below start with:
```
https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/
```

## How files are named

`gbr/{GEOGRAPHY}_{COVERAGE}_{YEAR}[_{MONTH}].json`. Change one part to get a different
file:

| Part | Values |
|---|---|
| GEOGRAPHY | `LAD` local authorities (lower tier), `CTYUA` counties and unitary authorities (upper tier), `CAUTH` combined authorities, `SA` Strategic Authorities, `ELE_MP` Westminster constituencies, `LSOA`, `MSOA`, `ITL1`–`ITL3`, `NUTS1`–`NUTS3` |
| COVERAGE | `UK`, `GB`, `EW` (England & Wales), `ENG`, `WLS`, `SCT`, `NIR` |
| YEAR, MONTH | The ONS boundary version, e.g. `2025_12` = December 2025; for `SA`, the date the authorities are shown as at |

Files in [`proposed/`](proposed/) use the same names for boundaries that are not yet
official, such as announced Strategic Authorities ([section 4](#4-strategic-authorities-and-drilling-into-one)).

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
| [lookups/LAD_UK_2025_12.csv](lookups/LAD_UK_2025_12.csv) | Local authority (Dec 2025; codes also match May 2025 and May 2026. Combined authorities as of May 2025) | `lad_id`, `lad_name`, `ctyua_*` upper-tier authority, `ctry_*` country, `rgn_*` region (England only), `cauth_*` combined authority (England only), `itl1_*`, `itl2_*`, `itl3_*` |
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

Strategic Authorities (SAs) are England's mayoral and non-mayoral combined authorities and
the Greater London Authority. They are not an ONS geography yet, and ONS's `CAUTH` file
leaves out the GLA and authorities set up since its last release. So they are built here
by merging the published LAD boundaries, which means their borders match the LAD file of
the same date exactly.

SAs change often, so there is one map per date. Files in `gbr/` show only the SAs legally
in force on that date. Files in [`proposed/`](proposed/) use the same names, and add the
areas that were agreed, proposed or named on that date, drawn on their planned footprints:

| File | SAs | What it shows |
|---|---|---|
| [SA_ENG_2025_12](SA_ENG_2025_12.json) | 16 | In force on 31 Dec 2025 (LAD Dec 2025 borders) |
| [proposed/SA_ENG_2025_12](proposed/SA_ENG_2025_12.json) | 22 | Plus the 6 Devolution Priority Programme areas |
| [SA_ENG_2026_07](SA_ENG_2026_07.json) | 20 | In force on 31 Jul 2026: 11 Established, 7 Mayoral, 2 Foundation (LAD May 2026 borders) |
| [proposed/SA_ENG_2026_07](proposed/SA_ENG_2026_07.json) | 22 | Plus Greater Essex and Norfolk and Suffolk; West of England with North Somerset |
| [proposed/SA_ENG_2026_10](proposed/SA_ENG_2026_10.json) | 30 | Budget 2026: plus 9 named areas; Devon, Plymouth and Torbay replaces Devon and Torbay |

Each has a `full/` version with `area` (m²), e.g. [full/SA_ENG_2026_07](full/SA_ENG_2026_07.json),
[proposed/full/SA_ENG_2026_10](proposed/full/SA_ENG_2026_10.json), and a lookup with one
row per SA, e.g. [lookups/SA_ENG_2026_07.csv](lookups/SA_ENG_2026_07.csv),
[proposed/lookups/SA_ENG_2026_10.csv](proposed/lookups/SA_ENG_2026_10.csv).

SA properties:

| Property | Meaning |
|---|---|
| `id` | Our `MSA0xx` code. One code is one footprint: when a council joins, the new area gets a new code (West of England with North Somerset is `MSA032`, not `MSA009`) |
| `name`, `short` | Name and acronym (e.g. `GMCA`) |
| `status` | On the file's date: `current` (legally in force), `agreed` (Devolution Priority Programme), `proposed` (expansion proposal submitted) or `named` (named in Budget 2026) |
| `tier` | For current SAs: `established`, `mayoral` or `foundation`. A mayoral SA still waiting for its first election is `mayoral` |
| `planned_tier` | The tier the government plans, for areas that are not current (and Lancashire, Oct 2026) |
| `gss_id` | ONS code of the authority: `E47…` combined authority code, or `E61000001` for the GLA. Blank for authorities ONS hasn't coded yet |
| `cty_id` | The county whose councils are exactly the SA's: metropolitan county (`E11…`: Greater Manchester, South Yorkshire, West Midlands, West Yorkshire) or county (`E10…`: Hertfordshire, Surrey, and Cumbria, a code retired in 2023 but used in older data) |
| `established_from` | Date the first authority on this footprint was legally set up, e.g. `2011-04-01` for Greater Manchester. It can be later than the file's date for an area that was then only agreed |
| `mayor_from` | Year of the first mayoral election for this footprint, held or scheduled (a number; empty if none) |
| `rgn_id`, `itl1_id` | Parent region and ITL1. Thames Valley and Greater Lincolnshire span two, written `E12000003;E12000004` |
| `itl2_id`, `itl2_2021_id` | The ITL2 that is exactly the SA, where one is |

A blank means there is no such value. The lookups add names for each code, plus `cauth_id`,
`body_id` (codes of the same authority share it: `MSA032` → `MSA009`), `replaces` (the
footprint a new code takes over from) and `research_set` (the 21 SAs used in the msa-data
research: everything in `proposed/SA_ENG_2025_12` except London, `MSA022`).

Colour by tier, or keep only the research set:

```python
sa = alt.Data(url=base + "SA_ENG_2026_07.json", format=alt.DataFormat(feature="geog", type="topojson"))
alt.Chart(sa).mark_geoshape(stroke="white").encode(color="properties.tier:N").project("mercator")

research = alt.Data(url=base + "proposed/SA_ENG_2025_12.json", format=alt.DataFormat(feature="geog", type="topojson"))
alt.Chart(research).mark_geoshape().transform_filter("datum.properties.id != 'MSA022'")
```

`lookups/LAD_UK_2025_12.csv` has `sa_id` / `sa_name` for each LAD in one of the 22 SAs on
`proposed/SA_ENG_2025_12`. For other dates, check the SA's `status` in that date's file.

### Drilling into one SA

`sa/<slug>/` holds one folder per SA on `proposed/SA_ENG_2025_12` (the research set and
London), e.g. `sa/msa016_cumbria/`, `sa/msa022_greater_london/`. Each folder has
`SA.json`, `LAD.json`, `MSOA.json` and `LSOA.json` (2021).

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

## 5. Lower-tier and upper-tier local authorities

Much of England has two tiers of council. **District councils** (lower tier) handle
things like housing, planning and bin collections. **County councils** (upper tier) handle
schools, social care and roads. Everywhere else, one council does both: unitary
authorities, metropolitan districts, London boroughs, and every council in Wales,
Scotland and Northern Ireland.

| File | Tier | What it covers |
|---|---|---|
| `LAD_*` | Lower (often called LTLA) | Every district plus every single-tier council |
| `CTYUA_*` ([UK](CTYUA_UK_2025_12.json), [England](CTYUA_ENG_2025_12.json), [full](full/CTYUA_UK_2025_12.json)) | Upper (often called UTLA) | The 21 English counties (codes starting `E10`) plus every single-tier council |

A single-tier council has the **same code and shape in both files**, e.g. Leeds is
`E08000035` in each. Only the counties and their districts (codes starting `E07`) differ.

Which file to use depends on how the data is published. Look at the codes: if they
include `E10…` codes, use `CTYUA`; if they include `E07…` codes, use `LAD`. Most ONS
statistics are lower tier. Data on services run by county councils (for example,
schools, children's services, adult social care and public health) is often upper tier.
The `ctyua_id` / `ctyua_name` columns in
[lookups/LAD_UK_2025_12.csv](lookups/LAD_UK_2025_12.csv) give each district its county
(and each single-tier council itself), so upper-tier data can be joined onto a LAD map.

Some health data uses *grouped* lower-tier areas, with Cornwall and the Isles of Scilly
together, and Hackney and the City of London together. Those groupings aren't published
here, so join the data to `LAD` and expect those four areas to need a manual fix.

## 6. One area per file (`areas/`)

Every local authority has its own file, named by its code:

```
gbr/areas/{code}.json         e.g. gbr/areas/E08000035.json  (Leeds)
```

The folder covers both tiers: districts, single-tier councils and English counties (`E10…`).
It also has codes that no longer exist (e.g. `E07000004` Aylesbury Vale, abolished
2020), so older data still has a shape. [`areas/index.csv`](areas/index.csv) lists every
file:

| Column | Meaning |
|---|---|
| `id`, `name` | Code and name |
| `tier` | `lower` (district), `upper` (county) or `both` (single-tier council) |
| `current` | `True` if the code is in use in the latest ONS release |
| `release` | The ONS release the shape comes from, e.g. `LAD_UK_2026_05` |
| `area` | Land area in m² (ONS, from the full-resolution boundary) |

Each file is cut from the full-resolution boundaries (the same shape as in `full/`) and has
`id`, `name` and `area`. Each code has **one file, holding its latest version**. ONS
sometimes redraws a boundary slightly without changing the code (e.g. coastline updates),
and when it does the file is updated. If you need the shape from a particular release,
filter the dated file instead.

Map one authority, or highlight it on a national map:

```python
def topo(url): return alt.Data(url=url, format=alt.DataFormat(feature="geog", type="topojson"))

leeds = alt.Chart(topo(base + "areas/E08000035.json")).mark_geoshape(fill="#c0392b")
leeds.project("mercator")                                   # zoomed to Leeds

alt.layer(
    alt.Chart(topo(base + "LAD_ENG_2026_05.json")).mark_geoshape(fill="#e6e6e6", stroke="white", strokeWidth=0.3),
    leeds,
).project("mercator")                                       # Leeds within England
```

The shapes line up exactly with the `full/` file of the same release. Standard `gbr/`
files are simplified more, so their edges differ slightly, which is only noticeable when
zoomed in.

## Things to watch

- **Match versions.** Join data and lookups to the boundary version they were published
  for. Codes change when local authorities merge, e.g. Cumbria, North Yorkshire and
  Somerset in April 2023.
- **Regions (`rgn`) cover England only.** For a UK-wide set of regions that includes Wales,
  Scotland and Northern Ireland, use ITL1.
- **Combined Authorities are not the same as Strategic Authorities.** The ONS Combined
  Authority list (`cauth`, December 2025) has 15 authorities. It leaves out the Greater
  London Authority and the four set up in 2026 (Cumbria, Cheshire and Warrington, Sussex
  and Brighton, Hampshire and the Solent), and includes two without a mayor (Devon and
  Torbay, Lancashire). The `SA` files cover them all.
- **Proposed areas are not official.** Files in `proposed/` show agreed or announced
  footprints, which can change before an authority is set up. The Wessex footprint
  (Bournemouth, Christchurch and Poole; Dorset; Somerset; Wiltshire) is an assumption,
  as the Budget did not list its councils.
- **North Ayrshire** is split between two ITL areas, because Arran and Cumbrae are in
  Highlands and Islands. The lookup assigns it to its mainland area, TLM93.
- **Side-by-side maps.** In `alt.hconcat` / `vconcat`, Vega-Lite shares one projection
  between charts with identical projection settings, so a filtered map can appear tiny.
  Use separate charts if each should zoom to its own area.
- **Need more detail when zoomed in?** Files in [`full/`](full/) are near full resolution.
  Methods 2 and 3 work on them too.
