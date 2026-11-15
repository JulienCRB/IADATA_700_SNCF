"""Page 3: Saisonnalité."""

import streamlit as st
from utils import get_data

from railinsight.regularite import Regularite
from railinsight.viz.charts import contributions_saison_bar

st.title("🌡️ Quand les retards apparaissent-ils ?")

st.markdown("""
Analyse de la saisonnalité et de l'impact sur les causes de retard.
""")

contributions = Regularite(get_data()).contributions_par_saison()

st.plotly_chart(contributions_saison_bar(contributions), use_container_width=True)

st.subheader("Contributions au taux de retard")
st.caption(
    "Chaque valeur est la médiane des liaisons nationales pour la saison "
    "concernée. Les liaisons internationales sont exclues."
)

tableau = (
    contributions.mul(100)
    .rename(
        columns={
            "contrib_reseau": "Réseau",
            "contrib_voyageurs": "Voyageurs",
            "contrib_externe": "Externe",
        }
    )
    .rename_axis("Saison")
    .reset_index()
)
st.dataframe(
    tableau.style.format(
        {colonne: "{:.1f} %" for colonne in ("Réseau", "Voyageurs", "Externe")}
    ),
    hide_index=True,
    use_container_width=True,
)
