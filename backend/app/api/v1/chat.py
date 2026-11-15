"""
Yojana Saathi - Conversational Chat & Streaming API Router
Milestone 6.4: Production-grade chat endpoints connecting frontend React clients
to the ConversationalOrchestrator with Server-Sent Events (SSE) streaming,
strict PII scrubbing, ephemeral session management, and zero secret leakage.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.exceptions import AppError
from app.core.pii_scrubber import scrub_pii
from app.schemas.chat import (
    ChatRequest,
    ChatResetRequest,
    ChatResetResponse,
    ChatResponse,
    ChatTranslateRequest,
    ChatTranslateResponse,
)
from app.services.orchestration.orchestrator import ConversationalOrchestrator
from app.services.translation_service import translate_assistant_text, translate_text_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Conversational Chat"])

# Process-level singleton orchestrator maintaining ephemeral session cache
_orchestrator: Optional[ConversationalOrchestrator] = None


def get_orchestrator() -> ConversationalOrchestrator:
    """Provides singleton conversational orchestrator with in-memory session profile store."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ConversationalOrchestrator()
    return _orchestrator


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Citizen Conversational Message Turn",
    description="Processes a multi-turn citizen query, performs intent routing, slot extraction, RAG retrieval, and deterministic eligibility evaluation.",
)
async def chat_message_turn(
    request: ChatRequest,
    orchestrator: ConversationalOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """
    Standard synchronous chat endpoint returning complete structured response with citations.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # 1. Defense-in-depth PII scrubbing before processing
    sanitized_message = scrub_pii(request.message)

    # 2. Pre-select scheme if explicitly provided
    if request.scheme_id:
        orchestrator.session_manager.set_scheme(session_id, request.scheme_id.strip())

    # 3. Process conversational turn
    try:
        response = await orchestrator.process_message(
            session_id=session_id,
            message=sanitized_message,
            language=request.language,
            citizen_profile=request.citizen_profile,
        )
    except Exception as exc:
        logger.error(f"Error in chat_message_turn: {type(exc).__name__}")
        raise AppError(
            status_code=500,
            detail="An error occurred while evaluating your welfare inquiry. Please try again.",
            error_code="ORCHESTRATION_ERROR",
        )

    return ChatResponse(
        session_id=session_id,
        message=response.message,
        intent=response.intent,
        language=response.language,
        scheme_id=response.scheme_id,
        eligibility_result=response.eligibility_result,
        candidate_evaluations=response.candidate_evaluations,
        profile_conflicts=response.profile_conflicts,
        citations=response.citations,
        formatted_citations_markdown=response.formatted_citations_markdown,
        suggested_followups=response.suggested_followups,
        active_profile=response.active_profile,
        diagnostics=response.diagnostics,
    )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Citizen Conversational Streaming Turn (SSE)",
    description="Streams citizen response incrementally using Server-Sent Events (SSE). Emits typed events: metadata, token, citations, eligibility, followups, done, error.",
)
async def chat_message_stream(
    request: ChatRequest,
    raw_request: Request,
    orchestrator: ConversationalOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) streaming endpoint.
    Maintains citation grounding and client disconnect detection.
    """
    session_id = request.session_id or str(uuid.uuid4())
    sanitized_message = scrub_pii(request.message)

    if request.scheme_id:
        orchestrator.session_manager.set_scheme(session_id, request.scheme_id.strip())

    async def sse_event_generator() -> AsyncIterator[str]:
        # 1. Check for immediate client disconnection
        if await raw_request.is_disconnected():
            logger.info("Client disconnected before stream start")
            return

        try:
            # 2. Execute authoritative orchestration
            response = await orchestrator.process_message(
                session_id=session_id,
                message=sanitized_message,
                language=request.language,
                citizen_profile=request.citizen_profile,
            )

            # 3. Emit metadata event
            metadata_payload = {
                "session_id": session_id,
                "intent": response.intent.value if hasattr(response.intent, "value") else str(response.intent),
                "language": response.language,
                "scheme_id": response.scheme_id,
                "diagnostics": response.diagnostics.model_dump() if response.diagnostics else None,
            }
            yield f"event: metadata\ndata: {json.dumps(metadata_payload)}\n\n"

            # 4. Emit citations event early if present (grounding established before tokens stream)
            if response.citations:
                citations_payload = {
                    "citations": [c.model_dump() for c in response.citations],
                    "formatted_markdown": response.formatted_citations_markdown,
                }
                yield f"event: citations\ndata: {json.dumps(citations_payload)}\n\n"

            # 5. Emit eligibility event early if present (statutory assessment established before tokens stream)
            if response.eligibility_result:
                elig_payload = response.eligibility_result.model_dump()
                yield f"event: eligibility\ndata: {json.dumps(elig_payload)}\n\n"

            # 6. Stream grounded response text chunks
            # Chunk by words to simulate natural streaming without sacrificing integrity
            full_text = response.message
            words = full_text.split(" ")
            chunk_size = 3

            for i in range(0, len(words), chunk_size):
                if await raw_request.is_disconnected():
                    logger.info("Client disconnected mid-stream")
                    return

                chunk = " ".join(words[i : i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "

                token_payload = {"delta": chunk}
                yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                await asyncio.sleep(0.02)  # Natural reading pacing

            # 7. Emit followups event if present
            if response.suggested_followups:
                followup_payload = {"items": response.suggested_followups}
                yield f"event: followups\ndata: {json.dumps(followup_payload)}\n\n"

            # 8. Emit active profile summary event
            if response.active_profile or response.profile_conflicts:
                profile_payload = {
                    "active_profile": response.active_profile,
                    "profile_conflicts": response.profile_conflicts,
                }
                yield f"event: profile\ndata: {json.dumps(profile_payload)}\n\n"

            # 9. Emit completion done event
            done_payload = {"session_id": session_id, "complete": True}
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

        except Exception as exc:
            logger.error(f"Streaming error: {type(exc).__name__}")
            err_payload = {
                "detail": "An error occurred during conversational streaming. Please retry.",
                "error_code": "STREAMING_ERROR",
            }
            yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/reset",
    response_model=ChatResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Ephemeral Chat Session",
    description="Explicitly resets and clears citizen demographic attributes for an active session.",
)
async def reset_chat_session(
    request: ChatResetRequest,
    orchestrator: ConversationalOrchestrator = Depends(get_orchestrator),
) -> ChatResetResponse:
    """
    Clears all accumulated profile attributes in ephemeral memory.
    """
    orchestrator.session_manager.reset_profile(request.session_id)
    return ChatResetResponse(
        session_id=request.session_id,
        status="reset_successful",
        message="Session profile cleared. New session ready.",
    )


@router.post(
    "/translate",
    response_model=ChatTranslateResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate Assistant Chat Message",
    description="Translates assistant messages into the requested language (en, hi, kn, te), preserving numbers, currency, and scheme names with caching.",
)
async def translate_chat_message(
    request: ChatTranslateRequest,
) -> ChatTranslateResponse:
    """Translates a message to the requested language while preserving official terminology."""
    translated, was_cached, is_translated = await translate_text_async(
        text=request.text,
        target_language=request.target_language,
        source_language=request.source_language,
    )
    return ChatTranslateResponse(
        translated_text=translated,
        target_language=request.target_language,
        source_language=request.source_language,
        cached=was_cached,
        is_translated=is_translated,
    )

