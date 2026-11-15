"""
Yojana Saathi - Chat API Schemas
Milestone 6.4: Strict Pydantic contracts for conversational chat endpoints and SSE streaming.
"""

from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.orchestration import (
    CitizenIntentEnum,
    EligibilityOrchestrationResult,
    RequestDiagnostics,
)
from app.schemas.rag import ProvenanceCitation


class ChatRequest(BaseModel):
    """Citizen incoming chat request payload."""
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Citizen message or conversational query in en, hi, kn, or te"
    )
    language: str = Field(
        default="en",
        description="Active citizen language code (en, hi, kn, te)"
    )
    session_id: Optional[str] = Field(
        None,
        description="Ephemeral session identifier (UUIDv4); server generates if omitted"
    )
    scheme_id: Optional[str] = Field(
        None,
        description="Optional explicitly focused scheme identifier"
    )
    citizen_profile: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional active in-memory citizen profile attributes for context"
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Message cannot be empty or whitespace only")
        return clean

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        lang = v.strip().lower()
        if lang not in ["en", "hi", "kn", "te"]:
            return "en"
        return lang

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean_v = v.strip()
        if not clean_v:
            return None
        try:
            val = uuid.UUID(clean_v)
            if val.version != 4:
                raise ValueError("session_id must be a version 4 (random) UUID")
            return str(val)
        except ValueError:
            raise ValueError("session_id must be a valid UUIDv4 string")


class ChatResponse(BaseModel):
    """Complete conversational response payload."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(..., description="Active session UUID")
    message: str = Field(..., description="Citizen-facing conversational answer")
    intent: CitizenIntentEnum = Field(..., description="Processed query intent")
    language: str = Field(..., description="Response language (en, hi, kn, te)")
    scheme_id: Optional[str] = Field(None, description="Associated scheme ID if applicable")
    eligibility_result: Optional[EligibilityOrchestrationResult] = Field(None, description="Authoritative deterministic rule outcome")
    candidate_evaluations: List[EligibilityOrchestrationResult] = Field(default_factory=list, description="Evaluated shortlist for discovery queries")
    profile_conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="Explicit attribute conflicts requiring user confirmation")
    citations: List[ProvenanceCitation] = Field(default_factory=list, description="Official provenance citations")
    formatted_citations_markdown: str = Field(default="", description="Rendered markdown references block")
    suggested_followups: List[str] = Field(default_factory=list, description="Contextual follow-up suggestions")
    active_profile: Dict[str, Any] = Field(default_factory=dict, description="Active validated citizen profile attributes")
    diagnostics: Optional[RequestDiagnostics] = Field(None, description="PII-safe per-request diagnostic telemetry")


class ChatResetRequest(BaseModel):
    """Session reset request payload."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Session UUID to reset")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        clean_v = v.strip()
        try:
            val = uuid.UUID(clean_v)
            if val.version != 4:
                raise ValueError("session_id must be a version 4 (random) UUID")
            return str(val)
        except ValueError:
            raise ValueError("session_id must be a valid UUIDv4 string")


class ChatResetResponse(BaseModel):
    """Session reset outcome."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    status: str = "reset_successful"
    message: str = "Session profile cleared. New session ready."


class ChatTranslateRequest(BaseModel):
    """Request payload to translate an assistant message."""
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=5000, description="Message text to translate")
    target_language: str = Field(..., description="Target language code: en, hi, kn, te")
    source_language: Optional[str] = Field(None, description="Optional source language code")

    @field_validator("target_language")
    @classmethod
    def validate_target_lang(cls, v: str) -> str:
        lang = v.strip().lower()
        if lang not in ["en", "hi", "kn", "te"]:
            raise ValueError("target_language must be one of: en, hi, kn, te")
        return lang


class ChatTranslateResponse(BaseModel):
    """Translated message response."""
    model_config = ConfigDict(from_attributes=True)

    translated_text: str = Field(..., description="Translated text preserving formatting and terms")
    target_language: str
    source_language: Optional[str] = None
    cached: bool = False
    is_translated: bool = True

