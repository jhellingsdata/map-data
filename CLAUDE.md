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
gbr/README.md        User guide to filtering UK files (nations, lookups, Altair/Vega-Lite snippets)
gbr/cities/london/   London subsets (legacy naming, see Known issues)
usa/, usa/cities/nyc/  US states, counties, NYC (hand-made, not from pipeline)
world/               World countries (Natural Earth, hand-made)
metadata/            One JSON per pipeline output, mirroring the data path
                     (gbr/full/X.json → metadata/gbr/full/X.json)
scripts/             ONS fetch + process pipeline (see below)
examples/            Altair / Vega-Lite snippets and view_map.py previewer
raw/                 Pipeline cache: ONS catalog CSV + raw GeoJSON downloads (git-ignored)
```

## Design rules

### Every TopoJSON file
- Single object named **`geog`**. (Exception: `usa/` files also include `states` / `nation` meshes.)
- Coordinates in **WGS84** (lon/lat), quantised TopoJSON. Users set the projection in the chart.
- Properties: **`id`** (official code, e.g. GSS `E06000001`, ITL `TLC`) and **`name`**.
  Add other properties only when they serve a purpose, with short lowercase names.
- `gbr/full/` files also carry **`area`** in m². **Always take area from the
  full-resolution (BFC) source**, never from simplified geometry, so it is the most
  correct value available. Normally this is ONS `Shape__Area` (calculated on the BFC in
  British National Grid), passed through unchanged. If a source reports area in square degrees (WGS84 re-publishes,
  e.g. LAD Dec 2016), the pipeline computes it from geometry in EPSG:27700 instead. This is
  within about 0.02% of ONS values.

### File naming (UK)
`{PREFIX}_{COVERAGE}_{YEAR}[_{MM}].json`
- `PREFIX`: geography code. `LAD`, `CAUTH`, `LSOA`, `MSOA`, `ITL1-3`, `NUTS1-3`, `CTRY`,
  `ELE_MP` (Westminster constituencies; ONS calls these PCON).
- `COVERAGE`: `UK`, `GB`, `EW`, `ENG`, `WLS`, `SCT`, `NIR`.
- `_{MM}` is added only for geographies that ONS releases more than once a year (LAD, CAUTH,
  PCON). Use the ONS vintage month (e.g. `_05` May, `_12` December).
- Same filename in `gbr/` and `gbr/full/` means the same vintage at two resolutions.
- Nation subsets swap the coverage code (`LAD_UK_2025_12` → `LAD_WLS_2025_12`). Each one is
  an exact filter of its source file by the first letter of the GSS code (E/W/S/N). They
  are built by `scripts/subsets.py`, and their metadata records the source file.

### Lookups (`gbr/lookups/*.csv`)
- Named after the boundary file whose `id`s they match, with one row per child area.
- Columns are `{level}_id` / `{level}_name` in lowercase (`lad`, `ctry`, `rgn`, `cauth`,
  `itl1`…, `lsoa`, `msoa`). Leave a value blank where the level doesn't exist (e.g. `rgn`
  outside England).
- Sources are ONS lookups with item ids pinned in `scripts/lookups.py`. Every child must
  map to exactly one parent. Where ONS data doesn't nest, resolve it with an explicit,
  commented best-fit override (e.g. North Ayrshire → ITL3 TLM93).
- Builds check the lookup against the boundary file's ids and fail on any mismatch.

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
uv run python -m scripts.pipeline process LAD --all [--force]
uv run python -m scripts.pipeline rebuild gbr/LAD_UK_2025_12.json  # re-process a published
                                                    # file from its metadata (current config)
uv run python -m scripts.subsets                         # nation subsets (SUBSET_SOURCES)
uv run python -m scripts.lookups                         # lookup CSVs (gbr/lookups/)
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
- Files made before the current pipeline (no `metadata/` entry) were made with a lost
  pipeline, partly by hand. Examples are older `LAD_UK_2021_12`…`2024_05`, ITL, NUTS, LSOA,
  MSOA, CTRY and ELE_MP. Some ITL files came from BUC (ultra-generalised) sources.
- `gbr/LAD_UK_2021.json` uses `AREACD`/`AREANM` properties. It is a legacy duplicate of
  `LAD_UK_2021_12.json` and is kept so existing links keep working.
- `CTRY_GB-ENG` style nation names differ from the `ENG`/`WLS` coverage codes used elsewhere.
- `gbr/cities/london/` and `usa/` / `world/` don't follow the UK naming scheme.

## Decision log
Newest first. Record what was decided and why.

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
