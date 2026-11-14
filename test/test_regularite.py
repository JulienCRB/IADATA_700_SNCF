"""Tests de la classe Regularite (point d'entrée des analyses)."""

import pandas as pd
import pytest

import railinsight.regularite as module_regularite
from railinsight.regularite import Regularite

#: Taux de retard de chaque liaison de test (la dernière est internationale).
TAUX_PAR_LIAISON = {"A": 0.40, "B": 0.10, "C": 0.12, "D": 0.08, "GENEVE": 0.50}


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
    """Pas de réseau dans les tests : le téléchargement est remplacé."""
    monkeypatch.setattr(module_regularite, "load", lambda dataset: _jeu_brut())

    regularite = Regularite.depuis_sncf()

    assert len(regularite.data) == len(_jeu_brut())


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
