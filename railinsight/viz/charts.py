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
#: Nom court d'une famille (``cause_dominante``, ``cause_evolution``) → libellé.
FAMILLE_NOMS = {"reseau": "Réseau", "voyageurs": "Voyageurs", "externe": "Externe"}
#: Une couleur par famille, la même sur tous les graphiques de l'application.
#: Palette inspirée de l'identité visuelle SNCF (valeurs non officielles : à
#: remplacer ici par les codes de la charte si l'équipe les obtient). Toutes les
#: couleurs des graphiques en découlent ; le thème Streamlit
#: (``.streamlit/config.toml``) reprend les mêmes.
PALETTE = {
    "nuit": "#1d2b4f",  # bleu nuit : texte, réseau
    "carmillon": "#e05206",  # orange-rouge SNCF : trains et gares, accent
    "cassis": "#a1006b",  # prune : s'aggrave
    "gris": "#9aa0ad",  # gris rail : aléas extérieurs, neutre
    "gris_clair": "#e3e6ec",  # fonds, liaisons non concernées
    "vert": "#3e8e5e",  # résiste mieux, peu de retards
}

FAMILLE_COULEURS = {
    "Réseau": PALETTE["nuit"],
    "Voyageurs": PALETTE["carmillon"],
    "Externe": PALETTE["gris"],
}

#: Libellés et unités des 3 composantes du score de fiabilité.
COMPOSANTE_LABELS = {
    "part_retard": "Trains en retard (%)",
    "taux_annulation": "Trains annulés (%)",
    "retard_moyen_tous_trains": "Retard moyen (min)",
}


def _libelle_liaison(data: pd.DataFrame) -> pd.Series:
    """Libellé lisible d'une liaison : « départ → arrivée »."""
    return data[ROUTE_COLUMNS[0]] + " → " + data[ROUTE_COLUMNS[1]]


def _couleurs(libelles: dict[str, str]) -> dict[str, str]:
    """Couleur de chaque famille, quel que soit le nom affiché."""
    return {libelles[f]: FAMILLE_COULEURS[FAMILLE_NOMS[f]] for f in FAMILLE_NOMS}


def contributions_saison_bar(
    contributions: pd.DataFrame, libelles: dict[str, str] = FAMILLE_NOMS
) -> go.Figure:
    """Compare la contribution des trois familles de causes selon la saison.

    Les barres sont côte à côte et non empilées : ce sont des médianes de
    liaisons, qui ne s'additionnent pas exactement.

    Args:
        contributions: Résultat de ``contributions_par_saison`` (indexé par
            saison, colonnes ``contrib_<famille>``).
        libelles: Nom affiché de chaque famille.

    Returns:
        Un graphique en barres groupées, en trains en retard sur 100.
    """
    if not set(FAMILLE_LABELS).issubset(contributions.columns):
        raise ValueError("Le résultat ne contient pas les contributions par famille.")

    noms = {f"contrib_{famille}": nom for famille, nom in libelles.items()}
    chart_data = (
        (contributions[list(FAMILLE_LABELS)] * 100)
        .rename(columns=noms)
        .rename_axis("saison")
        .reset_index()
        .melt(id_vars="saison", var_name="famille", value_name="trains")
    )
    chart_data["saison"] = chart_data["saison"].str.capitalize()
    return px.bar(
        chart_data,
        x="saison",
        y="trains",
        color="famille",
        color_discrete_map=_couleurs(libelles),
        barmode="group",
        labels={
            "saison": "",
            "trains": "Trains en retard sur 100",
            "famille": "Cause",
        },
    ).update_layout(
        legend={"orientation": "h", "y": 1.02, "x": 0, "yanchor": "bottom"},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )


