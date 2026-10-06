"""Tests de l'analyse des causes de retard."""

import pytest

from railinsight.analysis.causes import CausesAnalysis
from railinsight.config import CAUSE_COLUMNS
from railinsight.exceptions import AnalysisError


def test_causes_analysis_weights_by_delayed_trains(dataframe):
    result = CausesAnalysis(dataframe).analyze()

    assert len(result) == 2
    assert result.loc[0, "weighted_delays"] == 20
    assert result.loc[0, "prct_cause_infra"] == pytest.approx(30)


def test_seasonality_aggregates_months_by_season(dataframe):
    result = CausesAnalysis(dataframe).seasonality()
    winter = result.loc[result["season"] == "Hiver"].iloc[0]

    assert winter["weighted_delays"] == 35
    assert winter["prct_cause_infra"] == pytest.approx((20 * 30 + 15 * 40) / 35)


def test_causes_analysis_rejects_missing_columns(dataframe):
    with pytest.raises(AnalysisError, match="absentes"):
        CausesAnalysis(dataframe.drop(columns=[CAUSE_COLUMNS[0]])).analyze()
