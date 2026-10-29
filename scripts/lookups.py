"""
Build simple geography lookup tables (CSV) from ONS lookup services.

Usage:
    uv run python -m scripts.lookups

Each output pairs with a boundary file of the same name, e.g.
gbr/lookups/LAD_UK_2025_12.csv has one row per `id` in gbr/LAD_UK_2025_12.json.
Columns are `{level}_id` / `{level}_name` in lowercase, to match the `id`/`name`
properties used in the TopoJSON files.

ONS lookups are attribute-only Feature Services. They are fetched with the
same ArcGIS query API as boundaries and cached under raw/lookups/{item_id}.csv.
Item ids are pinned here (not searched) so outputs are reproducible.
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

from scripts.fetch import HEADERS, get_item_service_url, get_layer_id

LOOKUP_CACHE = Path("raw/lookups")
OUTPUT_DIR = Path("gbr/lookups")

# ONS lookup items used as sources
ONS_LOOKUPS = {
    "ward_ctry_2025_05": {
        "id": "7315ebba66154363806867bcfd52417a",
        "title": "Ward to Local Authority District to CTYUA to RGN to CTRY (May 2025) Lookup in the UK",
    },
    "lad_itl_2025_04": {
        "id": "6b9e75300d464335a4164b3da52f5ba1",
        "title": "Local Authority District (April 2025) to LAU1 to ITL3 to ITL2 to ITL1 (January 2025) Lookup in the UK",
    },
    "lad_cauth_2025_05": {
        "id": "ba77701e67bd4f3e80a97fb9a5fd4885",
        "title": "Local Authority District to Combined Authority (May 2025) Lookup in EN",
    },
    "lsoa_lad_2025": {
        "id": "f29a49574cc84f6d8e6e59ce2d8efb18",
        "title": "LSOA (2021) to Electoral Ward (2025) to LAD (2025) Best Fit Lookup in EW (V2)",
    },
}

# LADs split across ITL areas (via LAU1), assigned to the ITL3 holding most of
# their population. North Ayrshire: Arran and Cumbrae (~5k people) are in TLM20
# Highlands and Islands; the mainland (~130k) is in TLM93.
ITL3_BEST_FIT = {"S12000021": "TLM93"}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_lookup(key: str, page_size: int = 1000, delay: float = 0.3) -> pd.DataFrame:
    """Return an ONS lookup table as a DataFrame, using the local cache if present."""
    item_id = ONS_LOOKUPS[key]["id"]
    cache_path = LOOKUP_CACHE / f"{item_id}.csv"
    if cache_path.exists():
        return pd.read_csv(cache_path, dtype=str)

    print(f"Fetching lookup: {ONS_LOOKUPS[key]['title']}")
    service_url = get_item_service_url(item_id)
    query_url = f"{service_url}/{get_layer_id(service_url)}/query"

    rows, offset = [], 0
    while True:
        params = {
            "where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json",
            "resultOffset": offset, "resultRecordCount": page_size,
        }
        resp = requests.get(query_url, params=params, headers=HEADERS, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Lookup query error: {data['error']}")
        page = [f["attributes"] for f in data.get("features", [])]
        rows.extend(page)
        if len(page) < page_size and not data.get("exceededTransferLimit"):
            break
        offset += len(page)
        time.sleep(delay)

    df = pd.DataFrame(rows).astype(str).replace({"None": None})
    LOOKUP_CACHE.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)
    print(f"  {len(df):,} rows → {cache_path}")
    return df


def _levels(df: pd.DataFrame, levels: dict[str, str]) -> pd.DataFrame:
    """Select {CODE}CD/{CODE}NM column pairs and rename to {level}_id/{level}_name."""
    cols = {}
    for level, ons_code in levels.items():
        cols[f"{ons_code}CD"] = f"{level}_id"
        cols[f"{ons_code}NM"] = f"{level}_name"
    return df[list(cols)].rename(columns=cols).drop_duplicates()


def _one_per(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """Check each key maps to exactly one row (i.e. areas nest cleanly)."""
    dupes = df[df[key].duplicated(keep=False)]
    if not dupes.empty:
        raise ValueError(f"{key} maps to more than one parent:\n{dupes.to_string()}")
    return df


def _boundary_ids(path: str) -> dict[str, str]:
    topo = json.loads(Path(path).read_text())
    return {g["properties"]["id"]: g["properties"]["name"] for g in topo["objects"]["geog"]["geometries"]}


def _check_matches_boundary(df: pd.DataFrame, key: str, boundary_path: str) -> None:
    ids = _boundary_ids(boundary_path)
    missing = set(ids) - set(df[key])
    extra = set(df[key]) - set(ids)
    if missing or extra:
        raise ValueError(f"{key} doesn't match {boundary_path}: missing={missing} extra={extra}")


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def build_lad_2025() -> Path:
    """LAD (Dec 2025) → country, region, combined authority, ITL1-3."""
    # ONS lookups for LAD25 are dated April/May 2025; LAD codes and names are
    # identical in the May and December 2025 boundaries, so they apply to both.
    ctry = _levels(fetch_lookup("ward_ctry_2025_05"),
                   {"lad": "LAD25", "ctry": "CTRY25", "rgn": "RGN25"})
    itl = _levels(fetch_lookup("lad_itl_2025_04"),
                  {"lad": "LAD25", "itl1": "ITL125", "itl2": "ITL225", "itl3": "ITL325"})
    split = itl["lad_id"].isin(ITL3_BEST_FIT.keys())
    itl = itl[~split | (itl["itl3_id"] == itl["lad_id"].map(ITL3_BEST_FIT))]
    cauth = _levels(fetch_lookup("lad_cauth_2025_05"), {"lad": "LAD25", "cauth": "CAUTH25"})

    df = (
        _one_per(ctry, "lad_id")
        .merge(_one_per(itl.drop(columns="lad_name"), "lad_id"), on="lad_id", how="left")
        .merge(_one_per(cauth.drop(columns="lad_name"), "lad_id"), on="lad_id", how="left")
    )
    df = df[[
        "lad_id", "lad_name", "ctry_id", "ctry_name", "rgn_id", "rgn_name",
        "cauth_id", "cauth_name", "itl1_id", "itl1_name", "itl2_id", "itl2_name",
        "itl3_id", "itl3_name",
    ]].sort_values("lad_id")

    _check_matches_boundary(df, "lad_id", "gbr/LAD_UK_2025_12.json")
    cauth_ids = set(_boundary_ids("gbr/CAUTH_ENG_2025_12.json"))
    if set(df["cauth_id"].dropna()) != cauth_ids:
        print(f"  Warning: CAUTH lookup (May 2025) differs from CAUTH Dec 2025 boundaries: "
              f"{set(df['cauth_id'].dropna()) ^ cauth_ids}")

    return _write(df, "LAD_UK_2025_12.csv")


def build_lsoa_2021() -> Path:
    """LSOA (2021) → MSOA (2021) → LAD (2025, best fit)."""
    lsoa = _boundary_ids("gbr/LSOA_EW_2021.json")
    msoa_by_name = {name: code for code, name in _boundary_ids("gbr/MSOA_EW_2021.json").items()}

    df = pd.DataFrame({"lsoa_id": list(lsoa), "lsoa_name": list(lsoa.values())})
    # ONS 2021 LSOA names are their MSOA name plus a letter: 'Cardiff 032A' is in 'Cardiff 032'
    df["msoa_name"] = df["lsoa_name"].str[:-1]
    df["msoa_id"] = df["msoa_name"].map(msoa_by_name)
    if df["msoa_id"].isna().any():
        raise ValueError(f"LSOAs without an MSOA match:\n{df[df['msoa_id'].isna()].head()}")

    lad = _one_per(_levels(fetch_lookup("lsoa_lad_2025"), {"lsoa": "LSOA21", "lad": "LAD25"})
                   .drop(columns="lsoa_name"), "lsoa_id")
    df = df.merge(lad, on="lsoa_id", how="left")
    if df["lad_id"].isna().any():
        raise ValueError(f"LSOAs without a LAD match:\n{df[df['lad_id'].isna()].head()}")

    df = df[["lsoa_id", "lsoa_name", "msoa_id", "msoa_name", "lad_id", "lad_name"]].sort_values("lsoa_id")
    return _write(df, "LSOA_EW_2021.csv")


def _write(df: pd.DataFrame, filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False)
    print(f"Written {len(df):,} rows → {path}  ({path.stat().st_size / 1e3:.0f} KB)")
    return path


if __name__ == "__main__":
    build_lad_2025()
    build_lsoa_2021()
