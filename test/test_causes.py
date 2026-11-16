import pandas as pd
import pytest

from railinsight.analysis.causes import (
    FAMILLES_CAUSES,
    ajouter_nb_retard_par_famille,
    cause_dominante,
    contributions_par_liaison,
    contributions_par_saison,
    liaisons_les_plus_touchees,
    marquer_cause_fiable,
    repartition_par_niveau,
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


def _liaison_saison(
    gare_depart="PARIS",
    saison="hiver",
    nb_train_circule=100,
    reseau=10,
    voyageurs=5,
    externe=2,
    cause_fiable=True,
    internationale=False,
):
    """Construit une observation déjà préparée pour les tests de contributions."""
    return {
        "gare_depart": gare_depart,
        "gare_arrivee": "LYON",
        "saison": saison,
        "nb_train_circule": nb_train_circule,
        "nb_retard_reseau": reseau,
        "nb_retard_voyageurs": voyageurs,
        "nb_retard_externe": externe,
        "cause_fiable": cause_fiable,
        "internationale": internationale,
    }


def test_contributions_par_liaison_pondere_par_les_trains_circules():
    """Sur plusieurs mois, la contribution est pondérée, pas une moyenne simple."""
    data = pd.DataFrame(
        [
            _liaison_saison(nb_train_circule=100, reseau=10),
            _liaison_saison(nb_train_circule=300, reseau=60),
        ]
    )

    resultat = contributions_par_liaison(data)

    # (10 + 60) / (100 + 300) = 0.175, pas (0.10 + 0.20) / 2 = 0.15
    assert resultat.loc[("PARIS", "LYON"), "contrib_reseau"] == pytest.approx(0.175)


def test_contributions_par_liaison_exclut_les_observations_non_fiables():
    data = pd.DataFrame(
        [
            _liaison_saison(nb_train_circule=100, reseau=10),
            _liaison_saison(nb_train_circule=1000, reseau=999, cause_fiable=False),
        ]
    )

    resultat = contributions_par_liaison(data)

    assert resultat.loc[("PARIS", "LYON"), "contrib_reseau"] == pytest.approx(0.10)


def test_cause_dominante_retourne_le_nom_de_la_famille():
    contributions = pd.DataFrame(
        {
            "contrib_reseau": [0.10, 0.02],
            "contrib_voyageurs": [0.05, 0.08],
            "contrib_externe": [0.01, 0.01],
        },
        index=["liaison_a", "liaison_b"],
    )

    assert cause_dominante(contributions).tolist() == ["reseau", "voyageurs"]


def test_contributions_par_saison_prend_la_mediane_des_liaisons():
    """Pas de total réseau : on prend la liaison médiane, pas la somme des trains."""
    data = pd.DataFrame(
        [
            _liaison_saison(gare_depart="A", nb_train_circule=100, reseau=10),
            _liaison_saison(gare_depart="B", nb_train_circule=100, reseau=20),
            _liaison_saison(gare_depart="C", nb_train_circule=10_000, reseau=9_000),
        ]
    )

    resultat = contributions_par_saison(data)

    # Contributions 0.10, 0.20 et 0.90 : médiane 0.20. Un total réseau donnerait
    # (10 + 20 + 9000) / 10 200 = 0.885, écrasé par la plus grosse liaison.
    assert resultat.loc["hiver", "contrib_reseau"] == pytest.approx(0.20)


def test_contributions_par_saison_exclut_les_internationales():
    data = pd.DataFrame(
        [
            _liaison_saison(gare_depart="A", reseau=10),
            _liaison_saison(gare_depart="B", reseau=90, internationale=True),
        ]
    )

    resultat = contributions_par_saison(data)

    assert resultat.loc["hiver", "contrib_reseau"] == pytest.approx(0.10)


def test_contributions_par_saison_trie_les_saisons():
    data = pd.DataFrame(
        [_liaison_saison(saison=s) for s in ["été", "hiver", "automne", "printemps"]]
    )

    resultat = contributions_par_saison(data)

    assert resultat.index.tolist() == ["hiver", "printemps", "été", "automne"]


def test_contributions_par_saison_leve_une_erreur_si_colonne_manquante():
    """Une colonne requise manquante doit lever une `ValueError` explicite."""
    data = pd.DataFrame({"saison": ["hiver"], "nb_train_circule": [100]})

    with pytest.raises(ValueError, match="Colonnes manquantes"):
        contributions_par_saison(data)


def test_familles_causes_couvrent_les_six_colonnes_du_dataset():
    """Les 3 familles doivent couvrir exactement les 6 colonnes `prct_cause_*`."""
    toutes_colonnes = [col for colonnes in FAMILLES_CAUSES.values() for col in colonnes]
    assert len(toutes_colonnes) == 6
    assert len(set(toutes_colonnes)) == 6


def _contributions(reseau, voyageurs, externe):
    """Résultat de `contributions_par_liaison` pour des liaisons A, B, C..."""
    index = pd.MultiIndex.from_tuples(
        [(chr(65 + i), "PARIS") for i in range(len(reseau))],
        names=["gare_depart", "gare_arrivee"],
    )
    return pd.DataFrame(
        {
            "contrib_reseau": reseau,
            "contrib_voyageurs": voyageurs,
            "contrib_externe": externe,
        },
        index=index,
    )


def test_repartition_par_niveau_classe_les_liaisons():
    contributions = _contributions(
        reseau=[0.02, 0.04, 0.07, 0.10],
        voyageurs=[0.05, 0.05, 0.05, 0.05],
        externe=[0.01, 0.01, 0.01, 0.03],
    )

    repartition = repartition_par_niveau(contributions)

    # Réseau : 2, 4, 7 et 10 retards sur 100 → un quart des liaisons par niveau
    assert repartition.loc["reseau"].tolist() == pytest.approx([0.25] * 4)
    # 3 retards sur 100 tombent dans « 3 à 6 » (borne incluse à gauche)
    assert repartition.loc["externe", "3 à 6"] == pytest.approx(0.25)
    assert repartition.sum(axis=1).tolist() == pytest.approx([1.0, 1.0, 1.0])


def test_liaisons_les_plus_touchees_par_famille():
    contributions = _contributions(
        reseau=[0.02, 0.09, 0.05],
        voyageurs=[0.08, 0.01, 0.03],
        externe=[0.01, 0.02, 0.04],
    )

    plus_touchees = liaisons_les_plus_touchees(contributions, n=2)

    assert list(plus_touchees["reseau"].index) == [("B", "PARIS"), ("C", "PARIS")]
    assert list(plus_touchees["voyageurs"].index) == [("A", "PARIS"), ("C", "PARIS")]


def test_contributions_par_saison_total_de_la_liaison_mediane():
    data = pd.DataFrame(
        [
            _liaison_saison(gare_depart="A", reseau=10, voyageurs=5, externe=2),
            _liaison_saison(gare_depart="B", reseau=20, voyageurs=5, externe=5),
            _liaison_saison(gare_depart="C", reseau=4, voyageurs=4, externe=4),
        ]
    )

    resultat = contributions_par_saison(data)

    # Totaux par liaison : 0.17, 0.30, 0.12 → liaison médiane 0.17
    assert resultat.loc["hiver", "total"] == pytest.approx(0.17)
