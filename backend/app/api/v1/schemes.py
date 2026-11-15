import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Scheme, Rule, Document
from app.schemas.scheme import (
    SchemeListResponse,
    SchemeSummarySchema,
    SchemeDetailSchema,
    SchemePaginationMetadata,
    RuleSchema,
    DocumentSchema,
    ErrorResponse,
)
from app.schemas.provenance import (
    SchemeProvenanceResponse,
    CatalogFreshnessSummaryResponse,
)
from app.schemas.rag import (
    ChunkCategoryEnum,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
)
from app.core.exceptions import SchemeNotFoundException, InvalidFilterException
from app.services.search_service import SearchService
from app.services.freshness_service import FreshnessService, FreshnessConfig
from app.services.rag_retriever_service import RAGRetrieverService

router = APIRouter(prefix="/schemes", tags=["Schemes Catalog"])

ALLOWED_SCHEME_TYPES = {"CENTRAL_SECTOR", "CENTRALLY_SPONSORED", "STATE"}


@router.get(
    "",
    response_model=SchemeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List & Filter Welfare Schemes",
    description=(
        "Retrieves a paginated catalog of authoritative welfare schemes from SQLite. "
        "Supports multilingual search across English, Hindi, Kannada, and Telugu, "
        "as well as filtering by category, state applicability, and scheme type."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query or filter parameter"}
    }
)
async def list_schemes(
    category: Optional[str] = Query(
        None,
        description="Filter by welfare category (e.g. 'agriculture', 'healthcare', 'housing', 'employment')"
    ),
    state: Optional[str] = Query(
        None,
        description="Filter by state applicability (e.g. 'Karnataka', 'Telangana', or 'ALL')"
    ),
    scheme_type: Optional[str] = Query(
        None,
        description="Filter by administrative type: 'CENTRAL_SECTOR', 'CENTRALLY_SPONSORED', or 'STATE'"
    ),
    q: Optional[str] = Query(
        None,
        description="Search keyword across titles and descriptions in English, Hindi, Kannada, or Telugu"
    ),
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed, minimum 1)"
    ),
    page_size: int = Query(
        10,
        ge=1,
        le=100,
        description="Number of records per page (1 to 100)"
    ),
    session: AsyncSession = Depends(get_db),
) -> SchemeListResponse:
    # 1. Parameter Validation
    filters_applied: Dict[str, Any] = {}

    if category is not None:
        clean_category = category.strip()
        if not clean_category:
            raise InvalidFilterException("Category filter cannot be empty whitespace.")
        filters_applied["category"] = clean_category

    if state is not None:
        clean_state = state.strip()
        if not clean_state:
            raise InvalidFilterException("State filter cannot be empty whitespace.")
        filters_applied["state"] = clean_state

    if scheme_type is not None:
        clean_scheme_type = scheme_type.strip().upper()
        if clean_scheme_type not in ALLOWED_SCHEME_TYPES:
            raise InvalidFilterException(
                f"Invalid scheme_type '{scheme_type}'. Allowed values: {', '.join(sorted(ALLOWED_SCHEME_TYPES))}."
            )
        filters_applied["scheme_type"] = clean_scheme_type

    if q is not None:
        clean_q = q.strip()
        if not clean_q:
            raise InvalidFilterException("Search query 'q' cannot be empty whitespace.")
        filters_applied["q"] = clean_q

    # 2. Execute Multilingual Search or Filtered Query via SearchService
    schemes, total = await SearchService.search_schemes(
        session=session,
        q=filters_applied.get("q"),
        category=filters_applied.get("category"),
        state=filters_applied.get("state"),
        scheme_type=filters_applied.get("scheme_type"),
        page=page,
        page_size=page_size,
    )

    # 5. Build Summary Items
    items: List[SchemeSummarySchema] = []
    for s in schemes:
        items.append(
            SchemeSummarySchema(
                id=s.id,
                slug=s.slug,
                category=s.category,
                ministry=s.ministry,
                scheme_type=s.scheme_type,
                state_applicability=s.state_applicability,
                names=s.names,
                descriptions=s.descriptions,
                benefits=s.benefits,
                financial_amount_inr=s.financial_amount_inr,
                official_url=s.official_url,
                portal_name=s.portal_name,
                last_verified_date=s.last_verified_date,
                last_reviewed_date=getattr(s, "last_reviewed_date", s.last_verified_date),
                is_active=s.is_active,
                rules_count=len(s.rules),
                documents_count=len(s.documents),
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    pagination = SchemePaginationMetadata(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return SchemeListResponse(
        items=items,
        pagination=pagination,
        filters_applied=filters_applied,
    )


@router.get(
    "/freshness/summary",
    response_model=CatalogFreshnessSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Catalog Freshness and Audit Summary",
    description="Retrieves aggregate temporal freshness statistics and individual freshness assessments for all active welfare schemes.",
)
async def get_catalog_freshness_summary(
    review_due_days: int = Query(90, ge=1, le=1825, description="Review due threshold in days (default: 90)"),
    stale_days: int = Query(365, ge=1, le=3650, description="Stale threshold in days (default: 365)"),
    session: AsyncSession = Depends(get_db),
) -> CatalogFreshnessSummaryResponse:
    stmt = (
        select(Scheme)
        .where(Scheme.is_active == True)
        .order_by(Scheme.id.asc())
    )
    result = await session.execute(stmt)
    schemes = list(result.scalars().all())

    config = FreshnessConfig(review_due_days=review_due_days, stale_days=stale_days)
    return FreshnessService.get_catalog_freshness_summary(schemes=schemes, config=config)


@router.get(
    "/rag/retrieve",
    response_model=RAGRetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Grounded Scheme Knowledge Chunks",
    description=(
        "Retrieves semantic scheme knowledge chunks across 4 languages using SQLite FTS5 BM25 search. "
        "Returns verified provenance citations and formatted markdown references."
    ),
)
async def retrieve_scheme_chunks(
    query: str = Query(..., min_length=1, description="Natural language citizen query"),
    language: Optional[str] = Query(None, description="Language code: en, hi, kn, te"),
    category: Optional[ChunkCategoryEnum] = Query(None, description="Optional chunk category filter"),
    scheme_id: Optional[str] = Query(None, description="Optional scheme ID filter"),
    limit: int = Query(5, ge=1, le=20, description="Max chunks to return"),
    min_score: float = Query(0.05, ge=0.0, le=1.0, description="Relevance score threshold"),
    session: AsyncSession = Depends(get_db),
) -> RAGRetrievalResponse:
    retriever = RAGRetrieverService(session=session)
    request = RAGRetrievalRequest(
        query=query,
        language=language,
        category=category,
        scheme_id=scheme_id,
        limit=limit,
        min_score=min_score,
    )
    return await retriever.retrieve(request)


@router.get(
    "/{scheme_id}",
    response_model=SchemeDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Authoritative Scheme Details",
    description=(
        "Retrieves complete, clause-verified details for a single government scheme by ID or slug, "
        "including full multilingual content (en, hi, kn, te), official portal metadata, "
        "eligibility rules AST, and required document specifications."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Scheme not found in catalog"}
    }
)
async def get_scheme_detail(
    scheme_id: str,
    session: AsyncSession = Depends(get_db),
) -> SchemeDetailSchema:
    clean_id = scheme_id.strip()
    if not clean_id:
        raise SchemeNotFoundException(scheme_id)

    stmt = (
        select(Scheme)
        .where(
            or_(
                Scheme.id == clean_id,
                Scheme.slug == clean_id,
            )
        )
        .options(
            selectinload(Scheme.rules),
            selectinload(Scheme.documents),
        )
    )
    result = await session.execute(stmt)
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise SchemeNotFoundException(clean_id)

    return SchemeDetailSchema(
        id=scheme.id,
        slug=scheme.slug,
        category=scheme.category,
        ministry=scheme.ministry,
        scheme_type=scheme.scheme_type,
        state_applicability=scheme.state_applicability,
        names=scheme.names,
        descriptions=scheme.descriptions,
        benefits=scheme.benefits,
        financial_amount_inr=scheme.financial_amount_inr,
        official_url=scheme.official_url,
        portal_name=scheme.portal_name,
        last_verified_date=scheme.last_verified_date,
        last_reviewed_date=getattr(scheme, "last_reviewed_date", scheme.last_verified_date),
        is_active=scheme.is_active,
        source_citation=scheme.source_citation,
        application_procedure=getattr(scheme, "application_procedure", []),
        rules=[RuleSchema.model_validate(r) for r in scheme.rules],
        documents=[DocumentSchema.model_validate(d) for d in scheme.documents],
        rules_count=len(scheme.rules),
        documents_count=len(scheme.documents),
        created_at=scheme.created_at,
        updated_at=scheme.updated_at,
    )


@router.get(
    "/{scheme_id}/documents",
    status_code=status.HTTP_200_OK,
    summary="Get Scheme Required Documents Checklist",
    description="Retrieves the official document checklist for a scheme by ID or slug with optional session tracking.",
    responses={
        404: {"model": ErrorResponse, "description": "Scheme not found in catalog"}
    }
)
async def get_scheme_documents(
    scheme_id: str,
    session_id: Optional[str] = Query(None, description="Optional anonymous session ID"),
    session: AsyncSession = Depends(get_db),
):
    from app.services.document_service import DocumentChecklistService
    return await DocumentChecklistService.get_scheme_checklist(
        session=session,
        scheme_id=scheme_id,
        session_id=session_id,
    )


@router.get(
    "/{scheme_id}/provenance",
    response_model=SchemeProvenanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scheme Provenance & Freshness Traceability",
    description=(
        "Retrieves complete official primary-source citation metadata, relevant clauses, "
        "evidence verification status, and temporal guideline freshness analysis for a specific scheme."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Scheme not found in catalog"}
    }
)
async def get_scheme_provenance(
    scheme_id: str,
    review_due_days: int = Query(90, ge=1, le=1825, description="Custom review due threshold in days (default: 90)"),
    stale_days: int = Query(365, ge=1, le=3650, description="Custom stale threshold in days (default: 365)"),
    session: AsyncSession = Depends(get_db),
) -> SchemeProvenanceResponse:
    clean_id = scheme_id.strip()
    if not clean_id:
        raise SchemeNotFoundException(scheme_id)

    stmt = (
        select(Scheme)
        .where(
            or_(
                Scheme.id == clean_id,
                Scheme.slug == clean_id,
            )
        )
        .options(
            selectinload(Scheme.rules),
            selectinload(Scheme.documents),
        )
    )
    result = await session.execute(stmt)
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise SchemeNotFoundException(clean_id)

    config = FreshnessConfig(review_due_days=review_due_days, stale_days=stale_days)
    return FreshnessService.build_scheme_provenance(scheme=scheme, config=config)
