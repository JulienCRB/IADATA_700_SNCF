"""Exceptions explicites pour les erreurs de données et d'analyse."""


class RailInsightError(Exception):
    """Erreur de base de l'application RailInsight."""


class DataLoadError(RailInsightError):
    """Erreur de lecture ou de validation du jeu de données."""


class MissingColumnsError(DataLoadError):
    """Le jeu de données ne contient pas toutes les colonnes attendues."""


class DataValidationError(DataLoadError):
    """Les valeurs du jeu de données ne peuvent pas être normalisées."""


class AnalysisError(RailInsightError):
    """Erreur lors d'une analyse des données."""
