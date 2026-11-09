"""
Build English Strategic Authority (SA) maps, one per status snapshot, and per-SA drill-downs.

Usage:
    uv run python -m scripts.strategic_authorities

SAs are not an ONS geography, and ONS's CAUTH files leave out the GLA and the areas
without a combined authority code. So SAs are built here by dissolving published LAD
files, which keeps every border identical to the source.

Maps (`MAPS`): each is one snapshot date and one kind:

* current: the SAs legally in force on the date, in `gbr/` and `gbr/full/`;
* proposed: every SA with a status on the date (current, agreed, proposed, named),
  minus those being replaced by a new footprint, in `gbr/proposed/` and
  `gbr/proposed/full/`.

Each map gets a standard file dissolved from `gbr/LAD_UK_{lad}.json`, a full file
dissolved from `gbr/full/LAD_UK_{lad}.json` (keeping `area`, summed from the BFC LAD
areas), and a lookup CSV with one row per SA (`gbr/[proposed/]lookups/SA_ENG_{date}.csv`).
`lad` is the LAD release in force on the snapshot date (`LAD_VINTAGE`).

Per-SA folders (`gbr/sa/<slug>/{SA,LAD,MSOA,LSOA}.json`) cover the SAs on the
`FOLDER_MAP` map. Each is cut from gbr/full/LSOA_EW_2021.json and dissolved up to MSOA,
LAD and SA, so the four files overlay exactly.

Inputs (scripts/inputs/, written by `msa geographies export-map-data` in the msa-data
repo, which maintains the register):

* strategic_authorities.csv: one row per SA code (MSA001…), with parent areas and
  founding facts (gss_id, established_from, mayor_from, body_id, replaces, research_set).
* strategic_authorities_lads.csv: lad_id, lad_name, sa_id, sa_name, for every SA code. A
  LAD can sit in several codes (East Devon in MSA018 and MSA031), never two on one map.
* strategic_authority_status.csv: snapshot, sa_id, status, tier, planned_tier,
  replaced_by. One row per SA with a status on each snapshot date.

`cty_id` is derived here: the county (E10, current or retired) or metropolitan county
(E11) whose LADs are exactly the SA's.
"""

import json
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from shapely.geometry import shape

from scripts.fetch import HEADERS, get_item_service_url, get_layer_id
from scripts.process import _count_features
from scripts.validate import _decode, repair_file

INPUTS = Path("scripts/inputs")
AUTHORITIES = INPUTS / "strategic_authorities.csv"
SA_LADS = INPUTS / "strategic_authorities_lads.csv"
STATUS = INPUTS / "strategic_authority_status.csv"
METADATA_DIR = Path("metadata")
CACHE = Path("raw/sa")

# Snapshot date → the LAD release in force on it (LAD codes are the same in Dec 2025 and
# May 2026, so the 2026 maps use the newer geometry).
LAD_VINTAGE = {"2025_12": "2025_12", "2026_07": "2026_05", "2026_10": "2026_05"}
# (snapshot, proposed?). No current map for 2026_10: its SAs are the 2026_07 ones.
MAPS = [("2025_12", False), ("2025_12", True), ("2026_07", False), ("2026_07", True), ("2026_10", True)]
FOLDER_MAP = ("2025_12", True)  # the 21 research-set SAs plus the GLA

# Properties in the boundary files; the lookup CSVs carry these and more.
SA_FIELDS = [
    "name", "short", "status", "tier", "planned_tier", "gss_id", "cty_id",
    "established_from", "mayor_from", "rgn_id", "itl1_id", "itl2_id", "itl2_2021_id",
]
NUMBER_FIELDS = {"mayor_from"}

LSOA_SOURCE = Path("gbr/full/LSOA_EW_2021.json")
LSOA_LOOKUP = Path("gbr/lookups/LSOA_EW_2021.csv")
LAD_LOOKUP = Path("gbr/lookups/LAD_UK_2025_12.csv")

# Metropolitan counties (E11): ONS publishes their shapes only in the Dec 2022 upper-tier
# file that swaps the 36 metropolitan districts for the 6 counties. Codes are checked
# against the current names-and-codes list.
MCTY_SHAPES = "d173a7c071d8455eaa4b7f31b9bc60c2"  # CTYUA inc Metropolitan Counties (Dec 2022) BGC
MCTY_CODES = "03f1c4d7f89c4f77aab544a8dfd5a5d8"  # Metropolitan Counties (Dec 2025) Names and Codes
COUNTY_AREA_TOLERANCE = 0.01  # an exact LAD match must also agree on area


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(f"mapshaper failed:\n{' '.join(cmd)}\n{result.stderr}")


