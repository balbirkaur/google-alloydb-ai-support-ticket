CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration;

CREATE TABLE IF NOT EXISTS support_tickets (
   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
   description TEXT,
   issue_type TEXT,
   status TEXT,
   priority TEXT,
   embedding VECTOR(768),
   created_at TIMESTAMP DEFAULT NOW()
);