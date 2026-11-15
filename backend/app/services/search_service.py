"""
Yojana Saathi - SQLite FTS5 Multilingual Search Service
Zero-cost, local-first full-text search engine with BM25 ranking,
Unicode normalization, and curated synonym expansion across
English, Hindi, Kannada, and Telugu.
"""

import math
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import text, select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Scheme
from app.services.search_synonyms import SCHEME_SEARCH_METADATA, COMMON_QUERY_EXPANSIONS

# 16 BM25 column weights corresponding to schemes_fts columns in declared order:
# 0: scheme_id (UNINDEXED) -> 0.0
# 1: code                  -> 5.0
# 2-5: names (en, hi, kn, te) -> 10.0
# 6-9: descriptions (en, hi, kn, te) -> 1.0
# 10-13: benefits (en, hi, kn, te) -> 2.0
# 14: keywords             -> 4.0
# 15: synonyms             -> 3.0
BM25_WEIGHTS_SQL = "0.0, 5.0, 10.0, 10.0, 10.0, 10.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0, 4.0, 3.0"


def _is_valid_unicode_token_char(ch: str) -> bool:
    """
    Checks if a character is a valid Unicode letter (L), number (N),
    or combining mark (M: matras, viramas, anusvaras across all scripts).
    Does NOT rely on manual hex ranges.
    """
    cat = unicodedata.category(ch)
    return cat.startswith("L") or cat.startswith("N") or cat.startswith("M")


def normalize_query_tokens(text_input: str) -> List[str]:
    """
    Normalizes search text:
    - Normalizes currency and thousands separators (e.g. '₹6,000' or '6,000' -> '6000').
    - Preserves all Unicode letters, numbers, and combining marks across Indic & Latin scripts.
    - Safely strips punctuation and FTS5 control characters without throwing errors.
    """
    if not text_input:
        return []

    # 1. Normalize currency symbols and thousands separators:
    # Remove rupee symbols, Rs, INR, etc.
    t = re.sub(r"[₹\u20B9]", " ", text_input)
    t = re.sub(r"\b(rs|inr)\b\.?", " ", t, flags=re.IGNORECASE)
    # Remove commas between digits: '6,000' -> '6000', '15,000' -> '15000'
    t = re.sub(r"(\d),(\d)", r"\1\2", t)

    # 2. Extract valid tokens preserving all Unicode letters, marks, and numbers
    tokens: List[str] = []
    current: List[str] = []

    for ch in t:
        if _is_valid_unicode_token_char(ch) or ch == "-":
            current.append(ch)
        else:
            if current:
                token = "".join(current).strip("-")
                if token:
                    tokens.append(token)
                current = []
    if current:
        token = "".join(current).strip("-")
        if token:
            tokens.append(token)

    return tokens


def build_fts5_query(user_q: str) -> Optional[str]:
    """
    Safely constructs an FTS5 MATCH query string:
    - Tokenizes and cleans input using Unicode category preservation.
    - Normalizes numeric terms (e.g. ₹6,000 -> 6000).
    - Expands queries using curated synonyms (without conflating schemes).
    - Safely quotes tokens to prevent FTS5 syntax errors: \"token\"*.
    """
    tokens = normalize_query_tokens(user_q)
    if not tokens:
        return None

    # Check for synonym expansions
    expanded_terms: Set[str] = set()
    raw_lower = user_q.strip().lower()

    # Exact multi-word phrase match in synonyms
    if raw_lower in COMMON_QUERY_EXPANSIONS:
        for exp in COMMON_QUERY_EXPANSIONS[raw_lower]:
            expanded_terms.update(normalize_query_tokens(exp))

    # Token-level expansion
    for tok in tokens:
        tok_lower = tok.lower()
        if tok_lower in COMMON_QUERY_EXPANSIONS:
            for exp in COMMON_QUERY_EXPANSIONS[tok_lower]:
                expanded_terms.update(normalize_query_tokens(exp))

    # Build quoted prefix query terms
    all_query_tokens = list(dict.fromkeys(tokens + list(expanded_terms)))

    parts: List[str] = []
    for t in all_query_tokens:
        safe_t = t.replace('"', '""')
        # Use prefix matching: "token"*
        parts.append(f'"{safe_t}"*')

    if not parts:
        return None

    return " OR ".join(parts)


