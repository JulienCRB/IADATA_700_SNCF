"""Liaisons durablement en difficulté (Phase 2).

Porté depuis ``notebook/phase2_exploration.ipynb``, avec les propositions
validées par le groupe (``documentation/arbitrages_phase2.pdf``) :

- taux de retard calculé sur les trains circulés (prévus − annulés) ;
- liaisons internationales exclues des comparaisons ;
- seuil = quartile supérieur par classe de durée, sur la seule période de
  référence ;
- calcul par sens (l'affichage par axe se fait dans l'application).
"""

import pandas as pd

from railinsight.data.preprocessing import LIAISON
from railinsight.exceptions import (
    ColonnesManquantesError,
    DatasetVideError,
    DonneesInvalidesError,
    ParametreInvalideError,
    PeriodeInvalideError,
)
from railinsight.logger import get_logger

from .causes import contributions_par_liaison

log = get_logger(__name__)

#: Années (d'octobre à septembre) de la période de référence et de suivi.
ANNEES_REFERENCE: list[int] = [2023, 2024, 2025]
ANNEE_SUIVI: int = 2026

#: Nombre minimal de trains circulés sur une année complète pour que le taux
#: soit fiable (un retard de plus change le taux d'au plus 1 point).
VOLUME_MIN: int = 100


def taux_par_annee(data: pd.DataFrame, volume_min: int = VOLUME_MIN) -> pd.DataFrame:
    """Taux de retard par liaison et par année, hors liaisons internationales.

    Les liaisons-années avec trop peu de trains sont écartées. Le volume minimal
    est réduit en proportion pour une année incomplète (ex. 2018 : 9 mois, donc
    75 trains).

    Args:
        data: Jeu de régularité préparé (``preparer_regularite``).
        volume_min: Trains circulés minimum sur une année complète.

    Returns:
        Une ligne par liaison × année, avec ``classe_duree``,
        ``nb_train_circule``, ``nb_train_retard_arrivee`` et ``taux_retard``.

    Raises:
        ParametreInvalideError: Si `volume_min` est négatif.
        ColonnesManquantesError: Si une colonne requise est absente de `data`.
        DatasetVideError: Si aucune liaison nationale n'est présente dans `data`.
    """
    if volume_min < 0:
        raise ParametreInvalideError(
            "volume_min", volume_min, "le volume minimal doit être positif ou nul."
        )

    requis = {
        *LIAISON,
        "internationale",
        "annee",
        "classe_duree",
        "nb_train_circule",
        "nb_train_retard_arrivee",
        "date",
    }
    manquantes = requis - set(data.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="taux_par_annee")

    nationales = data[~data["internationale"]]
    if nationales.empty:
        raise DatasetVideError(
            "Aucune liaison nationale disponible pour calculer les taux annuels."
        )

    par_an = (
        nationales.groupby([*LIAISON, "annee"], observed=True)
        .agg(
            classe_duree=("classe_duree", "first"),
            nb_train_circule=("nb_train_circule", "sum"),
            nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
        )
        .reset_index()
    )
    par_an["taux_retard"] = (
        par_an["nb_train_retard_arrivee"] / par_an["nb_train_circule"]
    )

    mois_par_annee = data.groupby("annee")["date"].nunique()
    volume_requis = volume_min * par_an["annee"].map(mois_par_annee) / 12
    resultat = par_an[par_an["nb_train_circule"] >= volume_requis].reset_index(
        drop=True
    )

    log.debug(
        "Taux annuels calculés : %d liaisons-années retenues (volume_min=%d)",
        len(resultat),
        volume_min,
    )
    return resultat


