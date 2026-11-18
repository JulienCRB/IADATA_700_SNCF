"""Prétraitement des données.

Permet d'obtenir des dataframes ready-to-use dans les différentes analyses.
"""

import pandas as pd

from railinsight.exceptions import (
    ColonnesManquantesError,
    DatasetVideError,
    FormatDateInvalideError,
)

from .loader import FREQUENTATION, load
from .quality import (
    ajouter_gares,
    garder_gares_tgv_si_doublon,
    gares_uniques,
    normaliser_noms,
)

#: Colonnes identifiant une liaison (un sens de circulation).
LIAISON: list[str] = ["gare_depart", "gare_arrivee"]

#: Gares hors de France : une liaison qui en touche une est internationale.
GARES_ETRANGERES: list[str] = [
    "BARCELONA",
    "FRANCFORT",
    "GENEVE",
    "ITALIE",
    "LAUSANNE",
    "MADRID",
    "STUTTGART",
    "ZURICH",
]

#: Classes de durée du cadrage, avec leurs bornes en minutes.
CLASSES_DUREE: list[str] = ["< 1h30", "1h30-3h", "> 3h"]
BORNES_DUREE: list[float] = [0, 90, 180, float("inf")]

#: Saison météorologique de chaque mois.
SAISONS: dict[int, str] = {
    12: "hiver",
    1: "hiver",
    2: "hiver",
    3: "printemps",
    4: "printemps",
    5: "printemps",
    6: "été",
    7: "été",
    8: "été",
    9: "automne",
    10: "automne",
    11: "automne",
}
ORDRE_SAISONS: list[str] = ["hiver", "printemps", "été", "automne"]


def preprocess_gares(df_gares_brut: pd.DataFrame) -> pd.DataFrame:
    """Transforme la liste brute des gares en liste propre.

    Raises:
        DatasetVideError: Si `df_gares_brut` est vide.
        ColonnesManquantesError: Si une colonne requise est absente.
    """
    if df_gares_brut.empty:
        raise DatasetVideError("Le DataFrame brut des gares est vide.")

    df = df_gares_brut.rename(columns=str.lower).copy()
    if "libelle" not in df.columns:
        raise ColonnesManquantesError(["libelle"], contexte="preprocess_gares")

    # Créer le nom normalisé pour identifier les variantes d'une même gare
    df["gare"] = normaliser_noms(df["libelle"])

    # Conserver le libellé TGV lorsqu'il existe plusieurs variantes
    df = garder_gares_tgv_si_doublon(df)

    # Conserver une seule ligne par code UIC
    df = gares_uniques(df)

    # Ajouter les gares absentes du jeu de données
    gares_a_ajouter = [
        {
            "code_uic": 9998,
            "libelle": "BARCELONA",
            "departement": None,
            "commune": "Barcelona",
            "x_wgs84": 2.138206,
            "y_wgs84": 41.378218,
        },
        {
            "code_uic": 9997,
            "libelle": "FRANCFORT",
            "departement": None,
            "commune": "Frankfurt am Main",
            "x_wgs84": 8.662550,
            "y_wgs84": 50.106730,
        },
        {
            "code_uic": 9996,
            "libelle": "GENEVE",
            "departement": None,
            "commune": "Genève",
            "x_wgs84": 6.142447,
            "y_wgs84": 46.210217,
        },
        {
            "code_uic": 9995,
            "libelle": "ITALIE",
            "departement": None,
            "commune": "Rome",
            "x_wgs84": 12.496400,
            "y_wgs84": 41.902800,
        },
        {
            "code_uic": 9994,
            "libelle": "LAUSANNE",
            "departement": None,
            "commune": "Lausanne",
            "x_wgs84": 6.629111,
            "y_wgs84": 46.516806,
        },
        {
            "code_uic": 9993,
            "libelle": "MADRID",
            "departement": None,
            "commune": "Madrid",
            "x_wgs84": -3.690387,
            "y_wgs84": 40.406397,
        },
        {
            "code_uic": 9992,
            "libelle": "STUTTGART",
            "departement": None,
            "commune": "Stuttgart",
            "x_wgs84": 9.183400,
            "y_wgs84": 48.785610,
        },
        {
            "code_uic": 9991,
            "libelle": "ZURICH",
            "departement": None,
            "commune": "Zürich",
            "x_wgs84": 8.540278,
            "y_wgs84": 47.377778,
        },
    ]

    # Ajouter les gares propres
    df = ajouter_gares(df, gares_a_ajouter)

    # Normaliser les noms pour les jointures
    df["gare"] = normaliser_noms(df["libelle"])

    return df.reset_index(drop=True)