class SearchService:
    """
    High-performance multilingual SQLite FTS5 search service
    with BM25 relevance ranking and deterministic fallback.
    """

    @classmethod
    async def search_schemes(
        cls,
        session: AsyncSession,
        q: Optional[str] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        scheme_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Scheme], int]:
        """
        Executes a multilingual search over welfare schemes.
        When `q` is provided, executes an FTS5 MATCH query with BM25 ranking.
        When `q` is absent, executes standard filtered SQL retrieval.
        """
        # If no query string, use standard SQL filtering
        if not q or not q.strip():
            return await cls._search_standard_sql(
                session=session,
                category=category,
                state=state,
                scheme_type=scheme_type,
                page=page,
                page_size=page_size,
            )

        # 1. Build and sanitize FTS5 query expression
        clean_q = q.strip()
        fts_expr = build_fts5_query(clean_q)

        # If user entered only punctuation / symbols that yield no tokens
        if not fts_expr:
            return [], 0

        # 2. Check FTS5 virtual table
        try:
            # Query FTS5 table with BM25 score joined with schemes table
            sql_query = text(f"""
                SELECT f.scheme_id, bm25(schemes_fts, {BM25_WEIGHTS_SQL}) as score
                FROM schemes_fts f
                JOIN schemes s ON s.id = f.scheme_id
                WHERE schemes_fts MATCH :fts_match
                  AND s.is_active = 1
                ORDER BY score ASC
            """)
            result = await session.execute(sql_query, {"fts_match": fts_expr})
            fts_rows = result.fetchall()
            matched_scheme_ids = [row[0] for row in fts_rows]

        except Exception:
            # If FTS5 encounter any unexpected error, fallback to empty list
            matched_scheme_ids = []

        # 3. Retrieve any additional matching scheme IDs via deterministic substring search
        # to ensure zero false-negatives when FTS5 prefix matching only returns partial results
        # (e.g. Indic inflected forms or compound words where token is an infix/suffix).
        fallback_ids: List[str] = []
        try:
            search_term = clean_q.strip()
            escaped_term = search_term.encode("unicode-escape").decode("ascii")
            sub_stmt = select(Scheme.id).where(
                Scheme.is_active == True,
                or_(
                    Scheme.id.ilike(f"%{search_term}%"),
                    Scheme.slug.ilike(f"%{search_term}%"),
                    Scheme.ministry.ilike(f"%{search_term}%"),
                    cast(Scheme.names, String).contains(search_term),
                    cast(Scheme.names, String).contains(escaped_term),
                    cast(Scheme.descriptions, String).contains(search_term),
                    cast(Scheme.descriptions, String).contains(escaped_term),
                    cast(Scheme.benefits, String).contains(search_term),
                    cast(Scheme.benefits, String).contains(escaped_term),
                ),
            )
            sub_res = await session.execute(sub_stmt)
            fallback_ids = [row[0] for row in sub_res.fetchall()]
        except Exception:
            fallback_ids = []

        # Merge results: BM25 ranked FTS5 matches come first, followed by any additional substring matches
        all_matched_ids = list(dict.fromkeys(matched_scheme_ids + fallback_ids))

        if not all_matched_ids:
            return [], 0

        # 4. Filter matched IDs by category, state, scheme_type in Python/SQL
        conditions = [Scheme.id.in_(all_matched_ids), Scheme.is_active == True]
        if category:
            conditions.append(func.lower(Scheme.category) == category.strip().lower())
        if scheme_type:
            conditions.append(Scheme.scheme_type == scheme_type.strip().upper())
        if state:
            target_state = state.strip()
            conditions.append(
                or_(
                    cast(Scheme.state_applicability, String).contains('"ALL"'),
                    cast(Scheme.state_applicability, String).ilike(f'%"{target_state}"%'),
                )
            )

        # Fetch total count of filtered matching schemes
        count_stmt = select(func.count(Scheme.id)).where(*conditions)
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        if total == 0:
            return [], 0

        # Fetch full scheme entities
        fetch_stmt = (
            select(Scheme)
            .where(*conditions)
            .options(
                selectinload(Scheme.rules),
                selectinload(Scheme.documents),
            )
        )
        fetch_res = await session.execute(fetch_stmt)
        schemes_by_id = {s.id: s for s in fetch_res.scalars().all()}

        # Preserve BM25 ranking order
        ordered_schemes: List[Scheme] = []
        for sid in all_matched_ids:
            if sid in schemes_by_id:
                ordered_schemes.append(schemes_by_id[sid])

        # Apply pagination
        offset = (page - 1) * page_size
        paginated_schemes = ordered_schemes[offset : offset + page_size]

        return paginated_schemes, total

    @classmethod
    async def _search_standard_sql(
        cls,
        session: AsyncSession,
        category: Optional[str] = None,
        state: Optional[str] = None,
        scheme_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Scheme], int]:
        """Standard SQL filtered pagination when no search query is present."""
        conditions = [Scheme.is_active == True]
        if category:
            conditions.append(func.lower(Scheme.category) == category.strip().lower())
        if scheme_type:
            conditions.append(Scheme.scheme_type == scheme_type.strip().upper())
        if state:
            target_state = state.strip()
            conditions.append(
                or_(
                    cast(Scheme.state_applicability, String).contains('"ALL"'),
                    cast(Scheme.state_applicability, String).ilike(f'%"{target_state}"%'),
                )
            )

        count_stmt = select(func.count(Scheme.id)).where(*conditions)
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(Scheme)
            .where(*conditions)
            .options(
                selectinload(Scheme.rules),
                selectinload(Scheme.documents),
            )
            .order_by(Scheme.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(query)
        schemes = list(result.scalars().all())
        return schemes, total

    @classmethod
    async def _search_substring_fallback(
        cls,
        session: AsyncSession,
        raw_q: str,
        category: Optional[str] = None,
        state: Optional[str] = None,
        scheme_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Scheme], int]:
        """
        Deterministic SQL substring fallback to guarantee zero false-negatives
        for complex Indic scripts or un-tokenized substrings.
        """
        search_term = raw_q.strip()
        escaped_term = search_term.encode("unicode-escape").decode("ascii")

        conditions = [
            Scheme.is_active == True,
            or_(
                Scheme.id.ilike(f"%{search_term}%"),
                Scheme.slug.ilike(f"%{search_term}%"),
                Scheme.ministry.ilike(f"%{search_term}%"),
                cast(Scheme.names, String).contains(search_term),
                cast(Scheme.names, String).contains(escaped_term),
                cast(Scheme.descriptions, String).contains(search_term),
                cast(Scheme.descriptions, String).contains(escaped_term),
                cast(Scheme.benefits, String).contains(search_term),
                cast(Scheme.benefits, String).contains(escaped_term),
            )
        ]
        if category:
            conditions.append(func.lower(Scheme.category) == category.strip().lower())
        if scheme_type:
            conditions.append(Scheme.scheme_type == scheme_type.strip().upper())
        if state:
            target_state = state.strip()
            conditions.append(
                or_(
                    cast(Scheme.state_applicability, String).contains('"ALL"'),
                    cast(Scheme.state_applicability, String).ilike(f'%"{target_state}"%'),
                )
            )

        count_stmt = select(func.count(Scheme.id)).where(*conditions)
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(Scheme)
            .where(*conditions)
            .options(
                selectinload(Scheme.rules),
                selectinload(Scheme.documents),
            )
            .order_by(Scheme.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(query)
        schemes = list(result.scalars().all())
        return schemes, total
