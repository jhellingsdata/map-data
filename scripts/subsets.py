"""
Build per-nation subsets of published boundary files.

Usage:
    uv run python -m scripts.subsets

Each subset is an exact filter of its source file (same geometry and properties),
named by swapping the coverage code: gbr/LAD_UK_2025_12.json → gbr/LAD_WLS_2025_12.json.
Features are selected by the first letter of their GSS code (`id`), which
encodes the nation: E England, W Wales, S Scotland, N Northern Ireland.
"""

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from scripts.process import _count_features

METADATA_DIR = Path("metadata")

NATIONS = {"ENG": "E", "WLS": "W", "SCT": "S", "NIR": "N"}
COVERAGE_NATIONS = {
    "UK": ["ENG", "WLS", "SCT", "NIR"],
    "GB": ["ENG", "WLS", "SCT"],
    "EW": ["ENG", "WLS"],
}

# Source files to split. Add a file here to publish its nation subsets.
SUBSET_SOURCES = [
    "gbr/LAD_UK_2025_12.json",
    "gbr/ELE_MP_UK_2024_07.json",
    "gbr/LSOA_EW_2021.json",
    "gbr/MSOA_EW_2021.json",
]


def subset_path(source: Path, nation: str) -> Path:
    """gbr/LAD_UK_2025_12.json + WLS → gbr/LAD_WLS_2025_12.json"""
    new_name, n = re.subn(r"_(UK|GB|EW)_", f"_{nation}_", source.name, count=1)
    if n == 0:
        raise ValueError(f"No UK/GB/EW coverage code in {source.name}")
    return source.with_name(new_name)


def build_subset(source: Path, nation: str) -> Path:
    out = subset_path(source, nation)
    prefix = NATIONS[nation]
    cmd = [
        "mapshaper", str(source),
        "-filter", f"id.charAt(0) == '{prefix}'",
        "-o", str(out), "format=topojson",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"mapshaper failed:\n{result.stderr}")

    feature_count = _count_features(out)
    size_mb = out.stat().st_size / 1e6
    meta = {
        "source": {"file": str(source)},
        "processing": {
            "filter": f"id starts with '{prefix}' ({nation})",
            "processed": date.today().isoformat(),
        },
        "output": {
            "file": str(out),
            "format": "topojson",
            "objects_key": "geog",
            "feature_count": feature_count,
            "output_size_mb": round(size_mb, 2),
        },
    }
    meta_path = METADATA_DIR / out
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"  {nation}: {feature_count:>6,} features  {size_mb:6.2f} MB → {out}")
    return out


def main():
    for src in SUBSET_SOURCES:
        source = Path(src)
        coverage = re.search(r"_(UK|GB|EW)_", source.name).group(1)
        print(source)
        for nation in COVERAGE_NATIONS[coverage]:
            build_subset(source, nation)


if __name__ == "__main__":
    main()
