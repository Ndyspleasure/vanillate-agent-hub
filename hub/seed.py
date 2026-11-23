"""Import the versioned Vanillate atlas into a local Hub using a Founder identity."""

import json
import os
from pathlib import Path

from .models import Link, Project, Resource
from .store import audit, database, digest, now

CATALOG = Path(__file__).with_name("catalog") / "vanillate.json"


def ensure(db, table, key, fields, observed=None):
    # Callers supply fixed schema identifiers. All catalog values use placeholders.
    record = key | fields
    where = " AND ".join(f"{column}=?" for column in key)
    existing = db.execute(
        f"SELECT * FROM {table} WHERE {where}", tuple(key.values())
    ).fetchone()
    if existing:
        if any(existing[k] != v for k, v in fields.items()):
            raise ValueError(
                f"Existing {table} entry conflicts with catalog: {tuple(key.values())}"
            )
        return False
    if observed is not None:
        record["observed"] = observed
    columns = ",".join(record)
    placeholders = ",".join("?" for _ in record)
    db.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        tuple(record.values()),
    )
    return True


def import_catalog(token):
    catalog = json.loads(CATALOG.read_text())
    added = 0
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        actor = db.execute(
            "SELECT id FROM identities WHERE role='founder' AND scope='*' AND digest=?",
            (digest(token),),
        ).fetchone()
        if not actor:
            raise PermissionError(
                "A global Founder credential is required for this multi-project import"
            )
        for item in catalog:
            project = Project(id=item["id"], name=item["name"])
            count = int(
                ensure(db, "projects", {"id": project.id}, {"name": project.name})
            )
            for row in item["nodes"]:
                res = Resource.model_validate(row)
                count += ensure(
                    db,
                    "resources",
                    {"project": project.id, "id": res.id},
                    res.model_dump(exclude={"id"}),
                    now(),
                )
            for row in item["links"]:
                link = Link.model_validate(row)
                count += ensure(
                    db,
                    "links",
                    {"project": project.id, **link.model_dump(exclude={"evidence"})},
                    {"evidence": link.evidence},
                    now(),
                )
            if count:
                audit(db, project.id, actor["id"], "catalog.import", CATALOG.name)
            added += count
    return added


if __name__ == "__main__":
    print(f"Imported {import_catalog(os.environ['HUB_TOKEN'])} new records")
