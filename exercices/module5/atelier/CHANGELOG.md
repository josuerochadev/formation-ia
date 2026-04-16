# CHANGELOG — Atelier d'amélioration (M5E6)

Améliorations implémentées suite à la priorisation (`priorisation.md`). Toutes sont des modifications de prompts dans `fil-rouge/main.py` — aucun changement de code fonctionnel, aucun nouveau tool.

---

- **2026-04-16 — Clarifier le routing `search_web` vs `search_articles`** (`fil-rouge/main.py` — `SYSTEM_REACT`)
  *Quoi* : ajout d'une règle explicite "briefing / actus / dernières / récent / top N / tendances → **search_web**" + 4 exemples few-shot ("Briefing matinal 3 actus → search_web", "Archives ET actus → search_web", etc.).
  *Pourquoi* : Q07 et Q09 (LLM-as-Judge) scoraient 1.7/5 parce que l'agent routait "briefing matinal" vers `search_articles` (index RSS souvent vide) et répondait "rien trouvé" alors que `search_web` avait les données.

- **2026-04-16 — Instructions anti-hallucination / anti-acquiescement / transparence** (`fil-rouge/main.py` — `formuler_reponse`)
  *Quoi* : 5 règles impératives injectées dans le prompt de formulation : (1) ne JAMAIS inventer titre/URL/chiffre absent du résultat de l'outil, (2) corriger les fausses prémisses en citant la source, (3) proposer 2 interprétations au lieu d'inventer sur question ambiguë, (4) décrire honnêtement les vraies sources (RSS RAG + search web simulé 4 thèmes + SQLite), (5) respecter strictement le format demandé.
  *Pourquoi* : Q03 (ambigue, fidélité 1/5) inventait un titre d'article, Q06 (piège, fidélité 1/5) n'osait pas contredire une fausse affirmation sur les attaques cyber, Q05 (transparence, fidélité 1/5) inventait des liens et des sources. Tous ces cas montrent que le prompt générique "Formule une réponse claire" laisse le LLM remplir les vides.

- **2026-04-16 — Méta-description des sources réelles dans `SYSTEM_REACT`** (`fil-rouge/main.py`)
  *Quoi* : ajout d'un paragraphe "SOURCES RÉELLES DE L'AGENT" listant explicitement les 3 sources (RAG, search web simulé 4 catégories, SQLite) et précisant ce que l'agent **n'a pas** (bases académiques, APIs temps réel, sources payantes).
  *Pourquoi* : prévenir la tendance du LLM à inventer des sources au moment du routing (et par ricochet lors de la formulation si la requête porte sur la transparence — Q05).
