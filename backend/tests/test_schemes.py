import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_all_schemes():
    """Verify listing all active schemes returns 200 OK and expected 21 schemes."""
    response = client.get("/api/v1/schemes?page_size=50")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data
    assert "filters_applied" in data

    assert data["pagination"]["total"] == 21
    assert len(data["items"]) == 21

    scheme_ids = [item["id"] for item in data["items"]]
    assert "pm-kisan" in scheme_ids
    assert "pm-jay" in scheme_ids
    assert "pm-svanidhi" in scheme_ids
    assert "pmay-g" in scheme_ids
    assert "pm-kmy" in scheme_ids
    assert "pmmvy" in scheme_ids
    assert "pm-kusum" in scheme_ids
    assert "apy" in scheme_ids
    assert "pmjjby" in scheme_ids
    assert "pmsby" in scheme_ids
    assert "pm-mudra" in scheme_ids
    assert "ssy" in scheme_ids
    assert "pm-vishwakarma" in scheme_ids
    assert "day-nrlm" in scheme_ids
    assert "stand-up-india" in scheme_ids
    assert "pm-surya-ghar" in scheme_ids
    assert "pmuy" in scheme_ids
    assert "kcc" in scheme_ids
    assert "pm-sym" in scheme_ids
    assert "nsap-ignoaps" in scheme_ids
    assert "pmjdy" in scheme_ids

    # Check multilingual structure on items
    for item in data["items"]:
        for lang in ["en", "hi", "kn", "te"]:
            assert lang in item["names"]
            assert len(item["names"][lang].strip()) > 0
            assert lang in item["descriptions"]
            assert len(item["descriptions"][lang].strip()) > 0
            assert lang in item["benefits"]
            assert len(item["benefits"][lang].strip()) > 0

        assert item["official_url"].startswith("https://")
        assert len(item["portal_name"]) > 0
        assert len(item["last_verified_date"]) > 0
        assert item["rules_count"] > 0
        assert item["documents_count"] > 0


def test_pagination():
    """Verify pagination controls: page, page_size, total_pages, has_next, has_prev."""
    # Page 1 with size 2
    res1 = client.get("/api/v1/schemes?page=1&page_size=2")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["items"]) == 2
    assert data1["pagination"]["page"] == 1
    assert data1["pagination"]["page_size"] == 2
    assert data1["pagination"]["total"] == 21
    assert data1["pagination"]["total_pages"] == 11
    assert data1["pagination"]["has_next"] is True
    assert data1["pagination"]["has_prev"] is False

    # Page 2 with size 2
    res2 = client.get("/api/v1/schemes?page=2&page_size=2")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["items"]) == 2
    assert data2["pagination"]["page"] == 2
    assert data2["pagination"]["has_next"] is True
    assert data2["pagination"]["has_prev"] is True

    # Page 1 and Page 2 items must not overlap
    page1_ids = {s["id"] for s in data1["items"]}
    page2_ids = {s["id"] for s in data2["items"]}
    assert page1_ids.isdisjoint(page2_ids)

    # Page 11 with size 2 (last page, 1 remaining item out of 21)
    res11 = client.get("/api/v1/schemes?page=11&page_size=2")
    assert res11.status_code == 200
    data11 = res11.json()
    assert len(data11["items"]) == 1
    assert data11["pagination"]["page"] == 11
    assert data11["pagination"]["has_next"] is False
    assert data11["pagination"]["has_prev"] is True

    # Out of range page returns empty items list
    res12 = client.get("/api/v1/schemes?page=12&page_size=2")
    assert res12.status_code == 200
    data12 = res12.json()
    assert len(data12["items"]) == 0
    assert data12["pagination"]["has_next"] is False
    assert data12["pagination"]["has_prev"] is True


