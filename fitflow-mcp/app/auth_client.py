import os
import time

import httpx

from .consul_client import discover_service

DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL")
DEMO_USER_PASSWORD = os.getenv("DEMO_USER_PASSWORD")

_TOKEN_TTL_SECONDS = 50 * 60

_cached_token: str | None = None
_cached_at: float = 0.0


def get_token() -> str:
    global _cached_token, _cached_at

    if _cached_token and (time.time() - _cached_at) < _TOKEN_TTL_SECONDS:
        return _cached_token

    if not DEMO_USER_EMAIL or not DEMO_USER_PASSWORD:
        raise RuntimeError(
            "DEMO_USER_EMAIL / DEMO_USER_PASSWORD no configurados."
        )

    users_url = discover_service("users-svc")
    resp = httpx.post(
        f"{users_url}/login",
        json={"email": DEMO_USER_EMAIL, "password": DEMO_USER_PASSWORD},
        timeout=5.0,
    )
    resp.raise_for_status()

    _cached_token = resp.json()["access_token"]
    _cached_at = time.time()
    return _cached_token