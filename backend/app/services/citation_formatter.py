"""
Yojana Saathi - Provenance-Aware Citation Formatter
Milestone 6.1: Formats authoritative citations from retrieved chunks.
Strictly preserves verified metadata, distinguishes curated summaries from
verbatim official quotations, and renders multilingual markdown references.
"""

from typing import Dict, List, Optional
from app.schemas.provenance import VerificationStatus
from app.schemas.rag import (
    ContentTypeEnum,
    ProvenanceCitation,
    SchemeChunk,
)

# Multilingual status disclosures
STATUS_DISCLOSURES: Dict[VerificationStatus, Dict[str, str]] = {
    VerificationStatus.VERIFIED: {
        "en": "Verified against official government guidelines.",
        "hi": "आधिकारिक सरकारी दिशानिर्देशों के अनुसार सत्यापित।",
        "kn": "ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಮಾರ್ಗಸೂಚಿಗಳ ಪ್ರಕಾರ ಪರಿಶೀಲಿಸಲಾಗಿದೆ.",
        "te": "అధికారిక ప్రభుత్వ మార్గదర్శకాల ప్రకారం ధృవీకరించబడింది.",
    },
    VerificationStatus.PARTIALLY_VERIFIED: {
        "en": "Partially verified; specific operational guidelines pending confirmation.",
        "hi": "आंशिक रूप से सत्यापित; विशिष्ट परिचालन दिशानिर्देश पुष्टि हेतु प्रतीक्षारत हैं।",
        "kn": "ಭಾಗಶಃ ಪರಿಶೀಲಿಸಲಾಗಿದೆ; ನಿರ್ದಿಷ್ಟ ಮಾರ್ಗಸೂಚಿಗಳು ದೃಢೀಕರಣದ ನಿರೀಕ್ಷೆಯಲ್ಲಿವೆ.",
        "te": "పాక్షికంగా ధృవీకరించబడింది; నిర్దిష్ట కార్యాచరణ మార్గదర్శకాలు నిర్ధారణ కోసం వేచి ఉన్నాయి.",
    },
    VerificationStatus.REQUIRES_OFFICIAL_VERIFICATION: {
        "en": "Requires official physical or administrative verification by competent authorities.",
        "hi": "सक्षम अधिकारियों द्वारा आधिकारिक भौतिक या प्रशासनिक सत्यापन अनिवार्य है।",
        "kn": "ಸಕ್ಷಮ ಪ್ರಾಧಿಕಾರಗಳಿಂದ ಭೌತಿಕ ಅಥವಾ ಆಡಳಿತಾತ್ಮಕ ಪರಿಶೀಲನೆ ಕಡ್ಡಾಯವಾಗಿದೆ.",
        "te": "సమర్థ ప్రాధికార సంస్థల ద్వారా భౌతిక లేదా పరిపాలనా ధృవీకరణ తప్పనిసరి.",
    },
    VerificationStatus.UNVERIFIED: {
        "en": "Unverified; guidelines have not been formally established as official policy.",
        "hi": "असत्यापित; दिशानिर्देश अभी औपचारिक नीति के रूप में स्थापित नहीं हुए हैं।",
        "kn": "ದೃಢೀಕರಿಸಲಾಗಿಲ್ಲ; ಮಾರ್ಗಸೂಚಿಗಳನ್ನು ಅಧಿಕೃತ ನೀತಿಯಾಗಿ ಅಳವಡಿಸಲಾಗಿಲ್ಲ.",
        "te": "ధృవీకరించబడలేదు; మార్గదర్శకాలు అధికారిక విధానంగా స్థిరపడలేదు.",
    },
}

ATTRIBUTION_LABELS: Dict[ContentTypeEnum, Dict[str, str]] = {
    ContentTypeEnum.CURATED_SUMMARY: {
        "en": "Curated Summary from Official Guidelines",
        "hi": "आधिकारिक दिशानिर्देशों का क्यूरेटेड सारांश",
        "kn": "ಅಧಿಕೃತ ಮಾರ್ಗಸೂಚಿಗಳ ಸಾರಾಂಶ",
        "te": "అధికారిక మార్గదర్శకాల సారాంశం",
    },
    ContentTypeEnum.VERBATIM_OFFICIAL_TEXT: {
        "en": "Official Quotation (Verbatim)",
        "hi": "आधिकारिक उद्धरण (यथावत)",
        "kn": "ಅಧಿಕೃತ ಉಲ್ಲೇಖ (ಯಥಾವತ್)",
        "te": "అధికారిక ఉల్లేఖన (యథాతథం)",
    },
}

