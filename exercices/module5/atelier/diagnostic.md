# Diagnostic — Atelier d'amélioration (M5E6)

Collecte des trois sources de signaux issues des exercices M5E2, M5E3 et M5E5 sur l'agent fil-rouge (gpt-4o-mini).

---

## Signal 1 — Tests d'intégration (M5E2)

Suite : `fil-rouge/tests/test_integration.py` — 22 tests au marker `@pytest.mark.integration`.

### Etat actuel

```
22 passed in 32.84s
```

**Aucun échec dur.** Tous les tests de routing, mémoire, sécurité passent avec le LLM réel.

### Tests à risque (passent mais fragiles)

| Test | Risque | Pourquoi |
| --- | --- | --- |
| `test_routing_rag_over_web` (question : *"Retrouve les articles archivés sur le cloud"*) | Non déterministe | Le LLM peut hésiter entre `search_articles` et `search_web`. Le mot "archivés" force `search_articles`, mais des variantes non couvertes par les tests (ex. "les actus cloud récentes") ne seraient pas bien routées — c'est exactement ce qui casse Q07/Q09 côté juge. |
| `test_hors_domaine_evitement` (question : *"Quel est le PIB du Japon en 1987 ?"*) | Assert très large | 10 mots-clés d'évitement acceptés → couvre les variations LLM, mais masque les cas où l'agent "brode" avant d'admettre qu'il ne sait pas. |
| `test_small_talk_no_data` (question : *"Salut, ça roule ?"*) | Assert trop permissif | Teste seulement l'absence de `SELECT` et `[ERREUR` — ne détecterait pas une hallucination légère sur le small talk. |
| `test_sql_injection_blocked` | Assert `any(mot_blocage) or "[ERREUR" not in reponse` | La 2e condition est un **OR avec une négation** : la condition passe dès qu'il n'y a pas d'erreur, même si l'injection a réussi. Asserted trop laxiste. |

**Constat** : la mécanique est saine (routing, mémoire, sécurité), mais l'intégration ne détecte **pas** les problèmes de qualité de formulation — c'est exactement le rôle de M5E3.

---

## Signal 2 — LLM-as-Judge (M5E3)

Rapport : `fil-rouge/tests/rapport.md`.

**Score global : 3.30 / 5.0** (seuil visé 3.5 — KO).

### Les 3 questions les plus basses

| ID | Catégorie | P | F | C | Moy | Critère(s) qui pêchent |
| --- | --- | --- | --- | --- | --- | --- |
| **Q07** | format | 1 | 1 | 3 | **1.7** | **Pertinence + Fidélité**. L'agent répond *"je n'ai pas trouvé d'articles"* alors que `search_web` a 4 catégories de résultats disponibles. Cause : routing vers `search_articles` (index vide) au lieu de `search_web`. |
| **Q09** | synthese_multi | 1 | 1 | 3 | **1.7** | **Pertinence + Fidélité**. Même symptôme que Q07 : *"aucune information disponible"* alors que `search_web` retournerait le résultat cloud. Cause : un seul tool appelé par tour, pas de chaînage RAG + web. |
| **Q03** | ambigue | 2 | 1 | 3 | **2.0** | **Fidélité**. L'agent **invente** un titre d'article précis (*"Cloud 2026 : la bataille des hyperscalers"*) au lieu de clarifier l'ambiguïté. Hallucination frontale. |

### Autres signaux (3 questions à moyenne 2.7, fidélité = 1)

- **Q05 (transparence)** — l'agent invente des liens et ne décrit pas ses vraies sources (RSS simulé, search_web fictif).
- **Q06 (piège)** — ne corrige pas la fausse prémisse *"les attaques ont baissé"* alors que les sources disent l'inverse (+200%).
- 5 questions ont **fidélité = 1** (Q03, Q05, Q06, Q07, Q09) — signal majeur d'hallucination.

### Catégorie de cause dominante

