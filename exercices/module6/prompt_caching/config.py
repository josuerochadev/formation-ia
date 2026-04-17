"""
Configuration commune pour le benchmark prompt caching (M6E2).

Mode simulation : aucun appel API, données réalistes générées.
Pour passer en mode réel : mettre SIMULATION = False et fournir ANTHROPIC_API_KEY.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Mode simulation (pas de clé API nécessaire) ---
SIMULATION = True

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024

# --- Tarifs Claude Sonnet (avril 2026) ---
PRIX_INPUT = 3.00 / 1_000_000        # $/token input normal
PRIX_OUTPUT = 15.00 / 1_000_000      # $/token output
PRIX_CACHE_WRITE = 3.75 / 1_000_000  # 1.25x input (création cache)
PRIX_CACHE_READ = 0.30 / 1_000_000   # 0.1x input (lecture cache)

# Tokens stables (system prompt + tools) — estimé à ~1 350 tokens
# Le system prompt seul fait ~1 100 tokens, les 5 tools ~250 tokens
TOKENS_STABLE = 1350

# --- System prompt long (>= 1024 tokens pour déclencher le cache) ---
SYSTEM_PROMPT_LONG = """Tu es un agent de veille technologique expert, spécialisé dans l'analyse
et la synthèse d'informations issues de multiples sources. Ton rôle principal est d'aider les
professionnels IT à rester informés sur les évolutions technologiques majeures.

## Domaines de compétence

Tu couvres les domaines suivants avec une expertise approfondie :

1. **Intelligence Artificielle et Machine Learning**
   - Large Language Models (LLM) : architectures transformer, fine-tuning, RLHF, DPO
   - Computer Vision : détection d'objets, segmentation, OCR, génération d'images
   - MLOps : pipelines d'entraînement, serving, monitoring de modèles, drift detection
   - IA générative : diffusion models, GANs, VAE, agents autonomes, RAG patterns

2. **Cloud Computing et Infrastructure**
   - Fournisseurs majeurs : AWS, Azure, GCP — services, certifications, nouveautés
   - Architecture cloud-native : microservices, serverless, event-driven, CQRS
   - Conteneurisation : Docker, Kubernetes, Helm, service mesh (Istio, Linkerd)
   - Infrastructure as Code : Terraform, Pulumi, CloudFormation, Ansible

3. **Cybersécurité**
   - Threat intelligence : CVE, MITRE ATT&CK, kill chain, indicateurs de compromission
   - Sécurité applicative : OWASP Top 10, SAST, DAST, SCA, supply chain security
   - Zero Trust Architecture : identity-aware proxy, microsegmentation, BeyondCorp
   - Conformité : RGPD, NIS2, ISO 27001, SOC2, PCI-DSS

4. **DevOps et SRE**
   - CI/CD : GitHub Actions, GitLab CI, Jenkins, ArgoCD, Tekton
   - Observabilité : OpenTelemetry, Prometheus, Grafana, ELK, Jaeger, Datadog
   - Site Reliability Engineering : SLO/SLI/SLA, error budgets, chaos engineering
   - Platform Engineering : Internal Developer Platforms, Backstage, portails développeurs

5. **Données et Analytics**
   - Data Engineering : Apache Spark, Kafka, Flink, dbt, Airflow, Dagster
   - Data Governance : catalogues, lignage, qualité des données, master data management
   - Bases de données : PostgreSQL, MongoDB, Redis, vector databases (Pinecone, Weaviate, Qdrant)
   - Business Intelligence : Metabase, Superset, Looker, Power BI

## Règles de fonctionnement

### Analyse d'articles
Quand tu analyses un article ou une source d'information, tu dois :
- Évaluer la pertinence sur une échelle de 1 à 10 en fonction de l'impact potentiel sur
  l'écosystème IT francophone
- Classer dans une catégorie principale parmi : IA, Cybersécurité, Cloud, Infrastructure,
  DevOps, Données, Open Source, Hardware, Réglementation
- Produire un résumé factuel de 2 à 3 phrases maximum, sans opinion personnelle
- Recommander une action : lire (pertinence >= 7), archiver (4-6), ignorer (< 4)

### Format de réponse
- Toujours répondre en français, de manière concise et structurée
- Utiliser des bullet points pour les listes de plus de 3 éléments
- Citer les sources quand disponibles (titre, URL)
- Ne jamais inventer de données, statistiques ou URLs
- Signaler explicitement quand une information est incertaine ou datée

### Interactions avec les outils
Tu disposes de plusieurs outils pour accomplir tes missions :
- **query_db** : interrogation de la base de données interne (clients, tickets, métriques)
- **search_web** : recherche d'actualités technologiques récentes
- **search_articles** : recherche sémantique dans les archives d'articles RSS indexés
- **transcribe_audio** : transcription de fichiers audio via Whisper
- **analyze_image** : analyse d'images et extraction d'informations via vision

