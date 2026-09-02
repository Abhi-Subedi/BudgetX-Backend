from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError
from app.core.security import create_access_token, create_refresh_token
from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.schemas.oauth import GoogleCallbackIn, OAuthInitiateIn
from app.services import oauth_service

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/providers")
def list_providers(user: CurrentUser, db: DbSession):
    accounts = db.scalars(
        select(OAuthAccount).where(OAuthAccount.user_id == user.id)
    ).all()

    connected_providers = {a.provider: a for a in accounts}
    has_password = user.password_hash is not None

    providers = [
        {
            "provider": "password",
            "connected": has_password,
            "email": user.email if has_password else None,
        }
    ]

    for provider_name in ["google"]:
        account = connected_providers.get(provider_name)
        providers.append({
            "provider": provider_name,
            "connected": account is not None,
            "email": account.provider_email if account else None,
        })

    return {"providers": providers}


@router.post("/google")
def google_login(payload: OAuthInitiateIn):
    from app.auth.oauth import google
    url = google.get_google_authorization_url(state=payload.state)
    return {"url": url}


@router.get("/google/callback")
def google_callback_get(
    code: str,
    db: DbSession,
    state: str | None = None,
):
    from app.auth.oauth import google
    from app.services.auth_service import issue_tokens
    from app.schemas.user import UserOut

    # Validate required parameters
    if not code:
        raise AppError(400, "Missing authorization code.")

    token_data = google.exchange_code(code=code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise AppError(400, "Failed to get access token from Google.")

    user_info = google.get_user_info(access_token=access_token)
    sub = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name", email)

    if not sub or not email:
        raise AppError(400, "Could not retrieve user information from Google.")

    user, is_new = oauth_service.find_or_create_oauth_user(
        db=db,
        provider="google",
        provider_user_id=sub,
        email=email,
        name=name,
    )

    tokens = issue_tokens(user)
    return {
        "user": UserOut.model_validate(user).model_dump(),
        "tokens": tokens,
    }


@router.post("/google/link")
def google_link(payload: GoogleCallbackIn, user: CurrentUser, db: DbSession):
    from app.auth.oauth import google

    token_data = google.exchange_code(code=payload.code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise AppError(400, "Failed to get access token from Google.")

    user_info = google.get_user_info(access_token=access_token)
    sub = user_info.get("sub")
    email = user_info.get("email")

    if not sub:
        raise AppError(400, "Could not retrieve user information from Google.")

    oauth_account = oauth_service.link_oauth_account(
        db=db,
        user_id=user.id,
        provider="google",
        provider_user_id=sub,
        email=email,
    )

    return {
        "detail": "Google account linked successfully.",
        "provider": "google",
        "email": email,
    }


@router.delete("/google/unlink")
def google_unlink(user: CurrentUser, db: DbSession):
    oauth_service.unlink_oauth_account(db=db, user_id=user.id, provider="google")
    return {"detail": "Google account disconnected."}
