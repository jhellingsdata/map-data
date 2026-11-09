# English Strategic Authorities

Strategic Authorities (SAs) are the bodies that take on devolved powers in England. They
are combined authorities and combined county authorities, which group several councils,
plus the Greater London Authority. Each SA is in one of three tiers:

- **Established**: the most powers; eligible for an integrated funding settlement;
- **Mayoral**: an elected mayor;
- **Foundation**: no mayor.

The set of SAs changes often. New authorities are being set up, councils are joining
existing ones, and more areas are announced at each fiscal event. So this repo publishes
**one SA map per date**, plus *proposed* maps showing what was planned on that date.

All URLs below start with:
```
https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/
```

## Which file do I need?

| I want… | File |
|---|---|
| The latest SAs in force (July 2026) | [`SA_ENG_2026_07.json`](../SA_ENG_2026_07.json): 20 SAs (11 Established, 7 Mayoral, 2 Foundation) |
| The SAs in force at the end of 2025 | [`SA_ENG_2025_12.json`](../SA_ENG_2025_12.json): 16 SAs |
| The July 2026 SAs plus areas agreed or proposed but not yet in force | [`proposed/SA_ENG_2026_07.json`](../proposed/SA_ENG_2026_07.json): 22 areas |
| The map set out at Budget 2026, including the newly named areas | [`proposed/SA_ENG_2026_10.json`](../proposed/SA_ENG_2026_10.json): 30 areas |
| The 21 SAs used in the msa-data research | [`proposed/SA_ENG_2025_12.json`](../proposed/SA_ENG_2025_12.json), minus London (`MSA022`) |
| One SA with its councils and small areas | A folder below, e.g. [`sa/msa016_cumbria/`](msa016_cumbria/) |
| Accurate land areas, or a map zoomed in on a few SAs | The same name in `full/` or `proposed/full/` |
| Names, parent areas and codes as a table | The same name in `lookups/` or `proposed/lookups/` (`.csv`) |

The date in a filename is the date the SAs are shown as at. For example, `2026_07` is
31 July 2026.

**Current** files (`gbr/`) show only SAs legally in force on that date. **Proposed** files
(`gbr/proposed/`) have the same names and also include:
- areas **agreed** in the Devolution Priority Programme;
- areas **proposed** as an expansion;
- areas **named** for a future deal.

Each area is drawn on its planned footprint. When a footprint replaces an existing one,
only the new one is shown: West of England with North Somerset (`MSA032`) appears in
place of `MSA009`.

| File | SAs | LAD borders | Standard | Full | Lookup |
|---|---|---|---|---|---|
| `SA_ENG_2025_12` | 16 | Dec 2025 | [json](../SA_ENG_2025_12.json) | [json](../full/SA_ENG_2025_12.json) | [csv](../lookups/SA_ENG_2025_12.csv) |
| `proposed/SA_ENG_2025_12` | 22 | Dec 2025 | [json](../proposed/SA_ENG_2025_12.json) | [json](../proposed/full/SA_ENG_2025_12.json) | [csv](../proposed/lookups/SA_ENG_2025_12.csv) |
| `SA_ENG_2026_07` | 20 | May 2026 | [json](../SA_ENG_2026_07.json) | [json](../full/SA_ENG_2026_07.json) | [csv](../lookups/SA_ENG_2026_07.csv) |
| `proposed/SA_ENG_2026_07` | 22 | May 2026 | [json](../proposed/SA_ENG_2026_07.json) | [json](../proposed/full/SA_ENG_2026_07.json) | [csv](../proposed/lookups/SA_ENG_2026_07.csv) |
| `proposed/SA_ENG_2026_10` | 30 | May 2026 | [json](../proposed/SA_ENG_2026_10.json) | [json](../proposed/full/SA_ENG_2026_10.json) | [csv](../proposed/lookups/SA_ENG_2026_10.csv) |

There is no current file for October 2026. The SAs in force then are the same as in July.

## Every SA

The table shows each SA's tier if it was in force on each date, or its status in *italics*
if it was not. "→ `MSA0xx`" means a new footprint replaces it on that date's proposed map.

