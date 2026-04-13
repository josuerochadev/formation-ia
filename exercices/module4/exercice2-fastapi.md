# Exercice 2 — Exposer votre agent via FastAPI

**Matériel** : `pip install fastapi uvicorn`

---

## Étape 1 — Créer l'API

Fichier : [`rag/api.py`](rag/api.py)

- **POST /ask** : reçoit une question en JSON, appelle `rag_query()`, retourne la réponse avec les sources et la durée de traitement
- **GET /health** : vérification de l'état de l'API
- Modèles Pydantic pour la validation des entrées/sorties

## Étape 2 — Tester via Swagger

Lancement : `uvicorn api:app --reload` puis http://localhost:8000/docs

| Test | Endpoint | Statut | Réponse OK ? | Durée |
| --- | --- | --- | --- | --- |
| Question corpus (droits RGPD) | POST /ask | 200 | Oui — 6 droits listés, sources citées (scores 0.72-0.76) | 7.9s |
| Question hors corpus (action Apple) | POST /ask | 200 | Oui — "Je ne peux pas fournir d'informations..." (scores ~0.28) | 3.2s |
| Santé | GET /health | 200 | `{"status": "ok"}` | <1ms |

## Étape 3 — Authentification

Header `X-API-Key` obligatoire sur le endpoint `/ask`.

| Test | Header | Statut attendu | Statut obtenu |
| --- | --- | --- | --- |
| Sans clé | — | 403 | 403 — `"Clé API invalide ou manquante."` |
| Avec clé valide | `X-API-Key: cnil-rag-secret-key` | 200 | 200 — réponse complète |

La clé API est configurable via la variable d'environnement `API_KEY`.

## Livrable

- `api.py` fonctionnel avec 2 endpoints (POST /ask, GET /health)
- Authentification par X-API-Key (403 sans clé, 200 avec)
- Tests Swagger documentés ci-dessus
