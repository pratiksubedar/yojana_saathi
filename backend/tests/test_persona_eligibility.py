"""
Yojana Saathi - Phase 1: 6-Persona Multi-Scheme Discovery & Eligibility Engine Acceptance Tests

Tests multi-scheme discovery across all 21 welfare schemes for 6 distinct citizen personas:
1. Farmer Persona
2. Senior Citizen Persona
3. Low-Income Woman Persona
4. Student Persona
5. Unemployed Person Persona
6. Small Business Owner / Artisan Persona

Verifies:
- All 21 schemes are evaluated simultaneously from a single citizen profile.
- 3-state deterministic output: ELIGIBLE, POSSIBLY_ELIGIBLE, NOT_ELIGIBLE.
- Inclusion of all 9 presentation dimensions: name, ministry, status, why matched/failed,
  benefits, missing info, required documents, application steps, official URL, last verified date.
- Python rule engine remains the sole deterministic authority.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas.eligibility import EligibilityStatusEnum, RuleCompletenessEnum


@pytest.mark.asyncio
async def test_persona_1_farmer_multi_scheme_discovery():
    """
    Persona 1: Smallholder Rural Farmer
    - Should match: KCC (ELIGIBLE), PM-KISAN (POSSIBLY_ELIGIBLE due to statutory CSC verification)
    - Should be ineligible for: PM-SVANidhi (not a street vendor), SSY (no girl child), PM-Vishwakarma
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "occupation": "Farmer",
                "age": 38,
                "landholding_hectares": 1.5,
                "trade_category": "None",
                "is_bank_defaulter": False,
                "pays_income_tax": False,
                "is_regular_govt_employee": False,
                "is_institutional_landholder": False,
                "monthly_pension_inr": 0,
                "is_registered_professional": False,
                "has_savings_account": True,
                "has_water_source_for_irrigation": True,
                "has_existing_grid_connected_agri_pump": False,
            },
            "preferred_language": "en"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        results = data["results"]
        assert len(results) == 21, f"Expected 21 schemes evaluated, got {len(results)}"

        res_map = {r["scheme_id"]: r for r in results}

        # 1. KCC must be ELIGIBLE
        kcc = res_map["kcc"]
        assert kcc["status"] == EligibilityStatusEnum.ELIGIBLE
        assert len(kcc["conditions_satisfied"]) >= 3
        assert len(kcc["conditions_failed"]) == 0
        assert kcc["ministry"] == "Ministry of Agriculture and Farmers Welfare"
        assert kcc["official_url"] == "https://pmkisan.gov.in/"
        assert len(kcc["documents"]) >= 2
        assert len(kcc["application_procedure"]) >= 2

        # 2. PM-KISAN satisfies all criteria; returns POSSIBLY_ELIGIBLE due to PARTIAL rule completeness
        pm_kisan = res_map["pm-kisan"]
        assert pm_kisan["status"] == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
        assert pm_kisan["rule_completeness"] == RuleCompletenessEnum.PARTIAL
        assert len(pm_kisan["conditions_satisfied"]) >= 5
        assert len(pm_kisan["unresolved_criteria"]) >= 1

        # 3. PM-SVANidhi must be NOT_ELIGIBLE (occupation not Street Vendor)
        svanidhi = res_map["pm-svanidhi"]
        assert svanidhi["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert any(c["field"] == "occupation" for c in svanidhi["conditions_failed"])

        # 4. PM-Vishwakarma must be NOT_ELIGIBLE (farmer is not in 18 artisan trades)
        vishwakarma = res_map["pm-vishwakarma"]
        assert vishwakarma["status"] == EligibilityStatusEnum.NOT_ELIGIBLE


@pytest.mark.asyncio
async def test_persona_2_senior_citizen_multi_scheme_discovery():
    """
    Persona 2: Low-Income Senior Citizen (Age 72, BPL)
    - Should match: NSAP-IGNOAPS (ELIGIBLE), PM-JAY (POSSIBLY_ELIGIBLE senior 70+ pathway)
    - Should be ineligible for: APY (age > 40), PMJJBY (age > 50), PMSBY (age > 70), PM-KMY (age > 40)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "age": 72,
                "has_bpl_card": True,
                "is_regular_govt_employee": False,
                "has_savings_account": True,
                "pays_income_tax": False,
            },
            "preferred_language": "en"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        results = res.json()["results"]
        res_map = {r["scheme_id"]: r for r in results}

        # 1. NSAP-IGNOAPS must be ELIGIBLE
        ignoaps = res_map["nsap-ignoaps"]
        assert ignoaps["status"] == EligibilityStatusEnum.ELIGIBLE
        assert ignoaps["ministry"] == "Ministry of Rural Development"
        assert len(ignoaps["conditions_satisfied"]) >= 2
        assert len(ignoaps["documents"]) >= 3

        # 2. PM-JAY matches Senior 70+ age pathway
        pm_jay = res_map["pm-jay"]
        assert pm_jay["status"] == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
        assert any(c["field"] == "age" and c["status"] == "SATISFIED" for c in pm_jay["conditions_satisfied"])

        # 3. Age-limited schemes must be NOT_ELIGIBLE
        apy = res_map["apy"]
        assert apy["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert any(c["field"] == "age" for c in apy["conditions_failed"])

        pmjjby = res_map["pmjjby"]
        assert pmjjby["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert any(c["field"] == "age" for c in pmjjby["conditions_failed"])

        pmsby = res_map["pmsby"]
        assert pmsby["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert any(c["field"] == "age" for c in pmsby["conditions_failed"])


@pytest.mark.asyncio
async def test_persona_3_low_income_woman_multi_scheme_discovery():
    """
    Persona 3: Rural Low-Income Pregnant Woman (Age 23, BPL, SHG Member)
    - Should match: PMUY (ELIGIBLE), DAY-NRLM (ELIGIBLE), PMMVY (POSSIBLY_ELIGIBLE)
    - Should be ineligible for: PM-KISAN (not a farmer), NSAP-IGNOAPS (age < 60)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "gender": "Female",
                "age": 23,
                "is_deprived_household": True,
                "has_existing_lpg_connection": False,
                "is_rural_resident": True,
                "is_shg_member": True,
                "is_pregnant_or_lactating": True,
                "anc_checkups_completed": 2,
                "is_regular_govt_employee": False,
                "receives_formal_paid_maternity_benefits": False,
                "has_bpl_card": True,
                "has_savings_account": True,
                "pays_income_tax": False,
            },
            "preferred_language": "hi"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        results = res.json()["results"]
        res_map = {r["scheme_id"]: r for r in results}

        # 1. PMUY must be ELIGIBLE
        pmuy = res_map["pmuy"]
        assert pmuy["status"] == EligibilityStatusEnum.ELIGIBLE
        assert pmuy["ministry"] == "Ministry of Petroleum and Natural Gas"
        assert len(pmuy["documents"]) >= 3
        assert len(pmuy["application_procedure"]) >= 2

        # 2. DAY-NRLM must be ELIGIBLE
        day_nrlm = res_map["day-nrlm"]
        assert day_nrlm["status"] == EligibilityStatusEnum.ELIGIBLE
        assert day_nrlm["ministry"] == "Ministry of Rural Development"

        # 3. PMMVY is POSSIBLY_ELIGIBLE (satisfies conditions, PARTIAL completeness)
        pmmvy = res_map["pmmvy"]
        assert pmmvy["status"] == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
        assert len(pmmvy["conditions_satisfied"]) >= 5

        # 4. IGNOAPS must be NOT_ELIGIBLE (age 23 < 60)
        ignoaps = res_map["nsap-ignoaps"]
        assert ignoaps["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert any(c["field"] == "age" for c in ignoaps["conditions_failed"])


@pytest.mark.asyncio
async def test_persona_4_student_multi_scheme_discovery():
    """
    Persona 4: Student (Age 19, Non-earning, Enrolled in College)
    - Should match: PMJDY (ELIGIBLE if has_basic_savings_bank_account is False)
    - Should be ineligible for: PM-KISAN, PM-SVANidhi, NSAP-IGNOAPS, PM-KMY (not a farmer)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "age": 19,
                "occupation": "Student",
                "has_basic_savings_bank_account": False,
                "has_savings_account": False,
                "pays_income_tax": False,
                "has_bpl_card": False,
            },
            "preferred_language": "en"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        results = res.json()["results"]
        res_map = {r["scheme_id"]: r for r in results}

        # 1. PMJDY must be ELIGIBLE
        pmjdy = res_map["pmjdy"]
        assert pmjdy["status"] == EligibilityStatusEnum.ELIGIBLE
        assert pmjdy["ministry"] == "Ministry of Finance"

        # 2. Ineligible for Farmer/Elderly schemes
        assert res_map["pm-kisan"]["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert res_map["nsap-ignoaps"]["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert res_map["pm-kmy"]["status"] == EligibilityStatusEnum.NOT_ELIGIBLE


@pytest.mark.asyncio
async def test_persona_5_unemployed_person_multi_scheme_discovery():
    """
    Persona 5: Unemployed Worker looking for livelihood/social security (Age 28, Unorganised Worker, Income ₹7,500)
    - Should match: PM-SYM (ELIGIBLE), APY (ELIGIBLE), PMJJBY (ELIGIBLE), PMSBY (ELIGIBLE)
    - Should be ineligible for: NSAP-IGNOAPS (age 28 < 60), PM-KISAN (not farmer)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "age": 28,
                "occupation": "Unorganised Worker",
                "is_unorganised_worker": True,
                "monthly_income_inr": 7500.0,
                "is_epfo_esic_nps_member": False,
                "pays_income_tax": False,
                "has_savings_account": True,
                "is_regular_govt_employee": False,
            },
            "preferred_language": "te"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        results = res.json()["results"]
        res_map = {r["scheme_id"]: r for r in results}

        # 1. PM-SYM must be ELIGIBLE
        pm_sym = res_map["pm-sym"]
        assert pm_sym["status"] == EligibilityStatusEnum.ELIGIBLE
        assert pm_sym["ministry"] == "Ministry of Labour and Employment"
        assert len(pm_sym["conditions_satisfied"]) >= 4

        # 2. APY must be ELIGIBLE
        apy = res_map["apy"]
        assert apy["status"] == EligibilityStatusEnum.ELIGIBLE

        # 3. Insurance schemes must be ELIGIBLE
        assert res_map["pmjjby"]["status"] == EligibilityStatusEnum.ELIGIBLE
        assert res_map["pmsby"]["status"] == EligibilityStatusEnum.ELIGIBLE

        # 4. Ineligible for senior schemes
        assert res_map["nsap-ignoaps"]["status"] == EligibilityStatusEnum.NOT_ELIGIBLE


