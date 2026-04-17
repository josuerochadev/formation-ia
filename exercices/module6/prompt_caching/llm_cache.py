"""
M6E2 — Étape 2 : Client LLM avec prompt caching Anthropic.

Règle d'or : ordonner du plus stable au plus variable.
  1. system prompt (stable)     → cache_control: ephemeral
  2. tools definition (stable)  → cache_control: ephemeral sur le dernier tool
  3. messages (variable)        → PAS de cache

Maximum 4 breakpoints cache_control par requête.
Seuil minimum : 1024 tokens (Sonnet). TTL : 5 minutes.
"""
from anthropic import Anthropic
from config import (
    ANTHROPIC_API_KEY, MODEL, MAX_TOKENS,
    SYSTEM_PROMPT_LONG, TOOLS_DEFINITION,
)

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_tools_with_cache() -> list[dict]:
    """Ajoute cache_control sur le dernier tool (breakpoint #2)."""
    tools = []
    for i, tool in enumerate(TOOLS_DEFINITION):
        t = dict(tool)
        if i == len(TOOLS_DEFINITION) - 1:
            # Breakpoint cache sur le dernier tool = tout ce qui précède est caché
            t["cache_control"] = {"type": "ephemeral"}
        tools.append(t)
    return tools


# Pré-construit une seule fois (immuable entre les appels)
TOOLS_CACHED = _build_tools_with_cache()

SYSTEM_CACHED = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT_LONG,
        "cache_control": {"type": "ephemeral"},  # Breakpoint #1
    }
]


def appeler_llm_cache(user_message: str, history: list[dict] | None = None):
    """
    Appelle Claude avec prompt caching activé.

    Args:
        user_message: Message utilisateur courant.
        history: Historique de conversation (optionnel).

    Returns:
        (response, usage) — la réponse complète et les métriques d'usage.
    """
    if history is None:
        history = []

    messages = history + [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_CACHED,
        tools=TOOLS_CACHED,
        messages=messages,
    )

    return response, response.usage
