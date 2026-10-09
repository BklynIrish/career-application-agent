import os
from pathlib import Path
from unittest.mock import patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from test_evidence import upload, fact_payload


def correction(fact, **changes):
    return {'statement': 'Corrected synthetic example statement.', 'category': 'experience', 'expected_revision': fact['revision'], 'reason': 'Clarified the synthetic statement.', **changes}


def test_correction_preserves_history_and_evidence(client):
    source = upload(client).json()
    original = client.post('/facts', json=fact_payload(provenance_kind='document', source_document_id=source['id'])).json()
    client.post(f"/facts/{original['id']}/reviews", json={'decision': 'verified', 'expected_revision': 0, 'verification_basis': 'user_confirmed', 'note': 'Synthetic confirmation.'})
    result = client.post(f"/facts/{original['id']}/corrections", json=correction(original, expected_revision=1))
    assert result.status_code == 201
    link = result.json()
    facts = {fact['id']: fact for fact in client.get('/facts').json()}
    old, new = facts[original['id']], facts[link['replacement_fact_id']]
    assert old['statement'] == original['statement'] and old['status'] == 'rejected'
    assert new['status'] == 'pending' and new['revision'] == 0
    for field in ['source_document_id', 'source_locator', 'evidence_note', 'provenance_kind']:
        assert new[field] == original[field]
    history = client.get(f"/facts/{original['id']}/reviews").json()
    assert len(history) == 2 and history[-1]['decision'] == 'rejected'
    assert new['id'] in history[-1]['note']
    assert client.get('/fact-corrections').json()[0]['id'] == link['id']
    assert client.get(f"/facts/{new['id']}/reviews").json() == []
    assert client.post(f"/facts/{old['id']}/reviews", json={'decision': 'verified', 'expected_revision': old['revision'], 'verification_basis': 'user_confirmed', 'note': 'Cannot revive old version.'}).status_code == 409


def test_category_only_correction_and_chains(client):
    original = client.post('/facts', json=fact_payload()).json()
    result = client.post(f"/facts/{original['id']}/corrections", json=correction(original, statement=original['statement'], category='experience')).json()
    new = next(fact for fact in client.get('/facts').json() if fact['id'] == result['replacement_fact_id'])
    assert new['statement'] == original['statement'] and new['category'] == 'experience'
    assert client.post(f"/facts/{original['id']}/corrections", json=correction(original)).status_code == 409
    assert client.post(f"/facts/{new['id']}/corrections", json=correction(new)).status_code == 201
    assert len(client.get('/fact-corrections').json()) == 2


def test_stale_unchanged_and_duplicate_rejected(client):
    original = client.post('/facts', json=fact_payload()).json()
    assert client.post(f"/facts/{original['id']}/corrections", json=correction(original, expected_revision=7)).status_code == 409
    assert client.post(f"/facts/{original['id']}/corrections", json=correction(original, statement=original['statement'], category=original['category'])).status_code == 422
    client.post('/facts', json=fact_payload(statement='Corrected synthetic example statement.', category='experience'))
    assert client.post(f"/facts/{original['id']}/corrections", json=correction(original)).status_code == 409
    assert client.get('/fact-corrections').json() == []
    assert all(fact['status'] == 'pending' for fact in client.get('/facts').json())


def test_changed_source_blocks_correction(client):
    source = upload(client).json()
    fact = client.post('/facts', json=fact_payload(provenance_kind='document', source_document_id=source['id'])).json()
    path = Path(os.environ['SOURCE_STORAGE_DIR']) / (source['id'] + '.txt')
    path.chmod(0o600); path.write_bytes(b'Changed file')
    assert client.post(f"/facts/{fact['id']}/corrections", json=correction(fact)).status_code == 409
    assert len(client.get('/facts').json()) == 1


def test_commit_failure_rolls_back_replacement_and_review(client):
    fact = client.post('/facts', json=fact_payload()).json()
    with patch.object(Session, 'commit', side_effect=IntegrityError('test', {}, Exception('synthetic failure'))):
        assert client.post(f"/facts/{fact['id']}/corrections", json=correction(fact)).status_code == 409
    assert client.get('/fact-corrections').json() == []
    assert len(client.get('/facts').json()) == 1
    assert client.get('/facts').json()[0]['status'] == 'pending'
    assert client.get(f"/facts/{fact['id']}/reviews").json() == []
