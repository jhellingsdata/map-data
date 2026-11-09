"""
Build one TopoJSON file per area: gbr/areas/{GSS code}.json.

Usage:
    uv run python -m scripts.areas              # build / update every file
    uv run python -m scripts.areas --plan       # show which release supplies each code

Every local authority code that has appeared in an ONS full-resolution (BFC) release
gets one file: LAD codes (lower tier and unitary) and English county codes (E10, upper
tier). Each file holds its code's **latest** release ("latest wins"), so a file is
updated in place when ONS revises the geometry under an unchanged code. Retired codes
come from the last BFC release that contains them.

Files are exact extracts of a full-resolution file: the feature's arcs and the
quantisation grid are copied unchanged, so the shape (and validity) is identical to
the source and overlays it exactly. `area` is ONS `Shape__Area` from that source.

Sources:
  - current codes: the published gbr/full/ files in CURRENT_SOURCES
  - retired codes: older ONS BFC releases, built with the normal pipeline into
    raw/areas/sources/ (git-ignored, not published)

To find each code's last release, every LAD / CTYUA BFC item in the catalog is queried
for its codes only (no geometry). Results are cached in raw/areas/codes/.
"""

import argparse
import copy
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from scripts.catalog import fetch_catalog
from scripts.config import BOUNDARY_CONFIGS
from scripts.fetch import (
    HEADERS,
    build_output_filename,
    get_item_service_url,
    get_layer_id,
    parse_date_from_title,
    search_catalog,
)
from scripts.pipeline import build_one
from scripts.process import get_mapshaper_version
from scripts.validate import _drop_unused_arcs, repair_file

OUTPUT_DIR = Path("gbr/areas")
METADATA_PATH = Path("metadata/gbr/areas.json")
CODES_CACHE = Path("raw/areas/codes")
SOURCES_DIR = Path("raw/areas/sources")

# Boundary type → the published full-resolution file holding its current codes.
# E10 counties come from CTYUA; every other code from LAD (unitary-level CTYUA codes
# are the same areas as their LAD codes).
CURRENT_SOURCES = {
    "LAD_BFC": Path("gbr/full/LAD_UK_2026_05.json"),
    "CTYUA_BFC": Path("gbr/full/CTYUA_UK_2025_12.json"),
}

GSS_CODE = re.compile(r"^[ENSW]\d{8}$")
COVERAGE_RANK = {"UK": 0, "GB": 1, "EW": 2, "ENG": 3}  # prefer the widest coverage
FIRST_YEAR = 2009  # GSS codes date from 2009-11; older releases use other codes


def wanted(btype: str, code: str) -> bool:
    """Which boundary type supplies a code: E10 from CTYUA, everything else from LAD."""
    return code.startswith("E10") if btype == "CTYUA_BFC" else not code.startswith("E10")


def tier(code: str) -> str:
    """lower = district (two-tier area), upper = county, both = unitary-level authority."""
    return {"E07": "lower", "E10": "upper"}.get(code[:3], "both")


# ---------------------------------------------------------------------------
# Which release supplies each code
# ---------------------------------------------------------------------------

def release_codes(btype: str, row: pd.Series) -> dict[str, str]:
    """{code: name} for one ONS item, from an attribute-only query (cached)."""
    cache = CODES_CACHE / f"{row['id']}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    cfg = BOUNDARY_CONFIGS[btype]
    service = get_item_service_url(row["id"])
    query = f"{service}/{get_layer_id(service)}/query"
    codes: dict[str, str] = {}
    offset = 0
    while True:
        resp = requests.get(query, headers=HEADERS, timeout=60, params={
            "where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json",
            "resultOffset": offset, "resultRecordCount": 2000,
        })
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"{row['title']}: {data['error']}")
        feats = data.get("features", [])
        for f in feats:
            attrs = f["attributes"]
            id_f = next((k for k in attrs if re.fullmatch(cfg["id_pattern"], k, re.I)), None)
            name_f = next((k for k in attrs if re.fullmatch(cfg["name_pattern"], k, re.I)), None)
            if not (id_f and name_f):
                # e.g. CTYUA Dec 2021 EN uses CTYCDE/CTYNME; the UK release covers it
                print(f"  Skipping {row['title']}: no {cfg['id_pattern']} field in {list(attrs)}")
                break
            codes[attrs[id_f]] = attrs[name_f]
        if not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    CODES_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(codes, indent=1))
    return codes


