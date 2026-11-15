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
    cause_de_l_evolution,
    evolution_causes,
    liaisons_en_difficulte,
    taux_par_annee,
)
from railinsight.analysis.reliability import (
    agreger_derniers_mois,
    composantes_fiabilite,
    part_origine_interne,
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

    def contributions_par_liaison(self) -> pd.DataFrame:
        """Phase 1 : contributions des familles de causes et cause dominante.

        Returns:
            Une ligne par liaison nationale, avec les colonnes ``contrib_<famille>``
            et ``cause_dominante``.
        """
        contributions = contributions_par_liaison(self._nationales())
        contributions["cause_dominante"] = cause_dominante(contributions)
        return contributions

    def liaisons_en_difficulte(self) -> pd.DataFrame:
        """Phase 2 : liaisons durablement en difficulté et cause de leur évolution.

        Returns:
            Une ligne par liaison nationale (voir
            ``railinsight.analysis.difficulte.liaisons_en_difficulte``), plus
            ``cause_evolution`` pour les liaisons sélectionnées.
        """
        bilan = liaisons_en_difficulte(taux_par_annee(self._data))
        delta = evolution_causes(self._data)
        bilan["cause_evolution"] = cause_de_l_evolution(delta, bilan["en_difficulte"])
        return bilan

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
            ``part_origine_interne``.
        """
        recents = agreger_derniers_mois(self._data, n_mois)
        scores = score_fiabilite(composantes_fiabilite(recents))
        scores["part_origine_interne"] = part_origine_interne(recents)
        return scores

    def _nationales(self) -> pd.DataFrame:
        """Observations des liaisons nationales seulement (usage interne)."""
        return self._data[~self._data["internationale"]]
