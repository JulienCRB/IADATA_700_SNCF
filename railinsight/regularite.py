"""Point d'entrée des analyses : le jeu de régularité TGV préparé.

La classe `Regularite` prépare les données une seule fois, les garde privées,
et expose chaque analyse du cadrage sous forme de méthode. Les calculs
eux-mêmes restent dans les fonctions de ``railinsight.analysis``, testées
séparément : la classe ne fait que les enchaîner.

Exemple :
    >>> regularite = Regularite.depuis_sncf()
    >>> regularite.liaisons_en_difficulte()
"""

import pandas as pd

from railinsight.analysis.causes import (
    ajouter_nb_retard_par_famille,
    cause_dominante,
    contributions_par_liaison,
    contributions_par_saison,
    marquer_cause_fiable,
)
from railinsight.analysis.difficulte import (
    ajouter_axe,
    cause_de_l_evolution,
    classer_evolution,
    evolution_causes,
    liaisons_en_difficulte,
    taux_par_annee,
)
from railinsight.analysis.reliability import (
    agreger_derniers_mois,
    composantes_fiabilite,
    etoiles,
    niveau_fiabilite,
    part_origine_interne,
    position_dans_classe,
    score_fiabilite,
)
from railinsight.data.loader import REGULARITE, load
from railinsight.data.preprocessing import preparer_regularite


class Regularite:
    """Jeu de régularité mensuelle TGV, préparé pour toutes les analyses.

    Attributes:
        data: Copie du jeu préparé (une liaison × un mois par ligne).
    """

    def __init__(self, brut: pd.DataFrame) -> None:
        """Prépare le jeu brut : colonnes communes, causes fiables, retards par famille.

        Args:
            brut: Jeu de régularité brut, tel que publié par la SNCF.
        """
        data = preparer_regularite(brut)
        data["cause_fiable"] = marquer_cause_fiable(data)
        self._data = ajouter_nb_retard_par_famille(data)

    @classmethod
    def depuis_sncf(cls) -> "Regularite":
        """Télécharge le jeu de régularité depuis l'open data SNCF et le prépare."""
        return cls(load(REGULARITE))

    @property
    def data(self) -> pd.DataFrame:
        """Copie du jeu préparé : modifier la copie ne change pas l'objet."""
        return self._data.copy()

    @property
    def nb_liaisons(self) -> int:
        """Nombre de liaisons (sens de circulation) présentes dans les données."""
        return len(self._data.groupby(["gare_depart", "gare_arrivee"]))

    @property
    def periode(self) -> tuple[str, str]:
        """Premier et dernier mois disponibles, au format ``AAAA-MM``."""
        return self._data["date"].min(), self._data["date"].max()

    def contributions_par_liaison(self) -> pd.DataFrame:
        """Phase 1 : contributions des familles de causes et cause dominante.

        Returns:
            Une ligne par liaison nationale, avec les colonnes ``contrib_<famille>``
            et ``cause_dominante``.
        """
        contributions = contributions_par_liaison(self._nationales())
        contributions["cause_dominante"] = cause_dominante(contributions)
        return contributions

    def contribution_mediane(self) -> pd.Series:
        """Phase 1 : poids de chaque famille de causes pour la liaison médiane.

        Complète la cause dominante : une famille peut n'être la première cause
        d'aucune liaison tout en pesant sur toutes (cas de l'Externe).

        Returns:
            Série indexée par famille (``reseau``, ``voyageurs``, ``externe``),
            contribution médiane au taux de retard (taux, pas en points).
        """
        contributions = contributions_par_liaison(self._nationales())
        return contributions.median().rename(lambda c: c.removeprefix("contrib_"))

    def liaisons_en_difficulte(self) -> pd.DataFrame:
        """Phase 2 : liaisons durablement en difficulté et cause de leur évolution.

        Returns:
            Une ligne par liaison nationale (voir
            ``railinsight.analysis.difficulte.liaisons_en_difficulte``), plus
            ``cause_evolution`` pour les liaisons sélectionnées, ``axe`` et
            ``tendance``.
        """
        bilan = liaisons_en_difficulte(taux_par_annee(self._data))
        delta = evolution_causes(self._data)
        bilan["cause_evolution"] = cause_de_l_evolution(delta, bilan["en_difficulte"])
        return classer_evolution(ajouter_axe(bilan))

    def contributions_par_saison(self) -> pd.DataFrame:
        """Phase 3 : contribution des familles de causes par saison."""
        return contributions_par_saison(self._data)

    def score_fiabilite(self, n_mois: int = 12) -> pd.DataFrame:
        """Phase 4 : score de fiabilité sur les derniers mois, avec la part interne.

        Args:
            n_mois: Nombre de mois les plus récents à prendre en compte.

        Returns:
            Une ligne par liaison (voir
            ``railinsight.analysis.reliability.score_fiabilite``), plus
            ``part_origine_interne``, ``plus_fiable_que`` (part des liaisons de
            même durée moins fiables), ``niveau`` (verdict en mots) et ``etoiles``
            (note de 0 à 5, 5 = la plus fiable).
        """
        recents = agreger_derniers_mois(self._data, n_mois)
        scores = score_fiabilite(composantes_fiabilite(recents))
        scores["part_origine_interne"] = part_origine_interne(recents)
        scores["plus_fiable_que"] = position_dans_classe(scores)
        scores["niveau"] = scores["plus_fiable_que"].map(niveau_fiabilite)
        scores["etoiles"] = scores["score_fiabilite"].map(etoiles)
        return scores

    def historique_composantes(self) -> pd.DataFrame:
        """Les 3 composantes du score, année par année, en valeurs absolues.

        Le score lui-même n'est pas tracé dans le temps (il est relatif) : le
        cadrage prévoit d'afficher l'historique des composantes à la place.

        Returns:
            Une ligne par liaison × année (d'octobre à septembre).
        """
        return composantes_fiabilite(self._data, volume_min=0, par="annee")

    def _nationales(self) -> pd.DataFrame:
        """Observations des liaisons nationales seulement (usage interne)."""
        return self._data[~self._data["internationale"]]
