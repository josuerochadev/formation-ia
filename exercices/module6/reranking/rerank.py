"""
Exercice 4 — Re-ranking Cohere sur le RAG CNIL.

Ajoute un re-ranker Cohere après la recherche vectorielle ChromaDB
pour améliorer la précision (MRR, recall@k).
"""

import os
import cohere
from dotenv import load_dotenv

load_dotenv()


def _get_cohere_client() -> cohere.Client:
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise ValueError("COHERE_API_KEY manquante dans .env")
    return cohere.Client(api_key=api_key)


def rerank(question: str, chunks: list[dict], top_n: int = 3, client: cohere.Client = None) -> list[dict]:
    """
    Re-rank les chunks avec Cohere rerank-multilingual-v3.0.

    Args:
        question: La requête utilisateur.
        chunks: Liste de dicts avec au minimum une clé "texte".
        top_n: Nombre de résultats à retourner.
        client: Client Cohere (créé automatiquement si None).

    Returns:
        Les top_n chunks rerankés, enrichis d'un score "rerank_score".
    """
    if client is None:
        client = _get_cohere_client()

    if not chunks:
        return []

    docs = [c["texte"] for c in chunks]

    result = client.rerank(
        model="rerank-multilingual-v3.0",
        query=question,
        documents=docs,
        top_n=top_n,
    )

    reranked = []
    for r in result.results:
        chunk = chunks[r.index].copy()
        chunk["rerank_score"] = round(r.relevance_score, 4)
        reranked.append(chunk)

    return reranked
