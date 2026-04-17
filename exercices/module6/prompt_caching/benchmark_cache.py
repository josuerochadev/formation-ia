"""
M6E2 — Étape 3 : Benchmark AVEC prompt caching.
Lance les mêmes 20 requêtes avec cache_control activé.
La 1ère requête paie la création du cache ; les 19 suivantes le lisent.
Sauvegarde les résultats dans results_cache.json.

En mode SIMULATION : génère des données réalistes sans appel API.
"""
import json
import time
from config import (
    SIMULATION, REQUETES_BENCHMARK, TOKENS_STABLE,
    PRIX_INPUT, PRIX_OUTPUT, PRIX_CACHE_WRITE, PRIX_CACHE_READ,
)

if SIMULATION:
    from simulate import simuler_avec_cache
else:
    from llm_cache import appeler_llm_cache


def mesurer_requete_cache(user_message: str, is_first: bool) -> dict:
    """Lance une requête avec cache et collecte les métriques."""
    if SIMULATION:
        sim = simuler_avec_cache(user_message, TOKENS_STABLE, is_first)
        input_tokens = sim["input_tokens"]
        output_tokens = sim["output_tokens"]
        cache_creation = sim["cache_creation_input_tokens"]
        cache_read = sim["cache_read_input_tokens"]
        latence_ms = sim["latence_ms"]
        reponse_extrait = f"[SIMULATION] Réponse à : {user_message[:80]}..."
    else:
        t0 = time.perf_counter()
        response, usage = appeler_llm_cache(user_message)
        latence_ms = (time.perf_counter() - t0) * 1000
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        reponse_extrait = response.content[0].text[:200]

    # Tokens input "normaux" = ceux qui ne sont ni cache_creation ni cache_read
    input_normal = input_tokens - cache_creation - cache_read

    # Calcul du coût
    cout_input_normal = input_normal * PRIX_INPUT
    cout_cache_write = cache_creation * PRIX_CACHE_WRITE
    cout_cache_read = cache_read * PRIX_CACHE_READ
    cout_output = output_tokens * PRIX_OUTPUT
    cout_total = cout_input_normal + cout_cache_write + cout_cache_read + cout_output

    return {
        "question": user_message,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "input_normal_tokens": input_normal,
        "cout_input_normal": cout_input_normal,
        "cout_cache_write": cout_cache_write,
        "cout_cache_read": cout_cache_read,
        "cout_output": cout_output,
        "cout_total": cout_total,
        "latence_ms": round(latence_ms, 1),
        "reponse": reponse_extrait,
    }


def main():
    mode = "SIMULATION" if SIMULATION else "API RÉELLE"
    print("=" * 60)
    print(f"BENCHMARK AVEC CACHE — 20 requêtes [{mode}]")
    print("=" * 60)

    resultats = []
    for i, question in enumerate(REQUETES_BENCHMARK, 1):
        is_first = (i == 1)
        print(f"\n[{i:02d}/20] {question[:60]}...")
        r = mesurer_requete_cache(question, is_first)
        resultats.append(r)

        cache_info = ""
        if r["cache_creation_input_tokens"] > 0:
            cache_info = f" | CACHE_WRITE={r['cache_creation_input_tokens']}"
        if r["cache_read_input_tokens"] > 0:
            cache_info = f" | CACHE_READ={r['cache_read_input_tokens']}"

        print(f"  → input={r['input_tokens']} | output={r['output_tokens']}"
              f"{cache_info} | coût=${r['cout_total']:.6f} | latence={r['latence_ms']}ms")

    # --- Résumé ---
    total_input = sum(r["input_tokens"] for r in resultats)
    total_output = sum(r["output_tokens"] for r in resultats)
    total_cache_write = sum(r["cache_creation_input_tokens"] for r in resultats)
    total_cache_read = sum(r["cache_read_input_tokens"] for r in resultats)
    total_cout = sum(r["cout_total"] for r in resultats)
    latences = [r["latence_ms"] for r in resultats]
    latences_sorted = sorted(latences)
    p95_idx = int(0.95 * len(latences_sorted)) - 1

    print(f"\n{'='*60}")
    print(f"RÉSUMÉ AVEC CACHE")
    print(f"{'='*60}")
    print(f"  Tokens input totaux       : {total_input:,}")
    print(f"  Dont cache_creation       : {total_cache_write:,}")
    print(f"  Dont cache_read           : {total_cache_read:,}")
    print(f"  Tokens output totaux      : {total_output:,}")
    print(f"  Coût total                : ${total_cout:.6f}")
    print(f"  Latence moyenne           : {sum(latences)/len(latences):.0f} ms")
    print(f"  Latence P95               : {latences_sorted[p95_idx]:.0f} ms")

    # --- Sauvegarde ---
    with open("results_cache.json", "w") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    print("\nRésultats sauvegardés dans results_cache.json")


if __name__ == "__main__":
    main()
