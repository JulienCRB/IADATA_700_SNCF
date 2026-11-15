"""Tests des liaisons durablement en difficulté (Phase 2)."""

import pandas as pd
import pytest

from railinsight.analysis.difficulte import (
    cause_de_l_evolution,
    evolution_causes,
    liaisons_en_difficulte,
    seuils_par_classe,
    taux_par_annee,
)


def _mois(depart="A", annee=2023, circules=100, retards=10, internationale=False):
    """Une observation préparée (liaison x mois) avec les colonnes utiles."""
    return {
        "gare_depart": depart,
        "gare_arrivee": "PARIS",
        "date": f"{annee}-01",
        "annee": annee,
        "classe_duree": "> 3h",
        "internationale": internationale,
        "nb_train_circule": circules,
        "nb_train_retard_arrivee": retards,
    }


def test_taux_par_annee_calcule_sur_les_trains_circules():
    data = pd.DataFrame([_mois(circules=200, retards=30)])

    resultat = taux_par_annee(data)

    assert resultat.loc[0, "taux_retard"] == pytest.approx(0.15)


def test_taux_par_annee_ecarte_internationales_et_petits_volumes():
    data = pd.DataFrame(
        [
            _mois(depart="A", circules=200),
            _mois(depart="B", circules=50),
            _mois(depart="C", circules=200, internationale=True),
        ]
    )

    resultat = taux_par_annee(data, volume_min=100)

    # Une seule date dans l'année → volume requis 100 x 1/12 ≈ 8 trains
    assert resultat["gare_depart"].tolist() == ["A", "B"]

    resultat_annee_complete = taux_par_annee(data, volume_min=1200)
    assert resultat_annee_complete["gare_depart"].tolist() == ["A"]


def _par_an(depart, taux_par_annee_dict):
    """Lignes de `taux_par_annee` pour une liaison, à partir de {année: taux}."""
    return [
        {
            "gare_depart": depart,
            "gare_arrivee": "PARIS",
            "annee": annee,
            "classe_duree": "> 3h",
            "nb_train_circule": 100,
            "nb_train_retard_arrivee": taux * 100,
            "taux_retard": taux,
        }
        for annee, taux in taux_par_annee_dict.items()
    ]


def test_seuils_par_classe_sur_la_periode_de_reference_seulement():
    par_an = pd.DataFrame(
        _par_an("A", {2023: 0.10, 2024: 0.10, 2020: 0.90})
        + _par_an("B", {2023: 0.20, 2024: 0.20, 2020: 0.90})
    )

    seuils = seuils_par_classe(par_an, annees=[2023, 2024], quantile=0.5)

    # 2020 (hors référence) est ignorée : médiane de 0.10, 0.10, 0.20, 0.20
    assert seuils["> 3h"] == pytest.approx(0.15)


@pytest.fixture
def par_an() -> pd.DataFrame:
    return pd.DataFrame(
        _par_an("MAUVAISE", {2023: 0.40, 2024: 0.42, 2025: 0.44, 2026: 0.52})
        + _par_an("LIMITE", {2023: 0.50, 2024: 0.05, 2025: 0.05, 2026: 0.10})
        + _par_an("BONNE", {2023: 0.05, 2024: 0.05, 2025: 0.05, 2026: 0.07})
        + _par_an("CORRECTE", {2023: 0.10, 2024: 0.10, 2025: 0.10, 2026: 0.13})
    )


def test_liaisons_en_difficulte_au_moins_deux_annees_au_dessus(par_an):
    # Seuil (quartile supérieur des 12 taux de référence) : 0.405.
    # MAUVAISE le dépasse 2 années (0.42, 0.44), LIMITE une seule (0.50).
    bilan = liaisons_en_difficulte(par_an, annees_reference=[2023, 2024, 2025])

    selection = bilan[bilan["en_difficulte"]].index.get_level_values("gare_depart")
    assert list(selection) == ["MAUVAISE"]
    assert bilan.loc[("LIMITE", "PARIS"), "nb_annees_au_dessus"] == 1


def test_liaisons_en_difficulte_evolution_relative_a_la_tendance(par_an):
    bilan = liaisons_en_difficulte(par_an, annees_reference=[2023, 2024, 2025])

    mauvaise = bilan.loc[("MAUVAISE", "PARIS")]
    assert mauvaise["evolution"] == pytest.approx(0.10)
    # Évolutions des autres : -0.10 (LIMITE), +0.02, +0.03 → médiane +0.02
    assert mauvaise["evolution_relative"] == pytest.approx(0.08)


def _mois_causes(depart, annee, reseau, voyageurs=0, externe=0):
    return {
        "gare_depart": depart,
        "gare_arrivee": "PARIS",
        "annee": annee,
        "internationale": False,
        "cause_fiable": True,
        "nb_train_circule": 100,
        "nb_retard_reseau": reseau,
        "nb_retard_voyageurs": voyageurs,
        "nb_retard_externe": externe,
    }


def test_evolution_causes_et_cause_de_l_evolution():
    data = pd.DataFrame(
        [
            _mois_causes("A", 2024, reseau=10, externe=5),
            _mois_causes("A", 2026, reseau=20, externe=6),
            _mois_causes("B", 2024, reseau=10, externe=5),
            _mois_causes("B", 2026, reseau=10, externe=9),
        ]
    )

    delta = evolution_causes(data, annees_reference=[2024], annee_suivi=2026)

    assert delta.loc[("A", "PARIS"), "contrib_reseau"] == pytest.approx(0.10)
    assert delta.loc[("B", "PARIS"), "contrib_externe"] == pytest.approx(0.04)

    en_difficulte = pd.Series(
        [True, False],
        index=pd.MultiIndex.from_tuples(
            [("A", "PARIS"), ("B", "PARIS")], names=["gare_depart", "gare_arrivee"]
        ),
    )
    causes = cause_de_l_evolution(delta, en_difficulte)

    # A : +0.10 de Réseau contre +0.00 pour B → le Réseau porte son évolution
    assert causes.to_dict() == {("A", "PARIS"): "reseau"}
