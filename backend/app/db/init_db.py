import asyncio
import json
import logging
from pathlib import Path
from sqlalchemy import text
from app.db.base import Base
from app.db.session import async_engine
from app.db import models  # Ensures all models are registered on Base.metadata
from app.services.search_synonyms import SCHEME_SEARCH_METADATA
from app.services.chunking_service import SchemeChunkingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "schemes_seed.json"


async def sync_fts_index(conn_or_session) -> int:
    """
    Synchronizes the schemes_fts virtual table with current scheme records
    and enriches each entry with curated multilingual keywords and synonyms.
    Works with both AsyncConnection and AsyncSession.
    """
    # 1. Clear current FTS records
    await conn_or_session.execute(text("DELETE FROM schemes_fts"))

    # 2. Fetch all active schemes
    result = await conn_or_session.execute(
        text("SELECT id, names, descriptions, benefits FROM schemes WHERE is_active = 1")
    )
    rows = result.fetchall()
    count = 0

    insert_sql = text("""
        INSERT INTO schemes_fts (
            scheme_id, code,
            names_en, names_hi, names_kn, names_te,
            descriptions_en, descriptions_hi, descriptions_kn, descriptions_te,
            benefits_en, benefits_hi, benefits_kn, benefits_te,
            keywords, synonyms
        ) VALUES (
            :scheme_id, :code,
            :names_en, :names_hi, :names_kn, :names_te,
            :desc_en, :desc_hi, :desc_kn, :desc_te,
            :ben_en, :ben_hi, :ben_kn, :ben_te,
            :keywords, :synonyms
        )
    """)

    for row in rows:
        scheme_id = row[0]
        names = row[1] if isinstance(row[1], dict) else (json.loads(row[1]) if row[1] else {})
        descriptions = row[2] if isinstance(row[2], dict) else (json.loads(row[2]) if row[2] else {})
        benefits = row[3] if isinstance(row[3], dict) else (json.loads(row[3]) if row[3] else {})

        meta = SCHEME_SEARCH_METADATA.get(scheme_id, {})
        keywords_str = " ".join(meta.get("keywords", []))
        synonyms_str = " ".join(meta.get("synonyms", []))

        await conn_or_session.execute(
            insert_sql,
            {
                "scheme_id": scheme_id,
                "code": scheme_id,
                "names_en": names.get("en", ""),
                "names_hi": names.get("hi", ""),
                "names_kn": names.get("kn", ""),
                "names_te": names.get("te", ""),
                "desc_en": descriptions.get("en", ""),
                "desc_hi": descriptions.get("hi", ""),
                "desc_kn": descriptions.get("kn", ""),
                "desc_te": descriptions.get("te", ""),
                "ben_en": benefits.get("en", ""),
                "ben_hi": benefits.get("hi", ""),
                "ben_kn": benefits.get("kn", ""),
                "ben_te": benefits.get("te", ""),
                "keywords": keywords_str,
                "synonyms": synonyms_str,
            },
        )
        count += 1

    logger.info(f"Synchronized {count} schemes into schemes_fts virtual table.")
    return count


async def sync_chunks_index(conn_or_session) -> int:
    """
    Synchronizes the scheme_chunks table and scheme_chunks_fts virtual table
    with current scheme records by running the semantic chunker.
    Works with both AsyncConnection and AsyncSession.
    """
    # 1. Clear current chunks
    await conn_or_session.execute(text("DELETE FROM scheme_chunks"))
    await conn_or_session.execute(text("DELETE FROM scheme_chunks_fts"))

    # 2. Load seed data
    if not SEED_FILE_PATH.exists():
        logger.warning(f"Seed file not found at {SEED_FILE_PATH}, skipping chunk synchronization.")
        return 0

    with open(SEED_FILE_PATH, "r", encoding="utf-8") as fp:
        schemes = json.load(fp)

    chunks = SchemeChunkingService.chunk_all_schemes(schemes)

    insert_chunk_sql = text("""
        INSERT INTO scheme_chunks (
            chunk_id, scheme_id, category, language, content,
            source_url, issuing_authority, document_title, relevant_section,
            page_ref, verification_status, last_reviewed_date, content_type,
            is_verbatim, created_at, updated_at
        ) VALUES (
            :chunk_id, :scheme_id, :category, :language, :content,
            :source_url, :issuing_authority, :document_title, :relevant_section,
            :page_ref, :verification_status, :last_reviewed_date, :content_type,
            :is_verbatim, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
    """)

    for chunk in chunks:
        prov = chunk.provenance
        params = {
            "chunk_id": chunk.chunk_id,
            "scheme_id": chunk.scheme_id,
            "category": chunk.category.value,
            "language": chunk.language,
            "content": chunk.content,
            "source_url": prov.source_url,
            "issuing_authority": prov.issuing_authority,
            "document_title": prov.document_title,
            "relevant_section": prov.relevant_section,
            "page_ref": prov.page_ref,
            "verification_status": prov.verification_status.value,
            "last_reviewed_date": prov.last_reviewed_date,
            "content_type": chunk.content_type.value,
            "is_verbatim": 1 if chunk.is_verbatim else 0,
        }
        await conn_or_session.execute(insert_chunk_sql, params)

    logger.info(f"Synchronized {len(chunks)} semantic chunks into scheme_chunks and scheme_chunks_fts.")
    return len(chunks)


