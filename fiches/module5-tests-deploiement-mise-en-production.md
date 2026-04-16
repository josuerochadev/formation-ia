# Module 5 — Tests, Deploiement & Mise en Production

> Formation : *Maitriser les LLM et l'IA Generative* — AJC Formation

---

## Partie 1 — Tests

### Pourquoi tester un agent IA est different

Un agent IA ne retourne pas toujours la meme reponse pour la meme question. Les tests classiques (`assertEqual`) ne fonctionnent pas sur les sorties du LLM. Il faut une strategie a 3 niveaux :

| Niveau | Quoi tester | Outil | Deterministe ? |
|---|---|---|---|
| 1. Tests unitaires | Tools, memoire, parsing JSON, validation | pytest | Oui |
| 2. Tests d'integration | Pipeline complet : question → routing → tool → reponse | pytest + mock LLM | Partiellement |
| 3. Tests qualite LLM | Pertinence, fidelite, coherence des reponses | LLM-as-Judge | Non |

> Regle : testez en priorite ce qui EST deterministe (tools, memoire). Le LLM, on l'evalue autrement.

### Tests unitaires avec pytest

- Un test = une fonction qui commence par `test_`
- `assert` verifie qu'une condition est vraie ; si elle echoue, le test echoue
- pytest decouvre automatiquement tous les fichiers `test_*.py` et execute toutes les fonctions `test_*()`
- **Fixtures** (`@pytest.fixture`) : preparent des donnees de test reutilisables

**3 types de tests par tool** :
1. **Cas nominal** : le tool recoit des donnees valides → verifier que le resultat est correct
2. **Cas limite / vide** : le tool recoit des donnees inexistantes → verifier qu'il retourne vide, pas crash
3. **Cas d'erreur** : le tool recoit des donnees invalides → verifier qu'il gere l'erreur proprement

**Bonnes pratiques** :
- Lancer les tests souvent (apres chaque modification, pas juste a la fin)
- Un test qui passe puis echoue = regression
- Tester les cas d'erreur est aussi important qu'un test nominal
- Nommer les tests clairement : `test_client_existant` > `test_1`

### Tests d'integration

