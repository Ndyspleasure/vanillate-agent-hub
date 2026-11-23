CREATE TABLE browser_sessions (
 digest TEXT PRIMARY KEY, identity TEXT NOT NULL REFERENCES identities(id),
 credential_digest TEXT NOT NULL, expires INTEGER NOT NULL
);
CREATE INDEX audit_by_project ON audit(project,id);
PRAGMA user_version=3;
