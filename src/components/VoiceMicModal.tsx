import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mic,
  MicOff,
  X,
  MessageSquare,
  Sparkles,
  Volume2,
  Square,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  WifiOff,
  Globe,
  Edit3,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';
import { LANGUAGES, t } from '../data/translations';
import { Language } from '../types';
import { detectLanguageFromTranscript } from '../utils/languageDetection';
import { normalizeDomainTranscript, UncertainTerm } from '../utils/transcriptNormalizer';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onTranscriptSubmitted?: (text: string) => void;
}

const LOCALIZED_SAMPLE_QUERIES: Record<Language, string[]> = {
  en: [
    'I am a 38-year-old farmer with 1.2 hectares land. Which welfare schemes can I get?',
    'How do I apply for Ayushman Bharat ₹5 Lakh cashless health cover?',
    'I need financial grant for building a permanent house in rural area.',
    'What are the eligibility criteria for PM SVANidhi street vendor loans?',
  ],
  hi: [
    'मैं 38 वर्ष का किसान हूँ, 1.2 हेक्टेयर ज़मीन है। मुझे कौन सी योजना मिलेगी?',
    '5 लाख रुपये तक का मुफ्त इलाज कैसे मिलेगा? आयुष्मान कार्ड बनवाना है।',
    'ग्रामीण क्षेत्र में पक्का घर बनाने के लिए सरकारी सहायता चाहिए।',
    'स्ट्रीट वेंडर के लिए लोन योजना की क्या शर्तें हैं?',
  ],
  kn: [
    'ನಾನು 38 ವರ್ಷದ ರೈತ, 1.2 ಹೆಕ್ಟೇರ್ ಭೂಮಿ ಇದೆ. ನನಗೆ ಯಾವ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಲಭ್ಯವಿವೆ?',
    'ಆಯುಷ್ಮಾನ್ ಭಾರತ್ ಯೋಜನೆಯಡಿ ₹5 ಲಕ್ಷದವರೆಗೆ ಉಚಿತ ಚಿಕಿತ್ಸೆ ಹೇಗೆ ಪಡೆಯುವುದು?',
    'ಗ್ರಾಮೀಣ ಭಾಗದಲ್ಲಿ ಪಕ್ಕಾ ಮನೆ ನಿರ್ಮಿಸಲು ಸರ್ಕಾರದಿಂದ ಧನಸಹಾಯ ಪಡೆಯುವುದು ಹೇಗೆ?',
    'ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿಗಳ ಪಿಎಂ ಸ್ವನಿಧಿ ಸಾಲ ಯೋಜನೆಯ ನಿಯಮಗಳು ಯಾವುವು?',
  ],
  te: [
    'నేను 38 ఏళ్ల రైతును, నాకు 1.2 హెక్టార్ల వ్యవసాయ భూమి ఉంది. నాకు ఏ పథకాలు వర్తిస్తాయి?',
    'ఆయుష్మాన్ భారత్ పథకం ద్వారా ₹5 లక్షల ఉచిత వైద్యం ఎలా పొందాలి?',
    'గ్రామీణ ప్రాంతంలో పక్కా గృహ నిర్మాణానికి ప్రభుత్వ ఆర్థిక సహాయం కావాలి.',
    'వీధి వ్యాపారుల పిఎం స్వనిధి రుణ పథకం అర్హతలు ఏమిటి?',
  ],
};

