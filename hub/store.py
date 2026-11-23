import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def now():
    return int(time.time())


@contextmanager
def database():
    path = Path(os.environ.get("HUB_DB", "state/hub.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    with database() as db:
        db.execute("PRAGMA journal_mode=WAL")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            schema = Path(__file__).with_name("schema.sql").read_text()
            db.executescript("BEGIN IMMEDIATE;\n" + schema + "\nCOMMIT;")
        if version in (0, 1):
            migration = (
                Path(__file__).parent / "migrations" / "002_resource_metadata.sql"
            )
            db.executescript("BEGIN IMMEDIATE;\n" + migration.read_text() + "\nCOMMIT;")
        if version in (0, 1, 2):
            migration = (
                Path(__file__).parent / "migrations" / "003_browser_sessions.sql"
            )
            db.executescript("BEGIN IMMEDIATE;\n" + migration.read_text() + "\nCOMMIT;")
        elif version != 3:
            raise RuntimeError("Unknown database version")


def audit(db, project, actor, action, reference):
    db.execute(
        "INSERT INTO audit(project,actor,action,reference,at) VALUES(?,?,?,?,?)",
        (project, actor, action, str(reference), now()),
    )


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue(identity, role, scope):
    token = secrets.token_urlsafe(40)
    with database() as db:
        existing = db.execute(
            "SELECT role,scope FROM identities WHERE id=?", (identity,)
        ).fetchone()
        if existing and tuple(existing) != (role, scope):
            raise ValueError("Use a new identity for a different role or scope")
        db.execute(
            """INSERT INTO identities VALUES(?,?,?,?) ON CONFLICT(id)
                      DO UPDATE SET digest=excluded.digest""",
            (identity, digest(token), role, scope),
        )
        audit(db, scope, "local-admin", "issue", identity)
    return token
