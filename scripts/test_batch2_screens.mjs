/**
 * Yojana Saathi - Sprint B, Step 3, Batch 2 Integration Test Suite
 * Validates frontend integration of DocumentChecklist, EligibilityResults, and WhyNotEligible with FastAPI.
 */

import { test, describe, afterEach } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  fetchDocumentChecklist,
  markDocumentCollected,
  evaluateEligibility,
  evaluateSingleScheme,
  mapUserProfileToCitizenAttributes,
  mapBackendSchemeToFrontend,
} from '../src/services/schemeApi.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

const originalFetch = globalThis.fetch;

describe('Sprint B — Step 3 Batch 2: Static Code & Dependency Audit', () => {
  test('DocumentChecklist.tsx does not import or use MOCK_SCHEMES', () => {
    const content = fs.readFileSync(path.join(ROOT_DIR, 'src/pages/DocumentChecklist.tsx'), 'utf-8');
    assert.doesNotMatch(content, /import\s+{[^}]*MOCK_SCHEMES[^}]*}\s+from/);
    assert.doesNotMatch(content, /MOCK_SCHEMES\.find/);
    assert.match(content, /fetchDocumentChecklist/);
    assert.match(content, /markDocumentCollected/);
  });

  test('EligibilityResults.tsx does not import or use MOCK_SCHEMES', () => {
    const content = fs.readFileSync(path.join(ROOT_DIR, 'src/pages/EligibilityResults.tsx'), 'utf-8');
    assert.doesNotMatch(content, /import\s+{[^}]*MOCK_SCHEMES[^}]*}\s+from/);
    assert.doesNotMatch(content, /MOCK_SCHEMES\.filter/);
    assert.match(content, /evaluateEligibility/);
    assert.match(content, /fetchSchemes/);
    assert.match(content, /mapBackendSchemeToFrontend/);
  });

  test('WhyNotEligible.tsx does not import or use MOCK_SCHEMES', () => {
    const content = fs.readFileSync(path.join(ROOT_DIR, 'src/pages/WhyNotEligible.tsx'), 'utf-8');
    assert.doesNotMatch(content, /import\s+{[^}]*MOCK_SCHEMES[^}]*}\s+from/);
    assert.doesNotMatch(content, /MOCK_SCHEMES\.filter/);
    assert.doesNotMatch(content, /MOCK_SCHEMES\.find/);
    assert.match(content, /evaluateSingleScheme/);
    assert.match(content, /evaluateEligibility/);
  });
});