def _ids(path: Path) -> dict[str, str]:
    topo = json.loads(path.read_text())
    return {g["properties"]["id"]: g["properties"]["name"] for g in topo["objects"]["geog"]["geometries"]}


def slug(sa_id: str, name: str) -> str:
    """MSA016 + Cumbria → msa016_cumbria"""
    return f"{sa_id.lower()}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}"


def map_path(snapshot: str, proposed: bool, full: bool = False, kind: str = "boundary") -> Path:
    """gbr/[proposed/][full/|lookups/]SA_ENG_{snapshot}.json|csv"""
    root = Path("gbr/proposed") if proposed else Path("gbr")
    if kind == "lookup":
        return root / "lookups" / f"SA_ENG_{snapshot}.csv"
    return (root / "full" if full else root) / f"SA_ENG_{snapshot}.json"


def _report_repairs(out: Path) -> None:
    """Dissolving and re-quantising can create invalid polygons; repair any (scripts/validate.py)."""
    repaired = repair_file(out)
    if repaired:
        print(f"    repaired {len(repaired)} invalid in {out}: {[k for k, _ in repaired][:5]}")


def _write_metadata(out: Path, sources: list[Path], processing: dict) -> None:
    size_mb = out.stat().st_size / 1e6
    meta = {
        "source": {"files": [str(s) for s in sources], "inputs": [str(AUTHORITIES), str(SA_LADS), str(STATUS)]},
        "processing": {**processing, "processed": date.today().isoformat()},
        "output": {
            "file": str(out),
            "format": "topojson",
            "objects_key": "geog",
            "feature_count": _count_features(out),
            "output_size_mb": round(size_mb, 3),
        },
    }
    path = METADATA_DIR / out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2))


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    authorities = pd.read_csv(AUTHORITIES, dtype=str, keep_default_na=False)
    authorities["n_lads"] = authorities["n_lads"].astype(int)
    lads = pd.read_csv(SA_LADS, dtype=str)
    status = pd.read_csv(STATUS, dtype=str, keep_default_na=False)
    return authorities, lads, status


def map_status(status: pd.DataFrame, snapshot: str, proposed: bool) -> pd.DataFrame:
    """Status rows of the SAs on one map."""
    s = status[status["snapshot"] == snapshot]
    s = s[s["replaced_by"] == ""] if proposed else s[s["status"] == "current"]
    if s.empty:
        raise ValueError(f"no SAs for snapshot {snapshot}")
    return s.reset_index(drop=True)


def map_members(lads: pd.DataFrame, status: pd.DataFrame, snapshot: str, proposed: bool) -> pd.DataFrame:
    """(lad_id, sa_id) rows of one map; each LAD in at most one SA."""
    members = lads[lads["sa_id"].isin(map_status(status, snapshot, proposed)["sa_id"])]
    dup = members[members["lad_id"].duplicated(keep=False)]
    if not dup.empty:
        raise ValueError(f"{snapshot} {'proposed' if proposed else 'current'}: LADs in two SAs:\n{dup}")
    return members.reset_index(drop=True)


def _check_inputs(authorities: pd.DataFrame, lads: pd.DataFrame, status: pd.DataFrame) -> None:
    for vintage in set(LAD_VINTAGE.values()):
        unknown = set(lads["lad_id"]) - set(_ids(Path(f"gbr/LAD_UK_{vintage}.json")))
        if unknown:
            raise ValueError(f"SA member LADs not in LAD_UK_{vintage}: {sorted(unknown)}")
    counts = lads.groupby("sa_id").size()
    expected = authorities.set_index("id")["n_lads"]
    if not counts.reindex(expected.index).eq(expected).all():
        raise ValueError(f"member LAD counts disagree with n_lads:\n{counts}\n{expected}")
    unknown = set(status["sa_id"]) - set(authorities["id"])
    if unknown:
        raise ValueError(f"status rows for unknown SAs: {sorted(unknown)}")
    if set(status["snapshot"]) != set(LAD_VINTAGE):
        raise ValueError(f"status snapshots {sorted(set(status['snapshot']))} != {sorted(LAD_VINTAGE)}")


# ---------------------------------------------------------------------------
# County matches (cty_id)
# ---------------------------------------------------------------------------


