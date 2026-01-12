from genesis.database.manager import MetaverseDB
from genesis.api.auth import UserRole


def test_global_admin_add_remove():
    db = MetaverseDB()
    email = "superadmin@example.com"

    # Ensure clean state
    try:
        db.remove_global_admin(email)
    except Exception:
        pass

    added = db.add_global_admin(email, added_by="test")
    assert added is True
    assert email in db.list_global_admins()

    # Adding same again returns False
    added_again = db.add_global_admin(email, added_by="test")
    assert added_again is False

    removed = db.remove_global_admin(email)
    assert removed is True
    assert email not in db.list_global_admins()


def test_is_global_admin_affects_user_role():
    db = MetaverseDB()
    email = "elevate@example.com"

    # Ensure user exists in USERS_DB
    from genesis.api.auth import create_user, USERS_DB
    username = f"u_{email}"
    if username not in USERS_DB:
        create_user(username, "pass", email=email)

    try:
        db.add_global_admin(email, added_by="test")
        assert db.is_global_admin(email)

        # Simulate checking via API auth helpers
        # create_access_token with email
        from genesis.api.auth import create_access_token, get_current_user_from_token
        token = create_access_token({"sub": username, "role": UserRole.USER, "email": email})
        # Call the async auth helper directly with a credentials-like object
        import asyncio
        u = asyncio.get_event_loop().run_until_complete(
            get_current_user_from_token(type('Cred', (), {'credentials': token}))
        )
        assert u.role == UserRole.ADMIN
    finally:
        db.remove_global_admin(email)