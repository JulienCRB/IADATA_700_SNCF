"""Page 6: Carte du réseau."""

import pandas as pd
import streamlit as st

from railinsight.config import DATA_DIR, ROUTE_COLUMNS, STATIONS_PATH
from railinsight.data.quality import normaliser_noms
from railinsight.viz.charts import network_map, station_ranking


@st.cache_data
def load_routes() -> pd.DataFrame:
    """Liste des liaisons distinctes, noms de gares normalisés."""
    routes = pd.read_csv(
        DATA_DIR / "1_raw" / "regularite-mensuelle-tgv-aqst.csv",
        usecols=list(ROUTE_COLUMNS),
    ).drop_duplicates()
    for column in ROUTE_COLUMNS:
        routes[column] = normaliser_noms(routes[column])
    return routes


@st.cache_data
def load_stations() -> pd.DataFrame:
    """Coordonnées des gares."""
    return pd.read_csv(STATIONS_PATH)


st.title("🗺️ Carte du réseau")

st.markdown("""
Toutes les liaisons TGV présentes dans les données, sens aller et retour confondus.
""")

routes = load_routes()
st.plotly_chart(network_map(routes, load_stations()), use_container_width=True)

st.subheader("Gares les mieux desservies")
st.plotly_chart(station_ranking(routes), use_container_width=True)
