"""Single-instance Hub API. One transaction owns each domain mutation and its audit."""
import secrets
import sqlite3
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .models import Event, Id, Link, Project, Resource, Result, Review
from .store import audit, database, digest, initialize, now


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
windows = {}


@app.middleware("http")
async def guard(request: Request, call_next):
    auth = request.headers.get("authorization", "")
    with database() as db:
        identity = db.execute("SELECT id,role,scope FROM identities WHERE digest=?",
                              (digest(auth[7:]),)).fetchone() if auth.startswith("Bearer ") else None
    if not identity:
        return JSONResponse({"detail": "Authentication required"}, 401)
    request.state.actor = dict(identity)
    t = time.monotonic()
    window = windows.setdefault(identity["id"], deque())
    while window and window[0] < t - 60:
        window.popleft()
    if len(window) >= 120:
        return JSONResponse({"detail": "Rate limit"}, 429, headers={"Retry-After": "60"})
    window.append(t)
    if request.method == "POST":
        size = request.headers.get("content-length", "")
        if not size.isdecimal() or len(size) > 5 or int(size) > 8192 or "transfer-encoding" in request.headers:
            return JSONResponse({"detail": "Fixed body size up to 8192 bytes required"}, 413)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def invalid(request, exc):
    return JSONResponse({"detail": "Invalid request fields"}, 422)


@app.exception_handler(sqlite3.IntegrityError)
async def integrity(request, exc):
    return JSONResponse({"detail": "Duplicate or missing reference"}, 409)


def access(*roles):
    def check(request: Request):
        actor = request.state.actor
        project = request.path_params.get("p")
        if actor["role"] not in roles or project and actor["scope"] not in ("*", project):
            raise HTTPException(403)
        return actor["id"]
    return Depends(check)


founder = access("founder")
read = access("founder", "reader")
worker = access("indexer")


def rows(db, sql, args):
    return [dict(r) for r in db.execute(sql, args)]


@app.post("/projects", status_code=201)
def project(data: Project, request: Request, actor=founder):
    if request.state.actor["scope"] not in ("*", data.id):
        raise HTTPException(403)
    with database() as db:
        db.execute("INSERT INTO projects VALUES(?,?)", (data.id, data.name))
        audit(db, data.id, actor, "project.register", data.id)
    return data


@app.get("/projects")
def projects(request: Request, actor=read):
    scope = request.state.actor["scope"]
    with database() as db:
        return rows(db, "SELECT * FROM projects WHERE ?='*' OR id=? ORDER BY id", (scope, scope))


@app.post("/projects/{p}/resources", status_code=201)
def resource(p: Id, data: Resource, actor=founder):
    with database() as db:
        db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?)",
                   (p, data.id, data.kind, data.name, data.locator, data.summary,
                    data.authority, data.source, now()))
        audit(db, p, actor, "resource.register", data.id)
    return {"id": data.id}


@app.post("/projects/{p}/links", status_code=201)
def link(p: Id, data: Link, actor=founder):
    with database() as db:
        db.execute("INSERT INTO links VALUES(?,?,?,?,?,?)",
                   (p, data.origin, data.target, data.kind, data.evidence, now()))
        audit(db, p, actor, "link.register", f"{data.origin}/{data.kind}/{data.target}")
    return data


@app.post("/projects/{p}/events")
def ingest(p: Id, data: Event, actor=access("emitter", "founder")):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        prior = db.execute("SELECT * FROM events WHERE project=? AND actor=? AND external_id=?",
                           (p, actor, data.external_id)).fetchone()
        if prior:
            if any(prior[k] != v for k, v in data.model_dump().items()):
                raise HTTPException(409, "Event key reused with different evidence")
            return {"event": prior["id"]}
        event = db.execute("""INSERT INTO events(project,resource,actor,external_id,kind,version,observed)
                              VALUES(?,?,?,?,?,?,?)""",
                           (p, data.resource, actor, data.external_id, data.kind, data.version, now())).lastrowid
        db.execute("INSERT INTO jobs(event) VALUES(?)", (event,))
        audit(db, p, actor, "event.queue", event)
    return {"event": event}


