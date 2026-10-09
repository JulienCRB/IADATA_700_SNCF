"""Tests de l'analyse de fiabilité."""

import pytest

from railinsight.analysis.reliability import ReliabilityAnalysis
from railinsight.exceptions import AnalysisError


def test_reliability_aggregates_route_rates(dataframe):
    result = ReliabilityAnalysis(dataframe).analyze().iloc[0]

    assert result["planned_trains"] == 200
    assert result["cancelled_trains"] == 2
    assert result["delayed_over_15"] == 13
    assert result["unreliable_rate"] == pytest.approx(0.075)


def test_trend_has_one_row_per_route_and_month(dataframe):
    result = ReliabilityAnalysis(dataframe).trend()

    assert len(result) == 2
    assert result["delay_over_15_rate"].tolist() == pytest.approx([0.08, 0.05])


def test_reliability_rejects_missing_columns(dataframe):
    with pytest.raises(AnalysisError, match="absentes"):
        ReliabilityAnalysis(dataframe.drop(columns=["nb_train_retard_sup_15"])).analyze()
