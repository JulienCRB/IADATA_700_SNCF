"""Tests des rapports de qualité et valeurs extrêmes."""

import pandas as pd

from railinsight.data.quality import (
    ajouter_gares,
    garder_gares_tgv_si_doublon,
    gares_uniques,
    normaliser_noms,
)


def test_normaliser_noms():
    noms = pd.Series(["Paris-Lyon", "Sainte-Menehould", "LILLE TGV"])

    resultat = normaliser_noms(noms)

    assert resultat.tolist() == [
        "PARIS LYON",
        "ST MENEHOULD",
        "LILLE",
    ]


def test_garder_gares_tgv_si_doublon():
    df = pd.DataFrame(
        {
            "libelle": ["VALENCE", "VALENCE TGV", "PARIS"],
            "gare": ["VALENCE", "VALENCE", "PARIS"],
        }
    )

    resultat = garder_gares_tgv_si_doublon(df)

    assert resultat["libelle"].tolist() == ["VALENCE TGV", "PARIS"]
    assert resultat["gare"].is_unique


def test_gares_uniques():
    df = pd.DataFrame(
        {
            "CODE_UIC": [123, 123, 456, None],
            "LIBELLE": ["PARIS", "PARIS", "LYON", "INCONNUE"],
            "DEPARTEMEN": ["75", "75", "69", "00"],
            "COMMUNE": ["Paris", "Paris", "Lyon", "Inconnue"],
            "X_WGS84": [2.3, 2.3, 4.8, 0.0],
            "Y_WGS84": [48.8, 48.8, 45.7, 0.0],
        }
    )

    resultat = gares_uniques(df)

    assert resultat["code_uic"].is_unique
    assert resultat["code_uic"].notna().all()
    assert len(resultat) == 2
    assert "departement" in resultat.columns


def test_ajouter_gares():
    df = pd.DataFrame(
        {
            "code_uic": [123],
            "libelle": ["PARIS"],
        }
    )

    nouvelles_gares = [
        {"code_uic": 123, "libelle": "PARIS MODIFIE"},
        {"code_uic": 456, "libelle": "LYON"},
    ]

    resultat = ajouter_gares(df, nouvelles_gares)

    assert resultat["code_uic"].is_unique
    assert len(resultat) == 2
    assert resultat.loc[0, "libelle"] == "PARIS"


def test_ajouter_gares_liste_vide():
    df = pd.DataFrame(
        {
            "code_uic": [123],
            "libelle": ["PARIS"],
        }
    )

    resultat = ajouter_gares(df, [])

    pd.testing.assert_frame_equal(resultat, df)
