# Exercice 1 — Tests unitaires des tools de l'agent

## Objectif

Mettre en place une suite de tests unitaires deterministes pour **tous les tools** du fil-rouge,
executables en boucle sans cle API, sans reseau, en < 5 secondes.

---

## Cartographie de l'environnement de tests

### Fichiers de test dans `fil-rouge/tests/`

| Fichier | Module | Type | Appelle le LLM ? | Executable via pytest ? |
|---|---|---|---|---|
| `test_tools.py` | **M5E1** | Unitaire | Non (0 appel API) | Oui — **58 tests, < 4s** |
| `test_security.py` | M4E5 | Unitaire | Non | Oui — 27 tests |
| `test_llm_json.py` | M3E2 | Integration | Oui (4 appels API) | Oui mais couteux |
| `test_memory.py` | M3E4 | Integration | Oui (5+ appels API) | Oui mais couteux |
| `test_agent_debug.py` | M3E5 | Integration | Oui (4 appels API) | Oui mais couteux |
| `test_rag.py` | M3 | Integration | Oui (embeddings) | Oui mais necessite un index |
| `test_email.py` | M3 | Integration | Non | Semi (script, pas de fonctions `test_`) |
| `conftest.py` | — | Config | — | Configure `sys.path` + fixtures partagees |

### 2 categories distinctes

1. **Tests deterministes** (gratuits, rapides, lancables en boucle) :
   - `test_tools.py` — 58 tests couvrant les 6 modules tools
   - `test_security.py` — 27 tests couvrant injection, SQL, filtrage sortie
   - **Total : 85 tests en < 5s sans cle API**

2. **Tests avec appels LLM** (couteux, non deterministes) :
   - `test_llm_json.py`, `test_memory.py`, `test_agent_debug.py`, `test_rag.py`, `test_email.py`
   - Necessitent `OPENAI_API_KEY` et/ou des donnees pre-indexees

---

## Ce qui a ete ajuste

### 1. `conftest.py` — fixture d'isolation `data_dir`

**Probleme** : les fonctions de `database.py` ecrivent dans `fil-rouge/data/` (articles, archives, logs, SQLite). Lancer les tests risquait de polluer les vraies donnees.

**Solution** : une fixture `data_dir` qui :
- Cree un repertoire temporaire via `tmp_path` (detruit automatiquement par pytest)
- Patche **tous les chemins** de `config.py` et `tools/database.py` pour pointer vers ce repertoire
- Restaure les valeurs originales apres chaque test

```python
@pytest.fixture
def data_dir(tmp_path):
    import config
    config.DATA_DIR = str(tmp_path)
    config.ARTICLES_FILE = str(tmp_path / "articles.json")
    # ... (tous les chemins)
    yield tmp_path
    # Restore automatique
```

### 2. `conftest.py` — fixture `sample_articles`

Jeu de 3 articles fictifs reutilisable par tous les tests :
- 1 article IA (pertinence 9) — cas nominal
- 1 article Cloud (pertinence 7) — cas de filtrage
- 1 article Hors-sujet (pertinence 1) — cas d'exclusion

### 3. `test_tools.py` — de 8 a 58 tests

Organisation en classes par domaine fonctionnel, avec la methodologie **nominal / vide / erreur** :

| Classe | Module teste | Nb tests | Ce qui est verifie |
|---|---|---|---|
| `TestQueryDb` | `database.py` — `query_db` | 8 | SELECT, filtres, refus DELETE/UPDATE, erreur SQL |
| `TestChargerSauvegarderJson` | `database.py` — persistence | 3 | Fichier absent, round-trip, unicode |
| `TestArticles` | `database.py` — articles | 5 | Sauvegarde, deduplication, `article_deja_traite`, archivage, archivage vide |
| `TestHistoriqueEtLogs` | `database.py` — historique | 4 | Enregistrement envoi, multi-envois, logs JSONL |
| `TestSearchWeb` | `search.py` — `search_web` | 6 | 4 categories de mots-cles, fallback generique, structure retour |
| `TestFiltrerParTheme` | `search.py` — `filtrer_par_theme` | 5 | Filtrage positif, IA, aucun match, case-insensitive, liste vide |
| `TestEmailHelpers` | `email.py` — `_etoiles`, `_badge` | 6 | Max, zero, milieu, negatif, badge IA, badge inconnu |
| `TestGenererHtml` | `email.py` — `generer_html` | 4 | Contenu, structure HTML, liste vide, hors-sujet non filtre |
| `TestGenererTexte` | `email.py` — `generer_texte` | 3 | Contenu, format texte, liste vide |
| `TestRagUtils` | `rag.py` — utilitaires | 8 | Score fraicheur (4 cas), article_id (2 cas), index persistence (2 cas) |
| `TestTranscribeValidation` | `transcribe.py` — validation | 3 | Fichier absent, format invalide, format ok sans cle API |
| `TestVisionValidation` | `vision.py` — validation | 3 | Fichier absent, format invalide, format ok sans cle API |

### 4. Strategie de mock

Un seul mock dans toute la suite : `tools.rag.indexer_articles` dans les tests d'articles.

**Pourquoi ?** `sauvegarder_articles()` appelle `indexer_articles()` qui fait un appel API OpenAI pour les embeddings. On mocke uniquement ce point de contact pour garder les tests gratuits.

```python
with patch("tools.rag.indexer_articles", return_value=2):
    nb = sauvegarder_articles(sample_articles[:2])
```

**Piege rencontre** : `indexer_articles` est importe localement dans `sauvegarder_articles` (`from tools.rag import indexer_articles`), donc il faut patcher `tools.rag.indexer_articles` et non `tools.database.indexer_articles`.

---

## Fonctions testables vs non testables (sans API)

### Testable sans appel API (couvert par M5E1)

| Module | Fonctions couvertes |
|---|---|
| `database.py` | `query_db`, `charger_json`, `sauvegarder_json`, `article_deja_traite`, `sauvegarder_articles`, `enregistrer_envoi`, `archiver_articles_traites`, `ajouter_log` |
| `search.py` | `search_web` (banque simulee), `filtrer_par_theme` |
| `email.py` | `generer_html`, `generer_texte`, `_etoiles`, `_badge` |
| `rag.py` | `_score_fraicheur`, `_article_id`, `taille_index`, `vider_index` |
| `transcribe.py` | Validation entree (fichier absent, format invalide) |
| `vision.py` | Validation entree (fichier absent, format invalide) |

### Necessite l'API (hors perimetre M5E1)

| Module | Fonctions | API requise |
|---|---|---|
| `rag.py` | `indexer_articles`, `rechercher_articles` | OpenAI Embeddings |
| `transcribe.py` | `transcrire_audio` (apres validation) | Whisper API |
| `vision.py` | `analyser_image` (apres validation) | GPT-4o Vision |

---

## Execution

```bash
# Tests unitaires uniquement (gratuit, rapide)
cd fil-rouge && python -m pytest tests/test_tools.py tests/test_security.py -v

# Resultat attendu : 85 passed in < 5s

# Tests tools seuls
python -m pytest tests/test_tools.py -v
# 58 passed in ~4s
```

---

## Resultat

```
58 passed in 3.96s
```

Couverture des tools du fil-rouge passee de **1 module sur 6** (query_db seul) a **6 modules sur 6**, avec 58 tests deterministes executables sans cle API.