def releases(btype: str, catalog: pd.DataFrame) -> list[dict]:
    """BFC releases with GSS codes, newest first."""
    out = []
    for _, row in search_catalog(catalog, btype).iterrows():
        year, month = parse_date_from_title(row["title"])
        if year is None or int(year) < FIRST_YEAR:
            continue
        name = build_output_filename(btype, row["title"])[:-5]  # e.g. LAD_UK_2022_12
        coverage = name.split("_")[1]
        codes = {c: n for c, n in release_codes(btype, row).items() if GSS_CODE.match(str(c))}
        if not codes:
            continue
        published = (Path(BOUNDARY_CONFIGS[btype]["output_dir"]) / f"{name}.json").exists()
        # Same date: prefer an already-published file, then the widest coverage
        out.append({"btype": btype, "name": name, "id": row["id"], "title": row["title"],
                    "url": row.get("url", ""), "codes": codes,
                    "sort": (int(year), int(month or 0), published, -COVERAGE_RANK.get(coverage, 9))})
    return sorted(out, key=lambda r: r["sort"], reverse=True)


def plan_sources(catalog: pd.DataFrame) -> tuple[dict[str, dict], dict[str, Path]]:
    """
    Return ({code: release}, {release name: source file}).

    Each code gets the newest release containing it. The current file must be the
    newest release of its type, so current codes always come from it.
    """
    plan: dict[str, dict] = {}
    files: dict[str, Path] = {}
    for btype, current in CURRENT_SOURCES.items():
        rels = releases(btype, catalog)
        if rels[0]["name"] != current.stem:
            raise RuntimeError(f"{btype}: newest BFC release is {rels[0]['name']}, "
                               f"but CURRENT_SOURCES uses {current} — build that first")
        for rel in rels:
            for code in rel["codes"]:
                if wanted(btype, code) and code not in plan:
                    plan[code] = rel
        for rel in {r["name"]: r for r in plan.values() if r["btype"] == btype}.values():
            published = Path(BOUNDARY_CONFIGS[btype]["output_dir"]) / f"{rel['name']}.json"
            files[rel["name"]] = published if published.exists() else SOURCES_DIR / f"{rel['name']}.json"
    return plan, files


def build_sources(plan: dict[str, dict], files: dict[str, Path]) -> None:
    """Build any older release that isn't published, through the normal pipeline."""
    missing = {r["name"]: r for r in plan.values() if not files[r["name"]].exists()}
    if not missing:
        return
    mapshaper_ver = get_mapshaper_version()
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    for name, rel in sorted(missing.items()):
        out = files[name]
        print(f"\nBuilding source {name}: {rel['title']}")
        ok = build_one(rel["btype"], rel["id"], rel["title"], rel["url"], out, mapshaper_ver,
                       metadata_path=out.with_suffix(".meta.json"))
        if not ok:
            raise RuntimeError(f"Could not build source {name}")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _bbox(topo: dict) -> list[float]:
    xs, ys = [], []
    for arc in topo["arcs"]:
        x = y = 0
        for dx, dy in arc:
            x += dx
            y += dy
            xs.append(x)
            ys.append(y)
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    return [min(xs) * sx + tx, min(ys) * sy + ty, max(xs) * sx + tx, max(ys) * sy + ty]


