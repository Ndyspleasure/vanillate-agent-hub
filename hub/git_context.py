"""Read current main refs and compare them to the Atlas using the agent's own Git access."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

OWNER = "https://github.com/Ndyspleasure/"
ATLAS = OWNER + "vanillate-agent-hub"
PIN = re.compile(
    re.escape(OWNER) + r"([A-Za-z0-9][A-Za-z0-9_.-]*)/(?:blob|tree)/([0-9a-f]{40})/(.+)"
)


def git(directory, *args):
    return subprocess.run(
        ["git", *args],
        cwd=directory,
        capture_output=True,
        check=True,
        timeout=60,
        env=os.environ | {"GIT_TERMINAL_PROMPT": "0"},
    ).stdout


def fetch(directory, url, ref):
    git(
        directory,
        "fetch",
        "--quiet",
        "--no-tags",
        "--depth=1",
        "--filter=blob:none",
        url,
        ref,
    )
    return git(directory, "rev-parse", "FETCH_HEAD").decode().strip()


def changes(paths, tracked):
    impacted = {
        scope + "/" + node
        for path in paths
        for scope, node, location in tracked
        if path == location or path.startswith(location + "/")
    }
    return {
        "changed_path_count": len(paths),
        "paths_sample": paths[:30],
        "review_nodes": sorted(impacted),
    }


def inspect(root, repo, baseline, tracked):
    directory = root / repo
    directory.mkdir()
    git(directory, "init", "--bare", "--quiet")
    url = OWNER + repo + ".git"
    head = fetch(directory, url, "refs/heads/main")
    report = {
        "repository": repo,
        "branch": "main",
        "mapped_commit": baseline,
        "head": head,
    }
    if head == baseline:
        return report | {"state": "current"}
    report["state"] = "changed"
    try:
        fetch(directory, url, baseline)
        raw = git(
            directory,
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            baseline,
            head,
            "--",
        )
        paths = [os.fsdecode(path) for path in raw.split(b"\0") if path]
        report.update(changes(paths, tracked))
    except (subprocess.SubprocessError, OSError):
        report["detail"] = "diff_unavailable"
    return report


def check(project=None, query=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        atlas = root / "catalog"
        atlas.mkdir()
        git(atlas, "init", "--bare", "--quiet")
        commit = fetch(atlas, ATLAS + ".git", "refs/heads/main")
        catalog = json.loads(git(atlas, "show", commit + ":hub/catalog/vanillate.json"))
        selected = [m for m in catalog if not project or m["id"] == project]
        if not selected:
            raise ValueError("Project has no versioned Git catalog")
        tracked = {}
        for entry in selected:
            for node in entry["nodes"]:
                for value in {node["source"], node["locator"]}:
                    match = PIN.fullmatch(value)
                    if match:
                        repo, sha, location = match.groups()
                        tracked.setdefault((repo, sha), []).append(
                            (entry["id"], node["id"], location)
                        )
        results = []
        for index, ((repo, sha), nodes) in enumerate(sorted(tracked.items())):
            work = root / str(index)
            work.mkdir()
            try:
                results.append(inspect(work, repo, sha, nodes))
            except (OSError, subprocess.SubprocessError):
                results.append(
                    {"repository": repo, "mapped_commit": sha, "state": "unverified"}
                )
        report = {
            "context_source": "git_snapshot",
            "catalog_commit": commit,
            "repositories": results,
        }
        if query is not None:
            term = query.casefold()
            matches = [
                n
                for m in selected
                for n in m["nodes"]
                if any(
                    term in n[field].casefold()
                    for field in ("id", "name", "summary", "locator")
                )
            ]
            report["resources"] = matches[:5]
            ids = {n["id"] for n in matches[:5]}
            report["links"] = [
                edge
                for m in selected
                for edge in m["links"]
                if edge["origin"] in ids or edge["target"] in ids
            ][:20]
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Optional versioned Atlas project ID")
    args = parser.parse_args()
    try:
        report = check(args.project)
    except (ValueError, OSError, subprocess.SubprocessError):
        parser.exit(
            1, "Catalog main unavailable or project not mapped. Freshness unverified.\n"
        )
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if any(
        r["state"] == "unverified" or r.get("detail") for r in report["repositories"]
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
