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
- Les liaisons internationales n'ont pas de score (données peu fiables,
  décision de la Phase 2) ; leurs composantes restent calculées.

Le seuil de retard par classe de durée (5/10/15 minutes selon le cadrage) est
déjà celui de ``nb_train_retard_arrivee`` : la SNCF publie une régularité
« composite » qui applique ces seuils selon la durée du trajet.
"""

import pandas as pd

from railinsight.data.preprocessing import LIAISON
from railinsight.exceptions import (
    ColonnesManquantesError,
    DatasetVideError,
    ParametreInvalideError,
)
from railinsight.logger import get_logger

from .causes import FAMILLES_CAUSES
from .difficulte import VOLUME_MIN

log = get_logger(__name__)

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

    Raises:
        ParametreInvalideError: Si `n_mois` n'est pas strictement positif.
        ColonnesManquantesError: Si la colonne ``date`` est absente de `data`.
        DatasetVideError: Si `data` est vide.
    """
    if n_mois <= 0:
        raise ParametreInvalideError(
            "n_mois", n_mois, "le nombre de mois doit être strictement positif."
        )
    if "date" not in data.columns:
        raise ColonnesManquantesError(["date"], contexte="agreger_derniers_mois")
    if data.empty:
        raise DatasetVideError(
            "Le DataFrame fourni à 'agreger_derniers_mois' est vide."
        )

    derniers = sorted(data["date"].unique())[-n_mois:]
    log.debug("Filtrage sur les %d derniers mois : %s", len(derniers), derniers)
    return data[data["date"].isin(derniers)].copy()


def composantes_fiabilite(
    data: pd.DataFrame, volume_min: int = VOLUME_MIN, par: str | None = None
) -> pd.DataFrame:
    """Calcule les 3 composantes brutes du score de fiabilité, par liaison.

    Composantes (cadrage, section 3) : part de trains en retard (sur les trains
    circulés), taux d'annulation (sur les trains prévus), et retard moyen de
    tous les trains à l'arrivée (pondéré par les trains circulés chaque mois).
    Les liaisons avec moins de `volume_min` trains circulés sont écartées.

    Args:
        data: Jeu de régularité préparé (``preparer_regularite``), idéalement
            restreint aux 12 derniers mois via `agreger_derniers_mois`.
        volume_min: Nombre minimal de trains circulés sur la période.
        par: Colonne de découpage supplémentaire (ex. ``"annee"`` pour
            l'historique), ou `None` pour une seule valeur par liaison.

    Returns:
        Un DataFrame indexé par liaison (et par `par`) avec ``classe_duree``,
        ``internationale`` et les colonnes de `COMPOSANTES_FIABILITE`.

    Raises:
        ParametreInvalideError: Si `volume_min` est négatif.
        ColonnesManquantesError: Si une colonne requise est absente de `data`.
        DatasetVideError: Si aucune liaison n'atteint `volume_min`.
    """
    if volume_min < 0:
        raise ParametreInvalideError(
            "volume_min", volume_min, "le volume minimal doit être positif ou nul."
        )

    cles = LIAISON + ([par] if par else [])
    requis = {
        *cles,
        "classe_duree",
        "internationale",
        "nb_train_prevu",
        "nb_train_circule",
        "nb_annulation",
        "nb_train_retard_arrivee",
        "retard_moyen_tous_trains_arrivee",
    }
    manquantes = requis - set(data.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="composantes_fiabilite")

    data = data.copy()
    data["retard_pondere"] = (
        data["retard_moyen_tous_trains_arrivee"] * data["nb_train_circule"]
    )

    agg = data.groupby(cles, observed=True).agg(
        classe_duree=("classe_duree", "first"),
        internationale=("internationale", "first"),
        nb_train_prevu=("nb_train_prevu", "sum"),
        nb_train_circule=("nb_train_circule", "sum"),
        nb_annulation=("nb_annulation", "sum"),
        nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
        retard_pondere=("retard_pondere", "sum"),
    )
    agg = agg[agg["nb_train_circule"] >= volume_min]
    if agg.empty:
        raise DatasetVideError(
            f"""Aucune liaison ne dépasse le volume
            minimal de {volume_min} trains circulés."""
        )

    agg["part_retard"] = agg["nb_train_retard_arrivee"] / agg["nb_train_circule"]
    agg["taux_annulation"] = agg["nb_annulation"] / agg["nb_train_prevu"]
    agg["retard_moyen_tous_trains"] = agg["retard_pondere"] / agg["nb_train_circule"]

    log.debug(
        "Composantes de fiabilité calculées pour %d liaisons (volume_min=%d, par=%s)",
        len(agg),
        volume_min,
        par,
    )
    return agg[["classe_duree", "internationale", *COMPOSANTES_FIABILITE]]


