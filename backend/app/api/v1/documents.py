from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.document import (
    SchemeChecklistResponse,
    MarkChecklistItemRequest,
    ResetChecklistRequest,
    validate_uuid_format,
)
from app.schemas.scheme import ErrorResponse
from app.services.document_service import DocumentChecklistService

router = APIRouter(prefix="/documents", tags=["Document Checklist Service"])


@router.get(
    "/checklist/{scheme_id}",
    response_model=SchemeChecklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scheme Document Checklist",
    description=(
        "Retrieves authoritative document requirements for a scheme. "
        "Includes multilingual document names and guidance (en, hi, kn, te), "
        "distinguishes mandatory vs optional items, identifies CSC assisted items, "
        "and echoes collection status if an anonymous session_id (valid UUID) is provided."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Scheme not found in catalog"}
    }
)
async def get_document_checklist(
    scheme_id: str,
    session_id: Optional[str] = Query(
        None,
        description="Optional anonymous session identifier (standard UUID) to retrieve active collection status"
    ),
    lang: Optional[str] = Query(
        "en",
        description="Echoed preferred language code (en, hi, kn, te)"
    ),
    session: AsyncSession = Depends(get_db),
) -> SchemeChecklistResponse:
    clean_session = None
    if session_id is not None and session_id.strip():
        try:
            clean_session = validate_uuid_format(session_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc)
            )

    return await DocumentChecklistService.get_scheme_checklist(
        session=session,
        scheme_id=scheme_id,
        session_id=clean_session,
    )


@router.post(
    "/checklist/mark",
    response_model=SchemeChecklistResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Document as Collected (Ephemeral Session)",
    description=(
        "Marks or unmarks a document as collected in the citizen's anonymous session. "
        "Strictly zero-knowledge: does not accept or store Aadhaar numbers, bank account numbers, "
        "or actual document files."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Privacy violation or invalid request body"},
        404: {"model": ErrorResponse, "description": "Scheme or document not found"},
    }
)
async def mark_document_collected(
    payload: MarkChecklistItemRequest,
    session: AsyncSession = Depends(get_db),
) -> SchemeChecklistResponse:
    return await DocumentChecklistService.mark_document_collected(
        session=session,
        session_id=payload.session_id,
        scheme_id=payload.scheme_id,
        document_id=payload.document_id,
        is_collected=payload.is_collected,
    )


@router.post(
    "/checklist/reset",
    status_code=status.HTTP_200_OK,
    summary="Reset Ephemeral Session Checklist",
    description="Clears all ephemeral checklist marks for a given anonymous session.",
)
async def reset_checklist(
    payload: ResetChecklistRequest,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await DocumentChecklistService.reset_checklist(
        session=session,
        session_id=payload.session_id,
        scheme_id=payload.scheme_id,
    )

