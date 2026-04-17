"""
Exercice 3 — Benchmark cascade Haiku / Sonnet.

Compare le coût et la latence avec et sans cascade sur 15 questions variées.
Produit un tableau comparatif et une analyse des faux positifs.
"""

import json
import time
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv

load_dotenv()

from router import (
    repondre,
    repondre_sans_cascade,
    classifier_intent,
    _get_client,
    MODEL_HAIKU,
    MODEL_SONNET,
)

# --- 15 questions : 8 simples + 7 complexes ---
QUESTIONS = [
    # ── Simples (8) ──
    {"question": "Bonjour !", "attendu": "simple", "categorie_attendue": "salutation"},
    {"question": "Comment tu t'appelles ?", "attendu": "simple", "categorie_attendue": "salutation"},
    {"question": "C'est quoi un LLM ?", "attendu": "simple", "categorie_attendue": "faq"},
    {"question": "Quelle est la différence entre RAM et ROM ?", "attendu": "simple", "categorie_attendue": "faq"},
    {"question": "Qu'est-ce que Docker ?", "attendu": "simple", "categorie_attendue": "faq"},
    {"question": "Liste les principaux fournisseurs cloud", "attendu": "simple", "categorie_attendue": "faq"},
    {"question": "Quels sont les langages les plus populaires en 2025 ?", "attendu": "simple", "categorie_attendue": "faq"},
    {"question": "Merci pour ton aide, à bientôt !", "attendu": "simple", "categorie_attendue": "salutation"},
    # ── Complexes (7) ──
    {"question": "Compare les architectures microservices et monolithiques en termes de scalabilité, maintenabilité et coûts opérationnels", "attendu": "complexe", "categorie_attendue": "analyse"},
    {"question": "Écris un script Python qui implémente un cache LRU thread-safe avec expiration TTL", "attendu": "complexe", "categorie_attendue": "code"},
    {"question": "Analyse les implications du EU AI Act sur le déploiement de modèles de fondation open-source en entreprise", "attendu": "complexe", "categorie_attendue": "analyse"},
    {"question": "Synthétise les avantages et risques de l'adoption de Kubernetes vs des solutions serverless pour une startup de 10 développeurs", "attendu": "complexe", "categorie_attendue": "raisonnement"},
    {"question": "Explique étape par étape comment fonctionne le mécanisme d'attention dans les transformers, avec les calculs matriciels Q, K, V", "attendu": "complexe", "categorie_attendue": "raisonnement"},
    {"question": "Propose une architecture RAG optimale pour un corpus de 100K documents multilingues avec des contraintes de latence < 500ms", "attendu": "complexe", "categorie_attendue": "raisonnement"},
    {"question": "Écris une fonction Rust qui parse un fichier CSV en parallèle avec rayon et gère les erreurs proprement", "attendu": "complexe", "categorie_attendue": "code"},
]


