# Module 3 — Developpement Python & Prototypage de l'Agent IA

> Formation : *Maitriser les LLM et l'IA Generative* — AJC Formation

---

## 1. Fondamentaux Python pour les agents IA

### Briques de base

- **Fonctions modulaires** : isoler chaque capacite dans une fonction distincte pour faciliter les tests, la reutilisation et la lisibilite
- **Gestion des exceptions** : anticiper les erreurs reseau, API et parsing avec `try/except` pour garantir la resilience de l'agent
- **Manipulation de fichiers** : lire et ecrire des formats courants (JSON, CSV, PDF) pour alimenter l'agent en donnees
- **Requetes HTTP** : appeler des APIs externes avec `requests` pour recuperer des donnees et declencher des actions

### Logique fondamentale d'un agent IA

Toute la complexite repose sur un flux simple : **Entree → Traitement → Sortie**. Ce cycle peut s'iterer plusieurs fois avant de produire une reponse finale (pattern ReAct).

### Appel API robuste en Python

```python
import requests

def call_api(url):
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Erreur : {e}")
        return None
```

**Bonnes pratiques** : timeout gere explicitement, erreurs loguees pour le debug, valeur de retour coherente.

### Architecture recommandee d'un projet agent

```
agent/
├── main.py          # Point d'entree
├── llm.py           # Appels au modele
├── tools/           # Fonctions d'action
│   ├── search.py
│   ├── database.py
│   └── pdf.py
├── memory/          # Gestion du contexte
│   └── store.py
└── config.py        # Parametres globaux
```

**Principes de conception** :
- `main.py` orchestre sans contenir de logique metier
- `llm.py` centralise tous les appels au modele
- `tools/` contient des fonctions pures et testables
- `memory/` persiste le contexte entre les tours

---

## 2. Appel aux APIs LLM

### La formule de base d'un agent

| Composant | Role |
|---|---|
| **LLM** | Le moteur de raisonnement : GPT-4o, Claude, Mistral... |
| **Contexte** | System prompt + historique + donnees injectees |
| **Outils** | Fonctions appelables : recherche, DB, API... |

### Appel OpenAI

```python
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Tu es un assistant metier"},
        {"role": "user", "content": "Analyse ce ticket client"}
    ]
)
print(response.choices[0].message.content)
```

### Multi-provider : Claude et Mistral

Meme logique, syntaxes differentes. Creer une couche d'abstraction (`llm.py`) pour changer de modele sans modifier le reste.

| Element | OpenAI | Anthropic (Claude) | Mistral |
|---|---|---|---|
| System prompt | Dans input | Param system separe | Dans messages |
| Resultat | `response.output_text` | `response.content[0].text` | `response.choices[0].message.content` |

### Structurer les sorties du LLM

Une reponse en texte libre est difficile a exploiter automatiquement. En forcant le LLM a repondre en JSON, on obtient des donnees directement exploitables.

- Utiliser `response_format={"type": "json_object"}` dans l'appel API
- Definir le schema attendu dans le system prompt
- Valider avec `json.loads()` avant usage

```json
{
    "intent": "support",
    "priority": "high",
    "action": "create_ticket",
    "summary": "Client bloque sur la facturation"
}
```

---

## 3. Pattern ReAct : Reasoning + Acting

Le pattern ReAct est le coeur de l'intelligence d'un agent. Plutot que de repondre immediatement, l'agent **reflechit**, **agit**, **observe** le resultat et **itere** jusqu'a produire une reponse satisfaisante.

### Cycle ReAct

1. **Reflechit** : analyse la requete et planifie
2. **Choisit** : selectionne l'outil approprie
3. **Execute** : appelle le tool selectionne
4. **Observe** : analyse le resultat obtenu
5. **Recommence** : si besoin, relance le cycle

### Implementation minimale

```python
def agent(query):
    thought = llm(
        "Que dois-je faire ?",
        query
    )
    if "search" in thought:
        result = search_tool(query)
    else:
        result = llm(
            "Reponds directement",
            query
        )
    return result
```

En production, on delegue cette logique a un framework.

### Frameworks recommandes

