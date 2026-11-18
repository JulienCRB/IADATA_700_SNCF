"""Tests du chargement et de la normalisation des données."""

import pandas as pd
import pytest
import requests

import railinsight.data.loader as loader
from railinsight.data.loader import FREQUENTATION, GARES, LIGNES, REGULARITE, load
from railinsight.exceptions import (
    ChargementDonneesError,
    DatasetIntrouvableError,
    DatasetVideError,
    ErreurAPISNCF,
)


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

    with pytest.raises(DatasetIntrouvableError):
        load("dataset-inexistant")


def test_load_dataset_vide():
    """Vérifie qu'un nom de dataset vide lève une erreur."""

    with pytest.raises(DatasetIntrouvableError):
        load("")


def test_load_timeout(monkeypatch):
    """Vérifie la gestion d'un dépassement de délai réseau."""

    def fake_get(url, timeout):
        raise requests.Timeout()

    monkeypatch.setattr(loader.requests, "get", fake_get)

    with pytest.raises(ErreurAPISNCF):
        load("regularite")


def test_load_erreur_reseau(monkeypatch):
    """Vérifie la gestion d'une erreur de connexion."""

    def fake_get(url, timeout):
        raise requests.RequestException("erreur réseau")

    monkeypatch.setattr(loader.requests, "get", fake_get)

    with pytest.raises(ErreurAPISNCF):
        load("regularite")


def test_load_erreur_http(monkeypatch):
    """Vérifie la gestion d'une erreur serveur (code HTTP 500)."""

    class FakeResponse:
        status_code = 500
        ok = False
        content = b""

    def fake_get(url, timeout):
        return FakeResponse()

    monkeypatch.setattr(loader.requests, "get", fake_get)

    with pytest.raises(ErreurAPISNCF):
        load("regularite")


def test_load_csv_vide(monkeypatch):
    """Vérifie qu'un flux CSV vide lève une DatasetVideError."""

    class FakeResponse:
        status_code = 200
        ok = True
        content = b""

    def fake_get(url, timeout):
        return FakeResponse()

    monkeypatch.setattr(loader.requests, "get", fake_get)

    with pytest.raises(DatasetVideError):
        load("regularite")


def test_load_csv_malforme(monkeypatch):
    """Vérifie qu'un fichier CSV illisible lève une ChargementDonneesError."""

    class FakeResponse:
        status_code = 200
        ok = True
        content = b"a,b\n1,2"

    def fake_get(url, timeout):
        return FakeResponse()

    def fake_read_csv(flux):
        raise pd.errors.ParserError("erreur de lecture")

    monkeypatch.setattr(loader.requests, "get", fake_get)
    monkeypatch.setattr(loader.pd, "read_csv", fake_read_csv)

    with pytest.raises(ChargementDonneesError):
        load("regularite")


def test_load_dataframe_sans_lignes(monkeypatch):
    """Vérifie qu'un CSV avec seulement les noms de colonnes lève DatasetVideError."""

    class FakeResponse:
        status_code = 200
        ok = True
        content = b"col1,col2\n"

    def fake_get(url, timeout):
        return FakeResponse()

    monkeypatch.setattr(loader.requests, "get", fake_get)

    with pytest.raises(DatasetVideError):
        load("regularite")