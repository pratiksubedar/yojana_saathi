"""
Yojana Saathi - RAG & Semantic Chunking Schemas
Milestone 6.1: Structured semantic chunks, provenance metadata,
retrieval results, and citation models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.provenance import VerificationStatus


class ChunkCategoryEnum(str, Enum):
    """Authoritative semantic chunk category."""
    SCHEME_OVERVIEW = "scheme_overview"
    SCHEME_BENEFIT = "scheme_benefit"
    ELIGIBILITY_CLAUSE = "eligibility_clause"
    EXCLUSION_CLAUSE = "exclusion_clause"
    DOCUMENT_REQUIREMENT = "document_requirement"
    APPLICATION_PROCEDURE = "application_procedure"


class ContentTypeEnum(str, Enum):
    """Distinction between curated summary and verbatim official text."""
    CURATED_SUMMARY = "curated_summary"
    VERBATIM_OFFICIAL_TEXT = "verbatim_official_text"


class ChunkProvenanceSchema(BaseModel):
    """Traceable official source citation backing a semantic chunk."""
    model_config = ConfigDict(from_attributes=True)

    source_url: str = Field(..., description="Official government document or portal URL")
    issuing_authority: str = Field(..., description="Ministry, department, or statutory authority")
    document_title: str = Field(..., description="Title of operational guidelines or gazette notification")
    relevant_section: Optional[str] = Field(None, description="Specific clause, section, or chapter")
    page_ref: Optional[str] = Field(None, description="Page number reference where explicitly available")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.VERIFIED,
        description="Factual verification level (VERIFIED, PARTIALLY_VERIFIED, REQUIRES_OFFICIAL_VERIFICATION, UNVERIFIED)"
    )
    last_reviewed_date: Optional[str] = Field(None, description="ISO date when information was last reviewed against source")


class SchemeChunk(BaseModel):
    """Atomic semantic chunk of a welfare scheme for RAG retrieval."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="Unique chunk identifier")
    scheme_id: str = Field(..., description="Parent scheme identifier (e.g., 'pm-kisan')")
    category: ChunkCategoryEnum = Field(..., description="Semantic chunk category")
    language: str = Field(..., description="Language code: en, hi, kn, te")
    content: str = Field(..., description="Text content of the chunk")
    provenance: ChunkProvenanceSchema = Field(..., description="Authoritative source citation metadata")
    content_type: ContentTypeEnum = Field(
        default=ContentTypeEnum.CURATED_SUMMARY,
        description="Indicates whether content is a curated summary or verbatim text"
    )
    is_verbatim: bool = Field(
        default=False,
        description="False for curated summaries; True only for verbatim quotations"
    )


class ProvenanceCitation(BaseModel):
    """Provenance-grounded citation formatted for assistant responses."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="Referenced chunk identifier")
    scheme_id: str = Field(..., description="Referenced scheme identifier")
    category: ChunkCategoryEnum = Field(..., description="Referenced chunk category")
    document_title: str = Field(..., description="Official guidelines or gazette title")
    issuing_authority: str = Field(..., description="Issuing government body")
    source_url: str = Field(..., description="Direct link to source document or portal")
    relevant_section: Optional[str] = Field(None, description="Clause or section cited")
    page_ref: Optional[str] = Field(None, description="Page reference where explicitly available")
    verification_status: VerificationStatus = Field(..., description="Authoritative verification tier")
    status_disclosure: str = Field(..., description="Localized disclosure note explaining verification tier")
    last_reviewed_date: Optional[str] = Field(None, description="Date of last review")
    content_type: ContentTypeEnum = Field(..., description="Curated summary or verbatim text")
    is_verbatim: bool = Field(default=False, description="Whether text is a verbatim quote")
    attribution_label: str = Field(..., description="Label distinguishing curated summary from official quotation")


class ChunkSearchResult(BaseModel):
    """Ranked search result item from RAG retrieval."""
    model_config = ConfigDict(from_attributes=True)

    chunk: SchemeChunk = Field(..., description="Matched scheme chunk")
    relevance_score: float = Field(..., description="Normalized relevance score (0.0 to 1.0)")
    bm25_rank: float = Field(..., description="SQLite FTS5 BM25 score")
    match_type: str = Field(..., description="Retrieval match type: fts5_bm25 or substring_fallback")


class RAGRetrievalRequest(BaseModel):
    """Request payload for RAG retrieval."""
    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., min_length=1, description="Natural language citizen query")
    language: Optional[str] = Field(None, description="Target language: en, hi, kn, te")
    category: Optional[ChunkCategoryEnum] = Field(None, description="Optional category filter")
    scheme_id: Optional[str] = Field(None, description="Optional scheme ID filter")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum chunks to retrieve")
    min_score: float = Field(default=0.05, ge=0.0, le=1.0, description="Minimum relevance score threshold")


class RAGRetrievalResponse(BaseModel):
    """Response payload containing retrieved chunks, citations, and formatted markdown."""
    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="Original user query")
    language: Optional[str] = Field(None, description="Query language")
    total_results: int = Field(..., description="Total matching chunks found above threshold")
    results: List[ChunkSearchResult] = Field(default_factory=list, description="Ranked retrieved chunks")
    citations: List[ProvenanceCitation] = Field(default_factory=list, description="Extracted provenance citations")
    formatted_citations_markdown: str = Field(default="", description="Rendered markdown references block")

