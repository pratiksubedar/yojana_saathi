"""
Regression tests for Multi-Turn Conversational Memory, Clarification Resolution,
Prompt Privacy Hardening, and Session Lifecycle Isolation.
"""

from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.pii_scrubber import mask_demographics_for_llm, scrub_pii
from app.schemas.orchestration import CitizenIntentEnum, EligibilityStatusEnum
from app.services.llm.base import LLMResponse, ProviderTypeEnum
from app.services.llm.gateway import LLMGateway
from app.services.orchestration.agent_intelligence import AgentIntelligenceService
from app.services.orchestration.orchestrator import (
    ConversationalOrchestrator,
    parse_boolean_response,
    resolve_ordinal_scheme,
)
from app.services.orchestration.session_manager import SessionProfileManager


# ==============================================================================
# TASK 1: YES/NO CLARIFICATION RESOLUTION & NATURAL LANGUAGE VARIATIONS
# ==============================================================================

def test_parse_boolean_response_multilingual():
    """Confirms affirmative and negative natural language parsing across all 4 supported languages."""
    # English variations
    assert parse_boolean_response("Yes") is True
    assert parse_boolean_response("yes, i do") is True
    assert parse_boolean_response("I do") is True
    assert parse_boolean_response("Yes, I am") is True
    assert parse_boolean_response("No") is False
    assert parse_boolean_response("no, i don't") is False
    assert parse_boolean_response("I don't") is False
    assert parse_boolean_response("no, i do not") is False

    # Hindi variations
    assert parse_boolean_response("हाँ") is True
    assert parse_boolean_response("जी हाँ") is True
    assert parse_boolean_response("haan ji") is True
    assert parse_boolean_response("नहीं") is False
    assert parse_boolean_response("जी नहीं") is False
    assert parse_boolean_response("nahi") is False

    # Kannada variations
    assert parse_boolean_response("ಹೌದು") is True
    assert parse_boolean_response("ಹೌದು ನಾನು") is True
    assert parse_boolean_response("ಇಲ್ಲ") is False
    assert parse_boolean_response("ಅಲ್ಲ") is False

    # Telugu variations
    assert parse_boolean_response("అవును") is True
    assert parse_boolean_response("కాదు") is False
    assert parse_boolean_response("లేదు") is False

    # Arbitrary non-boolean messages must NOT match
    assert parse_boolean_response("What about KCC scheme?") is None
    assert parse_boolean_response("I live in Tumakuru") is None
    assert parse_boolean_response("1.5 hectares") is None


@pytest.mark.asyncio
async def test_boolean_clarification_maps_to_target_field():
    """Confirms that when a boolean question is pending, 'No, I don't' maps to the target field."""
    orch = ConversationalOrchestrator()
    sid = "test-bool-clarify"

    # Turn 1: Ask about PM-KISAN with occupation=Farmer, land=1.5ha.
    # PM-KISAN rules will ask whether citizen pays income tax (pays_income_tax).
    r1 = await orch.process_message(
        session_id=sid,
        message="I am a farmer with 1.5 hectares land, check PM-KISAN",
    )
    assert r1.eligibility_result is not None
    # Verify pending question has field populated
    sess = orch.session_manager.get_session(sid)
    assert sess.pending_question is not None
    assert sess.pending_question.get("field") == "pays_income_tax"
    assert sess.pending_question.get("scheme_id") == "pm-kisan"

    # Turn 2: Citizen answers with a natural negative "No, I don't"
    r2 = await orch.process_message(
        session_id=sid,
        message="No, I don't",
    )
    # The negative answer must map to pays_income_tax=False
    assert r2.active_profile.get("pays_income_tax") is False
    assert r2.scheme_id == "pm-kisan"


@pytest.mark.asyncio
async def test_context_switch_clears_previous_pending_question():
    """Confirms that switching schemes clears any previous pending clarification question."""
    orch = ConversationalOrchestrator()
    sid = "test-context-switch"

    # Turn 1: PM-KISAN sets a pending question
    await orch.process_message(
        session_id=sid,
        message="I am a farmer with 1.5 hectares land, check PM-KISAN",
    )
    sess = orch.session_manager.get_session(sid)
    assert sess.pending_question is not None
    assert sess.pending_question.get("scheme_id") == "pm-kisan"

    # Turn 2: User switches to Ayushman Bharat
    r2 = await orch.process_message(
        session_id=sid,
        message="Now tell me about Ayushman Bharat PM-JAY",
    )
    sess = orch.session_manager.get_session(sid)
    # Previous PM-KISAN pending question must be cleared
    assert sess.selected_scheme_id == "pm-jay"
    assert sess.pending_question is None


