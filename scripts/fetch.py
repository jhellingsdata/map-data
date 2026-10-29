"""
Search the ONS catalog and download source boundary files.

Download strategy:
  ONS items are hosted as ArcGIS Feature Services.
  1. Get the service URL from the ArcGIS item REST API.
  2. Query the feature service for all features as GeoJSON, with pagination
     (services cap at 2000 features per request).
  3. Write a single merged GeoJSON to raw/downloads/{item_id}.geojson.

This approach is reliable for all ONS items regardless of whether a
pre-packaged file download is available.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from scripts.catalog import parse_modified
from scripts.config import BOUNDARY_CONFIGS, COVERAGE_MAP, MONTH_MAP, TITLE_EXCLUDE, VALID_ITEM_TYPES

DOWNLOAD_DIR = Path("raw/downloads")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36"
    ),
}

ARCGIS_ITEM_URL = "https://www.arcgis.com/sharing/rest/content/items/{id}?f=json"
FEATURE_QUERY_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "f": "geojson",
    "resultRecordCount": 2000,
    "resultOffset": 0,
}


# ---------------------------------------------------------------------------
# Catalog search
# ---------------------------------------------------------------------------

def search_catalog(df: pd.DataFrame, boundary_type: str) -> pd.DataFrame:
    """
    Filter the catalog for a specific boundary type.

    Matches on title keywords AND the preferred edition keyword (e.g. 'BGC').
    Only Feature Service / Feature Layer items are returned.
    """
    cfg = BOUNDARY_CONFIGS.get(boundary_type.upper())
    if cfg is None:
        raise ValueError(f"Unknown boundary type '{boundary_type}'. "
                         f"Available: {', '.join(BOUNDARY_CONFIGS)}")

    mask = pd.Series(True, index=df.index)

    if "type" in df.columns:
        mask &= df["type"].isin(VALID_ITEM_TYPES)

    if "title" in df.columns:
        for kw in cfg["title_keywords"]:
            mask &= df["title"].str.contains(kw, case=False, na=False)
        edition_kw = cfg.get("edition_keyword", "")
        if edition_kw:
            mask &= df["title"].str.contains(edition_kw, case=False, na=False)
        for kw in TITLE_EXCLUDE + cfg.get("title_exclude", []):
            mask &= ~df["title"].str.contains(kw, case=False, na=False, regex=False)

    results = df[mask].copy()

    if "modified" in results.columns:
        results["_modified_dt"] = parse_modified(results["modified"])
        results = results.sort_values("_modified_dt", ascending=False).drop(columns=["_modified_dt"])

    return results.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Title parsing helpers
# ---------------------------------------------------------------------------

def parse_date_from_title(title: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract (year, month_number) from an ONS title string.

    'Local Authority Districts (December 2024) Boundaries UK BGC' → ('2024', '12')
    Returns (None, None) if no date pattern is found.
    """
    match = re.search(r"\((\w+)\s+(\d{4})\)", title)
    if not match:
        return None, None
    month_name = match.group(1).lower()
    year = match.group(2)
    month = MONTH_MAP.get(month_name)
    return year, month


def parse_coverage_from_title(title: str, default: str = "UK") -> str:
    """Extract a short coverage code from an ONS title string."""
    for pattern, code in COVERAGE_MAP:
        if re.search(pattern, title, re.IGNORECASE):
            return code
    return default


def build_output_filename(boundary_type: str, title: str) -> str:
    """
    Construct the standardised output filename (without path) from title.

    LAD, 'Local Authority Districts (December 2024) Boundaries UK BGC'
      → 'LAD_UK_2024_12.json'
    """
    cfg = BOUNDARY_CONFIGS[boundary_type.upper()]
    year, month = parse_date_from_title(title)
    coverage = parse_coverage_from_title(title, cfg["coverage_default"])
    prefix = cfg["output_prefix"]

    if year is None:
        raise ValueError(f"Could not extract date from title: {title!r}")

    if cfg["versioned_by_month"] and month:
        return f"{prefix}_{coverage}_{year}_{month}.json"
    return f"{prefix}_{coverage}_{year}.json"


# ---------------------------------------------------------------------------
# Feature service download
# ---------------------------------------------------------------------------

