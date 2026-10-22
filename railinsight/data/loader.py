"""Chargement des jeux de données open data SNCF directement en DataFrame.

Aucun fichier n'est créé : les données restent en mémoire.
"""

import io

import pandas as pd
import requests

BASE_URL = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets"

# Identifiants des jeux de données (visibles dans l'URL de chaque page du portail)
REGULARITE = "regularite-mensuelle-tgv-aqst"
GARES = "liste-des-gares"
LIGNES = "lignes-lgv-et-par-ecartement"
FREQUENTATION = "frequentation-gares"


def load(dataset: str) -> pd.DataFrame:
    """Charge un jeu de données SNCF Open Data en DataFrame.

    Args:
        dataset: Identifiant du jeu de données sur le portail SNCF
            (par exemple ``REGULARITE``).

    Returns:
        Le jeu de données complet, sans passer par un fichier.
    """
    response = requests.get(
        f"{BASE_URL}/{dataset}/exports/csv?delimiter=,", timeout=120
    )
    response.raise_for_status()
    return pd.read_csv(io.BytesIO(response.content))
