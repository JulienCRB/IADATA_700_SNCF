"""Test de démarrage de l'application Streamlit."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).parent.parent / "app"
PAGES = [APP_DIR / "main.py", *sorted((APP_DIR / "pages").glob("*.py"))]


@pytest.mark.parametrize("page", PAGES, ids=lambda page: page.name)
def test_page_starts_without_error(page):
    app = AppTest.from_file(str(page)).run(timeout=30)

    assert not app.exception
