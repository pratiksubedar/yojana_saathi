/**
 * Yojana Saathi - Speech & Audio Presentation Utilities
 * Phase 2 — Voice-First Multilingual Experience
 *
 * Implements:
 * 1. extractSpeakableText: Extracts short, conversational speech summaries from full markdown responses
 *    - Strips markdown tables, URLs, raw citations, and bullet points.
 *    - Leaves detailed document checklists, step lists, and links for visual display.
 *    - Limits spoken length to ~2-3 conversational sentences (max ~220 chars).
 * 2. Voice pack availability and regional locale validation.
 */

import type { Language } from '../types/index.ts';

const SPEECH_LOCALES: Record<Language, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  kn: 'kn-IN',
  te: 'te-IN',
};

/**
 * Extracts a concise, conversational summary for speech synthesis (Task 4):
 * - Keeps spoken responses short and conversational.
 * - Strips markdown tables, URLs, raw citations, and bullet points.
 * - Leaves detailed document checklists, step lists, and links for visual display.
 * - Limits spoken length to ~2-3 conversational sentences (max ~220 chars).
 */
export function extractSpeakableText(fullText: string, fullRead: boolean = false): string {
  if (!fullText || !fullText.trim()) return '';

  let cleaned = fullText.trim();

  // 1. Remove markdown links [text](url) -> keep text only
  cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // 2. Remove bare URLs
  cleaned = cleaned.replace(/https?:\/\/\S+/g, '');

  // 3. Cut off at major markdown structural boundaries (citations, document checklists, application steps)
  const boundaryPatterns = fullRead
    ? [/#{1,4}\s*(?:Official Citations|Sources|References|सत्यापित स्रोत|ಉಲ್ಲೇಖಗಳು|ఆధారాలు)/i]
    : [
        /#{1,4}\s*(?:Official Citations|Sources|References|सत्यापित स्रोत|ಉಲ್ಲೇಖಗಳು|ఆధారాలు)/i,
        /#{1,4}\s*(?:Required Documents|Documents|दस्तावेज़|ದಾಖಲೆಗಳು|పత్రాలు)/i,
        /#{1,4}\s*(?:Application Steps|How to Apply|आवेदन प्रक्रिया|ಅರ್ಜಿ ಸಲ್ಲಿಸುವ ವಿಧಾನ|దరఖాస్తు విధానಂ)/i,
        /#{1,4}\s*(?:Eligibility Criteria|पात्रता शर्तें|ಅರ್ಹತಾ ಷರತ್ತುಗಳು|అర్హత నిబంధనలు)/i,
      ];

  for (const pattern of boundaryPatterns) {
    const idx = cleaned.search(pattern);
    if (idx !== -1) {
      cleaned = cleaned.slice(0, idx).trim();
    }
  }

  // 4. In fullRead mode, convert bullets into natural pauses; in short summary mode, cut off at lists
  if (!fullRead) {
    const listMatch = cleaned.search(/(?:\r?\n|^)\s*(?:[-*•]|\d+\.)\s+/m);
    if (listMatch !== -1) {
      const lead = cleaned.slice(0, listMatch).trim();
      if (lead) {
        cleaned = lead;
      }
    }
  } else {
    cleaned = cleaned.replace(/(?:\r?\n|^)\s*(?:[-*•]|\d+\.)\s+/g, '. ');
  }

  // 5. Remove markdown formatting markers (bold, italic, code, headers, blockquotes)
  cleaned = cleaned
    .replace(/[#*`_~>]/g, '')
    .replace(/\|[^\n]+\|/g, '') // strip markdown tables
    .replace(/\s+/g, ' ')
    .trim();

  if (fullRead) {
    return cleaned;
  }

  // 6. Split into sentences and keep the first 1-2 conversational sentences (up to 220 characters)
  const sentences = cleaned.match(/[^.!?।\n]+[.!?।]/g);
  if (sentences && sentences.length > 0) {
    let result = '';
    for (const s of sentences) {
      const trimmedSentence = s.trim();
      if ((result + ' ' + trimmedSentence).trim().length <= 220) {
        result = result ? `${result} ${trimmedSentence}` : trimmedSentence;
      } else {
        break;
      }
    }
    if (result) return result;
  }

  // Fallback: truncate at word boundary if single long sentence
  if (cleaned.length > 220) {
    return cleaned.slice(0, 210).replace(/\s+\S*$/, '') + '...';
  }

  return cleaned;
}

/**
 * Checks if the browser or operating system has an authentic regional voice installed
 * for the requested language.
 */
export function checkVoiceSupportForLanguage(
  voices: SpeechSynthesisVoice[],
  language: Language
): { isAvailable: boolean; voiceName?: string } {
  if (!voices || voices.length === 0) {
    return { isAvailable: false };
  }

  const targetLocale = (SPEECH_LOCALES[language] || 'en-IN').toLowerCase();
  const prefix = targetLocale.split('-')[0];

  const nameHints: Record<Language, string[]> = {
    en: ['india', 'english'],
    hi: ['hindi', 'lekha'],
    kn: ['kannada'],
    te: ['telugu'],
  };

  const hints = nameHints[language] || [];

  const matched = voices.find((v) => {
    const vLang = v.lang.toLowerCase();
    const vName = v.name.toLowerCase();
    if (vLang === targetLocale || vLang.startsWith(prefix)) return true;
    return hints.some((h) => vName.includes(h));
  });

  if (matched) {
    return { isAvailable: true, voiceName: matched.name };
  }

  return { isAvailable: false };
}
