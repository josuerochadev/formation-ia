# Module 4 — RAG & Integration dans le Systeme d'Information

> Formation : *Maitriser les LLM et l'IA Generative* — AJC Formation

---

## Partie 1 — Memoire Documentaire (RAG)

### Comprendre le principe du RAG

Le **RAG (Retrieval Augmented Generation)** permet a un agent d'interroger une base documentaire externe, d'injecter du contexte fiable dans le prompt et de produire des reponses precises et actualisees.

**Flux** : Question → Recherche → Injection → Reponse

| Sans RAG | Avec RAG |
|---|---|
| Connaissance figee, limitee a l'entrainement du modele. Risque eleve d'hallucinations sur des sujets specialises. | Connaissance augmentee et actualisee a partir de vos propres documents metier. Reponses fiables et tracables. |

### Construire un pipeline RAG complet

Deux grandes phases : **ingestion des donnees** (preparer et indexer les documents) et **recherche et augmentation** (retrouver les extraits pertinents au moment de la requete).

**Etape 1 — Ingestion des donnees** : charger vos sources documentaires (PDF, CSV/Excel, bases SQL, APIs internes). La diversite des sources est une force, a condition de les normaliser.

**Etape 2 — Chunking (decoupage)** : decouper les documents en morceaux exploitables de **300 a 800 tokens**, avec chevauchement (overlap) pour preserver le contexte. Privilegier un decoupage semantique (titres, paragraphes).

**Etape 3 — Embeddings** : transformer les textes en **vecteurs numeriques** qui capturent leur sens semantique. Deux documents proches dans le sens auront des vecteurs proches dans l'espace vectoriel.

```python
from openai import OpenAI

client = OpenAI()
embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input="Procedure de remboursement client"
)
# embedding.data[0].embedding → vecteur de 1536 dimensions
```

> **text-embedding-3-small** d'OpenAI offre un excellent rapport qualite/cout. Des alternatives open source (BAAI/bge, sentence-transformers) permettent un deploiement 100% local.

### Preparation des donnees

> La qualite du RAG depend a 80% de la qualite des donnees ingerees.

| Format | Outil Python | Pieges courants |
|---|---|---|
| PDF | PyMuPDF, pdfplumber | PDF scannes → OCR necessaire, tableaux mal extraits |
| CSV / Excel | pandas | Encodage UTF-8/Latin-1, colonnes vides, doublons |
| JSON | json natif | Structures imbriquees, champs manquants |
| SQL | sqlite3, sqlalchemy | Donnees normalisees (jointures), NULL values |

**Checklist avant ingestion** :
- Tous les fichiers en UTF-8
- Doublons supprimes
- Donnees personnelles anonymisees (RGPD)
- PDFs scannes OCRises
- Seules les colonnes/champs utiles selectionnes

### Etape 4 — Stockage vectoriel

Les embeddings doivent etre stockes dans une **base de donnees vectorielle** optimisee pour la recherche par similarite.

| Base | Profil |
|---|---|
| **FAISS** | Local & rapide. Bibliotheque Meta, ideale pour du prototypage ou des volumes moderes. Pas de serveur requis. |
| **Chroma** | Simple & integre. Interface Python native, parfait pour debuter et tester rapidement un pipeline complet. |
| **Qdrant** | Scalable & production-ready. Architecture distribuee, filtres avances, ideal pour les deploiements en entreprise. |

### Etape 5 — Retrieval (Recherche)

A chaque requete utilisateur, l'agent calcule l'embedding de la question et **recherche les chunks les plus proches semantiquement** dans la base vectorielle. On recupere generalement les **3 a 5 extraits les plus pertinents**.

```python
# Recherche des k chunks les plus pertinents
results = vector_db.similarity_search(query, k=3)

# Chaque resultat contient :
# - result.page_content → le texte du chunk
# - result.metadata     → source, date, auteur...
```

- **Parametre k** : trop petit → contexte insuffisant. Trop grand → bruit et cout token accru. **k=3 a 5** est un bon point de depart.
- **Score de similarite** : filtrer les resultats sous un seuil pour eviter d'injecter des documents peu pertinents.

### Filtrer les resultats : score de similarite

