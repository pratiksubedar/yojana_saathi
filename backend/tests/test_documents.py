import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import async_session_factory
from app.db.models import EphemeralChecklistItem
from app.services.document_service import DocumentChecklistService

client = TestClient(app)


def test_get_checklist_success():
    """Verify retrieving document checklist for a scheme returns 200 OK and expected documents."""
    res = client.get("/api/v1/documents/checklist/pm-kisan")
    assert res.status_code == 200
    data = res.json()

    assert data["scheme_id"] == "pm-kisan"
    assert data["total_documents"] == 3
    assert data["mandatory_count"] == 3
    assert data["optional_count"] == 0
    assert data["collected_count"] == 0
    assert data["is_complete"] is False

    # Check multilingual scheme titles and disclaimers
    for lang in ["en", "hi", "kn", "te"]:
        assert lang in data["scheme_name"]
        assert len(data["scheme_name"][lang].strip()) > 0
        assert lang in data["disclaimer"]
        assert len(data["disclaimer"][lang].strip()) > 0

    # Official source references
    assert data["official_portal_url"].startswith("https://")
    assert "issuing_authority" in data["source_citation"]

    # Documents verification
    doc_ids = [d["id"] for d in data["documents"]]
    assert "doc-pmk-aadhaar" in doc_ids
    assert "doc-pmk-land" in doc_ids
    assert "doc-pmk-bank" in doc_ids

    for doc in data["documents"]:
        assert doc["is_mandatory"] is True
        assert doc["csc_assisted"] is True
        assert len(doc["issuer"]) > 0
        assert doc["is_collected"] is False
        for lang in ["en", "hi", "kn", "te"]:
            assert lang in doc["names"]
            assert len(doc["names"][lang].strip()) > 0
            assert lang in doc["descriptions"]
            assert len(doc["descriptions"][lang].strip()) > 0


def test_mandatory_vs_optional_distinction():
    """Verify that optional documents are distinguished from mandatory ones and never affect completion."""
    session_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/documents/checklist/pmay-g?session_id={session_id}")
    assert res.status_code == 200
    data = res.json()

    assert data["total_documents"] == 4
    assert data["mandatory_count"] == 3
    assert data["optional_count"] == 1

    optional_docs = [d for d in data["documents"] if not d["is_mandatory"]]
    assert len(optional_docs) == 1
    assert optional_docs[0]["id"] == "doc-pmg-swachh-toilet"

    # Marking the optional document alone does NOT trigger completion
    mark_opt = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pmay-g",
            "document_id": "doc-pmg-swachh-toilet",
            "is_collected": True,
        }
    )
    assert mark_opt.status_code == 200
    data_opt = mark_opt.json()
    assert data_opt["collected_count"] == 1
    assert data_opt["mandatory_collected_count"] == 0
    assert data_opt["is_complete"] is False

    # Marking all 3 mandatory documents completes the checklist, regardless of optional doc
    client.post("/api/v1/documents/checklist/mark", json={"session_id": session_id, "scheme_id": "pmay-g", "document_id": "doc-pmg-aadhaar", "is_collected": True})
    client.post("/api/v1/documents/checklist/mark", json={"session_id": session_id, "scheme_id": "pmay-g", "document_id": "doc-pmg-mgnrega", "is_collected": True})
    res_comp = client.post("/api/v1/documents/checklist/mark", json={"session_id": session_id, "scheme_id": "pmay-g", "document_id": "doc-pmg-bank", "is_collected": True})
    assert res_comp.status_code == 200
    assert res_comp.json()["is_complete"] is True

    # Clean up test session
    client.post("/api/v1/documents/checklist/reset", json={"session_id": session_id})


def test_get_checklist_via_schemes_route():
    """Verify that GET /api/v1/schemes/{scheme_id}/documents also returns the checklist."""
    res = client.get("/api/v1/schemes/pm-jay/documents")
    assert res.status_code == 200
    data = res.json()
    assert data["scheme_id"] == "pm-jay"
    assert len(data["documents"]) == 2


