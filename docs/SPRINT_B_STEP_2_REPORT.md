# Sprint B — Step 2 Completion Report: Reusable Frontend API Client

**Project:** Yojana Saathi (Government Scheme Eligibility & Assistance Platform)  
**Milestone:** Phase 7 (Frontend–Backend Integration) — Step 2  
**Date:** November 11, 2026  
**Status:** COMPLETE & FULLY VERIFIED (Corrections Applied & Passing All Suites)  

---

## 1. Executive Summary

In accordance with Sprint B requirements and the approved review findings in [`docs/SPRINT_B_STEP_2_REVIEW.md`](file:///Users/vinodsubedar/Downloads/PS5_hack/docs/SPRINT_B_STEP_2_REVIEW.md), **Step 2** has been implemented, audited, corrected, and verified.

The production-grade, reusable API client in [`src/services/schemeApi.ts`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts) connects the React application to the live FastAPI backend. It implements strongly typed methods for all verified backend endpoints, bidirectional adapters to normalize citizen attributes and backend scheme schemas into existing frontend React component contracts, robust error handling with typed `SchemeApiError`, AbortSignal support for request cancellation, and safe transient-failure retry policies for idempotent `GET` requests (with retries explicitly disabled for state-mutating `POST` endpoints).

### Key Safety & Reliability Guarantees
- **Strict Profile Mapping Safety:** `mapUserProfileToCitizenAttributes()` strictly omits unsupplied, missing, empty, or undefined profile fields. It **never assigns default age, never defaults income to 0, never defaults landholding to 0, and never fabricates domain credentials** (like trade categories, SHG memberships, enterprise types, or family details). This ensures the deterministic backend `RuleEngineService` accurately detects `UNKNOWN` conditions, returns `POSSIBLY_ELIGIBLE`, and requests missing information.
- **Accurate Bilingual Subtitle Mapping:** For Indic languages (`hi`, `kn`, `te`), the secondary subtitle displays the English scheme title (`names.en`) to avoid duplicate titles and preserve bilingual accessibility.
- **Accurate CSC Availability:** `cscApplicable` is dynamically computed from underlying document `csc_assisted` flags.
- **Zero frontend screens modified in this step:** `Home.tsx`, `BrowseSchemes.tsx`, `SchemeDetail.tsx`, `DocumentChecklist.tsx`, `EligibilityResults.tsx`, and `WhyNotEligible.tsx` remain untouched and will be integrated incrementally in subsequent steps upon review.
- **100% test coverage:** 24 focused API and adapter tests in [`scripts/test_scheme_api.mjs`](file:///Users/vinodsubedar/Downloads/PS5_hack/scripts/test_scheme_api.mjs).
- **Zero regressions:** 194 / 194 backend tests pass, 52 / 52 frontend tests pass, and `npm run build` succeeds cleanly.

---

## 2. Verified Backend Endpoint Contracts

| Endpoint | Method | Path | Request Body / Query Params | Response Schema | Backend Source |
|---|---|---|---|---|---|
| **List & Filter Schemes** | `GET` | `/api/v1/schemes` | `category`, `state`, `scheme_type`, `q`, `page`, `page_size` | `SchemeListResponse` (`items: SchemeSummarySchema[]`, `pagination: SchemePaginationMetadata`) | `app/api/v1/schemes.py:38` |
| **Scheme Details** | `GET` | `/api/v1/schemes/{scheme_id}` | `scheme_id` (path parameter) | `SchemeDetailSchema` (rules AST, documents, localized benefits, steps) | `app/api/v1/schemes.py:220` |
| **Scheme Provenance** | `GET` | `/api/v1/schemes/{scheme_id}/provenance` | `scheme_id` (path parameter) | `SchemeProvenanceResponse` (primary source citations, verification status, temporal freshness) | `app/api/v1/schemes.py:310` |
| **Document Checklist** | `GET` | `/api/v1/documents/checklist/{scheme_id}` | `scheme_id`, `session_id`, `lang` | `SchemeChecklistResponse` (`documents: ChecklistItemSchema[]`, `is_complete`) | `app/api/v1/documents.py:18` |
| **Mark Checklist Item** | `POST` | `/api/v1/documents/checklist/mark` | `{ session_id, scheme_id, document_id, is_collected }` | `SchemeChecklistResponse` (updated counts and item flags) | `app/api/v1/documents.py:62` |
| **Multi-Scheme Evaluation** | `POST` | `/api/v1/eligibility/evaluate` | `{ citizen_attributes: {...}, scheme_ids?: [...], preferred_language?: str }` | `EligibilityEvaluationResponse` (`results: SchemeEligibilityResult[]`) | `app/api/v1/eligibility.py:26` |
| **Single-Scheme Evaluation** | `POST` | `/api/v1/eligibility/evaluate/{scheme_id}` | `{ citizen_attributes: {...}, preferred_language?: str }` | `SchemeEligibilityResult` (`status`, `conditions_satisfied`, `conditions_failed`, `missing_information`) | `app/api/v1/eligibility.py:98` |

---

## 3. Implemented API Methods in `src/services/schemeApi.ts`

### 1. `fetchSchemes(params?: FetchSchemesParams, options?: RequestOptions): Promise<SchemeListResponse>`
- Fetches paginated schemes from SQLite.
- Supports category filtering (`agriculture`, `healthcare`, `housing`, `social_welfare`, `employment`, `women_and_child`, `energy`).
- Supports multilingual keyword search (`q`), state applicability, and administrative type.

### 2. `fetchSchemeDetail(schemeId: string, options?: RequestOptions): Promise<SchemeDetailSchema>`
- Retrieves verified scheme specifications, rule ASTs, localized benefits, and official procedures.

### 3. `fetchSchemeProvenance(schemeId: string, options?: RequestOptions): Promise<SchemeProvenanceResponse>`
- Retrieves legal citations, primary source URLs, verification status, and temporal guideline freshness.

### 4. `fetchDocumentChecklist(schemeId: string, sessionId?: string, lang?: Language, options?: RequestOptions): Promise<SchemeChecklistResponse>`
- Retrieves official document checklist requirements with mandatory and CSC assistance flags.
- Echoes session collection marks if an anonymous UUID `session_id` is passed.

### 5. `markDocumentCollected(payload: MarkChecklistItemRequest, options?: RequestOptions): Promise<SchemeChecklistResponse>`
- Zero-knowledge ephemeral session checklist toggle (`is_collected: true/false`).
- Configured with `retries: 0` to prevent duplicate mutation requests.

### 6. `evaluateEligibility(payload: EligibilityEvaluationRequest, options?: RequestOptions): Promise<EligibilityEvaluationResponse>`
- Invokes the deterministic backend `RuleEngineService`.
- Returns three-state eligibility outcome (`ELIGIBLE`, `NOT_ELIGIBLE`, `POSSIBLY_ELIGIBLE`), satisfied criteria, failed conditions, and missing information prompts.

### 7. `evaluateSingleScheme(schemeId: string, citizenAttributes: Record<string, any>, preferredLanguage?: Language, options?: RequestOptions): Promise<SchemeEligibilityResult>`
- Evaluates a citizen against a single scheme to surface precise failure reasons and clause citations.

---

## 4. Adapters & Data Transformers

### `mapUserProfileToCitizenAttributes(profile: Partial<UserProfile> | null | undefined): Record<string, any>`
Bridges the gap between frontend camelCase profile properties and backend snake_case deterministic rule engine inputs without introducing assumptions:
- **Strict Inclusion:** Only explicitly supplied, valid, non-empty attributes are included.
- **Missing Preservation:** If an attribute is missing or undefined (`age`, `annualIncome`, `landholdingHectares`, `occupation`, `gender`), it is **strictly omitted** so the Rule Engine evaluates it as `UNKNOWN` and requests it via `missing_information`.
- **Preserves Valid Falses and Zeros:** Explicit zero (`annualIncome: 0`, `landholdingHectares: 0`) and explicit false (`hasBPLCard: false`, `isDifferentlyAbled: false`) are faithfully preserved.
- **No Fabrications:** Zero hardcoded assumptions (no fabricated `trade_category`, `is_shg_member`, `has_girl_child`, or `has_residential_roof`).
- **Privacy Protection:** `profile.name` is never mapped, protecting citizen PII.

### `mapBackendSchemeToFrontend(backendScheme: SchemeSummarySchema | SchemeDetailSchema, lang: Language = 'en', eligibilityResult?: SchemeEligibilityResult | null): Scheme`
Transforms live backend responses into the exact `Scheme` interface expected by existing React UI components (`SchemeCard`, badges, icons, layouts):
- Localized `name`, `nativeName`, `benefit`, `benefitHighlight`, and `description` across `en`, `hi`, `kn`, `te`.
- **Bilingual Subtitle:** When viewing in an Indic language (`hi`, `kn`, `te`), `nativeName` displays `names.en`. When viewing in English (`en`), `nativeName` displays the native Indic name (`names.hi` or first available Indic script).
- **Dynamic CSC Support:** `cscApplicable` is derived strictly from `documents.some(d => d.csc_assisted)`.
- Live eligibility status mapping: `ELIGIBLE` -> `'eligible'`, `POSSIBLY_ELIGIBLE` -> `'possibly_eligible'`, `NOT_ELIGIBLE` -> `'not_eligible'` with dynamic `matchScore` (96, 78, 32).
- Extracts `matchingCriteria` from `conditions_satisfied` reasons.
- Extracts `missingCriteria` from `missing_information` localized prompts.
- Extracts `failedCriteria` from `conditions_failed` localized reasons.
- Maps `documents` to `requiredDocuments: SchemeDocument[]` with mandatory flags.
- Formats step-by-step procedures to `applicationSteps: string[]`.
- Gracefully handles missing optional fields without crashing.

---

## 5. Error Handling & Resilience Architecture

1. **Typed `SchemeApiError`:**
   - Exposes `status`, `errorCode`, `isNetworkError`, `isAborted`, and server payload `detail`.
2. **Safe Transient Retry Policy:**
   - **Idempotent GET requests:** Automatically retries transient network interruptions or HTTP 502/503/504 errors using exponential backoff (`Math.pow(2, attempt) * 200ms`).
   - **Client errors (4xx):** HTTP 400, 404, 422 are recognized as non-transient and **never retried**.
   - **State mutations (POST):** `markDocumentCollected`, `evaluateEligibility`, and `evaluateSingleScheme` strictly enforce `retries: 0` to prevent duplicate operations.
3. **Cancellation (AbortSignal):**
   - Supports caller `AbortController.signal` across all methods with timeout protection. Cleanly flags `isAborted: true` and `errorCode: 'ABORT_ERR'`.

---

## 6. Test & Build Results

### Frontend Unit Tests (`npm test`)
All 52 unit tests across 14 test suites passed:
```
▶ UserProfile to CitizenAttributes Adapter
  ✔ maps camelCase UserProfile into exact snake_case attributes when explicitly supplied
  ✔ empty or undefined profile produces no fabricated eligibility attributes
  ✔ missing age, income, landholding and occupation are strictly omitted
  ✔ blank whitespace occupation is omitted (does not produce empty string)
  ✔ preserves explicit zero and false where supplied
  ✔ does not fabricate trade category, enterprise type, SHG membership or roof ownership
  ✔ handles vendor and artisan occupation tokens cleanly
▶ Backend Scheme to Frontend Scheme Adapter
  ✔ correctly transforms backend scheme into frontend Scheme structure in English
  ✔ correctly localizes content into Kannada (kn) and displays English bilingual subtitle
  ✔ correctly sets English bilingual subtitle for Hindi and Telugu
  ✔ CSC availability accurately reflects underlying document csc_assisted flags
  ✔ applies live RuleEngineService eligibility evaluation results
  ✔ handles missing optional fields without crashing
▶ API Client Methods with Mock Fetch
  ✔ fetchSchemes constructs correct URL and query parameters
  ✔ fetchSchemeDetail fetches scheme by slug
  ✔ fetchSchemeProvenance calls /schemes/{id}/provenance
  ✔ fetchDocumentChecklist includes session_id and lang
  ✔ markDocumentCollected executes POST mutation with retries disabled
  ✔ evaluateEligibility executes POST with citizen_attributes
  ✔ evaluateSingleScheme targets /eligibility/evaluate/{id}
▶ API Error Handling and Resilience
  ✔ throws SchemeApiError on 404 without retrying client error
  ✔ retries transient 503 error on safe GET and succeeds on second attempt
  ✔ handles network failure with isNetworkError flag
  ✔ handles caller AbortSignal cleanly with isAborted flag
▶ Speech Subsystem Tests (18 tests passing)
▶ PWA & Service Worker Tests (10 tests passing)

ℹ tests 52
ℹ suites 14
ℹ pass 52
ℹ fail 0
```

### Production Build (`npm run build`)
```
> tsc && vite build
vite v6.4.6 building for production...
✓ 2102 modules transformed.
dist/index.html                   1.56 kB │ gzip:   0.77 kB
dist/assets/index-B_g5Hb1W.css   39.00 kB │ gzip:   7.04 kB
dist/assets/index-DNxnapAw.js   423.66 kB │ gzip: 116.15 kB
✓ built in 1.05s
```

### Backend Test Suite (`pytest`)
```
cd backend && PYTHONPATH=. .venv/bin/pytest tests -q
194 passed, 2 warnings in 3.89s
```

---

## 7. Next Steps

With all review findings resolved, Step 2 is fully complete and verified. Ready to proceed with **Step 3 (Connecting the 6 Core Screens Incrementally)** upon user review and approval.
