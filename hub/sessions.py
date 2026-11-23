"""Dashboard cookies are revocable, scoped read-only derivatives of an API identity."""

import secrets

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from .store import database, digest, now

COOKIE = "vanillate_session"


def identity(db, cookie):
    return db.execute(
        """SELECT i.id,'reader' AS role,i.scope FROM browser_sessions s
                         JOIN identities i ON i.id=s.identity AND i.digest=s.credential_digest
                         WHERE s.digest=? AND s.expires>?""",
        (digest(cookie), now()),
    ).fetchone()


def create(request, remember):
    if not request.headers.get("authorization", "").startswith("Bearer "):
        raise HTTPException(403)
    local = request.url.hostname in ("localhost", "127.0.0.1", "::1")
    secure = request.url.scheme == "https"
    if not local and not secure:
        raise HTTPException(400, "HTTPS required")
    lifetime = (30 if remember else 1) * 86400
    cookie = secrets.token_urlsafe(40)
    with database() as db:
        db.execute(
            "DELETE FROM browser_sessions WHERE expires<=? OR digest=?",
            (now(), digest(request.cookies.get(COOKIE, ""))),
        )
        db.execute(
            "INSERT INTO browser_sessions VALUES(?,?,?,?)",
            (
                digest(cookie),
                request.state.actor["id"],
                digest(request.headers["authorization"][7:]),
                now() + lifetime,
            ),
        )
    response = JSONResponse({"connected": True}, headers={"Cache-Control": "no-store"})
    response.set_cookie(
        COOKIE,
        cookie,
        max_age=lifetime if remember else None,
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    return response


def logout(request):
    with database() as db:
        db.execute(
            "DELETE FROM browser_sessions WHERE digest=?",
            (digest(request.cookies.get(COOKIE, "")),),
        )
    response = JSONResponse({"connected": False})
    response.delete_cookie(COOKIE, samesite="strict")
    return response
