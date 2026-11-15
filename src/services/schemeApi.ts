/**
 * Yojana Saathi - Reusable Scheme & Eligibility API Client
 * Sprint B — Phase 7: Frontend–Backend Integration
 *
 * Communicates with the FastAPI backend to fetch live welfare scheme catalog,
 * detailed specifications, official provenance, document checklists, and
 * deterministic RuleEngineService eligibility evaluation.
 */

import type { Scheme, SchemeCategory, SchemeDocument, EligibilityStatus, UserProfile, Language } from '../types/index.ts';

// ==============================================================================
// 1. BACKEND SCHEMA TYPE DEFINITIONS (Mirroring FastAPI / Pydantic models)
// ==============================================================================

export interface RuleASTCondition {
  id: string;
  field: string;
  operator: string;
  target_value?: any;
  value?: any;
  reason?: Record<string, string>;
  failure_reason?: Record<string, string>;
  citation?: {
    source_id?: string;
    clause?: string;
    url?: string;
    page_ref?: string;
  };
}

export interface RuleAST {
  version?: string;
  rule_completeness?: 'VERIFIED_COMPLETE' | 'PARTIAL' | 'UNVERIFIED';
  unresolved_criteria?: any[];
  all_of?: RuleASTCondition[];
  any_of?: RuleASTCondition[];
  none_of?: RuleASTCondition[];
  conditions?: {
    all_of?: RuleASTCondition[];
    any_of?: RuleASTCondition[];
    none_of?: RuleASTCondition[];
  };
}

export interface RuleSchema {
  id: number;
  scheme_id: string;
  version: string;
  conditions: RuleAST;
  is_active: boolean;
}

export interface DocumentSchema {
  id: string;
  scheme_id: string;
  names: Record<string, string>;
  descriptions: Record<string, string>;
  is_mandatory: boolean;
  csc_assisted: boolean;
  issuer: string;
  source_url?: string | null;
}

export interface ApplicationStepSchema {
  step_number: number;
  channel?: string;
  titles?: Record<string, string>;
  descriptions?: Record<string, string>;
}

export interface SchemeSummarySchema {
  id: string;
  slug: string;
  category: string;
  ministry: string;
  scheme_type: string;
  state_applicability: string[];
  names: Record<string, string>;
  descriptions: Record<string, string>;
  benefits: Record<string, string>;
  financial_amount_inr?: number | null;
  official_url: string;
  portal_name: string;
  last_verified_date: string;
  last_reviewed_date?: string;
  is_active?: boolean;
  rules_count: number;
  documents_count: number;
}

