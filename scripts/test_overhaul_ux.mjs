import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = process.cwd();

test('Overhaul UX: Home Screen Voice-First & Low-Literacy Visual Guide', () => {
  const homeCode = fs.readFileSync(path.join(projectRoot, 'src/pages/Home.tsx'), 'utf8');

  // Must have prominent hero CTA
  assert.ok(homeCode.includes("t('findSchemesHeroCTA'"), 'Home screen must include findSchemesHeroCTA');
  assert.ok(homeCode.includes("t('orTypeMessage'"), 'Home screen must offer orTypeMessage fallback');
  assert.ok(homeCode.includes('/assistant'), 'Home screen buttons must route to /assistant');

  // Must include visual 3-step guide for low-literacy citizens
  assert.ok(homeCode.includes('How It Works - Visual 3-Step Guide'), 'Home screen must include 3-step guide for low-literacy users');
  assert.ok(homeCode.includes('🎙️') && homeCode.includes('⚡') && homeCode.includes('📋'), 'Home screen must feature visual emojis');

  // Must include quick-start entries for common citizen groups
  assert.ok(homeCode.includes("t('categoryFarmers'"), 'Home screen must include Farmers quick entry');
  assert.ok(homeCode.includes("t('categorySeniors'"), 'Home screen must include Seniors quick entry');
  assert.ok(homeCode.includes("t('categoryWomenChild'"), 'Home screen must include Women & Children quick entry');
  assert.ok(homeCode.includes("t('categoryVendors'"), 'Home screen must include Vendors quick entry');
});

test('Overhaul UX: Scheme Details Strict 7-Step Hierarchy', () => {
  const detailCode = fs.readFileSync(path.join(projectRoot, 'src/pages/SchemeDetail.tsx'), 'utf8');

  // Must strictly answer the 7 steps in order
  const step1 = detailCode.indexOf("t('sevenStepsTitle1'");
  const step2 = detailCode.indexOf("t('sevenStepsTitle2'");
  const step3 = detailCode.indexOf("t('sevenStepsTitle3'");
  const step4 = detailCode.indexOf("t('sevenStepsTitle4'");
  const step5 = detailCode.indexOf("t('sevenStepsTitle5'");
  const step6 = detailCode.indexOf("t('sevenStepsTitle6'");
  const step7 = detailCode.indexOf("t('sevenStepsTitle7'");

  assert.ok(step1 !== -1 && step2 !== -1 && step3 !== -1 && step4 !== -1 && step5 !== -1 && step6 !== -1 && step7 !== -1, 'All 7 step headings must be present');
  assert.ok(step1 < step2, 'Step 1 must appear before Step 2');
  assert.ok(step2 < step3, 'Step 2 must appear before Step 3');
  assert.ok(step3 < step4, 'Step 3 must appear before Step 4');
  assert.ok(step4 < step5, 'Step 4 must appear before Step 5');
  assert.ok(step5 < step6, 'Step 5 must appear before Step 6');
  assert.ok(step6 < step7, 'Step 6 must appear before Step 7');

  // Must have prominent Read Scheme To Me button
  assert.ok(detailCode.includes("t('readSchemeToMe'"), 'Must include readSchemeToMe button');
});

test('Overhaul UX: Eligibility Results 3-Bucket Organization & TTS Audio Summary', () => {
  const eligCode = fs.readFileSync(path.join(projectRoot, 'src/pages/EligibilityResults.tsx'), 'utf8');

  // Must include the 3 plain-language bucket labels
  assert.ok(eligCode.includes("t('bucketYouMayBeEligible'"), 'Must include bucketYouMayBeEligible');
  assert.ok(eligCode.includes("t('bucketNeedsMoreInfo'"), 'Must include bucketNeedsMoreInfo');
  assert.ok(eligCode.includes("t('bucketNotEligible'"), 'Must include bucketNotEligible');

  // Must have audio summary speech synthesis
  assert.ok(eligCode.includes('handleReadSummaryAloud'), 'Must have handleReadSummaryAloud handler');
  assert.ok(eligCode.includes('useSpeechSynthesis'), 'Must use useSpeechSynthesis');
});

test('Overhaul UX: Translations Coverage for 4 Languages', () => {
  const transCode = fs.readFileSync(path.join(projectRoot, 'src/data/translations.ts'), 'utf8');

  // All 4 languages supported for new keys
  const requiredKeys = [
    'bucketYouMayBeEligible',
    'bucketNeedsMoreInfo',
    'bucketNotEligible',
    'findSchemesHeroCTA',
    'readSchemeToMe',
    'sevenStepsTitle1',
    'sevenStepsTitle2',
    'sevenStepsTitle3',
    'sevenStepsTitle4',
    'sevenStepsTitle5',
    'sevenStepsTitle6',
    'sevenStepsTitle7',
  ];

  for (const k of requiredKeys) {
    assert.ok(transCode.includes(k), `Translations must contain key ${k}`);
  }
});

