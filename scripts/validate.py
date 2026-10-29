"""
Check and repair polygon validity in published TopoJSON files.

Usage:
    uv run python -m scripts.validate                      # check every published file
    uv run python -m scripts.validate gbr/LAD_UK_2025_12.json gbr/full/*.json
    uv run python -m scripts.validate --repair gbr/LSOA_EW_2021.json

Why polygons become invalid (OGC rules, as used by shapely/GEOS, QGIS, PostGIS):
  - Quantisation. TopoJSON rounds coordinates to a grid, which can make a ring
    touch or cross itself at narrow necks. mapshaper's `fix-geometry` output option
    removes most crossings but not rings that touch themselves at a point.
  - Source holes written as shells. ArcGIS's GeoJSON export sometimes writes a hole
    (lake, tidal inlet) as an extra outer polygon ("nested shells"). ONS Shape__Area
    matches treating these as holes, and charts otherwise draw the hole filled.

Repair re-builds only the invalid features with shapely `make_valid(method="linework")`,
which treats every ring as a boundary: nested shells become holes, and pinched
rings are split at the touching point, without moving existing vertices. Any new
vertices are snap-rounded onto the file's grid (GEOS set_precision). Repaired
features are written back into the TopoJSON as new arcs on the file's existing grid;
all other features keep their arcs, so their coordinates and shared borders are
unchanged.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import shapely
from shapely import make_valid, set_precision
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity

PUBLISHED_DIRS = ["gbr", "usa", "world"]


def _decode(path: Path) -> dict:
    """Return the `geog` object of a TopoJSON file as a GeoJSON FeatureCollection."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "geog.json"
        result = subprocess.run(
            ["mapshaper", "-i", str(path), "-target", "geog", "-o", str(out), "format=geojson"],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"mapshaper could not decode {path}:\n{result.stderr}")
        return json.loads(out.read_text())


def _label(feature: dict, index: int) -> str:
    props = feature.get("properties") or {}
    return str(props.get("id") or props.get("name") or f"#{index}")


def find_invalid(path: Path) -> tuple[int, list[tuple[str, str]]]:
    """Return (feature_count, [(label, reason), ...]) for invalid or empty features."""
    features = _decode(path)["features"]
    problems = []
    for i, f in enumerate(features):
        if f["geometry"] is None:
            problems.append((_label(f, i), "Null geometry"))
            continue
        geom = shape(f["geometry"])
        if not geom.is_valid:
            problems.append((_label(f, i), explain_validity(geom)))
    return len(features), problems


def _polygonal(geom) -> Polygon | MultiPolygon:
    """Keep only the polygon parts of a make_valid result (drops stray lines/points)."""
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    parts = []
    for g in getattr(geom, "geoms", []):
        if isinstance(g, Polygon):
            parts.append(g)
        elif isinstance(g, MultiPolygon):
            parts.extend(g.geoms)
    return MultiPolygon(parts) if len(parts) > 1 else (parts[0] if parts else Polygon())


def _grid(topo: dict):
    """Return functions mapping lon/lat arrays to the file's integer grid and back."""
    if "transform" not in topo:
        return None
    scale = np.array(topo["transform"]["scale"])
    translate = np.array(topo["transform"]["translate"])
    return (lambda c: (c - translate) / scale), (lambda c: c * scale + translate)


def _make_valid_on_grid(geom, grid):
    """
    make_valid, then snap-round onto the file's grid with a guaranteed-valid result.

    The grid spacing differs in x and y, so work in integer grid units, where GEOS
    set_precision(1) snap-rounds new vertices (e.g. at crossings) without creating
    new intersections. Existing vertices are already on the grid and don't move.
    """
    if grid is None:
        return _polygonal(make_valid(geom, method="linework"))
    to_grid, from_grid = grid
    on_grid = shapely.transform(geom, to_grid)
    fixed = _polygonal(set_precision(make_valid(on_grid, method="linework"), 1.0))
    return shapely.transform(fixed, from_grid)


def _encode_polygon(geom, topo: dict, grid) -> dict:
    """
    Append geom's rings to topo["arcs"] and return a TopoJSON geometry referencing them.

    Rings are written as new, unshared arcs on the existing grid. Exteriors are
    clockwise and holes anticlockwise, matching mapshaper and d3-geo (which uses
    winding order to decide which side of a ring is inside).
    """
    def add_ring(coords) -> int:
        coords = np.asarray(coords)
        if grid is not None:
            coords = np.rint(grid[0](coords)).astype(int)
        pts = []
        for pt in map(tuple, coords.tolist()):
            if not pts or pt != pts[-1]:
                pts.append(pt)
        if grid is not None:  # delta-encode
            arc = [list(pts[0])] + [[b[0] - a[0], b[1] - a[1]] for a, b in zip(pts, pts[1:])]
        else:
            arc = [list(p) for p in pts]
        topo["arcs"].append(arc)
        return len(topo["arcs"]) - 1

    polys = []
    for p in getattr(geom, "geoms", [geom]):
        p = orient(p, sign=-1.0)
        polys.append([[add_ring(p.exterior.coords)]] + [[add_ring(r.coords)] for r in p.interiors])
    if len(polys) == 1:
        return {"type": "Polygon", "arcs": polys[0]}
    return {"type": "MultiPolygon", "arcs": polys}


