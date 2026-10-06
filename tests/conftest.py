from sqlalchemy import create_engine
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from main import app
from database import get_db,Base
import models

TEST_DATABASE_URL = "sqlite:///./test.db"
TEST_ENGINE = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

TestSession = sessionmaker(autocommit = False, autoflush = False, bind=TEST_ENGINE)

def override_get_db():
    db = TestSession()
    try: 
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture()
def client():
    Base.metadata.create_all(bind = TEST_ENGINE)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind = TEST_ENGINE)

@pytest.fixture()
def auth_headers(client):
    client.post("/users/register", json = {"email": "test@example.com", "password": "password"})
    response = client.post("/users/login", data = {"username": "test@example.com", "password": "password"})
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture()
def admin_headers(client):
    client.post("/users/register", json = {"email": "admin@example.com", "password": "password"})
    response = client.post("/users/login", data = {"username": "admin@example.com", "password": "password"})
    db = TestSession()
    try: 
        user=db.query(models.Users).filter(models.Users.email == "admin@example.com").first()
        if user:
            user.role = "admin"
            db.commit()
    finally:
        db.close()
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture()
def db_session():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()




