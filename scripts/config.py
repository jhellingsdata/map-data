"""
Boundary type configurations for ONS GeoPortal data.

Each entry defines how to find, download, and process a specific boundary type.

Key fields:
  title_keywords    - All must appear in the ONS catalog title (case-insensitive)
  edition_keyword   - Boundary version to target (BGC = Generalised Clipped,
                      BFC = Full resolution Clipped to coastline)
  id_pattern        - Regex matched against shapefile fields to find the code column
  name_pattern      - Regex matched against shapefile fields to find the name column
  extra_fields      - Additional columns to keep: {target_name: source_field_regex}
  simplification_pct- % of vertices to keep (None = no simplification)
  output_dir        - Relative output directory (default 'gbr', full-res use 'gbr/full')
  title_exclude     - Optional extra title substrings to skip (on top of TITLE_EXCLUDE)
"""

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

# Maps coverage keywords found in ONS titles → short code used in output filenames
COVERAGE_MAP = [
    ("England and Wales", "EW"),
    ("Great Britain", "GB"),
    ("Northern Ireland", "NIR"),
    ("Scotland", "SCT"),
    ("Wales", "WLS"),
    ("England", "ENG"),
    (r"\bUK\b", "UK"),
    (r"\bGB\b", "GB"),
    (r"\bEW\b", "EW"),
    (r"\bEN\b", "ENG"),
]

# Output filenames follow: {PREFIX}_{COVERAGE}_{YEAR}[_{MONTH}].json
# MONTH is only appended when > 1 edition is released per year (LAD, PCON etc.)