describe('Sprint B — Step 3 Batch 2: Document Checklist Integration', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('fetchDocumentChecklist includes session_id and lang, preserving mandatory vs optional and CSC flags', async () => {
    const mockChecklistResponse = {
      scheme_id: 'pm-kisan',
      scheme_name: {
        en: 'PM-KISAN Samman Nidhi',
        hi: 'प्रधानमंत्री किसान सम्मान निधि',
        kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಕಿಸಾನ್ ಸಮ್ಮಾನ್ ನಿಧಿ',
        te: 'ప్రధానమంత్రి కిసాన్ సమ్మాన్ నిధి',
      },
      total_documents: 3,
      mandatory_count: 2,
      optional_count: 1,
      collected_count: 1,
      mandatory_collected_count: 1,
      is_complete: false,
      documents: [
        {
          id: 'doc-pmk-aadhaar',
          scheme_id: 'pm-kisan',
          names: { en: 'Aadhaar Card', kn: 'ಆಧಾರ್ ಕಾರ್ಡ್' },
          descriptions: { en: 'Mandatory ID', kn: 'ಕಡ್ಡಾಯ ಗುರುತಿನ ಚೀಟಿ' },
          is_mandatory: true,
          csc_assisted: false,
          issuer: 'UIDAI',
          source_url: 'https://uidai.gov.in',
          is_collected: true,
        },
        {
          id: 'doc-pmk-land',
          scheme_id: 'pm-kisan',
          names: { en: 'Land Ownership Document (RTC/Khatauni)', kn: 'ಭೂ ಒಡೆತನ ದಾಖಲೆ (ಆರ್‌ಟಿಸಿ)' },
          descriptions: { en: 'Updated land record', kn: 'ನವೀಕರಿಸಿದ ಪಹಣಿ' },
          is_mandatory: true,
          csc_assisted: true,
          issuer: 'Revenue Department',
          source_url: 'https://bhoomi.karnataka.gov.in',
          is_collected: false,
        },
        {
          id: 'doc-pmk-photo',
          scheme_id: 'pm-kisan',
          names: { en: 'Passport Photo', kn: 'ಭಾವಚಿತ್ರ' },
          descriptions: { en: 'Recent photo', kn: 'ಇತ್ತೀಚಿನ ಭಾವಚಿತ್ರ' },
          is_mandatory: false,
          csc_assisted: true,
          issuer: 'Self',
          is_collected: false,
        },
      ],
      source_citation: { title: 'PM-KISAN Guidelines' },
      official_portal_url: 'https://pmkisan.gov.in',
      disclaimer: { en: 'Verification required' },
      session_id: 'c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930',
    };

    let requestedUrl = '';
    globalThis.fetch = async (url) => {
      requestedUrl = url.toString();
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => mockChecklistResponse,
      };
    };

    const res = await fetchDocumentChecklist(
      'pm-kisan',
      'c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930',
      'kn'
    );

    assert.match(requestedUrl, /\/documents\/checklist\/pm-kisan\?/);
    assert.match(requestedUrl, /session_id=c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930/);
    assert.match(requestedUrl, /lang=kn/);

    assert.strictEqual(res.scheme_id, 'pm-kisan');
    assert.strictEqual(res.total_documents, 3);
    assert.strictEqual(res.mandatory_count, 2);
    assert.strictEqual(res.optional_count, 1);
    assert.strictEqual(res.documents[1].csc_assisted, true);
    assert.strictEqual(res.documents[0].is_collected, true);
  });

  test('markDocumentCollected executes POST with exact payload and updates collection status', async () => {
    let capturedMethod = '';
    let capturedBody = null;

    globalThis.fetch = async (url, init) => {
      capturedMethod = init?.method || '';
      capturedBody = JSON.parse(init?.body || '{}');
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          scheme_id: 'pm-kisan',
          scheme_name: { en: 'PM-KISAN' },
          total_documents: 1,
          mandatory_count: 1,
          optional_count: 0,
          collected_count: 1,
          mandatory_collected_count: 1,
          is_complete: true,
          documents: [
            {
              id: 'doc-pmk-land',
              scheme_id: 'pm-kisan',
              names: { en: 'Land Record' },
              descriptions: { en: 'RTC' },
              is_mandatory: true,
              csc_assisted: true,
              issuer: 'Revenue',
              is_collected: true,
            },
          ],
          source_citation: {},
          official_portal_url: 'https://pmkisan.gov.in',
          disclaimer: {},
          session_id: 'c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930',
        }),
      };
    };

    const res = await markDocumentCollected({
      session_id: 'c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930',
      scheme_id: 'pm-kisan',
      document_id: 'doc-pmk-land',
      is_collected: true,
    });

    assert.strictEqual(capturedMethod, 'POST');
    assert.strictEqual(capturedBody.session_id, 'c9b4e120-7f2a-4a8e-9d21-6b45f1e8a930');
    assert.strictEqual(capturedBody.scheme_id, 'pm-kisan');
    assert.strictEqual(capturedBody.document_id, 'doc-pmk-land');
    assert.strictEqual(capturedBody.is_collected, true);
    assert.strictEqual(res.is_complete, true);
    assert.strictEqual(res.documents[0].is_collected, true);
  });
});

