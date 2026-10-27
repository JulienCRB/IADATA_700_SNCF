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
        raise DataValidationError(
            "Le résultat ne contient pas les colonnes de fiabilité."
        )
    if top_n < 1:
        raise DataValidationError("top_n doit être supérieur ou égal à 1.")
    chart_data = data.nlargest(top_n, "unreliable_rate").copy()
    chart_data["liaison"] = (
        chart_data[ROUTE_COLUMNS[0]].astype(str)
        + " → "
        + chart_data[ROUTE_COLUMNS[1]].astype(str)
    )
    return px.bar(
        chart_data,
        x="unreliable_rate",
        y="liaison",
        orientation="h",
        labels={
            "unreliable_rate": "Annulations et retards > 15 min",
            "liaison": "Liaison",
        },
        title="Liaisons TGV les moins fiables",
    ).update_layout(yaxis={"categoryorder": "total ascending"})


def cause_stacked_bar(
    data: pd.DataFrame, columns: Sequence[str] = CAUSE_COLUMNS
) -> go.Figure:
    """Construit un graphique empilé de la saisonnalité des causes."""
    selected = list(columns)
    if not {"season", *selected}.issubset(data.columns):
        raise DataValidationError(
            "Le résultat ne contient pas les colonnes saison/causes."
        )
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


def network_map(routes: pd.DataFrame, stations: pd.DataFrame) -> go.Figure:
    """Trace les liaisons entre gares sur une carte.

    Args:
        routes: Liaisons avec les colonnes de ``ROUTE_COLUMNS``.
        stations: Gares avec les colonnes ``gare``, ``latitude``, ``longitude``.

    Returns:
        Une figure où chaque liaison (sens confondus) est un segment.
    """
    if not set(ROUTE_COLUMNS).issubset(routes.columns):
        raise DataValidationError("Les liaisons doivent avoir départ et arrivée.")
    if not {"gare", "latitude", "longitude"}.issubset(stations.columns):
        raise DataValidationError("Les gares doivent avoir des coordonnées.")

    coords = stations.set_index("gare")[["latitude", "longitude"]]
    pairs = (
        routes[list(ROUTE_COLUMNS)]
        .apply(lambda row: tuple(sorted(row)), axis=1)
        .drop_duplicates()
    )
    pairs = [pair for pair in pairs if set(pair).issubset(coords.index)]

    lats: list[float | None] = []
    lons: list[float | None] = []
    for start, end in pairs:
        lats += [coords.at[start, "latitude"], coords.at[end, "latitude"], None]
        lons += [coords.at[start, "longitude"], coords.at[end, "longitude"], None]

    degree = pd.Series([gare for pair in pairs for gare in pair]).value_counts()
    used = sorted(degree.index)
    figure = go.Figure(
        [
            go.Scattermap(
                lat=lats,
                lon=lons,
                mode="lines",
                line={"width": 1, "color": "#2c3e50"},
                opacity=0.35,
                hoverinfo="skip",
                name="Liaisons",
            ),
            go.Scattermap(
                lat=coords.loc[used, "latitude"],
                lon=coords.loc[used, "longitude"],
                text=[f"{gare} : {degree[gare]} liaisons" for gare in used],
                mode="markers",
                marker={
                    "size": [5 + 2 * degree[gare] for gare in used],
                    "color": "#34495e",
                    "opacity": 0.8,
                },
                hovertemplate="%{text}<extra></extra>",
                name="Gares",
            ),
        ]
    )
    figure.update_layout(
        map={
            "style": "carto-positron",
            "center": {"lat": 46.6, "lon": 4.0},
            "zoom": 4.6,
        },
        title=f"{len(pairs)} liaisons TGV entre {len(used)} gares",
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        showlegend=False,
        height=650,
    )
    return figure


def station_ranking(routes: pd.DataFrame, top_n: int | None = None) -> go.Figure:
    """Classe les gares selon leur nombre de liaisons (sens confondus).

    Sans ``top_n``, toutes les gares sont affichées.
    """
    if not set(ROUTE_COLUMNS).issubset(routes.columns):
        raise DataValidationError("Les liaisons doivent avoir départ et arrivée.")
    if top_n is not None and top_n < 1:
        raise DataValidationError("top_n doit être supérieur ou égal à 1.")

    pairs = (
        routes[list(ROUTE_COLUMNS)]
        .apply(lambda row: tuple(sorted(row)), axis=1)
        .drop_duplicates()
    )
    degree = pd.Series([gare for pair in pairs for gare in pair]).value_counts()
    ranking = degree.head(top_n).rename_axis("gare").reset_index(name="liaisons")
    return px.bar(
        ranking,
        x="liaisons",
        y="gare",
        orientation="h",
        labels={"liaisons": "Nombre de liaisons", "gare": "Gare"},
        title=f"Nombre de liaisons pour {len(ranking)} gares",
    ).update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(400, 22 * len(ranking)),
    )
