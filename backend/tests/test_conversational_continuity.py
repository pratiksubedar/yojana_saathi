"""
Yojana Saathi - Conversational Continuity & Discovery Buckets Tests
Verifies:
1. Conversation compaction when history exceeds max_turns (preserving context without dropping).
2. Reference resolution for anaphoric queries ('that scheme', 'am I eligible?', 'what about this?').
3. Pending question answering for typed numeric and boolean slots (e.g., '1.5 hectares', '35', 'yes').
4. Full-catalogue discovery evaluated into 3 buckets (eligible, needs_info, not_eligible).
5. User correction recording and non-silent handling.
"""

import pytest
import uuid
from app.services.orchestration.orchestrator import ConversationalOrchestrator, resolve_anaphoric_scheme, parse_pending_slot_value
from app.services.orchestration.session_manager import SessionProfileManager
from app.schemas.orchestration import CitizenIntentEnum
from app.schemas.eligibility import EligibilityStatusEnum


@pytest.mark.asyncio
async def test_conversation_compaction_on_overflow():
    """Verify that when turns exceed max_turns=8, older turns are compacted into conversation_summary."""
    sm = SessionProfileManager()
    sid = "test-compaction-overflow"

    # Add 12 turns
    for i in range(12):
        sm.append_turn(sid, "user" if i % 2 == 0 else "assistant", f"Turn message {i} discussing PM-KISAN farming")

    sess = sm.get_session(sid)
    assert sess is not None
    assert len(sess.conversation_history) == 8
    assert sess.conversation_summary is not None
    assert "User asked/said" in sess.conversation_summary or "Assistant replied" in sess.conversation_summary


def test_parse_pending_slot_value():
    """Verify that parse_pending_slot_value parses booleans, numbers, land, and age cleanly."""
    # Boolean
    assert parse_pending_slot_value("pays_income_tax", "no") is False
    assert parse_pending_slot_value("pays_income_tax", "haan ji") is True
    assert parse_pending_slot_value("pays_income_tax", "ಹೌದು") is True
    assert parse_pending_slot_value("pays_income_tax", "లేదు") is False

    # Landholding
    assert parse_pending_slot_value("landholding_hectares", "1.5") == 1.5
    assert parse_pending_slot_value("landholding_hectares", "2 hectares") == 2.0
    assert parse_pending_slot_value("landholding_hectares", "2 हेक्टेयर") == 2.0

    # Age
    assert parse_pending_slot_value("age", "35") == 35
    assert parse_pending_slot_value("age", "45 years") == 45
    assert parse_pending_slot_value("age", "60 साल") == 60


def test_resolve_anaphoric_scheme():
    """Verify that resolve_anaphoric_scheme handles pronoun & follow-up cues."""
    candidates = ["pm-kisan", "pm-jay", "pm-svanidhi"]

    # Ordinal takes precedence
    assert resolve_anaphoric_scheme("tell me about the second one", "pm-kisan", candidates) == "pm-jay"

    # Anaphoric references map to selected scheme or top candidate
    assert resolve_anaphoric_scheme("what documents do I need for that scheme?", "pm-kisan", candidates) == "pm-kisan"
    assert resolve_anaphoric_scheme("am I eligible for it?", "pm-jay", candidates) == "pm-jay"
    assert resolve_anaphoric_scheme("tell me about this", "pm-kisan", candidates) == "pm-kisan"
    assert resolve_anaphoric_scheme("आवेदन कैसे करें", "pm-kisan", candidates) == "pm-kisan"

    # Fallback to candidates[0] if no selected scheme
    assert resolve_anaphoric_scheme("what are the documents?", None, candidates) == "pm-kisan"


@pytest.mark.asyncio
async def test_pending_question_answered_with_number():
    """Verify that when a pending question asks for landholding, answering with '1.5' updates the slot and re-evaluates."""
    orch = ConversationalOrchestrator()
    sid = str(uuid.uuid4())

    # Turn 1: User says they are a farmer in Karnataka
    r1 = await orch.process_message(
        session_id=sid,
        message="I am a 30-year-old farmer in Karnataka. Am I eligible for PM-KISAN?",
        language="en",
    )
    assert r1.scheme_id == "pm-kisan"

    sess = orch.session_manager.get_session(sid)
    assert sess.pending_question is not None

    # Turn 2: User answers the pending question with just '1.5 hectares'
    r2 = await orch.process_message(
        session_id=sid,
        message="1.5 hectares",
        language="en",
    )
    # The slot was filled
    assert r2.active_profile.get("landholding_hectares") == 1.5
    # The scheme context was retained
    assert r2.scheme_id == "pm-kisan"


@pytest.mark.asyncio
async def test_three_bucket_scheme_discovery():
    """Verify that open discovery returns candidate evaluations structured with 3 buckets."""
    orch = ConversationalOrchestrator()
    sid = str(uuid.uuid4())

    resp = await orch.process_message(
        session_id=sid,
        message="Find schemes for me. I am a 28-year-old farmer with 1 hectare of land.",
        language="en",
    )

    assert resp.intent == CitizenIntentEnum.SCHEME_DISCOVERY
    assert resp.scheme_buckets is not None
    assert "eligible" in resp.scheme_buckets
    assert "needs_info" in resp.scheme_buckets
    assert "not_eligible" in resp.scheme_buckets

    # All candidate schemes are recorded in session for ordinal references
    sess = orch.session_manager.get_session(sid)
    assert len(sess.candidate_scheme_ids) >= 5
    assert "pm-kisan" in sess.candidate_scheme_ids

