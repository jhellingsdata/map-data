"""
Fetch and cache the ONS GeoPortal catalog from the ArcGIS Hub feed.

The feed returns a CSV of every dataset published on geoportal.statistics.gov.uk.
We cache it locally under raw/catalog/ and only re-fetch when force_refresh=True
or the cached file is older than max_age_hours.
"""

import io
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from scripts.config import CATALOG_COLUMNS

CATALOG_URL = "https://hub.arcgis.com/api/feed/all/csv"
CATALOG_PARAMS = {"target": "geoportal.statistics.gov.uk"}
CATALOG_CACHE = Path("raw/catalog/ons_catalog.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/149.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://geoportal.statistics.gov.uk/",
}


def fetch_catalog(force_refresh: bool = False, max_age_hours: int = 24) -> pd.DataFrame:
    """
    Return the ONS catalog as a DataFrame.

    Uses cached file if fresh enough; otherwise re-downloads.
    Only retains the columns defined in CATALOG_COLUMNS (if present).
    """
    if not force_refresh and CATALOG_CACHE.exists():
        age = datetime.now() - datetime.fromtimestamp(CATALOG_CACHE.stat().st_mtime)
        if age < timedelta(hours=max_age_hours):
            print(f"Using cached catalog ({age.seconds // 3600}h {(age.seconds % 3600) // 60}m old)")
            return _load_csv(CATALOG_CACHE)

    print("Fetching ONS catalog from ArcGIS Hub…")
    CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)

    resp = requests.get(CATALOG_URL, params=CATALOG_PARAMS, headers=HEADERS, timeout=120)
    resp.raise_for_status()

    df = pd.read_csv(io.StringIO(resp.text), low_memory=False)
    available = [c for c in CATALOG_COLUMNS if c in df.columns]
    df = df[available]

    df.to_csv(CATALOG_CACHE, index=False)
    print(f"Saved {len(df):,} catalog entries to {CATALOG_CACHE}")
    return df


def _load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded {len(df):,} catalog entries from {path}")
    return df


def catalog_info(df: pd.DataFrame) -> None:
    """Print a quick summary of the catalog."""
    print(f"Total entries : {len(df):,}")
    if "type" in df.columns:
        print("\nTop item types:")
        print(df["type"].value_counts().head(10).to_string())
    if "modified" in df.columns:
        latest = pd.to_datetime(df["modified"], unit="ms", errors="coerce").max()
        print(f"\nMost recently modified: {latest:%Y-%m-%d}" if pd.notna(latest) else "")