Les tests unitaires verifient chaque brique isolement. Les tests d'integration verifient que les briques fonctionnent **ensemble** :
- Le routing fonctionne (question BDD → `query_db` appele, salutation → reponse directe)
- La memoire est injectee (l'agent se souvient du contexte)
- Les erreurs sont gerees (question hors sujet → pas de crash)

> Attention : ces tests appellent le LLM reel → cout + non deterministe.

### LLM-as-Judge : evaluer la qualite des reponses

On ne peut pas faire `assertEqual` sur une reponse LLM. Mais on peut demander a un LLM d'evaluer la qualite.

| Critere | Question au juge | Score |
|---|---|---|
| Pertinence | La reponse repond-elle a la question ? | 1-5 |
| Fidelite | Basee sur le contexte fourni (pas inventee) ? | 1-5 |
| Coherence | Claire, structuree et logique ? | 1-5 |

| Score moyen | Interpretation |
|---|---|
| 4.5 – 5.0 | Pret pour la production |
| 3.5 – 4.5 | Optimiser les prompts |
| 2.5 – 3.5 | Revoir RAG ou tools |
| < 2.5 | Probleme structurel |

> Le LLM-as-Judge n'est pas parfait — mais c'est la meilleure approche automatisable pour evaluer la qualite a l'echelle.

### Construire son corpus de test

Pour evaluer la qualite de l'agent, il faut un jeu de questions de test (votre "examen") avec les bonnes reponses connues a l'avance. 4 types de questions a inclure :

1. **Question dans le corpus** : la reponse existe dans vos documents RAG → l'agent DOIT repondre correctement
2. **Question proche mais differente** : reformulation → verifier que le RAG retrouve le bon passage
3. **Question HORS du corpus** : la reponse n'existe PAS → l'agent DOIT refuser poliment, pas inventer
4. **Question piege / ambigue** : question floue → verifier que l'agent demande des precisions

> Regle : au moins 5 questions dans le corpus, 2 hors corpus, 1 ambigue, 2 libres.

### Perimetre de l'agent : "je ne sais pas" est la bonne reponse

L'agent RAG ne sait QUE ce qui est dans sa base documentaire. Il n'a pas acces a Internet ni la connaissance generale d'un ChatGPT. Un agent qui invente une reponse hors de ses documents = **hallucination**. Un agent qui dit "je ne sais pas" = **agent fiable**.

### Tester un agent sans RAG

Pas de RAG ne veut pas dire pas de tests. L'agent utilise un LLM + des tools + de la memoire — tout ca se teste. Le perimetre est defini par son system prompt et ses outils :
- Le bon tool est-il appele ? (routing)
- Les parametres envoyes au tool sont-ils corrects ?
- Le resultat du tool est-il exploite correctement ?
- Hors perimetre = refus poli ?
- Les erreurs de tools sont-elles gerees ?

---

## Partie 2 — Docker

### Pourquoi Docker

Docker empaquete votre application + toutes ses dependances dans un "conteneur" portable.

| Sans Docker | Avec Docker |
|---|---|
| "Ca marche sur ma machine" | Ca marche partout, identique |
| Installer Python, libs, configs a la main | 1 commande : `docker run` |
| Conflits de versions entre projets | Environnement isole, pas de conflits |
| Impossible a reproduire facilement | Reproductible : dev = staging = prod |
| Le deploiement est un cauchemar | Deploiement en 1 commande |

### Les 3 concepts cles

- **Image** : la recette de cuisine. Un fichier qui decrit comment construire l'environnement. Creee avec `docker build`.
- **Conteneur** : le plat prepare. Une instance en cours d'execution d'une image. Cree avec `docker run`. Isole du reste du systeme.
- **Registre** : le livre de recettes partage. Docker Hub, GCP Artifact Registry. On y pousse (`push`) et tire (`pull`) les images.

**Flux** : Dockerfile → `docker build` → Image → `docker run` → Conteneur → `docker push` → Registre

### Ecrire un Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Dependances d'abord (cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Puis le code
COPY . .

# Variables d'env (surchargeables)
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Verification sante automatique
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -f http://localhost:8000/health || exit 1

# Demarrage
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Points cles :
- `FROM python:3.11-slim` : image de base legere (~150 MB)
- `COPY requirements.txt` + `RUN pip install` EN PREMIER : exploite le cache Docker (si le code change mais pas les deps, Docker ne reinstalle pas les libs)
- `HEALTHCHECK` : Docker verifie que l'agent repond ; si `/health` ne repond plus, redemarrage automatique

### Commandes Docker essentielles

```bash
docker build -t agent-ia:v1 .          # Construire l'image
docker run -d -p 8000:8000 \           # Lancer le conteneur
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  --name mon-agent agent-ia:v1
docker ps                               # Conteneurs actifs
docker logs -f mon-agent                 # Logs en temps reel
docker exec -it mon-agent /bin/bash      # Entrer dans le conteneur
docker stop mon-agent && docker rm mon-agent  # Arreter et supprimer
```

---

## Partie 3 — Deploiement Cloud

### Pourquoi deployer dans le cloud

- **Accessibilite** : agent accessible 24/7, de n'importe ou, via une simple URL
- **Scalabilite** : le cloud ajoute des instances automatiquement quand la charge augmente
- **Fiabilite** : redemarrage automatique en cas de crash
- **Integration** : les autres applications (CRM, Slack, n8n) peuvent appeler l'agent via son URL publique

### Comparatif des plateformes

| Plateforme | Service | Cout depart | Complexite | Ideal pour |
|---|---|---|---|---|
| **GCP** | Cloud Run | Gratuit (petit vol.) | Faible | Prototype → production |
| **AWS** | Lambda + API GW | Gratuit (petit vol.) | Moyenne | Serverless, evenements |
| **Scaleway** | Serverless Containers | ~5 EUR/mois | Faible | Souverainete EU |
| **Azure** | Container Apps | ~10 EUR/mois | Moyenne | Ecosysteme Microsoft |

> Recommandation pour commencer : **GCP Cloud Run**. Le plus simple, scale automatiquement, ne facture qu'a l'utilisation.

### Checklist pre-deploiement

- Cles API en variables d'environnement (pas dans le code)
- Dockerfile fonctionne en local
- Tests passent (pytest)
- `/health` repond
- Authentification API activee
- CORS configure

### Deployer sur GCP Cloud Run

```bash
# 1. Se connecter
gcloud auth login
gcloud config set project MON_PROJET

# 2. Construire et pousser l'image
gcloud builds submit --tag gcr.io/MON_PROJET/agent-ia:v1

# 3. Deployer sur Cloud Run
gcloud run deploy agent-ia \
  --image gcr.io/MON_PROJET/agent-ia:v1 \
  --port 8000 \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY

# 4. Cloud Run donne une URL publique :
# https://agent-ia-xxxxx-ew.a.run.app
```

### Estimation des couts mensuels

Le cout dominant est TOUJOURS l'API LLM, pas l'hebergement.

| Usage | API LLM / mois | Hebergement | Total |
|---|---|---|---|
| 100 req/jour (pilote) | ~15 $ | ~0 $ (free tier) | ~15 $/mois |
| 500 req/jour (1 service) | ~75 $ | ~5 $ | ~80 $/mois |
| 1 000 req/jour (entreprise) | ~150 $ | ~10 $ | ~160 $/mois |
| 10 000 req/jour (scale) | ~1 500 $ | ~30 $ | ~1 530 $/mois |

**Tips pour reduire les couts** :
- Utiliser GPT-4o mini ou Claude Haiku pour les taches simples (classification, routing)
- Reserver le modele puissant (GPT-4o, Claude Sonnet) pour la generation de reponse
- Mettre en cache les reponses aux questions frequentes
- Optimiser la taille des chunks RAG pour reduire les tokens injectes

---

## Partie 4 — Monitoring

### Les 4 metriques essentielles

> Un agent en production sans monitoring, c'est conduire de nuit sans phares.

| Metrique | Pourquoi | Comment mesurer | Seuil d'alerte |
|---|---|---|---|
| Temps de reponse | UX et SLA | `time.time()` avant/apres chaque appel | > 10 secondes |
| Taux d'erreur | Fiabilite | Compteur erreurs / total requetes | > 5% |
| Cout par requete | Budget | Tokens (in+out) x prix par token | > 0.10 $ / requete |
| Taux de fallback | Qualite RAG | Nb "je ne sais pas" / total requetes | > 20% |

**Actions correctives** :
- Latence > 10s : reduire les tokens, utiliser un modele plus rapide, cacher les resultats frequents
- Erreurs > 5% : ameliorer la gestion d'erreur (retry), monitorer les tools individuellement
- Cout > budget : modele leger pour le routing, resumer les chunks avant injection, cache
- Fallback > 20% : enrichir le corpus, ajuster le seuil de similarite, ameliorer le chunking

### Implementer le monitoring

```python
# monitoring.py
import time, json, logging
from datetime import datetime

metrics = {
    "total": 0, "erreurs": 0,
    "latence_totale": 0, "cout_total": 0,
    "fallbacks": 0
}

def log_request(question, latency_ms, tokens_in, tokens_out,
                error=None, fallback=False):
    cost = (tokens_in * 2.5 + tokens_out * 10) / 1_000_000
    metrics["total"] += 1
    metrics["latence_totale"] += latency_ms
    metrics["cout_total"] += cost
    if error: metrics["erreurs"] += 1
    if fallback: metrics["fallbacks"] += 1

def get_dashboard():
    n = metrics["total"] or 1
    return {
        "total_requetes": n,
        "latence_moy_ms": metrics["latence_totale"] // n,
        "taux_erreur": f"{metrics['erreurs']/n*100:.1f}%",
        "cout_total": f"{metrics['cout_total']:.2f} $",
    }
```

Exposer dans l'API via un endpoint `/metrics` accessible en temps reel.

### Outils de dashboard et alertes

| Outil | Type | Ideal pour |
|---|---|---|
| Endpoint `/metrics` | Maison | Prototype, verification rapide |
| Prometheus + Grafana | Open source | Dashboards temps reel, historique |
| LangSmith | SaaS (LangChain) | Tracing LLM natif, debug chaines |
| Sentry | SaaS | Erreurs, stack traces, alertes |
| Logs cloud natifs | GCP/AWS/Azure | Recherche, filtrage, retention |

---

## Partie 5 — KPIs Metier

### KPIs techniques vs KPIs metier

**KPIs techniques** (equipe IT) : temps de reponse moyen, taux d'erreur, cout API mensuel, uptime/disponibilite, tokens consommes.

**KPIs metier** (direction) : temps gagne par les equipes, taux de resolution automatique, cout par transaction vs avant, satisfaction utilisateur (CSAT), volume traite sans humain.

> La direction ne demandera jamais votre taux d'erreur API. Elle demandera : "Combien de temps on gagne ? Combien ca coute vs ce que ca rapporte ?"

### Calculer le ROI

**Formule** : `ROI = (Gains - Couts) / Couts x 100`

- Gains = (temps_avant - temps_apres) x nb_transactions x cout_horaire
- Couts = API_LLM + hebergement + maintenance humaine

**Exemple concret — Service support** :
- AVANT : 200 tickets/jour x 15 min/ticket x 25 EUR/h = 1 250 EUR/jour
- APRES (60% automatise) : 120 tickets automatises/jour = 750 EUR economises/jour
- Couts agent : API LLM ~5 EUR + hebergement ~1 EUR + maintenance ~4 EUR = **10 EUR/jour**
- **Gain net : 740 EUR/jour = 16 000 EUR/mois. ROI = 7 400%**

### Cas reel — IKEA

2021 : IKEA deploie "Billie", un chatbot IA pour gerer les appels du service client. Billie resout 47% des demandes (3.2 millions d'interactions, 13 MEUR d'economies). Au lieu de couper les effectifs, IKEA reconvertit 8 500 employes en conseillers en decoration d'interieur — un nouveau service payant qui genere 1.3 milliard EUR de CA (3.3% du CA total IKEA, objectif 10% d'ici 2028).

