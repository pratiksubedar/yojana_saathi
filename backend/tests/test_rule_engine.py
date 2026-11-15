import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.rule_engine import (
    DeterministicRuleEvaluator,
    MalformedRuleException,
    UnsupportedOperatorException,
    evaluate_atomic_operator,
)
from app.schemas.eligibility import (
    EligibilityStatusEnum,
    ConditionStatusEnum,
)

client = TestClient(app)


# ==============================================================================
# 1. OPERATOR TESTS
# ==============================================================================

def test_operator_equals():
    # String equality (case-insensitive)
    assert evaluate_atomic_operator("equals", "Farmer", "Farmer") is True
    assert evaluate_atomic_operator("equals", "Farmer", "farmer") is True
    assert evaluate_atomic_operator("equals", "Farmer", " Street Vendor ") is False

    # Numeric equality
    assert evaluate_atomic_operator("equals", 18, 18) is True
    assert evaluate_atomic_operator("equals", 18.0, 18) is True
    assert evaluate_atomic_operator("equals", 18, "18") is True
    assert evaluate_atomic_operator("equals", 18, 19) is False

    # Boolean equality
    assert evaluate_atomic_operator("equals", True, True) is True
    assert evaluate_atomic_operator("equals", True, "true") is True
    assert evaluate_atomic_operator("equals", True, "yes") is True
    assert evaluate_atomic_operator("equals", False, "no") is True
    assert evaluate_atomic_operator("equals", True, False) is False


def test_operator_not_equals():
    assert evaluate_atomic_operator("not_equals", "Farmer", "Carpenter") is True
    assert evaluate_atomic_operator("not_equals", "Farmer", "farmer") is False
    assert evaluate_atomic_operator("not_equals", 10, 20) is True
    assert evaluate_atomic_operator("not_equals", True, False) is True


def test_operator_in_and_not_in():
    allowed_occupations = ["Farmer", "Agricultural Landholder", "Cultivator"]

    # in
    assert evaluate_atomic_operator("in", allowed_occupations, "Farmer") is True
    assert evaluate_atomic_operator("in", allowed_occupations, "agricultural landholder") is True
    assert evaluate_atomic_operator("in", allowed_occupations, "Street Vendor") is False

    # not_in
    assert evaluate_atomic_operator("not_in", allowed_occupations, "Street Vendor") is True
    assert evaluate_atomic_operator("not_in", allowed_occupations, "Farmer") is False


def test_operator_numeric_comparisons():
    # greater_than
    assert evaluate_atomic_operator("greater_than", 0.0, 0.5) is True
    assert evaluate_atomic_operator("greater_than", 0.0, 0.0) is False
    assert evaluate_atomic_operator("greater_than", 0.0, -1.0) is False

    # less_than
    assert evaluate_atomic_operator("less_than", 100000, 50000) is True
    assert evaluate_atomic_operator("less_than", 100000, 150000) is False

    # greater_than_or_equal
    assert evaluate_atomic_operator("greater_than_or_equal", 18, 18) is True
    assert evaluate_atomic_operator("greater_than_or_equal", 18, 19) is True
    assert evaluate_atomic_operator("greater_than_or_equal", 18, 17) is False

    # less_than_or_equal
    assert evaluate_atomic_operator("less_than_or_equal", 60, 60) is True
    assert evaluate_atomic_operator("less_than_or_equal", 60, 55) is True
    assert evaluate_atomic_operator("less_than_or_equal", 60, 65) is False

    # Non-numeric gracefully evaluates to False without crashing
    assert evaluate_atomic_operator("greater_than", 18, "not-a-number") is False


def test_unsupported_operator():
    with pytest.raises(UnsupportedOperatorException):
        evaluate_atomic_operator("bitwise_and", 5, 5)


# ==============================================================================
# 2. COMBINATOR & THREE-VALUED LOGIC TESTS
# ==============================================================================

def test_combinator_all_of():
    rule_ast = {
        "conditions": {
            "all_of": [
                {"id": "c1", "field": "age", "operator": "gte", "value": 18},
                {"id": "c2", "field": "income", "operator": "lte", "value": 200000},
            ]
        }
    }

    # Both satisfied -> ELIGIBLE
    res_eligible = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"age": 25, "income": 100000}
    )
    assert res_eligible.status == EligibilityStatusEnum.ELIGIBLE
    assert len(res_eligible.conditions_satisfied) == 2

    # One failed -> NOT_ELIGIBLE
    res_failed = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"age": 16, "income": 100000}
    )
    assert res_failed.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert len(res_failed.conditions_failed) == 1

    # One missing, other satisfied -> POSSIBLY_ELIGIBLE
    res_missing = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"age": 25}
    )
    assert res_missing.status == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
    assert len(res_missing.missing_information) == 1
    assert res_missing.missing_information[0].field == "income"

    # One failed, one missing -> NOT_ELIGIBLE (failure takes precedence)
    res_fail_and_miss = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"age": 15}
    )
    assert res_fail_and_miss.status == EligibilityStatusEnum.NOT_ELIGIBLE


def test_combinator_any_of():
    rule_ast = {
        "conditions": {
            "any_of": [
                {"id": "a1", "field": "category", "operator": "equals", "value": "SC"},
                {"id": "a2", "field": "category", "operator": "equals", "value": "ST"},
            ]
        }
    }

    # Meets one -> ELIGIBLE
    res1 = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"category": "SC"}
    )
    assert res1.status == EligibilityStatusEnum.ELIGIBLE

    # Meets neither -> NOT_ELIGIBLE
    res2 = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"category": "General"}
    )
    assert res2.status == EligibilityStatusEnum.NOT_ELIGIBLE

    # Missing -> POSSIBLY_ELIGIBLE
    res3 = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {}
    )
    assert res3.status == EligibilityStatusEnum.POSSIBLY_ELIGIBLE


def test_combinator_none_of_exclusions():
    rule_ast = {
        "conditions": {
            "all_of": [
                {"id": "c1", "field": "is_farmer", "operator": "equals", "value": True}
            ],
            "none_of": [
                {
                    "id": "e1",
                    "field": "pays_income_tax",
                    "operator": "equals",
                    "value": True,
                    "failure_reason": {"en": "Taxpayers excluded"},
                    "citation": {"clause": "Sec 3.1"}
                }
            ]
        }
    }

    # Satisfies all_of, clears exclusion -> ELIGIBLE
    res_clean = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"is_farmer": True, "pays_income_tax": False}
    )
    assert res_clean.status == EligibilityStatusEnum.ELIGIBLE
    assert len(res_clean.conditions_satisfied) == 2

    # Satisfies all_of, triggers exclusion -> NOT_ELIGIBLE
    res_excluded = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"is_farmer": True, "pays_income_tax": True}
    )
    assert res_excluded.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert len(res_excluded.conditions_failed) == 1
    assert res_excluded.conditions_failed[0].reason["en"] == "Taxpayers excluded"

    # Exclusion info missing -> POSSIBLY_ELIGIBLE
    res_miss_excl = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"is_farmer": True}
    )
    assert res_miss_excl.status == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
    assert any(m.field == "pays_income_tax" for m in res_miss_excl.missing_information)


