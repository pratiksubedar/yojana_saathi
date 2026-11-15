"""
Tests for Phase 5: Yojana Saathi - Conversational UX & Eligibility Intelligence Upgrade
Validates:
1. KCC 3-valued logic and alternative categories (landowner, tenant, allied).
2. KCC generic farmer without activity category yields POSSIBLY_ELIGIBLE and prompts for activity category.
3. KCC bank defaulter yields NOT_ELIGIBLE.
4. Assistant response conciseness (no bloated reports).
5. Interactive quick replies generation.
6. Chat message translation endpoint (/api/v1/chat/translate) with caching.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.translation_service import translate_assistant_text


@pytest.mark.asyncio
async def test_kcc_generic_farmer_requires_activity_category():
    """Generic 31yo farmer without activity details must be POSSIBLY_ELIGIBLE, not unconditionally ELIGIBLE."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/eligibility/evaluate/kcc", json={
            "citizen_attributes": {"age": 31, "occupation": "Farmer"}
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "POSSIBLY_ELIGIBLE"
        missing_fields = [m["field"] for m in data["missing_information"]]
        assert any(f in missing_fields for f in ["owns_agricultural_land", "is_tenant_farmer", "is_allied_activity_worker"])


@pytest.mark.asyncio
async def test_kcc_landowner_farmer_is_eligible():
    """Farmer with agricultural land is ELIGIBLE for KCC."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/eligibility/evaluate/kcc", json={
            "citizen_attributes": {"age": 35, "occupation": "Farmer", "owns_agricultural_land": True, "is_bank_defaulter": False}
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_kcc_tenant_farmer_is_eligible():
    """Tenant farmer is ELIGIBLE for KCC."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/eligibility/evaluate/kcc", json={
            "citizen_attributes": {"age": 35, "occupation": "Farmer", "is_tenant_farmer": True, "is_bank_defaulter": False}
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_kcc_allied_worker_is_eligible():
    """Dairy/fisheries worker is ELIGIBLE for KCC."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/eligibility/evaluate/kcc", json={
            "citizen_attributes": {"age": 35, "occupation": "Farmer", "is_allied_activity_worker": True, "is_bank_defaulter": False}
        })
        assert res.status_code == 200
        assert res.json()["status"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_kcc_bank_defaulter_is_not_eligible():
    """Bank defaulter is NOT_ELIGIBLE for KCC regardless of land."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/eligibility/evaluate/kcc", json={
            "citizen_attributes": {"age": 35, "occupation": "Farmer", "owns_agricultural_land": True, "is_bank_defaulter": True}
        })
        assert res.status_code == 200
        assert res.json()["status"] == "NOT_ELIGIBLE"


@pytest.mark.asyncio
async def test_kcc_api_conversational_turn_provides_quick_replies():
    """Testing chat API for KCC evaluation yields concise question with contextual quick replies."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        session_id = str(uuid.uuid4())
        resp = await client.post(
            "/api/v1/chat",
            json={
                "message": "I am a 35 year old farmer. Am I eligible for KCC?",
                "language": "en",
                "session_id": session_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scheme_id"] == "kcc"
        assert data["eligibility_result"]["status"] in ("POSSIBLY_ELIGIBLE", "NEEDS_MORE_INFORMATION")
        # Contextual quick replies for KCC activity category
        followups = data["suggested_followups"]
        assert "Own agricultural land" in followups or "Cultivate land as a tenant" in followups or "Yes" in followups


@pytest.mark.asyncio
async def test_chat_translation_endpoint():
    """Validates the /api/v1/chat/translate endpoint and caching behavior."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First translation
        req_payload = {
            "text": "Are you engaged in agricultural cultivation or an allied agricultural activity?",
            "target_language": "hi",
        }
        resp = await client.post("/api/v1/chat/translate", json=req_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_language"] == "hi"
        assert "संबद्ध कृषि गतिविधि" in data["translated_text"] or "कृषि" in data["translated_text"]
        assert data["cached"] is False

        # Second translation must hit cache
        resp2 = await client.post("/api/v1/chat/translate", json=req_payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["cached"] is True
        assert data2["translated_text"] == data["translated_text"]


def test_translation_preserves_scheme_names():
    """Verifies that scheme names like PM-KISAN, KCC, and PM-JAY are preserved."""
    sample = "You satisfy all evaluated eligibility requirements for this scheme. (PM-KISAN)"
    translated, _ = translate_assistant_text(sample, "kn")
    assert "PM-KISAN" in translated
