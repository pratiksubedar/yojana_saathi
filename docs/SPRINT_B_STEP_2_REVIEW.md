# Sprint B — Step 2 Code Review Report: Frontend Scheme API Client

**Project:** Yojana Saathi (Government Scheme Eligibility & Assistance Platform)  
**Milestone:** Phase 7 (Frontend–Backend Integration) — Step 2 Code Review  
**Date:** November 11, 2026  
**Auditor:** Antigravity AI (Pair Programming Assistant)  
**Status:** **CHANGES REQUIRED** (Review complete; actionable corrections specified)  

---

## 1. Executive Summary

A strict, read-only audit of Sprint B Step 2 was conducted across:
- [`src/services/schemeApi.ts`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts)
- [`scripts/test_scheme_api.mjs`](file:///Users/vinodsubedar/Downloads/PS5_hack/scripts/test_scheme_api.mjs)
- [`docs/SPRINT_B_STEP_2_REPORT.md`](file:///Users/vinodsubedar/Downloads/PS5_hack/docs/SPRINT_B_STEP_2_REPORT.md)
- Backend schemas in `backend/app/schemas/` (`scheme.py`, `eligibility.py`, `document.py`, `provenance.py`)
- Backend endpoints in `backend/app/api/v1/` (`schemes.py`, `eligibility.py`, `documents.py`)
- Existing frontend interfaces in `src/types/index.ts` (`UserProfile`, `Scheme`, `EligibilityOutcomeItem`)

### Review Summary Table

| Category | Finding ID | Severity | Status | Summary |
|---|---|---|---|---|
| **Profile Mapping Safety** | FIND-B2-01 | **CRITICAL** | OPEN | Silent defaulting & attribute fabrication in `mapUserProfileToCitizenAttributes` destroys rule engine missing-field detection |
| **Profile Mapping Safety** | FIND-B2-02 | **HIGH** | OPEN | Empty occupation converted to empty string instead of omitted, causing false `FAILED` instead of `UNKNOWN` |
| **Scheme Transformation** | FIND-B2-03 | **MEDIUM** | OPEN | No-op ternary `requiredDocuments.length > 0 ? true : true` hardcoded for `cscApplicable` |
| **Scheme Transformation** | FIND-B2-04 | **MEDIUM** | OPEN | Dual identical script display when viewing non-English languages |
| **Test Quality** | FIND-B2-05 | **LOW** | OPEN | Unit tests codified unsafe defaulting (`age=30`, `income=0`) instead of validating field omission |

---

## 2. Detailed Findings & Concrete Evidence

### FIND-B2-01: Silent Defaulting & Attribute Fabrication in `mapUserProfileToCitizenAttributes`
- **File & Lines:** [`src/services/schemeApi.ts:413-469`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts#L413-L469)
- **Severity:** **CRITICAL**
- **Description:**
  `mapUserProfileToCitizenAttributes()` silently supplies default values for unprovided citizen fields and fabricates domain-specific attributes:
  ```typescript
  // src/services/schemeApi.ts:413-440
  const annualIncome = typeof profile.annualIncome === 'number' ? profile.annualIncome : 0;
  const monthlyIncome = Math.round(annualIncome / 12);
  const landholding = typeof profile.landholdingHectares === 'number' ? profile.landholdingHectares : 0;
  const isBpl = Boolean(profile.hasBPLCard);
  ...
  age: Number(profile.age) || 30,
  gender: profile.gender ? profile.gender.toLowerCase() : 'male',
  landholding_hectares: landholding,
  annual_income_inr: annualIncome,
  monthly_income_inr: monthlyIncome,
  ```
  Furthermore, lines 443–468 inject hardcoded statutory defaults:
  ```typescript
  trade_category: 'Carpenter (Suthar)',
  enterprise_type: 'Micro Enterprise',
  is_greenfield_enterprise: true,
  is_shg_member: true,
  is_rural_resident: true,
  has_grid_electricity_connection: true,
  has_residential_roof: true,
  has_girl_child: false,
  girl_child_age: 5,
  ```
- **Concrete Impact:**
  1. **Income Fabrication:** If a citizen has not entered an income, the adapter sends `annual_income_inr: 0` and `monthly_income_inr: 0`. Any scheme with an income ceiling (e.g. `pm-sym` <= ₹15,000/month) evaluates this condition as `SATISFIED` rather than `UNKNOWN`. The citizen appears eligible even though their income is completely unknown.
  2. **Age Fabrication:** If a citizen has not entered an age, the adapter sends `age: 30`. This falsely satisfies age criteria for youth and middle-age schemes (APY, PMJJBY, PMSBY, PM-SYM), while automatically disqualifying elderly citizens from `nsap-ignoaps` (which requires age >= 60).
  3. **Gender Fabrication:** Missing gender defaults to `'male'`, automatically disqualifying citizens from maternity and women-empowerment schemes (PMMVY, PMUY, DAY-NRLM).
  4. **Landholding Fabrication:** Missing landholding defaults to `0`. PM-KISAN requires `landholding_hectares > 0`. Because `0 > 0` is false, PM-KISAN immediately reports `FAILED` (`NOT_ELIGIBLE`) instead of reporting `missing_information` (`POSSIBLY_ELIGIBLE`).
  5. **Fabricated Occupations / Memberships:** Falsely declaring that every citizen is a `'Carpenter (Suthar)'`, a `'Micro Enterprise'`, and an `'is_shg_member: true'` creates false-positive qualifications for PM Vishwakarma, PM MUDRA, and DAY-NRLM.
- **Required Correction:**
  The deterministic backend `RuleEngineService` is explicitly engineered to handle missing attributes: when an attribute is omitted from `citizen_attributes`, condition evaluation returns `ConditionStatusEnum.UNKNOWN`, populates `missing_information` with the multilingual question prompt, and returns `POSSIBLY_ELIGIBLE`.
  The adapter must **only include attributes that are explicitly defined and non-null in `UserProfile`**. Unknown attributes must be omitted completely.

---

### FIND-B2-02: Empty Occupation String Evaluated as FAILED Instead of UNKNOWN
- **File & Lines:** [`src/services/schemeApi.ts:419-434`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts#L419-L434)
- **Severity:** **HIGH**
- **Description:**
  When `profile.occupation` is undefined, `let normalizedOccupation = profile.occupation || ''` assigns `""` and sends `occupation: ""`.
  In `backend/app/services/rule_engine.py:382`:
  ```python
  if operator == "in":
      if citizen_val in target:  # "" in ['Farmer', ...] -> False!
          return ConditionStatusEnum.SATISFIED
      return ConditionStatusEnum.FAILED
  ```
  Because the key `occupation` is present in the dictionary with value `""`, the rule engine evaluates the condition as `FAILED` (`NOT_ELIGIBLE`) instead of `UNKNOWN` (`POSSIBLY_ELIGIBLE`).
- **Required Correction:**
  If `profile.occupation` is missing, null, or empty whitespace, omit `occupation` from `citizen_attributes` entirely.

---

### FIND-B2-03: Redundant Hardcoded Ternary for `cscApplicable`
- **File & Lines:** [`src/services/schemeApi.ts:607`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts#L607)
- **Severity:** **MEDIUM**
- **Description:**
  ```typescript
  cscApplicable: requiredDocuments.length > 0 ? true : true,
  ```
  This is a no-op ternary expression that always evaluates to `true`, ignoring whether the scheme's documents actually declare `csc_assisted: true/false`.
- **Required Correction:**
  Derive `cscApplicable` from the underlying documents:
  ```typescript
  cscApplicable: Array.isArray(rawDocs) && rawDocs.length > 0 ? rawDocs.some(d => d.csc_assisted) : true,
  ```

---

### FIND-B2-04: Non-English Languages Produce Duplicate Bilingual Titles
- **File & Lines:** [`src/services/schemeApi.ts:486`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts#L486)
- **Severity:** **MEDIUM**
- **Description:**
  ```typescript
  const localizedName = names[lang] || names.en || backendScheme.id;
  const localizedNative = names[lang !== 'en' ? lang : 'hi'] || names.hi || names.en || '';
  ```
  When `lang === 'kn'` (Kannada):
  - `localizedName` = `names['kn']` (e.g. "ಪಿಎಂ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ")
  - `localizedNative` = `names['kn']` (e.g. "ಪಿಎಂ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ")
  In `SchemeCard.tsx` lines 65–69:
  ```tsx
  <h3>{localizedScheme.name}</h3>
  <p>{localizedScheme.nativeName}</p>
  ```
  The UI displays identical Kannada text in both the title and subtitle. The intention of `nativeName` is bilingual display: showing the Indic native script when browsing in English, and showing the official English/Hindi title when browsing in an Indic language.
- **Required Correction:**
  ```typescript
  const localizedName = names[lang] || names.en || backendScheme.id;
  const localizedNative = lang === 'en' 
    ? (names.hi || names.kn || names.te || '') 
    : (names.en || '');
  ```

---

### FIND-B2-05: Unit Tests Codified Unsafe Defaulting Assumptions
- **File & Lines:** [`scripts/test_scheme_api.mjs:57-67`](file:///Users/vinodsubedar/Downloads/PS5_hack/scripts/test_scheme_api.mjs#L57-L67)
- **Severity:** **LOW**
- **Description:**
  The test `'safely falls back on missing or incomplete profile numbers'` explicitly asserts:
  ```javascript
  assert.strictEqual(attrs.age, 30);
  assert.strictEqual(attrs.annual_income_inr, 0);
  assert.strictEqual(attrs.has_bpl_card, false);
  ```
  This test verified that defaulting occurred, rather than verifying that unknown fields are preserved as missing so the Rule Engine can identify missing information.
- **Required Correction:**
  Update the unit test to verify that empty or undefined profile attributes are omitted from the mapped output.

---

## 3. API Contract & Security Verification

1. **Endpoint Alignment:**
   - `fetchSchemes()` matches `GET /api/v1/schemes` query params (`category`, `state`, `scheme_type`, `q`, `page`, `page_size`).
   - `fetchSchemeDetail()` matches `GET /api/v1/schemes/{scheme_id}`.
   - `fetchSchemeProvenance()` matches `GET /api/v1/schemes/{scheme_id}/provenance`.
   - `fetchDocumentChecklist()` matches `GET /api/v1/documents/checklist/{scheme_id}`.
   - `markDocumentCollected()` matches `POST /api/v1/documents/checklist/mark`.
   - `evaluateEligibility()` matches `POST /api/v1/eligibility/evaluate`.
   - `evaluateSingleScheme()` matches `POST /api/v1/eligibility/evaluate/{scheme_id}`.
2. **Security & Privacy (PII Protection):**
   - Citizen name (`profile.name`) is correctly omitted from `mapUserProfileToCitizenAttributes()`, preventing PII transmission to eligibility evaluation endpoints.
   - Ephemeral session IDs are passed only via path/query or body, with zero browser storage persistence.
3. **Reliability & Cancellation:**
   - Safe GET requests retry on transient 502/503/504 errors with exponential backoff.
   - Client errors (4xx) are never retried.
   - POST operations strictly enforce `retries: 0` to prevent duplicate mutations.
   - `AbortSignal` is supported across all methods.

---

## 4. Required Action Plan (Before Step 3 Screen Integration)

To achieve **APPROVED** status:

1. **Fix `mapUserProfileToCitizenAttributes` in `src/services/schemeApi.ts`:**
   - Only map defined, non-empty attributes (`age`, `gender`, `state`, `district`, `occupation`, `landholding_hectares`, `annual_income_inr`, `social_category`, `has_bpl_card`, `is_differently_abled`).
   - Calculate `monthly_income_inr` only when `annualIncome` is explicitly provided.
   - Remove hardcoded domain fabrications (`trade_category`, `is_shg_member`, `enterprise_type`, `has_girl_child`, `has_residential_roof`, etc.).
   - Omit missing/undefined fields so `RuleEngineService` can detect `UNKNOWN` conditions and return `missing_information`.
2. **Fix `mapBackendSchemeToFrontend` in `src/services/schemeApi.ts`:**
   - Fix `cscApplicable` to derive from `documents.some(d => d.csc_assisted)`.
   - Fix `localizedNative` to display the bilingual counterpart (`names.en` when `lang !== 'en'`, and Indic name when `lang === 'en'`).
3. **Update Unit Tests in `scripts/test_scheme_api.mjs`:**
   - Verify omission of undefined profile fields.
   - Verify that unknown profile attributes produce `undefined` in attributes dictionary.
4. **Run Full Verification:**
   - `npm test`
   - `npm run build`
   - `pytest`

---

## 5. Final Verdict

**CHANGES REQUIRED**

*Reason:* The profile mapping adapter `mapUserProfileToCitizenAttributes()` introduces silent defaults (`age: 30`, `annual_income_inr: 0`, `landholding: 0`, `gender: 'male'`) and fabricates domain credentials (`trade_category: 'Carpenter (Suthar)'`), compromising the deterministic authority of the backend Rule Engine. Once the specified corrections are applied and verified, Step 2 can be approved to proceed with Step 3 screen integration.