export const VoiceMicModal: React.FC<Props> = ({ isOpen, onClose, onTranscriptSubmitted }) => {
  const navigate = useNavigate();
  const { language, setLanguage } = useApp();

  // Keep speech recognition language synchronized with modal language (user can correct it anytime)
  const [modalLanguage, setModalLanguage] = useState<Language>(language);
  const [rawRecognized, setRawRecognized] = useState<string>('');
  const [editableTranscript, setEditableTranscript] = useState<string>('');
  const [uncertainTerms, setUncertainTerms] = useState<UncertainTerm[]>([]);
  const [detectedStatus, setDetectedStatus] = useState<'none' | 'script_match' | 'uncertain' | 'manual'>('none');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [activeQueryIndex, setActiveQueryIndex] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isSubmittingRef = useRef(false);
  const userEditedRef = useRef(false);
  const wasOpenRef = useRef(false);

  const {
    isSupported,
    isListening,
    transcript,
    interimTranscript,
    errorType,
    permissionDenied,
    startListening,
    stopListening,
    abortListening,
    resetTranscript,
    setCustomTranscript,
  } = useSpeechRecognition(modalLanguage);

  // Open / close lifecycle: only reset when isOpen transitions, never when language changes
  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      wasOpenRef.current = true;
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        try {
          window.speechSynthesis.cancel();
        } catch {
          // ignore
        }
      }
      isSubmittingRef.current = false;
      userEditedRef.current = false;
      setIsSubmitting(false);
      setModalLanguage(language);
      setRawRecognized('');
      setEditableTranscript('');
      setUncertainTerms([]);
      setDetectedStatus('none');
      setValidationError(null);
      setActiveQueryIndex(null);
      resetTranscript();
      if (isSupported) {
        startListening();
      }
    } else if (!isOpen && wasOpenRef.current) {
      wasOpenRef.current = false;
      abortListening();
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }, [isOpen, language, isSupported, startListening, abortListening, resetTranscript]);

  // Synchronize live speech recognition transcript + domain normalization into editable textarea
  useEffect(() => {
    if (!isOpen) return;
    const combined = (transcript || interimTranscript).trim();
    if (!combined) return;

    setRawRecognized(combined);

    if (!userEditedRef.current || isListening) {
      const normalized = normalizeDomainTranscript(combined, modalLanguage);
      setEditableTranscript(normalized.correctedTranscript);
      setUncertainTerms(normalized.uncertainTerms);
      setValidationError(null);
    }

    const detection = detectLanguageFromTranscript(combined, modalLanguage);
    if (detection.isAutoDetected && detection.confidence === 'script_match') {
      setDetectedStatus('script_match');
      if (detection.detectedLanguage !== modalLanguage) {
        setModalLanguage(detection.detectedLanguage);
      }
    } else if (detectedStatus === 'none') {
      setDetectedStatus('uncertain');
    }
  }, [transcript, interimTranscript, isOpen, isListening, modalLanguage, detectedStatus]);

  // Escape to cancel
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  if (!isOpen) return null;

  const currentQueries = LOCALIZED_SAMPLE_QUERIES[modalLanguage] || LOCALIZED_SAMPLE_QUERIES.en;

  const handleLanguageChange = (newLang: Language) => {
    setModalLanguage(newLang);
    setLanguage(newLang);
    setDetectedStatus('manual');
    if (isListening) {
      stopListening();
    }
  };

  const handleSelectSample = (sampleText: string, idx: number) => {
    stopListening();
    userEditedRef.current = false;
    setActiveQueryIndex(idx);
    setCustomTranscript(sampleText);
    setEditableTranscript(sampleText);
    setValidationError(null);

    const detection = detectLanguageFromTranscript(sampleText, modalLanguage);
    setDetectedStatus(detection.isAutoDetected ? 'script_match' : 'uncertain');
  };

  const handleRetryRecording = () => {
    userEditedRef.current = false;
    setEditableTranscript('');
    setValidationError(null);
    setActiveQueryIndex(null);
    setDetectedStatus('none');
    resetTranscript();
    if (isSupported && !permissionDenied) {
      startListening();
    }
  };

  const handleClearTranscript = () => {
    userEditedRef.current = false;
    setEditableTranscript('');
    setValidationError(null);
    setActiveQueryIndex(null);
    setDetectedStatus('none');
    resetTranscript();
  };

  const handleCancel = () => {
    abortListening();
    resetTranscript();
    setEditableTranscript('');
    onClose();
  };

  const handleConfirmAndSend = () => {
    const finalQuery = editableTranscript.trim();
    if (!finalQuery) {
      setValidationError('Please speak or type a question before sending.');
      return;
    }
    if (finalQuery.includes('[acres/hectares?]')) {
      setValidationError('Please confirm the uncertain land unit (acres or hectares) before sending.');
      return;
    }
    if (isSubmittingRef.current) return;

    isSubmittingRef.current = true;
    setIsSubmitting(true);
    stopListening();

    // Keep global app language synchronized with confirmed modal language
    if (modalLanguage !== language) {
      setLanguage(modalLanguage);
    }

    if (onTranscriptSubmitted) {
      onClose();
      onTranscriptSubmitted(finalQuery);
      return;
    }

    onClose();
    navigate(`/assistant?q=${encodeURIComponent(finalQuery)}&voice=true`);
  };

  const handleSwitchToText = () => {
    const pendingText = editableTranscript.trim();
    abortListening();
    onClose();
    if (pendingText) {
      navigate(`/assistant?q=${encodeURIComponent(pendingText)}`);
    } else {
      navigate('/assistant');
    }
  };

  const renderErrorBanner = () => {
    if (permissionDenied || errorType === 'permission_denied') {
      return (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-card flex items-start gap-2.5 text-xs text-status-red" role="alert">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block">{t('scenario1Title', modalLanguage)}</span>
            <p className="mt-0.5 leading-relaxed">{t('micPermissionDenied', modalLanguage)}</p>
          </div>
        </div>
      );
    }

    if (errorType === 'no_microphone') {
      return (
        <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-card flex items-start gap-2.5 text-xs text-status-red" role="alert">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block">{t('micNoMicrophoneFound', modalLanguage)}</span>
          </div>
        </div>
      );
    }

    if (errorType === 'network_error') {
      return (
        <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-card flex items-start gap-2.5 text-xs text-status-amber" role="alert">
          <WifiOff className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block">{t('micNetworkError', modalLanguage)}</span>
          </div>
        </div>
      );
    }

    if (errorType === 'no_speech') {
      return (
        <div className="mb-3 p-3 bg-neutral-canvas border border-neutral-mist rounded-card flex items-start gap-2.5 text-xs text-neutral-slate" role="status">
          <MicOff className="w-4 h-4 flex-shrink-0 mt-0.5 text-brand-indigo" />
          <div>
            <span className="font-medium block">{t('micNoAudioDetected', modalLanguage)}</span>
          </div>
        </div>
      );
    }

    if (!isSupported) {
      return (
        <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-card flex items-start gap-2.5 text-xs text-status-amber" role="alert">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block">Web Speech API Notice</span>
            <p className="mt-0.5 leading-relaxed">{t('browserSpeechNotSupported', modalLanguage)}</p>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-label={t('voiceModalTitleListening', modalLanguage)}
    >
      <div className="bg-white rounded-t-2xl sm:rounded-2xl max-w-lg w-full p-5 sm:p-6 shadow-modal border border-neutral-mist relative max-h-[92vh] overflow-y-auto">
        {/* Close / Cancel Button */}
        <button
          onClick={handleCancel}
          className="absolute top-4 right-4 p-2 text-neutral-slate hover:text-neutral-ink rounded-full hover:bg-neutral-mist/50 transition-colors"
          aria-label={t('cancelVoiceModalAction', modalLanguage)}
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="text-center mb-3">
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-brand-indigo-tint text-brand-indigo border border-brand-indigo/20 mb-2">
            <Sparkles className="w-3.5 h-3.5 text-brand-orange" />
            {isSupported ? t('browserSpeechEngineActive', modalLanguage) : t('aiBetaBadge', modalLanguage)}
          </span>
          <h2 className="font-heading font-bold text-xl text-neutral-ink">
            {isListening
              ? t('voiceModalTitleListening', modalLanguage)
              : editableTranscript.trim()
              ? 'Review & Edit Transcript'
              : t('voiceModalTitleReady', modalLanguage)}
          </h2>
          <p className="text-xs text-neutral-slate mt-1">
            {t('voiceModalListeningSubtext', modalLanguage)}
          </p>
        </div>

        {/* Language Confirmation & Correction Bar */}
        <div className="bg-neutral-canvas border border-neutral-mist rounded-card p-2.5 mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs">
            <Globe className="w-3.5 h-3.5 text-brand-indigo" />
            <span className="font-semibold text-neutral-ink">Language:</span>
            {detectedStatus === 'script_match' && (
              <span className="text-[11px] font-semibold text-status-green bg-status-green-bg px-2 py-0.5 rounded-full">
                Detected from script
              </span>
            )}
            {detectedStatus === 'uncertain' && (
              <span className="text-[11px] font-medium text-amber-800 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                Confirm language
              </span>
            )}
            {detectedStatus === 'manual' && (
              <span className="text-[11px] font-medium text-brand-indigo bg-brand-indigo-tint px-2 py-0.5 rounded-full">
                Selected manually
              </span>
            )}
          </div>

          <select
            aria-label="Speech recognition language"
            value={modalLanguage}
            onChange={(e) => handleLanguageChange(e.target.value as Language)}
            className="text-xs font-bold text-brand-indigo bg-white border border-brand-indigo/30 rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-brand-indigo"
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.nativeName} ({lang.name})
              </option>
            ))}
          </select>
        </div>

        {/* Dynamic Error & Status Banner */}
        {renderErrorBanner()}

        {/* Animated Mic & Controls */}
        <div className="flex flex-col items-center justify-center py-2">
          <div className="relative mb-2.5">
            <button
              onClick={isListening ? stopListening : startListening}
              disabled={!isSupported || permissionDenied}
              aria-label={isListening ? t('stopListeningAction', modalLanguage) : t('startListeningAction', modalLanguage)}
              className={`w-16 h-16 rounded-full flex items-center justify-center shadow-lg transition-transform active:scale-95 focus:outline-none focus:ring-4 focus:ring-brand-indigo/30 ${
                isListening
                  ? 'bg-brand-orange text-white ring-8 ring-brand-orange/20 animate-pulse'
                  : 'bg-brand-indigo text-white hover:bg-brand-indigo-hover'
              } disabled:opacity-50`}
            >
              {isListening ? <Mic className="w-7 h-7" /> : <MicOff className="w-7 h-7" />}
            </button>
          </div>

          <div className="flex items-center gap-2 mb-2" aria-live="polite">
            {isListening ? (
              <div className="flex items-center gap-1.5 h-5">
                <span className="w-1.5 h-3 bg-brand-indigo rounded-full animate-voice-wave-1"></span>
                <span className="w-1.5 h-5 bg-brand-indigo rounded-full animate-voice-wave-2"></span>
                <span className="w-1.5 h-3 bg-brand-orange rounded-full animate-voice-wave-3"></span>
                <span className="w-1.5 h-6 bg-brand-indigo rounded-full animate-voice-wave-4"></span>
                <span className="w-1.5 h-3 bg-brand-indigo rounded-full animate-voice-wave-5"></span>
              </div>
            ) : (
              <span className="text-xs text-neutral-slate font-medium">
                {editableTranscript.trim()
                  ? 'Review or edit your text below before sending'
                  : t('tapToSpeak', modalLanguage)}
              </span>
            )}
          </div>

          {/* Retry / Stop listening controls */}
          {isSupported && !permissionDenied && (
            <div className="flex items-center gap-4 mb-2">
              {isListening ? (
                <button
                  type="button"
                  onClick={stopListening}
                  className="inline-flex items-center gap-1 text-xs font-bold text-status-red hover:underline focus:outline-none"
                >
                  <Square className="w-3.5 h-3.5 fill-status-red" />
                  <span>{t('stopListeningAction', modalLanguage)}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleRetryRecording}
                  className="inline-flex items-center gap-1 text-xs font-bold text-brand-indigo hover:underline focus:outline-none"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Retry Recording</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Editable Transcript Box */}
        <div className="bg-neutral-canvas border border-brand-indigo/30 rounded-card p-3 mb-3">
          <div className="flex items-center justify-between text-[11px] font-semibold text-brand-indigo mb-1.5">
            <span className="inline-flex items-center gap-1">
              <Edit3 className="w-3.5 h-3.5" />
              <span>{t('recognizedTranscriptLabel', modalLanguage)} (Editable)</span>
            </span>
            {editableTranscript && (
              <button
                type="button"
                onClick={handleClearTranscript}
                className="text-neutral-slate hover:text-neutral-ink font-normal text-[11px] underline"
              >
                Clear
              </button>
            )}
          </div>

          <textarea
            aria-label="Editable speech transcript"
            rows={3}
            value={editableTranscript}
            onChange={(e) => {
              userEditedRef.current = true;
              setEditableTranscript(e.target.value);
              if (!e.target.value.includes('[acres/hectares?]')) {
                setUncertainTerms([]);
              }
              setValidationError(null);
            }}
            placeholder={
              isListening
                ? 'Listening... speak now, or type to edit'
                : 'Speak into the microphone, pick a sample, or type your question here...'
            }
            className="w-full bg-white border border-neutral-mist rounded-lg p-2.5 text-sm text-neutral-ink leading-relaxed focus:outline-none focus:ring-2 focus:ring-brand-indigo resize-none"
          />

          {rawRecognized && rawRecognized !== editableTranscript && (
            <p className="text-[11px] text-neutral-slate mt-1.5">
              Original heard: <span className="italic">&ldquo;{rawRecognized}&rdquo;</span>
            </p>
          )}

          {uncertainTerms.length > 0 && editableTranscript.includes('[acres/hectares?]') && (
            <div className="mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg space-y-1.5" role="status">
              <p className="text-xs font-semibold text-amber-900">
                {uncertainTerms[0].message}
              </p>
              <div className="flex flex-wrap gap-2">
                {uncertainTerms[0].candidates.map((cand) => (
                  <button
                    key={cand}
                    type="button"
                    onClick={() => {
                      userEditedRef.current = true;
                      const numMatch = cand.match(/^(\d+(?:\.\d+)?)\s+(.+)$/);
                      const unitOnly = numMatch ? numMatch[2] : cand;
                      setEditableTranscript((prev) => prev.replace('[acres/hectares?]', unitOnly));
                      setUncertainTerms([]);
                      setValidationError(null);
                    }}
                    className="px-2.5 py-1 bg-white hover:bg-amber-100 text-amber-950 font-bold text-xs rounded-full border border-amber-300 transition-colors"
                  >
                    Use &ldquo;{cand}&rdquo;
                  </button>
                ))}
              </div>
            </div>
          )}

          {validationError && (
            <p className="text-xs text-status-red font-semibold mt-1" role="alert">
              {validationError}
            </p>
          )}
        </div>

        {/* Localized Sample Queries */}
        <div className="mb-3.5">
          <span className="text-xs font-bold text-neutral-slate block mb-1.5">
            {t('sampleQueriesTitle', modalLanguage)}
          </span>
          <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
            {currentQueries.map((queryText, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectSample(queryText, idx)}
                className={`w-full text-left p-2 rounded-lg text-xs transition-colors flex items-center justify-between min-h-[36px] ${
                  activeQueryIndex === idx
                    ? 'bg-brand-indigo-tint text-brand-indigo font-bold border border-brand-indigo/30'
                    : 'bg-neutral-mist/40 text-neutral-slate hover:bg-neutral-mist hover:text-neutral-ink'
                }`}
              >
                <span className="truncate pr-2">{queryText}</span>
                <Volume2 className="w-3.5 h-3.5 flex-shrink-0 opacity-70" />
              </button>
            ))}
          </div>
        </div>

        {/* Explicit Privacy Disclosure */}
        <div className="bg-neutral-canvas border border-neutral-mist/80 rounded-lg p-2.5 mb-3.5 text-[11px] text-neutral-slate leading-relaxed">
          🔒 <strong>Privacy Notice:</strong> {t('speechPrivacyNotice', modalLanguage)}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-2">
          <button
            type="button"
            onClick={handleConfirmAndSend}
            disabled={isSubmitting}
            className="w-full bg-brand-indigo hover:bg-brand-indigo-hover disabled:opacity-40 text-white font-bold py-3 px-4 rounded-button shadow-sm text-sm flex items-center justify-center gap-2 transition-transform active:scale-98 min-h-[48px]"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{isSubmitting ? '...' : t('askThisQuestionAction', modalLanguage)}</span>
          </button>
          <button
            type="button"
            onClick={handleCancel}
            className="w-full sm:w-auto bg-neutral-canvas hover:bg-neutral-mist text-neutral-ink font-semibold py-3 px-4 rounded-button border border-neutral-mist text-xs flex items-center justify-center gap-1.5 transition-colors min-h-[48px]"
          >
            <span>{t('cancelAction', modalLanguage)}</span>
          </button>
          <button
            type="button"
            onClick={handleSwitchToText}
            className="w-full sm:w-auto bg-neutral-canvas hover:bg-neutral-mist text-neutral-ink font-semibold py-3 px-3 rounded-button border border-neutral-mist text-xs flex items-center justify-center gap-1.5 transition-colors min-h-[48px]"
            title={t('switchToTextModeAction', modalLanguage)}
          >
            <MessageSquare className="w-4 h-4 text-neutral-slate" />
          </button>
        </div>
      </div>
    </div>
  );
};