def preprocess_regularite(
    df_regularite: pd.DataFrame,
    df_gares_propre: pd.DataFrame,
) -> pd.DataFrame:
    """Ajoute les colonnes uic_depart et uic_arrivee au jeu de régularité.

    Le code UIC est retrouvé en comparant le nom normalisé de la gare avec
    la liste propre des gares. Les gares introuvables peuvent être renseignées
    manuellement dans le dictionnaire uic_manuels.

    Raises:
        DatasetVideError: Si `df_regularite` ou `df_gares_propre` est vide.
        ColonnesManquantesError: Si une colonne requise est absente.
    """
    if df_regularite.empty:
        raise DatasetVideError("Le DataFrame de régularité est vide.")
    if df_gares_propre.empty:
        raise DatasetVideError("Le référentiel propre des gares est vide.")

    manquantes_reg = set(LIAISON) - set(df_regularite.columns)
    if manquantes_reg:
        raise ColonnesManquantesError(
            manquantes_reg, contexte="preprocess_regularite (df_regularite)"
        )

    manquantes_gares = {"gare", "code_uic"} - set(df_gares_propre.columns)
    if manquantes_gares:
        raise ColonnesManquantesError(
            manquantes_gares, contexte="preprocess_regularite (df_gares_propre)"
        )

    df = df_regularite.copy()

    # Nom normalisé -> code UIC
    # Une seule ligne par nom pour éviter les ambiguïtés
    correspondance = df_gares_propre.drop_duplicates(subset="gare").set_index("gare")[
        "code_uic"
    ]

    # Codes UIC manquants, d'après les noms dans la régularité
    uic_manuels = {
        "BELLEGARDE (AIN)": 87745000,
        "LILLE": 87223263,
        "MARNE LA VALLEE": 87721761,
        "METZ": 87192039,
        "MONTPELLIER": 87773002,
        "NANCY": 87141002,
        "PARIS LYON": 87686006,
        "PARIS MONTPARNASSE": 87391011,
        "STRASBOURG": 87212027,
        "VALENCE ALIXAN TGV": 87763029,
    }

    for sens in ["depart", "arrivee"]:
        nom_gare = df[f"gare_{sens}"]

        # Jointure sur le nom normalisé
        uic = normaliser_noms(nom_gare).map(correspondance)

        # Compléter les codes UIC manquants
        uic = uic.fillna(nom_gare.map(uic_manuels))

        # Utiliser un entier qui accepte les valeurs manquantes
        df[f"uic_{sens}"] = uic.astype("Int64")

    # Identifier les gares sans code UIC
    manquantes = pd.concat(
        [
            df.loc[df["uic_depart"].isna(), "gare_depart"],
            df.loc[df["uic_arrivee"].isna(), "gare_arrivee"],
        ]
    ).unique()

    print(f"{len(manquantes)} gares sans code UIC : {sorted(manquantes)}")

    return df


def preprocess_dates(
    df_regularite: pd.DataFrame,
    colonne_date: str = "date",
) -> pd.DataFrame:
    """Crée une table de dates mensuelles à partir du dataset de régularité.

    La table couvre la période comprise entre le premier mois et le dernier
    mois présents dans le dataset de régularité.

    Colonnes créées :
        - date : date au format AAAA-MM
        - AAAA : année
        - MM : numéro du mois
        - AAAAMM : clé de tri chronologique
        - mois : nom complet du mois en français
        - mois_court : abréviation du mois suivie d'un point
        - mois_annee : abréviation suivie de l'année sur deux chiffres
        - saison : saison météorologique

    Raises:
        ColonnesManquantesError: Si `colonne_date` est absente de `df_regularite`.
        FormatDateInvalideError: Si les dates sont vides ou ne respectent pas le
            format ``AAAA-MM``.
    """
    if colonne_date not in df_regularite.columns:
        raise ColonnesManquantesError([colonne_date], contexte="preprocess_dates")

    # Convertir les dates au format datetime
    try:
        dates = pd.to_datetime(
            df_regularite[colonne_date],
            format="%Y-%m",
            errors="raise",
        )
    except (ValueError, TypeError) as err:
        raise FormatDateInvalideError(
            colonne_date,
            details="les dates doivent respecter le format 'AAAA-MM'.",
        ) from err

    # Vérifier que le dataset contient des dates
    if dates.isna().all():
        raise FormatDateInvalideError(
            colonne_date,
            details="la colonne ne contient aucune date valide.",
        )

    date_min = dates.min()
    date_max = dates.max()

    # Générer une ligne par mois
    dates_mensuelles = pd.date_range(
        start=date_min,
        end=date_max,
        freq="MS",
    )

    df_dates = pd.DataFrame(
        {
            "date": dates_mensuelles.strftime("%Y-%m"),
            "AAAA": dates_mensuelles.year,
            "MM": dates_mensuelles.month,
            "AAAAMM": (dates_mensuelles.year * 100 + dates_mensuelles.month),
        }
    )

    # Noms complets des mois en français
    noms_mois = {
        1: "janvier",
        2: "février",
        3: "mars",
        4: "avril",
        5: "mai",
        6: "juin",
        7: "juillet",
        8: "août",
        9: "septembre",
        10: "octobre",
        11: "novembre",
        12: "décembre",
    }

    df_dates["mois"] = df_dates["MM"].map(noms_mois)

    # Abréviation de trois lettres suivie d'un point
    df_dates["mois_court"] = df_dates["mois"].str[:3] + "."

    # Abréviation suivie de l'année sur deux chiffres (ex. "jan. 25")
    df_dates["mois_annee"] = (
        df_dates["mois_court"] + " " + dates_mensuelles.strftime("%y")
    )

    # Déterminer la saison météorologique
    df_dates["saison"] = df_dates["MM"].map(SAISONS)

    return df_dates


