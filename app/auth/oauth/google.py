"""Google OAuth 2.0 provider.

Requires configuration:
  - GOOGLE_CLIENT_ID
  - GOOGLE_CLIENT_SECRET
Set these in your .env file or environment variables.
"""

import secrets
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

settings = get_settings()


def get_redirect_uri() -> str:
    if settings.environment == "production":
        return f"{settings.frontend_url_production}/api/oauth/google/callback"
    return "http://localhost:8000/api/oauth/google/callback"


def get_google_authorization_url(state: str | None = None) -> str:
    """Build the Google OAuth authorization URL."""
    if not settings.google_client_id:
        raise AppError(500, "Google OAuth is not configured. Set GOOGLE_CLIENT_ID.")
    if state is None:
        state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for access/refresh tokens."""
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppError(500, "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": get_redirect_uri(),
        "grant_type": "authorization_code",
    }
    resp = httpx.get(GOOGLE_TOKEN_URL, data=data, timeout=15)
    if resp.status_code != 200:
        detail = resp.json().get("error_description", resp.text)
        raise AppError(400, f"Google token exchange failed: {detail}")
    return resp.json()


def get_user_info(access_token: str) -> dict:
    """Fetch the authenticated user's profile from Google."""
    resp = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise AppError(401, "Failed to fetch Google user info.")
    return resp.json()
