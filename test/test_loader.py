"""Tests du chargement et de la normalisation des données."""

import pandas as pd
import pytest

from railinsight.data.loader import FREQUENTATION, GARES, LIGNES, REGULARITE, load


@pytest.mark.parametrize(
    "dataset",
    [
        REGULARITE,
        GARES,
        LIGNES,
        FREQUENTATION,
    ],
)
def test_load(dataset):
    """Teste le chargement des différents datasets SNCF."""

    df = load(dataset)

    # Vérification du type et du contenu
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    # Vérification des colonnes
    assert len(df.columns) > 0
    assert df.columns.is_unique

    # Vérification de l'absence de lignes entièrement vides
    assert not df.isna().all(axis=1).any()


def test_load_invalid_dataset():
    """Teste le comportement avec un identifiant invalide."""

    with pytest.raises(Exception):
        load("dataset-inexistant")


"""
from railinsight.data.loader import load_data, normalize_dataframe
from railinsight.exceptions import (
    DataLoadError,
    DataValidationError,
    MissingColumnsError,
)

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
    """
