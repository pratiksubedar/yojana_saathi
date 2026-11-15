from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RuleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique rule ID")
    scheme_id: str = Field(..., description="Parent scheme slug/ID")
    version: str = Field(..., description="Rule guideline version")
    conditions: Dict[str, Any] = Field(..., description="Declarative AST conditions and citations")
    is_active: bool = Field(default=True, description="Rule active status")


class DocumentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique document code/ID")
    scheme_id: str = Field(..., description="Parent scheme slug/ID")
    names: Dict[str, str] = Field(..., description="Multilingual document names (en, hi, kn, te)")
    descriptions: Dict[str, str] = Field(..., description="Multilingual issuance guidelines")
    is_mandatory: bool = Field(..., description="Whether document is strictly required")
    csc_assisted: bool = Field(..., description="Whether Common Service Centre can assist in obtaining")
    issuer: str = Field(..., description="Designated issuing authority")
    source_url: Optional[str] = Field(None, description="Official issuing authority or guidelines URL for document")


class SchemeSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique scheme slug/ID")
    slug: str = Field(..., description="URL-friendly slug")
    category: str = Field(..., description="Welfare domain (e.g. agriculture, healthcare, housing)")
    ministry: str = Field(..., description="Central or State administrative ministry")
    scheme_type: str = Field(..., description="CENTRAL_SECTOR or CENTRALLY_SPONSORED")
    state_applicability: List[str] = Field(..., description="List of applicable states or ['ALL']")
    
    # Multilingual localized strings
    names: Dict[str, str] = Field(..., description="Localized scheme names (en, hi, kn, te)")
    descriptions: Dict[str, str] = Field(..., description="Localized scheme summaries (en, hi, kn, te)")
    benefits: Dict[str, str] = Field(..., description="Localized tangible financial/service benefits")
    financial_amount_inr: Optional[float] = Field(None, description="Direct financial assistance amount in INR")
    
    # Official metadata
    official_url: str = Field(..., description="Verified official government portal URL")
    portal_name: str = Field(..., description="Official government portal title")
    last_verified_date: str = Field(..., description="ISO date of initial authoritative guideline verification")
    last_reviewed_date: str = Field(default="2026-11-10", description="ISO date of most recent review against official source")
    is_active: bool = Field(default=True, description="Scheme active status")

    rules_count: int = Field(default=0, description="Number of eligibility rules configured")
    documents_count: int = Field(default=0, description="Number of required/supporting documents")


class SchemeDetailSchema(SchemeSummarySchema):
    source_citation: Dict[str, Any] = Field(..., description="Official guidelines citation and publication details")
    application_procedure: List[Dict[str, Any]] = Field(default_factory=list, description="Step-by-step official application procedure in multiple languages")
    rules: List[RuleSchema] = Field(default_factory=list, description="Associated deterministic eligibility rules")
    documents: List[DocumentSchema] = Field(default_factory=list, description="Required identity and income documents")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class SchemePaginationMetadata(BaseModel):
    total: int = Field(..., description="Total matching schemes found")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of schemes per page")
    total_pages: int = Field(..., description="Total available pages")
    has_next: bool = Field(..., description="Whether there is a subsequent page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class SchemeListResponse(BaseModel):
    items: List[SchemeSummarySchema] = Field(..., description="List of scheme summary items")
    pagination: SchemePaginationMetadata = Field(..., description="Pagination metadata")
    filters_applied: Dict[str, Any] = Field(..., description="Search and filter parameters applied to query")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human-readable error description")
    error_code: str = Field(..., description="Machine-readable error identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

