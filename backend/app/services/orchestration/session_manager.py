"""
Yojana Saathi - Ephemeral Session Profile Manager
Milestone 6.3: Ephemeral in-memory session management with 30-minute idle TTL.
Stores only allowlisted, validated attributes. Zero PII, zero transcript logging.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.schemas.orchestration import CitizenProfileAttributes, EphemeralSessionProfile

DEFAULT_SESSION_TTL_SECONDS = 1800  # 30 minutes


class SessionProfileManager:
    """
    Manages in-memory conversational sessions.
    Automatically purges expired sessions and guarantees strict attribute isolation.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS):
        self._sessions: Dict[str, EphemeralSessionProfile] = {}
        self.ttl_seconds = ttl_seconds

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def cleanup_expired_sessions(self) -> int:
        """Purges sessions inactive longer than the configured TTL. Returns purged count."""
        now = self._now()
        expired_ids = [
            sid
            for sid, profile in self._sessions.items()
            if (now - profile.last_active_at).total_seconds() > self.ttl_seconds
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)

    def get_session(self, session_id: str) -> Optional[EphemeralSessionProfile]:
        """Retrieves a session if it exists and has not expired."""
        self.cleanup_expired_sessions()
        session = self._sessions.get(session_id)
        if session:
            session.last_active_at = self._now()
        return session

    def get_or_create_session(
        self, session_id: Optional[str] = None, language: str = "en"
    ) -> EphemeralSessionProfile:
        """Retrieves an existing session or creates a fresh, empty profile."""
        self.cleanup_expired_sessions()

        if session_id and session_id in self._sessions:
            sess = self._sessions[session_id]
            sess.last_active_at = self._now()
            return sess

        new_id = session_id or str(uuid.uuid4())
        profile = EphemeralSessionProfile(
            session_id=new_id,
            attributes=CitizenProfileAttributes(),
            active_language=language,
            selected_scheme_id=None,
            created_at=self._now(),
            last_active_at=self._now(),
        )
        self._sessions[new_id] = profile
        return profile

    def update_attributes(
        self, session_id: str, new_attributes: Dict[str, Any]
    ) -> EphemeralSessionProfile:
        """
        Merges new validated attributes into the session profile.
        Overwrites existing values when corrected.
        """
        session = self.get_or_create_session(session_id)
        current_dict = session.attributes.model_dump(exclude_unset=False, exclude_none=True)
        current_dict.update(new_attributes)

        # Re-validate to ensure model integrity
        session.attributes = CitizenProfileAttributes(**current_dict)
        session.last_active_at = self._now()
        return session

    def set_scheme(self, session_id: str, scheme_id: Optional[str]) -> EphemeralSessionProfile:
        """Updates the actively focused scheme for the session."""
        session = self.get_or_create_session(session_id)
        session.selected_scheme_id = scheme_id
        session.last_active_at = self._now()
        return session

    def set_candidate_schemes(self, session_id: str, scheme_ids: List[str]) -> EphemeralSessionProfile:
        """Records recently discovered/evaluated candidate scheme IDs for ordinal reference resolution."""
        session = self.get_or_create_session(session_id)
        session.candidate_scheme_ids = list(scheme_ids)
        session.last_active_at = self._now()
        return session

    def set_language(self, session_id: str, language: str) -> EphemeralSessionProfile:
        """Updates the active language for the session."""
        session = self.get_or_create_session(session_id)
        session.active_language = language
        session.last_active_at = self._now()
        return session

    def _compact_turns(self, existing_summary: Optional[str], trimmed_turns: List[Dict[str, str]]) -> str:
        """
        Deterministically compacts trimmed dialogue turns into a concise running summary.
        Preserves core context, topics, and scheme mentions without PII.
        """
        summary_points: List[str] = []
        if existing_summary:
            summary_points.append(existing_summary.strip())

        for turn in trimmed_turns:
            role = turn.get("role", "user")
            content = turn.get("content", "").strip()
            if not content:
                continue
            # Keep a brief representative snippet (first ~120 chars)
            first_clause = content.split("\n")[0][:120].strip()
            if role == "user":
                summary_points.append(f"User asked/said: {first_clause}")
            else:
                summary_points.append(f"Assistant replied regarding: {first_clause}")

        # Retain latest 4 summary points up to 400 characters max
        recent_points = summary_points[-4:]
        compacted = " | ".join(recent_points)
        return compacted[:400]

    def append_turn(self, session_id: str, role: str, content: str, max_turns: int = 8) -> EphemeralSessionProfile:
        """
        Appends a PII-scrubbed turn to ephemeral in-memory history (never persisted).
        When history exceeds max_turns, earlier turns are compacted into conversation_summary.
        """
        session = self.get_or_create_session(session_id)
        clean_content = (content or "").strip()
        if clean_content:
            session.conversation_history.append({"role": role, "content": clean_content[:800]})
            if len(session.conversation_history) > max_turns:
                trimmed = session.conversation_history[:-max_turns]
                session.conversation_summary = self._compact_turns(session.conversation_summary, trimmed)
                session.conversation_history = session.conversation_history[-max_turns:]
        session.last_active_at = self._now()
        return session

    def record_correction(
        self, session_id: str, field: str, previous_value: Any, new_value: Any
    ) -> EphemeralSessionProfile:
        """Records a user-initiated profile attribute correction."""
        session = self.get_or_create_session(session_id)
        session.recent_corrections.append({
            "field": field,
            "previous_value": previous_value,
            "new_value": new_value,
            "timestamp": self._now().isoformat(),
        })
        # Keep only the last 5 corrections
        if len(session.recent_corrections) > 5:
            session.recent_corrections = session.recent_corrections[-5:]
        session.last_active_at = self._now()
        return session

    def set_pending_question(
        self,
        session_id: str,
        field: Optional[str] = None,
        scheme_id: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> EphemeralSessionProfile:
        """Records the pending clarification question for short follow-up continuity."""
        session = self.get_or_create_session(session_id)
        if field or prompt:
            session.pending_question = {
                "field": field,
                "scheme_id": scheme_id,
                "prompt": prompt,
            }
        else:
            session.pending_question = None
        session.last_active_at = self._now()
        return session

    def set_last_intent(self, session_id: str, intent: Optional[str]) -> EphemeralSessionProfile:
        """Records the last classified intent."""
        session = self.get_or_create_session(session_id)
        session.last_intent = intent
        session.last_active_at = self._now()
        return session

    def reset_profile(self, session_id: str) -> EphemeralSessionProfile:
        """Clears all accumulated profile attributes while preserving session ID and language."""
        session = self.get_or_create_session(session_id)
        session.attributes = CitizenProfileAttributes()
        session.selected_scheme_id = None
        session.candidate_scheme_ids = []
        session.conversation_history = []
        session.conversation_summary = None
        session.recent_corrections = []
        session.pending_question = None
        session.last_intent = None
        session.last_active_at = self._now()
        return session

    def delete_session(self, session_id: str) -> bool:
        """Explicitly deletes a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

