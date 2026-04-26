-- =====================================================
-- Migration 002 — Enrichissement Profil Candidat Self-Service
-- =====================================================

-- Nouveaux champs profil candidat (enrichissement pour scoring IA)
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS ville VARCHAR(100);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS diplome VARCHAR(100);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS etablissement VARCHAR(255);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS dernier_poste VARCHAR(255);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS annees_experience VARCHAR(50);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS pretentions_salariales DECIMAL(12,2);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS disponibilite VARCHAR(50);
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS motivation TEXT;
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS ai_extracted_data JSONB DEFAULT '{}';
ALTER TABLE candidates ADD COLUMN IF NOT EXISTS profile_completion INTEGER DEFAULT 0;

-- Ajouter le rôle 'employe' dans la contrainte users
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (
  role IN (
    'super_admin','directeur_hierarchique','directeur_fonctionnel',
    'directeur_rh','directeur_general','candidat','employe'
  )
);

-- Index pour accès rapide candidat → user
CREATE INDEX IF NOT EXISTS idx_candidates_user ON candidates(user_id);
