# Module 2 — Conception Fonctionnelle & Architecture Technique d'un Agent IA

> Formation : *Maitriser les LLM et l'IA Generative* — AJC Formation

---

## 1. Identifier les opportunites d'automatisation

### Qu'est-ce qu'un Agent IA ?

Un agent IA est un systeme autonome capable d'executer un cycle complet pour atteindre un objectif defini :

| Etape | Role |
|---|---|
| **Percevoir** | Recevoir et interpreter les informations de son environnement |
| **Raisonner** | Analyser la situation et choisir la meilleure strategie |
| **Decider** | Selectionner l'action la plus appropriee au contexte |
| **Executer** | Agir via des outils connectes aux systemes d'entreprise |

### Exemples d'agents en entreprise

- **Support Client** : traitement automatique des demandes recurrentes, escalade intelligente
- **Analyse Documentaire** : extraction d'informations cles, synthese de contrats et rapports
- **Reporting Automatise** : generation et diffusion de rapports periodiques sans intervention humaine
- **Qualification de Leads** : scoring automatique, enrichissement de fiches prospects dans le CRM

### Methode d'identification des processus automatisables

L'analyse repose sur deux dimensions complementaires :

| Dimension | Criteres |
|---|---|
| **Valeur Metier** | Gain de temps mesurable, reduction des couts operationnels, amelioration de la qualite de service, meilleure satisfaction client |
| **Faisabilite Technique** | Disponibilite et qualite des donnees, complexite du raisonnement requis, integration avec les systemes existants, contraintes reglementaires |

### Matrice de priorisation

| Processus | Valeur Metier | Faisabilite | Priorite |
|---|---|---|---|
| Support client automatise | Elevee | Elevee | Haute |
| Qualification de leads | Elevee | Elevee | Haute |
| Analyse de contrats | Elevee | Moyenne | Moyenne |
| Reporting automatise | Moyenne | Elevee | Moyenne |
| Strategie marketing IA | Moyenne | Faible | Basse |

> **Conseil** : demarrez par un pilote sur un processus a haute valeur et haute faisabilite pour demontrer la valeur avant de passer a l'echelle.

---

## 2. Typologie des agents IA

### Agent Reactif

Le plus simple et rapide a deployer. Flux direct sans memoire ni planification complexe.

- **Flux** : Entree → Analyse → Reponse
- **Cas d'usage** : chatbot FAQ, agent support interne IT/RH, assistant documentaire
- **Caracteristiques** : reponse rapide, architecture simple, peu de planification, ideal en point d'entree

### Agent avec Raisonnement : Pattern ReAct

Le pattern ReAct (**Re**asoning + **Act**ing) alterne entre raisonnement interne et appels d'outils externes. C'est le standard pour les agents IA d'entreprise modernes.

- **Cycle** : Question recue → Raisonnement → Action → Observation & Reponse
- **Exemple** : un agent analyse une question client, interroge la base documentaire, recupere des donnees CRM, puis synthetise une reponse personnalisee — en une seule interaction

### Agent Planificateur

Le plus sophistique. Il decompose un objectif complexe en sous-taches, les planifie et les execute de facon sequentielle ou parallele.

**Exemple — Qualification de lead** :
1. Analyser le lead entrant (extraction des infos cles depuis formulaire/email)
2. Rechercher les infos entreprise (enrichissement via LinkedIn, web, bases tierces)
3. Generer un email personnalise (adapte au profil et au secteur)
4. Programmer un rendez-vous (proposition de creneaux et mise a jour CRM)

### Co-conception avec l'IA

Utiliser le LLM comme partenaire de reflexion avant de coder :

| Usage | Prompt type | Resultat |
|---|---|---|
| Explorer les cas d'usage | "Liste 10 processus automatisables dans un service [X]..." | Matrice de priorisation |
| Choisir le pattern | "Mon agent doit [objectif]. Quel pattern ?" | Recommandation argumentee |
| Rediger le CdC | "Redige le CdC pour un agent de [usage]..." | Draft complet |
| Anticiper les risques | "Quels sont les 5 risques de [scenario] ?" | Registre des risques |

