import pandas as pd
import pytest

from railinsight.data import preprocessing
from railinsight.data.preprocessing import (
    preprocess_dates,
    preprocess_fq,
    preprocess_gares,
    preprocess_regularite,
)


def test_preprocess_gare():
    """Vérifie le nettoyage et l'unicité des gares."""

    df_brut = pd.DataFrame(
        {
            "code_uic": [123, 123, 456],
            "libelle": ["VALENCE", "VALENCE TGV", "PARIS"],
            "departement": ["26", "26", "75"],
            "commune": ["Valence", "Valence", "Paris"],
            "x_wgs84": [4.9, 4.9, 2.3],
            "y_wgs84": [44.9, 44.9, 48.8],
        }
    )

    df_original = df_brut.copy(deep=True)

    resultat = preprocess_gares(df_brut)

    assert isinstance(resultat, pd.DataFrame)
    assert resultat["code_uic"].is_unique
    assert "gare" in resultat.columns
    assert resultat["gare"].notna().all()
    assert "VALENCE TGV" in resultat["libelle"].values

    # Vérifier que le DataFrame d'origine n'a pas été modifié
    pd.testing.assert_frame_equal(df_brut, df_original)


def test_preprocess_regularite():
    """Vérifie l'ajout des codes UIC aux gares de la régularité."""

    df_gares = pd.DataFrame(
        {
            "code_uic": [123, 456],
            "libelle": ["PARIS", "LYON"],
            "departement": ["75", "69"],
            "commune": ["Paris", "Lyon"],
            "x_wgs84": [2.3, 4.8],
            "y_wgs84": [48.8, 45.7],
            "gare": ["PARIS", "LYON"],
        }
    )

    df_regularite = pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LILLE"],
            "gare_arrivee": ["LYON", "PARIS"],
        }
    )

    resultat = preprocess_regularite(df_regularite, df_gares)

    assert "uic_depart" in resultat.columns
    assert "uic_arrivee" in resultat.columns

    # Vérifier les correspondances
    assert resultat.loc[0, "uic_depart"] == 123
    assert resultat.loc[0, "uic_arrivee"] == 456
    assert resultat.loc[1, "uic_depart"] == 87223263
    assert resultat.loc[1, "uic_arrivee"] == 123

    # Vérifier le type des codes UIC
    assert str(resultat["uic_depart"].dtype) == "Int64"
    assert str(resultat["uic_arrivee"].dtype) == "Int64"

    # Toutes les gares doivent avoir un code UIC
    assert resultat["uic_depart"].notna().all()
    assert resultat["uic_arrivee"].notna().all()

    # Un code UIC ne doit pas correspondre à plusieurs noms de gares
    correspondances = pd.concat(
        [
            resultat[["gare_depart", "uic_depart"]].rename(
                columns={
                    "gare_depart": "gare",
                    "uic_depart": "uic",
                }
            ),
            resultat[["gare_arrivee", "uic_arrivee"]].rename(
                columns={
                    "gare_arrivee": "gare",
                    "uic_arrivee": "uic",
                }
            ),
        ]
    ).drop_duplicates()

    assert correspondances.groupby("uic")["gare"].nunique().max() == 1


def test_preprocess_regularite_noms_ambigus():
    """Vérifie que les noms de gares ambigus ne reçoivent pas d'UIC arbitraire."""

    df_gares = pd.DataFrame(
        {
            "code_uic": [123, 456, 789],
            "libelle": ["VALENCE", "PARIS", "VALENCE TGV"],
            "gare": ["VALENCE", "PARIS", "VALENCE"],
        }
    )

    df_regularite = pd.DataFrame(
        {
            "gare_depart": ["PARIS"],
            "gare_arrivee": ["PARIS"],
        }
    )

    resultat = preprocess_regularite(df_regularite, df_gares)

    # Identifier les codes UIC associés aux noms normalisés dupliqués
    noms_doublons = df_gares.loc[
        df_gares["gare"].duplicated(keep=False),
        "gare",
    ].unique()

    codes_uic_doublons = df_gares.loc[
        df_gares["gare"].isin(noms_doublons),
        "code_uic",
    ]

    # Rassembler les codes UIC attribués
    codes_utilises = pd.concat(
        [
            resultat["uic_depart"],
            resultat["uic_arrivee"],
        ]
    ).dropna()

    assert not codes_utilises.isin(codes_uic_doublons).any()

    # PARIS reste correctement identifié
    assert resultat.loc[0, "uic_depart"] == 456
    assert resultat.loc[0, "uic_arrivee"] == 456


