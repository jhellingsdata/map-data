"""
Quick map viewer for local TopoJSON files using Altair.

Usage:
    uv run python examples/view_map.py gbr/LAD_UK_2024_05.json
    uv run python examples/view_map.py gbr/LAD_UK_2024_05.json gbr/LSOA_EW_2021.json
    uv run python examples/view_map.py gbr/LAD_UK_2024_05.json --color id
    uv run python examples/view_map.py gbr/LAD_UK_2024_05.json --save

Opens a browser window with an interactive map. Pass multiple files to compare
them side-by-side. Use --save to write a standalone HTML file instead.

All TopoJSON files in this repo use the 'geog' objects key.
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

import altair as alt


def load_topo(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def make_chart(topo: dict, title: str, color_field: str | None = None) -> alt.Chart:
    data = alt.InlineData(values=topo, format=alt.DataFormat(feature="geog", type="topojson"))

    if color_field:
        color = alt.Color(f"{color_field}:N", legend=None)
        tooltip = [alt.Tooltip("id:N"), alt.Tooltip("name:N")]
    else:
        color = alt.value("#d0d0d0")
        tooltip = [alt.Tooltip("id:N"), alt.Tooltip("name:N")]

    return (
        alt.Chart(data)
        .mark_geoshape(stroke="white", strokeWidth=0.4)
        .encode(color=color, tooltip=tooltip)
        .project(type="mercator")
        .properties(width=500, height=600, title=title)
    )


def main():
    parser = argparse.ArgumentParser(description="View TopoJSON map files with Altair")
    parser.add_argument("files", nargs="+", help="Path(s) to TopoJSON file(s)")
    parser.add_argument("--color", metavar="FIELD",
                        help="Property to colour by (e.g. 'id'). Defaults to plain grey.")
    parser.add_argument("--save", action="store_true",
                        help="Save HTML alongside the input file instead of opening browser")
    args = parser.parse_args()

    charts = []
    for fpath in args.files:
        path = Path(fpath)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)
        topo = load_topo(path)
        n_features = _count_features(topo)
        title = f"{path.stem}  ({n_features:,} features)"
        charts.append(make_chart(topo, title, args.color))

    combined = alt.hconcat(*charts) if len(charts) > 1 else charts[0]

    # Determine output path
    first = Path(args.files[0])
    out_path = first.parent / f"{first.stem}_preview.html"

    combined.save(str(out_path))
    print(f"Saved → {out_path}")

    if not args.save:
        webbrowser.open(f"file://{out_path.resolve()}")


def _count_features(topo: dict) -> int:
    for layer in topo.get("objects", {}).values():
        return len(layer.get("geometries", []))
    return 0


if __name__ == "__main__":
    main()