---

## Partie 6 — Conduite du Changement

### Plan de deploiement en 3 phases

| Phase | Duree | Perimetre | Critere Go/No-Go |
|---|---|---|---|
| 1. Pilote | 2-4 semaines | 5-10 utilisateurs, cas simples | Resolution > 40%, CSAT > 3.5, 0 incident critique |
| 2. Deploiement progressif | 1-2 mois | 1 service complet, tous les cas | Resolution > 50%, erreurs < 5% |
| 3. Generalisation | Continu | Tous les services | KPIs stables, adoption > 70% |

> A chaque phase : mesurer les KPIs, recueillir le feedback, ajuster. Un **plan de repli** est non negociable avant tout Go/No-Go.

### Gerer les resistances

| Objection | Reponse |
|---|---|
| "L'IA va nous remplacer" | L'agent traite les taches repetitives — vous gardez les cas complexes. Cf. IKEA : 0 licenciement, 8 500 reconversions. |
| "On ne peut pas lui faire confiance" | Montrer les garde-fous : validation humaine sur les actions sensibles, logs, taux d'erreur mesure et affiche. |
| "Ca va couter trop cher" | Presenter le ROI avec les chiffres reels du pilote. Le cout dominant est l'API LLM (~15 $/mois pour un pilote). |
| "C'est trop technique" | L'interface est simple (chat, email). L'IA se cache derriere les outils existants. Les utilisateurs n'ont rien a installer. |

