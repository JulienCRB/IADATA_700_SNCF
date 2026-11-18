"""Chargement des jeux de données open data SNCF directement en DataFrame.

Aucun fichier n'est créé : les données restent en mémoire.
"""

import io

import pandas as pd
import requests

from railinsight.exceptions import (
    ChargementDonneesError,
    DatasetIntrouvableError,
    DatasetVideError,
    ErreurAPISNCF,
)
from railinsight.logger import get_logger

log = get_logger(__name__)

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

    Raises:
        DatasetIntrouvableError: Si le dataset n'existe pas sur le portail (404).
        ErreurAPISNCF: Si la requête réseau échoue ou renvoie une erreur HTTP.
        ChargementDonneesError: Si le flux CSV renvoyé est illisible.
        DatasetVideError: Si le jeu de données téléchargé est vide.
    """
    if not dataset or not dataset.strip():
        raise DatasetIntrouvableError(dataset)

    url = f"{BASE_URL}/{dataset}/exports/csv?delimiter=,"
    log.info("Téléchargement du dataset %s", dataset)

    try:
        response = requests.get(url, timeout=120)
    except requests.Timeout as err:
        raise ErreurAPISNCF(
            dataset, "Délai d'attente dépassé lors du téléchargement."
        ) from err
    except requests.RequestException as err:
        raise ErreurAPISNCF(
            dataset, f"Erreur réseau lors de l'appel à l'API SNCF : {err}"
        ) from err

    if response.status_code == 404:
        raise DatasetIntrouvableError(dataset)
    if not response.ok:
        raise ErreurAPISNCF(
            dataset,
            "Réponse HTTP en erreur de l'API SNCF.",
            status_code=response.status_code,
        )

    try:
        data = pd.read_csv(io.BytesIO(response.content))
    except pd.errors.EmptyDataError as err:
        raise DatasetVideError(
            f"Le flux CSV renvoyé pour le dataset '{dataset}' est vide."
        ) from err
    except pd.errors.ParserError as err:
        raise ChargementDonneesError(
            f"Impossible de parser le CSV du dataset '{dataset}' : {err}"
        ) from err

    if data.empty:
        raise DatasetVideError(f"Le dataset '{dataset}' ne contient aucune ligne.")

    log.info("Dataset %s chargé : %d lignes, %d colonnes", dataset, *data.shape)
    return data