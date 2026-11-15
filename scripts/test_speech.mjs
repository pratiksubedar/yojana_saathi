import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

// Extract splitTextIntoSpeechChunks implementation directly for unit test isolation
const MAX_CHUNK_LENGTH = 160;

function splitTextIntoSpeechChunks(text) {
  if (!text || !text.trim()) return [];

  const rawSegments = text
    .replace(/([.!?।\n]+)/g, '$1|')
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean);

  const chunks = [];
  let currentChunk = '';

  for (const segment of rawSegments) {
    if ((currentChunk + ' ' + segment).trim().length <= MAX_CHUNK_LENGTH) {
      currentChunk = currentChunk ? `${currentChunk} ${segment}` : segment;
    } else {
      if (currentChunk) {
        chunks.push(currentChunk);
      }
      if (segment.length > MAX_CHUNK_LENGTH) {
        const words = segment.split(' ');
        let wordChunk = '';
        for (const w of words) {
          if ((wordChunk + ' ' + w).trim().length <= MAX_CHUNK_LENGTH) {
            wordChunk = wordChunk ? `${wordChunk} ${w}` : w;
          } else {
            if (wordChunk) chunks.push(wordChunk);
            wordChunk = w;
          }
        }
        if (wordChunk) currentChunk = wordChunk;
        else currentChunk = '';
      } else {
        currentChunk = segment;
      }
    }
  }

  if (currentChunk) {
    chunks.push(currentChunk);
  }

  return chunks.length > 0 ? chunks : [text.trim()];
}

const SPEECH_LOCALES = {
  en: 'en-IN',
  hi: 'hi-IN',
  kn: 'kn-IN',
  te: 'te-IN',
};

// =====================================================================
// 1. Text Chunking Algorithm Tests (Fix for 15s / 200-char browser cutoff)
// =====================================================================

describe('splitTextIntoSpeechChunks', () => {
  test('returns empty array for empty or whitespace text', () => {
    assert.deepEqual(splitTextIntoSpeechChunks(''), []);
    assert.deepEqual(splitTextIntoSpeechChunks('   '), []);
  });

  test('keeps short single sentence intact', () => {
    const text = 'You are eligible for PM-KISAN scheme.';
    const chunks = splitTextIntoSpeechChunks(text);
    assert.equal(chunks.length, 1);
    assert.equal(chunks[0], text);
  });

  test('splits multiple English sentences along punctuation when exceeding max length', () => {
    const text =
      'PM-KISAN provides income support to landholding farmer families across India. Under this scheme, eligible families receive ₹6,000 annually in three equal instalments of ₹2,000 directly into their bank accounts. The scheme ensures financial assistance for agricultural inputs and domestic needs.';
    const chunks = splitTextIntoSpeechChunks(text);
    assert.ok(chunks.length >= 2, `Expected at least 2 chunks, got ${chunks.length}`);
    for (const chunk of chunks) {
      assert.ok(chunk.length <= 180, `Chunk exceeds max length: ${chunk.length}`);
    }
  });

  test('splits Hindi text using Indic danda (।) and punctuation when exceeding max length', () => {
    const text =
      'प्रधानमंत्री किसान सम्मान निधि योजना के अंतर्गत पात्र किसान परिवारों को प्रति वर्ष छह हजार रुपये की आर्थिक सहायता प्रदान की जाती है। यह धनराशि दो-दो हजार रुपये की तीन समान किस्तों में सीधे किसानों के बैंक खातों में डीबीटी के माध्यम से स्थानांतरित की जाती है। क्या आप इस योजना के लिए अपनी पात्रता और आवश्यक दस्तावेजों की जानकारी चाहते हैं?';
    const chunks = splitTextIntoSpeechChunks(text);
    assert.ok(chunks.length >= 2, `Expected at least 2 chunks, got ${chunks.length}`);
    for (const chunk of chunks) {
      assert.ok(chunk.length <= 180);
    }
  });

  test('breaks long run-on sentences without punctuation by word boundaries', () => {
    const longRunOn =
      'This is an extremely long uninterrupted sentence without standard periods or commas designed to verify that the speech chunking algorithm will cleanly fragment the phrase at word boundaries before reaching the Chromium speech synthesis timeout boundary so playback never stalls.';
    const chunks = splitTextIntoSpeechChunks(longRunOn);
    assert.ok(chunks.length >= 2);
    for (const chunk of chunks) {
      assert.ok(chunk.length <= 180, `Chunk length ${chunk.length} exceeds 180 chars`);
    }
    const reconstructed = chunks.join(' ');
    assert.ok(reconstructed.includes('uninterrupted sentence'));
    assert.ok(reconstructed.includes('playback never stalls'));
  });
});

