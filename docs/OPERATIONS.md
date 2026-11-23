# Security and operations

## Identities

Control of the Hub host and database grants administrative authority. The Founder or a trusted operator provisions one random credential for each identity with `python -m hub.admin issue ID ROLE SCOPE`. Issuing again with the same arguments rotates it. Revoke with `python -m hub.admin revoke ID`. Old events retain the principal ID. Tokens are displayed once by the CLI and only SHA-256 digests of random tokens are stored. Use private terminal sessions, a private file mode and separate environment files for each client.

Founders register source records and decide on proposals. Readers retrieve project data. Emitters only submit events. Indexers only claim jobs and propose summaries for owned, unexpired leases. All non-Founder identities are provisioned per project. Use separate data directories, identities and configuration for development and production. Never give a worker the Hub DB file, a Founder token or provider credentials.

Only register metadata suitable for every authorized reader of that project. Inputs use allowlisted fields, locator restrictions, field limits and checks for common secret patterns. These checks cannot identify arbitrary secrets embedded in prose. The hook omits file contents; registered summaries and locators may reach the local model. Screen those fields before registration. Treat all evidence and generated text as untrusted, including accepted summaries. The worker has no tool execution interface. Apply least privilege to its OS account as well.

## Deployment responsibilities

Use one Uvicorn service bound to loopback on the personal computer and a separate worker process with its own identity. Set HUB_DB to an absolute path on persistent local disk. Keep the current database path when upgrading; selecting a new path initializes an empty database. To relocate it, stop writers, create a consistent backup, restore and verify the copy before switching configuration. Use a dedicated OS account, private file permissions and full-disk encryption. Keep database files, WAL/SHM and backup destinations outside deployment inputs.

Monitor disk space, queue depth, oldest queued event, expired leases, exhausted jobs and the last successful backup. Supervise services locally and start the backend before the worker. Log status and correlation IDs; redact payloads and credentials. Apply migrations once during a maintenance window. Configure concurrency, limits and timeouts at the backend and approved bridge. The [Founder decision](adr/0002-vercel-personal-computer.md) defines the Vercel deployment boundary and tests before domain cutover.

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

## Automatic backup policy (proposed, pending installation)

Schedule the SQLite online backup operation daily on the PC with catch-up on the next boot or wake after a missed run. Use Task Scheduler on Windows or a persistent systemd timer on Linux. Run a single backup at a time under a restricted account. The manual command above demonstrates one snapshot. For scheduled runs, create a unique temporary file, perform integrity and foreign-key checks, then atomically rename the verified file within the backup destination. Record success only after verification. On failure retain prior good copies, report the error and retry with a bounded delay.

Proposed starting retention is seven daily and four weekly verified copies. Copy encrypted backups to a Founder-approved separate device or destination, with recovery keys held separately. Local-only snapshots do not cover loss of the PC or its disk. Record the last verified off-device backup and alert on a missed daily recovery point. An outage longer than the schedule extends the potential loss window. Run an isolated restore drill monthly, after schema changes and before switching machines. Compare restored audit/event IDs, queue counts and history, reconcile post-snapshot events from retained sender records, and measure actual recovery time. Retain replayable events for at least the agreed restore window where feasible. Founder approval is needed for the retention targets and external destination.
