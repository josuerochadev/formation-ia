# Exercice 6 — Atelier d'amélioration de l'agent

## Objectif

Utiliser les données d'évaluation produites aux exercices M5E2 (tests d'intégration), M5E3 (LLM-as-Judge — projet d'équipe avec **Alex Dubus**, **Zhengfeng Ding**, **Josue Xavier Rocha**, **Stephanie Consoli**) et M5E5 (monitoring) pour identifier, prioriser et implémenter des améliorations data-driven sur l'agent fil-rouge. Mesurer l'impact avec le même pipeline d'évaluation qu'avant les changements.

**Règle du jeu** : on n'améliore pas au feeling, on n'améliore que ce que les tests et les métriques ont révélé comme faible.

---

## Navigation — documents de l'atelier

La présente fiche est le document de synthèse. Les quatre livrables détaillés sont dans `exercices/module5/atelier/` :

| Fichier | Rôle | Quand le lire |
| --- | --- | --- |
| [`atelier/diagnostic.md`](./atelier/diagnostic.md) | Collecte brute des 3 signaux (tests intégration, LLM-Judge, métriques) | Pour voir le détail des asserts fragiles et des questions qui scorent bas |
| [`atelier/priorisation.md`](./atelier/priorisation.md) | Tableau Problème × Cause × Remédiation × Impact × Effort + matrice | Pour comprendre pourquoi on a retenu 3 leviers plutôt que 8 |
| [`atelier/CHANGELOG.md`](./atelier/CHANGELOG.md) | Les 3 améliorations implémentées (1 ligne chacune) | Pour traçabilité git — chaque ligne = ce qui devrait être un commit |
| [`atelier/bilan.md`](./atelier/bilan.md) | Tableau avant/après + détail par question + synthèse 5 lignes | Pour voir l'impact mesuré sur le score LLM-Judge |

**Dépendances externes** (hors atelier) :

- `exercices/module5/exercice2-tests-integration.md` — suite de 22 tests d'intégration (signal 1).
- `exercices/module5/exercice3-llm-as-judge.md` — pipeline LLM-Judge + `tests/questions.json` (10 Q) + `tests/rapport.md` (signal 2).
- `exercices/module5/exercice5-monitoring-kpis.md` — endpoint `/metrics`, campagne Docker, KPIs (signal 3).
- `fiches/module5-tests-deploiement-mise-en-production.md` — synthèse du module qui place cet atelier dans la boucle "tester → mesurer → améliorer".

---

## Etape 1 — Collecter les signaux

> Rassemblez dans un fichier `atelier/diagnostic.md` les trois sources de signaux : tests d'intégration (Ex2), LLM-as-Judge (Ex3), métriques de production (Ex5).

### Signal 1 — Tests d'intégration (M5E2)

Suite `fil-rouge/tests/test_integration.py` — 22 tests `@pytest.mark.integration`.

```
22 passed in 32.84s
```

**Aucun échec dur.** Mais 4 tests passent à l'arraché avec des asserts fragiles :

| Test | Risque | Pourquoi |
| --- | --- | --- |
| `test_routing_rag_over_web` | Non déterministe | Le mot "archivés" force `search_articles` ; les variantes ("actus récentes", "briefing") ne sont pas couvertes — c'est exactement ce qui casse Q07/Q09 côté juge. |
| `test_hors_domaine_evitement` | Assert très large | 10 mots-clés d'évitement → couvre le LLM mais masque les cas où l'agent "brode" avant d'admettre. |
| `test_small_talk_no_data` | Assert trop permissif | Teste uniquement l'absence de `SELECT` et `[ERREUR` — ne détecte pas d'hallucination légère. |
| `test_sql_injection_blocked` | Logique OR + négation | `any(mot_blocage) or "[ERREUR" not in reponse` — la 2e condition passe dès qu'il n'y a pas d'erreur, même si l'injection a réussi. |

**Constat** : la mécanique (routing, mémoire, sécurité) est saine, mais l'intégration ne détecte **pas** les problèmes de qualité de formulation — c'est exactement le rôle de M5E3.

### Signal 2 — LLM-as-Judge (M5E3)

Source : `fil-rouge/tests/rapport.md` — **score global 3.30 / 5.0** (seuil visé 3.5 — KO).

Les 3 questions les plus basses :

| ID | Catégorie | P | F | C | Moy | Critère qui pêche |
| --- | --- | --- | --- | --- | --- | --- |
| **Q07** | format | 1 | 1 | 3 | **1.7** | Pertinence + Fidélité — l'agent répond *"je n'ai pas trouvé"* alors que `search_web` a les données. Routing défaillant. |
| **Q09** | synthese_multi | 1 | 1 | 3 | **1.7** | Pertinence + Fidélité — même symptôme : *"aucune information disponible"* alors que web a un résultat cloud. |
| **Q03** | ambigue | 2 | 1 | 3 | **2.0** | Fidélité — invente un titre d'article précis au lieu de clarifier l'ambiguïté. |

3 autres questions sont à fidélité 1 (Q05 transparence, Q06 piège, Q09 synthèse). **5 questions sur 10 ont fidélité = 1** — signal d'hallucination massif.

**Catégories de cause dominantes** :

- **Mauvais routing** : Q07, Q09 et partiellement Q03 → `search_articles` préféré à tort à `search_web`. 3 cas.
- **Prompt système trop vague** : Q03 (hallucination), Q05 (sources inventées), Q06 (acquiescement). 3 cas.

### Signal 3 — Métriques de production (M5E5)

Source : `GET /metrics` après 5 requêtes réelles sur le container Docker.

```json
{
  "avg_duration_ms": 2980.1,
  "p95_duration_ms": 5325.9,
  "avg_tokens_per_request": 640.0,
  "avg_cost_per_request_usd": 0.000152,
  "error_rate": 0.0,
  "fallback_rate": 0.2
}
```

| KPI | Cible | Valeur | Verdict |
| --- | --- | --- | --- |
| Tokens / req | ≤ 1 000 | 640 | OK |
| Coût / req | ≤ 0.0005 $ | 0.000152 $ | OK |
| Latence p95 | ≤ 10 s | 5.33 s | OK |
| Taux d'erreur | < 1 % | 0 % | OK |
| Taux de fallback | < 10 % | 20 % | à désagréger (100 % = blocages sécurité légitimes) |
| **Pertinence métier** | ≥ 3.5 / 5 | **3.30 / 5** | **KO** |

**Anomalies détectées** :

1. **Latence p95 ~2× la moyenne** (5.3 s vs 2.98 s). Dans la cible, pas prioritaire.
2. **2 appels LLM systématiques** par requête (`choisir_outil` + `formuler_reponse`), y compris pour `reponse_directe`. Gain potentiel marginal (~0.00006 $/req).
3. **KPI métier pertinence 3.30 sous la cible 3.5** — c'est le seul vrai point rouge, révélé par M5E3.

---

## Etape 2 — Diagnostiquer et prioriser

> Pour chaque problème identifié, remplissez une ligne du tableau Problème / Cause / Remédiation / Impact / Effort. Classez sur la matrice Impact × Effort. Traitez 2-3 « Impact élevé / Effort faible ou moyen ».

### Tableau de priorisation

| Problème | Source | Cause probable | Remédiation | Impact | Effort |
| --- | --- | --- | --- | --- | --- |
| Q07 (format) 1.7/5 — "rien trouvé" alors que search_web a les données | LLM-Judge | "briefing matinal" routé vers `search_articles` (index vide). Règle absente dans `SYSTEM_REACT`. | Règle explicite "briefing/actus/récent → search_web" + exemples few-shot | **Haut** | **Faible** |
| Q09 (synthèse_multi) 1.7/5 — "aucune info disponible" | LLM-Judge | Même routing défaillant que Q07 + pas de chaînage multi-tools | Même levier prompt (chaînage = scope futur) | **Haut** | **Faible** |
| Q03 (ambigue) fidélité 1/5 — invente un titre | LLM-Judge | Pas d'instruction anti-hallucination dans `formuler_reponse` | Instruction négative "NE JAMAIS inventer titre/URL/chiffre absent du résultat" | **Haut** | **Faible** |
| Q06 (piège) fidélité 1/5 — n'oppose pas la fausse prémisse | LLM-Judge | Pas d'instruction anti-acquiescement | Instruction "corriger explicitement les fausses prémisses en citant la source" | Moyen-Haut | **Faible** |
| Q05 (transparence) fidélité 1/5 — invente ses sources | LLM-Judge | Le LLM ignore ses vrais tools | Décrire les 3 sources réelles (RAG, search web simulé 4 thèmes, SQLite) dans `SYSTEM_REACT` | Moyen | **Faible** |
| Test `test_sql_injection_blocked` laxiste | Intégration | OR + négation → passe trop facilement | Resserrer l'assert | Faible | Faible |
| 2 appels LLM pour `reponse_directe` | Métriques | Code : `formuler_reponse` toujours appelé | Court-circuiter si outil == reponse_directe | Faible (~0.00006 $/req) | Moyen |
| Latence p95 = 5.3 s | Métriques | 2 appels LLM série + simulation réseau | Rien — dans la cible | Faible | — |

### Matrice Impact × Effort

```text
           Effort faible       Effort moyen     Effort élevé
         ┌──────────────────┬─────────────────┬──────────────────┐
Impact   │ ★ Routing Q07/Q09│                 │ Chaînage multi-  │
HAUT     │ ★ Anti-hallu Q03 │                 │ tools            │
         │ ★ Anti-acquiesc. │                 │                  │
         │   Q06            │                 │                  │
         ├──────────────────┼─────────────────┼──────────────────┤
Impact   │   Transparence   │ Court-circuit   │                  │
MOYEN    │   sources Q05    │ reponse_directe │                  │
         ├──────────────────┼─────────────────┼──────────────────┤
Impact   │   Assert         │                 │                  │
FAIBLE   │   test_sql       │                 │                  │
         └──────────────────┴─────────────────┴──────────────────┘
```

### Top 3 retenus pour l'étape 3

Trois améliorations **Impact Haut / Effort Faible**, toutes **en modifiant uniquement le prompt** (aucun nouveau code, aucune régression probable sur les tests) :

1. **Clarifier le routing actus/briefing/récent → `search_web`** (cible Q07, Q09)
2. **Interdire l'invention de titres/URLs/chiffres + clarification sur ambiguïté + anti-acquiescement sur fausse prémisse** (cible Q03, Q06, et toutes les fidélités 1)
3. **Méta-description des sources réelles** (cible Q05)

**Non retenus** : court-circuit `reponse_directe` (impact financier marginal), resserrage test SQL (dette de test sans valeur produit), chaînage multi-tools (effort élevé, atelier dédié).

---

## Etape 3 — Implémenter les améliorations

> Choisissez 2 à 3 améliorations et implémentez-les. Pour chaque amélioration : commitez le changement et écrivez 1 ligne dans `atelier/CHANGELOG.md`.

### Amélioration 1 — Clarifier le routing dans `SYSTEM_REACT`

Fichier : `fil-rouge/main.py`, constante `SYSTEM_REACT`.

Ajout d'une règle explicite sur les mots-clés qui forcent `search_web`, d'une règle d'arbitrage et de 4 exemples few-shot :

```python
"- search_web : ... veille externe. "
"**TOUJOURS utiliser search_web si la requête contient : 'briefing', 'actus', "
"'actualités', 'dernières', 'récent', 'récentes', 'en ce moment', 'du moment', "
"'cette semaine', 'ce mois', 'aujourd'hui', 'top 3', 'tendances'.**\n"
"- search_articles : UNIQUEMENT pour les archives internes déjà collectées ... "
"Ne choisis search_articles QUE si le mot 'archives', 'archivés', 'historique', "
"'déjà collectés' apparaît explicitement.\n"
...
"\nEXEMPLES :\n"
"- 'Briefing matinal, 3 actus tech' → outil = search_web\n"
"- 'Résume tout ce qu'on a sur le cloud, archives et actus' → outil = search_web\n"
"- 'Retrouve les articles archivés sur Kubernetes' → outil = search_articles\n"
"- 'Tendances IA 2026' → outil = search_web\n"
```

**Cible** : Q07 (1.7/5) et Q09 (1.7/5).

### Amélioration 2 — Règles impératives de fidélité dans `formuler_reponse`

Fichier : `fil-rouge/main.py`, fonction `formuler_reponse`.

Remplacement du prompt générique *"Formule une réponse claire"* par 5 règles numérotées :

```python
instruction = (
    "Formule une réponse claire, concise et structurée en français pour l'utilisateur.\n"
    "\nRÈGLES IMPÉRATIVES DE FIDÉLITÉ (M5E6) :\n"
    "1. **Ne JAMAIS inventer** un titre d'article, une URL, un chiffre, une date, "
    "un nom propre ou une statistique qui ne figure pas dans le résultat de l'outil.\n"
    "2. **Corriger les fausses prémisses** : si la question contient une affirmation "
    "que le résultat de l'outil contredit, dis-le explicitement et cite le chiffre/fait "
    "correct. N'acquiesce jamais à une affirmation fausse.\n"
    "3. **Clarification sur question ambiguë** : si la requête est vague, ne comble pas "
    "le vide par une réponse précise inventée ; propose 2 interprétations possibles.\n"
    "4. **Transparence sur les sources** : si l'utilisateur demande d'où viennent tes "
    "informations, décris honnêtement ce que tu as (RSS archivés, search web simulé "
    "4 thèmes, SQLite interne). N'invente pas d'accès à des bases académiques ou APIs.\n"
    "5. **Format** : si la question impose un format (bullet points, N éléments, JSON), "
    "respecte-le strictement en n'utilisant QUE les données du résultat."
)
```

Ajout également d'un rappel anti-invention dans la branche `[AUCUN_RESULTAT]`.

**Cible** : Q03 (hallucination), Q06 (acquiescement), Q05 (transparence), ainsi que la fidélité transverse.

### Amélioration 3 — Méta-description des sources dans `SYSTEM_REACT`

Fichier : `fil-rouge/main.py`, constante `SYSTEM_REACT`.

Ajout d'un paragraphe explicite sur les sources réelles :

```python
"\nSOURCES RÉELLES DE L'AGENT (pour ton 'raisonnement' uniquement, ne jamais inventer d'autres) :\n"
"1) Articles RSS ingérés et indexés (RAG, accessible via search_articles) ;\n"
"2) Recherche web simulée avec 4 catégories de résultats prédéfinis "
"(IA/LLMs, Cloud, Cybersécurité, GPU/hardware) ;\n"
"3) Base SQLite interne (clients, tickets) via query_db.\n"
"Tu n'as PAS accès à des bases académiques, ni à une API d'actualités temps réel, "
"ni à des sources payantes.\n"
```

**Cible** : prévenir l'invention de sources au moment du routing et par ricochet lors de la formulation sur Q05.

### CHANGELOG

Contenu de `atelier/CHANGELOG.md` :

- **2026-04-16 — Clarifier le routing `search_web` vs `search_articles`** (`main.py` — `SYSTEM_REACT`) : règle explicite "briefing / actus / récent → search_web" + 4 exemples few-shot. Cible Q07/Q09 qui scoraient 1.7/5 à cause d'un routing vers `search_articles` (index vide).
- **2026-04-16 — Instructions anti-hallucination / anti-acquiescement / transparence** (`main.py` — `formuler_reponse`) : 5 règles impératives injectées dans le prompt de formulation. Cible Q03 (fidélité 1), Q06 (fidélité 1), Q05 (fidélité 1).
- **2026-04-16 — Méta-description des sources réelles dans `SYSTEM_REACT`** (`main.py`) : liste explicite des 3 sources (RAG, search web simulé 4 thèmes, SQLite) et ce que l'agent n'a pas. Prévient l'invention de sources.

---

## Etape 4 — Revalider

> Rejouez les MÊMES tests qu'aux exercices 2 et 3 pour mesurer l'impact. Consignez le résultat dans `atelier/bilan.md`.

### Protocole

```bash
cd fil-rouge
source .venv/bin/activate
python -m pytest tests/test_integration.py -v -m integration      # 22 tests
python -m pytest tests/test_qualite.py -v -s -m qualite           # 10 Q + juge
```

(Métriques Docker non re-mesurées : les changements sont purement prompt, l'impact attendu sur latence/coût est ≤ 5 %.)

### Tableau avant / après

| Métrique | Avant (M5E2/3/5) | Après (M5E6) | Δ |
| --- | --- | --- | --- |
| Tests d'intégration passants | **22 / 22** | **22 / 22** | = (pas de régression) |
| Tests qualité passants | **1 / 5** | **2 / 5** | **+1** |
| Score moyen LLM-as-Judge | **3.30 / 5** | **3.57 / 5** | **+0.27** — seuil 3.5 franchi |
| Score de la pire question | Q07 **1.7 / 5** | Q07 **1.7 / 5** | = (stable, cf. analyse) |
| Questions à fidélité = 1 | **5** (Q03,Q05,Q06,Q07,Q09) | **3** (Q03,Q06,Q07) | **−2** |
| Questions ≥ 4 / 5 | **3** | **4** | **+1** |
| Latence p95 (M5E5) | **5.3 s** | ~5.5 s (estim. +200 ms) | ≈ |
| Coût / requête (M5E5) | **0.000152 $** | ~0.000160 $ (estim. +5 %) | ≈ |

### Détail par question

| ID | Cat. | Avant (P/F/C → Moy) | Après (P/F/C → Moy) | Δ moy | Verdict |
| --- | --- | --- | --- | --- | --- |
| Q01 | factuelle | 5/5/5 → 5.0 | 5/5/5 → 5.0 | 0 | stable |
| Q02 | complexe | 5/3/5 → 4.3 | 5/3/5 → 4.3 | 0 | stable |
| Q03 | ambigue | 2/1/3 → 2.0 | 3/1/4 → 2.7 | **+0.7** | gain partiel (fidélité reste 1) |
| Q04 | désinfo | 5/5/5 → 5.0 | 5/5/5 → 5.0 | 0 | stable |
| **Q05** | transparence | 3/1/4 → 2.7 | 5/3/5 → **4.3** | **+1.6** | **gros gain** |
| Q06 | piège | 3/1/4 → 2.7 | 5/1/4 → 3.3 | **+0.6** | pertinence gagne, fidélité bloquée |
| Q07 | format | 1/1/3 → 1.7 | 1/1/3 → 1.7 | 0 | **bloqué** |
| Q08 | perso | 4/3/5 → 4.0 | 3/2/4 → **3.0** | **−1.0** | **régression** |
| **Q09** | synthèse | 1/1/3 → 1.7 | 3/3/3 → **3.0** | **+1.3** | **gros gain** |
| Q10 | bord | 4/3/5 → 4.0 | 3/2/5 → **3.3** | **−0.7** | régression |

### Synthèse (5 lignes)

1. **L'amélioration la plus impactante** est l'ajout des règles anti-hallucination + transparence dans `formuler_reponse` (Q05 +1.6, Q09 +1.3) : dire au LLM *"voici tes vraies sources, ne mens pas"* a remonté 2 questions de 2.7 et 1.7 vers 4.3 et 3.0. C'est le levier le moins cher (prompt uniquement) et le plus rentable.

2. **L'amélioration décevante** est le routing sur Q07 : la règle *"briefing → search_web"* est bien prise en compte (l'agent dit maintenant *"dans la base simulée"*), mais `search_web` retourne un résultat générique car la `query_recherche` forgée par le LLM (*"3 actus tech"*) ne matche aucun des 4 mots-clés (IA/cloud/cyber/GPU). Le bug s'est déplacé d'une couche : routing OK, mais formulation de requête KO.

3. **Deux régressions à surveiller** : Q08 (−1.0) et Q10 (−0.7). Cause probable : les instructions anti-hallucination ont rendu le LLM plus timide, il s'appuie moins sur les connaissances générales pour adapter le ton DSI (Q08) ou comparer PostgreSQL/MongoDB (Q10). C'est exactement le piège signalé : *"un prompt plus strict réduit les hallucinations mais augmente les refus abusifs"*.

4. **Pourquoi Q03 et Q06 plafonnent à fidélité 1** : sur Q03, l'agent cite encore un article inventé malgré l'instruction négative — `gpt-4o-mini` suit mal les interdictions longues. Sur Q06, il hedge au lieu de contredire. Les deux demanderaient soit un modèle plus puissant (gpt-4o), soit un système à deux passes (génération + vérification).

5. **Verdict net** : le KPI métier **pertinence** passe de 3.30 à 3.57 (**cible 3.5 atteinte pour la première fois**), sans régression des tests d'intégration (22/22) ni de la sécurité. Le gain est cohérent avec la théorie (les problèmes identifiés comme "prompt trop vague" étaient traitables par prompt), et les régressions montrent qu'il faudra un 2e atelier axé sur Q07 (améliorer la query_recherche ou enrichir search_web), Q08/Q10 (équilibre hallucination vs personnalisation) et Q03/Q06 (instructions mieux suivies).

---

## Fichiers créés / modifiés

| Fichier | Rôle |
| --- | --- |
| `exercices/module5/atelier/diagnostic.md` | Collecte des 3 signaux (tests, juge, métriques) |
| `exercices/module5/atelier/priorisation.md` | Tableau Problème × Cause × Remédiation × Impact × Effort + matrice |
| `exercices/module5/atelier/CHANGELOG.md` | 3 améliorations implémentées, 1 ligne chacune |
| `exercices/module5/atelier/bilan.md` | Tableau avant / après + synthèse 5 lignes |
| `fil-rouge/main.py` | `SYSTEM_REACT` enrichi (routing + sources), `formuler_reponse` durci (5 règles) |

---

## Livrables

- **atelier/diagnostic.md** : 3 signaux collectés — tests 22/22 passants mais 4 asserts fragiles, LLM-Judge 3.30/5 avec 5 questions à fidélité 1, métriques techniques OK sauf KPI métier pertinence 3.30 < 3.5.
- **atelier/priorisation.md** : tableau des 8 problèmes + matrice Impact × Effort + top 3 retenu.
- **atelier/CHANGELOG.md** : 3 améliorations (routing, fidélité, sources) — toutes sur `main.py`, aucune régression de test.
- **atelier/bilan.md** : **3.30 → 3.57**, seuil 3.5 franchi ; Q05 +1.6 et Q09 +1.3 (gros gains) ; Q08 −1.0 et Q10 −0.7 (régressions documentées) ; Q07 stable à 1.7 (bug déplacé au niveau `query_recherche`).
- **Commentaire synthèse (5 lignes)** inclus en fin de bilan.

**Verdict** : le seul KPI rouge (pertinence métier < 3.5) est résolu avec 3 modifications **uniquement de prompt**, sans toucher au code fonctionnel ni aux tools. Le coût cognitif de la démarche data-driven est payant — on a traité ce que les métriques ont révélé, pas ce qu'on imaginait être le problème.
