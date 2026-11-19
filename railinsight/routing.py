"""Tracé des liaisons le long des voies, à partir des lignes du réseau ferré national.

Le tracé officiel (SNCF Réseau, « Formes des lignes du RFN ») est téléchargé une
fois dans ``data/1_raw``, transformé en graphe, puis chaque liaison est tracée par
le plus court chemin entre les deux gares. Si une gare n'est pas reliée au
réseau (gare étrangère, tracé absent), la liaison reste une ligne droite.
"""

import json
from collections.abc import Iterable
from pathlib import Path

import networkx as nx
import numpy as np
import requests
from scipy.spatial import cKDTree
from shapely import LineString, MultiLineString
from shapely.geometry import shape

from railinsight.logger import get_logger

log = get_logger(__name__)

RACINE = Path(__file__).resolve().parents[1]
CHEMIN_RESEAU = RACINE / "data" / "1_raw" / "rfn_lignes_exploitees.geojson"
CHEMIN_CACHE = RACINE / "data" / "3_processed" / "chemins_ferroviaires.json"

URL_RESEAU = (
    "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/"
    "formes-des-lignes-du-rfn/exports/geojson"
    '?where=libelle%3D"Exploit%C3%A9e"&limit=-1'
)

#: Tolérance de Douglas-Peucker (degrés) du tracé renvoyé au navigateur.
TOLERANCE_TRACE = 0.002
#: Tolérance (degrés) appliquée au réseau avant de construire le graphe.
TOLERANCE_GRAPHE = 0.00003
#: Distance maximale entre une gare et le réseau pour la rattacher au graphe.
RAYON_RATTACHEMENT_KM = 5.0
#: Distance (degrés) sous laquelle un bout de tronçon est raccordé à un nœud voisin.
RAYON_JONCTION = 0.002
#: Distance (degrés) sous laquelle un réseau isolé est raccordé au réseau principal.
RAYON_COMPOSANTES = 0.03

KM_PAR_DEGRE = 111.2
#: Cosinus de la latitude moyenne de la France, pour corriger les longitudes.
COS_LATITUDE = 0.69

Point = tuple[float, float]  # (latitude, longitude)


def telecharger_reseau(chemin: Path = CHEMIN_RESEAU, url: str = URL_RESEAU) -> Path:
    """Télécharge le GeoJSON des lignes exploitées s'il n'est pas déjà en cache."""
    if chemin.exists():
        return chemin
    log.info("Téléchargement du tracé du réseau ferré")
    reponse = requests.get(url, timeout=300)
    reponse.raise_for_status()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(reponse.content)
    return chemin


def _distance_km(a: Point, b: Point) -> float:
    return float(np.hypot(a[0] - b[0], (a[1] - b[1]) * COS_LATITUDE) * KM_PAR_DEGRE)