def retards_sur_100_bar(
    poids: pd.Series, libelles: dict[str, str] = FAMILLE_NOMS
) -> go.Figure:
    """Les trains en retard d'une liaison typique, répartis par cause, sur une ligne.

    Args:
        poids: Résultat de ``Regularite.contribution_mediane`` : contribution de
            chaque famille (``reseau``, ``voyageurs``, ``externe``), en taux.
        libelles: Nom affiché de chaque famille.

    Returns:
        Une barre horizontale unique, un segment par famille, nombres arrondis.
    """
    if not set(FAMILLE_NOMS).issubset(poids.index):
        raise ValueError("Il faut la contribution des trois familles de causes.")

    chart_data = pd.DataFrame(
        {
            "famille": [libelles[f] for f in FAMILLE_NOMS],
            "trains": [round(poids[f] * 100) for f in FAMILLE_NOMS],
            "couleur": [FAMILLE_COULEURS[FAMILLE_NOMS[f]] for f in FAMILLE_NOMS],
        }
    )
    chart_data["texte"] = (
        chart_data["trains"].astype(str) + " · " + chart_data["famille"].str.lower()
    )
    figure = px.bar(
        chart_data,
        x="trains",
        y=[""] * len(chart_data),
        color="famille",
        color_discrete_sequence=chart_data["couleur"].tolist(),
        orientation="h",
        text="texte",
        hover_name="famille",
        hover_data={"trains": True, "texte": False},
    )
    figure.update_traces(textposition="inside", insidetextanchor="middle")
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return figure.update_layout(
        height=110,
        showlegend=False,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        uniformtext={"minsize": 12, "mode": "show"},
    )


#: Couleurs des niveaux de retard, du plus faible (vert) au plus fort (rouge).
NIVEAU_COULEURS = ["#c9e4d2", "#f9d8b8", PALETTE["carmillon"], PALETTE["cassis"]]


def niveaux_par_famille_bar(
    repartition: pd.DataFrame, libelles: dict[str, str] = FAMILLE_NOMS
) -> go.Figure:
    """Part des liaisons à chaque niveau de retard, pour chaque famille.

    Args:
        repartition: Résultat de ``repartition_par_niveau`` (indexé par famille,
            une colonne par niveau, parts de 0 à 1).
        libelles: Nom affiché de chaque famille.

    Returns:
        Une barre à 100 % par famille, du vert (peu de retards) au rouge.
    """
    if not set(FAMILLE_NOMS).issubset(repartition.index):
        raise ValueError("Il faut la répartition des trois familles de causes.")

    niveaux = list(repartition.columns)
    chart_data = (
        (repartition.loc[list(FAMILLE_NOMS)] * 100)
        .rename(index=libelles)
        .rename_axis("famille")
        .reset_index()
        .melt(id_vars="famille", var_name="niveau", value_name="part")
    )
    chart_data["texte"] = chart_data["part"].map(
        lambda p: f"{p:.0f} %" if p >= 5 else ""
    )
    figure = px.bar(
        chart_data,
        x="part",
        y="famille",
        color="niveau",
        color_discrete_sequence=NIVEAU_COULEURS,
        category_orders={"niveau": niveaux, "famille": list(libelles.values())},
        orientation="h",
        text="texte",
        labels={
            "part": "Part des liaisons (%)",
            "famille": "",
            "niveau": "Trains en retard sur 100 :",
        },
    )
    figure.update_traces(textposition="inside", insidetextanchor="middle")
    figure.update_xaxes(range=[0, 100], ticksuffix=" %")
    return figure.update_layout(
        height=280,
        legend={"orientation": "h", "y": 1.15, "x": 0},
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
    )


#: Couleur de chaque tendance de 2026 (Phase 2).
TENDANCE_COULEURS = {
    "s'aggrave": PALETTE["cassis"],
    "suit le réseau": PALETTE["gris"],
    "résiste mieux": PALETTE["vert"],
}


