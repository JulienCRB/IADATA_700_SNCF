"""Tests de la classe Regularite (point d'entrée des analyses)."""

from pathlib import Path

import pandas as pd
import pytest

import railinsight.regularite as module_regularite
from railinsight.data.loader import REGULARITE
from railinsight.regularite import Regularite

DATA_TEST_DIR = Path(__file__).parent / "data_test"

#: Taux de retard de chaque liaison de test (la dernière est internationale).
TAUX_PAR_LIAISON = {"A": 0.40, "B": 0.10, "C": 0.12, "D": 0.08, "GENEVE": 0.50}


def _charger_csv_test(dataset: str) -> pd.DataFrame:
    return pd.read_csv(DATA_TEST_DIR / f"{dataset}.csv")


def _jeu_brut() -> pd.DataFrame:
    """Petit jeu brut au format SNCF : 5 liaisons vers Paris, oct. 2022 → sept. 2026."""
    lignes = []
    for date in pd.date_range("2022-10", "2026-09", freq="MS").strftime("%Y-%m"):
        for depart, taux in TAUX_PAR_LIAISON.items():
            lignes.append(
                {
                    "date": date,
                    "gare_depart": depart,
                    "gare_arrivee": "PARIS",
                    "duree_moyenne": 200,
                    "nb_train_prevu": 110,
                    "nb_annulation": 10,
                    "nb_train_retard_arrivee": int(taux * 100),
                    "retard_moyen_tous_trains_arrivee": taux * 20,
                    "prct_cause_externe": 20,
                    "prct_cause_infra": 30,
                    "prct_cause_gestion_trafic": 20,
                    "prct_cause_materiel_roulant": 10,
                    "prct_cause_gestion_gare": 10,
                    "prct_cause_prise_en_charge_voyageurs": 10,
                }
            )
    return pd.DataFrame(lignes)


@pytest.fixture
def regularite() -> Regularite:
    return Regularite(_jeu_brut())


def test_init_prepare_les_colonnes_communes(regularite):
    colonnes = regularite.data.columns

    for colonne in ["annee", "classe_duree", "internationale", "cause_fiable"]:
        assert colonne in colonnes
    assert "nb_retard_reseau" in colonnes


def test_data_renvoie_une_copie(regularite):
    """Encapsulation : modifier la copie ne change pas les données de l'objet."""
    copie = regularite.data
    copie["nb_train_prevu"] = 0

    assert (regularite.data["nb_train_prevu"] == 110).all()


def test_depuis_sncf_telecharge_puis_prepare(monkeypatch):
    """Pas de réseau dans les tests : lecture depuis le fichier CSV de test."""
    monkeypatch.setattr(module_regularite, "load", _charger_csv_test)

    reg = Regularite.depuis_sncf()

    df_attendu = _charger_csv_test(REGULARITE)
    assert len(reg.data) == len(df_attendu)
    assert "classe_duree" in reg.data.columns
    assert "cause_fiable" in reg.data.columns


def test_contributions_par_liaison_sans_internationales(regularite):
    contributions = regularite.contributions_par_liaison()

    assert "GENEVE" not in contributions.index.get_level_values("gare_depart")
    # Réseau = infra (30 %) + gestion du trafic (20 %) : la famille dominante
    assert (contributions["cause_dominante"] == "reseau").all()


def test_liaisons_en_difficulte_selectionne_la_pire_liaison(regularite):
    bilan = regularite.liaisons_en_difficulte()

    selection = bilan[bilan["en_difficulte"]].index.get_level_values("gare_depart")
    assert list(selection) == ["A"]
    assert "cause_evolution" in bilan.columns


def test_contributions_par_saison_quatre_saisons(regularite):
    saisons = regularite.contributions_par_saison()

    assert saisons.index.tolist() == ["hiver", "printemps", "été", "automne"]


def test_score_fiabilite_avec_part_interne(regularite):
    scores = regularite.score_fiabilite()

    # A a le plus de retards : c'est la moins fiable de sa classe
    assert scores["score_fiabilite"].idxmax() == ("A", "PARIS")
    assert pd.isna(scores.loc[("GENEVE", "PARIS"), "score_fiabilite"])
    # Réseau + Voyageurs = 30 + 20 + 10 + 10 + 10 = 80 % des retards
    assert scores["part_origine_interne"].iloc[0] == pytest.approx(0.8)


def test_nb_liaisons_et_periode(regularite):
    assert regularite.nb_liaisons == len(TAUX_PAR_LIAISON)
    assert regularite.periode == ("2022-10", "2026-09")


def test_liaisons_en_difficulte_ajoute_l_axe(regularite):
    bilan = regularite.liaisons_en_difficulte()

    assert bilan.loc[("A", "PARIS"), "axe"] == "A ↔ PARIS"


def test_historique_composantes_une_ligne_par_annee(regularite):
    historique = regularite.historique_composantes().loc[("A", "PARIS")]

    # Oct. 2022 → sept. 2026 : les années 2023 à 2026
    assert historique.index.tolist() == [2023, 2024, 2025, 2026]
    assert historique["part_retard"].iloc[0] == pytest.approx(0.40)


def test_contribution_mediane_par_famille(regularite):
    poids = regularite.contribution_mediane()

    # Liaisons nationales A, B, C, D : taux 0.40, 0.10, 0.12, 0.08 → médiane 0.11.
    # Externe = 20 % des retards → 0.11 x 0.20 = 0.022, même sans être dominant.
    assert poids.index.tolist() == ["reseau", "voyageurs", "externe"]
    assert poids["externe"] == pytest.approx(0.022)


def test_score_fiabilite_verdict_en_mots(regularite):
    scores = regularite.score_fiabilite()

    # A est la moins fiable des 4 liaisons nationales ; GENEVE n'a pas de verdict
    assert scores.loc[("A", "PARIS"), "niveau"] == "peu fiable"
    assert scores.loc[("A", "PARIS"), "plus_fiable_que"] == pytest.approx(0.0)
    assert pd.isna(scores.loc[("GENEVE", "PARIS"), "niveau"])


def test_score_fiabilite_en_etoiles(regularite):
    scores = regularite.score_fiabilite()

    # D a le moins de retards : la plus fiable, donc le plus d'étoiles
    assert scores["etoiles"].idxmax() == ("D", "PARIS")
    assert scores["etoiles"].dropna().between(0, 5).all()
