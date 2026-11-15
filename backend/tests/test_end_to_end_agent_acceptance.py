"""
End-to-End Acceptance & LLM Agent Intelligence Regression Tests (Tests A-H + LLM Grounding).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.orchestration import CitizenIntentEnum
from app.services.llm.base import LLMResponse, ProviderTypeEnum
from app.services.llm.gateway import LLMGateway
from app.services.orchestration.agent_intelligence import AgentIntelligenceService
from app.services.orchestration.orchestrator import ConversationalOrchestrator


@pytest.mark.asyncio
async def test_acceptance_a_farmer_20_hectares():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-a",
        message="I am a 25 year old farmer with 20 hectares of land. Which schemes am I eligible for?",
    )
    assert resp.intent == CitizenIntentEnum.SCHEME_DISCOVERY
    assert resp.active_profile.get("age") == 25
    assert resp.active_profile.get("occupation") == "Farmer"
    assert resp.active_profile.get("landholding_hectares") == 20.0
    assert any(ev.scheme_id == "pm-kisan" for ev in resp.candidate_evaluations)
    assert "01.06.2019" in resp.message or "more than 2 hectares" in resp.message.lower()
    assert resp.diagnostics is not None
    assert resp.diagnostics.eligibility_invoked is True


@pytest.mark.asyncio
async def test_acceptance_b_short_followup_income():
    orch = ConversationalOrchestrator()
    # Turn 1: ask about PM-JAY
    r1 = await orch.process_message(
        session_id="test-acc-b",
        message="Am I eligible for Ayushman Bharat PM-JAY?",
    )
    assert r1.scheme_id == "pm-jay"
    # Turn 2: short follow-up giving income in ₹ lakh
    r2 = await orch.process_message(
        session_id="test-acc-b",
        message="My annual household income is ₹2 lakh",
    )
    assert r2.active_profile.get("annual_income_inr") == 200000.0
    assert r2.scheme_id == "pm-jay"


@pytest.mark.asyncio
async def test_acceptance_c_hindi_street_vendor():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-c",
        message="मैं 32 साल की महिला हूँ और स्ट्रीट वेंडर हूँ, मुझे कौन सी योजना मिल सकती है?",
    )
    assert resp.language == "hi"
    assert resp.active_profile.get("occupation") == "Street Vendor"
    assert resp.active_profile.get("gender") == "Female"
    assert "pm-svanidhi" in resp.diagnostics.rag_scheme_ids or resp.scheme_id == "pm-svanidhi"


@pytest.mark.asyncio
async def test_acceptance_d_kannada_farmer_pension():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-d",
        message="ನಾನು 65 ವರ್ಷದ ರೈತ, ನನಗೆ ಪಿಂಚಣಿ ಯೋಜನೆ ಸಿಗುತ್ತದೆಯೇ?",
    )
    assert resp.language == "kn"
    assert resp.active_profile.get("occupation") == "Farmer"


@pytest.mark.asyncio
async def test_acceptance_e_telugu_pregnant_woman():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-e",
        message="నేను గర్భిణీ మహిళను, నాకు ప్రభుత్వ సహాయం ఏమిటి?",
    )
    assert resp.language == "te"
    assert resp.active_profile.get("is_pregnant_or_lactating") is True


@pytest.mark.asyncio
async def test_acceptance_f_compare_pmkisan_and_pmkmy():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-f",
        message="Compare PM-KISAN and PM-KMY",
    )
    assert "pm-kisan" in resp.diagnostics.rag_scheme_ids
    assert "pm-kmy" in resp.diagnostics.rag_scheme_ids
    assert len(resp.citations) >= 2


@pytest.mark.asyncio
async def test_acceptance_g_profile_conflict():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-g",
        message="I am 25 years old, check PM-KISAN eligibility",
        citizen_profile={"age": 40, "occupation": "Farmer"},
    )
    assert len(resp.profile_conflicts) == 1
    assert resp.profile_conflicts[0]["field"] == "age"
    assert resp.profile_conflicts[0]["confirmed_value"] == 40
    assert resp.profile_conflicts[0]["new_value"] == 25


@pytest.mark.asyncio
async def test_acceptance_h_unknown_local_phone_number():
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-acc-h",
        message="What is the exact district office phone number for PM-KISAN grievance redressal in Tumakuru?",
    )
    msg_lower = resp.message.lower()
    assert "could not find" in msg_lower or "not available" in msg_lower
    assert "official" in msg_lower


@pytest.mark.asyncio
async def test_real_llm_nlu_and_grounded_synthesis_path():
    """Verifies that when a real LLM provider is configured, NLU & synthesis use it and track actual_llm_inference=True."""
    mock_primary = MagicMock()
    mock_primary.provider_type = ProviderTypeEnum.GEMINI
    mock_primary.model_name = "gemini-2.5-flash"

    gateway = LLMGateway(primary_provider=mock_primary)
    gateway.generate_text = AsyncMock(
        side_effect=[
            LLMResponse(
                text='{"intent": "ELIGIBILITY_CHECK", "target_scheme_ids": ["pm-kisan"], "is_comparison": false, "search_query": "PM-KISAN eligibility", "language": "en"}',
                provider=ProviderTypeEnum.GEMINI,
                model="gemini-2.5-flash",
                latency_ms=42.0,
                fallback_chain=["gemini (ok)"],
            ),
            LLMResponse(
                text="Based on the deterministic rule check, we still need a few details to confirm your PM-KISAN eligibility. Do you pay income tax?",
                provider=ProviderTypeEnum.GEMINI,
                model="gemini-2.5-flash",
                latency_ms=85.0,
                fallback_chain=["gemini (ok)"],
            ),
        ]
    )

    intel = AgentIntelligenceService(gateway=gateway)
    orch = ConversationalOrchestrator(agent_intelligence=intel)
    resp = await orch.process_message(
        session_id="test-llm-real",
        message="I am a farmer, can I get PM-KISAN?",
    )
    assert resp.diagnostics.actual_llm_inference is True
    assert resp.diagnostics.llm_provider == "gemini"
    assert resp.diagnostics.llm_model == "gemini-2.5-flash"
    assert "income tax" in resp.message.lower()
    assert resp.eligibility_result is not None
    assert resp.eligibility_result.scheme_id == "pm-kisan"
    assert resp.diagnostics.nlu_llm_success is True
    assert resp.diagnostics.synthesis_llm_success is True
    assert "nlu" in resp.diagnostics.stage_latencies_ms
    assert "attribute_extraction" in resp.diagnostics.stage_latencies_ms
    assert "synthesis" in resp.diagnostics.stage_latencies_ms


@pytest.mark.asyncio
async def test_groq_nlu_and_grounded_synthesis_path():
    """Verifies that when Groq is configured, NLU & synthesis use it and track actual_llm_inference=True and llm_provider='groq'."""
    mock_primary = MagicMock()
    mock_primary.provider_type = ProviderTypeEnum.GROQ
    mock_primary.model_name = "llama-3.3-70b-versatile"

    gateway = LLMGateway(primary_provider=mock_primary)
    gateway.generate_text = AsyncMock(
        side_effect=[
            LLMResponse(
                text='{"intent": "ELIGIBILITY_CHECK", "target_scheme_ids": ["pm-kisan"], "is_comparison": false, "search_query": "PM-KISAN eligibility", "language": "en"}',
                provider=ProviderTypeEnum.GROQ,
                model="llama-3.3-70b-versatile",
                latency_ms=30.0,
                fallback_chain=["groq (ok)"],
            ),
            LLMResponse(
                text="Based on the deterministic rule check, we still need a few details to confirm your PM-KISAN eligibility. Do you pay income tax?",
                provider=ProviderTypeEnum.GROQ,
                model="llama-3.3-70b-versatile",
                latency_ms=65.0,
                fallback_chain=["groq (ok)"],
            ),
        ]
    )

    intel = AgentIntelligenceService(gateway=gateway)
    orch = ConversationalOrchestrator(agent_intelligence=intel)
    resp = await orch.process_message(
        session_id="test-groq-real",
        message="I am a farmer, can I get PM-KISAN?",
    )
    assert resp.diagnostics.actual_llm_inference is True
    assert resp.diagnostics.llm_provider == "groq"
    assert resp.diagnostics.llm_model == "llama-3.3-70b-versatile"
    assert "income tax" in resp.message.lower()
    assert resp.eligibility_result is not None
    assert resp.eligibility_result.scheme_id == "pm-kisan"
    assert resp.diagnostics.nlu_llm_success is True
    assert resp.diagnostics.synthesis_llm_success is True


@pytest.mark.asyncio
async def test_attribute_extractor_zero_external_gemini_calls():
    """Verifies that AttributeExtractor performs 100% local deterministic extraction with zero LLM gateway calls."""
    mock_gateway = MagicMock(spec=LLMGateway)
    mock_gateway.generate_text = AsyncMock()
    mock_gateway.extract_slots = AsyncMock()

    from app.services.orchestration.attribute_extractor import AttributeExtractor
    extractor = AttributeExtractor(gateway=mock_gateway)

    result = await extractor.extract_and_validate(
        text="I am a 34 year old female farmer in Karnataka with 1.5 hectares of land",
        current_profile={},
        language="en",
    )

    # Must NOT call the LLM gateway for slot extraction
    mock_gateway.generate_text.assert_not_called()
    mock_gateway.extract_slots.assert_not_called()

    # Attributes extracted correctly and deterministically
    assert result.validated_attributes.get("age") == 34
    assert result.validated_attributes.get("gender") == "Female"
    assert result.validated_attributes.get("occupation") == "Farmer"
    assert result.validated_attributes.get("state") == "Karnataka"
    assert result.validated_attributes.get("landholding_hectares") == 1.5


@pytest.mark.asyncio
async def test_gemini_timeout_and_429_quota_deterministic_fallback():
    """Verifies that when Gemini times out or throws 429 quota exhaustion, it falls back to deterministic safely with actual_llm_inference=False."""
    mock_primary = MagicMock()
    mock_primary.provider_type = ProviderTypeEnum.GEMINI
    mock_primary.model_name = "gemini-3.5-flash-lite"

    gateway = LLMGateway(primary_provider=mock_primary)
    gateway.generate_text = AsyncMock(
        side_effect=Exception("HTTP 429: Resource has been exhausted (e.g. check quota)")
    )

    intel = AgentIntelligenceService(gateway=gateway)
    orch = ConversationalOrchestrator(agent_intelligence=intel)

    resp = await orch.process_message(
        session_id="test-quota-fallback",
        message="I am a 30 year old farmer with 1 hectare land, check PM-KISAN",
    )

    # Must gracefully fall back to deterministic rules engine
    assert resp.diagnostics.actual_llm_inference is False
    assert resp.diagnostics.llm_provider == "deterministic"
    assert resp.diagnostics.response_status == "fallback"
    assert resp.diagnostics.nlu_llm_success is False
    assert resp.diagnostics.synthesis_llm_success is False
    # Eligibility result MUST still be evaluated authoritatively by Python
    assert resp.eligibility_result is not None
    assert resp.eligibility_result.scheme_id == "pm-kisan"


@pytest.mark.asyncio
async def test_missing_info_triggers_clarification_no_invented_eligibility():
    """Verifies that missing information triggers clarification rather than invented eligibility conclusions."""
    orch = ConversationalOrchestrator()
    resp = await orch.process_message(
        session_id="test-missing-clarification",
        message="Am I eligible for PM-KISAN?",
    )
    # Without land ownership or farmer status, it must request clarification
    assert resp.eligibility_result is not None
    assert resp.eligibility_result.status.value == "NEEDS_MORE_INFORMATION"
    assert len(resp.eligibility_result.missing_prompts) > 0
    assert resp.diagnostics.eligibility_outcomes.get("pm-kisan") == "NEEDS_MORE_INFORMATION"
    assert any("occupation" in p.lower() or "landholding" in p.lower() for p in resp.eligibility_result.missing_prompts)