def seuils_par_classe(
    par_an: pd.DataFrame,
    annees: list[int] = ANNEES_REFERENCE,
    quantile: float = 0.75,
) -> pd.Series:
    """Seuil de difficulté de chaque classe de durée : le quartile supérieur.

    Args:
        par_an: Résultat de `taux_par_annee`.
        annees: Années utilisées pour le calcul (la période de référence).
        quantile: Quantile du taux de retard qui sert de seuil.

    Returns:
        Série indexée par classe de durée, avec le seuil de taux de retard.

    Raises:
        ParametreInvalideError: Si `quantile` n'est pas dans ``]0, 1[`` ou si
            `annees` est vide.
        ColonnesManquantesError: Si une colonne requise est absente.
        PeriodeInvalideError: Si aucune donnée ne correspond à `annees`.
    """
    if not (0 < quantile < 1):
        raise ParametreInvalideError(
            "quantile",
            quantile,
            "le quantile doit être compris strictement entre 0 et 1.",
        )
    if not annees:
        raise ParametreInvalideError(
            "annees", annees, "la liste des années de référence ne peut pas être vide."
        )

    manquantes = {"annee", "classe_duree", "taux_retard"} - set(par_an.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="seuils_par_classe")

    reference = par_an[par_an["annee"].isin(annees)]
    if reference.empty:
        raise PeriodeInvalideError(
            f"Aucune donnée disponible pour les années de référence {annees}."
        )

    return reference.groupby("classe_duree", observed=True)["taux_retard"].quantile(
        quantile
    )


def liaisons_en_difficulte(
    par_an: pd.DataFrame,
    annees_reference: list[int] = ANNEES_REFERENCE,
    annee_suivi: int = ANNEE_SUIVI,
    min_annees: int = 2,
) -> pd.DataFrame:
    """Repère les liaisons durablement en difficulté et leur évolution.

    Une liaison est « durablement en difficulté » si son taux de retard dépasse
    le seuil de sa classe au moins `min_annees` années de la période de
    référence (cadrage). Son évolution est ensuite comparée à celle des autres
    liaisons, car toute l'année de suivi peut être dégradée (cas de 2026).

    Args:
        par_an: Résultat de `taux_par_annee`.
        annees_reference: Années de la période de référence.
        annee_suivi: Année de la période de suivi.
        min_annees: Nombre d'années au-dessus du seuil pour être sélectionnée.

    Returns:
        Une ligne par liaison avec ``classe_duree``, ``nb_annees_au_dessus``,
        ``en_difficulte``, ``taux_reference``, ``taux_suivi``, ``evolution``
        (en points de taux) et ``evolution_relative`` (écart à l'évolution
        médiane des liaisons non sélectionnées).

    Raises:
        ParametreInvalideError: Si `min_annees` n'est pas compris entre 1 et
            ``len(annees_reference)``.
        ColonnesManquantesError: Si une colonne requise est absente.
        PeriodeInvalideError: Si la période de référence ou l'année de suivi est
            absente de `par_an`.
    """
    if not (1 <= min_annees <= len(annees_reference)):
        raise ParametreInvalideError(
            "min_annees",
            min_annees,
            f"doit être compris entre 1 et {len(annees_reference)}.",
        )

    requis = {
        *LIAISON,
        "annee",
        "classe_duree",
        "taux_retard",
        "nb_train_circule",
        "nb_train_retard_arrivee",
    }
    manquantes = requis - set(par_an.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="liaisons_en_difficulte")

    seuils = seuils_par_classe(par_an, annees_reference)
    reference = par_an[par_an["annee"].isin(annees_reference)].copy()
    reference["au_dessus"] = reference["taux_retard"] > reference["classe_duree"].map(
        seuils
    ).astype(float)

    bilan = reference.groupby(LIAISON).agg(
        classe_duree=("classe_duree", "first"),
        nb_annees_au_dessus=("au_dessus", "sum"),
        nb_train_circule=("nb_train_circule", "sum"),
        nb_train_retard_arrivee=("nb_train_retard_arrivee", "sum"),
    )
    bilan["en_difficulte"] = bilan["nb_annees_au_dessus"] >= min_annees
    bilan["taux_reference"] = (
        bilan["nb_train_retard_arrivee"] / bilan["nb_train_circule"]
    )

    suivi = par_an[par_an["annee"] == annee_suivi].set_index(LIAISON)
    if suivi.empty:
        raise PeriodeInvalideError(
            f"Aucune donnée disponible pour l'année de suivi {annee_suivi}."
        )

    bilan["taux_suivi"] = suivi["taux_retard"]
    bilan["evolution"] = bilan["taux_suivi"] - bilan["taux_reference"]
    tendance = bilan.loc[~bilan["en_difficulte"], "evolution"].median()
    bilan["evolution_relative"] = bilan["evolution"] - tendance

    log.info(
        "Liaisons en difficulté identifiées : %d/%d (référence=%s, suivi=%s)",
        int(bilan["en_difficulte"].sum()),
        len(bilan),
        annees_reference,
        annee_suivi,
    )
    return bilan.drop(columns=["nb_train_circule", "nb_train_retard_arrivee"])


