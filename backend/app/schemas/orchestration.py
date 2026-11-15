"""
Yojana Saathi - Orchestration & Intent Schemas
Milestone 6.3: Typed contracts for intent routing, validated citizen profile slots,
session state, and synthesized multi-turn responses.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.eligibility import EligibilityStatusEnum
from app.schemas.rag import ProvenanceCitation


class CitizenIntentEnum(str, Enum):
    """Categorized citizen query intents."""
    SCHEME_DISCOVERY = "SCHEME_DISCOVERY"
    SCHEME_INFORMATION = "SCHEME_INFORMATION"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    DOCUMENT_REQUIREMENTS = "DOCUMENT_REQUIREMENTS"
    APPLICATION_GUIDANCE = "APPLICATION_GUIDANCE"
    GENERAL_HELP = "GENERAL_HELP"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"


class IntentClassificationResult(BaseModel):
    """Result of intent routing."""
    model_config = ConfigDict(from_attributes=True)

    intent: CitizenIntentEnum = Field(..., description="Classified intent")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    detected_scheme_id: Optional[str] = Field(None, description="Explicitly detected or mentioned scheme ID")
    detected_language: str = Field(default="en", description="Detected or requested language (en, hi, kn, te)")
    reasoning: str = Field(default="", description="Diagnostic justification for classification")


class CitizenProfileAttributes(BaseModel):
    """
    Validated allowlisted citizen demographic and socio-economic attributes.
    Strictly forbids arbitrary, unknown, or PII fields.
    """
    model_config = ConfigDict(extra="forbid")

    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years (0 to 120)")
    gender: Optional[str] = Field(None, description="Gender: Female, Male, Other")
    occupation: Optional[str] = Field(None, description="Primary occupation: Farmer, Street Vendor, Laborer, Other")
    state: Optional[str] = Field(None, description="Indian State or Union Territory")
    social_category: Optional[str] = Field(None, description="Caste / Social Category: General, OBC, SC, ST, EWS")
    owns_agricultural_land: Optional[bool] = Field(None, description="Whether citizen owns agricultural land")
    landholding_hectares: Optional[float] = Field(None, ge=0.0, description="Agricultural landholding size in hectares")
    annual_income_inr: Optional[float] = Field(None, ge=0.0, description="Annual household income in INR")
    has_bpl_card: Optional[bool] = Field(None, description="Active BPL / Ration Card holder")
    has_nfsa_priority_or_secc_entitlement: Optional[bool] = Field(None, description="NFSA Priority or SECC entitlement")
    household_monthly_income_inr: Optional[float] = Field(None, ge=0.0, description="Highest monthly income of household in INR")
    pays_income_tax: Optional[bool] = Field(None, description="Paid income tax in last assessment year")
    is_pregnant_or_lactating: Optional[bool] = Field(None, description="Currently pregnant or lactating mother")
    anc_checkups_completed: Optional[int] = Field(None, ge=0, description="Count of completed Antenatal Checkups")
    owns_motorized_three_or_four_wheeler: Optional[bool] = Field(None, description="Owns 3- or 4-wheeler motor vehicle")
    owns_unirrigated_land_gte_5_acres: Optional[bool] = Field(None, description="Owns 5 acres or more of unirrigated land")
    is_institutional_landholder: Optional[bool] = Field(None, description="Land registered under institution or trust")
    has_water_source_for_irrigation: Optional[bool] = Field(None, description="Reliable water source on farm")
    has_existing_grid_connected_agri_pump: Optional[bool] = Field(None, description="Has grid-connected electric pump")
    is_regular_govt_employee: Optional[bool] = Field(None, description="Regular government employee")
    has_regular_govt_job: Optional[bool] = Field(None, description="Household member has regular govt job")
    monthly_pension_inr: Optional[float] = Field(None, ge=0.0, description="Monthly pension amount in INR")
    is_registered_professional: Optional[bool] = Field(None, description="Practising registered professional")
    is_enrolled_in_other_pension_nps_esic_epfo: Optional[bool] = Field(None, description="Enrolled in NPS/ESIC/EPFO")
    is_enrolled_in_pm_sym_or_pm_lvm: Optional[bool] = Field(None, description="Enrolled in PM-SYM or PM-LVM")
    is_constitutional_post_holder_or_elected_representative: Optional[bool] = Field(None, description="Constitutional post holder")
    is_mts_or_class_iv_or_group_d_employee: Optional[bool] = Field(None, description="MTS/Class IV/Group D exception")
    receives_formal_paid_maternity_benefits: Optional[bool] = Field(None, description="Receives paid maternity leave")
    has_willful_bank_default: Optional[bool] = Field(None, description="Has willful default history")
    owns_pucca_house: Optional[bool] = Field(None, description="Owns pucca residential house")
    is_bank_defaulter: Optional[bool] = Field(None, description="Existing institutional bank credit default")
    is_tenant_farmer: Optional[bool] = Field(None, description="Cultivates land as tenant, oral lessee or sharecropper")
    is_allied_activity_worker: Optional[bool] = Field(None, description="Engaged in animal husbandry, dairy, poultry, or fisheries")
    is_shg_or_jlg_farmer: Optional[bool] = Field(None, description="Member of SHG or JLG farmer group")
    farmer_type: Optional[str] = Field(None, description="Farmer category: Landowner, Tenant, Sharecropper, Animal Husbandry, Fisheries, Other")
    kcc_activity_category: Optional[str] = Field(None, description="KCC agricultural/allied activity category")

    @field_validator("occupation", mode="before")
    @classmethod
    def normalize_occupation(cls, val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip().title()
        if any(w in s.lower() for w in ["farmer", "agri", "किसान", "ರೈತ", "రైతు"]):
            return "Farmer"
        if any(w in s.lower() for w in ["street vendor", "vendor", "hawker", "वेंडर", "ವ್ಯಾಪಾರಿ", "వ్యాపారి"]):
            return "Street Vendor"
        if any(w in s.lower() for w in ["labor", "labour", "मजदूर", "ಕೂಲಿ", "కూలీ"]):
            return "Laborer"
        return s

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip().title()
        if any(w in s.lower() for w in ["female", "woman", "महिला", "ಮಹಿಳೆ", "మహిళ"]):
            return "Female"
        if any(w in s.lower() for w in ["male", "man", "पुरुष", "ಪುರುಷ", "పురుషుడు"]):
            return "Male"
        return s


class ValidationResult(BaseModel):
    """Detailed result of attribute schema validation."""
    model_config = ConfigDict(from_attributes=True)

    is_valid: bool = Field(..., description="Whether all submitted attributes passed validation")
    validated_attributes: Dict[str, Any] = Field(default_factory=dict, description="Clean, validated attributes")
    rejected_fields: Dict[str, str] = Field(default_factory=dict, description="Fields rejected with reasons")
    ambiguities: List[str] = Field(default_factory=list, description="Ambiguous or conflicting statements noted")


class EphemeralSessionProfile(BaseModel):
    """In-memory session state for conversational multi-turn slot filling."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str = Field(..., description="Unique UUID session identifier")
    attributes: CitizenProfileAttributes = Field(default_factory=CitizenProfileAttributes, description="Accumulated profile attributes")
    active_language: str = Field(default="en", description="Citizen active language")
    selected_scheme_id: Optional[str] = Field(None, description="Currently focused scheme ID if any")
    candidate_scheme_ids: List[str] = Field(default_factory=list, description="Recent candidate schemes presented to user for ordinal references")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Ephemeral in-memory recent dialogue turns (PII-scrubbed, never persisted)")
    conversation_summary: Optional[str] = Field(None, description="Running compaction summary of older turns to preserve multi-turn context")
    recent_corrections: List[Dict[str, Any]] = Field(default_factory=list, description="Recent user corrections acknowledged")
    pending_question: Optional[Dict[str, Any]] = Field(None, description="Pending clarification question metadata (field, scheme_id, prompt)")
    last_intent: Optional[str] = Field(None, description="Previous turn intent for short follow-up continuity")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RequestDiagnostics(BaseModel):
    """PII-safe per-request runtime telemetry for observability."""
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    llm_provider: str
    llm_model: str
    actual_llm_inference: bool = False
    nlu_llm_success: bool = False
    synthesis_llm_success: bool = False
    stage_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    fallback_reason: Optional[str] = None
    detected_intent: str
    rag_chunks_retrieved: int = 0
    rag_scheme_ids: List[str] = Field(default_factory=list)
    eligibility_invoked: bool = False
    eligibility_outcomes: Dict[str, str] = Field(default_factory=dict)
    response_status: str = "ok"
    latency_ms: float = 0.0
    error_category: Optional[str] = None


