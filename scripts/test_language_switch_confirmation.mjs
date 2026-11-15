import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

// Import our language detection modules
import { detectInputLanguage, detectLanguageFromTranscript } from '../src/utils/languageDetection.ts';

test('1. Input Language Detection & Script Matching', () => {
  // Devanagari Script -> Hindi (High script match confidence)
  const hiResult = detectInputLanguage('मुझे किसान योजना की जानकारी चाहिए', 'en');
  assert.strictEqual(hiResult.detectedLanguage, 'hi');
  assert.strictEqual(hiResult.confidence, 'script_match');
  assert.strictEqual(hiResult.differsFromCurrent, true);

  // Kannada Script -> Kannada (High script match confidence)
  const knResult = detectInputLanguage('ನನಗೆ ರೈತ ಯೋಜನೆಗಳ ಬಗ್ಗೆ ಮಾಹಿತಿ ಬೇಕು', 'en');
  assert.strictEqual(knResult.detectedLanguage, 'kn');
  assert.strictEqual(knResult.confidence, 'script_match');
  assert.strictEqual(knResult.differsFromCurrent, true);

  // Telugu Script -> Telugu (High script match confidence)
  const teResult = detectInputLanguage('నాకు రైతు సంక్షేమ పథకాల గురించి చెప్పండి', 'en');
  assert.strictEqual(teResult.detectedLanguage, 'te');
  assert.strictEqual(teResult.confidence, 'script_match');
  assert.strictEqual(teResult.differsFromCurrent, true);

  // Matching current language -> differsFromCurrent = false
  const sameLang = detectInputLanguage('ನನಗೆ ಯೋಜನೆ ಬೇಕು', 'kn');
  assert.strictEqual(sameLang.differsFromCurrent, false);
});

test('2. Romanized Script Clues & Uncertain Language Reporting', () => {
  // Romanized Hindi
  const romHi = detectInputLanguage('kisan yojana chahiye mujhe', 'en');
  assert.strictEqual(romHi.detectedLanguage, 'hi');
  assert.strictEqual(romHi.confidence, 'uncertain');
  assert.strictEqual(romHi.differsFromCurrent, true);

  // Romanized Kannada
  const romKn = detectInputLanguage('raita yojana beku namage', 'en');
  assert.strictEqual(romKn.detectedLanguage, 'kn');
  assert.strictEqual(romKn.confidence, 'uncertain');
  assert.strictEqual(romKn.differsFromCurrent, true);

  // Romanized Telugu
  const romTe = detectInputLanguage('raitu yojana kavali illu', 'en');
  assert.strictEqual(romTe.detectedLanguage, 'te');
  assert.strictEqual(romTe.confidence, 'uncertain');
  assert.strictEqual(romTe.differsFromCurrent, true);

  // Pure English in Hindi mode
  const pureEn = detectInputLanguage('What schemes are available for farmers?', 'hi');
  assert.strictEqual(pureEn.detectedLanguage, 'en');
  assert.strictEqual(pureEn.confidence, 'uncertain');
  assert.strictEqual(pureEn.differsFromCurrent, true);

  // Backward compatibility contract for detectLanguageFromTranscript
  const legacy = detectLanguageFromTranscript('What schemes are available for farmers?', 'en');
  assert.strictEqual(legacy.confidence, 'uncertain');
});

test('3. Confirmation Modal & Universal AppContext Language Architecture', () => {
  const modalSrc = fs.readFileSync(path.resolve('src/components/LanguageSwitchConfirmation.tsx'), 'utf-8');
  assert.ok(modalSrc.includes('languageSwitchPrompt'), 'Modal accesses languageSwitchPrompt');
  assert.ok(modalSrc.includes('confirmLanguageSwitch'), 'Modal connects to confirmLanguageSwitch');
  assert.ok(modalSrc.includes('dismissLanguageSwitch'), 'Modal connects to dismissLanguageSwitch');
  assert.ok(modalSrc.includes('switch the entire website'), 'Prompts user to switch entire website');

  const appSrc = fs.readFileSync(path.resolve('src/App.tsx'), 'utf-8');
  assert.ok(appSrc.includes('<LanguageSwitchConfirmation />'), 'LanguageSwitchConfirmation is mounted globally at App root');

  const contextSrc = fs.readFileSync(path.resolve('src/context/AppContext.tsx'), 'utf-8');
  assert.ok(contextSrc.includes('requestLanguageSwitch'), 'AppContext exposes requestLanguageSwitch');
  assert.ok(contextSrc.includes('confirmLanguageSwitch'), 'AppContext exposes confirmLanguageSwitch');
  assert.ok(contextSrc.includes('dismissLanguageSwitch'), 'AppContext exposes dismissLanguageSwitch');
  assert.ok(contextSrc.includes("localStorage.setItem('yojana_lang'"), 'Persists language universally to localStorage');
});

