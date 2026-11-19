"""Test de démarrage de l'application Streamlit."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import railinsight.data.loader as loader
import railinsight.data.preprocessing as preprocessing
import railinsight.regularite as regularite

APP_DIR = Path(__file__).parent.parent / "app"
DATA_TEST_DIR = Path(__file__).parent / "data_test"
PAGES = [APP_DIR / "main.py", *sorted((APP_DIR / "vues").glob("*.py"))]


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.name)
def test_page_starts_without_error(page, monkeypatch):
    def fake_load(dataset):
        return pd.read_csv(DATA_TEST_DIR / f"{dataset}.csv")

    monkeypatch.setattr(loader, "load", fake_load)
    monkeypatch.setattr(preprocessing, "load", fake_load)
    monkeypatch.setattr(regularite, "load", fake_load)

    app = AppTest.from_file(str(page)).run(timeout=30)

    assert not app.exception
