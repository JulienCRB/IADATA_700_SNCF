"""Indicateurs de qualité et repérage exploratoire des valeurs extrêmes."""

import pandas as pd


def normaliser_noms(s: pd.Series) -> pd.Series:
    """Majuscules, sans accents, tirets remplacés par des espaces.

    Permet de comparer les noms de gares entre les différentes sources
    (ex. régularité TGV vs liste des gares), qui n'utilisent pas la même
    convention de nommage (accents, tirets, espaces multiples, "SAINT" écrit
    en entier ou abrégé, suffixe "TGV"...).
    """
    return (
        s.str.upper()
        .str.normalize("NFKD")  # sépare la lettre de son accent : É -> E + ´
        .str.encode("ascii", errors="ignore")  # supprime les accents
        .str.decode("ascii")
        .str.replace("-", " ", regex=False)
        .str.replace(r"\bSAINTE\b", "ST", regex=True)  # SAINTE -> STE
        .str.replace(r"\bSAINT\b", "ST", regex=True)  # SAINT -> ST
        .str.replace(r"\bTGV\b", "", regex=True)  # supprime le mot "TGV"
        .str.replace(r"\s+", " ", regex=True)  # espaces multiples -> un seul
        .str.strip()  # retire l'espace laissé en fin de nom par la suppression de "TGV"
    )


def garder_gares_tgv_si_doublon(df: pd.DataFrame) -> pd.DataFrame:
    """Résout les doublons créés par la suppression du mot "TGV".

    Si plusieurs libellés d'origine donnent le même nom normalisé (ex. "Valence"
    et "Valence-TGV" -> "VALENCE") et que l'un d'eux contient "TGV", on ne garde
    que les lignes de la gare TGV. Sans variante TGV, le groupe est laissé tel quel.

    Le DataFrame doit contenir la colonne d'origine "libelle" et la colonne
    normalisée "gare".
    """
    df = df.copy()
    est_tgv = df["libelle"].str.upper().str.contains(r"\bTGV\b", regex=True, na=False)

    # Nombre de libellés d'origine différents pour un même nom normalisé
    nb_libelles = df.groupby("gare")["libelle"].transform("nunique")

    # Le groupe contient-il au moins une gare TGV ?
    groupe_a_un_tgv = est_tgv.groupby(df["gare"]).transform("any")

    # À retirer : gare en doublon, avec une variante TGV, et qui n'est pas la TGV
    a_supprimer = (nb_libelles > 1) & groupe_a_un_tgv & ~est_tgv

    return df[~a_supprimer]


def gares_uniques(df: pd.DataFrame) -> pd.DataFrame:
    """Une ligne par gare (code UIC unique), avec sa localisation.

    Le jeu de données d'origine contient une ligne par couple (gare, ligne de
    chemin de fer) : une gare desservie par trois lignes apparaît trois fois.
    On ne garde ici qu'une ligne par code UIC, et seulement les colonnes
    d'identification et de localisation.
    """
    df = df.rename(columns=str.lower)  # accepte CODE_UIC comme code_uic

    # Selon la source, la colonne s'appelle "departemen" (API) ou "departement"
    col_dep = "departemen" if "departemen" in df.columns else "departement"
    colonnes = ["code_uic", "libelle", col_dep, "commune", "x_wgs84", "y_wgs84"]

    return (
        df[colonnes]
        .rename(columns={col_dep: "departement"})
        .dropna(subset=["code_uic"])  # écarte les lignes sans code UIC
        .drop_duplicates(subset="code_uic")  # garde la première ligne de chaque gare
        .reset_index(drop=True)
    )


def ajouter_gares(df: pd.DataFrame, nouvelles_gares: list[dict]) -> pd.DataFrame:
    """Ajoute à la liste des gares des gares qui en sont absentes.

    Utile pour les gares absentes du jeu de données d'origine (par exemple
    les gares étrangères). Chaque gare est un dictionnaire dont les clés sont
    les colonnes du DataFrame ("code_uic", "libelle", "departement", ...).
    Si un code UIC existe déjà, la ligne d'origine est conservée.
    """
    if not nouvelles_gares:
        return df

    df_nouvelles = pd.DataFrame(nouvelles_gares)
    return (
        pd.concat([df, df_nouvelles], ignore_index=True)
        .drop_duplicates(subset="code_uic")
        .reset_index(drop=True)
    )
