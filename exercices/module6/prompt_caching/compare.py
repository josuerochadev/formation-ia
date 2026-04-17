"""
M6E2 — Étape 4 : Tableau comparatif avant/après prompt caching.
Lit results_no_cache.json et results_cache.json, affiche le tableau de gains.
"""
import json
import sys


def load_results(path: str) -> list[dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERREUR : fichier {path} introuvable.")
        print("Lancez d'abord benchmark_no_cache.py puis benchmark_cache.py.")
        sys.exit(1)


def compute_stats(results: list[dict], has_cache: bool = False) -> dict:
    """Calcule les agrégats à partir d'une liste de résultats."""
    total_input = sum(r["input_tokens"] for r in results)
    total_output = sum(r["output_tokens"] for r in results)

    if has_cache:
        cout_input = sum(
            r["cout_input_normal"] + r["cout_cache_write"] + r["cout_cache_read"]
            for r in results
        )
        total_cache_read = sum(r["cache_read_input_tokens"] for r in results)
    else:
        cout_input = sum(r["cout_input"] for r in results)
        total_cache_read = 0

    cout_output = sum(r["cout_output"] for r in results)
    cout_total = cout_input + cout_output

    latences = sorted(r["latence_ms"] for r in results)
    n = len(latences)
    lat_avg = sum(latences) / n
    lat_p95 = latences[int(0.95 * n) - 1]

    return {
        "total_input": total_input,
        "total_output": total_output,
        "cache_read": total_cache_read,
        "cout_input": cout_input,
        "cout_output": cout_output,
        "cout_total": cout_total,
        "lat_avg": lat_avg,
        "lat_p95": lat_p95,
    }


def pct_change(before: float, after: float) -> str:
    """Calcule le pourcentage de variation."""
    if before == 0:
        return "N/A"
    pct = ((after - before) / before) * 100
    return f"{pct:+.1f}%"


def main():
    avant = load_results("results_no_cache.json")
    apres = load_results("results_cache.json")

    s_avant = compute_stats(avant, has_cache=False)
    s_apres = compute_stats(apres, has_cache=True)

    # --- Tableau ---
    print()
    print("=" * 72)
    print("  TABLEAU COMPARATIF — PROMPT CACHING (M6E2)")
    print("=" * 72)
    print(f"  {'Métrique':<32} {'Avant':>10} {'Après':>10} {'Gain':>10}")
    print(f"  {'-'*32} {'-'*10} {'-'*10} {'-'*10}")

    rows = [
        ("Tokens input (20 req)",
         f"{s_avant['total_input']:,}", f"{s_apres['total_input']:,}",
         pct_change(s_avant['total_input'], s_apres['total_input'])),

        ("Dont cache_read",
         "0", f"{s_apres['cache_read']:,}", "—"),

        ("Tokens output (20 req)",
         f"{s_avant['total_output']:,}", f"{s_apres['total_output']:,}",
         pct_change(s_avant['total_output'], s_apres['total_output'])),

        ("Coût input ($)",
         f"${s_avant['cout_input']:.6f}", f"${s_apres['cout_input']:.6f}",
         pct_change(s_avant['cout_input'], s_apres['cout_input'])),

        ("Coût output ($)",
         f"${s_avant['cout_output']:.6f}", f"${s_apres['cout_output']:.6f}",
         pct_change(s_avant['cout_output'], s_apres['cout_output'])),

        ("Coût total ($)",
         f"${s_avant['cout_total']:.6f}", f"${s_apres['cout_total']:.6f}",
         pct_change(s_avant['cout_total'], s_apres['cout_total'])),

        ("Latence moyenne (ms)",
         f"{s_avant['lat_avg']:.0f}", f"{s_apres['lat_avg']:.0f}",
         pct_change(s_avant['lat_avg'], s_apres['lat_avg'])),

        ("Latence P95 (ms)",
         f"{s_avant['lat_p95']:.0f}", f"{s_apres['lat_p95']:.0f}",
         pct_change(s_avant['lat_p95'], s_apres['lat_p95'])),
    ]

    for label, v_avant, v_apres, gain in rows:
        print(f"  {label:<32} {v_avant:>10} {v_apres:>10} {gain:>10}")

    print(f"  {'-'*32} {'-'*10} {'-'*10} {'-'*10}")
    print()

    # --- Analyse ---
    gain_cout = (1 - s_apres['cout_total'] / s_avant['cout_total']) * 100 if s_avant['cout_total'] > 0 else 0
    gain_input = (1 - s_apres['cout_input'] / s_avant['cout_input']) * 100 if s_avant['cout_input'] > 0 else 0

    print(f"  ANALYSE :")
    print(f"  → Économie sur le coût input : {gain_input:.1f}%")
    print(f"  → Économie sur le coût total : {gain_cout:.1f}%")

    if s_apres['cache_read'] > 0:
        ratio = s_apres['cache_read'] / s_apres['total_input'] * 100
        print(f"  → Taux de cache hit (tokens) : {ratio:.1f}%")

    print()


if __name__ == "__main__":
    main()
