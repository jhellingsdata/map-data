# map-data — project guide

Guide for maintainers and AI coding assistants. `AGENTS.md` is a symlink to this file.
**Keep it current:** when a decision is made or a rule changes, update the relevant section
and add an entry to the [Decision log](#decision-log) in the same commit.

## Purpose & users

A datastore of standardised, ready-to-chart boundary files (TopoJSON), mainly UK, plus key
international ones and teaching examples (e.g. New York). Files are loaded straight from
GitHub raw URLs into **Vega-Lite / Altair**, so every file must work with
`format: {type: "topojson", feature: "geog"}` and no further processing.

Users:
- Professional chart makers (Economics Observatory, LSE Growth Lab).
- Data science / dataviz teaching, including LSE students on a data visualisation for
  policymaking course. Assume users are **not GIS specialists**. Prefer simple, predictable
  files over clever ones.

Goals:
1. Cover the commonly used boundaries.
2. Standardise them: one projection, consistent property names, sensible file size, TopoJSON.
3. UK statistics are published on inconsistent geography vintages, so publish **each
   version** (e.g. every LAD release), not just the latest.
4. Paths should feel like querying an API: change one part of the filename to get a
   different geography, coverage or date.

## Layout

```
gbr/                 UK boundaries, standard resolution (charting whole UK / nations)
gbr/full/            UK boundaries near full resolution, plus `area` (m²), for zooming / subsetting
gbr/lookups/         CSV lookups (child → parent areas), named after the boundary file they match
gbr/areas/           One file per GSS code (LAD, CTYUA counties), latest version, + index.csv
gbr/README.md        User guide to filtering UK files (nations, lookups, Altair/Vega-Lite snippets)
gbr/sa/<slug>/       One folder per English Strategic Authority: SA, LAD, MSOA, LSOA files
gbr/cities/london/   London subsets (legacy naming, see Known issues)
usa/, usa/cities/nyc/  US states, counties, NYC (hand-made, not from pipeline)
world/               World countries (Natural Earth, hand-made)
metadata/            One JSON per pipeline output, mirroring the data path
                     (gbr/full/X.json → metadata/gbr/full/X.json); gbr/areas/ has one
                     shared file, metadata/gbr/areas.json
scripts/             ONS fetch + process pipeline (see below)
examples/            Altair / Vega-Lite snippets and view_map.py previewer
raw/                 Pipeline cache: ONS catalog CSV, raw GeoJSON downloads, and
                     raw/areas/ (code lists, unpublished older sources) (git-ignored)
```

## Design rules

### Every TopoJSON file
- Single object named **`geog`**. (Exception: `usa/` files also include `states` / `nation` meshes.)
- Coordinates in **WGS84** (lon/lat), quantised TopoJSON. Users set the projection in the chart.
- Properties: **`id`** (official code, e.g. GSS `E06000001`, ITL `TLC`) and **`name`**.
  Add other properties only when they serve a purpose, with short lowercase names.
- **Valid polygons (OGC/GEOS rules)**, so GIS operations (union, dissolve, overlay) work
  without `make_valid`. Every script that writes TopoJSON uses mapshaper `-o ... fix-geometry`
  and then `scripts.validate.repair_file()`. `uv run python -m scripts.validate` must
  report no invalid features before committing data.
  - Repair rewrites only the invalid features with shapely `make_valid(method="linework")`,
    snap-rounded onto the file's existing grid. All other features keep their arcs.
  - Never use mapshaper `-clean` on published files. It dropped and emptied features and
    crashed on full LSOA.
- `gbr/full/` files also carry **`area`** in m². **Always take area from the
  full-resolution (BFC) source**, never from simplified geometry, so it is the most
  correct value available. Normally this is ONS `Shape__Area` (calculated on the BFC in
  British National Grid), passed through unchanged. The pipeline checks every source's area
  field against its geometry in EPSG:27700. If the median ratio is more than 2% from 1
  (square degrees in WGS84 re-publishes such as LAD Dec 2016, Web Mercator m² in LAD Dec
  2019), it computes area from the unsimplified geometry in EPSG:27700 instead. This is
  within about 0.02% of ONS values.

### File naming (UK)
`{PREFIX}_{COVERAGE}_{YEAR}[_{MM}].json`
- `PREFIX`: geography code. `LAD` (lower tier), `CTYUA` (upper tier), `CAUTH`, `SA`, `LSOA`, `MSOA`, `ITL1-3`, `NUTS1-3`, `CTRY`,
  `ELE_MP` (Westminster constituencies; ONS calls these PCON).
- `COVERAGE`: `UK`, `GB`, `EW`, `ENG`, `WLS`, `SCT`, `NIR`.
- `_{MM}` is added only for geographies that ONS releases more than once a year (LAD, CTYUA,
  CAUTH, PCON). Use the ONS vintage month (e.g. `_05` May, `_12` December).
- Same filename in `gbr/` and `gbr/full/` means the same vintage at two resolutions.
- Nation subsets swap the coverage code (`LAD_UK_2025_12` → `LAD_WLS_2025_12`). Each one is
  an exact filter of its source file by the first letter of the GSS code (E/W/S/N). They
  are built by `scripts/subsets.py`, and their metadata records the source file.

### Lookups (`gbr/lookups/*.csv`)
- Named after the boundary file whose `id`s they match, with one row per child area.
- Columns are `{level}_id` / `{level}_name` in lowercase (`lad`, `ctyua`, `ctry`, `rgn`, `cauth`,
  `itl1`…, `lsoa`, `msoa`). Leave a value blank where the level doesn't exist (e.g. `rgn`
  outside England).
