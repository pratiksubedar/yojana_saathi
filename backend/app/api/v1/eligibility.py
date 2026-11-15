from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Scheme
from app.schemas.eligibility import (
    EligibilityEvaluationRequest,
    EligibilityEvaluationResponse,
    SchemeEligibilityResult,
)
from app.schemas.scheme import ErrorResponse
from app.services.rule_engine import (
    DeterministicRuleEvaluator,
    MalformedRuleException,
    UnsupportedOperatorException,
)
from app.core.exceptions import SchemeNotFoundException, AppError

router = APIRouter(prefix="/eligibility", tags=["Eligibility Evaluation Engine"])


@router.post(
    "/evaluate",
    response_model=EligibilityEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Citizen Eligibility Across Schemes",
    description=(
        "Deterministically evaluates citizen profile attributes against one or multiple welfare schemes. "
        "Returns a three-state outcome (ELIGIBLE, NOT_ELIGIBLE, POSSIBLY_ELIGIBLE) with satisfied criteria, "
        "failed conditions, missing information requests, and official clause citations across English, "
        "Hindi, Kannada, and Telugu."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input attributes or unsupported operator"},
        404: {"model": ErrorResponse, "description": "Specified scheme not found"},
    }
)
async def evaluate_eligibility(
    payload: EligibilityEvaluationRequest,
    session: AsyncSession = Depends(get_db),
) -> EligibilityEvaluationResponse:
    # 1. Query requested or all active schemes
    stmt = (
        select(Scheme)
        .where(Scheme.is_active == True)
        .options(
            selectinload(Scheme.rules),
            selectinload(Scheme.documents),
        )
        .order_by(Scheme.id.asc())
    )

    if payload.scheme_ids:
        # Validate that specified schemes exist
        clean_ids = [sid.strip() for sid in payload.scheme_ids if sid.strip()]
        stmt = stmt.where(
            or_(
                Scheme.id.in_(clean_ids),
                Scheme.slug.in_(clean_ids),
            )
        )

    result = await session.execute(stmt)
    schemes = result.scalars().all()

    if payload.scheme_ids and not schemes:
        raise SchemeNotFoundException(", ".join(payload.scheme_ids))

    results: List[SchemeEligibilityResult] = []

    # 2. Evaluate each scheme deterministically
    for scheme in schemes:
        if not scheme.rules:
            continue

        primary_rule = scheme.rules[0]
        try:
            eval_result = DeterministicRuleEvaluator.evaluate_scheme(
                scheme_id=scheme.id,
                scheme_name=scheme.names,
                rule_ast=primary_rule.conditions,
                citizen_attributes=payload.citizen_attributes,
            )
            # Enrich result with full metadata for comprehensive presentation
            eval_result.ministry = scheme.ministry
            eval_result.benefits = scheme.benefits
            eval_result.official_url = scheme.official_url
            eval_result.last_verified_date = scheme.last_verified_date
            eval_result.application_procedure = scheme.application_procedure or []
            eval_result.documents = [
                {
                    "id": doc.id,
                    "names": doc.names,
                    "descriptions": doc.descriptions,
                    "is_mandatory": doc.is_mandatory,
                    "csc_assisted": doc.csc_assisted,
                    "issuer": doc.issuer,
                    "source_url": doc.source_url,
                }
                for doc in (scheme.documents or [])
            ]
            results.append(eval_result)
        except UnsupportedOperatorException as exc:
            raise AppError(status_code=400, detail=str(exc), error_code="UNSUPPORTED_OPERATOR")
        except MalformedRuleException as exc:
            raise AppError(status_code=500, detail=f"Scheme '{scheme.id}' rule is malformed: {exc}", error_code="MALFORMED_RULE")

    return EligibilityEvaluationResponse(
        results=results,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        preferred_language=payload.preferred_language,
    )


@router.post(
    "/evaluate/{scheme_id}",
    response_model=SchemeEligibilityResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Citizen Eligibility for Single Scheme",
    description="Evaluates citizen profile attributes against a specific scheme identified by ID or slug.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input attributes or unsupported operator"},
        404: {"model": ErrorResponse, "description": "Scheme not found in catalog"},
    }
)
async def evaluate_single_scheme_eligibility(
    scheme_id: str,
    payload: EligibilityEvaluationRequest,
    session: AsyncSession = Depends(get_db),
) -> SchemeEligibilityResult:
    clean_id = scheme_id.strip()
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

    if not scheme.rules:
        raise AppError(
            status_code=500,
            detail=f"Scheme '{clean_id}' has no eligibility rules configured.",
            error_code="NO_RULES_CONFIGURED",
        )

    try:
        eval_result = DeterministicRuleEvaluator.evaluate_scheme(
            scheme_id=scheme.id,
            scheme_name=scheme.names,
            rule_ast=scheme.rules[0].conditions,
            citizen_attributes=payload.citizen_attributes,
        )
        eval_result.ministry = scheme.ministry
        eval_result.benefits = scheme.benefits
        eval_result.official_url = scheme.official_url
        eval_result.last_verified_date = scheme.last_verified_date
        eval_result.application_procedure = scheme.application_procedure or []
        eval_result.documents = [
            {
                "id": doc.id,
                "names": doc.names,
                "descriptions": doc.descriptions,
                "is_mandatory": doc.is_mandatory,
                "csc_assisted": doc.csc_assisted,
                "issuer": doc.issuer,
                "source_url": doc.source_url,
            }
            for doc in (scheme.documents or [])
        ]
        return eval_result
    except UnsupportedOperatorException as exc:
        raise AppError(status_code=400, detail=str(exc), error_code="UNSUPPORTED_OPERATOR")
    except MalformedRuleException as exc:
        raise AppError(status_code=500, detail=f"Scheme '{clean_id}' rule is malformed: {exc}", error_code="MALFORMED_RULE")

