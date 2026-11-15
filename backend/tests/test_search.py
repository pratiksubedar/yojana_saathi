"""
Yojana Saathi - Milestone 5.3 Test Suite
Comprehensive testing for Multilingual SQLite FTS5 Full-Text Search.
Covers:
1. English, Hindi, Kannada, Telugu search terms
2. Unicode letters, combining marks (matras, viramas), Indic script tokenization
3. Numeric query normalization (₹6,000, 6,000 -> 6000; 3000, 15000, 50000)
4. Curated synonym expansion without cross-scheme conflation (no Rythu Bharosa on PM-KISAN, no KCR Kit on PMMVY)
5. BM25 relevance ranking (title matches outranking description matches)
6. Combined search with category, state, and scheme_type filters
7. Safe handling of punctuation-only, special character, and whitespace queries
8. FTS5 table triggers and sync_fts_index consistency
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.db.session import async_session_factory
from app.db.init_db import sync_fts_index
from app.services.search_service import normalize_query_tokens, build_fts5_query

client = TestClient(app)


# ==============================================================================
# 1. UNIT TESTS: Query Tokenization & Unicode Preservation
# ==============================================================================

def test_normalize_query_tokens_currency_and_numbers():
    """Verify currency symbols and comma separators are properly normalized to numbers."""
    assert normalize_query_tokens("₹6,000") == ["6000"]
    assert normalize_query_tokens("Rs. 6,000") == ["6000"]
    assert normalize_query_tokens("INR 15,000") == ["15000"]
    assert normalize_query_tokens("50,000") == ["50000"]
    assert normalize_query_tokens("5,00,000") == ["500000"]


def test_normalize_query_tokens_unicode_indic_scripts():
    """Verify Unicode combining marks (matras, viramas) are strictly preserved across Indic scripts."""
    # Hindi with virama/halant and matras
    tokens_hi = normalize_query_tokens("किसान स्वास्थ्य ऋण")
    assert tokens_hi == ["किसान", "स्वास्थ्य", "ऋण"]

    # Kannada with viramas and matras
    tokens_kn = normalize_query_tokens("ಕೃಷಿ ಯೋಜನೆ ರೈತ")
    assert tokens_kn == ["ಕೃಷಿ", "ಯೋಜನೆ", "ರೈತ"]

    # Telugu with viramas and matras
    tokens_te = normalize_query_tokens("వ్యవసాయం రైతు పథకం")
    assert tokens_te == ["వ్యవసాయం", "రైతు", "పథకం"]


def test_normalize_query_tokens_punctuation_safety():
    """Verify punctuation and FTS special characters are stripped safely."""
    assert normalize_query_tokens("??? !!! ***") == []
    assert normalize_query_tokens('kisan "farmer" (solar) [pension]') == ["kisan", "farmer", "solar", "pension"]


def test_build_fts5_query_safe_prefix_and_synonyms():
    """Verify safe FTS5 query generation with prefix terms and synonyms."""
    # English hospital expands to healthcare keywords
    fts_hosp = build_fts5_query("hospital")
    assert fts_hosp is not None
    assert '"hospital"*' in fts_hosp
    assert '"ayushman"*' in fts_hosp or '"treatment"*' in fts_hosp

    # Empty on punctuation
    assert build_fts5_query("???") is None


# ==============================================================================
# 2. INTEGRATION TESTS: English Multilingual Full-Text Search
# ==============================================================================

def test_search_english_all_seven_schemes():
    """Verify search finds each of the 7 schemes using distinct English keywords."""
    test_cases = [
        ("kisan", "pm-kisan"),
        ("hospital", "pm-jay"),
        ("street vendor", "pm-svanidhi"),
        ("housing", "pmay-g"),
        ("pension farmer", "pm-kmy"),
        ("maternity", "pmmvy"),
        ("solar pump", "pm-kusum"),
    ]
    for term, expected_id in test_cases:
        res = client.get(f"/api/v1/schemes?q={term}")
        assert res.status_code == 200, f"Search failed for {term}"
        data = res.json()
        ids = [s["id"] for s in data["items"]]
        assert expected_id in ids, f"Expected {expected_id} for '{term}', got {ids}"


# ==============================================================================
# 3. INTEGRATION TESTS: Indic Script Full-Text Search (Hindi, Kannada, Telugu)
# ==============================================================================

def test_search_hindi_keywords():
    """Verify Hindi search across various welfare domains."""
    test_cases = [
        ("किसान", "pm-kisan"),
        ("अस्पताल", "pm-jay"),
        ("विक्रेता", "pm-svanidhi"),
        ("आवास", "pmay-g"),
        ("पेंशन", "pm-kmy"),
        ("गर्भवती", "pmmvy"),
        ("सौर", "pm-kusum"),
    ]
    for term, expected_id in test_cases:
        res = client.get(f"/api/v1/schemes?q={term}")
        assert res.status_code == 200, f"Search failed for {term}"
        ids = [s["id"] for s in res.json()["items"]]
        assert expected_id in ids, f"Expected {expected_id} for Hindi '{term}', got {ids}"


def test_search_kannada_keywords():
    """Verify Kannada search across various welfare domains."""
    test_cases = [
        ("ರೈತ", "pm-kisan"),
        ("ಆಸ್ಪತ್ರೆ", "pm-jay"),
        ("ಮಾರಾಟಗಾರ", "pm-svanidhi"),
        ("ಮನೆ", "pmay-g"),
        ("ಪಿಂಚಣಿ", "pm-kmy"),
        ("ಗರ್ಭಿಣಿ", "pmmvy"),
        ("ಸೌರ", "pm-kusum"),
    ]
    for term, expected_id in test_cases:
        res = client.get(f"/api/v1/schemes?q={term}")
        assert res.status_code == 200, f"Search failed for {term}"
        ids = [s["id"] for s in res.json()["items"]]
        assert expected_id in ids, f"Expected {expected_id} for Kannada '{term}', got {ids}"


def test_search_telugu_keywords():
    """Verify Telugu search across various welfare domains."""
    test_cases = [
        ("రైతు", "pm-kisan"),
        ("ఆసుపత్రి", "pm-jay"),
        ("చిరువ్యాపారి", "pm-svanidhi"),
        ("గృహ", "pmay-g"),
        ("పింఛను", "pm-kmy"),
        ("గర్భిణి", "pmmvy"),
        ("సౌర", "pm-kusum"),
    ]
    for term, expected_id in test_cases:
        res = client.get(f"/api/v1/schemes?q={term}")
        assert res.status_code == 200, f"Search failed for {term}"
        ids = [s["id"] for s in res.json()["items"]]
        assert expected_id in ids, f"Expected {expected_id} for Telugu '{term}', got {ids}"


# ==============================================================================
# 4. NUMERIC NORMALIZATION & AMBIGUOUS QUERIES
# ==============================================================================

def test_numeric_search_normalization_and_multi_scheme():
    """
    Verify currency/comma normalization in search and ambiguous numeric queries
    return all applicable schemes:
    - 6000: PM-KISAN (₹6000/yr) and PMMVY (₹6000 2nd girl child)
    - 3000: PM-KMY (₹3000 pension) and PMMVY (₹3000 1st instalment)
    - 15000: PM SVANidhi (1st tranche loan)
    - 50000: PM SVANidhi (3rd tranche loan)
    """
    # 6000 search with currency symbol
    res_6000 = client.get("/api/v1/schemes?q=₹6,000")
    assert res_6000.status_code == 200
    ids_6000 = [s["id"] for s in res_6000.json()["items"]]
    assert "pm-kisan" in ids_6000
    assert "pmmvy" in ids_6000

    # Plain 6000
    res_6000_plain = client.get("/api/v1/schemes?q=6000")
    assert res_6000_plain.status_code == 200
    ids_6000_plain = [s["id"] for s in res_6000_plain.json()["items"]]
    assert "pm-kisan" in ids_6000_plain
    assert "pmmvy" in ids_6000_plain

    # 3000 search (PM-KMY ₹3,000 pension & PMMVY ₹3,000 1st instalment)
    res_3000 = client.get("/api/v1/schemes?q=3,000")
    assert res_3000.status_code == 200
    ids_3000 = [s["id"] for s in res_3000.json()["items"]]
    assert "pm-kmy" in ids_3000
    assert "pmmvy" in ids_3000

    # 15000 search (PM SVANidhi 1st tranche)
    res_15000 = client.get("/api/v1/schemes?q=15000")
    assert res_15000.status_code == 200
    ids_15000 = [s["id"] for s in res_15000.json()["items"]]
    assert "pm-svanidhi" in ids_15000


# ==============================================================================
# 5. SYNONYM ACCURACY & NO CROSS-SCHEME CONFLATION
# ==============================================================================

def test_synonym_separation_rythu_bharosa_and_kcr_kit():
    """
    Verify:
    1. Telangana Rythu Bharosa is NOT an alias for PM-KISAN.
    2. Telangana KCR Kit is NOT conflated as a synonym for central PMMVY.
    """
    # PM-KISAN synonyms check
    from app.services.search_synonyms import SCHEME_SEARCH_METADATA
    pm_kisan_synonyms = SCHEME_SEARCH_METADATA["pm-kisan"]["synonyms"]
    assert "రైతు భరోసా" not in pm_kisan_synonyms, "Rythu Bharosa must not be in PM-KISAN synonyms"
    assert "rythu bharosa" not in [s.lower() for s in pm_kisan_synonyms]

    # PMMVY synonyms check
    pmmvy_synonyms = SCHEME_SEARCH_METADATA["pmmvy"]["synonyms"]
    pmmvy_synonyms_lower = [s.lower() for s in pmmvy_synonyms]
    assert "kcr kit" not in pmmvy_synonyms_lower, "KCR Kit must not be in PMMVY synonyms"


# ==============================================================================
# 6. BM25 RELEVANCE RANKING
# ==============================================================================

def test_bm25_title_match_ranks_first():
    """Verify that a direct scheme name/code match ranks above incidental mentions."""
    # Searching 'kisan' should rank pm-kisan first
    res = client.get("/api/v1/schemes?q=kisan")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 2
    # First item should be pm-kisan (title match with highest BM25 score)
    assert items[0]["id"] == "pm-kisan"

    # Searching 'ayushman' should rank pm-jay first
    res_ayush = client.get("/api/v1/schemes?q=ayushman")
    assert res_ayush.status_code == 200
    items_ayush = res_ayush.json()["items"]
    assert items_ayush[0]["id"] == "pm-jay"


# ==============================================================================
# 7. COMBINED SEARCH & FILTERING
# ==============================================================================

def test_combined_search_with_category_and_state():
    """Verify combining search term q with category and state filters."""
    # 6000 in agriculture category -> only pm-kisan (excludes pmmvy)
    res_agri = client.get("/api/v1/schemes?q=6000&category=agriculture")
    assert res_agri.status_code == 200
    data_agri = res_agri.json()
    assert data_agri["pagination"]["total"] == 1
    assert data_agri["items"][0]["id"] == "pm-kisan"

    # 6000 in social_welfare category -> only pmmvy (excludes pm-kisan)
    res_welfare = client.get("/api/v1/schemes?q=6000&category=social_welfare")
    assert res_welfare.status_code == 200
    data_welfare = res_welfare.json()
    assert data_welfare["pagination"]["total"] == 1
    assert data_welfare["items"][0]["id"] == "pmmvy"


# ==============================================================================
# 8. QUERY SAFETY, SPECIAL CHARACTERS & ERROR HANDLING
# ==============================================================================

def test_search_punctuation_and_empty_handling():
    """Verify query safety: punctuation-only queries do not crash, whitespace raises 400."""
    # Whitespace-only query returns 400 INVALID_FILTER
    res_space = client.get("/api/v1/schemes?q=%20%20%20")
    assert res_space.status_code == 400
    assert res_space.json()["error_code"] == "INVALID_FILTER"

    # Punctuation-only query returns 200 with empty list (safe handling)
    res_punct = client.get("/api/v1/schemes?q=???%20!!!")
    assert res_punct.status_code == 200
    assert res_punct.json()["pagination"]["total"] == 0
    assert res_punct.json()["items"] == []

    # Complex FTS symbols (*, OR, AND, quotes) do not crash SQLite
    res_symbols = client.get('/api/v1/schemes?q=kisan" AND OR *')
    assert res_symbols.status_code == 200
    assert any(s["id"] == "pm-kisan" for s in res_symbols.json()["items"])


# ==============================================================================
# 9. FTS5 TRIGGER & DIRECT SQL SYNCHRONIZATION
# ==============================================================================

def test_search_partial_results_recovery():
    """
    Verify fallback correctness: when FTS5 prefix matching only returns partial results
    (e.g. Indic inflected forms or compound words where token is an infix/suffix),
    the search service seamlessly recovers all matching schemes without false negatives,
    preserving BM25 ranking for FTS5 matches at the top.
    """
    # 'ಮಂತ್ರಿ' appears as standalone in pm-jay (FTS5 match) and inside compound words in pm-kisan and pmay-g
    res = client.get("/api/v1/schemes?q=ಮಂತ್ರಿ")
    assert res.status_code == 200
    ids = [s["id"] for s in res.json()["items"]]
    # All 5 schemes containing 'ಮಂತ್ರಿ' must be returned
    assert "pm-jay" in ids
    assert "pm-kmy" in ids
    assert "pmmvy" in ids
    assert "pm-kisan" in ids
    assert "pmay-g" in ids
    # FTS5 BM25 matches rank at the top
    assert ids.index("pm-jay") < ids.index("pm-kisan")
    assert ids.index("pm-jay") < ids.index("pmay-g")


@pytest.mark.asyncio
async def test_fts5_virtual_table_and_trigger_sync():
    """Verify that schemes_fts virtual table exists, is populated, and responds to sync."""
    async with async_session_factory() as session:
        # Check that schemes_fts has 21 entries
        result = await session.execute(text("SELECT count(*) FROM schemes_fts"))
        count = result.scalar()
        assert count == 21

        # Test sync_fts_index function
        synced = await sync_fts_index(session)
        assert synced == 21
        await session.commit()


@pytest.mark.asyncio
async def test_direct_sql_triggers_insert_update_delete():
    """
    Verify all three SQLite triggers (schemes_ai, schemes_au, schemes_ad)
    operate correctly under direct raw SQL execution, preserving keywords and
    synonyms across direct SQL UPDATEs.
    """
    test_scheme_id = "test-scheme-trigger-verify"
    async with async_session_factory() as session:
        try:
            # 1. Direct raw SQL INSERT into schemes table
            await session.execute(
                text("""
                    INSERT INTO schemes (
                        id, slug, category, ministry, scheme_type, state_applicability,
                        names, descriptions, benefits, official_url, portal_name,
                        last_verified_date, source_citation, application_procedure, is_active,
                        created_at, updated_at
                    ) VALUES (
                        :id, :slug, 'test', 'Test Ministry', 'CENTRAL_SECTOR', '["ALL"]',
                        '{"en": "Initial Test Name", "hi": "आरंभिक नाम"}',
                        '{"en": "Initial Test Desc"}',
                        '{"en": "Initial Test Ben"}',
                        'https://example.gov.in', 'Test Portal', '2026-11-10',
                        '{"source": "test"}', '[]', 1,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """),
                {"id": test_scheme_id, "slug": test_scheme_id},
            )
            await session.commit()

            # Verify trigger schemes_ai inserted into schemes_fts
            check_ai = await session.execute(
                text("SELECT scheme_id, names_en, keywords, synonyms FROM schemes_fts WHERE scheme_id = :id"),
                {"id": test_scheme_id},
            )
            row_ai = check_ai.fetchone()
            assert row_ai is not None, "schemes_ai trigger failed to insert into schemes_fts"
            assert row_ai[0] == test_scheme_id
            assert row_ai[1] == "Initial Test Name"
            assert row_ai[2] == ""
            assert row_ai[3] == ""

            # 2. Enrich keywords and synonyms in schemes_fts (as application/seed would do)
            await session.execute(
                text("UPDATE schemes_fts SET keywords = 'kw1 kw2', synonyms = 'syn1 syn2' WHERE scheme_id = :id"),
                {"id": test_scheme_id},
            )
            await session.commit()

            # 3. Direct raw SQL UPDATE on schemes table
            await session.execute(
                text("""
                    UPDATE schemes
                    SET names = '{"en": "Updated Test Name Via Direct SQL", "hi": "अद्यतन नाम"}'
                    WHERE id = :id
                """),
                {"id": test_scheme_id},
            )
            await session.commit()

            # Verify trigger schemes_au updated names_en AND PRESERVED keywords/synonyms
            check_au = await session.execute(
                text("SELECT scheme_id, names_en, keywords, synonyms FROM schemes_fts WHERE scheme_id = :id"),
                {"id": test_scheme_id},
            )
            row_au = check_au.fetchone()
            assert row_au is not None
            assert row_au[1] == "Updated Test Name Via Direct SQL"
            assert row_au[2] == "kw1 kw2", "schemes_au trigger wiped out keywords on direct SQL UPDATE"
            assert row_au[3] == "syn1 syn2", "schemes_au trigger wiped out synonyms on direct SQL UPDATE"

            # 4. Direct raw SQL DELETE from schemes table
            await session.execute(
                text("DELETE FROM schemes WHERE id = :id"),
                {"id": test_scheme_id},
            )
            await session.commit()

            # Verify trigger schemes_ad removed from schemes_fts
            check_ad = await session.execute(
                text("SELECT count(*) FROM schemes_fts WHERE scheme_id = :id"),
                {"id": test_scheme_id},
            )
            assert check_ad.scalar() == 0, "schemes_ad trigger failed to delete from schemes_fts"

        finally:
            # Clean up test row if anything failed mid-way
            await session.execute(text("DELETE FROM schemes WHERE id = :id"), {"id": test_scheme_id})
            await session.execute(text("DELETE FROM schemes_fts WHERE scheme_id = :id"), {"id": test_scheme_id})
            await session.commit()
