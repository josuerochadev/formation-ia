# Module 6 — Optimisation & Caching

> Formation : *Maitriser les LLM et l'IA Generative* — AJC Formation
> Module bonus | 3h30 | Demi-journee

---

## Bloc 1 — Mesurer (30 min)

### On n'optimise que ce qu'on mesure

Avant de toucher a quoi que ce soit : instrumenter. Un agent "optimise au doigt mouille" finit toujours plus lent ET plus cher que l'original.

> Regle d'or : une baseline chiffree sur 50 requetes reelles AVANT toute optimisation.

### Les 3 metriques cles

| Metrique | Definition | Cible prod |
|---|---|---|
| TTFT — Time To First Token | Temps envoi requete → 1er token recu | < 1s |
| Cout par requete | sum(input x prix_in) + (output x prix_out) | < 0,01 EUR/req |
| Qualite | Score LLM-as-Judge ou humain sur 20 cas | > 80% |

Piege classique : optimiser le cout et casser la qualite. Toujours mesurer les 3 ensemble.

Metriques secondaires : latence totale (end-to-end), taux d'erreur, tokens/s.

### Outils d'observabilite : Langfuse vs LangSmith

| Critere | Langfuse | LangSmith |
|---|---|---|
| Editeur | Open-source (self-host) | LangChain (SaaS) |
| Integration | SDK Python, decorateur `@observe` | Integre LangChain/LangGraph |
| Prix | Free tier genereux, self-host gratuit | Free tier limite |
| Forces | Traces, evals, prompt mgmt, RGPD | Graph visuel des chaines |

> Recommandation formation : Langfuse — self-hostable, pas de lock-in, RGPD-friendly.

### Instrumenter avec Langfuse

```python
from langfuse.decorators import observe
from langfuse.openai import openai  # drop-in

@observe()
def ask_agent(question: str):
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content

# → dashboard Langfuse auto-rempli :
#   latence, tokens in/out, cout $, trace
```

Exercice : lancer 20 requetes sur l'agent M3, observer dans Langfuse les p50/p95 latence, cout total, distribution tokens → c'est votre baseline.

---

## Bloc 2 — Prompt Caching (1h15)

### Le levier #1 de reduction des couts

Si vous ne devez retenir qu'UN SEUL levier de cette formation, c'est celui-la.

| | Cout | Latence | Effort | Risque |
|---|---|---|---|---|
| Gain | jusqu'a -90% | jusqu'a -85% | quelques lignes | nul |
| Detail | sur les tokens en cache hit | sur le TTFT | de code seulement | si bien fait |

Pourquoi ca marche : on ne re-facture pas la "lecture" d'un contexte deja vu recemment.

### Mecanisme : ce que le LLM "voit" a chaque appel

Un appel LLM classique envoie toujours la meme structure :

```
[Systeme long (3000 tok)] + [Outils (800 tok)] + [Few-shots (1500 tok)]
+ [Historique conv (500 tok)] + [Nouvelle question (50 tok)]
= 5850 tokens envoyes x 100 requetes = 585 000 tokens factures
```

Sur 100 requetes : ~85% des tokens sont STRICTEMENT IDENTIQUES. Le prompt caching dit : "ce prefixe, je l'ai deja encode — ne me le refacture pas plein tarif."

### Anthropic — Prompt caching explicite (`cache_control`)

```python
client.messages.create(
    model="claude-3-5-sonnet-20241022",
    system=[
        {"type": "text",
         "text": LONG_SYSTEM_PROMPT,
         "cache_control": {"type": "ephemeral"}
         # ← cached
        },
    ],
    tools=[...],  # cache_control aussi
    messages=[{"role": "user", "content": "..."}],
)
```

| Parametre | Detail |
|---|---|
| Tarifs | Write : 1.25x prix normal / Read : 0.1x prix normal → **-90%** |
| TTL | 5 min (ephemeral), 1h (extended, beta) |
| Minimum | 1024 tok (Sonnet/Opus), 2048 tok (Haiku) |

### Anatomie d'un bon prompt cache

Le cache match du prefixe vers le suffixe. Si un token change au milieu, tout ce qui suit est re-facture plein tarif.

Ordre optimal (du plus stable au plus variable) :

1. **System prompt** — quasi-jamais modifie
2. **Outils / function schemas** — stables sur la session
3. **Few-shot examples** — identiques d'un appel a l'autre
4. **Documents RAG** — si stables sur la session
5. **Historique de conversation** — grossit lentement
6. **Message utilisateur courant** — toujours nouveau