def evolution_avant_apres(bilan: pd.DataFrame) -> go.Figure:
    """Taux de retard avant (2023-2025) et en 2026, pour chaque liaison en difficulté.

    Chaque liaison est une ligne qui relie ses deux taux : plus la ligne va vers
    la droite, plus la liaison s'est dégradée. La couleur dit si elle s'aggrave
    plus que le reste du réseau, suit la tendance ou résiste mieux.

    Args:
        bilan: Résultat de ``Regularite.liaisons_en_difficulte`` (colonnes
            ``en_difficulte``, ``taux_reference``, ``taux_suivi``, ``tendance``).

    Returns:
        Un graphique « avant / après », une ligne par liaison en difficulté.
    """
    requis = {"en_difficulte", "taux_reference", "taux_suivi", "tendance"}
    if not requis.issubset(bilan.columns):
        raise ValueError("Le résultat ne contient pas l'évolution des liaisons.")

    selection = bilan[bilan["en_difficulte"]].reset_index()
    selection["liaison"] = _libelle_liaison(selection)
    selection = selection.sort_values("taux_suivi")
    selection[["avant", "apres"]] = (
        selection[["taux_reference", "taux_suivi"]] * 100
    ).to_numpy()

    figure = go.Figure()
    # Une ligne par liaison, de « avant » à « 2026 », colorée selon la tendance
    for tendance, couleur in TENDANCE_COULEURS.items():
        groupe = selection[selection["tendance"] == tendance]
        x: list[float | None] = []
        y: list[str | None] = []
        for _, ligne in groupe.iterrows():
            x += [ligne["avant"], ligne["apres"], None]
            y += [ligne["liaison"], ligne["liaison"], None]
        figure.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"color": couleur, "width": 4},
                name=tendance,
                hoverinfo="skip",
            )
        )
    # Les deux extrémités : cercle vide = avant, point plein = 2026
    figure.add_trace(
        go.Scatter(
            x=selection["avant"],
            y=selection["liaison"],
            mode="markers",
            marker={"symbol": "circle-open", "size": 10, "color": "#555"},
            name="2023-2025",
            hovertemplate="%{y}<br>2023-2025 : %{x:.0f} sur 100<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=selection["apres"],
            y=selection["liaison"],
            mode="markers",
            marker={
                "size": 11,
                "color": selection["tendance"].map(TENDANCE_COULEURS).tolist(),
            },
            name="2026",
            hovertemplate="%{y}<br>2026 : %{x:.0f} sur 100<extra></extra>",
        )
    )
    return figure.update_layout(
        xaxis_title="Trains en retard sur 100",
        yaxis={"categoryorder": "array", "categoryarray": selection["liaison"]},
        height=max(400, 26 * len(selection)),
        legend={"orientation": "h", "y": 1.02, "x": 0, "yanchor": "bottom"},
        margin={"l": 0, "r": 0, "t": 60, "b": 0},
    )


