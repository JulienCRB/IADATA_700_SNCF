"""Page « Ma liaison » : fiabilité, causes et historique d'un trajet (Phase 4)."""

import pandas as pd
import streamlit as st
from utils import (
    LIBELLES_FAMILLES,
    etoiles_texte,
    get_regularite,
    nom_gare,
    pourcent,
)

from railinsight.analysis.reliability import medianes_par_classe
from railinsight.viz.charts import historique_composantes_line, retards_sur_100_bar

#: Verdict affiché, avec sa couleur.
VERDICTS = {
    "plutôt fiable": ("🟢", st.success),
    "dans la moyenne": ("🟡", st.info),
    "peu fiable": ("🔴", st.error),
}
#: Nom grand public de chaque classe de durée.
TRAJETS = {
    "< 1h30": "trajets de moins de 1h30",
    "1h30-3h": "trajets de 1h30 à 3h",
    "> 3h": "trajets de plus de 3h",
}

regularite = get_regularite()
scores = regularite.score_fiabilite()
typiques = medianes_par_classe(scores)
contributions = regularite.contributions_par_liaison()
historique = regularite.historique_composantes()
en_difficulte = regularite.liaisons_en_difficulte()["en_difficulte"]

st.title("🔍 Ma liaison")
st.markdown("Choisissez votre trajet : voici sa fiabilité sur les 12 derniers mois.")

col1, col2 = st.columns(2)
departs = sorted(scores.index.get_level_values("gare_depart").unique())
depart = col1.selectbox("🚉 Je pars de", departs)
arrivee = col2.selectbox("🏁 Je vais à", sorted(scores.loc[depart].index))
liaison = (depart, arrivee)
ligne = scores.loc[liaison]
typique = typiques.loc[ligne["classe_duree"]]
trajets = TRAJETS[ligne["classe_duree"]]

st.subheader(f"{nom_gare(depart)} → {nom_gare(arrivee)}")

# --- Le verdict ----------------------------------------------------------------
if pd.isna(ligne["niveau"]):
    st.warning(
        "**Liaison internationale : pas de verdict.** Ses données sont peu fiables "
        "(retards parfois non renseignés, causes manquantes). Les chiffres ci-dessous "
        "sont donnés à titre indicatif."
    )
else:
    icone, afficher = VERDICTS[ligne["niveau"]]
    comparaison = (
        f"plus fiable que **{pourcent(ligne['plus_fiable_que'])}** des {trajets}"
        if ligne["plus_fiable_que"] > 0
        else f"le **moins fiable** des {trajets}"
    )
    col_note, col_verdict = st.columns([1, 2])
    col_note.metric(
        "Note de fiabilité",
        f"{etoiles_texte(int(ligne['etoiles']))}",
        delta=f"{int(ligne['etoiles'])} / 5",
        delta_color="off",
        help="5 étoiles : le trajet le plus fiable parmi les trajets de même durée ; "
        "0 étoile : le moins fiable. Voir « Comment est calculée la note ? » en bas "
        "de page.",
    )
    with col_verdict:
        afficher(f"**{ligne['niveau'].capitalize()}** : {comparaison}.", icon=icone)
    if en_difficulte.get(liaison, False):
        st.markdown(
            "⚠️ Ce trajet fait partie des **liaisons durablement en difficulté** "
            "(voir la page du même nom)."
        )

# --- Les chiffres clés, comparés à un trajet typique ---------------------------
ecart_retard = (ligne["part_retard"] - typique["part_retard"]) * 100
ecart_annulation = (ligne["taux_annulation"] - typique["taux_annulation"]) * 100
ecart_minutes = ligne["retard_moyen_tous_trains"] - typique["retard_moyen_tous_trains"]

st.markdown("**Sur 100 trains**, comparé à un trajet typique de même durée :")
col1, col2, col3 = st.columns(3)
with col1.container(border=True):
    st.metric(
        "Arrivent en retard",
        f"{ligne['part_retard'] * 100:.0f}",
        delta=f"{ecart_retard:+.0f} vs trajet typique",
        delta_color="inverse",
    )
with col2.container(border=True):
    st.metric(
        "Sont annulés",
        f"{ligne['taux_annulation'] * 100:.1f}".replace(".", ","),
        delta=f"{ecart_annulation:+.1f} vs trajet typique".replace(".", ","),
        delta_color="inverse",
    )
with col3.container(border=True):
    st.metric(
        "Retard moyen par train",
        f"{ligne['retard_moyen_tous_trains']:.0f} min",
        delta=f"{ecart_minutes:+.0f} min vs trajet typique",
        delta_color="inverse",
        help="Moyenne sur tous les trains, y compris ceux à l'heure.",
    )
st.caption(
    "En retard = plus de 5 min (trajet de moins de 1h30), 10 min (1h30 à 3h) ou "
    "15 min (plus de 3h) à l'arrivée. Rouge : moins bien qu'un trajet typique ; "
    "vert : mieux."
)

# --- D'où viennent ses retards ? -----------------------------------------------
if liaison in contributions.index:
    st.subheader("D'où viennent ses retards ?")
    poids = contributions.loc[liaison].drop("cause_dominante")
    poids.index = poids.index.str.removeprefix("contrib_")
    st.plotly_chart(
        retards_sur_100_bar(poids.astype(float), LIBELLES_FAMILLES), width="stretch"
    )
    st.caption(
        f"Trains en retard sur 100, selon leur cause, de 2018 à 2026. Sur les 12 "
        f"derniers mois, {pourcent(ligne['part_origine_interne'])} des retards "
        "viennent de la SNCF (réseau, trains et gares) plutôt que d'aléas extérieurs."
    )

# --- Comment a-t-il évolué ? ---------------------------------------------------
st.subheader("Comment a-t-il évolué ?")
st.plotly_chart(historique_composantes_line(historique.loc[liaison]), width="stretch")
st.caption(
    "Années d'octobre à septembre (2026 = octobre 2025 à septembre 2026). 2018 ne "
    "compte que 9 mois."
)

with st.expander("ℹ️ Comment est calculée la note ?"):
    st.markdown(f"""
- On compare ce trajet aux autres **{trajets}** : un trajet court et un trajet long
  ne se comparent pas.
- Trois critères comptent autant l'un que l'autre : la part de **trains en retard**,
  la part de **trains annulés** et le **retard moyen**.
- Pour chaque critère, on classe le trajet parmi les trajets comparables, puis on
  fait la moyenne des trois classements. Cette moyenne donne la **note sur 5
  étoiles** : 5 pour le plus fiable, 0 pour le moins fiable.
- Le verdict dépend du rang du trajet : **plutôt fiable** dans le meilleur tiers,
  **peu fiable** dans le moins bon tiers.
- Il porte sur les **12 derniers mois** : c'est une photographie récente, pas un
  bilan sur plusieurs années.
""")
