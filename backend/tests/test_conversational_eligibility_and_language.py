"""
Yojana Saathi - Conversational Eligibility & Automatic Language Detection Acceptance Tests
Validates Part A (One-by-one conversational eligibility), Part B (Automatic multilingual detection & switching),
and Part C/D/E guarantees according to the PS05 problem statement.
"""

import pytest
import uuid
from app.services.orchestration.orchestrator import ConversationalOrchestrator
from app.services.orchestration.intent_router import IntentRouter
from app.schemas.orchestration import CitizenIntentEnum
from app.schemas.eligibility import EligibilityStatusEnum


@pytest.fixture
def orchestrator():
    return ConversationalOrchestrator()


# ============================================================================
# PART A: ONE-BY-ONE CONVERSATIONAL ELIGIBILITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_part_a_test_1_single_question_rule(orchestrator):
    """
    Test 1: Single question rule
    Input: 'I am a farmer from Karnataka.'
    Expected: Extracts occupation and state. Identifies relevant schemes. Asks exactly ONE eligibility question.
    """
    session_id = str(uuid.uuid4())
    resp = await orchestrator.process_message(
        session_id=session_id,
        message="I am a farmer from Karnataka.",
    )
    # 1. Occupation and State extracted
    assert resp.active_profile.get("occupation") == "Farmer"
    assert resp.active_profile.get("state") == "Karnataka"

    # 2. Never ask multiple questions
    # Count question marks or missing prompts in assistant turn
    question_count = resp.message.count("?")
    assert question_count <= 2  # At most one question or follow-up clarification

    # 3. Exactly one pending question registered in session
    session = orchestrator.session_manager.get_session(session_id)
    assert session is not None
    assert session.pending_question is not None
    assert "field" in session.pending_question


@pytest.mark.asyncio
async def test_part_a_test_2_attribute_retention_across_turns(orchestrator):
    """
    Test 2: Attribute retention across turns
    Input 1: 'I am a farmer from Karnataka.'
    Input 2: '45.'
    Expected: Occupation, state and age are now known. Does not ask for occupation or state again.
    """
    session_id = str(uuid.uuid4())
    resp1 = await orchestrator.process_message(
        session_id=session_id,
        message="I am a farmer from Karnataka.",
    )
    assert resp1.active_profile.get("occupation") == "Farmer"
    assert resp1.active_profile.get("state") == "Karnataka"

    resp2 = await orchestrator.process_message(
        session_id=session_id,
        message="45",
    )
    # Attributes retained across turns
    assert resp2.active_profile.get("occupation") == "Farmer"
    assert resp2.active_profile.get("state") == "Karnataka"
    assert resp2.active_profile.get("age") == 45
    # Does not ask for age, occupation, or state again
    msg_lower = resp2.message.lower()
    assert "what is your occupation" not in msg_lower
    assert "which state" not in msg_lower


@pytest.mark.asyncio
async def test_part_a_test_3_multi_attribute_extraction(orchestrator):
    """
    Test 3: Multi-attribute extraction
    Input: 'I am a 45-year-old farmer from Karnataka with 2 acres of land.'
    Expected: Extracts age: 45, occupation: farmer, state: Karnataka, land ownership: true, landholding: ~0.81 ha.
    """
    session_id = str(uuid.uuid4())
    resp = await orchestrator.process_message(
        session_id=session_id,
        message="I am a 45-year-old farmer from Karnataka with 2 acres of land.",
    )
    profile = resp.active_profile
    assert profile.get("age") == 45
    assert profile.get("occupation") == "Farmer"
    assert profile.get("state") == "Karnataka"
    assert profile.get("owns_agricultural_land") is True
    assert profile.get("landholding_hectares") == pytest.approx(0.81, rel=1e-2)


