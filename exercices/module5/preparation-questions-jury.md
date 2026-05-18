# Preparation questions jury — Soutenance Luciole

Document de revision : questions probables du formateur classees par module, avec reponses preparees appliquees au projet Luciole.

---

## Module 1 — Fondamentaux IA & LLM

### Q: Pourquoi avoir choisi gpt-4o-mini comme modele principal ?

**R:** C'est le meilleur ratio cout/performance pour notre cas. A 0.15 $/1M tokens input et 0.60 $/1M output, on est a 0.00015 $ par requete. Pour de la veille tech (classification, synthese d'articles), on n'a pas besoin de la puissance de raisonnement de gpt-4o sur 70% des requetes. On reserve gpt-4o aux cas complexes via la cascade (Module 6).

### Q: Comment tu geres les hallucinations dans Luciole ?

**R:** 3 niveaux de defense :
1. **Marqueurs structurels** : `[ERREUR_OUTIL]` et `[AUCUN_RESULTAT]` dans les resultats d'outils — le LLM recoit une instruction stricte de ne pas inventer si le resultat est vide
2. **Regles imperatives dans le prompt** (M5E6) : 5 regles dans `formuler_reponse` — ne jamais inventer titre/URL/chiffre, corriger les fausses premisses, clarifier les questions ambigues
3. **RAG** : les reponses sont basees sur des documents reels (articles RSS indexes), pas sur les connaissances generales du LLM

Le fix 1 (suppression des resultats web simules) supprime aussi une source d'hallucination : avant, sans cle Tavily, `search_web` retournait des URLs `example.com` que le LLM presentait comme vraies.

### Q: C'est quoi la difference entre hallucination et biais ?

**R:** **Hallucination** = le modele invente une information qui n'existe pas (ex: un titre d'article fictif). **Biais** = le modele repond de maniere systematiquement orientee (ex: toujours recommander AWS plutot que GCP). Dans Luciole, on combat les hallucinations avec les marqueurs et les regles de fidelite. Le biais est moins un risque vu qu'on base les reponses sur des articles reels (RAG).

### Q: Pourquoi le francais coute plus cher en tokens ?