> **Bonne pratique** : "Tu es un architecte d'agents IA senior. Contexte : [X]. Produis : 1) matrice entrees/sorties 2) choix de pattern justifie 3) liste des tools 4) KPIs 5) risques"

---

## 3. Rediger le cahier des charges fonctionnel

### Structure du cahier des charges (5 dimensions)

1. **Probleme Metier** : description precise du probleme a resoudre et des objectifs mesurables
2. **Utilisateurs Cibles** : profils des utilisateurs finaux, internes et externes concernes
3. **Cas d'Usage** : liste des scenarios fonctionnels couverts par l'agent
4. **Entrees & Sorties** : definition exacte des inputs acceptes et des outputs produits
5. **KPIs & Performance** : metriques de succes permettant d'evaluer objectivement l'agent

### Exemple : Definition du probleme metier (support client)

- **Probleme** : le service support traite 300 emails/jour, dont 60% sont des demandes repetitives (reinitialisation de mot de passe, suivi de commande, questions FAQ). Chaque ticket mobilise en moyenne 8 minutes d'un agent humain.
- **Objectif** : automatiser 60% des reponses aux demandes frequentes
- **Gain attendu** : reduction de 4h/jour de charge agent, amelioration CSAT
- **Perimetre** : emails entrants canal B2C, hors reclamations complexes

### Entrees, sorties & KPIs

**Entrees acceptees** :
- Message texte utilisateur
- Document PDF / Word
- Email entrant formate
- Ticket support existant

**Sorties produites** :
- Reponse textuelle personnalisee
- Action dans un outil tiers
- Creation / mise a jour de ticket
- Synthese structuree

**Indicateurs de performance** :

| KPI | Description | Cible |
|---|---|---|
| Taux de resolution automatique | % de demandes traitees sans intervention humaine | 60% |
| Temps moyen de reponse | Delai entre reception et envoi de la reponse | < 30 sec |
| Satisfaction utilisateur (CSAT) | Note de satisfaction post-interaction | >= 4/5 |
| Cout par requete | Cout LLM + infrastructure par interaction | A optimiser |

---

## 4. Architecture d'un agent IA — Les 7 couches

### Vue d'ensemble

L'architecture complete d'un agent IA s'articule autour de sept couches interdependantes :

1. **Couche d'Entree / Perception**
2. **Orchestration / Logique Agent**
3. **Raisonnement (LLM)**
4. **Memoire**
5. **Outils & Actions Externes**
6. **Controle & Gouvernance**
7. **Sortie / Resultat**

### Couche 1 : Perception & Entree

Point d'entree de l'agent. Recoit, parse et structure toutes les informations entrantes.

**Interfaces d'entree** : chat web, Slack/Teams, API REST/Webhooks, formulaires structures, emails entrants

**Pretraitements appliques** :
- **Parsing** : extraction du contenu utile
- **Nettoyage** : suppression du bruit, normalisation
- **Extraction du contexte** : identification de l'utilisateur, de l'historique
- **Detection de langue** et du canal source

> La qualite du pretraitement conditionne directement la qualite du raisonnement en aval.

### Couche 2 : Orchestration & Logique d'Agent

Le cerveau decisionnel. Analyse l'intention, choisit le workflow et coordonne les appels aux differentes couches.

- **Analyse d'intention** : identification du type de demande et de l'objectif utilisateur
- **Choix du workflow** : selection du parcours de traitement adapte au cas d'usage
- **Decision d'action** : repondre directement, chercher, appeler un outil ou escalader vers un humain
- **Gestion des etapes** : application du pattern ReAct ou planification multi-etapes

### Couches 3 & 4 : Raisonnement (LLM) & Memoire

Le moteur de raisonnement et la memoire fonctionnent en tandem.

**Moteur LLM** (GPT-4/4o, Claude 3, Mistral Large, Gemini Pro) : comprendre la requete, raisonner, decider des actions, generer la reponse finale.

**Types de memoire** :

| Type | Contenu |
|---|---|
| **Memoire Courte (Court Terme)** | Contexte de la conversation en cours, historique des derniers echanges |
| **Memoire Longue (RAG)** | Base documentaire vectorisee, connaissances metier persistantes, profil utilisateur |

