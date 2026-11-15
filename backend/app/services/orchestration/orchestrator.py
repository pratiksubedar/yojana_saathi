"""
Yojana Saathi - Master Conversational Orchestrator
Integrates LLM-first NLU & grounded synthesis, multilingual intent routing,
strict typed slot extraction, ephemeral session profile & dialogue memory,
local RAG retrieval with provenance citations, authoritative deterministic
rule engine evaluation, and PII-safe per-request observability.
"""

import json
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.eligibility import EligibilityStatusEnum
from app.schemas.orchestration import (
    CitizenIntentEnum,
    EligibilityOrchestrationResult,
    RequestDiagnostics,
    SynthesizedResponse,
    ValidationResult,
)
from app.schemas.rag import (
    ChunkCategoryEnum,
    ChunkSearchResult,
    ProvenanceCitation,
    RAGRetrievalRequest,
)
from app.services.orchestration.agent_intelligence import (
    AgentIntelligenceService,
    check_evidence_sufficiency,
)
from app.services.orchestration.attribute_extractor import AttributeExtractor
from app.services.orchestration.eligibility_orchestrator import EligibilityOrchestrator
from app.services.orchestration.response_synthesizer import ResponseSynthesizer
from app.services.orchestration.session_manager import SessionProfileManager
from app.services.rag_retriever_service import RAGRetrieverService

logger = logging.getLogger(__name__)

AFFIRMATIVE_PHRASES = {
    "yes", "yeah", "yep", "yup", "yes i do", "yes, i do", "i do", "yes i am", "yes, i am",
    "i am", "yes we do", "yes, we do", "we do", "true", "correct", "right", "sure", "of course",
    "haan", "ha", "haan ji", "ji haan", "sahi", "bilkul", "हाँ", "हां", "हाँ जी", "जी हाँ", "जी हां", "सही", "बिल्कुल",
    "ಹೌದು", "ಖಂಡಿತ", "ಹೌದು ನಾನು", "ಹೌದು ಇದೆ", "haudu", "houdu",
    "అవును", "అవును నేను", "ఉంది", "నిజం", "avunu",
}
NEGATIVE_PHRASES = {
    "no", "nope", "nah", "no i don't", "no, i don't", "i don't", "no i do not", "no, i do not",
    "i do not", "no i am not", "no, i am not", "i am not", "no we don't", "no, we don't",
    "we don't", "false", "never", "not at all",
    "nahi", "nahin", "nahi ji", "ji nahi", "galat", "नहीं", "ना", "नहीं जी", "जी नहीं", "गलत",
    "ಇಲ್ಲ", "ಅಲ್ಲ", "ಇಲ್ಲ ನಾನು", "illa", "alla",
    "కాదు", "లేదు", "కాదు నేను", "kadu", "ledu",
}

ORDINAL_MAP = {
    "first": 0, "1st": 0, "पहला": 0, "पहला वाला": 0, "ಮೊದಲ": 0, "ಮೊದಲನೆಯ": 0, "ಮೊದಟಿ": 0, "ఒకటి": 0,
    "second": 1, "2nd": 1, "दूसरा": 1, "दूसरा वाला": 1, "ಎರಡನೇ": 1, "ಎರಡನೆಯ": 1, "రెండవ": 1, "రెండు": 1,
    "third": 2, "3rd": 2, "तीसरा": 2, "तीसरा वाला": 2, "ಮೂರನೇ": 2, "ಮೂರನೆಯ": 2, "మూడవ": 2, "మూడు": 2,
    "fourth": 3, "4th": 3, "चौथा": 3, "ನಾಲ್ಕನೇ": 3, "ನಾಲ್ಕನೆಯ": 3, "నాల్గవ": 3,
}


def parse_boolean_response(text: str) -> Optional[bool]:
    """
    Robustly parses affirmative and negative responses across supported languages.
    Returns True for affirmative, False for negative, and None for arbitrary messages.
    """
    if not text:
        return None
    raw = text.strip().lower().rstrip(".!?")
    if raw in AFFIRMATIVE_PHRASES:
        return True
    if raw in NEGATIVE_PHRASES:
        return False
    clean = re.sub(r"[^\w\s]", "", raw).strip()
    if clean in AFFIRMATIVE_PHRASES:
        return True
    if clean in NEGATIVE_PHRASES:
        return False
    return None


def resolve_ordinal_scheme(message: str, candidate_schemes: List[str]) -> Optional[str]:
    """
    Resolves ordinal scheme references ('the second one', 'explain 2nd', 'दूसरा वाला')
    against recently discovered candidate schemes.
    """
    if not candidate_schemes:
        return None
    msg_clean = message.lower()
    for word, idx in ORDINAL_MAP.items():
        if re.search(r"\b" + re.escape(word) + r"\b", msg_clean) or word in msg_clean:
            if 0 <= idx < len(candidate_schemes):
                return candidate_schemes[idx]
    return None


def resolve_anaphoric_scheme(
    message: str,
    selected_scheme_id: Optional[str],
    candidate_schemes: List[str],
) -> Optional[str]:
    """
    Resolves pronoun / anaphoric scheme references ('that scheme', 'this scheme', 'it',
    'what about this', 'am I eligible for it', 'us yojana') to the active or top candidate scheme.
    """
    clean = message.lower().strip()
    ord_id = resolve_ordinal_scheme(message, candidate_schemes)
    if ord_id:
        return ord_id

    anaphoric_patterns = [
        r"\b(?:that|this|the)\s+(?:scheme|yojana|program)\b",
        r"\b(?:about|for)\s+(?:that|this|it)\b",
        r"\b(?:tell\s+me\s+)?(?:about|details?\s+of)\s+(?:that|this|it)\b",
        r"\b(?:am\s+i|are\s+we)\s+eligible\b",
        r"\bcan\s+i\s+(?:get|apply\s+for)\s+(?:it|this|that)\b",
        r"\b(?:what\s+(?:are\s+the\s+)?|which\s+)?documents?\b",
        r"\bhow\s+(?:do\s+i|can\s+i|to)\s+apply\b",
        r"\bwhat\s+about\s+(?:this|that)\b",
        # Hindi
        r"उस\s+योजना", r"इस\s+योजना", r"इसके\s+बारे", r"उसके\s+बारे",
        r"क्या\s+मैं\s+पात्र", r"दस्तावेज", r"आवेदन",
        # Kannada
        r"ಆ\s+ಯೋಜನೆ", r"ಈ\s+ಯೋಜನೆ", r"ಇದರ\s+ಬಗ್ಗೆ", r"ಅದರ\s+ಬಗ್ಗೆ",
        r"ಅರ್ಹ", r"ದಾಖಲೆ", r"ಅರ್ಜಿ",
        # Telugu
        r"ఆ\s+పథకం", r"ఈ\s+పథకం", r"దీని\s+గురించి", r"దాని\s+గురించి",
        r"అర్హు", r"పత్రాలు", r"దరఖాస్తు",
    ]
    if any(re.search(pat, clean) for pat in anaphoric_patterns):
        if selected_scheme_id:
            return selected_scheme_id
        if candidate_schemes:
            return candidate_schemes[0]
    return None