# ==============================================================================
# TASK 2: PROFILE CONFLICT HANDLING
# ==============================================================================

@pytest.mark.asyncio
async def test_confirmed_profile_conflict_detection_and_notification():
    """Confirms that contradicting a confirmed profile attribute produces a polite conflict notice and preserves confirmed profile."""
    orch = ConversationalOrchestrator()
    sid = "test-conflict-check"

    # Confirmed profile has age=40
    confirmed = {"age": 40, "occupation": "Farmer"}

    resp = await orch.process_message(
        session_id=sid,
        message="I am actually 25 years old now, check PM-KISAN",
        citizen_profile=confirmed,
    )
    # Conflict detected
    assert len(resp.profile_conflicts) == 1
    conf = resp.profile_conflicts[0]
    assert conf["field"] == "age"
    assert conf["confirmed_value"] == 40
    assert conf["new_value"] == 25

    # Notice must be present in the returned message
    assert "40" in resp.message
    assert "25" in resp.message
    assert "update your profile" in resp.message.lower()

    # Confirmed profile was not silently overwritten
    sess = orch.session_manager.get_session(sid)
    assert sess.attributes.age != 25 or sess.attributes.age is None


@pytest.mark.asyncio
async def test_unconfirmed_attribute_updates_without_conflict():
    """Confirms that newer statements smoothly update unconfirmed conversational attributes."""
    orch = ConversationalOrchestrator()
    sid = "test-unconfirmed-update"

    # Turn 1: User says land is 1 hectare
    await orch.process_message(
        session_id=sid,
        message="I am a farmer with 1 hectare of land",
    )
    sess = orch.session_manager.get_session(sid)
    assert sess.attributes.landholding_hectares == 1.0

    # Turn 2: User corrects land to 2 hectares (not confirmed in UI)
    resp = await orch.process_message(
        session_id=sid,
        message="Actually my land is 2 hectares",
    )
    sess = orch.session_manager.get_session(sid)
    # Replaced smoothly without conflict
    assert sess.attributes.landholding_hectares == 2.0
    assert len(resp.profile_conflicts) == 0


# ==============================================================================
# TASK 3: GEMINI PROMPT PRIVACY HARDENING
# ==============================================================================

def test_mask_demographics_for_llm_preserves_structure_masks_values():
    """Verifies that sensitive demographic attributes are replaced with semantic tokens."""
    raw = "I am a 35 year old female farmer from Karnataka with an annual income of ₹1.5 lakh and 2 hectares of land."
    masked = mask_demographics_for_llm(raw)

    # Specific demographic values must NOT appear
    assert "35" not in masked
    assert "1.5 lakh" not in masked
    assert "Karnataka" not in masked
    assert "female" not in masked
    assert "farmer" not in masked
    assert "2 hectares" not in masked

    # Semantic tokens must be present
    assert "[AGE]" in masked
    assert "[OCCUPATION]" in masked
    assert "[LOCATION]" in masked
    assert "[INCOME]" in masked
    assert "[LANDHOLDING]" in masked
    assert "[GENDER]" in masked