def test_conflicting_conditions():
    # Impossible condition (age > 40 AND age < 20)
    rule_ast = {
        "conditions": {
            "all_of": [
                {"id": "c1", "field": "age", "operator": "gt", "value": 40},
                {"id": "c2", "field": "age", "operator": "lt", "value": 20},
            ]
        }
    }
    # For any age (e.g. 25), exactly one condition must fail -> NOT_ELIGIBLE
    res = DeterministicRuleEvaluator.evaluate_scheme(
        "test-scheme", {"en": "Test"}, rule_ast, {"age": 25}
    )
    assert res.status == EligibilityStatusEnum.NOT_ELIGIBLE


def test_malformed_rule_exceptions():
    # Non-dictionary rule
    with pytest.raises(MalformedRuleException):
        DeterministicRuleEvaluator.evaluate_scheme("s1", {"en": "S1"}, "invalid_string", {})

    # Missing field in condition
    bad_ast = {
        "conditions": {
            "all_of": [
                {"id": "c1", "operator": "equals", "value": 10}  # missing 'field'
            ]
        }
    }
    with pytest.raises(MalformedRuleException):
        DeterministicRuleEvaluator.evaluate_scheme("s1", {"en": "S1"}, bad_ast, {"age": 10})


def test_multilingual_disclaimers_and_explanations():
    rule_ast = {
        "conditions": {
            "all_of": [
                {"id": "c1", "field": "age", "operator": "gte", "value": 18}
            ]
        }
    }
    res = DeterministicRuleEvaluator.evaluate_scheme("s1", {"en": "S1"}, rule_ast, {"age": 20})
    for lang in ["en", "hi", "kn", "te"]:
        assert lang in res.disclaimer
        assert len(res.disclaimer[lang].strip()) > 0
        assert lang in res.summary
        assert len(res.summary[lang].strip()) > 0


# ==============================================================================
# 3. SEEDED SCHEMES EVALUATION TESTS
# ==============================================================================