BOOLEAN_PROFILE_FIELDS = {
    "owns_agricultural_land", "has_bpl_card", "has_nfsa_priority_or_secc_entitlement",
    "pays_income_tax", "is_pregnant_or_lactating", "owns_motorized_three_or_four_wheeler",
    "owns_unirrigated_land_gte_5_acres", "is_institutional_landholder",
    "has_water_source_for_irrigation", "has_existing_grid_connected_agri_pump",
    "is_regular_govt_employee", "has_regular_govt_job", "is_registered_professional",
    "is_enrolled_in_other_pension_nps_esic_epfo", "is_enrolled_in_pm_sym_or_pm_lvm",
    "is_constitutional_post_holder_or_elected_representative",
    "is_mts_or_class_iv_or_group_d_employee", "receives_formal_paid_maternity_benefits",
    "has_willful_bank_default", "owns_pucca_house", "has_eshram_or_mgnrega_card",
    "has_government_health_insurance", "has_savings_account",
    "is_bank_defaulter", "is_tenant_farmer", "is_allied_activity_worker", "is_shg_or_jlg_farmer"
}


def parse_pending_slot_value(field: str, message: str) -> Optional[Any]:
    """
    Extracts a typed value for a specific pending profile slot when a citizen
    answers a clarification question with a short numeric or text answer.
    Guarantees that yes/no answers are accepted ONLY for genuine boolean fields.
    """
    if not message:
        return None
    clean = message.strip().lower()

    # 1. Boolean field check: strictly only for fields that expect boolean
    if field in BOOLEAN_PROFILE_FIELDS:
        if field == "is_bank_defaulter":
            if any(w in clean for w in ["no default", "not a defaulter", "never defaulted", "clean", "no loan default", "డిఫాల్ట్ లేదు", "ಸುಸ್ತಿದಾರನಲ್ಲ", "डिफ़ॉल्ट नहीं"]):
                return False
            if any(w in clean for w in ["bank defaulter", "loan default", "defaulter", "have default", "డిఫాల్ట్ ఉంది", "ಸುಸ್ತಿದಾರ", "डिफ़ॉल्ट है"]):
                return True
        if field == "owns_agricultural_land":
            if any(w in clean for w in ["own agricultural land", "landowner", "owner cultivator", "own land"]):
                return True
        if field == "is_tenant_farmer":
            if any(w in clean for w in ["cultivate land as a tenant", "tenant", "sharecropper", "oral lessee"]):
                return True
        if field == "is_allied_activity_worker":
            if any(w in clean for w in ["animal husbandry", "dairy", "poultry", "fisheries", "allied"]):
                return True
        bool_val = parse_boolean_response(clean)
        if bool_val is not None:
            return bool_val

    # 1b. Farmer type & agricultural activity categories
    if field in ("farmer_type", "kcc_activity_category"):
        if any(w in clean for w in ["own agricultural land", "landowner", "owner cultivator", "own land"]):
            return "Landowner"
        if any(w in clean for w in ["cultivate land as a tenant", "tenant", "sharecropper", "oral lessee"]):
            return "Tenant"
        if any(w in clean for w in ["animal husbandry", "dairy", "poultry", "fisheries", "allied"]):
            return "Allied"

    # 2. Landholding (hectares / acres)
    if field == "landholding_hectares":
        if any(p in clean for p in ["no land", "don't have land", "do not have land", "landless", "भूमिहीन", "ಭೂಹೀನ", "భూమిలేని"]):
            return None
        if any(p in clean for p in ["less than 2", "under 2", "2 एकड़ से कम", "2 ಎಕರೆಗಿಂತ ಕಡಿಮೆ", "2 ఎకరాల కంటే తక్కువ"]):
            return 0.6  # ~1.5 acres in hectares
        if any(p in clean for p in ["2 to 5", "2-5", "2 से 5", "2 ರಿಂದ 5", "2 నుండి 5"]):
            return 1.4  # ~3.5 acres in hectares
        if any(p in clean for p in ["more than 5", "above 5", "5 एकड़ से अधिक", "5 ಎಕರೆಗಿಂತ ಹೆಚ್ಚು", "5 ఎకరాల కంటే ఎక్కువ"]):
            return 3.0  # ~7.4 acres in hectares
        norm = clean
        for w_num, d_num in [
            ("one", "1"), ("two", "2"), ("three", "3"), ("four", "4"), ("five", "5"),
            ("एक", "1"), ("दो", "2"), ("तीन", "3"), ("ಒಂದು", "1"), ("ಎರಡು", "2"),
            ("ఒక", "1"), ("రెండు", "2")
        ]:
            norm = re.sub(rf"\b{w_num}\s*(?=acres?|hectares?|एकड़|ಎಕರೆ|ఎకరాలు)", f"{d_num} ", norm)
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hectares?|hectors?|हेक्टेयर|ಹೆಕ್ಟೇರ್|హెక్టార్లు|acres?|एकड़|ಎಕರೆ|ఎకరాలు)?", norm)
        if m:
            val = float(m.group(1))
            if any(unit in norm for unit in ["acre", "acres", "एकड़", "ಎಕರೆ", "ఎకరాలు"]):
                val = round(val * 0.404686, 2)
            return val

    # 3. Age (years)
    if field == "age":
        if any(w in clean for w in ["18 - 40", "18 to 40", "18-40"]):
            return 28
        if any(w in clean for w in ["41 - 59", "41 to 59", "41-59"]):
            return 48
        if any(w in clean for w in ["60+", "60 plus", "senior", "वरिष्ठ", "ಹಿರಿಯ", "సీనియర్"]):
            return 65
        corr = re.search(r"\b(?:actually\s*,?\s*)?(?:i am|i'm|im|my age is|age is)?\s*(\d{1,3})\s*(?:,\s*)?(?:not|aur nahi)\s*(\d{1,3})\b", clean)
        if corr:
            val = int(corr.group(1))
            if 0 <= val <= 120:
                return val
        m = re.search(r"(\d{1,3})\s*(?:years?|yrs?|साल|ವರ್ಷ|సంవత్సరాలు)?", clean)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 120:
                return val

    # 4. Annual / Monthly Income
    if field in ("annual_income_inr", "household_monthly_income_inr"):
        if any(w in clean for w in ["under 1.5", "under 1.5 lakh", "less than 1.5", "1.5 लाख से कम", "1.5 ಲಕ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ"]):
            return 100000.0
        if any(w in clean for w in ["1.5 - 3", "1.5 to 3", "1.5-3"]):
            return 200000.0
        if any(w in clean for w in ["3 - 8", "3 to 8", "3-8"]):
            return 500000.0
        if any(w in clean for w in ["above 8", "more than 8", "8 lakh se adhik", "8 लाख से अधिक"]):
            return 1000000.0
        clean_num = re.sub(r"(\d),(\d)", r"\1\2", clean)
        m_lakh = re.search(r"(\d+(?:\.\d+)?)\s*lakh", clean_num)
        if m_lakh:
            return float(m_lakh.group(1)) * 100000.0
        m_num = re.search(r"(\d{4,8})", clean_num)
        if m_num:
            return float(m_num.group(1))

    # 5. Completed ANC checkups
    if field == "anc_checkups_completed":
        m = re.search(r"(\d{1,2})", clean)
        if m:
            return int(m.group(1))

    # 6. Occupation
    if field == "occupation":
        if any(w in clean for w in ["farmer", "farming", "agriculture", "किसान", "खेती", "ರೈತ", "ಕೃಷಿ", "రైతు", "వ్యవసాయ", "kisaan", "raitha", "raithu"]):
            return "Farmer"
        if any(w in clean for w in ["street vendor", "vendor", "hawker", "वेंडर", "फेरीवाला", "ಬೀದಿ ವ್ಯಾಪಾರಿ", "వీధి ವ್ಯಾಪಾರಿ", "thela", "vyapari"]):
            return "Street Vendor"
        if any(w in clean for w in ["laborer", "labourer", "worker", "मजदूर", "ಕೂಲಿ", "కూలీ", "kooli", "mazdoor"]):
            return "Laborer"

    # 7. State
    if field == "state":
        if any(w in clean for w in ["karnataka", "ಕರ್ನಾಟಕ", "कर्नाटक", "కర్ణాటక"]):
            return "Karnataka"
        if any(w in clean for w in ["andhra pradesh", "ಆಂಧ್ರ ಪ್ರದೇಶ", "आंध्र प्रदेश", "ఆంధ్రప్రదేశ్"]):
            return "Andhra Pradesh"
        if any(w in clean for w in ["telangana", "ತೆಲಂಗಾಣ", "तेलंगाना", "తెలంగాణ"]):
            return "Telangana"
        if any(w in clean for w in ["tamil nadu", "ತಮಿಳುನಾಡು", "तमिलनाडु", "తమిళనాడు"]):
            return "Tamil Nadu"
        if any(w in clean for w in ["maharashtra", "ಮಹಾರಾಷ್ಟ್ರ", "महाराष्ट्र", "మహారాష్ట్ర"]):
            return "Maharashtra"
        if any(w in clean for w in ["uttar pradesh", "ಉತ್ತರ ಪ್ರದೇಶ", "उत्तर प्रदेश", "ఉత్తరప్రదేశ్"]):
            return "Uttar Pradesh"
        if any(w in clean for w in ["bihar", "ಬಿಹಾರ", "बिहार", "బీహార్"]):
            return "Bihar"
        if any(w in clean for w in ["delhi", "ದೆಹಲಿ", "दिल्ली", "ఢిల్లీ"]):
            return "Delhi"
        for st in [
            "karnataka", "andhra pradesh", "telangana", "maharashtra", "tamil nadu",
            "uttar pradesh", "bihar", "delhi", "madhya pradesh", "rajasthan",
            "gujarat", "punjab", "haryana", "kerala", "west bengal", "odisha",
        ]:
            if st in clean:
                return st.title()

    # 8. Gender
    if field == "gender":
        if any(w in clean for w in ["female", "woman", "महिला", "ಮಹಿಳೆ", "మహిళ"]):
            return "Female"
        if any(w in clean for w in ["male", "man", "पुरुष", "ಪುರುಷ", "పురుషుడు"]):
            return "Male"

    # 9. Monthly Pension (INR)
    if field == "monthly_pension_inr":
        if any(w in clean for w in ["not retired", "no pension", "none", "no", "nahin", "nahi", "illa", "ledu", "0", "zero", "निವೃತ್ತರಲ್ಲ", "ಸೇವಾವೃತ್ತರಲ್ಲ", "ನಿವೃತ್ತರಲ್ಲ", "ಪಿಂಚಣಿ ಇಲ್ಲ", "सेवानिवृत्त नहीं", "कोई पेंशन नहीं", "पेंशन नहीं", "పదవీ విరమణ లేదు", "పెన్షన్ లేదు", "పింఛను లేదు", "exempt", "छूट", "ವಿನಾಯಿತಿ"]) or ("पेंशन" in clean and any(neg in clean for neg in ["नहीं", "नाहीं", "no"])) or ("ಪಿಂಚಣಿ" in clean and "ಇಲ್ಲ" in clean) or ("పెన్షన్" in clean and "లేదు" in clean):
            return 0.0
        if any(w in clean for w in ["under 10,000", "under 10000", "less than", "कम", "ಕಡಿಮೆ", "తక్కువ"]):
            return 5000.0
        if any(w in clean for w in ["10,000 or more", "10000 or more", "above 10,000", "above 10000", "more than", "अधिक", "ಹೆಚ್ಚು", "ఎక్కువ"]):
            return 15000.0
        m = re.search(r"(\d+(?:\.\d+)?)", clean)
        if m:
            return float(m.group(1))

    # 10. Social Category (Caste)
    if field == "social_category":
        if any(w in clean for w in ["general", "सामान्य"]):
            return "General"
        if any(w in clean for w in ["obc", "ओबीसी", "ಒಬಿಸಿ", "ఓబీసీ"]):
            return "OBC"
        if any(w in clean for w in ["sc", "एससी", "ಎಸ್‌ಸಿ", "ఎస్సీ", "scheduled caste"]):
            return "SC"
        if any(w in clean for w in ["st", "एसटी", "ಎಸ್‌ಟಿ", "ఎస్టీ", "scheduled tribe"]):
            return "ST"

    return None


