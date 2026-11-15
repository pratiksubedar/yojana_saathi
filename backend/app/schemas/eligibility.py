from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EligibilityStatusEnum(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    NEEDS_MORE_INFORMATION = "NEEDS_MORE_INFORMATION"
    NOT_VERIFIED = "NOT_VERIFIED"
    POSSIBLY_ELIGIBLE = "POSSIBLY_ELIGIBLE"


class RuleCompletenessEnum(str, Enum):
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"


class ConditionStatusEnum(str, Enum):
    SATISFIED = "SATISFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class EvaluatedCondition(BaseModel):
    model_config = ConfigDict(extra="ignore")

    condition_id: str = Field(..., description="Condition identifier from rule AST")
    field: str = Field(..., description="Evaluated citizen attribute name")
    operator: str = Field(..., description="Comparison operator used")
    target_value: Any = Field(..., description="Target threshold or allowed values")
    citizen_value: Any = Field(None, description="Actual value provided by citizen, or None if missing")
    status: ConditionStatusEnum = Field(..., description="SATISFIED, FAILED, or UNKNOWN")
    reason: Dict[str, str] = Field(default_factory=dict, description="Multilingual rationale or failure explanation")
    citation: Optional[Dict[str, Any]] = Field(None, description="Official clause citation backing this condition")


class MissingFieldInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field: str = Field(..., description="Missing attribute key name")
    prompt: Dict[str, str] = Field(..., description="Multilingual conversational question asking for this field")
    expected_type: str = Field(..., description="Data type: boolean, number, string, select")
    citation: Optional[Dict[str, Any]] = Field(None, description="Clause reference requiring this attribute")


class SchemeEligibilityResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scheme_id: str = Field(..., description="Evaluated scheme identifier")
    scheme_name: Dict[str, str] = Field(..., description="Multilingual scheme titles (en, hi, kn, te)")
    status: EligibilityStatusEnum = Field(..., description="Final 3-state eligibility outcome")
    rule_completeness: RuleCompletenessEnum = Field(
        default=RuleCompletenessEnum.PARTIAL,
        description="Completeness tier of encoded rules: VERIFIED_COMPLETE, PARTIAL, or UNVERIFIED"
    )
    summary: Dict[str, str] = Field(..., description="Multilingual high-level explanation of outcome")
    conditions_satisfied: List[EvaluatedCondition] = Field(
        default_factory=list, description="List of conditions the citizen successfully met"
    )
    conditions_failed: List[EvaluatedCondition] = Field(
        default_factory=list, description="List of conditions the citizen failed to meet"
    )
    missing_information: List[MissingFieldInfo] = Field(
        default_factory=list, description="Required attributes not provided in citizen inputs"
    )
    unresolved_criteria: List[Dict[str, Any]] = Field(
        default_factory=list, description="Statutory exclusions or criteria requiring manual CSC verification"
    )
    disclaimer: Dict[str, str] = Field(
        ..., description="Multilingual legal/advisory disclaimer"
    )
    source_citations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Official ministry citations backing the evaluation"
    )
    ministry: Optional[str] = Field(None, description="Administrative Ministry or Department")
    benefits: Optional[Dict[str, str]] = Field(None, description="Multilingual tangible benefits")
    official_url: Optional[str] = Field(None, description="Official government scheme portal URL")
    last_verified_date: Optional[str] = Field(None, description="Authoritative ISO verification date")
    application_procedure: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Step-by-step application procedure"
    )
    documents: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Required identity and income documents"
    )


class EligibilityEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    citizen_attributes: Dict[str, Any] = Field(
        ...,
        description="Dictionary of citizen profile attributes (e.g. occupation, landholding_hectares, has_bpl_card, pays_income_tax, age)"
    )
    scheme_ids: Optional[List[str]] = Field(
        None,
        description="Optional list of specific scheme slugs/IDs to evaluate. If omitted or null, all active schemes are evaluated."
    )
    preferred_language: str = Field(
        default="en",
        description="Preferred language for summary representation (en, hi, kn, te)"
    )


class EligibilityEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    results: List[SchemeEligibilityResult] = Field(..., description="Evaluation outcomes for each requested scheme")
    evaluated_at: str = Field(..., description="ISO 8601 UTC timestamp of evaluation run")
    preferred_language: str = Field(default="en", description="Echoed preferred language")

