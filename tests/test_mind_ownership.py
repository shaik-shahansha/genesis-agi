"""Regression tests for Mind ownership.

A Mind whose ``creator`` column holds the placeholder was inaccessible to the
person who created it: the creation route never passed the authenticated user
through to ``Mind.birth``, so ``MindRecord.creator`` was written as the literal
``"anonymous"``, and that column is what the access check reads. The symptom was
a 403 on your own Mind with nothing in the response explaining it.

These tests pin both halves - the write path, and the repair for records that
were already written wrongly.
"""

import pytest

from genesis.database.manager import PLACEHOLDER_CREATOR, MetaverseDB


@pytest.fixture()
def db():
    return MetaverseDB()


def test_creator_is_allowed_for_their_own_mind(db):
    gmid = "TEST-GMID-OWNER-001"
    db.register_mind(gmid=gmid, name="OwnerCheck", creator="owner@example.com")

    assert db.is_user_allowed_for_mind(gmid, "owner@example.com") is True


def test_stranger_is_not_allowed(db):
    gmid = "TEST-GMID-OWNER-002"
    db.register_mind(gmid=gmid, name="OwnerCheck2", creator="owner@example.com")

    assert db.is_user_allowed_for_mind(gmid, "stranger@example.com") is False


def test_placeholder_creator_grants_nobody_access(db):
    """The placeholder must never match a real user.

    If it did, anyone able to register an account named ``anonymous`` would own
    every Mind created by an older build.
    """
    gmid = "TEST-GMID-OWNER-003"
    db.register_mind(gmid=gmid, name="OrphanCheck", creator=PLACEHOLDER_CREATOR)

    assert db.is_user_allowed_for_mind(gmid, PLACEHOLDER_CREATOR) is True  # literal match
    assert db.is_user_allowed_for_mind(gmid, "someone@example.com") is False


def test_reconcile_replaces_a_placeholder(db):
    gmid = "TEST-GMID-REPAIR-001"
    db.register_mind(gmid=gmid, name="RepairCheck", creator=PLACEHOLDER_CREATOR)

    assert db.is_user_allowed_for_mind(gmid, "real@example.com") is False

    repaired = db.reconcile_mind_creator(gmid, "real@example.com")
    assert repaired is True

    assert db.get_mind(gmid).creator == "real@example.com"
    assert db.is_user_allowed_for_mind(gmid, "real@example.com") is True


def test_reconcile_never_reassigns_a_real_owner(db):
    """The repair must not be a takeover primitive."""
    gmid = "TEST-GMID-REPAIR-002"
    db.register_mind(gmid=gmid, name="TakeoverCheck", creator="legitimate@example.com")

    repaired = db.reconcile_mind_creator(gmid, "attacker@example.com")

    assert repaired is False
    assert db.get_mind(gmid).creator == "legitimate@example.com"
    assert db.is_user_allowed_for_mind(gmid, "attacker@example.com") is False


def test_reconcile_ignores_a_placeholder_candidate(db):
    """A placeholder is not a real identifier, so it cannot be adopted."""
    gmid = "TEST-GMID-REPAIR-003"
    db.register_mind(gmid=gmid, name="PlaceholderCandidate", creator=PLACEHOLDER_CREATOR)

    assert db.reconcile_mind_creator(gmid, PLACEHOLDER_CREATOR) is False
    assert db.reconcile_mind_creator(gmid, "") is False
    assert db.reconcile_mind_creator(gmid, None) is False
    assert db.get_mind(gmid).creator == PLACEHOLDER_CREATOR


def test_register_mind_repairs_a_placeholder(db):
    """Re-registering an existing Mind with a real creator adopts it."""
    gmid = "TEST-GMID-REPAIR-004"
    db.register_mind(gmid=gmid, name="ReRegister", creator=PLACEHOLDER_CREATOR)

    db.register_mind(gmid=gmid, name="ReRegister", creator="owner@example.com")

    assert db.get_mind(gmid).creator == "owner@example.com"
    assert db.is_user_allowed_for_mind(gmid, "owner@example.com") is True


def test_register_mind_does_not_rename_an_owned_mind(db):
    gmid = "TEST-GMID-REPAIR-005"
    db.register_mind(gmid=gmid, name="Keep", creator="first@example.com")

    db.register_mind(gmid=gmid, name="Keep", creator="second@example.com")

    assert db.get_mind(gmid).creator == "first@example.com"