def evolution_causes(
    data: pd.DataFrame,
    annees_reference: list[int] = ANNEES_REFERENCE,
    annee_suivi: int = ANNEE_SUIVI,
) -> pd.DataFrame:
    """Évolution de la contribution de chaque famille entre référence et suivi.

    Args:
        data: Jeu de régularité préparé, avec ``cause_fiable`` et les colonnes
            ``nb_retard_<famille>``.
        annees_reference: Années de la période de référence.
        annee_suivi: Année de la période de suivi.

    Returns:
        Une ligne par liaison nationale, avec une colonne ``contrib_<famille>``
        (contribution de suivi contribution de référence, en taux).

    Raises:
        ColonnesManquantesError: Si une colonne requise est absente.
        PeriodeInvalideError: Si les données de référence ou de suivi sont absentes.
    """
    requis = {*LIAISON, "internationale", "annee", "cause_fiable", "nb_train_circule"}
    manquantes = requis - set(data.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="evolution_causes")

    nationales = data[~data["internationale"]].copy()
    nationales["periode"] = None
    nationales.loc[nationales["annee"].isin(annees_reference), "periode"] = "reference"
    nationales.loc[nationales["annee"] == annee_suivi, "periode"] = "suivi"

    avec_periode = nationales[nationales["periode"].notna()]
    if avec_periode.empty:
        raise PeriodeInvalideError(
            f"Aucune donnée disponible pour {annees_reference} ou {annee_suivi}."
        )

    contrib = contributions_par_liaison(avec_periode, par="periode")
    periodes_presentes = set(contrib.index.get_level_values("periode"))
    if "reference" not in periodes_presentes:
        raise PeriodeInvalideError(
            f"""Aucune donnée fiable disponible
            pour la période de référence {annees_reference}."""
        )
    if "suivi" not in periodes_presentes:
        raise PeriodeInvalideError(
            f"Aucune donnée fiable disponible pour l'année de suivi {annee_suivi}."
        )

    reference = contrib.xs("reference", level="periode")
    suivi = contrib.xs("suivi", level="periode")
    delta = (suivi - reference).dropna()

    log.debug("Évolution des causes calculée pour %d liaisons", len(delta))
    return delta


def cause_de_l_evolution(delta: pd.DataFrame, en_difficulte: pd.Series) -> pd.Series:
    """Famille qui porte l'évolution propre à chaque liaison sélectionnée.

    On retire à chaque liaison l'évolution médiane des liaisons non
    sélectionnées (la tendance du réseau), puis on garde la famille dont
    l'écart est le plus fort.

    Args:
        delta: Résultat de `evolution_causes`.
        en_difficulte: Colonne ``en_difficulte`` de `liaisons_en_difficulte`.

    Returns:
        Série indexée par liaison sélectionnée, avec le nom de la famille.

    Raises:
        DatasetVideError: Si `delta` est vide ou si aucune liaison n'est en
            difficulté.
    """
    if delta.empty:
        raise DatasetVideError("Le DataFrame d'évolution des causes est vide.")

    selection = en_difficulte.reindex(delta.index, fill_value=False)
    if not selection.any():
        raise DatasetVideError(
            "Aucune liaison en difficulté sélectionnée pour analyser l'évolution."
        )

    tendance = delta[~selection].median()
    ecart = delta[selection] - tendance
    return ecart.idxmax(axis=1).str.removeprefix("contrib_")