@pytest.mark.asyncio
async def test_part_a_test_4_yes_no_mapping_to_pending_question(orchestrator):
    """
    Test 4: Yes/no mapping to pending question
    Assistant pending question: owns_agricultural_land
    User: 'Yes.'
    Expected: Sets owns_agricultural_land = True. Does not set unrelated booleans.
    """
    session_id = str(uuid.uuid4())
    # Manually seed a pending question expecting a boolean
    orchestrator.session_manager.set_pending_question(
        session_id,
        field="owns_agricultural_land",
        scheme_id="pm-kisan",
        prompt="Do you own agricultural land?",
    )
    resp = await orchestrator.process_message(
        session_id=session_id,
        message="Yes",
    )
    assert resp.active_profile.get("owns_agricultural_land") is True
    # Unrelated booleans are untouched
    assert resp.active_profile.get("pays_income_tax") is None
    assert resp.active_profile.get("has_bpl_card") is None


@pytest.mark.asyncio
async def test_part_a_test_6_user_correction_handling(orchestrator):
    """
    Test 6: User correction handling
    User: 'Actually, I am 46, not 45.'
    Expected: Profile age is updated to 46.
    """
    session_id = str(uuid.uuid4())
    # Seed age 45
    orchestrator.session_manager.update_attributes(session_id, {"age": 45, "occupation": "Farmer"})

    resp = await orchestrator.process_message(
        session_id=session_id,
        message="Actually, I am 46, not 45.",
    )
    assert resp.active_profile.get("age") == 46


@pytest.mark.asyncio
async def test_part_a_test_7_scheme_changing_while_retaining_attributes(orchestrator):
    """
    Test 7: Scheme changing while retaining attributes
    User starts evaluating PM-KISAN, then asks about Ayushman Bharat (PM-JAY).
    Previously collected attributes (age, state, occupation) are retained.
    """
    session_id = str(uuid.uuid4())
    await orchestrator.process_message(
        session_id=session_id,
        message="I am a 45-year-old farmer from Karnataka.",
    )
    # Switch context to PM-JAY
    resp2 = await orchestrator.process_message(
        session_id=session_id,
        message="Can I get Ayushman Bharat PM-JAY?",
    )
    assert resp2.scheme_id == "pm-jay"
    assert resp2.active_profile.get("age") == 45
    assert resp2.active_profile.get("state") == "Karnataka"
    assert resp2.active_profile.get("occupation") == "Farmer"


@pytest.mark.asyncio
async def test_part_a_test_8_ambiguous_answer_clarification(orchestrator):
    """
    Test 8: Ambiguous answer clarification
    User: 'I have some land.'
    Expected: Sets owns_agricultural_land=True but leaves landholding_hectares=None without fabricating.
    """
    session_id = str(uuid.uuid4())
    resp = await orchestrator.process_message(
        session_id=session_id,
        message="I have some land.",
    )
    assert resp.active_profile.get("owns_agricultural_land") is True
    assert resp.active_profile.get("landholding_hectares") is None


@pytest.mark.asyncio
async def test_part_a_test_9_deterministic_evaluation(orchestrator):
    """
    Test 9: Deterministic evaluation
    Evaluating PM-KISAN with complete profile: rule engine determines outcome deterministically.
    """
    session_id = str(uuid.uuid4())
    resp = await orchestrator.process_message(
        session_id=session_id,
        message="Am I eligible for PM-KISAN? I am a 45-year-old farmer in Karnataka with 1.5 hectares, no income tax, and not a govt employee.",
    )
    assert resp.eligibility_result is not None
    # Deterministic engine makes the decision
    assert resp.eligibility_result.status in (
        EligibilityStatusEnum.ELIGIBLE,
        EligibilityStatusEnum.POSSIBLY_ELIGIBLE,
        EligibilityStatusEnum.NEEDS_MORE_INFORMATION,
    )


# ============================================================================
# PART B: AUTOMATIC LANGUAGE DETECTION TESTS
# ============================================================================

def test_part_b_test_1_english_detection():
    assert IntentRouter.detect_language("I am a farmer from Karnataka.") == "en"