class EligibilityOrchestrationResult(BaseModel):
    """Authoritative deterministic eligibility outcome with conversational context."""
    model_config = ConfigDict(from_attributes=True)

    scheme_id: str
    scheme_name: Dict[str, str]
    status: EligibilityStatusEnum
    summary: str
    satisfied_conditions: List[str] = Field(default_factory=list)
    failed_conditions: List[str] = Field(default_factory=list)
    missing_prompts: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    unresolved_notes: List[str] = Field(default_factory=list)
    citations: List[ProvenanceCitation] = Field(default_factory=list)
    is_clarification_needed: bool = False
    clarification_message: Optional[str] = None


class SynthesizedResponse(BaseModel):
    """Complete conversational response with citations, next steps, and profile summary."""
    model_config = ConfigDict(from_attributes=True)

    message: str = Field(..., description="Citizen-facing conversational answer in active language")
    intent: CitizenIntentEnum = Field(..., description="Processed query intent")
    language: str = Field(..., description="Response language (en, hi, kn, te)")
    scheme_id: Optional[str] = Field(None, description="Associated scheme ID if applicable")
    eligibility_result: Optional[EligibilityOrchestrationResult] = Field(None, description="Deterministic rule outcome if evaluated")
    candidate_evaluations: List[EligibilityOrchestrationResult] = Field(default_factory=list, description="Evaluated shortlist for discovery queries")
    scheme_buckets: Optional[Dict[str, List[str]]] = Field(default=None, description="Schemes grouped by eligible, needs_info, not_eligible")
    corrected_attributes: List[Dict[str, Any]] = Field(default_factory=list, description="Attributes updated in this turn via user correction")
    profile_conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="Explicit attribute conflicts requiring user confirmation")
    citations: List[ProvenanceCitation] = Field(default_factory=list, description="Official provenance citations")
    formatted_citations_markdown: str = Field(default="", description="Rendered markdown references block")
    suggested_followups: List[str] = Field(default_factory=list, description="Follow-up guidance or missing prompts")
    active_profile: Dict[str, Any] = Field(default_factory=dict, description="Active validated citizen profile attributes")
    diagnostics: Optional[RequestDiagnostics] = Field(None, description="PII-safe runtime observability metadata")

