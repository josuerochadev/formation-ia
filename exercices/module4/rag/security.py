"""
Module de securite pour l'API RAG CNIL.
Exercice M4E5 : detection d'injections, filtrage de sortie.
Adapte du module security.py du fil-rouge.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns de prompt injection (case-insensitive)
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    r"ignore\s+(toutes?\s+)?(tes|les|vos)\s+instructions",
    r"oublie\s+(toutes?\s+)?(tes|les|vos)\s+(instructions|regles|consignes)",
    r"tu\s+es\s+maintenant",
    r"you\s+are\s+now",
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(r[eé]p[eè]te|repets|affiche|montre|donne|copie).*system\s*prompt",
    r"(repeat|show|display|reveal|print).*system\s*prompt",
    r"instructions?\s+(cach[eé]es?|secr[eè]tes?|internes?|hidden)",
    r"(ton|tes|votre|vos)\s+system\s*prompt",
    r"INSTRUCTION\s+SYST[EÈ]ME\s+PRIORITAIRE",
    r"(override|bypass|disable)\s+(security|safety|filter|restriction)",
    r"jailbreak",
    r"DAN\s*mode",
    r"(ignore|disregard)\s+(the\s+)?(above|previous|prior)",
    # Specifiques au RAG : tentatives de sortir du contexte CNIL
    r"oublie\s+(le\s+)?contexte",
    r"ne\s+tiens?\s+(pas\s+)?compte\s+du\s+contexte",
    r"r[eé]ponds?\s+(sans|hors)\s+(du\s+)?contexte",
]

# Patterns de donnees sensibles a masquer en sortie
# Ordre important : IBAN avant telephone (evite les faux positifs)
SENSITIVE_PATTERNS = [
    ("iban", r"\b[A-Z]{2}\d{2}(?:\s?[\dA-Z]{4}){2,7}(?:\s?\d{1,3})?\b", "[IBAN MASQUE]"),
    ("carte_bancaire", r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CB MASQUE]"),
    ("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL MASQUE]"),
    ("phone_fr", r"(?:(?:\+33|0)\s*[1-9])(?:[\s.-]*\d{2}){4}", "[TEL MASQUE]"),
    ("numero_secu", r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b", "[NIR MASQUE]"),
]


# ---------------------------------------------------------------------------
# Detection de prompt injection
# ---------------------------------------------------------------------------
def detecter_injection(texte: str) -> tuple[bool, str]:
    """Detecte les tentatives de prompt injection dans la question."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, texte, re.IGNORECASE):
            logger.warning(f"[SECURITE] Injection detectee — pattern: {pattern}")
            return True, pattern
    return False, ""


# ---------------------------------------------------------------------------
# Filtrage de la sortie (donnees sensibles)
# ---------------------------------------------------------------------------
def filtrer_sortie(texte: str) -> str:
    """Masque les donnees sensibles dans la reponse du LLM."""
    resultat = texte
    for nom, pattern, remplacement in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, resultat)
        if matches:
            logger.info(f"[SECURITE] {len(matches)} {nom}(s) masque(s) dans la sortie.")
        resultat = re.sub(pattern, remplacement, resultat)
    return resultat


# ---------------------------------------------------------------------------
# Analyse complete
# ---------------------------------------------------------------------------
def analyser_securite(question: str) -> dict:
    """
    Analyse de securite sur la question utilisateur.

    Returns:
        dict: bloque (bool), raison (str), type (str)
    """
    injection, pattern = detecter_injection(question)
    if injection:
        return {
            "bloque": True,
            "raison": "Tentative de prompt injection detectee. Requete bloquee.",
            "type": "injection",
        }
    return {"bloque": False, "raison": "", "type": "ok"}
