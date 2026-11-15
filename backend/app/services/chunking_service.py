"""
Yojana Saathi - Scheme Semantic Chunking Service
Milestone 6.1: Structured semantic chunking system for welfare schemes.
Generates atomic, multilingual, provenance-grounded chunks across:
- scheme_overview
- scheme_benefit
- eligibility_clause
- exclusion_clause
- document_requirement
- application_procedure
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from app.schemas.provenance import VerificationStatus
from app.schemas.rag import (
    ChunkCategoryEnum,
    ChunkProvenanceSchema,
    ContentTypeEnum,
    SchemeChunk,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["en", "hi", "kn", "te"]

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "te": "తెలుగు (Telugu)",
}


class SchemeChunkingService:
    """
    Transforms rich structured scheme records into atomic semantic chunks
    with full provenance metadata, maintaining strict distinction between
    curated summaries and verbatim official text.
    """

    @staticmethod
    def _extract_dict(val: Any) -> Dict[str, Any]:
        """Safely extracts dictionary from dict, JSON string, or None."""
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    @staticmethod
    def _extract_list(val: Any) -> List[Any]:
        """Safely extracts list from list, JSON string, or None."""
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return []

    @classmethod
    def chunk_scheme(cls, scheme_data: Union[Dict[str, Any], Any]) -> List[SchemeChunk]:
        """
        Generates semantic chunks for a single scheme across all 4 languages.
        Accepts either a seed dictionary or a SQLAlchemy Scheme model instance.
        """
        chunks: List[SchemeChunk] = []

        # 1. Normalize scheme fields whether dict or SQLAlchemy model
        if hasattr(scheme_data, "__table__"):
            # SQLAlchemy model instance
            scheme_id = getattr(scheme_data, "id")
            names = cls._extract_dict(getattr(scheme_data, "names", {}))
            descriptions = cls._extract_dict(getattr(scheme_data, "descriptions", {}))
            benefits = cls._extract_dict(getattr(scheme_data, "benefits", {}))
            financial_amount = getattr(scheme_data, "financial_amount_inr", None)
            category = getattr(scheme_data, "category", "")
            ministry = getattr(scheme_data, "ministry", "")
            scheme_type = getattr(scheme_data, "scheme_type", "CENTRAL_SECTOR")
            official_url = getattr(scheme_data, "official_url", "")
            portal_name = getattr(scheme_data, "portal_name", "")
            last_reviewed_date = getattr(scheme_data, "last_reviewed_date", None)
            source_citation = cls._extract_dict(getattr(scheme_data, "source_citation", {}))
            application_procedure = cls._extract_list(getattr(scheme_data, "application_procedure", []))

            # Rules AST
            rules_attr = getattr(scheme_data, "rules", [])
            if rules_attr and len(rules_attr) > 0:
                first_rule = rules_attr[0]
                rule_conditions = cls._extract_dict(getattr(first_rule, "conditions", {}))
            else:
                rule_conditions = {}

            # Documents
            docs_attr = getattr(scheme_data, "documents", [])
            documents_list = []
            for d in docs_attr:
                documents_list.append({
                    "id": getattr(d, "id"),
                    "names": cls._extract_dict(getattr(d, "names", {})),
                    "descriptions": cls._extract_dict(getattr(d, "descriptions", {})),
                    "is_mandatory": getattr(d, "is_mandatory", True),
                    "issuer": getattr(d, "issuer", "Government Authority"),
                    "source_url": getattr(d, "source_url", None),
                })
        else:
            # Dictionary from schemes_seed.json
            scheme_id = scheme_data["id"]
            names = cls._extract_dict(scheme_data.get("names", {}))
            descriptions = cls._extract_dict(scheme_data.get("descriptions", {}))
            benefits = cls._extract_dict(scheme_data.get("benefits", {}))
            financial_amount = scheme_data.get("financial_amount_inr")
            category = scheme_data.get("category", "")
            ministry = scheme_data.get("ministry", "")
            scheme_type = scheme_data.get("scheme_type", "CENTRAL_SECTOR")
            official_url = scheme_data.get("official_url", "")
            portal_name = scheme_data.get("portal_name", "")
            last_reviewed_date = scheme_data.get("last_reviewed_date")
            source_citation = cls._extract_dict(scheme_data.get("source_citation", {}))
            application_procedure = cls._extract_list(scheme_data.get("application_procedure", []))

            # Rules AST
            rules_val = scheme_data.get("rules", {})
            if isinstance(rules_val, dict):
                rule_conditions = cls._extract_dict(rules_val.get("conditions", {}))
                # Merge rule-level unresolved criteria if present
                if "unresolved_criteria" in rules_val and "unresolved_criteria" not in rule_conditions:
                    rule_conditions["unresolved_criteria"] = rules_val["unresolved_criteria"]
            else:
                rule_conditions = {}

            # Documents
            documents_list = cls._extract_list(scheme_data.get("documents", []))

        # Default source metadata
        default_doc_title = source_citation.get("title", f"{names.get('en', scheme_id)} Guidelines")
        default_source_url = source_citation.get("url") or official_url
        default_authority = source_citation.get("issuing_authority", ministry)
        raw_status = source_citation.get("verification_status", "VERIFIED")
        try:
            default_verification_status = VerificationStatus(raw_status)
        except ValueError:
            default_verification_status = VerificationStatus.VERIFIED

        relevant_sections = source_citation.get("relevant_sections", [])
        overview_section = relevant_sections[0] if relevant_sections else None

        # ----------------------------------------------------------------------
        # 1. CATEGORY: scheme_overview
        # ----------------------------------------------------------------------
        for lang in SUPPORTED_LANGUAGES:
            name_t = names.get(lang) or names.get("en", scheme_id)
            desc_t = descriptions.get(lang) or descriptions.get("en", "")
            overview_text = (
                f"{name_t}: {desc_t} "
                f"(Ministry: {ministry}; Category: {category}; Type: {scheme_type})."
            )

            chunks.append(
                SchemeChunk(
                    chunk_id=f"{scheme_id}_overview_{lang}",
                    scheme_id=scheme_id,
                    category=ChunkCategoryEnum.SCHEME_OVERVIEW,
                    language=lang,
                    content=overview_text,
                    provenance=ChunkProvenanceSchema(
                        source_url=default_source_url,
                        issuing_authority=default_authority,
                        document_title=default_doc_title,
                        relevant_section=overview_section,
                        page_ref=None,
                        verification_status=default_verification_status,
                        last_reviewed_date=last_reviewed_date,
                    ),
                    content_type=ContentTypeEnum.CURATED_SUMMARY,
                    is_verbatim=False,
                )
            )

        # ----------------------------------------------------------------------
        # 2. CATEGORY: scheme_benefit
        # ----------------------------------------------------------------------
        benefit_section = None
        for s in relevant_sections:
            if "benefit" in s.lower() or "assistance" in s.lower():
                benefit_section = s
                break
        if not benefit_section and relevant_sections:
            benefit_section = relevant_sections[0]

        for lang in SUPPORTED_LANGUAGES:
            name_t = names.get(lang) or names.get("en", scheme_id)
            ben_t = benefits.get(lang) or benefits.get("en", "")
            amount_str = f" ₹{financial_amount:,.0f}" if financial_amount else ""
            benefit_content = f"{name_t} Benefits{amount_str}: {ben_t}"

            chunks.append(
                SchemeChunk(
                    chunk_id=f"{scheme_id}_benefit_{lang}",
                    scheme_id=scheme_id,
                    category=ChunkCategoryEnum.SCHEME_BENEFIT,
                    language=lang,
                    content=benefit_content,
                    provenance=ChunkProvenanceSchema(
                        source_url=default_source_url,
                        issuing_authority=default_authority,
                        document_title=default_doc_title,
                        relevant_section=benefit_section,
                        page_ref=None,
                        verification_status=default_verification_status,
                        last_reviewed_date=last_reviewed_date,
                    ),
                    content_type=ContentTypeEnum.CURATED_SUMMARY,
                    is_verbatim=False,
                )
            )

        # ----------------------------------------------------------------------
        # 3. CATEGORY: eligibility_clause (Inclusion conditions: all_of, any_of)
        # ----------------------------------------------------------------------
        inclusion_conditions = []
        for cond in rule_conditions.get("all_of", []):
            if isinstance(cond, dict):
                inclusion_conditions.append(cond)
        for cond in rule_conditions.get("any_of", []):
            if isinstance(cond, dict):
                inclusion_conditions.append(cond)

        for cond in inclusion_conditions:
            cond_id = cond.get("id", "cond")
            cit = cond.get("citation", {})
            clause_section = cit.get("clause")
            page_ref = cit.get("page_ref")  # Exact string or None (never invented)
            cit_url = cit.get("url") or default_source_url

            failure_reason_dict = cond.get("failure_reason", {})
            field_name = cond.get("field", "")
            operator = cond.get("operator", "")
            target_val = cond.get("value", "")

            for lang in SUPPORTED_LANGUAGES:
                name_t = names.get(lang) or names.get("en", scheme_id)
                reason_t = failure_reason_dict.get(lang) or failure_reason_dict.get("en", "")
                if not reason_t:
                    reason_t = f"Requires {field_name} {operator} {target_val}"
                elig_content = f"Eligibility Requirement for {name_t}: {reason_t}"

                chunks.append(
                    SchemeChunk(
                        chunk_id=f"{scheme_id}_elig_{cond_id}_{lang}",
                        scheme_id=scheme_id,
                        category=ChunkCategoryEnum.ELIGIBILITY_CLAUSE,
                        language=lang,
                        content=elig_content,
                        provenance=ChunkProvenanceSchema(
                            source_url=cit_url,
                            issuing_authority=default_authority,
                            document_title=default_doc_title,
                            relevant_section=clause_section,
                            page_ref=page_ref,
                            verification_status=default_verification_status,
                            last_reviewed_date=last_reviewed_date,
                        ),
                        content_type=ContentTypeEnum.CURATED_SUMMARY,
                        is_verbatim=False,
                    )
                )

        # Unresolved criteria that represent inclusion conditions requiring official verification
        unresolved_list = rule_conditions.get("unresolved_criteria", [])
        for idx, unres in enumerate(unresolved_list):
            if not isinstance(unres, dict):
                continue
            unres_clause = unres.get("clause")
            unres_title = unres.get("title", f"Criterion {idx+1}")
            unres_desc = unres.get("description", "")
            unres_method = unres.get("verification_method", "")
            raw_v_status = unres.get("status") or unres.get("verification_status", "REQUIRES_OFFICIAL_VERIFICATION")
            try:
                v_status = VerificationStatus(raw_v_status)
            except ValueError:
                v_status = VerificationStatus.REQUIRES_OFFICIAL_VERIFICATION

            # Categorize: if clause specifies exclusions, route to exclusion_clause, else eligibility_clause
            is_exclusion = "exclusion" in (unres_clause or "").lower() or "disqualification" in unres_desc.lower()
            cat = ChunkCategoryEnum.EXCLUSION_CLAUSE if is_exclusion else ChunkCategoryEnum.ELIGIBILITY_CLAUSE
            prefix = "excl" if is_exclusion else "elig"

            for lang in SUPPORTED_LANGUAGES:
                name_t = names.get(lang) or names.get("en", scheme_id)
                unres_content = (
                    f"{'Exclusion' if is_exclusion else 'Eligibility'} parameter for {name_t} - {unres_title}: "
                    f"{unres_desc} (Official verification method: {unres_method})."
                )

                chunks.append(
                    SchemeChunk(
                        chunk_id=f"{scheme_id}_{prefix}_unres_{idx+1}_{lang}",
                        scheme_id=scheme_id,
                        category=cat,
                        language=lang,
                        content=unres_content,
                        provenance=ChunkProvenanceSchema(
                            source_url=default_source_url,
                            issuing_authority=default_authority,
                            document_title=default_doc_title,
                            relevant_section=unres_clause,
                            page_ref=None,
                            verification_status=v_status,
                            last_reviewed_date=last_reviewed_date,
                        ),
                        content_type=ContentTypeEnum.CURATED_SUMMARY,
                        is_verbatim=False,
                    )
                )

        # ----------------------------------------------------------------------
        # 4. CATEGORY: exclusion_clause (Deterministic exclusion rules: none_of)
        # ----------------------------------------------------------------------
        exclusion_conditions = []
        for cond in rule_conditions.get("none_of", []):
            if isinstance(cond, dict):
                exclusion_conditions.append(cond)

        for cond in exclusion_conditions:
            cond_id = cond.get("id", "excl")
            cit = cond.get("citation", {})
            clause_section = cit.get("clause")
            page_ref = cit.get("page_ref")  # Exact string or None (never invented)
            cit_url = cit.get("url") or default_source_url

            failure_reason_dict = cond.get("failure_reason", {})
            field_name = cond.get("field", "")
            operator = cond.get("operator", "")
            target_val = cond.get("value", "")

            for lang in SUPPORTED_LANGUAGES:
                name_t = names.get(lang) or names.get("en", scheme_id)
                reason_t = failure_reason_dict.get(lang) or failure_reason_dict.get("en", "")
                if not reason_t:
                    reason_t = f"Disqualified if {field_name} {operator} {target_val}"
                excl_content = f"Disqualification / Exclusion parameter for {name_t}: {reason_t}"

                chunks.append(
                    SchemeChunk(
                        chunk_id=f"{scheme_id}_excl_{cond_id}_{lang}",
                        scheme_id=scheme_id,
                        category=ChunkCategoryEnum.EXCLUSION_CLAUSE,
                        language=lang,
                        content=excl_content,
                        provenance=ChunkProvenanceSchema(
                            source_url=cit_url,
                            issuing_authority=default_authority,
                            document_title=default_doc_title,
                            relevant_section=clause_section,
                            page_ref=page_ref,
                            verification_status=default_verification_status,
                            last_reviewed_date=last_reviewed_date,
                        ),
                        content_type=ContentTypeEnum.CURATED_SUMMARY,
                        is_verbatim=False,
                    )
                )

        # ----------------------------------------------------------------------
        # 5. CATEGORY: document_requirement
        # ----------------------------------------------------------------------
        for doc in documents_list:
            if not isinstance(doc, dict):
                continue
            doc_id = doc.get("id", "doc")
            doc_names = cls._extract_dict(doc.get("names", {}))
            doc_descs = cls._extract_dict(doc.get("descriptions", {}))
            is_mandatory = doc.get("is_mandatory", True)
            issuer = doc.get("issuer", "Government Authority")
            doc_url = doc.get("source_url") or default_source_url

            for lang in SUPPORTED_LANGUAGES:
                name_t = names.get(lang) or names.get("en", scheme_id)
                doc_name_t = doc_names.get(lang) or doc_names.get("en", doc_id)
                doc_desc_t = doc_descs.get(lang) or doc_descs.get("en", "")
                mand_str = "Mandatory" if is_mandatory else "Optional / Alternative"

                doc_content = (
                    f"Required Supporting Document for {name_t} - {doc_name_t}: {doc_desc_t} "
                    f"({mand_str}; Issuing Authority: {issuer})."
                )

                chunks.append(
                    SchemeChunk(
                        chunk_id=f"{scheme_id}_doc_{doc_id}_{lang}",
                        scheme_id=scheme_id,
                        category=ChunkCategoryEnum.DOCUMENT_REQUIREMENT,
                        language=lang,
                        content=doc_content,
                        provenance=ChunkProvenanceSchema(
                            source_url=doc_url,
                            issuing_authority=issuer,
                            document_title=f"{doc_name_t} Guidelines",
                            relevant_section="Required Supporting Documents",
                            page_ref=None,
                            verification_status=default_verification_status,
                            last_reviewed_date=last_reviewed_date,
                        ),
                        content_type=ContentTypeEnum.CURATED_SUMMARY,
                        is_verbatim=False,
                    )
                )

        # ----------------------------------------------------------------------
        # 6. CATEGORY: application_procedure
        # ----------------------------------------------------------------------
        for step in application_procedure:
            if not isinstance(step, dict):
                continue
            step_num = step.get("step_number", 1)
            step_titles = cls._extract_dict(step.get("titles", {}))
            step_descs = cls._extract_dict(step.get("descriptions", {}))
            step_channel = step.get("channel", "ONLINE")

            for lang in SUPPORTED_LANGUAGES:
                name_t = names.get(lang) or names.get("en", scheme_id)
                step_title_t = step_titles.get(lang) or step_titles.get("en", f"Step {step_num}")
                step_desc_t = step_descs.get(lang) or step_descs.get("en", "")

                step_content = (
                    f"Application Procedure Step {step_num} for {name_t} - {step_title_t}: "
                    f"{step_desc_t} (Filing Channel: {step_channel})."
                )

                chunks.append(
                    SchemeChunk(
                        chunk_id=f"{scheme_id}_proc_step{step_num}_{lang}",
                        scheme_id=scheme_id,
                        category=ChunkCategoryEnum.APPLICATION_PROCEDURE,
                        language=lang,
                        content=step_content,
                        provenance=ChunkProvenanceSchema(
                            source_url=official_url or default_source_url,
                            issuing_authority=default_authority,
                            document_title=portal_name or default_doc_title,
                            relevant_section=f"Application Procedure (Step {step_num})",
                            page_ref=None,
                            verification_status=default_verification_status,
                            last_reviewed_date=last_reviewed_date,
                        ),
                        content_type=ContentTypeEnum.CURATED_SUMMARY,
                        is_verbatim=False,
                    )
                )

        return chunks

    @classmethod
    def chunk_all_schemes(cls, schemes_data: List[Union[Dict[str, Any], Any]]) -> List[SchemeChunk]:
        """Chunks a collection of schemes across all 4 languages."""
        all_chunks: List[SchemeChunk] = []
        for scheme in schemes_data:
            all_chunks.extend(cls.chunk_scheme(scheme))
        logger.info(f"Chunked {len(schemes_data)} scheme(s) into {len(all_chunks)} semantic chunks.")
        return all_chunks

