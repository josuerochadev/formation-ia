"""
M6E2 — Simulateur de métriques Anthropic.

Génère des données réalistes basées sur le comportement documenté du prompt caching :
- System prompt + tools = ~1350 tokens stables (cachables)
- Chaque requête utilisateur = 15-30 tokens variables
- Output = 150-400 tokens selon la question
- Latence sans cache : 800-2500 ms (prefill complet)
- Latence avec cache_read : 400-1500 ms (prefill partiel, ~30-40% plus rapide)
- cache_creation : même latence que sans cache (1er appel)
"""
import random


def simuler_sans_cache(question: str, tokens_stable: int) -> dict:
    """Simule un appel API SANS prompt caching."""
    # Tokens input = system + tools + message utilisateur
    tokens_user = len(question.split()) + random.randint(5, 15)  # ~mots → tokens approx
    input_tokens = tokens_stable + tokens_user
    output_tokens = random.randint(150, 400)
    latence_ms = random.uniform(800, 2500)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latence_ms": round(latence_ms, 1),
    }


def simuler_avec_cache(question: str, tokens_stable: int, is_first: bool) -> dict:
    """
    Simule un appel API AVEC prompt caching.

    - 1er appel : cache_creation (paye 1.25x sur les tokens stables)
    - Appels suivants : cache_read (paye 0.1x sur les tokens stables)
    """
    tokens_user = len(question.split()) + random.randint(5, 15)
    input_tokens = tokens_stable + tokens_user
    output_tokens = random.randint(150, 400)

    if is_first:
        # Création du cache — latence similaire à sans cache
        cache_creation = tokens_stable
        cache_read = 0
        latence_ms = random.uniform(800, 2500)
    else:
        # Lecture du cache — latence réduite (~30-40% plus rapide)
        cache_creation = 0
        cache_read = tokens_stable
        latence_ms = random.uniform(400, 1500)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "latence_ms": round(latence_ms, 1),
    }
