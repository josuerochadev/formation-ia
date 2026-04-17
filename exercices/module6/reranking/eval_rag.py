"""
Exercice 4 — Évaluation du re-ranking Cohere sur le RAG CNIL.

Compare les métriques MRR et recall@k avec et sans re-ranker
sur l'eval set de 10 questions CNIL.
"""

import json
import os
import sys
import time

# Ajouter le chemin du RAG module4 au path
RAG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "module4", "rag")
sys.path.insert(0, RAG_DIR)
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from vectorstore import rechercher as rechercher_vectoriel
from rerank import rerank, _get_cohere_client


# --- Métriques ---
def mrr(positions: list[int]) -> float:
    """Mean Reciprocal Rank. positions[i] = rang du doc attendu (0 si absent)."""
    return sum(1 / p if p > 0 else 0 for p in positions) / len(positions)


def recall_at_k(positions: list[int], k: int) -> float:
    """Recall@k : proportion de questions où le doc attendu est dans le top-k."""
    return sum(1 for p in positions if 0 < p <= k) / len(positions)


def trouver_position(chunks: list[dict], document_attendu: str) -> int:
    """
    Trouve la position (1-indexed) du chunk provenant du document attendu.
    Retourne 0 si le document n'est pas dans les résultats.
    """
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "")
        if document_attendu.lower() in source.lower():
            return i
    return 0


