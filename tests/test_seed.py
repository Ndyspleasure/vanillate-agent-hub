import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hub.dashboard import snapshot
from hub.seed import import_catalog
from hub.store import database, initialize, issue


class AtlasImportTest(unittest.TestCase):
    def test_import_authority_replay_and_conflict(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, HUB_DB=str(Path(tmp) / "hub.db")),
        ):
            initialize()
            with self.assertRaises(PermissionError):
                import_catalog(issue("reader", "reader", "vanillate-web"))
            token = issue("studio", "founder", "*")
            self.assertGreater(import_catalog(token), 0)
            self.assertEqual(import_catalog(token), 0)
            for key in ("vanillate-bot", "vanillate-web", "vanillate-ecosystem"):
                data = snapshot(key)
                ids = {n["id"] for n in data["nodes"]}
                for edge in data["links"]:
                    self.assertTrue(
                        {edge["origin"], edge["target"], edge["evidence"]} <= ids
                    )
            with database() as db:
                db.execute("DELETE FROM links WHERE project='vanillate-ecosystem'")
                db.execute(
                    "UPDATE projects SET name='Founder edit' WHERE id='vanillate-web'"
                )
            with self.assertRaises(ValueError):
                import_catalog(token)
            self.assertEqual(snapshot("vanillate-ecosystem")["links"], [])
            self.assertEqual(snapshot("vanillate-web")["name"], "Founder edit")
