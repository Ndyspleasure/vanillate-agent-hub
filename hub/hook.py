"""Opt-in PostToolUse emitter. Send only mapped file IDs and content hashes."""
import hashlib
import json
import os
import sys
from pathlib import Path

from .client import hub_client, project_path


def collect(payload, root, mapping):
    if payload.get("hook_event_name") != "PostToolUse" or payload.get("tool_name") not in ("Edit", "Write"):
        return None
    target = (Path(payload["cwd"]) / payload["tool_input"]["file_path"]).resolve()
    if not target.is_relative_to(root):
        return None
    resource = mapping.get(str(target.relative_to(root)))
    if not resource or not target.is_file() or target.stat().st_size > 4_000_000:
        return None
    with target.open("rb") as source:
        version = hashlib.file_digest(source, "sha256").hexdigest()
    identity = json.dumps([payload["session_id"], payload["tool_use_id"], resource, version])
    return {"resource": resource, "version": version, "kind": "file.changed",
            "external_id": hashlib.sha256(identity.encode()).hexdigest()}


def main():
    try:
        raw = sys.stdin.buffer.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError()
        event = collect(json.loads(raw), Path(os.environ["HUB_REPO_ROOT"]).resolve(),
                        json.loads(os.environ["HUB_FILE_MAP"]))
        if event:
            with hub_client() as client:
                client.post(project_path()+"/events", json=event).raise_for_status()
    except Exception as exc:
        print(f"Hub hook did not deliver ({type(exc).__name__})", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
