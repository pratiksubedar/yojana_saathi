import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = process.cwd();

test('Voice AI Button — Architecture & Integration Verification', async (t) => {
  const bottomNavPath = path.join(projectRoot, 'src/components/BottomNav.tsx');
  const assistantChatPath = path.join(projectRoot, 'src/pages/AssistantChat.tsx');

  const bottomNavContent = fs.readFileSync(bottomNavPath, 'utf8');
  const assistantChatContent = fs.readFileSync(assistantChatPath, 'utf8');

  await t.test('1. BottomNav defines onVoiceClick prop and triggers it directly when on Assistant page', () => {
    assert.ok(
      bottomNavContent.includes('export interface BottomNavProps'),
      'BottomNav should export BottomNavProps interface'
    );
    assert.ok(
      bottomNavContent.includes('onVoiceClick?: () => void;'),
      'BottomNavProps must include optional onVoiceClick callback'
    );
    assert.ok(
      bottomNavContent.includes('isAssistantPage'),
      'BottomNav should detect if currently on /assistant page'
    );
    assert.ok(
      bottomNavContent.includes('onVoiceClick()'),
      'BottomNav should directly invoke onVoiceClick() if provided when already on Assistant'
    );
    assert.ok(
      bottomNavContent.includes("window.dispatchEvent(new CustomEvent('yojana:start-voice-ai'))"),
      'BottomNav should dispatch custom event as resilient cross-component bridge'
    );
    assert.ok(
      bottomNavContent.includes("navigate('/assistant?voice=true&mode=chat&start=' + Date.now())"),
      'BottomNav should navigate to /assistant with voice=true and mode=chat and timestamp'
    );
  });

  await t.test('2. AssistantChat connects onVoiceClick and handles immediate microphone activation', () => {
    assert.ok(
      assistantChatContent.includes('<BottomNav onVoiceClick={handleBottomVoiceClick} />'),
      'AssistantChat must pass handleBottomVoiceClick to BottomNav'
    );
    assert.ok(
      assistantChatContent.includes("window.addEventListener('yojana:start-voice-ai'"),
      'AssistantChat must listen for yojana:start-voice-ai custom event'
    );
    assert.ok(
      assistantChatContent.includes('handleBottomVoiceClick'),
      'AssistantChat must define handleBottomVoiceClick handler'
    );
  });

  await t.test('3. Prevents multiple simultaneous speech recognition sessions', () => {
    // Check that handleBottomVoiceClick guards against already-listening state
    assert.ok(
      assistantChatContent.includes('if (isListening || isListeningRef.current)'),
      'handleBottomVoiceClick must check if already listening and return early'
    );
  });

  await t.test('4. Gracefully handles microphone permission denied and allows text input', () => {
    assert.ok(
      assistantChatContent.includes('sttPermissionDenied || sttErrorType === \'permission_denied\''),
      'handleBottomVoiceClick must check for permission denied state'
    );
    assert.ok(
      assistantChatContent.includes('setPermissionDeniedBanner(true)'),
      'Must display the permission denied banner when permission is denied'
    );
    assert.ok(
      assistantChatContent.includes('inputRef.current?.focus()'),
      'Must focus text input to allow immediate text typing when mic is blocked'
    );
  });

  await t.test('5. Respects Pause Voice functionality without automatic background restarts', () => {
    assert.ok(
      assistantChatContent.includes('pauseVoiceInteraction = useCallback'),
      'Must provide pauseVoiceInteraction function'
    );
    assert.ok(
      assistantChatContent.includes('setIsVoicePaused(true)'),
      'pauseVoiceInteraction must set isVoicePaused to true'
    );
    // Background auto-listening loops must check !isVoicePaused
    assert.ok(
      assistantChatContent.includes('if (activeMode === \'chat\' && isVoiceActive && !isVoicePaused'),
      'Assistant speech end turn-taking must respect isVoicePaused'
    );
    assert.ok(
      assistantChatContent.includes('if (!isVoiceActive || isVoicePaused || !isOnline || sttPermissionDenied) return;'),
      'Guided mode step transitions must respect isVoicePaused'
    );
  });

  await t.test('6. User does NOT have to click the large central microphone button again', () => {
    // handleBottomVoiceClick directly calls startListening()
    assert.ok(
      assistantChatContent.includes('startListening();'),
      'handleBottomVoiceClick must directly call startListening() without requiring orb click'
    );
    // And initial mount or query params trigger handleBottomVoiceClick
    assert.ok(
      assistantChatContent.includes('handleBottomVoiceClick();'),
      'Auto-start effect must invoke handleBottomVoiceClick on navigation with voice params'
    );
  });

  await t.test('7. Preserves existing voice interaction behaviour and eligibility processing', () => {
    assert.ok(
      assistantChatContent.includes('handleHandsFreeSpeechEnd'),
      'Preserves hands-free speech end handler'
    );
    assert.ok(
      assistantChatContent.includes('handleGuidedVoiceInput'),
      'Preserves guided profile input processing from spoken text'
    );
    assert.ok(
      assistantChatContent.includes('handleSendMessage(trimmed, true)'),
      'Preserves chat mode voice message submission'
    );
    assert.ok(
      assistantChatContent.includes('executeGuidedEvaluation'),
      'Preserves full scheme rule engine evaluation after guided profile'
    );
  });

  await t.test('8. AI Support Chat is default mode and Guided Scheme Eligibility never opens automatically', () => {
    // 1. activeMode default initialization
    assert.ok(
      assistantChatContent.includes("isGuidedFromParam ? 'guided' : 'chat'"),
      'activeMode must default to chat unless isGuidedFromParam is explicitly present'
    );
    // 2. handleBottomVoiceClick explicitly ensures chat mode
    assert.ok(
      assistantChatContent.includes("setActiveMode('chat');"),
      'handleBottomVoiceClick must explicitly select AI Support Chat mode'
    );
    // 3. BottomNav explicitly navigates with mode=chat
    assert.ok(
      bottomNavContent.includes('mode=chat'),
      'BottomNav must specify mode=chat when routing to Assistant'
    );
    // 4. Stale guided params are cleaned up
    assert.ok(
      assistantChatContent.includes("updatedParams.delete('guided')"),
      'Stale guided query params must be cleared when entering via Voice AI'
    );
    // 5. Manual mode switching remains available
    assert.ok(
      assistantChatContent.includes("onClick={() => setActiveMode('guided')}"),
      'Manual mode switch to Guided Scheme Eligibility must remain available'
    );
    assert.ok(
      assistantChatContent.includes("onClick={() => setActiveMode('chat')}"),
      'Manual mode switch to AI Support Chat must remain available'
    );
  });

  await t.test('9. Hands-free voice input silence detection pause is configured to 2000ms (2 seconds)', () => {
    const speechRecPath = path.join(projectRoot, 'src/hooks/useSpeechRecognition.ts');
    const speechRecContent = fs.readFileSync(speechRecPath, 'utf8');

    assert.ok(
      assistantChatContent.includes('silenceTimeoutMs: 2000'),
      'AssistantChat must set silenceTimeoutMs to 2000ms'
    );
    assert.ok(
      speechRecContent.includes('silenceTimeoutMs || 2000'),
      'useSpeechRecognition must default silence timeout to 2000ms'
    );
  });
});