def _query_url(item_id: str) -> str:
    service = get_item_service_url(item_id)
    return f"{service}/{get_layer_id(service)}/query"


def _metropolitan_counties() -> dict[str, tuple[str, dict]]:
    """{E11 code: (name, GeoJSON geometry)}, cached in raw/sa/."""
    cache = CACHE / "mcty_2022_12_bgc.geojson"
    if not cache.exists():
        resp = requests.get(_query_url(MCTY_SHAPES), headers=HEADERS, timeout=120, params={
            "where": "UTLA22CD LIKE 'E11%'", "outFields": "UTLA22CD,UTLA22NM",
            "returnGeometry": "true", "outSR": 4326, "f": "geojson",
        })
        resp.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(resp.text)
    features = json.loads(cache.read_text())["features"]
    shapes = {f["properties"]["UTLA22CD"]: (f["properties"]["UTLA22NM"], f["geometry"]) for f in features}

    codes_cache = CACHE / "mcty_2025_12_codes.json"
    if not codes_cache.exists():
        resp = requests.get(_query_url(MCTY_CODES), headers=HEADERS, timeout=60,
                            params={"where": "1=1", "outFields": "*", "f": "json"})
        resp.raise_for_status()
        codes_cache.write_text(resp.text)
    current = {f["attributes"]["MCTY25CD"]: f["attributes"]["MCTY25NM"]
               for f in json.loads(codes_cache.read_text())["features"]}
    if {k: v[0] for k, v in shapes.items()} != current:
        raise ValueError(f"E11 shapes (Dec 2022) differ from the Dec 2025 code list: {current}")
    return shapes


def county_matches(lads: pd.DataFrame) -> pd.DataFrame:
    """sa_id → cty_id, cty_name where one county's LADs are exactly the SA's.

    Counties are every E10 file in gbr/areas/ (current and retired) and the six E11
    metropolitan counties. A LAD belongs to a county if its interior point lies inside
    it. E10 matches must also agree with the county's ONS area to within 1%.
    """
    lad_file = Path(f"gbr/full/LAD_UK_{LAD_VINTAGE['2026_10']}.json")
    lad_features = _decode(lad_file)["features"]
    points = {f["properties"]["id"]: shape(f["geometry"]).representative_point() for f in lad_features}
    lad_area = {f["properties"]["id"]: f["properties"]["area"] for f in lad_features}

    index = pd.read_csv("gbr/areas/index.csv", dtype={"id": str, "name": str})
    counties = {}  # code → (name, geometry, ONS area or None)
    for r in index[index["id"].str.startswith("E10")].itertuples():
        geom = _decode(Path(f"gbr/areas/{r.id}.json"))["features"][0]["geometry"]
        counties[r.id] = (r.name, shape(geom), r.area)
    for code, (name, geom) in _metropolitan_counties().items():
        counties[code] = (name, shape(geom), None)

    county_lads = {code: frozenset(l for l, p in points.items() if g.contains(p))
                   for code, (_, g, _) in counties.items()}
    rows = []
    for sa_id, group in lads.groupby("sa_id"):
        own = frozenset(group["lad_id"])
        hits = [c for c, members in county_lads.items() if members == own]
        if len(hits) > 1:
            raise ValueError(f"{sa_id} matches several counties: {hits}")
        if not hits:
            continue
        code = hits[0]
        name, _, area = counties[code]
        if area is not None:
            ratio = sum(lad_area[l] for l in own) / area
            if abs(ratio - 1) > COUNTY_AREA_TOLERANCE:
                print(f"  {sa_id} has {code}'s LADs but area ratio {ratio:.4f}; not matched")
                continue
        rows.append({"sa_id": sa_id, "cty_id": code, "cty_name": name})
    return pd.DataFrame(rows, columns=["sa_id", "cty_id", "cty_name"])


# ---------------------------------------------------------------------------
# National files
# ---------------------------------------------------------------------------


def map_attributes(authorities: pd.DataFrame, status: pd.DataFrame, counties: pd.DataFrame) -> pd.DataFrame:
    """One row per SA on a map: register fields + status on the date + county match."""
    a = authorities.rename(columns={"id": "sa_id"})
    s = status[["sa_id", "status", "tier", "planned_tier"]]
    return s.merge(a, on="sa_id", how="left").merge(counties, on="sa_id", how="left").fillna("")


