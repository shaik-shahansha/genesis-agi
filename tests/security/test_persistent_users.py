"""Accounts must survive a restart.

`auth.USERS_DB` was the user store, and it was process memory. The `users` table
recorded a username, an email and a role but **no password**, so:

  * every account created through the admin panel existed in the database and
    could not sign in after a restart — the row was there, the credential
    nowhere;
  * a JWT issued before a restart was rejected after it, because token resolution
    read the same empty dict;
  * `minds.creator` could name an account that no longer had any way to
    authenticate.

These tests simulate a restart by clearing the cache, which is exactly what a new
process starts with, and assert the account still works.
"""

import importlib
import os
import uuid

import pytest

from genesis.api import auth as auth_module
from genesis.database.manager import MetaverseDB


@pytest.fixture()
def restartable(monkeypatch):
    """A clean store, with the dev bootstrap admin enabled.

    `GENESIS_ENV=development` so the bootstrap admin is seeded and the test does
    not depend on a configured password. The admin's durable row is removed
    first: it is a real record now, so leaving one behind would mean the next
    test starts with an account that it did not create.
    """
    monkeypatch.setenv("GENESIS_ENV", "development")
    monkeypatch.delenv(auth_module.ADMIN_PASSWORD_ENV, raising=False)
    monkeypatch.setattr(auth_module, "USERS_DB", {})
    db = MetaverseDB()
    db.delete_user_record(auth_module.DEFAULT_ADMIN_USERNAME)
    auth_module.USERS_DB.pop(auth_module.DEFAULT_ADMIN_USERNAME, None)
    yield db


def simulate_restart():
    """Drop the process cache, as a new process would start with it empty."""
    auth_module.USERS_DB.clear()


def unique(prefix: str) -> str:
    """Usernames and emails are UNIQUE in the table, so tests must not collide."""
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def test_created_user_can_sign_in_after_a_restart(restartable):
    username = unique("restart")
    password = "a-real-password-1234"

    auth_module.create_user(username, password, email=f"{username}@example.com")
    assert auth_module.authenticate_user(username, password) is not None

    simulate_restart()

    # The point of the whole change.
    assert auth_module.authenticate_user(username, password) is not None


def test_wrong_password_is_still_refused_after_a_restart(restartable):
    """Durability must not become permissiveness."""
    username = unique("restart-neg")
    password = "a-real-password-1234"

    auth_module.create_user(username, password, email=f"{username}@example.com")
    simulate_restart()

    assert auth_module.authenticate_user(username, "not-the-password") is None
    assert auth_module.authenticate_user(username, "") is None


def test_password_change_persists_across_a_restart(restartable):
    username = unique("rotate")
    old = "the-original-password"
    new = "the-rotated-password-99"

    auth_module.create_user(username, old, email=f"{username}@example.com")
    assert auth_module.update_user_password(username, new) is True

    simulate_restart()

    assert auth_module.authenticate_user(username, old) is None
    assert auth_module.authenticate_user(username, new) is not None


def test_delete_persists_across_a_restart(restartable):
    username = unique("deleted")
    password = "a-real-password-1234"

    auth_module.create_user(username, password, email=f"{username}@example.com")
    assert auth_module.delete_user(username) is True

    simulate_restart()

    assert auth_module.authenticate_user(username, password) is None
    assert restartable.get_user_credentials(username) is None


def test_token_issued_before_a_restart_still_resolves(restartable):
    """A restart must not sign out every existing session."""
    username = unique("session")
    auth_module.create_user(username, "a-real-password-1234", email=f"{username}@example.com")

    token = auth_module.create_access_token({"sub": username, "role": "user"})

    simulate_restart()

    import asyncio

    user = asyncio.run(auth_module.resolve_user_from_token(token))
    assert user is not None
    assert user.username == username


def test_disabled_user_is_refused_after_a_restart(restartable):
    """`disabled` must be enforced on the durable read, not only in memory."""
    username = unique("disabled")
    password = "a-real-password-1234"

    auth_module.create_user(username, password, email=f"{username}@example.com")
    restartable.update_user_record(username, disabled=True)
    auth_module.invalidate_user_cache(username)

    assert auth_module.authenticate_user(username, password) is None


