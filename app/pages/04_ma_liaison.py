"""Page 4: Ma liaison."""

import pandas as pd
import streamlit as st
from utils import get_data, get_map_data

from railinsight.regularite import Regularite
from railinsight.viz.charts import ROUTE_COLUMNS, network_map

st.title("🔍 Ma liaison")

st.markdown("Choisis une liaison nationale pour consulter sa fiabilité récente.")

scores = Regularite(get_data()).score_fiabilite()
liaisons = scores.dropna(subset=["score_fiabilite"])

options = liaisons.index.tolist()
libelles = [f"{depart} → {arrivee}" for depart, arrivee in options]
choix = st.selectbox("Liaison TGV", libelles)
liaison = options[libelles.index(choix)]
indicateurs = liaisons.loc[liaison]

st.caption(
    f"Classe de durée : {indicateurs['classe_duree']} · "
    "Calculé sur les 12 derniers mois disponibles."
)

score, retards, annulations, retard_moyen = st.columns(4)
score_help = "Plus bas = plus fiable parmi les liaisons de durée similaire."
score_value = f"{indicateurs['score_fiabilite']:.0%}"
score.metric("Score comparatif", score_value, help=score_help)
retards.metric("Trains en retard", f"{indicateurs['part_retard']:.1%}")
annulations.metric("Trains annulés", f"{indicateurs['taux_annulation']:.1%}")
retard_moyen_value = f"{indicateurs['retard_moyen_tous_trains']:.1f} min"
retard_moyen.metric("Retard moyen", retard_moyen_value)

part_interne = indicateurs["part_origine_interne"]
part_affichee = "Indisponible" if pd.isna(part_interne) else f"{part_interne:.1%}"
st.metric("Part interne (Réseau + Voyageurs)", part_affichee)

_, stations = get_map_data()
route_selectionnee = pd.DataFrame([liaison], columns=ROUTE_COLUMNS)
st.subheader("Trajet sélectionné")
st.plotly_chart(network_map(route_selectionnee, stations), use_container_width=True)