### Maintenir un agent en production

| Tache | Frequence | Qui | Quoi |
|---|---|---|---|
| Surveiller les metriques | Quotidien | IT / Ops | Dashboard /metrics, alertes Slack |
| Relire les logs d'erreur | Hebdomadaire | IT / Dev | Identifier les patterns d'erreur recurrents |
| Mettre a jour le corpus RAG | Mensuel | Metier + IT | Ajouter les nouveaux docs, supprimer les obsoletes |
| Evaluer la qualite (LLM-as-Judge) | Mensuel | IT | Lancer le jeu de tests qualite, comparer avec le mois precedent |
| Mettre a jour les modeles LLM | Trimestriel | IT | Tester les nouvelles versions, comparer cout/qualite |
| Audit RGPD | Annuel | DPO + IT | Verifier anonymisation, RBAC, journalisation, purge |

> Un agent n'est pas un projet qu'on livre et qu'on oublie. C'est un service vivant qui necessite une maintenance continue.

---

## Soutenance finale

30 minutes par participant : 15 min demo | 10 min KPIs & plan | 5 min questions.

**Demo live (15 min)** : 3-5 questions en live a l'agent, RAG fonctionnel (vos documents), au moins 1 outil externe, 1 cas d'erreur gere proprement, les logs de tracabilite, les tests qui passent (pytest).

