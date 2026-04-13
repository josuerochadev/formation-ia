"""
Exercice 2 — Exposer le pipeline RAG via FastAPI.
Endpoints : POST /ask, GET /health
Authentification par X-API-Key.
"""
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from query import rag_query

load_dotenv()

API_KEY = os.getenv("API_KEY", "cnil-rag-secret-key")

app = FastAPI(
    title="API RAG — Corpus CNIL",
    description="Pipeline RAG sur les documents CNIL (RGPD, sécurité des données).",
    version="1.0.0",
)


# --- Modèles Pydantic ---

class QuestionRequest(BaseModel):
    question: str
    n_chunks: int = 3


class SourceInfo(BaseModel):
    texte: str
    source: str
    page: int
    score: float


class AnswerResponse(BaseModel):
    reponse: str
    sources: list[str]
    chunks_utilises: list[SourceInfo]
    duree_secondes: float


# --- Authentification ---

def _verifier_api_key(x_api_key: str | None):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide ou manquante.")


# --- Endpoints ---

@app.get("/health")
def health():
    """Vérification de l'état de l'API."""
    return {"status": "ok"}


@app.post("/ask", response_model=AnswerResponse)
def ask(req: QuestionRequest, x_api_key: str | None = Header(default=None)):
    """
    Pose une question au pipeline RAG.
    Nécessite le header X-API-Key.
    """
    _verifier_api_key(x_api_key)

    debut = time.time()
    resultat = rag_query(req.question, n_chunks=req.n_chunks)
    duree = round(time.time() - debut, 3)

    return AnswerResponse(
        reponse=resultat["reponse"],
        sources=resultat["sources"],
        chunks_utilises=[
            SourceInfo(
                texte=c["texte"][:300],
                source=c["source"],
                page=c["page"],
                score=c["score"],
            )
            for c in resultat["chunks_utilises"]
        ],
        duree_secondes=duree,
    )
