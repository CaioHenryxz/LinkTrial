PRAGMA foreign_keys=ON;
PRAGMA secure_delete=ON;
CREATE TABLE IF NOT EXISTS patients(id TEXT PRIMARY KEY, pseudonym TEXT NOT NULL UNIQUE, institution TEXT NOT NULL, clinical_cipher TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS consents(id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE, purpose TEXT NOT NULL CHECK(purpose IN ('matching','referral')), granted INTEGER NOT NULL CHECK(granted IN (0,1)), notice_version TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS consent_patient ON consents(patient_id,purpose,at);
CREATE TABLE IF NOT EXISTS studies(id TEXT PRIMARY KEY, title TEXT NOT NULL, source TEXT NOT NULL, registry_status TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1, verified_at TEXT, version INTEGER NOT NULL DEFAULT 1, body_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS study_versions(id TEXT PRIMARY KEY, study_id TEXT NOT NULL REFERENCES studies(id), version INTEGER NOT NULL, body_json TEXT NOT NULL, at TEXT NOT NULL, UNIQUE(study_id,version));
CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE, study_id TEXT NOT NULL REFERENCES studies(id), patient_version INTEGER NOT NULL, study_version INTEGER NOT NULL, result_cipher TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, match_id TEXT NOT NULL REFERENCES matches(id) ON DELETE CASCADE, decision TEXT NOT NULL CHECK(decision IN ('forward','hold')), note_cipher TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS referrals(id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE, study_id TEXT NOT NULL REFERENCES studies(id), review_id TEXT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE, center TEXT NOT NULL, status TEXT NOT NULL, outcome TEXT, enrolled_at TEXT, at TEXT NOT NULL, UNIQUE(patient_id,study_id));
CREATE TABLE IF NOT EXISTS pending_items(id TEXT PRIMARY KEY, referral_id TEXT NOT NULL REFERENCES referrals(id) ON DELETE CASCADE, content_cipher TEXT NOT NULL, resolved_at TEXT, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, referral_id TEXT NOT NULL REFERENCES referrals(id) ON DELETE CASCADE, kind TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_runs(id TEXT PRIMARY KEY, state TEXT NOT NULL, processed INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL, finished_at TEXT);
CREATE INDEX IF NOT EXISTS study_visible ON studies(archived,enabled,registry_status,verified_at);
CREATE INDEX IF NOT EXISTS referrals_patient ON referrals(patient_id);
-- Identity is stored in a separate vault.sqlite, never joined by catalog/match APIs.
-- All SQL parameters are bound. Clinical data, snapshots and notes are AES-256-GCM encrypted.
