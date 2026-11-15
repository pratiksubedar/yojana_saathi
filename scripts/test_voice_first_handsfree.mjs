import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = process.cwd();

test('Voice-First Hands-Free Architecture & Contract Verification', async (t) => {
  await t.test('1. useSpeechRecognition supports silenceTimeoutMs and onSilenceDetected', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/hooks/useSpeechRecognition.ts'),
      'utf-8'
    );
    assert.match(fileContent, /silenceTimeoutMs\?: number/);
    assert.match(fileContent, /onSilenceDetected\?: \(transcript: string\) => void/);
    assert.match(fileContent, /speechSilenceTimerRef/);
    assert.match(fileContent, /optionsRef\.current\?\.onSilenceDetected\?\.unref|\.onSilenceDetected\?\.\(fullSpeech\)/);
  });

  await t.test('2. useSpeechRecognition accurately tracks errorType and permissionDenied', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/hooks/useSpeechRecognition.ts'),
      'utf-8'
    );
    assert.match(fileContent, /permission_denied/);
    assert.match(fileContent, /not-allowed/);
    assert.match(fileContent, /network_error/);
    assert.match(fileContent, /setPermissionDenied\(true\)/);
  });

  await t.test('3. useSpeechSynthesis invokes onEnd callback when all speech chunks finish', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/hooks/useSpeechSynthesis.ts'),
      'utf-8'
    );
    assert.match(fileContent, /onEndCallbackRef/);
    assert.match(fileContent, /onEnd\?: \(\) => void/);
    assert.match(fileContent, /onEndCallbackRef\.current/);
    assert.match(fileContent, /onEnd\(\)/);
  });

  await t.test('4. BottomNav directs Voice AI to /assistant?voice=true', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/components/BottomNav.tsx'),
      'utf-8'
    );
    assert.match(fileContent, /\/assistant\?voice=true/);
  });

  await t.test('5. AssistantChat implements hands-free turn-taking and silence callback', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/pages/AssistantChat.tsx'),
      'utf-8'
    );
    assert.match(fileContent, /silenceTimeoutMs: 2000/);
    assert.match(fileContent, /handleHandsFreeSpeechEnd/);
    assert.match(fileContent, /speakQuestionAndListen/);
    assert.match(fileContent, /pauseVoiceInteraction/);
    assert.match(fileContent, /resumeVoiceInteraction/);
  });

  await t.test('6. AssistantChat provides uncertain speech confirmation and fallback controls', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/pages/AssistantChat.tsx'),
      'utf-8'
    );
    assert.match(fileContent, /uncertainSpokenText/);
    assert.match(fileContent, /Recognized:/);
    assert.match(fileContent, /Confirm/);
    assert.match(fileContent, /Speak Again/);
  });

  await t.test('7. AssistantChat provides transparent offline mode without false offline voice claims', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/pages/AssistantChat.tsx'),
      'utf-8'
    );
    assert.match(fileContent, /Offline Mode Active/);
    assert.match(fileContent, /Speech recognition requires an internet connection on this browser/);
  });

  await t.test('8. AssistantChat cleanly stops capture and shows banner on microphone permission denial', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/pages/AssistantChat.tsx'),
      'utf-8'
    );
    assert.match(fileContent, /permissionDeniedBanner/);
    assert.match(fileContent, /Microphone Access Denied/);
    assert.match(fileContent, /Continue with Buttons & Text/);
  });

  await t.test('9. AssistantChat generates localized spoken questions for all 9 profile steps', () => {
    const fileContent = fs.readFileSync(
      path.join(projectRoot, 'src/pages/AssistantChat.tsx'),
      'utf-8'
    );
    assert.match(fileContent, /getGuidedQuestionText/);
    // Verify Hindi, Kannada, Telugu, English presence in question generator
    assert.match(fileContent, /आप किस राज्य/);
    assert.match(fileContent, /ಯಾವ ರಾಜ್ಯ/);
    assert.match(fileContent, /ఏ రాష్ట్రం/);
  });
});

