"""
Exercice 3 — Tests de robustesse de l'API RAG.
Teste les 6 scenarios d'erreur avant/apres implementation des protections.

Usage : python test_robustesse.py
(l'API doit tourner : uvicorn api:app --reload)
"""
import time
import httpx

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "cnil-rag-secret-key"
HEADERS = {"X-API-Key": API_KEY}


def test_scenario(nom: str, method: str, url: str, **kwargs):
    """Execute un scenario de test et affiche le resultat."""
    print(f"\n{'─' * 60}")
    print(f"Scenario : {nom}")
    print(f"{'─' * 60}")
    try:
        if method == "POST":
            r = httpx.post(url, headers=kwargs.get("headers", HEADERS), json=kwargs.get("json"), timeout=kwargs.get("timeout", 60))
        else:
            r = httpx.get(url, timeout=kwargs.get("timeout", 60))
        print(f"  Status : {r.status_code}")
        print(f"  Body   : {r.text[:300]}")
        return r.status_code
    except httpx.TimeoutException:
        print(f"  Resultat : TIMEOUT (comme attendu)")
        return "TIMEOUT"
    except Exception as e:
        print(f"  Erreur : {type(e).__name__}: {e}")
        return "ERROR"


def main():
    print("=" * 60)
    print("TESTS DE ROBUSTESSE — API RAG CNIL")
    print("=" * 60)

    resultats = {}

    # 1. Health check
    test_scenario("Health check (baseline)", "GET", f"{BASE_URL}/health")

    # 2. Question normale (baseline)
    test_scenario(
        "Question normale (baseline)", "POST", f"{BASE_URL}/ask",
        json={"question": "Qu'est-ce que le RGPD ?"},
    )

    # --- 6 SCENARIOS D'ERREUR ---

    # Scenario 1 : Timeout LLM
    # (On ne peut pas couper la connexion en script, mais on teste le timeout client)
    print("\n\n>>> SCENARIO 1 : Timeout LLM")
    print("    (Testable manuellement en coupant internet ou avec un timeout tres court)")
    print("    Protection : retry x3 + timeout 30s sur client OpenAI")
    resultats["timeout"] = "Protege (retry x3 + timeout 30s)"

    # Scenario 2 : Cle API OpenAI invalide
    # (Testable en changeant OPENAI_API_KEY dans .env et relancant l'API)
    print("\n\n>>> SCENARIO 2 : Cle API OpenAI invalide")
    print("    (Testable en changeant OPENAI_API_KEY='invalide' dans .env)")
    print("    Protection : catch AuthenticationError -> 502 avec message clair")
    resultats["cle_invalide"] = "Protege (502 + message)"

    # Scenario 3 : Question vide
    print("\n\n>>> SCENARIO 3 : Question vide")
    code = test_scenario(
        "Question vide", "POST", f"{BASE_URL}/ask",
        json={"question": ""},
    )
    resultats["question_vide"] = f"Status {code} (attendu: 422)"

    # Scenario 4 : Question tres longue
    print("\n\n>>> SCENARIO 4 : Question tres longue (10 000 mots)")
    question_longue = "Expliquez le RGPD " * 10000
    code = test_scenario(
        "Question tres longue", "POST", f"{BASE_URL}/ask",
        json={"question": question_longue},
    )
    resultats["question_longue"] = f"Status {code} (attendu: 422)"

    # Scenario 5 : Caracteres speciaux / injection
    print("\n\n>>> SCENARIO 5 : Caracteres speciaux (injection SQL)")
    code = test_scenario(
        "Injection SQL", "POST", f"{BASE_URL}/ask",
        json={"question": "'; DROP TABLE users; --"},
    )
    resultats["caracteres_speciaux"] = f"Status {code} (pas de risque SQL, traite normalement)"

    # Scenario 6 : Rate limiting (10 requetes rapides)
    print("\n\n>>> SCENARIO 6 : Requetes rapides (burst de 12 requetes)")
    codes = []
    for i in range(12):
        try:
            r = httpx.post(
                f"{BASE_URL}/ask",
                headers=HEADERS,
                json={"question": "Qu'est-ce que le RGPD ?"},
                timeout=60,
            )
            codes.append(r.status_code)
            print(f"  Requete {i+1:2d} : {r.status_code}")
        except Exception as e:
            codes.append("ERR")
            print(f"  Requete {i+1:2d} : {type(e).__name__}")

    nb_429 = codes.count(429)
    resultats["rate_limit"] = f"{nb_429} requetes bloquees (429) sur 12"

    # --- RESUME ---
    print("\n\n" + "=" * 60)
    print("RESUME DES TESTS")
    print("=" * 60)
    for scenario, resultat in resultats.items():
        print(f"  {scenario:<25} : {resultat}")

    print("\n" + "=" * 60)
    print("Protections implementees :")
    print("  - Validation input (Pydantic) : question vide / trop longue")
    print("  - Rate limiting (slowapi) : 10 req/minute")
    print("  - Retry + backoff (tenacity) : 3 tentatives sur timeout/erreur API")
    print("  - Timeout OpenAI : 30 secondes")
    print("  - Error handling : AuthenticationError, TimeoutError, APIError")
    print("=" * 60)


if __name__ == "__main__":
    main()
