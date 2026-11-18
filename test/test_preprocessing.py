from pathlib import Path

import pandas as pd
import pytest

from railinsight.data import preprocessing
from railinsight.data.loader import FREQUENTATION, REGULARITE
from railinsight.data.preprocessing import (
    preparer_regularite,
    preprocess_dates,
    preprocess_fq,
    preprocess_gares,
    preprocess_regularite,
)
from railinsight.exceptions import (
    ColonnesManquantesError,
    DatasetVideError,
    FormatDateInvalideError,
)

DATA_TEST_DIR = Path(__file__).parent / "data_test"


def _charger_csv_test(dataset: str) -> pd.DataFrame:
    return pd.read_csv(DATA_TEST_DIR / f"{dataset}.csv")


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


def test_preprocess_gares_vide():
    """Vérifie qu'un DataFrame vide de gares lève une erreur."""

    with pytest.raises(DatasetVideError):
        preprocess_gares(pd.DataFrame())


def test_preprocess_gares_colonne_manquante():
    """Vérifie qu'une colonne manquante dans les gares lève une erreur."""

    with pytest.raises(ColonnesManquantesError):
        preprocess_gares(pd.DataFrame({"code_uic": [123]}))


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


def test_preprocess_regularite_erreurs():
    """Vérifie les erreurs sur DataFrame vide ou colonnes manquantes."""

    df_reg = pd.DataFrame({"gare_depart": ["PARIS"], "gare_arrivee": ["LYON"]})
    df_gares = pd.DataFrame({"gare": ["PARIS"], "code_uic": [123]})

    with pytest.raises(DatasetVideError):
        preprocess_regularite(pd.DataFrame(), df_gares)

    with pytest.raises(DatasetVideError):
        preprocess_regularite(df_reg, pd.DataFrame())

    with pytest.raises(ColonnesManquantesError):
        preprocess_regularite(pd.DataFrame({"gare_depart": ["PARIS"]}), df_gares)

    with pytest.raises(ColonnesManquantesError):
        preprocess_regularite(df_reg, pd.DataFrame({"gare": ["PARIS"]}))


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
        "jan. 25",
        "fév. 25",
        "mar. 25",
        "avr. 25",
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

    with pytest.raises(FormatDateInvalideError):
        preprocess_dates(df_regularite)


def test_preprocess_dates_vides():
    """Vérifie qu'une colonne ne contenant que des valeurs nulles lève une erreur."""

    df_regularite = pd.DataFrame({"date": [None, None]})

    with pytest.raises(FormatDateInvalideError):
        preprocess_dates(df_regularite)


def test_preprocess_dates_colonne_absente():
    """Vérifie qu'une colonne de dates absente déclenche une erreur."""

    df_regularite = pd.DataFrame({"mois": ["2025-01", "2025-02"]})

    with pytest.raises(ColonnesManquantesError):
        preprocess_dates(df_regularite)


def test_preprocess_fq(monkeypatch):
    """Vérifie le chargement et la normalisation de la fréquentation depuis le CSV local."""

    df_brut = _charger_csv_test(FREQUENTATION)
    appels = []

    def fake_load(dataset):
        appels.append(dataset)
        return _charger_csv_test(dataset)

    monkeypatch.setattr(preprocessing, "load", fake_load)

    resultat = preprocess_fq()

    # Vérifier que le bon dataset a été demandé sans appel API
    assert appels == [preprocessing.FREQUENTATION]
    assert "nom_gare" in resultat.columns
    assert len(resultat) == len(df_brut)

    # Vérifier la normalisation des noms
    noms_attendus = preprocessing.normaliser_noms(df_brut["nom_gare"])
    assert resultat["gare"].tolist() == noms_attendus.tolist()


def test_preprocess_fq_colonne_manquante(monkeypatch):
    """Vérifie qu'une erreur est levée si la colonne gare est absente."""

    def fake_load(dataset):
        return pd.DataFrame({"frequentation": [1000]})

    monkeypatch.setattr(preprocessing, "load", fake_load)

    with pytest.raises(ColonnesManquantesError):
        preprocess_fq()


def _brut(date="2024-01", depart="Paris-Lyon", arrivee="Lyon", duree=120, prevus=100):
    """Construit une ligne brute de régularité (colonnes utiles seulement)."""
    return {
        "date": date,
        "gare_depart": depart,
        "gare_arrivee": arrivee,
        "duree_moyenne": duree,
        "nb_train_prevu": prevus,
        "nb_annulation": 10,
    }


def test_preparer_regularite_annee_d_octobre_a_septembre():
    data = pd.DataFrame([_brut(date="2024-09"), _brut(date="2024-10")])

    resultat = preparer_regularite(data)

    # Octobre 2024 ouvre l'année 2025 (oct. 2024 → sept. 2025)
    assert resultat["annee"].tolist() == [2024, 2025]
    assert resultat["saison"].tolist() == ["automne", "automne"]


def test_preparer_regularite_classe_duree_sur_la_duree_mediane():
    data = pd.DataFrame(
        [
            _brut(depart="A", duree=60),
            _brut(depart="B", duree=91),
            _brut(depart="B", duree=95),
            _brut(depart="C", duree=200),
            _brut(depart="C", duree=100),
            _brut(depart="C", duree=190),
        ]
    )

    resultat = preparer_regularite(data)

    # C : médiane 190 → "> 3h", même si un mois isolé fait 100 minutes
    assert resultat["classe_duree"].astype(str).tolist() == [
        "< 1h30",
        "1h30-3h",
        "1h30-3h",
        "> 3h",
        "> 3h",
        "> 3h",
    ]


def test_preparer_regularite_marque_les_internationales_et_les_circules():
    data = pd.DataFrame([_brut(), _brut(arrivee="Genève")])

    resultat = preparer_regularite(data)

    # Noms normalisés : "Genève" devient "GENEVE", reconnue comme étrangère
    assert resultat["gare_depart"].tolist() == ["PARIS LYON", "PARIS LYON"]
    assert resultat["internationale"].tolist() == [False, True]
    assert resultat["nb_train_circule"].tolist() == [90, 90]


def test_preparer_regularite_sur_donnees_test():
    """Vérifie preparer_regularite sur le CSV de régularité enregistré en local."""

    df_reg = _charger_csv_test(REGULARITE)
    resultat = preparer_regularite(df_reg)

    assert len(resultat) == len(df_reg)
    for col in ["annee", "saison", "classe_duree", "internationale", "nb_train_circule"]:
        assert col in resultat.columns


def test_preparer_regularite_erreurs():
    """Vérifie les erreurs levées par preparer_regularite."""

    with pytest.raises(DatasetVideError):
        preparer_regularite(pd.DataFrame())

    with pytest.raises(ColonnesManquantesError):
        preparer_regularite(pd.DataFrame({"date": ["2024-01"]}))

    with pytest.raises(FormatDateInvalideError):
        preparer_regularite(pd.DataFrame([_brut(date="invalide")]))