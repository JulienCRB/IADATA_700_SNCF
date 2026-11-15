"""Page 6: Carte du réseau."""

import streamlit as st
from utils import get_map_data

from railinsight.viz.charts import network_map, station_ranking

st.title("🗺️ Carte du réseau")

st.markdown("""
Toutes les liaisons TGV présentes dans les données, sens aller et retour confondus.
""")

routes, stations = get_map_data()
st.plotly_chart(network_map(routes, stations), use_container_width=True)

st.subheader("Gares les mieux desservies")
st.plotly_chart(station_ranking(routes), use_container_width=True)
