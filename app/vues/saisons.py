"""Page « Saisons » : quand les causes de retard pèsent-elles le plus (Phase 3) ?"""

import streamlit as st
from utils import LIBELLES_FAMILLES, get_regularite, libelle_famille, tracer_page

from railinsight.viz.charts import contributions_saison_bar

#: Icône et nom avec article de chaque saison.
ICONES = {"hiver": "❄️", "printemps": "🌸", "été": "☀️", "automne": "🍂"}
AVEC_ARTICLE = {
    "hiver": "l'hiver",
    "printemps": "le printemps",
    "été": "l'été",
    "automne": "l'automne",
}

tracer_page("Saisons")

contributions = get_regularite().contributions_par_saison()
familles = contributions.drop(columns="total")
plus_dure = contributions["total"].idxmax()
plus_calme = contributions["total"].idxmin()

st.title("🌡️ Quand les retards apparaissent-ils ?")
st.markdown(
    f"Les retards varient selon la saison : **{AVEC_ARTICLE[plus_dure]} est la "
    f"saison la plus difficile**, **{AVEC_ARTICLE[plus_calme]} la plus calme**. Et "
    "la cause principale n'est pas toujours la même."
)

for colonne, (saison, ligne) in zip(st.columns(4), contributions.iterrows()):
    with colonne.container(border=True):
        st.markdown(f"#### {ICONES[saison]} {saison.capitalize()}")
        st.metric("Trains en retard, sur 100", f"≈ {ligne['total'] * 100:.0f}")
        cause = familles.loc[saison].idxmax().removeprefix("contrib_")
        st.markdown(f"1re cause : **{libelle_famille(cause)}**")

st.subheader("Saison par saison, d'où viennent les retards ?")
st.plotly_chart(
    contributions_saison_bar(contributions, LIBELLES_FAMILLES), width="stretch"
)
st.markdown("""
- Le **réseau** est la première cause en hiver, au printemps et en automne.
- L'**été**, ce sont les **trains et les gares** qui passent devant. C'est cohérent
  avec l'affluence des vacances, mais ce n'est qu'une hypothèse : les données
  disent d'où viennent les retards, pas pourquoi.
- Les **aléas extérieurs** pèsent à peu près autant toute l'année.
""")

with st.expander("ℹ️ Bon à savoir avant de conclure"):
    st.markdown("""
- Ce sont les chiffres d'une **liaison typique** (la médiane des liaisons
  françaises) : la moitié des liaisons font mieux, l'autre moitié moins bien.
- Toutes les années de 2018 à 2026 sont réunies : une année exceptionnelle peut
  peser sur une saison.
- Les saisons sont météorologiques : l'hiver va de décembre à février, le printemps
  de mars à mai, l'été de juin à août, l'automne de septembre à novembre.
- Les liaisons internationales ne sont pas incluses (données peu fiables).
""")

with st.expander("📋 Les valeurs"):
    st.dataframe(
        (contributions * 100).round(1).rename(index=str.capitalize),
        column_config={
            "contrib_reseau": "Réseau",
            "contrib_voyageurs": "Trains et gares",
            "contrib_externe": "Aléas extérieurs",
            "total": "Total en retard",
        },
    )
    st.caption(
        "Trains en retard sur 100 trains circulés, pour une liaison typique. Le total "
        "est celui de la liaison typique : il n'est pas exactement la somme des "
        "trois colonnes."
    )