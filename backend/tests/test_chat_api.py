"""
Yojana Saathi - Unit & Integration Tests for Milestone 6.4 Chat API
Tests POST /api/v1/chat and POST /api/v1/chat/stream across multilingual scenarios,
multi-turn session state, SSE event streaming, strict PII redaction, session isolation,
request bounds, and deterministic offline resilience.
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.eligibility import EligibilityStatusEnum
from app.schemas.orchestration import CitizenIntentEnum

client = TestClient(app)


# =====================================================================
# 1. Multilingual Chat Turn Tests
# =====================================================================

class TestMultilingualChatAPI:
    """Verifies chat turns in English, Hindi, Kannada, and Telugu."""

    @pytest.mark.parametrize(
        "message,language,expected_intent,expected_scheme",
        [
            # English
            ("Am I eligible for PM-KISAN? I am a farmer with 1.5 hectares of land.", "en", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan"),
            ("What documents are required for PM-JAY Ayushman Bharat?", "en", CitizenIntentEnum.DOCUMENT_REQUIREMENTS, "pm-jay"),
            ("How to apply for PM-SVANidhi vendor loan?", "en", CitizenIntentEnum.APPLICATION_GUIDANCE, "pm-svanidhi"),
            ("List all government schemes available", "en", CitizenIntentEnum.SCHEME_DISCOVERY, None),
            ("Hello, can you help me?", "en", CitizenIntentEnum.GENERAL_HELP, None),
            ("Who won the cricket match yesterday?", "en", CitizenIntentEnum.UNSUPPORTED_QUERY, None),

            # Hindi
            ("क्या मैं पीएम किसान योजना के लिए पात्र हूँ? मैं एक किसान हूँ।", "hi", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan"),
            ("आयुष्मान भारत के लिए कौन से दस्तावेज चाहिए?", "hi", CitizenIntentEnum.DOCUMENT_REQUIREMENTS, "pm-jay"),

            # Kannada
            ("ನಾನು ಪಿಎಂ ಕಿಸಾನ್ ಯೋಜನೆಗೆ ಅರ್ಹನೇ? ನಾನು 1.5 ಹೆಕ್ಟೇರ್ ಭೂಮಿ ಹೊಂದಿರುವ ರೈತ.", "kn", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan"),

            # Telugu
            ("నేను పీఎం కిసాన్ పథకానికి అర్హుడినా? నేను 1.5 హెక్టార్లు ఉన్న రైతును.", "te", CitizenIntentEnum.ELIGIBILITY_CHECK, "pm-kisan"),
        ],
    )
    def test_chat_multilingual_queries(
        self, message: str, language: str, expected_intent: CitizenIntentEnum, expected_scheme: str
    ):
        sess_id = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/chat",
            json={
                "message": message,
                "language": language,
                "session_id": sess_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sess_id
        assert data["language"] == language
        assert data["intent"] == expected_intent.value
        if expected_scheme:
            assert data["scheme_id"] == expected_scheme
        assert len(data["message"]) > 10


# =====================================================================
# 2. Multi-turn Session & Eligibility Verification
# =====================================================================

class TestMultiTurnSessionChat:
    """Verifies that accumulated demographic profile attributes persist across turns."""

    def test_multi_turn_conversation_flow(self):
        sess_id = str(uuid.uuid4())

        # Turn 1: Greeting
        resp1 = client.post(
            "/api/v1/chat",
            json={"message": "Hello!", "language": "en", "session_id": sess_id},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["intent"] == CitizenIntentEnum.GENERAL_HELP.value

        # Turn 2: Mention scheme & ask eligibility with initial attributes
        resp2 = client.post(
            "/api/v1/chat",
            json={
                "message": "Am I eligible for PM-KISAN? I am a farmer with 1.5 hectares of land.",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["intent"] == CitizenIntentEnum.ELIGIBILITY_CHECK.value
        assert data2["scheme_id"] == "pm-kisan"
        assert data2["active_profile"].get("occupation") == "Farmer"
        assert data2["active_profile"].get("landholding_hectares") == 1.5
        assert data2["eligibility_result"] is not None
        assert data2["eligibility_result"]["status"] == EligibilityStatusEnum.NEEDS_MORE_INFORMATION.value
        assert len(data2["eligibility_result"]["missing_prompts"]) > 0

        # Turn 3: Provide remaining exclusion criteria
        resp3 = client.post(
            "/api/v1/chat",
            json={
                "message": "I do not pay income tax, not a government employee, not a registered professional, not institutional land, and zero pension.",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert data3["eligibility_result"] is not None
        assert data3["eligibility_result"]["status"] == EligibilityStatusEnum.NOT_VERIFIED.value
        assert len(data3["eligibility_result"]["satisfied_conditions"]) > 0
        assert len(data3["eligibility_result"]["failed_conditions"]) == 0
        assert len(data3["eligibility_result"]["missing_prompts"]) == 0
        assert len(data3["citations"]) > 0

        # Turn 4: Reset session
        reset_resp = client.post(
            "/api/v1/chat/reset",
            json={"session_id": sess_id},
        )
        assert reset_resp.status_code == 200
        assert reset_resp.json()["status"] == "reset_successful"

        # Turn 5: Verify profile was cleared
        resp5 = client.post(
            "/api/v1/chat",
            json={"message": "Can I get PM-KISAN?", "language": "en", "session_id": sess_id},
        )
        assert resp5.status_code == 200
        data5 = resp5.json()
        # Missing prompts should be asked again since profile was cleared
        assert len(data5["eligibility_result"]["missing_prompts"]) > 0


# =====================================================================
# 3. Privacy, PII Redaction & Session Isolation Tests
# =====================================================================

class TestPrivacyAndSecurity:
    """Verifies that PII is redacted, never stored, and sessions are cryptographic islands."""

    def test_pii_redaction_before_processing(self):
        sess_id = str(uuid.uuid4())
        # Message with sensitive credentials and legitimate attributes
        sensitive_query = (
            "My Aadhaar is 2345 6789 0123, PAN is ABCDE1234F, mobile is 9876543210, "
            "and bank account is account 12345678901234. I am a 40 year old farmer with 2 hectares."
        )

        resp = client.post(
            "/api/v1/chat",
            json={"message": sensitive_query, "language": "en", "session_id": sess_id},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Legitimate attributes extracted
        assert data["active_profile"].get("age") == 40
        assert data["active_profile"].get("occupation") == "Farmer"
        assert data["active_profile"].get("landholding_hectares") == 2.0

        # Sensitive credentials strictly absent from active_profile
        profile_keys = list(data["active_profile"].keys())
        for prohibited in ["aadhaar", "pan", "phone", "bank", "account"]:
            assert not any(prohibited in k.lower() for k in profile_keys)

    def test_cryptographic_session_isolation(self):
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        # Session A: Farmer aged 35
        client.post(
            "/api/v1/chat",
            json={"message": "I am a 35 year old farmer.", "language": "en", "session_id": session_a},
        )

        # Session B: Street vendor aged 50
        client.post(
            "/api/v1/chat",
            json={"message": "I am a 50 year old street vendor.", "language": "en", "session_id": session_b},
        )

        # Query Session A
        resp_a = client.post(
            "/api/v1/chat",
            json={"message": "Hello again", "language": "en", "session_id": session_a},
        )
        assert resp_a.json()["active_profile"]["age"] == 35
        assert resp_a.json()["active_profile"]["occupation"] == "Farmer"

        # Query Session B
        resp_b = client.post(
            "/api/v1/chat",
            json={"message": "Hello again", "language": "en", "session_id": session_b},
        )
        assert resp_b.json()["active_profile"]["age"] == 50
        assert resp_b.json()["active_profile"]["occupation"] == "Street Vendor"

    def test_cross_session_reset_isolation(self):
        """Verifies resetting session B profile does not clear or alter session A profile."""
        session_a = str(uuid.uuid4())
        session_b = str(uuid.uuid4())

        # Establish attributes in Session A
        client.post(
            "/api/v1/chat",
            json={"message": "I am a 42 year old farmer with 2 hectares.", "language": "en", "session_id": session_a},
        )

        # Establish attributes in Session B
        client.post(
            "/api/v1/chat",
            json={"message": "I am a 28 year old street vendor.", "language": "en", "session_id": session_b},
        )

        # Reset Session B explicitly
        reset_resp = client.post(
            "/api/v1/chat/reset",
            json={"session_id": session_b},
        )
        assert reset_resp.status_code == 200
        assert reset_resp.json()["status"] == "reset_successful"

        # Verify Session B is empty
        query_b = client.post(
            "/api/v1/chat",
            json={"message": "Hello again", "language": "en", "session_id": session_b},
        )
        assert query_b.json()["active_profile"] == {}

        # Verify Session A is completely intact
        query_a = client.post(
            "/api/v1/chat",
            json={"message": "Hello again", "language": "en", "session_id": session_a},
        )
        assert query_a.json()["active_profile"]["age"] == 42
        assert query_a.json()["active_profile"]["occupation"] == "Farmer"
        assert query_a.json()["active_profile"]["landholding_hectares"] == 2.0

    def test_session_ttl_expiration_and_cleanup(self):
        """Verifies expired in-memory session profiles are purged and do not leak attributes."""
        from datetime import datetime, timezone, timedelta
        from app.api.v1.chat import get_orchestrator

        orchestrator = get_orchestrator()
        test_sid = str(uuid.uuid4())

        # Seed profile in manager
        orchestrator.session_manager.update_attributes(
            session_id=test_sid,
            new_attributes={"age": 55, "occupation": "Farmer"},
        )
        profile = orchestrator.session_manager.get_session(test_sid)
        assert profile is not None
        assert profile.attributes.age == 55

        # Manually backdate last_active_at past TTL (e.g. 35 minutes ago)
        profile.last_active_at = datetime.now(timezone.utc) - timedelta(minutes=35)

        # Calling get_session must purge it and return None
        expired = orchestrator.session_manager.get_session(test_sid)
        assert expired is None

        # Subsequent query with that session_id starts with a fresh empty profile
        resp = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "language": "en", "session_id": test_sid},
        )
        assert resp.json()["active_profile"] == {}


# =====================================================================
# 4. Request Validation & Bounds Tests
# =====================================================================

class TestRequestValidation:
    """Verifies strict Pydantic rejection of invalid inputs."""

    def test_invalid_uuid_session_id_rejected(self):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "session_id": "malformed-not-a-uuid"},
        )
        assert resp.status_code == 422

    def test_reset_malformed_uuid_rejected(self):
        resp = client.post(
            "/api/v1/chat/reset",
            json={"session_id": "invalid-uuid-token"},
        )
        assert resp.status_code == 422

    def test_non_uuidv4_session_id_rejected(self):
        """Ensures non-v4 UUIDs (e.g. UUIDv1) without cryptographic randomness are rejected."""
        u1 = uuid.uuid1()
        resp = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "session_id": str(u1)},
        )
        assert resp.status_code == 422
        resp_reset = client.post(
            "/api/v1/chat/reset",
            json={"session_id": str(u1)},
        )
        assert resp_reset.status_code == 422

    def test_empty_message_rejected(self):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "   "},
        )
        assert resp.status_code == 422

    def test_oversized_payload_rejected(self):
        oversized = "a" * 2001
        resp = client.post(
            "/api/v1/chat",
            json={"message": oversized},
        )
        assert resp.status_code == 422

    def test_unauthorized_extra_fields_rejected(self):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "unauthorized_admin_param": True},
        )
        assert resp.status_code == 422


# =====================================================================
# 5. Server-Sent Events (SSE) Streaming Tests
# =====================================================================

class TestSSEStreamingAPI:
    """Verifies incremental Server-Sent Events streaming on /api/v1/chat/stream."""

    def test_chat_stream_events_format(self):
        sess_id = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/chat/stream",
            json={
                "message": "Am I eligible for PM-KISAN? I am a farmer with 1.5 hectares of land.",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        body_text = resp.text
        events: list = []
        for block in body_text.strip().split("\n\n"):
            if not block.strip():
                continue
            lines = block.strip().split("\n")
            event_type = None
            data_val = None
            for line in lines:
                if line.startswith("event: "):
                    event_type = line[len("event: ") :].strip()
                elif line.startswith("data: "):
                    data_val = json.loads(line[len("data: ") :].strip())
            if event_type:
                events.append((event_type, data_val))

        # Check emitted event types
        event_types = [e[0] for e in events]
        assert "metadata" in event_types
        assert "token" in event_types
        assert "done" in event_types

        # Metadata payload checks
        metadata_event = next(e[1] for e in events if e[0] == "metadata")
        assert metadata_event["session_id"] == sess_id
        assert metadata_event["intent"] == CitizenIntentEnum.ELIGIBILITY_CHECK.value

        # Done event checks
        done_event = next(e[1] for e in events if e[0] == "done")
        assert done_event["complete"] is True

    def test_sse_citations_emitted_before_tokens(self):
        """Confirms citations are emitted before tokens so grounded sources precede streamed text."""
        sess_id = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/chat/stream",
            json={
                "message": "What documents are required for PM-JAY Ayushman Bharat?",
                "language": "en",
                "session_id": sess_id,
            },
        )
        assert resp.status_code == 200
        event_types = []
        for block in resp.text.strip().split("\n\n"):
            if not block.strip():
                continue
            for line in block.strip().split("\n"):
                if line.startswith("event: "):
                    event_types.append(line[len("event: ") :].strip())

        # Assert citations and metadata appear before the first token
        first_token_idx = event_types.index("token")
        if "citations" in event_types:
            citations_idx = event_types.index("citations")
            assert citations_idx < first_token_idx, "Citations must be emitted before first text token"


# =====================================================================
# 6. Non-Destructive PII Scrubber Unit Tests
# =====================================================================

class TestPIIScrubberDirect:
    """Verifies that scrub_pii redacts sensitive credentials while preserving legitimate numbers."""

    def test_scrub_pii_preserves_legitimate_scheme_numbers(self):
        from app.core.pii_scrubber import scrub_pii

        legitimate = (
            "I am 45 years old and have 1.5 hectares of land (about 3.7 acres). "
            "My annual income is ₹120000 and I receive ₹6,000 under PM-KISAN or ₹3,000 under PM-KMY."
        )
        scrubbed = scrub_pii(legitimate)
        assert scrubbed == legitimate
        assert "45" in scrubbed
        assert "1.5" in scrubbed
        assert "6,000" in scrubbed
        assert "3,000" in scrubbed

    def test_scrub_pii_redacts_credentials(self):
        from app.core.pii_scrubber import scrub_pii

        sensitive = (
            "Aadhaar: 2345 6789 0123, PAN: ABCDE1234F, Phone: +91 9876543210, "
            "bank account no 123456789012345, OTP is 123456."
        )
        scrubbed = scrub_pii(sensitive)
        assert "2345 6789 0123" not in scrubbed
        assert "[AADHAAR_REDACTED]" in scrubbed
        assert "ABCDE1234F" not in scrubbed
        assert "[PAN_REDACTED]" in scrubbed
        assert "9876543210" not in scrubbed
        assert "[PHONE_REDACTED]" in scrubbed
        assert "123456789012345" not in scrubbed
        assert "[BANK_ACCOUNT_REDACTED]" in scrubbed
        assert "123456" not in scrubbed
        assert "[SECRET_REDACTED]" in scrubbed


# =====================================================================
# 7. Offline & Fallback Resilience Tests
# =====================================================================

class TestOfflineAndFallbackResilience:
    """Verifies that the chat endpoints operate deterministically without network or external services."""

    def test_offline_deterministic_chat_completion(self):
        resp = client.post(
            "/api/v1/chat",
            json={
                "message": "Tell me about PM-KISAN Samman Nidhi",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scheme_id"] == "pm-kisan"
        assert "PM-KISAN" in data["message"] or "PM Kisan" in data["message"]
        assert len(data["citations"]) > 0
        assert data["formatted_citations_markdown"] != ""


# =====================================================================
# 8. Storage Hygiene and Privacy Verification Tests
# =====================================================================

class TestStorageHygieneAndPrivacy:
    """Verifies that frontend code does not persist raw chat messages or citizen profiles to browser storage."""

    def test_no_chat_or_profile_set_item_in_frontend(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        app_context = (root / "src" / "context" / "AppContext.tsx").read_text(encoding="utf-8")
        chat_api = (root / "src" / "services" / "chatApi.ts").read_text(encoding="utf-8")

        # Confirm no localStorage/sessionStorage setItem calls for chat messages
        assert "setItem('yojana_chat'" not in app_context
        assert 'setItem("yojana_chat"' not in app_context
        assert "setItem('yojana_chat'" not in chat_api
        assert 'setItem("yojana_chat"' not in chat_api

        # Confirm no localStorage/sessionStorage setItem calls for citizen profile
        assert "setItem('yojana_profile'" not in app_context
        assert 'setItem("yojana_profile"' not in app_context
        assert "setItem('yojana_profile'" not in chat_api
        assert 'setItem("yojana_profile"' not in chat_api

        # Confirm sessionStorage is used exclusively for the ephemeral session bearer token
        assert "SESSION_KEY = 'yojana_chat_session_id'" in chat_api
        assert "sessionStorage.setItem(SESSION_KEY, currentId)" in chat_api

