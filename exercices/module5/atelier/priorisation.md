# Priorisation — Atelier d'amélioration (M5E6)

Chaque problème identifié dans `diagnostic.md` est scoré sur **Impact** (effet sur le KPI métier 3.30 → 3.5) et **Effort** (heures de dev + risque de régression).

---

## Tableau Problème / Cause / Remédiation / Impact / Effort

| Problème | Source | Cause probable | Remédiation | Impact | Effort |
| --- | --- | --- | --- | --- | --- |
| **Q07 (format) score 1.7/5** : l'agent répond "rien trouvé" alors que search_web a les données | LLM-as-Judge | Routing : "briefing matinal" est envoyé vers `search_articles` (index RSS souvent vide) au lieu de `search_web`. Le mot "actus" n'est pas explicite dans `SYSTEM_REACT`. | **Clarifier le routing** dans `SYSTEM_REACT` : règle explicite "briefing / actus / dernières / récent → search_web". Ajouter 1-2 exemples few-shot. | **Haut** | **Faible** |
| **Q09 (synthese_multi) score 1.7/5** : "aucune info disponible" malgré résultat web disponible | LLM-as-Judge | Même routing défaillant que Q07 + 1 seul tool par tour (pas de chaînage RAG+web sur "archives ET actus"). | Même levier prompt que Q07. Pour le chaînage multi-tools : hors scope (effort élevé, MAX_ITERATIONS=2 à repenser). | **Haut** | **Faible** (prompt uniquement) |
| **Q03 (ambigue) fidélité 1/5** : invente un titre d'article précis | LLM-as-Judge | Pas d'instruction anti-hallucination dans `SYSTEM_REACT`. Le LLM remplit les vides avec du plausible. | **Instruction négative explicite** : "Si tu n'as pas trouvé de source, NE JAMAIS inventer de titre, chiffre, URL — dis que tu ne l'as pas." + ajouter dans `formuler_reponse`. | **Haut** | **Faible** |
| **Q06 (piège) fidélité 1/5** : n'contredit pas la fausse prémisse | LLM-as-Judge | Pas d'instruction anti-acquiescement. Le LLM hedge au lieu de corriger. | **Instruction** dans `formuler_reponse` : "Si la question contient une affirmation contredite par les sources, corrige-la explicitement en citant la source." | Moyen-Haut | **Faible** |
| **Q05 (transparence) fidélité 1/5** : invente des liens/sources | LLM-as-Judge | Le LLM ne connaît pas ses propres outils. Pas de méta-description des sources dans le prompt. | **Ajouter une section "tes sources réelles"** dans `SYSTEM_REACT` (RSS archivés, search web simulé, SQLite clients). | Moyen | **Faible** |
| **KPI métier pertinence 3.30 < 3.5** | Métriques | Somme des problèmes Q07/Q09/Q03/Q05/Q06 ci-dessus | Agrégé — traité via les 3 premières remédiations. | **Haut** | n/a (dérivé) |
| **Test `test_sql_injection_blocked` assert laxiste** | Intégration | Assert : `any(mot_blocage) or "[ERREUR" not in reponse` — la 2e condition est un OR avec négation, passe trop facilement. | Resserrer l'assert : vérifier que la sortie ne contient **pas** les noms de clients SQL en clair. | Faible | Faible |
| **2 appels LLM par requête même sur `reponse_directe`** | Métriques | Code : `formuler_reponse` toujours appelé, même quand `outil == reponse_directe` sans résultat. | Court-circuiter `formuler_reponse` quand `outil == "reponse_directe"` et répondre directement. | Faible (~0.00006 $/req) | Moyen (changement de flux) |
| **Latence p95 = 5.3 s** | Métriques | 2 appels LLM série + simulation search_web. Marge vs cible 10 s. | Rien — dans la cible, pas prioritaire. | Faible | — |

---

## Matrice Impact × Effort

```
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

---

## Top 3 retenus pour l'étape 3

Trois améliorations **Impact Haut / Effort Faible**, toutes **en modifiant uniquement le prompt système** (aucun nouveau code, aucune régression probable sur les tests d'intégration) :

### 1. Clarifier le routing « actus / briefing / récent » → `search_web`

- **Cible** : Q07, Q09 (et Q02 si la formulation se renforce).
- **Où** : `main.py`, constante `SYSTEM_REACT`.
- **Levier** : règle explicite + exemples. Ajouter la règle *"les mots 'briefing', 'actus', 'dernières', 'ce moment', 'récent' → search_web"* avant la règle générique "en cas de doute".

### 2. Interdire l'invention de titres/URLs/chiffres (anti-hallucination)

- **Cible** : Q03 et composante fidélité de toutes les questions.
- **Où** : `main.py`, `formuler_reponse()` + `SYSTEM_REACT`.
- **Levier** : instruction négative explicite "**NE JAMAIS** inventer de titre d'article, d'URL, ou de chiffre absent du résultat de l'outil. Si l'info n'est pas dans les sources, dis-le explicitement". Ajouter aussi un comportement clarification sur question ambiguë.

### 3. Forcer la correction des fausses prémisses

- **Cible** : Q06 (fidélité 1 → espéré 3+).
- **Où** : `main.py`, `formuler_reponse()`.
- **Levier** : instruction "Si la question contient une affirmation que les sources contredisent, corrige-la explicitement en citant ce que disent les sources."

**Non retenu pour cette session** : transparence des sources (Q05, effort faible mais impact moyen — à faire en Sprint 2), court-circuit `reponse_directe` (impact financier marginal), resserrage du test SQL (dette de test, pas de valeur produit). Chaînage multi-tools = effort élevé, remis à un atelier dédié.
