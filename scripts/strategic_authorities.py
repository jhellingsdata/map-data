"""
Build English Strategic Authority (SA) boundaries and per-SA drill-down files.

Usage:
    uv run python -m scripts.strategic_authorities

Strategic Authorities (mayoral and non-mayoral combined authorities, and the newer
Devolution Priority Programme areas) are not an ONS geography yet, and ONS's CAUTH
files leave out the areas without a combined authority code. So SAs are built here
by dissolving published files, which keeps every border identical to the source:

* gbr/SA_ENG_2025_12.json and gbr/full/SA_ENG_2025_12.json: the 21 SAs, dissolved
  from gbr/LAD_UK_2025_12.json and gbr/full/LAD_UK_2025_12.json (the full one keeps
  `area`, summed from the BFC LAD areas).
* gbr/lookups/SA_ENG_2025_12.csv: one row per SA with its parent and matching areas.
* gbr/sa/<slug>/{SA,LAD,MSOA,LSOA}.json: for each SA, its LSOAs (2021) cut from
  gbr/full/LSOA_EW_2021.json and dissolved up to MSOA, LAD and SA. All four come from
  the same LSOA geometry, so they overlay exactly.

Inputs (scripts/inputs/, written by `msa geographies export-map-data` in the
msa-data repo, which maintains SA membership):

* strategic_authorities.csv: id (MSA code), name, short, cauth_id, rgn_id,
  itl1_id, itl2_id, itl2_2021_id, n_lads
* strategic_authorities_lads.csv: lad_id, lad_name, sa_id, sa_name

Every 2021 LSOA and MSOA lies wholly inside one SA (checked on build), so the
per-SA files are exact cuts, not best fits.
"""

import json
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from scripts.process import _count_features
from scripts.validate import repair_file

INPUTS = Path("scripts/inputs")
AUTHORITIES = INPUTS / "strategic_authorities.csv"
SA_LADS = INPUTS / "strategic_authorities_lads.csv"
METADATA_DIR = Path("metadata")
VINTAGE = "2025_12"  # the LAD boundaries the SAs are dissolved from
SA_FIELDS = ["name", "short", "cauth_id", "rgn_id", "itl1_id", "itl2_id", "itl2_2021_id"]
NATIONAL = {  # output → LAD source
    Path(f"gbr/SA_ENG_{VINTAGE}.json"): Path(f"gbr/LAD_UK_{VINTAGE}.json"),
    Path(f"gbr/full/SA_ENG_{VINTAGE}.json"): Path(f"gbr/full/LAD_UK_{VINTAGE}.json"),
}
LSOA_SOURCE = Path("gbr/full/LSOA_EW_2021.json")
LSOA_LOOKUP = Path("gbr/lookups/LSOA_EW_2021.csv")
LAD_LOOKUP = Path(f"gbr/lookups/LAD_UK_{VINTAGE}.csv")


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


def _report_repairs(out: Path) -> None:
    """Dissolving and re-quantising can create invalid polygons; repair any (scripts/validate.py)."""
    repaired = repair_file(out)
    if repaired:
        print(f"    repaired {len(repaired)} invalid in {out}: {[k for k, _ in repaired][:5]}")


