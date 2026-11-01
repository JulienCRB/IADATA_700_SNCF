"""Calculs et indicateurs liés à la fiabilité ferroviaire.

Score de fiabilité V1 (Phase 4), porté depuis le notebook
``notebook/phase3_phase4_exploration.ipynb``. Conforme au cadrage du projet
(``documentation/cadrage_question_directrice.md``, section 3) :

- 3 composantes à poids égaux : part de trains en retard, taux d'annulation,
  retard moyen de tous les trains.
- Normalisation par rang (percentile), calculée à l'intérieur de la classe de
  durée de la liaison, pour comparer des liaisons de longueur comparable.
- Calculé sur les 12 derniers mois disponibles.
- La part d'origine interne (Réseau + Voyageurs) est calculée à part, affichée
  à côté du score sans influencer son calcul.

Limite connue (à documenter dans la datasheet) : le seuil de retard par classe
de durée (5/10/15 minutes selon le cadrage) n'est pas disponible dans le
dataset SNCF. La composante ``part_retard`` utilise donc
``nb_train_retard_arrivee`` (seuil standard SNCF) comme proxy pour toutes les
classes de durée.
"""

import pandas as pd

from .causes import FAMILLES_CAUSES

#: Colonnes des 3 composantes brutes du score de fiabilité.
COMPOSANTES_FIABILITE: list[str] = [
    "part_retard",
    "taux_annulation",
    "retard_moyen_tous_trains",
]


def agreger_derniers_mois(data: pd.DataFrame, n_mois: int = 12) -> pd.DataFrame:
    """Restreint le jeu de données aux `n_mois` mois les plus récents.

    Args:
        data: Jeu de régularité, avec une colonne ``date`` au format ``AAAA-MM``.
        n_mois: Nombre de mois à conserver.

    Returns:
        Les lignes dont la date fait partie des `n_mois` derniers mois disponibles.
    """
    derniers = sorted(data["date"].unique())[-n_mois:]
    return data[data["date"].isin(derniers)].copy()


def composantes_fiabilite(
    data: pd.DataFrame, liaison_cols: list[str] = ["gare_depart", "gare_arrivee"]
) -> pd.DataFrame:
    """Calcule les 3 composantes brutes du score de fiabilité, par liaison.

    Composantes (cadrage, section 3) : part de trains en retard (sur les trains
    circulés, c'est-à-dire prévus moins annulés), taux d'annulation, et retard
    moyen de tous les trains à l'arrivée (pondéré par le nombre de trains
    prévus chaque mois).

    Args:
        data: Jeu de régularité (idéalement restreint aux 12 derniers mois via
            `agreger_derniers_mois`), avec les colonnes ``nb_train_prevu``,
            ``nb_annulation``, ``nb_train_retard_arrivee``,
            ``retard_moyen_tous_trains_arrivee`` et ``classe_duree``.
        liaison_cols: Colonnes identifiant une liaison.

    Returns:
        Un DataFrame indexé par liaison avec les colonnes de `COMPOSANTES_FIABILITE` et
        ``classe_duree``.
    """
    data = data.copy()
    data["nb_train_circule"] = data["nb_train_prevu"] - data["nb_annulation"]
    data["retard_pondere"] = (
        data["retard_moyen_tous_trains_arrivee"] * data["nb_train_prevu"]
    )

    agg = data.groupby(liaison_cols).agg(
        nb_train_prevu=("nb_train_prevu", "sum"),
        nb_train_circule=("nb_train_circule", "sum"),
        nb_annulation=("nb_annulation", "sum"),
        nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
        retard_pondere=("retard_pondere", "sum"),
        classe_duree=("classe_duree", "first"),
    )

    agg["part_retard"] = agg["nb_train_retard_arrivee"] / agg["nb_train_circule"]
    agg["taux_annulation"] = agg["nb_annulation"] / agg["nb_train_prevu"]
    agg["retard_moyen_tous_trains"] = agg["retard_pondere"] / agg["nb_train_prevu"]

    return agg[["classe_duree", *COMPOSANTES_FIABILITE]]


def score_fiabilite(
    data: pd.DataFrame, composantes: list[str] = COMPOSANTES_FIABILITE
) -> pd.DataFrame:
    """Ajoute le rang par classe de durée et le score de fiabilité (poids égaux).

    Le score est la moyenne des rangs en pourcentile des composantes, calculés
    à l'intérieur de la classe de durée de chaque liaison. Un score proche de
    0 indique une liaison fiable par rapport aux autres liaisons de durée
    comparable ; proche de 1, une liaison peu fiable.

    Args:
        data: Résultat de `composantes_fiabilite` (colonnes ``classe_duree`` +
            `composantes`).
        composantes: Colonnes à utiliser pour le score.

    Returns:
        Copie de `data` avec une colonne ``rang_<composante>`` par composante et
        ``score_fiabilite``.

    Raises:
        ValueError: Si la colonne ``classe_duree`` est absente de `data`.
    """
    if "classe_duree" not in data.columns:
        raise ValueError(
            "La colonne 'classe_duree' est requise pour normaliser par classe."
        )

    data = data.copy()
    rangs = data.groupby("classe_duree", observed=True)[composantes].rank(pct=True)
    rangs.columns = [f"rang_{c}" for c in composantes]
    data = data.join(rangs)
    data["score_fiabilite"] = data[rangs.columns].mean(axis=1)
    return data


def part_origine_interne(
    data: pd.DataFrame,
    familles: dict[str, list[str]] = FAMILLES_CAUSES,
    liaison_cols: list[str] = ["gare_depart", "gare_arrivee"],
) -> pd.Series:
    """Part des retards d'origine interne (Réseau + Voyageurs), par liaison.

    Affichée à côté du score de fiabilité, sans entrer dans son calcul
    (cadrage, section 3). Ne garde que les observations ``cause_fiable``.

    Args:
        data: Jeu de régularité avec ``cause_fiable`` et ``nb_retard_<famille>``
            (voir ``railinsight.analysis.causes.marquer_cause_fiable`` et
            ``railinsight.analysis.causes.ajouter_nb_retard_par_famille``).
        familles: Groupes de causes ; les clés "reseau" et "voyageurs" sont
            utilisées comme origine interne, les autres clés comme origine
            externe.
        liaison_cols: Colonnes identifiant une liaison.

    Returns:
        Série indexée par liaison, part (0-1) des retards d'origine interne.
    """
    data_ok = data[data["cause_fiable"]]
    colonnes_nb_retard = {f"nb_retard_{famille}": famille for famille in familles}
    agg = data_ok.groupby(liaison_cols)[list(colonnes_nb_retard)].sum()

    internes = [
        colonne
        for colonne, famille in colonnes_nb_retard.items()
        if famille in ("reseau", "voyageurs")
    ]
    total = agg.sum(axis=1)
    return agg[internes].sum(axis=1) / total
