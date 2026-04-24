-- =====================================================
-- SaaS RH Multi-Tenant V3 — Schéma PostgreSQL Supabase
-- =====================================================

-- 1. TENANTS
CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  domain VARCHAR(255) UNIQUE,
  slug VARCHAR(100) UNIQUE NOT NULL,
  logo_url TEXT,
  primary_color VARCHAR(7) DEFAULT '#1E40AF',
  secondary_color VARCHAR(7) DEFAULT '#F59E0B',
  cimr_rate DECIMAL(5,2) DEFAULT 6.00,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. USERS
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  email VARCHAR(255),
  role VARCHAR(50) CHECK (role IN (
    'super_admin','directeur_hierarchique','directeur_fonctionnel',
    'directeur_rh','directeur_general','candidat'
  )) DEFAULT 'candidat',
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. JOB_OFFERS
CREATE TABLE IF NOT EXISTS job_offers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  created_by UUID REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  reference VARCHAR(100),
  entity_organisationnelle VARCHAR(255),
  site VARCHAR(255),
  fonction VARCHAR(255),
  type_remuneration VARCHAR(50),
  grade VARCHAR(10),
  salaire_base DECIMAL(12,2),
  indemnite_panier DECIMAL(12,2) DEFAULT 0,
  indemnite_transport DECIMAL(12,2) DEFAULT 0,
  prime_loyer DECIMAL(12,2) DEFAULT 0,
  prime_aid DECIMAL(12,2) DEFAULT 0,
  taux_cimr DECIMAL(5,2) DEFAULT 6.00,
  description TEXT,
  requirements TEXT,
  is_published BOOLEAN DEFAULT false,
  is_budgeted BOOLEAN DEFAULT false,
  status VARCHAR(50) DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  published_at TIMESTAMPTZ
);

-- 4. CANDIDATES
CREATE TABLE IF NOT EXISTS candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  user_id UUID REFERENCES users(id),
  job_offer_id UUID REFERENCES job_offers(id),
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(20),
  birth_date DATE,
  situation_familiale VARCHAR(50),
  personnes_a_charge INTEGER DEFAULT 0,
  cv_url TEXT,
  cv_text TEXT,
  ai_score DECIMAL(5,2),
  ai_skills JSONB,
  ai_summary TEXT,
  pipeline_stage VARCHAR(50) DEFAULT 'applied',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. CHATBOT_SESSIONS
CREATE TABLE IF NOT EXISTS chatbot_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  candidate_id UUID REFERENCES candidates(id),
  messages JSONB DEFAULT '[]',
  qualification_score DECIMAL(5,2),
  is_completed BOOLEAN DEFAULT false,
  groq_analysis JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. EVALUATIONS
CREATE TABLE IF NOT EXISTS evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  candidate_id UUID REFERENCES candidates(id),
  evaluator_id UUID REFERENCES users(id),
  criteria JSONB,
  global_score DECIMAL(5,2),
  final_opinion VARCHAR(20),
  comments TEXT,
  groq_suggestion TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. APPROVAL_REQUESTS
CREATE TABLE IF NOT EXISTS approval_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  candidate_id UUID REFERENCES candidates(id),
  job_offer_id UUID REFERENCES job_offers(id),
  nom_collaborateur VARCHAR(255),
  date_embauche DATE,
  date_naissance DATE,
  situation_familiale VARCHAR(50),
  personnes_a_charge INTEGER,
  salaire_base DECIMAL(12,2),
  prime_anciennete DECIMAL(12,2) DEFAULT 0,
  indemnite_representation DECIMAL(12,2) DEFAULT 0,
  indemnite_panier DECIMAL(12,2) DEFAULT 0,
  indemnite_gsm DECIMAL(12,2) DEFAULT 0,
  indemnite_transport DECIMAL(12,2) DEFAULT 0,
  prime_loyer DECIMAL(12,2) DEFAULT 0,
  salaire_mensuel_brut DECIMAL(12,2),
  salaire_mensuel_net DECIMAL(12,2),
  salaire_annuel_garanti DECIMAL(12,2),
  salaire_annuel_total DECIMAL(12,2),
  taux_cimr DECIMAL(5,2),
  prime_aid DECIMAL(12,2) DEFAULT 0,
  status VARCHAR(50) DEFAULT 'pending_hierarchique',
  signed_hierarchique_at TIMESTAMPTZ,
  signed_fonctionnel_at TIMESTAMPTZ,
  signed_rh_at TIMESTAMPTZ,
  signed_dg_at TIMESTAMPTZ,
  rejected_by UUID REFERENCES users(id),
  rejection_reason TEXT,
  pdf_url TEXT,
  groq_recommendation JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. WORKFLOW_STATES
