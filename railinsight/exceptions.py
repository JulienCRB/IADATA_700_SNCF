"""Exceptions personnalisées du projet RailInsight (IADATA_700_SNCF)."""

from collections.abc import Iterable
from typing import Any


class RailInsightError(Exception):
    """Exception mère de toutes les erreurs métier du projet RailInsight."""


# =====================================================================
# 1. Erreurs de chargement / API Open Data SNCF (loader.py)
# =====================================================================


class ChargementDonneesError(RailInsightError):
    """Erreur survenue lors de la récupération ou de la lecture d'un dataset."""


class ErreurAPISNCF(ChargementDonneesError):
    """Échec de communication ou réponse HTTP en erreur de l'API SNCF Open Data."""

    def __init__(
        self,
        dataset: str,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        self.dataset = dataset
        self.status_code = status_code
        detail_http = f" (HTTP {status_code})" if status_code is not None else ""
        super().__init__(f"[{dataset}]{detail_http} {message}")


class DatasetIntrouvableError(ErreurAPISNCF):
    """Identifiant de dataset inconnu sur le portail SNCF Open Data (HTTP 404)."""

    def __init__(self, dataset: str) -> None:
        super().__init__(
            dataset,
            "Jeu de données introuvable sur le portail SNCF Open Data.",
            status_code=404,
        )


# =====================================================================
# 2. Erreurs de validation et de structure des données
# =====================================================================


class DonneesInvalidesError(RailInsightError):
    """Données absentes, incomplètes ou mal structurées."""


class ColonnesManquantesError(DonneesInvalidesError):
    """Une ou plusieurs colonnes attendues sont absentes du DataFrame."""

    def __init__(
        self,
        colonnes: Iterable[str],
        *,
        contexte: str | None = None,
    ) -> None:
        self.colonnes = sorted(set(colonnes))
        self.contexte = contexte
        prefixe = f"Dans '{contexte}' — " if contexte else ""
        super().__init__(f"{prefixe}Colonnes manquantes : {', '.join(self.colonnes)}")


class DatasetVideError(DonneesInvalidesError):
    """Le DataFrame est vide ou ne contient plus aucune ligne après filtrage."""


class FormatDateInvalideError(DonneesInvalidesError):
    """Colonne de dates vide ou non conforme au format attendu (AAAA-MM)."""

    def __init__(self, colonne: str, details: str | None = None) -> None:
        self.colonne = colonne
        suffixe = f" : {details}" if details else ""
        super().__init__(f"Dates invalides dans la colonne '{colonne}'{suffixe}")


# =====================================================================
# 3. Erreurs de paramètres ou de périmètre d'analyse
# =====================================================================


class AnalyseError(RailInsightError):
    """Erreur liée au paramétrage ou au périmètre d'un calcul métier."""


class ParametreInvalideError(AnalyseError):
    """Paramètre d'analyse hors domaine valide (seuil, quantile, volume, n...)."""

    def __init__(self, parametre: str, valeur: Any, raison: str) -> None:
        self.parametre = parametre
        self.valeur = valeur
        super().__init__(f"Paramètre '{parametre}={valeur!r}' invalide : {raison}")


class PeriodeInvalideError(AnalyseError):
    """Période de référence ou année de suivi absente des données disponibles."""