def test_filter_by_category():
    """Verify filtering schemes by domain category."""
    # Agriculture -> PM-KISAN, PM-KMY, PM-KUSUM, KCC
    res_agri = client.get("/api/v1/schemes?category=agriculture")
    assert res_agri.status_code == 200
    data_agri = res_agri.json()
    assert data_agri["pagination"]["total"] == 4
    agri_ids = {s["id"] for s in data_agri["items"]}
    assert agri_ids == {"pm-kisan", "pm-kmy", "pm-kusum", "kcc"}
    assert data_agri["filters_applied"]["category"] == "agriculture"

    # Social Welfare -> PMMVY, APY, PMJJBY, PMSBY, DAY-NRLM, PM-SYM, NSAP-IGNOAPS, PMJDY
    res_welfare = client.get("/api/v1/schemes?category=social_welfare&page_size=20")
    assert res_welfare.status_code == 200
    data_welfare = res_welfare.json()
    assert data_welfare["pagination"]["total"] == 8
    welfare_ids = {s["id"] for s in data_welfare["items"]}
    assert "pmmvy" in welfare_ids
    assert "apy" in welfare_ids

    # Healthcare -> PM-JAY
    res_health = client.get("/api/v1/schemes?category=healthcare")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["pagination"]["total"] == 1
    assert data_health["items"][0]["id"] == "pm-jay"

    # Housing -> PMAY-G
    res_housing = client.get("/api/v1/schemes?category=housing")
    assert res_housing.status_code == 200
    data_housing = res_housing.json()
    assert data_housing["pagination"]["total"] == 1
    assert data_housing["items"][0]["id"] == "pmay-g"

    # Employment -> PM-SVANidhi, PM-MUDRA, PM-Vishwakarma, Stand-Up India
    res_emp = client.get("/api/v1/schemes?category=employment")
    assert res_emp.status_code == 200
    data_emp = res_emp.json()
    assert data_emp["pagination"]["total"] == 4
    emp_ids = {s["id"] for s in data_emp["items"]}
    assert emp_ids == {"pm-svanidhi", "pm-mudra", "pm-vishwakarma", "stand-up-india"}

    # Women and Child -> SSY, PMUY
    res_wc = client.get("/api/v1/schemes?category=women_and_child")
    assert res_wc.status_code == 200
    data_wc = res_wc.json()
    assert data_wc["pagination"]["total"] == 2
    wc_ids = {s["id"] for s in data_wc["items"]}
    assert wc_ids == {"ssy", "pmuy"}

    # Energy -> PM Surya Ghar
    res_energy = client.get("/api/v1/schemes?category=energy")
    assert res_energy.status_code == 200
    data_energy = res_energy.json()
    assert data_energy["pagination"]["total"] == 1
    assert data_energy["items"][0]["id"] == "pm-surya-ghar"


def test_filter_by_scheme_type():
    """Verify filtering schemes by scheme_type (CENTRAL_SECTOR vs CENTRALLY_SPONSORED)."""
    # Central sector: 15 schemes
    res_cs = client.get("/api/v1/schemes?scheme_type=CENTRAL_SECTOR&page_size=30")
    assert res_cs.status_code == 200
    data_cs = res_cs.json()
    assert data_cs["pagination"]["total"] == 15
    cs_ids = {s["id"] for s in data_cs["items"]}
    assert "pm-kisan" in cs_ids
    assert "pm-svanidhi" in cs_ids
    assert "pm-kmy" in cs_ids

    # Centrally sponsored: pm-jay, pmay-g, pmmvy, pm-kusum, day-nrlm, nsap-ignoaps
    res_spon = client.get("/api/v1/schemes?scheme_type=CENTRALLY_SPONSORED")
    assert res_spon.status_code == 200
    data_spon = res_spon.json()
    assert data_spon["pagination"]["total"] == 6
    spon_ids = {s["id"] for s in data_spon["items"]}
    assert spon_ids == {"pm-jay", "pmay-g", "pmmvy", "pm-kusum", "day-nrlm", "nsap-ignoaps"}


def test_filter_by_state_applicability():
    """Verify state filtering correctly includes nationwide schemes applicable to all states."""
    res_kn = client.get("/api/v1/schemes?state=Karnataka")
    assert res_kn.status_code == 200
    data_kn = res_kn.json()
    assert data_kn["pagination"]["total"] == 21

    res_te = client.get("/api/v1/schemes?state=Telangana")
    assert res_te.status_code == 200
    data_te = res_te.json()
    assert data_te["pagination"]["total"] == 21


def test_multilingual_search():
    """Verify multilingual search across English, Hindi, Kannada, and Telugu terms."""
    # English query
    res_en = client.get("/api/v1/schemes?q=kisan")
    assert res_en.status_code == 200
    assert any(s["id"] == "pm-kisan" for s in res_en.json()["items"])

    # Hindi query
    res_hi = client.get("/api/v1/schemes?q=किसान")
    assert res_hi.status_code == 200
    assert any(s["id"] == "pm-kisan" for s in res_hi.json()["items"])

    # Kannada query
    res_kn = client.get("/api/v1/schemes?q=ಕಿಸಾನ್")
    assert res_kn.status_code == 200
    assert any(s["id"] == "pm-kisan" for s in res_kn.json()["items"])

    # Telugu query
    res_te = client.get("/api/v1/schemes?q=ఆరోగ్య")
    assert res_te.status_code == 200
    assert any(s["id"] == "pm-jay" for s in res_te.json()["items"])


def test_empty_results():
    """Verify that queries matching no schemes cleanly return HTTP 200 with empty items list."""
    # Non-existent category
    res_cat = client.get("/api/v1/schemes?category=astrophysics")
    assert res_cat.status_code == 200
    data_cat = res_cat.json()
    assert data_cat["pagination"]["total"] == 0
    assert data_cat["items"] == []

    # Non-matching search query
    res_q = client.get("/api/v1/schemes?q=nonexistentqueryxyz987")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["pagination"]["total"] == 0
    assert data_q["items"] == []


