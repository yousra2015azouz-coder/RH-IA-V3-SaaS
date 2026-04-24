# SaaS RH Multi-Tenant — Plan d'Implémentation V3

## Objectif
Construire **from scratch** dans `c:\Users\Session Youssef\Desktop\RH-IA V3\` une plateforme SaaS RH multi-tenant complète, fonctionnelle et exécutable, selon le prompt fourni.

**Stack** : FastAPI · Supabase PostgreSQL + RLS · GROQ API · Vanilla JS/HTML/CSS · ReportLab · APScheduler · EventBus

---

## Structure Cible (exacte du prompt)

```
saas-rh/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── auth/           router.py · dependencies.py · models.py
│   ├── tenants/        router.py · models.py · service.py
│   ├── modules/
│   │   ├── recruitment/   router.py · models.py · service.py
│   │   ├── chatbot/       router.py · service.py
│   │   ├── evaluation/    router.py · service.py
│   │   ├── approval/      router.py · service.py
│   │   ├── onboarding/    router.py · service.py
│   │   ├── talent/        router.py · service.py
│   │   ├── turnover/      router.py · service.py
│   │   ├── documents/     router.py · service.py
│   │   ├── notifications/ service.py
│   │   └── ai/            groq_client.py · cv_parser.py · scorer.py · recommender.py
│   ├── events/         bus.py · handlers.py
│   ├── workflow/       engine.py · states.py
│   ├── jobs/           scheduler.py
│   └── utils/          pdf_generator.py · helpers.py
├── frontend/
│   ├── public/         index.html · job-detail.html · apply.html
│   ├── auth/           login.html · register.html
│   ├── dashboards/
│   │   ├── super_admin/index.html
│   │   ├── directeur_rh/   index.html · jobs.html · candidates.html · approvals.html
│   │   ├── directeur_hierarchique/index.html
│   │   ├── directeur_fonctionnel/index.html
│   │   └── directeur_general/index.html
│   └── assets/         css/theme.css · js/api.js · js/auth.js · js/tenant.js
├── supabase/
│   ├── migrations/001_initial_schema.sql
│   └── seed.sql
├── .env.example
├── requirements.txt
└── README.md
```

---

## Phase 1 — Config & Database

### [NEW] `backend/config.py`
- Chargement `.env` (GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, JWT_SECRET)
- Instances singleton : `supabase_admin`, `groq_client`
- Constantes : modèles GROQ, rate limits

### [NEW] `backend/database.py`
- Helper `get_data(result)` 
- Méthodes CRUD réutilisables

### [NEW] `supabase/migrations/001_initial_schema.sql`
10 tables du prompt :
`tenants · users · job_offers · candidates · chatbot_sessions · evaluations · approval_requests · workflow_states · employees · audit_logs`

Avec RLS + policy `tenant_isolation` sur chaque table.

---

## Phase 2 — Auth & Tenants

### [NEW] `backend/auth/`
- `POST /api/v1/auth/login` → Supabase sign_in → JWT + profil utilisateur
- `POST /api/v1/auth/signup` → créer compte candidat
- `dependencies.py` → `get_current_user()`, `require_roles([])`

### [NEW] `backend/tenants/`
- `GET/POST/PATCH /api/v1/tenants` (super_admin only)
- Branding par tenant (couleurs, logo, domaine)

---

## Phase 3 — Modules IA (GROQ)

### [NEW] `backend/modules/ai/groq_client.py`
```python
async def call_groq(system_prompt, user_content,
    model="llama3-70b-8192", temperature=0.3, max_tokens=2048) -> str
