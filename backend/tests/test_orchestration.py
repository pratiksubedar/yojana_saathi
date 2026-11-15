"""
Yojana Saathi - Unit & Integration Tests for Milestone 6.3 Orchestration
Tests multilingual intent routing, strict typed slot extraction, ephemeral session management,
authoritative deterministic rule engine parity, RAG citations, and privacy guarantees.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.schemas.eligibility import EligibilityStatusEnum
from app.schemas.orchestration import (
    CitizenIntentEnum,
    CitizenProfileAttributes,
    ValidationResult,
)
from app.services.orchestration.attribute_extractor import AttributeExtractor
from app.services.orchestration.eligibility_orchestrator import EligibilityOrchestrator
from app.services.orchestration.intent_router import IntentRouter
from app.services.orchestration.orchestrator import ConversationalOrchestrator
from app.services.orchestration.response_synthesizer import ResponseSynthesizer
from app.services.orchestration.session_manager import SessionProfileManager
from app.services.rule_engine import DeterministicRuleEvaluator, FIELD_PROMPTS


# =====================================================================
# 1. Intent Routing Tests Across 4 Languages
# =====================================================================

class TestIntentRouting:
    """Tests multilingual intent classification and scheme target extraction."""

    @pytest.mark.parametrize(
        "query,expected_intent,expected_scheme,expected_lang",
        [
            # English
            ("Can I get PM-KISAN subsidy if I have 1.5 hectares?", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan", "en"),
            ("What documents are required for PM-JAY Ayushman Bharat?", CitizenIntentEnum.DOCUMENT_REQUIREMENTS, "pm-jay", "en"),
            ("How to apply for PM-SVANidhi vendor loan?", CitizenIntentEnum.APPLICATION_GUIDANCE, "pm-svanidhi", "en"),
            ("Tell me about PMAY-G rural housing scheme", CitizenIntentEnum.SCHEME_INFORMATION, "pmay-g", "en"),
            ("List all government schemes available", CitizenIntentEnum.SCHEME_DISCOVERY, None, "en"),
            ("Hello, can you help me?", CitizenIntentEnum.GENERAL_HELP, None, "en"),
            ("Who won the cricket ipl match yesterday?", CitizenIntentEnum.UNSUPPORTED_QUERY, None, "en"),
            ("What is the current bitcoin price?", CitizenIntentEnum.UNSUPPORTED_QUERY, None, "en"),

            # Hindi
            ("क्या मैं पीएम किसान योजना के लिए पात्र हूँ?", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan", "hi"),
            ("आयुष्मान भारत के लिए कौन से दस्तावेज चाहिए?", CitizenIntentEnum.DOCUMENT_REQUIREMENTS, "pm-jay", "hi"),
            ("पीएम स्वनिधि के लिए आवेदन कैसे करें?", CitizenIntentEnum.APPLICATION_GUIDANCE, "pm-svanidhi", "hi"),
            ("प्रधानमंत्री आवास योजना क्या है?", CitizenIntentEnum.SCHEME_INFORMATION, "pmay-g", "hi"),
            ("सभी सरकारी योजनाओं की सूची दिखाएं", CitizenIntentEnum.SCHEME_DISCOVERY, None, "hi"),
            ("नमस्ते, आप कौन हैं?", CitizenIntentEnum.GENERAL_HELP, None, "hi"),

            # Kannada
            ("ನಾನು ಪಿಎಂ ಕಿಸಾನ್ ಯೋಜನೆಗೆ ಅರ್ಹನೇ?", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan", "kn"),
            ("ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಯೋಜನೆಗೆ ಯಾವ ದಾಖಲೆಗಳು ಬೇಕು?", CitizenIntentEnum.DOCUMENT_REQUIREMENTS, "pm-jay", "kn"),
            ("ಸ್ವನಿಧಿ ಸಾಲಕ್ಕೆ ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು ಹೇಗೆ?", CitizenIntentEnum.APPLICATION_GUIDANCE, "pm-svanidhi", "kn"),
            ("ನಮಸ್ಕಾರ, ನನಗೆ ಸಹಾಯ ಬೇಕು", CitizenIntentEnum.GENERAL_HELP, None, "kn"),

            # Telugu
            ("నేను పీఎం కిసాన్ పథకానికి అర్హుడినా?", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan", "te"),
            ("ఆయుష్మాన్ భారత్ కోసం ఏ పత్రాలు అవసరం?", CitizenIntentEnum.DOCUMENT_REQUIREMENTS, "pm-jay", "te"),
            ("పీఎం స్వనిధికి ఎలా దరఖాస్తు చేయాలి?", CitizenIntentEnum.APPLICATION_GUIDANCE, "pm-svanidhi", "te"),
            ("నమస్కారం, సహాయం చేయండి", CitizenIntentEnum.GENERAL_HELP, None, "te"),
        ],
    )
    def test_multilingual_intent_classification(
        self, query: str, expected_intent: CitizenIntentEnum, expected_scheme: str, expected_lang: str
    ):
        result = IntentRouter.classify(query)
        assert result.intent == expected_intent
        assert result.detected_language == expected_lang
        if expected_scheme:
            assert result.detected_scheme_id == expected_scheme


# =====================================================================
# 2. Attribute Extraction, Validation & Privacy Tests
# =====================================================================

class TestAttributeExtraction:
    """Tests typed slot extraction, strict validation, and PII protection."""

    @pytest.mark.asyncio
    async def test_valid_attribute_extraction_and_normalization(self):
        extractor = AttributeExtractor()
        text = "I am a 35 year old farmer with 1.8 hectares of agricultural land and a BPL card."
        res: ValidationResult = await extractor.extract_and_validate(text)

        assert res.is_valid is True
        assert res.validated_attributes.get("age") == 35
        assert res.validated_attributes.get("occupation") == "Farmer"
        assert res.validated_attributes.get("landholding_hectares") == 1.8
        assert res.validated_attributes.get("has_bpl_card") is True

    @pytest.mark.asyncio
    async def test_rejection_of_out_of_bounds_values(self):
        extractor = AttributeExtractor()
        # Test direct Pydantic model bounds
        with pytest.raises(Exception):
            CitizenProfileAttributes(age=150)  # > 120

        with pytest.raises(Exception):
            CitizenProfileAttributes(landholding_hectares=-2.5)  # < 0

    @pytest.mark.asyncio
    async def test_rejection_of_unauthorized_fields(self):
        # CitizenProfileAttributes has extra="forbid"
        with pytest.raises(Exception):
            CitizenProfileAttributes(aadhaar_number="123456789012")

        with pytest.raises(Exception):
            CitizenProfileAttributes(credit_score=750)

    @pytest.mark.asyncio
    async def test_pii_discarding(self):
        extractor = AttributeExtractor()
        text = "My Aadhaar is 1234 5678 9012 and PAN is ABCDE1234F. I am 40 years old."
        res = await extractor.extract_and_validate(text)

        # Age is extracted
        assert res.validated_attributes.get("age") == 40
        # PII is not extracted into attributes
        assert "aadhaar" not in res.validated_attributes
        assert "pan" not in res.validated_attributes
        assert any("Aadhaar" in amb for amb in res.ambiguities)
        assert any("PAN" in amb for amb in res.ambiguities)

    @pytest.mark.asyncio
    async def test_multilingual_slot_extraction(self):
        extractor = AttributeExtractor()
        hi_text = "मेरी आयु 45 वर्ष है और मैं एक किसान हूँ"
        res = await extractor.extract_and_validate(hi_text, language="hi")
        assert res.validated_attributes.get("age") == 45
        assert res.validated_attributes.get("occupation") == "Farmer"


# =====================================================================
# 3. Multi-turn Session Profile Management Tests
# =====================================================================

class TestSessionManager:
    """Tests ephemeral session profile lifecycle, updates, and TTL purge."""

    def test_session_lifecycle_and_updates(self):
        mgr = SessionProfileManager(ttl_seconds=1800)
        session = mgr.get_or_create_session("sess-1", language="en")
        assert session.session_id == "sess-1"
        assert session.active_language == "en"

        # Update attributes
        mgr.update_attributes("sess-1", {"age": 28, "occupation": "Farmer"})
        sess_updated = mgr.get_session("sess-1")
        assert sess_updated.attributes.age == 28
        assert sess_updated.attributes.occupation == "Farmer"

        # Correction: update age to 30
        mgr.update_attributes("sess-1", {"age": 30})
        sess_corrected = mgr.get_session("sess-1")
        assert sess_corrected.attributes.age == 30
        assert sess_corrected.attributes.occupation == "Farmer"

        # Reset profile
        mgr.reset_profile("sess-1")
        sess_reset = mgr.get_session("sess-1")
        assert sess_reset.attributes.age is None
        assert sess_reset.attributes.occupation is None

    def test_session_expiry_purge(self):
        mgr = SessionProfileManager(ttl_seconds=60)
        mgr.get_or_create_session("sess-active")
        expired_sess = mgr.get_or_create_session("sess-expired")

        # Artificially age the expired session
        expired_sess.last_active_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        purged_count = mgr.cleanup_expired_sessions()
        assert purged_count == 1
        assert mgr.get_session("sess-expired") is None
        assert mgr.get_session("sess-active") is not None


# =====================================================================
# 4. Authoritative Rule Engine Parity & Orchestration Tests
# =====================================================================

class TestEligibilityOrchestrationParity:
    """Verifies that EligibilityOrchestrator yields exact parity with DeterministicRuleEvaluator."""

    @pytest.mark.asyncio
    async def test_pm_kisan_exact_parity_eligible(self):
        orchestrator = EligibilityOrchestrator()
        citizen_profile = {
            "occupation": "Farmer",
            "landholding_hectares": 1.5,
            "is_institutional_landholder": False,
            "pays_income_tax": False,
            "is_regular_govt_employee": False,
            "monthly_pension_inr": 0.0,
            "is_registered_professional": False,
        }

        scheme_data = await orchestrator.get_scheme_data("pm-kisan")
        assert scheme_data is not None

        # Direct rule engine call
        direct_eval = DeterministicRuleEvaluator.evaluate_scheme(
            scheme_id=scheme_data["id"],
            scheme_name=scheme_data["names"],
            rule_ast=scheme_data["rule_ast"],
            citizen_attributes=citizen_profile,
        )

        # Orchestrator call
        orch_eval = await orchestrator.evaluate(
            scheme_id="pm-kisan",
            citizen_profile=citizen_profile,
            language="en",
        )

        # Note: PM-KISAN has rule_completeness=PARTIAL (constitutional post holders requires official CSC verification)
        # Therefore, EligibilityOrchestrator maps POSSIBLY_ELIGIBLE with 0 missing fields to NOT_VERIFIED.
        assert orch_eval.status == EligibilityStatusEnum.NOT_VERIFIED
        assert len(orch_eval.failed_conditions) == len(direct_eval.conditions_failed) == 0
        assert len(orch_eval.missing_prompts) == len(direct_eval.missing_information) == 0
        assert len(orch_eval.unresolved_notes) > 0

    @pytest.mark.asyncio
    async def test_pm_kisan_not_eligible_due_to_tax(self):
        orchestrator = EligibilityOrchestrator()
        citizen_profile = {
            "occupation": "Farmer",
            "landholding_hectares": 1.5,
            "is_institutional_landholder": False,
            "pays_income_tax": True,  # Disqualifying exclusion
            "is_regular_govt_employee": False,
            "monthly_pension_inr": 0.0,
            "is_registered_professional": False,
        }

        orch_eval = await orchestrator.evaluate(
            scheme_id="pm-kisan",
            citizen_profile=citizen_profile,
            language="en",
        )

        assert orch_eval.status == EligibilityStatusEnum.NOT_ELIGIBLE
        assert len(orch_eval.failed_conditions) > 0

    @pytest.mark.asyncio
    async def test_missing_fields_generate_localized_prompts(self):
        orchestrator = EligibilityOrchestrator()
        # Incomplete profile (missing landholding, tax status, etc.)
        citizen_profile = {"occupation": "Farmer"}

        orch_eval = await orchestrator.evaluate(
            scheme_id="pm-kisan",
            citizen_profile=citizen_profile,
            language="hi",
        )

        assert orch_eval.status == EligibilityStatusEnum.NEEDS_MORE_INFORMATION
        assert len(orch_eval.missing_prompts) > 0
        # Check that Hindi prompts are provided from FIELD_PROMPTS
        assert any("हेक्टेयर" in p for p in orch_eval.missing_prompts)

    @pytest.mark.asyncio
    async def test_unspecified_scheme_requests_clarification(self):
        orchestrator = EligibilityOrchestrator()
        orch_eval = await orchestrator.evaluate(
            scheme_id=None,
            citizen_profile={"age": 30},
            language="en",
        )
        assert orch_eval.is_clarification_needed is True
        assert "Which scheme" in orch_eval.clarification_message


# =====================================================================
# 5. Full End-to-End Conversational Orchestration Tests
# =====================================================================

class TestConversationalOrchestrator:
    """Tests the full multi-turn conversational loop."""

    @pytest.mark.asyncio
    async def test_conversational_turn_sequence(self):
        orchestrator = ConversationalOrchestrator()
        session_id = "test-conv-001"

        # Turn 1: Greeting
        resp1 = await orchestrator.process_message(
            session_id=session_id,
            message="Hello, can you help me?",
            language="en",
        )
        assert resp1.intent == CitizenIntentEnum.GENERAL_HELP
        assert "Yojana Saathi" in resp1.message

        # Turn 2: Mention scheme & ask eligibility with initial attributes
        resp2 = await orchestrator.process_message(
            session_id=session_id,
            message="Am I eligible for PM-KISAN? I am a farmer with 1.5 hectares of land.",
            language="en",
        )
        assert resp2.intent == CitizenIntentEnum.ELIGIBILITY_CHECK
        assert resp2.scheme_id == "pm-kisan"
        assert resp2.active_profile.get("occupation") == "Farmer"
        assert resp2.active_profile.get("landholding_hectares") == 1.5
        # Status should be NEEDS_MORE_INFORMATION because income tax status is not yet answered
        assert resp2.eligibility_result.status == EligibilityStatusEnum.NEEDS_MORE_INFORMATION
        assert len(resp2.eligibility_result.missing_prompts) > 0

        # Turn 3: Answer all remaining exclusion fields
        resp3 = await orchestrator.process_message(
            session_id=session_id,
            message="I do not pay income tax, not a government employee, not a registered professional, not institutional land, and zero pension.",
            language="en",
        )
        assert resp3.intent == CitizenIntentEnum.ELIGIBILITY_CHECK
        assert resp3.active_profile.get("pays_income_tax") is False
        assert resp3.active_profile.get("is_regular_govt_employee") is False
        assert resp3.active_profile.get("is_registered_professional") is False
        assert resp3.active_profile.get("is_institutional_landholder") is False
        assert resp3.active_profile.get("monthly_pension_inr") == 0.0
        # Rules are PARTIAL so status is NOT_VERIFIED with zero failed conditions and unresolved notes
        assert resp3.eligibility_result.status == EligibilityStatusEnum.NOT_VERIFIED
        assert len(resp3.eligibility_result.satisfied_conditions) > 0
        assert len(resp3.eligibility_result.failed_conditions) == 0
        assert len(resp3.eligibility_result.missing_prompts) == 0
        assert len(resp3.eligibility_result.unresolved_notes) > 0
        assert len(resp3.citations) > 0

    @pytest.mark.asyncio
    async def test_unsupported_query_safeguard(self):
        orchestrator = ConversationalOrchestrator()
        resp = await orchestrator.process_message(
            session_id="test-unsupported",
            message="Can you give me the latest stock market share tips?",
            language="en",
        )
        assert resp.intent == CitizenIntentEnum.UNSUPPORTED_QUERY
        assert "exclusively in official Government of India welfare schemes" in resp.message
