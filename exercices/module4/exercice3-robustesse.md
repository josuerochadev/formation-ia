# Exercice 3 — Rendre l'agent robuste en production

## Etape 1 — Provoquer les erreurs (AVANT protections)

| Scenario            | Comment le provoquer                          | Comportement observe          | Acceptable ? |
|---------------------|-----------------------------------------------|-------------------------------|--------------|
| Timeout LLM         | Couper la connexion / timeout=0.001           | Exception non geree, 500      | Non          |
| Cle API invalide    | Changer temporairement OPENAI_API_KEY         | AuthenticationError, 500      | Non          |
| Question vide       | `{"question": ""}`                            | Envoi au LLM quand meme, 500 | Non          |
| Question tres longue| Texte de 10 000 mots                          | Token overflow, cout eleve    | Non          |
| Caracteres speciaux | `{"question": "'; DROP TABLE --"}`            | Passe tel quel au LLM        | Acceptable   |
| Requetes rapides    | 10 requetes en 1 seconde                      | Toutes traitees, pas de limite| Non          |

## Etape 2 — Protections implementees

1. **Retry avec backoff exponentiel** sur l'appel LLM (3 tentatives, facteur x2)
2. **Timeout** sur l'appel OpenAI (30s)
3. **Validation input** : question non vide, longueur max 2000 caracteres
4. **Rate limiting** : max 10 requetes / minute par cle API
5. **Gestion erreurs API** : catch AuthenticationError, Timeout, APIError avec messages clairs

## Etape 3 — Re-test (APRES protections)

| Scenario            | Avant fix                    | Apres fix                                  | Bloque ? |
|---------------------|------------------------------|--------------------------------------------|----------|
| Timeout             | Exception 500                | Retry x3 puis 504 Gateway Timeout          | Non      |
| Cle invalide        | AuthenticationError 500      | 502 "Erreur d'authentification OpenAI"     | Non      |
| Question vide       | Envoi au LLM quand meme     | 422 "La question ne peut pas etre vide"    | Non      |
| Question longue     | Token overflow               | 422 "Question trop longue (max 2000 car.)" | Non      |
| Caracteres speciaux | Passe au LLM                 | Passe au LLM (pas de risque SQL/XSS)      | Non      |
| Requetes rapides    | Toutes traitees              | 429 "Trop de requetes" apres 10/min        | Non      |

## Livrable

- `test_robustesse.py` : script de test des 6 scenarios
- `api.py` : protections integrees (validation, rate limit, error handling)
- `query.py` : retry + timeout sur l'appel LLM
