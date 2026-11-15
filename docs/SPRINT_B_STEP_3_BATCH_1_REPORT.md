# Sprint B — Step 3 Batch 1 Integration Report

**Project:** Yojana Saathi (Government Scheme Eligibility & Assistance Platform)  
**Milestone:** Phase 7 (Frontend–Backend Integration) — Step 3, Batch 1: Core Screens Integration  
**Date:** November 11, 2026  
**Status:** COMPLETED & VERIFIED (Batch 1 Only)  

---

## 1. Executive Summary

Sprint B Step 3, Batch 1 successfully integrated the first three core frontend screens with the FastAPI backend, removing static mock scheme dependencies (`MOCK_SCHEMES`) from their active user experience while strictly preserving the existing Stitch design, UI layout, components, and zero-cost local architecture.

### Target Screens Completed in Batch 1:
1. `src/pages/Home.tsx` — Connected to live `GET /schemes?page_size=6` via `fetchSchemes({ pageSize: 6 })` with loading skeletons, error recovery, empty state, and responsive multilingual title and metric presentation.
2. `src/pages/BrowseSchemes.tsx` — Connected to live `GET /schemes` via `fetchSchemes({ category, q, pageSize: 50 })` with 300ms query debouncing, 8 category filters (`all`, `agriculture`, `healthcare`, `housing`, `social_welfare`, `employment`, `women_and_child`, `energy`), dynamic counter, loading skeletons, error recovery, and search reset.
3. `src/pages/SchemeDetail.tsx` — Connected to live `GET /schemes/{scheme_id}` and `GET /schemes/{scheme_id}/provenance` via `fetchSchemeDetail(id)` and `fetchSchemeProvenance(id)`. Features official statutory citations, primary source guidelines link, guideline version, issuing authority, temporal freshness assessment, statutory verification notice for unresolved criteria, application procedure, and a dedicated 404 Not Found screen.

---

## 2. Files Modified

