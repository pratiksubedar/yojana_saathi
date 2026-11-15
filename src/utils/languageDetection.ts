import type { Language } from '../types/index.ts';

export interface LanguageDetectionResult {
  detectedLanguage: Language;
  confidence: 'script_match' | 'uncertain';
  isAutoDetected: boolean;
}

export interface EnhancedLanguageDetection {
  detectedLanguage: Language;
  confidence: 'script_match' | 'vocabulary_match' | 'uncertain';
  isAutoDetected: boolean;
  differsFromCurrent: boolean;
  suggestedLanguage: Language;
  candidates: Language[];
  reason?: string;
}

const HINDI_ROMAN_KEYWORDS = [
  'kisan', 'yojana', 'mujhe', 'mera', 'meri', 'kya', 'chahiye', 'kaise', 'pension',
  'kheti', 'sarkari', 'batao', 'patrata', 'namaste', 'nahi', 'haan', 'aavedan',
  'madad', 'paise', 'labh', 'bataiye', 'shiksha', 'awas', 'ghar'
];

const KANNADA_ROMAN_KEYWORDS = [
  'nanna', 'nimage', 'namage', 'yavudu', 'beku', 'yojane', 'yojana', 'raitha', 'raita', 'hege', 'arhathe',
  'sahaya', 'namaskara', 'illa', 'houdu', 'thilisi', 'krishi', 'sarkari', 'hana',
  'bhandu', 'arji', 'maaduvudu', 'maneya'
];

const TELUGU_ROMAN_KEYWORDS = [
  'naa', 'meeku', 'emiti', 'kavali', 'pathakam', 'rythu', 'raitu', 'ela', 'arhatha',
  'sahayam', 'namaskaram', 'ledu', 'avunu', 'cheppandi', 'prabhutva', 'vyavasayam',
  'dabbu', 'darakhastu', 'illu', 'kosam', 'yojana'
];

const ENGLISH_KEYWORDS = [
  'farmer', 'scheme', 'schemes', 'pension', 'eligible', 'eligibility', 'benefit',
  'benefits', 'apply', 'government', 'subsidy', 'loan', 'housing', 'help', 'details',
  'which', 'where', 'income', 'student', 'worker', 'vendor'
];

/**
 * Identifies the likely language of a transcript using Unicode script ranges.
 * Never claims certainty for Latin script because Romanized Hindi/Kannada/Telugu
 * can also be transcribed in Latin characters by browser engines.
 */
export function detectLanguageFromTranscript(
  text: string,
  fallbackLanguage: Language = 'en'
): LanguageDetectionResult {
  const trimmed = (text || '').trim();
  if (!trimmed) {
    return {
      detectedLanguage: fallbackLanguage,
      confidence: 'uncertain',
      isAutoDetected: false,
    };
  }

  // Devanagari Unicode block (Hindi)
  if (/[\u0900-\u097F]/.test(trimmed)) {
    return {
      detectedLanguage: 'hi',
      confidence: 'script_match',
      isAutoDetected: true,
    };
  }

  // Kannada Unicode block
  if (/[\u0C80-\u0CFF]/.test(trimmed)) {
    return {
      detectedLanguage: 'kn',
      confidence: 'script_match',
      isAutoDetected: true,
    };
  }

  // Telugu Unicode block
  if (/[\u0C00-\u0C7F]/.test(trimmed)) {
    return {
      detectedLanguage: 'te',
      confidence: 'script_match',
      isAutoDetected: true,
    };
  }

  // Latin script: could be English or Romanized regional text; never claim high certainty
  return {
    detectedLanguage: fallbackLanguage === 'en' ? 'en' : fallbackLanguage,
    confidence: 'uncertain',
    isAutoDetected: false,
  };
}

/**
 * Enhanced multi-lingual detection comparing user input with the current site language.
 * Identifies native scripts, code-mixed Romanized vocabulary, and uncertainty.
 */
