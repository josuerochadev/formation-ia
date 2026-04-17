"""
M6E2 — Étape 1 : Benchmark SANS prompt caching.
Lance 20 requêtes variées vers Claude et mesure tokens/latence/coût.
Sauvegarde les résultats dans results_no_cache.json.

En mode SIMULATION : génère des données réalistes sans appel API.
"""
import json
import time
from config import (
    SIMULATION, MODEL, MAX_TOKENS,
    SYSTEM_PROMPT_LONG, TOOLS_DEFINITION, REQUETES_BENCHMARK,
    PRIX_INPUT, PRIX_OUTPUT, TOKENS_STABLE,
)

if SIMULATION:
    from simulate import simuler_sans_cache
else:
    from anthropic import Anthropic
    from config import ANTHROPIC_API_KEY
    client = Anthropic(api_key=ANTHROPIC_API_KEY)


def appeler_llm_sans_cache(user_message: str) -> dict:
    """Appel standard sans cache_control."""
    if SIMULATION:
        sim = simuler_sans_cache(user_message, TOKENS_STABLE)
        input_tokens = sim["input_tokens"]
        output_tokens = sim["output_tokens"]
        latence_ms = sim["latence_ms"]
        reponse_extrait = f"[SIMULATION] Réponse à : {user_message[:80]}..."
    else:
        t0 = time.perf_counter()
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT_LONG,        # string simple, pas de cache_control
            tools=TOOLS_DEFINITION,           # tools sans cache_control
            messages=[{"role": "user", "content": user_message}],
        )
        latence_ms = (time.perf_counter() - t0) * 1000
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        reponse_extrait = response.content[0].text[:200]

    cout_input = input_tokens * PRIX_INPUT
    cout_output = output_tokens * PRIX_OUTPUT

    return {
        "question": user_message,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cout_input": cout_input,
        "cout_output": cout_output,
        "cout_total": cout_input + cout_output,
        "latence_ms": round(latence_ms, 1),
        "reponse": reponse_extrait,
    }


def main():
    mode = "SIMULATION" if SIMULATION else "API RÉELLE"
    print("=" * 60)
    print(f"BENCHMARK SANS CACHE — 20 requêtes [{mode}]")
    print("=" * 60)

    resultats = []
    for i, question in enumerate(REQUETES_BENCHMARK, 1):
        print(f"\n[{i:02d}/20] {question[:60]}...")
        r = appeler_llm_sans_cache(question)
        resultats.append(r)
        print(f"  → input={r['input_tokens']} | output={r['output_tokens']} "
              f"| coût=${r['cout_total']:.6f} | latence={r['latence_ms']}ms")

    # --- Résumé ---
    total_input = sum(r["input_tokens"] for r in resultats)
    total_output = sum(r["output_tokens"] for r in resultats)
    total_cout = sum(r["cout_total"] for r in resultats)
    latences = [r["latence_ms"] for r in resultats]
    latences_sorted = sorted(latences)
    p95_idx = int(0.95 * len(latences_sorted)) - 1

    print(f"\n{'='*60}")
    print(f"RÉSUMÉ SANS CACHE")
    print(f"{'='*60}")
    print(f"  Tokens input totaux  : {total_input:,}")
    print(f"  Tokens output totaux : {total_output:,}")
    print(f"  Coût total           : ${total_cout:.6f}")
    print(f"  Latence moyenne      : {sum(latences)/len(latences):.0f} ms")
    print(f"  Latence P95          : {latences_sorted[p95_idx]:.0f} ms")

    # --- Sauvegarde ---
    with open("results_no_cache.json", "w") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    print("\nRésultats sauvegardés dans results_no_cache.json")


if __name__ == "__main__":
    main()