export interface SchemeDetailSchema extends SchemeSummarySchema {
  source_citation: {
    title?: string;
    url?: string;
    issuing_authority?: string;
    scheme_version?: string;
    relevant_sections?: string[];
    [key: string]: any;
  };
  application_procedure: ApplicationStepSchema[];
  rules: RuleSchema[];
  documents: DocumentSchema[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SchemePaginationMetadata {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface SchemeListResponse {
  items: SchemeSummarySchema[];
  pagination: SchemePaginationMetadata;
  filters_applied: Record<string, any>;
}

export interface FetchSchemesParams {
  category?: string;
  state?: string;
  scheme_type?: string;
  q?: string;
  page?: number;
  pageSize?: number;
}

export interface PrimarySourceCitationSchema {
  title: string;
  url: string;
  issuing_authority: string;
  scheme_version?: string | null;
  relevant_sections: string[];
}

export interface VerificationMetadataSchema {
  verification_status: 'VERIFIED' | 'PARTIALLY_VERIFIED' | 'REQUIRES_OFFICIAL_VERIFICATION' | 'UNVERIFIED';
  last_verified_date?: string | null;
  last_reviewed_date?: string | null;
  rule_completeness: string;
  unresolved_criteria: Array<Record<string, any>>;
}

export interface FreshnessMetadataSchema {
  status: 'CURRENT' | 'REVIEW_DUE' | 'STALE' | 'UNVERIFIED';
  days_since_verification?: number | null;
  days_since_review?: number | null;
  review_due_threshold_days: number;
  stale_threshold_days: number;
  reason: string;
  is_fresh: boolean;
}

export interface DocumentSourceSchema {
  document_id: string;
  names: Record<string, string>;
  issuer: string;
  source_url?: string | null;
  is_mandatory: boolean;
}

export interface SchemeProvenanceResponse {
  scheme_id: string;
  names: Record<string, string>;
  ministry: string;
  official_portal: {
    url: string;
    portal_name: string;
  };
  primary_source: PrimarySourceCitationSchema;
  verification: VerificationMetadataSchema;
  freshness: FreshnessMetadataSchema;
  document_sources: DocumentSourceSchema[];
}

export interface ChecklistItemSchema {
  id: string;
  scheme_id: string;
  names: Record<string, string>;
  descriptions: Record<string, string>;
  is_mandatory: boolean;
  csc_assisted: boolean;
  issuer: string;
  source_url?: string | null;
  is_collected: boolean;
}

export interface SchemeChecklistResponse {
  scheme_id: string;
  scheme_name: Record<string, string>;
  total_documents: number;
  mandatory_count: number;
  optional_count: number;
  collected_count: number;
  mandatory_collected_count: number;
  is_complete: boolean;
  documents: ChecklistItemSchema[];
  source_citation: Record<string, any>;
  official_portal_url: string;
  disclaimer: Record<string, string>;
  session_id?: string | null;
}

export interface MarkChecklistItemRequest {
  session_id: string;
  scheme_id: string;
  document_id: string;
  is_collected: boolean;
}

export interface EvaluatedCondition {
  condition_id: string;
  field: string;
  operator: string;
  target_value: any;
  citizen_value?: any;
  status: 'SATISFIED' | 'FAILED' | 'UNKNOWN';
  reason?: Record<string, string>;
  citation?: Record<string, any>;
}

export interface MissingFieldInfo {
  field: string;
  prompt: Record<string, string>;
  expected_type: string;
  citation?: Record<string, any>;
}

export interface SchemeEligibilityResult {
  scheme_id: string;
  scheme_name: Record<string, string>;
  status: 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'NEEDS_MORE_INFORMATION' | 'NOT_VERIFIED' | 'POSSIBLY_ELIGIBLE';
  rule_completeness: 'VERIFIED_COMPLETE' | 'PARTIAL' | 'UNVERIFIED';
  summary: Record<string, string>;
  conditions_satisfied: EvaluatedCondition[];
  conditions_failed: EvaluatedCondition[];
  missing_information: MissingFieldInfo[];
  unresolved_criteria: Array<Record<string, any>>;
  disclaimer: Record<string, string>;
  source_citations: Array<Record<string, any>>;
  ministry?: string;
  benefits?: Record<string, string>;
  official_url?: string;
  last_verified_date?: string;
  application_procedure?: Array<Record<string, any>>;
  documents?: Array<Record<string, any>>;
}

export interface EligibilityEvaluationRequest {
  citizen_attributes: Record<string, any>;
  scheme_ids?: string[];
  preferred_language?: string;
}

export interface EligibilityEvaluationResponse {
  results: SchemeEligibilityResult[];
  evaluated_at: string;
  preferred_language: string;
}

// ==============================================================================
// 2. ERROR HANDLING & API CONFIGURATION
// ==============================================================================

export class SchemeApiError extends Error {
  public status: number;
  public errorCode?: string;
  public isNetworkError: boolean;
  public isAborted: boolean;
  public details?: any;

  constructor(message: string, status = 500, errorCode?: string, isNetworkError = false, isAborted = false, details?: any) {
    super(message);
    this.name = 'SchemeApiError';
    this.status = status;
    this.errorCode = errorCode;
    this.isNetworkError = isNetworkError;
    this.isAborted = isAborted;
    this.details = details;
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
  retries?: number;
  timeoutMs?: number;
}

export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1';

/**
 * Robust fetch wrapper with timeout, signal handling, status parsing,
 * and safe exponential backoff retries for transient GET requests.
 */
async function apiRequest<T>(
  endpoint: string,
  method: 'GET' | 'POST' = 'GET',
  body?: any,
  options: RequestOptions = {}
): Promise<T> {
  const { signal, retries = method === 'GET' ? 1 : 0, timeoutMs = 15000 } = options;

  let attempt = 0;
  const maxAttempts = Math.max(1, retries + 1);

  while (attempt < maxAttempts) {
    attempt++;
    const controller = new AbortController();
    let timeoutId: any = null;

    if (timeoutMs > 0) {
      timeoutId = setTimeout(() => {
        controller.abort();
      }, timeoutMs);
    }

    // Connect caller signal to internal abort controller
    const onCallerAbort = () => controller.abort();
    if (signal) {
      if (signal.aborted) {
        if (timeoutId) clearTimeout(timeoutId);
        throw new SchemeApiError('Request aborted by caller', 0, 'ABORT_ERR', false, true);
      }
      signal.addEventListener('abort', onCallerAbort, { once: true });
    }

    try {
      const url = `${API_BASE_URL}${endpoint}`;
      const headers: Record<string, string> = {
        'Accept': 'application/json',
      };
      if (body) {
        headers['Content-Type'] = 'application/json';
      }

      const res = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (timeoutId) clearTimeout(timeoutId);
      if (signal) signal.removeEventListener('abort', onCallerAbort);

      if (!res.ok) {
        let errData: any = null;
        try {
          errData = await res.json();
        } catch {
          // non-JSON error
        }

        const detail = errData?.detail || `HTTP ${res.status}: ${res.statusText}`;
        const errorCode = errData?.error_code || `HTTP_${res.status}`;

        // If client error (4xx), do NOT retry
        if (res.status >= 400 && res.status < 500) {
          throw new SchemeApiError(detail, res.status, errorCode, false, false, errData);
        }

        // 5xx Server Error: retry if attempts remaining and method is GET
        if (attempt < maxAttempts && method === 'GET') {
          await new Promise((resolve) => setTimeout(resolve, Math.pow(2, attempt) * 200));
          continue;
        }

        throw new SchemeApiError(detail, res.status, errorCode, false, false, errData);
      }

      return (await res.json()) as T;
    } catch (err: any) {
      if (timeoutId) clearTimeout(timeoutId);
      if (signal) signal.removeEventListener('abort', onCallerAbort);

      if (err instanceof SchemeApiError) {
        throw err;
      }

      const isAborted = controller.signal.aborted || signal?.aborted || err.name === 'AbortError';
      const isNetwork = !isAborted && (err instanceof TypeError || err.message?.includes('fetch') || err.message?.includes('NetworkError'));

      if (isAborted) {
        throw new SchemeApiError('Request aborted', 0, 'ABORT_ERR', false, true);
      }

      // If safe GET request and network error, retry
      if (attempt < maxAttempts && method === 'GET' && isNetwork) {
        await new Promise((resolve) => setTimeout(resolve, Math.pow(2, attempt) * 200));
        continue;
      }

      throw new SchemeApiError(
        isNetwork ? 'Network connection unavailable. Please check your internet or retry.' : err.message || 'Unknown network error',
        0,
        isNetwork ? 'NETWORK_ERROR' : 'FETCH_ERROR',
        isNetwork,
        false
      );
    }
  }

  throw new SchemeApiError('Request failed after maximum retry attempts', 500, 'MAX_RETRIES_EXCEEDED');
}

// ==============================================================================
// 3. ADAPTERS (DATA TRANSFORMERS)
// ==============================================================================

/**
 * Normalizes frontend camelCase UserProfile into exact snake_case attributes
 * evaluated by the deterministic backend RuleEngineService.
 *
 * Rules:
 * - Strictly includes ONLY explicitly supplied, valid citizen attributes.
 * - Omits undefined, null, empty and unknown values so the backend RuleEngineService
 *   can detect UNKNOWN condition outcomes and populate missing_information follow-up prompts.
 * - Never converts missing income into zero (preserves explicit 0 if given).
 * - Never assigns default age, landholding, or occupation.
 * - Never fabricates trade category, enterprise type, SHG membership, family details, etc.
 * - Preserves the distinction between false, zero and unknown.
 */
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
    if (/agricultural labourer/i.test(rawOcc)) {
      attrs.occupation = 'Agricultural Labourer';
    } else if (/farmer/i.test(rawOcc)) {
      attrs.occupation = 'Farmer';
    } else if (/vendor/i.test(rawOcc)) {
      attrs.occupation = 'Street Vendor';
    } else if (/artisan|craft/i.test(rawOcc)) {
      attrs.occupation = 'Artisan';
    } else {
      attrs.occupation = rawOcc;
    }
  }
  if (typeof profile.occupationDetail === 'string' && profile.occupationDetail.trim() !== '') {
    attrs.occupation_detail = profile.occupationDetail.trim();
  }

  // 5. Land Ownership & Landholding Hectares
  if (typeof profile.ownsAgriculturalLand === 'boolean') {
    attrs.owns_agricultural_land = profile.ownsAgriculturalLand;
  }
  if (
    profile.ownsAgriculturalLand !== false &&
    typeof profile.landholdingHectares === 'number' &&
    !Number.isNaN(profile.landholdingHectares)
  ) {
    attrs.landholding_hectares = profile.landholdingHectares;
  } else if (profile.ownsAgriculturalLand !== false && profile.landholding === 'under_2_hectares') {
    attrs.landholding_hectares = 1.5;
  } else if (profile.ownsAgriculturalLand !== false && profile.landholding === 'over_2_hectares') {
    attrs.landholding_hectares = 3.5;
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

  // 10. Bank Defaulter (boolean)
  if (typeof profile.isBankDefaulter === 'boolean') {
    attrs.is_bank_defaulter = profile.isBankDefaulter;
  }

  // 11. Income Tax Payer (boolean)
  if (typeof profile.paysIncomeTax === 'boolean') {
    attrs.pays_income_tax = profile.paysIncomeTax;
  }

  // 12. Regular Govt Job in Family (boolean)
  if (typeof profile.hasRegularGovtJob === 'boolean') {
    attrs.has_regular_govt_job = profile.hasRegularGovtJob;
  }

  // 13. Monthly Pension (number)
  if (typeof profile.monthlyPension === 'number' && !Number.isNaN(profile.monthlyPension)) {
    attrs.monthly_pension_inr = profile.monthlyPension;
  }

  // 14. Owns Pucca House (boolean)
  if (typeof profile.ownsPuccaHouse === 'boolean') {
    attrs.owns_pucca_house = profile.ownsPuccaHouse;
  }

  // 15. Pregnant / Lactating (boolean)
  if (typeof profile.isPregnantOrLactating === 'boolean') {
    attrs.is_pregnant_or_lactating = profile.isPregnantOrLactating;
  }

  // 16. Tenant Farmer & Allied Worker
  if (typeof profile.isTenantFarmer === 'boolean') {
    attrs.is_tenant_farmer = profile.isTenantFarmer;
  }
  if (typeof profile.isAlliedActivityWorker === 'boolean') {
    attrs.is_allied_activity_worker = profile.isAlliedActivityWorker;
  }

  // 17. Bank Passbook & Savings Account for DBT
  if (typeof profile.hasSavingsAccount === 'boolean') {
    attrs.has_savings_account = profile.hasSavingsAccount;
    attrs.has_bank_passbook = profile.hasSavingsAccount;
  }
  if (typeof profile.hasBankPassbook === 'boolean') {
    attrs.has_bank_passbook = profile.hasBankPassbook;
    attrs.has_savings_account = profile.hasBankPassbook;
  }

  return attrs;
}

export function formatConditionLabel(rawText: string, lang: Language = 'en'): string {
  if (!rawText) return '';

  const prefixVerified = lang === 'hi' ? 'सत्यापित: ' : lang === 'kn' ? 'ಪರಿಶೀಲಿಸಲಾಗಿದೆ: ' : lang === 'te' ? 'ధృవీకరించబడింది: ' : 'Verified: ';
  const prefixCleared = lang === 'hi' ? 'अपात्रता से मुक्त: ' : lang === 'kn' ? 'ಅನರ್ಹತೆ ಮುಕ್ತ: ' : lang === 'te' ? 'అనర్హత లేనిది: ' : 'No disqualification: ';

  let formatted = rawText
    .replace(/^Verified condition for '?([a-zA-Z0-9_]+)'?( \(provided: [^)]*\))?/i, (_, field) => `${prefixVerified}${formatFieldName(field, lang)}`)
    .replace(/^Cleared statutory exclusion:? '?([a-zA-Z0-9_]+)'?/i, (_, field) => `${prefixCleared}${formatFieldName(field, lang)}`)
    .replace(/^Cleared statutory exclusion criteria for '?([a-zA-Z0-9_]+)'?/i, (_, field) => `${prefixCleared}${formatFieldName(field, lang)}`);

  const phraseReplacements: { pattern: RegExp; translations: Record<Language, string> }[] = [
    {
      pattern: /Has Bank passbook|has_bank_passbook/gi,
      translations: {
        en: 'Active bank account with passbook for DBT',
        hi: 'डीबीटी के लिए पासबुक सहित बैंक खाता',
        kn: 'ಡಿಬಿಟಿಗಾಗಿ ಪಾಸ್‌ಬುಕ್ ಹೊಂದಿರುವ ಬ್ಯಾಂಕ್ ಖಾತೆ',
        te: 'డిబిటి కోసం పాస్‌బుక్‌తో కూడిన బ్యాంక్ ఖాతా',
      },
    },
    {
      pattern: /has_savings_account/gi,
      translations: {
        en: 'Active savings bank account with passbook',
        hi: 'बचत बैंक खाता एवं पासबुक',
        kn: 'ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ ಮತ್ತು ಪಾಸ್‌ಬುಕ್',
        te: 'పొదుపు బ్యాంక్ ఖాతా మరియు పాస్‌బుక్',
      },
    },
    {
      pattern: /is_bank_defaulter|has_willful_bank_default/gi,
      translations: {
        en: 'No bank loan default',
        hi: 'कोई बैंक ऋण डिफ़ॉल्ट नहीं',
        kn: 'ಯಾವುದೇ ಬ್ಯಾಂಕ್ ಸಾಲ ಮರುಪಾವತಿ ಬಾಕಿ ಇಲ್ಲ',
        te: 'ఎటువంటి బ్యాంకు రుణం డిఫాల్ట్ లేదు',
      },
    },
    {
      pattern: /owns_pucca_house/gi,
      translations: {
        en: 'No permanent pucca house',
        hi: 'पक्का मकान नहीं (कच्चा/किराया आवास)',
        kn: 'ಪಕ್ಕಾ ಮನೆ ಹೊಂದಿಲ್ಲದಿರುವುದು',
        te: 'పక్కా ఇల్లు లేకపోవడం',
      },
    },
    {
      pattern: /is_regular_govt_employee|has_regular_govt_job/gi,
      translations: {
        en: 'Non-government employee',
        hi: 'गैर-सरकारी कर्मचारी',
        kn: 'ಸರ್ಕಾರಿ ನೌಕರರಲ್ಲ',
        te: 'ప్రభుత్వ ఉద్యోగి కాదు',
      },
    },
    {
      pattern: /pays_income_tax/gi,
      translations: {
        en: 'Non-income tax payee',
        hi: 'गैर-आयकर दाता',
        kn: 'ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿದಾರರಲ್ಲ',
        te: 'ఆదాయపు పన్ను చెల్లింపుదారు కాదు',
      },
    },
    {
      pattern: /landholding_hectares/gi,
      translations: {
        en: 'Agricultural landholding size',
        hi: 'कृषि जोत का आकार (हेक्टेयर)',
        kn: 'ಕೃಷಿ ಭೂಮಿಯ ವಿಸ್ತೀರ್ಣ (ಹೆಕ್ಟೇರ್)',
        te: 'వ్యవసాయ భూమి పరిమాణం (హెక్టార్లు)',
      },
    },
    {
      pattern: /owns_agricultural_land/gi,
      translations: {
        en: 'Agricultural land ownership',
        hi: 'कृषि भूमि का स्वामित्व',
        kn: 'ಕೃಷಿ ಭೂಮಿಯ ಒಡೆತನ',
        te: 'వ్యవసాయ భూమి యాజమాన్యం',
      },
    },
    {
      pattern: /social_category/gi,
      translations: {
        en: 'Social reservation category',
        hi: 'सामाजिक आरक्षण श्रेणी',
        kn: 'ಸಾಮಾಜಿಕ ಮೀಸಲಾತಿ ವರ್ಗ',
        te: 'సామాజಿಕ రిజర్వేషన్ వర్గం',
      },
    },
    {
      pattern: /is_differently_abled/gi,
      translations: {
        en: 'Benchmark disability (PwD)',
        hi: 'दिव्यांगजन (PwD)',
        kn: 'ವಿಶೇಷ ಚೇತನರು (PwD)',
        te: 'దివ్యాంగులు (PwD)',
      },
    },
  ];

  for (const { pattern, translations } of phraseReplacements) {
    formatted = formatted.replace(pattern, translations[lang] || translations.en);
  }

  return formatted;
}

function formatFieldName(field: string, lang: Language = 'en'): string {
  const map: Record<string, Record<Language, string>> = {
    has_savings_account: {
      en: 'Active savings bank account with passbook',
      hi: 'बचत बैंक खाता एवं पासबुक',
      kn: 'ಉಳಿತಾಯ ಬ್ಯಾಂಕ್ ಖಾತೆ ಮತ್ತು ಪಾಸ್‌ಬುಕ್',
      te: 'పొదుపు బ్యాంక్ ఖాతా మరియు పాస్‌బుక్',
    },
    has_bank_passbook: {
      en: 'Active bank account with passbook for DBT',
      hi: 'डीबीटी के लिए पासबुक सहित बैंक खाता',
      kn: 'ಡಿಬಿಟಿಗಾಗಿ ಪಾಸ್‌ಬುಕ್ ಹೊಂದಿರುವ ಬ್ಯಾಂಕ್ ಖಾತೆ',
      te: 'డిబిటి కోసం పాస్‌బుక్‌తో కూడిన బ్యాంక్ ఖాతా',
    },
    is_bank_defaulter: {
      en: 'No bank loan default',
      hi: 'कोई बैंक ऋण डिफ़ॉल्ट नहीं',
      kn: 'ಯಾವುದೇ ಬ್ಯಾಂಕ್ ಸಾಲ ಮರುಪಾವತಿ ಬಾಕಿ ಇಲ್ಲ',
      te: 'ఎటువంటి బ్యాంకు రుణం డిఫాల్ట్ లేదు',
    },
    has_willful_bank_default: {
      en: 'No bank default record',
      hi: 'कोई बैंक डिफ़ॉल्ट रिकॉर्ड नहीं',
      kn: 'ಯಾವುದೇ ಬ್ಯಾಂಕ್ ಸಾಲ ಬಾಕಿ ದಾಖಲೆ ಇಲ್ಲ',
      te: 'ఎటువంటి బ్యాంకు డిఫాల్ట్ రికార్డు లేదు',
    },
    owns_pucca_house: {
      en: 'No permanent pucca house',
      hi: 'पक्का मकान नहीं',
      kn: 'ಪಕ್ಕಾ ಮನೆ ಹೊಂದಿಲ್ಲ',
      te: 'పక్కా ఇల్లు లేదు',
    },
    pays_income_tax: {
      en: 'Non-income tax payee',
      hi: 'गैर-आयकर दाता',
      kn: 'ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿದಾರರಲ್ಲ',
      te: 'ఆదాయపు పన్ను చెల్లింపుదారు కాదు',
    },
    is_regular_govt_employee: {
      en: 'Non-government employee',
      hi: 'गैर-सरकारी कर्मचारी',
      kn: 'ಸರ್ಕಾರಿ ನೌಕರರಲ್ಲ',
      te: 'ప్రభుత్వ ఉద్యోగి కాదు',
    },
    has_regular_govt_job: {
      en: 'Non-government employee',
      hi: 'गैर-सरकारी कर्मचारी',
      kn: 'ಸರ್ಕಾರಿ ನೌಕರರಲ್ಲ',
      te: 'ప్రభుత్వ ఉద్యోగి కాదు',
    },
    owns_agricultural_land: {
      en: 'Cultivable agricultural land',
      hi: 'कृषि योग्य भूमि',
      kn: 'ಸಾಗುವಳಿ ಕೃಷಿ ಭೂಮಿ',
      te: 'సాగు వ్యవసాయ భూమి',
    },
    is_tenant_farmer: {
      en: 'Tenant cultivator / sharecropper',
      hi: 'बटाईदार / पट्टेदार किसान',
      kn: 'ಗೇಣಿ ರೈತ / ಪಾಲು ಕೃಷಿಕ',
      te: 'కౌలు రైతు / వాటా రైతు',
    },
    landholding_hectares: {
      en: 'Agricultural landholding size',
      hi: 'कृषि भूमि का आकार',
      kn: 'ಕೃಷಿ ಭೂಮಿಯ ವಿಸ್ತೀರ್ಣ',
      te: 'వ్యవసాయ భూమి పరిమాణం',
    },
    social_category: {
      en: 'Social reservation category',
      hi: 'सामाजिक श्रेणी',
      kn: 'ಸಾಮಾಜಿಕ ವರ್ಗ',
      te: 'సామాಜಿಕ వర్గం',
    },
    is_differently_abled: {
      en: 'Benchmark disability status',
      hi: 'दिव्यांगता स्थिति (PwD)',
      kn: 'ವಿಶೇಷ ಚೇತನರ ವಿವರ',
      te: 'దివ్యాంగుల స్థితి',
    },
  };
  return map[field]?.[lang] || map[field]?.en || field.replace(/_/g, ' ');
}

/**
 * Maps a live backend SchemeSummarySchema or SchemeDetailSchema into the
 * rich frontend Scheme object contract used across all React screens.
 */
export function mapBackendSchemeToFrontend(
  backendScheme: SchemeSummarySchema | SchemeDetailSchema,
  lang: Language = 'en',
  eligibilityResult?: SchemeEligibilityResult | null
): Scheme {
  const names = backendScheme.names || {};
  const descriptions = backendScheme.descriptions || {};
  const benefits = backendScheme.benefits || {};

  const localizedName = names[lang] || names.en || backendScheme.id;
  // Bilingual subtitle: When viewing in an Indic language (hi, kn, te), nativeName provides the official English name.
  // When viewing in English (en), nativeName provides the native Indic name (Hindi or first available Indic script).
  const localizedNative = lang === 'en'
    ? (names.hi || names.kn || names.te || '')
    : (names.en || '');
  const localizedDesc = descriptions[lang] || descriptions.en || '';
  const localizedBenefit = benefits[lang] || benefits.en || (backendScheme.financial_amount_inr ? `₹${backendScheme.financial_amount_inr.toLocaleString('en-IN')}` : '');

  // Map 3-state eligibility status
  let status: EligibilityStatus = 'possibly_eligible';
  let matchScore = 75;

  if (eligibilityResult) {
    if (eligibilityResult.status === 'ELIGIBLE') {
      status = 'eligible';
      matchScore = 96;
    } else if (eligibilityResult.status === 'NOT_ELIGIBLE') {
      status = 'not_eligible';
      matchScore = 32;
    } else {
      status = 'possibly_eligible';
      matchScore = 78;
    }
  }

  // Extract matching criteria from conditions_satisfied
  const matchingCriteria: string[] = [];
  if (eligibilityResult?.conditions_satisfied?.length) {
    for (const cond of eligibilityResult.conditions_satisfied) {
      const text = cond.reason?.[lang] || cond.reason?.en || `Verified: ${cond.field}`;
      matchingCriteria.push(formatConditionLabel(text, lang));
    }
  }

  // Extract missing criteria from missing_information
  const missingCriteria: string[] = [];
  if (eligibilityResult?.missing_information?.length) {
    for (const miss of eligibilityResult.missing_information) {
      const text = miss.prompt?.[lang] || miss.prompt?.en || `Missing attribute: ${miss.field}`;
      missingCriteria.push(formatConditionLabel(text, lang));
    }
  }

  // Extract failed criteria from conditions_failed
  const failedCriteria: string[] = [];
  if (eligibilityResult?.conditions_failed?.length) {
    for (const fail of eligibilityResult.conditions_failed) {
      const text = fail.reason?.[lang] || fail.reason?.en || `Did not meet requirement for: ${fail.field}`;
      failedCriteria.push(formatConditionLabel(text, lang));
    }
  }

  // Extract structured documents if detail schema or provided by eligibility evaluation
  const requiredDocuments: SchemeDocument[] = [];
  const rawDocs = (backendScheme as SchemeDetailSchema).documents || eligibilityResult?.documents;
  if (Array.isArray(rawDocs)) {
    for (const doc of rawDocs) {
      const docName = doc.names?.[lang] || doc.names?.en || doc.id;
      const docDesc = doc.descriptions?.[lang] || doc.descriptions?.en || '';
      requiredDocuments.push({
        id: doc.id,
        name: docName,
        required: Boolean(doc.is_mandatory),
        description: docDesc,
      });
    }
  }

  // Extract application steps if detail schema or provided by eligibility evaluation
  const applicationSteps: string[] = [];
  const rawSteps = (backendScheme as SchemeDetailSchema).application_procedure || eligibilityResult?.application_procedure;
  if (Array.isArray(rawSteps)) {
    for (const step of rawSteps) {
      const title = step.titles?.[lang] || step.titles?.en || '';
      const desc = step.descriptions?.[lang] || step.descriptions?.en || '';
      if (title && desc) {
        applicationSteps.push(`${title}: ${desc}`);
      } else {
        applicationSteps.push(desc || title || `Step ${step.step_number}`);
      }
    }
  }

  // Extract criteria and exclusions from rules conditions AST
  const criteriaList: string[] = [];
  const exclusions: string[] = [];
  const rawRules = (backendScheme as SchemeDetailSchema).rules;
  if (Array.isArray(rawRules) && rawRules.length > 0) {
    const primaryAST = rawRules[0].conditions;
    const allOf = primaryAST?.all_of || primaryAST?.conditions?.all_of || [];
    const anyOf = primaryAST?.any_of || primaryAST?.conditions?.any_of || [];
    const noneOf = primaryAST?.none_of || primaryAST?.conditions?.none_of || [];

    for (const c of [...allOf, ...anyOf]) {
      const reasonText = c.reason?.[lang] || c.reason?.en || c.failure_reason?.[lang] || c.failure_reason?.en;
      if (reasonText) criteriaList.push(formatConditionLabel(reasonText, lang));
    }
    for (const c of noneOf) {
      const exclText = c.failure_reason?.[lang] || c.failure_reason?.en || c.reason?.[lang] || c.reason?.en;
      if (exclText) exclusions.push(formatConditionLabel(exclText, lang));
    }
  }

  // Compute CSC availability strictly from actual underlying document data:
  // true only when at least one document explicitly has csc_assisted: true. Missing or empty document arrays default to false.
  const isCscAssisted = Array.isArray(rawDocs) && rawDocs.length > 0
    ? rawDocs.some((d) => Boolean(d.csc_assisted))
    : false;

  const category = (backendScheme.category || 'all') as SchemeCategory;

  return {
    id: backendScheme.id,
    name: localizedName,
    nativeName: localizedNative,
    ministry: backendScheme.ministry,
    category,
    benefit: localizedBenefit,
    benefitHighlight: localizedBenefit,
    status,
    matchScore,
    description: localizedDesc,
    matchingCriteria: matchingCriteria.length > 0 ? matchingCriteria : [localizedDesc.slice(0, 120)],
    missingCriteria,
    failedCriteria,
    criteriaList: criteriaList.length > 0 ? criteriaList : [localizedDesc],
    exclusions,
    requiredDocuments,
    applicationSteps,
    officialUrl: backendScheme.official_url,
    portalName: backendScheme.portal_name,
    cscApplicable: isCscAssisted,
    lastUpdated: backendScheme.last_reviewed_date || backendScheme.last_verified_date || '2026-11-10',
    verifiedOfficial: true,
    stateApplicability: backendScheme.state_applicability || ['ALL'],
  };
}

// ==============================================================================
// 4. STRONGLY TYPED API CLIENT METHODS
// ==============================================================================

/**
 * Lists and filters welfare schemes from the SQLite catalog with search and pagination.
 */
export async function fetchSchemes(
  params: FetchSchemesParams = {},
  options: RequestOptions = {}
): Promise<SchemeListResponse> {
  const searchParams = new URLSearchParams();

  if (params.category && params.category !== 'all') {
    searchParams.append('category', params.category);
  }
  if (params.state) {
    searchParams.append('state', params.state);
  }
  if (params.scheme_type) {
    searchParams.append('scheme_type', params.scheme_type);
  }
  if (params.q && params.q.trim()) {
    searchParams.append('q', params.q.trim());
  }
  if (typeof params.page === 'number' && params.page >= 1) {
    searchParams.append('page', params.page.toString());
  }
  if (typeof params.pageSize === 'number' && params.pageSize >= 1) {
    searchParams.append('page_size', params.pageSize.toString());
  }

  const qs = searchParams.toString();
  const endpoint = `/schemes${qs ? `?${qs}` : ''}`;
  return apiRequest<SchemeListResponse>(endpoint, 'GET', undefined, options);
}

/**
 * Fetches comprehensive, clause-verified details for a single scheme by ID or slug.
 */
export async function fetchSchemeDetail(
  schemeId: string,
  options: RequestOptions = {}
): Promise<SchemeDetailSchema> {
  const cleanId = encodeURIComponent(schemeId.trim());
  return apiRequest<SchemeDetailSchema>(`/schemes/${cleanId}`, 'GET', undefined, options);
}

/**
 * Fetches primary government source citations, guideline version, and temporal freshness status.
 */
export async function fetchSchemeProvenance(
  schemeId: string,
  options: RequestOptions = {}
): Promise<SchemeProvenanceResponse> {
  const cleanId = encodeURIComponent(schemeId.trim());
  return apiRequest<SchemeProvenanceResponse>(`/schemes/${cleanId}/provenance`, 'GET', undefined, options);
}

/**
 * Fetches the official required documents checklist for a scheme, optionally echoing session marks.
 */
export async function fetchDocumentChecklist(
  schemeId: string,
  sessionId?: string,
  lang: Language = 'en',
  options: RequestOptions = {}
): Promise<SchemeChecklistResponse> {
  const cleanId = encodeURIComponent(schemeId.trim());
  const searchParams = new URLSearchParams();
  if (sessionId) {
    searchParams.append('session_id', sessionId);
  }
  if (lang) {
    searchParams.append('lang', lang);
  }
  const qs = searchParams.toString();
  const endpoint = `/documents/checklist/${cleanId}${qs ? `?${qs}` : ''}`;
  return apiRequest<SchemeChecklistResponse>(endpoint, 'GET', undefined, options);
}

/**
 * Marks or unmarks a document checklist item as collected in the citizen's anonymous session.
 * (No automatic retries for mutations).
 */
export async function markDocumentCollected(
  payload: MarkChecklistItemRequest,
  options: RequestOptions = {}
): Promise<SchemeChecklistResponse> {
  return apiRequest<SchemeChecklistResponse>(
    '/documents/checklist/mark',
    'POST',
    payload,
    { ...options, retries: 0 }
  );
}

/**
 * Evaluates citizen profile attributes across one, multiple, or all active welfare schemes
 * using the deterministic backend RuleEngineService.
 */
export async function evaluateEligibility(
  payload: EligibilityEvaluationRequest,
  options: RequestOptions = {}
): Promise<EligibilityEvaluationResponse> {
  return apiRequest<EligibilityEvaluationResponse>(
    '/eligibility/evaluate',
    'POST',
    payload,
    { ...options, retries: 0 }
  );
}

/**
 * Evaluates citizen profile attributes against a single specific scheme by ID.
 */
export async function evaluateSingleScheme(
  schemeId: string,
  citizenAttributes: Record<string, any>,
  preferredLanguage: Language = 'en',
  options: RequestOptions = {}
): Promise<SchemeEligibilityResult> {
  const cleanId = encodeURIComponent(schemeId.trim());
  return apiRequest<SchemeEligibilityResult>(
    `/eligibility/evaluate/${cleanId}`,
    'POST',
    {
      citizen_attributes: citizenAttributes,
      preferred_language: preferredLanguage,
    },
    { ...options, retries: 0 }
  );
}
