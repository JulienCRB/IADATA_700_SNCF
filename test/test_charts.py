"""Tests des figures Plotly."""

import pandas as pd
import pytest

from railinsight.viz.charts import (
    contributions_saison_bar,
    network_map,
    reliability_bar,
    station_ranking,
)


@pytest.fixture
def routes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "gare_depart": ["PARIS", "LYON", "PARIS", "INCONNUE"],
            "gare_arrivee": ["LYON", "PARIS", "LILLE", "PARIS"],
        }
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


@pytest.fixture
def scores() -> pd.DataFrame:
    index = pd.MultiIndex.from_tuples(
        [("PARIS", "LYON"), ("LYON", "PARIS"), ("PARIS", "LILLE"), ("PARIS", "GENEVE")],
        names=["gare_depart", "gare_arrivee"],
    )
    return pd.DataFrame({"score_fiabilite": [0.1, 0.9, 0.5, None]}, index=index)


def test_reliability_bar_garde_les_moins_fiables(scores):
    figure = reliability_bar(scores, top_n=2)

    assert sorted(figure.data[0].x) == [0.5, 0.9]
    assert "LYON → PARIS" in figure.data[0].y


def test_reliability_bar_ignore_les_liaisons_sans_score(scores):
    figure = reliability_bar(scores, top_n=10)

    assert len(figure.data[0].x) == 3


def test_reliability_bar_colonnes_manquantes(routes):
    with pytest.raises(ValueError, match="score"):
        reliability_bar(routes)


def test_reliability_bar_top_n_invalide(scores):
    with pytest.raises(ValueError, match="top_n"):
        reliability_bar(scores, top_n=0)


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


def test_network_map(routes, stations):
    figure = network_map(routes, stations)

    # PARIS-LYON (deux sens) et PARIS-LILLE ; INCONNUE est ignorée.
    assert "2 liaisons TGV entre 3 gares" in figure.layout.title.text
    assert len(figure.data) == 2


def test_network_map_routes_invalides(stations):
    with pytest.raises(ValueError, match="départ et arrivée"):
        network_map(pd.DataFrame({"a": [1]}), stations)


def test_network_map_gares_invalides(routes):
    with pytest.raises(ValueError, match="coordonnées"):
        network_map(routes, pd.DataFrame({"gare": ["PARIS"]}))


def test_station_ranking(routes):
    figure = station_ranking(routes)

    assert "PARIS" in figure.data[0].y
    assert max(figure.data[0].x) == 3


def test_station_ranking_top_n(routes):
    figure = station_ranking(routes, top_n=1)

    assert list(figure.data[0].y) == ["PARIS"]


def test_station_ranking_routes_invalides():
    with pytest.raises(ValueError, match="départ et arrivée"):
        station_ranking(pd.DataFrame({"a": [1]}))


def test_station_ranking_top_n_invalide(routes):
    with pytest.raises(ValueError, match="top_n"):
        station_ranking(routes, top_n=0)
