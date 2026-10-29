"""Tests des figures Plotly."""

import pandas as pd
import pytest

from railinsight.viz.charts import (
    CAUSE_COLUMNS,
    cause_stacked_bar,
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


def test_reliability_bar(routes):
    data = routes.assign(unreliable_rate=[0.1, 0.3, 0.2, 0.05])

    figure = reliability_bar(data, top_n=2)

    assert sorted(figure.data[0].x) == [0.2, 0.3]


def test_reliability_bar_colonnes_manquantes(routes):
    with pytest.raises(ValueError, match="fiabilité"):
        reliability_bar(routes)


def test_reliability_bar_top_n_invalide(routes):
    data = routes.assign(unreliable_rate=0.1)

    with pytest.raises(ValueError, match="top_n"):
        reliability_bar(data, top_n=0)


def test_cause_stacked_bar():
    data = pd.DataFrame({"season": ["Hiver", "Été"]})
    for column in CAUSE_COLUMNS:
        data[column] = [10.0, 20.0]

    figure = cause_stacked_bar(data, CAUSE_COLUMNS[:2])

    assert len(figure.data) == 2


def test_cause_stacked_bar_colonnes_manquantes():
    with pytest.raises(ValueError, match="saison"):
        cause_stacked_bar(pd.DataFrame({"season": ["Hiver"]}))


def test_cause_stacked_bar_cause_inconnue():
    data = pd.DataFrame({"season": ["Hiver"], "autre": [1.0]})

    with pytest.raises(ValueError, match="inconnues"):
        cause_stacked_bar(data, ["autre"])


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
