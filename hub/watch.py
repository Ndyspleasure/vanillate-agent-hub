"""Observe main tips for registered repositories listed in the curated Atlas."""

import asyncio
import json
import logging
import os
import re
import secrets
import subprocess

from .seed import CATALOG
from .store import audit, database, digest, now


def targets():
    result = {}
    with database() as db:
        for project in json.loads(CATALOG.read_text()):
            for node in project["nodes"]:
                url = node["locator"]
                if node["kind"] != "repository" or not re.fullmatch(
                    r"https://github.com/Ndyspleasure/[A-Za-z0-9_.-]+", url
                ):
                    continue
                key = (project["id"], node["id"])
                row = db.execute(
                    "SELECT source FROM resources WHERE project=? AND id=? AND locator=?",
                    (*key, url),
                ).fetchone()
                if row and row["source"] == node["source"]:
                    sha = re.search(r"/(?:blob|tree)/([0-9a-f]{40})/", row["source"])
                    if sha:
                        result.setdefault(url, []).append((*key, sha[1]))
    return result


def observe(project, resource, baseline, head):
    actor = "git-monitor." + project
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        last = db.execute(
            "SELECT id,version FROM events WHERE project=? AND resource=? AND actor=? ORDER BY id DESC LIMIT 1",
            (project, resource, actor),
        ).fetchone()
        if head == (last["version"] if last else baseline):
            return
        db.execute(
            "INSERT OR IGNORE INTO identities VALUES(?,?,'emitter',?)",
            (actor, digest(secrets.token_urlsafe(40)), project),
        )
        event = db.execute(
            """INSERT INTO events(project,resource,actor,external_id,kind,version,observed)
                              VALUES(?,?,?,?,'commit.changed',?,?)""",
            (
                project,
                resource,
                actor,
                f"{resource}-{last['id'] if last else 0}-{head}",
                head,
                now(),
            ),
        ).lastrowid
        db.execute("INSERT INTO jobs(event) VALUES(?)", (event,))
        audit(db, project, actor, "event.queue", event)


def scan():
    for url, registrations in targets().items():
        try:
            output = subprocess.run(
                ["git", "ls-remote", "--exit-code", url, "refs/heads/main"],
                capture_output=True,
                timeout=10,
                check=True,
                text=True,
                env=os.environ
                | {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"},
            )
            head, ref = output.stdout.strip().split()
            if ref != "refs/heads/main" or not re.fullmatch("[0-9a-f]{40}", head):
                raise ValueError("Unexpected Git ref")
            for registration in registrations:
                observe(*registration, head)
        except (ValueError, OSError, subprocess.SubprocessError):
            logging.getLogger(__name__).warning("Git ref unavailable for %s", url)


async def monitor():
    while True:
        try:
            await asyncio.to_thread(scan)
        except Exception:
            logging.getLogger(__name__).exception("Git monitor cycle failed")
        await asyncio.sleep(60)
