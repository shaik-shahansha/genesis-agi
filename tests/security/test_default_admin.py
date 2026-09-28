"""The bootstrap admin account must not exist outside development.

`_initialize_default_users()` used to create `admin` with the password
`genesis-admin-2026` unconditionally — in every environment, including
production, on first authentication attempt. That string is published in this
repository, so every Genesis install on the internet was reachable by anyone who
had read it.

This is the same failure the signing-key check (item B12) exists to prevent: a
default shipped for a developer's convenience that is indistinguishable from a
working credential in a deployment. These tests pin the boundary.
"""

import importlib

import pytest

from genesis.api import auth as auth_module


@pytest.fixture()
def clean_users(monkeypatch):
    """Give each test its own empty world.

    Both stores have to be cleared. `USERS_DB` is process memory, but the
    bootstrap admin is now also a row in `users`, so a row left by another test
    would satisfy "seed the admin" and this file's assertions about *not*
    seeding would never actually run.
    """
    monkeypatch.setattr(auth_module, "USERS_DB", {})
    _purge_durable_admin()
    yield auth_module.USERS_DB
    _purge_durable_admin()


def _purge_durable_admin():
    """Remove the bootstrap admin from the database, if it is there."""
    try:
        from genesis.database.manager import MetaverseDB
        MetaverseDB().delete_user_record(auth_module.DEFAULT_ADMIN_USERNAME)
    except Exception:  # noqa: BLE001 - the database may not be initialised yet
        pass
    auth_module.USERS_DB.pop(auth_module.DEFAULT_ADMIN_USERNAME, None)


def _seed(monkeypatch, environment, password=None):
    monkeypatch.setenv("GENESIS_ENV", environment)
    if password is None:
        monkeypatch.delenv(auth_module.ADMIN_PASSWORD_ENV, raising=False)
    else:
        monkeypatch.setenv(auth_module.ADMIN_PASSWORD_ENV, password)
    auth_module._initialize_default_users()


def test_production_does_not_seed_the_published_password(clean_users, monkeypatch):
    """The whole point: a default install must not have a known admin login."""
    _seed(monkeypatch, "production")

    assert auth_module.USERS_DB == {}, (
        "an admin account was created in production with the default password"
    )


def test_unset_environment_is_treated_as_production(clean_users, monkeypatch):
    """An unset GENESIS_ENV must not be read as 'development'.

    Every real deployment that forgets to set it is still a deployment.
    """
    monkeypatch.delenv("GENESIS_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv(auth_module.ADMIN_PASSWORD_ENV, raising=False)

    auth_module._initialize_default_users()

    assert auth_module.USERS_DB == {}


def test_development_seeds_the_convenience_account(clean_users, monkeypatch):
    """Local work should still work without ceremony."""
    _seed(monkeypatch, "development")

    assert "admin" in auth_module.USERS_DB
    user = auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD)
    assert user is not None


def test_test_environment_seeds_the_convenience_account(clean_users, monkeypatch):
    _seed(monkeypatch, "test")

    assert "admin" in auth_module.USERS_DB


def test_configured_password_is_used_when_supplied(clean_users, monkeypatch):
    """Production bootstraps from an explicit secret instead of a default."""
    _seed(monkeypatch, "production", password="a-real-bootstrap-password")

    assert "admin" in auth_module.USERS_DB
    assert auth_module.authenticate_user("admin", "a-real-bootstrap-password") is not None
    assert auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD) is None


def test_configured_password_overrides_the_dev_default(clean_users, monkeypatch):
    """An explicit password wins even in development."""
    _seed(monkeypatch, "development", password="a-real-bootstrap-password")

    assert auth_module.authenticate_user("admin", "a-real-bootstrap-password") is not None
    assert auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD) is None


def test_short_configured_password_is_refused(clean_users, monkeypatch):
    """A real-looking but weak bootstrap secret is worse than none.

    It would be assumed safe because it was configured deliberately.
    """
    _seed(monkeypatch, "production", password="short")

    assert auth_module.USERS_DB == {}


def test_blank_configured_password_is_refused(clean_users, monkeypatch):
    _seed(monkeypatch, "production", password="   ")

    assert auth_module.USERS_DB == {}


def test_seeding_is_idempotent(clean_users, monkeypatch):
    """Repeated calls must not reset a password that has since been changed."""
    _seed(monkeypatch, "test")
    auth_module.update_user_password("admin", "changed-by-the-operator")

    auth_module._initialize_default_users()

    assert auth_module.authenticate_user("admin", "changed-by-the-operator") is not None
    assert auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD) is None


def test_unauthenticated_lookup_does_not_seed_in_production(clean_users, monkeypatch):
    """The seed used to run as a side effect of *trying to log in*.

    That mattered: it meant the account appeared on the first request to a
    production deployment rather than at startup, so a deploy that had never
    been touched still had the account the moment it was probed.
    """
    monkeypatch.setenv("GENESIS_ENV", "production")
    monkeypatch.delenv(auth_module.ADMIN_PASSWORD_ENV, raising=False)

    assert auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD) is None
    assert auth_module.USERS_DB == {}
