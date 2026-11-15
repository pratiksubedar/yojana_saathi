/**
 * Yojana Saathi - Sprint B, Step 3, Batch 1 Integration Test Suite
 * Validates frontend integration of Home, BrowseSchemes, and SchemeDetail with FastAPI.
 */

import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  fetchSchemes,
  fetchSchemeDetail,
  fetchSchemeProvenance,
  mapBackendSchemeToFrontend,
} from '../src/services/schemeApi.ts';
import { getLocalizedScheme } from '../src/data/mockSchemes.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

const originalFetch = globalThis.fetch;

describe('Sprint B — Step 3 Batch 1: Static Code & Dependency Audit', () => {
  test('Home.tsx does not import or use MOCK_SCHEMES for rendered schemes', () => {
    const homeContent = fs.readFileSync(path.join(ROOT_DIR, 'src/pages/Home.tsx'), 'utf-8');
    assert.doesNotMatch(homeContent, /import\s+{[^}]*MOCK_SCHEMES[^}]*}\s+from/);
    assert.doesNotMatch(homeContent, /MOCK_SCHEMES\.slice/);
    assert.match(homeContent, /fetchSchemes/);
    assert.match(homeContent, /mapBackendSchemeToFrontend/);
  });

  test('BrowseSchemes.tsx does not import or use MOCK_SCHEMES for filtered schemes', () => {
    const browseContent = fs.readFileSync(path.join(ROOT_DIR, 'src/pages/BrowseSchemes.tsx'), 'utf-8');
    assert.doesNotMatch(browseContent, /import\s+{[^}]*MOCK_SCHEMES[^}]*}\s+from/);
    assert.doesNotMatch(browseContent, /MOCK_SCHEMES\.filter/);
    assert.match(browseContent, /fetchSchemes/);
    assert.match(browseContent, /mapBackendSchemeToFrontend/);
    assert.match(browseContent, /debouncedQuery/);
  });

  test('SchemeDetail.tsx does not import or use MOCK_SCHEMES', () => {
    const detailContent = fs.readFileSync(path.join(ROOT_DIR, 'src/pages/SchemeDetail.tsx'), 'utf-8');
    assert.doesNotMatch(detailContent, /import\s+{[^}]*MOCK_SCHEMES[^}]*}\s+from/);
    assert.doesNotMatch(detailContent, /MOCK_SCHEMES\.find/);
    assert.match(detailContent, /fetchSchemeDetail/);
    assert.match(detailContent, /fetchSchemeProvenance/);
    assert.match(detailContent, /mapBackendSchemeToFrontend/);
  });

  test('getLocalizedScheme preserves live backend mapped schemes (verifiedOfficial)', () => {
    const liveBackendScheme = {
      id: 'pm-kisan',
      name: 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ',
      nativeName: 'PM-KISAN Samman Nidhi', // English subtitle for Indic view
      ministry: 'Ministry of Agriculture',
      category: 'agriculture',
      benefit: '₹6,000 / year',
      benefitHighlight: '₹6,000 / year',
      status: 'eligible',
      matchScore: 95,
      description: 'ಕೃಷಿಕರ ಆದಾಯ ಬೆಂಬಲ ಯೋಜನೆ',
      matchingCriteria: ['Verified Landowner'],
      missingCriteria: [],
      failedCriteria: [],
      criteriaList: ['Small/Marginal farmer'],
      exclusions: ['Income tax payees'],
      requiredDocuments: [],
      applicationSteps: ['Step 1: Visit portal'],
      officialUrl: 'https://pmkisan.gov.in',
      portalName: 'PM-KISAN Portal',
      cscApplicable: true,
      lastUpdated: '2026-11-10',
      verifiedOfficial: true,
    };

    const result = getLocalizedScheme(liveBackendScheme, 'kn');
    // Must NOT be overwritten with mock values
    assert.strictEqual(result.nativeName, 'PM-KISAN Samman Nidhi');
    assert.strictEqual(result.name, 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ');
  });
});

