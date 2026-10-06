"""Analyse des causes de retard et de leur saisonnalité."""

import pandas as pd

from railinsight.analysis.base import BaseAnalysis
from railinsight.config import (
    CAUSE_COLUMNS,
    DATE_COLUMN,
    DELAYED_ARRIVAL_COLUMN,
)
from railinsight.exceptions import AnalysisError

MONTH_TO_SEASON = {
    12: "Hiver",
    1: "Hiver",
    2: "Hiver",
    3: "Printemps",
    4: "Printemps",
    5: "Printemps",
    6: "Été",
    7: "Été",
    8: "Été",
    9: "Automne",
    10: "Automne",
    11: "Automne",
}


class CausesAnalysis(BaseAnalysis):
    """Agrège les parts des causes, pondérées par les retards à l'arrivée."""

    def _validate_columns(self) -> None:
        required = (DATE_COLUMN, DELAYED_ARRIVAL_COLUMN, *CAUSE_COLUMNS)
        missing = sorted(set(required).difference(self.data.columns))
        if missing:
            raise AnalysisError(
                "Colonnes nécessaires à l'analyse des causes absentes : "
                + ", ".join(missing)
            )

    def analyze(self) -> pd.DataFrame:
        """Calcule les parts moyennes pondérées par mois."""
        self._validate_columns()
        records = self.data[[DATE_COLUMN, DELAYED_ARRIVAL_COLUMN, *CAUSE_COLUMNS]].copy()
        records["_weighted_delays"] = records[DELAYED_ARRIVAL_COLUMN].fillna(0)
        records["_weighted_delays"] = records["_weighted_delays"].clip(lower=0)
        for column in CAUSE_COLUMNS:
            records[column] = records[column].mul(records["_weighted_delays"])
        grouped = records.groupby(DATE_COLUMN, dropna=False).agg(
            weighted_delays=("_weighted_delays", "sum"),
            **{column: (column, "sum") for column in CAUSE_COLUMNS},
        )
        denominator = grouped["weighted_delays"].where(grouped["weighted_delays"] > 0)
        for column in CAUSE_COLUMNS:
            grouped[column] = grouped[column].div(denominator)
        return grouped.reset_index()

    def seasonality(self) -> pd.DataFrame:
        """Compare les parts pondérées des causes entre saisons."""
        monthly = self.analyze()
        month_numbers = pd.PeriodIndex(monthly[DATE_COLUMN], freq="M").month
        monthly["season"] = month_numbers.map(MONTH_TO_SEASON)
        seasonal_results = []
        for season, seasonal_data in monthly.groupby(
            "season", sort=False, dropna=False
        ):
            weights = seasonal_data["weighted_delays"]
            total_weight = weights.sum()
            result = {"season": season, "weighted_delays": total_weight}
            for column in CAUSE_COLUMNS:
                result[column] = (
                    (seasonal_data[column] * weights).sum() / total_weight
                    if total_weight > 0
                    else float("nan")
                )
            seasonal_results.append(result)
        return pd.DataFrame(seasonal_results)