```

### [NEW] `backend/modules/ai/cv_parser.py`
- Input : texte brut CV (PyMuPDF)
- Output JSON : `{skills, experience_years, education, languages, score_pertinence}`
- Comparaison avec `job_offer.requirements`
- Score 0-100

### [NEW] `backend/modules/ai/scorer.py`
- Score matching candidat/poste
- `decision: PROCEED | REJECT`
- `points_forts, points_faibles, recommandation`

### [NEW] `backend/modules/ai/recommender.py`
- Recommandation décision approbation (mixtral-8x7b-32768)
- Détection biais, conditions, risques

---

## Phase 4 — Recrutement

### [NEW] `backend/modules/recruitment/router.py`
| Méthode | Endpoint | Rôle |
|---------|----------|------|
| POST | `/api/v1/jobs` | directeur_rh |
| GET | `/api/v1/jobs/public/{tenant_slug}` | PUBLIC |
| GET | `/api/v1/jobs/{id}` | authentifié |
| PATCH | `/api/v1/jobs/{id}/publish` | directeur_rh |
| POST | `/api/v1/jobs/{id}/apply` | candidat |
| GET | `/api/v1/candidates` | rh/managers |
| GET | `/api/v1/candidates/{id}` | rh/managers |
| PATCH | `/api/v1/candidates/{id}/stage` | rh |
| GET | `/api/v1/dashboard/rh` | directeur_rh |

### [NEW] `backend/modules/recruitment/service.py`
- Upload CV → PyMuPDF extract → GROQ parse → score
- Publish event `candidate_created`
- KPIs dashboard (pipeline_distribution, avg_ai_score, etc.)

---

## Phase 5 — Chatbot

### [NEW] `backend/modules/chatbot/`
- Session GROQ 5 questions séquentielles
- Scoring comportemental final
- `POST /api/v1/chatbot/session` · `POST /api/v1/chatbot/message`
- Event `chatbot_completed` → pipeline_stage = interview

---

## Phase 6 — Évaluation

### [NEW] `backend/modules/evaluation/`
- Grille critères (1-5 par axe)
- GROQ suggère score global
- `POST /api/v1/evaluations`
- Event `evaluation_submitted`

---

## Phase 7 — Approbation (Workflow 4 Signatures)

### [NEW] `backend/modules/approval/service.py`

**Calculs fiscaux marocains :**
```
CNSS     = min(salaire_brut, 6000) × 4.48%
AMO      = salaire_brut × 2.26%
IR       = tranches progressives (0-30K: 0%, 30-50K: 10%, ...)
CIMR     = salaire_brut × taux_cimr
Net      = Brut - IR - CNSS - AMO - CIMR
SAG      = Net × 13.33  (+ primes)
SAT      = SAG + avantages annuels
```

**Workflow séquentiel :**
```
pending_hierarchique → pending_fonctionnel → pending_rh → pending_dg → approved
                                                                      ↘ rejected
```
- Chaque signature notifie le suivant
- GROQ recommandation avant validation DG
- À la 4ème signature → event `approval_completed`

### [NEW] `backend/modules/approval/router.py`
- `POST /api/v1/approval/request`
- `POST /api/v1/approval/{id}/sign`
- `POST /api/v1/approval/{id}/reject`
- `GET  /api/v1/approval/{id}/status`

---

## Phase 8 — Documents PDF

### [NEW] `backend/utils/pdf_generator.py` + `backend/modules/documents/service.py`

**Document 1 — Compte Rendu d'Entretien :**
- Candidat, poste, critères 1-5, score global, avis final
- Généré avec ReportLab

**Document 2 — Demande d'Approbation RH :**
- Sections : Nature | Infos générales | Infos organisationnelles | Situation salariale | Avantages | Positionnement salarial | Commentaires | Approbations (4 zones signature)
- Upload Supabase Storage → URL publique retournée

---

## Phase 9 — Onboarding · Talent · Turnover

### [NEW] `backend/modules/onboarding/`
- Steps onboarding (GROQ génère plan personnalisé)
- Progress tracker par employee
- Event `employee_created` → init steps

### [NEW] `backend/modules/talent/`
- Matrice 9-Box (performance × potentiel)
- GROQ analyse par position (mixtral-8x7b-32768)
- `POST /api/v1/talent/evaluate`

### [NEW] `backend/modules/turnover/`
- Prédiction risque départ (mixtral-8x7b-32768)
- risk_level : LOW | MEDIUM | HIGH | CRITICAL
- Alertes automatiques si CRITICAL

---

## Phase 10 — Infrastructure

### [NEW] `backend/events/bus.py`
EventBus pub/sub Python :
| Événement | Handler |
|-----------|---------|
| `candidate_created` | cv_parser + chatbot_start |
| `chatbot_completed` | update pipeline_stage |
| `evaluation_submitted` | workflow + approval creation |
| `approval_completed` | pdf_generation + employee_create |
| `employee_created` | onboarding_steps init |
| `risk_detected` | alert_manager + notify DRH |

### [NEW] `backend/workflow/engine.py`
FSM transitions validées :
```
applied → chatbot → interview → evaluation → approved/rejected → hired
```
Règles auto :
- score ≥ 70 → approval auto
- score 50-69 → review manuelle
- score < 50 → rejet auto + notification candidat

### [NEW] `backend/jobs/scheduler.py`
APScheduler :
- Rappels approbations en attente (quotidien)
- Analyse turnover (hebdomadaire)
- Nettoyage sessions expirées

---

## Phase 10b — Error Tracking System

### [NEW] `backend/modules/error_tracker/`
Système de capture, stockage et visualisation des erreurs en temps réel.

**Table SQL** `error_logs` :
```sql
CREATE TABLE error_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID,
  user_id UUID,
  level VARCHAR(20),  -- ERROR | WARNING | INFO | CRITICAL
  module VARCHAR(100),
  endpoint VARCHAR(255),
  message TEXT,
  traceback TEXT,
  request_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Composants** :
