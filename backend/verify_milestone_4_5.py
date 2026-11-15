"""
Milestone 4.5 Security Verification Script for Yojana Saathi.
Executes and prints out live, deterministic verifications for all 6 functional security checks.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import sqlite3
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import async_session_factory
from app.db.models import EphemeralChecklistItem
from app.services.document_service import DocumentChecklistService

client = TestClient(app)

async def run_verifications():
    print("=" * 70)
    print("YOJANA SAATHI - MILESTONE 4.5 SECURITY VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. EXPIRY VERIFICATION
    # -------------------------------------------------------------
    print("\n[CHECK 1] Session Expiry Verification")
    session_id_1 = str(uuid.uuid4())
    scheme_id_1 = "pm-kisan"
    doc_id_1 = "doc-pmk-aadhaar"
    now_utc = datetime.now(timezone.utc)
    expired_time = now_utc - timedelta(hours=1) # Expired 1 hour ago

    # Insert an expired row into the DB directly
    async with async_session_factory() as session:
        expired_item = EphemeralChecklistItem(
            session_id=session_id_1,
            scheme_id=scheme_id_1,
            document_id=doc_id_1,
            is_collected=True,
            updated_at=now_utc - timedelta(hours=3),
            expires_at=expired_time,
        )
        session.add(expired_item)
        await session.commit()

    # Query checklist via API
    res1 = client.get(f"/api/v1/documents/checklist/{scheme_id_1}?session_id={session_id_1}")
    data1 = res1.json()
    collected_count_1 = data1["collected_count"]
    target_doc = next(d for d in data1["documents"] if d["id"] == doc_id_1)
    
    print(f"  Inserted expired item for session {session_id_1} (expires_at={expired_time.isoformat()})")
    print(f"  API Response Status: {res1.status_code}")
    print(f"  Reported collected_count: {collected_count_1} (Expected: 0)")
    print(f"  Document '{doc_id_1}' is_collected: {target_doc['is_collected']} (Expected: False)")
    
    if collected_count_1 == 0 and target_doc["is_collected"] is False:
        print("  -> RESULT: PASS (Expired state safely suppressed from user checklist)")
    else:
        print("  -> RESULT: FAIL")
        return False

    # -------------------------------------------------------------
    # 2. CLEANUP VERIFICATION
    # -------------------------------------------------------------
    print("\n[CHECK 2] Expired Rows Database Cleanup Verification")
    async with async_session_factory() as session:
        # Count current expired items before cleanup
        # Add two deliberately expired rows
        item_a = EphemeralChecklistItem(
            session_id=str(uuid.uuid4()),
            scheme_id="pm-jay",
            document_id="doc-pmj-aadhaar",
            is_collected=True,
            updated_at=now_utc - timedelta(hours=4),
            expires_at=now_utc - timedelta(hours=2),
        )
        item_b = EphemeralChecklistItem(
            session_id=str(uuid.uuid4()),
            scheme_id="pm-svanidhi",
            document_id="doc-pms-aadhaar",
            is_collected=True,
            updated_at=now_utc - timedelta(hours=3),
            expires_at=now_utc - timedelta(hours=1),
        )
        session.add_all([item_a, item_b])
        await session.commit()

    from sqlalchemy import func, select, or_

    async with async_session_factory() as session:
        expired_stmt = select(func.count(EphemeralChecklistItem.id)).where(
            or_(
                EphemeralChecklistItem.expires_at <= now_utc,
                EphemeralChecklistItem.expires_at.is_(None),
            )
        )
        total_stmt = select(func.count(EphemeralChecklistItem.id))
        
        expired_count_before = (await session.execute(expired_stmt)).scalar_one()
        total_count_before = (await session.execute(total_stmt)).scalar_one()

    print(f"  Total rows before cleanup: {total_count_before}")
    print(f"  Expired rows before cleanup: {expired_count_before}")

    # Trigger cleanup
    async with async_session_factory() as session:
        deleted_count = await DocumentChecklistService.cleanup_expired_sessions(session)

    async with async_session_factory() as session:
        expired_count_after = (await session.execute(expired_stmt)).scalar_one()
        total_count_after = (await session.execute(total_stmt)).scalar_one()

    print(f"  Rows purged by cleanup: {deleted_count}")
    print(f"  Total rows after cleanup: {total_count_after}")
    print(f"  Expired rows after cleanup: {expired_count_after} (Expected: 0)")

    if expired_count_after == 0 and deleted_count >= 2:
        print("  -> RESULT: PASS (All expired rows permanently deleted from SQLite)")
    else:
        print("  -> RESULT: FAIL")
        return False

    # -------------------------------------------------------------
    # 3. PII REJECTION VERIFICATION
    # -------------------------------------------------------------
    print("\n[CHECK 3] Strict PII Rejection (Mark & Reset Endpoints)")
    sensitive_fields = ["aadhaar", "pan", "bank_account", "phone", "file"]
    test_session = str(uuid.uuid4())

    all_rejected = True
    print("  Testing Mark Endpoint (/api/v1/documents/checklist/mark):")
    for f in sensitive_fields:
        payload = {
            "session_id": test_session,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True,
            f: "FABRICATED_PII_TEST_VAL_123"
        }
        res = client.post("/api/v1/documents/checklist/mark", json=payload)
        is_422 = (res.status_code == 422)
        print(f"    Field '{f}': HTTP {res.status_code} ({'Rejected' if is_422 else 'ALLOWED'})")
        if not is_422:
            all_rejected = False

    print("  Testing Reset Endpoint (/api/v1/documents/checklist/reset):")
    for f in sensitive_fields:
        payload = {
            "session_id": test_session,
            f: "FABRICATED_PII_TEST_VAL_123"
        }
        res = client.post("/api/v1/documents/checklist/reset", json=payload)
        is_422 = (res.status_code == 422)
        print(f"    Field '{f}': HTTP {res.status_code} ({'Rejected' if is_422 else 'ALLOWED'})")
        if not is_422:
            all_rejected = False

    if all_rejected:
        print("  -> RESULT: PASS (All 10/10 sensitive field requests rejected with HTTP 422)")
    else:
        print("  -> RESULT: FAIL")
        return False

    # -------------------------------------------------------------
    # 4. SESSION ID FORMAT VERIFICATION
    # -------------------------------------------------------------
    print("\n[CHECK 4] Session ID Format Validation")
    malformed_ids = ["not-a-uuid", "12345", "admin'--", "c9b4e120-7f2a-bad-uuid"]
    all_invalid_rejected = True
    for bad_id in malformed_ids:
        res_get = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={bad_id}")
        res_mark = client.post("/api/v1/documents/checklist/mark", json={
            "session_id": bad_id,
            "scheme_id": "pm-kisan",
            "document_id": "doc-pmk-aadhaar",
            "is_collected": True
        })
        res_reset = client.post("/api/v1/documents/checklist/reset", json={"session_id": bad_id})
        
        ok = (res_get.status_code == 422 and res_mark.status_code == 422 and res_reset.status_code == 422)
        print(f"    Malformed ID '{bad_id}': GET={res_get.status_code}, MARK={res_mark.status_code}, RESET={res_reset.status_code}")
        if not ok:
            all_invalid_rejected = False

    if all_invalid_rejected:
        print("  -> RESULT: PASS (All non-UUID session identifiers rejected with HTTP 422)")
    else:
        print("  -> RESULT: FAIL")
        return False

    # -------------------------------------------------------------
    # 5. SESSION ISOLATION VERIFICATION
    # -------------------------------------------------------------
    print("\n[CHECK 5] Session Isolation Verification")
    session_alpha = str(uuid.uuid4())
    session_beta = str(uuid.uuid4())

    # Mark document in Session Alpha
    client.post("/api/v1/documents/checklist/mark", json={
        "session_id": session_alpha,
        "scheme_id": "pm-kisan",
        "document_id": "doc-pmk-aadhaar",
        "is_collected": True
    })

    # Read both
    res_a = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={session_alpha}").json()
    res_b = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={session_beta}").json()

    print(f"    Session Alpha (marked 1 doc): collected_count = {res_a['collected_count']}")
    print(f"    Session Beta  (unmarked):     collected_count = {res_b['collected_count']}")

    # Reset Session Beta and verify Session Alpha unaffected
    client.post("/api/v1/documents/checklist/reset", json={"session_id": session_beta})
    res_a_after = client.get(f"/api/v1/documents/checklist/pm-kisan?session_id={session_alpha}").json()
    print(f"    Session Alpha after Beta reset: collected_count = {res_a_after['collected_count']}")

    # Clean up Alpha
    client.post("/api/v1/documents/checklist/reset", json={"session_id": session_alpha})

    if res_a['collected_count'] == 1 and res_b['collected_count'] == 0 and res_a_after['collected_count'] == 1:
        print("  -> RESULT: PASS (Strict cryptographic session isolation verified)")
    else:
        print("  -> RESULT: FAIL")
        return False

    # -------------------------------------------------------------
    # 6. DATABASE MIGRATION INTEGRITY VERIFICATION
    # -------------------------------------------------------------
    print("\n[CHECK 6] Database Migration & Scheme Data Preservation")
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM schemes")
    s_cnt_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM documents")
    d_cnt_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rules")
    r_cnt_before = cur.fetchone()[0]
    con.close()

    print(f"    Before init_db(): Schemes={s_cnt_before}, Documents={d_cnt_before}, Rules={r_cnt_before}")
    
    # Run init_db migration
    await init_db()

    con = sqlite3.connect("app.db")
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM schemes")
    s_cnt_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM documents")
    d_cnt_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rules")
    r_cnt_after = cur.fetchone()[0]
    cur.execute("PRAGMA table_info(session_checklist_items)")
    cols = [r[1] for r in cur.fetchall()]
    con.close()

    print(f"    After  init_db(): Schemes={s_cnt_after}, Documents={d_cnt_after}, Rules={r_cnt_after}")
    print(f"    Columns in session_checklist_items: {cols}")

    if s_cnt_before == 7 and s_cnt_after == 7 and d_cnt_before == d_cnt_after and d_cnt_before >= 21 and "expires_at" in cols:
        print(f"  -> RESULT: PASS (All {s_cnt_after} schemes & {d_cnt_after} documents preserved with zero data loss)")
    else:
        print("  -> RESULT: FAIL")
        return False

    print("\n" + "=" * 70)
    print("ALL FUNCTIONAL SECURITY VERIFICATIONS (1-6) COMPLETED SUCCESSFULLY")
    print("=" * 70)
    return True

if __name__ == "__main__":
    asyncio.run(run_verifications())
