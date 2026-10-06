"""Téléchargement explicite des jeux de données open data SNCF."""

from pathlib import Path

import requests

BASE_URL = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets"
DATASETS = [
    "regularite-mensuelle-tgv-aqst",
    "liste-des-gares",
    "lignes-lgv-et-par-ecartement",
    "frequentation-gares"
]

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

for dataset in DATASETS:
    response = requests.get(f"{BASE_URL}/{dataset}/exports/csv?delimiter=,", timeout=120)
    response.raise_for_status()
    (RAW_DIR / f"{dataset}.csv").write_bytes(response.content)
    print(f"{dataset}.csv téléchargé")




