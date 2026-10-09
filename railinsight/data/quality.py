"""Indicateurs de qualité et repérage exploratoire des valeurs extrêmes."""

import pandas as pd

from railinsight.config import OUTLIER_IQR_MULTIPLIER
from railinsight.exceptions import DataValidationError


def missing_report(data: pd.DataFrame) -> pd.DataFrame:
    """Retourne le nombre et le pourcentage de valeurs manquantes par colonne."""
    if not isinstance(data, pd.DataFrame):
        raise DataValidationError("Le rapport de valeurs manquantes attend un DataFrame.")
    counts = data.isna().sum()
    return pd.DataFrame(
        {
            "missing_count": counts.astype("int64"),
            "missing_percent": (counts / len(data) * 100 if len(data) else 0.0),
        }
    )


def outlier_flags(
    data: pd.DataFrame, columns: list[str] | tuple[str, ...] | None = None
) -> pd.DataFrame:
    """Signale les valeurs extrêmes numériques selon la règle de Tukey."""
    if not isinstance(data, pd.DataFrame):
        raise DataValidationError("Le repérage d'extrêmes attend un DataFrame.")

    selected = list(columns) if columns is not None else list(
        data.select_dtypes(include="number").columns
    )
    unknown = sorted(set(selected).difference(data.columns))
    if unknown:
        raise DataValidationError("Colonnes inconnues : " + ", ".join(unknown))
    non_numeric = [
        column for column in selected
        if not pd.api.types.is_numeric_dtype(data[column].dtype)
    ]
    if non_numeric:
        raise DataValidationError(
            "Le repérage d'extrêmes exige des colonnes numériques : "
            + ", ".join(non_numeric)
        )

    flags = pd.DataFrame(False, index=data.index, columns=selected, dtype=bool)
    for column in selected:
        values = data[column]
        if values.notna().sum() < 2:
            continue
        first_quartile = values.quantile(0.25)
        third_quartile = values.quantile(0.75)
        spread = third_quartile - first_quartile
        flags[column] = (values < first_quartile - OUTLIER_IQR_MULTIPLIER * spread) | (
            values > third_quartile + OUTLIER_IQR_MULTIPLIER * spread
        )
    return flags
