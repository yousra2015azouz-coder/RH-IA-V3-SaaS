-- Seed data for testing
-- Run after 001_initial_schema.sql

-- Tenant de démonstration
INSERT INTO tenants (id, name, slug, domain, primary_color, secondary_color, cimr_rate, is_active)
VALUES (
  'a0000000-0000-0000-0000-000000000001',
  'Entreprise Démo SA',
  'demo',
  'demo.localhost',
  '#1E40AF',
  '#F59E0B',
  6.00,
  true
) ON CONFLICT (slug) DO NOTHING;

-- Note: Les users sont créés via Supabase Auth (auth.users)
-- puis le profil est inséré dans public.users par le backend au signup.

-- Offre d'emploi de démonstration (sans created_by pour le seed)
INSERT INTO job_offers (
  id, tenant_id, title, reference, entity_organisationnelle,
  site, fonction, type_remuneration, grade,
  salaire_base, indemnite_transport, indemnite_panier,
  taux_cimr, description, requirements,
  is_published, is_budgeted, status
) VALUES (
  'b0000000-0000-0000-0000-000000000001',
  'a0000000-0000-0000-0000-000000000001',
  'Responsable RH Senior',
  'RH-2026-001',
  'Direction des Ressources Humaines',
  'Siège - Casablanca',
  'Responsable RH',
  'Fixe',
  'S3',
  18000.00,
  550.00,
  550.00,
  6.00,
  'Nous recherchons un(e) Responsable RH Senior pour piloter la politique RH de notre groupe. Vous serez en charge du recrutement, de la gestion des carrières et du développement des compétences.',
  'Bac+5 en RH ou Management. Minimum 5 ans d''expérience en RH. Maîtrise du droit du travail marocain. Excellentes compétences en communication.',
  true,
  true,
  'published'
) ON CONFLICT DO NOTHING;

INSERT INTO job_offers (
  id, tenant_id, title, reference, entity_organisationnelle,
  site, fonction, type_remuneration, grade,
  salaire_base, indemnite_transport,
  taux_cimr, description, requirements,
  is_published, is_budgeted, status
) VALUES (
  'b0000000-0000-0000-0000-000000000002',
  'a0000000-0000-0000-0000-000000000001',
  'Développeur Full-Stack',
  'IT-2026-003',
  'Direction Informatique',
  'Siège - Casablanca',
  'Développeur',
  'Fixe + Variable',
  'S2',
  15000.00,
  550.00,
  6.00,
  'Rejoignez notre équipe tech pour développer des solutions innovantes. Vous travaillerez sur des projets React/FastAPI en méthode agile.',
  'Bac+5 Informatique. 3+ ans d''expérience. Maîtrise React, Python/FastAPI, PostgreSQL. Expérience CI/CD souhaitée.',
  true,
  true,
  'published'
) ON CONFLICT DO NOTHING;