| Score (cosine) | Interpretation | Action |
|---|---|---|
| > 0.85 | Tres pertinent | Injecter |
| 0.70 – 0.85 | Pertinent | Injecter si besoin |
| 0.50 – 0.70 | Faiblement pertinent | Ignorer |
| < 0.50 | Non pertinent | Ne pas injecter |

```python
def retrieval_avec_seuil(query, k=5, seuil=0.70):
    results = vector_db.similarity_search_with_score(query, k=k)
    pertinents = [
        (doc, score)
        for doc, score in results
        if score >= seuil
    ]
    if not pertinents:
        return None, "Aucun doc pertinent."
    return pertinents
```

> Le pire scenario n'est pas 'pas de reponse'. C'est une reponse basee sur des documents non pertinents que l'utilisateur prend pour argent comptant.

### Etape 6 — Augmentation du Prompt

Injecter les extraits recuperes dans le prompt envoye au LLM :

```python
documents = "\n\n".join([r.page_content for r in results])

prompt = f"""
Tu es un assistant expert. Reponds uniquement a partir
du contexte fourni.

Contexte :
{documents}

Question : {user_question}

Reponse :
"""

response = llm.invoke(prompt)
```

> **Bonne pratique** : precisez toujours dans le prompt que l'agent doit se baser sur le contexte fourni et signaler s'il ne trouve pas l'information, pour eviter les hallucinations.

### Qualite et fiabilite du RAG

**Bonnes pratiques** :
- Filtrer les documents (qualite > quantite)
- Normaliser les formats (encodage, structure)
- Versionner la base documentaire
- Enrichir avec des metadonnees (date, source, auteur)

**Risques a anticiper** :
- **Bruit documentaire** : chunks non pertinents injectes dans le prompt
- **Reponses biaisees** : si les sources sont partielles ou obsoletes
- **Hallucinations** : quand le retrieval est trop faible ou vide

### RGPD & Gouvernance des donnees

Des lors que l'agent traite des donnees internes ou personnelles, les exigences reglementaires s'appliquent pleinement.

- **Anonymisation** : masquer ou pseudonymiser les donnees sensibles (noms, emails, numeros de contrats) avant l'ingestion dans la base vectorielle
- **Gestion des acces (RBAC)** : controler qui peut interroger quels documents. Un commercial ne doit pas acceder aux donnees RH via l'agent.
- **Journalisation** : enregistrer toutes les requetes et reponses pour assurer la tracabilite, detecter les abus et repondre aux audits
- **Purge & cycle de vie** : mettre en place des politiques de suppression des donnees obsoletes pour respecter le droit a l'oubli et limiter l'exposition

---

## Partie 2 — Integration Systeme

### Architecture d'integration dans le SI

L'agent devient une **brique active du Systeme d'Information**, exposee via des interfaces et connectee aux outils existants.

| Couche | Role |
|---|---|
| **1. Front** | Chatbot, interface metier, API client ou portail collaborateur — le point d'entree utilisateur |
| **2. Back (Agent)** | LLM + RAG + orchestration des outils. Cerveau de l'application, pilotant la logique de reponse |
| **3. Connecteurs** | APIs REST internes et externes, webhooks, SDKs — les ponts vers les systemes existants de l'entreprise |

### Integration via FastAPI

**FastAPI** est le framework Python de reference pour exposer un agent sous forme d'API REST.

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    status: str

@app.post("/ask", response_model=AskResponse)
def ask_agent(req: AskRequest):
    """Endpoint principal de l'agent."""
    response = agent.run(req.question)
    return AskResponse(answer=response, status="success")

