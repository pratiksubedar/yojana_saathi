/**
 * Yojana Saathi - Scheme & Eligibility API Client Unit Tests
 * Sprint B — Phase 7: Step 2 Verification
 *
 * Verifies:
 * - mapUserProfileToCitizenAttributes adapter (camelCase -> snake_case)
 * - mapBackendSchemeToFrontend adapter (multilingual localization & status mapping)
 * - Handling of missing optional fields
 * - Strongly-typed fetch methods with query parameters
 * - Error parsing (HTTP 404, 422, 500)
 * - Transient error retry behavior for safe GET requests
 * - Network failure handling
 * - AbortSignal cancellation handling
 */

import { test, describe, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';

import {
  mapUserProfileToCitizenAttributes,
  mapBackendSchemeToFrontend,
  fetchSchemes,
  fetchSchemeDetail,
  fetchSchemeProvenance,
  fetchDocumentChecklist,
  markDocumentCollected,
  evaluateEligibility,
  evaluateSingleScheme,
  SchemeApiError,
  API_BASE_URL,
} from '../src/services/schemeApi.ts';

describe('UserProfile to CitizenAttributes Adapter', () => {
  test('maps camelCase UserProfile into exact snake_case attributes when explicitly supplied', () => {
    const profile = {
      name: 'Ramesh Kumar',
      age: 42,
      state: 'Karnataka',
      district: 'Bengaluru Rural',
      gender: 'Male',
      occupation: 'Small Farmer (< 2 Hectares)',
      landholdingHectares: 1.5,
      annualIncome: 96000,
      socialCategory: 'OBC',
      hasBPLCard: true,
      isDifferentlyAbled: false,
    };

    const attrs = mapUserProfileToCitizenAttributes(profile);

    assert.strictEqual(attrs.age, 42);
    assert.strictEqual(attrs.gender, 'male');
    assert.strictEqual(attrs.state, 'Karnataka');
    assert.strictEqual(attrs.district, 'Bengaluru Rural');
    assert.strictEqual(attrs.occupation, 'Farmer');
    assert.strictEqual(attrs.landholding_hectares, 1.5);
    assert.strictEqual(attrs.annual_income_inr, 96000);
    assert.strictEqual(attrs.monthly_income_inr, 8000);
    assert.strictEqual(attrs.social_category, 'OBC');
    assert.strictEqual(attrs.has_bpl_card, true);
    assert.strictEqual(attrs.is_differently_abled, false);

    // Verify citizen name (PII) is NOT mapped into eligibility attributes
    assert.strictEqual('name' in attrs, false);
  });

  test('empty or undefined profile produces no fabricated eligibility attributes', () => {
    const emptyAttrs = mapUserProfileToCitizenAttributes({});
    assert.deepStrictEqual(emptyAttrs, {}, 'Empty profile must produce an empty attribute map');

    const nullAttrs = mapUserProfileToCitizenAttributes(null);
    assert.deepStrictEqual(nullAttrs, {}, 'Null profile must produce an empty attribute map');

    const undefinedAttrs = mapUserProfileToCitizenAttributes(undefined);
    assert.deepStrictEqual(undefinedAttrs, {}, 'Undefined profile must produce an empty attribute map');
  });

  test('missing age, income, landholding and occupation are strictly omitted', () => {
    const partialProfile = {
      gender: 'Female',
      state: 'Karnataka',
    };
    const attrs = mapUserProfileToCitizenAttributes(partialProfile);

    assert.strictEqual('age' in attrs, false, 'Missing age must be omitted so Rule Engine detects UNKNOWN');
    assert.strictEqual('annual_income_inr' in attrs, false, 'Missing annual income must be omitted');
    assert.strictEqual('monthly_income_inr' in attrs, false, 'Missing monthly income must be omitted');
    assert.strictEqual('landholding_hectares' in attrs, false, 'Missing landholding must be omitted');
    assert.strictEqual('occupation' in attrs, false, 'Missing occupation must be omitted');
    assert.strictEqual(attrs.gender, 'female');
    assert.strictEqual(attrs.state, 'Karnataka');
  });

  test('blank whitespace occupation is omitted (does not produce empty string)', () => {
    const blankOccProfile = {
      age: 28,
      occupation: '   ',
    };
    const attrs = mapUserProfileToCitizenAttributes(blankOccProfile);

    assert.strictEqual(attrs.age, 28);
    assert.strictEqual('occupation' in attrs, false, 'Blank whitespace occupation must be omitted');
  });

  test('preserves explicit zero and false where supplied', () => {
    const zeroProfile = {
      annualIncome: 0,
      landholdingHectares: 0,
      hasBPLCard: false,
      isDifferentlyAbled: false,
    };
    const attrs = mapUserProfileToCitizenAttributes(zeroProfile);

    assert.strictEqual(attrs.annual_income_inr, 0, 'Explicit 0 income must be preserved');
    assert.strictEqual(attrs.monthly_income_inr, 0, 'Explicit 0 monthly income must be preserved');
    assert.strictEqual(attrs.landholding_hectares, 0, 'Explicit 0 landholding must be preserved');
    assert.strictEqual(attrs.has_bpl_card, false, 'Explicit false BPL card must be preserved');
    assert.strictEqual(attrs.is_differently_abled, false, 'Explicit false differently abled must be preserved');
  });

  test('does not fabricate trade category, enterprise type, SHG membership or roof ownership', () => {
    const attrs = mapUserProfileToCitizenAttributes({ age: 25 });

    assert.strictEqual('trade_category' in attrs, false, 'trade_category must never be fabricated');
    assert.strictEqual('enterprise_type' in attrs, false, 'enterprise_type must never be fabricated');
    assert.strictEqual('is_shg_member' in attrs, false, 'is_shg_member must never be fabricated');
    assert.strictEqual('has_girl_child' in attrs, false, 'has_girl_child must never be fabricated');
    assert.strictEqual('has_residential_roof' in attrs, false, 'has_residential_roof must never be fabricated');
    assert.strictEqual('is_regular_govt_employee' in attrs, false, 'is_regular_govt_employee must not be defaulted');
    assert.strictEqual('is_bank_defaulter' in attrs, false, 'is_bank_defaulter must not be defaulted');
    assert.strictEqual('pays_income_tax' in attrs, false, 'pays_income_tax must not be defaulted');
  });

  test('handles vendor and artisan occupation tokens cleanly', () => {
    const vendorProfile = {
      age: 29,
      gender: 'Female',
      occupation: 'Street Vendor / Hawkers',
      annualIncome: 60000,
    };
    const vendorAttrs = mapUserProfileToCitizenAttributes(vendorProfile);
    assert.strictEqual(vendorAttrs.occupation, 'Street Vendor');
    assert.strictEqual(vendorAttrs.gender, 'female');

    const artisanProfile = {
      age: 35,
      occupation: 'Traditional Artisan / Carpenter',
      annualIncome: 72000,
    };
    const artisanAttrs = mapUserProfileToCitizenAttributes(artisanProfile);
    assert.strictEqual(artisanAttrs.occupation, 'Artisan');
  });
});

describe('Backend Scheme to Frontend Scheme Adapter', () => {
  const sampleBackendScheme = {
    id: 'pm-kisan',
    slug: 'pm-kisan',
    category: 'agriculture',
    ministry: 'Ministry of Agriculture & Farmers Welfare',
    scheme_type: 'CENTRAL_SECTOR',
    state_applicability: ['ALL'],
    names: {
      en: 'PM-KISAN Samman Nidhi',
      hi: 'पीएम किसान सम्मान निधि',
      kn: 'ಪಿಎಂ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ',
      te: 'పీఎం కిసాన్ సమ్మాన్ నిధి',
    },
    descriptions: {
      en: 'Income support of Rs 6000 per year for farmer families.',
      hi: 'किसान परिवारों के लिए ₹6,000 प्रति वर्ष की आय सहायता।',
      kn: 'ರೈತ ಕುಟುಂಬಗಳಿಗೆ ವರ್ಷಕ್ಕೆ ₹6,000 ಆದಾಯ ಬೆಂಬಲ.',
      te: 'రైతు కుటుంబాలకు సంవత్సరానికి ₹6,000 ఆదాయ సాయం.',
    },
    benefits: {
      en: '₹6,000 per year in 3 equal installments.',
      hi: '₹6,000 प्रति वर्ष 3 समान किस्तों में।',
      kn: 'ವರ್ಷಕ್ಕೆ ₹6,000 ಮೊತ್ತ 3 ಸಮಾನ ಕಂತುಗಳಲ್ಲಿ.',
      te: 'ఏడాదికి ₹6,000 మొత్తం 3 సమాన వాయిదాలలో.',
    },
    financial_amount_inr: 6000.0,
    official_url: 'https://pmkisan.gov.in',
    portal_name: 'PM-KISAN National Portal',
    last_verified_date: '2026-10-15',
    last_reviewed_date: '2026-11-10',
    rules_count: 1,
    documents_count: 2,
    documents: [
      {
        id: 'doc-pmk-aadhaar',
        scheme_id: 'pm-kisan',
        names: {
          en: 'Aadhaar Card',
          hi: 'आधार कार्ड',
          kn: 'ಆಧಾರ್ ಕಾರ್ಡ್',
          te: 'ఆధార్ కార్డు',
        },
        descriptions: {
          en: 'Mandatory identification proof with linked mobile number.',
          hi: 'लिंक्ड मोबाइल नंबर के साथ अनिवार्य पहचान प्रमाण।',
          kn: 'ಲಿಂಕ್ ಮಾಡಲಾದ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಕಡ್ಡಾಯ ಗುರುತಿನ ಪುರಾವೆ.',
          te: 'లింక్ చేయబడిన మొబైల్ నంబరుతో తప్పనిసరి గుర్తింపు రుజువు.',
        },
        is_mandatory: true,
        csc_assisted: true,
        issuer: 'UIDAI',
        source_url: 'https://uidai.gov.in/',
      },
    ],
    application_procedure: [
      {
        step_number: 1,
        channel: 'ONLINE',
        titles: {
          en: 'Registration',
          hi: 'पंजीकरण',
          kn: 'ನೋಂದಣಿ',
          te: 'నమోదు',
        },
        descriptions: {
          en: 'Visit https://pmkisan.gov.in and click New Farmer Registration.',
          hi: 'पोर्टल पर जाएं और पंजीकरण करें।',
          kn: 'ಪೋರ್ಟಲ್‌ಗೆ ಭೇಟಿ ನೀಡಿ ನೋಂದಾಯಿಸಿ.',
          te: 'పోర్టల్ సందర్శించి నమోదు చేసుకోండి.',
        },
      },
    ],
  };

  test('correctly transforms backend scheme into frontend Scheme structure in English', () => {
    const frontend = mapBackendSchemeToFrontend(sampleBackendScheme, 'en');

    assert.strictEqual(frontend.id, 'pm-kisan');
    assert.strictEqual(frontend.name, 'PM-KISAN Samman Nidhi');
    assert.strictEqual(frontend.nativeName, 'पीएम किसान सम्मान निधि');
    assert.strictEqual(frontend.ministry, 'Ministry of Agriculture & Farmers Welfare');
    assert.strictEqual(frontend.category, 'agriculture');
    assert.strictEqual(frontend.benefit, '₹6,000 per year in 3 equal installments.');
    assert.strictEqual(frontend.status, 'possibly_eligible');
    assert.strictEqual(frontend.officialUrl, 'https://pmkisan.gov.in');
    assert.strictEqual(frontend.portalName, 'PM-KISAN National Portal');
    assert.strictEqual(frontend.verifiedOfficial, true);
    assert.strictEqual(frontend.requiredDocuments.length, 1);
    assert.strictEqual(frontend.requiredDocuments[0].name, 'Aadhaar Card');
    assert.strictEqual(frontend.applicationSteps.length, 1);
    assert.ok(frontend.applicationSteps[0].includes('Registration: Visit https://pmkisan.gov.in'));
  });

  test('correctly localizes content into Kannada (kn) and displays English bilingual subtitle', () => {
    const frontend = mapBackendSchemeToFrontend(sampleBackendScheme, 'kn');

    assert.strictEqual(frontend.name, 'ಪಿಎಂ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ', 'Primary name should be in Kannada');
    assert.strictEqual(frontend.nativeName, 'PM-KISAN Samman Nidhi', 'Subtitle should show English name to avoid duplicate Kannada text');
    assert.strictEqual(frontend.benefit, 'ವರ್ಷಕ್ಕೆ ₹6,000 ಮೊತ್ತ 3 ಸಮಾನ ಕಂತುಗಳಲ್ಲಿ.');
    assert.strictEqual(frontend.description, 'ರೈತ ಕುಟುಂಬಗಳಿಗೆ ವರ್ಷಕ್ಕೆ ₹6,000 ಆದಾಯ ಬೆಂಬಲ.');
    assert.strictEqual(frontend.requiredDocuments[0].name, 'ಆಧಾರ್ ಕಾರ್ಡ್');
    assert.ok(frontend.applicationSteps[0].includes('ನೋಂದಣಿ: ಪೋರ್ಟಲ್‌ಗೆ ಭೇಟಿ ನೀಡಿ'));
  });

  test('correctly sets English bilingual subtitle for Hindi and Telugu', () => {
    const frontendHi = mapBackendSchemeToFrontend(sampleBackendScheme, 'hi');
    assert.strictEqual(frontendHi.name, 'पीएम किसान सम्मान निधि');
    assert.strictEqual(frontendHi.nativeName, 'PM-KISAN Samman Nidhi');

    const frontendTe = mapBackendSchemeToFrontend(sampleBackendScheme, 'te');
    assert.strictEqual(frontendTe.name, 'పీఎం కిసాన్ సమ్మాన్ నిధి');
    assert.strictEqual(frontendTe.nativeName, 'PM-KISAN Samman Nidhi');
  });

  test('CSC availability accurately reflects underlying document csc_assisted flags', () => {
    // 1. At least one CSC-assisted document → true
    const frontendWithCsc = mapBackendSchemeToFrontend(sampleBackendScheme, 'en');
    assert.strictEqual(frontendWithCsc.cscApplicable, true, 'Should be true when at least one document is csc_assisted');

    // 2. Documents present but none CSC-assisted → false
    const nonCscScheme = {
      ...sampleBackendScheme,
      documents: [
        {
          id: 'doc-no-csc-1',
          scheme_id: 'pm-kisan',
          names: { en: 'Direct Online Affidavit' },
          descriptions: { en: 'Self-declaration' },
          is_mandatory: true,
          csc_assisted: false,
          issuer: 'Self',
        },
        {
          id: 'doc-no-csc-2',
          scheme_id: 'pm-kisan',
          names: { en: 'Bank Confirmation' },
          descriptions: { en: 'Bank online letter' },
          is_mandatory: false,
          csc_assisted: false,
          issuer: 'Bank',
        },
      ],
    };
    const frontendWithoutCsc = mapBackendSchemeToFrontend(nonCscScheme, 'en');
    assert.strictEqual(frontendWithoutCsc.cscApplicable, false, 'Should be false when no documents are csc_assisted');

    // 3. Empty document array → false
    const emptyDocsScheme = {
      ...sampleBackendScheme,
      documents: [],
    };
    const frontendEmptyDocs = mapBackendSchemeToFrontend(emptyDocsScheme, 'en');
    assert.strictEqual(frontendEmptyDocs.cscApplicable, false, 'Empty document array must not default to true');

    // 4. Missing document array → false
    const missingDocsScheme = {
      ...sampleBackendScheme,
      documents: undefined,
    };
    const frontendMissingDocs = mapBackendSchemeToFrontend(missingDocsScheme, 'en');
    assert.strictEqual(frontendMissingDocs.cscApplicable, false, 'Missing document array must not default to true');
  });

  test('applies live RuleEngineService eligibility evaluation results', () => {
    const eligibilityResult = {
      scheme_id: 'pm-kisan',
      scheme_name: sampleBackendScheme.names,
      status: 'ELIGIBLE',
      rule_completeness: 'VERIFIED_COMPLETE',
      summary: { en: 'You qualify for all evaluated PM-KISAN criteria.' },
      conditions_satisfied: [
        {
          condition_id: 'c1',
          field: 'occupation',
          operator: 'equals',
          target_value: 'Farmer',
          status: 'SATISFIED',
          reason: { en: 'Applicant is a verified cultivator.' },
        },
      ],
      conditions_failed: [],
      missing_information: [
        {
          field: 'land_registry_doc',
          prompt: { en: 'Please confirm state land record status.' },
          expected_type: 'boolean',
        },
      ],
      unresolved_criteria: [],
      disclaimer: { en: 'Preliminary guidance.' },
      source_citations: [],
    };

    const frontend = mapBackendSchemeToFrontend(sampleBackendScheme, 'en', eligibilityResult);

    assert.strictEqual(frontend.status, 'eligible');
    assert.strictEqual(frontend.matchScore, 96);
    assert.deepStrictEqual(frontend.matchingCriteria, ['Applicant is a verified cultivator.']);
    assert.deepStrictEqual(frontend.missingCriteria, ['Please confirm state land record status.']);
    assert.strictEqual(frontend.failedCriteria?.length, 0);
  });

  test('handles missing optional fields without crashing', () => {
    const bareScheme = {
      id: 'bare-scheme',
      slug: 'bare-scheme',
      category: 'social_welfare',
      ministry: 'Ministry of Social Justice',
      scheme_type: 'CENTRAL_SECTOR',
      state_applicability: ['ALL'],
      names: {},
      descriptions: {},
      benefits: {},
      official_url: 'https://example.gov.in',
      portal_name: 'Portal',
      last_verified_date: '2026-01-01',
      rules_count: 0,
      documents_count: 0,
    };

    const frontend = mapBackendSchemeToFrontend(bareScheme, 'en');

    assert.strictEqual(frontend.id, 'bare-scheme');
    assert.strictEqual(frontend.name, 'bare-scheme');
    assert.strictEqual(frontend.status, 'possibly_eligible');
    assert.deepStrictEqual(frontend.requiredDocuments, []);
    assert.deepStrictEqual(frontend.applicationSteps, []);
  });
});

describe('API Client Methods with Mock Fetch', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('fetchSchemes constructs correct URL and query parameters', async () => {
    let requestedUrl = '';
    globalThis.fetch = async (url) => {
      requestedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        json: async () => ({
          items: [],
          pagination: { total: 0, page: 2, page_size: 10, total_pages: 0, has_next: false, has_prev: true },
          filters_applied: {},
        }),
      };
    };

    const res = await fetchSchemes({
      category: 'agriculture',
      q: 'farmer',
      page: 2,
      pageSize: 10,
    });

    assert.ok(requestedUrl.includes('/schemes?'));
    assert.ok(requestedUrl.includes('category=agriculture'));
    assert.ok(requestedUrl.includes('q=farmer'));
    assert.ok(requestedUrl.includes('page=2'));
    assert.ok(requestedUrl.includes('page_size=10'));
    assert.strictEqual(res.pagination.page, 2);
  });

  test('fetchSchemeDetail fetches scheme by slug', async () => {
    let requestedUrl = '';
    globalThis.fetch = async (url) => {
      requestedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'pm-jay', ministry: 'National Health Authority' }),
      };
    };

    const scheme = await fetchSchemeDetail('pm-jay');
    assert.ok(requestedUrl.endsWith('/schemes/pm-jay'));
    assert.strictEqual(scheme.id, 'pm-jay');
  });

  test('fetchSchemeProvenance calls /schemes/{id}/provenance', async () => {
    let requestedUrl = '';
    globalThis.fetch = async (url) => {
      requestedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        json: async () => ({
          scheme_id: 'pm-kisan',
          primary_source: { title: 'Operational Guidelines' },
          freshness: { is_fresh: true, status: 'CURRENT' },
        }),
      };
    };

    const prov = await fetchSchemeProvenance('pm-kisan');
    assert.ok(requestedUrl.endsWith('/schemes/pm-kisan/provenance'));
    assert.strictEqual(prov.freshness.is_fresh, true);
  });

  test('fetchDocumentChecklist includes session_id and lang', async () => {
    let requestedUrl = '';
    globalThis.fetch = async (url) => {
      requestedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        json: async () => ({
          scheme_id: 'pmay-g',
          total_documents: 3,
          documents: [],
        }),
      };
    };

    const checklist = await fetchDocumentChecklist('pmay-g', '550e8400-e29b-41d4-a716-446655440000', 'hi');
    assert.ok(requestedUrl.includes('/documents/checklist/pmay-g?'));
    assert.ok(requestedUrl.includes('session_id=550e8400-e29b-41d4-a716-446655440000'));
    assert.ok(requestedUrl.includes('lang=hi'));
    assert.strictEqual(checklist.scheme_id, 'pmay-g');
  });

  test('markDocumentCollected executes POST mutation with retries disabled', async () => {
    let requestOptions = null;
    globalThis.fetch = async (url, opts) => {
      requestOptions = opts;
      return {
        ok: true,
        status: 200,
        json: async () => ({ scheme_id: 'pm-kisan', collected_count: 1 }),
      };
    };

    const payload = {
      session_id: '550e8400-e29b-41d4-a716-446655440000',
      scheme_id: 'pm-kisan',
      document_id: 'doc-pmk-aadhaar',
      is_collected: true,
    };

    const result = await markDocumentCollected(payload);
    assert.strictEqual(requestOptions.method, 'POST');
    assert.strictEqual(JSON.parse(requestOptions.body).document_id, 'doc-pmk-aadhaar');
    assert.strictEqual(result.collected_count, 1);
  });

  test('evaluateEligibility executes POST with citizen_attributes', async () => {
    let requestBody = null;
    globalThis.fetch = async (url, opts) => {
      requestBody = JSON.parse(opts.body);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          results: [{ scheme_id: 'pm-kisan', status: 'ELIGIBLE' }],
          evaluated_at: '2026-11-11T12:00:00Z',
          preferred_language: 'kn',
        }),
      };
    };

    const res = await evaluateEligibility({
      citizen_attributes: { age: 35, occupation: 'Farmer' },
      preferred_language: 'kn',
    });

    assert.strictEqual(requestBody.citizen_attributes.occupation, 'Farmer');
    assert.strictEqual(res.results[0].status, 'ELIGIBLE');
  });

  test('evaluateSingleScheme targets /eligibility/evaluate/{id}', async () => {
    let requestedUrl = '';
    globalThis.fetch = async (url, opts) => {
      requestedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        json: async () => ({
          scheme_id: 'pm-jay',
          status: 'POSSIBLY_ELIGIBLE',
          conditions_failed: [],
        }),
      };
    };

    const res = await evaluateSingleScheme('pm-jay', { age: 25 }, 'te');
    assert.ok(requestedUrl.endsWith('/eligibility/evaluate/pm-jay'));
    assert.strictEqual(res.scheme_id, 'pm-jay');
  });
});

