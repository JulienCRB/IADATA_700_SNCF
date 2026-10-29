"""Page 6: Carte du réseau."""

import pandas as pd
import streamlit as st
from utils import get_data

from railinsight.data.loader import GARES, load
from railinsight.data.preprocessing import preprocess_gares, preprocess_regularite
from railinsight.data.quality import normaliser_noms
from railinsight.viz.charts import ROUTE_COLUMNS, network_map, station_ranking


@st.cache_data
def load_map_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Liaisons distinctes et coordonnées des gares, via le preprocessing commun."""
    gares = preprocess_gares(load(GARES))
    regularite = preprocess_regularite(get_data(), gares)

    names = pd.concat(
        [
            pd.DataFrame(
                {
                    "gare": normaliser_noms(regularite[column]),
                    "code_uic": regularite[f"uic_{sens}"],
                }
            )
            for column, sens in zip(ROUTE_COLUMNS, ("depart", "arrivee"))
        ]
    ).drop_duplicates()
    stations = names.merge(
        gares[["code_uic", "x_wgs84", "y_wgs84"]].astype({"code_uic": "Int64"}),
        on="code_uic",
    ).rename(columns={"x_wgs84": "longitude", "y_wgs84": "latitude"})

    routes = regularite[list(ROUTE_COLUMNS)].drop_duplicates()
    for column in ROUTE_COLUMNS:
        routes[column] = normaliser_noms(routes[column])
    return routes, stations.drop_duplicates(subset="gare")


st.title("🗺️ Carte du réseau")

st.markdown("""
Toutes les liaisons TGV présentes dans les données, sens aller et retour confondus.
""")

routes, stations = load_map_data()
st.plotly_chart(network_map(routes, stations), use_container_width=True)

st.subheader("Gares les mieux desservies")
st.plotly_chart(station_ranking(routes), use_container_width=True)
