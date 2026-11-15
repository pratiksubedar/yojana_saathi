from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Scheme, Document, EphemeralChecklistItem
from app.schemas.document import (
    ChecklistItemSchema,
    SchemeChecklistResponse,
)
from app.core.exceptions import SchemeNotFoundException, AppError

# Sliding window expiration policy: 2 hours from creation or last update
CHECKLIST_SESSION_TTL_HOURS = 2

DOCUMENT_DISCLAIMERS: Dict[str, str] = {
    "en": (
        "Physical verification of original documents by designated authorities or Common Service "
        "Centres (CSCs) is mandatory. Digital checklist markers are for citizen guidance only and "
        "do not constitute statutory verification."
    ),
    "hi": (
        "नामित अधिकारियों या कॉमन सर्विस सेंटरों (CSC) द्वारा मूल दस्तावेजों का भौतिक सत्यापन अनिवार्य है। "
        "डिजिटल चेकलिस्ट मार्कर केवल नागरिक मार्गदर्शन के लिए हैं और यह वैधानिक सत्यापन नहीं हैं।"
    ),
    "kn": (
        "ನಿಯೋಜಿತ ಪ್ರಾಧಿಕಾರಗಳು ಅಥವಾ ಸಾಮಾನ್ಯ ಸೇವಾ ಕೇಂದ್ರಗಳ (CSC) ಮೂಲಕ ಮೂಲ ದಾಖಲೆಗಳ ಭೌತಿಕ ಪರಿಶೀಲನೆ ಕಡ್ಡಾಯವಾಗಿದೆ. "
        "ಡಿಜಿಟಲ್ ಚೆಕ್‌ಲಿಸ್ಟ್ ಕೇವಲ ನಾಗರಿಕರ ಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ ಮಾತ್ರವಾಗಿದ್ದು, ಇದು ಶಾಸನಬದ್ಧ ಪರಿಶೀಲನೆಯಾಗಿರುವುದಿಲ್ಲ."
    ),
    "te": (
        "నిర్దేశిత అధికారులు లేదా కామన్ సర్వీస్ సెంటర్ల (CSC) ద్వారా అసలు పత్రాల భౌతిక ధృవీకరణ తప్పనిసరి. "
        "డిజిటల్ చెక్‌లిస్ట్ కేవలం పౌరుల మార్గదర్శకత్వం కోసం మాత్రమే, ఇది చట్టబద్ధమైన ధృవీకరణ కాదు."
    ),
}


