# 📘 DOSSIER TECHNIQUE D'ARCHITECTURE : SaaS RH-IA V3
**Conception d'une plateforme SaaS RH intelligente et Event-Driven**

---

## 1. Introduction & Objectif du Projet
Le projet SaaS RH-IA V3 est une solution cloud B2B multi-tenant conçue pour révolutionner la gestion des ressources humaines. L'objectif principal est de fournir aux entreprises une plateforme intégrée, scalable et intelligente capable de gérer l'intégralité du cycle de vie d'un collaborateur : du recrutement (parsing de CV, chatbot IA), à l'évaluation, jusqu'à la validation hiérarchique, la génération documentaire, l'onboarding et l'analyse prédictive du turnover (matrice 9-Box).

Ce document détaille l'architecture logicielle, les workflows asynchrones, la modélisation des données et l'implémentation de l'Intelligence Artificielle qui rendent cette plateforme conforme aux standards industriels actuels.

---

## 2. Architecture Globale du Système

La plateforme repose sur une architecture **Modulaire, API-First et Event-Driven**. Elle est conçue pour garantir une séparation stricte des préoccupations (Sécurité, Métier, IA, Présentation) tout en assurant une haute scalabilité.

### 2.1. Choix Technologiques
- **Frontend** : Vanilla HTML/JS/CSS (Glassmorphism & composants dynamiques) pour une performance brute et une intégration native.
- **Backend (API Gateway & Logique)** : Python avec **FastAPI**. Choisi pour ses performances asynchrones (`asyncio`), idéales pour gérer les I/O intensifs (Appels IA, génération PDF).
- **Base de Données & Auth** : **Supabase** (PostgreSQL). Fournit le RLS (Row Level Security) crucial pour l'isolation multi-tenant, le stockage S3 pour les CV/Logos, et la gestion d'identité (Auth).
- **Couche IA** : **Groq API** (Modèles Llama-3/Mixtral) pour une inférence ultra-rapide (parsing de CV, chatbot, scoring).
- **Déploiement (DevOps)** : Vercel (Serverless) pour le backend/frontend, garantissant une haute disponibilité.

### 2.2. Schéma Architectural
```mermaid
graph TD
    Client[Navigateur / Utilisateur] -->|HTTPS| API[FastAPI Gateway]
    
    subgraph Backend [Backend Core (FastAPI)]
        API --> Auth[Auth Middleware]
        Auth --> Routes[Modules Métier]
        
        Routes --> Bus((Event Bus))
        Bus --> Handlers[Event Handlers]
        
        Routes --> PDF[Document Generator]
    end

    subgraph Intelligence Artificielle
        Routes --> AI[AI Service]
        Handlers --> AI
        AI -->|REST API| Groq[Groq Llama-3]
    end

    subgraph Infrastructure Data (Supabase)
        Routes --> DB[(PostgreSQL)]
        Handlers --> DB
        Auth --> SupaAuth[Supabase Auth]
        PDF --> Storage[S3 Storage Bucket]
    end
```

---

## 3. Architecture Event-Driven (Communication Inter-Modules)

Pour éviter un couplage fort entre les 12 modules de l'application, nous avons implémenté un **Event Bus** asynchrone (Pub/Sub). Les actions utilisateur émettent des événements qui déclenchent des tâches en arrière-plan sans bloquer la requête HTTP.

### 3.1. Les Événements Clés
- `candidate_created` : Déclenché lors du dépôt d'un CV.
- `chatbot_completed` : Fin de l'entretien interactif IA.
- `evaluation_submitted` : Validation de l'évaluation technique par le RH.
- `approval_completed` : Signature finale par le Directeur Général.
- `employee_created` : Passage du statut de candidat à employé.

### 3.2. Scénario de Flux Complet (Recrutement → Onboarding)
1. **Émission** : Le candidat postule. Le frontend appelle l'API. Le module de recrutement insère les données et publie `candidate_created`.
2. **Réaction (Asynchrone)** : L'Event Bus intercepte l'événement. Il déclenche le **Parsing IA** du CV et l'envoi d'un email (Notification Module) invitant le candidat au Chatbot.
3. **Poursuite** : Le candidat passe le chatbot. `chatbot_completed` est émis. Le RH est notifié.
4. **Validation** : Le RH évalue. Si le score IA + RH dépasse 70%, `evaluation_submitted` déclenche la création de la *Demande d'Approbation*.
5. **Onboarding** : Lorsque le DG signe la demande, `approval_completed` est émis. Cela lance la génération du contrat (Doc 5.2), crée l'employé dans la base, publie `employee_created`, ce qui génère automatiquement les accès SaaS et les tâches d'onboarding.

---

## 4. Workflow Engine & Orchestration

Le moteur de workflow (Workflow Module) gère la machine à états (State Machine) des candidats. Les transitions sont strictement contrôlées par des règles métier.

### 4.1. Les États du Pipeline
1. `new` : Nouvelle candidature.
2. `screening` : Analyse IA en cours.
3. `chatbot_invite` / `chatbot_completed` : Phase d'entretien interactif.
4. `evaluation_completed` : RH a donné son avis.
5. `approved` : Validé par les directeurs.
6. `hired` : Employé intégré (Onboarding initié).
7. `rejected` : Candidature écartée.

### 4.2. Règles de Décision Automatisées
- **Auto-Rejet** : Si le scoring combiné (CV + Chatbot) est `< 50%`, l'état passe automatiquement à `rejected` sans intervention humaine.
- **Auto-Approbation** : Si le score est `> 70%`, le passage à l'état de validation hiérarchique est automatique.
- **Sécurité (RLS)** : Une transition d'état d'un candidat appartenant au `Tenant A` ne peut être effectuée ou vue que par les utilisateurs du `Tenant A`.

