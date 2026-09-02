from pydantic import BaseModel


class OAuthInitiateIn(BaseModel):
    state: str | None = None


class GoogleCallbackIn(BaseModel):
    code: str
    state: str | None = None
