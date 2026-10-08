import hashlib
import io
import os
from pathlib import Path
import zipfile

import pytest
from sqlalchemy.orm import Session

from app import evidence


def upload(client, data=b"Synthetic career source", **metadata):
    return client.post("/sources", files={"file": ("../../master.txt", data, "text/plain")},
        data={"document_kind": "master_resume", "version_label": "v1", **metadata})


def fact_payload(**changes):
    return {"statement": "Completed twenty synthetic example initiatives.", "category": "metric",
            "provenance_kind": "user_confirmation", "source_locator": "Synthetic confirmation dated 2026-10-08",
            "evidence_note": "Synthetic user attestation for test purposes only.", **changes}


def test_upload_bytes_hash_and_integrity(client):
    content = b"Synthetic career source"
    response = upload(client, content)
    assert response.status_code == 201
    source = response.json()
    assert source["original_filename"] == "master.txt"
    assert source["sha256"] == hashlib.sha256(content).hexdigest()
    stored = Path(os.environ["SOURCE_STORAGE_DIR"]) / (source["id"] + ".txt")
    assert stored.read_bytes() == content
    assert stored.stat().st_mode & 0o222 == 0
    assert client.get(f"/sources/{source['id']}/integrity").json()["status"] == "intact"
    assert upload(client, content).status_code == 409
    assert len(list(stored.parent.iterdir())) == 1


def test_version_preserves_old_bytes(client):
    first = upload(client).json()
    second = upload(client, b"Changed synthetic source", version_label="v2", supersedes_id=first["id"])
    assert second.status_code == 201
    assert second.json()["supersedes_id"] == first["id"]
    root = Path(os.environ["SOURCE_STORAGE_DIR"])
    assert (root / (first["id"] + ".txt")).read_bytes() == b"Synthetic career source"
    assert len(client.get("/sources").json()) == 2
    assert upload(client, b"Third version", supersedes_id="missing").status_code == 422
    assert upload(client, b"Another version", document_kind="htcmf", supersedes_id=first["id"]).status_code == 422


def test_bad_uploads(client, monkeypatch):
    assert upload(client, b"").status_code == 422
    assert upload(client, b"\xff").status_code == 422
    assert client.post("/sources", files={"file": ("resume.exe", b"data")}, data={"document_kind": "htcmf", "version_label": "v1"}).status_code == 415
    assert client.post("/sources", files={"file": ("resume.docx", b"not a zip")}, data={"document_kind": "htcmf", "version_label": "v1"}).status_code == 422
    monkeypatch.setattr(evidence, "MAX_SOURCE_BYTES", 10)
    assert upload(client, b"x" * 11).status_code == 413
    assert client.get("/sources").json() == []


@pytest.mark.parametrize("suffix", ["docx", "pdf"])
def test_basic_format_acceptance(client, suffix):
    if suffix == "docx":
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
        content = buffer.getvalue()
    else:
        # Registration checks the header, not full PDF parser validity.
        content = b"%PDF-1.7\nSynthetic header fixture"
    result = client.post("/sources", files={"file": (f"source.{suffix}", content)},
                         data={"document_kind": "supporting", "version_label": "test"})
    assert result.status_code == 201
    assert result.json()["sha256"] == hashlib.sha256(content).hexdigest()


def test_fact_pending_and_source_validation(client):
    fact = client.post("/facts", json=fact_payload()).json()
    assert fact["status"] == "pending"
    assert fact["revision"] == 0
    assert client.get("/facts?status=verified").json() == []
    assert client.post("/facts", json=fact_payload(provenance_kind="document")).status_code == 422
    assert client.post("/facts", json=fact_payload(provenance_kind="document", source_document_id="missing")).status_code == 422
    assert client.post("/facts", json=fact_payload(status="verified")).status_code == 422


def test_review_history_stale_review_and_rejection(client):
    fact = client.post("/facts", json=fact_payload()).json()
    path = f"/facts/{fact['id']}/reviews"
    assert client.post(path, json={"decision": "verified", "expected_revision": 0, "note": "Confirmed by user"}).status_code == 422
    review = {"decision": "verified", "expected_revision": 0, "verification_basis": "user_confirmed", "note": "User explicitly confirmed this synthetic claim"}
    result = client.post(path, json=review)
    assert result.status_code == 200
    assert result.json()["status"] == "verified"
    assert len(client.get("/facts?status=verified").json()) == 1
    assert client.post(path, json=review).status_code == 409
    reverted = client.post(path, json={"decision": "rejected", "expected_revision": 1, "note": "Incorrect scope; replace with a corrected fact"})
    assert reverted.json()["revision"] == 2
    assert client.get("/facts?status=verified").json() == []
    history = client.get(path).json()
    assert [item["decision"] for item in history] == ["verified", "rejected"]
    assert history[0]["verification_basis"] == "user_confirmed"
    assert history[1]["previous_status"] == "verified"


def test_missing_or_changed_source_blocks_verification(client):
    source = upload(client).json()
    fact = client.post("/facts", json=fact_payload(provenance_kind="document", source_document_id=source["id"])).json()
    stored = Path(os.environ["SOURCE_STORAGE_DIR"]) / (source["id"] + ".txt")
    stored.chmod(0o600)
    stored.write_bytes(b"Changed outside application")
    assert client.get(f"/sources/{source['id']}/integrity").status_code == 409
    review = {"decision": "verified", "expected_revision": 0, "verification_basis": "document_supported", "note": "Checked source document"}
    assert client.post(f"/facts/{fact['id']}/reviews", json=review).status_code == 409
    assert client.get("/facts").json()[0]["status"] == "pending"
    stored.unlink()
    assert client.get(f"/sources/{source['id']}/integrity").status_code == 409


def test_failed_database_commit_removes_new_copy(client, monkeypatch):
    def fail_commit(_):
        raise RuntimeError("Synthetic database failure")
    monkeypatch.setattr(Session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="Synthetic database failure"):
        upload(client)
    assert list(Path(os.environ["SOURCE_STORAGE_DIR"]).iterdir()) == []
    assert client.get("/sources").json() == []