- Sources are ONS lookups with item ids pinned in `scripts/lookups.py`. Every child must
  map to exactly one parent. Where ONS data doesn't nest, resolve it with an explicit,
  commented best-fit override (e.g. North Ayrshire → ITL3 TLM93).
- Builds check the lookup against the boundary file's ids and fail on any mismatch.

### Local authority tiers
- `LAD` is the lower tier (districts plus single-tier councils). `CTYUA` is the upper tier
  (21 English counties `E10…` plus the same single-tier councils). A single-tier council
  has the same code and area at both tiers, so only `E07` districts and `E10` counties differ.
- The LAD lookup's `ctyua_*` columns map each LAD to its upper-tier authority (itself if
  single tier). Most ONS data is lower tier; county-run services (DfE, OHID, social care)
  are often upper tier.

### Per-area files (`gbr/areas/{code}.json`)
- One file per GSS code ever seen in an ONS LAD or CTYUA **BFC** release since 2009:
  `E10` codes from CTYUA, all others from LAD. `index.csv` lists `id`, `name`, `tier`
  (`lower`/`upper`/`both`), `current`, `release`, `area`.
- **Latest wins.** Each file holds the newest release that contains its code, and is
  updated in place when ONS revises the geometry. Retired codes keep their last release.
  Never add version folders here; users who need a specific release filter the dated file.
- Files are **exact extracts** of a full-resolution file (arcs and quantisation grid
  copied unchanged, via `scripts/areas.py:extract`), so they overlay `gbr/full/` exactly
  and inherit its validity and ONS `area`. Current codes come from the `gbr/full/` files in
  `CURRENT_SOURCES`; older releases are built by the pipeline into `raw/areas/sources/`
  and not published.
- When a new LAD or CTYUA BFC release is published, update `CURRENT_SOURCES` and rerun
  `scripts.areas`.

### Resolution & size
- `gbr/`: built from ONS **BGC** (generalised, clipped to coastline). Target: whole-UK file
  under about 1 MB for LAD-scale, under about 10 MB for LSOA-scale.
- `gbr/full/`: built from ONS **BFC** (full, clipped), usually simplified to 50%. Keep every
  file **under 50 MB** (GitHub warns above 50 MB and rejects files over 100 MB). Lower the
  percentage for large geographies (LSOA uses 25%).
- When changing a percentage, compare before and after by rendering whole-UK and zoomed
  subsets (a city and a rural coastline) in Altair. Then use `pipeline rebuild` on the
  published files.
- Simplification: mapshaper `visvalingam weighted keep-shapes`. The percentage for each type
  is set in `scripts/config.py`.

### Changing published files
Files are linked from teaching materials and published charts by raw URL. **Never rename,
move or delete a published file** without a deliberate decision recorded below. Fixing data
in place (same path) is fine.

## Pipeline (`scripts/`)

Requires `uv` and `mapshaper` (npm, tested with 0.7.25).

```bash
uv run python -m scripts.pipeline catalog [--refresh]   # cache ONS catalog (raw/catalog/)
uv run python -m scripts.pipeline search LAD_BFC        # list ONS versions; ✓ = already built
uv run python -m scripts.pipeline process LAD           # build latest version
uv run python -m scripts.pipeline process LAD --count 3 # build up to 3 missing versions
uv run python -m scripts.pipeline process LAD --version UK_2021_05  # one specific version
uv run python -m scripts.pipeline process LAD --all [--force]
uv run python -m scripts.pipeline rebuild gbr/LAD_UK_2025_12.json  # re-process a published
                                                    # file from its metadata (current config)
uv run python -m scripts.subsets                         # nation subsets (SUBSET_SOURCES)
uv run python -m scripts.lookups                         # lookup CSVs (gbr/lookups/)
uv run python -m scripts.areas [--plan]                  # per-area files (gbr/areas/)
uv run python -m scripts.validate [--repair] [files]    # polygon validity (default: all files)
uv run python examples/view_map.py gbr/LAD_UK_2025_12.json   # preview in browser
```

