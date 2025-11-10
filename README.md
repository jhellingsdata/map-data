# map-data
Collection of topojson boundaries to be used for building map visualisations



### Available data:

## UK

**Administrative:**
- Local Authority Districts (UK): [May 2024](gbr/LAD_UK_2024_05.json), [Dec 2023](gbr/LAD_UK_2023_12.json), [May 2023](gbr/LAD_UK_2023_05.json), [Dec 2022](gbr/LAD_UK_2022_12.json), [May 2022](gbr/LAD_UK_2022_05.json), [Dec 2021](gbr/LAD_UK_2021_12.json)

**OECD/Eurostat:**
- ITL1 - International Territorial Level 1 (UK): [2025](gbr/ITL1_UK_2025.json), [2021](gbr/ITL1_UK_2021.json)
- ITL2 - International Territorial Level 2 (UK): [2025](gbr/ITL2_UK_2025.json), [2021](gbr/ITL2_UK_2021.json)
- ITL3 - International Territorial Level 3 (UK): [2025](gbr/ITL3_UK_2025.json), [2021](gbr/ITL3_UK_2021.json)
- NUTS1 - Nomenclature of Territorial Units for Statistics 1: (UK [2018](gbr/NUTS1_UK_2018.json)), (England & Wales [2015](gbr/NUTS1_EW_2015.json))
- NUTS2 - Nomenclature of Territorial Units for Statistics 2: (UK [2018](gbr/NUTS2_UK_2018.json)), (England & Wales [2015](gbr/NUTS2_EW_2015.json)), 
- NUTS3 - Nomenclature of Territorial Units for Statistics 3: (UK [2018](gbr/NUTS3_UK_2018.json)), (England & Wales [2015](gbr/NUTS3_EW_2015.json))

**Census:**
- Lower layer Super Output Areas (England & Wales): [2021](gbr/LSOA_EW_2001.json), [2011](gbr/LSOA_EW_2011.json), [2001](gbr/LSOA_EW_2001.json)
- Middle layer Super Output Areas (England & Wales): [2021](gbr/MSOA_EW_2021.json), [2011](gbr/MSOA_EW_2011.json), [2001](gbr/MSOA_EW_2001.json)

**Electoral:**
- Westminster Parliamentary Constituencies (UK): [Jul 2024](gbr/ELE_MP_UK_2024_07.json), [Dec 2021](gbr/ELE_MP_UK_2021_12.json), [Dec 2020](gbr/ELE_MP_UK_2020_12.json), [Dec 2019](gbr/ELE_MP_UK_2019_12.json), [Dec 2018](gbr/ELE_MP_UK_2018_12.json), [Dec 2017](gbr/ELE_MP_UK_2017_12.json), [Dec 2016](gbr/ELE_MP_UK_2016_12.json)
- Westminster Parliamentary Constituencies (GB): [Dec 2015](gbr/ELE_MP_GB_2015_12.json)

## USA
- States: [states_2017](usa/states_2017.json)
- Counties: [counties_2017](usa/counties_2017.json)

#### Cities
- New York: 
    - Boroughs: [boroughs](usa/cities/nyc/boroughs.json)
    - Zip code tabulation areas: [zcta](usa/cities/nyc/zcta.json)


## World
- Countries: [world](world/world.json)

<br>
<br>

## Mapping with TopoJSON in Vega-Lite / Altair

1. Get the raw GitHub file link to any of the TopoJSONs:
    - "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/{folder}/{map_filename}.json"
    - "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/ITL1_UK_2021.json"
    - When viewing large files in GitHub, it may not show a button to access the 'raw' file. In these cases, add `raw=true` to the page URL and it will redirect to the raw link.

Note: all TopoJSONs in this repo use the `geog` feature key. 

In Altair (Python)
```python 
import altair as alt

topo_url = "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/ITL1_UK_2021.json"
data = alt.Data(url=topo_url, format=alt.DataFormat(feature='geog', type='topojson'))

alt.Chart(data).mark_geoshape().project(
    type='mercator'     # Find other projections here: https://vega.github.io/vega/docs/projections/
)
```


In Vega-Lite:
```json
{
    "$schema": "https://vega.github.io/schema/vega-lite/v5.20.1.json",
    "data": {
        "url": "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/ITL1_UK_2021.json",
        "format": {"feature": "geog", "type": "topojson"}
    },
    "mark": {"type": "geoshape"},
    "projection": {"type": "mercator"}
}
```

> TopoJSON works a bit different than GeoJSON in Vega-Lite/Altair. We set the 'feature' instead of the property for xyz..