import io
import os
from pathlib import Path
import zipfile
from test_evidence import upload, fact_payload


def test_preview_import_and_repeat(client):
    source = upload(client, b'Delivered 20 initiatives.\nAchieved 95% on-time delivery.').json()
    preview = client.get(f"/sources/{source['id']}/candidates").json()
    assert len(preview['candidates']) == 2
    assert client.get('/facts').json() == []
    item = preview['candidates'][0]
    body = {'source_sha256': source['sha256'], 'items': [{'candidate_id': item['candidate_id'], 'statement': 'Delivered 20 initiatives during 2020.', 'category': 'metric'}]}
    assert client.post(f"/sources/{source['id']}/facts/import", json=body).json()['created'] == 1
    fact = client.get('/facts').json()[0]
    assert fact['status'] == 'pending' and fact['source_document_id'] == source['id']
    assert fact['source_locator'] == 'Line 1' and fact['evidence_note'] == item['statement']
    assert fact['statement'].endswith('2020.')
    assert client.post(f"/sources/{source['id']}/facts/import", json=body).json()['skipped_duplicates'] == 1


def test_user_confirmation_duplicate_and_overlap(client):
    client.post('/facts', json=fact_payload(statement='Delivered 20 healthcare initiatives.'))
    source = upload(client, b'Delivered 20 healthcare initiatives.\nDelivered 20 healthcare initiatives on time.').json()
    preview = client.get(f"/sources/{source['id']}/candidates").json()
    first, second = preview['candidates']
    assert first['duplicate_fact_id']
    assert second['possible_matches'] and not second['duplicate_fact_id']
    body = {'source_sha256': source['sha256'], 'items': [{'candidate_id': first['candidate_id'], 'statement': 'DELIVERED 20 healthcare initiatives!', 'category': 'experience'}]}
    assert client.post(f"/sources/{source['id']}/facts/import", json=body).json()['created'] == 0
    assert len(client.get('/facts').json()) == 1


def test_invalid_import_is_atomic(client):
    source = upload(client, b'Example source passage.').json()
    item = client.get(f"/sources/{source['id']}/candidates").json()['candidates'][0]
    body = {'source_sha256': source['sha256'], 'items': [{'candidate_id': item['candidate_id'], 'statement': item['statement'], 'category': 'experience'}, {'candidate_id': 'fabricated', 'statement': 'Invented qualification', 'category': 'skill'}]}
    assert client.post(f"/sources/{source['id']}/facts/import", json=body).status_code == 422
    assert client.get('/facts').json() == []
    body['items'] = [body['items'][0]]
    body['source_sha256'] = 'stale'
    assert client.post(f"/sources/{source['id']}/facts/import", json=body).status_code == 409
    body['source_sha256'] = source['sha256']
    body['items'][0]['category'] = 'invented'
    assert client.post(f"/sources/{source['id']}/facts/import", json=body).status_code == 422


def test_integrity_and_pdf_limit(client):
    source = upload(client, b'Original example source.').json()
    path = Path(os.environ['SOURCE_STORAGE_DIR']) / (source['id'] + '.txt')
    path.chmod(0o600); path.write_bytes(b'Changed example source.')
    assert client.get(f"/sources/{source['id']}/candidates").status_code == 409
    pdf = client.post('/sources', files={'file': ('test.pdf', b'%PDF-1.7\nexample')}, data={'document_kind': 'supporting', 'version_label': 'test'}).json()
    assert client.get(f"/sources/{pdf['id']}/candidates").status_code == 415


def test_docx_tables_and_runs(client):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Delivered </w:t></w:r><w:r><w:t>20 initiatives.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>SQL training completed.</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
    source = client.post('/sources', files={'file': ('test.docx', data.getvalue())}, data={'document_kind': 'master_resume', 'version_label': 'test'}).json()
    preview = client.get(f"/sources/{source['id']}/candidates").json()
    assert [item['statement'] for item in preview['candidates']] == ['Delivered 20 initiatives.', 'SQL training completed.']
    assert preview['candidates'][1]['source_locator'] == 'DOCX paragraph 2'


def test_batch_reviews_and_stale_rejection(client):
    facts = [client.post('/facts', json=fact_payload(statement=text)).json() for text in ['First synthetic example.', 'Second synthetic example.']]
    body = {'decision': 'verified', 'verification_basis': 'user_confirmed', 'note': 'Confirmed both synthetic statements.', 'items': [{'fact_id': fact['id'], 'expected_revision': 0} for fact in facts]}
    assert client.post('/facts/bulk-reviews', json=body).json()['reviewed'] == 2
    for fact in client.get('/facts').json():
        assert fact['status'] == 'verified' and fact['revision'] == 1
        assert len(client.get(f"/facts/{fact['id']}/reviews").json()) == 1
    assert client.post('/facts/bulk-reviews', json=body).status_code == 409
    assert all(fact['revision'] == 1 for fact in client.get('/facts').json())


def test_batch_failure_rolls_back_every_review(client):
    facts = [client.post('/facts', json=fact_payload(statement=text)).json() for text in ['First synthetic example.', 'Second synthetic example.']]
    body = {'decision': 'verified', 'verification_basis': 'user_confirmed', 'note': 'Synthetic review note.', 'items': [{'fact_id': facts[0]['id'], 'expected_revision': 0}, {'fact_id': facts[1]['id'], 'expected_revision': 7}]}
    assert client.post('/facts/bulk-reviews', json=body).status_code == 409
    assert all(fact['status'] == 'pending' and fact['revision'] == 0 for fact in client.get('/facts').json())
    assert client.get(f"/facts/{facts[0]['id']}/reviews").json() == []
    body['items'] = [body['items'][0], body['items'][0]]
    assert client.post('/facts/bulk-reviews', json=body).status_code == 422
