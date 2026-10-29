"""Utilitaires Streamlit - RailInsight."""

import pandas as pd
import streamlit as st

from railinsight.data.loader import REGULARITE, load


@st.cache_data
def get_data() -> pd.DataFrame:
    """Charge les données de régularité TGV (mises en cache)."""
    return load(REGULARITE)