export function detectInputLanguage(
  text: string,
  currentLanguage: Language
): EnhancedLanguageDetection {
  const trimmed = (text || '').trim();
  if (!trimmed) {
    return {
      detectedLanguage: currentLanguage,
      confidence: 'uncertain',
      isAutoDetected: false,
      differsFromCurrent: false,
      suggestedLanguage: currentLanguage,
      candidates: [currentLanguage],
    };
  }

  // 1. Script Match (Highest Confidence)
  if (/[\u0900-\u097F]/.test(trimmed)) {
    return {
      detectedLanguage: 'hi',
      confidence: 'script_match',
      isAutoDetected: true,
      differsFromCurrent: currentLanguage !== 'hi',
      suggestedLanguage: 'hi',
      candidates: ['hi'],
      reason: 'Devanagari script detected',
    };
  }

  if (/[\u0C80-\u0CFF]/.test(trimmed)) {
    return {
      detectedLanguage: 'kn',
      confidence: 'script_match',
      isAutoDetected: true,
      differsFromCurrent: currentLanguage !== 'kn',
      suggestedLanguage: 'kn',
      candidates: ['kn'],
      reason: 'Kannada script detected',
    };
  }

  if (/[\u0C00-\u0C7F]/.test(trimmed)) {
    return {
      detectedLanguage: 'te',
      confidence: 'script_match',
      isAutoDetected: true,
      differsFromCurrent: currentLanguage !== 'te',
      suggestedLanguage: 'te',
      candidates: ['te'],
      reason: 'Telugu script detected',
    };
  }

  // 2. Latin script Romanized vocabulary analysis
  const words = trimmed.toLowerCase().split(/\s+/);
  let hiScore = 0;
  let knScore = 0;
  let teScore = 0;
  let enScore = 0;

  for (const w of words) {
    const cleanW = w.replace(/[^a-z]/g, '');
    if (!cleanW) continue;
    if (HINDI_ROMAN_KEYWORDS.includes(cleanW)) hiScore += 1;
    if (KANNADA_ROMAN_KEYWORDS.includes(cleanW)) knScore += 1;
    if (TELUGU_ROMAN_KEYWORDS.includes(cleanW)) teScore += 1;
    if (ENGLISH_KEYWORDS.includes(cleanW)) enScore += 1;
  }

  // Check Romanized Indic matches
  if (hiScore >= 1 && hiScore > knScore && hiScore > teScore) {
    return {
      detectedLanguage: 'hi',
      confidence: 'uncertain', // Per rule: Latin script must remain uncertain to prompt user confirmation
      isAutoDetected: true,
      differsFromCurrent: currentLanguage !== 'hi',
      suggestedLanguage: 'hi',
      candidates: ['hi', 'en'],
      reason: 'Romanized Hindi words detected',
    };
  }

  if (knScore >= 1 && knScore > hiScore && knScore > teScore) {
    return {
      detectedLanguage: 'kn',
      confidence: 'uncertain',
      isAutoDetected: true,
      differsFromCurrent: currentLanguage !== 'kn',
      suggestedLanguage: 'kn',
      candidates: ['kn', 'en'],
      reason: 'Romanized Kannada words detected',
    };
  }

  if (teScore >= 1 && teScore > hiScore && teScore > knScore) {
    return {
      detectedLanguage: 'te',
      confidence: 'uncertain',
      isAutoDetected: true,
      differsFromCurrent: currentLanguage !== 'te',
      suggestedLanguage: 'te',
      candidates: ['te', 'en'],
      reason: 'Romanized Telugu words detected',
    };
  }

  if (enScore >= 1 && currentLanguage !== 'en') {
    return {
      detectedLanguage: 'en',
      confidence: 'uncertain',
      isAutoDetected: true,
      differsFromCurrent: true,
      suggestedLanguage: 'en',
      candidates: ['en', currentLanguage],
      reason: 'English words detected',
    };
  }

  // Ambiguous or matching current
  return {
    detectedLanguage: currentLanguage,
    confidence: 'uncertain',
    isAutoDetected: false,
    differsFromCurrent: false,
    suggestedLanguage: currentLanguage,
    candidates: ['en', 'hi', 'kn', 'te'],
  };
}