@app.post("/projects/{p}/claim")
def claim(p: Id, actor=worker):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        expired = rows(db, """SELECT event FROM jobs JOIN events ON id=event WHERE project=?
                          AND status='leased' AND expires<=? AND attempts>=3""", (p, now()))
        for item in expired:
            db.execute("UPDATE jobs SET status='failed',lease=NULL WHERE event=?", (item["event"],))
            audit(db, p, actor, "job.exhausted", item["event"])
        job = db.execute("""SELECT e.id AS event,e.kind,e.version,e.resource,e.observed,r.locator,r.summary
                         FROM jobs j JOIN events e ON e.id=j.event
                         JOIN resources r ON r.project=e.project AND r.id=e.resource
                         WHERE e.project=? AND (status='queued' OR (status='leased' AND expires<=?))
                         ORDER BY e.id LIMIT 1""", (p, now())).fetchone()
        if not job:
            return None
        lease = secrets.token_hex(24)
        db.execute("""UPDATE jobs SET status='leased', owner=?,lease=?,expires=?,attempts=attempts+1
                      WHERE event=?""", (actor, lease, now()+180, job["event"]))
        audit(db, p, actor, "job.claim", job["event"])
    return {**dict(job), "lease": lease}


@app.post("/projects/{p}/jobs/{event}/proposal", status_code=201)
def propose(p: Id, event: int, data: Result, actor=worker):
    with database() as db:
        changed = db.execute("""UPDATE jobs SET status='proposed',lease=NULL WHERE event=?
                              AND event IN (SELECT id FROM events WHERE project=?) AND status='leased'
                              AND lease=? AND owner=? AND expires>?""",
                             (event, p, data.lease, actor, now())).rowcount
        if not changed:
            raise HTTPException(409, "Lease unavailable")
        db.execute("INSERT INTO proposals(event,summary,model,author,created) VALUES(?,?,?,?,?)",
                   (event, data.summary, data.model, actor, now()))
        audit(db, p, actor, "proposal.submit", event)
    return {"event": event}


@app.get("/projects/{p}/jobs")
def jobs(p: Id, actor=read):
    with database() as db:
        return rows(db, """SELECT e.*,j.status,j.attempts,j.expires,j.owner,s.summary,s.model,s.decision
                    FROM events e JOIN jobs j ON j.event=e.id LEFT JOIN proposals s ON s.event=e.id
                    WHERE project=? ORDER BY e.id DESC LIMIT 100""", (p,))


@app.post("/projects/{p}/jobs/{event}/review")
def review(p: Id, event: int, data: Review, actor=founder):
    with database() as db:
        changed = db.execute("""UPDATE proposals SET decision=?,reviewer=?,reviewed=?
                             WHERE event=? AND event IN (SELECT id FROM events WHERE project=?)
                             AND decision IS NULL""", (data.decision, actor, now(), event, p)).rowcount
        if not changed:
            raise HTTPException(409, "No pending proposal")
        db.execute("UPDATE jobs SET status=? WHERE event=?", (data.decision, event))
        audit(db, p, actor, "proposal."+data.decision, event)
    return data


@app.get("/projects/{p}/audit")
def history(p: Id, actor=founder):
    with database() as db:
        return rows(db, "SELECT * FROM audit WHERE project=? ORDER BY id DESC LIMIT 100", (p,))


@app.get("/projects/{p}/context")
def context(p: Id, q: str = Query(min_length=1, max_length=100), actor=read):
    with database() as db:
        db.execute("BEGIN")
        if not db.execute("SELECT 1 FROM projects WHERE id=?", (p,)).fetchone():
            raise HTTPException(404)
        facts = rows(db, """SELECT * FROM resources WHERE project=? AND
                     instr(lower(id||' '||name||' '||summary||' '||locator),lower(?))>0
                     ORDER BY (lower(id)=lower(?)) DESC,id LIMIT 5""", (p, q, q))
        for fact in facts:
            key = (p, fact["id"])
            fact["changes"] = rows(db, """SELECT id,kind,version,observed,actor FROM events
                                    WHERE project=? AND resource=? ORDER BY id DESC LIMIT 2""", key)
            fact["freshness"] = "needs_review" if fact["changes"] else "as_registered"
            fact["validation"] = "observed"
            fact["links"] = rows(db, """SELECT l.kind,l.origin,l.target,r.locator AS related_locator,
                                 s.locator AS evidence,l.observed FROM links l JOIN resources s
                                 ON s.project=l.project AND s.id=l.evidence JOIN resources r
                                 ON r.project=l.project AND r.id=CASE WHEN l.origin=? THEN l.target ELSE l.origin END
                                 WHERE l.project=? AND (l.origin=? OR l.target=?)
                                 ORDER BY l.origin,l.target,l.kind LIMIT 5""", (key[1], *key, key[1]))
            fact["inferences"] = rows(db, """SELECT event,summary,model,author,created,reviewer,reviewed,
                                       version,'inferred' AS validation,'OLLAMA_OBSERVATION' AS authority
                                       FROM proposals JOIN events ON events.id=event WHERE project=? AND resource=?
                                       AND decision='accepted' ORDER BY event DESC LIMIT 2""", key)
    return {"project": p, "resources": facts}
