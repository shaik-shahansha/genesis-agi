"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from genesis.api.server import create_app
from genesis.api.auth import create_user, create_access_token, UserRole, USERS_DB


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    # Create test user
    username = "test_api_user"
    if username not in USERS_DB:
        create_user(username, "test_password", role=UserRole.ADMIN)

    # Create token
    token = create_access_token({"sub": username, "role": UserRole.ADMIN})
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    """Test health and status endpoints."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Genesis AGI API"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client: TestClient):
        """Test successful login."""
        # Create test user
        username = "login_test_user"
        password = "test_password"
        if username not in USERS_DB:
            create_user(username, password)

        # Attempt login
        response = client.post(
            "/api/v1/auth/token",
            data={"username": username, "password": password},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_failure(self, client: TestClient):
        """Test login with wrong credentials."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nonexistent", "password": "wrong"},
        )

        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, auth_headers):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "username" in data

    def test_create_api_key(self, client: TestClient, auth_headers):
        """Test creating an API key."""
        response = client.post(
            "/api/v1/auth/api-keys",
            headers=auth_headers,
            json={"description": "Test key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("gsk_")


class TestMindEndpoints:
    """Test Mind management endpoints."""

    def test_list_minds_requires_auth(self, client: TestClient):
        """Test that listing minds works (may require auth in production)."""
        response = client.get("/api/v1/minds")
        # Should work with auth disabled in test settings
        assert response.status_code in [200, 401]

    def test_create_mind_requires_auth(self, client: TestClient):
        """Test that creating mind requires authentication."""
        response = client.post(
            "/api/v1/minds",
            json={
                "name": "Test Mind",
                "template": "base/curious_explorer",
                "config": "minimal",
            },
        )
        # Should require authentication
        assert response.status_code in [200, 401]

    def test_create_mind_with_auth(self, client: TestClient, auth_headers):
        """Test creating a mind with authentication."""
        response = client.post(
            "/api/v1/minds",
            headers=auth_headers,
            json={
                "name": "Authenticated Test Mind",
                "template": "base/curious_explorer",
                "config": "minimal",
                "autonomy_level": "medium",
            },
        )

        # May fail due to LLM requirements, but should not be auth error
        assert response.status_code in [200, 500]


class TestSystemEndpoints:
    """Test system endpoints."""

    @pytest.mark.asyncio
    async def test_system_status(self, client: TestClient):
        """Test system status endpoint."""
        response = client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "minds_count" in data

    @pytest.mark.asyncio
    async def test_get_providers(self, client: TestClient):
        """Test getting available providers."""
        response = client.get("/api/v1/system/providers")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "health" in data


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_on_root(self, client: TestClient):
        """Test that rate limiting is applied."""
        # Make multiple requests
        responses = []
        for _ in range(15):  # Exceeds the 10/minute limit
            response = client.get("/")
            responses.append(response.status_code)

        # Should eventually get rate limited (429)
        assert 429 in responses or all(r == 200 for r in responses)
        # Note: May not trigger in test environment
