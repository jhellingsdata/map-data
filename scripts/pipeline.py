"""
End-to-end pipeline CLI for fetching and processing ONS boundary data.

Usage:
    uv run python -m scripts.pipeline catalog              # refresh catalog
    uv run python -m scripts.pipeline search LAD           # list available LAD versions
    uv run python -m scripts.pipeline search all           # list all supported types
    uv run python -m scripts.pipeline process LAD          # process latest LAD
    uv run python -m scripts.pipeline process LAD --all    # process all available LAD versions
    uv run python -m scripts.pipeline process all          # process latest of every type
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.catalog import fetch_catalog
from scripts.config import BOUNDARY_CONFIGS
from scripts.fetch import (
    build_output_filename,
    download_boundary,
    find_shapefile,
    search_catalog,
)
from scripts.process import (
    build_metadata,
    detect_fields,
    get_mapshaper_version,
    process_boundary,
)

METADATA_DIR = Path("metadata")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_catalog(args):
    fetch_catalog(force_refresh=args.refresh)


def cmd_search(args):
    df = fetch_catalog()
    types_to_search = (
        list(BOUNDARY_CONFIGS.keys()) if args.boundary_type.lower() == "all"
        else [args.boundary_type.upper()]
    )
    for btype in types_to_search:
        results = search_catalog(df, btype)
        cfg = BOUNDARY_CONFIGS[btype]
        print(f"\n{'─' * 60}")
        print(f"{btype}  ({cfg['name']})  —  {len(results)} matches")
        print(f"{'─' * 60}")
        if results.empty:
            print("  No matches found.")
        else:
            for _, row in results.iterrows():
                title = row.get("title", "")
                item_id = row.get("id", "")
                try:
                    fname = build_output_filename(btype, title)
                    out_path = Path(cfg.get("output_dir", "gbr")) / fname
                    exists = "✓" if out_path.exists() else " "
                except ValueError:
                    fname = "(date not parseable)"
                    exists = " "
                print(f"  [{exists}] [{item_id}]  {title}")
                print(f"        → {Path(cfg.get('output_dir', 'gbr')) / fname if fname != '(date not parseable)' else fname}")


def cmd_process(args):
    df = fetch_catalog()
    mapshaper_ver = get_mapshaper_version()

    types_to_process = (
        list(BOUNDARY_CONFIGS.keys()) if args.boundary_type.lower() == "all"
        else [args.boundary_type.upper()]
    )

    for btype in types_to_process:
        cfg = BOUNDARY_CONFIGS[btype]
        output_dir = Path(cfg.get("output_dir", "gbr"))
        results = search_catalog(df, btype)

        if results.empty:
            print(f"\n[{btype}] No catalog matches — skipping.")
            continue

        iterate_all = args.all or (args.count is not None)
        rows = results if iterate_all else results.iloc[:1]
        new_count = 0

        for _, row in rows.iterrows():
            title = row.get("title", "")
            item_id = row.get("id", "")
            source_url = row.get("url", "")

            print(f"\n{'=' * 60}")
            print(f"[{btype}] {title}")
            print(f"  id: {item_id}")

            try:
                output_filename = build_output_filename(btype, title)
            except ValueError as e:
                print(f"  Skipping: {e}")
                continue

            output_path = output_dir / output_filename
            # Metadata mirrors the data path: gbr/full/X.json → metadata/gbr/full/X.json
            metadata_path = METADATA_DIR / output_path

            if output_path.exists() and not args.force:
                print(f"  Already exists: {output_path}  (use --force to overwrite)")
                continue

            # Download
            try:
                extract_dir = download_boundary(
                    item_id,
                    page_size=cfg.get("download_page_size", 2000),
                )
                shp_path = find_shapefile(extract_dir)
            except (RuntimeError, FileNotFoundError) as e:
                print(f"  Download failed: {e}")
                continue

            # Detect source field names
            try:
                id_field, name_field, extra_fields = detect_fields(
                    shp_path,
                    cfg["id_pattern"],
                    cfg["name_pattern"],
                    cfg.get("extra_fields"),
                )
            except (RuntimeError, ValueError) as e:
                print(f"  Field detection failed: {e}")
                continue

            print(f"  id field: {id_field}  |  name field: {name_field}")
            if extra_fields:
                print(f"  extra fields: {extra_fields}")

            # Process
            try:
                feature_count, source_mb, output_mb = process_boundary(
                    shp_path,
                    id_field,
                    name_field,
                    output_path,
                    simplification_pct=cfg.get("simplification_pct"),
                    extra_fields=extra_fields,
                )
            except RuntimeError as e:
                print(f"  Processing failed: {e}")
                continue

            # Save metadata
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            meta = build_metadata(
                boundary_type=btype,
                source_id=item_id,
                source_title=title,
                source_url=source_url,
                id_field=id_field,
                name_field=name_field,
                extra_fields=extra_fields,
                simplification_pct=cfg.get("simplification_pct"),
                output_file=str(output_path),
                feature_count=feature_count,
                source_size_mb=source_mb,
                output_size_mb=output_mb,
                mapshaper_version=mapshaper_ver,
            )
            with open(metadata_path, "w") as f:
                json.dump(meta, f, indent=2)
            print(f"  Metadata → {metadata_path}")
            new_count += 1
            if args.count is not None and new_count >= args.count:
                print(f"  Reached --count {args.count} limit.")
                break

    print("\nDone.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and process ONS boundary data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_catalog = sub.add_parser("catalog", help="Fetch / refresh the ONS catalog")
    p_catalog.add_argument("--refresh", action="store_true", help="Force re-download even if cached")
    p_catalog.set_defaults(func=cmd_catalog)

    p_search = sub.add_parser("search", help="Search catalog for available boundary versions")
    p_search.add_argument("boundary_type", help="Boundary type (e.g. LAD, LSOA) or 'all'")
    p_search.set_defaults(func=cmd_search)

    p_process = sub.add_parser("process", help="Download and process boundary files")
    p_process.add_argument("boundary_type", help="Boundary type (e.g. LAD) or 'all'")
    p_process.add_argument("--all", action="store_true", dest="all",
                            help="Process all available versions, not just the latest")
    p_process.add_argument("--count", type=int, default=None, metavar="N",
                            help="Process at most N new (non-existing) files from the top of results")
    p_process.add_argument("--force", action="store_true",
                            help="Overwrite existing output files")
    p_process.set_defaults(func=cmd_process)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
