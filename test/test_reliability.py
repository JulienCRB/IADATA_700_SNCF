import pandas as pd
import pytest

from railinsight.analysis.reliability import (
    COMPOSANTES_FIABILITE,
    agreger_derniers_mois,
    composantes_fiabilite,
    etoiles,
    medianes_par_classe,
    niveau_fiabilite,
    part_origine_interne,
    position_dans_classe,
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
    internationale=False,
    nb_train_prevu=200,
    nb_annulation=10,
    nb_train_retard_arrivee=38,
    retard_moyen_tous_trains_arrivee=5.0,
):
    """Construit une observation (liaison x mois) préparée pour les tests."""
    return {
        "gare_depart": gare_depart,
        "gare_arrivee": gare_arrivee,
        "classe_duree": classe_duree,
        "internationale": internationale,
        "nb_train_prevu": nb_train_prevu,
        "nb_annulation": nb_annulation,
        "nb_train_circule": nb_train_prevu - nb_annulation,
        "nb_train_retard_arrivee": nb_train_retard_arrivee,
        "retard_moyen_tous_trains_arrivee": retard_moyen_tous_trains_arrivee,
    }


def test_composantes_fiabilite_calcule_les_trois_composantes():
    """Vérifie le calcul des 3 composantes sur un cas simple, à la main."""
    data = pd.DataFrame([_mois_liaison()])

    resultat = composantes_fiabilite(data)
    ligne = resultat.loc[("PARIS", "LYON")]

    # part_retard = trains en retard / trains circulés = 38 / (200 - 10) = 0.2
    assert ligne["part_retard"] == pytest.approx(0.2)
    # taux_annulation = annulés / prévus = 10 / 200 = 0.05
    assert ligne["taux_annulation"] == pytest.approx(0.05)
    assert ligne["retard_moyen_tous_trains"] == pytest.approx(5.0)
    assert ligne["classe_duree"] == "> 3h"


def test_composantes_fiabilite_pondere_le_retard_moyen_par_les_trains_circules():
    """Le retard moyen sur plusieurs mois doit être pondéré, pas une moyenne simple."""
    data = pd.DataFrame(
        [
            _mois_liaison(nb_train_prevu=110, retard_moyen_tous_trains_arrivee=10.0),
            _mois_liaison(nb_train_prevu=310, retard_moyen_tous_trains_arrivee=2.0),
        ]
    )

    resultat = composantes_fiabilite(data)

    # Trains circulés : 100 et 300. (100*10 + 300*2) / 400 = 4.0, pas 6.0
    assert resultat.loc[("PARIS", "LYON"), "retard_moyen_tous_trains"] == pytest.approx(
        4.0
    )


def test_composantes_fiabilite_ecarte_les_petits_volumes():
    data = pd.DataFrame(
        [
            _mois_liaison(gare_depart="PARIS"),
            _mois_liaison(gare_depart="PETITE", nb_train_prevu=50, nb_annulation=0),
        ]
    )

    resultat = composantes_fiabilite(data, volume_min=100)

    assert list(resultat.index) == [("PARIS", "LYON")]


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


def test_score_fiabilite_ne_classe_pas_les_internationales():
    """Les liaisons internationales gardent un score vide (décision Phase 2)."""
    data = pd.DataFrame(
        {
            "classe_duree": ["> 3h", "> 3h", "> 3h"],
            "internationale": [False, False, True],
            "part_retard": [0.1, 0.2, 0.9],
            "taux_annulation": [0.01, 0.02, 0.9],
            "retard_moyen_tous_trains": [3.0, 4.0, 30.0],
        },
        index=["bonne", "moyenne", "etrangere"],
    )

    resultat = score_fiabilite(data)

    assert pd.isna(resultat.loc["etrangere", "score_fiabilite"])
    # L'internationale ne compte pas dans le classement des autres
    assert resultat.loc["moyenne", "score_fiabilite"] == pytest.approx(1.0)


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


def test_composantes_fiabilite_par_annee():
    """Avec `par`, une ligne par liaison et par année (historique)."""
    data = pd.DataFrame(
        [
            {**_mois_liaison(nb_train_retard_arrivee=19), "annee": 2025},
            {**_mois_liaison(nb_train_retard_arrivee=38), "annee": 2026},
        ]
    )

    resultat = composantes_fiabilite(data, volume_min=0, par="annee")

    assert resultat.loc[("PARIS", "LYON", 2025), "part_retard"] == pytest.approx(0.1)
    assert resultat.loc[("PARIS", "LYON", 2026), "part_retard"] == pytest.approx(0.2)


def test_position_dans_classe_part_des_liaisons_moins_fiables():
    scores = pd.DataFrame(
        {
            "classe_duree": ["> 3h"] * 4,
            "score_fiabilite": [0.2, 0.4, 0.6, 0.8],
        },
        index=["a", "b", "c", "d"],
    )

    position = position_dans_classe(scores)

    # « a » est plus fiable que 3 liaisons sur 4, « d » que personne
    assert position.tolist() == pytest.approx([0.75, 0.5, 0.25, 0.0])


def test_niveau_fiabilite_par_tiers():
    assert niveau_fiabilite(0.9) == "plutôt fiable"
    assert niveau_fiabilite(0.5) == "dans la moyenne"
    assert niveau_fiabilite(0.1) == "peu fiable"
    assert niveau_fiabilite(float("nan")) is None


def test_medianes_par_classe_sans_internationales():
    scores = pd.DataFrame(
        {
            "classe_duree": ["> 3h", "> 3h", "> 3h"],
            "internationale": [False, False, True],
            "part_retard": [0.10, 0.20, 0.90],
            "taux_annulation": [0.01, 0.03, 0.50],
            "retard_moyen_tous_trains": [2.0, 4.0, 30.0],
        }
    )

    medianes = medianes_par_classe(scores)

    assert medianes.loc["> 3h", "part_retard"] == pytest.approx(0.15)


def test_etoiles_cinq_pour_la_plus_fiable():
    assert etoiles(0.0) == 5
    assert etoiles(1.0) == 0
    assert etoiles(0.43) == 3
    assert etoiles(float("nan")) is None