REFERENCES_HEADER: Dict[str, str] = {
    "en": "Official Sources & Provenance",
    "hi": "आधिकारिक स्रोत एवं साक्ष्य",
    "kn": "ಅಧಿಕೃತ ಮೂಲಗಳು ಮತ್ತು ಪರಿಶೀಲನೆ",
    "te": "అధికారిక ఆధారాలు మరియు మూలాలు",
}


class CitationFormatter:
    """
    Transforms chunk metadata into verifiable, provenance-grounded citations.
    Enforces anti-hallucination rules: never fabricates missing sections,
    pages, or authorities.
    """

    @classmethod
    def format_citation(cls, chunk: SchemeChunk, language: str = "en") -> ProvenanceCitation:
        """
        Extracts and formats an authoritative citation from a SchemeChunk.
        """
        lang = language if language in ["en", "hi", "kn", "te"] else "en"
        prov = chunk.provenance

        # Determine verification disclosure
        v_status = prov.verification_status
        disclosure_dict = STATUS_DISCLOSURES.get(v_status, STATUS_DISCLOSURES[VerificationStatus.VERIFIED])
        disclosure = disclosure_dict.get(lang, disclosure_dict["en"])

        # Determine attribution label
        attr_dict = ATTRIBUTION_LABELS.get(chunk.content_type, ATTRIBUTION_LABELS[ContentTypeEnum.CURATED_SUMMARY])
        attribution = attr_dict.get(lang, attr_dict["en"])

        return ProvenanceCitation(
            chunk_id=chunk.chunk_id,
            scheme_id=chunk.scheme_id,
            category=chunk.category,
            document_title=prov.document_title,
            issuing_authority=prov.issuing_authority,
            source_url=prov.source_url,
            relevant_section=prov.relevant_section,
            page_ref=prov.page_ref,
            verification_status=v_status,
            status_disclosure=disclosure,
            last_reviewed_date=prov.last_reviewed_date,
            content_type=chunk.content_type,
            is_verbatim=chunk.is_verbatim,
            attribution_label=attribution,
        )

    @classmethod
    def format_inline_citation(cls, citation: ProvenanceCitation) -> str:
        """
        Creates a compact inline citation tag for assistant responses:
        e.g., [PM-KISAN Operational Guidelines, Section 2.1, Page 2]
        """
        parts = [citation.document_title]
        if citation.relevant_section:
            parts.append(citation.relevant_section)
        if citation.page_ref:
            parts.append(citation.page_ref)
        return f"[{', '.join(parts)}]"

    @classmethod
    def format_citations_markdown(
        cls,
        citations: List[ProvenanceCitation],
        language: str = "en",
    ) -> str:
        """
        Renders a deduplicated, structured markdown bibliography block.
        Never labels curated summaries as official quotations.
        """
        if not citations:
            return ""

        lang = language if language in ["en", "hi", "kn", "te"] else "en"
        header = REFERENCES_HEADER.get(lang, REFERENCES_HEADER["en"])

        # Deduplicate citations by (document_title, source_url, relevant_section, page_ref)
        seen = set()
        deduped: List[ProvenanceCitation] = []
        for cit in citations:
            key = (cit.document_title, cit.source_url, cit.relevant_section, cit.page_ref)
            if key not in seen:
                seen.add(key)
                deduped.append(cit)

        lines: List[str] = [f"### {header}", ""]

        for idx, cit in enumerate(deduped, 1):
            # Attribution indicator
            prefix = f"[{cit.attribution_label}]"
            lines.append(f"{idx}. **{prefix} {cit.document_title}**")
            lines.append(f"   - **Issuing Authority:** {cit.issuing_authority}")

            # Include relevant section only if genuinely present
            if cit.relevant_section and cit.page_ref:
                lines.append(f"   - **Section / Page:** {cit.relevant_section}, {cit.page_ref}")
            elif cit.relevant_section:
                lines.append(f"   - **Section:** {cit.relevant_section}")
            elif cit.page_ref:
                lines.append(f"   - **Page:** {cit.page_ref}")

            lines.append(f"   - **Official Source:** {cit.source_url}")
            lines.append(f"   - **Verification Status:** {cit.status_disclosure}")

            if cit.last_reviewed_date:
                lines.append(f"   - **Last Reviewed:** {cit.last_reviewed_date}")

            lines.append("")

        return "\n".join(lines).strip()