class ConversationalOrchestrator:
    """
    Master coordinator for citizen multi-turn dialogue.
    Maintains zero PII, enforces deterministic rule engine decisions,
    and grounds all responses in verified citations.
    """

    def __init__(
        self,
        session_manager: Optional[SessionProfileManager] = None,
        attribute_extractor: Optional[AttributeExtractor] = None,
        eligibility_orchestrator: Optional[EligibilityOrchestrator] = None,
        rag_service: Optional[RAGRetrieverService] = None,
        agent_intelligence: Optional[AgentIntelligenceService] = None,
        db_session: Optional[AsyncSession] = None,
    ):
        self.session_manager = session_manager or SessionProfileManager()
        self.attribute_extractor = attribute_extractor or AttributeExtractor()
        self.eligibility_orchestrator = eligibility_orchestrator or EligibilityOrchestrator(session=db_session)
        self.rag_service = rag_service or RAGRetrieverService(session=db_session)
        self.agent_intelligence = agent_intelligence or AgentIntelligenceService()
        self._db_session = db_session

    def _build_diagnostics(
        self,
        request_id: str,
        start_time: float,
        llm_provider: str,
        llm_model: str,
        actual_llm_inference: bool,
        fallback_reason: Optional[str],
        intent: CitizenIntentEnum,
        rag_results: List[ChunkSearchResult],
        eligibility_results: List[EligibilityOrchestrationResult],
        nlu_llm_success: bool = False,
        synthesis_llm_success: bool = False,
        stage_latencies_ms: Optional[Dict[str, float]] = None,
        error_category: Optional[str] = None,
    ) -> RequestDiagnostics:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        rag_schemes: List[str] = []
        for r in rag_results:
            if r.chunk.scheme_id and r.chunk.scheme_id not in rag_schemes:
                rag_schemes.append(r.chunk.scheme_id)

        outcomes = {
            ev.scheme_id: ev.status.value
            for ev in eligibility_results
            if ev and ev.scheme_id
        }

        # actual_llm_inference is true if at least one real LLM step succeeded
        real_inference = actual_llm_inference or nlu_llm_success or synthesis_llm_success

        status = "ok"
        if error_category:
            status = "error"
        elif not real_inference and self.agent_intelligence.gateway.is_real_llm_configured():
            status = "fallback"

        diag = RequestDiagnostics(
            request_id=request_id,
            llm_provider=llm_provider if real_inference else "deterministic",
            llm_model=llm_model if real_inference else "deterministic-rules-v1",
            actual_llm_inference=real_inference,
            nlu_llm_success=nlu_llm_success,
            synthesis_llm_success=synthesis_llm_success,
            stage_latencies_ms=stage_latencies_ms or {},
            fallback_reason=fallback_reason,
            detected_intent=intent.value,
            rag_chunks_retrieved=len(rag_results),
            rag_scheme_ids=rag_schemes,
            eligibility_invoked=bool(eligibility_results),
            eligibility_outcomes=outcomes,
            response_status=status,
            latency_ms=latency_ms,
            error_category=error_category,
        )
        # PII-safe structured log (no raw user message, no profile values, no secrets)
        logger.info(
            "chat_turn request_id=%s provider=%s model=%s real_llm=%s nlu_ok=%s syn_ok=%s intent=%s rag_count=%d rag_schemes=%s elig=%s status=%s latency_ms=%.1f",
            diag.request_id,
            diag.llm_provider,
            diag.llm_model,
            diag.actual_llm_inference,
            diag.nlu_llm_success,
            diag.synthesis_llm_success,
            diag.detected_intent,
            diag.rag_chunks_retrieved,
            diag.rag_scheme_ids,
            diag.eligibility_outcomes,
            diag.response_status,
            diag.latency_ms,
        )
        return diag

    async def process_message(
        self,
        session_id: str,
        message: str,
        language: Optional[str] = None,
        citizen_profile: Optional[Dict[str, Any]] = None,
    ) -> SynthesizedResponse:
        """
        Processes a single conversational turn from a citizen across English, Hindi,
        Kannada, or Telugu.
        """
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())

        # 1. Retrieve or initialize ephemeral session
        session = self.session_manager.get_or_create_session(
            session_id=session_id,
            language=language or "en",
        )
        current_lang = language or session.active_language
        session_profile_dict = session.attributes.model_dump(exclude_none=True)
        confirmed_profile = {k: v for k, v in (citizen_profile or {}).items() if v is not None}
        baseline_profile = {**session_profile_dict, **confirmed_profile}

        # 2. LLM-first NLU & Turn Understanding (with deterministic fallback)
        t_nlu_start = time.perf_counter()
        nlu = await self.agent_intelligence.understand_turn(
            message=message,
            language=current_lang,
            history=session.conversation_history,
            active_profile=baseline_profile,
            pending_question=session.pending_question,
            selected_scheme_id=session.selected_scheme_id,
            candidate_scheme_ids=session.candidate_scheme_ids,
            conversation_summary=session.conversation_summary,
        )
        stage_latencies_ms: Dict[str, float] = {
            "nlu": round((time.perf_counter() - t_nlu_start) * 1000, 2)
        }
        intent: CitizenIntentEnum = nlu["intent"]
        detected_scheme_ids: List[str] = nlu["target_scheme_ids"]
        is_comparison: bool = nlu["is_comparison"]
        search_query: str = nlu["search_query"] or message
        active_lang = language or nlu["language"] or current_lang

        # Anaphoric and Ordinal reference resolution ('that scheme', 'the second one', 'am I eligible?')
        if not detected_scheme_ids:
            anaphoric_sid = resolve_anaphoric_scheme(
                message, session.selected_scheme_id, session.candidate_scheme_ids
            )
            if anaphoric_sid:
                detected_scheme_ids = [anaphoric_sid]
                msg_lower = message.lower()
                if any(w in msg_lower for w in ["document", "proof", "papers", "दस्तावेज", "ದಾಖಲೆ", "పత్రాలు"]):
                    intent = CitizenIntentEnum.DOCUMENT_REQUIREMENTS
                elif any(w in msg_lower for w in ["apply", "procedure", "how to", "process", "आवेदन", "ಅರ್ಜಿ", "దరఖాస్తు"]):
                    intent = CitizenIntentEnum.APPLICATION_GUIDANCE
                elif any(w in msg_lower for w in ["eligible", "qualify", "पात्र", "ಅರ್ಹ", "అర్హ"]):
                    intent = CitizenIntentEnum.ELIGIBILITY_CHECK
                elif intent in (CitizenIntentEnum.GENERAL_HELP, CitizenIntentEnum.SCHEME_DISCOVERY):
                    intent = CitizenIntentEnum.SCHEME_INFORMATION

        llm_provider = nlu["llm_provider"]
        llm_model = nlu["llm_model"]
        nlu_llm_success = nlu.get("actual_llm_inference", False)
        actual_llm_inference = nlu_llm_success
        fallback_reason = nlu.get("fallback_reason")

        self.session_manager.set_language(session.session_id, active_lang)

        # Update scheme focus if a single scheme is explicitly identified
        if len(detected_scheme_ids) == 1:
            new_sid = detected_scheme_ids[0]
            # If user switches context to another scheme, clear previous pending question
            if (
                session.pending_question
                and session.pending_question.get("scheme_id")
                and session.pending_question["scheme_id"] != new_sid
            ):
                self.session_manager.set_pending_question(session.session_id, None, None, None)
            self.session_manager.set_scheme(session.session_id, new_sid)

        target_scheme_id = (
            detected_scheme_ids[0]
            if len(detected_scheme_ids) == 1
            else (None if len(detected_scheme_ids) > 1 else session.selected_scheme_id)
        )

        # 3. Handle Unsupported & Out-of-Domain queries immediately
        if intent == CitizenIntentEnum.UNSUPPORTED_QUERY:
            resp = ResponseSynthesizer.synthesize(
                intent=CitizenIntentEnum.UNSUPPORTED_QUERY,
                language=active_lang,
                scheme_id=target_scheme_id,
                active_profile=baseline_profile,
            )
            resp.diagnostics = self._build_diagnostics(
                request_id, start_time,
                llm_provider if nlu_llm_success else "deterministic",
                llm_model if nlu_llm_success else "deterministic-rules-v1",
                nlu_llm_success,
                fallback_reason,
                intent, [], [],
                nlu_llm_success=nlu_llm_success,
                synthesis_llm_success=False,
                stage_latencies_ms=stage_latencies_ms,
            )
            self.session_manager.append_turn(session.session_id, "user", message)
            self.session_manager.append_turn(session.session_id, "assistant", resp.message)
            return resp

        # 4. Multilingual Attribute Extraction, Validation & Short Follow-up Mapping (Local Deterministic)
        t_attr_start = time.perf_counter()
        validation_result: ValidationResult = await self.attribute_extractor.extract_and_validate(
            text=message,
            current_profile=baseline_profile,
            language=active_lang,
        )
        stage_latencies_ms["attribute_extraction"] = round((time.perf_counter() - t_attr_start) * 1000, 2)

        # Handle answers to pending clarification questions (both booleans and typed values)
        pending_q = session.pending_question
        if pending_q and pending_q.get("field"):
            p_field = pending_q["field"]
            if p_field not in validation_result.validated_attributes:
                parsed_val = parse_pending_slot_value(p_field, message)
                if parsed_val is not None:
                    validation_result.validated_attributes[p_field] = parsed_val

        # If user answered a pending question, preserve eligibility check continuity
        if pending_q and validation_result.validated_attributes and not detected_scheme_ids:
            if pending_q.get("scheme_id"):
                target_scheme_id = pending_q["scheme_id"]
                self.session_manager.set_scheme(session.session_id, target_scheme_id)
            if intent in (CitizenIntentEnum.GENERAL_HELP, CitizenIntentEnum.SCHEME_DISCOVERY):
                intent = CitizenIntentEnum.ELIGIBILITY_CHECK

        # Detect conflicts between confirmed profile and new explicit values in message
        profile_conflicts: List[Dict[str, Any]] = []
        non_conflicting_updates: Dict[str, Any] = {}
        for k, new_val in validation_result.validated_attributes.items():
            if k in confirmed_profile and confirmed_profile[k] != new_val:
                profile_conflicts.append({
                    "field": k,
                    "confirmed_value": confirmed_profile[k],
                    "new_value": new_val,
                })
                self.session_manager.record_correction(
                    session.session_id, k, confirmed_profile[k], new_val
                )
            else:
                prev_sess_val = session_profile_dict.get(k)
                if prev_sess_val is not None and prev_sess_val != new_val:
                    self.session_manager.record_correction(
                        session.session_id, k, prev_sess_val, new_val
                    )
                non_conflicting_updates[k] = new_val

        # Update session profile with non-conflicting attributes (protects confirmed profile from silent overwrite)
        if non_conflicting_updates:
            session = self.session_manager.update_attributes(
                session_id=session.session_id,
                new_attributes=non_conflicting_updates,
            )

        eval_profile = {
            **confirmed_profile,
            **session.attributes.model_dump(exclude_none=True),
            **validation_result.validated_attributes,
        }
        updated_profile_dict = eval_profile

        # 5. Handle General Help / Greetings
        if intent == CitizenIntentEnum.GENERAL_HELP:
            t_syn_start = time.perf_counter()
            llm_msg, syn_real, syn_prov, syn_model, syn_fb = await self.agent_intelligence.synthesize_response(
                message=message,
                language=active_lang,
                intent=intent,
                history=session.conversation_history,
                active_profile=updated_profile_dict,
                rag_results=[],
                has_sufficient_evidence=True,
            )
            stage_latencies_ms["synthesis"] = round((time.perf_counter() - t_syn_start) * 1000, 2)
            resp = ResponseSynthesizer.synthesize(
                intent=CitizenIntentEnum.GENERAL_HELP,
                language=active_lang,
                scheme_id=target_scheme_id,
                active_profile=updated_profile_dict,
                llm_synthesized_message=llm_msg,
            )
            real_inference = nlu_llm_success or syn_real
            active_prov = syn_prov if syn_real else (llm_provider if nlu_llm_success else "deterministic")
            active_model = syn_model if syn_real else (llm_model if nlu_llm_success else "deterministic-rules-v1")
            active_fb = syn_fb if not syn_real else fallback_reason
            resp.diagnostics = self._build_diagnostics(
                request_id, start_time,
                active_prov,
                active_model,
                real_inference,
                active_fb,
                intent, [], [],
                nlu_llm_success=nlu_llm_success,
                synthesis_llm_success=syn_real,
                stage_latencies_ms=stage_latencies_ms,
            )
            self.session_manager.append_turn(session.session_id, "user", message)
            self.session_manager.append_turn(session.session_id, "assistant", resp.message)
            self.session_manager.set_last_intent(session.session_id, intent.value)
            return resp

        # 6. Multi-Scheme Comparison Path (e.g. "Compare PM-KISAN and PM-KMY")
        if is_comparison and len(detected_scheme_ids) >= 2:
            t_comp_rag_start = time.perf_counter()
            all_rag_results: List[ChunkSearchResult] = []
            all_citations: List[ProvenanceCitation] = []
            seen_chunks = set()
            comp_evals: List[EligibilityOrchestrationResult] = []

            for sid in detected_scheme_ids[:3]:
                try:
                    rag_resp = await self.rag_service.retrieve(
                        RAGRetrievalRequest(
                            query=f"{sid} {search_query}",
                            language=active_lang,
                            scheme_id=sid,
                            limit=2,
                            min_score=0.0,
                        )
                    )
                    for r in rag_resp.results:
                        if r.chunk.chunk_id not in seen_chunks:
                            seen_chunks.add(r.chunk.chunk_id)
                            all_rag_results.append(r)
                    for c in rag_resp.citations:
                        if c.chunk_id not in {x.chunk_id for x in all_citations}:
                            all_citations.append(c)
                except Exception as e:
                    logger.warning(f"Comparison RAG retrieval failed for {sid}: {e}")

                if updated_profile_dict:
                    try:
                        ev = await self.eligibility_orchestrator.evaluate(
                            scheme_id=sid,
                            citizen_profile=updated_profile_dict,
                            language=active_lang,
                        )
                        if not ev.is_clarification_needed:
                            comp_evals.append(ev)
                    except Exception:
                        pass

            stage_latencies_ms["rag"] = round((time.perf_counter() - t_comp_rag_start) * 1000, 2)
            rag_text = "\n\n".join(
                f"**{r.chunk.provenance.document_title}**\n{r.chunk.content}"
                for r in all_rag_results
            )
            t_syn_start = time.perf_counter()
            llm_msg, syn_real, syn_prov, syn_model, syn_fb = await self.agent_intelligence.synthesize_response(
                message=message,
                language=active_lang,
                intent=CitizenIntentEnum.SCHEME_INFORMATION,
                history=session.conversation_history,
                active_profile=updated_profile_dict,
                rag_results=all_rag_results,
                has_sufficient_evidence=bool(all_rag_results),
                candidate_evaluations=comp_evals,
                profile_conflicts=profile_conflicts,
                is_comparison=True,
            )
            stage_latencies_ms["synthesis"] = round((time.perf_counter() - t_syn_start) * 1000, 2)
            resp = ResponseSynthesizer.synthesize(
                intent=CitizenIntentEnum.SCHEME_INFORMATION,
                language=active_lang,
                scheme_id=None,
                retrieved_text=rag_text,
                citations=all_citations,
                validation_result=validation_result,
                active_profile=updated_profile_dict,
                candidate_evaluations=comp_evals,
                profile_conflicts=profile_conflicts,
                has_sufficient_evidence=bool(all_rag_results),
                llm_synthesized_message=llm_msg,
            )
            real_inference = nlu_llm_success or syn_real
            active_prov = syn_prov if syn_real else (llm_provider if nlu_llm_success else "deterministic")
            active_model = syn_model if syn_real else (llm_model if nlu_llm_success else "deterministic-rules-v1")
            active_fb = syn_fb if not syn_real else fallback_reason
            resp.diagnostics = self._build_diagnostics(
                request_id, start_time,
                active_prov,
                active_model,
                real_inference,
                active_fb,
                CitizenIntentEnum.SCHEME_INFORMATION,
                all_rag_results,
                comp_evals,
                nlu_llm_success=nlu_llm_success,
                synthesis_llm_success=syn_real,
                stage_latencies_ms=stage_latencies_ms,
            )
            self.session_manager.append_turn(session.session_id, "user", message)
            self.session_manager.append_turn(session.session_id, "assistant", resp.message)
            self.session_manager.set_last_intent(session.session_id, CitizenIntentEnum.SCHEME_INFORMATION.value)
            return resp

        # 7. Eligibility Check Path
        # If user asks for eligibility or provides citizen profile, but no specific scheme is targeted,
        # route to SCHEME_DISCOVERY so we evaluate candidate schemes against their profile!
        if intent == CitizenIntentEnum.ELIGIBILITY_CHECK and not target_scheme_id:
            intent = CitizenIntentEnum.SCHEME_DISCOVERY

        is_explicit_other_intent = intent in [
            CitizenIntentEnum.DOCUMENT_REQUIREMENTS,
            CitizenIntentEnum.APPLICATION_GUIDANCE,
            CitizenIntentEnum.SCHEME_INFORMATION,
            CitizenIntentEnum.SCHEME_DISCOVERY,
        ]

        if intent == CitizenIntentEnum.ELIGIBILITY_CHECK or (
            validation_result.validated_attributes and target_scheme_id and not is_explicit_other_intent
        ):
            t_rules_start = time.perf_counter()
            elig_result = await self.eligibility_orchestrator.evaluate(
                scheme_id=target_scheme_id,
                citizen_profile=updated_profile_dict,
                language=active_lang,
            )
            stage_latencies_ms["rules"] = round((time.perf_counter() - t_rules_start) * 1000, 2)

            rag_results: List[ChunkSearchResult] = []
            rag_citations: List[ProvenanceCitation] = []
            if target_scheme_id:
                t_rag_start = time.perf_counter()
                try:
                    rag_resp = await self.rag_service.retrieve(
                        RAGRetrievalRequest(
                            query=f"{target_scheme_id} eligibility overview",
                            language=active_lang,
                            scheme_id=target_scheme_id,
                            limit=2,
                            min_score=0.0,
                        )
                    )
                    rag_results = rag_resp.results
                    rag_citations = rag_resp.citations
                except Exception as e:
                    logger.info(f"RAG retrieval skipped during eligibility check: {e}")
                stage_latencies_ms["rag"] = round((time.perf_counter() - t_rag_start) * 1000, 2)

            t_syn_start = time.perf_counter()
            llm_msg, syn_real, syn_prov, syn_model, syn_fb = await self.agent_intelligence.synthesize_response(
                message=message,
                language=active_lang,
                intent=CitizenIntentEnum.ELIGIBILITY_CHECK,
                history=session.conversation_history,
                active_profile=updated_profile_dict,
                rag_results=rag_results,
                has_sufficient_evidence=True,
                eligibility_result=elig_result,
                profile_conflicts=profile_conflicts,
            )
            stage_latencies_ms["synthesis"] = round((time.perf_counter() - t_syn_start) * 1000, 2)

            # Update pending question for multi-turn follow-up
            if elig_result.missing_prompts:
                first_field = (
                    elig_result.missing_fields[0]
                    if getattr(elig_result, "missing_fields", None) and len(elig_result.missing_fields) > 0
                    else None
                )
                self.session_manager.set_pending_question(
                    session.session_id,
                    field=first_field,
                    scheme_id=elig_result.scheme_id,
                    prompt=elig_result.missing_prompts[0],
                )
            else:
                self.session_manager.set_pending_question(session.session_id, None, None, None)

            resp = ResponseSynthesizer.synthesize(
                intent=CitizenIntentEnum.ELIGIBILITY_CHECK,
                language=active_lang,
                scheme_id=target_scheme_id,
                citations=rag_citations,
                eligibility_result=elig_result,
                validation_result=validation_result,
                active_profile=updated_profile_dict,
                profile_conflicts=profile_conflicts,
                llm_synthesized_message=llm_msg,
            )
            real_inference = nlu_llm_success or syn_real
            active_prov = syn_prov if syn_real else (llm_provider if nlu_llm_success else "deterministic")
            active_model = syn_model if syn_real else (llm_model if nlu_llm_success else "deterministic-rules-v1")
            active_fb = syn_fb if not syn_real else fallback_reason
            resp.diagnostics = self._build_diagnostics(
                request_id, start_time,
                active_prov,
                active_model,
                real_inference,
                active_fb,
                CitizenIntentEnum.ELIGIBILITY_CHECK,
                rag_results,
                [elig_result],
                nlu_llm_success=nlu_llm_success,
                synthesis_llm_success=syn_real,
                stage_latencies_ms=stage_latencies_ms,
            )
            self.session_manager.append_turn(session.session_id, "user", message)
            self.session_manager.append_turn(session.session_id, "assistant", resp.message)
            self.session_manager.set_last_intent(session.session_id, CitizenIntentEnum.ELIGIBILITY_CHECK.value)
            return resp

        # 8. RAG Retrieval for Discovery, Informational, Document, or Application Guidance
        category_map = {
            CitizenIntentEnum.DOCUMENT_REQUIREMENTS: ChunkCategoryEnum.DOCUMENT_REQUIREMENT,
            CitizenIntentEnum.APPLICATION_GUIDANCE: ChunkCategoryEnum.APPLICATION_PROCEDURE,
            CitizenIntentEnum.SCHEME_INFORMATION: ChunkCategoryEnum.SCHEME_OVERVIEW,
            CitizenIntentEnum.SCHEME_DISCOVERY: ChunkCategoryEnum.SCHEME_OVERVIEW,
        }
        category_filter = category_map.get(intent)

        rag_query = search_query
        if intent == CitizenIntentEnum.SCHEME_DISCOVERY and updated_profile_dict:
            context_terms: List[str] = []
            if updated_profile_dict.get("occupation"):
                context_terms.append(str(updated_profile_dict["occupation"]))
            if updated_profile_dict.get("gender"):
                context_terms.append(str(updated_profile_dict["gender"]))
            if updated_profile_dict.get("age") is not None and int(updated_profile_dict["age"]) >= 60:
                context_terms.append("senior citizen pension")
            if context_terms:
                rag_query = f"{search_query} {' '.join(context_terms)}"

        rag_text: Optional[str] = None
        citations: List[ProvenanceCitation] = []
        matched_scheme_ids: List[str] = []
        selected_results: List[ChunkSearchResult] = []

        t_rag_start = time.perf_counter()
        try:
            rag_resp = await self.rag_service.retrieve(
                RAGRetrievalRequest(
                    query=rag_query,
                    language=active_lang,
                    category=category_filter,
                    scheme_id=target_scheme_id,
                    limit=6 if intent == CitizenIntentEnum.SCHEME_DISCOVERY else 3,
                    min_score=0.0,
                )
            )
            if not rag_resp.results and category_filter is not None:
                rag_resp = await self.rag_service.retrieve(
                    RAGRetrievalRequest(
                        query=rag_query,
                        language=active_lang,
                        category=None,
                        scheme_id=target_scheme_id,
                        limit=4,
                        min_score=0.0,
                    )
                )

            if rag_resp.results:
                seen_schemes = set()
                for r in rag_resp.results:
                    if intent == CitizenIntentEnum.SCHEME_DISCOVERY:
                        if r.chunk.scheme_id in seen_schemes:
                            continue
                        seen_schemes.add(r.chunk.scheme_id)
                        matched_scheme_ids.append(r.chunk.scheme_id)
                    selected_results.append(r)
                    if len(selected_results) >= (3 if intent == CitizenIntentEnum.SCHEME_DISCOVERY else 2):
                        break

                selected_chunk_ids = {r.chunk.chunk_id for r in selected_results}
                citations = [c for c in rag_resp.citations if c.chunk_id in selected_chunk_ids] or rag_resp.citations[:3]

                rag_text = "\n\n".join(
                    f"**{r.chunk.provenance.document_title}**\n{r.chunk.content}"
                    for r in selected_results
                )
        except Exception as e:
            logger.warning(f"RAG retrieval query failed: {e}")
        stage_latencies_ms["rag"] = round((time.perf_counter() - t_rag_start) * 1000, 2)

        has_sufficient_evidence = check_evidence_sufficiency(message, selected_results)

        # Evaluate candidate schemes deterministically for SCHEME_DISCOVERY
        candidate_evaluations: List[EligibilityOrchestrationResult] = []
        if intent == CitizenIntentEnum.SCHEME_DISCOVERY and not target_scheme_id:
            t_rules_start = time.perf_counter()
            # Order priority: RAG matched schemes, occupation-relevant schemes, then remaining catalog
            seed_schemes = list(self.eligibility_orchestrator._get_seed_data().keys())
            eval_candidates: List[str] = []
            for sid in matched_scheme_ids:
                if sid not in eval_candidates:
                    eval_candidates.append(sid)

            occ = eval_profile.get("occupation")
            if occ == "Farmer" or eval_profile.get("owns_agricultural_land") is True:
                for farmer_sid in ["pm-kisan", "kcc", "pm-kusum", "pm-kmy"]:
                    if farmer_sid not in eval_candidates:
                        eval_candidates.append(farmer_sid)
            elif occ == "Street Vendor":
                for vendor_sid in ["pm-svanidhi", "pmjjby", "pmsby"]:
                    if vendor_sid not in eval_candidates:
                        eval_candidates.append(vendor_sid)

            for sid in seed_schemes:
                if sid not in eval_candidates:
                    eval_candidates.append(sid)

            evaluated_all: List[EligibilityOrchestrationResult] = []
            for sid in eval_candidates:
                try:
                    ev = await self.eligibility_orchestrator.evaluate(
                        scheme_id=sid,
                        citizen_profile=eval_profile,
                        language=active_lang,
                    )
                    evaluated_all.append(ev)
                except Exception:
                    continue

            # Bucket into 3 distinct categories
            eligible_list = [ev for ev in evaluated_all if ev.status == EligibilityStatusEnum.ELIGIBLE]
            needs_info_list = [
                ev for ev in evaluated_all
                if ev.status in (
                    EligibilityStatusEnum.NEEDS_MORE_INFORMATION,
                    EligibilityStatusEnum.POSSIBLY_ELIGIBLE,
                    EligibilityStatusEnum.NOT_VERIFIED,
                )
            ]
            not_eligible_list = [ev for ev in evaluated_all if ev.status == EligibilityStatusEnum.NOT_ELIGIBLE]

            # Prioritize: All eligible schemes, top 3 needs_info schemes, top 2 not_eligible schemes
            candidate_evaluations = eligible_list + needs_info_list[:3] + not_eligible_list[:2]

            # Register all evaluated scheme IDs in session for ordinal references
            all_discovered_ids = [ev.scheme_id for ev in evaluated_all]
            self.session_manager.set_candidate_schemes(session.session_id, all_discovered_ids)
            stage_latencies_ms["rules"] = round((time.perf_counter() - t_rules_start) * 1000, 2)

        top_incomplete = next(
            (ev for ev in candidate_evaluations if ev.status in (EligibilityStatusEnum.NEEDS_MORE_INFORMATION, EligibilityStatusEnum.POSSIBLY_ELIGIBLE) and ev.missing_prompts),
            None,
        )
        if top_incomplete:
            first_field = (
                top_incomplete.missing_fields[0]
                if getattr(top_incomplete, "missing_fields", None) and len(top_incomplete.missing_fields) > 0
                else None
            )
            self.session_manager.set_pending_question(
                session.session_id,
                field=first_field,
                scheme_id=top_incomplete.scheme_id,
                prompt=top_incomplete.missing_prompts[0],
            )

        effective_scheme_id = target_scheme_id or (matched_scheme_ids[0] if len(matched_scheme_ids) == 1 else None)

        t_syn_start = time.perf_counter()
        llm_msg, syn_real, syn_prov, syn_model, syn_fb = await self.agent_intelligence.synthesize_response(
            message=message,
            language=active_lang,
            intent=intent,
            history=session.conversation_history,
            active_profile=updated_profile_dict,
            rag_results=selected_results,
            has_sufficient_evidence=has_sufficient_evidence,
            candidate_evaluations=candidate_evaluations,
            profile_conflicts=profile_conflicts,
            is_comparison=is_comparison,
            conversation_summary=session.conversation_summary,
        )
        stage_latencies_ms["synthesis"] = round((time.perf_counter() - t_syn_start) * 1000, 2)

        resp = ResponseSynthesizer.synthesize(
            intent=intent,
            language=active_lang,
            scheme_id=effective_scheme_id,
            retrieved_text=rag_text,
            citations=citations,
            validation_result=validation_result,
            active_profile=updated_profile_dict,
            candidate_evaluations=candidate_evaluations,
            profile_conflicts=profile_conflicts,
            has_sufficient_evidence=has_sufficient_evidence,
            llm_synthesized_message=llm_msg,
        )
        real_inference = nlu_llm_success or syn_real
        active_prov = syn_prov if syn_real else (llm_provider if nlu_llm_success else "deterministic")
        active_model = syn_model if syn_real else (llm_model if nlu_llm_success else "deterministic-rules-v1")
        active_fb = syn_fb if not syn_real else fallback_reason
        resp.diagnostics = self._build_diagnostics(
            request_id, start_time,
            active_prov,
            active_model,
            real_inference,
            active_fb,
            intent,
            selected_results,
            candidate_evaluations,
            nlu_llm_success=nlu_llm_success,
            synthesis_llm_success=syn_real,
            stage_latencies_ms=stage_latencies_ms,
        )
        self.session_manager.append_turn(session.session_id, "user", message)
        self.session_manager.append_turn(session.session_id, "assistant", resp.message)
        self.session_manager.set_last_intent(session.session_id, intent.value)
        return resp
