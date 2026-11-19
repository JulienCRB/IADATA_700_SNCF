"""Tests des figures Plotly."""

import pandas as pd
import pytest

from railinsight.viz.charts import (
    carte_difficulte,
    contributions_saison_bar,
    evolution_avant_apres,
    gares_concernees_bar,
    historique_composantes_line,
    niveaux_par_famille_bar,
    retards_sur_100_bar,
)


@pytest.fixture
def stations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "gare": ["PARIS", "LYON", "LILLE"],
            "latitude": [48.85, 45.76, 50.63],
            "longitude": [2.35, 4.83, 3.06],
        }
    )


def test_contributions_saison_bar_une_serie_par_famille():
    contributions = pd.DataFrame(
        {
            "contrib_reseau": [0.06, 0.05],
            "contrib_voyageurs": [0.04, 0.07],
            "contrib_externe": [0.03, 0.03],
        },
        index=pd.Index(["hiver", "été"], name="saison"),
    )

    figure = contributions_saison_bar(contributions)

    assert [trace.name for trace in figure.data] == ["Réseau", "Voyageurs", "Externe"]
    # Les contributions sont affichées en points de taux de retard
    assert list(figure.data[0].y) == pytest.approx([6.0, 5.0])


def test_contributions_saison_bar_colonnes_manquantes():
    with pytest.raises(ValueError, match="contributions"):
        contributions_saison_bar(pd.DataFrame({"contrib_reseau": [0.1]}))


def test_historique_composantes_line_une_courbe_par_composante():
    historique = pd.DataFrame(
        {
            "part_retard": [0.10, 0.12],
            "taux_annulation": [0.01, 0.02],
            "retard_moyen_tous_trains": [3.0, 4.0],
        },
        index=pd.Index([2025, 2026], name="annee"),
    )

    figure = historique_composantes_line(historique)

    assert len(figure.data) == 3
    # Les taux sont affichés en pourcentage
    assert list(figure.data[0].y) == pytest.approx([10.0, 12.0])


def test_historique_composantes_line_colonnes_manquantes():
    with pytest.raises(ValueError, match="composantes"):
        historique_composantes_line(pd.DataFrame({"part_retard": [0.1]}))


def test_retards_sur_100_bar_un_segment_par_famille():
    poids = pd.Series({"reseau": 0.057, "voyageurs": 0.052, "externe": 0.030})

    figure = retards_sur_100_bar(
        poids, {"reseau": "Réseau", "voyageurs": "Trains", "externe": "Aléas"}
    )

    assert [trace.x[0] for trace in figure.data] == [6, 5, 3]
    assert figure.data[1].text[0] == "5 · trains"


def test_retards_sur_100_bar_familles_manquantes():
    with pytest.raises(ValueError, match="trois familles"):
        retards_sur_100_bar(pd.Series({"reseau": 0.05}))


def test_niveaux_par_famille_bar_une_barre_par_famille_a_100_pourcent():
    repartition = pd.DataFrame(
        {
            "moins de 3": [0.1, 0.2, 0.5],
            "3 à 6": [0.5, 0.6, 0.5],
            "6 et plus": [0.4, 0.2, 0.0],
        },
        index=["reseau", "voyageurs", "externe"],
    )

    figure = niveaux_par_famille_bar(repartition)

    # Une série par niveau, chacune avec une valeur par famille
    assert [trace.name for trace in figure.data] == ["moins de 3", "3 à 6", "6 et plus"]
    assert list(figure.data[0].x) == pytest.approx([10.0, 20.0, 50.0])
    # Les petites parts (moins de 5 %) ne sont pas étiquetées
    assert figure.data[2].text[2] == ""


def test_niveaux_par_famille_bar_familles_manquantes():
    with pytest.raises(ValueError, match="trois familles"):
        niveaux_par_famille_bar(pd.DataFrame({"x": [1.0]}, index=["reseau"]))


def _bilan():
    return pd.DataFrame(
        {
            "gare_depart": ["A", "B", "C"],
            "gare_arrivee": ["PARIS", "PARIS", "PARIS"],
            "en_difficulte": [True, True, False],
            "taux_reference": [0.20, 0.25, 0.10],
            "taux_suivi": [0.30, 0.24, 0.12],
            "tendance": ["s'aggrave", "résiste mieux", "suit le réseau"],
        }
    ).set_index(["gare_depart", "gare_arrivee"])


