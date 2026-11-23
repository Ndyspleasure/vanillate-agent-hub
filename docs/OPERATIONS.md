# Security and operations

## Identities

Control of the Hub host and database grants administrative authority. The Founder or a trusted operator provisions one random credential for each identity with `python -m hub.admin issue ID ROLE SCOPE`. Issuing again with the same arguments rotates it. Revoke with `python -m hub.admin revoke ID`. Old events retain the principal ID. Tokens are displayed once by the CLI and only SHA-256 digests of random tokens are stored. Use private terminal sessions, a private file mode and separate environment files for each client.

Founders register source records and decide on proposals. Readers retrieve project data. Emitters only submit events. Indexers only claim jobs and propose summaries for owned, unexpired leases. All non-Founder identities are provisioned per project. Use separate data directories, identities and configuration for development and production. Never give a worker the Hub DB file, a Founder token or provider credentials.

Only register metadata suitable for every authorized reader of that project. Inputs use allowlisted fields, locator restrictions, field limits and checks for common secret patterns. These checks cannot identify arbitrary secrets embedded in prose. The hook omits file contents; registered summaries and locators may reach the local model. Screen those fields before registration. Treat all evidence and generated text as untrusted, including accepted summaries. The worker has no tool execution interface. Apply least privilege to its OS account as well.

## Single-host deployment

The local server works after the README steps. For a Founder-approved VPS deployment use a dedicated OS account, private local data directory and one Uvicorn process. Set HUB_DB to an absolute path on a persistent local volume. Apply schema initialization/migrations during a maintenance window before starting the service. Supervise the process with the host service manager, start it from the trusted checkout and bind it to loopback.

Terminate TLS in a reverse proxy with a valid certificate. Configure body/header timeouts (for example 15 seconds), an 8 KiB body limit, IP-level abuse limits and a private ingress policy. Disable logging of request bodies, query strings and Authorization headers at each layer. Start Uvicorn with `--no-access-log --timeout-keep-alive 5 --limit-concurrency 64`. Use the database-backed audit and job APIs to check operations. Monitor disk space, 5xx responses and exhausted jobs. An expired lease may still read as leased until another worker polls. No production endpoint, provider integration or domain has been provisioned.

## Backup and restore

Use SQLite's online backup API to capture committed WAL contents. Protect the backup as sensitive data. The following creates a new snapshot at an unused path.

```sh
umask 077
python - <<'PY'
import os, sqlite3
from pathlib import Path
src = Path(os.getenv("HUB_DB", "state/hub.sqlite3")).resolve()
dst = Path("state/hub-backup.sqlite3")
dst.touch(mode=0o600, exist_ok=False)
with sqlite3.connect(src.as_uri() + "?mode=ro", uri=True) as live, sqlite3.connect(dst) as copy:
    live.backup(copy)
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not copy.execute("PRAGMA foreign_key_check").fetchall()
PY
```

For a restore drill, stop writers and copy the snapshot into a **fresh private directory**. Set HUB_DB to that new copy, run `python -m hub.admin init` and start the API on an isolated port. Check a known context, job and audit record before switching traffic. Rotate credentials after recovery because a snapshot can restore older credential digests. Preserve the old database with its WAL and SHM files until recovery is verified.

Schema versions are recorded with PRAGMA user_version. Unknown versions fail startup. The current schema retains events, proposals and audit history indefinitely. Agree retention and backup schedules with the Founder before long-running deployment.
