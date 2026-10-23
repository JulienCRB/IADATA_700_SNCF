"""Streamlit main app - RailInsight."""

import streamlit as st

st.set_page_config(
    page_title="RailInsight - TGV Fiabilité", page_icon="🚄", layout="wide"
)

st.title("🚄 RailInsight - Comprendre les retards des TGV")

st.markdown("""
### Bienvenue sur RailInsight

Cette application explore la fiabilité du réseau TGV français et comprend
l'origine des retards : réseau, trains ou aléas extérieurs.

**Navigue dans les pages pour :**
- Voir d'où viennent les retards
- Découvrir les liaisons en difficulté
- Comprendre la saisonnalité
- Analyser ta liaison préférée
- Consulter la datasheet et méthodologie
""")
