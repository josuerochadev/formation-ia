# M6E2 — Prompt Caching (Anthropic)

## Objectif

Diviser par ~10 le coût des tokens d'entrée stables (system prompt, définition des tools)
grâce au **prompt caching** d'Anthropic. Mesure réelle avant/après sur 20 requêtes.

> **Ne pas confondre :**
> - **Prompt caching** = cache de l'INPUT envoyé au LLM (réutilisation des mêmes tokens) — géré par Anthropic
> - **Semantic cache** = cache de la RÉPONSE quand une question similaire revient — géré par nous (Redis + embeddings)

## Prérequis

- `pip install anthropic python-dotenv`
- Variable `ANTHROPIC_API_KEY` dans `.env`
- Modèle : `claude-sonnet-4-20250514`

## Structure

```
prompt_caching/
├── config.py               # System prompt long, tools, tarifs, requêtes
├── benchmark_no_cache.py   # Étape 1 : 20 requêtes SANS cache
├── llm_cache.py            # Étape 2 : client avec cache_control
├── benchmark_cache.py      # Étape 3 : 20 requêtes AVEC cache
└── compare.py              # Étape 4 : tableau comparatif
```

## Exécution

```bash
cd exercices/module6/prompt_caching

# Étape 1 — Baseline sans cache
python benchmark_no_cache.py

# Étape 3 — Avec cache (lancer dans les 5 min après l'étape 1 pour comparer)
python benchmark_cache.py

# Étape 4 — Comparaison
python compare.py
```

## Points clés du prompt caching

| Paramètre | Valeur |
|---|---|
| Seuil minimum | 1024 tokens (Sonnet), 2048 (Haiku) |
| TTL | 5 minutes |
| Max breakpoints | 4 par requête |
| Coût cache_creation | 1.25x prix input normal |
| Coût cache_read | 0.1x prix input normal |
| Break-even | Dès la 2e lecture |

### Ordre des blocs (du plus stable au plus variable)

1. `system` → `cache_control: {"type": "ephemeral"}` (breakpoint #1)
2. `tools` → `cache_control` sur le dernier tool (breakpoint #2)
3. `messages` → PAS de cache (variable à chaque requête)

## Résultats attendus

- Requête 1 : `cache_creation_input_tokens` élevé (création du cache, 1.25x)
- Requêtes 2-20 : `cache_read_input_tokens` élevé (lecture, 0.1x)
- Économie input : **~85-90%** sur les 20 requêtes
- Latence : légère réduction (le cache accélère le prefill)
