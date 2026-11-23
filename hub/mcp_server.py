"""Read-only MCP stdio client adapter for the authenticated Hub API."""

import logging
import os

import httpx

from mcp.server.fastmcp import FastMCP

from .git_context import check
from .client import hub_client, project_path

logging.getLogger("httpx").setLevel(logging.WARNING)
server = FastMCP("Vanillate Agent Hub")


@server.tool()
def get_project_context(query: str) -> dict:
    """Find source-backed context in the configured project."""
    if not 1 <= len(query) <= 100:
        raise ValueError("Query must contain 1–100 characters")
    try:
        with hub_client() as client:
            return (
                client.get(project_path() + "/context", params={"q": query})
                .raise_for_status()
                .json()
            )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in (502, 503, 504):
            raise
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Git uses only the client machine's independent repository credentials.
    report = check(os.environ["HUB_PROJECT"], query)
    return {"hub_status": "unreachable", **report}


@server.tool()
def list_projects() -> list[dict]:
    """List projects visible to the configured identity."""
    with hub_client() as client:
        return client.get("/projects").raise_for_status().json()


if __name__ == "__main__":
    server.run(transport="stdio")