def build_national(out: Path, source: Path, attrs: Path, members: Path, keep_area: bool, note: str) -> Path:
    fields = ["id", *SA_FIELDS] + (["area"] if keep_area else [])
    strings = [f for f in SA_FIELDS if f not in NUMBER_FIELDS]
    cmd = [
        "mapshaper", str(source),
        "-join", str(members), "keys=id,lad_id", "fields=sa_id", "string-fields=lad_id,sa_id",
        "-filter", "sa_id != null && sa_id !== ''",
        "-dissolve", "sa_id", *(["calc=area=sum(area)"] if keep_area else []),
        "-join", str(attrs), "keys=sa_id,sa_id", f"fields={','.join(SA_FIELDS)}",
        f"string-fields=sa_id,{','.join(strings)}",
        "-rename-fields", "id=sa_id",
        "-filter-fields", ",".join(fields),
        "-rename-layers", "geog",
        "-o", str(out), "format=topojson", "fix-geometry",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(cmd)
    _report_repairs(out)
    _write_metadata(
        out,
        [source],
        {"map": note, "method": "dissolve member LADs by sa_id (no further simplification)", "fields": fields},
    )
    print(f"  {_count_features(out):>3} SAs  {out.stat().st_size / 1e6:6.2f} MB → {out}")
    return out


def build_sa_lookup(attrs: pd.DataFrame, out: Path) -> Path:
    """One row per SA on a map: status, founding facts, parent and matching areas."""
    lad = pd.read_csv(LAD_LOOKUP, dtype=str)
    rgn = dict(zip(lad["rgn_id"], lad["rgn_name"]))
    itl1 = dict(zip(lad["itl1_id"], lad["itl1_name"]))
    itl2 = dict(zip(lad["itl2_id"], lad["itl2_name"]))
    cauth = dict(zip(lad["cauth_id"], lad["cauth_name"]))
    itl2_2021 = _ids(Path("gbr/ITL2_UK_2021.json"))

    def names(codes: pd.Series, table: dict) -> pd.Series:
        return codes.fillna("").map(lambda c: ";".join(table.get(x, "") for x in c.split(";")) if c else "")

    a = attrs
    df = pd.DataFrame(
        {
            "sa_id": a["sa_id"],
            "sa_name": a["name"],
            "sa_short": a["short"],
            "status": a["status"],
            "tier": a["tier"],
            "planned_tier": a["planned_tier"],
            "gss_id": a["gss_id"],
            "cty_id": a["cty_id"],
            "cty_name": a["cty_name"],
            "established_from": a["established_from"],
            "mayor_from": a["mayor_from"],
            "body_id": a["body_id"],
            "replaces": a["replaces"],
            "research_set": a["research_set"],
            "ctry_id": "E92000001",
            "ctry_name": "England",
            "rgn_id": a["rgn_id"],
            "rgn_name": names(a["rgn_id"], rgn),
            "itl1_id": a["itl1_id"],
            "itl1_name": names(a["itl1_id"], itl1),
            "cauth_id": a["cauth_id"],
            "cauth_name": names(a["cauth_id"], cauth),
            "itl2_id": a["itl2_id"],
            "itl2_name": names(a["itl2_id"], itl2),
            "itl2_2021_id": a["itl2_2021_id"],
            "itl2_2021_name": names(a["itl2_2021_id"], itl2_2021),
            "n_lads": a["n_lads"],
        }
    ).sort_values("sa_id")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"  {len(df)} rows → {out}")
    return out


def build_map(snapshot: str, proposed: bool, authorities, lads, status, counties, tmp: Path) -> None:
    kind = "proposed" if proposed else "current"
    vintage = LAD_VINTAGE[snapshot]
    s = map_status(status, snapshot, proposed)
    attrs = map_attributes(authorities, s, counties)
    members = map_members(lads, status, snapshot, proposed)
    attrs_csv, members_csv = tmp / f"{snapshot}_{kind}_attrs.csv", tmp / f"{snapshot}_{kind}_lads.csv"
    attrs.to_csv(attrs_csv, index=False)
    members[["lad_id", "sa_id"]].to_csv(members_csv, index=False)

    tiers = s[s["status"] == "current"]["tier"].value_counts().to_dict()
    print(f"{snapshot} {kind}: {len(s)} SAs ({dict(s['status'].value_counts())}; current tiers {tiers})")
    note = f"{kind} SAs on {snapshot}, LAD boundaries {vintage}"
    for full in (False, True):
        source = Path("gbr/full" if full else "gbr") / f"LAD_UK_{vintage}.json"
        build_national(map_path(snapshot, proposed, full), source, attrs_csv, members_csv, full, note)
    build_sa_lookup(attrs, map_path(snapshot, proposed, kind="lookup"))


