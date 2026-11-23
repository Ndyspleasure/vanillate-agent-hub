ALTER TABLE resources ADD COLUMN provider TEXT;
ALTER TABLE resources ADD COLUMN environment TEXT;
PRAGMA user_version=2;