def ajouter_axe(bilan: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la colonne ``axe`` : les deux sens d'une liaison sous un même nom.

    Le calcul reste fait par sens ; l'axe sert seulement à regrouper les deux
    sens à l'affichage (décision 4 de la Phase 2).

    Args:
        bilan: DataFrame indexé par liaison (gare de départ, gare d'arrivée).

    Returns:
        Copie de `bilan` avec ``axe`` (ex. ``"LYON ↔ PARIS"``, gares triées).

    Raises:
        DonneesInvalidesError: Si l'index de `bilan` n'a pas deux niveaux.
    """
    if bilan.index.nlevels != 2:
        raise DonneesInvalidesError(
            "L'index de 'bilan' doit contenir deux niveaux (gare_depart, gare_arrivee)."
        )

    bilan = bilan.copy()
    bilan["axe"] = [" ↔ ".join(sorted(liaison)) for liaison in bilan.index]
    return bilan


#: Les trois tendances de 2026, par rapport au reste du réseau.
TENDANCES: list[str] = ["s'aggrave", "suit le réseau", "résiste mieux"]


def classer_evolution(bilan: pd.DataFrame, seuil: float = 0.01) -> pd.DataFrame:
    """Range chaque liaison dans une tendance, selon son évolution relative.

    À 1 point près (`seuil`), une liaison « suit le réseau » ; au-delà, elle
    « s'aggrave » plus que les autres ou « résiste mieux » (Phase 2).

    Args:
        bilan: Résultat de `liaisons_en_difficulte` (colonne
            ``evolution_relative``).
        seuil: Écart toléré à l'évolution du réseau, en taux.

    Returns:
        Copie de `bilan` avec la colonne ``tendance`` (une valeur de `TENDANCES`).

    Raises:
        ParametreInvalideError: Si `seuil` est négatif.
        ColonnesManquantesError: Si ``evolution_relative`` est absente de `bilan`.
    """
    if seuil < 0:
        raise ParametreInvalideError(
            "seuil", seuil, "le seuil d'évolution doit être positif ou nul."
        )
    if "evolution_relative" not in bilan.columns:
        raise ColonnesManquantesError(
            ["evolution_relative"], contexte="classer_evolution"
        )

    bilan = bilan.copy()
    relative = bilan["evolution_relative"]
    bilan["tendance"] = TENDANCES[1]
    bilan.loc[relative > seuil, "tendance"] = TENDANCES[0]
    bilan.loc[relative < -seuil, "tendance"] = TENDANCES[2]
    return bilan


def gares_concernees(bilan: pd.DataFrame) -> pd.Series:
    """Nombre de liaisons en difficulté qui partent de ou arrivent à chaque gare.

    Args:
        bilan: Résultat de `liaisons_en_difficulte` (colonne ``en_difficulte``).

    Returns:
        Série indexée par gare, de la plus concernée à la moins concernée.

    Raises:
        ColonnesManquantesError: Si ``en_difficulte`` est absente de `bilan`.
    """
    if "en_difficulte" not in bilan.columns:
        raise ColonnesManquantesError(["en_difficulte"], contexte="gares_concernees")

    selection = bilan[bilan["en_difficulte"]]
    gares = pd.Series(
        [gare for liaison in selection.index for gare in liaison], dtype="object"
    )
    return gares.value_counts()