describe('Sprint B — Step 3 Batch 2: Eligibility Results Evaluation', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('evaluateEligibility submits sanitized citizen attributes without fabricated defaults', async () => {
    const rawProfile = {
      name: 'Ramesh Kumar',
      age: 38,
      gender: 'Male',
      annualIncome: 120000,
      occupation: 'Farmer (< 2 Hectares)',
      landholdingHectares: 1.2,
      socialCategory: 'OBC',
      hasBPLCard: true,
      isDifferentlyAbled: false,
    };

    const citizenAttrs = mapUserProfileToCitizenAttributes(rawProfile);
    assert.strictEqual(citizenAttrs.name, undefined); // Zero-knowledge: name never sent to rule engine
    assert.strictEqual(citizenAttrs.age, 38);
    assert.strictEqual(citizenAttrs.gender, 'male');
    assert.strictEqual(citizenAttrs.annual_income_inr, 120000);
    assert.strictEqual(citizenAttrs.landholding_hectares, 1.2);
    assert.strictEqual(citizenAttrs.has_bpl_card, true);
    assert.strictEqual(citizenAttrs.is_differently_abled, false);

    let capturedPayload = null;
    globalThis.fetch = async (url, init) => {
      capturedPayload = JSON.parse(init?.body || '{}');
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          results: [
            {
              scheme_id: 'pm-kisan',
              scheme_name: { en: 'PM-KISAN Samman Nidhi' },
              status: 'ELIGIBLE',
              rule_completeness: 'PARTIAL',
              summary: { en: 'Met preliminary eligibility conditions' },
              conditions_satisfied: [
                {
                  condition_id: 'c1',
                  field: 'occupation',
                  operator: 'in',
                  target_value: ['Farmer'],
                  status: 'SATISFIED',
                  reason: { en: 'Small and marginal farmer category verified' },
                },
              ],
              conditions_failed: [],
              missing_information: [],
              unresolved_criteria: [],
              disclaimer: { en: 'Disclaimer' },
              source_citations: [],
            },
          ],
          evaluated_at: '2026-11-11T12:00:00Z',
          preferred_language: 'en',
        }),
      };
    };

    const res = await evaluateEligibility({
      citizen_attributes: citizenAttrs,
      preferred_language: 'en',
    });

    assert.strictEqual(capturedPayload.citizen_attributes.name, undefined);
    assert.strictEqual(capturedPayload.citizen_attributes.age, 38);
    assert.strictEqual(res.results.length, 1);
    assert.strictEqual(res.results[0].status, 'ELIGIBLE');
    assert.strictEqual(res.results[0].conditions_satisfied.length, 1);
  });

  test('missing attributes produce POSSIBLY_ELIGIBLE with missing prompts instead of false outcomes', async () => {
    // Completely empty profile
    const emptyAttrs = mapUserProfileToCitizenAttributes({});
    assert.deepStrictEqual(emptyAttrs, {});

    globalThis.fetch = async () => {
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({
          results: [
            {
              scheme_id: 'pm-kisan',
              scheme_name: { en: 'PM-KISAN' },
              status: 'POSSIBLY_ELIGIBLE',
              rule_completeness: 'PARTIAL',
              summary: { en: 'Further information required' },
              conditions_satisfied: [],
              conditions_failed: [],
              missing_information: [
                {
                  field: 'occupation',
                  prompt: { en: 'Please state your primary occupation', hi: 'कृपया अपना मुख्य व्यवसाय बताएं' },
                  expected_type: 'string',
                },
                {
                  field: 'landholding_hectares',
                  prompt: { en: 'Please specify your agricultural landholding size in hectares', hi: 'कृपया कृषि भूमि का आकार बताएं' },
                  expected_type: 'number',
                },
              ],
              unresolved_criteria: [],
              disclaimer: {},
              source_citations: [],
            },
          ],
          evaluated_at: '2026-11-11T12:00:00Z',
          preferred_language: 'en',
        }),
      };
    };

    const res = await evaluateEligibility({
      citizen_attributes: emptyAttrs,
      preferred_language: 'en',
    });

    assert.strictEqual(res.results[0].status, 'POSSIBLY_ELIGIBLE');
    assert.strictEqual(res.results[0].missing_information.length, 2);
    assert.strictEqual(res.results[0].missing_information[0].field, 'occupation');
  });
});

