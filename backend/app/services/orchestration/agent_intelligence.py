"""
Yojana Saathi - LLM Agent Intelligence Layer
Provides real LLM-powered NLU (intent, multi-scheme detection, query rewriting,
conversational continuity) and grounded response synthesis using RAG chunks
and authoritative Python RuleEngineService outcomes.
Never invents eligibility outcomes or overrides deterministic rules.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.pii_scrubber import mask_demographics_for_llm
from app.schemas.orchestration import (
    CitizenIntentEnum,
    EligibilityOrchestrationResult,
)
from app.schemas.rag import ChunkSearchResult
from app.services.llm.base import ProviderTypeEnum
from app.services.llm.gateway import LLMGateway
from app.services.llm.groq import sanitize_url
from app.services.orchestration.intent_router import IntentRouter

logger = logging.getLogger(__name__)

LANG_NAMES = {
    "en": "English",
    "hi": "Hindi (Devanagari script)",
    "kn": "Kannada (Kannada script)",
    "te": "Telugu (Telugu script)",
}

SPECIFIC_DETAIL_MARKERS = [
    "phone number", "mobile number", "contact number", "helpline",
    "district office", "address", "pin code", "pincode", "email",
    "grievance", "tumakuru", "officer name", "nodal officer",
    "last date", "deadline", "next installment date",
]


def check_evidence_sufficiency(query: str, results: List[ChunkSearchResult]) -> bool:
    """
    Checks whether retrieved RAG chunks actually contain evidence for specific
    factual queries (e.g., local office phone numbers, specific city names, deadlines).
    Returns False if the user asks for specific local/contact/date details absent from all chunks.
    """
    lower_q = (query or "").lower()
    matched_markers = [m for m in SPECIFIC_DETAIL_MARKERS if m in lower_q]
    if not matched_markers:
        return True

    if not results:
        return False

    combined_chunks = " ".join((r.chunk.content or "").lower() for r in results)

    # Verify at least one of the specific markers or a phone-number pattern appears in chunks
    has_marker_in_chunks = any(m in combined_chunks for m in matched_markers)
    has_phone_in_chunks = bool(re.search(r"\b\d{10,11}\b|\b1800[-\s]?\d+", combined_chunks))
    return has_marker_in_chunks or has_phone_in_chunks


class AgentIntelligenceService:
    """
    Coordinates LLMGateway for NLU and grounded synthesis with strict fallback tracking.
    """

    def __init__(self, gateway: Optional[LLMGateway] = None):
        self.gateway = gateway or LLMGateway()

    async def understand_turn(
        self,
        message: str,
        language: str,
        history: List[Dict[str, str]],
        active_profile: Dict[str, Any],
        pending_question: Optional[Dict[str, Any]],
        selected_scheme_id: Optional[str],
        candidate_scheme_ids: Optional[List[str]] = None,
        conversation_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Uses real LLM when configured & reachable for NLU; falls back to IntentRouter otherwise.
        Returns a dict with:
          intent, target_scheme_ids, search_query, language, is_comparison,
          actual_llm_inference, llm_provider, llm_model, fallback_reason
        """
        configured_provider, configured_model = self.gateway.get_configured_provider_info()

        # Always compute deterministic baseline first for safety & comparison
        det_intent_res = IntentRouter.classify(message=message, current_language=language)
        det_scheme_ids = IntentRouter.detect_scheme_ids(message)
        is_comparison = any(
            kw in message.lower()
            for kw in ["compare", "comparison", "difference", "vs", "versus", "better between", "तुलना", "अंतर", "ಹೋಲಿಕೆ", "ವ್ಯತ್ಯಾಸ", "పోలిక", "తేడా"]
        )

        # If no real LLM is configured, return deterministic NLU honestly
        if not self.gateway.is_real_llm_configured():
            return {
                "intent": det_intent_res.intent,
                "target_scheme_ids": det_scheme_ids,
                "search_query": message,
                "language": det_intent_res.detected_language or language,
                "is_comparison": is_comparison,
                "actual_llm_inference": False,
                "llm_provider": configured_provider,
                "llm_model": configured_model,
                "fallback_reason": "LLM_PRIMARY_PROVIDER is set to deterministic",
            }

        # Real LLM NLU call with strict demographic privacy masking
        system_prompt = (
            "You are the NLU router for Yojana Saathi, a multilingual Indian government welfare scheme assistant.\n"
            "Analyze the citizen's latest message using the conversation history, pending question, and active context.\n"
            "Output ONLY valid JSON with these keys:\n"
            '- "intent": one of ["SCHEME_DISCOVERY", "SCHEME_INFORMATION", "ELIGIBILITY_CHECK", "DOCUMENT_REQUIREMENTS", "APPLICATION_GUIDANCE", "GENERAL_HELP", "UNSUPPORTED_QUERY"]\n'
            '- "target_scheme_ids": array of lowercase scheme IDs mentioned or implied (e.g. ["pm-kisan", "pm-kmy"]), or []\n'
            '- "is_comparison": boolean (true if comparing 2+ schemes)\n'
            '- "search_query": concise English search query capturing the core scheme/welfare topic for RAG retrieval\n'
            '- "language": one of ["en", "hi", "kn", "te"]\n'
            "Rules:\n"
            "- If the user refers to an ordinal scheme (e.g. 'the second one', 'the first scheme', 'the 3rd one', 'दूसरा', 'ಎರಡನೇ', 'రెండవ'), map it to the corresponding scheme ID from the candidate schemes or conversation history.\n"
            "- If the user is answering a pending clarification question (e.g. giving income, age, land, state, or yes/no), keep the active scheme/intent (ELIGIBILITY_CHECK or SCHEME_DISCOVERY).\n"
            "- Never invent scheme IDs not from India's central welfare schemes.\n"
            "- Only mark UNSUPPORTED_QUERY for clearly non-welfare topics (cricket, movies, crypto, recipes, etc.)."
        )

        # Privacy hardening: Mask raw demographic attributes from dialogue history and latest message
        history_str = "\n".join(
            f"{t.get('role', 'user')}: {mask_demographics_for_llm(t.get('content', '')[:300])}"
            for t in history[-6:]
        ) or "None"

        masked_message = mask_demographics_for_llm(message, active_profile)

        summary_prefix = f"Prior conversation summary:\n{conversation_summary}\n\n" if conversation_summary else ""

        prompt = (
            f"{summary_prefix}Recent conversation:\n{history_str}\n\n"
            f"Currently selected scheme: {selected_scheme_id or 'None'}\n"
            f"Candidate schemes in context: {json.dumps(candidate_scheme_ids) if candidate_scheme_ids else 'None'}\n"
            f"Pending question asked to user: {json.dumps(pending_question) if pending_question else 'None'}\n"
            f"Preferred UI language: {language}\n"
            f"Latest citizen message: {masked_message}\n\n"
            "Return ONLY valid JSON."
        )

        try:
            llm_resp = await self.gateway.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=300,
                temperature=0.0,
                timeout_seconds=getattr(settings, "groq_nlu_timeout_seconds", getattr(settings, "gemini_nlu_timeout_seconds", 6.0)),
            )
            if llm_resp.provider == ProviderTypeEnum.DETERMINISTIC:
                return {
                    "intent": det_intent_res.intent,
                    "target_scheme_ids": det_scheme_ids,
                    "search_query": message,
                    "language": det_intent_res.detected_language or language,
                    "is_comparison": is_comparison,
                    "actual_llm_inference": False,
                    "llm_provider": llm_resp.provider.value,
                    "llm_model": llm_resp.model,
                    "fallback_reason": "; ".join(llm_resp.fallback_chain) or "LLM provider unavailable",
                }

            raw = llm_resp.text.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            parsed = json.loads(raw)
            raw_intent = str(parsed.get("intent", det_intent_res.intent.value)).upper()
            try:
                parsed_intent = CitizenIntentEnum(raw_intent)
            except ValueError:
                parsed_intent = det_intent_res.intent

            parsed_schemes = parsed.get("target_scheme_ids") or []
            if not isinstance(parsed_schemes, list):
                parsed_schemes = det_scheme_ids
            clean_schemes = [str(s).strip().lower() for s in parsed_schemes if s]
            # Merge deterministic scheme hits so explicit scheme names are never lost
            for s in det_scheme_ids:
                if s not in clean_schemes:
                    clean_schemes.append(s)

            parsed_lang = str(parsed.get("language", "")).strip().lower()
            if parsed_lang not in ("en", "hi", "kn", "te"):
                parsed_lang = det_intent_res.detected_language or language

            return {
                "intent": parsed_intent,
                "target_scheme_ids": clean_schemes,
                "search_query": str(parsed.get("search_query") or message).strip(),
                "language": parsed_lang,
                "is_comparison": bool(parsed.get("is_comparison", is_comparison)),
                "actual_llm_inference": True,
                "llm_provider": llm_resp.provider.value,
                "llm_model": llm_resp.model,
                "fallback_reason": None,
            }
        except Exception as exc:
            err_msg = sanitize_url(f"{type(exc).__name__}: {str(exc)[:100]}")
            logger.warning(f"LLM NLU failed ({err_msg}); falling back to deterministic NLU.")
            return {
                "intent": det_intent_res.intent,
                "target_scheme_ids": det_scheme_ids,
                "search_query": message,
                "language": det_intent_res.detected_language or language,
                "is_comparison": is_comparison,
                "actual_llm_inference": False,
                "llm_provider": configured_provider,
                "llm_model": configured_model,
                "fallback_reason": err_msg,
            }

    async def synthesize_response(
        self,
        message: str,
        language: str,
        intent: CitizenIntentEnum,
        history: List[Dict[str, str]],
        active_profile: Dict[str, Any],
        rag_results: List[ChunkSearchResult],
        has_sufficient_evidence: bool,
        eligibility_result: Optional[EligibilityOrchestrationResult] = None,
        candidate_evaluations: Optional[List[EligibilityOrchestrationResult]] = None,
        profile_conflicts: Optional[List[Dict[str, Any]]] = None,
        is_comparison: bool = False,
        conversation_summary: Optional[str] = None,
    ) -> Tuple[Optional[str], bool, str, str, Optional[str]]:
        """
        Synthesizes a natural, grounded conversational response using the real LLM.
        Returns: (text_or_None, actual_llm_inference, provider_name, model_name, fallback_reason)
        """
        configured_provider, configured_model = self.gateway.get_configured_provider_info()
        if not self.gateway.is_real_llm_configured():
            return None, False, configured_provider, configured_model, "LLM_PRIMARY_PROVIDER is set to deterministic"

        lang_label = LANG_NAMES.get(language, "English")

        system_prompt = (
            "You are Yojana Saathi (योजना साथी), a helpful, trustworthy multilingual voice-first AI agent "
            "for discovering Indian government welfare schemes.\n"
            f"Respond ONLY in {lang_label}.\n"
            "STRICT GROUNDING RULES:\n"
            "1. Python RuleEngineService is the SOLE authority for eligibility decisions. NEVER contradict or override its status "
            "(ELIGIBLE, NOT_ELIGIBLE, NEEDS_MORE_INFORMATION, NOT_VERIFIED), satisfied conditions, failed conditions, or unresolved criteria.\n"
            "2. Use ONLY facts present in the Verified RAG Scheme Context and RuleEngineService Output below.\n"
            "3. NEVER fabricate benefit amounts, phone numbers, office addresses, deadlines, or official URLs.\n"
            "4. If 'has_sufficient_evidence' is false or the retrieved context does not contain the specific detail requested, "
            "explicitly say that this specific information is not available in your verified scheme records and advise checking the official portal.\n"
            "5. If eligibility status is NEEDS_MORE_INFORMATION, ask at most ONE clear, natural follow-up question for the top missing detail.\n"
            "6. Keep responses clear, conversational, and well-structured with markdown headings or bullets where helpful.\n"
            "7. If a PROFILE CONFLICT NOTICE is present, politely acknowledge that the citizen's newly stated value differs from their saved profile, explain that this check used the new value, and ask if they would like to update their profile."
        )

        # Assemble grounded context
        rag_context_blocks = []
        for idx, r in enumerate(rag_results[:6], start=1):
            c = r.chunk
            rag_context_blocks.append(
                f"[Chunk {idx} | scheme={c.scheme_id} | category={c.category.value} | title={c.provenance.document_title} | url={c.provenance.source_url}]\n"
                f"{c.content}"
            )
        rag_context = "\n\n".join(rag_context_blocks) or "No matching scheme chunks retrieved."

        eval_blocks = []
        if eligibility_result:
            eval_blocks.append(eligibility_result.model_dump(exclude={"citations"}))
        for ev in (candidate_evaluations or []):
            eval_blocks.append(ev.model_dump(exclude={"citations"}))

        # Privacy hardening: Mask raw demographic attributes from dialogue history and latest message
        history_str = "\n".join(
            f"{t.get('role', 'user')}: {mask_demographics_for_llm(t.get('content', '')[:300])}"
            for t in history[-6:]
        ) or "None"

        masked_message = mask_demographics_for_llm(message, active_profile)

        # Build conflict section if user supplied a correction to an existing confirmed profile
        conflict_section = ""
        if profile_conflicts:
            c_lines = []
            for c in profile_conflicts:
                f_name = str(c.get("field", "")).replace("_", " ").title()
                c_lines.append(
                    f"- {f_name}: citizen stated '{c.get('new_value')}', saved profile had '{c.get('confirmed_value')}'."
                )
            conflict_section = f"=== PROFILE CONFLICT NOTICE ===\n" + "\n".join(c_lines) + "\n\n"

        summary_prefix = f"Prior Conversation Summary:\n{conversation_summary}\n\n" if conversation_summary else ""

        # Privacy minimization: Send ONLY eligibility rule outcome statuses (e.g. ELIGIBLE / NEEDS_MORE_INFORMATION)
        # and missing prompt questions. NEVER send the citizen's personal profile (age, income, land, caste, gender).
        prompt = (
            f"{summary_prefix}Recent Conversation:\n{history_str}\n\n"
            f"Citizen's Latest Message: {masked_message}\n"
            f"Classified Intent: {intent.value} (is_comparison={is_comparison})\n"
            f"Has Sufficient Evidence for Specific Query: {has_sufficient_evidence}\n\n"
            f"{conflict_section}"
            f"=== VERIFIED RAG SCHEME CONTEXT ===\n{rag_context}\n\n"
            f"=== AUTHORITATIVE PYTHON RULE ENGINE OUTCOMES (NO CITIZEN PROFILE) ===\n{json.dumps(eval_blocks, ensure_ascii=False)}\n\n"
            f"Write a helpful, accurate, grounded response in {lang_label}."
        )

        try:
            llm_resp = await self.gateway.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=900,
                temperature=0.2,
                timeout_seconds=getattr(settings, "groq_synthesis_timeout_seconds", getattr(settings, "gemini_synthesis_timeout_seconds", 7.0)),
            )
            if llm_resp.provider == ProviderTypeEnum.DETERMINISTIC or not llm_resp.text.strip():
                return (
                    None,
                    False,
                    llm_resp.provider.value,
                    llm_resp.model,
                    "; ".join(llm_resp.fallback_chain) or "LLM fallback to deterministic",
                )
            return llm_resp.text.strip(), True, llm_resp.provider.value, llm_resp.model, None
        except Exception as exc:
            err_msg = sanitize_url(f"{type(exc).__name__}: {str(exc)[:100]}")
            logger.warning(f"LLM synthesis failed ({err_msg}); falling back to deterministic synthesizer.")
            return None, False, configured_provider, configured_model, err_msg

