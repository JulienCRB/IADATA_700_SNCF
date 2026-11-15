"""Analyses dédiées à l'identification et l'étude des causes de pannes ou de retards.

Reprend les conventions validées en Phase 1 (répartition des causes par liaison) et
en Phase 3 (lecture par saison). Les contributions sont toujours calculées par
liaison, sur les trains circulés : jamais de total réseau (cadrage, section 2).
Les trois familles de causes suivent le cadrage du projet
(``documentation/cadrage_question_directrice.md``, section 2) :

- SNCF Réseau : infrastructure, gestion du trafic.
- SNCF Voyageurs : matériel roulant, gestion en gare, prise en charge des voyageurs.
- Externe : causes externes (inclut les grèves, non isolables).
"""

import pandas as pd

from railinsight.data.preprocessing import LIAISON, ORDRE_SAISONS

#: Colonnes `prct_cause_*` du dataset de régularité, groupées par famille.
FAMILLES_CAUSES: dict[str, list[str]] = {
    "reseau": ["prct_cause_infra", "prct_cause_gestion_trafic"],
    "voyageurs": [
        "prct_cause_materiel_roulant",
        "prct_cause_gestion_gare",
        "prct_cause_prise_en_charge_voyageurs",
    ],
    "externe": ["prct_cause_externe"],
}


def marquer_cause_fiable(
    data: pd.DataFrame,
    familles: dict[str, list[str]] = FAMILLES_CAUSES,
    tolerance: float = 5.0,
) -> pd.Series:
    """Repère les observations dont la répartition des causes est exploitable.

    Une observation est jugée non fiable si elle a des trains en retard à l'arrivée
    mais que la somme des pourcentages de causes s'écarte de plus de `tolerance`
    points de 100 (Phase 1 : 83 observations sur 12 907, concentrées sur les liaisons
    internationales en 2018).

    Args:
        data: Jeu de régularité, avec les colonnes ``prct_cause_*`` et
            ``nb_train_retard_arrivee``.
        familles: Groupes de colonnes de causes à sommer.
        tolerance: Écart maximal toléré à 100, en points.

    Returns:
        Série booléenne, `True` si l'observation est exploitable.
    """
    toutes_causes = [colonne for colonnes in familles.values() for colonne in colonnes]
    somme_causes = data[toutes_causes].sum(axis=1)
    a_des_retards = data["nb_train_retard_arrivee"] > 0
    return ~(a_des_retards & ((somme_causes - 100).abs() > tolerance))


def ajouter_nb_retard_par_famille(
    data: pd.DataFrame, familles: dict[str, list[str]] = FAMILLES_CAUSES
) -> pd.DataFrame:
    """Ajoute une colonne ``nb_retard_<famille>`` par groupe de causes.

    Args:
        data: Jeu de régularité, avec les colonnes ``prct_cause_*`` et
            ``nb_train_retard_arrivee``.
        familles: Groupes de colonnes de causes à sommer.

    Returns:
        Copie de `data` avec une colonne supplémentaire par famille.
    """
    data = data.copy()
    for famille, colonnes in familles.items():
        data[f"nb_retard_{famille}"] = (
            data["nb_train_retard_arrivee"] * data[colonnes].sum(axis=1) / 100
        )
    return data


def contributions_par_liaison(
    data: pd.DataFrame,
    par: str | None = None,
    familles: dict[str, list[str]] = FAMILLES_CAUSES,
) -> pd.DataFrame:
    """Contribution de chaque famille de causes au taux de retard, par liaison.

    La contribution d'une famille est la part des trains circulés qui sont en
    retard à cause d'elle (trains en retard de la famille ÷ trains circulés).
    Les trois contributions s'additionnent au taux de retard de la liaison.
    Ne garde que les observations ``cause_fiable``.

    Args:
        data: Jeu de régularité préparé (``preparer_regularite``), avec
            ``cause_fiable`` et les colonnes ``nb_retard_<famille>``.
        par: Colonne de découpage supplémentaire (ex. ``"saison"``), ou `None`
            pour une seule valeur par liaison.
        familles: Groupes de causes à agréger.

    Returns:
        Un DataFrame indexé par liaison (et par `par`), avec une colonne
        ``contrib_<famille>`` par famille.
    """
    cles = LIAISON + ([par] if par else [])
    colonnes_nb_retard = [f"nb_retard_{famille}" for famille in familles]

    data_ok = data[data["cause_fiable"]]
    agg = data_ok.groupby(cles, observed=True)[
        ["nb_train_circule", *colonnes_nb_retard]
    ].sum()

    for famille in familles:
        agg[f"contrib_{famille}"] = (
            agg[f"nb_retard_{famille}"] / agg["nb_train_circule"]
        )
    return agg[[f"contrib_{famille}" for famille in familles]]


def cause_dominante(contributions: pd.DataFrame) -> pd.Series:
    """Famille de causes qui contribue le plus au retard de chaque liaison (Phase 1).

    Args:
        contributions: Résultat de `contributions_par_liaison`.

    Returns:
        Série indexée comme `contributions`, avec le nom de la famille
        dominante (``"reseau"``, ``"voyageurs"`` ou ``"externe"``).
    """
    return contributions.idxmax(axis=1).str.removeprefix("contrib_")


def contributions_par_saison(
    data: pd.DataFrame, familles: dict[str, list[str]] = FAMILLES_CAUSES
) -> pd.DataFrame:
    """Contribution de chaque famille par saison, pour la liaison médiane (Phase 3).

    Le cadrage interdit tout total réseau (un même train compte dans plusieurs
    liaisons) : on calcule les contributions de chaque liaison pour chaque
    saison, puis on prend la médiane des liaisons. Les liaisons internationales
    sont exclues (données peu fiables, décision de la Phase 2).

    Args:
        data: Jeu de régularité préparé, avec ``saison``, ``internationale``,
            ``cause_fiable`` et les colonnes ``nb_retard_<famille>``.
        familles: Groupes de causes à agréger.

    Returns:
        Un DataFrame indexé par saison (hiver → automne), avec une colonne
        ``contrib_<famille>`` par famille.

    Raises:
        ValueError: Si une colonne requise est absente de `data`.
    """
    requis = {"saison", "internationale", "nb_train_circule", "cause_fiable"}
    if not requis.issubset(data.columns):
        raise ValueError(f"Colonnes manquantes : {requis.difference(data.columns)}")

    nationales = data[~data["internationale"]]
    par_liaison = contributions_par_liaison(nationales, par="saison", familles=familles)
    medianes = par_liaison.groupby("saison").median()
    return medianes.reindex([s for s in ORDRE_SAISONS if s in medianes.index])