Flow:
1. `catalog.py` downloads the ArcGIS Hub CSV of everything on geoportal.statistics.gov.uk.
2. `fetch.py` filters it using the title keywords and edition (`BGC`/`BFC`) from config.
   Then it pages through the ArcGIS Feature Service query API to get GeoJSON, saved as
   `raw/downloads/{item_id}.geojson` (resumable, cached).
3. `process.py` uses mapshaper to: rename the layer to `geog`, simplify, rename the
   code/name fields to `id`/`name`, keep only the configured fields, project to WGS84 and
   write TopoJSON.
4. `pipeline.py` writes `metadata/<data path>` with the source item, fields, settings and
   sizes.

To add a boundary type, add an entry to `BOUNDARY_CONFIGS` in `scripts/config.py`.
Use a `_BFC` suffix with `output_dir: "gbr/full"` for the high-resolution variant. Run
`search` first to check the title matching, then `process`. Use `--all` deliberately: it
builds every historic version ONS lists.

## Known issues / legacy
- Falls Church in `usa/counties_2017.json` has no geometry. Its shape collapsed in the
  hand-made file, and the repair can't recreate it. `scripts.validate` reports it.
- Files made before the current pipeline (no `metadata/` entry) were made with a lost
  pipeline, partly by hand. Examples are older `LAD_UK_2021_12`…`2024_05`, ITL, NUTS, LSOA,
  MSOA, CTRY and ELE_MP. Some ITL files came from BUC (ultra-generalised) sources.
- `gbr/LAD_UK_2021.json` uses `AREACD`/`AREANM` properties. It is a legacy duplicate of
  `LAD_UK_2021_12.json` and is kept so existing links keep working.
- `CTRY_GB-ENG` style nation names differ from the `ENG`/`WLS` coverage codes used elsewhere.
- `gbr/cities/london/` and `usa/` / `world/` don't follow the UK naming scheme.

## Decision log
Newest first. Record what was decided and why.

- **2026-11-09** Added upper-tier authorities: `CTYUA_UK_2025_12` (standard 8%, same as
  LAD; full 50%), `CTYUA_ENG_2025_12`, and `ctyua_id`/`ctyua_name` in the LAD lookup.
  Many county-run services publish upper-tier data, and LAD alone couldn't map it. The
  prefix follows ONS (`CTYUA`), not the health-data terms UTLA/LTLA. The "inc Metropolitan
  Counties" catalog variant is excluded because it would overwrite the same filename.
  Grouped LTLAs (Cornwall + Scilly, Hackney + City) are not published.
- **2026-11-09** Area units are now checked by geometry, not by guessing from the first
  value. LAD Dec 2019 BFC reports `Shape__Area` in Web Mercator m² (about 2.6× too large
  in England), which the old sub-1 "square degrees" test missed. It is used only for the
  four Buckinghamshire districts in `gbr/areas/`. Every other source matches geodesic
  area to within 0.4%.
- **2026-11-09** Added `gbr/areas/{code}.json`, one file per LAD/CTYUA code, cut from
  full-resolution files so `area` is ONS `Shape__Area`. It uses one flat folder by code
  (codes are unique across geographies) and **latest wins**, not version folders, to
  avoid hundreds of near-identical copies per release. Retired codes are included, from
  their last BFC release, so data on old codes still has a shape. One shared metadata
  file replaces about 440 per-file ones.
- **2026-11-09** **Same code ≠ same geometry.** GSS policy gives a new code for a legal
  boundary change, and never for a rename. But ONS redraws geometry under unchanged codes:
  303 of 346 LAD codes kept from Dec 2016 to Dec 2023 changed area, mostly coastline
  remaps (Lancaster −9.3 km², Wirral +3.9 km²). Dec 2025 → May 2026 changed 36, including
  about 0.16 km² moving from Bristol to North Somerset. A code identifies the same area
  for joining data; dated files are still needed for exact geometry.

