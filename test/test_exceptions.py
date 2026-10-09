"""Tests des exceptions personnalisées."""

from railinsight.exceptions import (
    AnalysisError,
    DataLoadError,
    DataValidationError,
    MissingColumnsError,
    RailInsightError,
)


def test_custom_exceptions_share_project_base():
    for error in (
        DataLoadError,
        DataValidationError,
        MissingColumnsError,
        AnalysisError,
    ):
        assert issubclass(error, RailInsightError)


def test_exception_keeps_message():
    error = DataValidationError("date invalide")

    assert str(error) == "date invalide"
