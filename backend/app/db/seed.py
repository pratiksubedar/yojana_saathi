import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import select
from app.db.session import async_session_factory
from app.db.models import Scheme, Rule, Document
from app.db.init_db import init_db, sync_fts_index, sync_chunks_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "schemes_seed.json"


def load_seed_data(file_path: Path = DATA_PATH) -> List[Dict[str, Any]]:
    """Loads and validates the JSON seed file from disk."""
    if not file_path.exists():
        raise FileNotFoundError(f"Scheme seed file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError("Root element in schemes_seed.json must be a JSON array.")
    return data


async def seed_schemes(data: List[Dict[str, Any]] = None) -> int:
    """
    Seeds verified welfare scheme records and their associated rules and documents
    into the database idempotently.
    """
    if data is None:
        data = load_seed_data()

    logger.info(f"Seeding {len(data)} verified scheme record(s) into database...")
    seeded_count = 0

    async with async_session_factory() as session:
        for item in data:
            scheme_id = item["id"]

            # Check if scheme already exists
            stmt = select(Scheme).where(Scheme.id == scheme_id)
            result = await session.execute(stmt)
            existing_scheme = result.scalar_one_or_none()

            if existing_scheme:
                logger.info(f"Updating existing scheme: {scheme_id}")
                scheme = existing_scheme
                scheme.slug = item["slug"]
                scheme.category = item["category"]
                scheme.ministry = item["ministry"]
                scheme.scheme_type = item.get("scheme_type", "CENTRAL_SECTOR")
                scheme.state_applicability = item.get("state_applicability", ["ALL"])
                scheme.financial_amount_inr = item.get("financial_amount_inr")
                scheme.names = item["names"]
                scheme.descriptions = item["descriptions"]
                scheme.benefits = item["benefits"]
                scheme.official_url = item["official_url"]
                scheme.portal_name = item["portal_name"]
                scheme.last_verified_date = item["last_verified_date"]
                scheme.last_reviewed_date = item.get("last_reviewed_date", item["last_verified_date"])
                scheme.source_citation = item["source_citation"]
                scheme.application_procedure = item.get("application_procedure", [])
                scheme.is_active = True

                # Clear previous rules and documents to ensure fresh idempotent seed
                scheme.rules.clear()
                scheme.documents.clear()
            else:
                logger.info(f"Creating new scheme: {scheme_id}")
                scheme = Scheme(
                    id=scheme_id,
                    slug=item["slug"],
                    category=item["category"],
                    ministry=item["ministry"],
                    scheme_type=item.get("scheme_type", "CENTRAL_SECTOR"),
                    state_applicability=item.get("state_applicability", ["ALL"]),
                    financial_amount_inr=item.get("financial_amount_inr"),
                    names=item["names"],
                    descriptions=item["descriptions"],
                    benefits=item["benefits"],
                    official_url=item["official_url"],
                    portal_name=item["portal_name"],
                    last_verified_date=item["last_verified_date"],
                    last_reviewed_date=item.get("last_reviewed_date", item["last_verified_date"]),
                    source_citation=item["source_citation"],
                    application_procedure=item.get("application_procedure", []),
                    is_active=True,
                )
                session.add(scheme)

            # Add or update Rule record
            rule_data = item.get("rules", {})
            if rule_data:
                conditions_dict = dict(rule_data.get("conditions", {}))
                conditions_dict["rule_completeness"] = rule_data.get("rule_completeness", "PARTIAL")
                conditions_dict["unresolved_criteria"] = rule_data.get("unresolved_criteria", [])

                if existing_scheme and existing_scheme.rules:
                    existing_scheme.rules[0].version = rule_data.get("version", "2026.1")
                    existing_scheme.rules[0].conditions = conditions_dict
                else:
                    rule = Rule(
                        version=rule_data.get("version", "2026.1"),
                        conditions=conditions_dict,
                        is_active=True,
                    )
                    scheme.rules.append(rule)

            # Add or refresh Document records
            if existing_scheme:
                scheme.documents.clear()

            for doc_item in item.get("documents", []):
                doc = Document(
                    id=doc_item["id"],
                    names=doc_item["names"],
                    descriptions=doc_item["descriptions"],
                    is_mandatory=doc_item.get("is_mandatory", True),
                    csc_assisted=doc_item.get("csc_assisted", True),
                    issuer=doc_item.get("issuer", "Government Authority"),
                    source_url=doc_item.get("source_url"),
                )
                scheme.documents.append(doc)

            seeded_count += 1

        await session.commit()

        # Synchronize FTS5 search index and RAG semantic chunks
        await sync_fts_index(session)
        await sync_chunks_index(session)
        await session.commit()

    logger.info(f"Successfully seeded {seeded_count} scheme(s) and their associated rules & documents.")
    return seeded_count


async def main():
    await init_db()
    count = await seed_schemes()
    print(f"Database setup and seeding completed. Total schemes seeded: {count}")


if __name__ == "__main__":
    asyncio.run(main())

