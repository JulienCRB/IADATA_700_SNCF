# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Permet à Sphinx de trouver le package `railinsight` depuis la racine du repo.
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'RailInsight'
copyright = '2026, RailInsight Team'
author = 'RailInsight Team'

version = '1.0.0'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Lit les docstrings au format Google.
    'sphinx.ext.viewcode',  # Ajoute des liens vers le code source.
    'sphinx.ext.githubpages',  # Génère le fichier .nojekyll pour GitHub Pages.
    'myst_parser',  # Permet d'inclure des fichiers Markdown (README, cadrage).
]

# Évite de ré-exécuter du code au moment du build (pas d'appel réseau/API SNCF).
autodoc_mock_imports = []

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

templates_path = ['_templates']
exclude_patterns = []

language = 'fr'

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