@pytest.mark.asyncio
async def test_persona_6_small_business_owner_multi_scheme_discovery():
    """
    Persona 6: Traditional Artisan / Micro-Enterprise Owner (Age 34, Carpenter / Suthar)
    - Should match: PM-Vishwakarma (ELIGIBLE), PM-Mudra (ELIGIBLE)
    - Should be ineligible for: PM-KISAN (not agricultural landholder), NSAP-IGNOAPS (age < 60)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "age": 34,
                "occupation": "Artisan / Carpenter",
                "trade_category": "Carpenter (Suthar)",
                "landholding_hectares": 0.0,
                "enterprise_type": "Micro Enterprise",
                "is_regular_govt_employee": False,
                "is_bank_defaulter": False,
                "has_savings_account": True,
                "pays_income_tax": False,
            },
            "preferred_language": "kn"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        results = res.json()["results"]
        res_map = {r["scheme_id"]: r for r in results}

        # 1. PM-Vishwakarma must be ELIGIBLE
        vish = res_map["pm-vishwakarma"]
        assert vish["status"] == EligibilityStatusEnum.ELIGIBLE
        assert vish["ministry"] == "Ministry of Micro, Small and Medium Enterprises"
        assert len(vish["documents"]) >= 2
        assert len(vish["application_procedure"]) >= 2

        # 2. PM-Mudra must be ELIGIBLE
        mudra = res_map["pm-mudra"]
        assert mudra["status"] == EligibilityStatusEnum.ELIGIBLE
        assert mudra["ministry"] == "Ministry of Finance"

        # 3. Ineligible schemes
        assert res_map["pm-kisan"]["status"] == EligibilityStatusEnum.NOT_ELIGIBLE
        assert res_map["nsap-ignoaps"]["status"] == EligibilityStatusEnum.NOT_ELIGIBLE


@pytest.mark.asyncio
async def test_all_9_dimensions_present_in_results():
    """
    Verifies that every evaluated scheme result contains all 9 required dimensions:
    1. Scheme name and ministry
    2. Eligibility status
    3. Why matched/did not match (conditions_satisfied / conditions_failed)
    4. Benefits
    5. Missing info (missing_information)
    6. Required documents (documents)
    7. Application steps (application_procedure)
    8. Official source link (official_url)
    9. Last verified date (last_verified_date)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "citizen_attributes": {
                "age": 30,
                "gender": "Female",
            },
            "preferred_language": "en"
        }
        res = await client.post("/api/v1/eligibility/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        results = data["results"]

        for item in results:
            sid = item["scheme_id"]
            # 1. Name and ministry
            assert item["scheme_name"]["en"], f"Missing scheme_name for {sid}"
            assert item["ministry"], f"Missing ministry for {sid}"
            # 2. Status
            assert item["status"] in ["ELIGIBLE", "POSSIBLY_ELIGIBLE", "NOT_ELIGIBLE"]
            # 3. Why matched/failed
            assert "conditions_satisfied" in item
            assert "conditions_failed" in item
            # 4. Benefits
            assert item["benefits"] is not None and "en" in item["benefits"], f"Missing benefits for {sid}"
            # 5. Missing info
            assert "missing_information" in item
            # 6. Required documents
            assert isinstance(item["documents"], list) and len(item["documents"]) > 0, f"Missing documents for {sid}"
            # 7. Application steps
            assert isinstance(item["application_procedure"], list) and len(item["application_procedure"]) > 0, f"Missing steps for {sid}"
            # 8. Official source link
            assert item["official_url"].startswith("http"), f"Invalid official_url for {sid}"
            # 9. Last verified date
            assert item["last_verified_date"], f"Missing last_verified_date for {sid}"
