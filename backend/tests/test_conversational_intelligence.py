"""
Yojana Saathi - Conversational Intelligence & Natural Query Regression Tests
Covers Tests A, B, C, D, E, G for open-ended discovery, PM-KISAN 20ha rules,
profile conflict resolution, missing land ownership, follow-up continuity, and
strict deterministic eligibility.
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.orchestration import CitizenIntentEnum
from app.services.orchestration.intent_router import IntentRouter


class TestNaturalIntentUnderstanding:
    def test_farmer_financial_support_classified_as_discovery(self):
        res = IntentRouter.classify("I'm a farmer. What financial support can I receive?", "en")
        assert res.intent == CitizenIntentEnum.SCHEME_DISCOVERY

    def test_open_ended_farmer_with_20ha_classified_as_discovery(self):
        res = IntentRouter.classify(
            "I'm a farmer of 25 years age and I have land. What if I have land of 20 hectares? Which schemes am I eligible for?",
            "en",
        )
        assert res.intent == CitizenIntentEnum.SCHEME_DISCOVERY

    def test_elderly_pension_query_classified_as_discovery(self):
        res = IntentRouter.classify("My mother is 65 and has no pension. What can she apply for?", "en")
        assert res.intent == CitizenIntentEnum.SCHEME_DISCOVERY

    def test_small_business_loan_classified_as_discovery(self):
        res = IntentRouter.classify("I want to start a small business. Are there any government loans?", "en")
        assert res.intent == CitizenIntentEnum.SCHEME_DISCOVERY

    def test_pm_kisan_documents_classified_correctly(self):
        res = IntentRouter.classify("What documents do I need to apply for PM-KISAN?", "en")
        assert res.intent == CitizenIntentEnum.DOCUMENT_REQUIREMENTS
        assert res.detected_scheme_id == "pm-kisan"

    def test_already_applied_status_classified_as_application_guidance(self):
        res = IntentRouter.classify("I have already applied. How do I check the application process?", "en")
        assert res.intent == CitizenIntentEnum.APPLICATION_GUIDANCE

    def test_women_in_karnataka_classified_as_discovery(self):
        res = IntentRouter.classify("What schemes are available for women in Karnataka?", "en")
        assert res.intent == CitizenIntentEnum.SCHEME_DISCOVERY

    def test_extended_scheme_aliases_detected(self):
        assert IntentRouter.detect_scheme_id("Tell me about Mudra loan") == "pm-mudra"
        assert IntentRouter.detect_scheme_id("What is PM Surya Ghar?") == "pm-surya-ghar"
        assert IntentRouter.detect_scheme_id("PM Vishwakarma artisan scheme") == "pm-vishwakarma"
        assert IntentRouter.detect_scheme_id("Ujjwala gas connection") == "pmuy"


@pytest.mark.asyncio
async def test_test_a_open_ended_discovery_with_20_hectares():
    """Test A: Open-ended farmer discovery extracts all attributes and evaluates candidate schemes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "message": "I'm a 25-year-old farmer in Karnataka with 20 hectares of land. Which schemes can I get?",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "SCHEME_DISCOVERY"
        assert data["active_profile"].get("age") == 25
        assert data["active_profile"].get("occupation") == "Farmer"
        assert data["active_profile"].get("landholding_hectares") == 20.0
        assert data["active_profile"].get("state") == "Karnataka"
        assert "which scheme would you like" not in data["message"].lower()
        assert len(data["candidate_evaluations"]) >= 2
        assert "pm-kisan" in data["message"].lower()


