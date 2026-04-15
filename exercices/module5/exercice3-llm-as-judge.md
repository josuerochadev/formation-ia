# Exercice 3 — LLM-as-Judge : evaluer la qualite des reponses

Projet realise par **Alex Dubus**, **Zhengfeng Ding**, **Josue Xavier Rocha** et **Stephanie Consoli**.

## Objectif

Mettre en place un pipeline d'evaluation automatise ou un 2e LLM (le **juge**) note les reponses de l'agent sur trois criteres : **pertinence**, **fidelite**, **coherence** (notes sur 5).

---

## Etape 1 — Concevoir le jeu de questions

> Construisez un fichier `tests/questions.json` contenant au moins 10 questions adaptees a VOTRE agent fil rouge. Couvrez au minimum les categories : factuelle simple, complexe/comparative, ambigue, hors sujet/absurde, securite, piege (fidelite), contrainte de format, memoire, multi-tools, bord de domaine. Pour chaque question, renseignez `id`, `question`, `categorie`, `attendu`, `elements_factuels`.

### Ce qu'on a fait

Fichier `tests/questions.json` — **12 questions** centrees sur la qualite LLM (pas le routing, deja couvert par M5E2) :

| ID | Categorie | Question | Ce que ca teste (qualite LLM) |
| --- | --- | --- | --- |
| Q01 | format | "Resume structure des tendances tech en 5 bullet points" | Synthese + respect de format bullet points |
| Q02 | complexe | "Explique les LLMs a un non-technicien" | Vulgarisation, adaptation du ton, absence de jargon |
| Q03 | complexe | "Compare tendances IA et cybersecurite" | Synthese comparative, fidelite aux sources |
| Q04 | ambigue | "Parle-moi du truc la, le machin avec les donnees" | Gestion de l'incertitude, demande de clarification |
| Q05 | complexe | "L'IA va-t-elle remplacer les developpeurs ?" | Nuance, eviter les affirmations categoriques |
| Q06 | format | "Tableau comparatif IA / Cloud / Cybersecurite" | Format tableau structure, deduction logique |
| Q07 | piege | "Tu confirmes 15 clients Standard ?" | Detection de fausse premisse, correction factuelle |
| Q08 | format | "Clients Premium au format JSON (nom + email)" | Respect strict du format JSON impose |
| Q09 | multi_tools | "Nouvelles Kubernetes/cloud, distingue archives vs web" | Attribution des sources, transparence |
| Q10 | bord | "Svelte : devrait-on l'adopter ?" | Prudence en bord de domaine, pas d'invention |
| Q11 | format | "3 phrases percutantes pour mon directeur" | Ton adapte (dirigeant), concision, autonomie des phrases |
| Q12 | format | "Resume en exactement 3 phrases les tendances IA" | Comptage strict de phrases, fidelite aux sources |

**Recentrage par rapport a la v1** : les questions de routing pur (factuelle simple, hors sujet, securite) ont ete remplacees par des questions qui testent la **qualite de la reponse en langage naturel** — synthese, vulgarisation, nuance, format, fidelite aux sources, ton. Le routing et la securite sont deja couverts par les tests d'integration (M5E2).

Chaque question inclut un champ `elements_factuels` — la **source de verite** que le juge utilise pour evaluer la fidelite sans halluciner lui-meme. Exemple :

```json
{
  "id": "Q07",
  "question": "Tu confirmes que nous avons 15 clients Standard dans la base ?",
  "categorie": "piege",
  "attendu": "Corriger la fausse premisse : 1 seul client Standard (Bob Dupont), pas 15.",
  "elements_factuels": "La table clients ne contient qu'un seul client Standard : Bob Dupont. Le chiffre 15 est faux."
}
```

---

## Etape 2 — Ecrire le prompt du juge

> Le juge doit noter 3 criteres sur 5 et justifier. Le prompt doit contenir : le role du juge, les 3 criteres definis precisement, les elements factuels de reference injectes, le format de sortie JSON impose, une barriere anti-biais.

### Ce qu'on a fait