def carte_difficulte(bilan: pd.DataFrame, stations: pd.DataFrame) -> go.Figure:
    """Carte des liaisons en difficulté, colorées selon leur tendance en 2026.

    Toutes les liaisons du bilan sont tracées en fond, en gris clair ; les
    liaisons en difficulté ressortent en couleur (rouge : s'aggrave, gris : suit
    le réseau, vert : résiste mieux).

    Args:
        bilan: Résultat de ``Regularite.liaisons_en_difficulte`` (indexé par
            liaison, colonnes ``en_difficulte`` et ``tendance``).
        stations: Gares avec les colonnes ``gare``, ``latitude``, ``longitude``.

    Returns:
        Une carte, une ligne par liaison.
    """
    if not {"en_difficulte", "tendance"}.issubset(bilan.columns):
        raise ValueError("Le résultat ne contient pas les liaisons en difficulté.")
    if not {"gare", "latitude", "longitude"}.issubset(stations.columns):
        raise ValueError("Les gares doivent avoir des coordonnées.")

    coords = stations.set_index("gare")[["latitude", "longitude"]]

    def segments(liaisons: pd.Index) -> tuple[list, list, list]:
        """Coordonnées des liaisons, séparées par None pour couper les lignes."""
        lats, lons, noms = [], [], []
        for depart, arrivee in liaisons:
            if depart in coords.index and arrivee in coords.index:
                nom = f"{depart} → {arrivee}"
                lats += [coords.at[depart, "latitude"], coords.at[arrivee, "latitude"]]
                lons += [
                    coords.at[depart, "longitude"],
                    coords.at[arrivee, "longitude"],
                ]
                lats.append(None)
                lons.append(None)
                noms += [nom, nom, None]
        return lats, lons, noms

    lats, lons, _ = segments(bilan.index)
    traces = [
        go.Scattermap(
            lat=lats,
            lon=lons,
            mode="lines",
            line={"width": 1, "color": PALETTE["gris_clair"]},
            hoverinfo="skip",
            name="Autres liaisons",
        )
    ]
    selection = bilan[bilan["en_difficulte"]]
    for tendance, couleur in TENDANCE_COULEURS.items():
        groupe = selection[selection["tendance"] == tendance]
        lats, lons, noms = segments(groupe.index)
        traces.append(
            go.Scattermap(
                lat=lats,
                lon=lons,
                mode="lines",
                line={"width": 4, "color": couleur},
                text=noms,
                hovertemplate="%{text}<extra></extra>",
                name=tendance,
            )
        )
    gares = sorted({gare for liaison in selection.index for gare in liaison})
    gares = [gare for gare in gares if gare in coords.index]
    traces.append(
        go.Scattermap(
            lat=coords.loc[gares, "latitude"],
            lon=coords.loc[gares, "longitude"],
            mode="markers",
            marker={"size": 8, "color": PALETTE["nuit"]},
            text=gares,
            hovertemplate="%{text}<extra></extra>",
            name="Gares concernées",
        )
    )
    return go.Figure(traces).update_layout(
        map={
            "style": "carto-positron",
            "center": {"lat": 46.6, "lon": 2.8},
            "zoom": 4.4,
        },
        height=520,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        legend={
            "orientation": "h",
            "y": 0.01,
            "x": 0.01,
            "bgcolor": "rgba(255,255,255,0.8)",
        },
    )


def gares_concernees_bar(gares: pd.Series, top_n: int = 8) -> go.Figure:
    """Les gares qui reviennent le plus souvent parmi les liaisons en difficulté.

    Args:
        gares: Résultat de ``gares_concernees`` (nombre de liaisons par gare).
        top_n: Nombre de gares à afficher.

    Returns:
        Un graphique en barres horizontales, la plus concernée en haut.
    """
    if top_n < 1:
        raise ValueError("top_n doit être supérieur ou égal à 1.")

    chart_data = gares.head(top_n).rename_axis("gare").reset_index(name="liaisons")
    return px.bar(
        chart_data,
        x="liaisons",
        y="gare",
        orientation="h",
        text="liaisons",
        color_discrete_sequence=[PALETTE["nuit"]],
        labels={"liaisons": "Liaisons en difficulté", "gare": ""},
    ).update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(260, 34 * len(chart_data)),
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
    )


def historique_composantes_line(historique: pd.DataFrame) -> go.Figure:
    """Historique des 3 composantes du score d'une liaison, année par année.

    Args:
        historique: Lignes de ``Regularite.historique_composantes`` pour une
            liaison, indexées par année.

    Returns:
        Trois petites courbes côte à côte, une par composante, chacune avec
        son titre et son échelle.
    """
    if not set(COMPOSANTE_LABELS).issubset(historique.columns):
        raise ValueError("L'historique ne contient pas les 3 composantes.")

    chart_data = historique[list(COMPOSANTE_LABELS)].copy()
    chart_data[["part_retard", "taux_annulation"]] *= 100
    chart_data = (
        chart_data.rename(columns=COMPOSANTE_LABELS)
        .rename_axis("annee")
        .reset_index()
        .melt(id_vars="annee", var_name="composante", value_name="valeur")
    )
    figure = px.line(
        chart_data,
        x="annee",
        y="valeur",
        facet_col="composante",
        facet_col_spacing=0.08,
        markers=True,
        labels={"annee": "", "valeur": ""},
    )
    figure.update_yaxes(matches=None, showticklabels=True)
    figure.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return figure.update_layout(height=380)