| Code | Name | Short | Dec 2025 | Jul 2026 | Oct 2026 | Drill-down |
|---|---|---|---|---|---|---|
| `MSA001` | Greater Manchester | GMCA | mayoral | established | established | [folder](msa001_greater_manchester/) |
| `MSA002` | West Midlands | WMCA | mayoral | established | established | [folder](msa002_west_midlands/) |
| `MSA003` | Liverpool City Region | LCRCA | mayoral | established | established | [folder](msa003_liverpool_city_region/) |
| `MSA004` | South Yorkshire | SYMCA | mayoral | established | established | [folder](msa004_south_yorkshire/) |
| `MSA005` | West Yorkshire | WYCA | mayoral | established | established | [folder](msa005_west_yorkshire/) |
| `MSA006` | Tees Valley | TVCA | mayoral | mayoral | mayoral | [folder](msa006_tees_valley/) |
| `MSA007` | North East | NECA | mayoral | established | established | [folder](msa007_north_east/) |
| `MSA008` | Cambridgeshire and Peterborough | CPCA | mayoral | established | established | [folder](msa008_cambridgeshire_and_peterborough/) |
| `MSA009` | West of England | WECA | mayoral | established (→ `MSA032`) | established (→ `MSA032`) | [folder](msa009_west_of_england/) |
| `MSA010` | York and North Yorkshire | YNYCA | mayoral | established | established | [folder](msa010_york_and_north_yorkshire/) |
| `MSA011` | East Midlands | EMCCA | mayoral | established | established | [folder](msa011_east_midlands/) |
| `MSA012` | Hull and East Yorkshire | HEYCA | mayoral | mayoral | mayoral | [folder](msa012_hull_and_east_yorkshire/) |
| `MSA013` | Greater Essex | GECCA | *agreed* | *agreed* | *agreed* | [folder](msa013_greater_essex/) |
| `MSA014` | Sussex and Brighton | SBCCA | *agreed* | mayoral | mayoral | [folder](msa014_sussex_and_brighton/) |
| `MSA015` | Hampshire and the Solent | HSCCA | *agreed* | mayoral | mayoral | [folder](msa015_hampshire_and_the_solent/) |
| `MSA016` | Cumbria | CCA | *agreed* | mayoral | mayoral | [folder](msa016_cumbria/) |
| `MSA017` | Cheshire and Warrington | CWCA | *agreed* | mayoral | mayoral | [folder](msa017_cheshire_and_warrington/) |
| `MSA018` | Devon and Torbay | DTCCA | foundation | foundation | foundation (→ `MSA031`) | [folder](msa018_devon_and_torbay/) |
| `MSA019` | Greater Lincolnshire | GLCCA | mayoral | mayoral | mayoral | [folder](msa019_greater_lincolnshire/) |
| `MSA020` | Lancashire | LCCA | foundation | foundation | foundation, planned mayoral | [folder](msa020_lancashire/) |
| `MSA021` | Norfolk and Suffolk | NSCCA | *agreed* | *agreed* | *agreed* | [folder](msa021_norfolk_and_suffolk/) |
| `MSA022` | Greater London | GLA | mayoral | established | established | [folder](msa022_greater_london/) |
| `MSA023` | Hertfordshire | | – | – | *named* | |
| `MSA024` | Kent and Medway | | – | – | *named* | |
| `MSA025` | Thames Valley | | – | – | *named* | |
| `MSA026` | Surrey | | – | – | *named* | |
| `MSA027` | Leicester, Leicestershire and Rutland | | – | – | *named* | |
| `MSA028` | Stoke and Staffordshire | | – | – | *named* | |
| `MSA029` | Wessex | | – | – | *named* | |
| `MSA030` | Cornwall | | – | – | *named* | |
| `MSA031` | Devon, Plymouth and Torbay | | – | – | *named* | |
| `MSA032` | West of England *(adds North Somerset)* | WECA | – | *proposed* | *proposed* | |

## Codes

SAs have no single official code, so each has an `MSA0xx` code, maintained in the
msa-data repo. **One code is one footprint.** When a council joins or leaves, the new
area gets a new code, and the old one keeps its councils. So data keyed by a code always
means the same set of councils. A change of tier keeps the code: Lancashire stays
`MSA020` if it gains a mayor.

Where an official code exists, it is in `gss_id`: the ONS combined authority code
(`E47…`), or `E61000001` for the GLA. ONS has not yet coded the authorities set up in
2026, so their `gss_id` is blank.

## Properties

| Property | Meaning |
|---|---|
| `id` | `MSA0xx` code |
| `name`, `short` | Name and acronym (e.g. `GMCA`) |
| `status` | On the file's date: `current` (legally in force), `agreed` (Devolution Priority Programme), `proposed` (expansion proposal submitted) or `named` (named at Budget 2026) |
| `tier` | For current SAs: `established`, `mayoral` or `foundation`. A mayoral SA whose first election hasn't happened yet is `mayoral` |
| `planned_tier` | The tier the government plans, for areas not yet in force (and Lancashire, October 2026). Kent and Medway is `mayoral or foundation` |
| `gss_id` | ONS code of the authority, where one exists |
| `cty_id` | The county whose councils are exactly the SA's: a metropolitan county (`E11…`: Greater Manchester, South Yorkshire, West Midlands, West Yorkshire) or a county (`E10…`: Hertfordshire, Surrey, and Cumbria, whose code was retired in 2023 but appears in older data) |
| `established_from` | Date the first authority on this footprint was legally set up, e.g. `2011-04-01` for Greater Manchester. It can be later than the file's date, for an area that was then only agreed |
| `mayor_from` | Year of the first mayoral election for this footprint, held or scheduled (a number; empty if none) |
| `rgn_id`, `itl1_id` | Parent region and ITL1. An SA spanning two lists both, e.g. Greater Lincolnshire `E12000003;E12000004` |
| `itl2_id`, `itl2_2021_id` | The ITL2 (2025, 2021) that is exactly the SA, where one is |
| `area` | Land area in m², `full/` files only |

