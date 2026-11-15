# Sprint B — Step 2 Fix & Verification Report

**Project:** Yojana Saathi (Government Scheme Eligibility & Assistance Platform)  
**Milestone:** Phase 7 (Frontend–Backend Integration) — Step 2 Corrections  
**Date:** November 11, 2026  
**Status:** ALL FINDINGS RESOLVED & 100% VERIFIED  

---

## 1. Summary of Changes Applied

All five findings from the code review ([`docs/SPRINT_B_STEP_2_REVIEW.md`](file:///Users/vinodsubedar/Downloads/PS5_hack/docs/SPRINT_B_STEP_2_REVIEW.md)) have been resolved in [`src/services/schemeApi.ts`](file:///Users/vinodsubedar/Downloads/PS5_hack/src/services/schemeApi.ts) and verified via [`scripts/test_scheme_api.mjs`](file:///Users/vinodsubedar/Downloads/PS5_hack/scripts/test_scheme_api.mjs).

---

## 2. Review Findings & Resolution Matrix

| Finding ID | Severity | File & Lines | Description | Exact Fix Applied | Verification Status |
|---|---|---|---|---|---|
| **FIND-B2-01** | **CRITICAL** | `src/services/schemeApi.ts:413-469` | Unsafe defaults (`age: 30`, `annual_income_inr: 0`, `landholding: 0`, `gender: 'male'`) and arbitrary domain fabrications (`trade_category: 'Carpenter (Suthar)'`, `is_shg_member: true`, etc.) | **Completely purged all default values and domain assumptions.** Only explicitly supplied, non-empty attributes are included. Missing attributes are omitted so `RuleEngineService` detects `UNKNOWN` conditions and issues `missing_information` prompts. Explicit 0 and explicit false are preserved. | **RESOLVED & VERIFIED** |
| **FIND-B2-02** | **HIGH** | `src/services/schemeApi.ts:419-434` | Empty/whitespace occupation string (`occupation: ""`) caused the Rule Engine to evaluate `FAILED` instead of `UNKNOWN` | If `profile.occupation` is undefined, null, or empty whitespace (`profile.occupation.trim() === ''`), the `occupation` key is **completely omitted**. | **RESOLVED & VERIFIED** |
| **FIND-B2-03** | **MEDIUM** | `src/services/schemeApi.ts:608-612` | Always-true no-op ternary for CSC availability | Derived strictly from document records: `const isCscAssisted = Array.isArray(rawDocs) && rawDocs.length > 0 ? rawDocs.some((d) => Boolean(d.csc_assisted)) : false;`. True only when at least one document explicitly has `csc_assisted: true`; empty or missing document arrays strictly default to `false`. | **RESOLVED & VERIFIED** |
| **FIND-B2-04** | **MEDIUM** | `src/services/schemeApi.ts:486` | In Indic languages (`hi`, `kn`, `te`), `nativeName` displayed the same Indic text as `name`, producing duplicate titles | `const localizedNative = lang === 'en' ? (names.hi || names.kn || names.te || '') : (names.en || '');`. When viewing in Kannada, Hindi, or Telugu, subtitle cleanly displays the English scheme title (`names.en`). | **RESOLVED & VERIFIED** |
| **FIND-B2-05** | **LOW** | `scripts/test_scheme_api.mjs:57-67` | Unit tests codified unsafe defaulting (`assert.strictEqual(attrs.age, 30)`) | Test suite updated and expanded with 7 new rigorous tests asserting omission of missing fields, preservation of explicit 0 and false, and absence of fabricated attributes. | **RESOLVED & VERIFIED** |

---

## 3. Detailed Code Modifications in `src/services/schemeApi.ts`

### 1. `mapUserProfileToCitizenAttributes` Fix
```typescript
export function mapUserProfileToCitizenAttributes(profile: Partial<UserProfile> | null | undefined): Record<string, any> {
  const attrs: Record<string, any> = {};
  if (!profile) return attrs;

  // 1. Age (numeric, non-null, valid finite number >= 0)
  if (typeof profile.age === 'number' && !Number.isNaN(profile.age)) {
    attrs.age = profile.age;
  } else if (typeof profile.age === 'string' && (profile.age as string).trim() !== '') {
    const parsedAge = Number(profile.age);
    if (!Number.isNaN(parsedAge)) {
      attrs.age = parsedAge;
    }
  }

  // 2. Gender (string, non-empty, normalized to lowercase)
  if (typeof profile.gender === 'string' && profile.gender.trim() !== '') {
    attrs.gender = profile.gender.trim().toLowerCase();
  }

  // 3. State & District (string, non-empty)
  if (typeof profile.state === 'string' && profile.state.trim() !== '') {
    attrs.state = profile.state.trim();
  }
  if (typeof profile.district === 'string' && profile.district.trim() !== '') {
    attrs.district = profile.district.trim();
  }

  // 4. Occupation (string, non-empty; normalize complex descriptors if present)
  if (typeof profile.occupation === 'string' && profile.occupation.trim() !== '') {
    const rawOcc = profile.occupation.trim();
    if (/farmer/i.test(rawOcc)) {
      attrs.occupation = 'Farmer';
    } else if (/vendor/i.test(rawOcc)) {
      attrs.occupation = 'Street Vendor';
    } else if (/artisan|craft/i.test(rawOcc)) {
      attrs.occupation = 'Artisan';
    } else {
      attrs.occupation = rawOcc;
    }
  }

  // 5. Landholding Hectares (numeric, non-null; preserve explicit 0 if supplied)
  if (typeof profile.landholdingHectares === 'number' && !Number.isNaN(profile.landholdingHectares)) {
    attrs.landholding_hectares = profile.landholdingHectares;
  }

  // 6. Annual & Monthly Income (numeric, non-null; preserve explicit 0 if supplied)
  if (typeof profile.annualIncome === 'number' && !Number.isNaN(profile.annualIncome)) {
    attrs.annual_income_inr = profile.annualIncome;
    attrs.monthly_income_inr = Math.round(profile.annualIncome / 12);
  }

  // 7. Social Category (string, non-empty)
  if (typeof profile.socialCategory === 'string' && profile.socialCategory.trim() !== '') {
    attrs.social_category = profile.socialCategory.trim();
  }

  // 8. BPL Card (boolean; preserve explicit true/false)
  if (typeof profile.hasBPLCard === 'boolean') {
    attrs.has_bpl_card = profile.hasBPLCard;
  }

  // 9. Differently Abled (boolean; preserve explicit true/false)
  if (typeof profile.isDifferentlyAbled === 'boolean') {
    attrs.is_differently_abled = profile.isDifferentlyAbled;
  }

  return attrs;
}
```

### 2. Bilingual Subtitle Mapping Fix
```typescript
  const localizedName = names[lang] || names.en || backendScheme.id;
  // Bilingual subtitle: When viewing in an Indic language (hi, kn, te), nativeName provides the official English name.
  // When viewing in English (en), nativeName provides the native Indic name (Hindi or first available Indic script).
  const localizedNative = lang === 'en'
    ? (names.hi || names.kn || names.te || '')
    : (names.en || '');
  const localizedDesc = descriptions[lang] || descriptions.en || '';
```

### 3. CSC Availability Fix
```typescript
  // Compute CSC availability strictly from actual underlying document data:
  // true only when at least one document explicitly has csc_assisted: true. Missing or empty document arrays default to false.
  const isCscAssisted = Array.isArray(rawDocs) && rawDocs.length > 0
    ? rawDocs.some((d) => Boolean(d.csc_assisted))
    : false;
```

---

## 4. Test & Verification Evidence

### 1. Frontend Unit Tests (`npm test -- --run`)
52 unit tests executed across 14 test suites, 100% passing:
- `maps camelCase UserProfile into exact snake_case attributes when explicitly supplied` (PASS)
- `empty or undefined profile produces no fabricated eligibility attributes` (PASS)
- `missing age, income, landholding and occupation are strictly omitted` (PASS)
- `blank whitespace occupation is omitted (does not produce empty string)` (PASS)
- `preserves explicit zero and false where supplied` (PASS)
- `does not fabricate trade category, enterprise type, SHG membership or roof ownership` (PASS)
- `handles vendor and artisan occupation tokens cleanly` (PASS)
- `correctly localizes content into Kannada (kn) and displays English bilingual subtitle` (PASS)
- `correctly sets English bilingual subtitle for Hindi and Telugu` (PASS)
- `CSC availability accurately reflects underlying document csc_assisted flags` (PASS):
  - At least one CSC-assisted document → `true`
  - Documents present but none CSC-assisted → `false`
  - Empty document array → `false`
  - Missing document array → `false`
- `applies live RuleEngineService eligibility evaluation results` (PASS)
- `handles missing optional fields without crashing` (PASS)
- All speech tests (18 tests) (PASS)
- All PWA and offline tests (10 tests) (PASS)

### 2. Frontend Production Build (`npm run build`)
```
> tsc && vite build
vite v6.4.6 building for production...
✓ 2102 modules transformed.
dist/index.html                   1.56 kB │ gzip:   0.77 kB
dist/assets/index-B_g5Hb1W.css   39.00 kB │ gzip:   7.04 kB
dist/assets/index-DNxnapAw.js   423.66 kB │ gzip: 116.15 kB
✓ built in 1.05s
```

### 3. Backend Pytest Suite (`pytest tests -q`)
```
cd backend && PYTHONPATH=. .venv/bin/pytest tests -q
194 passed, 2 warnings in 3.89s
```

---

## 5. Conclusion

All review findings from `docs/SPRINT_B_STEP_2_REVIEW.md` are resolved. No frontend screens were modified. The reusable API client in `src/services/schemeApi.ts` is fully compliant with backend contracts and deterministic eligibility principles, and is ready for Step 3 screen integration.