# Lancement : uvicorn main:app --reload
# Documentation auto : http://localhost:8000/docs
```

> **Bonne pratique** : typer les entrees/sorties avec Pydantic (`BaseModel`). FastAPI genere alors la validation automatique, les erreurs 422 explicites et la doc Swagger complete. Cf. [`fil-rouge/api.py`](../fil-rouge/api.py) pour l'implementation reelle.

> FastAPI genere automatiquement une documentation interactive (Swagger UI) accessible sur `/docs`. Ideal pour partager l'API avec les equipes front ou les integrateurs metier.

### Cas d'usage de l'exposition via API

- **Chatbot interne** : interface conversationnelle pour les employes (procedures RH, support IT, FAQ metier — disponible 24h/24)
- **API metier** : l'agent est consomme par d'autres applications du SI (CRM, ERP, portail client). Reponses structurees en JSON.
- **Automatisation de processus** : declenchement automatique de l'agent sur des evenements metier (nouvelle commande, ticket entrant, rapport quotidien)

### Webhooks & Automatisation evenementielle

L'agent peut etre declenche de facon **reactive par des evenements** issus de vos systemes :

- **Ticket entrant** : reception d'un ticket support → l'agent l'analyse automatiquement → genere une reponse draft ou le classe dans la bonne categorie
- **Email entrant** : un email client arrive → l'agent le classifie (demande de devis, reclamation, info) → declenche l'action appropriee dans le CRM
- **Rapport periodique** : a heure fixe → l'agent agrege les donnees du jour → genere un resume structure → l'envoie sur Slack ou par email

### Connexion aux outils metiers

L'agent prend toute sa valeur lorsqu'il peut **agir directement dans les outils du quotidien** :

| Outil | Exemples | Actions |
|---|---|---|
| **CRM** | Salesforce, HubSpot | Lecture/ecriture de contacts, opportunites, historique client |
| **Support** | Zendesk, Jira | Creation et mise a jour de tickets, assignation automatique |
| **Collaboration** | Slack, Teams | Envoi de notifications, resumes quotidiens, alertes en temps reel |
| **ERP** | SAP, Odoo | Consultation des stocks, statut commandes, donnees financieres |

### Exemple : Outil connecte a Jira

```python
from langchain.tools import tool
from jira import JIRA

jira = JIRA(server="https://your-domain.atlassian.net",
            basic_auth=("email", "api_token"))

@tool
def create_ticket(issue: str) -> str:
    """Cree un ticket Jira a partir d'une description."""
    new_issue = jira.create_issue(
        project="SUPPORT",
        summary=issue,
        issuetype={"name": "Bug"}
    )
    return f"Ticket cree : {new_issue.key}"

# L'agent appelle cet outil automatiquement
# quand l'utilisateur dit "cree un ticket pour..."
```

### Orchestration avec des outils no-code

Les plateformes **no-code/low-code** permettent un prototypage en heures plutot qu'en jours :

| Plateforme | Profil |
|---|---|
| **n8n** (Open Source) | Solution auto-hebergeable, ideale pour la souverainete des donnees. Connecteurs visuels puissants, workflow complexes possibles. |
| **Make** (ex-Integromat) | Interface visuelle intuitive, centaine de connecteurs disponibles. Excellent pour les automatisations multi-etapes avec logique conditionnelle. |
| **Zapier** | Le plus accessible, ideal pour les equipes metier. Connecte l'agent a +5000 applications sans configuration technique avancee. |

### Multimodalite

Les agents modernes ne se limitent plus au texte. En combinant plusieurs modeles specialises, il est possible de creer un agent **capable de comprendre et traiter des documents, images et audio** :

| Modalite | Cas d'usage | Outil |
|---|---|---|
| Audio → Texte | Compte-rendus reunions, messages vocaux | Whisper (OpenAI) |
| Image → Texte | Factures, bons de commande, schemas | GPT-4o Vision / Claude |
| PDF scan → Texte | Documents archives, contrats scannes | OCR + LLM |

### Gestion des erreurs en production

En contexte de production, les **defaillances sont inevitables**. Un agent robuste anticipe ces situations et les gere gracieusement.

**Cas frequents** : API tierce indisponible ou lente, timeout de connexion, donnees incorrectes ou format inattendu, quota API depasse (rate limit).

```python
try:
    result = call_api()
except TimeoutError:
    log_error("Timeout API")
    return "Service momentanement indisponible."
except ValueError as e:
    log_error(f"Donnees invalides: {e}")
    return "Erreur de format, reessayez."
except Exception as e:
    log_error(e)
    return "Erreur temporaire."
```

### Implementer les 4 barrieres de securite

**Validation input** (detection de prompt injection) :
```python
PATTERNS_INJECTION = [
    r"ignore\s+tes\s+instructions",
    r"tu\s+es\s+maintenant",
    r"system\s*prompt",
    r"repete.*tes\s+instructions",
]

