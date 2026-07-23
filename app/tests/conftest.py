import pytest
import os

# Set the environment variable and settings DATABASE_URL BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_project_management.db"

from app.config import settings
settings.DATABASE_URL = "sqlite:///./test_project_management.db"

from app.database import Base, engine
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Start fresh by deleting any previous test database
    if os.path.exists("./test_project_management.db"):
        try:
            os.remove("./test_project_management.db")
        except Exception:
            pass
            
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    
    # Clean up connections so the file is not locked on disk
    engine.dispose()
    
    if os.path.exists("./test_project_management.db"):
        try:
            os.remove("./test_project_management.db")
        except Exception:
            pass

@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as c:
        yield c
