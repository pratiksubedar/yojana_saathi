import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

# Standard UUID v4/generic format: 8-4-4-4-12 hex characters
UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# Prohibited sensitive keys representing citizen credentials or document uploads
PROHIBITED_PII_KEYS = {
    "aadhaar", "aadhaar_number", "aadhaar_no", "uid", "uidai",
    "bank_account", "account_number", "account_no", "ifsc", "ifsc_code",
    "pan", "pan_number", "phone", "mobile", "mobile_number",
    "document_content", "document_file", "file", "image", "pdf", "bytes",
    "passbook", "salary", "income_certificate", "caste_certificate"
}


def validate_uuid_format(v: str) -> str:
    """Enforces standard UUID format for session tracking identifiers."""
    cleaned = v.strip()
    if not UUID_REGEX.match(cleaned):
        try:
            val = uuid.UUID(cleaned)
            return str(val)
        except (ValueError, AttributeError):
            raise ValueError(
                f"Invalid session_id '{v}'. Standard UUID format required (e.g. 'c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930')."
            )
    return cleaned.lower()


def scan_for_sensitive_keys(data: Any) -> None:
    """Recursively scans incoming request payloads for prohibited sensitive citizen keys."""
    if isinstance(data, dict):
        found = set(k.lower() for k in data.keys()).intersection(PROHIBITED_PII_KEYS)
        if found:
            raise ValueError(
                f"Privacy violation: Request contains prohibited sensitive citizen keys: {', '.join(sorted(found))}. "
                "Yojana Saathi does not collect, accept, or store citizen credentials or document files."
            )
        for val in data.values():
            if isinstance(val, (dict, list)):
                scan_for_sensitive_keys(val)
    elif isinstance(data, list):
        for item in data:
            scan_for_sensitive_keys(item)


class ChecklistItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: str = Field(..., description="Unique document ID (e.g. doc-pmk-aadhaar)")
    scheme_id: str = Field(..., description="Parent scheme identifier")
    names: Dict[str, str] = Field(..., description="Multilingual document names (en, hi, kn, te)")
    descriptions: Dict[str, str] = Field(..., description="Multilingual guidance and issuance requirements")
    is_mandatory: bool = Field(..., description="True if mandatory for official application")
    csc_assisted: bool = Field(..., description="True if Common Service Centre can assist in obtaining")
    issuer: str = Field(..., description="Designated issuing authority")
    source_url: Optional[str] = Field(None, description="Official issuing authority or guidelines URL for document")
    is_collected: bool = Field(default=False, description="Whether citizen has marked this item as collected in session")


class SchemeChecklistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    scheme_id: str = Field(..., description="Target welfare scheme identifier")
    scheme_name: Dict[str, str] = Field(..., description="Multilingual scheme names (en, hi, kn, te)")
    total_documents: int = Field(..., description="Total number of required/recommended documents")
    mandatory_count: int = Field(..., description="Count of mandatory documents")
    optional_count: int = Field(..., description="Count of optional/supporting documents")
    collected_count: int = Field(..., description="Count of documents marked collected in current active session")
    mandatory_collected_count: int = Field(..., description="Count of mandatory documents collected")
    is_complete: bool = Field(..., description="True if all mandatory documents have been marked collected")
    documents: List[ChecklistItemSchema] = Field(..., description="List of checklist items with collection flags")
    source_citation: Dict[str, Any] = Field(..., description="Authoritative guidelines source citation")
    official_portal_url: str = Field(..., description="Official government scheme application portal")
    disclaimer: Dict[str, str] = Field(..., description="Multilingual document verification disclaimer")
    session_id: Optional[str] = Field(None, description="Echoed anonymous session identifier (UUID)")


class MarkChecklistItemRequest(BaseModel):
    # Strict extra='forbid' ensures unexpected fields are rejected with HTTP 422
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Anonymous session identifier (must be valid standard UUID)")
    scheme_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{1,64}$", description="Target scheme identifier")
    document_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{1,64}$", description="Document code being updated")
    is_collected: bool = Field(default=True, description="Collection state: true if acquired, false otherwise")

    @field_validator("session_id")
    @classmethod
    def validate_session_uuid(cls, v: str) -> str:
        return validate_uuid_format(v)

    @model_validator(mode="before")
    @classmethod
    def reject_sensitive_pii(cls, data: Any) -> Any:
        scan_for_sensitive_keys(data)
        return data


class ResetChecklistRequest(BaseModel):
    # Strict extra='forbid' prevents silent acceptance of extra/sensitive fields on reset
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Anonymous session identifier (must be valid standard UUID)")
    scheme_id: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9_-]{1,64}$", description="Optional scheme ID to reset specific scheme, or reset all")

    @field_validator("session_id")
    @classmethod
    def validate_session_uuid(cls, v: str) -> str:
        return validate_uuid_format(v)

    @model_validator(mode="before")
    @classmethod
    def reject_sensitive_pii(cls, data: Any) -> Any:
        scan_for_sensitive_keys(data)
        return data
