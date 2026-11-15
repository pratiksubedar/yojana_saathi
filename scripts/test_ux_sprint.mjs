/**
 * Yojana Saathi — UX, Voice AI & Conversational Intelligence Regression Tests
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import { detectLanguageFromTranscript } from '../src/utils/languageDetection.ts';
import { normalizeDomainTranscript } from '../src/utils/transcriptNormalizer.ts';

const ROOT = process.cwd();

describe('Navigation Redesign: Settings -> Profile', () => {
  test('BottomNav links to /profile and does not contain /settings', () => {
    const bottomNavSrc = fs.readFileSync(path.join(ROOT, 'src/components/BottomNav.tsx'), 'utf8');
    assert.ok(bottomNavSrc.includes("path: '/profile'"), 'BottomNav must include /profile');
    assert.ok(!bottomNavSrc.includes("path: '/settings'"), 'BottomNav must not include /settings');
  });

  test('Header includes a Settings gear link to /settings', () => {
    const headerSrc = fs.readFileSync(path.join(ROOT, 'src/components/Header.tsx'), 'utf8');
    assert.ok(headerSrc.includes("navigate('/settings')"), 'Header must navigate to /settings');
    assert.ok(headerSrc.includes('Settings'), 'Header must render Settings icon');
  });
});

describe('Citizen Profile & Zero-Fabrication Guarantees', () => {
  test('AppContext initializes DEFAULT_PROFILE as empty object without fabricated defaults', () => {
    const ctxSrc = fs.readFileSync(path.join(ROOT, 'src/context/AppContext.tsx'), 'utf8');
    assert.ok(
      ctxSrc.includes('const DEFAULT_PROFILE: UserProfile = {};'),
      'DEFAULT_PROFILE must be strictly empty'
    );
    assert.ok(!ctxSrc.includes('Ramesh Kumar'), 'Must not contain hardcoded Ramesh Kumar demo profile');
  });

  test('AppContext tracks attributeSources (user vs detected) and protects user-corrected values', () => {
    const ctxSrc = fs.readFileSync(path.join(ROOT, 'src/context/AppContext.tsx'), 'utf8');
    assert.ok(ctxSrc.includes('attributeSources'), 'Must track attributeSources');
    assert.ok(ctxSrc.includes("attributeSources[key] !== 'user'"), 'mergeDetectedProfile must not overwrite user-provided fields');
  });

  test('Settings page does not duplicate Profile editing or summary', () => {
    const settingsSrc = fs.readFileSync(path.join(ROOT, 'src/pages/SettingsProfile.tsx'), 'utf8');
    assert.ok(!settingsSrc.includes('userProfile.age'), 'Settings must not duplicate profile attributes');
    assert.ok(settingsSrc.includes('Language & Regional Preferences'));
    assert.ok(settingsSrc.includes('Voice & Speech Preferences'));
    assert.ok(settingsSrc.includes('Accessibility'));
    assert.ok(settingsSrc.includes('Privacy & Data Controls'));
  });
});

describe('Voice AI: Script Language Detection & Editable Transcript Flow', () => {
  test('detectLanguageFromTranscript identifies Devanagari, Kannada, Telugu scripts with script_match', () => {
    const hi = detectLanguageFromTranscript('मुझे पीएम किसान योजना की जानकारी चाहिए', 'en');
    assert.strictEqual(hi.detectedLanguage, 'hi');
    assert.strictEqual(hi.confidence, 'script_match');
    assert.strictEqual(hi.isAutoDetected, true);

    const kn = detectLanguageFromTranscript('ನನಗೆ ಕೃಷಿ ಯೋಜನೆಗಳು ಬೇಕು', 'en');
    assert.strictEqual(kn.detectedLanguage, 'kn');
    assert.strictEqual(kn.confidence, 'script_match');

    const te = detectLanguageFromTranscript('నాకు వ్యవసాయ పథకాలు కావాలి', 'en');
    assert.strictEqual(te.detectedLanguage, 'te');
    assert.strictEqual(te.confidence, 'script_match');
  });

  test('detectLanguageFromTranscript never claims certainty for Latin script', () => {
    const en = detectLanguageFromTranscript('What schemes are available for farmers?', 'en');
    assert.strictEqual(en.detectedLanguage, 'en');
    assert.strictEqual(en.confidence, 'uncertain');
    assert.strictEqual(en.isAutoDetected, false);
  });

  test('VoiceMicModal provides editable textarea, retry, cancel, and language correction', () => {
    const modalSrc = fs.readFileSync(path.join(ROOT, 'src/components/VoiceMicModal.tsx'), 'utf8');
    assert.ok(modalSrc.includes('<textarea'), 'VoiceMicModal must render an editable textarea');
    assert.ok(modalSrc.includes('Retry Recording'), 'VoiceMicModal must include Retry Recording');
    assert.ok(modalSrc.includes('handleConfirmAndSend'), 'VoiceMicModal must require explicit Confirm & Send');
    assert.ok(modalSrc.includes('Speech recognition language'), 'VoiceMicModal must include language selector');
  });
});

describe('My Schemes & Privacy-First Architecture (Sprint A)', () => {
  test('BottomNav links to /my-schemes and /profile and removes /locker', () => {
    const bottomNavSrc = fs.readFileSync(path.join(ROOT, 'src/components/BottomNav.tsx'), 'utf8');
    assert.ok(bottomNavSrc.includes("path: '/my-schemes'"), 'BottomNav must include /my-schemes');
    assert.ok(!bottomNavSrc.includes("path: '/locker'"), 'BottomNav must not include /locker');
  });

  test('AppContext never persists citizen profile or saved schemes to localStorage', () => {
    const ctxSrc = fs.readFileSync(path.join(ROOT, 'src/context/AppContext.tsx'), 'utf8');
    assert.ok(!ctxSrc.includes("localStorage.setItem('yojana_saved_schemes'"), 'Must not persist personalized schemes');
    assert.ok(!ctxSrc.includes("localStorage.setItem('yojana_locker_docs'"), 'Must not persist locker documents');
    assert.ok(!ctxSrc.includes("localStorage.setItem('yojana_profile'"), 'Must not persist citizen profile');
  });

  test('MySchemes does not import MOCK_SCHEMES and uses live eligibility evaluation without document storage', () => {
    const mySchemesSrc = fs.readFileSync(path.join(ROOT, 'src/pages/MySchemes.tsx'), 'utf8');
    assert.ok(!mySchemesSrc.includes('MOCK_SCHEMES'), 'MySchemes must not use MOCK_SCHEMES');
    assert.ok(mySchemesSrc.includes('fetchSchemes'), 'MySchemes must fetch live schemes');
    assert.ok(mySchemesSrc.includes('evaluateEligibility'), 'MySchemes must evaluate eligibility');
    assert.ok(!mySchemesSrc.includes('type="file"'), 'MySchemes must not have document upload');
  });

  test('ProfileConfirmation supports all 7 required eligibility criteria and Clear my information', () => {
    const profileSrc = fs.readFileSync(path.join(ROOT, 'src/pages/ProfileConfirmation.tsx'), 'utf8');
    assert.ok(profileSrc.includes('INDIAN_STATES_AND_UTS'), 'Must include all Indian States and UTs');
    assert.ok(profileSrc.includes('ownsAgriculturalLand'), 'Must support land ownership Yes/No');
    assert.ok(profileSrc.includes('Annual Household Income'), 'Must distinguish household income');
    assert.ok(profileSrc.includes('Clear my information'), 'Must provide Clear my information action');
  });
});

describe('Markdown Rendering in AssistantChat (Test F)', () => {
  test('AssistantChat uses MarkdownRenderer for assistant messages and streaming text', () => {
    const chatSrc = fs.readFileSync(path.join(ROOT, 'src/pages/AssistantChat.tsx'), 'utf8');
    assert.ok(chatSrc.includes('MarkdownRenderer'), 'AssistantChat must import and use MarkdownRenderer');
    assert.ok(chatSrc.includes('<MarkdownRenderer content={msg.text}'), 'Must render completed messages with MarkdownRenderer');
    assert.ok(chatSrc.includes('<MarkdownRenderer content={streamingText}'), 'Must render streaming text with MarkdownRenderer');
  });

  test('MarkdownRenderer supports headings, bold, lists, and safe http(s) links', () => {
    const mdSrc = fs.readFileSync(path.join(ROOT, 'src/components/MarkdownRenderer.tsx'), 'utf8');
    assert.ok(mdSrc.includes("trimmed.startsWith('### ')"), 'Must handle ### headings');
    assert.ok(mdSrc.includes("token.startsWith('**')"), 'Must handle **bold** text');
    assert.ok(mdSrc.includes('isSafeUrl'), 'Must validate safe URLs');
    assert.ok(!mdSrc.includes('dangerouslySetInnerHTML={'), 'Must not use dangerouslySetInnerHTML');
  });
});

describe('STT Domain Normalization, Safety & Duplicate Prevention', () => {
  test('flags ambiguous "1.2 actors of land" for user confirmation without silently guessing', () => {
    const res = normalizeDomainTranscript(
      'I am a 38 years old farmer with 1.2 actors of land which welfare schemes can I get',
      'en'
    );
    assert.ok(res.correctedTranscript.includes('38-year-old'), 'Preserves age 38');
    assert.ok(res.correctedTranscript.includes('1.2 [acres/hectares?]'), 'Flags ambiguous unit');
    assert.strictEqual(res.uncertainTerms.length, 1);
    assert.deepStrictEqual(res.uncertainTerms[0].candidates, ['1.2 acres', '1.2 hectares']);
  });

  test('normalizes "20 hectors" and "pm kisan" while keeping "1.2 acres" untouched', () => {
    const res1 = normalizeDomainTranscript('I have 20 hectors and want pm kisan', 'en');
    assert.ok(res1.correctedTranscript.includes('20 hectares'));
    assert.ok(res1.correctedTranscript.includes('PM-KISAN'));

    const res2 = normalizeDomainTranscript('I own 1.2 acres of land', 'en');
    assert.strictEqual(res2.correctedTranscript, 'I own 1.2 acres of land');
    assert.strictEqual(res2.uncertainTerms.length, 0);
  });

  test('preserves negations and numeric values strictly', () => {
    const res = normalizeDomainTranscript("I don't own agricultural land and I am 38 years old.", 'en');
    assert.ok(res.correctedTranscript.includes("don't own agricultural land"));
    assert.ok(res.correctedTranscript.includes('38'));
  });

  test('prevents duplicate final chunks and preserves transcript across language switch', () => {
    const hookSrc = fs.readFileSync(path.join(ROOT, 'src/hooks/useSpeechRecognition.ts'), 'utf8');
    assert.ok(hookSrc.includes('lastFinalChunkRef'), 'Must deduplicate consecutive final chunks');
    assert.ok(hookSrc.includes('recognitionRef.current.onresult = null'), 'Must clean up event handlers on unmount');

    const modalSrc = fs.readFileSync(path.join(ROOT, 'src/components/VoiceMicModal.tsx'), 'utf8');
    assert.ok(modalSrc.includes('wasOpenRef'), 'Must only reset transcript when modal opens, not on language change');

    const chatSrc = fs.readFileSync(path.join(ROOT, 'src/pages/AssistantChat.tsx'), 'utf8');
    assert.ok(chatSrc.includes('lastSubmissionRef'), 'Must guard against rapid duplicate submissions');
  });
});