describe('Sprint B — Step 3 Batch 1: Home Screen Live Data & State Handling', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('fetchSchemes({ pageSize: 6 }) fetches and maps top schemes in all 4 languages', async () => {
    const mockApiResponse = {
      items: [
        {
          id: 'pm-kisan',
          slug: 'pm-kisan',
          category: 'agriculture',
          ministry: 'Ministry of Agriculture & Farmers Welfare',
          scheme_type: 'CENTRAL_SECTOR',
          state_applicability: ['ALL'],
          names: {
            en: 'PM-KISAN Samman Nidhi',
            hi: 'प्रधानमंत्री किसान सम्मान निधि',
            kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ',
            te: 'ప్రధానమంత్రి కిసాన్ సమ్మాన్ నిధి',
          },
          descriptions: {
            en: 'Income support of Rs 6,000 per year',
            hi: 'सभी भूमिधारक किसान परिवारों को प्रति वर्ष 6,000 रुपये',
            kn: 'ಎಲ್ಲಾ ಭೂಹಿಡುವಳಿ ಹೊಂದಿರುವ ರೈತ ಕುಟುಂಬಗಳಿಗೆ ವಾರ್ಷಿಕ ರೂ. 6,000',
            te: 'అన్ని భూమి కలిగిన రైతు కుటుంబాలకు సంవత్సరానికి రూ. 6,000',
          },
          benefits: {
            en: '₹6,000 per year',
            hi: '₹6,000 प्रति वर्ष',
            kn: 'ವಾರ್ಷಿಕ ₹6,000',
            te: 'సంవత్సరానికి ₹6,000',
          },
          financial_amount_inr: 6000,
          official_url: 'https://pmkisan.gov.in',
          portal_name: 'PM-KISAN Portal',
          last_verified_date: '2026-10-15',
          last_reviewed_date: '2026-11-10',
          rules_count: 5,
          documents_count: 4,
        },
      ],
      pagination: {
        total: 21,
        page: 1,
        page_size: 6,
        total_pages: 4,
        has_next: true,
        has_prev: false,
      },
      filters_applied: {},
    };

    globalThis.fetch = async (url) => {
      assert.match(url.toString(), /page_size=6/);
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => mockApiResponse,
      };
    };

    const res = await fetchSchemes({ pageSize: 6 });
    assert.strictEqual(res.pagination.total, 21);
    assert.strictEqual(res.items.length, 1);

    // Test multilingual mapping
    const mappedKn = mapBackendSchemeToFrontend(res.items[0], 'kn');
    assert.strictEqual(mappedKn.name, 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ');
    assert.strictEqual(mappedKn.nativeName, 'PM-KISAN Samman Nidhi'); // Bilingual subtitle
    assert.strictEqual(mappedKn.benefit, 'ವಾರ್ಷಿಕ ₹6,000');

    const mappedHi = mapBackendSchemeToFrontend(res.items[0], 'hi');
    assert.strictEqual(mappedHi.name, 'प्रधानमंत्री किसान सम्मान निधि');
    assert.strictEqual(mappedHi.nativeName, 'PM-KISAN Samman Nidhi');

    const mappedEn = mapBackendSchemeToFrontend(res.items[0], 'en');
    assert.strictEqual(mappedEn.name, 'PM-KISAN Samman Nidhi');
    assert.strictEqual(mappedEn.nativeName, 'प्रधानमंत्री किसान सम्मान निधि');
  });
});

describe('Sprint B — Step 3 Batch 1: Browse Schemes Filtering & Debounce', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('omits category filter when category is "all"', async () => {
    let capturedUrl = '';
    globalThis.fetch = async (url) => {
      capturedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          items: [],
          pagination: { total: 0, page: 1, page_size: 50, total_pages: 0, has_next: false, has_prev: false },
          filters_applied: {},
        }),
      };
    };

    await fetchSchemes({ category: undefined, q: undefined, pageSize: 50 });
    assert.doesNotMatch(capturedUrl, /category=/);
    assert.doesNotMatch(capturedUrl, /q=/);
    assert.match(capturedUrl, /page_size=50/);
  });

  test('attaches category filter for specific category e.g. "women_and_child"', async () => {
    let capturedUrl = '';
    globalThis.fetch = async (url) => {
      capturedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          items: [],
          pagination: { total: 0, page: 1, page_size: 50, total_pages: 0, has_next: false, has_prev: false },
          filters_applied: { category: 'women_and_child' },
        }),
      };
    };

    await fetchSchemes({ category: 'women_and_child', pageSize: 50 });
    assert.match(capturedUrl, /category=women_and_child/);
  });

  test('trims search query and omits whitespace to prevent FastAPI 400', async () => {
    let capturedUrl = '';
    globalThis.fetch = async (url) => {
      capturedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          items: [],
          pagination: { total: 0, page: 1, page_size: 50, total_pages: 0, has_next: false, has_prev: false },
          filters_applied: {},
        }),
      };
    };

    // White space only
    await fetchSchemes({ q: '   ', pageSize: 50 });
    assert.doesNotMatch(capturedUrl, /q=/);

    // Valid keyword
    await fetchSchemes({ q: '  kisan  ', pageSize: 50 });
    assert.match(capturedUrl, /q=kisan/);
  });
});