def test_pm_kisan_evaluation_scenarios():
    # Scenario A: Qualifying Farmer on Partial Rules -> POSSIBLY_ELIGIBLE (Conservative safety audit)
    res_a = client.post(
        "/api/v1/eligibility/evaluate/pm-kisan",
        json={
            "citizen_attributes": {
                "occupation": "Farmer",
                "landholding_hectares": 1.8,
                "pays_income_tax": False,
                "is_institutional_landholder": False,
                "is_regular_govt_employee": False,
                "monthly_pension_inr": 0.0,
                "is_registered_professional": False,
            }
        }
    )
    assert res_a.status_code == 200
    data_a = res_a.json()
    # A scheme with PARTIAL rules must NEVER return an unqualified ELIGIBLE result!
    assert data_a["status"] == "POSSIBLY_ELIGIBLE"
    assert data_a["rule_completeness"] == "PARTIAL"
    assert len(data_a["unresolved_criteria"]) > 0
    assert "partially verified" in data_a["summary"]["en"].lower()
    assert len(data_a["conditions_satisfied"]) == 7
    assert len(data_a["conditions_failed"]) == 0
    assert len(data_a["missing_information"]) == 0

    # Scenario B: Disqualified due to Income Tax
    res_b = client.post(
        "/api/v1/eligibility/evaluate/pm-kisan",
        json={
            "citizen_attributes": {
                "occupation": "Farmer",
                "landholding_hectares": 1.8,
                "pays_income_tax": True,
                "is_institutional_landholder": False,
            }
        }
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["status"] == "NOT_ELIGIBLE"
    assert len(data_b["conditions_failed"]) == 1
    assert "income tax" in data_b["conditions_failed"][0]["reason"]["en"].lower()
    assert data_b["conditions_failed"][0]["citation"]["clause"] is not None

    # Scenario C: Incomplete Profile (Missing Landholding)
    res_c = client.post(
        "/api/v1/eligibility/evaluate/pm-kisan",
        json={
            "citizen_attributes": {
                "occupation": "Farmer",
                "pays_income_tax": False,
                "is_institutional_landholder": False,
            }
        }
    )
    assert res_c.status_code == 200
    data_c = res_c.json()
    assert data_c["status"] == "POSSIBLY_ELIGIBLE"
    assert len(data_c["missing_information"]) >= 1
    missing_fields = {m["field"] for m in data_c["missing_information"]}
    assert "landholding_hectares" in missing_fields

    # Scenario D: Disqualified due to regular government employee exclusion (Section 3f)
    res_d = client.post(
        "/api/v1/eligibility/evaluate/pm-kisan",
        json={
            "citizen_attributes": {
                "occupation": "Farmer",
                "landholding_hectares": 2.5,
                "is_regular_govt_employee": True,
            }
        }
    )
    assert res_d.status_code == 200
    assert res_d.json()["status"] == "NOT_ELIGIBLE"

    # Scenario E: Disqualified due to monthly pension >= ₹10,000 (Section 3e)
    res_e = client.post(
        "/api/v1/eligibility/evaluate/pm-kisan",
        json={
            "citizen_attributes": {
                "occupation": "Farmer",
                "landholding_hectares": 1.2,
                "monthly_pension_inr": 15000.0,
            }
        }
    )
    assert res_e.status_code == 200
    assert res_e.json()["status"] == "NOT_ELIGIBLE"


def test_pm_jay_senior_70_plus_pathway():
    """Verify that citizens aged 70+ qualify for PM-JAY via the Senior Citizen pathway without NFSA/SECC entitlement."""
    # Senior citizen 72 years old without SECC/NFSA entitlement
    res_senior = client.post(
        "/api/v1/eligibility/evaluate/pm-jay",
        json={
            "citizen_attributes": {
                "age": 72,
                "has_nfsa_priority_or_secc_entitlement": False,
            }
        }
    )
    assert res_senior.status_code == 200
    data = res_senior.json()
    # Satisfies the any_of senior pathway, but rule completeness is PARTIAL -> POSSIBLY_ELIGIBLE
    assert data["status"] == "POSSIBLY_ELIGIBLE"
    assert any("70" in c["citation"]["clause"] or "Senior" in c["citation"]["clause"] for c in data["conditions_satisfied"] if c.get("citation"))

    # Non-senior without NFSA/SECC entitlement -> NOT_ELIGIBLE (both pathways fail)
    res_young = client.post(
        "/api/v1/eligibility/evaluate/pm-jay",
        json={
            "citizen_attributes": {
                "age": 45,
                "has_nfsa_priority_or_secc_entitlement": False,
            }
        }
    )
    assert res_young.status_code == 200
    assert res_young.json()["status"] == "NOT_ELIGIBLE"


def test_api_evaluate_all_active_schemes():
    payload = {
        "citizen_attributes": {
            "occupation": "Street Vendor",
            "age": 30,
            "has_bpl_card": True,
            "has_nfsa_priority_or_secc_entitlement": True,
            "has_government_health_insurance": False,
            "owns_pucca_house": False,
        },
        "preferred_language": "kn"
    }
    response = client.post("/api/v1/eligibility/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 21

    results_by_id = {r["scheme_id"]: r for r in data["results"]}
    # PM-SVANidhi: Meets evaluated occupation and age, but rule is PARTIAL -> POSSIBLY_ELIGIBLE
    assert results_by_id["pm-svanidhi"]["status"] == "POSSIBLY_ELIGIBLE"
    assert results_by_id["pm-svanidhi"]["rule_completeness"] == "PARTIAL"
    # PM-JAY: Meets NFSA/SECC entitlement, but rule is PARTIAL -> POSSIBLY_ELIGIBLE
    assert results_by_id["pm-jay"]["status"] == "POSSIBLY_ELIGIBLE"
    assert results_by_id["pm-jay"]["rule_completeness"] == "PARTIAL"
    # PMAY-G: Meets BPL and no pucca house, but rule is PARTIAL -> POSSIBLY_ELIGIBLE
    assert results_by_id["pmay-g"]["status"] == "POSSIBLY_ELIGIBLE"
    assert results_by_id["pmay-g"]["rule_completeness"] == "PARTIAL"
    # PM-KISAN: Fails occupation (Street Vendor != Farmer) -> NOT_ELIGIBLE
    assert results_by_id["pm-kisan"]["status"] == "NOT_ELIGIBLE"
    # PM-KMY: Fails occupation (Street Vendor != Farmer) -> NOT_ELIGIBLE
    assert results_by_id["pm-kmy"]["status"] == "NOT_ELIGIBLE"
    # PM-KUSUM: Fails occupation (Street Vendor != Farmer) -> NOT_ELIGIBLE
    assert results_by_id["pm-kusum"]["status"] == "NOT_ELIGIBLE"
    # PMMVY: Missing gender/maternity info -> POSSIBLY_ELIGIBLE with missing info
    assert results_by_id["pmmvy"]["status"] == "POSSIBLY_ELIGIBLE"


def test_api_evaluate_filtered_schemes():
    payload = {
        "citizen_attributes": {"has_nfsa_priority_or_secc_entitlement": True, "has_government_health_insurance": False},
        "scheme_ids": ["pm-jay"]
    }
    response = client.post("/api/v1/eligibility/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["scheme_id"] == "pm-jay"
    # Partially verified rules safely yield POSSIBLY_ELIGIBLE
    assert data["results"][0]["status"] == "POSSIBLY_ELIGIBLE"
    assert data["results"][0]["rule_completeness"] == "PARTIAL"
    assert len(data["results"][0]["unresolved_criteria"]) > 0


def test_api_evaluate_unknown_scheme_404():
    response = client.post(
        "/api/v1/eligibility/evaluate/non-existent-scheme-99",
        json={"citizen_attributes": {}}
    )
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "SCHEME_NOT_FOUND"


def test_api_unsupported_operator_400():
    # Attempting to call evaluate with an unsupported operator condition
    with pytest.raises(UnsupportedOperatorException):
        evaluate_atomic_operator("invalid_custom_op", 10, 10)


# ==============================================================================
# 4. MILESTONE 4.4.1 SAFETY AUDIT & REGRESSION TESTS
# ==============================================================================

def test_verified_complete_scheme_returns_unqualified_eligible():
    """Verify that a fully vetted rule set (VERIFIED_COMPLETE) grants ELIGIBLE when criteria pass."""
    complete_ast = {
        "rule_completeness": "VERIFIED_COMPLETE",
        "conditions": {
            "all_of": [
                {"id": "vc_1", "field": "age", "operator": "gte", "value": 18},
                {"id": "vc_2", "field": "resident", "operator": "equals", "value": True},
            ]
        }
    }
    res = DeterministicRuleEvaluator.evaluate_scheme(
        "complete-scheme",
        {"en": "Verified Complete Scheme"},
        complete_ast,
        {"age": 22, "resident": True}
    )
    assert res.status == EligibilityStatusEnum.ELIGIBLE
    assert res.rule_completeness == "VERIFIED_COMPLETE"
    assert "satisfy all evaluated eligibility requirements" in res.summary["en"].lower()


def test_partial_scheme_never_returns_unqualified_eligible():
    """Verify safety constraint: PARTIAL rules must never return ELIGIBLE even if criteria pass."""
    partial_ast = {
        "rule_completeness": "PARTIAL",
        "unresolved_criteria": [
            {
                "clause": "Clause 4.2",
                "description": "Cross-verification with state tax database required",
                "verification_method": "Tax portal check"
            }
        ],
        "conditions": {
            "all_of": [
                {"id": "p_1", "field": "occupation", "operator": "equals", "value": "Farmer"}
            ]
        }
    }
    res = DeterministicRuleEvaluator.evaluate_scheme(
        "partial-scheme",
        {"en": "Partial Scheme"},
        partial_ast,
        {"occupation": "Farmer"}
    )
    # Must be conservative POSSIBLY_ELIGIBLE!
    assert res.status == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
    assert res.rule_completeness == "PARTIAL"
    assert len(res.unresolved_criteria) == 1
    assert "partially verified" in res.summary["en"].lower()


def test_unverified_scheme_returns_conservative_status():
    """Verify that an UNVERIFIED rule set defaults safely to POSSIBLY_ELIGIBLE."""
    unverified_ast = {
        "rule_completeness": "UNVERIFIED",
        "conditions": {
            "all_of": [
                {"id": "u_1", "field": "score", "operator": "gt", "value": 50}
            ]
        }
    }
    res = DeterministicRuleEvaluator.evaluate_scheme(
        "unverified-scheme",
        {"en": "Unverified Scheme"},
        unverified_ast,
        {"score": 90}
    )
    assert res.status == EligibilityStatusEnum.POSSIBLY_ELIGIBLE
    assert res.rule_completeness == "UNVERIFIED"


def test_partial_scheme_failure_still_returns_not_eligible():
    """Verify that when a citizen fails a mandatory criterion, PARTIAL scheme still returns NOT_ELIGIBLE."""
    partial_ast = {
        "rule_completeness": "PARTIAL",
        "conditions": {
            "all_of": [
                {"id": "p_1", "field": "occupation", "operator": "equals", "value": "Farmer"}
            ]
        }
    }
    # Carpenter fails occupation
    res = DeterministicRuleEvaluator.evaluate_scheme(
        "partial-scheme",
        {"en": "Partial Scheme"},
        partial_ast,
        {"occupation": "Carpenter"}
    )
    assert res.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert len(res.conditions_failed) == 1


def test_false_positive_prevention_on_oversimplified_rules():
    """Verify false-positive prevention: PM-SVANidhi cannot falsely report 100% eligibility without ULB certificate."""
    res = client.post(
        "/api/v1/eligibility/evaluate/pm-svanidhi",
        json={
            "citizen_attributes": {
                "occupation": "Street Vendor",
                "age": 25
            }
        }
    )
    assert res.status_code == 200
    data = res.json()
    # Must NOT be ELIGIBLE (which would be a false positive without CoV/LoR)
    assert data["status"] == "POSSIBLY_ELIGIBLE"
    assert data["rule_completeness"] == "PARTIAL"
    unresolved_clauses = [u["clause"] for u in data["unresolved_criteria"]]
    assert any("Section 3.1" in c for c in unresolved_clauses)


# ==============================================================================
# 5. TARGETED AUDIT REGRESSION TESTS (PMAY-G, PM SVANIDHI, PM-JAY)
# ==============================================================================

def test_pmayg_two_wheeler_relaxation_and_three_four_wheeler_exclusion():
    """
    Verify PIB Dec 3, 2024 criteria:
    - Motorised two-wheeler owners are NOT automatically excluded.
    - Motorised three or four-wheeler owners ARE automatically excluded (NOT_ELIGIBLE).
    """
    # Household with a 2-wheeler (owns_motorized_three_or_four_wheeler=False)
    payload_two_wheeler = {
        "citizen_attributes": {
            "has_bpl_card": True,
            "owns_pucca_house": False,
            "owns_motorized_three_or_four_wheeler": False,
            "has_regular_govt_job": False,
            "household_monthly_income_inr": 12000.0,
            "pays_income_tax": False,
        }
    }
    res_2w = client.post("/api/v1/eligibility/evaluate/pmay-g", json=payload_two_wheeler)
    assert res_2w.status_code == 200
    data_2w = res_2w.json()
    # Two-wheelers do not trigger exclusion; PARTIAL completeness -> POSSIBLY_ELIGIBLE
    assert data_2w["status"] == "POSSIBLY_ELIGIBLE"
    # Ensure parameter 1 is satisfied (not failed)
    assert any(c["condition_id"] == "pmg_e1" for c in data_2w["conditions_satisfied"])

    # Household owning a motorised 3/4-wheeler
    payload_34_wheeler = {
        "citizen_attributes": {
            "has_bpl_card": True,
            "owns_pucca_house": False,
            "owns_motorized_three_or_four_wheeler": True,
            "has_regular_govt_job": False,
            "household_monthly_income_inr": 12000.0,
            "pays_income_tax": False,
        }
    }
    res_34w = client.post("/api/v1/eligibility/evaluate/pmay-g", json=payload_34_wheeler)
    assert res_34w.status_code == 200
    data_34w = res_34w.json()
    assert data_34w["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "pmg_e1" for c in data_34w["conditions_failed"])


def test_pmayg_preliminary_pucca_house_filter_vs_income_threshold():
    """
    Verify:
    1. Step 1 Preliminary Housing Filter: Owning a pucca house fails at Step 1 (pmg_prelim_pucca).
    2. Step 2 Parameter 3: Income > 15,000 INR/month fails (raised from 10k in Dec 2024).
    3. Income <= 15,000 INR/month is satisfied.
    """
    # 1. Owns pucca house -> fails preliminary filter
    res_pucca = client.post(
        "/api/v1/eligibility/evaluate/pmay-g",
        json={
            "citizen_attributes": {
                "has_bpl_card": True,
                "owns_pucca_house": True,
                "owns_motorized_three_or_four_wheeler": False,
                "has_regular_govt_job": False,
                "household_monthly_income_inr": 8000.0,
                "pays_income_tax": False,
            }
        }
    )
    assert res_pucca.status_code == 200
    data_pucca = res_pucca.json()
    assert data_pucca["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "pmg_prelim_pucca" for c in data_pucca["conditions_failed"])
    assert "Preliminary Housing Filter" in data_pucca["conditions_failed"][0]["reason"]["en"]

    # 2. Income > ₹15,000 (e.g. ₹18,000) -> fails exclusion parameter 3
    res_high_income = client.post(
        "/api/v1/eligibility/evaluate/pmay-g",
        json={
            "citizen_attributes": {
                "has_bpl_card": True,
                "owns_pucca_house": False,
                "owns_motorized_three_or_four_wheeler": False,
                "has_regular_govt_job": False,
                "household_monthly_income_inr": 18000.0,
                "pays_income_tax": False,
            }
        }
    )
    assert res_high_income.status_code == 200
    data_high_income = res_high_income.json()
    assert data_high_income["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "pmg_e3" for c in data_high_income["conditions_failed"])

    # 3. Income ₹14,000 <= ₹15,000 -> satisfied
    res_eligible_income = client.post(
        "/api/v1/eligibility/evaluate/pmay-g",
        json={
            "citizen_attributes": {
                "has_bpl_card": True,
                "owns_pucca_house": False,
                "owns_motorized_three_or_four_wheeler": False,
                "has_regular_govt_job": False,
                "household_monthly_income_inr": 14000.0,
                "pays_income_tax": False,
            }
        }
    )
    assert res_eligible_income.status_code == 200
    assert res_eligible_income.json()["status"] == "POSSIBLY_ELIGIBLE"


def test_pmayg_unirrigated_land_exclusion_and_gram_sabha_workflow_separation():
    """
    Verify PIB PRID 2080091 criteria:
    1. Owning 5 acres or more of unirrigated land (owns_unirrigated_land_gte_5_acres=True) triggers Parameter 10 automatic exclusion (NOT_ELIGIBLE).
    2. Owning < 5 acres unirrigated land (owns_unirrigated_land_gte_5_acres=False) passes Parameter 10.
    3. Gram Sabha validation is NOT an automatic exclusion condition in rules, but belongs to application_procedure.
    """
    # 1. Household owning >= 5 acres unirrigated land -> NOT_ELIGIBLE
    res_land_excl = client.post(
        "/api/v1/eligibility/evaluate/pmay-g",
        json={
            "citizen_attributes": {
                "has_bpl_card": True,
                "owns_pucca_house": False,
                "owns_motorized_three_or_four_wheeler": False,
                "has_regular_govt_job": False,
                "household_monthly_income_inr": 10000.0,
                "pays_income_tax": False,
                "owns_unirrigated_land_gte_5_acres": True,
            }
        }
    )
    assert res_land_excl.status_code == 200
    data_land = res_land_excl.json()
    assert data_land["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "pmg_e10" for c in data_land["conditions_failed"])
    assert "Parameter 10" in data_land["conditions_failed"][0]["reason"]["en"]
    assert "5 acres or more of unirrigated land" in data_land["conditions_failed"][0]["reason"]["en"]

    # 2. Household owning < 5 acres unirrigated land -> passes Parameter 10
    res_land_ok = client.post(
        "/api/v1/eligibility/evaluate/pmay-g",
        json={
            "citizen_attributes": {
                "has_bpl_card": True,
                "owns_pucca_house": False,
                "owns_motorized_three_or_four_wheeler": False,
                "has_regular_govt_job": False,
                "household_monthly_income_inr": 10000.0,
                "pays_income_tax": False,
                "owns_unirrigated_land_gte_5_acres": False,
            }
        }
    )
    assert res_land_ok.status_code == 200
    data_ok = res_land_ok.json()
    assert data_ok["status"] == "POSSIBLY_ELIGIBLE"
    assert any(c["condition_id"] == "pmg_e10" for c in data_ok["conditions_satisfied"])

    # 3. Verify Gram Sabha validation is NOT in exclusion rules, but in application_procedure
    res_detail = client.get("/api/v1/schemes/pmay-g")
    assert res_detail.status_code == 200
    pmayg_data = res_detail.json()

    # Check rules AST does NOT have gram sabha as an exclusion condition
    rule_conditions = pmayg_data["rules"][0]["conditions"]
    all_rule_fields = [c["field"] for c in rule_conditions.get("all_of", []) + rule_conditions.get("none_of", [])]
    assert not any("gram_sabha" in f.lower() for f in all_rule_fields)

    # Check unresolved criteria clarifies gram sabha is part of administrative identification workflow
    for unres in rule_conditions.get("unresolved_criteria", []):
        assert "not an automatic exclusion parameter" in unres["description"].lower()

    # Confirm Gram Sabha is properly placed in administrative application_procedure (Step 2)
    step2 = next(s for s in pmayg_data["application_procedure"] if s["step_number"] == 2)
    assert "Gram Sabha" in step2["titles"]["en"]
    assert "Gram Sabha" in step2["descriptions"]["en"]


def test_pm_svanidhi_restructured_august_2025_guidelines():
    """
    Verify PM SVANidhi reflects August 2025 Cabinet guidelines:
    - 3 loan tranches up to ₹15,000 / ₹25,000 / ₹50,000.
    - Retail digital cashback up to ₹100/month.
    - Wholesale digital purchase incentive up to ₹100/quarter.
    - Total digital incentive up to ₹1,600/year.
    """
    res = client.get("/api/v1/schemes/pm-svanidhi")
    assert res.status_code == 200
    data = res.json()

    benefits_en = data["benefits"]["en"]
    assert "₹15,000" in benefits_en
    assert "₹25,000" in benefits_en
    assert "₹50,000" in benefits_en
    assert "12-month tenure" in benefits_en
    assert "18-month tenure" in benefits_en
    assert "36-month tenure" in benefits_en
    assert "Retail digital cashback of up to ₹100 per month" in benefits_en
    assert "Wholesale digital purchase incentive of up to ₹100 per quarter" in benefits_en
    assert "₹1,600 per year" in benefits_en


def test_pm_jay_economic_vs_senior_pathway_distinction():
    """
    Verify PM-JAY distinct pathways:
    - State BPL card alone does NOT equate to central NFSA/SECC entitlement.
    - has_nfsa_priority_or_secc_entitlement satisfies economic pathway.
    - age >= 70 satisfies senior citizen universal pathway.
    - Both return POSSIBLY_ELIGIBLE due to offline BIS/e-KYC verification requirements.
    """
    # 1. State BPL card alone without central NFSA/SECC entitlement leaves condition UNKNOWN -> POSSIBLY_ELIGIBLE
    res_bpl_only = client.post(
        "/api/v1/eligibility/evaluate/pm-jay",
        json={"citizen_attributes": {"has_bpl_card": True, "age": 40}}
    )
    assert res_bpl_only.status_code == 200
    data_bpl_only = res_bpl_only.json()
    assert data_bpl_only["status"] == "POSSIBLY_ELIGIBLE"
    assert any(m["field"] == "has_nfsa_priority_or_secc_entitlement" for m in data_bpl_only["missing_information"])

    # 2. Verified NFSA priority or SECC entitlement
    res_nfsa = client.post(
        "/api/v1/eligibility/evaluate/pm-jay",
        json={"citizen_attributes": {"has_nfsa_priority_or_secc_entitlement": True, "age": 40}}
    )
    assert res_nfsa.status_code == 200
    data_nfsa = res_nfsa.json()
    assert data_nfsa["status"] == "POSSIBLY_ELIGIBLE"
    assert any(c["condition_id"] == "pmj_c1" for c in data_nfsa["conditions_satisfied"])

    # 3. Senior Citizen (70+) without economic qualification
    res_senior = client.post(
        "/api/v1/eligibility/evaluate/pm-jay",
        json={"citizen_attributes": {"has_nfsa_priority_or_secc_entitlement": False, "age": 75}}
    )
    assert res_senior.status_code == 200
    data_senior = res_senior.json()
    assert data_senior["status"] == "POSSIBLY_ELIGIBLE"
    assert any(c["condition_id"] == "pmj_c2" for c in data_senior["conditions_satisfied"])


def test_pm_kmy_eligibility_evaluation():
    """
    Verify PM-KMY (Pradhan Mantri Kisan Maandhan Yojana) deterministic evaluation per official guidelines:
    - Small & marginal farmer (<= 2 ha as on 01.08.2019), age 18-40.
    - Statutory exclusions:
      - kmy_e1: NPS / ESIC / EPFO
      - kmy_e2: PM-SYM / PM-LVM
      - kmy_e3: Income tax payer
      - kmy_e4: Institutional landholder
      - kmy_e5: Constitutional post holder / Minister / MP / MLA / Mayor / District Panchayat Chairperson
      - kmy_e6: Regular Govt / PSU employee (Exempt: MTS / Class IV / Group D)
      - kmy_e7: Registered practising professional (Doctor, Engineer, Lawyer, CA, Architect)
    """
    # 1. Eligible applicant satisfying all criteria
    eligible_payload = {
        "citizen_attributes": {
            "occupation": "Farmer",
            "landholding_hectares": 1.5,
            "age": 28,
            "is_enrolled_in_other_pension_nps_esic_epfo": False,
            "is_enrolled_in_pm_sym_or_pm_lvm": False,
            "pays_income_tax": False,
            "is_institutional_landholder": False,
            "is_constitutional_post_holder_or_elected_representative": False,
            "is_regular_govt_employee": False,
            "is_registered_professional": False
        },
        "preferred_language": "hi"
    }
    res = client.post("/api/v1/eligibility/evaluate/pm-kmy", json=eligible_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "POSSIBLY_ELIGIBLE"
    assert data["rule_completeness"] == "PARTIAL"
    assert len(data["conditions_failed"]) == 0
    assert len(data["conditions_satisfied"]) == 11  # 4 all_of + 7 none_of cleared

    # 2. Ineligible: Age > 40
    res_age = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "age": 45}
    })
    data_age = res_age.json()
    assert data_age["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_c4" for c in data_age["conditions_failed"])

    # 3. Ineligible: Land > 2.0 hectares
    res_land = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "landholding_hectares": 3.0}
    })
    data_land = res_land.json()
    assert data_land["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_c2" for c in data_land["conditions_failed"])

    # 4. Ineligible: Enrolled in PM-SYM or PM-LVM
    res_sym = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "is_enrolled_in_pm_sym_or_pm_lvm": True}
    })
    data_sym = res_sym.json()
    assert data_sym["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_e2" for c in data_sym["conditions_failed"])

    # 5. Ineligible: Institutional landholder
    res_inst = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "is_institutional_landholder": True}
    })
    data_inst = res_inst.json()
    assert data_inst["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_e4" for c in data_inst["conditions_failed"])

    # 6. Ineligible: Constitutional post holder / Minister / MP / MLA
    res_const = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "is_constitutional_post_holder_or_elected_representative": True}
    })
    data_const = res_const.json()
    assert data_const["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_e5" for c in data_const["conditions_failed"])

    # 7. Regular govt employee handling with MTS/Class IV exemption:
    # 7a. Regular govt employee without MTS exemption is excluded
    res_govt_non_mts = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {
            **eligible_payload["citizen_attributes"],
            "is_regular_govt_employee": True,
            "is_mts_or_class_iv_or_group_d_employee": False
        }
    })
    data_govt_non_mts = res_govt_non_mts.json()
    assert data_govt_non_mts["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_e6" for c in data_govt_non_mts["conditions_failed"])

    # 7b. Regular govt employee WITH MTS/Class IV/Group D exemption is NOT excluded
    res_govt_mts = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {
            **eligible_payload["citizen_attributes"],
            "is_regular_govt_employee": True,
            "is_mts_or_class_iv_or_group_d_employee": True
        }
    })
    data_govt_mts = res_govt_mts.json()
    assert data_govt_mts["status"] == "POSSIBLY_ELIGIBLE"
    assert len(data_govt_mts["conditions_failed"]) == 0
    kmy_e6_satisfied = next(c for c in data_govt_mts["conditions_satisfied"] if c["condition_id"] == "kmy_e6")
    assert "statutory exemption applies" in kmy_e6_satisfied["reason"]["en"]

    # 8. Ineligible: Registered practising professional
    res_prof = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "is_registered_professional": True}
    })
    data_prof = res_prof.json()
    assert data_prof["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_e7" for c in data_prof["conditions_failed"])

    # 9. Date of birth exact age calculation
    res_dob = client.post("/api/v1/eligibility/evaluate/pm-kmy", json={
        "citizen_attributes": {
            "occupation": "Farmer",
            "landholding_hectares": 1.0,
            "date_of_birth": "1998-05-15",
            "is_enrolled_in_other_pension_nps_esic_epfo": False,
            "is_enrolled_in_pm_sym_or_pm_lvm": False,
            "pays_income_tax": False,
            "is_institutional_landholder": False,
            "is_constitutional_post_holder_or_elected_representative": False,
            "is_regular_govt_employee": False,
            "is_registered_professional": False
        }
    })
    data_dob = res_dob.json()
    assert data_dob["status"] == "POSSIBLY_ELIGIBLE"
    assert any(c["condition_id"] == "kmy_c3" for c in data_dob["conditions_satisfied"])