**Presentation (10 min)** : le probleme metier quantifie, l'architecture (7 couches), 3 KPIs avec cibles et resultats, le ROI estime, le plan de deploiement, les lecons apprises.

### Grille de notation — /100 points

| Critere | Points | Description |
|---|---|---|
| Fonctionnement technique | /25 | L'agent fonctionne en demo live, tests passent |
| Pertinence metier | /20 | Probleme reel et quantifie |
| Architecture & RAG | /15 | 7 couches, pipeline RAG, choix justifies |
| KPIs et ROI | /15 | Metriques mesurees, ROI calcule |
| Securite & RGPD | /10 | Cas d'erreur geres, conformite |
| Qualite presentation | /10 | Clarte, respect du temps, Q&A |
| Innovation | /5 | Element inattendu, bonus |

| Score | Appreciation |
|---|---|
| 80-100 | Excellent |
| 60-79 | Bon — ajustements |
| 40-59 | Suffisant — consolider |
| < 40 | Insuffisant |

---

## Competences acquises

- Mettre en place une strategie de tests a 3 niveaux (unitaires, integration, LLM-as-Judge) adaptee aux specificites non deterministes de l'IA
- Conteneuriser un agent avec Docker (Dockerfile, build, run, healthcheck) et le deployer dans le cloud (GCP Cloud Run, AWS, Scaleway)
- Implementer un monitoring operationnel (metriques, dashboard, alertes) et mesurer l'impact metier (KPIs, ROI)
- Piloter la conduite du changement : plan de deploiement en 3 phases, gestion des resistances, maintenance continue

---

## Voir aussi

- **Exercices** :
  - [M5E1 — Tests unitaires](../exercices/module5/exercice1-tests-unitaires.md) — 85 tests deterministes sur les tools
  - [M5E2 — Tests d'integration](../exercices/module5/exercice2-tests-integration.md) — routing, memoire, erreurs
  - [M5E3 — LLM-as-Judge](../exercices/module5/exercice3-llm-as-judge.md) — evaluation qualite automatisee (10 questions, 3 criteres)
  - [M5E4 — Containerisation Docker](../exercices/module5/exercice4-docker.md) — Dockerfile + FastAPI, healthcheck
- **Fil rouge** :
  - [`fil-rouge/tests/`](../fil-rouge/tests/) — suite de tests pytest
  - [`fil-rouge/Dockerfile`](../fil-rouge/Dockerfile) — image python:3.11-slim + uvicorn
  - [`fil-rouge/api.py`](../fil-rouge/api.py) — endpoints `/health` et `/ask`
