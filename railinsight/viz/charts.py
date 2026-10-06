"""Figures Plotly pour les résultats des analyses RailInsight."""

from collections.abc import Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from railinsight.config import CAUSE_COLUMNS, ROUTE_COLUMNS
from railinsight.exceptions import DataValidationError

CAUSE_LABELS = {
    "prct_cause_externe": "Causes externes",
    "prct_cause_infra": "Infrastructure",
    "prct_cause_gestion_trafic": "Gestion du trafic",
    "prct_cause_materiel_roulant": "Matériel roulant",
    "prct_cause_gestion_gare": "Gestion en gare",
    "prct_cause_prise_en_charge_voyageurs": "Prise en charge voyageurs",
}


def reliability_bar(data: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Construit un classement graphique des liaisons les moins fiables."""
    if "unreliable_rate" not in data or not set(ROUTE_COLUMNS).issubset(data.columns):
        raise DataValidationError("Le résultat ne contient pas les colonnes de fiabilité.")
    if top_n < 1:
        raise DataValidationError("top_n doit être supérieur ou égal à 1.")
    chart_data = data.nlargest(top_n, "unreliable_rate").copy()
    chart_data["liaison"] = chart_data[ROUTE_COLUMNS[0]].astype(str) + " → " + chart_data[
        ROUTE_COLUMNS[1]
    ].astype(str)
    return px.bar(
        chart_data,
        x="unreliable_rate",
        y="liaison",
        orientation="h",
        labels={"unreliable_rate": "Annulations et retards > 15 min", "liaison": "Liaison"},
        title="Liaisons TGV les moins fiables",
    ).update_layout(yaxis={"categoryorder": "total ascending"})


def cause_stacked_bar(data: pd.DataFrame, columns: Sequence[str] = CAUSE_COLUMNS) -> go.Figure:
    """Construit un graphique empilé de la saisonnalité des causes."""
    selected = list(columns)
    if not {"season", *selected}.issubset(data.columns):
        raise DataValidationError("Le résultat ne contient pas les colonnes saison/causes.")
    unknown_causes = sorted(set(selected).difference(CAUSE_COLUMNS))
    if unknown_causes:
        raise DataValidationError("Causes inconnues : " + ", ".join(unknown_causes))
    chart_data = data.melt(
        id_vars="season", value_vars=selected, var_name="cause", value_name="part"
    )
    chart_data["cause"] = chart_data["cause"].map(CAUSE_LABELS)
    return px.bar(
        chart_data,
        x="season",
        y="part",
        color="cause",
        barmode="stack",
        labels={"season": "Saison", "part": "Part des retards (%)", "cause": "Cause"},
        title="Causes de retard selon la saison",
    )