@pytest.mark.asyncio
async def test_gemini_nlu_and_synthesis_prompts_have_zero_raw_demographics():
    """Inspects the exact prompt payloads constructed for Gemini to verify zero demographic leakage."""
    captured_prompts = []

    mock_gateway = MagicMock(spec=LLMGateway)
    mock_gateway.is_real_llm_configured.return_value = True
    mock_gateway.get_configured_provider_info.return_value = ("gemini", "gemini-3.5-flash-lite")

    async def fake_generate_text(prompt, system_prompt, **kwargs):
        captured_prompts.append({"prompt": prompt, "system_prompt": system_prompt})
        if "NLU router" in system_prompt:
            return LLMResponse(
                text='{"intent": "SCHEME_DISCOVERY", "target_scheme_ids": ["pm-kisan"], "is_comparison": false, "search_query": "PM-KISAN", "language": "en"}',
                provider=ProviderTypeEnum.GEMINI,
                model="gemini-3.5-flash-lite",
                latency_ms=15.0,
            )
        return LLMResponse(
            text="Based on verified government guidelines, you qualify for PM-KISAN.",
            provider=ProviderTypeEnum.GEMINI,
            model="gemini-3.5-flash-lite",
            latency_ms=25.0,
        )

    mock_gateway.generate_text = AsyncMock(side_effect=fake_generate_text)

    intel = AgentIntelligenceService(gateway=mock_gateway)
    orch = ConversationalOrchestrator(agent_intelligence=intel)

    # Process a message containing rich demographic details
    await orch.process_message(
        session_id="test-privacy-payload",
        message="I am a 45-year-old farmer from Karnataka with an annual income of ₹1.8 lakh and 3 hectares of land",
    )

    # Both NLU and Synthesis were called
    assert len(captured_prompts) >= 2
    nlu_prompt = captured_prompts[0]["prompt"]
    synthesis_prompt = captured_prompts[1]["prompt"]

    # Verify NLU prompt has NO raw demographics
    assert "45" not in nlu_prompt
    assert "1.8 lakh" not in nlu_prompt
    assert "Karnataka" not in nlu_prompt
    assert "3 hectares" not in nlu_prompt
    assert "[AGE]" in nlu_prompt or "[OCCUPATION]" in nlu_prompt

    # Verify Synthesis prompt has NO raw demographics
    assert "45" not in synthesis_prompt
    assert "1.8 lakh" not in synthesis_prompt
    assert "Karnataka" not in synthesis_prompt
    assert "3 hectares" not in synthesis_prompt


# ==============================================================================
# TASK 4: SCHEME CONTEXT & ORDINAL RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_a_scheme_reference_retention():
    """Scenario A: User asks about PM-KISAN, then 'Am I eligible for it?' -> PM-KISAN preserved."""
    orch = ConversationalOrchestrator()
    sid = "test-scen-a"

    # Turn 1: Explains PM-KISAN
    r1 = await orch.process_message(
        session_id=sid,
        message="Tell me about PM-KISAN.",
    )
    assert r1.scheme_id == "pm-kisan"

    # Turn 2: Pronoun reference without mentioning scheme
    r2 = await orch.process_message(
        session_id=sid,
        message="Am I eligible for it?",
    )
    assert r2.scheme_id == "pm-kisan"


@pytest.mark.asyncio
async def test_scenario_b_scheme_switch_and_subsequent_reference():
    """Scenario B: PM-KISAN -> Ayushman Bharat -> 'Am I eligible for it?' -> PM-JAY selected."""
    orch = ConversationalOrchestrator()
    sid = "test-scen-b"

    # Turn 1: PM-KISAN
    await orch.process_message(session_id=sid, message="Tell me about PM-KISAN.")
    # Turn 2: Switch to Ayushman Bharat
    await orch.process_message(session_id=sid, message="Now explain Ayushman Bharat.")
    # Turn 3: Pronoun follow-up
    r3 = await orch.process_message(session_id=sid, message="Am I eligible for it?")
    assert r3.scheme_id == "pm-jay"


@pytest.mark.asyncio
async def test_scenario_c_ordinal_scheme_resolution():
    """Scenario C: Assistant presents schemes -> User says 'Explain the second one' -> 2nd resolved."""
    orch = ConversationalOrchestrator()
    sid = "test-scen-c"

    # Turn 1: Discover farmer schemes
    r1 = await orch.process_message(
        session_id=sid,
        message="Show me schemes for farmers.",
    )
    sess = orch.session_manager.get_session(sid)
    assert len(sess.candidate_scheme_ids) >= 2
    second_candidate = sess.candidate_scheme_ids[1]

    # Turn 2: Ordinal query
    r2 = await orch.process_message(
        session_id=sid,
        message="Explain the second one.",
    )
    assert r2.scheme_id == second_candidate