> Jusqu'a 4 breakpoints `cache_control` par requete Anthropic.

### OpenAI — Caching automatique

Depuis oct. 2024, OpenAI cache automatiquement tout prefixe >= 1024 tokens.

| Point | Detail |
|---|---|
| Declenchement | Automatique des que prompt >= 1024 tok |
| Remise | -50% sur tokens en cache hit (vs -90% Anthropic) |
| Granularite | Blocs de 128 tokens |
| TTL | 5-10 min (non garanti) |
| Monitoring | `usage.prompt_tokens_details.cached_tokens` |

Moins puissant qu'Anthropic, mais zero effort d'implementation.

### Bonnes pratiques pour un prompt "cache-friendly"

**A faire** :
- Mettre tout ce qui est stable en premier (system, tools, exemples)
- Injecter date/heure ou user_id a la FIN du system prompt
- Garder les few-shots identiques d'une requete a l'autre
- Versionner les prompts (un changement de virgule = cache miss global)

**A eviter** :
- Interpoler la question utilisateur dans le system prompt
- Randomiser l'ordre des outils ou des exemples
- Mettre un timestamp en DEBUT de prompt (casse tout le cache)
- Changer le system prompt entre deux appels sans raison

### Resultats attendus (avant/apres caching)

| Metrique | Sans cache | Avec cache (hit) | Gain |
|---|---|---|---|
| Input tokens factures | 5 000 | 500 | -90% |
| Cout / requete | 0,015 EUR | 0,002 EUR | -87% |
| TTFT (p50) | 1,8 s | 0,4 s | -78% |
| Qualite (LLM-judge) | 87% | 87% | = |

Investissement : ~2h de refactor. ROI sur 10 000 req/jour : ~40 EUR/jour economises. Payback en moins d'une journee.

---

## Bloc 3 — Routing & Cascade de modeles (30 min)

### Toutes les requetes ne meritent pas un Opus

Principe : classer d'abord la difficulte de la requete, puis router vers le bon modele.

| Tier | Part | Modele | Cas d'usage |
|---|---|---|---|
| Petit | 70% | Haiku / gpt-4o-mini | Classification d'intention, extraction simple, reponses courtes |
| Moyen | 25% | Sonnet / gpt-4o | Raisonnement multi-etapes, redaction longue, tool use complexe |
| Gros | 5% | Opus / o1 | Ambiguite forte, chaines longues, cas difficiles seulement |

> Regle empirique : 70% Haiku / 25% Sonnet / 5% Opus → cout divise par 5 a qualite equivalente.

### Implementation : LangChain vs Custom

**Option A — LangChain RouterChain** :

```python
from langchain.chains.router import MultiPromptChain
router = MultiPromptChain.from_prompts(...)
```

\+ Bibliotheque mature, integration tools native
\- Overhead, moins de controle fin

**Option B — Custom (recommande)** :

```python
def route(question: str) -> str:
    # Petit appel Haiku pour classifier
    intent = classify(question)
    return {
        "simple": "haiku",
        "medium": "sonnet",
        "hard":   "opus"
    }[intent]
```

\+ Transparence totale, cache-friendly, pas de dependance externe → a privilegier en prod.

---

## Bloc 4 — RAG optimise (45 min)

### Le RAG naif plafonne vite

Rappel M4 : embed → search top-k → stuff dans le prompt. Ca marche... jusqu'a 500 docs. Au-dela : recall qui s'effondre, hallucinations, latence qui explose.

4 techniques d'optimisation :

1. **Re-ranking** — Cohere rerank-v3 → +20% recall
2. **Contextual retrieval** — Anthropic → -49% echec retrieval
3. **Hybrid search** — BM25 + dense → lexical + semantique
4. **Query rewriting / HyDE** — Reformulation avant recherche

### Re-ranking : Retrieve large, rerank small

Probleme : top-5 d'un vector store ≠ les 5 meilleurs. La similarite cosinus n'est PAS la pertinence.

| Etape | Detail |
|---|---|
| 1. Retrieve — top-50 | Vector store (rapide, imprecis) ~30ms |
| 2. Rerank — top-5 | Cross-encoder (Cohere, BGE) ~150ms, tres precis |

```python
from cohere import Client
results = cohere.rerank(query=q, documents=top50,
                        top_n=5, model="rerank-v3.5")
```

Gain : +20% recall | latence +150ms | cout : 2 $/1M docs rerankes.

### Contextual retrieval (Anthropic)

