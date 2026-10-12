# Application Streamlit - RailInsight

## Structure

```
app/
├── main.py              ← Page d'accueil (automatiquement servie en premier)
├── pages/               ← Pages supplémentaires (numérotées 01_, 02_, etc.)
│   ├── 01_retards.py   
│   ├── 02_liaisons.py
│   ├── 03_saisons.py
│   ├── 04_ma_liaison.py
│   └── 05_donnees.py
├── utils.py            ← Fonctions partagées + cache des données
└── config.py           ← Config générale (optionnel)
```

## Exécuter l'app

```bash
# Installation des dépendances (une fois)
uv sync

# Lancer l'app
streamlit run app/main.py
```

## Comment structurer le code

### 1️⃣ **Créer une page** (`app/pages/XX_nom.py`)

```python
import streamlit as st
from app.utils import get_data

st.title("Ma page")

data = get_data()  # Récupère les données en cache
# ... ton code Streamlit ici
```

### 2️⃣ **Utiliser le package `railinsight`**

Le dossier `railinsight/` contient la logique métier :
- `railinsight.data.loader` → charge les données
- `railinsight.data.quality` → vérifie la qualité
- `railinsight.analysis.causes` → analyse les causes
- `railinsight.analysis.reliability` → calcule les scores
- `railinsight.viz.charts` → crée les graphiques

**Exemple :**
```python
from railinsight.analysis.causes import analyze_causes
from railinsight.viz.charts import plot_causes

data = get_data()
causes = analyze_causes(data)
fig = plot_causes(causes)
st.plotly_chart(fig)  # ou st.pyplot(fig)
```

### 3️⃣ **Mettre en cache** (important!)

Streamlit réexécute tout à chaque interaction. Utilise `@st.cache_data` pour éviter de recharger les données :

```python
@st.cache_data
def get_data():
    return load_data(...)
```

## Pages selon le cadrage

Regarde [documentation/cadrage_question_directrice.md](../documentation/cadrage_question_directrice.md) pour les spécifications.

| Page | Contenu | Selon le cadrage |
|------|---------|-----------------|
| `main.py` | Accueil + explication | Section 5, "Accueil" |
| `01_retards.py` | Distribution par cause | Section 5, "D'où viennent les retards ?" |
| `02_liaisons.py` | Liaisons en difficulté | Section 5, "Liaisons en difficulté" |
| `03_saisons.py` | Saisonnalité | Section 5, "Saisons" |
| `04_ma_liaison.py` | Score de fiabilité | Section 5, "Ma liaison" |
| `05_donnees.py` | Datasheet + méthodologie | Section 5, "Données et limites" |

