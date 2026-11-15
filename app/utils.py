"""Utilitaires Streamlit - RailInsight."""

import pandas as pd
import streamlit as st

from railinsight.data.loader import GARES, REGULARITE, load
from railinsight.data.preprocessing import preprocess_gares, preprocess_regularite
from railinsight.data.quality import normaliser_noms


@st.cache_data
def get_data() -> pd.DataFrame:
    """Charge les données de régularité TGV (mises en cache)."""
    return load(REGULARITE)


@st.cache_data
def get_map_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prépare les liaisons et coordonnées des gares pour les cartes."""
    gares = preprocess_gares(load(GARES))
    regularite = preprocess_regularite(get_data(), gares)

    names = pd.concat(
        [
            pd.DataFrame(
                {
                    "gare": normaliser_noms(regularite[column]),
                    "code_uic": regularite[f"uic_{sens}"],
                }
            )
            for column, sens in zip(
                ("gare_depart", "gare_arrivee"), ("depart", "arrivee")
            )
        ]
    ).drop_duplicates()
    stations = names.merge(
        gares[["code_uic", "x_wgs84", "y_wgs84"]].astype({"code_uic": "Int64"}),
        on="code_uic",
    ).rename(columns={"x_wgs84": "longitude", "y_wgs84": "latitude"})

    routes = regularite[["gare_depart", "gare_arrivee"]].drop_duplicates()
    for column in ("gare_depart", "gare_arrivee"):
        routes[column] = normaliser_noms(routes[column])
    return routes, stations.drop_duplicates(subset="gare")
