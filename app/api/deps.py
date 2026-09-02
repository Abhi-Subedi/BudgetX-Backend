from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AppError(401, "Please sign in to continue.")
    subject = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise AppError(401, "Invalid session. Please sign in again.") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError(401, "Invalid session. Please sign in again.")
    return user


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