# ---------------------------------------------------------------------------
# Per-SA drill-down files
# ---------------------------------------------------------------------------


def _lsoa_table(members: pd.DataFrame) -> pd.DataFrame:
    """LSOA → MSOA → LAD → SA, checking every LSOA and MSOA sits in one SA."""
    lsoa = pd.read_csv(LSOA_LOOKUP, dtype=str).merge(members[["lad_id", "sa_id"]], on="lad_id", how="left")
    for level in ("msoa_id", "lad_id"):
        split = lsoa.groupby(level)["sa_id"].agg(lambda s: s.fillna("none").nunique())
        if (split > 1).any():
            raise ValueError(f"{level}s split across an SA boundary: {list(split[split > 1].index)}")
    return lsoa


def build_sa_folder(sa: pd.Series, lsoa: pd.DataFrame, tmp: Path) -> list[Path]:
    folder = Path("gbr/sa") / slug(sa["id"], sa["name"])
    folder.mkdir(parents=True, exist_ok=True)
    rows = lsoa[lsoa["sa_id"] == sa["id"]]
    attrs = tmp / f"{sa['id']}_lsoa.csv"
    rows[["lsoa_id", "msoa_id", "msoa_name", "lad_id", "lad_name", "sa_id"]].to_csv(attrs, index=False)
    cut = tmp / f"{sa['id']}_lsoa.json"
    _run([
        "mapshaper", str(LSOA_SOURCE),
        "-join", str(attrs), "keys=id,lsoa_id", "string-fields=lsoa_id,msoa_id,lad_id,sa_id",
        "-filter", f"sa_id === '{sa['id']}'",
        "-o", str(cut), "format=topojson",
    ])

    sa_name = json.dumps(sa["name"])
    layers = {  # file → mapshaper steps applied to the LSOA cut
        "LSOA": [],
        "MSOA": [
            "-dissolve", "msoa_id", "calc=area=sum(area)", "copy-fields=msoa_name,lad_id",
            "-rename-fields", "id=msoa_id,name=msoa_name",
        ],
        "LAD": [
            "-dissolve", "lad_id", "calc=area=sum(area)", "copy-fields=lad_name",
            "-rename-fields", "id=lad_id,name=lad_name",
        ],
        "SA": [
            "-dissolve", "sa_id", "calc=area=sum(area)",
            "-rename-fields", "id=sa_id", "-each", f"name={sa_name}",
        ],
    }
    fields = {
        "LSOA": "id,name,area,msoa_id,lad_id",
        "MSOA": "id,name,area,lad_id",
        "LAD": "id,name,area",
        "SA": "id,name,area",
    }
    outputs = []
    for layer, steps in layers.items():
        out = folder / f"{layer}.json"
        _run([
            "mapshaper", str(cut), *steps,
            "-filter-fields", fields[layer],
            "-rename-layers", "geog",
            "-o", str(out), "format=topojson", "fix-geometry",
        ])
        _report_repairs(out)
        _write_metadata(
            out,
            [LSOA_SOURCE, LSOA_LOOKUP],
            {
                "subset": f"LSOAs (2021) in {sa['id']} {sa['name']}",
                "method": f"dissolve the LSOA cut by {steps[1]}" if steps else "cut from full LSOAs",
                "fields": fields[layer].split(","),
            },
        )
        outputs.append(out)
    counts = {p.stem: _count_features(p) for p in outputs}
    size = sum(p.stat().st_size for p in outputs) / 1e6
    print(f"  {sa['id']} {sa['name']:<34} {counts}  {size:5.2f} MB → {folder}")
    return outputs


def main():
    authorities, lads, status = load_inputs()
    _check_inputs(authorities, lads, status)
    print("County matches")
    counties = county_matches(lads)
    for r in counties.itertuples():
        print(f"  {r.sa_id} = {r.cty_id} {r.cty_name}")

    with tempfile.TemporaryDirectory() as tmp:
        for snapshot, proposed in MAPS:
            build_map(snapshot, proposed, authorities, lads, status, counties, Path(tmp))

        print("Per-SA files")
        members = map_members(lads, status, *FOLDER_MAP)
        lsoa = _lsoa_table(members)
        for _, sa in authorities[authorities["id"].isin(members["sa_id"])].iterrows():
            build_sa_folder(sa, lsoa, Path(tmp))


if __name__ == "__main__":
    main()
