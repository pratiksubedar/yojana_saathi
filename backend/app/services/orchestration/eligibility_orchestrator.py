"""
Yojana Saathi - Deterministic Eligibility Orchestrator
Milestone 6.3: Orchestrates deterministic eligibility checks using RuleEngineService as
the sole authority. Translates missing field prompts via FIELD_PROMPTS, preserves
unresolved criteria notes, and prevents any LLM hallucination of statutory outcomes.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scheme
from app.db.session import async_session_factory
from app.schemas.eligibility import (
    EligibilityStatusEnum,
    SchemeEligibilityResult,
)
from app.schemas.provenance import VerificationStatus
from app.schemas.orchestration import EligibilityOrchestrationResult
from app.schemas.rag import ChunkCategoryEnum, ContentTypeEnum, ProvenanceCitation
from app.services.citation_formatter import ATTRIBUTION_LABELS, STATUS_DISCLOSURES
from app.services.rule_engine import (
    DeterministicRuleEvaluator,
    FIELD_PROMPTS,
)

# Seed path for offline / in-memory resilience
SEED_FILE_PATH = Path(__file__).resolve().parents[3] / "data" / "schemes_seed.json"


class EligibilityOrchestrator:
    """
    Coordinates profile attributes with RuleEngineService.
    Ensures zero LLM interference in eligibility determinations.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session
        self._seed_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _get_seed_data(self) -> Dict[str, Dict[str, Any]]:
        """Loads and caches scheme seed data for fallback execution."""
        if self._seed_cache is None:
            if SEED_FILE_PATH.exists():
                with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
                    schemes_list = json.load(f)
                    self._seed_cache = {s["id"]: s for s in schemes_list}
            else:
                self._seed_cache = {}
        return self._seed_cache

    async def get_scheme_data(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves scheme record and its rule AST from DB or fallback seed."""
        clean_id = scheme_id.strip()

        # 1. Attempt Database Lookup
        try:
            if self._session is not None:
                db_sess = self._session
                owns_session = False
            else:
                db_sess = async_session_factory()
                owns_session = True

            try:
                stmt = (
                    select(Scheme)
                    .where(or_(Scheme.id == clean_id, Scheme.slug == clean_id))
                    .options(selectinload(Scheme.rules))
                )
                result = await db_sess.execute(stmt)
                scheme = result.scalar_one_or_none()
                if scheme and scheme.rules:
                    rule = scheme.rules[0]
                    conditions_ast = dict(rule.conditions)
                    unresolved = conditions_ast.get("unresolved_criteria", [])
                    return {
                        "id": scheme.id,
                        "names": scheme.names,
                        "rule_ast": conditions_ast,
                        "unresolved_criteria": unresolved,
                        "source_citation": scheme.source_citation,
                    }
            finally:
                if owns_session:
                    await db_sess.close()
        except Exception:
            pass

        # 2. Fallback to schemes_seed.json
        seed_data = self._get_seed_data()
        if clean_id in seed_data:
            s = seed_data[clean_id]
            rule_entry = s.get("rules", {})
            conditions_ast = dict(rule_entry.get("conditions", {}))
            if "rule_completeness" in rule_entry:
                conditions_ast["rule_completeness"] = rule_entry["rule_completeness"]
            if "unresolved_criteria" in rule_entry:
                conditions_ast["unresolved_criteria"] = rule_entry["unresolved_criteria"]
            return {
                "id": s["id"],
                "names": s.get("names", {}),
                "rule_ast": conditions_ast,
                "unresolved_criteria": rule_entry.get("unresolved_criteria", []),
                "source_citation": s.get("source_citation", {}),
            }

        return None

    async def evaluate(
        self,
        scheme_id: Optional[str],
        citizen_profile: Dict[str, Any],
        language: str = "en",
    ) -> EligibilityOrchestrationResult:
        """
        Executes authoritative deterministic rule engine evaluation for a scheme.
        Generates localized missing prompts and clarifies ambiguity when scheme is unstated.
        """
        lang = language if language in ["en", "hi", "kn", "te"] else "en"

        if not scheme_id:
            clarification_msgs = {
                "en": "Which scheme would you like to check eligibility for? (e.g., PM-KISAN, PM-JAY, PM-SVANidhi, PMAY-G, PM-KMY, PMMVY, PM-KUSUM)",
                "hi": "आप किस योजना के लिए पात्रता जांचना चाहते हैं? (उदा. पीएम-किसान, पीएम-जय, पीएम-स्वनिधि, पीएमएवाई-जी, पीएम-केएमवाई, पीएमएमवीवाई, पीएम-कुसुम)",
                "kn": "ನೀವು ಯಾವ ಯೋಜನೆಯ ಅರ್ಹತೆಯನ್ನು ಪರಿಶೀಲಿಸಲು ಬಯಸುತ್ತೀರಿ? (ಉದಾ: ಪಿಎಂ-ಕಿಸಾನ್, ಪಿಎಂ-ಜೆಎವೈ, ಪಿಎಂ-ಸ್ವನಿಧಿ, ಪಿಎಂಎವೈ-ಜಿ, ಪಿಎಂ-ಕೆಎಂವೈ, ಪಿಎಂಎಂವಿವೈ, ಪಿಎಂ-ಕುಸುಮ್)",
                "te": "మీరు ఏ పథకం కోసం అర్హతను తనిఖీ చేయాలనుకుంటున్నారు? (ఉదా: పీఎం-కిసాన్, పీఎం-జేఏవై, పీఎం-స్వనిధి, పీఎంఏవై-జీ, పీఎం-కేఎంవై, పీఎంఎంవీవై, పీఎం-కుసుమ్)",
            }
            return EligibilityOrchestrationResult(
                scheme_id="unspecified",
                scheme_name={"en": "Unspecified Scheme"},
                status=EligibilityStatusEnum.POSSIBLY_ELIGIBLE,
                summary=clarification_msgs.get(lang, clarification_msgs["en"]),
                is_clarification_needed=True,
                clarification_message=clarification_msgs.get(lang, clarification_msgs["en"]),
            )

        scheme_data = await self.get_scheme_data(scheme_id)
        if not scheme_data:
            unknown_msgs = {
                "en": f"Scheme '{scheme_id}' was not found in our verified knowledge base.",
                "hi": f"योजना '{scheme_id}' हमारे सत्यापित डेटाबेस में नहीं मिली।",
                "kn": f"'{scheme_id}' ಯೋಜನೆಯು ನಮ್ಮ ಪರಿಶೀಲಿಸಿದ ಡೇಟಾಬೇಸ್‌ನಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ.",
                "te": f"'{scheme_id}' పథకం మా ధృవీకరించిన డేటాబేస్‌లో కనుగొనబడలేదు.",
            }
            return EligibilityOrchestrationResult(
                scheme_id=scheme_id,
                scheme_name={"en": scheme_id},
                status=EligibilityStatusEnum.POSSIBLY_ELIGIBLE,
                summary=unknown_msgs.get(lang, unknown_msgs["en"]),
                is_clarification_needed=True,
                clarification_message=unknown_msgs.get(lang, unknown_msgs["en"]),
            )

        # Invoke Deterministic Rule Engine
        rule_result: SchemeEligibilityResult = DeterministicRuleEvaluator.evaluate_scheme(
            scheme_id=scheme_data["id"],
            scheme_name=scheme_data["names"],
            rule_ast=scheme_data["rule_ast"],
            citizen_attributes=citizen_profile,
        )

        # Extract satisfied conditions
        satisfied_descriptions: List[str] = []
        for cond in rule_result.conditions_satisfied:
            desc = cond.reason.get(lang) or cond.reason.get("en") or cond.condition_id
            satisfied_descriptions.append(desc)

        # Extract failed conditions
        failed_descriptions: List[str] = []
        for cond in rule_result.conditions_failed:
            desc = cond.reason.get(lang) or cond.reason.get("en") or cond.condition_id
            failed_descriptions.append(desc)

        # Formulate localized prompts for missing fields using FIELD_PROMPTS
        missing_prompts: List[str] = []
        missing_fields: List[str] = []
        for mf in rule_result.missing_information:
            field_name = mf.field
            missing_fields.append(field_name)
            if field_name in FIELD_PROMPTS and "prompts" in FIELD_PROMPTS[field_name]:
                field_prompts = FIELD_PROMPTS[field_name]["prompts"]
                prompt_text = field_prompts.get(lang) or field_prompts.get("en")
                if prompt_text:
                    missing_prompts.append(prompt_text)
            else:
                missing_prompts.append(mf.prompt.get(lang) or mf.prompt.get("en") or f"Please provide {field_name}.")

        # For KCC: If agricultural activity category is unresolved (any_of conditions missing)
        if scheme_data.get("id") == "kcc":
            kcc_acts = {"owns_agricultural_land", "is_tenant_farmer", "is_allied_activity_worker"}
            if any(f in kcc_acts for f in missing_fields):
                kcc_unified_prompts = {
                    "en": "Are you engaged in agricultural cultivation or an allied agricultural activity?",
                    "hi": "क्या आप कृषि खेती या उससे संबंधित संबद्ध कृषि गतिविधि में संलग्न हैं?",
                    "kn": "ನೀವು ಕೃಷಿ ಸಾಗುವಳಿ ಅಥವಾ ಕೃಷಿ ಸಂಬಂಧಿತ ಚಟುವಟಿಕೆಯಲ್ಲಿ ತೊಡಗಿದ್ದೀರಾ?",
                    "te": "మీరు వ్యవసాయ సాగు లేదా అనుబంధ వ్యవసాయ కార్యకలాపాలలో నిమగ్నమై ఉన్నారా?",
                }
                unified_prompt = kcc_unified_prompts.get(lang, kcc_unified_prompts["en"])
                filtered_prompts = [
                    p for i, p in enumerate(missing_prompts)
                    if i < len(missing_fields) and missing_fields[i] not in kcc_acts
                ]
                missing_prompts = [unified_prompt] + filtered_prompts
                missing_fields = ["farmer_type"] + [f for f in missing_fields if f not in kcc_acts]

        # Collect unresolved statutory notes
        unresolved_notes: List[str] = []
        unresolved_src = rule_result.unresolved_criteria or scheme_data.get("unresolved_criteria", [])
        if not unresolved_src:
            seed_data = self._get_seed_data()
            if scheme_data["id"] in seed_data:
                unresolved_src = seed_data[scheme_data["id"]].get("rules", {}).get("unresolved_criteria", [])

        for uc in unresolved_src:
            if isinstance(uc, dict):
                clause = uc.get("clause", "")
                title = uc.get("title", "")
                desc = uc.get("description", "")
                unresolved_notes.append(f"{title} ({clause}): {desc}")
            else:
                unresolved_notes.append(str(uc))

        # Assemble source provenance citation
        citations: List[ProvenanceCitation] = []
        src_cite = scheme_data.get("source_citation") or {}
        if src_cite.get("url"):
            v_status_str = src_cite.get("verification_status", "VERIFIED")
            try:
                v_status = VerificationStatus(v_status_str)
            except Exception:
                v_status = VerificationStatus.VERIFIED

            status_disc_dict = STATUS_DISCLOSURES.get(v_status, STATUS_DISCLOSURES[VerificationStatus.VERIFIED])
            disclosure = status_disc_dict.get(lang, status_disc_dict["en"])
            attr_dict = ATTRIBUTION_LABELS.get(ContentTypeEnum.CURATED_SUMMARY)
            attribution = attr_dict.get(lang, attr_dict["en"])

            sections = src_cite.get("relevant_sections", [])
            sec_str = ", ".join(sections) if isinstance(sections, list) else str(sections or "")

            citations.append(
                ProvenanceCitation(
                    chunk_id=f"cite_{scheme_data['id']}_rules",
                    scheme_id=scheme_data["id"],
                    category=ChunkCategoryEnum.ELIGIBILITY_CLAUSE,
                    source_url=src_cite.get("url", ""),
                    issuing_authority=src_cite.get("issuing_authority", "Government of India"),
                    document_title=src_cite.get("title", f"{scheme_data['id'].upper()} Guidelines"),
                    relevant_section=sec_str or None,
                    verification_status=v_status,
                    status_disclosure=disclosure,
                    content_type=ContentTypeEnum.CURATED_SUMMARY,
                    is_verbatim=False,
                    attribution_label=attribution,
                )
            )

        # Summary in target language
        summary_text = (
            rule_result.summary.get(lang)
            or rule_result.summary.get("en")
            or "Evaluation complete."
        )

        # Map legacy POSSIBLY_ELIGIBLE into explicit NEEDS_MORE_INFORMATION or NOT_VERIFIED
        canonical_status = rule_result.status
        if canonical_status == EligibilityStatusEnum.POSSIBLY_ELIGIBLE:
            if missing_prompts:
                canonical_status = EligibilityStatusEnum.NEEDS_MORE_INFORMATION
            else:
                canonical_status = EligibilityStatusEnum.NOT_VERIFIED

        return EligibilityOrchestrationResult(
            scheme_id=scheme_data["id"],
            scheme_name=scheme_data["names"],
            status=canonical_status,
            summary=summary_text,
            satisfied_conditions=satisfied_descriptions,
            failed_conditions=failed_descriptions,
            missing_prompts=missing_prompts,
            missing_fields=missing_fields,
            unresolved_notes=unresolved_notes,
            citations=citations,
            is_clarification_needed=False,
        )
