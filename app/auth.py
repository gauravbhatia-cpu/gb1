"""Small Supabase Auth bridge for FastAPI dependencies."""

from dataclasses import dataclass
import os

import requests
from fastapi import Depends, HTTPException, Request

from app.config import settings


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None = None


def _supabase_credentials() -> tuple[str, str]:
    url = (
        os.getenv("SCOUT_SUPABASE_URL") or os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or
        settings.supabase_url or ""
    )
    key = (
        os.getenv("SCOUT_SUPABASE_KEY") or
        os.getenv("SUPABASE_PUBLISHABLE_KEY") or
        os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or
        settings.supabase_publishable_key or settings.supabase_anon_key or ""
    )
    return url, key


def public_auth_config() -> dict:
    url, key = _supabase_credentials()
    return {
        "supabaseUrl": url,
        "supabaseKey": key,
    }


def optional_current_user(request: Request) -> AuthUser | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    url, key = _supabase_credentials()
    if not url or not key:
        raise HTTPException(503, "Authentication is not configured")
    try:
        response = requests.get(
            f"{url.rstrip('/')}/auth/v1/user",
            headers={"apikey": key, "Authorization": f"Bearer {token}"},
            timeout=8,
        )
    except requests.RequestException as exc:
        raise HTTPException(503, "Authentication service is unavailable") from exc
    if response.status_code != 200:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    payload = response.json()
    return AuthUser(id=payload["id"], email=payload.get("email"))


def require_current_user(user: AuthUser | None = Depends(optional_current_user)) -> AuthUser:
    if user is None:
        raise HTTPException(401, "Sign in to use your private workspace")
    return user
