"""
Exercice 3 — Cascade Haiku / Sonnet (router).

Router les requêtes vers le bon modèle selon leur complexité.
Haiku classifie l'intent ; seules les requêtes complexes sont escaladées vers Sonnet.
"""

import os
import json
import time
import logging
from dotenv import load_dotenv
import anthropic

load_dotenv()

logger = logging.getLogger(__name__)

# --- Modèles ---
MODEL_HAIKU = "claude-3-5-haiku-20241022"
MODEL_SONNET = "claude-sonnet-4-20250514"

# --- Prompt de classification ---
PROMPT_ROUTER = """Classe cette requête utilisateur.
Réponds UNIQUEMENT en JSON avec les clés complexite et categorie.
- complexite = simple si : salutation, FAQ, reformulation, lookup direct
- complexite = complexe si : raisonnement multi-étapes, synthèse, code, analyse
- categorie = salutation | faq | raisonnement | code | analyse

Requête : {question}"""


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY manquante dans .env")
    return anthropic.Anthropic(api_key=api_key)


def classifier_intent(question: str, client: anthropic.Anthropic = None) -> dict:
    """
    Appelle Haiku pour classifier la complexité et catégorie d'une requête.

    Returns:
        dict avec clés "complexite" (simple|complexe) et "categorie".
        Fallback vers "complexe" si le parsing JSON échoue.
    """
    if client is None:
        client = _get_client()

    start = time.time()
    response = client.messages.create(
        model=MODEL_HAIKU,
        max_tokens=100,
        messages=[{"role": "user", "content": PROMPT_ROUTER.format(question=question)}],
    )
    latency_ms = (time.time() - start) * 1000

    texte = response.content[0].text.strip()
    usage = response.usage

    # Parsing JSON avec fallback
    try:
        result = json.loads(texte)
    except json.JSONDecodeError:
        # Tenter d'extraire le JSON depuis un bloc markdown
        import re
        match = re.search(r"\{.*\}", texte, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                result = {"complexite": "complexe", "categorie": "raisonnement"}
        else:
            result = {"complexite": "complexe", "categorie": "raisonnement"}

    # Valider les clés
    if "complexite" not in result or result["complexite"] not in ("simple", "complexe"):
        result["complexite"] = "complexe"
    if "categorie" not in result:
        result["categorie"] = "raisonnement"

    result["_router_latency_ms"] = round(latency_ms, 1)
    result["_router_tokens"] = {
        "input": usage.input_tokens,
        "output": usage.output_tokens,
    }

    return result


def appeler_llm_anthropic(
    question: str,
    model: str = MODEL_SONNET,
    client: anthropic.Anthropic = None,
    system_prompt: str = "Tu es un assistant expert en technologie. Réponds en français, de façon concise et précise.",
) -> dict:
    """
    Appelle un modèle Anthropic et retourne la réponse + métadonnées.

    Returns:
        dict avec clés: reponse, model, latency_ms, tokens.
    """
    if client is None:
        client = _get_client()

    start = time.time()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}],
    )
    latency_ms = (time.time() - start) * 1000
    usage = response.usage

    return {
        "reponse": response.content[0].text.strip(),
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "tokens": {
            "input": usage.input_tokens,
            "output": usage.output_tokens,
        },
    }


def repondre(question: str, client: anthropic.Anthropic = None) -> dict:
    """
    Cascade Haiku → Sonnet.
    Haiku classifie ; si simple → Haiku répond, sinon → Sonnet.

    Returns:
        dict avec: reponse, routing, model_used, latency_total_ms, tokens_total, cost.
    """
    if client is None:
        client = _get_client()

    # Étape 1 : classification par Haiku
    routing = classifier_intent(question, client=client)
    model_used = MODEL_HAIKU if routing["complexite"] == "simple" else MODEL_SONNET

    # Étape 2 : génération par le modèle choisi
    result = appeler_llm_anthropic(question, model=model_used, client=client)

    # Coûts (tarifs officiels Anthropic en $/Mtok, avril 2025)
    # Haiku : $0.80 input / $4.00 output
    # Sonnet : $3.00 input / $15.00 output
    PRICING = {
        MODEL_HAIKU: {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
        MODEL_SONNET: {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    }

    # Coût du routeur (Haiku)
    router_cost = (
        routing["_router_tokens"]["input"] * PRICING[MODEL_HAIKU]["input"]
        + routing["_router_tokens"]["output"] * PRICING[MODEL_HAIKU]["output"]
    )
    # Coût de la génération
    gen_pricing = PRICING[model_used]
    gen_cost = (
        result["tokens"]["input"] * gen_pricing["input"]
        + result["tokens"]["output"] * gen_pricing["output"]
    )

    total_tokens = {
        "input": routing["_router_tokens"]["input"] + result["tokens"]["input"],
        "output": routing["_router_tokens"]["output"] + result["tokens"]["output"],
    }

    return {
        "reponse": result["reponse"],
        "routing": {
            "complexite": routing["complexite"],
            "categorie": routing["categorie"],
        },
        "model_used": model_used,
        "latency_total_ms": round(routing["_router_latency_ms"] + result["latency_ms"], 1),
        "tokens_total": total_tokens,
        "cost_usd": round(router_cost + gen_cost, 6),
        "_detail": {
            "router_cost": round(router_cost, 6),
            "generation_cost": round(gen_cost, 6),
            "router_latency_ms": routing["_router_latency_ms"],
            "generation_latency_ms": result["latency_ms"],
        },
    }


def repondre_sans_cascade(question: str, client: anthropic.Anthropic = None) -> dict:
    """
    Baseline : tout envoyer à Sonnet (pas de routeur).
    """
    if client is None:
        client = _get_client()

    result = appeler_llm_anthropic(question, model=MODEL_SONNET, client=client)

    PRICING_SONNET = {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000}
    cost = (
        result["tokens"]["input"] * PRICING_SONNET["input"]
        + result["tokens"]["output"] * PRICING_SONNET["output"]
    )

    return {
        "reponse": result["reponse"],
        "model_used": MODEL_SONNET,
        "latency_ms": result["latency_ms"],
        "tokens": result["tokens"],
        "cost_usd": round(cost, 6),
    }


if __name__ == "__main__":
    # Test rapide
    tests = [
        "Bonjour !",
        "Explique-moi l'architecture transformer avec attention multi-têtes",
    ]
    client = _get_client()
    for q in tests:
        print(f"\n{'='*60}")
        print(f"Q: {q}")
        r = repondre(q, client=client)
        print(f"Routing: {r['routing']}")
        print(f"Model: {r['model_used']}")
        print(f"Latence: {r['latency_total_ms']}ms")
        print(f"Coût: ${r['cost_usd']}")
        print(f"Réponse: {r['reponse'][:200]}...")
