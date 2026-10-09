"""Fiabilité par liaison et tendances mensuelles."""

import pandas as pd

from railinsight.analysis.base import BaseAnalysis
from railinsight.config import (
    CANCELLED_TRAINS_COLUMN,
    DATE_COLUMN,
    DELAYED_15_COLUMN,
    PLANNED_TRAINS_COLUMN,
    ROUTE_COLUMNS,
)
from railinsight.exceptions import AnalysisError


class ReliabilityAnalysis(BaseAnalysis):
    """Calcule les taux d'annulation et de retard significatif par liaison."""

    def _validate_columns(self) -> None:
        required = (
            *ROUTE_COLUMNS,
            DATE_COLUMN,
            PLANNED_TRAINS_COLUMN,
            CANCELLED_TRAINS_COLUMN,
            DELAYED_15_COLUMN,
        )
        missing = sorted(set(required).difference(self.data.columns))
        if missing:
            raise AnalysisError(
                "Colonnes nécessaires à l'analyse de fiabilité absentes : "
                + ", ".join(missing)
            )

    def analyze(self) -> pd.DataFrame:
        """Agrège la fiabilité sur l'ensemble de la période disponible."""
        self._validate_columns()
        grouped = self.data.groupby(list(ROUTE_COLUMNS), dropna=False).agg(
            planned_trains=(PLANNED_TRAINS_COLUMN, "sum"),
            cancelled_trains=(CANCELLED_TRAINS_COLUMN, "sum"),
            delayed_over_15=(DELAYED_15_COLUMN, "sum"),
        )
        denominator = grouped["planned_trains"].where(grouped["planned_trains"] > 0)
        grouped["cancellation_rate"] = grouped["cancelled_trains"].div(denominator)
        grouped["delay_over_15_rate"] = grouped["delayed_over_15"].div(denominator)
        grouped["unreliable_rate"] = (
            grouped["cancelled_trains"] + grouped["delayed_over_15"]
        ).div(denominator)
        return grouped.reset_index().sort_values(
            "unreliable_rate", ascending=False, na_position="last"
        )

    def trend(self) -> pd.DataFrame:
        """Retourne le taux de retard de plus de 15 minutes par liaison et mois."""
        self._validate_columns()
        grouped = self.data.groupby([*ROUTE_COLUMNS, DATE_COLUMN], dropna=False).agg(
            planned_trains=(PLANNED_TRAINS_COLUMN, "sum"),
            delayed_over_15=(DELAYED_15_COLUMN, "sum"),
        )
        denominator = grouped["planned_trains"].where(grouped["planned_trains"] > 0)
        grouped["delay_over_15_rate"] = grouped["delayed_over_15"].div(denominator)
        return grouped.reset_index().sort_values([*ROUTE_COLUMNS, DATE_COLUMN])