Idee (sept. 2024) : avant d'embedder un chunk, generer un resume de son contexte dans le document.

```python
# Chunk brut
"Le taux d'interet est de 3,2%."

# Chunk contextualise (via LLM)
"Contrat ACME-2024 signe avec
 Societe Generale le 12/03/2024.
 Le taux d'interet est de 3,2%."

# → embed CELUI-LA dans le vector store
```

Gains Anthropic : -49% echec retrieval (contextual seul), -67% echec retrieval (+ reranking).

Cout : 1 passe LLM par chunk — mitige par le prompt caching (on reutilise le document entier).

### Hybrid search + HyDE

**Hybrid — BM25 + Dense** :
- Dense : semantique (voiture ≈ auto)
- BM25 : lexical exact (codes, noms propres, IDs)
- Fusion : Reciprocal Rank Fusion (RRF)
- → Indispensable si vocabulaire technique

**HyDE — Hypothetical Document Embedding** :
- La question ≠ les documents cibles
- Solution : LLM genere une reponse hypothetique, on embed CETTE REPONSE et on cherche
- +10-15% recall sur questions mal formulees

**Query rewriting** — reformuler la question avant la recherche :
- Expansion : ajouter synonymes et termes lies
- Decomposition : multi-hop → plusieurs requetes paralleles
- Resolution d'anaphores ("il", "ce document") via l'historique

---

## Bloc 5 — Semantic Cache (20 min)

### Cacher les REPONSES, pas juste les prompts

Idee : deux utilisateurs posent une question semantiquement equivalente → servir la reponse cachee.

Outils : GPTCache, Redis Vector, LangChain LLMCache. Seuil cosinus > 0.95 typique.

**Pertinent quand** :
- FAQ, chatbot support
- Questions repetitives
- Reponses sans contexte perso
- Documentation publique
- → Gain typique : 30-50% des appels LLM evites

**DANGEREUX quand** :
- Reponses dependant de l'utilisateur (clients, commandes, droits)
- Donnees temporelles ("aujourd'hui", "ce mois-ci")
- Reglemente / conformite → tracabilite perdue

---

## Patterns de production — Checklist resilience

| Pattern | Pourquoi | Outils |
|---|---|---|
| Rate limiting | Eviter cout runaway & abus | Redis, tenacity |
| Fallback multi-provider | Panne OpenAI ? → Anthropic | LiteLLM, custom |
| Retry avec backoff | 5xx et 429 passagers | tenacity, backoff |
| Budget alerts | Alerte Slack si cout > seuil | Langfuse, custom |
| Circuit breaker | Couper un tool qui echoue 10x | pybreaker |
| Token budget / requete | Cap dur max_tokens + input | middleware |

---

## Checklist "prod-ready perf"

Avant de considerer un agent pret pour la production :

- [ ] Baseline mesuree (TTFT, cout/req, qualite) sur 50 requetes reelles
- [ ] Observabilite en place (Langfuse ou LangSmith)
- [ ] Prompt caching active + gain mesure > 50% sur cout input
- [ ] Structure de prompt versionnee et stable
- [ ] Routing multi-modeles (petit / moyen / gros)
- [ ] RAG : re-ranking + (hybrid OU contextual) actives
- [ ] Fallback multi-provider configure
- [ ] Tests qualite non-regression (LLM-as-Judge) sur 20 cas d'or

> Objectif atteint : cout /5, latence /3, qualite maintenue. Bienvenue en prod.

---

## Competences acquises

- Mesurer les 3 metriques cles d'un agent LLM (TTFT, cout/req, qualite) avec Langfuse ou LangSmith
- Mettre en place le prompt caching (Anthropic `cache_control`, OpenAI auto-cache) et mesurer les gains reels
- Router intelligemment les requetes entre modeles (Haiku classif, Opus raisonnement)
- Optimiser un pipeline RAG (re-ranking, hybrid search, query rewriting, contextual retrieval)
- Decider quand un cache semantique est pertinent — et quand il devient dangereux
- Construire une stack prod-ready avec fallback, rate limiting et budget alerts

---

## Voir aussi

- **Exercices** :
  - [M6E1 — Langfuse LLM observability](../exercices/module6/m6e1_langfuse.md) — instrumentation et baseline
- **Fil rouge** :
  - [`fil-rouge/main.py`](../fil-rouge/main.py) — boucle agent ReAct
  - [`fil-rouge/llm.py`](../fil-rouge/llm.py) — client OpenAI centralise