describe('API Error Handling and Resilience', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('throws SchemeApiError on 404 without retrying client error', async () => {
    let fetchCount = 0;
    globalThis.fetch = async () => {
      fetchCount++;
      return {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Scheme not found in catalog', error_code: 'SCHEME_NOT_FOUND' }),
      };
    };

    await assert.rejects(
      async () => {
        await fetchSchemeDetail('non-existent-scheme', { retries: 2 });
      },
      (err) => {
        assert.ok(err instanceof SchemeApiError);
        assert.strictEqual(err.status, 404);
        assert.strictEqual(err.errorCode, 'SCHEME_NOT_FOUND');
        assert.strictEqual(err.message, 'Scheme not found in catalog');
        return true;
      }
    );

    // Client error (4xx) must NOT retry
    assert.strictEqual(fetchCount, 1);
  });

  test('retries transient 503 error on safe GET and succeeds on second attempt', async () => {
    let attempt = 0;
    globalThis.fetch = async () => {
      attempt++;
      if (attempt === 1) {
        return {
          ok: false,
          status: 503,
          statusText: 'Service Unavailable',
          json: async () => ({ detail: 'Busy' }),
        };
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'pm-kisan', category: 'agriculture' }),
      };
    };

    const scheme = await fetchSchemeDetail('pm-kisan', { retries: 1 });
    assert.strictEqual(attempt, 2);
    assert.strictEqual(scheme.id, 'pm-kisan');
  });

  test('handles network failure with isNetworkError flag', async () => {
    globalThis.fetch = async () => {
      throw new TypeError('Failed to fetch');
    };

    await assert.rejects(
      async () => {
        await fetchSchemeDetail('pm-kisan', { retries: 0 });
      },
      (err) => {
        assert.ok(err instanceof SchemeApiError);
        assert.strictEqual(err.isNetworkError, true);
        assert.strictEqual(err.errorCode, 'NETWORK_ERROR');
        return true;
      }
    );
  });

  test('handles caller AbortSignal cleanly with isAborted flag', async () => {
    const controller = new AbortController();
    controller.abort();

    await assert.rejects(
      async () => {
        await fetchSchemes({}, { signal: controller.signal });
      },
      (err) => {
        assert.ok(err instanceof SchemeApiError);
        assert.strictEqual(err.isAborted, true);
        assert.strictEqual(err.errorCode, 'ABORT_ERR');
        return true;
      }
    );
  });
});

