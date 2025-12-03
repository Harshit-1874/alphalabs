import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from app import app
from dependencies import get_current_user
from database import get_db
from models import User, UserSettings

# Create a TestClient
client = TestClient(app)

# Mock User Data
MOCK_USER_ID = uuid.uuid4()
MOCK_CLERK_ID = "user_test123"
MOCK_USER = User(
    id=MOCK_USER_ID,
    clerk_id=MOCK_CLERK_ID,
    email="test@example.com",
    first_name="Test",
    last_name="User",
    username="testuser",
    plan="free",
    timezone="UTC",
    is_active=True,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

MOCK_SETTINGS = UserSettings(
    user_id=MOCK_USER_ID,
    theme="dark",
    default_capital=10000.00
)

# Mock Dependency: get_current_user
async def mock_get_current_user():
    return MOCK_USER

# Mock Dependency: get_db
async def mock_get_db():
    mock_session = AsyncMock()
    
    # Mock execute result for settings
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MOCK_SETTINGS
    mock_session.execute.return_value = mock_result
    
    yield mock_session

# Apply overrides
app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_db] = mock_get_db

def test_get_me():
    """Test GET /api/users/me"""
    response = client.get("/api/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["clerk_id"] == MOCK_CLERK_ID

def test_get_my_settings():
    """Test GET /api/users/me/settings"""
    response = client.get("/api/users/me/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["theme"] == "dark"
    assert float(data["settings"]["default_capital"]) == 10000.00

def test_update_my_settings():
    """Test PUT /api/users/me/settings"""
    payload = {
        "theme": "light",
        "default_capital": 50000.00
    }
    
    # We need to mock the DB session specifically for this test to verify updates
    # or we can check if the global MOCK_SETTINGS was updated (since it's a mutable object)
    
    # Reset MOCK_SETTINGS values before test
    MOCK_SETTINGS.theme = "dark"
    MOCK_SETTINGS.default_capital = 10000.00
    
    response = client.put("/api/users/me/settings", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["theme"] == "light"
    assert float(data["settings"]["default_capital"]) == 50000.00
    
    # Verify the object was updated
    assert MOCK_SETTINGS.theme == "light"
    assert float(MOCK_SETTINGS.default_capital) == 50000.00

@patch("api.users.verify_clerk_token")
@patch("api.users.get_user_id_from_token")
def test_sync_user_success(mock_get_user_id, mock_verify_token):
    """Test POST /api/users/sync success"""
    mock_verify_token.return_value = {
        "email": "new@example.com",
        "first_name": "New",
        "last_name": "User",
        "username": "newuser",
        "image_url": "http://image.com"
    }
    mock_get_user_id.return_value = "user_new123"
    
    # Mock DB to return None (user doesn't exist)
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None # User not found
    mock_session.execute.return_value = mock_result
    
    async def mock_refresh(instance):
        instance.id = uuid.uuid4()
        instance.plan = "free"
        instance.timezone = "UTC"
        instance.is_active = True
        
    mock_session.refresh.side_effect = mock_refresh
    
    async def local_mock_get_db():
        yield mock_session
        
    app.dependency_overrides[get_db] = local_mock_get_db
    
    # We need to pass Authorization header
    headers = {"Authorization": "Bearer test_token"}
    response = client.post("/api/users/sync", headers=headers)
    
    # Reset override
    app.dependency_overrides[get_db] = mock_get_db
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User created"
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["clerk_id"] == "user_new123"

def test_sync_user_auth_error():
    """Test POST /api/users/sync without auth"""
    # This endpoint requires auth header but we are not mocking the dependency here
    # It should fail because verify_clerk_token will be called with None
    
    # We need to ensure verify_clerk_token raises HTTPException(401) when token is missing/invalid
    # In the real app, verify_clerk_token does this.
    # Since we are NOT patching verify_clerk_token here, it will run the real function (or try to).
    # However, without CLERK_SECRET_KEY env var, it might fail differently.
    
    # Let's patch it to raise 401 to simulate auth failure behavior
    with patch("api.users.verify_clerk_token") as mock_verify:
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=401, detail="Invalid token")
        
        response = client.post("/api/users/sync")
        assert response.status_code == 401
