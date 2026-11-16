"""Utilitaires Streamlit - RailInsight.

Le chargement passe par ici, avec un cache : les données ne sont téléchargées
et préparées qu'une fois, puis réutilisées par toutes les pages.
"""

import pandas as pd
import streamlit as st

from railinsight.data.loader import GARES, REGULARITE, load
from railinsight.data.preprocessing import preprocess_gares, preprocess_regularite
from railinsight.data.quality import normaliser_noms
from railinsight.regularite import Regularite
from railinsight.viz.charts import ROUTE_COLUMNS

#: Jeu de données utilisé et sa licence, cités par les pages.
SOURCE_URL = (
    "https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/"
)
LICENCE_URL = "https://data.sncf.com/pages/cgu/A1#A1"

#: Noms grand public des familles de causes, partagés par toutes les pages.
LIBELLES_FAMILLES = {
    "reseau": "Réseau",
    "voyageurs": "Trains et gares",
    "externe": "Aléas extérieurs",
}


@st.cache_data(show_spinner="Téléchargement des données SNCF…")
def get_data() -> pd.DataFrame:
    """Charge les données de régularité TGV brutes (mises en cache)."""
    return load(REGULARITE)


@st.cache_data(show_spinner="Préparation des analyses…")
def get_regularite() -> Regularite:
    """Jeu de régularité préparé, point d'entrée de toutes les analyses."""
    return Regularite(get_data())


@st.cache_data(show_spinner="Chargement de la carte…")
def get_gares() -> pd.DataFrame:
    """Coordonnées des gares des liaisons, via le preprocessing commun."""
    gares = preprocess_gares(load(GARES))
    regularite = preprocess_regularite(get_data(), gares)

    noms = pd.concat(
        [
            pd.DataFrame(
                {
                    "gare": normaliser_noms(regularite[colonne]),
                    "code_uic": regularite[f"uic_{sens}"],
                }
            )
            for colonne, sens in zip(ROUTE_COLUMNS, ("depart", "arrivee"))
        ]
    ).drop_duplicates()
    stations = noms.merge(
        gares[["code_uic", "x_wgs84", "y_wgs84"]].astype({"code_uic": "Int64"}),
        on="code_uic",
    ).rename(columns={"x_wgs84": "longitude", "y_wgs84": "latitude"})
    return stations.drop_duplicates(subset="gare")


def etoiles_texte(nombre: int) -> str:
    """Note en étoiles : ``3`` → ``★★★☆☆``."""
    return "★" * nombre + "☆" * (5 - nombre)


def pourcent(valeur: float) -> str:
    """Formate un taux (0-1) en pourcentage français, ex. ``14,7 %``."""
    return f"{valeur * 100:.1f} %".replace(".", ",")


def libelle_famille(nom: str) -> str:
    """Libellé d'une famille de causes (``reseau`` → ``Réseau``)."""
    return LIBELLES_FAMILLES[nom]


def nom_gare(nom: str) -> str:
    """Nom de gare lisible : ``AIX EN PROVENCE`` → ``Aix en Provence``."""
    petits_mots = {"EN", "DE", "DU", "DES", "LA", "LE", "LES", "SUR", "ET", "SOUS"}
    mots = [m.lower() if m in petits_mots else m.capitalize() for m in nom.split()]
    return " ".join(mots)