def valider_input(question, max_len=5000):
    if not question.strip():
        return False, "Question vide."
    question = question.strip()[:max_len]
    for p in PATTERNS_INJECTION:
        if re.search(p, question.lower()):
            return False, "Non autorise."
    return True, question
```

**Filtrage output** (masquage de donnees sensibles) :
```python
SENSIBLE = [
    (r"[\w.-]+@[\w.-]+\.\w+", "[EMAIL]"),
    (r"0[1-9]\s?\d{2}(\s?\d{2}){3}", "[TELEPHONE]"),
    (r"\d{4}[\s-]?\d{4}[\s-]?\d{4}"
     r"[\s-]?\d{4}", "[CARTE]"),
]

def filtrer_output(reponse):
    for pattern, mask in SENSIBLE:
        reponse = re.sub(pattern, mask, reponse)
    return reponse
```

> Ces defenses bloquent 95% des tentatives basiques. La securite est un jeu de couches, pas un mur unique.

---

## Projet Fil Rouge — Construire un agent complet de bout en bout

Les participants construisent un **agent IA complet et fonctionnel**, ancre dans un contexte metier reel, depuis la memoire documentaire jusqu'a l'exposition en API.

### Livrables attendus

1. **Pipeline RAG fonctionnel** : ingestion → chunking → embeddings → stockage → retrieval. Le pipeline tourne sur un corpus documentaire reel et les reponses sont pertinentes.
2. **Integration API operationnelle** : endpoint FastAPI deploye, teste via Swagger. L'agent repond correctement a des requetes JSON depuis un client externe.
3. **Demonstration cas d'usage metier** : presentation d'un scenario reel (question metier → retrieval documentaire → action dans un outil). Resultat observable et evaluable.
4. **Gestion des erreurs** : le systeme ne plante pas sur des cas limites. Les erreurs sont capturees, journalisees et l'utilisateur recoit un message explicite.

---

## Message cle

> **Un agent IA n'est utile que s'il est connecte a la realite metier.**

- **Sans RAG** : l'agent ne sait pas. Il opere dans le vide, deconnecte de vos procedures, vos donnees et votre contexte. Ses reponses sont generiques et peu fiables.
- **Sans integration** : l'agent ne sert a rien. Meme brillant, s'il ne peut pas agir dans vos systemes, il reste un chatbot sans impact metier reel.

**RAG + Integration = un agent qui sait ET qui agit.** C'est la combinaison qui transforme un prototype en outil de production a valeur ajoutee reelle.

---

## Competences acquises

- Construire une memoire documentaire intelligente (RAG) : ingestion, chunking, embeddings, stockage vectoriel et retrieval de bout en bout
- Connecter l'agent aux systemes existants : APIs REST, webhooks, outils metier (CRM, ticketing, messagerie) et automatisation no-code
- Exposer et securiser un agent en production : FastAPI, gestion des erreurs, gouvernance RGPD, journalisation et controle d'acces
- Automatiser des workflows metier complets : de l'evenement declencheur a l'action dans l'outil, en passant par l'analyse contextuelle de l'agent

---

## Voir aussi

- **Exercices** :
  - [M4E1 — Pipeline RAG](../exercices/module4/exercice1-pipeline-rag.md) — ChromaDB, pdfplumber, corpus CNIL
  - [M4E2 — FastAPI](../exercices/module4/exercice2-fastapi.md) — exposition de l'agent RAG en API
  - [M4E3 — Robustesse](../exercices/module4/exercice3-robustesse.md) — gestion d'erreurs, retry, timeouts
  - [M4E4 — Multimodal](../exercices/module4/exercice4-multimodal.md) — audio (Whisper) + image (Vision)
  - [M4E5 — Securite](../exercices/module4/exercice5-securite.md) — 4 barrieres, prompt injection
- **Fil rouge** :
  - [`fil-rouge/tools/rag.py`](../fil-rouge/tools/rag.py) — RAG numpy (similarite cosinus)
  - [`fil-rouge/security.py`](../fil-rouge/security.py) — 4 barrieres de securite operationnelles
  - [`fil-rouge/api.py`](../fil-rouge/api.py) — wrapper FastAPI avec Pydantic
