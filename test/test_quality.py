"""Tests des rapports de qualité et valeurs extrêmes."""

import pandas as pd
import pytest

from railinsight.data.quality import missing_report, outlier_flags
from railinsight.exceptions import DataValidationError


def test_missing_report_counts_nulls():
    report = missing_report(pd.DataFrame({"a": [1, None], "b": [None, None]}))

    assert report.loc["a", "missing_count"] == 1
    assert report.loc["a", "missing_percent"] == 50
    assert report.loc["b", "missing_percent"] == 100


def test_missing_report_handles_empty_dataframe():
    report = missing_report(pd.DataFrame(columns=["a"]))

    assert report.loc["a", "missing_count"] == 0
    assert report.loc["a", "missing_percent"] == 0


def test_outlier_flags_marks_extreme_numeric_value():
    result = outlier_flags(pd.DataFrame({"value": [1, 2, 2, 3, 100]}))

    assert result["value"].tolist() == [False, False, False, False, True]


def test_outlier_flags_rejects_unknown_column():
    with pytest.raises(DataValidationError, match="inconnues"):
        outlier_flags(pd.DataFrame({"a": [1, 2]}), ["missing"])