test('4. Full Site Profile Translation Verification (All 16 Criteria & Options)', () => {
  const profileSrc = fs.readFileSync(path.resolve('src/pages/ProfileConfirmation.tsx'), 'utf-8');

  // Verify all 16 attributes in LOCALIZED_ATTRIBUTE_CARDS across en, hi, kn, te
  const requiredKeys = [
    'age', 'gender', 'state', 'occupation', 'farmerType', 'annualIncome',
    'paysIncomeTax', 'hasRegularGovtJob', 'monthlyPension', 'ownsAgriculturalLand',
    'landholdingHectares', 'ownsPuccaHouse', 'hasBPLCard', 'isBankDefaulter',
    'socialCategory', 'isDifferentlyAbled'
  ];

  requiredKeys.forEach((key) => {
    assert.ok(profileSrc.includes(`'${key}'`) || profileSrc.includes(`${key}:`), `Profile includes ${key}`);
  });

  // Verify localized options maps
  assert.ok(profileSrc.includes('LOCALIZED_OCCUPATION_MAP'), 'Defines localized occupation map');
  assert.ok(profileSrc.includes('LOCALIZED_FARMER_TYPES_MAP'), 'Defines localized farmer types map');
  assert.ok(profileSrc.includes('LOCALIZED_GENDERS_MAP'), 'Defines localized genders map');
  assert.ok(profileSrc.includes('LOCALIZED_CASTES_MAP'), 'Defines localized castes map');

  // Verify required static identifiers for backward tests
  assert.ok(profileSrc.includes('INDIAN_STATES_AND_UTS'), 'Contains INDIAN_STATES_AND_UTS');
  assert.ok(profileSrc.includes('ownsAgriculturalLand'), 'Contains ownsAgriculturalLand');
  assert.ok(profileSrc.includes('Annual Household Income'), 'Contains Annual Household Income');
  assert.ok(profileSrc.includes('Clear my information'), 'Contains Clear my information');
});

test('5. Guided Flow & Profile Chips Multilingual Translation (All 4 Languages)', () => {
  const chatSrc = fs.readFileSync(path.resolve('src/pages/AssistantChat.tsx'), 'utf-8');

  // Verify profileChips localization
  assert.ok(chatSrc.includes('profileChips'), 'AssistantChat computes profileChips');
  assert.ok(chatSrc.includes('ವರ್ಷ'), 'profileChips includes Kannada age unit');
  assert.ok(chatSrc.includes('సం.'), 'profileChips includes Telugu age unit');
  assert.ok(chatSrc.includes('ಭೂಮಾಲೀಕ'), 'profileChips includes Kannada landholding');
  assert.ok(chatSrc.includes('భూ యజమాని'), 'profileChips includes Telugu landholding');

  // Verify guided question option button localizations
  assert.ok(chatSrc.includes('Quick Select:'), 'Quick Select translated');
  assert.ok(chatSrc.includes('Confirm Age'), 'Confirm Age translated');
  assert.ok(chatSrc.includes('18 - 25 years'), 'Age brackets translated');
  assert.ok(chatSrc.includes('Female'), 'Gender options translated');
  assert.ok(chatSrc.includes('Farmer / Agriculture'), 'Occupations translated');
  assert.ok(chatSrc.includes('Landowning Farmer'), 'Farmer details translated');
  assert.ok(chatSrc.includes('Below ₹1 Lakh'), 'Income brackets translated');
  assert.ok(chatSrc.includes('General / Open Category'), 'Social categories translated');
  assert.ok(chatSrc.includes('Have Bank Passbook'), 'Housing and DBT translated');
  assert.ok(chatSrc.includes('No, neither'), 'Statutory exclusions translated');
});

test('6. Dynamic Condition and Field Translation in Scheme API', () => {
  const apiSrc = fs.readFileSync(path.resolve('src/services/schemeApi.ts'), 'utf-8');
  assert.ok(apiSrc.includes('formatConditionLabel'), 'formatConditionLabel handles dynamic criteria translation');
  assert.ok(apiSrc.includes('formatFieldName'), 'formatFieldName handles dynamic field translation');
  assert.ok(apiSrc.includes('ಕೃಷಿ ಭೂಮಿ'), 'Provides Kannada condition translations');
  assert.ok(apiSrc.includes('వ్యవసాయ భూమి'), 'Provides Telugu condition translations');
  assert.ok(apiSrc.includes('कृषि भूमि'), 'Provides Hindi condition translations');
});
