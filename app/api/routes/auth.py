from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession
from app.core.rate_limit import rate_limit
from app.schemas import LoginIn, RefreshIn, RegisterIn, TokenPair, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

auth_limit = rate_limit(config_name="auth")


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth_limit)])
def register(payload: RegisterIn, db: DbSession):
    user = auth_service.register(
        db,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        currency=payload.currency,
        locale=payload.locale,
    )
    tokens = TokenPair(**auth_service.issue_tokens(user))
    return {"user": UserOut.model_validate(user).model_dump(), "tokens": tokens.model_dump()}


@router.post("/login", dependencies=[Depends(auth_limit)])
def login(payload: LoginIn, db: DbSession):
    user = auth_service.authenticate(db, email=payload.email, password=payload.password)
    tokens = TokenPair(**auth_service.issue_tokens(user))
    return {"user": UserOut.model_validate(user).model_dump(), "tokens": tokens.model_dump()}


@router.post("/refresh", dependencies=[Depends(auth_limit)])
def refresh(payload: RefreshIn, db: DbSession):
    tokens = TokenPair(**auth_service.refresh_tokens(db, payload.refresh_token))
    return {"tokens": tokens.model_dump()}
