"""Chargement et normalisation du jeu de données SNCF."""

from pathlib import Path

import pandas as pd

from railinsight.config import (
    CAUSE_COLUMNS,
    CANCELLED_TRAINS_COLUMN,
    DATE_COLUMN,
    DEFAULT_DATA_PATH,
    DELAYED_15_COLUMN,
    DELAYED_ARRIVAL_COLUMN,
    PLANNED_TRAINS_COLUMN,
    ROUTE_COLUMNS,
)
from railinsight.exceptions import DataLoadError, DataValidationError, MissingColumnsError

REQUIRED_COLUMNS = (
    DATE_COLUMN,
    *ROUTE_COLUMNS,
    PLANNED_TRAINS_COLUMN,
    CANCELLED_TRAINS_COLUMN,
    DELAYED_15_COLUMN,
    DELAYED_ARRIVAL_COLUMN,
    *CAUSE_COLUMNS,
)
MISSING_MARKERS = {"", "na", "n/a", "nan", "null", "none", "?", "-", "—"}


def normalize_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les marqueurs de valeurs manquantes et normalise les types."""
    if not isinstance(data, pd.DataFrame):
        raise DataValidationError("Les données à normaliser doivent être un DataFrame.")

    normalized = data.copy()
    normalized.columns = [str(column).replace("\ufeff", "").strip() for column in data.columns]
    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(normalized.columns))
    if missing_columns:
        raise MissingColumnsError(
            "Colonnes obligatoires manquantes : " + ", ".join(missing_columns)
        )

    for column in normalized.select_dtypes(include=["object", "string"]).columns:
        values = normalized[column].astype("string").str.strip()
        normalized[column] = values.mask(
            values.str.casefold().isin(MISSING_MARKERS), pd.NA
        )

    parsed_dates = pd.to_datetime(
        normalized[DATE_COLUMN], format="%Y-%m", errors="coerce"
    )
    if parsed_dates.isna().any():
        invalid_count = int(parsed_dates.isna().sum())
        raise DataValidationError(
            f"La colonne {DATE_COLUMN!r} contient {invalid_count} date(s) invalide(s)."
        )
    normalized[DATE_COLUMN] = parsed_dates.dt.to_period("M")

    text_columns = [*ROUTE_COLUMNS, "service"]
    for column in text_columns:
        if column in normalized:
            normalized[column] = normalized[column].astype("string").str.strip()

    for column in normalized.columns:
        if column not in (DATE_COLUMN, *text_columns) and (
            pd.api.types.is_object_dtype(normalized[column].dtype)
            or pd.api.types.is_string_dtype(normalized[column].dtype)
        ):
            converted = pd.to_numeric(normalized[column], errors="coerce")
            has_non_missing_text = normalized[column].notna() & converted.isna()
            if has_non_missing_text.any():
                examples = normalized.loc[has_non_missing_text, column].head(3).tolist()
                raise DataValidationError(
                    f"Valeurs non numériques dans {column!r} : {examples!r}."
                )
            normalized[column] = converted

    return normalized


def load_data(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Lit le CSV SNCF puis renvoie un DataFrame normalisé."""
    data_path = Path(path)
    try:
        raw_data = pd.read_csv(data_path, encoding="utf-8-sig")
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise DataLoadError(f"Impossible de lire le fichier {data_path}: {exc}") from exc
    return normalize_dataframe(raw_data)