| File | Nature of Change | Purpose |
|---|---|---|
| [`src/pages/Home.tsx`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/pages/Home.tsx) | Modified | Replaced `MOCK_SCHEMES.slice(0, 3)` with `fetchSchemes({ pageSize: 6 })` + `mapBackendSchemeToFrontend`. Added loading skeleton cards, error recovery with retry, empty state, dynamic metric count, and language re-mapping. |
| [`src/pages/BrowseSchemes.tsx`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/pages/BrowseSchemes.tsx) | Modified | Replaced client-side mock filtering with backend search and category filtering via `fetchSchemes`. Added 300ms debounce, support for all 8 categories, loading skeletons, error recovery with retry, dynamic results count, and empty state reset. |
| [`src/pages/SchemeDetail.tsx`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/pages/SchemeDetail.tsx) | Modified | Replaced `MOCK_SCHEMES.find` with concurrent `fetchSchemeDetail(id)` and `fetchSchemeProvenance(id)`. Added official statutory citations card, guideline PDF link, guideline version, issuing authority, freshness audit, unresolved criteria advisory, application procedure steps, 404 Not Found card, and error retry state. |
| [`src/data/mockSchemes.ts`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/data/mockSchemes.ts) | Modified | Added guard in `getLocalizedScheme` to preserve live backend mapped schemes (`verifiedOfficial: true`), preventing static mock translations from clobbering live Indic/English strings. |
| [`src/data/translations.ts`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/data/translations.ts) | Modified | Added clean localized UI strings across English, Hindi, Kannada, and Telugu for loading, error, scheme-not-found, and provenance guidelines. |
| [`package.json`](file:///Users/vinodsubedar/Downloads/PS5_hack/package.json) | Modified | Added `scripts/test_batch1_screens.mjs` to `npm test` and added `npm run test:batch1`. |
| [`scripts/test_batch1_screens.mjs`](file:///Users/vinodsubedar/Downloads/PS5_hack/scripts/test_batch1_screens.mjs) | Created | 11 unit/integration tests validating static code separation, live fetching, debouncing, category mapping, provenance display, and 404 handling. |

---

## 3. Endpoints Connected & Actual Response Structures

### 1. `GET /schemes` (`list_schemes`)
- **Query Parameters Sent:**
  - `page_size`: 6 (Home) or 50 (Browse)
  - `category`: optional, omitted if `'all'` or undefined
  - `q`: optional trimmed search string, omitted if empty or whitespace to avoid FastAPI 400 validation error
- **FastAPI Model:** `SchemeListResponse`
  ```json
  {
    "items": [
      {
        "id": "pm-kisan",
        "slug": "pm-kisan",
        "category": "agriculture",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
        "scheme_type": "CENTRAL_SECTOR",
        "state_applicability": ["ALL"],
        "names": { "en": "PM-KISAN Samman Nidhi", "hi": "...", "kn": "...", "te": "..." },
        "descriptions": { "en": "...", "hi": "...", "kn": "...", "te": "..." },
        "benefits": { "en": "₹6,000 per year", "hi": "...", "kn": "...", "te": "..." },
        "financial_amount_inr": 6000,
        "official_url": "https://pmkisan.gov.in",
        "portal_name": "PM-KISAN Portal",
        "last_verified_date": "2026-10-15",
        "last_reviewed_date": "2026-11-10",
        "rules_count": 5,
        "documents_count": 4
      }
    ],
    "pagination": {
      "total": 21,
      "page": 1,
      "page_size": 6,
      "total_pages": 4,
      "has_next": true,
      "has_prev": false
    },
    "filters_applied": {}
  }
  ```

### 2. `GET /schemes/{scheme_id}` (`get_scheme_detail`)
- **Path Parameter:** `scheme_id` (e.g. `pm-kisan` or URL-encoded slug)
- **FastAPI Model:** `SchemeDetailSchema`
  - Includes `application_procedure`: array of `{ step_number, titles, descriptions }`
  - Includes `rules`: array of `RuleSchema` with AST conditions (`all_of`, `any_of`, `none_of`)
  - Includes `documents`: array of `DocumentSchema` with `csc_assisted: boolean`
  - Includes `source_citation`: `{ title, url, issuing_authority, relevant_sections }`

### 3. `GET /schemes/{scheme_id}/provenance` (`get_scheme_provenance`)
- **Path Parameter:** `scheme_id`
- **FastAPI Model:** `SchemeProvenanceResponse`
  - `primary_source`: `{ title, url, issuing_authority, scheme_version, relevant_sections }`
  - `verification`: `{ verification_status, last_verified_date, last_reviewed_date, rule_completeness, unresolved_criteria }`
  - `freshness`: `{ status, days_since_verification, days_since_review, reason, is_fresh }`

---

## 4. Screen-by-Screen Implementation Summary

### Screen 1: `src/pages/Home.tsx`
- **Catalog Integration:** Invokes `fetchSchemes({ pageSize: 6 })` on mount and maps results through `mapBackendSchemeToFrontend(item, language)`. Top 3 items are rendered in the featured section.
- **Dynamic Metric:** Displays live count from `pagination.total` (`21+` schemes indexed) instead of a hardcoded string.
- **Loading Skeleton:** Displays 3 pulsing skeleton cards matching `SchemeCard` dimensions with title, badges, and benefit block placeholders while awaiting API response.
- **Error Recovery:** Catches network or server failures and displays an alert card with clear error description and a "Retry" button that invokes `loadFeaturedSchemes()`.
- **Language Synchronization:** Triggered when the citizen changes language via the header, re-requesting/re-mapping strings in real-time.
- **Zero Mock Dependency:** Static `MOCK_SCHEMES.slice(0, 3)` completely removed from the file.

### Screen 2: `src/pages/BrowseSchemes.tsx`
- **Catalog Integration:** Invokes `fetchSchemes({ category, q, pageSize: 50 })` whenever `debouncedQuery`, `selectedCategory`, or `language` changes.
- **300ms Debounce:** Prevents excessive server roundtrips during citizen text input.
- **Category Support:** Fully supports all 8 categories in the 21-scheme catalog (`all`, `agriculture`, `healthcare`, `housing`, `social_welfare`, `employment`, `women_and_child`, `energy`). When `'all'` is selected, the category parameter is omitted.
- **Whitespace Safety:** Whitespace-only search input is pruned to prevent FastAPI 400 `InvalidFilterException`.
- **Loading Skeleton:** Displays 4 pulsing card skeletons during network flight.
- **Empty State:** When no results match a query or filter, displays a centered card with `SlidersHorizontal` icon and a "View All" button that resets both search input and category.
- **Error Recovery:** Catches API errors, provides an error card with network awareness and a "Retry" button.
- **Zero Mock Dependency:** Client-side `MOCK_SCHEMES.filter()` completely removed.

### Screen 3: `src/pages/SchemeDetail.tsx`
- **Authoritative Detail & Provenance:** Concurrently invokes `fetchSchemeDetail(id)` and `fetchSchemeProvenance(id)`. Provenance failures do not crash the page (gracefully fall back to scheme detail citations).
- **Official Provenance & Verification Display:** Displays official government provenance only when returned by the backend:
  - Official Primary Source title with direct link to official guidelines PDF.
  - Issuing Authority and Guideline Version.
  - Key Statutory Clauses pill tags (`provenance.primary_source.relevant_sections`).
  - Verification status badge (`VERIFIED`) and freshness audit reason.
  - Statutory Verification Notice disclosing unresolved statutory criteria (e.g. CSC physical verification or statutory self-declaration requirement).
- **Application Procedure:** Renders numbered application steps parsed from `scheme.applicationSteps` with step title and description.
- **Speech Synthesis (TTS):** Preserves native voice read-aloud functionality via `useSpeechSynthesis` using live localized name, benefit highlight, and description.
- **State Handling:**
  - **Loading:** Pulsing hero card and criteria skeletons.
  - **404 Not Found:** Renders `ShieldAlert` card explaining the scheme could not be found with a "Back to Scheme Catalog" button navigating to `/browse`.
  - **Error:** Clean error card with "Retry" button.
- **Zero Mock Dependency:** `MOCK_SCHEMES.find()` completely removed.

---

## 5. Verification & Test Results

### 1. Frontend Test Suite
- Executed `npm test` (`scripts/test_speech.mjs`, `scripts/test_pwa_offline.mjs`, `scripts/test_scheme_api.mjs`, `scripts/test_batch1_screens.mjs`).
- **Result:** **63 / 63 tests passing (100%)** across 18 test suites in ~508ms.
  - Audit tests: Confirmed `MOCK_SCHEMES` is not used in `Home.tsx`, `BrowseSchemes.tsx`, or `SchemeDetail.tsx`.
  - Localization tests: Verified Kannada, Hindi, Telugu, and English mapping.
  - Search/Filter tests: Verified debounce, whitespace trimming, and 8 categories.
  - Detail/Provenance tests: Verified rule AST criteria, application steps, statutory clauses, freshness reasons, and 404 handling.

### 2. Production Build Verification
- Executed `npm run build` (`tsc && vite build`).
- **Result:** **Clean compilation in 1.06s** with zero errors or warnings.
  - Assets generated: `dist/assets/index-DqXr4D2R.css` (39.60 kB) and `dist/assets/index-w0q28QRW.js` (445.89 kB).

### 3. Backend Test Suite (Regression Safety)
- Executed `pytest tests -q` inside `backend/.venv`.
- **Result:** **194 / 194 tests passing (100%)** in 3.85s. Zero backend regressions.

---

## 6. Known Limitations or Unresolved Issues

- **None for Batch 1:** All three targeted screens operate seamlessly with the live FastAPI backend, handle loading/error/empty/404 states, and honor multilingual language selections.
- **Mock Data in Other Files:** As per instructions, `src/data/mockSchemes.ts` remains in the project for remaining unintegrated screens and static unit tests, but is completely eliminated from the active code paths of the three Batch 1 screens.

---

## 7. Confirmation of Scope Boundaries

- **Batch 2 Screens:**
  - `src/pages/DocumentChecklist.tsx` — **NOT MODIFIED** (Timestamp verified: Nov 10, 2026).
  - `src/pages/EligibilityResults.tsx` — **NOT MODIFIED** (Timestamp verified: Nov 10, 2026).
  - `src/pages/WhyNotEligible.tsx` — **NOT MODIFIED** (Timestamp verified: Nov 10, 2026).
- **Backend & Database:** No modifications made to backend routes, database schema, SQLite seed data, rule engine, or RAG retriever.
- **Dependencies:** Strictly zero new npm packages or paid external cloud services added.
- **UI/UX Design:** Stitch design, layout, styling, and interactions 100% preserved.

---

## 8. Checkpoint & Stop Notice

Batch 1 is **complete, verified, and stopped**. We await review and approval before starting Batch 2.

