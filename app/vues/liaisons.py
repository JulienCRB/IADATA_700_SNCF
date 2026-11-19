"""Page « Liaisons en difficulté » : lesquelles, et comment évoluent-elles (Phase 2)."""

import streamlit as st
from utils import (
    get_gares,
    get_regularite,
    get_reseau,
    libelle_famille,
    log_action,
    nom_gare,
    pourcent,
    tracer_page,
)

from railinsight.analysis.difficulte import TENDANCES, gares_concernees
from railinsight.data.preprocessing import CLASSES_DUREE
from railinsight.viz.charts import (
    carte_difficulte,
    evolution_avant_apres,
    gares_concernees_bar,
)

#: Nom grand public de chaque classe de durée.
TRAJETS = {
    "< 1h30": "Trajets courts (moins de 1h30)",
    "1h30-3h": "Trajets moyens (1h30 à 3h)",
    "> 3h": "Trajets longs (plus de 3h)",
}

tracer_page("Liaisons en difficulté")

bilan_complet = get_regularite().liaisons_en_difficulte()

st.title("🚨 Liaisons durablement en difficulté")
st.markdown("""
Certaines liaisons ont **plus de retards que les autres, année après année**. Nous
les repérons ainsi : une liaison est « en difficulté » si elle fait partie du
**quart des liaisons les plus en retard** de sa catégorie (trajets courts, moyens
ou longs) **au moins 2 années sur 3**, entre 2023 et 2025.
""")

classe = st.segmented_control(
    "Type de trajet",
    ["Toutes", *CLASSES_DUREE],
    default="Toutes",
    format_func=lambda c: TRAJETS.get(c, "Tous les trajets"),
)
filtre_actif = classe or "Toutes"
if st.session_state.get("filtre_classe_liaisons") != filtre_actif:
    st.session_state["filtre_classe_liaisons"] = filtre_actif
    log_action("Liaisons en difficulté — Filtre type de trajet : %s", filtre_actif)

bilan = bilan_complet
if classe and classe != "Toutes":
    bilan = bilan_complet[bilan_complet["classe_duree"] == classe]
selection = bilan[bilan["en_difficulte"]]
tendance_reseau = bilan_complet.loc[~bilan_complet["en_difficulte"], "evolution"]

# --- En bref -----------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1.container(border=True):
    st.metric("Liaisons en difficulté", f"{len(selection)} sur {len(bilan)}")
    st.caption(f"Elles se regroupent sur {selection['axe'].nunique()} axes.")
with col2.container(border=True):
    st.metric(
        "2026, une année difficile pour tous",
        f"+{tendance_reseau.median() * 100:.0f} retards sur 100",
        help="Hausse du nombre de trains en retard entre 2023-2025 et 2026, pour "
        "une liaison typique qui n'est pas en difficulté.",
    )
    st.caption("Sur une liaison typique, entre 2023-2025 et 2026.")
with col3.container(border=True):
    aggravees = (selection["tendance"] == TENDANCES[0]).sum()
    st.metric("Se dégradent plus que les autres", f"{aggravees} sur {len(selection)}")
    st.caption("Parmi les liaisons en difficulté, en 2026.")

if selection.empty:
    st.info("Aucune liaison en difficulté pour ce type de trajet.")
    st.stop()

# --- Où sont-elles ? ---------------------------------------------------------
st.subheader("Où sont-elles ?")
gares = gares_concernees(bilan)
stations = get_gares()
col_carte, col_gares = st.columns([2, 1])
reseau = get_reseau()
col_carte.plotly_chart(carte_difficulte(bilan, stations, reseau), width="stretch")
if reseau is not None:
    reseau.sauver_cache()
with col_gares:
    if len(gares) >= 3:
        st.markdown(
            "Les difficultés se concentrent autour de quelques gares : "
            f"**{nom_gare(gares.index[0])}** ({gares.iloc[0]} liaisons), "
            f"**{nom_gare(gares.index[1])}** ({gares.iloc[1]}) et "
            f"**{nom_gare(gares.index[2])}** ({gares.iloc[2]})."
        )
    st.plotly_chart(gares_concernees_bar(gares, top_n=6), width="stretch")
    st.caption(
        "Sur la carte : en rouge, les liaisons qui s'aggravent plus que les autres ; "
        "en gris foncé, celles qui suivent le réseau ; en vert, celles qui résistent "
        "mieux. Les traits relient les gares en ligne droite (ce n'est pas le tracé "
        "des voies) ; les deux sens d'un axe se superposent."
    )

# --- Et en 2026 ? ------------------------------------------------------------
st.subheader("Et en 2026 ?")
st.markdown("""
Chaque ligne relie le retard d'une liaison **avant** (2023-2025, cercle vide) à son
retard **en 2026** (point plein). Plus la ligne va vers la droite, plus la liaison
s'est dégradée. Comme 2026 a été difficile partout, la couleur compare chaque
liaison au reste du réseau :
""")
legende = st.columns(3)
legende[0].markdown(":red[**s'aggrave**] : se dégrade plus que les autres")
legende[1].markdown(":gray[**suit le réseau**] : comme les autres, à 1 point près")
legende[2].markdown(":green[**résiste mieux**] : se dégrade moins que les autres")
st.plotly_chart(evolution_avant_apres(bilan), width="stretch")

# --- Bon à savoir --------------------------------------------------------------
with st.expander("ℹ️ Bon à savoir avant de conclure"):
    st.markdown("""
- **Une liaison choisie pour ses mauvais résultats a tendance à s'améliorer un peu
  ensuite**, simplement par effet statistique (« régression vers la moyenne »). Les
  liaisons qui « résistent mieux » sont donc à lire avec prudence.
- **Le calcul est fait par sens** : Mâcon → Paris peut être en difficulté sans que
  Paris → Mâcon le soit. Le tableau ci-dessous regroupe les deux sens par axe.
- **Les liaisons internationales ne sont pas classées** : leurs données sont peu
  fiables (voir *Données et limites*).
""")

# --- Les données ---------------------------------------------------------------
st.subheader("Les données, axe par axe")
tableau = selection.reset_index().sort_values(["axe", "gare_depart"])
tableau["sens"] = tableau["gare_depart"] + " → " + tableau["gare_arrivee"]
tableau["trajet"] = tableau["classe_duree"].map(lambda c: TRAJETS[c].split(" (")[0])
tableau["taux_reference"] = tableau["taux_reference"].map(pourcent)
tableau["taux_suivi"] = tableau["taux_suivi"].map(pourcent)
tableau["cause_evolution"] = tableau["cause_evolution"].map(libelle_famille)
st.dataframe(
    tableau[
        [
            "axe",
            "sens",
            "trajet",
            "taux_reference",
            "taux_suivi",
            "tendance",
            "cause_evolution",
        ]
    ],
    hide_index=True,
    column_config={
        "axe": st.column_config.TextColumn("Axe", width="medium"),
        "sens": st.column_config.TextColumn("Sens en difficulté", width="medium"),
        "trajet": st.column_config.TextColumn("Trajet", width="small"),
        "taux_reference": st.column_config.TextColumn(
            "En retard 2023-2025", width="small"
        ),
        "taux_suivi": st.column_config.TextColumn("En retard 2026", width="small"),
        "tendance": st.column_config.TextColumn("En 2026", width="small"),
        "cause_evolution": st.column_config.TextColumn(
            "Cause principale de l'évolution",
            width="small",
            help="Famille de causes qui a le plus augmenté sur cette liaison, par "
            "rapport au reste du réseau.",
        ),
    },
)
