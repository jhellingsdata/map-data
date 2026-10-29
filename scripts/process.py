"""
MapShaper processing pipeline.

Takes a source shapefile and produces a standardised TopoJSON with:
  - id and name properties (renamed from detected source columns)
  - Optional extra properties (e.g. area from Shape__Area, in m²)
  - Objects key named 'geog' (consistent across the repo)
  - Projected to WGS84 (ONS shapefiles use British National Grid)
  - Simplification via Visvalingam weighted with keep-shapes (or none for BFC variants)
"""

import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

from scripts.config import BOUNDARY_CONFIGS

# Marker used in extra_fields when 'area' must be computed from geometry rather
# than passed through. Some ONS services are re-published in WGS84, so their
# Shape__Area is in square degrees. We then compute area in British National Grid
# (m²), which matches ONS's own values to within ~0.02%.
COMPUTED_AREA = "computed:EPSG:27700"


def detect_fields(
    shp_path: Path,
    id_pattern: str,
    name_pattern: str,
    extra_field_patterns: Optional[dict[str, str]] = None,
) -> tuple[str, str, dict[str, str]]:
    """
    Run mapshaper -info to list attribute fields, then match id/name/extra patterns.

    Returns (id_field, name_field, extra_fields) where extra_fields maps
    target_name → actual_source_field_name for any additional columns.
    Raises ValueError if id or name pattern doesn't match.
    """
    result = subprocess.run(
        ["mapshaper", str(shp_path), "-info"],
        capture_output=True, text=True, timeout=60,
    )
    output = result.stdout + result.stderr

    # mapshaper >= 0.6 uses a table format; older versions used "Attribute fields: a, b, c"
    # Table format: lines like " FieldName  | value"
    table_rows = re.findall(r"^\s+([\w.]+)\s+\|\s*(.*)$", output, re.MULTILINE)
    first_values = {f: v.strip() for f, v in table_rows if f.lower() != "field"}  # drop header row

    if first_values:
        fields = list(first_values)
    else:
        fields_match = re.search(r"Attribute fields[^:]*:\s*(.+)", output)
        if not fields_match:
            raise RuntimeError(f"Could not parse fields from mapshaper -info output:\n{output}")
        raw_fields = fields_match.group(1)
        fields = [f.strip().rstrip(",") for f in re.split(r",\s*", raw_fields) if f.strip()]

    id_field = _match_field(fields, id_pattern)
    name_field = _match_field(fields, name_pattern)

    if id_field is None:
        raise ValueError(f"No field matching id_pattern r'{id_pattern}' in: {fields}")
    if name_field is None:
        raise ValueError(f"No field matching name_pattern r'{name_pattern}' in: {fields}")

    extra_fields: dict[str, str] = {}
    for target_name, pattern in (extra_field_patterns or {}).items():
        found = _match_field(fields, pattern)
        if found and target_name == "area" and _is_square_degrees(first_values.get(found)):
            print(f"  Warning: {found} looks like square degrees ({first_values[found]}), "
                  f"computing area from geometry instead")
            extra_fields[target_name] = COMPUTED_AREA
        elif found:
            extra_fields[target_name] = found
        else:
            print(f"  Warning: extra field pattern r'{pattern}' not found in: {fields}")

    return id_field, name_field, extra_fields


def _match_field(fields: list[str], pattern: str) -> Optional[str]:
    for field in fields:
        if re.fullmatch(pattern, field, re.IGNORECASE):
            return field
    return None


def _is_square_degrees(value: Optional[str]) -> bool:
    """No UK boundary is under 1 m², so a sub-1 area must be in square degrees."""
    try:
        return float(value) < 1
    except (TypeError, ValueError):
        return False


def process_boundary(
    shp_path: Path,
    id_field: str,
    name_field: str,
    output_path: Path,
    simplification_pct: Optional[int] = 50,
    extra_fields: Optional[dict[str, str]] = None,
) -> tuple[int, float, float]:
    """
    Run the full MapShaper pipeline and write a TopoJSON to output_path.

    simplification_pct=None skips simplification entirely (for full-resolution variants).
    extra_fields maps {target_name: source_field_name} for additional preserved columns.

    Returns (feature_count, source_size_mb, output_size_mb).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_size_mb = shp_path.stat().st_size / 1e6

    # Build field rename and filter lists
    rename_parts = [f"id={id_field}", f"name={name_field}"]
    keep_fields = ["id", "name"]
    computed_parts = []
    for target, source in (extra_fields or {}).items():
        if source == COMPUTED_AREA:
            computed_parts.append(f"{target}=this.area")
        else:
            rename_parts.append(f"{target}={source}")
        keep_fields.append(target)

    # snap: merge near-coincident vertices so neighbouring areas share arcs. Some ONS
    # sources (e.g. LAD May 2021) have borders that don't quite match, which
    # otherwise bloats the TopoJSON ~2.5x and leaves slivers after simplification.
    cmd = ["mapshaper", "-i", str(shp_path), "snap", "-rename-layers", "geog"]
    if computed_parts:
        # Compute before simplifying, in a metric projection
        cmd += ["-proj", "EPSG:27700", "-each", ";".join(computed_parts), "-proj", "wgs84"]
    if simplification_pct is not None:
        cmd += ["-simplify", f"{simplification_pct}%", "visvalingam", "weighted", "keep-shapes"]
    cmd += [
        "-rename-fields", ",".join(rename_parts),
        "-filter-fields", ",".join(keep_fields),
        "-proj", "wgs84",
        "-o", str(output_path), "format=topojson",
    ]

    label = f"simplification={simplification_pct}%" if simplification_pct else "no simplification"
    print(f"Running mapshaper ({label})…")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"mapshaper failed:\n{result.stderr}")
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())

    output_size_mb = output_path.stat().st_size / 1e6
    feature_count = _count_features(output_path)
    print(
        f"Written {feature_count} features → {output_path}  "
        f"({source_size_mb:.1f} MB → {output_size_mb:.2f} MB)"
    )
    return feature_count, source_size_mb, output_size_mb


def _count_features(topo_path: Path) -> int:
    with open(topo_path) as f:
        topo = json.load(f)
    for layer in topo.get("objects", {}).values():
        return len(layer.get("geometries", []))
    return 0


def build_metadata(
    boundary_type: str,
    source_id: str,
    source_title: str,
    source_url: str,
    id_field: str,
    name_field: str,
    extra_fields: dict[str, str],
    simplification_pct: Optional[int],
    output_file: str,
    feature_count: int,
    source_size_mb: float,
    output_size_mb: float,
    mapshaper_version: str,
    downloaded: Optional[str] = None,
) -> dict:
    return {
        "source": {
            "id": source_id,
            "title": source_title,
            "url": source_url,
            "downloaded": downloaded or date.today().isoformat(),
        },
        "processing": {
            "boundary_type": boundary_type,
            "id_field": id_field,
            "name_field": name_field,
            "extra_fields": extra_fields,
            "simplification_pct": simplification_pct,
            "method": "visvalingam weighted keep-shapes" if simplification_pct else "none",
            "projection": "wgs84",
            "processed": date.today().isoformat(),
            "mapshaper_version": mapshaper_version,
        },
        "output": {
            "file": output_file,
            "format": "topojson",
            "objects_key": "geog",
            "feature_count": feature_count,
            "source_size_mb": round(source_size_mb, 2),
            "output_size_mb": round(output_size_mb, 2),
        },
    }


def get_mapshaper_version() -> str:
    result = subprocess.run(["mapshaper", "--version"], capture_output=True, text=True, timeout=10)
    return result.stdout.strip() or result.stderr.strip()