def _write_metadata(out: Path, sources: list[Path], processing: dict) -> None:
    size_mb = out.stat().st_size / 1e6
    meta = {
        "source": {"files": [str(s) for s in sources], "inputs": [str(AUTHORITIES), str(SA_LADS)]},
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


def _check_inputs(authorities: pd.DataFrame, lads: pd.DataFrame) -> None:
    lad_ids = _ids(Path(f"gbr/LAD_UK_{VINTAGE}.json"))
    unknown = set(lads["lad_id"]) - set(lad_ids)
    if unknown:
        raise ValueError(f"SA member LADs not in LAD_UK_{VINTAGE}: {sorted(unknown)}")
    if lads["lad_id"].duplicated().any():
        raise ValueError("a LAD is listed in more than one SA")
    counts = lads.groupby("sa_id").size()
    expected = authorities.set_index("id")["n_lads"]
    if not counts.reindex(expected.index).eq(expected).all():
        raise ValueError(f"member LAD counts disagree with n_lads:\n{counts}\n{expected}")


# ---------------------------------------------------------------------------
# National files
# ---------------------------------------------------------------------------


def build_national(out: Path, source: Path, keep_area: bool) -> Path:
    fields = ["id", *SA_FIELDS] + (["area"] if keep_area else [])
    cmd = [
        "mapshaper", str(source),
        "-join", str(SA_LADS), "keys=id,lad_id", "fields=sa_id", "string-fields=lad_id,sa_id",
        "-filter", "sa_id != null && sa_id !== ''",
        "-dissolve", "sa_id", *(["calc=area=sum(area)"] if keep_area else []),
        "-join", str(AUTHORITIES), "keys=sa_id,id", f"fields={','.join(SA_FIELDS)}",
        f"string-fields=id,{','.join(SA_FIELDS)}",
        "-rename-fields", "id=sa_id",
        "-filter-fields", ",".join(fields),
        "-rename-layers", "geog",
        "-o", str(out), "format=topojson", "fix-geometry",
    ]
    _run(cmd)
    _report_repairs(out)
    _write_metadata(
        out,
        [source],
        {"method": "dissolve member LADs by sa_id (no further simplification)", "fields": fields},
    )
    print(f"  {_count_features(out):>3} SAs  {out.stat().st_size / 1e6:6.2f} MB → {out}")
    return out


def build_sa_lookup(authorities: pd.DataFrame) -> Path:
    """One row per SA: parent region / ITL1 and the areas that exactly match it."""
    lad = pd.read_csv(LAD_LOOKUP, dtype=str)
    rgn = dict(zip(lad["rgn_id"], lad["rgn_name"]))
    itl1 = dict(zip(lad["itl1_id"], lad["itl1_name"]))
    itl2 = dict(zip(lad["itl2_id"], lad["itl2_name"]))
    cauth = dict(zip(lad["cauth_id"], lad["cauth_name"]))
    itl2_2021 = _ids(Path("gbr/ITL2_UK_2021.json"))

    def names(codes: pd.Series, table: dict) -> pd.Series:
        return codes.fillna("").map(lambda c: ";".join(table.get(x, "") for x in c.split(";")) if c else "")

    a = authorities.fillna("")
    df = pd.DataFrame(
        {
            "sa_id": a["id"],
            "sa_name": a["name"],
            "sa_short": a["short"],
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
    )
    path = Path(f"gbr/lookups/SA_ENG_{VINTAGE}.csv")
    df.to_csv(path, index=False)
    print(f"  {len(df)} rows → {path}")
    return path


# ---------------------------------------------------------------------------
# Per-SA drill-down files
# ---------------------------------------------------------------------------


def _lsoa_table(lads: pd.DataFrame) -> pd.DataFrame:
    """LSOA → MSOA → LAD → SA, checking every LSOA and MSOA sits in one SA."""
    lsoa = pd.read_csv(LSOA_LOOKUP, dtype=str).merge(lads[["lad_id", "sa_id"]], on="lad_id", how="left")
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
    authorities = pd.read_csv(AUTHORITIES, dtype=str, keep_default_na=False)
    authorities["n_lads"] = authorities["n_lads"].astype(int)
    lads = pd.read_csv(SA_LADS, dtype=str)
    _check_inputs(authorities, lads)

    print("National SA files")
    for out, source in NATIONAL.items():
        build_national(out, source, keep_area="full" in out.parts)
    build_sa_lookup(authorities)

    print("Per-SA files")
    lsoa = _lsoa_table(lads)
    with tempfile.TemporaryDirectory() as tmp:
        for _, sa in authorities.iterrows():
            build_sa_folder(sa, lsoa, Path(tmp))


if __name__ == "__main__":
    main()
