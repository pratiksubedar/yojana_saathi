"""
Yojana Saathi - RAG Retriever Service
Milestone 6.1: Zero-cost, local-first RAG retrieval engine using SQLite FTS5 BM25.
Retrieves semantic scheme chunks across all 4 languages with Unicode preservation,
curated synonym expansion, relevance ranking, and noise filtering.
"""

import logging
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.schemas.provenance import VerificationStatus
from app.schemas.rag import (
    ChunkCategoryEnum,
    ChunkProvenanceSchema,
    ChunkSearchResult,
    ContentTypeEnum,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
    SchemeChunk,
)
from app.services.citation_formatter import CitationFormatter
from app.services.search_service import normalize_query_tokens
from app.services.search_synonyms import COMMON_QUERY_EXPANSIONS, SCHEME_SEARCH_METADATA

logger = logging.getLogger(__name__)

STOP_WORDS: Set[str] = {
    # English
    "the", "is", "in", "and", "or", "for", "to", "of", "with", "a", "an", "on", "at", "by", "from",
    "how", "what", "which", "who", "when", "where", "can", "i", "do", "does", "any", "all",
    "my", "me", "we", "our", "you", "your", "he", "she", "his", "her", "they", "their", "it", "its",
    "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "no", "not",
    "want", "need", "start", "receive", "get", "give", "tell", "please", "there", "here", "this", "that",
    "about", "already", "applied", "check", "some", "more", "know", "help",
    # Hindi
    "का", "की", "के", "में", "और", "से", "पर", "है", "हैं", "को", "या", "क्या", "कैसे",
    # Kannada
    "ಮತ್ತು", "ಅಥವಾ", "ನಲ್ಲಿ", "ಗೆ", "ಯ", "ರ", "ಇಂದ", "ಒಂದು", "ಹೇಗೆ", "ಏನು",
    # Telugu
    "మరియు", "లేదా", "లో", "కోసం", "యొక్క", "నుండి", "ఎలా", "ఏమిటి",
}
# 0: chunk_id (UNINDEXED) -> 0.0
# 1: scheme_id            -> 5.0
# 2: category             -> 3.0
# 3: language             -> 2.0
# 4: content              -> 10.0 (highest content weight)
# 5: document_title       -> 4.0
# 6: issuing_authority    -> 2.0
# 7: relevant_section     -> 3.0
BM25_WEIGHTS_SQL = "0.0, 5.0, 3.0, 2.0, 10.0, 4.0, 2.0, 3.0"

# Category intent mapping for automatic category detection
INTENT_KEYWORDS: Dict[ChunkCategoryEnum, Set[str]] = {
    ChunkCategoryEnum.SCHEME_BENEFIT: {
        "benefit", "benefits", "assistance", "money", "rupees", "cash", "grant", "subsidy", "amount",
        "लाभ", "सहायता", "पैसे", "रुपये", "अनुदान", "किस्त",
        "ಪ್ರಯೋಜನ", "ಸಹಾಯಧನ", "ಹಣ", "ಅನುದಾನ", "ಕಂತು",
        "ప్రయోజనాలు", "సహాయం", "డబ్బు", "రూపాయలు", "సబ్సిడీ", "విడత",
    },
    ChunkCategoryEnum.DOCUMENT_REQUIREMENT: {
        "document", "documents", "certificate", "card", "proof", "ration", "aadhaar", "pan",
        "दस्तावेज", "दस्तावेज़", "प्रमाण", "कार्ड", "राशन", "आधार",
        "ದಾಖಲೆ", "ದಾಖಲೆಗಳು", "ಪ್ರಮಾಣಪತ್ರ", "ಕಾರ್ಡ್", "ರೇಷನ್", "ಆಧಾರ್",
        "పత్రాలు", "ధ్రువీకరణ", "కార్డు", "రేషన్", "ఆధార్",
    },
    ChunkCategoryEnum.APPLICATION_PROCEDURE: {
        "apply", "application", "procedure", "process", "register", "registration", "portal", "step", "csc",
        "आवेदन", "प्रक्रिया", "पंजीकरण", "पोर्टल", "चरण",
        "ಅರ್ಜಿ", "ನೋಂದಣಿ", "ಪ್ರಕ್ರಿಯೆ", "ಪೋರ್ಟಲ್", "ಹಂತ",
        "దరఖాస్తు", "నమోదు", "విధానం", "పోర్టల్", "దశ",
    },
    ChunkCategoryEnum.ELIGIBILITY_CLAUSE: {
        "eligible", "eligibility", "qualify", "requirement", "criteria", "who", "can",
        "पात्र", "पात्रता", "शर्त", "मापदंड",
        "ಅರ್ಹ", "ಅರ್ಹತೆ", "ಮಾನದಂಡ", "ಷರತ್ತು",
        "అర్హత", "అర్హులు", "నిబంధనలు", "పరిమితి",
    },
    ChunkCategoryEnum.EXCLUSION_CLAUSE: {
        "exclude", "excluded", "exclusion", "disqualify", "ineligible", "not eligible", "cannot",
        "अपात्र", "बहिष्कार", "अपात्रता", "छूट",
        "ಅನರ್ಹ", "ಹೊರತುಪಡಿಸಿ", "ಅನರ್ಹತೆ",
        "అనర్హత", "మినహాయింపు", "అనర్హులు",
    },
}


