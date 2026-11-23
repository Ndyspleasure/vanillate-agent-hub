import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from hub.store import initialize, issue


class MCPTest(unittest.TestCase):
    def test_stdio_to_live_api(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, HUB_DB=str(Path(tmp) / "hub.db")),
        ):
            initialize()
            founder = issue("owner", "founder", "*")
            reader = issue("client", "reader", "demo")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
                proc = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "hub.api:app",
                        "--fd",
                        str(sock.fileno()),
                        "--log-level",
                        "warning",
                    ],
                    pass_fds=(sock.fileno(),),
                )
                try:
                    url = f"http://127.0.0.1:{port}"
                    with httpx.Client(
                        base_url=url, headers={"authorization": "Bearer " + founder}
                    ) as http:
                        for _ in range(100):
                            try:
                                http.get("/projects").raise_for_status()
                                break
                            except httpx.ConnectError:
                                time.sleep(0.05)
                        http.post(
                            "/projects", json={"id": "demo", "name": "Demo"}
                        ).raise_for_status()
                        http.post(
                            "/projects/demo/resources",
                            json={
                                "id": "inventory",
                                "kind": "component",
                                "name": "Inventory",
                                "locator": "src/items",
                                "summary": "Item storage",
                                "source": "docs/inventory.md",
                            },
                        ).raise_for_status()
                    asyncio.run(self.check_stdio(url, reader))
                finally:
                    proc.terminate()
                    proc.wait(timeout=10)

    async def check_stdio(self, url, reader):
        config = StdioServerParameters(
            command=sys.executable,
            args=["-m", "hub.mcp_server"],
            env={"HUB_URL": url, "HUB_TOKEN": reader, "HUB_PROJECT": "demo"},
        )
        async with stdio_client(config) as (rx, tx), ClientSession(rx, tx) as session:
            await session.initialize()
            tools = await session.list_tools()
            self.assertEqual(
                {t.name for t in tools.tools}, {"get_project_context", "list_projects"}
            )
            start = time.perf_counter()
            result = await session.call_tool(
                "get_project_context", {"query": "inventory"}
            )
            elapsed = (time.perf_counter() - start) * 1000
            self.assertFalse(result.isError)
            body = result.content[0].text
            resources = json.loads(body)["resources"]
            self.assertEqual(resources[0]["source"], "docs/inventory.md")
            print(
                f"MCP sample: {len(body.encode())} bytes, {len(resources)} resource, {elapsed:.1f} ms"
            )
