"""Exceptions métier du projet RailInsight."""

from collections.abc import Iterable
from typing import Any


class RailInsightError(Exception):
    """Exception racine de toutes les erreurs métier de RailInsight."""


class ChargementDonneesError(RailInsightError):
    """Erreur survenue lors du téléchargement ou de la lecture d'un dataset."""


class ErreurAPISNCF(ChargementDonneesError):
    """Erreur renvoyée par l'API Open Data SNCF ou lors de l'appel réseau."""

    def __init__(
        self, dataset: str, message: str, status_code: int | None = None
    ) -> None:
        """Initialise l'erreur avec le nom du dataset et le statut HTTP éventuel."""
        self.dataset = dataset
        self.status_code = status_code
        prefixe = f"[{dataset}]"
        if status_code is not None:
            prefixe = f"{prefixe} (HTTP {status_code})"
        super().__init__(f"{prefixe} {message}")


class DatasetIntrouvableError(ErreurAPISNCF):
    """Le dataset demandé n'existe pas sur le portail SNCF (HTTP 404)."""

    def __init__(self, dataset: str) -> None:
        """Initialise l'erreur 404 pour un identifiant de dataset inconnu."""
        super().__init__(
            dataset,
            "Dataset introuvable sur le portail SNCF.",
            status_code=404,
        )


class DonneesInvalidesError(RailInsightError):
    """Les données fournies ne respectent pas la structure ou le format attendu."""


class ColonnesManquantesError(DonneesInvalidesError):
    """Une ou plusieurs colonnes indispensables sont absentes du DataFrame."""

    def __init__(
        self, colonnes: Iterable[str], contexte: str | None = None
    ) -> None:
        """Initialise l'erreur avec la liste triée des colonnes manquantes."""
        self.colonnes = sorted(set(colonnes))
        self.contexte = contexte
        liste = ", ".join(self.colonnes)
        message = f"Colonnes manquantes : {liste}"
        if contexte:
            message = f"Dans '{contexte}' — {message}"
        super().__init__(message)


class DatasetVideError(DonneesInvalidesError):
    """Le jeu de données est vide ou ne contient aucune observation exploitable."""


class FormatDateInvalideError(DonneesInvalidesError):
    """Une colonne de dates ne respecte pas le format attendu."""

    def __init__(self, colonne: str, details: str | None = None) -> None:
        """Initialise l'erreur avec le nom de la colonne de dates en cause."""
        self.colonne = colonne
        self.details = details
        message = f"Dates invalides dans la colonne '{colonne}'"
        if details:
            message = f"{message} : {details}"
        super().__init__(message)


class AnalyseError(RailInsightError):
    """Erreur survenue lors du calcul d'un indicateur d'analyse."""


class ParametreInvalideError(AnalyseError):
    """Un paramètre passé à une fonction d'analyse est hors bornes ou invalide."""

    def __init__(self, parametre: str, valeur: Any, message: str) -> None:
        """Initialise l'erreur avec le nom et la valeur invalide du paramètre."""
        self.parametre = parametre
        self.valeur = valeur
        super().__init__(f"Paramètre '{parametre}={valeur}' invalide : {message}")


class PeriodeInvalideError(AnalyseError):
    """Les périodes demandées sont absentes des données disponibles."""