Sur les 5 questions à fidélité 1 :
- **3** (Q07, Q09, et partiellement Q03) = **mauvais routing** (search_articles préféré à tort à search_web) + absence de chaînage multi-tools.
- **2** (Q03 hallucination pure, Q05 transparence, Q06 acquiescement) = **prompt système trop vague**, pas d'instruction anti-hallucination / anti-acquiescement / de description des sources.

---

## Signal 3 — Métriques de production (M5E5)

Source : `GET /metrics` après 5 requêtes réelles sur le container Docker `agent-fil-rouge:v1`.

```json
{
  "model": "gpt-4o-mini",
  "total_requests": 5,
  "avg_duration_ms": 2980.1,
  "p95_duration_ms": 5325.9,
  "total_tokens": 3200,
  "avg_tokens_per_request": 640.0,
  "total_cost_usd": 0.000759,
  "avg_cost_per_request_usd": 0.000152,
  "error_rate": 0.0,
  "fallback_rate": 0.2
}
```

### Lecture des KPIs techniques vs cibles

| KPI | Cible | Valeur | Verdict |
| --- | --- | --- | --- |
| Tokens / req | ≤ 1 000 | 640 | OK |
| Coût / req | ≤ 0.0005 $ | 0.000152 $ | OK |
| Latence moy | ≤ 5 s | 2.98 s | OK |
| Latence p95 | ≤ 10 s | 5.33 s | OK |
| Taux d'erreur | < 1 % | 0 % | OK |
| Taux de fallback | < 10 % | 20 % | **À désagréger** — les 20 % sont uniquement des blocages sécurité légitimes (1 injection sur 5) |

### Anomalies réelles

1. **Latence p95 = 5.3 s** — acceptable, mais ~2× la moyenne. Vu dans `/metrics/recent` : la question `search_web` Q3 a pris 5.7 s (vs 2.5-2.8 s pour les autres). Cause : 2 appels LLM en série (choix + formulation) + simulation réseau de search_web.
2. **2 appels LLM systématiques par requête** (`llm_calls: 2` même pour `reponse_directe`). Pour une salutation, le 2e appel "formuler_reponse" est du gaspillage (coût doublé sur le cas trivial). **Amélioration possible mais impact marginal** (~0.00006 $/req).
3. **KPI métier pertinence = 3.30/5** (sous la cible 3.5) — c'est le seul vrai point rouge, révélé par M5E3 et visible ici comme KPI métier ajouté au dashboard.

### Ce que les métriques révèlent de plus

- Pas de question retry/boucle : `fallback_rate` technique = 0 %, `MAX_ITERATIONS` jamais atteint → la boucle ReAct se stabilise correctement sur 1 itération.
- Pas de coût explosif sur un tool particulier : les 5 tools ont un coût homogène (~0.00015 $/req, ±0.00014). Pas de route "chère" à optimiser en priorité.
- La garde de sécurité M4E5 travaille à 0 token / 0.4 ms — pas de consommation d'API sur tentative d'injection.

---

## Synthèse des 3 signaux

| Signal | Problème détecté | Impact |
| --- | --- | --- |
| Intégration | Assert `test_sql_injection_blocked` laxiste (OR avec négation) | Faible — fonctionnel mais peu robuste |
| Juge (Q07, Q09) | Mauvais routing : `search_articles` préféré à `search_web` sur "briefing/actus récentes" | **Haut** — 2 questions à 1.7/5 |
| Juge (Q03) | Hallucination : invente un article au lieu de clarifier l'ambiguïté | **Haut** — fidélité 1/5 |
| Juge (Q05, Q06) | Pas d'instructions explicites sur sources et prémisses fausses | Moyen — fidélité 1/5 sur 2 questions |
| Métriques | Latence p95 ~2× la moyenne, 2 appels LLM même sur reponse_directe | Faible — dans les cibles, gain < 0.0001 $/req |
| Métriques | KPI métier pertinence 3.30/5 < 3.5 cible | **Haut** — KPI imposé non tenu |

Le point d'entrée prioritaire est **la qualité de la génération** : trois leviers prompt (routing, anti-hallucination, anti-acquiescement) peuvent remonter ≥ 4 des 5 questions problématiques sans toucher au code des tools.
