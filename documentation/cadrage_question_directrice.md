# RailInsight — Cadrage du projet

*Version du 10 octobre 2026*

## 1. Question directrice

> **D'où viennent les retards des TGV : du réseau, des trains ou d'aléas extérieurs ? Et que révèle ce découpage sur les liaisons durablement en difficulté et sur les saisons ?**

**Fil rouge** : comprendre l'origine des retards. C'est ce que l'application apporte au grand public : choisir *sa* liaison, voir son score de fiabilité, de quoi sont faits ses retards et comment ils évoluent.

**Ce qu'on mesure** : des causes *déclarées*. Elles sont attribuées par la SNCF, une seule par train (celle de la plus grosse perte de temps). L'étude est descriptive, sans conclusion causale.

## 2. Décisions validées

| Sujet | Décision |
| --- | --- |
| Unité d'observation | Une liaison × un mois (pas de donnée train par train) |
| Agrégation | Jamais de total réseau : un même train compte dans plusieurs liaisons. Vue d'ensemble = distribution des liaisons |
| Pondération | Toujours par le nombre de trains, jamais de moyenne de taux |
| Causes | Raisonner en contributions (taux de retard × part de la cause), pas en parts brutes |
| SNCF Réseau | `prct_cause_infra`, `prct_cause_gestion_trafic` |
| SNCF Voyageurs | `prct_cause_materiel_roulant`, `prct_cause_gestion_gare`, `prct_cause_prise_en_charge_voyageurs` |
| Externe | `prct_cause_externe` (inclut les grèves, non isolables) |
| Saisonnalité | Axe de lecture des causes, pas une catégorie de cause |
| Classes de comparaison | 3 classes de durée de trajet : < 1 h 30 (seuil 5 min), 1 h 30–3 h (10 min), > 3 h (15 min) |
| Grain du classement | Une valeur par liaison et par an, par classe de durée, petites liaisons exclues |
| « Durablement en difficulté » | Au-dessus du seuil (quartile supérieur, à confirmer sur la distribution) la majorité des années de la période de référence |
| Prédiction | Abandonnée : le brief demande de comprendre les causes structurelles |
| Liaisons internationales | Gardées ou non selon leur part du volume de trains, à mesurer |

## 3. Score de fiabilité (V1)

| Élément | Décision |
| --- | --- |
| Composantes | Part de trains en retard (seuil de la classe de durée), taux d'annulation, retard moyen de tous les trains (`retard_moyen_tous_trains_arrivee`) |
| Poids | Égaux : un tiers chacune. A documenter dans la datasheet, avec un test de sensibilité éventuellement |
| Normalisation | Rang de chaque composante à l'intérieur de la classe de durée |
| Période | Les 12 derniers mois |
| Causes | Toutes causes confondues (score « vécu » un retard est un retard) ; la part d'origine interne (Réseau + Voyageurs) est affichée à côté, sans entrer dans le calcul |
| Historique | Le score n'est pas tracé dans le temps (il est relatif). L'historique montre les 3 composantes en valeurs absolues, année par année |


## 4. Plan d'action par phase

### Phase 0 — Préparer les données

- Vérifier le schéma, la période couverte, les doublons, les faux codes (gare « 0 »).
- Contrôler les faux zéros des causes : la somme des six `prct_cause_*` doit valoir environ 100.
- Mesurer la part des liaisons internationales.
- Ouvrir la `DATASHEET.md` (7 sections) et y consigner chaque décision.

### Phase 1 — Découper les retards
- Pour chaque liaison : contributions Réseau / Voyageurs / Externe.
- Distribution des liaisons selon leur cause dominante.
- Test de robustesse : reclasser `prise_en_charge_voyageurs` et vérifier que la conclusion tient.

### Phase 2 — Les liaisons durablement en difficulté
- Distribution de l'indicateur de retard par classe de durée et par an.
- Choix du seuil et du volume minimal à partir de ces distributions.
- Sélection des liaisons sur une **période de référence**.
- Évolution sur la **période suivante**, à saison égale, et cause qui porte cette évolution.

### Phase 3 — Lecture par saison
- Contributions des trois groupes de causes par saisonnalité ou trimestre.

### Phase 4 — Score de fiabilité
- Calcul des 3 composantes sur les 12 derniers mois, rang dans la classe de durée, moyenne à poids égaux.
- Test de sensibilité aux poids : si les classements changent fortement, redéfinir les poids.
- Part d'origine interne calculée pour chaque liaison.
- Afficher les 3 composantes en mesure absolues pour nuancer le score de fiabilité.
- Le rang est calculé parmi les liaisons de durée comparable

## 5. Contenu de l'application

| Page | Question | Contenu |
| --- | --- | --- |
| Accueil | Pourquoi s'y intéresser ? | Question directrice, chiffres clés, source et licence |
| D'où viennent les retards ? | Réseau, trains ou aléas ? | Distribution des liaisons par cause dominante |
| Liaisons en difficulté | Lesquelles, et comment évoluent-elles ? | Classement par classe de durée, tendances, cause qui porte l'évolution |
| Saisons | Quand les retards apparaissent-ils, et pourquoi ? | Contributions des causes par saison ou trimestre |
| Ma liaison | Ma liaison est-elle fiable ? | Score de fiabilité + part d'origine interne, historique des 3 composantes, découpage des causes |
| Données et limites | Peut-on faire confiance aux chiffres ? | Datasheet résumée, interdiction du total réseau, causes déclarées, construction du score |

## 6. Points encore ouverts

- [ ] Seuil exact et volume minimal (après lecture des distributions).
- [ ] Bornes de la période de référence et de la période de suivi.
- [ ] Années atypiques (crise sanitaire, grèves) : gardées, signalées ou exclues.
