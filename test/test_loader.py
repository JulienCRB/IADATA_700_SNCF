"""Tests du chargement et de la normalisation des données."""

from pathlib import Path

import pandas as pd
import pytest

from railinsight.data.loader import load_data, normalize_dataframe
from railinsight.exceptions import DataLoadError, DataValidationError, MissingColumnsError


def test_normalize_parses_dates_numeric_values_and_fake_missing(raw_dataframe):
    result = normalize_dataframe(raw_dataframe)

    assert str(result.loc[0, "date"]) == "2024-01"
    assert result.loc[0, "nb_train_prevu"] == 100
    assert pd.isna(result.loc[0, "commentaire_annulation"])


def test_normalize_rejects_missing_required_columns():
    with pytest.raises(MissingColumnsError, match="Colonnes obligatoires"):
        normalize_dataframe(pd.DataFrame({"date": ["2024-01"]}))


def test_normalize_rejects_invalid_dates(raw_dataframe):
    raw_dataframe.loc[0, "date"] = "pas-une-date"
    with pytest.raises(DataValidationError, match="date"):
        normalize_dataframe(raw_dataframe)


def test_load_data_reports_missing_file(tmp_path):
    with pytest.raises(DataLoadError, match="Impossible de lire"):
        load_data(tmp_path / "absent.csv")


def test_loads_mini_csv_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "mini_sncf.csv"
    result = load_data(fixture_path)

    assert len(result) == 2
    assert result["nb_train_prevu"].sum() == 200