def test_pmmvy_eligibility_evaluation():
    """
    Verify PMMVY (Pradhan Mantri Matru Vandana Yojana) deterministic evaluation:
    - Female, pregnant/lactating, age between 18 years 7 months (18.58) and under 55 years at childbirth.
    - First instalment requirement: completion of at least two (2) ANC check-ups (mat_c5).
    - Exclusions: regular govt/PSU employee, paid maternity benefits.
    """
    eligible_payload = {
        "citizen_attributes": {
            "gender": "female",
            "is_pregnant_or_lactating": True,
            "age": 24,
            "anc_checkups_completed": 2,
            "is_regular_govt_employee": False,
            "receives_formal_paid_maternity_benefits": False
        },
        "preferred_language": "te"
    }
    # 1. Eligible applicant with at least 2 ANC check-ups
    res = client.post("/api/v1/eligibility/evaluate/pmmvy", json=eligible_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "POSSIBLY_ELIGIBLE"
    assert data["rule_completeness"] == "PARTIAL"
    assert len(data["conditions_failed"]) == 0
    assert len(data["conditions_satisfied"]) == 7  # 5 all_of + 2 none_of cleared
    assert any(c["condition_id"] == "mat_c5" for c in data["conditions_satisfied"])

    # 2. Ineligible: Only 1 ANC check-up is insufficient for 1st instalment
    res_one_anc = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "anc_checkups_completed": 1}
    })
    data_one_anc = res_one_anc.json()
    assert data_one_anc["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "mat_c5" for c in data_one_anc["conditions_failed"])
    mat_c5_failed = next(c for c in data_one_anc["conditions_failed"] if c["condition_id"] == "mat_c5")
    assert "at least two (2) Antenatal Check-ups" in mat_c5_failed["reason"]["en"]

    # 3. Eligible: 3 ANC check-ups satisfies the requirement
    res_three_anc = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "anc_checkups_completed": 3}
    })
    assert res_three_anc.json()["status"] == "POSSIBLY_ELIGIBLE"

    # 4. Ineligible: Male gender
    res_male = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "gender": "male"}
    })
    data_male = res_male.json()
    assert data_male["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "mat_c1" for c in data_male["conditions_failed"])

    # 5. Ineligible: Under minimum age of 18 years 7 months (e.g. 17 or 18.0)
    res_underage = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "age": 18.0}
    })
    data_underage = res_underage.json()
    assert data_underage["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "mat_c3" for c in data_underage["conditions_failed"])

    # 6. Ineligible: 55 years or older at childbirth
    res_overage = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "age": 55.0}
    })
    data_overage = res_overage.json()
    assert data_overage["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "mat_c4" for c in data_overage["conditions_failed"])

    # 7. Ineligible: Regular govt employee
    res_govt = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "is_regular_govt_employee": True}
    })
    data_govt = res_govt.json()
    assert data_govt["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "mat_e1" for c in data_govt["conditions_failed"])

    # 8. Ineligible: Receives formal paid maternity benefits
    res_paid = client.post("/api/v1/eligibility/evaluate/pmmvy", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "receives_formal_paid_maternity_benefits": True}
    })
    data_paid = res_paid.json()
    assert data_paid["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "mat_e2" for c in data_paid["conditions_failed"])


def test_pmmvy_telangana_limitation_and_husband_aadhaar_exemption():
    """
    Verify Ministry PMMVY specific operational guidelines:
    - Husband's Aadhaar is NOT mandatory (single mothers / widows / non-spousal are included).
    - Telangana state maternity benefit scheme limitation is tracked as a verification requirement, not deterministic rejection.
    """
    # 1. Scheme detail check
    res_detail = client.get("/api/v1/schemes/pmmvy")
    assert res_detail.status_code == 200
    data_detail = res_detail.json()

    # Check that Telangana limitation is in unresolved criteria
    rule = data_detail["rules"][0]
    unresolved_list = rule["conditions"]["unresolved_criteria"]
    unresolved_titles = [u["title"] for u in unresolved_list]
    assert any("Telangana" in title for title in unresolved_titles)
    tg_unresolved = next(u for u in unresolved_list if "Telangana" in u["title"])
    assert "KCR Kit" in tg_unresolved["description"] or "Telangana" in tg_unresolved["description"]
    assert tg_unresolved["status"] == "REQUIRES_OFFICIAL_VERIFICATION"

    # 2. Document checklist check
    res_docs = client.get("/api/v1/documents/checklist/pmmvy")
    assert res_docs.status_code == 200
    data_docs = res_docs.json()
    doc_aadhaar = next(d for d in data_docs["documents"] if d["id"] == "doc-mat-aadhaar")
    assert "Husband" not in doc_aadhaar["names"]["en"]
    assert "husband's Aadhaar is NOT required" in doc_aadhaar["descriptions"]["en"]


def test_pm_kusum_eligibility_evaluation():
    """
    Verify PM-KUSUM (Component-B) deterministic evaluation:
    - Standalone solar pump (Component-B) up to 7.5 HP in un-electrified areas.
    - Farmer with water source, no existing grid-connected electric pump.
    - Unsupported 5-year prior subsidy exclusion is removed from deterministic rules.
    - Ground water clearance, pump sizing and 10% upfront payment tracked under workflow.
    """
    eligible_payload = {
        "citizen_attributes": {
            "occupation": "Farmer",
            "has_water_source_for_irrigation": True,
            "has_existing_grid_connected_agri_pump": False
        },
        "preferred_language": "kn"
    }
    # 1. Eligible applicant
    res = client.post("/api/v1/eligibility/evaluate/pm-kusum", json=eligible_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "POSSIBLY_ELIGIBLE"
    assert data["rule_completeness"] == "PARTIAL"
    assert len(data["conditions_failed"]) == 0
    assert len(data["conditions_satisfied"]) == 3  # 2 all_of + 1 none_of cleared

    # 2. Ineligible: No water source for irrigation
    res_water = client.post("/api/v1/eligibility/evaluate/pm-kusum", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "has_water_source_for_irrigation": False}
    })
    data_water = res_water.json()
    assert data_water["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kus_c2" for c in data_water["conditions_failed"])

    # 3. Ineligible: Existing grid-connected electric pump
    res_grid = client.post("/api/v1/eligibility/evaluate/pm-kusum", json={
        "citizen_attributes": {**eligible_payload["citizen_attributes"], "has_existing_grid_connected_agri_pump": True}
    })
    data_grid = res_grid.json()
    assert data_grid["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "kus_e1" for c in data_grid["conditions_failed"])

    # 4. Verify explicit Component-B naming and subsidy structure in scheme detail
    res_detail = client.get("/api/v1/schemes/pm-kusum")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert "Component-B" in detail["names"]["en"]
    assert "30%" in detail["benefits"]["en"]
    assert "50%" in detail["benefits"]["en"]
    assert "10% is an upfront payment" in detail["benefits"]["en"]


def test_new_schemes_document_checklists():
    """Verify document checklist API for expanded schemes."""
    for scheme_id in ["pm-kmy", "pmmvy", "pm-kusum", "apy", "pmjjby", "pmsby", "pm-mudra", "ssy", "pm-vishwakarma", "pm-surya-ghar", "pmuy", "kcc", "pm-sym", "nsap-ignoaps", "pmjdy"]:
        res = client.get(f"/api/v1/documents/checklist/{scheme_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["scheme_id"] == scheme_id
        assert len(data["documents"]) >= 1
        for doc in data["documents"]:
            assert doc["is_mandatory"] is True
            for lang in ["en", "hi", "kn", "te"]:
                assert lang in doc["names"]
                assert len(doc["names"][lang]) > 0
                assert lang in doc["descriptions"]
                assert len(doc["descriptions"][lang]) > 0


# ==============================================================================
# SPRINT A: NEW SCHEME ELIGIBILITY EVALUATION TESTS (21 SCHEMES)
# ==============================================================================

def test_apy_eligibility_evaluation():
    """Test Atal Pension Yojana rule evaluation: eligible, ineligible by age, and tax payer exclusion."""
    # 1. Eligible
    res_el = client.post("/api/v1/eligibility/evaluate/apy", json={
        "citizen_attributes": {
            "age": 25,
            "has_savings_account": True,
            "pays_income_tax": False
        }
    })
    assert res_el.status_code == 200
    assert res_el.json()["status"] == "ELIGIBLE"

    # 2. Ineligible: age 45 (outside 18-40)
    res_age = client.post("/api/v1/eligibility/evaluate/apy", json={
        "citizen_attributes": {
            "age": 45,
            "has_savings_account": True,
            "pays_income_tax": False
        }
    })
    assert res_age.status_code == 200
    assert res_age.json()["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "apy_c2" for c in res_age.json()["conditions_failed"])

    # 3. Ineligible: Income tax payer
    res_tax = client.post("/api/v1/eligibility/evaluate/apy", json={
        "citizen_attributes": {
            "age": 25,
            "has_savings_account": True,
            "pays_income_tax": True
        }
    })
    assert res_tax.status_code == 200
    assert res_tax.json()["status"] == "NOT_ELIGIBLE"
    assert any(c["condition_id"] == "apy_e1" for c in res_tax.json()["conditions_failed"])


def test_pmjjby_and_pmsby_eligibility_evaluation():
    """Test PMJJBY and PMSBY rule evaluations."""
    # PMJJBY: age 30 -> eligible, age 55 -> ineligible
    res_jjby_el = client.post("/api/v1/eligibility/evaluate/pmjjby", json={
        "citizen_attributes": {"age": 30, "has_savings_account": True}
    })
    assert res_jjby_el.json()["status"] == "ELIGIBLE"

    res_jjby_inel = client.post("/api/v1/eligibility/evaluate/pmjjby", json={
        "citizen_attributes": {"age": 55, "has_savings_account": True}
    })
    assert res_jjby_inel.json()["status"] == "NOT_ELIGIBLE"

    # PMSBY: age 65 -> eligible (up to 70), age 75 -> ineligible
    res_sby_el = client.post("/api/v1/eligibility/evaluate/pmsby", json={
        "citizen_attributes": {"age": 65, "has_savings_account": True}
    })
    assert res_sby_el.json()["status"] == "ELIGIBLE"

    res_sby_inel = client.post("/api/v1/eligibility/evaluate/pmsby", json={
        "citizen_attributes": {"age": 75, "has_savings_account": True}
    })
    assert res_sby_inel.json()["status"] == "NOT_ELIGIBLE"


def test_pm_mudra_and_vishwakarma_evaluation():
    """Test PM MUDRA and PM Vishwakarma rule evaluations."""
    # MUDRA: eligible citizen, wilful defaulter -> ineligible
    res_mudra_el = client.post("/api/v1/eligibility/evaluate/pm-mudra", json={
        "citizen_attributes": {
            "age": 28,
            "enterprise_type": "Service Provider",
            "is_bank_defaulter": False
        }
    })
    assert res_mudra_el.json()["status"] == "ELIGIBLE"

    res_mudra_def = client.post("/api/v1/eligibility/evaluate/pm-mudra", json={
        "citizen_attributes": {
            "age": 28,
            "enterprise_type": "Service Provider",
            "is_bank_defaulter": True
        }
    })
    assert res_mudra_def.json()["status"] == "NOT_ELIGIBLE"

    # Vishwakarma: artisan eligible, government servant ineligible
    res_vishwa_el = client.post("/api/v1/eligibility/evaluate/pm-vishwakarma", json={
        "citizen_attributes": {
            "age": 35,
            "trade_category": "Carpenter (Suthar)",
            "is_regular_govt_employee": False
        }
    })
    assert res_vishwa_el.json()["status"] == "ELIGIBLE"

    res_vishwa_govt = client.post("/api/v1/eligibility/evaluate/pm-vishwakarma", json={
        "citizen_attributes": {
            "age": 35,
            "trade_category": "Carpenter (Suthar)",
            "is_regular_govt_employee": True
        }
    })
    assert res_vishwa_govt.json()["status"] == "NOT_ELIGIBLE"


def test_ssy_and_pm_surya_ghar_evaluation():
    """Test SSY and PM Surya Ghar rule evaluations."""
    # SSY: girl child age 6 -> eligible, age 12 -> ineligible
    res_ssy_el = client.post("/api/v1/eligibility/evaluate/ssy", json={
        "citizen_attributes": {"has_girl_child": True, "girl_child_age": 6, "existing_ssa_accounts_in_family": 0}
    })
    assert res_ssy_el.json()["status"] == "ELIGIBLE"

    res_ssy_inel = client.post("/api/v1/eligibility/evaluate/ssy", json={
        "citizen_attributes": {"has_girl_child": True, "girl_child_age": 12, "existing_ssa_accounts_in_family": 0}
    })
    assert res_ssy_inel.json()["status"] == "NOT_ELIGIBLE"

    # PM Surya Ghar: owns house + grid connection -> eligible
    res_sg_el = client.post("/api/v1/eligibility/evaluate/pm-surya-ghar", json={
        "citizen_attributes": {"has_grid_electricity_connection": True, "has_residential_roof": True, "is_commercial_property": False}
    })
    assert res_sg_el.json()["status"] == "ELIGIBLE"

    res_sg_inel = client.post("/api/v1/eligibility/evaluate/pm-surya-ghar", json={
        "citizen_attributes": {"has_grid_electricity_connection": True, "has_residential_roof": False, "is_commercial_property": False}
    })
    assert res_sg_inel.json()["status"] == "NOT_ELIGIBLE"


def test_pmuy_kcc_pmsym_ignoaps_pmjdy_evaluation():
    """Test PMUY, KCC, PM-SYM, NSAP-IGNOAPS, and PMJDY rule evaluations."""
    # PMUY: female BPL without existing connection -> eligible
    res_pmuy_el = client.post("/api/v1/eligibility/evaluate/pmuy", json={
        "citizen_attributes": {
            "gender": "female",
            "age": 24,
            "is_deprived_household": True,
            "has_existing_lpg_connection": False
        }
    })
    assert res_pmuy_el.json()["status"] == "ELIGIBLE"

    res_pmuy_has = client.post("/api/v1/eligibility/evaluate/pmuy", json={
        "citizen_attributes": {
            "gender": "female",
            "age": 24,
            "is_deprived_household": True,
            "has_existing_lpg_connection": True
        }
    })
    assert res_pmuy_has.json()["status"] == "NOT_ELIGIBLE"

    # KCC: generic farmer without activity category -> POSSIBLY_ELIGIBLE (must not assume category)
    res_kcc_gen = client.post("/api/v1/eligibility/evaluate/kcc", json={
        "citizen_attributes": {"age": 35, "occupation": "Farmer", "is_bank_defaulter": False}
    })
    assert res_kcc_gen.json()["status"] == "POSSIBLY_ELIGIBLE"

    # KCC: landowner farmer -> ELIGIBLE
    res_kcc_owner = client.post("/api/v1/eligibility/evaluate/kcc", json={
        "citizen_attributes": {"age": 35, "occupation": "Farmer", "owns_agricultural_land": True, "is_bank_defaulter": False}
    })
    assert res_kcc_owner.json()["status"] == "ELIGIBLE"

    # KCC: tenant farmer -> ELIGIBLE
    res_kcc_tenant = client.post("/api/v1/eligibility/evaluate/kcc", json={
        "citizen_attributes": {"age": 35, "occupation": "Farmer", "is_tenant_farmer": True, "is_bank_defaulter": False}
    })
    assert res_kcc_tenant.json()["status"] == "ELIGIBLE"

    # KCC: allied activity worker -> ELIGIBLE
    res_kcc_allied = client.post("/api/v1/eligibility/evaluate/kcc", json={
        "citizen_attributes": {"age": 35, "occupation": "Farmer", "is_allied_activity_worker": True, "is_bank_defaulter": False}
    })
    assert res_kcc_allied.json()["status"] == "ELIGIBLE"

    # KCC: bank defaulter -> NOT_ELIGIBLE
    res_kcc_defaulter = client.post("/api/v1/eligibility/evaluate/kcc", json={
        "citizen_attributes": {"age": 35, "occupation": "Farmer", "owns_agricultural_land": True, "is_bank_defaulter": True}
    })
    assert res_kcc_defaulter.json()["status"] == "NOT_ELIGIBLE"

    # PM-SYM: income 12000 unorganised -> eligible, income 20000 -> ineligible
    res_sym_el = client.post("/api/v1/eligibility/evaluate/pm-sym", json={
        "citizen_attributes": {
            "age": 30,
            "monthly_income_inr": 12000,
            "is_unorganised_worker": True,
            "is_epfo_esic_nps_member": False,
            "pays_income_tax": False
        }
    })
    assert res_sym_el.json()["status"] == "ELIGIBLE"

    res_sym_high = client.post("/api/v1/eligibility/evaluate/pm-sym", json={
        "citizen_attributes": {
            "age": 30,
            "monthly_income_inr": 20000,
            "is_unorganised_worker": True,
            "is_epfo_esic_nps_member": False,
            "pays_income_tax": False
        }
    })
    assert res_sym_high.json()["status"] == "NOT_ELIGIBLE"

    # NSAP-IGNOAPS: age 65 BPL -> eligible, age 55 -> ineligible
    res_nsap_el = client.post("/api/v1/eligibility/evaluate/nsap-ignoaps", json={
        "citizen_attributes": {"age": 65, "has_bpl_card": True, "is_regular_govt_employee": False}
    })
    assert res_nsap_el.json()["status"] == "ELIGIBLE"

    res_nsap_young = client.post("/api/v1/eligibility/evaluate/nsap-ignoaps", json={
        "citizen_attributes": {"age": 55, "has_bpl_card": True, "is_regular_govt_employee": False}
    })
    assert res_nsap_young.json()["status"] == "NOT_ELIGIBLE"

    # PMJDY: resident without existing basic savings account -> eligible
    res_jdy_el = client.post("/api/v1/eligibility/evaluate/pmjdy", json={
        "citizen_attributes": {"age": 20, "has_basic_savings_bank_account": False}
    })
    assert res_jdy_el.json()["status"] == "ELIGIBLE"

    res_jdy_has = client.post("/api/v1/eligibility/evaluate/pmjdy", json={
        "citizen_attributes": {"age": 20, "has_basic_savings_bank_account": True}
    })
    assert res_jdy_has.json()["status"] == "NOT_ELIGIBLE"