@pytest.mark.asyncio
async def test_test_b_pm_kisan_20_hectares_not_rejected_by_land_size():
    """Test B: 20 hectares alone must NOT reject a farmer from PM-KISAN."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "message": "I am a farmer and I own 20 hectares. Am I eligible for PM-KISAN?",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "ELIGIBILITY_CHECK"
        assert data["scheme_id"] == "pm-kisan"
        assert data["eligibility_result"]["status"] == "NEEDS_MORE_INFORMATION"
        assert len(data["eligibility_result"]["failed_conditions"]) == 0
        # Progressive clarification: asks 1 question at a time with contextual quick replies
        assert len(data["suggested_followups"]) >= 1


@pytest.mark.asyncio
async def test_test_c_conflicting_age_uses_explicit_and_asks_update():
    """Test C: Existing profile age 30 vs new message age 25 uses 25 and flags conflict."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "message": "I am a farmer of 25 years age. Am I eligible for PM-KISAN?",
                "language": "en",
                "session_id": str(uuid.uuid4()),
                "citizen_profile": {"age": 30, "occupation": "Farmer", "state": "Karnataka"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_profile"].get("age") == 25
        assert len(data["profile_conflicts"]) == 1
        assert data["profile_conflicts"][0]["field"] == "age"
        assert data["profile_conflicts"][0]["confirmed_value"] == 30
        assert data["profile_conflicts"][0]["new_value"] == 25
        assert "update your profile" in data["message"].lower()


@pytest.mark.asyncio
async def test_test_d_missing_land_ownership_not_assumed():
    """Test D: Farmer aged 25 without land info does not fabricate landholding."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat",
            json={
                "message": "I'm a farmer aged 25. Am I eligible for PM-KISAN?",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_profile"].get("landholding_hectares") is None
        assert data["eligibility_result"]["status"] == "NEEDS_MORE_INFORMATION"


@pytest.mark.asyncio
async def test_test_e_followup_continuity_and_scheme_switch():
    """Test E: Follow-up answers retain context and switching to PM-KUSUM evaluates independently."""
    transport = ASGITransport(app=app)
    sess_id = str(uuid.uuid4())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/chat",
            json={
                "message": "I am a 25 years old farmer with 2 hectares. Am I eligible for PM-KISAN?",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert r1.status_code == 200
        assert r1.json()["scheme_id"] == "pm-kisan"

        # Answer exclusion question
        r2 = await client.post(
            "/api/v1/chat",
            json={
                "message": "No, I do not pay income tax.",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert r2.status_code == 200
        assert r2.json()["active_profile"].get("pays_income_tax") is False
        assert r2.json()["active_profile"].get("age") == 25

        # Switch to PM-KUSUM
        r3 = await client.post(
            "/api/v1/chat",
            json={
                "message": "What about PM-KUSUM?",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["scheme_id"] == "pm-kusum"
        assert d3["active_profile"].get("age") == 25
        assert d3["active_profile"].get("landholding_hectares") == 2.0


@pytest.mark.asyncio
async def test_test_g_no_fabricated_eligibility_for_partial_rules():
    """Test G: Partial/incomplete criteria yield NOT_VERIFIED or NEEDS_MORE_INFORMATION, never fabricated ELIGIBLE."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/chat",
            json={
                "message": "Am I eligible for PM-KISAN? I am 38 years old farmer with 1.2 hectares.",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["eligibility_result"]["status"] in ["NEEDS_MORE_INFORMATION", "NOT_VERIFIED"]


@pytest.mark.asyncio
async def test_actors_misrecognition_not_rejected_as_unrelated_actor():
    """Query containing 'actors of land' must NOT trigger UNSUPPORTED_QUERY ('actor')."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/chat",
            json={
                "message": "I am a 38 years old farmer with 1.2 actors of land which welfare schemes can I get",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["intent"] == "SCHEME_DISCOVERY"
        assert d["active_profile"].get("age") == 38
        assert d["active_profile"].get("occupation") == "Farmer"
        assert d["active_profile"].get("owns_agricultural_land") is True
        assert len(d["candidate_evaluations"]) >= 1


@pytest.mark.asyncio
async def test_acres_and_lakh_income_extraction_in_discovery():
    """Imperfect Indian-English discovery queries extract acres->hectares and lakh annual income."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/chat",
            json={
                "message": "I have 2 acres of land, what schemes are available?",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert r1.status_code == 200
        assert r1.json()["intent"] == "SCHEME_DISCOVERY"
        assert r1.json()["active_profile"].get("landholding_hectares") == 0.81

        r2 = await client.post(
            "/api/v1/chat",
            json={
                "message": "I am 38 and earn 3 lakh annually. Which schemes can I apply for?",
                "language": "en",
                "session_id": str(uuid.uuid4()),
            },
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["intent"] == "SCHEME_DISCOVERY"
        assert d2["active_profile"].get("age") == 38
        assert d2["active_profile"].get("annual_income_inr") == 300000.0
