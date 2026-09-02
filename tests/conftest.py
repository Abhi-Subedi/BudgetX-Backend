import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import _rate_limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    _rate_limiter._buckets.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    _rate_limiter._buckets.clear()


def register_and_login(client, *, name="Asha Rai", email="asha@example.com", password="hunter2secret", currency="USD"):
    response = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password, "currency": currency},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return {
        "user": data["user"],
        "headers": {"Authorization": f"Bearer {data['tokens']['access_token']}"},
        "refresh": data["tokens"]["refresh_token"],
    }


def get_categories(client, headers, kind="expense") -> list[dict]:
    response = client.get(f"/api/categories?kind={kind}", headers=headers)
    assert response.status_code == 200
    return response.json()["items"]