| Framework | Forces |
|---|---|
| **LangChain** | Ecosysteme riche, tres populaire, nombreux connecteurs prets a l'emploi |
| **LlamaIndex** | Oriente RAG et indexation de donnees, excellent pour les agents documentaires |

Ces frameworks gerent nativement le routing des tools, la gestion de la memoire et l'orchestration multi-etapes.

---

## 4. Ajout de Tools — Donner des capacites a l'agent

Un LLM sans outils est limite a sa connaissance interne. Les **tools** transforment un assistant passif en agent capable d'agir sur le monde reel : chercher, lire, calculer, ecrire en base de donnees.

### Trois tools essentiels

**Recherche Web** :
```python
def search_tool(query):
    # Appel SerpAPI, Tavily...
    return f"Resultat : {query}"
```
Permet a l'agent d'acceder a des informations recentes, hors de sa fenetre de connaissance.

**Lecture PDF** :
```python
from PyPDF2 import PdfReader

def read_pdf(file):
    reader = PdfReader(file)
    return reader.pages[0].extract_text()
```
Extrait le contenu textuel de documents pour alimenter le contexte de l'agent.

**Base SQL** :
```python
import sqlite3

def query_db(sql):
    conn = sqlite3.connect("db.sqlite")
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()
```
Donne a l'agent acces aux donnees structurees de l'entreprise en temps reel.

---

## 5. Gestion de la memoire

La memoire est ce qui transforme un LLM stateless en un agent capable de maintenir une conversation coherente et d'apprendre de ses interactions passees.

### Memoire courte (session)

Stocke l'historique de la conversation en cours en tant que liste de messages. Effacee a chaque nouvelle session.

```python
memory = []

def store(message):
    memory.append(message)

def recall():
    return memory[-5:]

# Utilisation
store({"role": "user", "content": "Bonjour"})
store({"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"})
context = recall()
# Injecter dans les messages LLM
```

### Memoire longue (persistante)

Conserve des informations entre les sessions : preferences, decisions passees, faits importants sur l'utilisateur.

- Base vectorielle (Chroma, Pinecone)
- Base de donnees relationnelle
- Fichiers JSON / Redis

### Bonnes pratiques memoire

- Limiter la fenetre de rappel (5 messages) pour controler les couts de tokens
- Stocker les messages avec leur role (`user` / `assistant`) pour reconstruire un historique valide
- Pour la memoire longue, utiliser un score de similarite pour ne recuperer que les souvenirs pertinents

---

## 6. RAG — Retrieval Augmented Generation

### LLM seul vs Agent RAG

| LLM seul | Agent RAG |
|---|---|
| Hallucine des informations | Repond a partir de vos documents |
| Ne connait pas vos donnees internes | Donne des reponses fiables et verifiables |
| Connaissance figee a la date d'entrainement | Acces aux donnees en temps reel |
| Incapable de citer ses sources | Cite les passages sources |

> Le RAG est le pattern le plus utilise en production pour les agents d'entreprise. Il resout le probleme fondamental de la fiabilite des LLMs sur des donnees specifiques.

### Pipeline RAG : les 5 etapes

1. **Decoupage** : segmenter les documents en chunks de taille optimale
2. **Embeddings** : convertir chaque chunk en vecteur numerique
3. **Stockage** : indexer les vecteurs dans une base vectorielle
4. **Recuperation** : trouver les chunks les plus similaires a la requete
5. **Generation** : injecter le contexte recupere dans le prompt du LLM

```python
def rag(query):
    # Etape 4 : Recuperation des documents similaires
    docs = retrieve_similar_docs(query)
    # Etape 5 : Generation avec contexte injecte
    context = "\n".join(docs)
    return llm(f"Contexte : {context}\nQuestion : {query}")
```

> L'etape de chunking est souvent sous-estimee : la taille des chunks (200-500 tokens) et leur chevauchement impactent directement la qualite de la recuperation.

---

## 7. Integration avec des systemes externes

Un agent veritablement utile en entreprise doit pouvoir agir sur les systemes existants — pas seulement repondre a des questions.

### Connecteurs et integrations

**APIs REST** :
```python
requests.post(
    "https://api.crm.com/ticket",
    json={"title": "Probleme client",
          "priority": "high"}
)
```
Communication universelle avec tout service exposant une API HTTP.

