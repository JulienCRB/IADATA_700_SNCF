"""Téléchargement explicite du jeu de données open data SNCF."""

from pathlib import Path

import requests

URL = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/regularite-mensuelle-tgv-aqst/exports/csv?delimiter=,"
# Racine du dépôt 
ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "data" / "raw" / "regularite-mensuelle-tgv-aqst.csv"

DEST.parent.mkdir(parents=True, exist_ok=True)
request = requests.get(URL, timeout=120)
request.raise_for_status()
DEST.write_bytes(request.content)




