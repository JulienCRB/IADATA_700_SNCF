# 🚄 RailInsight : d'où viennent les retards des TGV ?

[![CI](https://github.com/JulienCRB/IADATA_700_SNCF/actions/workflows/ci.yml/badge.svg)](https://github.com/JulienCRB/IADATA_700_SNCF/actions/workflows/ci.yml)

Application web interactive qui explore la ponctualité du réseau TGV français à partir des données ouvertes de la SNCF, et qui explique l'origine des retards : le réseau, les trains ou des aléas extérieurs.

**Application en ligne** : _(lien à ajouter après le déploiement)_

---

## Sommaire

1. [La question étudiée](#la-question-étudiée)
2. [Ce que montre l'application](#ce-que-montre-lapplication)
3. [Installation](#installation)
4. [Lancer l'application](#lancer-lapplication)
5. [Utiliser le package `railinsight`](#utiliser-le-package-railinsight)
6. [Tests et qualité du code](#tests-et-qualité-du-code)
7. [Logs](#logs)
8. [Déploiement](#déploiement)
9. [Structure du projet](#structure-du-projet)
10. [Méthodologie et limites](#méthodologie-et-limites)
11. [Travail en équipe](#travail-en-équipe)

---

## La question étudiée

> **D'où viennent les retards des TGV : du réseau, des trains ou d'aléas extérieurs ? Et que révèle ce découpage sur les liaisons durablement en difficulté et sur les saisons ?**

L'application permet à chacun de choisir *sa* liaison, de voir son score de fiabilité, de quoi sont faits ses retards et comment ils évoluent.

Le cadrage complet (décisions, phases d'analyse, contenu des pages) est dans [`documentation/cadrage_question_directrice.md`](documentation/cadrage_question_directrice.md). Les arbitrages de la phase 2 sont dans [`documentation/arbitrages_phase2.pdf`](documentation/arbitrages_phase2.pdf).

## Ce que montre l'application

| Page | Question | Contenu |
|---|---|---|
| Accueil | Pourquoi s'y intéresser ? | Question directrice, source des données |
| D'où viennent les retards ? | Réseau, trains ou aléas ? | Répartition des liaisons selon leurs causes de retard |
| Liaisons en difficulté | Lesquelles, et comment évoluent-elles ? | Liaisons durablement en difficulté, évolution et cause de cette évolution |
| Saisons | Quand les retards apparaissent-ils, et pourquoi ? | Contributions des causes par saison |
| Ma liaison | Ma liaison est-elle fiable ? | Score de fiabilité, part d'origine interne, découpage des causes |
| Données et limites | Peut-on faire confiance aux chiffres ? | Source, méthodologie, limites |
| Carte du réseau | Où passent les TGV ? | Carte interactive des liaisons et des gares |

**Données** : [Régularité mensuelle TGV (AQST)](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/information/), SNCF Open Data. Une ligne par liaison (gare de départ, gare d'arrivée) et par mois, depuis janvier 2018. Les données sont téléchargées directement depuis l'API SNCF au lancement de l'application (aucun fichier à fournir).

## Installation

### Prérequis

- **Python 3.13** (la version est fixée dans `.python-version`)
- **[uv](https://docs.astral.sh/uv/)**, le gestionnaire d'environnement et de dépendances du projet
- **Git**
- Une **connexion Internet** (les données sont chargées depuis l'API SNCF)

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/JulienCRB/IADATA_700_SNCF.git
cd IADATA_700_SNCF

# 2. Créer l'environnement virtuel et installer les dépendances
uv sync
```

`uv sync` crée le dossier `.venv` et installe les versions exactes figées dans `uv.lock`, y compris les outils de développement (pytest, ruff).

> ⚠️ Évitez les espaces et les caractères spéciaux dans le chemin du dossier du projet. Si vous déplacez ou renommez le dossier, supprimez `.venv` et relancez `uv sync`.

## Lancer l'application

```bash
uv run streamlit run app/main.py
```

L'application s'ouvre dans le navigateur, par défaut à l'adresse http://localhost:8501. Le premier chargement télécharge les données (quelques secondes) ; elles sont ensuite mises en cache par Streamlit.

La navigation entre les pages se fait par le menu de gauche.

## Utiliser le package `railinsight`

Toute la logique d'analyse est dans le package `railinsight`, indépendant de Streamlit. La classe `Regularite` en est le point d'entrée : elle télécharge et prépare les données une seule fois, puis expose chaque analyse du cadrage sous forme de méthode.

```python
from railinsight.regularite import Regularite

regularite = Regularite.depuis_sncf()

regularite.contributions_par_liaison()  # Phase 1 : causes de retard par liaison
regularite.liaisons_en_difficulte()     # Phase 2 : liaisons durablement en difficulté
regularite.contributions_par_saison()   # Phase 3 : causes par saison
regularite.score_fiabilite()            # Phase 4 : score de fiabilité (12 derniers mois)
```

| Module | Rôle |
|---|---|
| `railinsight.data.loader` | Téléchargement des jeux SNCF Open Data |
| `railinsight.data.preprocessing` | Préparation : noms de gares, codes UIC, années, classes de durée, saisons |
| `railinsight.data.quality` | Normalisation des noms de gares, contrôles de qualité |
| `railinsight.analysis.causes` | Familles de causes, contributions, cause dominante, saisons |
| `railinsight.analysis.difficulte` | Seuils, volume minimal, liaisons en difficulté, évolution |
| `railinsight.analysis.reliability` | Score de fiabilité et part d'origine interne |
| `railinsight.viz.charts` | Graphiques Plotly (barres, carte du réseau) |
| `railinsight.logger` | Configuration des logs |

## Tests et qualité du code

```bash
# Tests unitaires + couverture (échoue sous 90 %)
uv run pytest

# Style PEP 8, ordre des imports et docstrings (convention Google)
uv run ruff check .

# Formatage
uv run ruff format --check .   # vérifier
uv run ruff format .           # corriger
```

La configuration (seuil de couverture, règles ruff) est dans `pyproject.toml`. Les notebooks d'exploration (`notebook/`) sont exclus des vérifications de style.

### Intégration continue

Le pipeline GitHub Actions (`.github/workflows/ci.yml`) s'exécute à chaque Pull Request et à chaque push sur `develop` et `main`. Il installe l'environnement avec `uv sync --locked`, puis lance `ruff check`, `ruff format --check` et `pytest` avec le contrôle de couverture. Une Pull Request ne peut être fusionnée que si la CI passe et qu'au moins un membre de l'équipe l'a approuvée.

## Logs

Le module `railinsight.logger` écrit deux fichiers dans le dossier `logs/` (créé automatiquement, non versionné) :

| Fichier | Contenu |
|---|---|
| `logs/debug.log` | Tous les événements (téléchargements, préparation des données…) |
| `logs/errors.log` | Erreurs seulement (niveaux `ERROR` et `CRITICAL`) |

Les fichiers tournent à 1 Mo (3 sauvegardes conservées).

## Déploiement

_(À compléter une fois l'application déployée.)_

L'application est prévue pour **Streamlit Community Cloud** :

1. Se connecter sur [share.streamlit.io](https://share.streamlit.io) avec son compte GitHub.
2. Créer une application à partir du dépôt `JulienCRB/IADATA_700_SNCF`, branche `main`.
3. Indiquer `app/main.py` comme fichier principal et Python 3.13.
4. Déployer : les dépendances sont lues depuis le dépôt.

## Structure du projet

```
IADATA_700_SNCF/
├── app/                     # Application Streamlit
│   ├── main.py              # Page d'accueil
│   ├── pages/               # Une page par question du cadrage
│   └── utils.py             # Chargement des données en cache
├── railinsight/             # Package d'analyse (logique métier)
│   ├── data/                # Chargement, préparation, qualité
│   ├── analysis/            # Causes, difficulté, fiabilité
│   ├── viz/                 # Graphiques
│   ├── regularite.py        # Classe Regularite (point d'entrée)
│   └── logger.py            # Logs
├── test/                    # Tests unitaires (pytest)
├── notebook/                # Notebooks d'exploration (phases 1 et 2)
├── documentation/           # Cadrage et arbitrages
├── .github/workflows/       # Pipeline CI
├── .streamlit/config.toml   # Thème de l'application
├── pyproject.toml           # Dépendances et configuration des outils
└── uv.lock                  # Versions figées des dépendances
```

## Méthodologie et limites

Les principaux choix, détaillés dans le cadrage et les notebooks :

- **Unité d'observation** : une liaison × un mois. Il n'y a pas de donnée train par train.
- **Jamais de total réseau** : un même train compte dans plusieurs liaisons. Les résultats sont donnés par liaison, ou sous forme de distribution des liaisons.
- **Pondération** : toujours par le nombre de trains, jamais par une moyenne de taux.
- **Causes regroupées en trois familles** : Réseau (infrastructure, gestion du trafic), Voyageurs (matériel roulant, gestion en gare, prise en charge des voyageurs), Externe (dont les grèves).
- **Contributions plutôt que parts** : la contribution d'une cause est le taux de retard multiplié par la part de cette cause.
- **Observations sans cause fiable** : 83 observations (0,6 %) ont des trains en retard mais des causes non renseignées ; elles sont exclues des analyses de causes.
- **Liaisons internationales** : exclues des comparaisons, car elles concentrent les anomalies.

**Limites** :

- Les causes sont **déclarées** par la SNCF, une seule par train (celle de la plus grosse perte de temps). L'étude est **descriptive** : elle ne démontre pas de lien de causalité.
- Les résultats sur la cause dominante dépendent du regroupement des causes en familles.

## Travail en équipe

- Une branche par sujet, créée depuis `develop`.
- Une Pull Request vers `develop`, relue et approuvée par un autre membre, avec la CI au vert.
- `main` reçoit les versions stables, marquées par des tags (par exemple `v0.4.1`).

**Équipe** : _(noms à compléter)_
