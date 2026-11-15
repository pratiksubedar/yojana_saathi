"""
Yojana Saathi - Milestone 6.1 Test Suite
Tests for Scheme Knowledge Chunking, Provenance Citation Engine, and RAG Retrieval Service.

Covers:
1. All 7 schemes chunk coverage across all 6 semantic categories
2. All 4 languages (en, hi, kn, te) chunk completeness
3. Provenance metadata fidelity and non-invention of missing fields
4. RAG retrieval in English, Hindi, Kannada, and Telugu
5. Unicode combining mark and Indic script preservation
6. Irrelevant / noise query suppression (avoiding presenting unrelated schemes as relevant)
7. Category-specific retrieval (benefits, eligibility, exclusions, documents, application procedure)
8. Provenance-aware citation formatting across all 4 verification statuses
9. Attribution label distinction: Curated Summary vs Official Quotation
10. API endpoint GET /api/v1/schemes/rag/retrieve integration
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.db.session import async_session_factory
from app.schemas.provenance import VerificationStatus
from app.schemas.rag import (
    ChunkCategoryEnum,
    ChunkProvenanceSchema,
    ContentTypeEnum,
    RAGRetrievalRequest,
    SchemeChunk,
)
from app.services.chunking_service import SchemeChunkingService
from app.services.citation_formatter import CitationFormatter
from app.services.rag_retriever_service import RAGRetrieverService

client = TestClient(app)

SEED_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "schemes_seed.json"


# ==============================================================================
# 1. SEMANTIC CHUNKING TESTS
# ==============================================================================

def test_semantic_chunking_catalog_schemes_coverage():
    """Verify that all 21 schemes produce semantic chunks across all 6 categories and 4 languages."""
    with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    assert len(schemes) == 21
    chunks = SchemeChunkingService.chunk_all_schemes(schemes)

    # Expected count: >1000 chunks across 21 schemes
    assert len(chunks) >= 1000

    scheme_ids = {c.scheme_id for c in chunks}
    original_7 = {"pm-kisan", "pm-jay", "pm-svanidhi", "pmay-g", "pm-kmy", "pmmvy", "pm-kusum"}
    assert original_7.issubset(scheme_ids)
    assert len(scheme_ids) == 21

    # Verify all 6 categories are represented
    categories = {c.category for c in chunks}
    expected_categories = {
        ChunkCategoryEnum.SCHEME_OVERVIEW,
        ChunkCategoryEnum.SCHEME_BENEFIT,
        ChunkCategoryEnum.ELIGIBILITY_CLAUSE,
        ChunkCategoryEnum.EXCLUSION_CLAUSE,
        ChunkCategoryEnum.DOCUMENT_REQUIREMENT,
        ChunkCategoryEnum.APPLICATION_PROCEDURE,
    }
    assert categories == expected_categories

    # Verify balanced language coverage across en, hi, kn, te
    langs = {c.language for c in chunks}
    assert langs == {"en", "hi", "kn", "te"}
    counts_by_lang = {lang: sum(1 for c in chunks if c.language == lang) for lang in langs}
    assert counts_by_lang["en"] == counts_by_lang["hi"] == counts_by_lang["kn"] == counts_by_lang["te"]


def test_chunk_metadata_fidelity_and_non_invention():
    """Verify that chunk metadata preserves official facts and NEVER invents missing page numbers."""
    with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    chunks = SchemeChunkingService.chunk_all_schemes(schemes)

    # Check PM-KISAN overview chunk
    pmk_overview_en = next(c for c in chunks if c.chunk_id == "pm-kisan_overview_en")
    assert pmk_overview_en.scheme_id == "pm-kisan"
    assert pmk_overview_en.category == ChunkCategoryEnum.SCHEME_OVERVIEW
    assert pmk_overview_en.language == "en"
    assert pmk_overview_en.provenance.issuing_authority == "Department of Agriculture and Farmers Welfare, Government of India"
    assert pmk_overview_en.provenance.document_title == "Revised PM-KISAN Operational Guidelines & Expansion Letter (07.06.2019)"
    assert pmk_overview_en.provenance.verification_status == VerificationStatus.VERIFIED
    # No page number in overview -> must be strictly None (never invented)
    assert pmk_overview_en.provenance.page_ref is None
    assert pmk_overview_en.content_type == ContentTypeEnum.CURATED_SUMMARY
    assert pmk_overview_en.is_verbatim is False

    # Check PM-KISAN eligibility condition with genuine page_ref in seed
    pmk_elig = next(c for c in chunks if c.chunk_id == "pm-kisan_elig_pmk_c1_en")
    assert pmk_elig.provenance.relevant_section == "Section 2.1 (Definition of Beneficiary)"
    assert pmk_elig.provenance.page_ref == "Page 2"  # Exact genuine string from seed


# ==============================================================================
# 2. RAG RETRIEVER SERVICE TESTS (MULTILINGUAL)
# ==============================================================================

@pytest.mark.asyncio
async def test_rag_retrieval_english_queries():
    """Verify high-precision retrieval for English citizen queries."""
    retriever = RAGRetrieverService()

    # 1. PM-KISAN financial benefit
    res = await retriever.search("farmer ₹6,000 installment direct benefit transfer", language="en", limit=3)
    assert len(res) > 0
    top_scheme = res[0].chunk.scheme_id
    assert top_scheme == "pm-kisan"
    assert res[0].relevance_score > 0.4
    assert res[0].match_type in ["fts5_bm25", "substring_fallback"]

    # 2. PM-JAY health insurance
    res_jay = await retriever.search("health coverage hospital ₹5 lakh ayushman", language="en", limit=3)
    assert len(res_jay) > 0
    assert any(r.chunk.scheme_id == "pm-jay" for r in res_jay)


@pytest.mark.asyncio
async def test_rag_retrieval_hindi_queries():
    """Verify high-precision retrieval for Hindi queries with Devanagari Unicode preservation."""
    retriever = RAGRetrieverService()

    # Hindi PM-KISAN query
    res = await retriever.search("किसान सम्मान निधि ₹6,000 की किस्त", language="hi", limit=3)
    assert len(res) > 0
    assert res[0].chunk.scheme_id == "pm-kisan"
    assert res[0].chunk.language == "hi"

    # Hindi Street Vendor (PM SVANidhi)
    res_sva = await retriever.search("स्ट्रीट वेंडर ऋण स्वनिधि योजना", language="hi", limit=3)
    assert len(res_sva) > 0
    assert any(r.chunk.scheme_id == "pm-svanidhi" for r in res_sva)


@pytest.mark.asyncio
async def test_rag_retrieval_kannada_queries():
    """Verify high-precision retrieval for Kannada queries with viramas and matras."""
    retriever = RAGRetrieverService()

    # Kannada Solar Pump (PM-KUSUM)
    res = await retriever.search("ಸೌರ ಪಂಪ್ ಸೋಲಾರ್ ನೀರಾವರಿ ಕುಸುಮ್", language="kn", limit=3)
    assert len(res) > 0
    assert any(r.chunk.scheme_id == "pm-kusum" for r in res)
    assert res[0].chunk.language == "kn"


@pytest.mark.asyncio
async def test_rag_retrieval_telugu_queries():
    """Verify high-precision retrieval for Telugu queries with Unicode combining marks."""
    retriever = RAGRetrieverService()

    # Telugu Farmer scheme
    res = await retriever.search("రైతు వ్యవసాయ భూమి", language="te", limit=3)
    assert len(res) > 0
    assert any(r.chunk.scheme_id in ["pm-kisan", "pm-kusum", "pm-kmy"] for r in res)
    assert res[0].chunk.language == "te"


# ==============================================================================
# 3. NOISE SUPPRESSION & UNRELATED QUERY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_rag_retrieval_suppresses_unrelated_queries():
    """Verify that unrelated or alien queries return ZERO results and never falsely match schemes."""
    retriever = RAGRetrieverService()

    # Pure alien query
    res_alien = await retriever.search("quantum astronaut cryptocurrency mars alien spaceship", limit=5)
    assert len(res_alien) == 0

    # Irrelevant query containing one incidental word
    res_incidental = await retriever.search("quantum astronaut cryptocurrency mars mission alien", limit=5)
    assert len(res_incidental) == 0

    # Empty and whitespace queries
    res_empty = await retriever.search("", limit=5)
    assert len(res_empty) == 0

    res_punct = await retriever.search("??? --- !!! ***", limit=5)
    assert len(res_punct) == 0


# ==============================================================================
# 4. CATEGORY-FILTERED RETRIEVAL TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_rag_retrieval_category_filtering():
    """Verify retrieval when scoped to specific chunk categories."""
    retriever = RAGRetrieverService()

    # Document requirements for PM-JAY
    res_docs = await retriever.search(
        "documents required for Ayushman card",
        category=ChunkCategoryEnum.DOCUMENT_REQUIREMENT,
        scheme_id="pm-jay",
        limit=5,
    )
    assert len(res_docs) > 0
    for r in res_docs:
        assert r.chunk.category == ChunkCategoryEnum.DOCUMENT_REQUIREMENT
        assert r.chunk.scheme_id == "pm-jay"

    # Application procedure for PM SVANidhi
    res_app = await retriever.search(
        "how to apply on portal",
        category=ChunkCategoryEnum.APPLICATION_PROCEDURE,
        scheme_id="pm-svanidhi",
        limit=5,
    )
    assert len(res_app) > 0
    for r in res_app:
        assert r.chunk.category == ChunkCategoryEnum.APPLICATION_PROCEDURE
        assert r.chunk.scheme_id == "pm-svanidhi"


# ==============================================================================
# 5. CITATION FORMATTER & PROVENANCE STATUS TESTS
# ==============================================================================

def test_citation_formatter_all_four_provenance_statuses():
    """Verify that CitationFormatter handles all 4 verification tiers with proper disclosures."""
    # 1. VERIFIED
    c_ver = SchemeChunk(
        chunk_id="test_ver",
        scheme_id="pm-kisan",
        category=ChunkCategoryEnum.SCHEME_BENEFIT,
        language="en",
        content="Test benefit content",
        provenance=ChunkProvenanceSchema(
            source_url="https://pmkisan.gov.in/guidelines.pdf",
            issuing_authority="Ministry of Agriculture",
            document_title="PM-KISAN Guidelines",
            relevant_section="Section 2.1",
            page_ref="Page 5",
            verification_status=VerificationStatus.VERIFIED,
        ),
        content_type=ContentTypeEnum.CURATED_SUMMARY,
        is_verbatim=False,
    )
    cit_ver = CitationFormatter.format_citation(c_ver, "en")
    assert cit_ver.verification_status == VerificationStatus.VERIFIED
    assert "Verified against official government guidelines" in cit_ver.status_disclosure
    assert cit_ver.attribution_label == "Curated Summary from Official Guidelines"
    assert cit_ver.page_ref == "Page 5"

    # 2. PARTIALLY_VERIFIED
    c_part = SchemeChunk(
        chunk_id="test_part",
        scheme_id="test-scheme",
        category=ChunkCategoryEnum.ELIGIBILITY_CLAUSE,
        language="en",
        content="Partial rule content",
        provenance=ChunkProvenanceSchema(
            source_url="https://example.gov.in/draft.pdf",
            issuing_authority="State Agency",
            document_title="Draft Policy",
            verification_status=VerificationStatus.PARTIALLY_VERIFIED,
        ),
        content_type=ContentTypeEnum.CURATED_SUMMARY,
        is_verbatim=False,
    )
    cit_part = CitationFormatter.format_citation(c_part, "en")
    assert cit_part.verification_status == VerificationStatus.PARTIALLY_VERIFIED
    assert "Partially verified" in cit_part.status_disclosure
    assert cit_part.page_ref is None

    # 3. REQUIRES_OFFICIAL_VERIFICATION
    c_req = SchemeChunk(
        chunk_id="test_req",
        scheme_id="pmay-g",
        category=ChunkCategoryEnum.EXCLUSION_CLAUSE,
        language="en",
        content="Registry verification requirement",
        provenance=ChunkProvenanceSchema(
            source_url="https://pmayg.nic.in/framework.pdf",
            issuing_authority="Ministry of Rural Development",
            document_title="PMAY-G Framework",
            relevant_section="Section 2.2",
            verification_status=VerificationStatus.REQUIRES_OFFICIAL_VERIFICATION,
        ),
        content_type=ContentTypeEnum.CURATED_SUMMARY,
        is_verbatim=False,
    )
    cit_req = CitationFormatter.format_citation(c_req, "en")
    assert cit_req.verification_status == VerificationStatus.REQUIRES_OFFICIAL_VERIFICATION
    assert "Requires official physical or administrative verification" in cit_req.status_disclosure

    # 4. UNVERIFIED
    c_unver = SchemeChunk(
        chunk_id="test_unver",
        scheme_id="unver-scheme",
        category=ChunkCategoryEnum.SCHEME_OVERVIEW,
        language="en",
        content="Unverified overview",
        provenance=ChunkProvenanceSchema(
            source_url="https://example.gov.in/unverified",
            issuing_authority="Unknown Agency",
            document_title="Unverified Brief",
            verification_status=VerificationStatus.UNVERIFIED,
        ),
        content_type=ContentTypeEnum.CURATED_SUMMARY,
        is_verbatim=False,
    )
    cit_unver = CitationFormatter.format_citation(c_unver, "en")
    assert cit_unver.verification_status == VerificationStatus.UNVERIFIED
    assert "Unverified; guidelines have not been formally established" in cit_unver.status_disclosure


def test_citation_attribution_distinction_curated_vs_verbatim():
    """Verify clear distinction between curated summaries and verbatim official quotations."""
    # Curated Summary
    c_curated = SchemeChunk(
        chunk_id="test_c",
        scheme_id="pm-kisan",
        category=ChunkCategoryEnum.SCHEME_OVERVIEW,
        language="en",
        content="Curated summary text",
        provenance=ChunkProvenanceSchema(
            source_url="https://pmkisan.gov.in/",
            issuing_authority="Department of Agriculture",
            document_title="Guidelines",
            verification_status=VerificationStatus.VERIFIED,
        ),
        content_type=ContentTypeEnum.CURATED_SUMMARY,
        is_verbatim=False,
    )
    cit_c = CitationFormatter.format_citation(c_curated, "en")
    assert cit_c.attribution_label == "Curated Summary from Official Guidelines"
    assert cit_c.is_verbatim is False

    # Verbatim Official Text
    c_verbatim = SchemeChunk(
        chunk_id="test_v",
        scheme_id="pm-kisan",
        category=ChunkCategoryEnum.SCHEME_OVERVIEW,
        language="en",
        content="Verbatim gazette clause",
        provenance=ChunkProvenanceSchema(
            source_url="https://pmkisan.gov.in/",
            issuing_authority="Department of Agriculture",
            document_title="Gazette Notification",
            verification_status=VerificationStatus.VERIFIED,
        ),
        content_type=ContentTypeEnum.VERBATIM_OFFICIAL_TEXT,
        is_verbatim=True,
    )
    cit_v = CitationFormatter.format_citation(c_verbatim, "en")
    assert cit_v.attribution_label == "Official Quotation (Verbatim)"
    assert cit_v.is_verbatim is True

    # Test Markdown formatting distinctions
    md_output = CitationFormatter.format_citations_markdown([cit_c, cit_v], "en")
    assert "[Curated Summary from Official Guidelines]" in md_output
    assert "[Official Quotation (Verbatim)]" in md_output
    assert "### Official Sources & Provenance" in md_output


def test_citation_missing_metadata_handling():
    """Verify that citations never display missing fields as invented values."""
    c_no_page = SchemeChunk(
        chunk_id="test_np",
        scheme_id="pm-kisan",
        category=ChunkCategoryEnum.SCHEME_OVERVIEW,
        language="en",
        content="Overview content",
        provenance=ChunkProvenanceSchema(
            source_url="https://pmkisan.gov.in/",
            issuing_authority="Department of Agriculture",
            document_title="PM-KISAN Guidelines",
            relevant_section=None,
            page_ref=None,
            verification_status=VerificationStatus.VERIFIED,
        ),
        content_type=ContentTypeEnum.CURATED_SUMMARY,
        is_verbatim=False,
    )
    cit = CitationFormatter.format_citation(c_no_page, "en")
    md = CitationFormatter.format_citations_markdown([cit], "en")

    # Section and Page lines must NOT appear when None
    assert "- **Section:**" not in md
    assert "- **Page:**" not in md
    assert "- **Section / Page:**" not in md
    assert "Page 0" not in md


# ==============================================================================
# 6. INTEGRATION API ENDPOINT TESTS
# ==============================================================================

def test_api_rag_retrieve_endpoint_success():
    """Verify GET /api/v1/schemes/rag/retrieve returns grounded chunks and citations."""
    response = client.get(
        "/api/v1/schemes/rag/retrieve",
        params={
            "query": "farmer ₹6,000 subsidy PM-KISAN",
            "language": "en",
            "limit": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "farmer ₹6,000 subsidy PM-KISAN"
    assert data["total_results"] > 0
    assert len(data["results"]) <= 3

    top_result = data["results"][0]
    assert "chunk" in top_result
    assert "relevance_score" in top_result
    assert top_result["chunk"]["scheme_id"] == "pm-kisan"

    # Verify citations presence
    assert len(data["citations"]) > 0
    assert "formatted_citations_markdown" in data
    assert "### Official Sources & Provenance" in data["formatted_citations_markdown"]


def test_api_rag_retrieve_unrelated_query():
    """Verify GET /api/v1/schemes/rag/retrieve returns zero results for completely irrelevant query."""
    response = client.get(
        "/api/v1/schemes/rag/retrieve",
        params={
            "query": "quantum astronaut cryptocurrency mars alien spaceship",
            "language": "en",
            "limit": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert len(data["results"]) == 0
    assert len(data["citations"]) == 0
    assert data["formatted_citations_markdown"] == ""