def test_preprocess_dates():
    """Vérifie la création de la table de dates."""

    df_regularite = pd.DataFrame({"date": ["2025-01", "2025-03", "2025-04"]})

    resultat = preprocess_dates(df_regularite)

    # Tous les mois doivent être présents
    assert resultat["date"].tolist() == [
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
    ]

    # Vérifier les colonnes
    assert resultat.columns.tolist() == [
        "date",
        "AAAA",
        "MM",
        "AAAAMM",
        "mois",
        "mois_court",
        "mois_annee",
        "saison",
    ]

    # Vérifier les informations calendaires
    assert resultat["AAAA"].tolist() == [2025, 2025, 2025, 2025]
    assert resultat["MM"].tolist() == [1, 2, 3, 4]
    assert resultat["AAAAMM"].tolist() == [
        202501,
        202502,
        202503,
        202504,
    ]

    # Vérifier les noms des mois
    assert resultat["mois"].tolist() == [
        "janvier",
        "février",
        "mars",
        "avril",
    ]

    assert resultat["mois_court"].tolist() == [
        "jan.",
        "fév.",
        "mar.",
        "avr.",
    ]

    assert resultat["mois_annee"].tolist() == [
        "jan. AA",
        "fév. AA",
        "mar. AA",
        "avr. AA",
    ]

    # Vérifier les saisons
    assert resultat["saison"].tolist() == [
        "hiver",
        "hiver",
        "printemps",
        "printemps",
    ]


def test_preprocess_dates_changement_annee():
    """Vérifie la continuité des dates au changement d'année."""

    df_regularite = pd.DataFrame({"date": ["2024-12", "2025-02"]})

    resultat = preprocess_dates(df_regularite)

    assert resultat["date"].tolist() == [
        "2024-12",
        "2025-01",
        "2025-02",
    ]

    assert resultat["AAAAMM"].tolist() == [
        202412,
        202501,
        202502,
    ]

    assert resultat["saison"].tolist() == [
        "hiver",
        "hiver",
        "hiver",
    ]


def test_preprocess_dates_colonne_personnalisee():
    """Vérifie que le nom de la colonne de dates est configurable."""

    df_regularite = pd.DataFrame({"mois_reg": ["2025-01", "2025-02"]})

    resultat = preprocess_dates(
        df_regularite,
        colonne_date="mois_reg",
    )

    assert resultat["date"].tolist() == ["2025-01", "2025-02"]


def test_preprocess_dates_format_invalide():
    """Vérifie qu'une date invalide déclenche une erreur."""

    df_regularite = pd.DataFrame({"date": ["2025-01", "date_invalide"]})

    with pytest.raises(ValueError):
        preprocess_dates(df_regularite)


def test_preprocess_dates_colonne_absente():
    """Vérifie qu'une colonne de dates absente déclenche une erreur."""

    df_regularite = pd.DataFrame({"mois": ["2025-01", "2025-02"]})

    with pytest.raises(KeyError):
        preprocess_dates(df_regularite)


def test_preprocess_fq(monkeypatch):
    """Vérifie le chargement et la normalisation de la fréquentation."""

    df_brut = pd.DataFrame(
        {
            "gare": ["PARIS", "Lyon", "Marseille"],
            "frequentation": [1000, 800, 600],
        }
    )

    def fake_load(dataset):
        assert dataset == preprocessing.FREQUENTATION
        return df_brut.copy()

    monkeypatch.setattr(preprocessing, "load", fake_load)

    resultat = preprocess_fq()

    # Vérifier les colonnes et le nombre de lignes
    assert "gare" in resultat.columns
    assert "frequentation" in resultat.columns
    assert len(resultat) == len(df_brut)

    # Vérifier que les données numériques restent inchangées
    assert resultat["frequentation"].tolist() == [1000, 800, 600]

    # Vérifier la normalisation des noms
    noms_attendus = preprocessing.normaliser_noms(
        pd.Series(["PARIS", "Lyon", "Marseille"])
    )

    assert resultat["gare"].tolist() == noms_attendus.tolist()


def test_preprocess_fq_appelle_load(monkeypatch):
    """Vérifie que le dataset de fréquentation est chargé."""

    appels = []

    def fake_load(dataset):
        appels.append(dataset)

        return pd.DataFrame(
            {
                "gare": ["PARIS"],
                "frequentation": [1000],
            }
        )

    monkeypatch.setattr(preprocessing, "load", fake_load)

    preprocess_fq()

    assert appels == [preprocessing.FREQUENTATION]