@pytest.mark.asyncio
async def test_scenario_d_landholding_answer_associates_with_pending_scheme():
    """Scenario D: Assistant asks for landholding -> '1.5 hectares' -> associated with scheme, occupation preserved."""
    orch = ConversationalOrchestrator()
    sid = "test-scen-d"

    # Turn 1: Set farmer occupation and check PM-KISAN
    await orch.process_message(
        session_id=sid,
        message="I am a farmer, check PM-KISAN eligibility",
    )
    sess = orch.session_manager.get_session(sid)
    assert sess.attributes.occupation == "Farmer"

    # Turn 2: Give land size
    r2 = await orch.process_message(
        session_id=sid,
        message="1.5 hectares",
    )
    assert r2.active_profile.get("occupation") == "Farmer"
    assert r2.active_profile.get("landholding_hectares") == 1.5
    assert r2.scheme_id == "pm-kisan"


# ==============================================================================
# TASK 5: SESSION LIFECYCLE & MEMORY REGRESSION
# ==============================================================================

def test_session_isolation_between_uuids():
    """Confirms two distinct session UUIDs maintain strictly isolated profiles and histories."""
    sm = SessionProfileManager()
    s1 = sm.get_or_create_session("uuid-1111")
    s2 = sm.get_or_create_session("uuid-2222")

    sm.update_attributes("uuid-1111", {"age": 25, "occupation": "Farmer"})
    sm.append_turn("uuid-1111", "user", "Message from user 1")

    sm.update_attributes("uuid-2222", {"age": 55, "occupation": "Street Vendor"})
    sm.append_turn("uuid-2222", "user", "Message from user 2")

    sess1 = sm.get_session("uuid-1111")
    sess2 = sm.get_session("uuid-2222")

    assert sess1.attributes.age == 25
    assert sess1.attributes.occupation == "Farmer"
    assert len(sess1.conversation_history) == 1
    assert "user 1" in sess1.conversation_history[0]["content"]

    assert sess2.attributes.age == 55
    assert sess2.attributes.occupation == "Street Vendor"
    assert len(sess2.conversation_history) == 1
    assert "user 2" in sess2.conversation_history[0]["content"]


def test_session_expiry_ttl_clears_state():
    """Confirms sessions inactive longer than TTL are purged."""
    sm = SessionProfileManager(ttl_seconds=10)
    sess = sm.get_or_create_session("uuid-expiring")
    sm.update_attributes("uuid-expiring", {"age": 30})

    # Artificially age the session past 10 seconds
    sess.last_active_at = datetime.now(timezone.utc) - timedelta(seconds=15)

    # get_session triggers cleanup
    assert sm.get_session("uuid-expiring") is None
    assert "uuid-expiring" not in sm._sessions


def test_session_reset_profile_clears_all_ephemeral_data():
    """Confirms reset_profile clears attributes, history, candidate schemes, and pending question."""
    sm = SessionProfileManager()
    sid = "uuid-reset-test"
    sm.get_or_create_session(sid)
    sm.update_attributes(sid, {"age": 42})
    sm.set_scheme(sid, "pm-kisan")
    sm.set_candidate_schemes(sid, ["pm-kisan", "pm-kmy"])
    sm.append_turn(sid, "user", "Hello")
    sm.set_pending_question(sid, field="age", scheme_id="pm-kisan", prompt="Your age?")

    # Reset
    reset_sess = sm.reset_profile(sid)
    assert reset_sess.attributes.age is None
    assert reset_sess.selected_scheme_id is None
    assert reset_sess.candidate_scheme_ids == []
    assert reset_sess.conversation_history == []
    assert reset_sess.pending_question is None


def test_updating_one_attribute_preserves_unrelated_attributes():
    """Confirms updating one field does not erase other collected fields."""
    sm = SessionProfileManager()
    sid = "uuid-merge-test"
    sm.get_or_create_session(sid)

    sm.update_attributes(sid, {"age": 28, "gender": "Female"})
    sm.update_attributes(sid, {"occupation": "Farmer"})
    sm.update_attributes(sid, {"landholding_hectares": 2.5})

    sess = sm.get_session(sid)
    assert sess.attributes.age == 28
    assert sess.attributes.gender == "Female"
    assert sess.attributes.occupation == "Farmer"
    assert sess.attributes.landholding_hectares == 2.5
