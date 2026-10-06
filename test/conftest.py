"""Fixtures partagées par les tests RailInsight."""

import pandas as pd
import pytest

from railinsight.data.loader import normalize_dataframe


@pytest.fixture
def raw_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2024-01",
                "service": "National",
                "gare_depart": "PARIS MONTPARNASSE",
                "gare_arrivee": "BORDEAUX ST JEAN",
                "duree_moyenne": "135",
                "nb_train_prevu": "100",
                "nb_annulation": "2",
                "commentaire_annulation": "nan",
                "nb_train_depart_retard": "30",
                "retard_moyen_depart": "9.5",
                "retard_moyen_tous_trains_depart": "2.85",
                "commentaire_retards_depart": "",
                "nb_train_retard_arrivee": "20",
                "retard_moyen_arrivee": "18.0",
                "retard_moyen_tous_trains_arrivee": "3.6",
                "commentaires_retard_arrivee": "nan",
                "nb_train_retard_sup_15": "8",
                "retard_moyen_trains_retard_sup15": "18.0",
                "nb_train_retard_sup_30": "3",
                "nb_train_retard_sup_60": "1",
                "prct_cause_externe": "20",
                "prct_cause_infra": "30",
                "prct_cause_gestion_trafic": "10",
                "prct_cause_materiel_roulant": "15",
                "prct_cause_gestion_gare": "15",
                "prct_cause_prise_en_charge_voyageurs": "10",
            },
            {
                "date": "2024-02",
                "service": "National",
                "gare_depart": "PARIS MONTPARNASSE",
                "gare_arrivee": "BORDEAUX ST JEAN",
                "duree_moyenne": "135",
                "nb_train_prevu": "100",
                "nb_annulation": "0",
                "commentaire_annulation": "?",
                "nb_train_depart_retard": "25",
                "retard_moyen_depart": "8.0",
                "retard_moyen_tous_trains_depart": "2.0",
                "commentaire_retards_depart": "—",
                "nb_train_retard_arrivee": "15",
                "retard_moyen_arrivee": "16.0",
                "retard_moyen_tous_trains_arrivee": "2.4",
                "commentaires_retard_arrivee": "None",
                "nb_train_retard_sup_15": "5",
                "retard_moyen_trains_retard_sup15": "16.0",
                "nb_train_retard_sup_30": "2",
                "nb_train_retard_sup_60": "0",
                "prct_cause_externe": "10",
                "prct_cause_infra": "40",
                "prct_cause_gestion_trafic": "10",
                "prct_cause_materiel_roulant": "20",
                "prct_cause_gestion_gare": "10",
                "prct_cause_prise_en_charge_voyageurs": "10",
            },
        ]
    )


@pytest.fixture
def dataframe(raw_dataframe: pd.DataFrame) -> pd.DataFrame:
    return normalize_dataframe(raw_dataframe)