async def init_db() -> None:
    """
    Creates all SQLite database tables asynchronously based on SQLAlchemy metadata,
    runs non-destructive schema migrations, creates the schemes_fts FTS5 table
    along with synchronization triggers, and backfills the FTS5 index.
    Idempotent: uses CREATE TABLE IF NOT EXISTS under the hood.
    """
    logger.info("Initializing SQLite database tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Non-destructive column migrations
        # 1. session_checklist_items.expires_at
        table_check = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='session_checklist_items'")
        )
        if table_check.scalar():
            col_check = await conn.execute(text("PRAGMA table_info(session_checklist_items)"))
            existing_cols = {row[1] for row in col_check.fetchall()}
            if "expires_at" not in existing_cols:
                logger.info("Migrating session_checklist_items: adding expires_at column...")
                await conn.execute(
                    text("ALTER TABLE session_checklist_items ADD COLUMN expires_at DATETIME")
                )
                logger.info("Migration complete: expires_at column added successfully.")

        # 2. schemes.application_procedure and schemes.last_reviewed_date
        schemes_table_check = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='schemes'")
        )
        if schemes_table_check.scalar():
            col_check = await conn.execute(text("PRAGMA table_info(schemes)"))
            existing_cols = {row[1] for row in col_check.fetchall()}
            if "application_procedure" not in existing_cols:
                logger.info("Migrating schemes: adding application_procedure column...")
                await conn.execute(
                    text("ALTER TABLE schemes ADD COLUMN application_procedure JSON DEFAULT '[]'")
                )
                logger.info("Migration complete: application_procedure column added.")
            if "last_reviewed_date" not in existing_cols:
                logger.info("Migrating schemes: adding last_reviewed_date column...")
                await conn.execute(
                    text("ALTER TABLE schemes ADD COLUMN last_reviewed_date VARCHAR(32) DEFAULT '2026-11-10'")
                )
                logger.info("Migration complete: last_reviewed_date column added.")

        # 3. documents.source_url
        docs_table_check = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        )
        if docs_table_check.scalar():
            col_check = await conn.execute(text("PRAGMA table_info(documents)"))
            existing_cols = {row[1] for row in col_check.fetchall()}
            if "source_url" not in existing_cols:
                logger.info("Migrating documents: adding source_url column...")
                await conn.execute(
                    text("ALTER TABLE documents ADD COLUMN source_url VARCHAR(512)")
                )
                logger.info("Migration complete: source_url column added.")

        # 4. FTS5 Virtual Table & Triggers for Multilingual Full-Text Search
        logger.info("Setting up SQLite FTS5 schemes_fts virtual table and triggers...")
        await conn.execute(
            text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS schemes_fts USING fts5(
                    scheme_id UNINDEXED,
                    code,
                    names_en, names_hi, names_kn, names_te,
                    descriptions_en, descriptions_hi, descriptions_kn, descriptions_te,
                    benefits_en, benefits_hi, benefits_kn, benefits_te,
                    keywords,
                    synonyms,
                    tokenize = 'unicode61'
                )
            """)
        )

        # Triggers to keep FTS index synchronized on direct SQL modifications
        await conn.execute(text("DROP TRIGGER IF EXISTS schemes_ai"))
        await conn.execute(text("DROP TRIGGER IF EXISTS schemes_ad"))
        await conn.execute(text("DROP TRIGGER IF EXISTS schemes_au"))

        await conn.execute(
            text("""
                CREATE TRIGGER schemes_ai AFTER INSERT ON schemes BEGIN
                    INSERT INTO schemes_fts(
                        scheme_id, code,
                        names_en, names_hi, names_kn, names_te,
                        descriptions_en, descriptions_hi, descriptions_kn, descriptions_te,
                        benefits_en, benefits_hi, benefits_kn, benefits_te,
                        keywords, synonyms
                    ) VALUES (
                        NEW.id, NEW.id,
                        CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.en'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.hi'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.kn'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.te'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.en'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.hi'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.kn'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.te'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.en'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.hi'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.kn'), '') ELSE '' END,
                        CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.te'), '') ELSE '' END,
                        '', ''
                    );
                END
            """)
        )

        await conn.execute(
            text("""
                CREATE TRIGGER schemes_ad AFTER DELETE ON schemes BEGIN
                    DELETE FROM schemes_fts WHERE scheme_id = OLD.id;
                END
            """)
        )

        await conn.execute(
            text("""
                CREATE TRIGGER schemes_au AFTER UPDATE ON schemes BEGIN
                    UPDATE schemes_fts SET
                        scheme_id = NEW.id,
                        code = NEW.id,
                        names_en = CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.en'), '') ELSE '' END,
                        names_hi = CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.hi'), '') ELSE '' END,
                        names_kn = CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.kn'), '') ELSE '' END,
                        names_te = CASE WHEN json_valid(NEW.names) THEN COALESCE(json_extract(NEW.names, '$.te'), '') ELSE '' END,
                        descriptions_en = CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.en'), '') ELSE '' END,
                        descriptions_hi = CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.hi'), '') ELSE '' END,
                        descriptions_kn = CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.kn'), '') ELSE '' END,
                        descriptions_te = CASE WHEN json_valid(NEW.descriptions) THEN COALESCE(json_extract(NEW.descriptions, '$.te'), '') ELSE '' END,
                        benefits_en = CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.en'), '') ELSE '' END,
                        benefits_hi = CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.hi'), '') ELSE '' END,
                        benefits_kn = CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.kn'), '') ELSE '' END,
                        benefits_te = CASE WHEN json_valid(NEW.benefits) THEN COALESCE(json_extract(NEW.benefits, '$.te'), '') ELSE '' END
                    WHERE scheme_id = OLD.id;
                END
            """)
        )

        # 5. FTS5 Virtual Table & Triggers for RAG Scheme Semantic Chunks
        logger.info("Setting up SQLite FTS5 scheme_chunks_fts virtual table and triggers...")
        await conn.execute(
            text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS scheme_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    scheme_id,
                    category,
                    language,
                    content,
                    document_title,
                    issuing_authority,
                    relevant_section,
                    tokenize = 'unicode61'
                )
            """)
        )

        # Triggers to keep scheme_chunks_fts synchronized with scheme_chunks
        await conn.execute(text("DROP TRIGGER IF EXISTS scheme_chunks_ai"))
        await conn.execute(text("DROP TRIGGER IF EXISTS scheme_chunks_ad"))
        await conn.execute(text("DROP TRIGGER IF EXISTS scheme_chunks_au"))

        await conn.execute(
            text("""
                CREATE TRIGGER scheme_chunks_ai AFTER INSERT ON scheme_chunks BEGIN
                    INSERT INTO scheme_chunks_fts(
                        chunk_id, scheme_id, category, language, content,
                        document_title, issuing_authority, relevant_section
                    ) VALUES (
                        NEW.chunk_id, NEW.scheme_id, NEW.category, NEW.language, NEW.content,
                        NEW.document_title, NEW.issuing_authority, COALESCE(NEW.relevant_section, '')
                    );
                END
            """)
        )

        await conn.execute(
            text("""
                CREATE TRIGGER scheme_chunks_ad AFTER DELETE ON scheme_chunks BEGIN
                    DELETE FROM scheme_chunks_fts WHERE chunk_id = OLD.chunk_id;
                END
            """)
        )

        await conn.execute(
            text("""
                CREATE TRIGGER scheme_chunks_au AFTER UPDATE ON scheme_chunks BEGIN
                    UPDATE scheme_chunks_fts SET
                        scheme_id = NEW.scheme_id,
                        category = NEW.category,
                        language = NEW.language,
                        content = NEW.content,
                        document_title = NEW.document_title,
                        issuing_authority = NEW.issuing_authority,
                        relevant_section = COALESCE(NEW.relevant_section, '')
                    WHERE chunk_id = OLD.chunk_id;
                END
            """)
        )

        # Backfill / sync schemes_fts and scheme_chunks_fts
        await sync_fts_index(conn)
        await sync_chunks_index(conn)

    logger.info("Database tables, FTS5 search index, and RAG chunk store initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())


