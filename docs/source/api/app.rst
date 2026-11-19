app namespace
=============

.. py:module:: app

.. note::
   Les pages de l'application (``app/vues/``) sont des scripts Streamlit
   qui s'exécutent uniquement via ``streamlit run app/main.py`` : elles
   utilisent des imports relatifs (``from utils import ...``) propres au
   contexte Streamlit et ne peuvent pas être importées isolément par
   Sphinx. Seul le module utilitaire ``app.utils``, réutilisable et
   testé indépendamment, est documenté ici.

Submodules
----------

.. toctree::
   :maxdepth: 4

   app.utils
