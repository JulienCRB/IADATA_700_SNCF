"""Tests des exceptions personnalisées du projet."""

from railinsight.exceptions import (
    AnalyseError,
    ChargementDonneesError,
    ColonnesManquantesError,
    DatasetIntrouvableError,
    DatasetVideError,
    DonneesInvalidesError,
    ErreurAPISNCF,
    FormatDateInvalideError,
    ParametreInvalideError,
    PeriodeInvalideError,
    RailInsightError,
)


def test_hierarchie_exceptions():
    """Toutes les exceptions métier doivent hériter de RailInsightError."""
    assert issubclass(ChargementDonneesError, RailInsightError)
    assert issubclass(ErreurAPISNCF, ChargementDonneesError)
    assert issubclass(DatasetIntrouvableError, ErreurAPISNCF)

    assert issubclass(DonneesInvalidesError, RailInsightError)
    assert issubclass(ColonnesManquantesError, DonneesInvalidesError)
    assert issubclass(DatasetVideError, DonneesInvalidesError)
    assert issubclass(FormatDateInvalideError, DonneesInvalidesError)

    assert issubclass(AnalyseError, RailInsightError)
    assert issubclass(ParametreInvalideError, AnalyseError)
    assert issubclass(PeriodeInvalideError, AnalyseError)


def test_erreur_api_sncf():
    """Vérifie le message et les attributs de ErreurAPISNCF avec et sans code HTTP."""
    err_sans_code = ErreurAPISNCF("regularite", "Erreur réseau")
    assert err_sans_code.dataset == "regularite"
    assert err_sans_code.status_code is None
    assert str(err_sans_code) == "[regularite] Erreur réseau"

    err_avec_code = ErreurAPISNCF("regularite", "Erreur serveur", status_code=500)
    assert err_avec_code.status_code == 500
    assert str(err_avec_code) == "[regularite] (HTTP 500) Erreur serveur"


def test_dataset_introuvable_error():
    """Vérifie que DatasetIntrouvableError renseigne bien le code 404."""
    err = DatasetIntrouvableError("dataset-inconnu")

    assert err.dataset == "dataset-inconnu"
    assert err.status_code == 404
    assert "dataset-inconnu" in str(err)
    assert "404" in str(err)


def test_colonnes_manquantes_error():
    """Vérifie le tri des colonnes et l'affichage optionnel du contexte."""
    err_simple = ColonnesManquantesError(["b", "a", "a"])
    assert err_simple.colonnes == ["a", "b"]
    assert err_simple.contexte is None
    assert str(err_simple) == "Colonnes manquantes : a, b"

    err_contexte = ColonnesManquantesError(["date"], contexte="preprocess_dates")
    assert err_contexte.contexte == "preprocess_dates"
    assert str(err_contexte) == "Dans 'preprocess_dates' — Colonnes manquantes : date"


def test_format_date_invalide_error():
    """Vérifie le message de FormatDateInvalideError avec et sans détails."""
    err_simple = FormatDateInvalideError("date")
    assert err_simple.colonne == "date"
    assert str(err_simple) == "Dates invalides dans la colonne 'date'"

    err_details = FormatDateInvalideError("date", details="format attendu AAAA-MM")
    assert (
        str(err_details)
        == "Dates invalides dans la colonne 'date' : format attendu AAAA-MM"
    )


def test_parametre_invalide_error():
    """Vérifie les attributs et le message de ParametreInvalideError."""
    err = ParametreInvalideError("n_mois", -2, "doit être strictement positif")

    assert err.parametre == "n_mois"
    assert err.valeur == -2
    assert str(err) == "Paramètre 'n_mois=-2' invalide : doit être strictement positif"
