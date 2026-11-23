# Interfaces and walkthrough

## HTTP API

Send an `Authorization: Bearer` header on every request. JSON writes use a fixed Content-Length, at most 8192 bytes. IDs are 1–80 characters from ASCII letters, digits, dot, underscore and dash, starting with a letter or digit. Source locators are paths or HTTPS references without credentials, query or fragment. Times are UTC Unix seconds. The project prefix below is `/projects/{project_id}`.

| Method and path | Role | Body or result |
|---|---|---|
| GET /projects | reader, founder | Visible projects |
| POST /projects | founder | id, name |
| POST prefix/resources | founder | id, kind, name, locator, summary, source; optional authority, environment, provider |
| POST prefix/links | founder | origin, target, kind, evidence (registered resource ID) |
| POST prefix/events | emitter, founder | external_id, resource, kind, version (40 or 64 lowercase hexadecimal characters). Returns internal event ID. |
| POST prefix/claim | indexer | Empty request. Returns leased metadata or null. |
| POST prefix/jobs/{event}/proposal | indexer | lease, model, summary (1–600 characters). Must own the current lease. |
| GET prefix/jobs | reader, founder | Last 100 events with status, worker, attempts, expiry and proposal details |
| POST prefix/jobs/{event}/review | founder | decision equal to accepted or rejected, once only |
| POST prefix/jobs/{event}/retry | founder | Empty request. Requeue an exhausted job. |
| GET prefix/context?q=term | reader, founder | Relevant source locations, linked resources, observed changes, freshness, accepted inferences |
| GET prefix/audit | founder | Last 100 project audit records |

Supported event kinds are `file.changed`, `document.changed`, and `commit.changed`. Registered resources are append-only in this version. Repeated event delivery with the same identity/key and identical content returns the original event ID. Conflicting reuse returns 409. Missing credentials return 401, permission failures 403, invalid fields 422, excessive body sizes 413 and rate limits 429. A valid credential is limited to 120 requests per rolling minute per process.

## Map, change and review

Continue in the second terminal from the README with the Founder token. This example maps the real brief in your checkout and uses its current Git blob ID as the source version.

```sh
base="$HUB_URL/projects/$HUB_PROJECT"
post() { curl -fsS -H "Authorization: Bearer $HUB_TOKEN" --json "$2" "$base/$1"; }
post resources '{"id":"hub-repo","kind":"repository","provider":"github","name":"Hub repository","locator":"https://github.com/Ndyspleasure/vanillate-agent-hub","source":"docs/PROJECT_BRIEF.md","summary":"Dedicated repository for Agent Hub."}'
post resources '{"id":"brief","kind":"document","name":"Project brief","locator":"docs/PROJECT_BRIEF.md","summary":"Founder authority and delivery requirements.","source":"docs/PROJECT_BRIEF.md","authority":"APPROVED_SPECIFICATION"}'
post links '{"origin":"hub-repo","target":"brief","kind":"documented_by","evidence":"brief"}'
version=$(git hash-object docs/PROJECT_BRIEF.md)
post events "{\"external_id\":\"brief-$version\",\"resource\":\"brief\",\"kind\":\"document.changed\",\"version\":\"$version\"}"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" "$base/jobs"
```

The event is a manual demonstration. Its returned numeric ID identifies the job. Start the worker below in another terminal. After the job becomes `proposed`, read its summary and review the cited source. In the Founder terminal, replace 1 with the actual ID.

```sh
post jobs/1/review '{"decision":"accepted"}'
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" "$base/context?q=brief"
```

## Local Ollama

Install Ollama on the personal computer. Select an installed text model that supports JSON, and confirm its exact tagged name with `ollama list`. The worker checks `GET /api/tags` before claiming and posts to `/api/generate` on loopback. For a same-machine development run, use another terminal from the same checkout.

```sh
. .venv/bin/activate
export HUB_URL=http://127.0.0.1:8000 HUB_PROJECT=demo
export HUB_TOKEN="$(python -m hub.admin issue local-worker indexer demo)"
export OLLAMA_MODEL='replace-with-installed-name:tag'
python -m hub.worker --once
# Omit --once for continuous serial polling.
```

For a VPS installation, issue the worker credential on the Hub host, deliver only that scoped token to the personal computer and set HUB_URL to the authenticated HTTPS service. Keep Ollama bound to loopback. Default Ollama URL is http://127.0.0.1:11434. Worker logs record error types only. When the model is absent or its tags endpoint is offline, the worker leaves queued events alone. A crash after claim releases the work on lease expiry (180 seconds). Subsequent polling updates exhausted jobs to failed. The Founder can inspect the attempts and explicitly requeue. Generation has a 90-second HTTP inactivity timeout.

Benchmark on the actual machine with one job at a time. Record model tag/digest, quantization, CPU/GPU, peak RAM, model load time, warm generation latency, unsupported claims in output and timeout rate. Repeat on representative metadata before selecting a default. The automated fixture does not establish local inference quality.

## Claude Code

The opt-in command hook consumes Claude Code's documented PostToolUse JSON on stdin. Install the Hub in a trusted checkout outside the observed repository. Use a launcher that changes into the trusted Hub directory and executes its venv Python with `-m hub.hook`. Configure HUB_REPO_ROOT as the absolute observed repository path, HUB_FILE_MAP as a JSON object such as `{"docs/PROJECT_BRIEF.md":"brief"}`, HUB_PROJECT, HUB_URL and a project-scoped emitter token. Supply the token through the local environment. Avoid committing it in settings.

```json
{"hooks":{"PostToolUse":[{"matcher":"Edit|Write","hooks":[{"type":"command","command":"/absolute/path/to/trusted-hub-hook-launcher","timeout":20}]}]}}
```

The hook hashes mapped regular files up to 4 MB and sends IDs and hash only. Git renames, deletions, shell edits and disconnected delivery before Hub receipt require explicit events or replay. A delivery failure exits nonzero. Retry using the same event payload for idempotency. Hook payload parsing was tested with a fixture. Live Claude Code client behavior depends on its version and local configuration.

## MCP

Run `python -m hub.mcp_server` from the trusted Hub checkout with HUB_URL, HUB_PROJECT and a distinct reader token. Configure a stdio-capable client with a launcher that changes into that checkout and executes its absolute venv Python path. In Claude Code, register the launcher using `claude mcp add --transport stdio vanillate-hub -- /absolute/path/to/hub-mcp-launcher`. Keep credentials in the client environment. The client starts the subprocess; there is no public MCP port. The SDK negotiates the protocol. Tools are `list_projects()` and `get_project_context(query)`. Resource and prompt capabilities are outside this slice. HTTP context is also available to clients without MCP.
