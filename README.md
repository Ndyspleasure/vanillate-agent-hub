# Vanillate Agent Hub

A project context and intelligence index for Vanillate Studio. Register a component, link it to its repository and specification, record a version change, and retrieve the evidence through HTTP or MCP. A local Ollama worker can propose a derived summary. The Founder reviews it before it appears in agent context.

## Run locally

Use Python 3.12 on Linux or macOS. Run the following from the repository root. Keep the database on a local disk.

```sh
umask 077
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m hub.admin init
python -m uvicorn hub.api:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal in the same checkout, activate the virtual environment. The following registers a sample component and reads it back. Issuing a credential again rotates it immediately.

```sh
. .venv/bin/activate
export HUB_URL=http://127.0.0.1:8000 HUB_PROJECT=demo
export HUB_TOKEN="$(python -m hub.admin issue studio founder '*')"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" --json '{"id":"demo","name":"Demo project"}' "$HUB_URL/projects"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" --json '{"id":"inventory","kind":"component","name":"Inventory","locator":"src/inventory","summary":"Item storage","source":"docs/inventory.md"}' "$HUB_URL/projects/demo/resources"
curl -fsS -H "Authorization: Bearer $HUB_TOKEN" "$HUB_URL/projects/demo/context?q=inventory"
```

For repository and specification links, events, worker setup and review, continue with [the walkthrough](docs/INTERFACES.md). Sample paths are illustrative. Register your own known sources for real projects.

## Verify

```sh
python -m unittest -v
pip install ruff==0.14.5
ruff check hub tests
ruff format --check hub tests
```

Tests use isolated temporary databases, including a real loopback HTTP service and an MCP client/server handshake over stdio. The worker test supplies deterministic Ollama HTTP responses. No model download or provider account is required.

## Project references

- [Founder project brief](docs/PROJECT_BRIEF.md)
- [Architecture, flow and database model](docs/ARCHITECTURE.md)
- [Architecture decisions and alternatives](docs/adr/0001-initial-slice.md)
- [API, MCP, Claude hook and Ollama interfaces](docs/INTERFACES.md)
- [Security, deployment and recovery](docs/OPERATIONS.md)

## Atlas proyek

Open http://127.0.0.1:8000/dashboard/ after starting Uvicorn. The Indonesian dashboard opens with clearly marked example data. Choose **Hubungkan Hub**, enter a project-scoped Reader token, and select a project to see its actual resource graph. Founder tokens also have read access. Browser credentials live only in page memory.

Select a node to inspect its locator, source, authority label and relationships. Select a related resource to move the graph focus. **Daftar** provides access to all resources when the graph neighborhood exceeds seven nodes. The protected `GET /projects/{id}/map` endpoint reads nodes and directed edges in one transaction. The dashboard is read-only. The header links to the official Vanillate domain, https://vanillate.id.
