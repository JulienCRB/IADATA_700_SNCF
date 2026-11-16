# Application Streamlit - RailInsight

## Structure

```
app/
├── main.py          ← Point d'entrée : configuration + menu (st.navigation)
├── utils.py         ← Chargement des données avec cache + petits formats d'affichage
└── vues/            ← Une page par fichier, déclarée dans main.py
    ├── accueil.py
    ├── retards.py
    ├── liaisons.py
    ├── saisons.py
    ├── ma_liaison.py
    └── donnees.py
```

Le dossier s'appelle `vues/` et non `pages/` : Streamlit transforme automatiquement
un dossier `pages/` en menu, ce qui entrerait en conflit avec `st.navigation`.

## Exécuter l'app

```bash
uv sync
uv run streamlit run app/main.py
```

Streamlit recharge les pages quand on les modifie, mais pas le package `railinsight` :
après une modification de `railinsight/`, relancez la commande.

## Ajouter une page

1. Créer `app/vues/ma_page.py`.
2. La déclarer dans `main.py`, dans la bonne section :
   `st.Page("vues/ma_page.py", title="Ma page", icon="📄")`.
3. Elle est testée automatiquement par `test/test_app.py` (elle doit démarrer sans
   erreur).

## Règle : l'app affiche, `railinsight/` calcule

Une page ne fait aucun calcul : elle récupère les données préparées, appelle une
méthode de `Regularite` et affiche le résultat avec un graphique de
`railinsight.viz.charts`. Tout nouveau calcul va dans `railinsight/`, avec un test.

```python
import streamlit as st
from utils import get_regularite

from railinsight.viz.charts import contributions_saison_bar

contributions = get_regularite().contributions_par_saison()
st.plotly_chart(contributions_saison_bar(contributions), width="stretch")
```

`get_regularite()` est mis en cache : les données SNCF ne sont téléchargées et
préparées qu'une fois pour toutes les pages.

## Pages selon le cadrage (section 5)

| Page | Fichier | Méthode de `Regularite` |
|------|---------|-------------------------|
| Accueil | `accueil.py` | `nb_liaisons`, `periode`, chiffres clés |
| D'où viennent les retards ? | `retards.py` | `contributions_par_liaison()` |
| Liaisons en difficulté | `liaisons.py` | `liaisons_en_difficulte()` |
| Saisons | `saisons.py` | `contributions_par_saison()` |
| Ma liaison | `ma_liaison.py` | `score_fiabilite()`, `historique_composantes()` |
| Données et limites | `donnees.py` | `periode` |