def test_invalid_filter_errors_400():
    """Verify that invalid filter formats return consistent HTTP 400 structured error responses."""
    # Invalid scheme_type
    res_type = client.get("/api/v1/schemes?scheme_type=INTERNATIONAL")
    assert res_type.status_code == 400
    data_type = res_type.json()
    assert data_type["error_code"] == "INVALID_FILTER"
    assert "Invalid scheme_type" in data_type["detail"]
    assert "timestamp" in data_type

    # Whitespace only category
    res_cat = client.get("/api/v1/schemes?category=   ")
    assert res_cat.status_code == 400
    assert res_cat.json()["error_code"] == "INVALID_FILTER"

    # Whitespace only state
    res_state = client.get("/api/v1/schemes?state=   ")
    assert res_state.status_code == 400
    assert res_state.json()["error_code"] == "INVALID_FILTER"

    # Whitespace only search query
    res_q = client.get("/api/v1/schemes?q=   ")
    assert res_q.status_code == 400
    assert res_q.json()["error_code"] == "INVALID_FILTER"


def test_invalid_pagination_validation_422():
    """Verify that invalid pagination parameters trigger HTTP 422 Unprocessable Entity."""
    # Page < 1
    res_page = client.get("/api/v1/schemes?page=0")
    assert res_page.status_code == 422

    # Page size > 100
    res_size = client.get("/api/v1/schemes?page_size=150")
    assert res_size.status_code == 422


def test_scheme_detail_success():
    """Verify retrieving complete scheme details by ID with rules, citations, and documents."""
    response = client.get("/api/v1/schemes/pm-kisan")
    assert response.status_code == 200
    data = response.json()

    # Core metadata
    assert data["id"] == "pm-kisan"
    assert data["slug"] == "pm-kisan"
    assert data["category"] == "agriculture"
    assert data["scheme_type"] == "CENTRAL_SECTOR"
    assert data["financial_amount_inr"] == 6000.0

    # Multilingual content across all 4 languages
    for lang in ["en", "hi", "kn", "te"]:
        assert lang in data["names"]
        assert lang in data["descriptions"]
        assert lang in data["benefits"]
        assert len(data["names"][lang].strip()) > 0

    # Official verification and citation
    assert data["official_url"] == "https://pmkisan.gov.in/"
    assert data["portal_name"] == "PM-KISAN National Portal"
    assert data["last_verified_date"] == "2026-10-15"
    assert data["last_reviewed_date"] == "2026-11-10"
    assert "source_citation" in data
    assert data["source_citation"]["issuing_authority"] == "Department of Agriculture and Farmers Welfare, Government of India"

    # Application procedure (Milestone 5.1)
    assert len(data["application_procedure"]) >= 4
    step1 = data["application_procedure"][0]
    assert "titles" in step1 and "descriptions" in step1 and "channel" in step1
    for lang in ["en", "hi", "kn", "te"]:
        assert lang in step1["titles"]

    # Rules
    assert len(data["rules"]) > 0
    rule = data["rules"][0]
    assert rule["scheme_id"] == "pm-kisan"
    assert "conditions" in rule
    assert "all_of" in rule["conditions"]
    assert "none_of" in rule["conditions"]

    # Documents
    assert len(data["documents"]) == 3
    doc_ids = [d["id"] for d in data["documents"]]
    assert "doc-pmk-aadhaar" in doc_ids
    assert "doc-pmk-land" in doc_ids
    assert "doc-pmk-bank" in doc_ids

    # Document details check
    doc = data["documents"][0]
    assert doc["is_mandatory"] is True
    assert doc.get("source_url") is not None
    assert "names" in doc
    for lang in ["en", "hi", "kn", "te"]:
        assert lang in doc["names"]


def test_scheme_detail_by_slug():
    """Verify retrieving scheme by its slug identifier."""
    response = client.get("/api/v1/schemes/pm-jay")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "pm-jay"
    assert data["category"] == "healthcare"


def test_scheme_detail_not_found_404():
    """Verify that non-existent scheme IDs return a structured HTTP 404 response."""
    response = client.get("/api/v1/schemes/non-existent-scheme-999")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "SCHEME_NOT_FOUND"
    assert "non-existent-scheme-999" in data["detail"]
    assert "timestamp" in data


def test_new_schemes_detail_and_no_frontend_404():
    """Verify that all three newly expanded schemes resolve correctly without 404s."""
    for scheme_id in ["pm-kmy", "pmmvy", "pm-kusum"]:
        response = client.get(f"/api/v1/schemes/{scheme_id}")
        assert response.status_code == 200, f"Scheme {scheme_id} returned {response.status_code}"
        data = response.json()
        assert data["id"] == scheme_id
        assert data["slug"] == scheme_id
        assert len(data["application_procedure"]) >= 3
        assert len(data["rules"]) > 0
        assert len(data["documents"]) == 3
        for lang in ["en", "hi", "kn", "te"]:
            assert lang in data["names"]
            assert lang in data["descriptions"]
            assert lang in data["benefits"]
        assert data["official_url"].startswith("https://")
        assert data["source_citation"]["verification_status"] == "VERIFIED"
