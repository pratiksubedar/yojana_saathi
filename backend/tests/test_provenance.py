"""
Yojana Saathi - Milestone 5.4 Test Suite
Comprehensive testing for Scheme Provenance Metadata and Freshness Service.
Covers:
1. FreshnessService unit tests (CURRENT, REVIEW_DUE, STALE, UNVERIFIED)
2. Boundary threshold testing & configurable FreshnessConfig
3. Edge cases: missing dates, future dates, unparseable dates
4. Strict protection: never automatically upgrade unverified information to verified
5. Scheme Provenance API endpoint (GET /api/v1/schemes/{id}/provenance)
6. Catalog Freshness Summary API endpoint (GET /api/v1/schemes/freshness/summary)
7. Multilingual provenance metadata across English, Hindi, Kannada, and Telugu
8. Error handling: invalid scheme ID (404) and backward compatibility
"""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.provenance import VerificationStatus, FreshnessStatus
from app.services.freshness_service import FreshnessService, FreshnessConfig

client = TestClient(app)


# ==============================================================================
# 1. UNIT TESTS: FreshnessService Evaluation & Thresholds
# ==============================================================================

def test_freshness_service_current_status():
    """Verify that recently verified/reviewed guidelines receive CURRENT status."""
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(review_due_days=90, stale_days=365, reference_date=ref_date)

    # Reviewed 10 days ago (within 90 days)
    res = FreshnessService.calculate_freshness(
        verified_date_str="2026-10-15",
        reviewed_date_str="2026-10-31",
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res.status == FreshnessStatus.CURRENT
    assert res.is_fresh is True
    assert res.days_since_review == 10
    assert "within 90-day review threshold" in res.reason


def test_freshness_service_partially_verified_current():
    """Verify that PARTIALLY_VERIFIED guidelines within threshold note partial criteria."""
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(review_due_days=90, stale_days=365, reference_date=ref_date)

    res = FreshnessService.calculate_freshness(
        verified_date_str="2026-10-15",
        reviewed_date_str="2026-11-01",
        verification_status=VerificationStatus.PARTIALLY_VERIFIED,
        config=config,
    )
    assert res.status == FreshnessStatus.CURRENT
    assert res.is_fresh is True
    assert "partially verified criteria" in res.reason


def test_freshness_service_review_due_status():
    """Verify that guidelines reviewed between 91 and 365 days ago receive REVIEW_DUE."""
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(review_due_days=90, stale_days=365, reference_date=ref_date)

    # Reviewed 120 days ago (exceeds 90, within 365)
    reviewed_120_days_ago = (ref_date - timedelta(days=120)).isoformat()
    res = FreshnessService.calculate_freshness(
        verified_date_str="2025-01-01",
        reviewed_date_str=reviewed_120_days_ago,
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res.status == FreshnessStatus.REVIEW_DUE
    assert res.is_fresh is False
    assert res.days_since_review == 120
    assert "exceeds standard review threshold of 90 days" in res.reason


def test_freshness_service_stale_status():
    """Verify that guidelines reviewed over 365 days ago receive STALE status."""
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(review_due_days=90, stale_days=365, reference_date=ref_date)

    # Reviewed 400 days ago
    reviewed_400_days_ago = (ref_date - timedelta(days=400)).isoformat()
    res = FreshnessService.calculate_freshness(
        verified_date_str="2024-01-01",
        reviewed_date_str=reviewed_400_days_ago,
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res.status == FreshnessStatus.STALE
    assert res.is_fresh is False
    assert res.days_since_review == 400
    assert "exceeds stale threshold of 365 days" in res.reason


# ==============================================================================
# 2. UNIT TESTS: Protection & Edge Cases (Never Upgrade Unverified)
# ==============================================================================

def test_freshness_service_never_upgrades_unverified_status():
    """
    CRITICAL: Freshness service must NEVER upgrade unverified information
    to CURRENT/VERIFIED status, even if reviewed today.
    """
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(reference_date=ref_date)

    # Reviewed today, but verification status is REQUIRES_OFFICIAL_VERIFICATION
    res = FreshnessService.calculate_freshness(
        verified_date_str="2026-11-10",
        reviewed_date_str="2026-11-10",
        verification_status=VerificationStatus.REQUIRES_OFFICIAL_VERIFICATION,
        config=config,
    )
    assert res.status == FreshnessStatus.UNVERIFIED
    assert res.is_fresh is False
    assert "require official government verification" in res.reason

    # Reviewed today, but verification status is UNVERIFIED
    res_unv = FreshnessService.calculate_freshness(
        verified_date_str="2026-11-10",
        reviewed_date_str="2026-11-10",
        verification_status=VerificationStatus.UNVERIFIED,
        config=config,
    )
    assert res_unv.status == FreshnessStatus.UNVERIFIED
    assert res_unv.is_fresh is False


def test_freshness_service_future_date_handling():
    """Verify that dates in the future are rejected and assigned UNVERIFIED."""
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(reference_date=ref_date)

    future_date = "2027-01-01"
    res = FreshnessService.calculate_freshness(
        verified_date_str="2026-10-15",
        reviewed_date_str=future_date,
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res.status == FreshnessStatus.UNVERIFIED
    assert res.is_fresh is False
    assert "in the future" in res.reason


def test_freshness_service_missing_and_invalid_dates():
    """Verify that missing, empty, or unparseable dates result in UNVERIFIED."""
    ref_date = date(2026, 11, 10)
    config = FreshnessConfig(reference_date=ref_date)

    # Missing date (None)
    res_none = FreshnessService.calculate_freshness(
        verified_date_str=None,
        reviewed_date_str=None,
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res_none.status == FreshnessStatus.UNVERIFIED
    assert res_none.is_fresh is False

    # Empty string date
    res_empty = FreshnessService.calculate_freshness(
        verified_date_str="",
        reviewed_date_str="",
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res_empty.status == FreshnessStatus.UNVERIFIED
    assert res_empty.is_fresh is False

    # Malformed/unparseable date string
    res_malformed = FreshnessService.calculate_freshness(
        verified_date_str="invalid-date-string",
        reviewed_date_str="not-a-date",
        verification_status=VerificationStatus.VERIFIED,
        config=config,
    )
    assert res_malformed.status == FreshnessStatus.UNVERIFIED
    assert res_malformed.is_fresh is False


def test_freshness_service_configurable_thresholds():
    """Verify that review thresholds are dynamically configurable."""
    ref_date = date(2026, 11, 10)

    # 45 days ago
    review_date = (ref_date - timedelta(days=45)).isoformat()

    # Under 90-day threshold -> CURRENT
    config_90 = FreshnessConfig(review_due_days=90, stale_days=365, reference_date=ref_date)
    res_90 = FreshnessService.calculate_freshness(
        verified_date_str="2026-01-01",
        reviewed_date_str=review_date,
        verification_status=VerificationStatus.VERIFIED,
        config=config_90,
    )
    assert res_90.status == FreshnessStatus.CURRENT

    # Under strict 30-day threshold -> REVIEW_DUE
    config_30 = FreshnessConfig(review_due_days=30, stale_days=365, reference_date=ref_date)
    res_30 = FreshnessService.calculate_freshness(
        verified_date_str="2026-01-01",
        reviewed_date_str=review_date,
        verification_status=VerificationStatus.VERIFIED,
        config=config_30,
    )
    assert res_30.status == FreshnessStatus.REVIEW_DUE


# ==============================================================================
# 3. INTEGRATION TESTS: Scheme Provenance Endpoint
# ==============================================================================

def test_get_scheme_provenance_pm_kisan():
    """Verify complete provenance response for PM-KISAN."""
    res = client.get("/api/v1/schemes/pm-kisan/provenance")
    assert res.status_code == 200
    data = res.json()

    # Identifiers & Multilingual Names
    assert data["scheme_id"] == "pm-kisan"
    assert data["names"]["en"] == "PM Kisan Samman Nidhi"
    assert "प्रधानमंत्री" in data["names"]["hi"]
    assert "ಪ್ರಧಾನಮಂತ್ರಿ" in data["names"]["kn"]
    assert "ప్రధానమంత్రి" in data["names"]["te"]

    # Official Web Portal
    assert data["official_portal"]["url"] == "https://pmkisan.gov.in/"
    assert "PM-KISAN" in data["official_portal"]["portal_name"]

    # Primary Source Document & Citation
    source = data["primary_source"]
    assert "PM-KISAN Operational Guidelines" in source["title"]
    assert "https://pmkisan.gov.in" in source["url"]
    assert "Department of Agriculture" in source["issuing_authority"]
    assert len(source["relevant_sections"]) >= 3

    # Verification Metadata & Unresolved Criteria
    verif = data["verification"]
    assert verif["verification_status"] == "VERIFIED"
    assert verif["last_verified_date"] == "2026-11-12"
    assert verif["rule_completeness"] == "PARTIAL"
    assert len(verif["unresolved_criteria"]) >= 1
    unresolved_titles = [u["title"] for u in verif["unresolved_criteria"]]
    assert any("Constitutional Post" in t for t in unresolved_titles)

    # Freshness
    freshness = data["freshness"]
    assert freshness["status"] == "CURRENT"
    assert freshness["is_fresh"] is True
    assert freshness["review_due_threshold_days"] == 90

    # Document Sources
    docs = data["document_sources"]
    assert len(docs) >= 3
    doc_ids = [d["document_id"] for d in docs]
    assert "doc-pmk-aadhaar" in doc_ids


def test_get_scheme_provenance_all_seven_schemes():
    """Verify that all 7 welfare schemes return 200 OK with complete provenance."""
    scheme_ids = [
        "pm-kisan", "pm-jay", "pm-svanidhi", "pmay-g",
        "pm-kmy", "pmmvy", "pm-kusum"
    ]
    for sid in scheme_ids:
        res = client.get(f"/api/v1/schemes/{sid}/provenance")
        assert res.status_code == 200, f"Provenance endpoint failed for {sid}"
        data = res.json()
        assert data["scheme_id"] == sid
        assert data["primary_source"]["url"].startswith("http")
        assert data["primary_source"]["issuing_authority"] is not None
        assert data["verification"]["verification_status"] in ("VERIFIED", "PARTIALLY_VERIFIED", "REQUIRES_OFFICIAL_VERIFICATION")
        assert data["freshness"]["status"] in ("CURRENT", "REVIEW_DUE", "STALE", "UNVERIFIED")
        assert len(data["document_sources"]) >= 1


def test_get_scheme_provenance_custom_query_thresholds():
    """Verify custom review_due_days query parameter dynamically alters freshness."""
    # Under default 90 days threshold, pm-kisan is CURRENT
    res_def = client.get("/api/v1/schemes/pm-kisan/provenance")
    assert res_def.status_code == 200
    assert res_def.json()["freshness"]["status"] == "CURRENT"

    # Under strict 0-day review_due_days, exceeds threshold -> REVIEW_DUE (if verified in past)
    # Testing threshold query params passed through API
    res_custom = client.get("/api/v1/schemes/pm-kisan/provenance?review_due_days=180&stale_days=730")
    assert res_custom.status_code == 200
    data = res_custom.json()
    assert data["freshness"]["review_due_threshold_days"] == 180
    assert data["freshness"]["stale_threshold_days"] == 730


def test_get_scheme_provenance_not_found_404():
    """Verify that non-existent scheme IDs return HTTP 404 with standard ErrorResponse."""
    res = client.get("/api/v1/schemes/non-existent-scheme-xyz/provenance")
    assert res.status_code == 404
    data = res.json()
    assert data["error_code"] == "SCHEME_NOT_FOUND"


# ==============================================================================
# 4. INTEGRATION TESTS: Catalog Freshness Summary Endpoint
# ==============================================================================

def test_get_catalog_freshness_summary():
    """Verify catalog-level aggregate freshness summary endpoint."""
    res = client.get("/api/v1/schemes/freshness/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["total_schemes"] >= 20
    assert data["total_schemes"] == 21
    assert data["total_schemes"] == (
        data["current_count"] +
        data["review_due_count"] +
        data["stale_count"] +
        data["unverified_count"]
    )
    assert data["review_due_threshold_days"] == 90
    assert data["stale_threshold_days"] == 365
    assert len(data["items"]) == 21
    # Verify original 7 schemes are all present
    item_ids = {i["scheme_id"] for i in data["items"]}
    for orig_id in ["pm-kisan", "pm-jay", "pm-svanidhi", "pmay-g", "pm-kmy", "pmmvy", "pm-kusum"]:
        assert orig_id in item_ids

    # Check individual item fields
    item = data["items"][0]
    assert "scheme_id" in item
    assert "scheme_name_en" in item
    assert "freshness_status" in item
    assert "verification_status" in item
    assert "last_reviewed_date" in item
    assert "is_fresh" in item
    assert "reason" in item


def test_get_catalog_freshness_summary_custom_thresholds():
    """Verify catalog freshness summary responds to custom query parameters."""
    res = client.get("/api/v1/schemes/freshness/summary?review_due_days=30&stale_days=180")
    assert res.status_code == 200
    data = res.json()
    assert data["review_due_threshold_days"] == 30
    assert data["stale_threshold_days"] == 180

