"""Figures Plotly pour les résultats des analyses RailInsight."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROUTE_COLUMNS = ("gare_depart", "gare_arrivee")

#: Libellés affichés pour les trois familles de causes.
FAMILLE_LABELS = {
    "contrib_reseau": "Réseau",
    "contrib_voyageurs": "Voyageurs",
    "contrib_externe": "Externe",
}


def reliability_bar(scores: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Classe les liaisons les moins fiables selon leur score de fiabilité.

    Args:
        scores: Résultat de ``score_fiabilite``, indexé par liaison. Les
            liaisons sans score (internationales) sont ignorées.
        top_n: Nombre de liaisons à afficher.

    Returns:
        Un graphique en barres horizontales, la moins fiable en haut.
    """
    if "score_fiabilite" not in scores.columns:
        raise ValueError("Le résultat ne contient pas de score de fiabilité.")
    if top_n < 1:
        raise ValueError("top_n doit être supérieur ou égal à 1.")

    chart_data = (
        scores.dropna(subset=["score_fiabilite"])
        .nlargest(top_n, "score_fiabilite")
        .reset_index()
    )
    chart_data["liaison"] = (
        chart_data[ROUTE_COLUMNS[0]] + " → " + chart_data[ROUTE_COLUMNS[1]]
    )
    return px.bar(
        chart_data,
        x="score_fiabilite",
        y="liaison",
        orientation="h",
        range_x=[0, 1],
        labels={
            "score_fiabilite": "Score (0 = plus fiable, 1 = moins fiable de sa classe)",
            "liaison": "Liaison",
        },
        title="Liaisons TGV les moins fiables de leur classe de durée",
    ).update_layout(yaxis={"categoryorder": "total ascending"})


def contributions_saison_bar(contributions: pd.DataFrame) -> go.Figure:
    """Compare la contribution des trois familles de causes selon la saison.

    Les barres sont côte à côte et non empilées : ce sont des médianes de
    liaisons, qui ne s'additionnent pas exactement.

    Args:
        contributions: Résultat de ``contributions_par_saison`` (indexé par
            saison, colonnes ``contrib_<famille>``).

    Returns:
        Un graphique en barres groupées, en points de taux de retard.
    """
    if not set(FAMILLE_LABELS).issubset(contributions.columns):
        raise ValueError("Le résultat ne contient pas les contributions par famille.")

    chart_data = (
        (contributions[list(FAMILLE_LABELS)] * 100)
        .rename(columns=FAMILLE_LABELS)
        .rename_axis("saison")
        .reset_index()
        .melt(id_vars="saison", var_name="famille", value_name="points")
    )
    return px.bar(
        chart_data,
        x="saison",
        y="points",
        color="famille",
        barmode="group",
        labels={
            "saison": "Saison",
            "points": "Contribution au taux de retard (points)",
            "famille": "Famille de causes",
        },
        title="Causes de retard selon la saison (liaison médiane)",
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
        raise ValueError("Les liaisons doivent avoir départ et arrivée.")
    if not {"gare", "latitude", "longitude"}.issubset(stations.columns):
        raise ValueError("Les gares doivent avoir des coordonnées.")

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
        raise ValueError("Les liaisons doivent avoir départ et arrivée.")
    if top_n is not None and top_n < 1:
        raise ValueError("top_n doit être supérieur ou égal à 1.")

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