def test_checklist_scheme_not_found_404():
    """Verify that requesting a checklist for an unknown scheme returns HTTP 404."""
    res = client.get("/api/v1/documents/checklist/non-existent-scheme-999")
    assert res.status_code == 404
    data = res.json()
    assert data["error_code"] == "SCHEME_NOT_FOUND"


def test_mark_document_collection_flow():
    """Test session collection workflow with dynamic UUID: marking items, tracking progress, and completing."""
    session_id = str(uuid.uuid4())

    # Initial state (all uncollected)
    init_res = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={session_id}")
    assert init_res.status_code == 200
    assert init_res.json()["collected_count"] == 0
    assert init_res.json()["is_complete"] is False

    # Mark Aadhaar as collected
    res_step1 = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True,
        }
    )
    assert res_step1.status_code == 200
    data1 = res_step1.json()
    assert data1["collected_count"] == 1
    assert data1["mandatory_collected_count"] == 1
    assert data1["is_complete"] is False

    # Mark Land Record as collected
    res_step2 = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-land",
            "is_collected": True,
        }
    )
    assert res_step2.status_code == 200
    assert res_step2.json()["collected_count"] == 2
    assert res_step2.json()["is_complete"] is False

    # Mark Bank Passbook -> completes mandatory checklist!
    res_step3 = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-bank",
            "is_collected": True,
        }
    )
    assert res_step3.status_code == 200
    data3 = res_step3.json()
    assert data3["collected_count"] == 3
    assert data3["mandatory_collected_count"] == 3
    assert data3["is_complete"] is True

    # Unmark Land Record -> reverts is_complete to False
    res_unmark = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-land",
            "is_collected": False,
        }
    )
    assert res_unmark.status_code == 200
    data_unmark = res_unmark.json()
    assert data_unmark["collected_count"] == 2
    assert data_unmark["mandatory_collected_count"] == 2
    assert data_unmark["is_complete"] is False

    # Clean up test session
    client.post("/api/v1/documents/checklist/reset", json={"session_id": session_id})


def test_strict_pii_and_extra_fields_rejection():
    """Verify that sensitive PII fields (Aadhaar, PAN, bank account, phone, file) and extra unknown fields are rejected with HTTP 422 on BOTH mark and reset."""
    session_id = str(uuid.uuid4())
    prohibited_fields = ["aadhaar", "pan", "bank_account", "phone", "file"]

    # 1. Prohibited sensitive keys on mark endpoint
    for field_name in prohibited_fields:
        payload = {
            "session_id": session_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True,
            field_name: "fabricated_sensitive_val"
        }
        res = client.post("/api/v1/documents/checklist/mark", json=payload)
        assert res.status_code == 422, f"Expected 422 for field {field_name} on mark, got {res.status_code}"

    # 2. Unknown field on mark (extra='forbid')
    res_mark_unknown = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True,
            "custom_metadata_tag": "should_fail"
        }
    )
    assert res_mark_unknown.status_code == 422

    # 3. Prohibited sensitive keys on reset endpoint
    for field_name in prohibited_fields:
        payload = {
            "session_id": session_id,
            field_name: "fabricated_sensitive_val"
        }
        res = client.post("/api/v1/documents/checklist/reset", json=payload)
        assert res.status_code == 422, f"Expected 422 for field {field_name} on reset, got {res.status_code}"

    # 4. Unknown field on reset (extra='forbid')
    res_reset_unknown = client.post(
        "/api/v1/documents/checklist/reset",
        json={
            "session_id": session_id,
            "arbitrary_client_tag": "fail"
        }
    )
    assert res_reset_unknown.status_code == 422


