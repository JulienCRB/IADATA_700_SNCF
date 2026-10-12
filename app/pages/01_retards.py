"""Page 1: D'où viennent les retards?"""
import streamlit as st

st.title("📊 D'où viennent les retards ?")

st.markdown("""
Cette page montre la **distribution des liaisons** selon leur cause dominante.

- **Réseau** (infrastructure, gestion du trafic)
- **Trains** (matériel roulant, gestion en gare, prise en charge voyageurs)  
- **Externe** (causes externes, grèves)
""")

# TODO: Ajouter le code d'analyse depuis railinsight.analysis
