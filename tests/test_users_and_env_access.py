from genesis.database.manager import MetaverseDB


def test_create_and_list_users():
    db = MetaverseDB()
    username = "test_user_1"
    email = "test_user_1@example.com"

    # Ensure create_user_record returns a record and get_all_users contains it
    db.create_user_record(username=username, email=email, role="user")
    users = db.get_all_users()
    assert any(u['username'] == username and u['email'] == email for u in users)


def test_environment_access_controls():
    db = MetaverseDB()
    env_id = "ENV-TEST-ACCESS"
    name = "TestEnv"

    # create environment (low-level)
    db.register_environment(env_id=env_id, name=name, env_type="test", owner_gmid=None, is_public=False)

    # Default allowed users should be empty
    assert db.get_environment_allowed_users(env_id) == []

    # Add user access
    assert db.add_environment_user_access(env_id, "alice@example.com") is True
    assert "alice@example.com" in db.get_environment_allowed_users(env_id)

    # Adding again returns False
    assert db.add_environment_user_access(env_id, "alice@example.com") is False

    # Remove user
    assert db.remove_environment_user_access(env_id, "alice@example.com") is True
    assert "alice@example.com" not in db.get_environment_allowed_users(env_id)

    # Set public
    assert db.set_environment_public(env_id, True) is True
    env = db.get_environment(env_id)
    assert getattr(env, 'is_public', False) is True
