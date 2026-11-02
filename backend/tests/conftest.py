import os

# Must be set before the app is imported so the app uses a throw-away database.
os.environ["DATABASE_URL"] = "sqlite:///./test_pulsewatch.db"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["AUTH_USERNAME"] = "owner"
os.environ["AUTH_PASSWORD"] = "test-password"
os.environ["SECRET_KEY"] = "test-secret-key"
# Keep real SMTP settings from a developer's .env out of the tests.
for _name in ("SMTP_HOST", "ALERT_EMAIL_TO", "ALERT_EMAIL_FROM", "SMTP_USERNAME"):
    os.environ[_name] = ""

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        token = test_client.post("/api/auth/login", json={"username": "owner", "password": "test-password"}).json()["access_token"]
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client
    Base.metadata.drop_all(engine)


@pytest.fixture
def anon_client():
    """A client that is NOT logged in."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def remove_test_database():
    yield
    engine.dispose()
    if os.path.exists("test_pulsewatch.db"):
        os.remove("test_pulsewatch.db")