describe('API Base URL & Reverse Proxy Route Alignment', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('API_BASE_URL defaults to /api/v1', () => {
    assert.strictEqual(API_BASE_URL, '/api/v1', 'API_BASE_URL must default to /api/v1');
  });

  test('API_BASE_URL starts with /api matching Vite dev proxy configuration', () => {
    assert.ok(
      API_BASE_URL.startsWith('/api'),
      `API_BASE_URL (${API_BASE_URL}) must start with /api to route through vite.config.ts proxy`
    );
  });

  test('fetchSchemes constructs exact URL matching backend router (/api/v1/schemes)', async () => {
    let capturedUrl = '';
    globalThis.fetch = async (url) => {
      capturedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, page: 1, page_size: 10, total_pages: 0 }),
      };
    };

    await fetchSchemes({ page: 1, pageSize: 5 });
    assert.ok(
      capturedUrl.startsWith('/api/v1/schemes'),
      `fetchSchemes URL must target /api/v1/schemes, got: ${capturedUrl}`
    );
    assert.ok(capturedUrl.includes('page=1'));
    assert.ok(capturedUrl.includes('page_size=5'));
  });

  test('all endpoint paths use relative paths starting with / ensuring proper proxying', async () => {
    const endpointsTested = [];
    globalThis.fetch = async (url) => {
      endpointsTested.push(url.toString());
      return {
        ok: true,
        status: 200,
        json: async () => ({
          items: [],
          total: 0,
          id: 'test',
          scheme_id: 'test',
          results: [],
          documents: [],
        }),
      };
    };

    await fetchSchemes();
    await fetchSchemeDetail('pm-kisan');
    await fetchSchemeProvenance('pm-kisan');
    await fetchDocumentChecklist('pm-kisan');
    await evaluateEligibility({ citizen_attributes: {} });
    await evaluateSingleScheme('pm-kisan', { citizen_attributes: {} });

    for (const url of endpointsTested) {
      assert.ok(
        url.startsWith('/api/v1/'),
        `Endpoint URL [${url}] must start with /api/v1/ to align with Vite reverse proxy`
      );
    }
  });
});