class ReseauFerroviaire:
    """Graphe du réseau ferré, avec calcul de tracés entre deux gares."""

    def __init__(
        self,
        lignes: Iterable[Iterable[tuple[float, float]]],
        chemin_cache: Path | None = None,
    ) -> None:
        """Construit le graphe.

        Args:
            lignes: Polylignes du réseau, en couples (longitude, latitude).
            chemin_cache: Fichier JSON où mémoriser les tracés déjà calculés.
        """
        self._graphe = nx.Graph()
        self._noeuds: dict[Point, int] = {}
        self._coords: list[Point] = []
        extremites: list[int] = []
        for ligne in lignes:
            extremites += self._ajouter_ligne(ligne)
        self._arbre = (
            cKDTree(np.array(self._coords) * [1.0, COS_LATITUDE])
            if self._coords
            else None
        )
        self._relier_extremites(extremites)
        self._raccorder_composantes()
        self._chemin_cache = chemin_cache
        self._cache: dict[str, list[Point] | None] = {}
        self._modifie = False
        if chemin_cache and chemin_cache.exists():
            brut = json.loads(chemin_cache.read_text(encoding="utf-8"))
            self._cache = {
                cle: [(p[0], p[1]) for p in points] if points else None
                for cle, points in brut.items()
            }

    @classmethod
    def depuis_geojson(
        cls, chemin: Path, chemin_cache: Path | None = None
    ) -> "ReseauFerroviaire":
        """Construit le réseau depuis un fichier GeoJSON de lignes."""
        collection = json.loads(chemin.read_text(encoding="utf-8"))
        lignes = []
        for feature in collection["features"]:
            if not feature.get("geometry"):
                continue
            geometrie = shape(feature["geometry"]).simplify(TOLERANCE_GRAPHE)
            parties = (
                geometrie.geoms
                if isinstance(geometrie, MultiLineString)
                else [geometrie]
            )
            lignes += [list(partie.coords) for partie in parties]
        return cls(lignes, chemin_cache)

    def _noeud(self, lat: float, lon: float) -> int:
        cle = (round(lat, 5), round(lon, 5))
        if cle not in self._noeuds:
            self._noeuds[cle] = len(self._coords)
            self._coords.append(cle)
        return self._noeuds[cle]

    def _ajouter_ligne(self, ligne: Iterable[tuple[float, float]]) -> list[int]:
        """Ajoute une polyligne au graphe et renvoie ses deux extrémités."""
        noeuds = []
        precedent = None
        for lon, lat in ligne:
            courant = self._noeud(lat, lon)
            if precedent is not None and precedent != courant:
                poids = _distance_km(self._coords[precedent], self._coords[courant])
                self._graphe.add_edge(precedent, courant, poids=poids)
            precedent = courant
            noeuds.append(courant)
        return [noeuds[0], noeuds[-1]] if noeuds else []

    def _raccorder_composantes(self) -> None:
        """Raccorde au réseau principal les morceaux isolés qui en sont proches.

        Puis ne rattache les gares qu'aux nœuds du réseau principal.
        """
        if self._arbre is None:
            return
        composantes = sorted(nx.connected_components(self._graphe), key=len)[::-1]
        principal = set(composantes[0])
        donnees = self._arbre.data
        for composante in composantes[1:]:
            indices = np.fromiter(principal, dtype=int)
            distances, voisins = cKDTree(donnees[indices]).query(
                donnees[list(composante)]
            )
            meilleur = int(np.argmin(distances))
            if distances[meilleur] <= RAYON_COMPOSANTES:
                noeud = list(composante)[meilleur]
                cible = int(indices[voisins[meilleur]])
                poids = _distance_km(self._coords[noeud], self._coords[cible])
                self._graphe.add_edge(noeud, cible, poids=poids)
                principal |= composante
        self._indices = np.fromiter(principal, dtype=int)
        self._arbre_gares = cKDTree(donnees[self._indices])

    def _relier_extremites(self, extremites: list[int]) -> None:
        """Raccorde les bouts de tronçons aux nœuds voisins.

        Les tronçons du réseau ne se touchent pas exactement aux jonctions.
        """
        if self._arbre is None:
            return
        points = self._arbre.data[extremites]
        for extremite, voisins in zip(
            extremites, self._arbre.query_ball_point(points, RAYON_JONCTION)
        ):
            for voisin in voisins:
                if voisin != extremite:
                    poids = _distance_km(self._coords[extremite], self._coords[voisin])
                    self._graphe.add_edge(extremite, voisin, poids=poids)

    def _rattacher(self, point: Point) -> int | None:
        """Nœud du réseau le plus proche, s'il est assez près de la gare."""
        if self._arbre is None:
            return None
        _, position = self._arbre_gares.query([point[0], point[1] * COS_LATITUDE])
        indice = int(self._indices[position])
        if _distance_km(point, self._coords[indice]) > RAYON_RATTACHEMENT_KM:
            return None
        return indice

    def _calculer(self, depart: Point, arrivee: Point) -> list[Point] | None:
        debut, fin = self._rattacher(depart), self._rattacher(arrivee)
        if debut is None or fin is None:
            return None
        try:
            noeuds = nx.shortest_path(self._graphe, debut, fin, weight="poids")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        return [depart] + [self._coords[n] for n in noeuds] + [arrivee]

    def _chemin(self, depart: Point, arrivee: Point) -> list[Point] | None:
        """Chemin complet le long des voies (cache inclus), ``None`` si impossible."""
        depart = (float(depart[0]), float(depart[1]))
        arrivee = (float(arrivee[0]), float(arrivee[1]))
        cle = f"{depart}|{arrivee}"
        cle_inverse = f"{arrivee}|{depart}"
        if cle in self._cache:
            return self._cache[cle]
        if cle_inverse in self._cache:
            inverse = self._cache[cle_inverse]
            return inverse[::-1] if inverse else None
        self._cache[cle] = self._calculer(depart, arrivee)
        self._modifie = True
        return self._cache[cle]

    @staticmethod
    def _simplifier(points: list[Point]) -> tuple[list[float], list[float]]:
        # Les coordonnées sont en (lat, lon) ; Shapely attend (x, y).
        ligne = LineString([(lon, lat) for lat, lon in points]).simplify(
            TOLERANCE_TRACE
        )
        return [lat for _, lat in ligne.coords], [lon for lon, _ in ligne.coords]

    def tracer(self, depart: Point, arrivee: Point) -> tuple[list[float], list[float]]:
        """Tracé d'une liaison, en listes de latitudes et de longitudes.

        Args:
            depart: Gare de départ, en (latitude, longitude).
            arrivee: Gare d'arrivée, en (latitude, longitude).

        Returns:
            Le tracé le long des voies, ou la ligne droite entre les deux gares
            si l'une n'est pas reliée au réseau.
        """
        chemin = self._chemin(depart, arrivee)
        if not chemin:
            chemin = [depart, arrivee]
        return self._simplifier(chemin)

    def sauver_cache(self) -> None:
        """Écrit les tracés calculés dans le fichier de cache, s'il a changé."""
        if not (self._chemin_cache and self._modifie):
            return
        self._chemin_cache.parent.mkdir(parents=True, exist_ok=True)
        self._chemin_cache.write_text(json.dumps(self._cache), encoding="utf-8")
        self._modifie = False


def charger_reseau() -> ReseauFerroviaire | None:
    """Charge le réseau ferré, ou ``None`` s'il est indisponible (tracés droits)."""
    try:
        chemin = telecharger_reseau()
        return ReseauFerroviaire.depuis_geojson(chemin, CHEMIN_CACHE)
    except (requests.RequestException, OSError, ValueError, KeyError) as err:
        log.warning("Réseau ferré indisponible, tracés en ligne droite : %s", err)
        return None
