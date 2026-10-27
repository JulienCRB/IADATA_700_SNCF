"""Configuration partagée du projet RailInsight."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
LOG_DIR = DATA_DIR / "logs"

DATE_COLUMN = "date"
ROUTE_COLUMNS = ("gare_depart", "gare_arrivee")
PLANNED_TRAINS_COLUMN = "nb_train_prevu"
CANCELLED_TRAINS_COLUMN = "nb_annulation"
DELAYED_15_COLUMN = "nb_train_retard_sup_15"
DELAYED_ARRIVAL_COLUMN = "nb_train_retard_arrivee"
CAUSE_COLUMNS = (
    "prct_cause_externe",
    "prct_cause_infra",
    "prct_cause_gestion_trafic",
    "prct_cause_materiel_roulant",
    "prct_cause_gestion_gare",
    "prct_cause_prise_en_charge_voyageurs",
)
OUTLIER_IQR_MULTIPLIER = 1.5