BOUNDARY_CONFIGS = {
    # ------------------------------------------------------------------
    # Administrative
    # ------------------------------------------------------------------
    "LAD": {
        "name": "Local Authority Districts",
        "title_keywords": ["Local Authority Districts"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"LAD\d{2}CD",
        "name_pattern": r"LAD\d{2}NM",
        "extra_fields": {},
        # 8% of BGC ≈ 0.4 MB for the UK; 5% (as older files) gets angular when zoomed to a city
        "simplification_pct": 8,
        "output_prefix": "LAD",
        "output_dir": "gbr",
        "versioned_by_month": True,
    },

    "LAD_BFC": {
        "name": "Local Authority Districts (Full Resolution)",
        "title_keywords": ["Local Authority Districts"],
        "edition_keyword": "BFC",
        "coverage_default": "UK",
        "id_pattern": r"LAD\d{2}CD",
        "name_pattern": r"LAD\d{2}NM",
        "extra_fields": {"area": r"Shape_+Area"},
        "simplification_pct": 50,
        "output_prefix": "LAD",
        "output_dir": "gbr/full",
        "versioned_by_month": True,
        "download_page_size": 25,
    },

    "CAUTH": {
        "name": "Combined Authorities",
        "title_keywords": ["Combined Authorities"],
        "edition_keyword": "BGC",
        "coverage_default": "ENG",
        "id_pattern": r"CAUTH\d{2}CD",
        "name_pattern": r"CAUTH\d{2}NM",
        "extra_fields": {},
        # Only ~15 large regional shapes, so file size is never a concern
        "simplification_pct": 30,
        "output_prefix": "CAUTH",
        "output_dir": "gbr",
        "versioned_by_month": True,
    },

    "CAUTH_BFC": {
        "name": "Combined Authorities (Full Resolution)",
        "title_keywords": ["Combined Authorities"],
        "edition_keyword": "BFC",
        "coverage_default": "ENG",
        "id_pattern": r"CAUTH\d{2}CD",
        "name_pattern": r"CAUTH\d{2}NM",
        "extra_fields": {"area": r"Shape_+Area"},
        "simplification_pct": 50,
        "output_prefix": "CAUTH",
        "output_dir": "gbr/full",
        "versioned_by_month": True,
        # Each shape is a union of LADs at full resolution — fetch a few at a time
        "download_page_size": 5,
    },

    # Upper-tier local authorities: English counties (E10) plus every unitary-level
    # authority, which shares its LAD code and area
    "CTYUA": {
        "name": "Counties and Unitary Authorities",
        "title_keywords": ["Counties and Unitary Authorities"],
        "edition_keyword": "BGC",
        # Variant that adds metropolitan county shapes; would overwrite the same filename
        "title_exclude": ["inc Metropolitan Counties"],
        "coverage_default": "UK",
        "id_pattern": r"CTYUA\d{2}CD",
        "name_pattern": r"CTYUA\d{2}NM",
        "extra_fields": {},
        # Same source scale as LAD BGC, so the same percentage
        "simplification_pct": 8,
        "output_prefix": "CTYUA",
        "output_dir": "gbr",
        "versioned_by_month": True,
    },

    "CTYUA_BFC": {
        "name": "Counties and Unitary Authorities (Full Resolution)",
        "title_keywords": ["Counties and Unitary Authorities"],
        "edition_keyword": "BFC",
        "title_exclude": ["inc Metropolitan Counties"],
        "coverage_default": "UK",
        "id_pattern": r"CTYUA\d{2}CD",
        "name_pattern": r"CTYUA\d{2}NM",
        "extra_fields": {"area": r"Shape_+Area"},
        "simplification_pct": 50,
        "output_prefix": "CTYUA",
        "output_dir": "gbr/full",
        "versioned_by_month": True,
        "download_page_size": 10,
    },

    # ------------------------------------------------------------------
    # Census output areas
    # ------------------------------------------------------------------
    "LSOA": {
        "name": "Lower Layer Super Output Areas",
        "title_keywords": ["Lower Layer Super Output Areas"],
        "edition_keyword": "BGC",
        "coverage_default": "EW",
        "id_pattern": r"LSOA\d{2}CD",
        "name_pattern": r"LSOA\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 20,
        "output_prefix": "LSOA",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
    "LSOA_BFC": {
        "name": "Lower Layer Super Output Areas (Full Resolution)",
        "title_keywords": ["Lower Layer Super Output Areas"],
        # BFC = Full resolution, Clipped to coastline
        "edition_keyword": "BFC",
        "coverage_default": "EW",
        "id_pattern": r"LSOA\d{2}CD",
        "name_pattern": r"LSOA\d{2}NM",
        # Shape_+Area matches both Shape_Area and Shape__Area (ONS uses double underscore)
        "extra_fields": {"area": r"Shape_+Area"},
        # Fully unsimplified BFC produces ~150MB TopoJSON — too large for GitHub.
        # 50% gave 82MB (over GitHub's 50MB warning); 25% gives ~46MB with no visible
        # difference when zoomed to a borough.
        "simplification_pct": 25,
        "output_prefix": "LSOA",
        "output_dir": "gbr/full",
        "versioned_by_month": False,
        # Full-resolution geometry is large; smaller page size avoids 504 timeouts
        "download_page_size": 500,
    },
    "MSOA": {
        "name": "Middle Layer Super Output Areas",
        "title_keywords": ["Middle Layer Super Output Areas"],
        "edition_keyword": "BGC",
        "coverage_default": "EW",
        "id_pattern": r"MSOA\d{2}CD",
        "name_pattern": r"MSOA\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 30,
        "output_prefix": "MSOA",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
    "MSOA_BFC": {
        "name": "Middle Layer Super Output Areas (Full Resolution)",
        "title_keywords": ["Middle Layer Super Output Areas"],
        "edition_keyword": "BFC",
        "coverage_default": "EW",
        "id_pattern": r"MSOA\d{2}CD",
        "name_pattern": r"MSOA\d{2}NM",
        "extra_fields": {"area": r"Shape_+Area"},
        "simplification_pct": 50,
        "output_prefix": "MSOA",
        "output_dir": "gbr/full",
        "versioned_by_month": False,
        "download_page_size": 500,
    },

    # ------------------------------------------------------------------
    # OECD/Eurostat ITL
    # ------------------------------------------------------------------
    "ITL1": {
        "name": "International Territorial Level 1",
        "title_keywords": ["International Territorial Level 1"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"ITL1\d{2}CD",
        "name_pattern": r"ITL1\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 60,
        "output_prefix": "ITL1",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
    "ITL2": {
        "name": "International Territorial Level 2",
        "title_keywords": ["International Territorial Level 2"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"ITL2\d{2}CD",
        "name_pattern": r"ITL2\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 60,
        "output_prefix": "ITL2",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
    "ITL3": {
        "name": "International Territorial Level 3",
        "title_keywords": ["International Territorial Level 3"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"ITL3\d{2}CD",
        "name_pattern": r"ITL3\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 50,
        "output_prefix": "ITL3",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },

    # ------------------------------------------------------------------
    # Electoral
    # ------------------------------------------------------------------
    "PCON": {
        "name": "Westminster Parliamentary Constituencies",
        "title_keywords": ["Westminster Parliamentary Constituencies"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"PCON\d{2}CD",
        "name_pattern": r"PCON\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 50,
        "output_prefix": "ELE_MP",
        "output_dir": "gbr",
        "versioned_by_month": True,
    },

    # ------------------------------------------------------------------
    # NUTS (legacy Eurostat classification)
    # ------------------------------------------------------------------
    "NUTS1": {
        "name": "NUTS Level 1",
        "title_keywords": ["NUTS Level 1", "NUTS1"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"nuts1\d{2}cd|NUTS1\d{2}CD",
        "name_pattern": r"nuts1\d{2}nm|NUTS1\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 60,
        "output_prefix": "NUTS1",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
    "NUTS2": {
        "name": "NUTS Level 2",
        "title_keywords": ["NUTS Level 2", "NUTS2"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"nuts2\d{2}cd|NUTS2\d{2}CD",
        "name_pattern": r"nuts2\d{2}nm|NUTS2\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 60,
        "output_prefix": "NUTS2",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
    "NUTS3": {
        "name": "NUTS Level 3",
        "title_keywords": ["NUTS Level 3", "NUTS3"],
        "edition_keyword": "BGC",
        "coverage_default": "UK",
        "id_pattern": r"nuts3\d{2}cd|NUTS3\d{2}CD",
        "name_pattern": r"nuts3\d{2}nm|NUTS3\d{2}NM",
        "extra_fields": {},
        "simplification_pct": 50,
        "output_prefix": "NUTS3",
        "output_dir": "gbr",
        "versioned_by_month": False,
    },
}

# Columns to retain from the ONS Hub catalog CSV
CATALOG_COLUMNS = ["id", "created", "modified", "title", "type", "description", "tags", "snippet", "categories", "url"]

# Catalog titles containing these are never processed:
#   (WGS84)       - re-publishes of BNG datasets; Shape__Area is in square degrees,
#                   and the BNG original is always listed alongside
#   (Parts)       - historic part-districts, would collide with the main file name
#   Census Merged - 2011 merged districts, would collide with LAD_EW_2011_12
TITLE_EXCLUDE = ["(WGS84)", "(Parts)", "Census Merged"]

# Only these ArcGIS item types contain downloadable vector boundaries
VALID_ITEM_TYPES = {"Feature Service", "Feature Layer", "Map Service"}