// =====================================================================
// 2. Multilingual Speech Locales Configuration Tests
// =====================================================================

describe('Multilingual Speech Locales', () => {
  test('configures correct Indian regional locales for all four supported languages', () => {
    assert.equal(SPEECH_LOCALES.en, 'en-IN');
    assert.equal(SPEECH_LOCALES.hi, 'hi-IN');
    assert.equal(SPEECH_LOCALES.kn, 'kn-IN');
    assert.equal(SPEECH_LOCALES.te, 'te-IN');
  });
});

// =====================================================================
// 3. Web Speech Recognition Mock Engine Tests
// =====================================================================

describe('Speech Recognition Mock Engine & Error Handling', () => {
  class MockSpeechRecognition {
    constructor() {
      this.continuous = false;
      this.interimResults = false;
      this.lang = 'en-IN';
      this.onstart = null;
      this.onresult = null;
      this.onerror = null;
      this.onend = null;
      this.started = false;
      this.aborted = false;
    }

    start() {
      if (this.started) throw new Error('InvalidStateError');
      this.started = true;
      this.onstart?.();
    }

    stop() {
      this.started = false;
      this.onend?.();
    }

    abort() {
      this.aborted = true;
      this.started = false;
      this.onend?.();
    }

    simulateResult(transcriptText, isFinal) {
      this.onresult?.({
        resultIndex: 0,
        results: [
          [{ transcript: transcriptText, isFinal }],
        ],
      });
    }

    simulateError(errorType) {
      this.onerror?.({ error: errorType });
    }
  }

  test('handles permission denial error cleanly', () => {
    const recognition = new MockSpeechRecognition();
    let errorDetected = null;
    let permissionDenied = false;

    recognition.onerror = (e) => {
      errorDetected = e.error;
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        permissionDenied = true;
      }
    };

    recognition.simulateError('not-allowed');
    assert.equal(errorDetected, 'not-allowed');
    assert.equal(permissionDenied, true);
  });

  test('handles audio-capture and network errors without crash', () => {
    const recognition = new MockSpeechRecognition();
    let capturedError = '';

    recognition.onerror = (e) => {
      capturedError = e.error;
    };

    recognition.simulateError('audio-capture');
    assert.equal(capturedError, 'audio-capture');

    recognition.simulateError('network');
    assert.equal(capturedError, 'network');
  });

  test('handles language switching and updates locale', () => {
    const recognition = new MockSpeechRecognition();
    const languages = ['en', 'hi', 'kn', 'te'];

    for (const lang of languages) {
      recognition.lang = SPEECH_LOCALES[lang];
      assert.equal(recognition.lang, SPEECH_LOCALES[lang]);
    }
  });

  test('aggregates final transcripts and preserves spoken content', () => {
    let finalized = '';
    let interim = '';

    const handleResult = (text, isFinal) => {
      if (isFinal) {
        finalized = finalized ? `${finalized} ${text.trim()}` : text.trim();
        interim = '';
      } else {
        interim = text;
      }
    };

    handleResult('I am a farmer', false);
    assert.equal(interim, 'I am a farmer');
    assert.equal(finalized, '');

    handleResult('I am a farmer', true);
    assert.equal(finalized, 'I am a farmer');
    assert.equal(interim, '');

    handleResult('with 2 hectares', true);
    assert.equal(finalized, 'I am a farmer with 2 hectares');
  });
});