def run_benchmark():
    """Exécute le benchmark complet : avec et sans cascade."""
    client = _get_client()

    results_cascade = []
    results_baseline = []

    print("=" * 80)
    print("BENCHMARK CASCADE HAIKU / SONNET — 15 QUESTIONS")
    print("=" * 80)

    # --- Scénario 1 : SANS cascade (tout Sonnet) ---
    print("\n[1/2] Sans cascade (tout Sonnet)...")
    for i, q in enumerate(QUESTIONS, 1):
        print(f"  {i}/15 — {q['question'][:50]}...", end=" ", flush=True)
        r = repondre_sans_cascade(q["question"], client=client)
        r["question"] = q["question"]
        r["attendu"] = q["attendu"]
        results_baseline.append(r)
        print(f"✓ {r['latency_ms']:.0f}ms ${r['cost_usd']:.6f}")
        time.sleep(0.5)  # rate limit

    # --- Scénario 2 : AVEC cascade ---
    print("\n[2/2] Avec cascade (Haiku router + Haiku/Sonnet)...")
    for i, q in enumerate(QUESTIONS, 1):
        print(f"  {i}/15 — {q['question'][:50]}...", end=" ", flush=True)
        r = repondre(q["question"], client=client)
        r["question"] = q["question"]
        r["attendu"] = q["attendu"]
        results_cascade.append(r)
        model_short = "Haiku" if MODEL_HAIKU in r["model_used"] else "Sonnet"
        classif = r["routing"]["complexite"]
        match = "✓" if classif == q["attendu"] else "✗"
        print(f"{match} [{classif}→{model_short}] {r['latency_total_ms']:.0f}ms ${r['cost_usd']:.6f}")
        time.sleep(0.5)

    # --- Résultats ---
    print("\n" + "=" * 80)
    print("RÉSULTATS")
    print("=" * 80)

    total_baseline_cost = sum(r["cost_usd"] for r in results_baseline)
    total_cascade_cost = sum(r["cost_usd"] for r in results_cascade)
    avg_baseline_latency = sum(r["latency_ms"] for r in results_baseline) / len(results_baseline)
    avg_cascade_latency = sum(r["latency_total_ms"] for r in results_cascade) / len(results_cascade)

    haiku_calls = sum(1 for r in results_cascade if MODEL_HAIKU in r["model_used"])
    sonnet_calls = sum(1 for r in results_cascade if MODEL_SONNET in r["model_used"])
    economie_pct = ((total_baseline_cost - total_cascade_cost) / total_baseline_cost * 100) if total_baseline_cost > 0 else 0

    print(f"\n{'Scénario':<30} {'Haiku':<12} {'Sonnet':<12} {'Coût ($)':<15} {'Latence moy (ms)'}")
    print("─" * 85)
    print(f"{'Sans cascade (tout Sonnet)':<30} {'0':<12} {'15':<12} {f'${total_baseline_cost:.6f}':<15} {avg_baseline_latency:.0f}")
    print(f"{'Avec cascade':<30} {str(haiku_calls):<12} {str(sonnet_calls):<12} {f'${total_cascade_cost:.6f}':<15} {avg_cascade_latency:.0f}")
    print(f"{'Économie (%)':<30} {'—':<12} {'—':<12} {f'{economie_pct:.1f}%':<15} {f'{((avg_baseline_latency - avg_cascade_latency) / avg_baseline_latency * 100):.1f}%'}")

    # --- Analyse de la classification ---
    print(f"\n{'='*80}")
    print("ANALYSE DE LA CLASSIFICATION")
    print(f"{'='*80}")
    print(f"\n{'#':<4} {'Question':<55} {'Attendu':<10} {'Classé':<10} {'OK?'}")
    print("─" * 85)

    faux_positifs = []  # classé simple mais est complexe
    faux_negatifs = []  # classé complexe mais est simple

    for i, (q, r) in enumerate(zip(QUESTIONS, results_cascade), 1):
        classif = r["routing"]["complexite"]
        ok = "✓" if classif == q["attendu"] else "✗"
        question_short = q["question"][:52] + "..." if len(q["question"]) > 52 else q["question"]
        print(f"{i:<4} {question_short:<55} {q['attendu']:<10} {classif:<10} {ok}")

        if classif == "simple" and q["attendu"] == "complexe":
            faux_positifs.append(q["question"])
        elif classif == "complexe" and q["attendu"] == "simple":
            faux_negatifs.append(q["question"])

    correct = sum(1 for q, r in zip(QUESTIONS, results_cascade) if r["routing"]["complexite"] == q["attendu"])
    print(f"\nPrécision : {correct}/15 ({correct/15*100:.0f}%)")
    print(f"Faux positifs (simple alors que complexe) : {len(faux_positifs)}")
    print(f"Faux négatifs (complexe alors que simple) : {len(faux_negatifs)}")

    if faux_positifs:
        print("\n⚠ FAUX POSITIFS (pire cas — question complexe routée vers Haiku) :")
        for fp in faux_positifs:
            print(f"  - {fp}")
    if faux_negatifs:
        print("\n⚠ FAUX NÉGATIFS (gaspillage — question simple envoyée à Sonnet) :")
        for fn in faux_negatifs:
            print(f"  - {fn}")

    # --- Sauvegarder les résultats ---
    output = {
        "baseline": results_baseline,
        "cascade": results_cascade,
        "summary": {
            "baseline_cost": total_baseline_cost,
            "cascade_cost": total_cascade_cost,
            "economie_pct": round(economie_pct, 1),
            "baseline_latency_avg_ms": round(avg_baseline_latency, 0),
            "cascade_latency_avg_ms": round(avg_cascade_latency, 0),
            "haiku_calls": haiku_calls,
            "sonnet_calls": sonnet_calls,
            "classification_accuracy": f"{correct}/15",
            "faux_positifs": faux_positifs,
            "faux_negatifs": faux_negatifs,
        },
    }
    output_path = os.path.join(os.path.dirname(__file__), "results_cascade.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nRésultats sauvegardés dans {output_path}")

    return output


if __name__ == "__main__":
    run_benchmark()