def extract(topo: dict, geometry: dict) -> dict:
    """A topology holding only `geometry`, with its arcs and grid unchanged."""
    if "transform" not in topo:
        raise ValueError("expected a quantised TopoJSON (with a transform)")
    out = {"type": "Topology", "transform": topo["transform"], "arcs": topo["arcs"],
           "objects": {"geog": {"type": "GeometryCollection",
                                "geometries": [copy.deepcopy(geometry)]}}}
    _drop_unused_arcs(out)
    out["bbox"] = _bbox(out)
    return out


def build(plan: dict[str, dict], files: dict[str, Path]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    current_names = {p.stem for p in CURRENT_SOURCES.values()}
    rows, written = [], []
    for name, path in sorted(files.items()):
        topo = json.loads(path.read_text())
        by_code = {g["properties"]["id"]: g for g in topo["objects"]["geog"]["geometries"]}
        for code, rel in sorted(plan.items()):
            if rel["name"] != name:
                continue
            geom = by_code.get(code)
            if geom is None or "arcs" not in geom:
                raise RuntimeError(f"{code} has no geometry in {path}")
            out = OUTPUT_DIR / f"{code}.json"
            out.write_text(json.dumps(extract(topo, geom), separators=(",", ":")))
            written.append(out)
            props = geom["properties"]
            rows.append({"id": code, "name": props["name"], "tier": tier(code),
                         "current": name in current_names, "release": name,
                         "area": props.get("area")})
            if rows[-1]["area"] is None:
                raise RuntimeError(f"{code}: no area in {path}")

    stale = sorted(set(OUTPUT_DIR.glob("*.json")) - set(written))
    if stale:
        raise RuntimeError(f"Files with no planned source (codes never disappear): {stale[:5]}")

    # Exact extracts of valid files should need no repair; check anyway
    with ThreadPoolExecutor(max_workers=8) as pool:
        repairs = dict(zip([p.stem for p in written], pool.map(repair_file, written)))
    repaired = {code: r for code, r in repairs.items() if r}
    if repaired:
        print(f"  Repaired: {repaired}")

    index = pd.DataFrame(rows).sort_values("id")
    index.to_csv(OUTPUT_DIR / "index.csv", index=False)

    sizes = {p.stem: p.stat().st_size for p in written}
    meta = {
        "description": "One file per GSS code, each an exact single-feature extract of the "
                       "newest full-resolution release containing that code.",
        "processing": {"script": "scripts/areas.py", "processed": date.today().isoformat(),
                       "validity_repairs": sorted(repaired)},
        "sources": {
            name: {"file": str(files[name]), "published": not str(files[name]).startswith("raw/"),
                   "ons_item": next(r for r in plan.values() if r["name"] == name)["id"],
                   "ons_title": next(r for r in plan.values() if r["name"] == name)["title"],
                   "codes": sorted(c for c, r in plan.items() if r["name"] == name)}
            for name in sorted(files)
        },
        "output": {"dir": str(OUTPUT_DIR), "index": str(OUTPUT_DIR / "index.csv"),
                   "file_count": len(written), "total_size_mb": round(sum(sizes.values()) / 1e6, 2),
                   "largest": max(sizes, key=sizes.get),
                   "largest_size_mb": round(max(sizes.values()) / 1e6, 2)},
    }
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(meta, indent=2))
    n_current = int(index["current"].sum())
    print(f"\n{len(written)} files ({n_current} current, {len(written) - n_current} retired), "
          f"{meta['output']['total_size_mb']} MB → {OUTPUT_DIR}/")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--plan", action="store_true", help="Only show which release supplies each code")
    args = parser.parse_args()

    plan, files = plan_sources(fetch_catalog())
    for name, path in sorted(files.items()):
        codes = sorted(c for c, r in plan.items() if r["name"] == name)
        state = "ok" if path.exists() else "to build"
        print(f"{name:<18} {len(codes):>4} codes  {path} ({state})"
              + ("" if len(codes) > 12 else f"  {', '.join(codes)}"))
    if args.plan:
        return
    build_sources(plan, files)
    build(plan, files)


if __name__ == "__main__":
    main()
