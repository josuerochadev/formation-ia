"""
Exercice 2 & 3 — API RAG robuste en production.
Endpoints : POST /ask, GET /health
Protections : validation input, rate limiting, retry, timeout, error handling.
"""
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from openai import APITimeoutError, AuthenticationError, APIError
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from query import rag_query

load_dotenv()

API_KEY = os.getenv("API_KEY", "cnil-rag-secret-key")
MAX_QUESTION_LENGTH = 2000

# --- Rate limiter ---

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="API RAG — Corpus CNIL",
    description="Pipeline RAG sur les documents CNIL (RGPD, securite des donnees).",
    version="2.0.0",
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Trop de requetes. Limite : 10/minute."},
    )


# --- Modeles Pydantic ---

class QuestionRequest(BaseModel):
    question: str
    n_chunks: int = 3

    @field_validator("question")
    @classmethod
    def question_non_vide(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La question ne peut pas etre vide.")
        if len(v) > MAX_QUESTION_LENGTH:
            raise ValueError(
                f"Question trop longue ({len(v)} car.). Maximum : {MAX_QUESTION_LENGTH}."
            )
        return v


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
        raise HTTPException(status_code=403, detail="Cle API invalide ou manquante.")


# --- Endpoints ---

@app.get("/health")
def health():
    """Verification de l'etat de l'API."""
    return {"status": "ok"}


@app.post("/ask", response_model=AnswerResponse)
@limiter.limit("10/minute")
def ask(request: Request, req: QuestionRequest, x_api_key: str | None = Header(default=None)):
    """
    Pose une question au pipeline RAG.
    Necessite le header X-API-Key.
    """
    _verifier_api_key(x_api_key)

    debut = time.time()

    try:
        resultat = rag_query(req.question, n_chunks=req.n_chunks)
    except AuthenticationError:
        raise HTTPException(
            status_code=502,
            detail="Erreur d'authentification OpenAI. Verifiez la cle API.",
        )
    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Le LLM n'a pas repondu dans le delai imparti (timeout). Reessayez.",
        )
    except APIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur API OpenAI : {e.message}",
        )

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
