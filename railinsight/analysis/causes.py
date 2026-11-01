"""Analyses dédiées à l'identification et l'étude des causes de pannes ou de retards.

Reprend les conventions validées en Phase 1 (répartition des causes par liaison) et
portées depuis le notebook ``notebook/phase3_phase4_exploration.ipynb`` pour la Phase 3
(lecture par saison). Les trois familles de causes suivent le cadrage du projet
(``documentation/cadrage_question_directrice.md``, section 2) :

- SNCF Réseau : infrastructure, gestion du trafic.
- SNCF Voyageurs : matériel roulant, gestion en gare, prise en charge des voyageurs.
- Externe : causes externes (inclut les grèves, non isolables).
"""

import pandas as pd

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


def contributions_par_saison(
    data: pd.DataFrame, familles: dict[str, list[str]] = FAMILLES_CAUSES
) -> pd.DataFrame:
    """Contribution de chaque famille de causes au taux de retard, par saison.

    Ne garde que les observations ``cause_fiable``. La contribution est pondérée
    par le nombre de trains prévus (jamais une moyenne de taux, cf. cadrage).

    Args:
        data: Jeu de régularité prétraité, avec les colonnes ``saison``,
            ``nb_train_prevu``, ``cause_fiable`` et ``nb_retard_<famille>``
            (voir `ajouter_nb_retard_par_famille`).
        familles: Groupes de causes à agréger.

    Returns:
        Un DataFrame indexé par saison, avec une colonne ``contrib_<famille>``
        par famille.

    Raises:
        ValueError: Si une colonne requise est absente de `data`.
    """
    requis = {"saison", "nb_train_prevu", "cause_fiable"}
    if not requis.issubset(data.columns):
        raise ValueError(f"Colonnes manquantes : {requis.difference(data.columns)}")

    data_ok = data[data["cause_fiable"]]
    colonnes_nb_retard = [f"nb_retard_{famille}" for famille in familles]

    agg = data_ok.groupby("saison", observed=True).agg(
        nb_train_prevu=("nb_train_prevu", "sum"),
        **{colonne: (colonne, "sum") for colonne in colonnes_nb_retard},
    )
    for famille in familles:
        agg[f"contrib_{famille}"] = agg[f"nb_retard_{famille}"] / agg["nb_train_prevu"]

    return agg