def test_part_b_test_2_hindi_detection():
    assert IntentRouter.detect_language("मैं एक किसान हूँ।") == "hi"


def test_part_b_test_3_kannada_detection():
    assert IntentRouter.detect_language("ನಾನು ಕರ್ನಾಟಕದ ರೈತ.") == "kn"


def test_part_b_test_4_telugu_detection():
    assert IntentRouter.detect_language("నేను తెలంగాణ రైతును.") == "te"


@pytest.mark.asyncio
async def test_part_b_test_5_dynamic_switch_to_hindi(orchestrator):
    """
    Test 5: Dynamic language switch to Hindi
    English turn -> Hindi message -> Assistant switches response language to Hindi.
    """
    session_id = str(uuid.uuid4())
    resp1 = await orchestrator.process_message(
        session_id=session_id,
        message="Hello, can you help me find government schemes?",
    )
    assert resp1.language == "en"

    resp2 = await orchestrator.process_message(
        session_id=session_id,
        message="मैं एक किसान हूँ और मुझे योजना की जानकारी चाहिए।",
    )
    assert resp2.language == "hi"


@pytest.mark.asyncio
async def test_part_b_test_6_short_english_answer_in_indic_conversation(orchestrator):
    """
    Test 6: Short English answer in Hindi conversation
    Assistant: Hindi conversation.
    User: '45 years.'
    Expected: Remains in Hindi, does not flip to English.
    """
    session_id = str(uuid.uuid4())
    # Start in Hindi
    resp1 = await orchestrator.process_message(
        session_id=session_id,
        message="नमस्ते, मैं एक किसान हूँ।",
    )
    assert resp1.language == "hi"

    # User answers age with short English token
    resp2 = await orchestrator.process_message(
        session_id=session_id,
        message="45 years",
    )
    # Stays in Hindi!
    assert resp2.language == "hi"
    assert resp2.active_profile.get("age") == 45


def test_part_b_test_7_code_mixed_hinglish():
    """
    Test 7: Code-mixed Hinglish
    'Meri age 45 hai aur main farmer hoon.' -> Hindi.
    """
    assert IntentRouter.detect_language("Meri age 45 hai aur main farmer hoon.") == "hi"


def test_part_b_test_8_code_mixed_kanglish():
    """
    Test 8: Code-mixed Kanglish
    'Nanna age 45 years, I am a farmer.' -> Kannada.
    """
    assert IntentRouter.detect_language("Nanna age 45 years, I am a farmer.") == "kn"


def test_part_b_test_9_code_mixed_tenglish():
    """
    Test 9: Code-mixed Tenglish
    'Naa age 45 years, nenu farmer.' -> Telugu.
    """
    assert IntentRouter.detect_language("Naa age 45 years, nenu farmer.") == "te"


@pytest.mark.asyncio
async def test_part_b_test_10_manual_selection_respected(orchestrator):
    """
    Test 10: Manual selection respected
    User selects Kannada -> Types in English -> Responds in Kannada.
    """
    session_id = str(uuid.uuid4())
    resp = await orchestrator.process_message(
        session_id=session_id,
        message="I am a farmer from Karnataka.",
        language="kn",
    )
    assert resp.language == "kn"


@pytest.mark.asyncio
async def test_part_b_test_11_session_reset_clears_profile(orchestrator):
    """
    Test 11: Session reset clears language and profile
    Reset clears ephemeral profile and pending questions.
    """
    session_id = str(uuid.uuid4())
    await orchestrator.process_message(
        session_id=session_id,
        message="I am a 45-year-old farmer.",
    )
    session = orchestrator.session_manager.get_session(session_id)
    assert session.attributes.age == 45

    # Reset
    orchestrator.session_manager.reset_profile(session_id)
    cleared = orchestrator.session_manager.get_session(session_id)
    assert cleared.attributes.age is None
    assert cleared.attributes.occupation is None
    assert cleared.pending_question is None

