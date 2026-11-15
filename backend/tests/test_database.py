import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import async_session_factory, check_db_health
from app.db.models import Scheme, Rule, Document, CitizenSession
from app.db.seed import seed_schemes


@pytest.mark.asyncio
async def test_db_health_check():
    """Verify that check_db_health accurately reports connection, initialization, and scheme count."""
    health = await check_db_health()
    assert health["status"] == "CONNECTED"
    assert health["initialized"] is True
    assert health["schemes_indexed"] >= 4


@pytest.mark.asyncio
async def test_seeded_schemes_content():
    """Verify that seeded anchor schemes are present and have accurate multilingual data."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Scheme).options(
                selectinload(Scheme.rules),
                selectinload(Scheme.documents),
            )
        )
        schemes = result.scalars().all()
        scheme_ids = [s.id for s in schemes]

        # Anchor schemes verified from official ministries
        assert "pm-kisan" in scheme_ids
        assert "pm-jay" in scheme_ids
        assert "pm-svanidhi" in scheme_ids
        assert "pmay-g" in scheme_ids
        assert "pm-kmy" in scheme_ids
        assert "pmmvy" in scheme_ids
        assert "pm-kusum" in scheme_ids

        for scheme in schemes:
            # Multilingual name check (all 4 languages must be present)
            for lang in ["en", "hi", "kn", "te"]:
                assert lang in scheme.names, f"Missing {lang} name in {scheme.id}"
                assert len(scheme.names[lang].strip()) > 0
                assert lang in scheme.descriptions, f"Missing {lang} description in {scheme.id}"
                assert len(scheme.descriptions[lang].strip()) > 0
                assert lang in scheme.benefits, f"Missing {lang} benefits in {scheme.id}"
                assert len(scheme.benefits[lang].strip()) > 0

            # Official metadata check
            assert scheme.official_url.startswith("https://")
            assert scheme.portal_name is not None
            assert scheme.last_verified_date is not None
            assert scheme.source_citation is not None
            assert "issuing_authority" in scheme.source_citation
            assert scheme.ministry is not None
            assert scheme.is_active is True

            # Associated rules check
            assert len(scheme.rules) > 0
            for rule in scheme.rules:
                assert rule.conditions is not None
                assert "all_of" in rule.conditions
                for cond in rule.conditions["all_of"]:
                    assert "field" in cond
                    assert "operator" in cond
                    assert "citation" in cond
                    assert "clause" in cond["citation"]

            # Associated documents check
            assert len(scheme.documents) > 0
            for doc in scheme.documents:
                for lang in ["en", "hi", "kn", "te"]:
                    assert lang in doc.names, f"Missing {lang} document name in {doc.id}"
                    assert len(doc.names[lang].strip()) > 0
                assert doc.issuer is not None


@pytest.mark.asyncio
async def test_scheme_crud_and_cascade_delete():
    """Test creating, reading, updating, and deleting a scheme with cascaded rules and documents."""
    async with async_session_factory() as session:
        # Create
        test_scheme = Scheme(
            id="test-welfare-scheme",
            slug="test-welfare-scheme",
            category="financial_inclusion",
            ministry="Ministry of Testing",
            scheme_type="CENTRAL_SECTOR",
            state_applicability=["ALL"],
            names={
                "en": "Test Welfare Scheme",
                "hi": "परीक्षण कल्याण योजना",
                "kn": "ಪರೀಕ್ಷಾ ಕಲ್ಯಾಣ ಯೋಜನೆ",
                "te": "పరీక్ష సంక్షేమ పథకం"
            },
            descriptions={
                "en": "A test welfare scheme for automated testing.",
                "hi": "स्वचालित परीक्षण के लिए एक परीक्षण कल्याण योजना।",
                "kn": "ಸ್ವಯಂಚಾಲಿತ ಪರೀಕ್ಷೆಗಾಗಿ ಪರೀಕ್ಷಾ ಕಲ್ಯಾಣ ಯೋಜನೆ.",
                "te": "ఆటోమేటెడ్ టెస్టింగ్ కోసం పరీక్ష సంక్షేమ పథకం."
            },
            benefits={
                "en": "Financial benefit of Rs 1,000",
                "hi": "₹1,000 का वित्तीय लाभ",
                "kn": "₹1,000 ಆರ್ಥಿಕ ನೆರವು",
                "te": "₹1,000 ఆర్థిక ప్రయోజనం"
            },
            financial_amount_inr=1000.0,
            official_url="https://example.gov.in",
            portal_name="Example Portal",
            last_verified_date="2026-03-31",
            source_citation={"ministry": "Ministry of Testing", "clause": "Clause 1"},
            is_active=True,
        )

        test_rule = Rule(
            scheme_id="test-welfare-scheme",
            version="2026.1",
            conditions={
                "all_of": [
                    {"field": "age", "operator": "gte", "value": 18}
                ],
                "clause_citation": "Clause 3.1"
            },
            is_active=True
        )

        test_doc = Document(
            id="doc-test-scheme-aadhaar",
            scheme_id="test-welfare-scheme",
            names={
                "en": "Aadhaar Card",
                "hi": "आधार कार्ड",
                "kn": "ಆಧಾರ್ ಕಾರ್ಡ್",
                "te": "ఆధార్ కార్డు"
            },
            descriptions={
                "en": "Valid Aadhaar Card for proof of identity.",
                "hi": "पहचान के प्रमाण के लिए वैध आधार कार्ड।",
                "kn": "ಗುರುತಿನ ಪುರಾವೆಗಾಗಿ ಮಾನ್ಯವಾದ ಆಧಾರ್ ಕಾರ್ಡ್.",
                "te": "గుర్తింపు రుజువు కోసం చెల్లుబాటు అయ్యే ఆధార్ కార్డు."
            },
            is_mandatory=True,
            csc_assisted=False,
            issuer="UIDAI"
        )

        session.add(test_scheme)
        session.add(test_rule)
        session.add(test_doc)
        await session.commit()

    # Read
    async with async_session_factory() as session:
        stmt = (
            select(Scheme)
            .where(Scheme.id == "test-welfare-scheme")
            .options(selectinload(Scheme.rules), selectinload(Scheme.documents))
        )
        res = await session.execute(stmt)
        saved = res.scalar_one_or_none()
        assert saved is not None
        assert saved.names["en"] == "Test Welfare Scheme"
        assert len(saved.rules) == 1
        assert saved.rules[0].conditions["clause_citation"] == "Clause 3.1"
        assert len(saved.documents) == 1
        assert saved.documents[0].issuer == "UIDAI"

        # Update
        saved.category = "social_welfare"
        await session.commit()

    # Verify update
    async with async_session_factory() as session:
        updated = await session.get(Scheme, "test-welfare-scheme")
        assert updated.category == "social_welfare"

        # Delete & verify cascade
        await session.delete(updated)
        await session.commit()

    # Verify cascade deletion of children
    async with async_session_factory() as session:
        deleted_scheme = await session.get(Scheme, "test-welfare-scheme")
        deleted_rules_res = await session.execute(select(Rule).where(Rule.scheme_id == "test-welfare-scheme"))
        deleted_rules = deleted_rules_res.scalars().all()
        deleted_docs_res = await session.execute(select(Document).where(Document.scheme_id == "test-welfare-scheme"))
        deleted_docs = deleted_docs_res.scalars().all()

        assert deleted_scheme is None
        assert len(deleted_rules) == 0
        assert len(deleted_docs) == 0


@pytest.mark.asyncio
async def test_citizen_session_privacy():
    """Verify CitizenSession records adhere to privacy: only language and ephemeral metadata."""
    async with async_session_factory() as session:
        sess = CitizenSession(
            id="sess-xyz-123",
            language="kn"
        )
        session.add(sess)
        await session.commit()

    async with async_session_factory() as session:
        retrieved = await session.get(CitizenSession, "sess-xyz-123")
        assert retrieved is not None
        assert retrieved.language == "kn"
        assert retrieved.created_at is not None
        assert retrieved.last_active_at is not None

        # Clean up
        await session.delete(retrieved)
        await session.commit()


@pytest.mark.asyncio
async def test_idempotent_seeding():
    """Ensure running seed_schemes multiple times updates records without duplicating or throwing errors."""
    count1 = await seed_schemes()
    assert count1 >= 4

    count2 = await seed_schemes()
    assert count2 == count1
