### Altair code example for GeoJSON
import altair as alt

geo_url = "https://raw.githubusercontent.com/jhellingsdata/jhellingsdata.github.io/refs/heads/main/Data/UK%20Map%20Data/MSOA_2021_200m.geojson"
data = alt.Data(url=geo_url, format=alt.DataFormat(property='features', type='json'))

alt.Chart(data).mark_geoshape().project(
    type='mercator'     # Find other projections here: https://vega.github.io/vega/docs/projections/
)