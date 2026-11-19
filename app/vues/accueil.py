"""Page d'accueil : la question, l'essentiel en quatre chiffres, et où aller ensuite."""

import streamlit as st
from utils import (
    LICENCE_URL,
    SOURCE_URL,
    get_regularite,
    libelle_famille,
    nom_gare,
    tracer_page,
)

from railinsight.analysis.difficulte import gares_concernees

tracer_page("Accueil")

regularite = get_regularite()
debut, fin = regularite.periode
poids = regularite.contribution_mediane()
premiere_cause = regularite.contributions_par_liaison()["cause_dominante"].value_counts(
    normalize=True
)
bilan = regularite.liaisons_en_difficulte()
saisons = regularite.contributions_par_saison()["total"]
gares = gares_concernees(bilan)

st.title("🚄 RailInsight")
st.markdown("""
### Votre TGV sera-t-il à l'heure ? Et sinon, à cause de quoi ?

RailInsight analyse les retards des TGV, liaison par liaison, à partir des données
publiques de la SNCF : d'où ils viennent (le réseau, les trains, les aléas
extérieurs), quelles liaisons vont mal durablement, et à quelle saison.
""")

st.subheader("L'essentiel en quatre chiffres")
cartes = st.columns(4)
with cartes[0].container(border=True):
    st.metric(
        "TGV en retard, sur 100",
        f"{round(poids.sum() * 100)}",
        help="Liaison typique : la liaison du milieu quand on les range de la "
        "meilleure à la moins bonne. Détails : page « Données et limites ».",
    )
    st.caption("Sur une liaison typique, de 2018 à 2026.")
with cartes[1].container(border=True):
    cause = premiere_cause.idxmax()
    st.metric("Cause principale des retards", libelle_famille(cause))
    st.caption(f"1re cause sur {premiere_cause.max() * 100:.0f} % des liaisons.")
with cartes[2].container(border=True):
    st.metric(
        "Liaisons en difficulté",
        f"{int(bilan['en_difficulte'].sum())} / {len(bilan)}",
    )
    st.caption(
        f"Surtout autour de {nom_gare(gares.index[0])} et {nom_gare(gares.index[1])}."
        if len(gares) >= 2
        else "Plus de retards que les autres, année après année."
    )
with cartes[3].container(border=True):
    st.metric("Saison la plus difficile", saisons.idxmax().capitalize())
    st.caption(f"{saisons.max() * 100:.0f} TGV en retard sur 100.")

st.subheader("Que voulez-vous savoir ?")
questions = st.columns(2)
questions[0].markdown("""
- 🔍 **Mon trajet est-il fiable ?** → *Ma liaison* : sa note sur 5 étoiles, ses
  chiffres et leur évolution.
- 📊 **D'où viennent les retards ?** → *D'où viennent les retards ?* : le réseau, les
  trains et les gares, ou les aléas extérieurs.
""")
questions[1].markdown("""
- 🚨 **Quelles liaisons vont mal ?** → *Liaisons en difficulté* : la carte et
  l'évolution en 2026.
- 🌡️ **Quand partir ?** → *Saisons* : les retards et leurs causes selon la saison.
""")
st.caption("Toutes les pages sont accessibles depuis le menu à gauche.")

st.divider()
st.caption(
    f"Source : [Régularité mensuelle TGV par liaisons]({SOURCE_URL}), SNCF "
    f"Voyageurs, licence [ODbL]({LICENCE_URL}), de {debut} à {fin}. Les causes sont "
    "celles déclarées par la SNCF ; les chiffres décrivent des liaisons, jamais un "
    "total du réseau (un même TGV compte dans plusieurs liaisons). Méthode et "
    "limites : page *Données et limites*."
)