def score_fiabilite(
    data: pd.DataFrame, composantes: list[str] = COMPOSANTES_FIABILITE
) -> pd.DataFrame:
    """Ajoute le rang par classe de durée et le score de fiabilité (poids égaux).

    Le score est la moyenne des rangs en pourcentile des composantes, calculés
    à l'intérieur de la classe de durée de chaque liaison. Un score proche de
    0 indique une liaison fiable par rapport aux autres liaisons de durée
    comparable ; proche de 1, une liaison peu fiable. Si la colonne
    ``internationale`` est présente, ces liaisons ne sont pas classées et
    gardent un score vide.

    Args:
        data: Résultat de `composantes_fiabilite` (colonnes ``classe_duree`` +
            `composantes`).
        composantes: Colonnes à utiliser pour le score.

    Returns:
        Copie de `data` avec une colonne ``rang_<composante>`` par composante et
        ``score_fiabilite``.

    Raises:
        ParametreInvalideError: Si `composantes` est vide.
        ColonnesManquantesError: Si ``classe_duree`` ou une composante est
            absente de `data`.
    """
    if not composantes:
        raise ParametreInvalideError(
            "composantes",
            composantes,
            "la liste des composantes du score ne peut pas être vide.",
        )

    requis = {"classe_duree", *composantes}
    manquantes = requis - set(data.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="score_fiabilite")

    data = data.copy()
    comparables = data
    if "internationale" in data.columns:
        comparables = data[~data["internationale"]]
    rangs = comparables.groupby("classe_duree", observed=True)[composantes].rank(
        pct=True
    )
    rangs.columns = [f"rang_{c}" for c in composantes]
    data = data.join(rangs)
    data["score_fiabilite"] = data[rangs.columns].mean(axis=1)

    log.info(
        "Score de fiabilité calculé pour %d liaisons comparables",
        len(comparables),
    )
    return data


def part_origine_interne(
    data: pd.DataFrame,
    familles: dict[str, list[str]] = FAMILLES_CAUSES,
    liaison_cols: list[str] = LIAISON,
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

    Raises:
        ColonnesManquantesError: Si une colonne requise est absente de `data`.
        DatasetVideError: Si aucune observation fiable n'est disponible.
    """
    colonnes_nb_retard = {f"nb_retard_{famille}": famille for famille in familles}
    requis = {*liaison_cols, "cause_fiable", *colonnes_nb_retard}
    manquantes = requis - set(data.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="part_origine_interne")

    data_ok = data[data["cause_fiable"]]
    if data_ok.empty:
        raise DatasetVideError(
            """Aucune observation avec 'cause_fiable=True'
            pour calculer la part d'origine interne."""
        )

    agg = data_ok.groupby(liaison_cols)[list(colonnes_nb_retard)].sum()

    internes = [
        colonne
        for colonne, famille in colonnes_nb_retard.items()
        if famille in ("reseau", "voyageurs")
    ]
    total = agg.sum(axis=1)
    return agg[internes].sum(axis=1) / total


#: Verdict grand public, du plus fiable au moins fiable.
NIVEAUX_FIABILITE: list[str] = ["plutôt fiable", "dans la moyenne", "peu fiable"]


def position_dans_classe(scores: pd.DataFrame) -> pd.Series:
    """Part des liaisons de même classe de durée moins fiables que chaque liaison.

    Se lit « plus fiable que X % des trajets de même durée ». Les liaisons sans
    score (internationales) n'ont pas de position.

    Args:
        scores: Résultat de `score_fiabilite`.

    Returns:
        Série indexée par liaison, de 0 (la moins fiable) à près de 1.

    Raises:
        ColonnesManquantesError: Si ``classe_duree`` ou ``score_fiabilite`` est
            absente de `scores`.
    """
    manquantes = {"classe_duree", "score_fiabilite"} - set(scores.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="position_dans_classe")

    rang = scores.groupby("classe_duree", observed=True)["score_fiabilite"].rank(
        pct=True
    )
    return 1 - rang


def niveau_fiabilite(position: float) -> str | None:
    """Traduit une position dans la classe en verdict : tiers supérieur, etc.

    Args:
        position: Résultat de `position_dans_classe` pour une liaison.

    Returns:
        Une valeur de `NIVEAUX_FIABILITE`, ou `None` sans position.
    """
    if pd.isna(position):
        return None
    if position >= 2 / 3:
        return NIVEAUX_FIABILITE[0]
    if position >= 1 / 3:
        return NIVEAUX_FIABILITE[1]
    return NIVEAUX_FIABILITE[2]


def medianes_par_classe(
    scores: pd.DataFrame, composantes: list[str] = COMPOSANTES_FIABILITE
) -> pd.DataFrame:
    """Valeurs d'un trajet typique (médiane) de chaque classe de durée.

    Sert de point de comparaison : « 17 % de retards, contre 14 % pour un trajet
    typique de même durée ». Les liaisons internationales sont exclues.

    Args:
        scores: Résultat de `composantes_fiabilite` ou de `score_fiabilite`.
        composantes: Colonnes à résumer.

    Returns:
        Un DataFrame indexé par classe de durée, une colonne par composante.

    Raises:
        ColonnesManquantesError: Si ``classe_duree`` ou une composante est
            absente de `scores`.
    """
    manquantes = {"classe_duree", *composantes} - set(scores.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="medianes_par_classe")

    comparables = scores
    if "internationale" in scores.columns:
        comparables = scores[~scores["internationale"]]
    return comparables.groupby("classe_duree", observed=True)[composantes].median()


def etoiles(score: float) -> int | None:
    """Note de fiabilité sur 5 étoiles, 5 étant la plus fiable.

    Le score va de 0 (la plus fiable de sa classe) à 1 (la moins fiable) : on
    l'inverse et on le ramène sur 5, arrondi à l'étoile près.

    Args:
        score: Score de fiabilité (colonne ``score_fiabilite``).

    Returns:
        Un nombre d'étoiles de 0 à 5, ou `None` sans score.
    """
    if pd.isna(score):
        return None
    return round((1 - score) * 5)