- `backend/modules/error_tracker/service.py` — `log_error()` appelé dans chaque except
- `backend/modules/error_tracker/router.py` — `GET /api/v1/errors` (super_admin)
- Global exception handler FastAPI → stocke tout en DB
- `frontend/dashboards/super_admin/errors.html` — Dashboard erreurs temps réel (filtres par level/module/date)

---

## Phase 11 — Frontend

### Design System (`frontend/assets/css/theme.css`)
- Dark mode + glassmorphism
- Couleurs : `#1E40AF` (primary) + `#F59E0B` (accent)
- Police : Inter (Google Fonts)
- Animations micro-interactions

### Pages Publiques
- `public/index.html` — Offres par tenant (slug dans URL)
- `public/apply.html` — Formulaire multi-étapes + upload CV + chatbot

### Auth
- `auth/login.html` — Login + redirection par rôle
- `auth/register.html` — Inscription candidat

### Dashboards
| Dashboard | Contenu |
|-----------|---------|
| `super_admin/index.html` | Gestion tenants, stats globales |
| `directeur_rh/index.html` | KPIs animés, pipeline kanban |
| `directeur_rh/jobs.html` | CRUD offres d'emploi |
| `directeur_rh/candidates.html` | Pipeline + scores IA |
| `directeur_rh/approvals.html` | Demandes en cours |
| `directeur_hierarchique/index.html` | Validation hiérarchique |
| `directeur_fonctionnel/index.html` | Validation fonctionnelle |
| `directeur_general/index.html` | Décision finale + GROQ recommendation |

### JS Client (`frontend/assets/js/`)
- `api.js` — Fetch avec JWT, refresh, error handling
- `auth.js` — Login/logout/redirect par rôle
- `tenant.js` — Résolution tenant depuis URL/subdomain

---

## Phase 12 — Config Finale

### [NEW] `requirements.txt`
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
groq==0.9.0
supabase==2.4.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
apscheduler==3.10.4
httpx==0.27.0
PyMuPDF==1.24.3
reportlab==4.1.0
python-dotenv==1.0.1
```

### [NEW] `.env.example`
```
GROQ_API_KEY=gsk_xxxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx
SUPABASE_SERVICE_KEY=eyJxxx
JWT_SECRET_KEY=your_secret_key_min_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## Ordre d'Exécution

1. `requirements.txt` + `.env.example` + `README.md`
2. `supabase/migrations/001_initial_schema.sql` + `seed.sql`
3. `backend/config.py` + `backend/database.py`
4. `backend/auth/` (login, signup, middleware)
5. `backend/tenants/` (CRUD super_admin)
6. `backend/modules/ai/` (groq_client, cv_parser, scorer, recommender)
7. `backend/modules/recruitment/` (jobs + pipeline)
8. `backend/modules/chatbot/` + `backend/modules/evaluation/`
9. `backend/modules/approval/` (calculs fiscaux + workflow 4 signatures)
10. `backend/utils/pdf_generator.py` + `backend/modules/documents/`
11. `backend/modules/onboarding/` + `talent/` + `turnover/`
12. `backend/modules/notifications/` + `backend/events/` + `backend/workflow/`
13. `backend/jobs/scheduler.py` + `backend/main.py`
14. `frontend/assets/` (theme.css, api.js, auth.js, tenant.js)
15. `frontend/public/` (index, job-detail, apply)
16. `frontend/auth/` (login, register)
17. `frontend/dashboards/` (tous les rôles)

---

## Vérification Finale
- `uvicorn backend.main:app --reload --port 8000`
- `GET /health` → `{api: true, database: true, groq: true}`
- `GET /docs` → Swagger complet
- Portail public : `http://localhost:8000/`