describe('Sprint B — Step 3 Batch 2: Why Not Eligible Single Scheme Evaluation', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test('evaluateSingleScheme retrieves failed conditions with authoritative citations and clause references', async () => {
    const maleAttrs = { gender: 'male', age: 38 };

    const mockSingleResult = {
      scheme_id: 'pmmvy',
      scheme_name: {
        en: 'Pradhan Mantri Matru Vandana Yojana',
        hi: 'प्रधानमंत्री मातृ वंदना योजना',
        kn: 'ಪ್ರಧಾನಮಂತ್ರಿ ಮಾತೃ ವಂದನಾ ಯೋಜನೆ',
      },
      status: 'NOT_ELIGIBLE',
      rule_completeness: 'PARTIAL',
      summary: {
        en: 'Ineligible: Male applicant does not meet gender criteria for maternity benefits.',
        hi: 'अपात्र: पुरुष आवेदक मातृत्व लाभ मापदंड को पूर्ण नहीं करता।',
      },
      conditions_satisfied: [],
      conditions_failed: [
        {
          condition_id: 'pmmvy_c_gender',
          field: 'gender',
          operator: 'eq',
          target_value: 'female',
          citizen_value: 'male',
          status: 'FAILED',
          reason: {
            en: 'Applicant must be female (pregnant woman or lactating mother).',
            hi: 'आवेदक का महिला (गर्भवती या स्तनपान कराने वाली माता) होना आवश्यक है।',
            kn: 'ಅರ್ಜಿದಾರರು ಮಹಿಳೆಯಾಗಿರಬೇಕು (ಗರ್ಭಿಣಿ ಅಥವಾ ಹಾಲುಣಿಸುವ ತಾಯಿ).',
          },
          citation: {
            source_id: 'GOI-MWCD-PMMVY-2022',
            clause: 'Section 4 (Target Beneficiaries), Clause 4.1',
            url: 'https://www.wcd.gov.in/offerings/pradhan-mantri-matru-vandana-yojana',
            page_ref: 'Page 5',
          },
        },
      ],
      missing_information: [
        {
          field: 'is_pregnant_or_lactating',
          prompt: { en: 'Are you currently pregnant or a lactating mother?' },
          expected_type: 'boolean',
        },
      ],
      unresolved_criteria: [],
      disclaimer: { en: 'Official verification disclaimer' },
      source_citations: [],
    };

    let targetUrl = '';
    globalThis.fetch = async (url) => {
      targetUrl = url.toString();
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => mockSingleResult,
      };
    };

    const res = await evaluateSingleScheme('pmmvy', maleAttrs, 'en');

    assert.match(targetUrl, /\/eligibility\/evaluate\/pmmvy$/);
    assert.strictEqual(res.scheme_id, 'pmmvy');
    assert.strictEqual(res.status, 'NOT_ELIGIBLE');
    assert.strictEqual(res.conditions_failed.length, 1);
    assert.strictEqual(res.conditions_failed[0].field, 'gender');
    assert.strictEqual(res.conditions_failed[0].citizen_value, 'male');
    assert.strictEqual(res.conditions_failed[0].citation.clause, 'Section 4 (Target Beneficiaries), Clause 4.1');
    assert.strictEqual(res.conditions_failed[0].citation.source_id, 'GOI-MWCD-PMMVY-2022');

    // Confirms missing information is separated and not lumped into failed conditions
    assert.strictEqual(res.missing_information.length, 1);
    assert.strictEqual(res.missing_information[0].field, 'is_pregnant_or_lactating');
  });

  test('evaluateSingleScheme handles 404 for invalid scheme slug cleanly', async () => {
    globalThis.fetch = async () => {
      return {
        ok: false,
        status: 404,
        headers: new Headers({ 'Content-Type': 'application/json' }),
        json: async () => ({ detail: 'Scheme non-existent-scheme not found in catalog' }),
      };
    };

    await assert.rejects(
      async () => {
        await evaluateSingleScheme('non-existent-scheme', { age: 30 }, 'en');
      },
      (err) => {
        assert.strictEqual(err.status, 404);
        assert.strictEqual(err.name, 'SchemeApiError');
        return true;
      }
    );
  });
});