describe('Sprint B — Step 3 Batch 1: Scheme Detail & Provenance Integration', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('fetches full scheme detail, application procedure and rules AST', async () => {
    const mockDetail = {
      id: 'pm-kisan',
      slug: 'pm-kisan',
      category: 'agriculture',
      ministry: 'Ministry of Agriculture & Farmers Welfare',
      scheme_type: 'CENTRAL_SECTOR',
      state_applicability: ['ALL'],
      names: { en: 'PM-KISAN Samman Nidhi', hi: 'पीएम-किसान' },
      descriptions: { en: 'Direct income support', hi: 'प्रत्यक्ष आय सहायता' },
      benefits: { en: '₹6,000 / year', hi: '₹6,000 प्रति वर्ष' },
      financial_amount_inr: 6000,
      official_url: 'https://pmkisan.gov.in',
      portal_name: 'PM-KISAN Portal',
      last_verified_date: '2026-10-15',
      last_reviewed_date: '2026-11-10',
      rules_count: 1,
      documents_count: 2,
      source_citation: {
        title: 'PM-KISAN Operational Guidelines',
        url: 'https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf',
        issuing_authority: 'Department of Agriculture and Farmers Welfare',
      },
      application_procedure: [
        {
          step_number: 1,
          titles: { en: 'Portal Visit', hi: 'पोर्टल पर जाएं' },
          descriptions: {
            en: 'Visit https://pmkisan.gov.in and click Farmers Corner.',
            hi: 'पोर्टल पर जाएं और फार्मर्स कॉर्नर चुनें।',
          },
        },
      ],
      rules: [
        {
          id: 1,
          scheme_id: 'pm-kisan',
          version: '1.0',
          conditions: {
            all_of: [
              {
                id: 'c1',
                field: 'occupation',
                operator: 'in',
                reason: { en: 'Cultivable landholding farmer family', hi: 'कृषि योग्य भूमिधारक किसान परिवार' },
              },
            ],
            none_of: [
              {
                id: 'e1',
                field: 'is_income_tax_payee',
                operator: 'eq',
                failure_reason: { en: 'Income tax payees disqualified', hi: 'आयकर दाता अपात्र हैं' },
              },
            ],
          },
          is_active: true,
        },
      ],
      documents: [
        {
          id: 'doc-1',
          scheme_id: 'pm-kisan',
          names: { en: 'Land Record', hi: 'भूमि रिकॉर्ड' },
          descriptions: { en: 'RTC or Khatauni', hi: 'खतौनी या खसरा' },
          is_mandatory: true,
          csc_assisted: true,
          issuer: 'Revenue Department',
        },
      ],
    };

    globalThis.fetch = async (url) => {
      assert.match(url.toString(), /\/schemes\/pm-kisan$/);
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => mockDetail,
      };
    };

    const detail = await fetchSchemeDetail('pm-kisan');
    const mapped = mapBackendSchemeToFrontend(detail, 'en');

    assert.strictEqual(mapped.id, 'pm-kisan');
    assert.strictEqual(mapped.applicationSteps.length, 1);
    assert.strictEqual(mapped.applicationSteps[0], 'Portal Visit: Visit https://pmkisan.gov.in and click Farmers Corner.');
    assert.strictEqual(mapped.criteriaList.length, 1);
    assert.strictEqual(mapped.criteriaList[0], 'Cultivable landholding farmer family');
    assert.strictEqual(mapped.exclusions.length, 1);
    assert.strictEqual(mapped.exclusions[0], 'Income tax payees disqualified');
    assert.strictEqual(mapped.cscApplicable, true);
  });

  test('fetches scheme provenance with statutory clauses and freshness reason', async () => {
    const mockProvenance = {
      scheme_id: 'pm-kisan',
      names: { en: 'PM-KISAN Samman Nidhi' },
      ministry: 'Ministry of Agriculture',
      official_portal: { url: 'https://pmkisan.gov.in', portal_name: 'PM-KISAN Portal' },
      primary_source: {
        title: 'PM-KISAN Operational Guidelines',
        url: 'https://pmkisan.gov.in/Documents/OperationalGuidelines.pdf',
        issuing_authority: 'Department of Agriculture',
        scheme_version: 'Operational Guidelines (Revised)',
        relevant_sections: [
          'Section 2.1 (Definition of Beneficiary)',
          'Section 3 (Exclusion Categories)',
        ],
      },
      verification: {
        verification_status: 'VERIFIED',
        last_verified_date: '2026-10-15',
        last_reviewed_date: '2026-11-10',
        rule_completeness: 'PARTIAL',
        unresolved_criteria: [
          {
            clause: 'Section 3, Clause (b)',
            description: 'Constitutional post holders requirement',
          },
        ],
      },
      freshness: {
        status: 'CURRENT',
        days_since_verification: 27,
        days_since_review: 1,
        review_due_threshold_days: 90,
        stale_threshold_days: 365,
        reason: 'Authoritatively verified and reviewed 1 day(s) ago.',
        is_fresh: true,
      },
      document_sources: [],
    };

    globalThis.fetch = async (url) => {
      assert.match(url.toString(), /\/schemes\/pm-kisan\/provenance$/);
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => mockProvenance,
      };
    };

    const prov = await fetchSchemeProvenance('pm-kisan');
    assert.strictEqual(prov.primary_source.title, 'PM-KISAN Operational Guidelines');
    assert.strictEqual(prov.primary_source.relevant_sections.length, 2);
    assert.strictEqual(prov.verification.verification_status, 'VERIFIED');
    assert.strictEqual(prov.freshness.is_fresh, true);
  });

  test('handles 404 for nonexistent scheme without throwing uncaught generic exception', async () => {
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 404,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({ detail: 'Scheme invalid-scheme-id not found' }),
      };
    };

    await assert.rejects(
      async () => {
        await fetchSchemeDetail('invalid-scheme-id');
      },
      (err) => {
        assert.strictEqual(err.status, 404);
        assert.strictEqual(err.name, 'SchemeApiError');
        return true;
      }
    );
  });
});
