"""Tests for API authentication."""

import pytest
from datetime import timedelta
from genesis.api.auth import (
    create_access_token,
    create_user,
    authenticate_user,
    create_api_key,
    verify_password,
    get_password_hash,
    User,
    UserRole,
    USERS_DB,
    API_KEYS,
)


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)


class TestUserManagement:
    """Test user management functions."""

    def test_create_user(self):
        """Test creating a new user."""
        username = "test_user_123"
        password = "secure_password"

        # Clean up if exists
        if username in USERS_DB:
            del USERS_DB[username]

        user = create_user(
            username=username,
            password=password,
            email="test@example.com",
            role=UserRole.USER,
        )

        assert user.username == username
        assert user.email == "test@example.com"
        assert user.role == UserRole.USER
        assert username in USERS_DB

        # Clean up
        del USERS_DB[username]

    def test_create_duplicate_user(self):
        """Test that creating duplicate user raises error."""
        username = "duplicate_user"
        password = "password"

        # Clean up if exists
        if username in USERS_DB:
            del USERS_DB[username]

        create_user(username, password)

        with pytest.raises(ValueError, match="already exists"):
            create_user(username, password)

        # Clean up
        del USERS_DB[username]

    def test_authenticate_user(self):
        """Test user authentication."""
        username = "auth_test_user"
        password = "correct_password"

        # Clean up and create
        if username in USERS_DB:
            del USERS_DB[username]
        create_user(username, password)

        # Test correct authentication
        user = authenticate_user(username, password)
        assert user is not None
        assert user.username == username

        # Test wrong password
        user = authenticate_user(username, "wrong_password")
        assert user is None

        # Test non-existent user
        user = authenticate_user("nonexistent", password)
        assert user is None

        # Clean up
        del USERS_DB[username]


class TestTokenGeneration:
    """Test JWT token generation."""

    def test_create_access_token(self):
        """Test creating JWT access token."""
        data = {"sub": "test_user", "role": "user"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test creating token with custom expiration."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        assert token is not None


class TestAPIKeys:
    """Test API key management."""

    def test_create_api_key(self):
        """Test creating an API key."""
        username = "api_key_test_user"
        description = "Test API key"

        api_key = create_api_key(username, description)

        assert api_key.startswith("gsk_")
        assert api_key in API_KEYS
        assert API_KEYS[api_key]["username"] == username
        assert API_KEYS[api_key]["description"] == description

        # Clean up
        del API_KEYS[api_key]

    def test_api_key_format(self):
        """Test API key format."""
        api_key = create_api_key("test_user")

        assert api_key.startswith("gsk_")
        assert len(api_key) > 20  # Should be reasonably long

        # Clean up
        del API_KEYS[api_key]


class TestUserRoles:
    """Test user roles and permissions."""

    def test_user_roles(self):
        """Test different user roles."""
        assert UserRole.ADMIN == "admin"
        assert UserRole.USER == "user"
        assert UserRole.READONLY == "readonly"

    def test_user_model(self):
        """Test User model."""
        user = User(
            username="test",
            email="test@example.com",
            role=UserRole.ADMIN,
            disabled=False,
        )

        assert user.username == "test"
        assert user.role == UserRole.ADMIN
        assert not user.disabled
