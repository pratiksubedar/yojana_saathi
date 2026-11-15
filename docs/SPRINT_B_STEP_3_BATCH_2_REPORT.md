# Sprint B — Step 3 Batch 2 Integration Report

**Project:** Yojana Saathi (Government Scheme Eligibility & Assistance Platform)  
**Milestone:** Phase 7 (Frontend–Backend Integration) — Step 3, Batch 2: Remaining Three Core Screens  
**Date:** November 11, 2026  
**Status:** COMPLETED & VERIFIED (Batch 2 Complete — Main Screen Integration Finished)  

---

## 1. Executive Summary

Sprint B Step 3, Batch 2 completed the frontend-to-backend integration for the remaining three core screens:
1. `src/pages/DocumentChecklist.tsx`
2. `src/pages/EligibilityResults.tsx`
3. `src/pages/WhyNotEligible.tsx`

All six core citizen screens in the application are now fully connected to the FastAPI backend and deterministic `RuleEngineService`. Static mock scheme data (`MOCK_SCHEMES`) has been completely eliminated from the live runtime code paths across all six screens, preserving citizen privacy, zero-knowledge session isolation, and the existing Stitch design.

---

## 2. Files Modified in Batch 2

| File | Nature of Change | Purpose |
|---|---|---|
| [`src/pages/DocumentChecklist.tsx`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/pages/DocumentChecklist.tsx) | Modified | Connected to `fetchDocumentChecklist(id, sessionId, language)` and `markDocumentCollected(payload)`. Added live session-tracked progress bar, mandatory vs optional badge distinction, CSC-assisted tags, issuer and guidelines links, application procedure steps, 404 handling, and error retry state. |
| [`src/pages/EligibilityResults.tsx`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/pages/EligibilityResults.tsx) | Modified | Connected to `evaluateEligibility()` and `fetchSchemes({ pageSize: 50 })`. Submits sanitized citizen attributes via `mapUserProfileToCitizenAttributes()`. Correctly partitions live backend outcomes into 3 buckets: `eligible`, `possibly_eligible`, and `not_eligible`. Added loading skeletons and error recovery. |
| [`src/pages/WhyNotEligible.tsx`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/pages/WhyNotEligible.tsx) | Modified | Connected to `evaluateSingleScheme(schemeId, attributes, language)`. Renders exact failed conditions with official statutory citations (`source_id`, `clause`, `url`). Preserves UNKNOWN criteria as pending information queries rather than false disqualifications. Derives recommended alternatives strictly from live backend evaluation results. |
| [`src/data/translations.ts`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/data/translations.ts) | Modified | Added clean localized strings for CSC badges, unknown criteria guidance, alternative schemes fallback, and checklist readiness across `en`, `hi`, `kn`, and `te`. |
| [`package.json`](file:///Users/vinodsubedar/Downloads/PS5_hack/package.json) | Modified | Added `scripts/test_batch2_screens.mjs` to `npm test` and added `npm run test:batch2`. |
| [`scripts/test_batch2_screens.mjs`](file:///Users/vinodsubedar/Downloads/PS5_hack/scripts/test_batch2_screens.mjs) | Created | 9 unit/integration tests validating static mock independence, checklist session tracking, sanitized attribute mapping, 3-state eligibility outcomes, UNKNOWN criteria preservation, and statutory citation display. |

---

## 3. Exact Backend Endpoints Used & Contracts Discovered

### 1. `GET /api/v1/documents/checklist/{scheme_id}`
- **Query Parameters:** `session_id` (optional valid UUIDv4 string), `lang` (`en`, `hi`, `kn`, `te`).
- **Validation Rule:** If `session_id` is supplied, it must be a valid standard UUID or FastAPI raises HTTP 422. Handled via `getSessionId()` which generates cryptographically secure UUIDv4 tokens.
- **Response Structure (`SchemeChecklistResponse`):**
  - `scheme_id`: target scheme identifier
  - `scheme_name`: multilingual dict (`en`, `hi`, `kn`, `te`)
  - `total_documents`: total documents count
  - `mandatory_count`: number of mandatory documents
  - `optional_count`: number of optional documents
  - `collected_count`: count of documents marked collected in active session
  - `mandatory_collected_count`: count of mandatory documents collected
  - `is_complete`: boolean (`true` if all mandatory documents collected)
  - `documents`: array of `ChecklistItemSchema` (`id`, `names`, `descriptions`, `is_mandatory`, `csc_assisted`, `issuer`, `source_url`, `is_collected`)
  - `source_citation`: guidelines reference dict
  - `official_portal_url`: direct portal URL
  - `disclaimer`: legal advisory text

### 2. `POST /api/v1/documents/checklist/mark`
- **Request Body (`MarkChecklistItemRequest`):**
  - `session_id`: UUID string
  - `scheme_id`: string
  - `document_id`: string
  - `is_collected`: boolean
- **Safety Constraints:** `extra='forbid'`, strict scanning rejecting any sensitive citizen PII keys (`aadhaar`, `bank_account`, etc.).
- **Response:** Updated `SchemeChecklistResponse` echoing active collection state.

### 3. `POST /api/v1/eligibility/evaluate`
- **Request Body (`EligibilityEvaluationRequest`):**
  - `citizen_attributes`: sanitized dictionary of citizen demographics
  - `scheme_ids`: optional array of slugs (null evaluates all active schemes)
  - `preferred_language`: language code (`en`, `hi`, `kn`, `te`)
- **Response (`EligibilityEvaluationResponse`):**
  - `results`: array of `SchemeEligibilityResult`:
    - `scheme_id`: string
    - `status`: `ELIGIBLE`, `NOT_ELIGIBLE`, `POSSIBLY_ELIGIBLE`
    - `rule_completeness`: `VERIFIED_COMPLETE`, `PARTIAL`, `UNVERIFIED`
    - `summary`: multilingual rationale dict
    - `conditions_satisfied`: array of satisfied conditions with rationale
    - `conditions_failed`: array of failed conditions with reason and citation
    - `missing_information`: array of missing fields with conversational prompts and expected types
    - `unresolved_criteria`: array of criteria requiring physical CSC inspection

### 4. `POST /api/v1/eligibility/evaluate/{scheme_id}`
- **Path Parameter:** `scheme_id`
- **Request Body:** `{ "citizen_attributes": {...}, "preferred_language": "..." }`
- **Response:** Single `SchemeEligibilityResult` containing exact condition evaluations, failure reasons, and official statutory clause references (`source_id`, `clause`, `url`, `page_ref`).

---

## 4. Screen-by-Screen Implementation Details

### Screen 1: `src/pages/DocumentChecklist.tsx`
- **Checklist Loading & Session Synchronization:**
  - Calls `fetchDocumentChecklist(id, sessionId, language)` on mount.
  - Concurrently queries `fetchSchemeDetail(id)` to retrieve official application procedure steps.
  - Passes session token retrieved from `getSessionId()`.
- **Collection State Mutation:**
  - When citizen clicks a document row, `handleToggleDocument` optimistically updates the local progress UI and submits `markDocumentCollected({ session_id, scheme_id, document_id, is_collected })`.
  - Reverts gracefully to previous server state if a network error occurs.
  - Synchronizes with `AppContext.toggleDocumentCheck` without storing file contents or PII.
- **Design & Transparency:**
  - Clearly differentiates `Mandatory` (red border badge) and `Optional` (neutral badge) items.
  - Highlights `CSC Assisted` items (amber badge) indicating Common Service Centre support.
  - Renders document issuer authority and official portal external link when provided.
  - Zero false claims: UI explicitly states items are marked by the user for session tracking, not officially verified documents.
- **States:** Loading skeletons for progress and document list, 404 Not Found card with return button, error card with retry button, and empty checklist card.

### Screen 2: `src/pages/EligibilityResults.tsx`
- **Sole Eligibility Authority:**
  - React components perform **zero** eligibility calculations or heuristic guesses.
  - Invokes `evaluateEligibility()` with attributes strictly produced by `mapUserProfileToCitizenAttributes(userProfile)`.
- **Three-State Partitioning:**
  - Results are partitioned strictly based on the backend's returned enum:
    - `eligible` (`status === 'ELIGIBLE'`)
    - `possibly_eligible` (`status === 'POSSIBLY_ELIGIBLE'`)
    - `not_eligible` (`status === 'NOT_ELIGIBLE'`)
- **Metric Buckets & Filtering Tabs:**
  - Top summary banner displays the live counts for all 3 categories.
  - Clicking any bucket filters the list to that status.
  - Tab filters allow seamless navigation between `All`, `Eligible`, `Possibly Eligible`, and `Not Eligible`.
- **Rejection Breakdown Navigation:**
  - The "Not Eligible" tab surfaces an alert with an instant "View Reasons" button navigating to `/why-not-eligible/:id`.
- **States:** 3 skeleton pulsing placeholder cards during evaluation flight, friendly error card with "Retry" action, and empty filter fallback.

### Screen 3: `src/pages/WhyNotEligible.tsx`
- **Single Scheme Evaluation:**
  - Calls `evaluateSingleScheme(targetSchemeId, citizenAttrs, language)`.
  - If no ID is provided in route (`/why-not-eligible`), it queries all evaluations and selects the first ineligible scheme.
- **Failed Conditions & Authoritative Citations:**
  - Renders failed conditions only when present in `evaluation.conditions_failed`.
  - Displays localized failure reason (`fail.reason[lang]`).
  - Displays official statutory clause citation if returned (e.g. `Section 4, Clause 4.1`, issuing authority, official guidelines link).
- **UNKNOWN Criteria Preservation:**
  - Preserves `evaluation.missing_information` in a dedicated "Information Required for Verification" card with amber advisory styling.
  - Explicitly informs the citizen that missing attributes are **pending information**, NOT confirmed disqualifications.
  - Displays conversational question prompts (`miss.prompt[lang]`) explaining what is required.
- **Verified Alternative Recommendations:**
  - Derives alternatives strictly from schemes where `itemEval.status === 'ELIGIBLE'`.
  - Does **not** invent or fabricate alternative schemes. If none are eligible, displays a friendly notice with an "Edit Profile" button navigating to `/profile`.
- **States:** Skeleton loaders for explanation banner and failed criteria cards, 404 Not Found card, and error card with retry action.

---

## 5. Attribute Mapping & Safety Preservation

- **Zero Fabricated Defaults:** As enforced in Step 2 and validated across both batches, `mapUserProfileToCitizenAttributes` omits missing or empty fields.
- **Preservation of Explicit False and Zero:**
  - `hasBPLCard: false` -> `has_bpl_card: false`
  - `isDifferentlyAbled: false` -> `is_differently_abled: false`
  - `landholdingHectares: 0` -> `landholding_hectares: 0`
  - `annualIncome: 0` -> `annual_income_inr: 0`
- **Zero-Knowledge Privacy:** Citizen name (`name`) is strictly stripped and never sent to `/eligibility/evaluate` or `/documents/checklist/mark`.

---

## 6. Verification & Test Results

### 1. Frontend Test Suite
- Executed `npm test` across all 5 test files:
  - `scripts/test_speech.mjs`
  - `scripts/test_pwa_offline.mjs`
  - `scripts/test_scheme_api.mjs`
  - `scripts/test_batch1_screens.mjs`
  - `scripts/test_batch2_screens.mjs`
- **Result:** **72 / 72 tests passing (100%)** across 22 test suites in ~498ms.
  - Static audit: Confirmed zero imports or usages of `MOCK_SCHEMES` across all 6 core pages.
  - Checklist tests: Verified session tracking, mandatory/optional distinction, CSC flags, and mark mutation.
  - Eligibility tests: Verified sanitized attribute transmission, 3-state partitioning, and missing information handling.
  - Why-not-eligible tests: Verified failed condition rationale, statutory citations, and UNKNOWN preservation.

### 2. Production Build Verification
- Executed `npm run build` (`tsc && vite build`).
- **Result:** **Clean compilation in 1.07s** with zero errors or warnings.
  - Generated assets: `dist/assets/index-DGlSDSWd.css` (39.91 kB) and `dist/assets/index-DxORJH3H.js` (468.14 kB).

### 3. Backend Test Suite (Regression Safety)
- Executed `pytest tests -q` inside `backend/.venv`.
- **Result:** **194 / 194 tests passing (100%)** in 3.85s. Zero backend regressions.

---

## 7. Status of All Six Screens

| Screen | File | Backend Endpoints Connected | Static Mock Removed | Status |
|---|---|---|---|---|
| Home | `src/pages/Home.tsx` | `GET /schemes?page_size=6` | Yes | **LIVE & VERIFIED** |
| Browse Schemes | `src/pages/BrowseSchemes.tsx` | `GET /schemes?category=&q=` | Yes | **LIVE & VERIFIED** |
| Scheme Detail | `src/pages/SchemeDetail.tsx` | `GET /schemes/{id}`, `GET /schemes/{id}/provenance` | Yes | **LIVE & VERIFIED** |
| Document Checklist | `src/pages/DocumentChecklist.tsx` | `GET /documents/checklist/{id}`, `POST /documents/checklist/mark`, `GET /schemes/{id}` | Yes | **LIVE & VERIFIED** |
| Eligibility Results | `src/pages/EligibilityResults.tsx` | `POST /eligibility/evaluate`, `GET /schemes` | Yes | **LIVE & VERIFIED** |
| Why Not Eligible | `src/pages/WhyNotEligible.tsx` | `POST /eligibility/evaluate/{id}`, `GET /schemes/{id}`, `POST /eligibility/evaluate` | Yes | **LIVE & VERIFIED** |

---

## 8. Confirmation of Constraints & Scope Boundaries

- **Sprint C / Sprint D / Deployment:** **NOT STARTED**.
- **Backend Code:** **UNTOUCHED**. No routes, schemas, database models, seed data, or RuleEngine logic were changed.
- **Dependencies:** **ZERO** new dependencies or paid cloud APIs added.
- **Stitch UI Design:** 100% preserved with full visual fidelity.

---

## 9. Checkpoint Notice

Batch 2 is **complete, verified, and stopped**. All six core frontend screens are now fully integrated with the live backend. We await your review and direction before proceeding to subsequent roadmap tasks.

