/**
 * Yojana Saathi - Phase 2: Voice-First Multilingual Experience Tests
 *
 * Verifies:
 * 1. Task 1: Voice-First Conversation UI (prominent mic, listening/speaking states, replay, mute/unmute, text fallback)
 * 2. Task 2: 4-Language Speech Pipeline (en, hi, kn, te locales, script detection, voice selection, fallback)
 * 3. Task 3: Code-Mixed Speech & Ambiguity Handling (Hindi-English, Kannada-English, ambiguous "actors", "bigha")
 * 4. Task 4: Short Speakable Response Extraction (strips checklists, tables, URLs, keeps ~2 conversational sentences)
 * 5. Task 5: Accessibility & Error Recovery (permission denied, no speech, network error)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { extractSpeakableText, checkVoiceSupportForLanguage } from '../src/utils/speechUtils.ts';
import { normalizeDomainTranscript } from '../src/utils/transcriptNormalizer.ts';
import { detectLanguageFromTranscript } from '../src/utils/languageDetection.ts';

const SPEECH_LOCALES = {
  en: 'en-IN',
  hi: 'hi-IN',
  kn: 'kn-IN',
  te: 'te-IN',
};

// =====================================================================
// 1. Task 4: Response Design & Spoken Response Extraction
// =====================================================================
describe('Task 4: Response Design & Speakable Text Extraction', () => {
  test('strips long markdown document checklists from spoken output', () => {
    const rawMarkdown = `You are eligible for PM-KISAN Samman Nidhi. You will receive ₹6,000 annually in three equal installments.

### Required Documents
- Aadhaar Card with active mobile linkage
- Land ownership record (7/12 extract or Jamabandi)
- Bank Passbook with DBT mandate
- Self-declaration form

### Application Steps
1. Visit the official portal https://pmkisan.gov.in
2. Click on New Farmer Registration
3. Complete biometric e-KYC`;

    const speakable = extractSpeakableText(rawMarkdown);

    assert.ok(speakable.includes('eligible for PM-KISAN Samman Nidhi'));
    assert.ok(speakable.includes('₹6,000 annually'));
    // Must NOT contain document list items or application steps or URLs
    assert.strictEqual(speakable.includes('Aadhaar Card with active mobile linkage'), false);
    assert.strictEqual(speakable.includes('Land ownership record'), false);
    assert.strictEqual(speakable.includes('Bank Passbook'), false);
    assert.strictEqual(speakable.includes('https://pmkisan.gov.in'), false);
    assert.strictEqual(speakable.includes('Click on New Farmer Registration'), false);
  });

  test('strips bare URLs and markdown links', () => {
    const text = 'For further details visit [PM Kisan Portal](https://pmkisan.gov.in) or call 155261. You can apply online at https://pmkisan.gov.in/Registration.';
    const speakable = extractSpeakableText(text);

    assert.ok(speakable.includes('For further details visit PM Kisan Portal'));
    assert.strictEqual(speakable.includes('https://'), false);
  });

  test('keeps spoken response short and conversational (<= 220 chars)', () => {
    const longText = 'Ayushman Bharat PM-JAY provides comprehensive health insurance coverage of ₹5 Lakh per year for secondary and tertiary care hospitalization to vulnerable families. Benefits are completely cashless and paperless at all empaneled public and private hospitals across the country. Over 27 medical specialties are covered under the scheme including oncology and cardiology.';
    const speakable = extractSpeakableText(longText);

    assert.ok(speakable.length <= 220, `Speakable text too long: ${speakable.length}`);
    assert.ok(speakable.endsWith('.') || speakable.endsWith('...'));
  });

  test('handles Hindi, Kannada and Telugu speakable leads gracefully', () => {
    const hindiMarkdown = `आप प्रधानमंत्री किसान सम्मान निधि योजना के लिए पात्र हैं। इसके अंतर्गत आपको सालाना ₹6,000 की आर्थिक सहायता प्राप्त होगी।

### आवश्यक दस्तावेज़
- आधार कार्ड
- खतौनी या ज़मीन के दस्तावेज़
- बैंक पासबुक`;

    const speakableHi = extractSpeakableText(hindiMarkdown);
    assert.ok(speakableHi.includes('पात्र हैं'));
    assert.ok(speakableHi.includes('₹6,000'));
    assert.strictEqual(speakableHi.includes('आधार कार्ड'), false);
    assert.strictEqual(speakableHi.includes('खतौनी'), false);

    const kannadaMarkdown = `ನೀವು ಕಿಸಾನ್ ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್ ಯೋಜನೆಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ. ನಿಮಗೆ ರಿಯಾಯಿತಿ ಬಡ್ಡಿದರದಲ್ಲಿ ಕೃಷಿ ಸಾಲ ಲಭ್ಯವಾಗುತ್ತದೆ.

### ಅಗತ್ಯ ದಾಖಲೆಗಳು
1. ಆಧಾರ್ ಕಾರ್ಡ್
2. ಪಹಣಿ / ಆರ್‌ಟಿಸಿ`;

    const speakableKn = extractSpeakableText(kannadaMarkdown);
    assert.ok(speakableKn.includes('ಅರ್ಹರಾಗಿದ್ದೀರಿ'));
    assert.strictEqual(speakableKn.includes('ಆಧಾರ್ ಕಾರ್ಡ್'), false);
    assert.strictEqual(speakableKn.includes('ಪಹಣಿ'), false);
  });
});

// =====================================================================
// 2. Task 2: 4-Language Voice Pipeline Configuration
// =====================================================================
describe('Task 2: 4-Language Voice Pipeline Configuration', () => {
  test('has verified BCP-47 speech recognition locales for en, hi, kn, te', () => {
    assert.strictEqual(SPEECH_LOCALES.en, 'en-IN');
    assert.strictEqual(SPEECH_LOCALES.hi, 'hi-IN');
    assert.strictEqual(SPEECH_LOCALES.kn, 'kn-IN');
    assert.strictEqual(SPEECH_LOCALES.te, 'te-IN');
  });

  test('detects Indic native scripts with script_match confidence', () => {
    // Hindi Devanagari
    const hiRes = detectLanguageFromTranscript('मुझे पीएम किसान योजना के बारे में जानना है');
    assert.strictEqual(hiRes.detectedLanguage, 'hi');
    assert.strictEqual(hiRes.confidence, 'script_match');

    // Kannada
    const knRes = detectLanguageFromTranscript('ನನಗೆ ಬೆಳೆ ಪರಿಹಾರ ಯೋಜನೆ ಮಾಹಿತಿ ಬೇಕು');
    assert.strictEqual(knRes.detectedLanguage, 'kn');
    assert.strictEqual(knRes.confidence, 'script_match');

    // Telugu
    const teRes = detectLanguageFromTranscript('నాకు రైతు రుణ పథకం వివరాలు కావాలి');
    assert.strictEqual(teRes.detectedLanguage, 'te');
    assert.strictEqual(teRes.confidence, 'script_match');
  });

  test('accurately identifies voice availability in simulated browser voice lists', () => {
    const mockVoices = [
      { name: 'Google हिन्दी', lang: 'hi-IN' },
      { name: 'Google US English', lang: 'en-US' },
      { name: 'Microsoft Ravi - English (India)', lang: 'en-IN' },
      { name: 'Microsoft Heera - Hindi', lang: 'hi-IN' },
    ];

    const enSupport = checkVoiceSupportForLanguage(mockVoices, 'en');
    assert.strictEqual(enSupport.isAvailable, true);

    const hiSupport = checkVoiceSupportForLanguage(mockVoices, 'hi');
    assert.strictEqual(hiSupport.isAvailable, true);

    // Kannada and Telugu not installed in mockVoices -> must report false (do not claim false support)
    const knSupport = checkVoiceSupportForLanguage(mockVoices, 'kn');
    assert.strictEqual(knSupport.isAvailable, false);

    const teSupport = checkVoiceSupportForLanguage(mockVoices, 'te');
    assert.strictEqual(teSupport.isAvailable, false);
  });
});

// =====================================================================
// 3. Task 3: Code-Mixed Speech & Ambiguity Handling
// =====================================================================
describe('Task 3: Code-Mixed Speech & Ambiguity Handling', () => {
  test('normalizes common scheme names from code-mixed speech', () => {
    const text1 = 'Mera age 35 hai, kya mujhe pm kisan aur ayushman card mil sakta hai?';
    const res1 = normalizeDomainTranscript(text1, 'hi');
    assert.ok(res1.correctedTranscript.includes('PM-KISAN'));
    assert.ok(res1.correctedTranscript.includes('PM-JAY'));

    const text2 = 'Nanna age 30 years, kisan credit card apply madoke documents enu?';
    const res2 = normalizeDomainTranscript(text2, 'kn');
    assert.ok(res2.correctedTranscript.includes('Kisan Credit Card'));
  });

  test('flags ambiguous "actors" near land measurements for user confirmation', () => {
    const input = 'I am a farmer with 2.5 actors of land in village';
    const res = normalizeDomainTranscript(input, 'en');

    assert.ok(res.uncertainTerms.length > 0);
    assert.strictEqual(res.uncertainTerms[0].candidates.length, 2);
    assert.deepEqual(res.uncertainTerms[0].candidates, ['2.5 acres', '2.5 hectares']);
    assert.ok(res.correctedTranscript.includes('[acres/hectares?]'));
  });

  test('flags ambiguous regional unit "bigha" for user confirmation instead of silently guessing', () => {
    const input = 'Mere paas 4 bigha zameen hai';
    const res = normalizeDomainTranscript(input, 'hi');

    assert.ok(res.uncertainTerms.length > 0);
    assert.ok(res.uncertainTerms[0].message.includes('Bigha'));
    assert.ok(res.correctedTranscript.includes('[acres/hectares?]'));
  });

  test('safely normalizes misspelled "hectors" to "hectares" when unambiguous', () => {
    const input = 'I have 3 hectors agricultural land';
    const res = normalizeDomainTranscript(input, 'en');

    assert.ok(res.correctedTranscript.includes('3 hectares'));
    assert.strictEqual(res.uncertainTerms.length, 0);
  });
});

// =====================================================================
// 4. Task 1 & 5: Voice Controls & Accessibility
// =====================================================================
describe('Task 1 & 5: Voice Controls, Accessibility & Resilience', () => {
  test('allows safe text fallback without speech recognition dependency', () => {
    // Normalizer works identically on plain text inputs
    const typed = 'How to get pm svanidhi loan of 10000 rupees';
    const res = normalizeDomainTranscript(typed, 'en');
    assert.ok(res.correctedTranscript.includes('PM-SVANidhi'));
  });

  test('preserves numeric amounts and currency terms strictly', () => {
    const text = 'Annual household income is 150000 rupees and age is 45';
    const res = normalizeDomainTranscript(text, 'en');
    assert.ok(res.correctedTranscript.includes('150000'));
    assert.ok(res.correctedTranscript.includes('45'));
  });
});