def _drop_unused_arcs(topo: dict) -> None:
    """Remove arcs nothing references any more (e.g. a repaired feature's old coastline)."""
    used: dict[int, int] = {}

    def remap(arcs):
        if isinstance(arcs, list):
            return [remap(a) for a in arcs]
        i = arcs if arcs >= 0 else ~arcs
        new = used.setdefault(i, len(used))
        return new if arcs >= 0 else ~new

    def visit(obj):  # every object counts, e.g. usa/ files' `states` and `nation` meshes
        if "arcs" in obj:
            obj["arcs"] = remap(obj["arcs"])
        for g in obj.get("geometries", []):
            visit(g)

    for obj in topo["objects"].values():
        visit(obj)
    old_arcs = topo["arcs"]
    topo["arcs"] = [None] * len(used)
    for old, new in used.items():
        topo["arcs"][new] = old_arcs[old]


def repair_file(path: Path) -> list[tuple[str, float]]:
    """
    Repair invalid features in place. Returns [(label, relative_area_change), ...].

    Only invalid features are rewritten. Every other feature keeps its arcs, so its
    coordinates and shared borders are unchanged. Raises if a repair leaves an empty
    geometry or the file is still invalid afterwards.
    """
    topo = json.loads(path.read_text())
    if "geog" not in topo["objects"]:
        raise ValueError(f"{path}: no 'geog' object to repair")
    geometries = topo["objects"]["geog"]["geometries"]
    features = _decode(path)["features"]
    if len(features) != len(geometries):
        raise RuntimeError(f"{path}: decoded feature count doesn't match the TopoJSON")

    grid = _grid(topo)
    repaired = []
    for i, f in enumerate(features):
        if f["geometry"] is None:
            continue
        geom = shape(f["geometry"])
        if geom.is_valid:
            continue
        fixed = _make_valid_on_grid(geom, grid)
        if fixed.is_empty:
            raise RuntimeError(f"{path}: repairing {_label(f, i)} left no polygon")
        if not fixed.is_valid:
            raise RuntimeError(f"{path}: could not repair {_label(f, i)}: {explain_validity(fixed)}")
        new = _encode_polygon(fixed, topo, grid)
        geometries[i] = {**{k: v for k, v in geometries[i].items() if k not in ("type", "arcs")}, **new}
        repaired.append((_label(f, i), (fixed.area - geom.area) / geom.area if geom.area else 0.0))

    if repaired:
        _drop_unused_arcs(topo)
        path.write_text(json.dumps(topo, separators=(",", ":")))
    _, problems = find_invalid(path)
    nulls = [label for label, reason in problems if reason == "Null geometry"]
    if nulls:
        # Can't be repaired from the file itself: the shape has collapsed or is missing
        print(f"  Warning: {path} has {len(nulls)} feature(s) with no geometry: {nulls[:5]}")
    invalid = [p for p in problems if p[1] != "Null geometry"]
    if invalid:
        raise RuntimeError(f"{path}: still {len(invalid)} invalid after repair: {invalid[:5]}")
    return repaired


def published_files() -> list[Path]:
    return sorted(p for d in PUBLISHED_DIRS for p in Path(d).rglob("*.json"))


def main():
    parser = argparse.ArgumentParser(description="Check / repair polygon validity of TopoJSON files")
    parser.add_argument("files", nargs="*", help="Files to check (default: all published files)")
    parser.add_argument("--repair", action="store_true", help="Repair invalid features in place")
    args = parser.parse_args()

    files = [Path(f) for f in args.files] or published_files()
    n_bad_files = 0
    for path in files:
        try:
            count, problems = find_invalid(path)
        except RuntimeError as e:
            print(f"{path}: could not check ({e})")
            continue
        if not problems:
            print(f"{path}: ok ({count:,} features)")
            continue
        n_bad_files += 1
        reasons = sorted({r.split("[")[0] for _, r in problems})
        print(f"{path}: {len(problems)} invalid of {count:,}  ({', '.join(reasons)})")
        if args.repair:
            try:
                fixes = repair_file(path)
            except ValueError as e:
                print(f"  not repaired: {e}")
                continue
            largest = sorted(fixes, key=lambda x: -abs(x[1]))[:3]
            print(f"  repaired {len(fixes)}; largest area changes: "
                  + ", ".join(f"{k} {v * 100:+.3f}%" for k, v in largest))
    if n_bad_files and not args.repair:
        sys.exit(1)


if __name__ == "__main__":
    main()
