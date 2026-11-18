"""Tests du routage ferroviaire."""

import json

import pandas as pd
import pytest
import requests

from railinsight import routing
from railinsight.routing import ReseauFerroviaire
from railinsight.viz.charts import carte_difficulte

# Deux voies en L : A(lat 0, lon 0) -> B(0, 1) -> C(1, 1), en (lon, lat).
LIGNES = [[(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)], [(1.0, 0.0), (1.0, 0.5), (1.0, 1.0)]]
A, B, C = (0.0, 0.0), (0.0, 1.0), (1.0, 1.0)


@pytest.fixture
def reseau() -> ReseauFerroviaire:
    return ReseauFerroviaire(LIGNES)


def test_tracer_suit_les_voies_et_pas_la_ligne_droite(reseau):
    lats, lons = reseau.tracer(A, C)

    assert (lats[0], lons[0]) == A
    assert (lats[-1], lons[-1]) == C
    assert (0.0, 1.0) in list(zip(lats, lons))  # passe par le coude


def test_tracer_sens_inverse_reutilise_le_trace(reseau):
    lats, lons = reseau.tracer(A, C)
    lats_inv, lons_inv = reseau.tracer(C, A)

    assert lats_inv == lats[::-1]
    assert lons_inv == lons[::-1]


def test_gare_hors_reseau_donne_une_ligne_droite(reseau):
    etranger = (41.0, 2.0)

    assert reseau.tracer(A, etranger) == ([0.0, 41.0], [0.0, 2.0])


def test_gares_sans_chemin_donnent_une_ligne_droite():
    reseau = ReseauFerroviaire([[(0.0, 0.0), (0.1, 0.0)], [(1.0, 1.0), (1.1, 1.0)]])

    assert reseau.tracer((0.0, 0.0), (1.0, 1.0)) == ([0.0, 1.0], [0.0, 1.0])


def test_reseau_vide_donne_une_ligne_droite():
    assert ReseauFerroviaire([]).tracer(A, C) == ([0.0, 1.0], [0.0, 1.0])


def test_cache_sur_disque(tmp_path):
    chemin = tmp_path / "cache.json"
    reseau = ReseauFerroviaire(LIGNES, chemin)
    attendu = reseau.tracer(A, C)
    reseau.sauver_cache()

    relu = ReseauFerroviaire([], chemin)

    assert relu.tracer(A, C) == attendu
    relu.sauver_cache()  # rien de neuf : pas d'écriture


def test_depuis_geojson(tmp_path):
    collection = {
        "features": [
            {"geometry": {"type": "LineString", "coordinates": LIGNES[0]}},
            {
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [LIGNES[1]],
                }
            },
            {"geometry": None},
        ]
    }
    chemin = tmp_path / "rfn.geojson"
    chemin.write_text(json.dumps(collection), encoding="utf-8")

    reseau = ReseauFerroviaire.depuis_geojson(chemin)

    assert (0.0, 1.0) in list(zip(*reseau.tracer(A, C)))


def test_telecharger_reseau_utilise_le_fichier_existant(tmp_path, monkeypatch):
    chemin = tmp_path / "rfn.geojson"
    chemin.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(routing.requests, "get", lambda *a, **k: 1 / 0)

    assert routing.telecharger_reseau(chemin) == chemin


def test_telecharger_reseau_ecrit_le_fichier(tmp_path, monkeypatch):
    class Reponse:
        content = b"{}"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(routing.requests, "get", lambda *a, **k: Reponse())
    chemin = tmp_path / "dossier" / "rfn.geojson"

    assert routing.telecharger_reseau(chemin).read_bytes() == b"{}"


def test_charger_reseau_hors_ligne_renvoie_none(monkeypatch):
    def echec(*args, **kwargs):
        raise requests.ConnectionError("hors ligne")

    monkeypatch.setattr(routing, "telecharger_reseau", echec)

    assert routing.charger_reseau() is None


def test_charger_reseau(tmp_path, monkeypatch):
    chemin = tmp_path / "rfn.geojson"
    chemin.write_text(
        json.dumps(
            {
                "features": [
                    {"geometry": {"type": "LineString", "coordinates": LIGNES[0]}}
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(routing, "telecharger_reseau", lambda: chemin)
    monkeypatch.setattr(routing, "CHEMIN_CACHE", tmp_path / "cache.json")

    assert isinstance(routing.charger_reseau(), ReseauFerroviaire)


def test_carte_difficulte_utilise_le_reseau(reseau):
    stations = pd.DataFrame(
        {"gare": ["A", "C"], "latitude": [0.0, 1.0], "longitude": [0.0, 1.0]}
    )
    index = pd.MultiIndex.from_tuples([("A", "C")], names=["d", "a"])
    bilan = pd.DataFrame(
        {"en_difficulte": [True], "tendance": ["s'aggrave"]}, index=index
    )

    figure = carte_difficulte(bilan, stations, reseau)
    trace = {t.name: t for t in figure.data}["s'aggrave"]

    assert len(trace.lat) > 2  # extrémités + coude
    assert trace.text[0] == "A → C"
