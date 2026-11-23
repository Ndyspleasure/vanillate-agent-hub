import hashlib
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from hub.api import app, windows
from hub.hook import collect
from hub.store import database, initialize, issue
from hub.worker import cycle


class HubTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        env = patch.dict(os.environ, HUB_DB=str(self.root / "hub.db"))
        env.start()
        self.addCleanup(env.stop)
        initialize()
        windows.clear()
        self.clients = {}
        for role in ("founder", "reader", "emitter", "indexer"):
            token = issue(role, role, "*" if role == "founder" else "demo")
            client = TestClient(app, headers={"authorization": "Bearer " + token})
            self.clients[role] = client
            self.addCleanup(client.close)
        self.f = self.clients["founder"]
        self.w = self.clients["indexer"]
        self.r = self.clients["reader"]
        self.p = "/projects/demo"
        self.assertEqual(
            self.f.post("/projects", json={"id": "demo", "name": "Demo"}).status_code,
            201,
        )
        for name, kind, authority in [
            ("inventory", "component", "TECHNICAL_OBSERVATION"),
            ("spec", "document", "APPROVED_SPECIFICATION"),
            ("repo", "repository", "TECHNICAL_OBSERVATION"),
        ]:
            self.register(name, kind, authority)
        for origin, target, kind in [
            ("inventory", "repo", "implemented_in"),
            ("inventory", "spec", "documented_by"),
        ]:
            self.assertEqual(
                self.f.post(
                    self.p + "/links",
                    json={
                        "origin": origin,
                        "target": target,
                        "kind": kind,
                        "evidence": "spec",
                    },
                ).status_code,
                201,
            )

    def register(self, name, kind, authority):
        self.assertEqual(
            self.f.post(
                self.p + "/resources",
                json={
                    "id": name,
                    "name": name,
                    "kind": kind,
                    "authority": authority,
                    "locator": "docs/" + name,
                    "summary": name,
                    "source": "docs/spec",
                },
            ).status_code,
            201,
        )

    def event(self, **overrides):
        body = dict(
            resource="inventory",
            version="a" * 40,
            kind="file.changed",
            external_id="change-1",
        )
        return self.clients["emitter"].post(self.p + "/events", json=body | overrides)

    def test_dashboard_and_map_scope(self):
        with TestClient(app) as anonymous:
            self.assertEqual(anonymous.get("/").status_code, 200)
            self.assertIn('data-live="true"', anonymous.get("/dashboard/").text)
            self.assertEqual(anonymous.get("/dashboard/app.js").status_code, 200)
            self.assertEqual(anonymous.get(self.p + "/map").status_code, 401)
        self.assertEqual(self.r.get("/projects/other/map").status_code, 403)
        self.assertEqual(self.w.get(self.p + "/map").status_code, 403)
        result = self.r.get(self.p + "/map")
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.assertEqual(len(result.json()["nodes"]), 3)
        self.assertEqual(len(result.json()["links"]), 2)

    def test_remembered_reader_and_rotation(self):
        with TestClient(app, base_url="http://127.0.0.1") as browser:
            key = issue("browser", "founder", "demo")
            response = browser.post(
                "/session?remember=true", headers={"Authorization": "Bearer " + key}
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("HttpOnly", response.headers["set-cookie"])
            self.assertIn("Max-Age=2592000", response.headers["set-cookie"])
            self.assertEqual(browser.get(self.p + "/map").status_code, 200)
            self.assertEqual(browser.get("/projects/other/map").status_code, 403)
            self.assertEqual(
                browser.post(self.p + "/resources", json={}).status_code, 401
            )
            self.assertEqual(browser.get(self.p + "/audit").status_code, 403)
            issue("browser", "founder", "demo")
            self.assertEqual(browser.get(self.p + "/map").status_code, 401)

    def test_git_observation_replay_and_revert(self):
        from hub.watch import observe

        for head in ["a" * 40, "b" * 40, "b" * 40, "a" * 40]:
            observe("demo", "repo", "a" * 40, head)
        snapshot = self.r.get(self.p + "/map").json()
        self.assertEqual(
            [r["version"] for r in snapshot["events"]], ["a" * 40, "b" * 40]
        )
        self.assertEqual(len(self.r.get(self.p + "/jobs").json()), 2)

    def test_vertical_slice(self):
        event = self.event().json()["event"]
        initialize()
        self.assertEqual(self.r.get(self.p + "/jobs").json()[0]["status"], "queued")
        self.assertEqual(self.event().json()["event"], event)
        self.assertEqual(self.event(version="b" * 40).status_code, 409)

        def model(request):
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [{"name": "fixture:1"}]})
            body = json.loads(request.content)
            self.assertNotIn("lease", body["prompt"])
            self.assertEqual(json.loads(body["prompt"])["version"], "a" * 40)
            return httpx.Response(
                200,
                json={
                    "model": "fixture:1",
                    "response": '{"summary":"Impact unknown."}',
                },
            )

        with httpx.Client(
            base_url="http://localhost", transport=httpx.MockTransport(model)
        ) as client:
            self.assertTrue(cycle(self.w, client, self.p, "fixture:1"))

        def context():
            return self.r.get(self.p + "/context", params={"q": "inventory"}).json()[
                "resources"
            ][0]

        self.assertEqual(context()["inferences"], [])
        review = self.p + f"/jobs/{event}/review"
        self.assertEqual(
            self.w.post(review, json={"decision": "accepted"}).status_code, 403
        )
        self.assertEqual(
            self.f.post(review, json={"decision": "accepted"}).status_code, 200
        )
        self.assertEqual(
            self.f.post(review, json={"decision": "rejected"}).status_code, 409
        )
        facts = context()
        self.assertEqual(facts["freshness"], "needs_review")
        self.assertEqual(len(facts["links"]), 2)
        self.assertEqual(facts["changes"][0]["actor"], "emitter")
        self.assertEqual(facts["inferences"][0]["validation"], "inferred")
        self.assertEqual(facts["inferences"][0]["reviewer"], "founder")
        self.assertIn(
            "proposal.accepted",
            [a["action"] for a in self.f.get(self.p + "/audit").json()],
        )

    def test_permissions_and_input(self):
        self.assertEqual(TestClient(app).get("/projects").status_code, 401)
        self.assertEqual(self.r.get("/projects/other/context?q=x").status_code, 403)
        self.assertEqual(self.r.post(self.p + "/claim").status_code, 403)
        self.assertEqual(self.w.post(self.p + "/resources", json={}).status_code, 403)
        self.assertEqual(self.event(resource="unknown").status_code, 409)
        self.assertEqual(self.event(token="bad").status_code, 422)
        bad = {
            "id": "bad",
            "kind": "file",
            "name": "bad",
            "locator": "https://u:p@host/file",
            "source": "docs/spec",
            "summary": "metadata",
        }
        self.assertEqual(self.f.post(self.p + "/resources", json=bad).status_code, 422)
        self.assertEqual(
            self.f.post(self.p + "/events", content="x" * 9000).status_code, 413
        )
        issue("reader", "reader", "demo")
        self.assertEqual(self.r.get("/projects").status_code, 401)

    def test_lease_contention_expiry_and_retry(self):
        event = self.event(resource="spec").json()["event"]

        def claim(_):
            return self.w.post(self.p + "/claim").json()

        with ThreadPoolExecutor(2) as pool:
            claims = list(pool.map(claim, range(2)))
        self.assertEqual(sum(c is not None for c in claims), 1)
        original = next(c for c in claims if c)
        result = dict(lease=original["lease"], summary="Observation", model="test")
        url = self.p + f"/jobs/{event}/proposal"
        self.assertEqual(
            self.w.post(url, json=result | {"authority": "USER_DECISION"}).status_code,
            422,
        )
        for _ in range(3):
            with database() as db:
                db.execute("UPDATE jobs SET expires=0")
            claim(0)
        self.assertEqual(self.w.post(url, json=result).status_code, 409)
        self.assertEqual(self.r.get(self.p + "/jobs").json()[0]["status"], "failed")
        self.assertEqual(self.f.post(self.p + f"/jobs/{event}/retry").status_code, 200)
        self.assertIsNotNone(claim(0))
        self.assertEqual(
            self.r.get(self.p + "/context?q=spec").json()["resources"][0]["authority"],
            "APPROVED_SPECIFICATION",
        )

    def test_hook_only_mapped_hash(self):
        target = self.root / "doc.md"
        target.write_text("local contents")
        payload = dict(
            hook_event_name="PostToolUse",
            tool_name="Edit",
            session_id="s",
            tool_use_id="t",
            cwd=str(self.root),
            tool_input={"file_path": str(target)},
        )
        event = collect(payload, self.root, {"doc.md": "spec"})
        self.assertEqual(
            event["version"], hashlib.sha256(target.read_bytes()).hexdigest()
        )
        self.assertNotIn("local contents", json.dumps(event))
        self.assertIsNone(collect(payload, self.root, {}))