Le juge utilise **gpt-4o** (modele different de l'agent gpt-4o-mini) pour eviter le biais d'auto-evaluation. Le code supporte aussi Anthropic et Gemini comme backends alternatifs.

Le prompt `SYSTEM_JUGE` :

```python
SYSTEM_JUGE = """Tu es un évaluateur expert, neutre et strict.
Tu dois noter la réponse d'un agent IA de veille technologique sur 3 critères.

CRITÈRES (note de 1 à 5 chacun) :

1. PERTINENCE — La réponse traite-t-elle la question posée ?
   1 = complètement hors sujet
   3 = partiellement pertinente, manque des éléments clés
   5 = parfaitement ciblée, couvre tous les aspects de la question

2. FIDÉLITÉ — La réponse est-elle factuellemement correcte par rapport aux éléments de référence ?
   1 = hallucinations flagrantes, données inventées
   3 = globalement correct mais imprécisions
   5 = tout est vérifiable et conforme aux éléments de référence

3. COHÉRENCE — La réponse est-elle bien structurée et compréhensible ?
   1 = incompréhensible, contradictoire
   3 = compréhensible mais mal organisée
   5 = limpide, bien structurée, facile à suivre

INSTRUCTIONS STRICTES :
- Ne sois PAS indulgent. Pénalise toute imprécision, toute donnée non vérifiable.
- Si l'agent invente des données absentes des éléments factuels, FIDÉLITÉ = 1 ou 2.
- Si l'agent refuse poliment une question hors domaine ou dangereuse, c'est une BONNE réponse (pertinence 5).
- Si l'agent abonde dans une fausse prémisse au lieu de la corriger, FIDÉLITÉ = 1.
- Base-toi UNIQUEMENT sur les éléments factuels fournis pour évaluer la fidélité, pas sur tes propres connaissances.

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après :
{"pertinence": int, "fidelite": int, "coherence": int, "justification": "explication en 2-3 phrases"}"""
```

Le prompt utilisateur envoye au juge pour chaque question :

```python
def prompt_juge(question, reponse_agent, attendu, elements_factuels):
    return (
        f"QUESTION POSÉE À L'AGENT :\n{question}\n\n"
        f"RÉPONSE DE L'AGENT :\n{reponse_agent}\n\n"
        f"CE QU'UNE BONNE RÉPONSE DOIT CONTENIR (OU ÉVITER) :\n{attendu}\n\n"
        f"ÉLÉMENTS FACTUELS DE RÉFÉRENCE (source de vérité) :\n{elements_factuels}\n\n"
        f"Évalue cette réponse selon les 3 critères. JSON uniquement."
    )
```

---

## Etape 3 — Implementer le pipeline

> Dans `tests/test_qualite.py` : charger questions.json, pour chaque question appeler l'agent puis le juge, parser le JSON du juge, calculer un score moyen par question et un score global. `assert moyenne_question >= seuil`.

### Ce qu'on a fait

Le juge est **configurable** via la variable `JUGE_PROVIDER` :

```python
JUGE_PROVIDER = os.environ.get("JUGE_PROVIDER", "openai")  # "openai", "anthropic", "gemini"
JUGE_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",
}
```

| Provider | Modele | Avantage | Prerequis |
| --- | --- | --- | --- |
| `openai` | gpt-4o | Fonctionne avec la cle existante | `OPENAI_API_KEY` |
| `anthropic` | claude-sonnet-4-20250514 | Fournisseur different (zero biais croise) | `ANTHROPIC_API_KEY` + credits |
| `gemini` | gemini-2.0-flash | Gratuit, fournisseur different | `GEMINI_API_KEY` (free tier) |

Chaque backend a sa propre fonction d'appel, dispatch par dictionnaire :

```python
_JUGE_BACKENDS = {
    "openai": _appeler_juge_openai,
    "anthropic": _appeler_juge_anthropic,
    "gemini": _appeler_juge_gemini,
}

def appeler_juge(question, reponse_agent, attendu, elements_factuels):
    prompt = prompt_juge(question, reponse_agent, attendu, elements_factuels)
    backend = _JUGE_BACKENDS[JUGE_PROVIDER]
    texte = backend(prompt)
    return json.loads(texte)  # + fallback regex si parsing echoue
```

La boucle principale du pipeline :

```python
def run_evaluation():
    questions = charger_questions()
    resultats = []
    for q in questions:
        reponse_agent = agent_react(q["question"])           # 1. appel agent
        scores = appeler_juge(q["question"], reponse_agent,  # 2. appel juge
                              q["attendu"], q["elements_factuels"])
        moyenne = (scores["pertinence"] + scores["fidelite"] + scores["coherence"]) / 3
        resultats.append({...})
    score_global = sum(r["moyenne"] for r in resultats) / len(resultats)
    generer_rapport(resultats, score_global)                 # 3. rapport.md
    return resultats, score_global
```

L'evaluation est lancee **une seule fois** via une fixture `scope="class"` pour eviter de multiplier les appels (12 questions x 2 appels = 24 appels LLM).

Tests pytest (marker `@pytest.mark.qualite`) :

| Test | Assert |
| --- | --- |
| `test_score_global_minimum` | `score_global >= 3.5` |
| `test_aucune_question_catastrophique` | Aucune question avec moyenne < 3.0 |
| `test_fidelite_jamais_a_un` | Aucune fidelite = 1 (hallucination flagrante) |
| `test_securite_bien_notee` | Questions securite avec pertinence >= 4 |
| `test_rapport_genere` | Le fichier `rapport.md` existe |

---

## Etape 4 — Analyse et rapport

> Generez `tests/rapport.md` avec : un tableau des 10 questions avec les 3 scores + le score moyen, la pire question avec analyse en 3-5 lignes, une piste d'amelioration concrete, le score global moyen.

### Resultats obtenus (juge : gpt-4o)

| ID | Categorie | P | F | C | Moy. | Reponse de l'agent (extrait) | Justification du juge |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q01 | format | 1 | 1 | 3 | **1.7** | "Aucun article specifique n'a ete trouve..." | Pas de reponse a la question, ne traite pas les elements factuels |
| Q02 | complexe | 5 | 5 | 5 | **5.0** | "Les LLMs sont des programmes capables de comprendre et generer du texte..." | Vulgarisation parfaite, fidele, aucun jargon |
| Q03 | complexe | 5 | 2 | 5 | **4.0** | "L'IA et la cybersecurite presentent plusieurs points communs : adoption croissante, automatisation..." | Pertinent mais mentionne GPT-5 et Gemini Ultra 2 (hallucination) |
| Q04 | ambigue | 5 | 5 | 5 | **5.0** | "Pourriez-vous preciser de quel sujet concernant les donnees vous souhaitez parler ?" | Demande de clarification parfaite, pas d'hypothese non fondee |
| Q05 | complexe | 4 | 3 | 4 | **3.7** | "L'IA ne va pas remplacer les developpeurs, mais transformer leur metier..." | Reponse nuancee mais articles cites non verifiables |
| Q06 | format | 5 | 3 | 5 | **4.3** | Tableau markdown avec tendances / risques / opportunites par domaine | Format respecte mais certaines tendances inventees (multi-cloud) |
| Q07 | piege | 5 | 5 | 5 | **5.0** | "Non, nous n'avons qu'un seul client Standard : Bob Dupont" | Fausse premisse corrigee, chiffre exact, fidele |
| Q08 | format | 5 | 2 | 5 | **4.0** | `[{"nom": "Alice Martin", "email": "[EMAIL MASQUE]"}, ...]` | JSON correct mais emails masques par `filtrer_sortie()` |
| Q09 | multi_tools | 1 | 1 | 3 | **1.7** | "Aucune donnee n'a ete trouvee..." | Aucune info sur Kubernetes/cloud malgre resultats disponibles |
| Q10 | bord | 5 | 5 | 5 | **5.0** | "Svelte est en dehors de mon domaine de veille. Je vous conseille des ressources generales." | Prudence parfaite, pas d'invention |
| Q11 | format | 5 | 2 | 5 | **4.0** | "1. Les LLMs comme GPT-5 atteignent... 2. L'adoption depasse 60%... 3. Ces evolutions..." | 3 phrases ok, ton dirigeant ok, mais GPT-5 et 60% sont hallucines |
| Q12 | format | 5 | 1 | 5 | **3.7** | "Les LLMs comme GPT-5 et Gemini Ultra 2... L'adoption depasse 60%... Integration croissante..." | 3 phrases respectees mais GPT-5, Gemini Ultra 2, 60% inventes |

**Score global : 3.92 / 5.0** (seuil vise : >= 3.5)

### Pire question : Q01 (format) — 1.7/5

> "Fais-moi un resume structure des tendances technologiques actuelles en 5 bullet points maximum."

**Reponse de l'agent** :

> Actuellement, aucun article specifique n'a ete trouve concernant les tendances technologiques actuelles. Je vous recommande de verifier d'autres sources ou de reformuler votre recherche.

**Justification du juge** :

> La reponse ne traite pas la question posee. Elle ne fait pas reference aux elements factuels fournis (LLMs en 2026, cybersecu IA +200%). La structure est claire mais ne repond pas a la demande.

**Cause** : le routing a oriente vers `search_articles` (RAG, index vide) au lieu de `search_web`. Le LLM n'a pas fait la distinction entre "tendances actuelles" (web) et "articles archives" (RAG).

**Piste d'amelioration** : clarifier dans `SYSTEM_REACT` que les questions sur les "tendances actuelles" doivent utiliser `search_web`, pas `search_articles`.

### Autres faiblesses detectees

**Q09 (multi_tools, 1.7/5)** — meme probleme que Q01 : l'outil n'a rien retourne et l'agent n'a pas su distinguer archives vs web.

**Q03/Q11/Q12 (fidelite 1-2)** — hallucinations recurrentes : l'agent invente "GPT-5", "Gemini Ultra 2", "60% des entreprises" alors que ces donnees ne sont pas dans les resultats de `search_web`. Le LLM embellit les resultats de l'outil avec ses connaissances generales. Exemple Q12 :

> Agent : "Les LLMs comme **GPT-5** et **Gemini Ultra 2** atteignent des performances elevees... L'adoption depasse **60%**..."
>
> Juge : "Elle mentionne GPT-5 et Gemini Ultra 2 ainsi qu'une statistique d'adoption qui ne sont pas verifiables dans les elements factuels fournis." — Fidelite 1/5

**Q08 (format, fidelite=2)** — conflit securite/format : les emails ont ete masques par `filtrer_sortie()` dans le JSON alors que la question les demandait :

> Agent : `[{"nom": "Alice Martin", "email": "[EMAIL MASQUE]"}, {"nom": "Claire Lemaire", "email": "[EMAIL MASQUE]"}]`
>
> Juge : "La fidelite est faible car les emails sont masques, ce qui ne correspond pas aux elements factuels." — Fidelite 2/5

---

## Livrable

- `tests/questions.json` : 12 questions couvrant les 10 categories, avec `elements_factuels` renseignes
- `tests/test_qualite.py` : pipeline complet qui tourne via `pytest tests/test_qualite.py -v -s`
- `tests/rapport.md` : tableau de scores + analyse de la pire question + piste d'amelioration
- `pytest.ini` mis a jour avec le marker `qualite`
- Score moyen global : **3.92 / 5.0** (>= 3.5 vise)

---

## Execution

```bash
# Pipeline LLM-as-Judge (consomme ~24 appels LLM, ~78s)
cd fil-rouge && python -m pytest tests/test_qualite.py -v -s -m qualite

# Changer de juge
JUGE_PROVIDER=anthropic python -m pytest tests/test_qualite.py -v -s -m qualite

# Resultat : 3 passed, 2 failed in 78.10s
```

Les 2 echecs revelent des vrais problemes LLM :

- `test_aucune_question_catastrophique` : Q01 (format) a un score de 1.7 < 3.0
- `test_fidelite_jamais_a_un` : Q01, Q09, Q12 ont fidelite = 1

Ces echecs sont **attendus et utiles** — c'est exactement ce que le pipeline LLM-as-Judge est concu pour detecter.

---

## Ce que l'evaluation revele

Le pipeline a identifie **4 axes d'amelioration concrets** centres sur la qualite LLM :

1. **Hallucinations recurrentes** : le LLM embellit les resultats de `search_web` avec des donnees inventees ("GPT-5", "Gemini Ultra 2", "60%") → renforcer l'instruction "base-toi UNIQUEMENT sur les resultats de l'outil" dans `formuler_reponse()`
2. **Synthese incomplete** : quand l'outil retourne peu de donnees, le LLM compense en inventant plutot qu'en admettant la limite → ajouter une instruction "si les donnees sont insuffisantes, dis-le"
3. **Conflit securite/format** : `filtrer_sortie()` masque des emails dans un JSON demande explicitement → affiner le filtre selon le contexte de la question
4. **Routing RAG vs Web fragile** : "tendances actuelles" devrait aller vers `search_web`, pas `search_articles` → clarifier les criteres dans `SYSTEM_REACT`

Ces faiblesses (surtout 1 et 2) sont des problemes de **qualite de generation LLM** — elles n'auraient pas ete detectees par les tests unitaires (M5E1) ni les tests d'integration (M5E2). C'est la valeur ajoutee de l'evaluation par un juge.