def test_evolution_avant_apres_relie_les_deux_periodes():
    figure = evolution_avant_apres(_bilan())
    lignes = {trace.name: trace for trace in figure.data}

    # A s'aggrave : une ligne de 20 (avant) à 30 (2026) trains en retard sur 100
    assert list(lignes["s'aggrave"].x[:2]) == pytest.approx([20.0, 30.0])
    assert list(lignes["s'aggrave"].y[:2]) == ["A → PARIS", "A → PARIS"]
    # Seules les liaisons en difficulté apparaissent (C est exclue)
    assert set(lignes["2026"].y) == {"A → PARIS", "B → PARIS"}


def test_evolution_avant_apres_colonnes_manquantes():
    with pytest.raises(ValueError, match="évolution"):
        evolution_avant_apres(pd.DataFrame({"en_difficulte": [True]}))


def test_gares_concernees_bar_garde_les_plus_concernees():
    gares = pd.Series({"PARIS LYON": 8, "LYON PART DIEU": 7, "LILLE": 4})

    figure = gares_concernees_bar(gares, top_n=2)

    assert list(figure.data[0].y) == ["PARIS LYON", "LYON PART DIEU"]


def test_gares_concernees_bar_top_n_invalide():
    with pytest.raises(ValueError, match="top_n"):
        gares_concernees_bar(pd.Series({"PARIS": 1}), top_n=0)


def test_contributions_saison_bar_noms_grand_public():
    contributions = pd.DataFrame(
        {
            "contrib_reseau": [0.06],
            "contrib_voyageurs": [0.05],
            "contrib_externe": [0.03],
            "total": [0.14],
        },
        index=pd.Index(["été"], name="saison"),
    )
    libelles = {"reseau": "Réseau", "voyageurs": "Trains et gares", "externe": "Aléas"}

    figure = contributions_saison_bar(contributions, libelles)

    assert [trace.name for trace in figure.data] == [
        "Réseau",
        "Trains et gares",
        "Aléas",
    ]
    assert list(figure.data[0].x) == ["Été"]


def test_carte_difficulte_colore_les_liaisons_en_difficulte(stations):
    index = pd.MultiIndex.from_tuples(
        [("PARIS", "LYON"), ("PARIS", "LILLE"), ("LYON", "INCONNUE")],
        names=["gare_depart", "gare_arrivee"],
    )
    bilan = pd.DataFrame(
        {
            "en_difficulte": [True, False, True],
            "tendance": ["s'aggrave", "suit le réseau", "résiste mieux"],
        },
        index=index,
    )

    figure = carte_difficulte(bilan, stations)
    traces = {trace.name: trace for trace in figure.data}

    # PARIS → LYON en rouge ; LYON → INCONNUE ignorée (pas de coordonnées)
    assert traces["s'aggrave"].text[0] == "PARIS → LYON"
    assert list(traces["résiste mieux"].lat) == []
    assert set(traces["Gares concernées"].text) == {"LYON", "PARIS"}


def test_carte_difficulte_colonnes_manquantes(stations):
    with pytest.raises(ValueError, match="difficulté"):
        carte_difficulte(pd.DataFrame({"x": [1]}), stations)
    bilan = pd.DataFrame({"en_difficulte": [True], "tendance": ["s'aggrave"]})
    with pytest.raises(ValueError, match="coordonnées"):
        carte_difficulte(bilan, pd.DataFrame({"gare": ["PARIS"]}))


def test_carte_difficulte_dessine_les_courtes_au_dessus_avec_une_couleur(stations):
    index = pd.MultiIndex.from_tuples(
        [("PARIS", "LILLE"), ("PARIS", "LYON")], names=["gare_depart", "gare_arrivee"]
    )
    bilan = pd.DataFrame(
        {"en_difficulte": [True, True], "tendance": ["s'aggrave"] * 2}, index=index
    )

    figure = carte_difficulte(bilan, stations)
    liaisons = [t for t in figure.data if t.name == "s'aggrave" and t.lat]

    # PARIS → LYON (la plus longue) d'abord, donc dessinée sous PARIS → LILLE
    assert [t.text[0] for t in liaisons] == ["PARIS → LYON", "PARIS → LILLE"]
    assert liaisons[0].line.color == liaisons[1].line.color
    assert liaisons[0].line.width == liaisons[1].line.width
    assert [t.showlegend for t in liaisons] == [True, False]


def test_carte_difficulte_garde_une_entree_de_legende_par_tendance(stations):
    index = pd.MultiIndex.from_tuples(
        [("PARIS", "LYON")], names=["gare_depart", "gare_arrivee"]
    )
    bilan = pd.DataFrame(
        {"en_difficulte": [True], "tendance": ["s'aggrave"]}, index=index
    )

    figure = carte_difficulte(bilan, stations)
    legendes = [t.name for t in figure.data if t.showlegend is not False]

    assert legendes.count("s'aggrave") == 1
    assert "résiste mieux" in legendes
