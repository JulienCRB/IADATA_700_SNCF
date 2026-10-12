"""Utilitaires Streamlit - RailInsight"""
import streamlit as st
from railinsight.data.loader import load_data
from railinsight.analysis.causes import analyze_causes
from railinsight.analysis.reliability import compute_reliability_score


def get_data():
    """Charge les données (une seule fois, mise en cache)."""
    return load_data("data/1_raw/regularite-mensuelle-tgv-aqst.csv")


def get_causes_analysis(data):
    """Analyse les causes de retard."""
    return analyze_causes(data)


def get_reliability_scores(data):
    """Calcule les scores de fiabilité."""
    return compute_reliability_score(data)