A blank means there is no such value. The lookup CSVs have one row per SA, with these
fields plus names for each code, and:
- `cauth_id`: the ONS combined authority code;
- `body_id`: shared by codes of the same authority, e.g. `MSA032` → `MSA009`;
- `replaces`: the footprint a new code takes over from;
- `research_set`: `true` for the 21 SAs used in the msa-data research;
- `n_lads`: the number of member councils.

## How they are built

The boundaries are built by merging the member local authority districts (LADs) of each
SA from the LAD file in force on the date (December 2025 or May 2026). Each SA's borders
are therefore exactly those of its councils in that file, and `area` is the sum of the
councils' ONS areas. Membership, status and tier come from the msa-data repo, which
records the source of each date (statutory instruments, the 2026 Act, Budget 2026).

ONS also publishes combined authorities (`CAUTH_ENG_2025_12`), but those boundaries leave
out the Greater London Authority and every authority set up in 2026. Use the `SA` files
for a complete map.

## Drill-down folders

Each folder holds one SA with four layers, all built from the same 2021 LSOAs, so their
borders overlay exactly:

| File | Areas | Properties |
|---|---|---|
| `SA.json` | The SA outline | `id`, `name`, `area` |
| `LAD.json` | Its councils | `id`, `name`, `area` |
| `MSOA.json` | Its MSOAs (2021) | `id`, `name`, `area`, `lad_id` |
| `LSOA.json` | Its LSOAs (2021) | `id`, `name`, `area`, `msoa_id`, `lad_id` |

Folders exist for the 22 SAs on `proposed/SA_ENG_2025_12`: the research set plus London.
Each folder is named `{code}_{name}`, e.g. `msa022_greater_london`.

The folder outlines come from full-resolution LSOAs, so their edges differ very slightly
from the national `SA_` files, which are built from LADs. Layer a folder's own files
together rather than mixing them with a national file.

## Examples

Colour the July 2026 SAs by tier:

```python
import altair as alt
base = "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/"
def topo(path): return alt.Data(url=base + path, format=alt.DataFormat(feature="geog", type="topojson"))

alt.layer(
    alt.Chart(topo("LAD_ENG_2026_05.json")).mark_geoshape(fill="#eee", stroke="white", strokeWidth=0.3),
    alt.Chart(topo("SA_ENG_2026_07.json")).mark_geoshape(stroke="white").encode(
        color=alt.Color("properties.tier:N", sort=["established", "mayoral", "foundation"]),
        tooltip=["properties.name:N", "properties.tier:N"],
    ),
).project("mercator")
```

The LAD layer underneath fills in areas with no SA, and its borders line up exactly.

Map the msa-data research set of 21:

```python
alt.Chart(topo("proposed/SA_ENG_2025_12.json")).mark_geoshape().transform_filter(
    "datum.properties.id != 'MSA022'"
)
```

Show small areas under their council and SA borders:

```python
sa = "sa/msa022_greater_london/"
alt.layer(
    alt.Chart(topo(sa + "LSOA.json")).mark_geoshape(fill="#e8eef5", stroke="#9fb3c8", strokeWidth=0.1),
    alt.Chart(topo(sa + "LAD.json")).mark_geoshape(filled=False, stroke="#c0392b", strokeWidth=0.8),
    alt.Chart(topo(sa + "SA.json")).mark_geoshape(filled=False, stroke="black", strokeWidth=1.5),
).project("mercator")
```

Add up council-level data to SAs with the LAD lookup. Its `sa_id` follows
`proposed/SA_ENG_2025_12`; for another map, take its member councils from msa-data:

```python
import pandas as pd
# df: your data, one row per council, with columns lad_id and value
lookup = pd.read_csv(base + "lookups/LAD_UK_2025_12.csv", usecols=["lad_id", "sa_id"])
by_sa = df.merge(lookup, on="lad_id").groupby("sa_id", as_index=False)["value"].sum()
```

## Things to watch

- **Proposed areas are not official.** Their footprints can change before an authority is
  set up. Wessex (Bournemouth, Christchurch and Poole; Dorset; Somerset; Wiltshire) is an
  assumption, because the Budget did not list its councils.
- **Established dates.** The six longest-standing mayoral authorities and London are
  `established` from 29 June 2026, when the 2026 Act's tier section came into force. That
  is the earliest possible date; the exact designation dates are still to be confirmed.
- **Two West of England codes.** `MSA009` (three councils) is in force. `MSA032` adds
  North Somerset, whose membership is expected in late 2026 or early 2027. Both have the
  name "West of England" in the files, so check the `id`.
- **Match dates.** Data for a given year usually follows the SAs of that year. For
  example, a 2025 dataset fits `SA_ENG_2025_12`, where Cumbria is not yet an SA.