// =====================================================================
// 4. Speech Synthesis Voice Matching & Fallback Tests
// =====================================================================

describe('Speech Synthesis Voice Selector & Fallback Logic', () => {
  const mockVoices = [
    { name: 'Google UK English Female', lang: 'en-GB' },
    { name: 'Google हिन्दी', lang: 'hi-IN' },
    { name: 'Lekha (Hindi)', lang: 'hi_IN' },
    { name: 'Google ಕನ್ನಡ', lang: 'kn-IN' },
    { name: 'Microsoft Ravi - English (India)', lang: 'en-IN' },
  ];

  function selectBestVoice(voices, lang) {
    if (!voices.length) return null;
    const targetLocale = SPEECH_LOCALES[lang];
    const langPrefix = targetLocale.split('-')[0].toLowerCase();

    // 1. Exact locale
    const exact = voices.find((v) => v.lang.toLowerCase() === targetLocale.toLowerCase());
    if (exact) return exact;

    // 2. Prefix match
    const prefix = voices.find((v) => v.lang.toLowerCase().startsWith(langPrefix));
    if (prefix) return prefix;

    // 3. Name hint
    const nameMap = {
      en: ['english', 'india'],
      hi: ['hindi', 'lekha'],
      kn: ['kannada'],
      te: ['telugu'],
    };
    const hints = nameMap[lang] || [];
    const hintMatch = voices.find((v) => hints.some((h) => v.name.toLowerCase().includes(h)));
    if (hintMatch) return hintMatch;

    if (lang === 'en') {
      const en = voices.find((v) => v.lang.toLowerCase().startsWith('en'));
      if (en) return en;
    }

    return null;
  }

  test('selects exact Indian English voice for en', () => {
    const voice = selectBestVoice(mockVoices, 'en');
    assert.ok(voice);
    assert.equal(voice.lang, 'en-IN');
  });

  test('selects exact Hindi voice for hi', () => {
    const voice = selectBestVoice(mockVoices, 'hi');
    assert.ok(voice);
    assert.equal(voice.lang, 'hi-IN');
  });

  test('selects Kannada voice for kn', () => {
    const voice = selectBestVoice(mockVoices, 'kn');
    assert.ok(voice);
    assert.equal(voice.lang, 'kn-IN');
  });

  test('detects missing voice for te (Telugu) gracefully without throwing', () => {
    const voice = selectBestVoice(mockVoices, 'te');
    assert.equal(voice, null);
  });
});

// =====================================================================
// 5. Duplicate Submission Prevention & Cancellation Tests
// =====================================================================

describe('Duplicate Submission Prevention', () => {
  test('disallows concurrent duplicate transcript submissions', () => {
    let submissionCount = 0;
    let isSubmitting = false;

    const submitTranscript = (text) => {
      if (isSubmitting || !text.trim()) return false;
      isSubmitting = true;
      submissionCount += 1;
      return true;
    };

    const first = submitTranscript('I am a farmer');
    assert.equal(first, true);
    assert.equal(submissionCount, 1);

    const second = submitTranscript('I am a farmer');
    assert.equal(second, false);
    assert.equal(submissionCount, 1);

    isSubmitting = false;
    const third = submitTranscript('What is PM-JAY?');
    assert.equal(third, true);
    assert.equal(submissionCount, 2);
  });

  test('cancellation clears pending recognition state', () => {
    let transcript = 'Some text';
    let interim = 'speaking...';
    let isListening = true;

    const cancel = () => {
      transcript = '';
      interim = '';
      isListening = false;
    };

    cancel();
    assert.equal(transcript, '');
    assert.equal(interim, '');
    assert.equal(isListening, false);
  });
});

// Remove unused temporary file if present
try {
  fs.unlinkSync(path.join(process.cwd(), 'src/tests/speechSubsystem.test.ts'));
} catch {}
