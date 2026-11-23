import os
from urllib.parse import urlsplit

import httpx

from .models import Id
from pydantic import TypeAdapter


def checked_url(raw, local_only=False):
    parsed = urlsplit(raw)
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if (not parsed.hostname or parsed.username is not None or parsed.query or parsed.fragment
            or parsed.scheme not in ("https", "http") or parsed.scheme == "http" and not local
            or local_only and not local):
        raise ValueError("Expected HTTPS Hub URL or loopback HTTP URL")
    return raw.rstrip("/")


def hub_client():
    return httpx.Client(base_url=checked_url(os.getenv("HUB_URL", "http://127.0.0.1:8000")),
                        headers={"Authorization": "Bearer " + os.environ["HUB_TOKEN"]},
                        trust_env=False, timeout=10)


def project_path():
    return "/projects/" + TypeAdapter(Id).validate_python(os.environ["HUB_PROJECT"])
