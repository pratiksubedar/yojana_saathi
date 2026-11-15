import { useState, useEffect, useCallback, useRef } from 'react';
import { Language } from '../types';
import { SPEECH_LOCALES } from '../data/translations';

// Maximum character length for a single SpeechSynthesisUtterance to prevent browser cutoffs
const MAX_CHUNK_LENGTH = 160;

/**
 * Splits long text into natural punctuation-bounded speech chunks.
 * Prevents Chromium/Safari speech synthesis from freezing or truncating at ~15 seconds.
 */
export function splitTextIntoSpeechChunks(text: string): string[] {
  if (!text || !text.trim()) return [];

  // Match sentences or clauses ending in period, question mark, exclamation, newline, or Indic danda (।)
  const rawSegments = text
    .replace(/([.!?।\n]+)/g, '$1|')
    .split('|')
    .map((s) => s.trim())
    .filter(Boolean);

  const chunks: string[] = [];
  let currentChunk = '';

  for (const segment of rawSegments) {
    if ((currentChunk + ' ' + segment).trim().length <= MAX_CHUNK_LENGTH) {
      currentChunk = currentChunk ? `${currentChunk} ${segment}` : segment;
    } else {
      if (currentChunk) {
        chunks.push(currentChunk);
      }
      // If a single segment is longer than MAX_CHUNK_LENGTH, break by comma or whitespace
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

export const useSpeechSynthesis = (defaultLanguage: Language = 'en', defaultRate: number = 1.0) => {
  const [isSupported, setIsSupported] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentSpeakingId, setCurrentSpeakingId] = useState<string | null>(null);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [hasVoiceForLanguage, setHasVoiceForLanguage] = useState<Record<Language, boolean>>({
    en: false,
    hi: false,
    kn: false,
    te: false,
  });
  const [voiceUnavailableWarning, setVoiceUnavailableWarning] = useState<Language | null>(null);

  const chunkQueueRef = useRef<string[]>([]);
  const currentChunkIndexRef = useRef<number>(0);
  const activeLangRef = useRef<Language>(defaultLanguage);
  const activeRateRef = useRef<number>(defaultRate);
  const cancelRequestedRef = useRef<boolean>(false);
  const onEndCallbackRef = useRef<(() => void) | null>(null);

  // Load and index voices from browser
  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setIsSupported(false);
      return;
    }

    setIsSupported(true);

    const updateVoices = () => {
      const available = window.speechSynthesis.getVoices();
      setVoices(available);

      const checkLang = (code: string, nameHints: string[]) => {
        const codePrefix = code.toLowerCase().split('-')[0];
        return available.some((v) => {
          const vLang = v.lang.toLowerCase();
          const vName = v.name.toLowerCase();
          if (vLang === code.toLowerCase() || vLang.startsWith(codePrefix)) {
            return true;
          }
          return nameHints.some((hint) => vName.includes(hint.toLowerCase()));
        });
      };

      setHasVoiceForLanguage({
        en: checkLang('en-IN', ['english', 'en-']),
        hi: checkLang('hi-IN', ['hindi', 'lekha', 'hi-']),
        kn: checkLang('kn-IN', ['kannada', 'kn-']),
        te: checkLang('te-IN', ['telugu', 'te-']),
      });
    };

    updateVoices();

    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }

    return () => {
      cancelRequestedRef.current = true;
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const findBestVoice = useCallback(
    (lang: Language): SpeechSynthesisVoice | null => {
      if (!voices.length) return null;
      const targetLocale = (SPEECH_LOCALES[lang] || 'en-IN').toLowerCase();
      const langPrefix = targetLocale.split('-')[0].toLowerCase();

      // 1. Check authentic Indian accent voice hints first
      const indianVoiceHints: Record<Language, string[]> = {
        en: ['en-in', 'india', 'indian', 'rishi', 'veena', 'sangeeta', 'kavya', 'aarav', 'heera', 'google indian english'],
        hi: ['hi-in', 'hindi', 'lekha', 'neerja', 'swara', 'madhur', 'google हिन्दी'],
        kn: ['kn-in', 'kannada', 'sapna'],
        te: ['te-in', 'telugu', 'chitra'],
      };

      const hints = indianVoiceHints[lang] || [];
      const indianVoice = voices.find((v) => {
        const vLang = v.lang.toLowerCase().replace('_', '-');
        const vName = v.name.toLowerCase();
        return (
          vLang === targetLocale ||
          hints.some((hint) => vLang.includes(hint) || vName.includes(hint))
        );
      });
      if (indianVoice) return indianVoice;

      // 2. Exact locale match
      const exact = voices.find((v) => v.lang.toLowerCase().replace('_', '-') === targetLocale);
      if (exact) return exact;

      // 3. Language prefix match (e.g. 'hi', 'kn', 'te')
      const prefixMatch = voices.find((v) => v.lang.toLowerCase().startsWith(langPrefix));
      if (prefixMatch) return prefixMatch;

      // 4. Fallback for English: any English voice
      if (lang === 'en') {
        const enVoice = voices.find((v) => v.lang.toLowerCase().startsWith('en'));
        if (enVoice) return enVoice;
      }

      // For regional Indic languages without installed voice, return null to avoid speaking English voice with Indic text
      return null;
    },
    [voices]
  );

  const playNextChunk = useCallback(() => {
    if (cancelRequestedRef.current) {
      setIsSpeaking(false);
      setIsPaused(false);
      setCurrentSpeakingId(null);
      return;
    }

    const chunks = chunkQueueRef.current;
    const index = currentChunkIndexRef.current;

    if (index >= chunks.length) {
      setIsSpeaking(false);
      setIsPaused(false);
      setCurrentSpeakingId(null);
      const onEnd = onEndCallbackRef.current;
      onEndCallbackRef.current = null;
      if (onEnd && !cancelRequestedRef.current) {
        onEnd();
      }
      return;
    }

    const chunkText = chunks[index];
    const lang = activeLangRef.current;
    const rate = activeRateRef.current;

    const utterance = new SpeechSynthesisUtterance(chunkText);
    utterance.lang = SPEECH_LOCALES[lang] || 'en-IN';
    utterance.rate = Math.max(0.6, Math.min(1.8, rate));

    const voice = findBestVoice(lang);
    if (voice) {
      utterance.voice = voice;
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      setIsPaused(false);
    };

    utterance.onend = () => {
      if (!cancelRequestedRef.current) {
        currentChunkIndexRef.current += 1;
        playNextChunk();
      }
    };

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis chunk playback error:', e);
      if (!cancelRequestedRef.current) {
        currentChunkIndexRef.current += 1;
        playNextChunk();
      }
    };

    window.speechSynthesis.speak(utterance);
  }, [findBestVoice]);

  const speak = useCallback(
    (text: string, options?: { lang?: Language; rate?: number; messageId?: string; onEnd?: () => void }) => {
      if (!isSupported || typeof window === 'undefined' || !('speechSynthesis' in window)) {
        return;
      }

      // Cancel any ongoing speech or queue
      cancelRequestedRef.current = true;
      onEndCallbackRef.current = null;
      window.speechSynthesis.cancel();

      if (!text || !text.trim()) {
        setIsSpeaking(false);
        setIsPaused(false);
        setCurrentSpeakingId(null);
        return;
      }

      const lang = options?.lang || defaultLanguage;
      const rate = options?.rate !== undefined ? options.rate : defaultRate;
      const msgId = options?.messageId || null;

      activeLangRef.current = lang;
      activeRateRef.current = rate;
      setCurrentSpeakingId(msgId);
      setVoiceUnavailableWarning(null);
      onEndCallbackRef.current = options?.onEnd || null;

      // Verify voice availability for regional Indic languages
      const bestVoice = findBestVoice(lang);
      if (lang !== 'en' && !bestVoice) {
        // Voice is unavailable on this OS / browser for the selected Indic language
        setVoiceUnavailableWarning(lang);
        setIsSpeaking(false);
        setIsPaused(false);
        return;
      }

      // Split text into safe chunks to prevent Chrome utterance freeze
      const chunks = splitTextIntoSpeechChunks(text);
      chunkQueueRef.current = chunks;
      currentChunkIndexRef.current = 0;
      cancelRequestedRef.current = false;

      playNextChunk();
    },
    [isSupported, defaultLanguage, defaultRate, findBestVoice, playNextChunk]
  );

  const stop = useCallback(() => {
    cancelRequestedRef.current = true;
    onEndCallbackRef.current = null;
    chunkQueueRef.current = [];
    currentChunkIndexRef.current = 0;
    if (isSupported && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setIsPaused(false);
      setCurrentSpeakingId(null);
    }
  }, [isSupported]);

  const pause = useCallback(() => {
    if (isSupported && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  }, [isSupported]);

  const resume = useCallback(() => {
    if (isSupported && typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.resume();
      setIsPaused(false);
    }
  }, [isSupported]);

  return {
    isSupported,
    isSpeaking,
    isPaused,
    currentSpeakingId,
    hasVoiceForLanguage,
    voiceUnavailableWarning,
    voices,
    speak,
    stop,
    pause,
    resume,
  };
};