def build_fts5_chunk_query(tokens: List[str]) -> str:
    """
    Safely formats normalized tokens into a SQLite FTS5 prefix match expression.
    e.g., ["farmer", "kisan"] -> '"farmer"* OR "kisan"*'
    """
    if not tokens:
        return ""
    quoted = [f'"{tok}"*' for tok in tokens if tok]
    return " OR ".join(quoted)


def calculate_relevance_score(bm25_rank: float) -> float:
    """
    Converts raw SQLite FTS5 BM25 rank (negative float where more negative = more relevant)
    into a normalized score strictly in range [0.0, 1.0].
    """
    abs_rank = abs(bm25_rank)
    if abs_rank <= 0.0:
        return 0.0
    # Rational bounding function: score approaches 1.0 as abs_rank increases
    score = abs_rank / (1.0 + abs_rank)
    return round(float(score), 4)


class RAGRetrieverService:
    """
    High-precision, local-first RAG retriever backed by SQLite FTS5 and BM25 ranking.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    async def _get_session(self):
        if self._session is not None:
            return self._session, False
        return async_session_factory(), True

    @classmethod
    def expand_query_tokens(cls, query: str) -> List[str]:
        """
        Extracts normalized tokens and expands them using curated multilingual synonyms.
        """
        raw_tokens = normalize_query_tokens(query)
        if not raw_tokens:
            return []

        expanded: Set[str] = set(raw_tokens)
        lower_q = query.strip().lower()

        # 1. Expand from common query expansions
        for phrase, expansion_tokens in COMMON_QUERY_EXPANSIONS.items():
            if phrase in lower_q:
                expanded.update(expansion_tokens)

        # 2. Expand from scheme metadata synonyms and keywords
        for scheme_id, meta in SCHEME_SEARCH_METADATA.items():
            # If scheme_id or alias is mentioned
            if scheme_id in lower_q or any(syn.lower() in lower_q for syn in meta.get("synonyms", [])):
                expanded.add(scheme_id)
                for syn in meta.get("synonyms", [])[:3]:
                    expanded.update(normalize_query_tokens(syn))

        return [tok for tok in expanded if tok]

    @classmethod
    def detect_category_intent(cls, query: str) -> Optional[ChunkCategoryEnum]:
        """
        Detects if query strongly indicates a specific chunk category intent.
        """
        lower_q = query.strip().lower()
        tokens = set(normalize_query_tokens(query))
        for cat, keywords in INTENT_KEYWORDS.items():
            if any(kw in lower_q or kw in tokens for kw in keywords):
                return cat
        return None

    async def search(
        self,
        query: str,
        language: Optional[str] = None,
        category: Optional[ChunkCategoryEnum] = None,
        scheme_id: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.05,
    ) -> List[ChunkSearchResult]:
        """
        Executes multilingual BM25 search over scheme chunks with fallback and filtering.
        """
        clean_tokens = self.expand_query_tokens(query)
        if not clean_tokens:
            logger.info("RAG search query contains no valid tokens; returning empty results.")
            return []

        fts_expression = build_fts5_chunk_query(clean_tokens)
        session, is_local_session = await self._get_session()

        results_by_chunk_id: Dict[str, ChunkSearchResult] = {}

        try:
            # 1. PRIMARY FTS5 BM25 SEARCH
            fts_sql = text(f"""
                SELECT
                    c.chunk_id,
                    c.scheme_id,
                    c.category,
                    c.language,
                    c.content,
                    c.source_url,
                    c.issuing_authority,
                    c.document_title,
                    c.relevant_section,
                    c.page_ref,
                    c.verification_status,
                    c.last_reviewed_date,
                    c.content_type,
                    c.is_verbatim,
                    bm25(scheme_chunks_fts, {BM25_WEIGHTS_SQL}) AS bm25_rank
                FROM scheme_chunks_fts f
                JOIN scheme_chunks c ON c.chunk_id = f.chunk_id
                WHERE scheme_chunks_fts MATCH :query
                  AND (:language IS NULL OR c.language = :language)
                  AND (:category IS NULL OR c.category = :category)
                  AND (:scheme_id IS NULL OR c.scheme_id = :scheme_id)
                ORDER BY bm25_rank ASC
                LIMIT :limit
            """)

            res = await session.execute(
                fts_sql,
                {
                    "query": fts_expression,
                    "language": language,
                    "category": category.value if category else None,
                    "scheme_id": scheme_id,
                    "limit": limit * 2,
                },
            )
            rows = res.fetchall()

            raw_tokens = normalize_query_tokens(query)
            substantive_tokens = [t.lower() for t in raw_tokens if t.lower() not in STOP_WORDS and len(t) > 1]

            for r in rows:
                raw_status = r[10]
                try:
                    v_status = VerificationStatus(raw_status)
                except ValueError:
                    v_status = VerificationStatus.VERIFIED

                raw_cat = r[2]
                try:
                    cat_enum = ChunkCategoryEnum(raw_cat)
                except ValueError:
                    cat_enum = ChunkCategoryEnum.SCHEME_OVERVIEW

                raw_ctype = r[12]
                try:
                    ctype_enum = ContentTypeEnum(raw_ctype)
                except ValueError:
                    ctype_enum = ContentTypeEnum.CURATED_SUMMARY

                bm25_val = float(r[14])
                base_score = calculate_relevance_score(bm25_val)

                # Check substantive token overlap to suppress incidental noise
                content_lower = (r[4] or "").lower()
                title_lower = (r[7] or "").lower()
                scheme_id_lower = (r[1] or "").lower()
                searchable_text = f"{content_lower} {title_lower} {scheme_id_lower}"
                # Normalize commas in numbers (e.g. 6,000 -> 6000)
                searchable_text = re.sub(r"(\d),(\d)", r"\1\2", searchable_text)

                if substantive_tokens:
                    matched_tokens = sum(1 for tok in substantive_tokens if tok in searchable_text)
                    overlap_ratio = matched_tokens / len(substantive_tokens)

                    # For multi-token queries (>2 substantive words), require at least 20% overlap
                    if len(substantive_tokens) >= 3 and overlap_ratio < 0.20:
                        continue
                    if len(substantive_tokens) == 2 and overlap_ratio < 0.35:
                        continue
                    # Scale score by overlap
                    score = round(base_score * max(0.4, overlap_ratio), 4)
                else:
                    score = base_score

                if score < min_score:
                    continue

                chunk = SchemeChunk(
                    chunk_id=r[0],
                    scheme_id=r[1],
                    category=cat_enum,
                    language=r[3],
                    content=r[4],
                    provenance=ChunkProvenanceSchema(
                        source_url=r[5],
                        issuing_authority=r[6],
                        document_title=r[7],
                        relevant_section=r[8],
                        page_ref=r[9],
                        verification_status=v_status,
                        last_reviewed_date=r[11],
                    ),
                    content_type=ctype_enum,
                    is_verbatim=bool(r[13]),
                )

                results_by_chunk_id[chunk.chunk_id] = ChunkSearchResult(
                    chunk=chunk,
                    relevance_score=score,
                    bm25_rank=bm25_val,
                    match_type="fts5_bm25",
                )

            # 2. SUBSTRING FALLBACK FOR COMPOUND INDIC TOKENS
            # If results are below limit and query contains Indic or short tokens
            if len(results_by_chunk_id) < limit:
                raw_q_tokens = normalize_query_tokens(query)
                for tok in raw_q_tokens:
                    if len(tok) < 2:
                        continue
                    like_pattern = f"%{tok}%"
                    sub_sql = text("""
                        SELECT
                            chunk_id, scheme_id, category, language, content,
                            source_url, issuing_authority, document_title,
                            relevant_section, page_ref, verification_status,
                            last_reviewed_date, content_type, is_verbatim
                        FROM scheme_chunks
                        WHERE (content LIKE :pat OR document_title LIKE :pat)
                          AND (:language IS NULL OR language = :language)
                          AND (:category IS NULL OR category = :category)
                          AND (:scheme_id IS NULL OR scheme_id = :scheme_id)
                        LIMIT :limit
                    """)
                    sub_res = await session.execute(
                        sub_sql,
                        {
                            "pat": like_pattern,
                            "language": language,
                            "category": category.value if category else None,
                            "scheme_id": scheme_id,
                            "limit": limit,
                        },
                    )
                    sub_rows = sub_res.fetchall()

                    for r in sub_rows:
                        cid = r[0]
                        if cid in results_by_chunk_id:
                            continue

                        try:
                            v_status = VerificationStatus(r[10])
                        except ValueError:
                            v_status = VerificationStatus.VERIFIED

                        try:
                            cat_enum = ChunkCategoryEnum(r[2])
                        except ValueError:
                            cat_enum = ChunkCategoryEnum.SCHEME_OVERVIEW

                        try:
                            ctype_enum = ContentTypeEnum(r[12])
                        except ValueError:
                            ctype_enum = ContentTypeEnum.CURATED_SUMMARY

                        content_lower = (r[4] or "").lower()
                        title_lower = (r[7] or "").lower()
                        scheme_id_lower = (r[1] or "").lower()
                        searchable_text = f"{content_lower} {title_lower} {scheme_id_lower}"
                        searchable_text = re.sub(r"(\d),(\d)", r"\1\2", searchable_text)

                        if substantive_tokens:
                            matched_tokens = sum(1 for st in substantive_tokens if st in searchable_text)
                            overlap_ratio = matched_tokens / len(substantive_tokens)
                            if len(substantive_tokens) >= 3 and overlap_ratio < 0.20:
                                continue
                            if len(substantive_tokens) == 2 and overlap_ratio < 0.35:
                                continue
                            fallback_score = round(0.45 * max(0.4, overlap_ratio), 4)
                        else:
                            fallback_score = 0.45

                        if fallback_score < min_score:
                            continue

                        chunk = SchemeChunk(
                            chunk_id=cid,
                            scheme_id=r[1],
                            category=cat_enum,
                            language=r[3],
                            content=r[4],
                            provenance=ChunkProvenanceSchema(
                                source_url=r[5],
                                issuing_authority=r[6],
                                document_title=r[7],
                                relevant_section=r[8],
                                page_ref=r[9],
                                verification_status=v_status,
                                last_reviewed_date=r[11],
                            ),
                            content_type=ctype_enum,
                            is_verbatim=bool(r[13]),
                        )

                        results_by_chunk_id[cid] = ChunkSearchResult(
                            chunk=chunk,
                            relevance_score=fallback_score,
                            bm25_rank=-0.5,
                            match_type="substring_fallback",
                        )

        finally:
            if is_local_session:
                await session.close()

        # Sort all results descending by relevance_score
        sorted_results = sorted(
            results_by_chunk_id.values(),
            key=lambda x: x.relevance_score,
            reverse=True,
        )

        return sorted_results[:limit]

    async def retrieve(self, request: RAGRetrievalRequest) -> RAGRetrievalResponse:
        """
        Executes end-to-end RAG retrieval, extracts verified citations,
        and produces localized markdown references.
        """
        results = await self.search(
            query=request.query,
            language=request.language,
            category=request.category,
            scheme_id=request.scheme_id,
            limit=request.limit,
            min_score=request.min_score,
        )

        target_lang = request.language or "en"
        citations = [
            CitationFormatter.format_citation(r.chunk, target_lang)
            for r in results
        ]
        citations_md = CitationFormatter.format_citations_markdown(citations, target_lang)

        return RAGRetrievalResponse(
            query=request.query,
            language=request.language,
            total_results=len(results),
            results=results,
            citations=citations,
            formatted_citations_markdown=citations_md,
        )