---

## 5. Intégration de l'Intelligence Artificielle (AI Module)

L'IA n'est pas un simple gadget, elle est le moteur décisionnel du SaaS. Nous utilisons des LLM via l'API Groq pour plusieurs cas d'usage précis.

### 5.1. Parsing de CV et Scoring (Recrutement)
- **Logique** : Le texte du CV est extrait puis envoyé au LLM avec un *System Prompt* strict forçant une réponse en JSON (`json_mode`).
- **Résultat** : Extraction structurée des compétences, des années d'expérience et calcul d'un score de "Matching" (0-100) vis-à-vis de l'offre d'emploi.

### 5.2. Chatbot Pré-qualificatif Interactif
- **Logique** : Un agent conversationnel dynamique. Il pose 3 questions techniques générées à la volée en fonction du CV du candidat et de la description du poste.
- **Qualification** : À la fin de la conversation, un autre prompt évalue les réponses du candidat pour générer un résumé analytique et un score de communication.

### 5.3. Recommandation Décisionnelle (Approbation)
- Lors de la création du Document 5.2, l'IA rédige une justification professionnelle (Recommandation) synthétisant pourquoi ce profil est adéquat pour l'entreprise, détectant d'éventuels risques (ex: instabilité professionnelle).

---

## 6. Génération de Documents RH (Document Module) - CRITIQUE

Conformément aux exigences légales et opérationnelles, le SaaS génère à la volée des documents PDF professionnels (ReportLab) stockés sur le Cloud.

### 6.1. Compte Rendu d'Entretien (Doc 5.1)
Généré lors de la soumission de l'évaluation RH.
- **Contenu Dynamique** : Identité du candidat, intitulé exact du poste, matrice d'évaluation (Technique, Soft Skills, Motivation sur 5 étoiles), Score global calculé, et observations libres.
- **Branding** : Intégration automatique du logo du Tenant (Entreprise) au format en-tête d'entreprise.

### 6.2. Demande d'Approbation RH (Doc 5.2)
Généré lors de la complétion du circuit de signature (DG).
- **Moteur de Paie Intégré** : Le système calcule dynamiquement la structure salariale marocaine (Salaire de Base, Primes d'Ancienneté, Indemnités de Panier/Transport, Taux CIMR, Salaire Brut/Net) selon la situation familiale du candidat.
- **Layout Strict** : Structure en 2 colonnes avec coloration bleue institutionnelle.
- **Circuit de Signatures** : Apposition dynamique des noms et dates pour les 4 directeurs (Hiérarchique, Fonctionnel, RH, DG) prouvant la validité du workflow.

---

## 7. Modélisation des Données (Base de Données)

La base de données relationnelle PostgreSQL est structurée autour du concept de **Multi-Tenancy**. Chaque table critique possède une clé étrangère `tenant_id`.

### Tables Principales :
1. `tenants` : Les entreprises clientes (id, name, domain, logo_url).
2. `users` : Le personnel (id, tenant_id, role, email, active).
3. `job_offers` : Les fiches de poste (title, description, salaire_base, workflow_id).
4. `candidates` : Les postulants (id, tenant_id, job_offer_id, pipeline_stage, ai_extracted_data).
5. `approval_requests` : Suivi des signatures (id, candidate_id, signed_hr_at, signed_dg_at, status).
6. `employees` & `onboarding_tasks` : Créés post-recrutement.

---

## 8. Indicateurs de Performance (KPIs) & Modules Analytiques

Le SaaS intègre des modules analytiques exploitant les données générées par le workflow.

### 8.1. Talent Module (Matrice 9-Box)
Évalue les employés selon 2 axes (Performance vs Potentiel). L'interface RH permet de visualiser instantanément la répartition des "High Potentials" et des profils nécessitant un accompagnement.

### 8.2. Turnover Module & KPIs
- **Risque de Turnover** : Algorithme (simulé/IA) analysant l'ancienneté, les scores de performance et l'évolution salariale pour attribuer un risque (Low, Medium, High).
- **KPIs Suivis** : Taux de conversion (Candidature -> Entretien), Temps moyen d'approbation (SLA), Taux de complétion de l'onboarding.

---

## 9. Sécurité & Multi-Tenancy

- **Authentification** : Gestion par Supabase Auth (JWT). 
- **Autorisation (RBAC)** : Middlewares FastAPI bloquant l'accès selon le `role` (Super_Admin, Directeur_RH, DG, etc.).
- **Isolation des Données (RLS)** : Supabase Row Level Security garantit qu'une requête SQL effectuée par le RH de l'Entreprise A ne pourra techniquement jamais renvoyer les candidats de l'Entreprise B, même en cas de faille logicielle.

---

## 10. Scalabilité & Traitements Asynchrones (Jobs Module)

- **Scalabilité Horizontale** : L'API FastAPI étant "Stateless", elle peut être dupliquée sur de multiples instances (Serverless sur Vercel).
- **Tâches Asynchrones (APScheduler)** : Des scripts tournent en arrière-plan (Background Tasks) pour le nettoyage des données, la relance automatique des approbateurs (SLA de 48h dépassé) et le calcul massif des scores de turnover pendant les heures creuses.

---

## 11. Conclusion

Le SaaS RH-IA V3 est une architecture de grade industriel qui démontre comment l'orchestration événementielle, associée à l'Intelligence Artificielle générative, peut automatiser plus de 70% des tâches administratives RH (parsing, screening, génération de contrats). Le code source modulaire, l'isolation multi-tenant stricte et l'approche API-first assurent à cette solution une maintenabilité et une évolutivité parfaites pour un déploiement réel.