### Couche 5 : Outils & Actions Externes

Les outils (tools, functions, connectors) permettent a l'agent d'interagir avec les systemes d'information de l'entreprise.

- **CRM / ERP** : lecture et mise a jour des fiches clients, opportunites, commandes
- **Recherche Web / SQL** : interrogation de bases de donnees internes ou sources web
- **Lecture PDF / Documents** : extraction et analyse du contenu de fichiers
- **Email / Ticketing** : envoi d'emails automatiques, creation et mise a jour de tickets

**Conception d'un outil — Bonnes pratiques** :

Chaque outil doit etre **simple** (une fonction precise), **documente** (description claire lisible par le LLM) et **robuste** (gestion des erreurs, timeouts et cas limites).

**Exemple de specification d'outil** :

```
NOM : rechercher_commande
DESCRIPTION : "Recherche une commande par numero ou nom du client. Retourne les details"
ENTREES :
  - numero_commande (string, optionnel)
  - nom_client (string, optionnel)
SORTIE (succes) : JSON {statut, date, montant}
SORTIE (erreur) : {erreur, suggestion}
GESTION D'ERREUR :
  - Introuvable → message explicite
  - API down → retry 1x puis message
  - Timeout > 5s → abandon + message
```

**3 erreurs a eviter** :
- Description vague ("Gere les commandes") → le LLM ne sait pas quand l'appeler
- Pas de gestion d'erreur → l'agent plante silencieusement
- Outil trop generique (fait 5 choses) → le LLM confond les usages

### Couche 6 : Controle, Securite & Gouvernance

Non negociable en contexte professionnel :

- **RGPD & Conformite** : anonymisation des donnees personnelles, gestion des droits d'acces, registre des traitements
- **Garde-fous & Validation** : detection des hallucinations, validation humaine sur actions critiques, refus automatique hors perimetre
- **Logs & Tracabilite** : journalisation de chaque interaction, monitoring des couts LLM, alertes sur anomalies
- **Suivi des KPIs** : tableaux de bord temps reel sur les metriques de performance et de qualite

**4 barrieres de defense** :

1. **Validation input** : sanitisation, longueur max, detection patterns suspects
2. **System prompt defensif** : instructions explicites de refus, perimetre strict, non negociable
3. **Controle des actions** : whitelist de tools, validation humaine sur actions sensibles
4. **Filtrage output** : masquer emails, telephones, IBAN, donnees sensibles dans les reponses

**Niveaux de controle par action** :

| Niveau | Exemples | Controle |
|---|---|---|
| Lecture | Consulter FAQ, rechercher doc | Aucun |
| Creation | Creer ticket, enregistrer note | Log + notification |
| Modification | Modifier fiche client | Validation humaine |
| Irreversible | Envoyer email, paiement | Double validation |

### Les 5 menaces specifiques aux agents IA

| Menace | Description | Risque metier |
|---|---|---|
| **Prompt Injection** | Instructions cachees dans la requete utilisateur | Actions non autorisees |
| **Jailbreak** | Contournement des garde-fous du modele | Fuite d'informations sensibles |
| **Exfiltration** | Extraction du system prompt ou des donnees RAG | Vol de donnees proprietaires |
| **Action non autorisee** | Email, suppression, paiement sans validation | Impact financier/juridique |
| **Empoisonnement RAG** | Documents malveillants dans la base | Desinformation, manipulation |

> **La prompt injection est aux agents IA ce que l'injection SQL etait aux applications web en 2005.** C'est le risque #1 et il est souvent ignore par les equipes qui prototypent.

### Couche 7 : Sortie & Resultat

La sortie peut prendre plusieurs formes :

- **Reponse utilisateur** : texte conversationnel via le canal d'entree (chat, email, Slack)
- **Action executee** : mise a jour d'un outil tiers (CRM, calendrier, base de donnees, ticket)
- **Synthese / Rapport** : document structure genere automatiquement (resume, analyse, rapport periodique)
- **Notification** : alerte envoyee a un responsable pour validation ou escalade humaine

---

## 5. Gestion des donnees

Les donnees sont le facteur cle de reussite d'un agent IA.

