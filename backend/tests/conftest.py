import pytest
from unittest.mock import AsyncMock, MagicMock
from app import app
from database import get_db
from api.users import get_current_user

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.fixture
def mock_auth_dependency():
    from types import SimpleNamespace
    mock_user = SimpleNamespace(id="user_123", email="test@example.com")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides = {}

@pytest.fixture(autouse=True)
def override_db(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides = {}
