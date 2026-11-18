"""Page « Données et limites » : peut-on faire confiance aux chiffres ?"""

import streamlit as st
from utils import LICENCE_URL, SOURCE_URL, get_regularite, tracer_page

tracer_page("Données et limites")

regularite = get_regularite()
debut, fin = regularite.periode

st.title("📋 Peut-on faire confiance à ces chiffres ?")
st.markdown(
    "Oui, à condition de savoir les lire. Voici d'où ils viennent, ce qu'ils "
    "mesurent, et ce qu'ils ne disent pas."
)

# --- Les données -----------------------------------------------------------------
st.subheader("D'où viennent les données ?")
cartes = st.columns(3)
with cartes[0].container(border=True):
    st.markdown("#### 🏛️ Une source officielle")
    st.markdown(
        f"[Régularité mensuelle TGV par liaisons]({SOURCE_URL}), publiée par "
        f"**SNCF Voyageurs** en open data (licence [ODbL]({LICENCE_URL}))."
    )
with cartes[1].container(border=True):
    st.markdown("#### 📅 Mois par mois")
    st.markdown(f"De **{debut}** à **{fin}**, un bilan par liaison et par mois.")
with cartes[2].container(border=True):
    st.markdown("#### 🛤️ Liaison par liaison")
    st.markdown(
        f"**{regularite.nb_liaisons} liaisons**. Une liaison est un sens de "
        "circulation : Paris → Lyon et Lyon → Paris sont deux liaisons."
    )

# --- Le retard -------------------------------------------------------------------
st.subheader("Qu'est-ce qu'un train en retard ?")
st.markdown(
    "Un train est en retard s'il arrive **au terminus** avec plus de retard que le "
    "seuil de son trajet. Plus le trajet est long, plus le seuil est large :"
)
seuils = st.columns(3)
for colonne, (trajet, seuil) in zip(
    seuils,
    [
        ("Trajet de moins de 1h30", "5 min"),
        ("Trajet de 1h30 à 3h", "10 min"),
        ("Trajet de plus de 3h", "15 min"),
    ],
):
    with colonne.container(border=True):
        st.metric(trajet, f"plus de {seuil}")
st.caption("C'est la régularité « composite » publiée par la SNCF.")

# --- Les règles de lecture -------------------------------------------------------
st.subheader("Trois règles pour bien lire")
regles = st.columns(3)
with regles[0].container(border=True):
    st.markdown("#### 🚫 Jamais de total")
    st.markdown(
        "Un même TGV passe par plusieurs liaisons : additionner les liaisons le "
        "compterait plusieurs fois. Nous montrons donc une **liaison typique** (la "
        "médiane) ou la **répartition des liaisons**, jamais un total du réseau."
    )
with regles[1].container(border=True):
    st.markdown("#### 🏷️ Une seule cause par train")
    st.markdown(
        "La SNCF attribue chaque retard à **une seule cause**, celle qui a fait "
        "perdre le plus de temps. Un train retardé par un orage puis par une panne "
        "ne compte qu'une fois."
    )
with regles[2].container(border=True):
    st.markdown("#### 🔎 Décrire, pas expliquer")
    st.markdown(
        "Les chiffres disent **d'où viennent** les retards déclarés, pas **pourquoi**. "
        "Quand nous avançons une explication, nous la présentons comme une "
        "hypothèse."
    )

# --- Les calculs -----------------------------------------------------------------
st.subheader("Comment nous calculons")
with st.expander("📍 La « liaison typique »"):
    st.markdown("""
- C'est la **liaison médiane** : on range toutes les liaisons françaises de la
  meilleure à la moins bonne, et on prend celle du milieu. La moitié des liaisons
  fait mieux, l'autre moitié moins bien.
- **Pourquoi la médiane ?** Un total du réseau est impossible (un même TGV compte
  dans plusieurs liaisons), et une moyenne serait tirée par quelques liaisons aux
  chiffres extrêmes ou douteux. La médiane montre ce que vit une liaison ordinaire.
- **Et la durée du trajet ?** Elle dit à qui l'on se compare : la note de fiabilité,
  les liaisons en difficulté et le « trajet typique de même durée » (page *Ma
  liaison*) se calculent à l'intérieur de chaque classe de durée.
- Les chiffres d'ensemble (accueil, causes, saisons) mélangent les durées : c'est
  juste, car le seuil de retard tient déjà compte de la durée du trajet (5, 10 ou 15
  min).
- La médiane de chaque cause est calculée séparément : les trois ne s'additionnent
  pas exactement à la médiane du total.
""")
with st.expander("🧩 Les trois familles de causes"):
    st.markdown("""
- **Réseau** (SNCF Réseau) : infrastructure (voies, caténaires, signalisation,
  travaux) et régulation du trafic.
- **Trains et gares** (SNCF Voyageurs) : matériel roulant, organisation en gare,
  prise en charge des voyageurs.
- **Aléas extérieurs** : météo, obstacles, malveillance, grèves.

Un regroupement de plusieurs causes pèse mécaniquement plus : le réseau en réunit
deux, de poids comparable.
""")
with st.expander("⭐ La note de fiabilité (page *Ma liaison*)"):
    st.markdown("""
- Trois critères à poids égal : la part de **trains en retard**, la part de **trains
  annulés** et le **retard moyen** de tous les trains.
- Chaque trajet est comparé aux trajets de **même durée** uniquement.
- La note va de **0 à 5 étoiles** (5 = le plus fiable) et porte sur les **12 derniers
  mois**. Elle est relative : elle ne se compare pas d'une année à l'autre.
- La part des retards dus à la SNCF est affichée à côté, sans entrer dans la note.
""")
with st.expander("🚨 Les liaisons en difficulté"):
    st.markdown("""
- Une liaison est en difficulté si elle fait partie du **quart des liaisons les plus
  en retard** de sa catégorie de durée, **au moins 2 années sur 3** entre 2023 et
  2025.
- Son évolution en 2026 est comparée à celle du reste du réseau, car 2026 a été une
  année difficile pour tous.
- Les années vont d'octobre à septembre : « 2026 » couvre octobre 2025 à septembre
  2026.
""")
with st.expander("🧮 Les choix de calcul"):
    st.markdown("""
- **Trains circulés** : un train annulé ne peut pas être en retard, donc le taux de
  retard se calcule sur les trains qui ont réellement circulé.
- **Pondération par le nombre de trains** : un mois chargé compte plus qu'un mois
  calme ; jamais de moyenne de pourcentages.
- **Liaisons internationales** : exclues des comparaisons, affichées avec un
  avertissement.
- Le détail des choix de méthode est dans `documentation/arbitrages_phase2.pdf`.
""")

# --- Les limites -----------------------------------------------------------------
st.subheader("⚠️ Les limites connues")
st.markdown("""
- **Liaisons internationales** : leurs données sont peu fiables (retards non
  renseignés, taux extrêmes, causes manquantes).
- **Causes manquantes** : 83 mois de liaison ont des retards sans cause renseignée
  (surtout en 2018) ; ils sont exclus de l'analyse des causes.
- **Effet statistique** : une liaison choisie pour ses mauvais résultats tend à
  s'améliorer un peu ensuite (« régression vers la moyenne »).
- **Années particulières** : 2018 ne compte que 9 mois ; 2020-2021 sont marquées par
  la crise sanitaire.
""")