class DocumentChecklistService:
    """
    Service for managing scheme document checklists and session-based collection state.
    
    Privacy & Retention Guarantees:
    - Does NOT collect, accept, or store citizen document contents or actual document numbers
      (such as Aadhaar, PAN, or bank account numbers).
    - Maintains minimal anonymous checklist boolean flags ('is_collected') tied to a client-generated UUID.
    - Implements a strict 2-hour sliding-window expiration policy (SEC-01). Expired records are
      neither counted nor returned, and are periodically purged.
    """

    @classmethod
    async def cleanup_expired_sessions(cls, session: AsyncSession) -> int:
        """
        Purges all expired ephemeral checklist items where expires_at <= current UTC time,
        as well as any legacy records missing an expiration timestamp.
        Non-blocking, zero-cost, runs locally without external cron or paid schedulers.
        """
        now_utc = datetime.now(timezone.utc)
        del_stmt = delete(EphemeralChecklistItem).where(
            or_(
                EphemeralChecklistItem.expires_at <= now_utc,
                EphemeralChecklistItem.expires_at.is_(None),
            )
        )
        res = await session.execute(del_stmt)
        await session.commit()
        return res.rowcount or 0

    @classmethod
    async def get_scheme_checklist(
        cls,
        session: AsyncSession,
        scheme_id: str,
        session_id: Optional[str] = None,
    ) -> SchemeChecklistResponse:
        clean_id = scheme_id.strip()
        stmt = (
            select(Scheme)
            .where(
                or_(
                    Scheme.id == clean_id,
                    Scheme.slug == clean_id,
                )
            )
            .options(selectinload(Scheme.documents))
        )
        res = await session.execute(stmt)
        scheme = res.scalar_one_or_none()

        if not scheme:
            raise SchemeNotFoundException(clean_id)

        # 1. Fetch active (non-expired) collection marks if session_id provided
        collected_map: Dict[str, bool] = {}
        if session_id and session_id.strip():
            clean_session = session_id.strip().lower()
            now_utc = datetime.now(timezone.utc)
            item_stmt = select(EphemeralChecklistItem).where(
                and_(
                    EphemeralChecklistItem.session_id == clean_session,
                    EphemeralChecklistItem.scheme_id == scheme.id,
                    EphemeralChecklistItem.expires_at > now_utc,
                )
            )
            item_res = await session.execute(item_stmt)
            for mark in item_res.scalars().all():
                collected_map[mark.document_id] = mark.is_collected

        # 2. Build Checklist items
        checklist_items: List[ChecklistItemSchema] = []
        mandatory_count = 0
        optional_count = 0
        collected_count = 0
        mandatory_collected_count = 0

        for doc in scheme.documents:
            is_collected = collected_map.get(doc.id, False)

            if doc.is_mandatory:
                mandatory_count += 1
                if is_collected:
                    mandatory_collected_count += 1
            else:
                optional_count += 1

            if is_collected:
                collected_count += 1

            checklist_items.append(
                ChecklistItemSchema(
                    id=doc.id,
                    scheme_id=scheme.id,
                    names=doc.names,
                    descriptions=doc.descriptions,
                    is_mandatory=doc.is_mandatory,
                    csc_assisted=doc.csc_assisted,
                    issuer=doc.issuer,
                    source_url=getattr(doc, "source_url", None),
                    is_collected=is_collected,
                )
            )

        # Completion rule: all mandatory documents must be collected (optional documents never affect completion)
        is_complete = (mandatory_collected_count == mandatory_count) and (mandatory_count > 0)

        return SchemeChecklistResponse(
            scheme_id=scheme.id,
            scheme_name=scheme.names,
            total_documents=len(checklist_items),
            mandatory_count=mandatory_count,
            optional_count=optional_count,
            collected_count=collected_count,
            mandatory_collected_count=mandatory_collected_count,
            is_complete=is_complete,
            documents=checklist_items,
            source_citation=scheme.source_citation,
            official_portal_url=scheme.official_url,
            disclaimer=DOCUMENT_DISCLAIMERS,
            session_id=session_id,
        )

    @classmethod
    async def mark_document_collected(
        cls,
        session: AsyncSession,
        session_id: str,
        scheme_id: str,
        document_id: str,
        is_collected: bool = True,
    ) -> SchemeChecklistResponse:
        clean_session = session_id.strip().lower()
        clean_scheme = scheme_id.strip()
        clean_doc = document_id.strip()

        # Validate scheme exists
        scheme_stmt = select(Scheme).where(
            or_(
                Scheme.id == clean_scheme,
                Scheme.slug == clean_scheme,
            )
        ).options(selectinload(Scheme.documents))
        scheme_res = await session.execute(scheme_stmt)
        scheme = scheme_res.scalar_one_or_none()

        if not scheme:
            raise SchemeNotFoundException(clean_scheme)

        # Validate document belongs to this scheme
        valid_doc_ids = {d.id for d in scheme.documents}
        if clean_doc not in valid_doc_ids:
            raise AppError(
                status_code=404,
                detail=f"Document '{clean_doc}' is not part of scheme '{scheme.id}'. Valid documents: {', '.join(sorted(valid_doc_ids))}",
                error_code="DOCUMENT_NOT_FOUND",
            )

        now_utc = datetime.now(timezone.utc)
        new_expiry = now_utc + timedelta(hours=CHECKLIST_SESSION_TTL_HOURS)

        # Upsert ephemeral checklist mark with 2-hour sliding window expiration
        mark_stmt = select(EphemeralChecklistItem).where(
            and_(
                EphemeralChecklistItem.session_id == clean_session,
                EphemeralChecklistItem.scheme_id == scheme.id,
                EphemeralChecklistItem.document_id == clean_doc,
            )
        )
        mark_res = await session.execute(mark_stmt)
        existing_mark = mark_res.scalar_one_or_none()

        if existing_mark:
            existing_mark.is_collected = is_collected
            existing_mark.updated_at = now_utc
            existing_mark.expires_at = new_expiry
        else:
            new_mark = EphemeralChecklistItem(
                session_id=clean_session,
                scheme_id=scheme.id,
                document_id=clean_doc,
                is_collected=is_collected,
                updated_at=now_utc,
                expires_at=new_expiry,
            )
            session.add(new_mark)

        await session.commit()

        # Return updated checklist
        return await cls.get_scheme_checklist(session, scheme.id, session_id=clean_session)

    @classmethod
    async def reset_checklist(
        cls,
        session: AsyncSession,
        session_id: str,
        scheme_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean_session = session_id.strip().lower()
        conditions = [EphemeralChecklistItem.session_id == clean_session]

        if scheme_id and scheme_id.strip():
            clean_scheme = scheme_id.strip()
            conditions.append(EphemeralChecklistItem.scheme_id == clean_scheme)

        del_stmt = delete(EphemeralChecklistItem).where(and_(*conditions))
        res = await session.execute(del_stmt)
        await session.commit()

        return {
            "status": "RESET_SUCCESSFUL",
            "session_id": clean_session,
            "scheme_id": scheme_id,
            "items_reset": res.rowcount or 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
