"""Read-only MCP stdio client adapter for the authenticated Hub API."""
from mcp.server.fastmcp import FastMCP

from .client import hub_client, project_path

server = FastMCP("Vanillate Agent Hub")


@server.tool()
def get_project_context(query: str) -> dict:
    """Find source-backed context in the configured project."""
    with hub_client() as client:
        return client.get(project_path() + "/context", params={"q": query}).raise_for_status().json()


@server.tool()
def list_projects() -> list[dict]:
    """List projects visible to the configured identity."""
    with hub_client() as client:
        return client.get("/projects").raise_for_status().json()


if __name__ == "__main__":
    server.run(transport="stdio")
