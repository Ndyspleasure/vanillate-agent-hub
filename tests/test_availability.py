import unittest
from unittest.mock import patch

import httpx

from hub.git_context import changes
from hub.mcp_server import get_project_context


class OfflineContextTest(unittest.TestCase):
    def test_folder_impact(self):
        report = changes(
            ["src/wallet/model.js", "test/new.js"],
            [("bot", "wallet", "src/wallet"), ("bot", "other", "src/wall")],
        )
        self.assertEqual(report["review_nodes"], ["bot/wallet"])
        self.assertEqual(report["changed_path_count"], 2)

    def test_auth_failure_and_outage(self):
        for status in [401, 403, 503]:
            with (
                self.subTest(status=status),
                patch.dict("os.environ", HUB_PROJECT="vanillate-bot"),
                patch(
                    "hub.mcp_server.hub_client",
                    return_value=httpx.Client(
                        base_url="http://localhost",
                        transport=httpx.MockTransport(lambda _: httpx.Response(status)),
                    ),
                ),
                patch(
                    "hub.mcp_server.check",
                    return_value={"context_source": "git_snapshot"},
                ) as fallback,
            ):
                if status == 503:
                    self.assertEqual(
                        get_project_context("wallet")["hub_status"], "unreachable"
                    )
                    fallback.assert_called_once_with("vanillate-bot", "wallet")
                else:
                    with self.assertRaises(httpx.HTTPStatusError):
                        get_project_context("wallet")
                    fallback.assert_not_called()