def test_account_without_a_credential_is_refused_not_crashed(restartable):
    """Rows written by older builds have no password.

    `authenticate_user` used to call bcrypt with an empty hash, which raises
    `ValueError: Invalid salt` — an unhandled 500 on the login endpoint. A wrong
    username should be indistinguishable from an account with no password.
    """
    username = unique("legacy")
    restartable.create_user_record(username=username, email=f"{username}@example.com")

    assert auth_module.authenticate_user(username, "anything-at-all") is None


def test_legacy_account_can_be_recovered_by_setting_a_password(restartable):
    """The migration path for accounts that predate stored credentials."""
    username = unique("recover")
    restartable.create_user_record(username=username, email=f"{username}@example.com")

    password = "a-fresh-password-5678"
    assert auth_module.update_user_password(username, password) is True

    simulate_restart()

    assert auth_module.authenticate_user(username, password) is not None


def test_re_registering_a_username_does_not_take_over_the_account(restartable):
    """Creating a user must not adopt an existing row.

    An earlier draft of `create_user_record` backfilled a credential onto any
    existing row with none, which meant `create_user(existing_username, ...)`
    could set the password on an account it did not own. That is account
    takeover, so the rule is: an existing row is returned untouched, and changing
    a credential is only ever `update_user_password`.
    """
    username = unique("takeover")
    restartable.create_user_record(username=username, email=f"{username}@example.com")

    with pytest.raises(ValueError):
        auth_module.create_user(username, "attacker-chosen-password", email=f"{username}@example.com")

    creds = restartable.get_user_credentials(username)
    assert creds is not None
    assert not creds["hashed_password"]
    assert auth_module.authenticate_user(username, "attacker-chosen-password") is None


def test_bootstrap_admin_is_durable_and_rotatable(restartable):
    """The admin account must be a real row, not a per-start derivation.

    It used to live only in the in-memory dict, which had two consequences: it
    could not survive a restart except by re-deriving it from the environment,
    and `update_user_password("admin", ...)` failed with "no such user" because
    there was no row to update.
    """
    assert auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD) is not None

    rotated = "a-rotated-admin-password-01"
    assert auth_module.update_user_password("admin", rotated) is True

    simulate_restart()

    assert auth_module.authenticate_user("admin", rotated) is not None
    # A rotation must not be undone by the next start re-applying the configured
    # password, or rotating the admin would be impossible in practice.
    assert auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD) is None



def test_password_hash_is_never_serialised(restartable):
    """`/api/v1/admin/users` must not leak the hash."""
    username = unique("nohash")
    auth_module.create_user(username, "a-real-password-1234", email=f"{username}@example.com")

    listed = restartable.get_all_users()
    row = next(u for u in listed if u["username"] == username)

    assert "hashed_password" not in row
    assert "password" not in row
    # A presence flag is useful to an admin and reveals nothing.
    assert row["has_password"] is True


def test_credentials_reader_returns_the_hash(restartable):
    """The credential reader is the one path that does return it."""
    username = unique("creds")
    auth_module.create_user(username, "a-real-password-1234", email=f"{username}@example.com")

    creds = restartable.get_user_credentials(username)
    assert creds is not None
    assert creds["hashed_password"]
    assert creds["hashed_password"] != "a-real-password-1234"


def test_bootstrap_admin_is_not_restored_with_a_known_password(restartable, monkeypatch):
    """The bootstrap path must not resurrect a published credential.

    Guards the fix in tests/security/test_default_admin.py against this change:
    making users durable must not make the development password durable too.
    """
    monkeypatch.setenv("GENESIS_ENV", "production")
    monkeypatch.delenv(auth_module.ADMIN_PASSWORD_ENV, raising=False)
    auth_module.USERS_DB.clear()
    restartable.delete_user_record(auth_module.DEFAULT_ADMIN_USERNAME)

    auth_module.authenticate_user("admin", auth_module.DEFAULT_DEV_ADMIN_PASSWORD)

    assert "admin" not in auth_module.USERS_DB
