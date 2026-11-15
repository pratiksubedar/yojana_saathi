"""
Yojana Saathi - Scheme Provenance and Freshness Schemas
Milestone 5.4: Formal verification metadata, source citation tracking,
and configurable temporal freshness analysis.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class VerificationStatus(str, Enum):
    """Authoritative evidence verification level."""
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    REQUIRES_OFFICIAL_VERIFICATION = "REQUIRES_OFFICIAL_VERIFICATION"
    UNVERIFIED = "UNVERIFIED"


class FreshnessStatus(str, Enum):
    """Temporal freshness grade for scheme guidelines."""
    CURRENT = "CURRENT"
    REVIEW_DUE = "REVIEW_DUE"
    STALE = "STALE"
    UNVERIFIED = "UNVERIFIED"


class PrimarySourceCitationSchema(BaseModel):
    """Details of the official government document, gazette, or guideline."""
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., description="Official primary document or guidelines title")
    url: str = Field(..., description="Authoritative primary source or portal URL")
    issuing_authority: str = Field(..., description="Official government ministry, department, or designated agency")
    scheme_version: Optional[str] = Field(None, description="Official scheme guideline edition or amendment version")
    relevant_sections: List[str] = Field(default_factory=list, description="Specific clauses, chapters, or sections cited")


class VerificationMetadataSchema(BaseModel):
    """Authoritative factual verification status and rule completeness."""
    model_config = ConfigDict(from_attributes=True)

    verification_status: VerificationStatus = Field(..., description="Authoritative factual verification level")
    last_verified_date: Optional[str] = Field(None, description="ISO date of initial verification against official guidelines")
    last_reviewed_date: Optional[str] = Field(None, description="ISO date of most recent review against official source")
    rule_completeness: str = Field(default="COMPLETE", description="Eligibility rule AST completeness (COMPLETE or PARTIAL)")
    unresolved_criteria: List[Dict[str, Any]] = Field(default_factory=list, description="Specific criteria requiring localized or manual field verification")


class FreshnessMetadataSchema(BaseModel):
    """Temporal currency assessment and review threshold evaluation."""
    model_config = ConfigDict(from_attributes=True)

    status: FreshnessStatus = Field(..., description="Temporal freshness assessment (CURRENT, REVIEW_DUE, STALE, UNVERIFIED)")
    days_since_verification: Optional[int] = Field(None, description="Days elapsed since initial verification")
    days_since_review: Optional[int] = Field(None, description="Days elapsed since most recent review")
    review_due_threshold_days: int = Field(..., description="Configured days threshold after which review is due")
    stale_threshold_days: int = Field(..., description="Configured days threshold after which guidelines are considered stale")
    reason: str = Field(..., description="Human-readable justification for the assigned freshness status")
    is_fresh: bool = Field(..., description="True if guidelines are current and within review window")


class DocumentSourceSchema(BaseModel):
    """Source authority and citation for required supporting documents."""
    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., description="Document identifier code")
    names: Dict[str, str] = Field(..., description="Multilingual document names (en, hi, kn, te)")
    issuer: str = Field(..., description="Designated issuing authority")
    source_url: Optional[str] = Field(None, description="Official issuing authority or guidelines URL")
    is_mandatory: bool = Field(..., description="Whether document is strictly mandatory for scheme eligibility")


class OfficialPortalSchema(BaseModel):
    """Designated public portal metadata."""
    model_config = ConfigDict(from_attributes=True)

    url: str = Field(..., description="Official government portal URL")
    portal_name: str = Field(..., description="Designated portal title")


class SchemeProvenanceResponse(BaseModel):
    """Comprehensive read-only response for scheme source traceability and freshness."""
    model_config = ConfigDict(from_attributes=True)

    scheme_id: str = Field(..., description="Scheme unique slug/ID")
    names: Dict[str, str] = Field(..., description="Multilingual scheme names (en, hi, kn, te)")
    ministry: str = Field(..., description="Central or State administrative ministry")
    official_portal: OfficialPortalSchema = Field(..., description="Official government web portal details")
    primary_source: PrimarySourceCitationSchema = Field(..., description="Official primary source citation details")
    verification: VerificationMetadataSchema = Field(..., description="Factual verification grade and rule completeness")
    freshness: FreshnessMetadataSchema = Field(..., description="Temporal freshness evaluation against configured thresholds")
    document_sources: List[DocumentSourceSchema] = Field(default_factory=list, description="Supporting document issuance authorities")


class SchemeFreshnessItem(BaseModel):
    """Summary freshness assessment for an individual scheme in the catalog."""
    model_config = ConfigDict(from_attributes=True)

    scheme_id: str = Field(..., description="Scheme unique slug/ID")
    scheme_name_en: str = Field(..., description="English scheme name")
    freshness_status: FreshnessStatus = Field(..., description="Assigned freshness status")
    verification_status: VerificationStatus = Field(..., description="Assigned verification status")
    last_verified_date: Optional[str] = Field(None, description="ISO date of verification")
    last_reviewed_date: Optional[str] = Field(None, description="ISO date of review")
    days_since_review: Optional[int] = Field(None, description="Days elapsed since most recent review")
    is_fresh: bool = Field(..., description="Whether scheme is currently fresh")
    reason: str = Field(..., description="Freshness reasoning")


class CatalogFreshnessSummaryResponse(BaseModel):
    """Aggregate catalog-level freshness and audit summary."""
    model_config = ConfigDict(from_attributes=True)

    total_schemes: int = Field(..., description="Total active schemes in catalog")
    current_count: int = Field(..., description="Count of schemes with CURRENT status")
    review_due_count: int = Field(..., description="Count of schemes with REVIEW_DUE status")
    stale_count: int = Field(..., description="Count of schemes with STALE status")
    unverified_count: int = Field(..., description="Count of schemes with UNVERIFIED status")
    review_due_threshold_days: int = Field(..., description="Configured review due threshold (days)")
    stale_threshold_days: int = Field(..., description="Configured stale threshold (days)")
    items: List[SchemeFreshnessItem] = Field(..., description="List of per-scheme freshness evaluations")