def test_uuid_validation_enforcement():
    """Verify that non-UUID session IDs are rejected with HTTP 422 on all endpoints."""
    bad_session = "not-a-valid-uuid-123"

    # GET checklist with invalid UUID
    res_get = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={bad_session}")
    assert res_get.status_code == 422

    # POST mark with invalid UUID
    res_mark = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": bad_session,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True
        }
    )
    assert res_mark.status_code == 422

    # POST reset with invalid UUID
    res_reset = client.post(
        "/api/v1/documents/checklist/reset",
        json={"session_id": bad_session}
    )
    assert res_reset.status_code == 422


@pytest.mark.asyncio
async def test_session_expiry_ttl_and_cleanup():
    """Verify that expired records (> 2 hours old) are not counted as collected and are safely purged."""
    session_id = str(uuid.uuid4())
    scheme_id = "pm-kisan"
    doc_id = "doc-pmk-aadhaar"

    # Insert an expired record directly into DB (expires_at = 1 hour ago)
    now_utc = datetime.now(timezone.utc)
    expired_time = now_utc - timedelta(hours=1)

    async with async_session_factory() as session:
        item = EphemeralChecklistItem(
            session_id=session_id,
            scheme_id=scheme_id,
            document_id=doc_id,
            is_collected=True,
            updated_at=now_utc - timedelta(hours=3),
            expires_at=expired_time,
        )
        session.add(item)
        await session.commit()

    # Query checklist: expired record must NOT be counted as collected
    res = client.get(f"/api/v1/documents/checklist/{scheme_id}?session_id={session_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["collected_count"] == 0
    doc_item = next(d for d in data["documents"] if d["id"] == doc_id)
    assert doc_item["is_collected"] is False

    # Execute cleanup
    async with async_session_factory() as session:
        purged = await DocumentChecklistService.cleanup_expired_sessions(session)
        assert purged >= 1


def test_cross_session_isolation():
    """Verify that session A and session B do not leak or overwrite each other's checklist state."""
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())

    # Mark document in session A
    client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_a,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True
        }
    )

    # Session A sees collected_count = 1
    res_a = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={session_a}")
    assert res_a.json()["collected_count"] == 1

    # Session B sees collected_count = 0 (clean isolation)
    res_b = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={session_b}")
    assert res_b.json()["collected_count"] == 0

    # Cleanup
    client.post("/api/v1/documents/checklist/reset", json={"session_id": session_a})
    client.post("/api/v1/documents/checklist/reset", json={"session_id": session_b})


def test_mark_document_invalid_document_or_scheme_404():
    """Verify that attempting to mark an alien document or unknown scheme returns HTTP 404."""
    session_id = str(uuid.uuid4())

    # Unknown scheme
    res_bad_scheme = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "non-existent-scheme",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True,
        }
    )
    assert res_bad_scheme.status_code == 404

    # Document belongs to pm-kisan, but requested on pm-jay
    res_alien_doc = client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-jay",
            "document_id": "doc-pmk-land",
            "is_collected": True,
        }
    )
    assert res_alien_doc.status_code == 404
    assert res_alien_doc.json()["error_code"] == "DOCUMENT_NOT_FOUND"


def test_reset_session_checklist():
    """Verify that reset endpoint clears ephemeral checklist marks."""
    session_id = str(uuid.uuid4())

    # Mark an item
    client.post(
        "/api/v1/documents/checklist/mark",
        json={
            "session_id": session_id,
            "scheme_id": "pm-svanidhi",
            "document_id": "doc-pms-aadhaar",
            "is_collected": True,
        }
    )
    res_before = client.get(f"/api/v1/documents/checklist/pm-svanidhi?session_id={session_id}")
    assert res_before.json()["collected_count"] == 1

    # Reset
    res_reset = client.post(
        "/api/v1/documents/checklist/reset",
        json={"session_id": session_id}
    )
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "RESET_SUCCESSFUL"

    # Verify cleared
    res_after = client.get(f"/api/v1/documents/checklist/pm-svanidhi?session_id={session_id}")
    assert res_after.json()["collected_count"] == 0
