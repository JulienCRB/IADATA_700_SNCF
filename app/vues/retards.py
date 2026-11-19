"""Page « D'où viennent les retards ? » : le poids de chaque famille de causes."""

import streamlit as st
from utils import LIBELLES_FAMILLES, get_regularite, pourcent, tracer_page

from railinsight.analysis.causes import (
    liaisons_les_plus_touchees,
    repartition_par_niveau,
)
from railinsight.viz.charts import niveaux_par_famille_bar, retards_sur_100_bar

tracer_page("D'où viennent les retards ?")

regularite = get_regularite()
contributions = regularite.contributions_par_liaison()
premiere_cause = contributions["cause_dominante"].value_counts(normalize=True)
poids = regularite.contribution_mediane()
repartition = repartition_par_niveau(contributions)
plus_touchees = liaisons_les_plus_touchees(contributions)

#: Présentation grand public de chaque famille de causes.
FAMILLES = {
    "reseau": (
        "🛤️ Le réseau",
        "Voies, caténaires, signalisation, travaux, régulation du trafic "
        "(SNCF Réseau).",
    ),
    "voyageurs": (
        "🚆 Les trains et les gares",
        "Pannes de train, organisation en gare, montée et descente des voyageurs "
        "(SNCF Voyageurs).",
    ),
    "externe": (
        "🌧️ Les aléas extérieurs",
        "Météo, obstacles sur les voies, malveillance, grèves…",
    ),
}

st.title("📊 D'où viennent les retards ?")
st.markdown(
    f"Sur une liaison TGV typique, **environ {round(poids.sum() * 100)} trains sur "
    "100 arrivent en retard**. Voici à quoi ils sont dus."
)

st.plotly_chart(retards_sur_100_bar(poids, LIBELLES_FAMILLES), width="stretch")
st.caption(
    "Liaison typique (médiane des liaisons françaises), de 2018 à 2026 ; nombres "
    "arrondis. Les autres trains arrivent à l'heure."
)

st.subheader("Trois familles de causes")
for colonne, (famille, (titre, description)) in zip(st.columns(3), FAMILLES.items()):
    with colonne.container(border=True):
        st.markdown(f"#### {titre}")
        st.caption(description)
        st.metric(
            "Trains en retard, sur 100",
            f"≈ {poids[famille] * 100:.0f}",
            help="Liaison typique : la moitié des liaisons font plus, l'autre "
            "moitié moins.",
        )
        part = premiere_cause.get(famille, 0)
        if part > 0:
            st.markdown(
                f"**1re cause de retard** sur **{pourcent(part)}** des liaisons"
            )
        else:
            st.markdown("Jamais la 1re cause, mais **présent sur toutes les liaisons**")

st.subheader("Est-ce pareil sur toutes les liaisons ?")
st.markdown(
    "Non. Pour chaque cause, voici sur combien de liaisons elle provoque **peu** "
    "(vert) ou **beaucoup** (rouge) de retards."
)
st.plotly_chart(
    niveaux_par_famille_bar(repartition, LIBELLES_FAMILLES), width="stretch"
)

beaucoup = repartition[["6 à 9", "9 ou plus"]].sum(axis=1)
st.markdown(
    f"- Le **réseau** est la cause la plus inégale : sur "
    f"**{pourcent(beaucoup['reseau'])}** des liaisons, il provoque 6 retards ou plus "
    "sur 100 trains.\n"
    f"- Les **trains et les gares** pèsent de façon plus régulière "
    f"({pourcent(beaucoup['voyageurs'])} des liaisons à 6 retards ou plus).\n"
    f"- Les **aléas extérieurs** touchent toutes les liaisons, mais rarement "
    f"beaucoup ({pourcent(beaucoup['externe'])} des liaisons à 6 retards ou plus)."
)

st.subheader("Les liaisons les plus touchées")
for colonne, famille in zip(st.columns(3), LIBELLES_FAMILLES):
    with colonne.container(border=True):
        st.markdown(f"**{FAMILLES[famille][0]}**")
        for (depart, arrivee), valeur in plus_touchees[famille].items():
            detail = f"{valeur * 100:.0f} retards sur 100 trains"
            st.markdown(f"{depart} → {arrivee}  \n:gray[{detail}]")

with st.expander("ℹ️ Bon à savoir avant de conclure"):
    st.markdown("""
- **Une seule cause par train** : la SNCF attribue chaque retard à la cause qui a
  fait perdre le plus de temps. Un train retardé par un orage puis par une panne ne
  compte qu'une fois.
- **Le réseau regroupe deux causes de même poids** (infrastructure et régulation du
  trafic). C'est pour cela qu'il arrive si souvent en tête : classée ailleurs, la
  régulation du trafic lui ferait perdre cette première place.
- **Ces chiffres décrivent, ils n'expliquent pas** : ils disent d'où viennent les
  retards déclarés, pas pourquoi.
- Les liaisons internationales ne sont pas incluses (données peu fiables).
""")

with st.expander("📋 Le détail, liaison par liaison"):
    tableau = (contributions.drop(columns="cause_dominante") * 100).round(1)
    tableau["total"] = tableau.sum(axis=1)
    st.dataframe(
        tableau.sort_values("total", ascending=False),
        column_config={
            "contrib_reseau": "Réseau",
            "contrib_voyageurs": "Trains et gares",
            "contrib_externe": "Aléas extérieurs",
            "total": "Total en retard",
        },
    )
    st.caption(
        "Trains en retard sur 100 trains circulés, par famille de causes, de 2018 à "
        "2026. La somme des trois donne le total."
    )
