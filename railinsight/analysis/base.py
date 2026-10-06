"""Classe abstraite commune aux analyses métier."""

from abc import ABC, abstractmethod

import pandas as pd

from railinsight.exceptions import AnalysisError


class BaseAnalysis(ABC):
    """Base validant et conservant une copie du jeu de données."""

    def __init__(self, data: pd.DataFrame) -> None:
        if not isinstance(data, pd.DataFrame):
            raise AnalysisError("Une analyse attend un DataFrame pandas.")
        if data.empty:
            raise AnalysisError("Une analyse ne peut pas utiliser un DataFrame vide.")
        self.data = data.copy()

    @abstractmethod
    def analyze(self) -> pd.DataFrame:
        """Calcule et retourne le résultat de l'analyse."""
