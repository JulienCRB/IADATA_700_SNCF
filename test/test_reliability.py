import pandas as pd
import pytest

from railinsight.analysis.reliability import (
    COMPOSANTES_FIABILITE,
    agreger_derniers_mois,
    composantes_fiabilite,
    part_origine_interne,
    score_fiabilite,
)


def test_agreger_derniers_mois_garde_uniquement_les_n_derniers():
    """Seules les dates les plus récentes doivent être conservées."""
    data = pd.DataFrame({"date": ["2024-01", "2024-02", "2024-03", "2024-04"]})

    resultat = agreger_derniers_mois(data, n_mois=2)

    assert sorted(resultat["date"].unique()) == ["2024-03", "2024-04"]


def test_agreger_derniers_mois_ne_modifie_pas_l_original():
    """La fonction doit retourner une copie, sans modifier le DataFrame d'origine."""
    data = pd.DataFrame({"date": ["2024-01", "2024-02"]})
    original = data.copy(deep=True)

    agreger_derniers_mois(data, n_mois=1)

    pd.testing.assert_frame_equal(data, original)


def _mois_liaison(
    gare_depart="PARIS",
    gare_arrivee="LYON",
    classe_duree="> 3h",
    nb_train_prevu=100,
    nb_annulation=10,
    nb_train_retard_arrivee=20,
    retard_moyen_tous_trains_arrivee=5.0,
):
    """Construit une observation (liaison x mois) pour les tests de fiabilité."""
    return {
        "gare_depart": gare_depart,
        "gare_arrivee": gare_arrivee,
        "classe_duree": classe_duree,
        "nb_train_prevu": nb_train_prevu,
        "nb_annulation": nb_annulation,
        "nb_train_retard_arrivee": nb_train_retard_arrivee,
        "retard_moyen_tous_trains_arrivee": retard_moyen_tous_trains_arrivee,
    }


def test_composantes_fiabilite_calcule_les_trois_composantes():
    """Vérifie le calcul des 3 composantes sur un cas simple, à la main."""
    data = pd.DataFrame(
        [
            _mois_liaison(
                nb_train_prevu=100,
                nb_annulation=10,
                nb_train_retard_arrivee=18,
                retard_moyen_tous_trains_arrivee=5.0,
            )
        ]
    )

    resultat = composantes_fiabilite(data)
    ligne = resultat.loc[("PARIS", "LYON")]

    # part_retard = trains en retard / trains circulés = 18 / (100 - 10) = 0.2
    assert ligne["part_retard"] == pytest.approx(0.2)
    # taux_annulation = annulés / prévus = 10 / 100 = 0.1
    assert ligne["taux_annulation"] == pytest.approx(0.1)
    assert ligne["retard_moyen_tous_trains"] == pytest.approx(5.0)
    assert ligne["classe_duree"] == "> 3h"


def test_composantes_fiabilite_pondere_le_retard_moyen_par_les_trains_du_mois():
    """Le retard moyen sur plusieurs mois doit être pondéré, pas une moyenne simple."""
    data = pd.DataFrame(
        [
            _mois_liaison(nb_train_prevu=100, retard_moyen_tous_trains_arrivee=10.0),
            _mois_liaison(nb_train_prevu=300, retard_moyen_tous_trains_arrivee=2.0),
        ]
    )

    resultat = composantes_fiabilite(data)

    # (100*10 + 300*2) / 400 = 4.0, pas (10 + 2) / 2 = 6.0
    assert resultat.loc[("PARIS", "LYON"), "retard_moyen_tous_trains"] == pytest.approx(
        4.0
    )


def test_score_fiabilite_classe_la_moins_fiable_a_un_rang_eleve():
    """La pire liaison de sa classe doit avoir le score de fiabilité le plus haut."""
    data = pd.DataFrame(
        {
            "classe_duree": ["> 3h", "> 3h"],
            "part_retard": [0.1, 0.5],
            "taux_annulation": [0.01, 0.1],
            "retard_moyen_tous_trains": [3.0, 20.0],
        },
        index=["bonne_liaison", "mauvaise_liaison"],
    )

    resultat = score_fiabilite(data)

    assert (
        resultat.loc["mauvaise_liaison", "score_fiabilite"]
        > (resultat.loc["bonne_liaison", "score_fiabilite"])
    )
    assert resultat.loc["mauvaise_liaison", "score_fiabilite"] == pytest.approx(1.0)
    assert resultat.loc["bonne_liaison", "score_fiabilite"] == pytest.approx(0.5)


def test_score_fiabilite_normalise_par_classe_de_duree_separement():
    """Le rang doit être calculé à l'intérieur de chaque classe de durée."""
    data = pd.DataFrame(
        {
            "classe_duree": ["< 1h30", "> 3h"],
            "part_retard": [0.5, 0.01],
            "taux_annulation": [0.5, 0.01],
            "retard_moyen_tous_trains": [5.0, 1.0],
        },
        index=["seule_courte", "seule_longue"],
    )

    resultat = score_fiabilite(data)

    # Seule liaison de sa classe : rang = 1.0 (percentile max), peu importe la valeur
    assert resultat.loc["seule_courte", "score_fiabilite"] == pytest.approx(1.0)
    assert resultat.loc["seule_longue", "score_fiabilite"] == pytest.approx(1.0)


def test_score_fiabilite_leve_une_erreur_sans_classe_duree():
    """`classe_duree` est requise pour normaliser par classe de durée."""
    data = pd.DataFrame({"part_retard": [0.1], "taux_annulation": [0.1]})

    with pytest.raises(ValueError, match="classe_duree"):
        score_fiabilite(data, composantes=["part_retard", "taux_annulation"])


def test_composantes_fiabilite_couvre_les_colonnes_attendues():
    """`COMPOSANTES_FIABILITE` doit correspondre aux colonnes calculées."""
    assert COMPOSANTES_FIABILITE == [
        "part_retard",
        "taux_annulation",
        "retard_moyen_tous_trains",
    ]


def test_part_origine_interne_calcule_la_part_reseau_et_voyageurs():
    """La part interne doit regrouper réseau + voyageurs, hors externe."""
    data = pd.DataFrame(
        {
            "gare_depart": ["PARIS"],
            "gare_arrivee": ["LYON"],
            "cause_fiable": [True],
            "nb_retard_reseau": [60.0],
            "nb_retard_voyageurs": [20.0],
            "nb_retard_externe": [20.0],
        }
    )

    resultat = part_origine_interne(data)

    # (60 + 20) / (60 + 20 + 20) = 0.8
    assert resultat.loc[("PARIS", "LYON")] == pytest.approx(0.8)


def test_part_origine_interne_exclut_les_observations_non_fiables():
    """Les observations non fiables ne doivent pas être comptées."""
    data = pd.DataFrame(
        {
            "gare_depart": ["PARIS", "PARIS"],
            "gare_arrivee": ["LYON", "LYON"],
            "cause_fiable": [True, False],
            "nb_retard_reseau": [50.0, 999.0],
            "nb_retard_voyageurs": [50.0, 0.0],
            "nb_retard_externe": [0.0, 0.0],
        }
    )

    resultat = part_origine_interne(data)

    assert resultat.loc[("PARIS", "LYON")] == pytest.approx(1.0)
