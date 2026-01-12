from genesis.database.manager import MetaverseDB


def test_mind_access_add_remove():
    db = MetaverseDB()

    # Create a dummy mind
    gmid = "TEST-GMID-ACCESS"
    db.register_mind(gmid=gmid, name="TestMindAccess", creator="creator@example.com")

    # Ensure no users initially
    users = db.get_mind_allowed_users(gmid)
    assert users == []

    # Add a user
    added = db.add_mind_user_access(gmid, "alice@example.com", added_by="creator@example.com")
    assert added is True

    users = db.get_mind_allowed_users(gmid)
    assert "alice@example.com" in users

    # Adding same user again returns False
    added_again = db.add_mind_user_access(gmid, "alice@example.com", added_by="creator@example.com")
    assert added_again is False

    # Remove user
    removed = db.remove_mind_user_access(gmid, "alice@example.com")
    assert removed is True

    users = db.get_mind_allowed_users(gmid)
    assert "alice@example.com" not in users


def test_mind_public_flag():
    db = MetaverseDB()
    gmid = "TEST-GMID-PUBLIC"
    db.register_mind(gmid=gmid, name="TestMindPublic", creator="creator@example.com")

    # Default is public False
    assert db.get_mind(gmid).is_public is False

    updated = db.set_mind_public(gmid, True)
    assert updated is True
    assert db.get_mind(gmid).is_public is True

    updated = db.set_mind_public(gmid, False)
    assert updated is True
    assert db.get_mind(gmid).is_public is False