- **2026-10-29** All published polygons must be valid, and are now: 0 invalid features
  across every file. There were two causes:
  1. **Quantisation.** Rounding to the TopoJSON grid pinches narrow necks and coastlines.
     The raw ONS sources are valid, and so is unquantised output.
  2. **Holes written as outer parts.** ArcGIS's GeoJSON export, and some older files,
     write holes as extra outer parts ("nested shells"). Charts drew those holes filled,
     e.g. South Cambridgeshire over Cambridge in LAD Dec 2018, and Gateshead 005 over its
     neighbour. ONS `Shape__Area` always matches the hole reading.

  The fix is `fix-geometry` on output, then a targeted, grid-preserving repair
  (`scripts/validate.py`). mapshaper `-clean` was rejected: it dropped 2 MSOAs and emptied
  another. All pipeline files were rebuilt, and all legacy files repaired in place.
  `gbr/LSOA_EW_2021.json` and `LSOA_EW_2011.json` were rebuilt through the pipeline (BGC
  20%), because Bolton 018A had collapsed to nothing in both legacy files. Snap on import adds a few pinches, but the
  repair handles them, so it stays for the arc-sharing benefit.
- **2026-10-29** Older LAD nation subsets are published only at **code-change points**, one
  per distinct set of codes for each nation (see the `SUBSET_SOURCES` comment). These were
  found by comparing the codes in every ONS LAD release. Wales and NI have had no code
  changes, so only the latest is published. Added UK LAD May 2026, May 2021, Dec 2018 and
  Dec 2016 (standard), and May 2026 (full).
- **2026-10-29** Catalog titles containing `(WGS84)`, `(Parts)` or `Census Merged` are
  excluded (`TITLE_EXCLUDE`). WGS84 re-publishes have area in square degrees, and the BNG
  original exists, so `gbr/full/LAD_UK_2016_12.json` was rebuilt from it and now uses ONS area.
  The other two would overwrite real files with the same name.
- **2026-10-29** mapshaper imports use `snap`. LAD May 2021 BGC has borders that don't
  quite meet, which gave 10× the arcs (0.99 MB vs 0.41 MB) and unrepairable intersections.
  On clean sources snap moves only a handful of points.
- **2026-10-29** Added English Strategic Authorities (`SA_ENG_2025_12`, standard and full,
  `gbr/sa/<slug>/` drill-down folders, `lookups/SA_ENG_2025_12.csv`, and `sa_id`/`sa_name`
  in the LAD lookup). SAs are not an ONS geography and ONS `CAUTH` omits six of them, so
  they are dissolved from published files (`scripts/strategic_authorities.py`): national
  files from the LAD files, so borders match them exactly; each folder from the full LSOAs,
  dissolved to MSOA, LAD and SA, so its four files overlay exactly (checked: 0 m of border
  off the LSOA borders). Membership and attributes come from the msa-data repo
  (`scripts/inputs/`). `id` is our `MSA0xx` code (no ONS code exists); the prefix is `SA`,
  not `MSA`, because two of the 21 have no mayor. Folders are one file per layer, not a
  multi-object file, to keep the single-`geog` rule.
- **2026-10-29** Added a filtering guide (`gbr/README.md`), nation subsets (exact filters of
  the UK/EW file, not re-simplified, so geometry is identical) and lookup CSVs for LAD Dec
  2025 and LSOA 2021. This supports teaching on devolved nations and authorities.
  Lookups are CSV (not merged into the TopoJSON) to keep boundary files minimal and to
  work with both pandas and the Vega-Lite `lookup` transform.
- **2026-10-29** `gbr/full/LSOA_EW_2021.json` simplified at 25% instead of 50% (82 MB → 46 MB).
  This keeps it under GitHub's 50 MB warning, with no visible difference at borough zoom.
- **2026-10-29** BGC LAD simplification lowered from 20% to 8% (0.88 MB → 0.41 MB). The
  older hand-made files are about 5%, but 5% looks angular when zoomed to a city region,
  and nation-level charts are a key teaching use.
- **2026-10-29** Metadata path mirrors the data path (`metadata/gbr/full/…`, previously
  `metadata/full/…`). This avoids collisions if other countries gain `full/` folders.
- **2026-10-29** `area` must be m². If ONS `Shape__Area` is in square degrees, compute it
  from geometry in EPSG:27700. This fixed `gbr/full/LAD_UK_2016_12.json`, which had
  degree² values.
- **2026-06** Added the `gbr/full/` tier: BFC sources at 50% simplification with ONS
  `area`. Its purpose is to let users subset small areas at good resolution and to give
  exact land areas for density calculations.
- **2026-06** Rebuilt the ONS pipeline (`scripts/`) after the original was lost. Source is
  the ArcGIS Hub catalog CSV plus the Feature Service query API.
- Earlier: all files use the `geog` object key and `id`/`name` properties.