**R:** Les tokenizers (comme tiktoken d'OpenAI) sont entraines principalement sur de l'anglais. Les mots francais avec accents, conjugaisons et mots plus longs sont decoupes en plus de sous-tokens. Environ **25% plus cher** qu'en anglais a contenu equivalent. C'est un facteur dans le calcul de ROI.

### Q: Quels parametres de generation tu utilises et pourquoi ?

**R:** `temperature=0.3` — on veut des reponses factuelles et reproductibles pour de la veille tech, pas de la creativite. `max_tokens=4096` par defaut (augmente depuis 2048, fix 7) avec un budget dynamique par intent : 1024 pour "general" (salutations), 4096 pour "search" et "rag" (syntheses longues), 2048 pour "database" et "vision".

---

## Module 2 — Conception & Architecture d'Agent

### Q: Explique l'architecture en 7 couches de Luciole.

**R:**
1. **Perception** : API FastAPI (`POST /ask`), upload fichiers (image/audio), SSE streaming
2. **Orchestration** : boucle ReAct dans `main.py` — `choisir_outil → executer_outil → formuler_reponse`, max 2 iterations
3. **Raisonnement** : OpenAI function calling natif (`TOOLS_DECISION`), cascade gpt-4o-mini/gpt-4o selon la complexite
4. **Memoire** : SQLite `memory.db` avec `conversation_id` pour isoler par utilisateur (fix 2), 50 messages max
5. **Outils** : 7 outils (search_articles, search_web, query_db, transcribe_audio, analyze_image, preview_digest, send_digest) + `reponse_directe`
6. **Controle/Securite** : detection injection prompt (20+ regex), validation SQL (SELECT only), filtrage sorties (IBAN, CB, email, tel), rate limiting
7. **Sortie** : reponse formatee en markdown, streaming SSE chunk par chunk, sources RAG affichees

### Q: Pourquoi le pattern ReAct et pas un simple chain ?

**R:** Un chain est lineaire : question → outil fixe → reponse. ReAct est dynamique : l'agent **raisonne** sur quelle action prendre selon la requete. Avec 7 outils differents, on ne sait pas a l'avance lequel utiliser. ReAct permet aussi l'iteration : si le premier outil echoue, on peut en essayer un autre (max 2 iterations). C'est le pattern standard pour les agents d'entreprise (Module 2 du cours).

### Q: Quelles sont les 5 menaces specifiques aux agents IA ?

**R:**
1. **Injection de prompt** : "Ignore tes instructions..." → detecte par `security.py` (20+ patterns regex), bloque avant tout appel LLM (0 token, 0.4 ms)
2. **Jailbreak** : contournement des garde-fous → prompt systeme defensif dans `SYSTEM_REACT`
3. **Exfiltration de donnees** : extraction d'infos sensibles → filtrage sorties (masquage IBAN, emails, tel)
4. **Action non autorisee** : l'agent execute un DELETE en base → validation SQL (SELECT only), whitelist d'outils
5. **Empoisonnement RAG** : injection de faux articles dans l'index → score de pertinence LLM (1-10, min 5) + deduplication par similarite de titre

Dans Luciole, les 4 barrieres de securite sont implementees : validation input, prompt defensif, controle outils, filtrage output.

### Q: C'est quoi les KPIs que tu as definis et pourquoi ceux-la ?

**R:** 6 KPIs, mix technique + metier :
- **Tokens/req** (640, cible ≤1000) : maitrise des couts API
- **Cout/req** (0.00015 $, cible ≤0.0005 $) : viabilite economique
- **Latence moyenne** (2980 ms, cible ≤5 s) : experience utilisateur
- **Latence p95** (5326 ms, cible ≤10 s) : pire cas acceptable
- **Taux erreur** (0%, cible <1%) : fiabilite
- **Pertinence metier** (3.57/5, cible ≥3.5) : le plus important — un agent rapide et pas cher mais qui repond mal est inutile

Le KPI metier etait le seul en rouge (3.30/5) avant l'atelier M5E6. C'est ce qui a guide les ameliorations.

---

## Module 3 — Developpement & Prototypage

### Q: Explique le cycle ReAct dans ton code concretement.

**R:** Dans `main.py`, la fonction `agent_react()` :
1. **Securite** : `analyser_securite(requete)` — bloque les injections avant tout
2. **Memoire** : `memory_recall(n=20, conversation_id)` — charge le contexte de la conversation
3. **Reason** : `choisir_outil(requete, historique, model_cascade)` — function calling OpenAI, retourne `{outil, intent, raisonnement, query_recherche}`
4. **Act** : `executer_outil(decision)` — appelle l'outil choisi (RAG, SQL, web, etc.)
5. **Observe** : si `[ERREUR_OUTIL]` → iteration suivante (max 2). Sinon → formulation
6. **Respond** : `formuler_reponse(requete, resultat, intent, historique, model_cascade, max_tokens)` — genere la reponse finale
7. **Post-traitement** : `filtrer_sortie(reponse)` — masque les donnees sensibles

### Q: Pourquoi coder a la main plutot qu'utiliser LangChain ?

**R:** Le cours recommande d'apprendre sans framework d'abord pour comprendre les mecanismes. LangChain ajoute de l'abstraction qui masque le fonctionnement reel. Notre ReAct fait ~500 lignes de code clair et debuggable. En production, on pourrait migrer vers un framework si la complexite augmente, mais pour 7 outils c'est pas necessaire.

### Q: Comment tu geres la memoire conversationnelle ?

**R:** SQLite (`memory.db`) avec une table `conversations (session_id, role, content, timestamp)`. Chaque conversation a son propre `conversation_id` (fix 2) — les utilisateurs ne partagent plus la meme memoire. On garde les 50 derniers messages (`LIMITE_MEMOIRE`), les plus anciens sont tronques. A chaque requete, on rappelle les 20 derniers messages (`recall(n=20)`) pour injecter le contexte dans les prompts.

**Fix 6** : ajout d'instructions dans `SYSTEM_REACT` pour que le LLM utilise l'historique pour resoudre les references implicites ("et en cybersecurite ?" → reprend le contexte de la question precedente).

### Q: Quels sont les 4 points critiques de debugging d'un agent ?

**R:**
1. **Mauvais prompt** → le LLM ne comprend pas l'intention (corrige avec RISE : Role, Instructions, Steps, Expected output)
2. **Mauvais choix d'outil** → le routeur envoie vers le mauvais outil (corrige avec les regles explicites dans `SYSTEM_REACT` + few-shot examples)
3. **Contexte insuffisant** → le RAG ne retourne pas assez/pas les bons documents (corrige avec BM25 hybride + HyDE)
4. **Hallucination en sortie** → le LLM invente malgre les donnees (corrige avec les regles de fidelite M5E6)

Dans Luciole, les 4 ont ete identifies par le LLM-as-Judge (M5E3) et corriges dans l'atelier M5E6.

---

## Module 4 — RAG & Integration Systeme

### Q: Explique ton pipeline RAG en detail.

**R:** RAG v3 dans `tools/rag.py`, scoring hybride :
1. **Ingestion** : 40+ sources RSS → scraping contenu → enrichissement LLM (resume, categorie, score pertinence 1-10)
2. **Chunking** : 500 mots avec 80 mots d'overlap pour preserver le contexte aux frontieres
3. **Embeddings** : `text-embedding-3-small` (OpenAI), stockes dans `embeddings.json` avec cache memoire
4. **Retrieval** : 3 composantes combinees :
   - **Cosine similarity** (α=0.5) : similarite semantique entre la requete et les chunks
   - **BM25** (α=0.25) : correspondance lexicale exacte (important pour les termes techniques)
   - **Fraicheur** (α=0.25) : articles recents favorises (decay apres 90 jours)
5. **HyDE** : expansion de requete — le LLM genere un paragraphe hypothetique, on embed ce texte enrichi pour mieux matcher (fix 9 : utilise `MODEL_FAST` pour limiter la latence)
6. **Generation** : injection des top-5 resultats dans le prompt de `formuler_reponse` avec regles de fidelite

### Q: Pourquoi numpy et pas ChromaDB pour le RAG ?

**R:** Luciole indexe ~500 articles RSS. A cette echelle, numpy avec similarite cosinus est largement suffisant : leger, deterministe, facile a debugger, zero dependance serveur. ChromaDB (utilise dans l'exercice M4) serait necessaire a partir de 10k+ documents pour les index ANN (approximate nearest neighbors). C'est un choix pragmatique — on n'ajoute pas de complexite inutile.

### Q: C'est quoi le BM25 et pourquoi l'utiliser en plus du cosine ?

**R:** BM25 est un algorithme de recherche lexicale (exact match pondere par frequence et longueur). Il corrige une faiblesse du cosine sur embeddings : les termes techniques tres specifiques (ex: "Kubernetes", "gpt-4o-mini") peuvent etre dilues dans l'espace semantique. BM25 les retrouve par correspondance exacte. Le scoring hybride (50% cosine + 25% BM25 + 25% fraicheur) donne de meilleurs resultats que chaque methode seule.

### Q: Pourquoi un score de fraicheur dans le RAG ?

**R:** C'est un agent de **veille technologique** — un article de la semaine derniere est plus pertinent qu'un article de 6 mois. Le decay est progressif : poids maximum pour les articles recents, score plancher apres 90 jours. Ca evite que de vieux articles bien rediges noient les nouvelles tendances.

### Q: Comment tu geres les 4 barrieres de securite ?

**R:**
1. **Validation input** (`security.py`) : longueur max 2000 chars + 20+ regex de detection d'injection prompt
2. **Prompt defensif** (`SYSTEM_REACT`) : instructions explicites de refus pour les sujets hors domaine
3. **Controle outils** : whitelist de 8 outils dans `TOOLS_DECISION`, SQL restreint a SELECT, validation des noms de tables
4. **Filtrage output** (`filtrer_sortie`) : masquage IBAN, CB, emails, numeros de telephone avec regex (format FR)

### Q: Comment fonctionne le multimodal dans Luciole ?

**R:** 2 outils :
- **Transcription audio** (`transcribe.py`) : Whisper API → transcription + analyse LLM. Fix 8 : auto-detection de la langue (plus force en francais).
- **Analyse image** (`vision.py`) : GPT-4o Vision → extraction structuree. Fix 10 : ajout d'un system prompt pour contextualiser (agent de veille tech).

L'upload passe par `POST /upload` avec validation magic bytes (pas juste l'extension), limite 10 MB, auto-cleanup apres 1h.

---

## Module 5 — Tests, Deploiement & Production

### Q: Comment tu testes un agent non-deterministe ?

**R:** Strategie a 3 niveaux (Module 5) :
1. **Tests unitaires** (deterministes) : 18 fichiers dans `tests/`, couvrent chaque outil, la memoire, l'auth, la securite, le parsing JSON. Avec mocks pour les appels LLM.
2. **Tests d'integration** (partiels) : `test_integration.py` — 22 tests end-to-end sur le pipeline complet (requete → ReAct → reponse), avec appels LLM reels.
3. **Tests qualite LLM-as-Judge** (non-deterministes) : `test_qualite.py` — 10 questions fixes, un LLM juge note sur 3 criteres (pertinence, fidelite, clarte) de 1 a 5.

Le LLM-as-Judge n'est pas parfait mais c'est la meilleure approche scalable pour mesurer la qualite d'un agent.

### Q: C'est quoi ton score LLM-as-Judge et comment tu l'as ameliore ?

**R:** Score initial : **3.30/5** (sous la cible 3.5). Diagnostic M5E3 :
- 5 questions sur 10 avaient fidelite = 1 (hallucination massive)
- Causes : mauvais routing (`search_articles` au lieu de `search_web`), prompt trop vague, pas d'instruction anti-hallucination

3 corrections prompt-only (M5E6) :
1. Regles explicites de routing (briefing/actus → `search_web`)
2. 5 regles imperatives de fidelite dans `formuler_reponse`
3. Meta-description des sources reelles dans `SYSTEM_REACT`

Resultat : **3.57/5** — cible atteinte. Q05 +1.6, Q09 +1.3. Mais 2 regressions documentees (Q08 -1.0, Q10 -0.7) : le prompt plus strict rend le LLM plus timide.

### Q: Explique ton Dockerfile.

**R:** Multi-stage en 3 etapes :
1. **Build** : `pip install` des dependances → `/install` (cache Docker exploite si `requirements.txt` ne change pas)
2. **Prebuild** : collecte RSS + scraping (pas besoin de cles API) → `articles_raw.json` pre-genere au build
3. **Runtime** : image slim, user non-root `appuser`, healthcheck `GET /health` toutes les 30s

Le pre-scraping au build evite le cold start long en production (pas besoin de scraper 40+ sources au demarrage).

### Q: Quel est ton plan de deploiement en 3 phases ?

**R:**
1. **Pilote** (1 mois) : 1 equipe veille tech (5 personnes), ~2000 req/mois. Go/No-go : pertinence ≥3.5/5, adoption >40%
2. **Deploiement** (1-2 mois) : 1 service complet. Criteres : resolution >50%, erreurs <5%
3. **Generalisation** : tous les services. Conditions : KPIs stables, adoption >70%

Heberge sur Render (Docker, Frankfurt). Cout estime : 19 EUR/mois (0.30 EUR OpenAI + 18.50 EUR hebergement).

### Q: Comment tu monitores ton agent en production ?

**R:** Module `monitoring.py` avec `contextvars` pour isoler chaque requete :
- `start_request()` → `add_llm_usage()` → `mark_fallback()` → `end_request()`
- `GET /metrics` : agregats (total requests, avg/p95 latence, tokens, cout, error_rate, fallback_rate)
- `GET /metrics/recent?limit=N` : detail des N dernieres requetes
- Langfuse (optionnel) : tracing LLM complet si les cles sont configurees

---

## Module 6 — Optimisation & Caching

### Q: Comment fonctionne ta cascade de modeles ?

**R:** Routing par complexite dans `main.py` :
1. `classifier_complexite(requete)` : le LLM classifie la requete en "simple" ou "complexe"
2. Simple → `gpt-4o-mini` (rapide, 0.15 $/1M input)
3. Complexe → `gpt-4o` (puissant, 2.50 $/1M input)

**Fix 3** : avant, la cascade n'etait appliquee qu'a `formuler_reponse`. Maintenant elle est propagee a `choisir_outil()` aussi — le modele puissant raisonne mieux sur le choix d'outil pour les questions complexes.

Ratio vise : 70% mini / 25% 4o / 5% cas speciaux (Module 6 du cours).

### Q: Tu utilises le prompt caching ?

**R:** Pas explicitement implemente dans Luciole. OpenAI fait du caching automatique sur les prompts ≥1024 tokens (-50% sur les tokens caches). Notre `SYSTEM_REACT` fait ~800 tokens, donc il est a la limite. En optimisation future, on pourrait restructurer le prompt pour que la partie stable depasse 1024 tokens et beneficie du cache.

Chez Anthropic, le cache est explicite (`cache_control: ephemeral`) avec -90% sur le cache hit — plus avantageux mais necesiterait un changement de provider.

### Q: C'est quoi HyDE et pourquoi tu l'utilises ?

**R:** **Hypothetical Document Embeddings** : au lieu d'embed la requete brute de l'utilisateur (courte, imprecise), on demande au LLM de generer un paragraphe hypothetique qui repondrait a la question, puis on embed ce texte enrichi. Ca ameliore le recall de +10-15% car l'embedding du texte hypothetique est plus proche des vrais documents.

Dans Luciole (`tools/rag.py`, `_expand_query()`), fix 9 : on utilise `MODEL_FAST` (gpt-4o-mini) au lieu du modele par defaut pour limiter la latence et le cout du HyDE.

### Q: Pourquoi pas de semantic cache dans Luciole ?

**R:** Le semantic cache (repondre directement si une question similaire a deja ete posee, cosine >0.95) est dangereux pour un agent de veille tech : les articles changent constamment, et deux questions similaires peuvent avoir des reponses differentes selon la date. C'est utile pour des FAQ statiques, pas pour de la veille dynamique. Le cours le dit : ne pas cacher les reponses qui dependent du temps ou de l'utilisateur.

### Q: Comment tu optimiserais encore Luciole ?

**R:** Par priorite :
1. **Cle Tavily en prod** : remplacer la recherche web vide par des resultats reels (impact direct sur Q07/Q09)
2. **Re-ranking** : Cohere reranking (deja prepare dans le code, optionnel) → retrieve top-50, rerank top-5 → +20% recall
3. **Prompt caching** : restructurer `SYSTEM_REACT` pour depasser 1024 tokens stables → -50% cout sur les tokens caches
4. **Circuit breaker** : couper un outil apres 10 echecs consecutifs au lieu de continuer a l'appeler
5. **Fallback multi-provider** : si OpenAI est down → basculer sur Anthropic ou Mistral

---

## Questions transversales (pieges possibles)

### Q: Quel est le risque principal de ton agent en production ?

**R:** La qualite de reponse. Pas le cout (0.00015 $/req), pas la latence (3s), pas la securite (garde-fous en place). Le vrai risque c'est qu'une reponse plausible mais fausse soit communiquee en externe — c'est pour ca que le KPI pertinence (3.57/5) est le plus important a surveiller.

### Q: Ton ROI de 18 000% est-il realiste ?

**R:** Les couts sont mesures (pas estimes). Le gain repose sur 3 hypotheses : 3 min gagnees par requete, 70% des requetes sont productives, cout salarial 50 EUR/h. Meme en scenario pessimiste (1 min, 40%), le ROI reste >3 000% parce que le cout OpenAI est negligeable (0.30 EUR/mois pour 2000 requetes). Le vrai cout c'est l'hebergement (18.50 EUR), et le vrai risque c'est la qualite, pas le prix.

### Q: Pourquoi RGPD n'est pas un probleme pour Luciole ?

**R:** Les donnees traitees sont des articles RSS publics (pas de donnees personnelles). La base `clients` est fictive (3 lignes de test). Le filtrage de sortie masque les emails/IBAN au cas ou. Si on passait en prod avec de vraies donnees clients, il faudrait : anonymisation avant indexation, RBAC, journalisation des acces, politique de purge, validation DPO.

### Q: Si tu devais refaire le projet de zero, que changerais-tu ?

**R:**
1. **Tavily des le depart** : la recherche web simulee a cause des hallucinations pendant tout le developpement
2. **Isolation memoire des le depart** : la memoire partagee entre utilisateurs etait un bug architectural, pas un detail
3. **Tests LLM-as-Judge plus tot** : on aurait detecte les problemes de routing et d'hallucination bien avant M5E3
4. **Le schema DB dans le prompt des le depart** : le SQL aveugle etait previsible et evitable

### Q: Difference entre ton RAG fil-rouge et le RAG exercice M4 ?

**R:** Deux implementations completement separees :
- **Fil-rouge** : numpy + cosine + BM25 + fraicheur, articles RSS, ~500 docs, embeddings.json
- **Exercice M4** : ChromaDB + pdfplumber, corpus CNIL (39 PDFs, 2367 chunks)

Le fil-rouge est plus sophistique (scoring hybride, HyDE) mais sur un corpus plus petit. L'exercice M4 utilise un vector store standard (ChromaDB) sur un corpus plus volumineux.