**Webhooks** : l'agent reagit a des evenements entrants (nouveau ticket, message, alerte). Mode push : le systeme externe notifie l'agent en temps reel.

**CRM & Support** : Salesforce, HubSpot, Zendesk, Jira — l'agent peut lire et ecrire dans vos outils metiers directement.

**Messagerie** : Slack, Microsoft Teams — exposer l'agent comme un bot conversationnel natif dans les outils de communication.

---

## 8. Debug et observabilite de l'agent

Un agent en production est une boite noire si on ne l'instrumente pas. Logs, traces et monitoring sont indispensables.

### Les 4 points de defaillance critiques

| Point | Symptome |
|---|---|
| **Mauvais prompt** | Instructions ambigues → comportement imprevisible |
| **Mauvais choix d'outil** | Le LLM selectionne le mauvais tool pour la tache |
| **Contexte insuffisant** | Fenetre trop courte ou memoire mal injectee |
| **Hallucination** | Le LLM invente une reponse sans base factuelle |

### Logging minimal indispensable

Loguer systematiquement : la requete entrante, l'intent detecte, le tool appele, et les erreurs.

### Les 4 questions reflexes du debug agent

1. **L'intent est-il correct ?** → verifier le prompt de classification
2. **Le bon tool est-il appele ?** → verifier le routing
3. **Le tool retourne-t-il le bon resultat ?** → verifier la connexion externe
4. **La reponse finale est-elle coherente ?** → verifier le prompt de generation

### Exemple de diagnostic

```
09:14:02 INFO  Requete : "Statut commande CMD-4521 ?"
09:14:03 INFO  Intent detecte : general        ← ERREUR
09:14:03 INFO  Tool choisi : reponse_directe   ← CONSEQUENCE
09:14:04 INFO  Reponse : "Contactez le
               service client."                ← ECHEC
```

**Diagnostic** : Intent = 'general' au lieu de 'database' → le prompt de classification ne mentionne pas 'commande' comme declencheur.
**Fix** : enrichir les exemples du prompt.

---

## 9. Acceleration avec l'IA : Copilot & Cursor

Les outils d'assistance au code peuvent considerablement accelerer le developpement d'agents — a condition de les utiliser avec discernement.

### Cas d'usage pertinents

- Generation de fonctions boilerplate
- Auto-completion de code repetitif
- Debugging assiste avec explication
- Generation de tests unitaires
- Documentation automatique

### Regles d'or

- **Toujours relire** le code genere ligne par ligne
- **Tester systematiquement** avant integration
- **Garder le controle humain** sur l'architecture
- Ne pas faire confiance aveuglement aux imports suggeres
- Valider la logique metier manuellement

> **Posture recommandee** : l'IA genere, le developpeur valide. Utilisez ces outils pour aller plus vite sur les parties mecaniques, mais restez proprietaire des decisions d'architecture et de la qualite du code.

---

## Recapitulatif du module

Les 8 etapes du cycle de vie d'un agent IA en Python :

1. **Fondamentaux Python** : fonctions, exceptions, HTTP
2. **Appels API LLM** : sorties structurees
3. **Motif ReAct** : raisonnement + action
4. **Outils** : recherche, PDF, SQL
5. **Memoire** : court et long terme
6. **Pipeline RAG** : segmentation, embedding, recuperation
7. **Integrations externes** : APIs, CRM, messagerie
8. **Debogage & observabilite** : journaux, points de defaillance

> La prochaine etape naturelle est le deploiement de l'agent : containerisation Docker, exposition via une API FastAPI, et monitoring en production avec des outils comme LangSmith ou Weights & Biases.

---

## Competences acquises

- Structurer un projet agent Python propre et modulaire
- Appeler des APIs LLM (OpenAI, Anthropic, Mistral) et structurer les sorties en JSON
- Implementer le pattern ReAct (raisonnement + action iteratif)
- Creer des tools (recherche web, lecture PDF, requetes SQL)
- Gerer la memoire courte (session) et longue (persistante)
- Construire un pipeline RAG complet (chunking, embeddings, recuperation, generation)
- Connecter l'agent a des systemes externes (APIs REST, webhooks, CRM, messagerie)
- Debugger et instrumenter un agent avec des logs structures