def run_evaluation():
    """Exécute l'évaluation complète avec et sans re-ranking."""
    # Charger l'eval set
    eval_path = os.path.join(os.path.dirname(__file__), "eval_set.json")
    with open(eval_path, "r", encoding="utf-8") as f:
        eval_set = json.load(f)

    cohere_client = _get_cohere_client()

    N_VECTORIEL = 20  # top-20 pour le re-ranking
    N_RERANK = 3      # top-3 après re-ranking
    N_BASELINE = 10   # top-10 pour la baseline

    positions_baseline = []
    positions_reranked = []
    latencies_baseline = []
    latencies_reranked = []

    print("=" * 90)
    print("ÉVALUATION RAG : VECTORIEL SEUL vs VECTORIEL + RERANKER COHERE")
    print("=" * 90)

    for item in eval_set:
        q = item["question"]
        doc_attendu = item["document_attendu"]
        print(f"\n{'─'*90}")
        print(f"Q{item['id']}: {q}")
        print(f"Document attendu : {doc_attendu}")

        # --- Baseline : recherche vectorielle seule (top-10) ---
        t0 = time.time()
        chunks_vectoriel = rechercher_vectoriel(q, n=N_BASELINE)
        latency_base = (time.time() - t0) * 1000
        latencies_baseline.append(latency_base)

        pos_base = trouver_position(chunks_vectoriel, doc_attendu)
        positions_baseline.append(pos_base)

        print(f"  Vectoriel top-10 : position = {pos_base if pos_base > 0 else 'absent'} "
              f"({latency_base:.0f}ms)")
        if chunks_vectoriel:
            for i, c in enumerate(chunks_vectoriel[:5], 1):
                marker = " ◄" if doc_attendu.lower() in c.get("source", "").lower() else ""
                print(f"    {i}. {c['source']} (p.{c['page']}, score={c['score']}){marker}")

        # --- Avec re-ranking : top-20 vectoriel → rerank top-3 ---
        t0 = time.time()
        chunks_20 = rechercher_vectoriel(q, n=N_VECTORIEL)
        reranked = rerank(q, chunks_20, top_n=N_RERANK, client=cohere_client)
        latency_rerank = (time.time() - t0) * 1000
        latencies_reranked.append(latency_rerank)

        pos_rerank = trouver_position(reranked, doc_attendu)
        positions_reranked.append(pos_rerank)

        print(f"  Reranked top-3   : position = {pos_rerank if pos_rerank > 0 else 'absent'} "
              f"({latency_rerank:.0f}ms)")
        for i, c in enumerate(reranked, 1):
            marker = " ◄" if doc_attendu.lower() in c.get("source", "").lower() else ""
            print(f"    {i}. {c['source']} (p.{c['page']}, rerank={c.get('rerank_score', '?')}){marker}")

        time.sleep(0.3)  # rate limit Cohere

    # --- Tableau comparatif ---
    print(f"\n{'='*90}")
    print("TABLEAU COMPARATIF")
    print(f"{'='*90}")

    mrr_base = mrr(positions_baseline)
    mrr_rerank = mrr(positions_reranked)
    r1_base = recall_at_k(positions_baseline, 1)
    r1_rerank = recall_at_k(positions_reranked, 1)
    r3_base = recall_at_k(positions_baseline, 3)
    r3_rerank = recall_at_k(positions_reranked, 3)
    r10_base = recall_at_k(positions_baseline, 10)
    r10_rerank = recall_at_k(positions_reranked, 3)  # reranked n'a que 3 résultats
    avg_lat_base = sum(latencies_baseline) / len(latencies_baseline)
    avg_lat_rerank = sum(latencies_reranked) / len(latencies_reranked)

    # Coût Cohere rerank : ~$1.00 / 1000 recherches
    cost_rerank_per_query = 1.00 / 1000

    print(f"\n{'Métrique':<25} {'Vecteur seul':<20} {'+ Reranker Cohere':<20} {'Gain absolu'}")
    print("─" * 85)
    print(f"{'MRR sur top-10':<25} {mrr_base:<20.4f} {mrr_rerank:<20.4f} {mrr_rerank - mrr_base:+.4f}")
    print(f"{'Recall@1':<25} {r1_base:<20.2%} {r1_rerank:<20.2%} {r1_rerank - r1_base:+.2%}")
    print(f"{'Recall@3':<25} {r3_base:<20.2%} {r3_rerank:<20.2%} {r3_rerank - r3_base:+.2%}")
    print(f"{'Recall@10':<25} {r10_base:<20.2%} {r10_rerank:<20.2%} {r10_rerank - r10_base:+.2%}")
    print(f"{'Latence moy (ms)':<25} {avg_lat_base:<20.0f} {avg_lat_rerank:<20.0f} {avg_lat_rerank - avg_lat_base:+.0f}")
    print(f"{'Coût / requête ($)':<25} {'$0.000000':<20} {f'${cost_rerank_per_query:.6f}':<20} {f'+${cost_rerank_per_query:.6f}'}")

    # --- Détail par question ---
    print(f"\n{'='*90}")
    print("DÉTAIL PAR QUESTION")
    print(f"{'='*90}")
    print(f"\n{'#':<4} {'Question':<50} {'Pos base':<12} {'Pos rerank':<12} {'Amélioration'}")
    print("─" * 90)
    for item, pb, pr in zip(eval_set, positions_baseline, positions_reranked):
        q_short = item["question"][:47] + "..." if len(item["question"]) > 47 else item["question"]
        pb_str = str(pb) if pb > 0 else "absent"
        pr_str = str(pr) if pr > 0 else "absent"
        if pr > 0 and pb > 0:
            delta = f"+{pb - pr}" if pb > pr else ("=" if pb == pr else f"{pb - pr}")
        elif pr > 0 and pb == 0:
            delta = "récupéré !"
        elif pr == 0 and pb > 0:
            delta = "perdu !"
        else:
            delta = "—"
        print(f"{item['id']:<4} {q_short:<50} {pb_str:<12} {pr_str:<12} {delta}")

    # --- Sauvegarder ---
    output = {
        "positions_baseline": positions_baseline,
        "positions_reranked": positions_reranked,
        "metrics": {
            "mrr_baseline": round(mrr_base, 4),
            "mrr_reranked": round(mrr_rerank, 4),
            "recall_at_1_baseline": round(r1_base, 4),
            "recall_at_1_reranked": round(r1_rerank, 4),
            "recall_at_3_baseline": round(r3_base, 4),
            "recall_at_3_reranked": round(r3_rerank, 4),
            "recall_at_10_baseline": round(r10_base, 4),
            "avg_latency_baseline_ms": round(avg_lat_base, 0),
            "avg_latency_reranked_ms": round(avg_lat_rerank, 0),
            "cost_rerank_per_query": cost_rerank_per_query,
        },
        "eval_set": eval_set,
    }
    output_path = os.path.join(os.path.dirname(__file__), "results_reranking.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nRésultats sauvegardés dans {output_path}")

    return output


if __name__ == "__main__":
    run_evaluation()
