import os
import time

from genesis.database.base import init_db, drop_db
from genesis.storage.conversation import ConversationManager


def test_conversation_pagination(tmp_path, monkeypatch):
    # Use a temporary genesis_home for isolation (DB will be created at genesis_home/genesis.db)
    monkeypatch.setenv('GENESIS_HOME', str(tmp_path))

    # Initialize DB
    drop_db()
    init_db()

    mind_id = 'test-mind-001'

    # Ensure a MindRecord exists for foreign key constraint
    from genesis.database.base import get_session
    from genesis.database.models import MindRecord

    with get_session() as session:
        session.add(MindRecord(gmid=mind_id, name='Test Mind', creator='tester'))
        session.commit()

    cm = ConversationManager(mind_gmid=mind_id)

    # Add 120 messages
    for i in range(120):
        role = 'user' if i % 2 == 0 else 'assistant'
        cm.add_message(role=role, content=f'Message {i}', user_email='tester@example.com')
        # Small sleep to ensure timestamp differences
        time.sleep(0.001)

    # Fetch most recent 50 messages (chronological order)
    recent = cm.get_recent_messages(limit=50, user_email='tester@example.com')
    assert len(recent) == 50

    # Capture earliest id in this batch (for pagination cursor)
    earliest_in_batch = recent[0]['id']

    # Fetch previous page before earliest_in_batch
    prev = cm.get_messages_before(before_id=earliest_in_batch, limit=50, user_email='tester@example.com')
    assert len(prev) == 50

    # Ensure no overlap between prev and recent
    prev_ids = {m['id'] for m in prev}
    recent_ids = {m['id'] for m in recent}
    assert prev_ids.isdisjoint(recent_ids)

    # Fetch the last page (should have 20 messages remaining)
    earliest_prev = prev[0]['id']
    last_page = cm.get_messages_before(before_id=earliest_prev, limit=50, user_email='tester@example.com')
    assert len(last_page) == 20

    # No more messages earlier than last page
    if last_page:
        earliest_last = last_page[0]['id']
        empty = cm.get_messages_before(before_id=earliest_last, limit=50, user_email='tester@example.com')
        assert len(empty) == 0