### Sources de donnees utilisables

- Documents internes (PDF, Word, PowerPoint)
- Bases CRM et ERP
- Bases SQL / NoSQL
- APIs externes et flux temps reel
- Emails et historiques de conversation

### Etapes de preparation

1. **Suppression des doublons** : dedoublonnage et fusion des enregistrements redondants
2. **Correction des erreurs** : validation des formats, correction des incoherences
3. **Anonymisation RGPD** : masquage ou pseudonymisation des donnees personnelles
4. **Structuration & indexation** : formatage homogene pour l'injection en base vectorielle

> La qualite des donnees determine la qualite des reponses.

---

## 6. Parties prenantes & gouvernance de projet

Un projet d'agent IA est un projet transversal qui mobilise plusieurs expertises :

| Partie prenante | Responsabilites |
|---|---|
| **Metiers** | Definition des besoins, validation des cas d'usage, recette fonctionnelle et adoption |
| **IT & Architecture** | Conception de l'architecture, integration aux SI existants, deploiement et maintenance |
| **Juridique** | Conformite RGPD, analyse des risques, validation des traitements de donnees personnelles |
| **Direction** | Validation strategique, arbitrage budgetaire, sponsorship du projet et communication interne |

### Ce qui tue les projets IA

- **Le DPO n'a pas ete consulte** → projet bloque 2 semaines avant la prod pour non-conformite RGPD
- **Les metiers n'ont pas ete impliques** → l'agent repond a cote du vrai besoin, personne ne l'utilise
- **La direction n'a pas valide** → le budget est coupe en cours de route, le projet meurt
- **L'IT a travaille seul** → l'agent ne s'integre pas dans le SI existant, reste un prototype

### Ce que vous ferez en rentrant

- Convaincre un sponsor (direction) — sans sponsor, pas de budget, pas de deploiement
- Valider les donnees avec le DPO — avant de coder, pas apres
- Faire tester par les utilisateurs metier — ce sont eux qui decident si l'agent est utile
- Ne pas coder seul dans son coin — un agent qui marche en demo mais pas en vrai = zero

---

## 7. Exemple complet : Agent Support Client

### Architecture complete

**Flux** : Question recue (chat/email) → Orchestration (analyse d'intention, choix de workflow) → Raisonnement LLM (RAG + interrogation CRM) → Controle qualite (verification conformite et RGPD) → Sortie (reponse client ou creation ticket)

**Donnees mobilisees** :
- FAQ et documentation produit (RAG)
- Historique client (CRM)
- Base de tickets existants

**Outils connectes** :
- `rechercher_client` → CRM
- `rechercher_doc` → Base vectorielle
- `creer_ticket` → Helpdesk
- `envoyer_reponse` → Email/Chat

### Metriques de succes

| Metrique | Cible |
|---|---|
| Resolution automatique | 60% |
| Temps de reponse | 30s |
| Score CSAT | 4.2/5 |
| Charge agent | -40% |

---

## Points cles a retenir

- **Commencer par la valeur metier** : un agent IA se justifie par un gain mesurable. Valider l'opportunite avant de choisir la technologie.
- **Cadrer avant de coder** : un cahier des charges rigoureux evite les derives couteuses. Definir entrees, sorties et KPIs des le depart.
- **Architecture en couches** : les 7 couches garantissent un agent robuste, maintenable et evolutif. Ne pas negliger la gouvernance.
- **Gouvernance non negociable** : RGPD, tracabilite, garde-fous — la conformite doit etre integree des la conception, pas ajoutee apres.
- **Commencer petit, iterer vite** : un pilote cible sur un processus simple permet de valider l'approche avant de passer a l'echelle.

---

## Competences acquises

- Identifier les processus metiers automatisables par un agent IA
- Choisir le bon type d'agent (reactif, ReAct, planificateur) selon le contexte
- Rediger un cahier des charges fonctionnel rigoureux
- Concevoir une architecture en 7 couches
- Specifier des outils (tools) robustes et documentes
- Integrer la securite et la gouvernance des la conception
- Structurer les donnees et la preparation pour un agent performant
- Impliquer les bonnes parties prenantes dans un projet d'agent IA
