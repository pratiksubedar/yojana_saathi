import type { Language } from '../types/index.ts';

export interface UncertainTerm {
  rawTerm: string;
  candidates: string[];
  message: string;
  contextSnippet: string;
}

export interface TranscriptCorrectionResult {
  rawTranscript: string;
  correctedTranscript: string;
  appliedCorrections: { from: string; to: string }[];
  uncertainTerms: UncertainTerm[];
  hasChanges: boolean;
}

export const DOMAIN_VOCABULARY = {
  landAndAgriculture: [
    'hectare',
    'hectares',
    'acre',
    'acres',
    'agricultural land',
    'landholding',
    'farmer',
    'cultivator',
    'tenant farmer',
    'irrigation',
    'crop',
    'livestock',
    'Kisan Credit Card',
  ],
  schemeNames: [
    'PM-KISAN',
    'PM-KUSUM',
    'PM-KMY',
    'PM-JAY',
    'PMAY-G',
    'PM-SVANidhi',
    'PMMVY',
    'Ayushman Bharat',
    'MGNREGA',
    'Gruha Lakshmi',
    'Gruha Jyothi',
    'Yuva Nidhi',
    'Shakti',
    'Anna Bhagya',
  ],
  eligibilityTerms: [
    'annual income',
    'household income',
    'individual income',
    'caste category',
    'land ownership',
    'pension',
    'income tax',
    'government employee',
  ],
};

const SCHEME_NORMALIZATIONS: { pattern: RegExp; replacement: string }[] = [
  { pattern: /\bp\.?\s*m\.?\s*[-\s]?kisan\b|\bpm\s+kissan\b/gi, replacement: 'PM-KISAN' },
  { pattern: /\bp\.?\s*m\.?\s*[-\s]?kusum\b/gi, replacement: 'PM-KUSUM' },
  { pattern: /\bp\.?\s*m\.?\s*[-\s]?kmy\b|\bkisan\s+maandhan\b|\bkisan\s+mandhan\b/gi, replacement: 'PM-KMY' },
  { pattern: /\bp\.?\s*m\.?\s*[-\s]?jay\b|\bayushman\s+card\b/gi, replacement: 'PM-JAY' },
  { pattern: /\bp\.?\s*m\.?\s*a\.?\s*y\.?\s*[-\s]?g\b/gi, replacement: 'PMAY-G' },
  { pattern: /\bp\.?\s*m\.?\s*[-\s]?svanidhi\b|\bpm\s+swanidhi\b|\bswanidhi\b/gi, replacement: 'PM-SVANidhi' },
  { pattern: /\bp\.?\s*m\.?\s*m\.?\s*v\.?\s*y\.?\b|\bmatru\s+vandana\b/gi, replacement: 'PMMVY' },
  { pattern: /\bayushman\s+bharat\b|\bayushmaan\s+bharat\b/gi, replacement: 'Ayushman Bharat' },
  { pattern: /\bmgnrega\b|\bmanrega\b|\bnrega\b/gi, replacement: 'MGNREGA' },
  { pattern: /\bkisan\s+credit\s+card\b|\bkcc\s+card\b/gi, replacement: 'Kisan Credit Card' },
  { pattern: /\bpm\s+vishwakarma\b|\bvishwakarma\s+yojana\b/gi, replacement: 'PM Vishwakarma' },
  { pattern: /\bsukanya\s+samriddhi\b|\bsukanya\s+yojana\b/gi, replacement: 'Sukanya Samriddhi Yojana' },
  { pattern: /\bpm\s+surya\s+ghar\b|\bsurya\s+ghar\b/gi, replacement: 'PM Surya Ghar' },
  { pattern: /\bujjwala\s+yojana\b|\bujjwala\s+2\.?0?\b|\bujjwala\b/gi, replacement: 'PM Ujjwala Yojana' },
  { pattern: /\bjan\s+dhan\s+yojana\b|\bjandhan\b|\bpmjdy\b/gi, replacement: 'PM Jan Dhan Yojana' },
  { pattern: /\bshram\s+yogi\s+maandhan\b|\bshram\s+yogi\b|\bpmsym\b/gi, replacement: 'PM Shram Yogi Maandhan' },
  { pattern: /\bgruha\s+lakshmi\b|\bgriha\s+lakshmi\b/gi, replacement: 'Gruha Lakshmi' },
  { pattern: /\bgruha\s+jyothi\b|\bgruha\s+jyoti\b/gi, replacement: 'Gruha Jyothi' },
  { pattern: /\byuva\s+nidhi\b/gi, replacement: 'Yuva Nidhi' },
];