def get_item_service_url(item_id: str) -> str:
    """Fetch the feature service URL for an ArcGIS Online item."""
    resp = requests.get(
        ARCGIS_ITEM_URL.format(id=item_id),
        headers=HEADERS, timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    url = data.get("url", "")
    if not url:
        raise RuntimeError(
            f"No service URL found for item {item_id}. Item type: {data.get('type')}"
        )
    return url.rstrip("/")


def get_layer_id(service_url: str) -> int:
    """
    Return the layer id holding the boundaries in a feature service.

    Most ONS services publish their geometry as layer 0, but some (e.g.
    Combined Authorities) use a different id, so ask the service rather
    than assuming. Lookup services have no layers, only attribute tables,
    so fall back to those.
    """
    resp = requests.get(service_url, params={"f": "json"}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    info = resp.json()
    layers = info.get("layers") or info.get("tables") or []
    if not layers:
        raise RuntimeError(f"No layers found in feature service {service_url}")
    if len(layers) > 1:
        names = ", ".join(f"{l['id']}:{l['name']}" for l in layers)
        print(f"  Warning: {len(layers)} layers found ({names}), using the first")
    return layers[0]["id"]


def download_from_service(
    service_url: str,
    dest_path: Path,
    max_per_page: int = 2000,
    delay: float = 0.5,
    max_retries: int = 5,
) -> Path:
    """
    Download all features from a Feature Service layer as GeoJSON.

    Handles pagination and retries automatically. Progress is checkpointed to
    a partial file after each page so interrupted downloads can resume.
    """
    layer_id = get_layer_id(service_url)
    query_url = f"{service_url}/{layer_id}/query"
    partial_path = dest_path.with_suffix(".partial.json")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume from partial checkpoint if available
    all_features: list = []
    start_offset = 0
    if partial_path.exists():
        with open(partial_path) as f:
            checkpoint = json.load(f)
        all_features = checkpoint.get("features", [])
        start_offset = checkpoint.get("offset", 0)
        if all_features:
            print(f"  Resuming from offset {start_offset} ({len(all_features)} features already fetched)")

    offset = start_offset
    page = offset // max_per_page

    while True:
        page += 1
        params = {**FEATURE_QUERY_PARAMS, "resultOffset": offset, "resultRecordCount": max_per_page}

        features = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(query_url, params=params, headers=HEADERS, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise RuntimeError(f"Feature service error: {data['error']}")
                features = data.get("features", [])
                exceeded = data.get("exceededTransferLimit")
                break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait = attempt * 15
                    print(f"  Page {page} attempt {attempt} failed ({e}), retrying in {wait}s…")
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"Feature service request failed after {max_retries} attempts: {e}") from e

        all_features.extend(features)
        print(f"  Page {page}: {len(features)} features  (total so far: {len(all_features)})")

        # Save checkpoint after each page
        with open(partial_path, "w") as f:
            json.dump({"offset": offset + len(features), "features": all_features}, f)

        if len(features) < max_per_page:
            break
        if not exceeded and len(features) < max_per_page:
            break

        offset += max_per_page
        time.sleep(delay)

    geojson = {"type": "FeatureCollection", "features": all_features}
    with open(dest_path, "w") as f:
        json.dump(geojson, f)

    partial_path.unlink(missing_ok=True)

    size_mb = dest_path.stat().st_size / 1e6
    print(f"  Saved {len(all_features)} features ({size_mb:.1f} MB) → {dest_path}")
    return dest_path


def download_boundary(
    item_id: str,
    dest_dir: Path = DOWNLOAD_DIR,
    page_size: int = 2000,
) -> Path:
    """
    Download all features for an ArcGIS item as a GeoJSON file.

    Returns the path to the saved .geojson file.
    Skips download if the file already exists.
    Use a smaller page_size for full-resolution (BFC) datasets to avoid 504 timeouts.
    """
    dest_path = dest_dir / f"{item_id}.geojson"

    if dest_path.exists():
        size_mb = dest_path.stat().st_size / 1e6
        print(f"Already downloaded: {dest_path} ({size_mb:.1f} MB)")
        return dest_path

    print(f"Getting service URL for item {item_id}…")
    service_url = get_item_service_url(item_id)
    print(f"  Service: {service_url}")

    return download_from_service(service_url, dest_path, max_per_page=page_size)


def find_source_file(path: Path) -> Path:
    """
    Return the source file to pass to mapshaper.

    Accepts a directory (looks for .shp or .geojson inside) or a direct file path.
    """
    if path.is_file():
        return path
    # Search for .geojson first, then .shp
    for ext in ("*.geojson", "*.shp"):
        matches = list(path.rglob(ext))
        if matches:
            if len(matches) > 1:
                print(f"Warning: multiple {ext} files found, using {matches[0]}")
            return matches[0]
    raise FileNotFoundError(f"No .geojson or .shp file found in {path}")


# Keep backward-compatible alias
def find_shapefile(directory: Path) -> Path:
    return find_source_file(directory)
