CREATE TABLE identities (
 id TEXT PRIMARY KEY, digest TEXT NOT NULL UNIQUE, role TEXT NOT NULL
 CHECK(role IN ('founder','reader','emitter','indexer')), scope TEXT NOT NULL
);
CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE resources (
 project TEXT REFERENCES projects, id TEXT, kind TEXT NOT NULL, name TEXT NOT NULL,
 locator TEXT NOT NULL, summary TEXT NOT NULL, authority TEXT NOT NULL,
 source TEXT NOT NULL, observed INTEGER NOT NULL, PRIMARY KEY(project,id)
);
CREATE TABLE links (
 project TEXT, origin TEXT, target TEXT, kind TEXT, evidence TEXT NOT NULL, observed INTEGER NOT NULL,
 PRIMARY KEY(project,origin,target,kind),
 FOREIGN KEY(project,origin) REFERENCES resources(project,id),
 FOREIGN KEY(project,target) REFERENCES resources(project,id)
);
CREATE TABLE events (
 id INTEGER PRIMARY KEY, project TEXT, resource TEXT, actor TEXT REFERENCES identities,
 external_id TEXT NOT NULL, kind TEXT NOT NULL, version TEXT NOT NULL, observed INTEGER NOT NULL,
 UNIQUE(project,actor,external_id), FOREIGN KEY(project,resource) REFERENCES resources(project,id)
);
CREATE TABLE jobs (
 event INTEGER PRIMARY KEY REFERENCES events, status TEXT NOT NULL DEFAULT 'queued',
 attempts INTEGER NOT NULL DEFAULT 0, owner TEXT, lease TEXT, expires INTEGER
);
CREATE INDEX jobs_ready ON jobs(status,expires);
CREATE INDEX events_resource ON events(project,resource,id);
CREATE TABLE proposals (
 event INTEGER PRIMARY KEY REFERENCES events, summary TEXT NOT NULL, model TEXT NOT NULL,
 author TEXT REFERENCES identities, created INTEGER NOT NULL, decision TEXT, reviewer TEXT REFERENCES identities,
 reviewed INTEGER
);
CREATE TABLE audit (
 id INTEGER PRIMARY KEY, project TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
 reference TEXT NOT NULL, at INTEGER NOT NULL
);
PRAGMA user_version=1;
