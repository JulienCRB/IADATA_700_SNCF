import pandas as pd
import pytest

from railinsight.analysis.causes import (
    FAMILLES_CAUSES,
    ajouter_nb_retard_par_famille,
    contributions_par_saison,
    marquer_cause_fiable,
)


def _observation(
    prct_externe=10,
    prct_infra=30,
    prct_trafic=10,
    prct_materiel=20,
    prct_gare=15,
    prct_pec=15,
    nb_train_retard_arrivee=10,
):
    """Construit une observation (ligne) avec des pourcentages de cause par défaut."""
    return {
        "prct_cause_externe": prct_externe,
        "prct_cause_infra": prct_infra,
        "prct_cause_gestion_trafic": prct_trafic,
        "prct_cause_materiel_roulant": prct_materiel,
        "prct_cause_gestion_gare": prct_gare,
        "prct_cause_prise_en_charge_voyageurs": prct_pec,
        "nb_train_retard_arrivee": nb_train_retard_arrivee,
    }


def test_marquer_cause_fiable_detecte_les_anomalies():
    """Une observation avec des retards mais aucune cause renseignée est non fiable."""
    data = pd.DataFrame(
        [
            _observation(),  # somme à 100, fiable
            _observation(
                prct_externe=0,
                prct_infra=0,
                prct_trafic=0,
                prct_materiel=0,
                prct_gare=0,
                prct_pec=0,
                nb_train_retard_arrivee=5,
            ),  # somme à 0 mais des retards : non fiable
            _observation(nb_train_retard_arrivee=0),  # pas de retard : toujours fiable
        ]
    )

    resultat = marquer_cause_fiable(data)

    assert resultat.tolist() == [True, False, True]


def test_marquer_cause_fiable_tolere_les_petits_ecarts_d_arrondi():
    """Un léger écart d'arrondi (moins de `tolerance` points) reste fiable."""
    data = pd.DataFrame(
        [_observation(prct_externe=7, nb_train_retard_arrivee=10)]
    )  # somme 97

    resultat = marquer_cause_fiable(data, tolerance=5.0)

    assert resultat.tolist() == [True]


def test_ajouter_nb_retard_par_famille_repartit_les_trains_en_retard():
    """Le nombre de retards par famille doit correspondre aux pourcentages déclarés."""
    data = pd.DataFrame(
        [
            _observation(
                prct_externe=20,
                prct_infra=50,
                prct_trafic=10,
                prct_materiel=10,
                prct_gare=5,
                prct_pec=5,
                nb_train_retard_arrivee=10,
            )
        ]
    )

    resultat = ajouter_nb_retard_par_famille(data)

    # reseau = infra(50) + trafic(10) = 60 % de 10 trains = 6
    assert resultat.loc[0, "nb_retard_reseau"] == pytest.approx(6.0)
    # externe = 20 % de 10 trains = 2
    assert resultat.loc[0, "nb_retard_externe"] == pytest.approx(2.0)
    # la somme des 3 familles doit retomber sur le nombre total de trains en retard
    total = (
        resultat.loc[0, "nb_retard_reseau"]
        + resultat.loc[0, "nb_retard_voyageurs"]
        + resultat.loc[0, "nb_retard_externe"]
    )
    assert total == pytest.approx(10.0)


def test_ajouter_nb_retard_par_famille_ne_modifie_pas_l_original():
    """`ajouter_nb_retard_par_famille` doit retourner une copie."""
    data = pd.DataFrame([_observation()])
    original = data.copy(deep=True)

    ajouter_nb_retard_par_famille(data)

    pd.testing.assert_frame_equal(data, original)


def test_contributions_par_saison_pondere_par_le_nombre_de_trains():
    """Contribution par saison : moyenne pondérée, pas une moyenne simple."""
    data = pd.DataFrame(
        {
            "saison": ["hiver", "hiver"],
            "nb_train_prevu": [100, 300],
            "cause_fiable": [True, True],
            "nb_retard_reseau": [10, 60],
            "nb_retard_voyageurs": [5, 15],
            "nb_retard_externe": [2, 3],
        }
    )

    resultat = contributions_par_saison(data)

    # contrib_reseau = (10 + 60) / (100 + 300) = 0.175, pas (0.10 + 0.20) / 2 = 0.15
    assert resultat.loc["hiver", "contrib_reseau"] == pytest.approx(0.175)


def test_contributions_par_saison_exclut_les_observations_non_fiables():
    """Les observations `cause_fiable=False` ne comptent pas dans l'agrégation."""
    data = pd.DataFrame(
        {
            "saison": ["été", "été"],
            "nb_train_prevu": [100, 1_000_000],
            "cause_fiable": [True, False],
            "nb_retard_reseau": [10, 999_999],
            "nb_retard_voyageurs": [5, 0],
            "nb_retard_externe": [2, 0],
        }
    )

    resultat = contributions_par_saison(data)

    assert resultat.loc["été", "contrib_reseau"] == pytest.approx(0.10)


def test_contributions_par_saison_leve_une_erreur_si_colonne_manquante():
    """Une colonne requise manquante doit lever une `ValueError` explicite."""
    data = pd.DataFrame({"saison": ["hiver"], "nb_train_prevu": [100]})

    with pytest.raises(ValueError, match="Colonnes manquantes"):
        contributions_par_saison(data)


def test_familles_causes_couvrent_les_six_colonnes_du_dataset():
    """Les 3 familles doivent couvrir exactement les 6 colonnes `prct_cause_*`."""
    toutes_colonnes = [col for colonnes in FAMILLES_CAUSES.values() for col in colonnes]
    assert len(toutes_colonnes) == 6
    assert len(set(toutes_colonnes)) == 6
