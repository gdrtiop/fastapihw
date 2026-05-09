import os
import pytest
import fakeredis
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key"


fake_redis = fakeredis.FakeRedis(decode_responses=True)

with patch("redis.Redis", return_value=fake_redis):
    from app.database import Base, engine as test_engine
    from app.main import app
    from app.deps import get_db
    import app.crud as crud_module


crud_module.r = fake_redis

TestingSessionLocal = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def reset_redis():
    fake_redis.flushall()
    yield
    fake_redis.flushall()


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, username="testuser", password="testpass"):
    client.post("/register", json={"username": username, "password": password})
    resp = client.post("/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


TASK_PAYLOAD = {
    "title": "Test task",
    "description": "My description",
    "status": "todo",
    "priority": 3,
}