def preprocess_fq() -> pd.DataFrame:
    """Charge et prétraite le dataset de fréquentation.

    Raises:
        ChargementDonneesError: En cas d'échec de téléchargement ou de lecture.
        ColonnesManquantesError: Si la colonne ``nom_gare`` est absente.
    """
    df = load(FREQUENTATION)
    if "nom_gare" not in df.columns:
        raise ColonnesManquantesError(["nom_gare"], contexte="preprocess_fq")
    df = df.copy()
    df["gare"] = normaliser_noms(df["nom_gare"])
    return df


def preparer_regularite(df_regularite: pd.DataFrame) -> pd.DataFrame:
    """Ajoute au jeu de régularité les colonnes communes à toutes les analyses.

    Colonnes ajoutées :
        - annee : année d'octobre à septembre, nommée par l'année où elle se
          termine (oct. 2024 → sept. 2025 = 2025), comme en Phase 2.
        - saison : saison météorologique du mois.
        - classe_duree : classe de durée de la liaison (cadrage), à partir de sa
          durée médiane sur toute la période.
        - internationale : `True` si la liaison touche une gare étrangère.
        - nb_train_circule : trains réellement circulés (prévus − annulés).

    Les noms de gare sont aussi normalisés (majuscules, sans accents).

    Args:
        df_regularite: Jeu de régularité brut (sortie de ``load(REGULARITE)``).

    Returns:
        Une copie du jeu de régularité avec les colonnes ajoutées.

    Raises:
        DatasetVideError: Si `df_regularite` est vide.
        ColonnesManquantesError: Si une colonne requise est absente.
        FormatDateInvalideError: Si la colonne ``date`` n'est pas au format
            ``AAAA-MM``.
    """
    if df_regularite.empty:
        raise DatasetVideError("Le DataFrame de régularité à préparer est vide.")

    requis = {
        *LIAISON,
        "date",
        "duree_moyenne",
        "nb_train_prevu",
        "nb_annulation",
    }
    manquantes = requis - set(df_regularite.columns)
    if manquantes:
        raise ColonnesManquantesError(manquantes, contexte="preparer_regularite")

    df = df_regularite.copy()
    for colonne in LIAISON:
        df[colonne] = normaliser_noms(df[colonne])

    try:
        mois = df["date"].str[5:7].astype(int)
        annee_base = df["date"].str[:4].astype(int)
    except (ValueError, TypeError, AttributeError) as err:
        raise FormatDateInvalideError(
            "date",
            details="impossible d'extraire l'année et le mois au format 'AAAA-MM'.",
        ) from err

    df["annee"] = annee_base + (mois >= 10).astype(int)
    df["saison"] = mois.map(SAISONS)

    duree_liaison = df.groupby(LIAISON)["duree_moyenne"].transform("median")
    df["classe_duree"] = pd.cut(duree_liaison, bins=BORNES_DUREE, labels=CLASSES_DUREE)

    df["internationale"] = df["gare_depart"].isin(GARES_ETRANGERES) | df[
        "gare_arrivee"
    ].isin(GARES_ETRANGERES)
    df["nb_train_circule"] = df["nb_train_prevu"] - df["nb_annulation"]
    return df