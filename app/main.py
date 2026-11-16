"""Streamlit main app - RailInsight.

Point d'entrée : configure l'application et déclare les pages, dans l'ordre du
cadrage (section 5). Chaque page est un fichier de ``app/vues/``.
"""

from importlib.metadata import version

import streamlit as st

st.set_page_config(
    page_title="RailInsight - TGV Fiabilité", page_icon="🚄", layout="wide"
)

pages = {
    "": [
        st.Page("vues/accueil.py", title="Accueil", icon="🏠", default=True),
    ],
    "Analyses": [
        st.Page("vues/retards.py", title="D'où viennent les retards ?", icon="📊"),
        st.Page("vues/liaisons.py", title="Liaisons en difficulté", icon="🚨"),
        st.Page("vues/saisons.py", title="Saisons", icon="🌡️"),
        st.Page("vues/ma_liaison.py", title="Ma liaison", icon="🔍"),
    ],
    "Contexte": [
        st.Page("vues/donnees.py", title="Données et limites", icon="📋"),
    ],
}

st.sidebar.caption(f"RailInsight · version {version('iadata-700-projet')}")
st.navigation(pages).run()
