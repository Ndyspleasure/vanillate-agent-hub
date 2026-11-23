"""Read-only project map and public dashboard shell."""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .store import database

WEB = Path(__file__).with_name("web")
ASSETS = {"/dashboard/style.css": "style.css", "/dashboard/app.js": "app.js"}


def shell():
    page = (
        (WEB / "index.html")
        .read_text()
        .replace('data-live="false"', 'data-live="true"')
    )
    return HTMLResponse(
        page,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
        },
    )


def asset(path):
    return FileResponse(WEB / ASSETS[path])


def snapshot(project):
    with database() as db:
        db.execute("BEGIN")
        name = db.execute("SELECT name FROM projects WHERE id=?", (project,)).fetchone()
        if not name:
            raise HTTPException(404)
        nodes = [
            dict(r)
            for r in db.execute(
                """SELECT r.id,r.name,r.kind,r.locator,r.source,r.summary,r.authority,r.observed,
               EXISTS(SELECT 1 FROM events e WHERE e.project=r.project AND e.resource=r.id) AS changed
               FROM resources r WHERE project=? ORDER BY r.id""",
                (project,),
            )
        ]
        links = [
            dict(r)
            for r in db.execute(
                "SELECT origin,target,kind,evidence FROM links WHERE project=? ORDER BY origin,target,kind",
                (project,),
            )
        ]
        events = [
            dict(r)
            for r in db.execute(
                "SELECT resource,kind,version,observed FROM events WHERE project=? ORDER BY id DESC LIMIT 5",
                (project,),
            )
        ]
    return {"events": events, "name": name["name"], "nodes": nodes, "links": links}
