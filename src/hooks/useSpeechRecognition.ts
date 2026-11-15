import { useState, useEffect, useRef, useCallback } from 'react';
import { Language } from '../types';
import { SPEECH_LOCALES } from '../data/translations';

// Web Speech API interface declarations
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: ((this: SpeechRecognitionInstance, ev: Event) => any) | null;
  onresult: ((this: SpeechRecognitionInstance, ev: SpeechRecognitionEvent) => any) | null;
  onerror: ((this: SpeechRecognitionInstance, ev: SpeechRecognitionErrorEvent) => any) | null;
  onend: ((this: SpeechRecognitionInstance, ev: Event) => any) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

export type SpeechRecognitionErrorType =
  | 'permission_denied'
  | 'no_microphone'
  | 'network_error'
  | 'no_speech'
  | 'aborted'
  | 'unknown';

export interface SpeechRecognitionOptions {
  silenceTimeoutMs?: number;
  onSilenceDetected?: (transcript: string) => void;
}

export const useSpeechRecognition = (language: Language, options?: SpeechRecognitionOptions) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<SpeechRecognitionErrorType | null>(null);
  const [isSupported, setIsSupported] = useState(true);
  const [permissionDenied, setPermissionDenied] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const interimBufferRef = useRef<string>('');
  const lastFinalChunkRef = useRef<string>('');
  const silenceTimeoutRef = useRef<any>(null);
  const speechSilenceTimerRef = useRef<any>(null);
  const isListeningRef = useRef<boolean>(false);
  const transcriptRef = useRef<string>('');
  const optionsRef = useRef<SpeechRecognitionOptions | undefined>(options);

  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const clearSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
    if (speechSilenceTimerRef.current) {
      clearTimeout(speechSilenceTimerRef.current);
      speechSilenceTimerRef.current = null;
    }
  }, []);

  const resetSilenceTimeout = useCallback(() => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
    // Auto-stop after 15 seconds of total continuous silence to preserve resources
    silenceTimeoutRef.current = setTimeout(() => {
      if (recognitionRef.current && isListeningRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    }, 15000);
  }, []);

  // Initialize browser Speech Recognition engine once on mount
  useEffect(() => {
    if (typeof window === 'undefined') {
      setIsSupported(false);
      return;
    }

    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) {
      setIsSupported(false);
      return;
    }

    setIsSupported(true);

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = SPEECH_LOCALES[language] || 'en-IN';

      recognition.onstart = () => {
        isListeningRef.current = true;
        setIsListening(true);
        setError(null);
        setErrorType(null);
        setPermissionDenied(false);
        resetSilenceTimeout();
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        resetSilenceTimeout();
        let currentInterim = '';
        let currentFinal = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item.isFinal) {
            currentFinal += item[0].transcript;
          } else {
            currentInterim += item[0].transcript;
          }
        }

        interimBufferRef.current = currentInterim;
        setInterimTranscript(currentInterim);

        let currentTotal = transcriptRef.current;
        if (currentFinal) {
          const cleanFinal = currentFinal.trim();
          // Guard against duplicate consecutive final chunks fired by some mobile Web Speech engines
          if (cleanFinal && cleanFinal.toLowerCase() !== lastFinalChunkRef.current.toLowerCase()) {
            lastFinalChunkRef.current = cleanFinal;
            currentTotal = currentTotal ? `${currentTotal} ${cleanFinal}` : cleanFinal;
            transcriptRef.current = currentTotal;
            setTranscript(currentTotal);
          }
          interimBufferRef.current = '';
          setInterimTranscript('');
        }

        // Active speech detected: Start 2s silence timer (default 2000ms)
        const combinedSpoken = (currentTotal + ' ' + currentInterim).trim();
        if (combinedSpoken && combinedSpoken.length >= 2) {
          if (speechSilenceTimerRef.current) {
            clearTimeout(speechSilenceTimerRef.current);
          }
          const timeoutMs = optionsRef.current?.silenceTimeoutMs || 2000;
          speechSilenceTimerRef.current = setTimeout(() => {
            if (isListeningRef.current) {
              const fullSpeech = (transcriptRef.current + ' ' + interimBufferRef.current).trim();
              if (fullSpeech && fullSpeech.length >= 2) {
                try {
                  recognitionRef.current?.stop();
                } catch {
                  // ignore
                }
                isListeningRef.current = false;
                setIsListening(false);
                optionsRef.current?.onSilenceDetected?.(fullSpeech);
              }
            }
          }, timeoutMs);
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.warn('Speech Recognition error event:', event.error);
        setError(event.error);

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setErrorType('permission_denied');
          setPermissionDenied(true);
          isListeningRef.current = false;
          setIsListening(false);
        } else if (event.error === 'audio-capture') {
          setErrorType('no_microphone');
          isListeningRef.current = false;
          setIsListening(false);
        } else if (event.error === 'network') {
          setErrorType('network_error');
          isListeningRef.current = false;
          setIsListening(false);
        } else if (event.error === 'no-speech') {
          setErrorType('no_speech');
          // Non-fatal; user may resume speaking
        } else if (event.error === 'aborted') {
          setErrorType('aborted');
          isListeningRef.current = false;
          setIsListening(false);
        } else {
          setErrorType('unknown');
          isListeningRef.current = false;
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        isListeningRef.current = false;
        setIsListening(false);
        clearSilenceTimeout();
        // Flush any remaining interim buffer to transcript on stop (only if not already committed)
        if (interimBufferRef.current.trim()) {
          const leftover = interimBufferRef.current.trim();
          if (leftover.toLowerCase() !== lastFinalChunkRef.current.toLowerCase()) {
            lastFinalChunkRef.current = leftover;
            const updated = transcriptRef.current ? `${transcriptRef.current} ${leftover}` : leftover;
            transcriptRef.current = updated;
            setTranscript(updated);
          }
          interimBufferRef.current = '';
        }
        setInterimTranscript('');
      };

      recognitionRef.current = recognition;
    } catch (err) {
      console.warn('Speech Recognition init error:', err);
      setIsSupported(false);
    }

    return () => {
      clearSilenceTimeout();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onstart = null;
          recognitionRef.current.onresult = null;
          recognitionRef.current.onerror = null;
          recognitionRef.current.onend = null;
          recognitionRef.current.abort();
        } catch {
          // ignore cleanup abort
        }
      }
    };
  }, [clearSilenceTimeout, resetSilenceTimeout]);

  // Update recognition language dynamically when language prop changes
  useEffect(() => {
    if (recognitionRef.current) {
      recognitionRef.current.lang = SPEECH_LOCALES[language] || 'en-IN';
    }
  }, [language]);

  const startListening = useCallback(() => {
    clearSilenceTimeout();
    if (!recognitionRef.current) return;
    setError(null);
    setErrorType(null);
    setPermissionDenied(false);

    try {
      recognitionRef.current.lang = SPEECH_LOCALES[language] || 'en-IN';
      recognitionRef.current.start();
    } catch (err: any) {
      // If already started, ignore InvalidStateError
      if (err.name !== 'InvalidStateError') {
        setError(err.message || 'Error starting speech recognition');
        setErrorType('unknown');
      }
    }
  }, [language, clearSilenceTimeout]);

  const stopListening = useCallback(() => {
    clearSilenceTimeout();
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch {
      // ignore
    }
    isListeningRef.current = false;
    setIsListening(false);
  }, [clearSilenceTimeout]);

  const abortListening = useCallback(() => {
    clearSilenceTimeout();
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.abort();
    } catch {
      // ignore
    }
    isListeningRef.current = false;
    interimBufferRef.current = '';
    setInterimTranscript('');
    setIsListening(false);
  }, [clearSilenceTimeout]);

  const resetTranscript = useCallback(() => {
    clearSilenceTimeout();
    transcriptRef.current = '';
    setTranscript('');
    setInterimTranscript('');
    interimBufferRef.current = '';
    lastFinalChunkRef.current = '';
    setError(null);
    setErrorType(null);
  }, [clearSilenceTimeout]);

  const setCustomTranscript = useCallback((text: string) => {
    transcriptRef.current = text;
    setTranscript(text);
    setInterimTranscript('');
    interimBufferRef.current = '';
  }, []);

  return {
    isSupported,
    isListening,
    transcript,
    interimTranscript,
    error,
    errorType,
    permissionDenied,
    startListening,
    stopListening,
    abortListening,
    resetTranscript,
    setCustomTranscript,
  };
};