/**
 * Normalizes and corrects domain terms in a speech transcript using context-aware rules.
 * Strictly preserves numbers, measurements, negations, and original language.
 * Flags ambiguous terms (such as "actors" near land/numbers) for user confirmation
 * instead of silently guessing between acres and hectares.
 */
export function normalizeDomainTranscript(
  rawText: string,
  language: Language = 'en'
): TranscriptCorrectionResult {
  const rawTranscript = (rawText || '').trim();
  if (!rawTranscript) {
    return {
      rawTranscript: '',
      correctedTranscript: '',
      appliedCorrections: [],
      uncertainTerms: [],
      hasChanges: false,
    };
  }

  let text = rawTranscript;
  const appliedCorrections: { from: string; to: string }[] = [];
  const uncertainTerms: UncertainTerm[] = [];

  // 1. Normalize scheme names (safe, unambiguous)
  for (const rule of SCHEME_NORMALIZATIONS) {
    text = text.replace(rule.pattern, (match) => {
      if (match !== rule.replacement) {
        appliedCorrections.push({ from: match, to: rule.replacement });
      }
      return rule.replacement;
    });
  }

  // 2. Context-aware normalization of land units when near numbers or land/farm/zameen context
  const hasLandOrNumberContext =
    /\b\d+(?:\.\d+)?\s*(?:hectors?|actors?|bighas?|beegah?|बीघा)\b/i.test(text) ||
    /\b(?:land|farm|farmer|cultivator|agricultural|landholding|zameen|जमीन|ಭೂಮಿ|భూమి)\b/i.test(text);

  if (hasLandOrNumberContext) {
    text = text.replace(/\b(\d+(?:\.\d+)?)\s+hectors\b/gi, (match, num) => {
      const rep = `${num} hectares`;
      appliedCorrections.push({ from: match, to: rep });
      return rep;
    });
    text = text.replace(/\b(\d+(?:\.\d+)?)\s+hector\b/gi, (match, num) => {
      const unit = Number(num) === 1 ? 'hectare' : 'hectares';
      const rep = `${num} ${unit}`;
      appliedCorrections.push({ from: match, to: rep });
      return rep;
    });

    // 3. Ambiguous "actors" near numbers and land context: NEVER silently guess acres vs hectares
    text = text.replace(/\b(\d+(?:\.\d+)?)\s+actors\b/gi, (match, num) => {
      uncertainTerms.push({
        rawTerm: match,
        candidates: [`${num} acres`, `${num} hectares`],
        message: 'Please confirm this unit: did you mean acres or hectares?',
        contextSnippet: match,
      });
      return `${num} [acres/hectares?]`;
    });

    // 4. Ambiguous regional land unit "bigha" (varies by state between 0.25 to 0.62 acres): NEVER silently guess
    text = text.replace(/\b(\d+(?:\.\d+)?)\s*(?:bighas?|beegah?|बीघा)\b/gi, (match, num) => {
      uncertainTerms.push({
        rawTerm: match,
        candidates: [`${num} acres`, `${num} hectares`],
        message: 'Regional unit "Bigha" varies by state. Please confirm your land in standard acres or hectares.',
        contextSnippet: match,
      });
      return `${num} [acres/hectares?]`;
    });
  }

  // 5. Clean spacing around punctuation without altering numbers or negations
  if (language === 'en') {
    // Normalize common Indian-English phrasing without changing meaning or numbers
    text = text.replace(/\b(\d+)\s+years\s+old\b/gi, '$1-year-old');
  }

  return {
    rawTranscript,
    correctedTranscript: text,
    appliedCorrections,
    uncertainTerms,
    hasChanges: text !== rawTranscript,
  };
}

