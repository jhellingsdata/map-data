### Altair code example for TopoJSON
import altair as alt

topo_url = "https://raw.githubusercontent.com/jhellingsdata/map-data/refs/heads/main/gbr/ITL1_UK_2021.json"
data = alt.Data(url=topo_url, format=alt.DataFormat(feature='geog', type='topojson'))

alt.Chart(data).mark_geoshape().project(
    type='mercator'     # Find other projections here: https://vega.github.io/vega/docs/projections/
)