import time
from genesis.database.base import init_db, drop_db, get_session
from genesis.database.models import MindRecord
from genesis.storage.conversation import ConversationManager


def test_conversation_messages_endpoint(client, auth_headers, tmp_path, monkeypatch):
    # Isolate DB in temp genesis_home
    monkeypatch.setenv('GENESIS_HOME', str(tmp_path))
    drop_db()
    init_db()

    mind_id = 'api-test-mind'
    with get_session() as session:
        session.add(MindRecord(gmid=mind_id, name='API Test Mind', creator='tester'))
        session.commit()

    cm = ConversationManager(mind_gmid=mind_id)

    for i in range(75):
        role = 'user' if i % 2 == 0 else 'assistant'
        cm.add_message(role=role, content=f'API Message {i}', user_email='api_tester@example.com')
        time.sleep(0.001)

    # Fetch initial page via API
    resp = client.get(f"/api/v1/minds/{mind_id}/conversations/messages?user_email=api_tester@example.com&limit=50", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert 'messages' in data
    assert data['count'] == 50
    assert data['has_more'] is True
    assert data['next_before_id'] is not None

    # Fetch earlier messages using before_id
    before_id = data['next_before_id']
    resp2 = client.get(f"/api/v1/minds/{mind_id}/conversations/messages?user_email=api_tester@example.com&limit=50&before_id={before_id}", headers=auth_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2['count'] == 25
    # Ensure no overlap
    ids1 = {m['id'] for m in data['messages']}
    ids2 = {m['id'] for m in data2['messages']}
    assert ids1.isdisjoint(ids2)