CREATE TABLE IF NOT EXISTS workflow_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  entity_type VARCHAR(50),
  entity_id UUID NOT NULL,
  current_state VARCHAR(100),
  previous_state VARCHAR(100),
  triggered_by UUID REFERENCES users(id),
  event_name VARCHAR(100),
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. EMPLOYEES
CREATE TABLE IF NOT EXISTS employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  candidate_id UUID REFERENCES candidates(id),
  approval_request_id UUID REFERENCES approval_requests(id),
  matricule VARCHAR(50),
  full_name VARCHAR(255),
  email VARCHAR(255),
  date_embauche DATE,
  poste VARCHAR(255),
  departement VARCHAR(255),
  salaire DECIMAL(12,2),
  onboarding_status VARCHAR(50) DEFAULT 'in_progress',
  onboarding_steps JSONB DEFAULT '[]',
  performance_score DECIMAL(3,1) DEFAULT 1.0,
  potential_score DECIMAL(3,1) DEFAULT 1.0,
  nine_box_position VARCHAR(100),
  turnover_risk_score DECIMAL(5,2),
  status VARCHAR(50) DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. ONBOARDING_TASKS
CREATE TABLE IF NOT EXISTS onboarding_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id),
  title VARCHAR(255) NOT NULL,
  category VARCHAR(100),
  status VARCHAR(50) DEFAULT 'PENDING',
  due_date DATE,
  completed_at TIMESTAMPTZ,
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. TALENT_MATRIX
CREATE TABLE IF NOT EXISTS talent_matrix (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id),
  performance_score DECIMAL(3,1) NOT NULL,
  potential_score DECIMAL(3,1) NOT NULL,
  nine_box_label VARCHAR(100),
  ai_analysis JSONB,
  evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. TURNOVER_RISKS
CREATE TABLE IF NOT EXISTS turnover_risks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id),
  risk_score DECIMAL(5,2) DEFAULT 0,
  risk_level VARCHAR(20) DEFAULT 'LOW',
  factors JSONB DEFAULT '[]',
  recommendations JSONB DEFAULT '[]',
  retention_probability DECIMAL(5,2) DEFAULT 100,
  analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. DOCUMENTS
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  candidate_id UUID REFERENCES candidates(id),
  approval_request_id UUID REFERENCES approval_requests(id),
  type VARCHAR(50) NOT NULL,
  file_url TEXT,
  generated_by UUID REFERENCES users(id),
  generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  tenant_id UUID REFERENCES tenants(id),
  title VARCHAR(255),
  message TEXT,
  type VARCHAR(50),
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. AUDIT_LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id),
  user_id UUID REFERENCES users(id),
  action VARCHAR(255),
  entity_type VARCHAR(100),
  entity_id UUID,
  metadata JSONB,
  ip_address INET,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 16. ERROR_LOGS (système de monitoring)
CREATE TABLE IF NOT EXISTS error_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID,
  user_id UUID,
  level VARCHAR(20) DEFAULT 'ERROR',
  module VARCHAR(100),
  endpoint VARCHAR(255),
  message TEXT,
  traceback TEXT,
  request_data JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- ROW-LEVEL SECURITY
-- =====================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chatbot_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE talent_matrix ENABLE ROW LEVEL SECURITY;
ALTER TABLE turnover_risks ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policies (via service_role bypass côté backend)
CREATE POLICY "tenant_isolation_job_offers" ON job_offers
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_candidates" ON candidates
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_approvals" ON approval_requests
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_employees" ON employees
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_evaluations" ON evaluations
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_chatbot" ON chatbot_sessions
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_workflow" ON workflow_states
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_notifications" ON notifications
  USING (user_id = auth.uid());

CREATE POLICY "tenant_isolation_onboarding" ON onboarding_tasks
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_talent" ON talent_matrix
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_turnover" ON turnover_risks
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

CREATE POLICY "tenant_isolation_documents" ON documents
  USING (tenant_id = (SELECT tenant_id FROM users WHERE id = auth.uid()));

-- Users policies
CREATE POLICY "users_read_own" ON users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "users_admin_all" ON users
  FOR ALL USING (
    (SELECT role FROM users WHERE id = auth.uid()) = 'super_admin'
  );

CREATE POLICY "users_insert_self" ON users
  FOR INSERT WITH CHECK (true); -- Allow signup

-- =====================================================
-- INDEXES
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_candidates_tenant ON candidates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates(pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_candidates_job ON candidates(job_offer_id);
CREATE INDEX IF NOT EXISTS idx_job_offers_tenant ON job_offers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_job_offers_status ON job_offers(status);
CREATE INDEX IF NOT EXISTS idx_approval_tenant ON approval_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_employees_tenant ON employees(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_error_logs_level ON error_logs(level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_entity ON workflow_states(entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_logs(tenant_id, created_at DESC);