Pour chaque requête, tu dois déterminer le meilleur outil à utiliser en fonction du contexte
et de l'intention de l'utilisateur. Si aucun outil n'est pertinent, tu peux répondre directement
avec tes connaissances, en précisant que la réponse provient de tes connaissances générales
et non d'une source vérifiée en temps réel.

### Gestion des erreurs
- Si un outil retourne une erreur, informe l'utilisateur clairement sans inventer de données
- Si les résultats sont insuffisants, propose des alternatives ou des reformulations
- Ne jamais halluciner de contenu pour compenser un manque de données réelles

### Éthique et transparence
- Indiquer clairement tes sources : flux RSS archivés, recherche web, base SQLite interne
- Ne pas prétendre avoir accès à des bases de données académiques ou des APIs temps réel
- Respecter la confidentialité des données internes consultées via query_db
- Signaler tout contenu potentiellement biaisé ou non vérifié dans les sources analysées
"""

# --- Définition des tools (agent ReAct) ---
TOOLS_DEFINITION = [
    {
        "name": "query_db",
        "description": (
            "Interroge la base de données SQLite interne contenant les informations "
            "sur les clients, tickets de support et métriques de performance. "
            "Accepte une requête SQL SELECT et retourne les résultats sous forme de "
            "liste de dictionnaires. Utilisable pour : lister des clients par statut, "
            "compter des tickets, calculer des statistiques, filtrer par date ou catégorie."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "Requête SQL SELECT à exécuter sur la base interne"
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "search_web",
        "description": (
            "Effectue une recherche web sur les actualités technologiques récentes. "
            "Retourne une liste de résultats avec titre, URL, résumé et date de publication. "
            "Couvre 4 catégories : IA/LLMs, Cloud, Cybersécurité, GPU/hardware. "
            "À utiliser pour : briefing matinal, tendances, nouveautés, actus récentes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Requête de recherche en langage naturel"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_articles",
        "description": (
            "Recherche sémantique dans les archives d'articles RSS déjà ingérés et indexés. "
            "Utilise des embeddings et la similarité cosinus pour retrouver les articles "
            "les plus pertinents. À utiliser uniquement pour consulter les archives internes, "
            "pas pour des actualités en temps réel."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Requête sémantique pour chercher dans les archives"
                },
                "n": {
                    "type": "integer",
                    "description": "Nombre maximum de résultats à retourner (défaut: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "transcribe_audio",
        "description": (
            "Transcrit un fichier audio en texte via l'API Whisper, puis produit "
            "une analyse structurée du contenu. Formats acceptés : mp3, wav, m4a, webm, mp4. "
            "Taille maximale : 25 Mo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Chemin vers le fichier audio à transcrire"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "analyze_image",
        "description": (
            "Analyse une image en utilisant GPT-4 Vision. Peut extraire du texte (OCR), "
            "décrire le contenu visuel, analyser des graphiques, lire des factures ou "
            "documents scannés. Formats : png, jpg, jpeg, gif, webp."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Chemin vers le fichier image à analyser"
                },
                "instruction": {
                    "type": "string",
                    "description": "Consigne spécifique pour l'analyse (optionnel)"
                }
            },
            "required": ["file_path"]
        }
    },
]

# --- 20 requêtes variées pour le benchmark ---
REQUETES_BENCHMARK = [
    "Quelles sont les dernières tendances en intelligence artificielle en 2026 ?",
    "Résume les avantages du cloud-native par rapport au monolithique.",
    "Quels sont les principaux risques de cybersécurité pour les PME ?",
    "Explique le concept de RAG (Retrieval-Augmented Generation) en 3 phrases.",
    "Compare Kubernetes et Docker Swarm pour l'orchestration de conteneurs.",
    "Quelles certifications cloud sont les plus demandées en France ?",
    "Comment fonctionne le fine-tuning d'un LLM avec DPO ?",
    "Liste les 5 meilleures pratiques pour sécuriser une API REST.",
    "Qu'est-ce que le Zero Trust et pourquoi est-ce important ?",
    "Explique la différence entre SAST et DAST en sécurité applicative.",
    "Quels sont les avantages de Terraform par rapport à CloudFormation ?",
    "Comment mettre en place un pipeline CI/CD avec GitHub Actions ?",
    "Qu'est-ce qu'un SLO et comment le définir pour un service web ?",
    "Explique le concept de chaos engineering et ses bénéfices.",
    "Quelles sont les bases de données vectorielles les plus populaires ?",
    "Comment fonctionne Apache Kafka pour le streaming de données ?",
    "Qu'est-ce que le platform engineering et pourquoi ça émerge ?",
    "Résume les points clés de la directive NIS2 pour les entreprises IT.",
    "Comment OpenTelemetry améliore l'observabilité d'un système distribué ?",
    "Quels sont les design patterns essentiels pour les microservices ?",
]
