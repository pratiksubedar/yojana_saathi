import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Send,
  Volume2,
  VolumeX,
  Bot,
  ArrowRight,
  User,
  RotateCcw,
  AlertCircle,
  ExternalLink,
  CheckCircle2,
  XCircle,
  HelpCircle,
  FileText,
  ShieldCheck,
  Sparkles,
  WifiOff,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  Mic,
  MessageSquare,
  Globe,
  Users,
  Check,
  Filter,
  Pause,
  Play,
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { VoiceOrb, VoiceOrbState } from '../components/VoiceOrb';
import { MarkdownRenderer } from '../components/MarkdownRenderer';
import { 
  mapUserProfileToCitizenAttributes,
  evaluateEligibility,
  fetchSchemes,
  mapBackendSchemeToFrontend,
  SchemeDetailSchema,
  SchemeEligibilityResult,
  formatConditionLabel,
} from '../services/schemeApi';
import { useApp } from '../context/AppContext';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useSpeechRecognition, SpeechRecognitionOptions } from '../hooks/useSpeechRecognition';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { extractSpeakableText } from '../utils/speechUtils';
import { detectInputLanguage } from '../utils/languageDetection';
import { MOCK_SCHEMES, getLocalizedScheme } from '../data/mockSchemes';
import { LANGUAGES, t } from '../data/translations';
import {
  getSessionId,
  sendChatMessage,
  streamChatMessage,
  resetChatSession,
  translateChatMessage,
  ChatApiResponse,
} from '../services/chatApi';
import {
  ChatMessage,
  EligibilityOutcomeItem,
  ProvenanceCitationItem,
  UserProfile,
  Language,
  Scheme,
} from '../types';

const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Delhi (NCT)', 'Jammu and Kashmir', 'Ladakh', 'Puducherry'
];

interface MatchedSchemeViewItem {
  id: string;
  name: string;
  nativeName?: string;
  ministry?: string;
  category?: string;
  status: 'eligible' | 'possibly_eligible' | 'not_eligible';
  benefitHighlight: string;
  benefit?: string;
  description: string;
  matchReason: string;
  officialUrl?: string;
}

export const AssistantChat: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    chatMessages,
    addChatMessage,
    clearChat,
    userProfile,
    updateUserProfile,
    mergeDetectedProfile,
    language,
    setLanguage,
    setDetectedLanguage,
    languageSwitchPrompt,
    requestLanguageSwitch,
    confirmLanguageSwitch,
    dismissLanguageSwitch,
    voiceSpeed,
    autoReadAloud,
    setAutoReadAloud,
  } = useApp();

  const { isOnline, checkConnection } = useNetworkStatus();

  // Mode Selection: 'guided' (Profile-First) vs 'chat' (Freeform conversation)
  // AI Support Chat is the default mode. Guided Scheme Eligibility opens ONLY when explicitly requested (e.g. ?guided=true or ?mode=guided).
  const isGuidedFromParam =
    (searchParams.get('guided') === 'true' || searchParams.get('mode') === 'guided') &&
    searchParams.get('mode') !== 'chat';
  const [activeMode, setActiveMode] = useState<'guided' | 'chat'>(
    isGuidedFromParam ? 'guided' : 'chat'
  );

  // Guided Profile Flow State
  const TOTAL_GUIDED_STEPS = 9;
  const [guidedStep, setGuidedStep] = useState<number>(0);
  const [guidedAnswers, setGuidedAnswers] = useState<Partial<UserProfile>>({ ...userProfile });
  const [isGuidedComplete, setIsGuidedComplete] = useState<boolean>(false);
  const [isEvaluatingGuided, setIsEvaluatingGuided] = useState<boolean>(false);
  const [guidedMatchedSchemes, setGuidedMatchedSchemes] = useState<MatchedSchemeViewItem[]>([]);
  const [allAvailableSchemes, setAllAvailableSchemes] = useState<Scheme[]>([]);
  const [customAgeInput, setCustomAgeInput] = useState<string>(userProfile.age ? String(userProfile.age) : '');
  const [guidedVoiceHeard, setGuidedVoiceHeard] = useState<string | null>(null);

  // Voice-First hands-free conversational loop state
  const isVoiceFromParam = searchParams.get('voice') === 'true' || searchParams.get('voice') === '1';
  const [isVoiceActive, setIsVoiceActive] = useState<boolean>(true);
  const [isVoicePaused, setIsVoicePaused] = useState<boolean>(false);
  const [permissionDeniedBanner, setPermissionDeniedBanner] = useState<boolean>(false);
  const [uncertainSpokenText, setUncertainSpokenText] = useState<string | null>(null);
  const lastReadStepRef = useRef<number | null>(null);
  const lastSpokenMsgIdRef = useRef<string | null>(null);

  // Chat message & streaming state
  const [inputText, setInputText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string>('');
  const [streamingCitations, setStreamingCitations] = useState<ProvenanceCitationItem[]>([]);
  const [activeProfileState, setActiveProfileState] = useState<Record<string, any>>({});
  const [isEditingTranscript, setIsEditingTranscript] = useState(false);
  const [editableTranscript, setEditableTranscript] = useState('');

  // Per-message inline translation state with caching
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [translatingMsgId, setTranslatingMsgId] = useState<string | null>(null);
  const [openTranslateDropdownId, setOpenTranslateDropdownId] = useState<string | null>(null);
  const [activeMessageLang, setActiveMessageLang] = useState<Record<string, string | null>>({});
  const [translationFailedMsgId, setTranslationFailedMsgId] = useState<string | null>(null);

  // Load all schemes on mount for deterministic display & matching
  useEffect(() => {
    let mounted = true;
    fetchSchemes({ pageSize: 50 })
      .then((res) => {
        if (mounted && res && res.items && res.items.length > 0) {
          const mapped = res.items.map((item) => mapBackendSchemeToFrontend(item, language));
          setAllAvailableSchemes(mapped);
        } else if (mounted) {
          setAllAvailableSchemes(MOCK_SCHEMES);
        }
      })
      .catch((err) => {
        console.warn('Failed to fetch schemes for assistant matching:', err);
        if (mounted) setAllAvailableSchemes(MOCK_SCHEMES);
      });
    return () => {
      mounted = false;
    };
  }, [language]);

  // Synchronize userProfile changes into guidedAnswers bidirectionally
  useEffect(() => {
    if (userProfile && Object.keys(userProfile).length > 0) {
      setGuidedAnswers((prev) => ({ ...prev, ...userProfile }));
    }
  }, [userProfile]);

  // Live unified active profile merging central profile and guided answers
  const activeProfile = useMemo(() => {
    return {
      ...userProfile,
      ...guidedAnswers,
    };
  }, [userProfile, guidedAnswers]);

  // Compute live visual attribute chips for Active Profile Synced Bar
  const profileChips = useMemo(() => {
    const chips: { icon: string; label: string }[] = [];
    if (activeProfile.state) {
      chips.push({ icon: '📍', label: activeProfile.state });
    }
    if (activeProfile.age) {
      chips.push({
        icon: '🎂',
        label: `${activeProfile.age} ${language === 'hi' ? 'वर्ष' : language === 'kn' ? 'ವರ್ಷ' : language === 'te' ? 'సం.' : 'yrs'}`,
      });
    }
    if (activeProfile.gender) {
      const g = activeProfile.gender;
      const gLabel =
        g.toLowerCase() === 'female'
          ? (language === 'hi' ? 'महिला' : language === 'kn' ? 'ಮಹಿಳೆ' : language === 'te' ? 'మహిళ' : 'Female')
          : g.toLowerCase() === 'male'
          ? (language === 'hi' ? 'पुरुष' : language === 'kn' ? 'ಪುರುಷ' : language === 'te' ? 'పురుషుడు' : 'Male')
          : (language === 'hi' ? 'अन्य' : language === 'kn' ? 'ಇತರೆ' : language === 'te' ? 'ఇతర' : g);
      chips.push({ icon: '👤', label: gLabel });
    }
    if (activeProfile.occupation) {
      const occMap: Record<string, Record<Language, string>> = {
        Farmer: { en: 'Farmer', hi: 'किसान', kn: 'ರೈತ', te: 'రైతు' },
        'Street Vendor': { en: 'Street Vendor', hi: 'रेहड़ी वेंडर', kn: 'ಬೀದಿ ವ್ಯಾಪಾರಿ', te: 'వీధి వ్యాపారి' },
        'Daily Wage Worker': { en: 'Daily Wage', hi: 'दैनिक मजदूर', kn: 'ಕೂಲಿ ಕಾರ್ಮಿಕ', te: 'కూలీ కార్మికుడు' },
        Artisan: { en: 'Artisan', hi: 'कारीगर', kn: 'ಕುಶಲಕರ್ಮಿ', te: 'చేతివృత్తి' },
        Student: { en: 'Student', hi: 'छात्र', kn: 'ವಿದ್ಯಾರ್ಥಿ', te: 'విద్యార్థి' },
        Homemaker: { en: 'Homemaker', hi: 'गृहिणी', kn: 'ಗೃಹಿಣಿ', te: 'గృహిణి' },
      };
      const oLabel = occMap[activeProfile.occupation]?.[language] || activeProfile.occupation;
      chips.push({ icon: '💼', label: oLabel });
    }
    if (activeProfile.landholding) {
      const l = activeProfile.landholding;
      const lLabel = l.includes('under')
        ? (language === 'hi' ? '< 2 हेक्टेयर भूमि' : language === 'kn' ? '< 2 ಹೆಕ್ಟೇರ್ ಭೂಮಿ' : language === 'te' ? '< 2 హెక్టార్ల భూమి' : '< 2 Ha Land')
        : l.includes('medium') || l.includes('over')
        ? (language === 'hi' ? '> 2 हेक्टेयर भूमि' : language === 'kn' ? '> 2 ಹೆಕ್ಟೇರ್ ಭೂಮಿ' : language === 'te' ? '> 2 హెక్టార్ల భూమి' : '> 2 Ha Land')
        : l.includes('tenant')
        ? (language === 'hi' ? 'बटाईदार किसान' : language === 'kn' ? 'ಗೇಣಿದಾರ ರೈತ' : language === 'te' ? 'కౌలు రైతు' : 'Tenant Farmer')
        : l.includes('allied')
        ? (language === 'hi' ? 'पशुपालन/डेयरी' : language === 'kn' ? 'ಕೃಷಿ ಪೂರಕ' : language === 'te' ? 'అనుబంధ రంగం' : 'Allied Agri')
        : l;
      chips.push({ icon: '🌾', label: lLabel });
    } else if (activeProfile.ownsAgriculturalLand !== undefined) {
      chips.push({
        icon: '🌾',
        label: activeProfile.ownsAgriculturalLand
          ? (language === 'hi' ? 'भूमि मालिक' : language === 'kn' ? 'ಭೂಮಾಲೀಕ' : language === 'te' ? 'భూ యజమాని' : 'Landowner')
          : (language === 'hi' ? 'भूमिहीन' : language === 'kn' ? 'ಭೂಮಿ ಇಲ್ಲ' : language === 'te' ? 'భూమి లేనివారు' : 'Landless'),
      });
    }
    if (activeProfile.incomeRange) {
      const inc = activeProfile.incomeRange;
      const incLabel = inc === 'under_100000' || inc === 'under_1_lakh'
        ? (language === 'hi' ? '< ₹1 लाख' : language === 'kn' ? '< ₹1 ಲಕ್ಷ' : language === 'te' ? '< ₹1 లక్ష' : '< ₹1 Lakh')
        : inc === '100000_250000' || inc === '1_to_3_lakh'
        ? '₹1L - ₹2.5L'
        : inc === '250000_500000' || inc === '3_to_8_lakh'
        ? '₹2.5L - ₹5L'
        : (language === 'hi' ? '> ₹5 लाख' : language === 'kn' ? '> ₹5 ಲಕ್ಷ' : language === 'te' ? '> ₹5 లక్ష' : '> ₹5 Lakh');
      chips.push({ icon: '💰', label: incLabel });
    } else if (activeProfile.annualIncome) {
      chips.push({ icon: '💰', label: `₹${activeProfile.annualIncome.toLocaleString('en-IN')}` });
    }
    if (activeProfile.socialCategory) {
      const catMap: Record<string, Record<Language, string>> = {
        General: { en: 'General', hi: 'सामान्य', kn: 'ಸಾಮಾನ್ಯ', te: 'జనరల్' },
        OBC: { en: 'OBC', hi: 'ओबीसी', kn: 'ಒಬಿಸಿ', te: 'ఓబీసీ' },
        SC: { en: 'SC', hi: 'एससी', kn: 'ಎಸ್‍ಸಿ', te: 'ఎస్సీ' },
        ST: { en: 'ST', hi: 'एसटी', kn: 'ಎಸ್‍ಟಿ', te: 'ఎస్టీ' },
        EWS: { en: 'EWS', hi: 'ईडब्ल्यूएस', kn: 'ಇಡಬ್ಲ್ಯೂಎಸ್', te: 'ఈడబ్ల్యూఎస్' },
      };
      const catLabel = catMap[activeProfile.socialCategory]?.[language] || activeProfile.socialCategory;
      chips.push({ icon: '🏷️', label: catLabel });
    }
    if (activeProfile.hasBankPassbook !== undefined || activeProfile.hasSavingsAccount !== undefined) {
      const hasPb = activeProfile.hasBankPassbook ?? activeProfile.hasSavingsAccount;
      chips.push({
        icon: '🏦',
        label: hasPb
          ? (language === 'hi' ? 'बैंक पासबुक: हाँ' : language === 'kn' ? 'ಪಾಸ್‌ಬುಕ್: ಹೌದು' : language === 'te' ? 'పాస్‌బుక్: అవును' : 'Passbook: Yes')
          : (language === 'hi' ? 'पासबुक: नहीं' : language === 'kn' ? 'ಪಾಸ್‌ಬುಕ್: ಇಲ್ಲ' : language === 'te' ? 'పాస్‌బుక్: లేదు' : 'No Passbook'),
      });
    }
    if (activeProfile.ownsPuccaHouse !== undefined) {
      chips.push({
        icon: '🏠',
        label: activeProfile.ownsPuccaHouse
          ? (language === 'hi' ? 'पक्का मकान' : language === 'kn' ? 'ಪಕ್ಕಾ ಮನೆ' : language === 'te' ? 'పక్కా ఇల్లు' : 'Pucca House')
          : (language === 'hi' ? 'कच्चा मकान' : language === 'kn' ? 'ಕಚ್ಚಾ ಮನೆ' : language === 'te' ? 'కచ్చా ఇల్లు' : 'Kutcha House'),
      });
    }
    if (activeProfile.paysIncomeTax !== undefined) {
      chips.push({
        icon: '⚖️',
        label: activeProfile.paysIncomeTax
          ? (language === 'hi' ? 'आयकर दाता' : language === 'kn' ? 'ತೆರಿಗೆದಾರ' : language === 'te' ? 'పన్ను చెల్లింపుదారు' : 'Taxpayer')
          : (language === 'hi' ? 'गैर-करदाता' : language === 'kn' ? 'ತೆರಿಗೆ ರಹಿತ' : language === 'te' ? 'పన్ను చెల్లించని వారు' : 'Non-taxpayer'),
      });
    }
    return chips;
  }, [activeProfile, language]);

  // Handle Per-Message Inline Translation
  const handleTranslateMessage = async (messageId: string, text: string, targetLang: Language) => {
    const key = `${messageId}_${targetLang}`;
    if (translations[key]) {
      setActiveMessageLang((prev) => ({ ...prev, [messageId]: targetLang }));
      setOpenTranslateDropdownId(null);
      return;
    }
    setTranslatingMsgId(messageId);
    try {
      const res = await translateChatMessage(text, targetLang, language);
      if (res && res.is_translated !== false && res.translated_text && res.translated_text !== text) {
        setTranslations((prev) => ({ ...prev, [key]: res.translated_text }));
        setActiveMessageLang((prev) => ({ ...prev, [messageId]: targetLang }));
        setTranslationFailedMsgId(null);
      } else {
        // Did not genuinely translate - do not show "Translated to..." banner!
        setTranslationFailedMsgId(messageId);
        setTimeout(() => setTranslationFailedMsgId(null), 5000);
      }
    } catch (err) {
      console.warn('Translate error:', err);
      setTranslationFailedMsgId(messageId);
      setTimeout(() => setTranslationFailedMsgId(null), 5000);
    } finally {
      setTranslatingMsgId(null);
      setOpenTranslateDropdownId(null);
    }
  };

  // Universal language change: update assistant messages in chat view
  useEffect(() => {
    chatMessages.forEach(async (msg) => {
      if (msg.sender === 'assistant') {
        const key = `${msg.id}_${language}`;
        if (translations[key]) {
          setActiveMessageLang((prev) => ({ ...prev, [msg.id]: language }));
        } else {
          try {
            const res = await translateChatMessage(msg.text, language);
            if (res && res.is_translated !== false && res.translated_text && res.translated_text !== msg.text) {
              setTranslations((prev) => ({ ...prev, [key]: res.translated_text }));
              setActiveMessageLang((prev) => ({ ...prev, [msg.id]: language }));
            }
          } catch {}
        }
      }
    });
  }, [language]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevMessagesCountRef = useRef(chatMessages.length);
  const abortStreamRef = useRef<(() => void) | null>(null);
  const initialQueryHandledRef = useRef<boolean>(false);
  const isSubmittingRef = useRef<boolean>(false);
  const lastSubmissionRef = useRef<{ text: string; timestamp: number } | null>(null);

  // Speech Synthesis hook
  const {
    isSupported: isTtsSupported,
    isSpeaking,
    isPaused,
    currentSpeakingId,
    voiceUnavailableWarning,
    speak,
    stop: stopSpeaking,
    pause: pauseSpeaking,
    resume: resumeSpeaking,
  } = useSpeechSynthesis(language, voiceSpeed);

  // Hands-free voice speech end handler callback bridge
  const onSilenceDetectedRef = useRef<((text: string) => void) | null>(null);

  const speechOptions = useMemo<SpeechRecognitionOptions>(
    () => ({
      silenceTimeoutMs: 2000,
      onSilenceDetected: (spokenText: string) => {
        onSilenceDetectedRef.current?.(spokenText);
      },
    }),
    []
  );

  // Speech Recognition hook
  const {
    isSupported: isSttSupported,
    isListening,
    transcript: sttTranscript,
    interimTranscript: sttInterimTranscript,
    error: sttError,
    errorType: sttErrorType,
    permissionDenied: sttPermissionDenied,
    startListening,
    stopListening,
    abortListening,
    resetTranscript,
  } = useSpeechRecognition(language, speechOptions);

  const isListeningRef = useRef<boolean>(isListening);
  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  // Keep editable transcript and chat input box in sync with incoming recognition
  useEffect(() => {
    if (!isEditingTranscript) {
      const fullHeard = (sttTranscript + ' ' + sttInterimTranscript).trim();
      setEditableTranscript(fullHeard);
      if (activeMode === 'chat' && fullHeard) {
        setInputText(fullHeard);
      }
    }
  }, [sttTranscript, sttInterimTranscript, isEditingTranscript, activeMode]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      abortListening();
      if (abortStreamRef.current) {
        abortStreamRef.current();
        abortStreamRef.current = null;
      }
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    };
  }, [stopSpeaking, abortListening]);

  // Handle Assistant Chat message speech and hands-free turn-taking
  useEffect(() => {
    if (chatMessages.length > prevMessagesCountRef.current) {
      const lastMsg = chatMessages[chatMessages.length - 1];
      if (lastMsg && lastMsg.sender === 'assistant' && lastSpokenMsgIdRef.current !== lastMsg.id) {
        lastSpokenMsgIdRef.current = lastMsg.id;
        const speakable = extractSpeakableText(lastMsg.text, true);
        if (speakable && (autoReadAloud || (isVoiceActive && !isVoicePaused))) {
          speak(speakable, {
            lang: language,
            rate: voiceSpeed,
            messageId: lastMsg.id,
            onEnd: () => {
              if (activeMode === 'chat' && isVoiceActive && !isVoicePaused && isOnline && !sttPermissionDenied) {
                resetTranscript();
                startListening();
              }
            },
          });
        }
      }
    }
    prevMessagesCountRef.current = chatMessages.length;
  }, [
    chatMessages,
    autoReadAloud,
    isVoiceActive,
    isVoicePaused,
    language,
    voiceSpeed,
    speak,
    activeMode,
    isOnline,
    sttPermissionDenied,
    resetTranscript,
    startListening,
  ]);

  const handleToggleSpeak = useCallback(
    (msgId: string, text: string) => {
      if (isSpeaking && currentSpeakingId === msgId) {
        stopSpeaking();
      } else {
        stopSpeaking();
        const speakable = extractSpeakableText(text, true);
        if (speakable) {
          speak(speakable, { lang: language, rate: voiceSpeed, messageId: msgId });
        }
      }
    },
    [isSpeaking, currentSpeakingId, stopSpeaking, speak, language, voiceSpeed]
  );

  // Execute Rule Engine Evaluation for Completed Guided Profile
  const executeGuidedEvaluation = useCallback(
    async (finalProfile: Partial<UserProfile>) => {
      setIsEvaluatingGuided(true);
      updateUserProfile(finalProfile, 'user');
      mergeDetectedProfile(finalProfile, true);

      const citizenAttributes = mapUserProfileToCitizenAttributes({
        ...userProfile,
        ...finalProfile,
      });

      try {
        const evalRes = await evaluateEligibility({
          citizen_attributes: citizenAttributes,
          preferred_language: language,
        });

        const rawResults: SchemeEligibilityResult[] = evalRes.results || [];
        const sourcePool = allAvailableSchemes.length > 0 ? allAvailableSchemes : MOCK_SCHEMES;

        const matched: MatchedSchemeViewItem[] = [];

        rawResults.forEach((res) => {
          if (res.status === 'ELIGIBLE' || res.status === 'POSSIBLY_ELIGIBLE') {
            const foundScheme = sourcePool.find((s) => s.id === res.scheme_id);
            if (foundScheme) {
              const localized = getLocalizedScheme(foundScheme, language);
              const criteriaReasons: string[] = [];
              if (finalProfile.age) criteriaReasons.push(`Age: ${finalProfile.age}`);
              if (finalProfile.state) criteriaReasons.push(`State: ${finalProfile.state}`);
              if (finalProfile.occupation) criteriaReasons.push(String(finalProfile.occupation));
              if (finalProfile.incomeRange) {
                const incClean = finalProfile.incomeRange.replace(/_/g, ' ');
                criteriaReasons.push(`Income: ${incClean}`);
              }
              if (finalProfile.socialCategory) criteriaReasons.push(`Category: ${finalProfile.socialCategory}`);
              if (finalProfile.isDifferentlyAbled) criteriaReasons.push(`Benchmark Disability (PwD)`);
              if (finalProfile.ownsPuccaHouse === false) criteriaReasons.push(`No Pucca House`);
              if (finalProfile.hasSavingsAccount) criteriaReasons.push(`Active Bank Passbook`);

              matched.push({
                id: localized.id,
                name: localized.name,
                nativeName: localized.nativeName,
                ministry: localized.ministry,
                category: localized.category,
                status: res.status === 'ELIGIBLE' ? 'eligible' : 'possibly_eligible',
                benefitHighlight: localized.benefitHighlight || localized.benefit || 'Financial welfare support',
                benefit: localized.benefit,
                description: localized.description || '',
                matchReason: criteriaReasons.length > 0 ? criteriaReasons.map((r) => formatConditionLabel(r)).join(' • ') : 'Satisfies preliminary eligibility criteria',
                officialUrl: localized.officialUrl,
              });
            }
          }
        });

        // Sort: eligible schemes first, then possibly_eligible
        matched.sort((a, b) => {
          if (a.status === 'eligible' && b.status !== 'eligible') return -1;
          if (a.status !== 'eligible' && b.status === 'eligible') return 1;
          return 0;
        });

        setGuidedMatchedSchemes(matched);
      } catch (err) {
        console.warn('Backend evaluation fallback to client schemes:', err);
        // Deterministic fallback matching based on occupation and age
        const matchedFallback: MatchedSchemeViewItem[] = [];
        const sourcePool = allAvailableSchemes.length > 0 ? allAvailableSchemes : MOCK_SCHEMES;

        sourcePool.forEach((s) => {
          const loc = getLocalizedScheme(s, language);
          const isFarmer = String(finalProfile.occupation).toLowerCase().includes('farmer');
          const isVendor = String(finalProfile.occupation).toLowerCase().includes('vendor');
          const isSenior = (finalProfile.age || 0) >= 60;

          let matches = false;
          let reason = '';
          if (isFarmer && (s.id.includes('kisan') || s.id.includes('kcc') || s.category === 'agriculture')) {
            matches = true;
            reason = `Matched: Landholding Farmer in ${finalProfile.state || 'India'}`;
          } else if (isVendor && (s.id.includes('svanidhi') || s.category === 'employment')) {
            matches = true;
            reason = `Matched: Street Vendor / Micro Entrepreneur`;
          } else if (isSenior && (s.id.includes('pension') || s.id.includes('ignoaps') || s.category === 'social_welfare')) {
            matches = true;
            reason = `Matched: Senior Citizen Age ${finalProfile.age}`;
          } else if (s.id.includes('pm-jay') || s.id.includes('ayushman') || s.id.includes('pmay')) {
            matches = true;
            reason = `Matched: Low Income Family Welfare`;
          }

          if (matches) {
            matchedFallback.push({
              id: loc.id,
              name: loc.name,
              nativeName: loc.nativeName,
              ministry: loc.ministry,
              category: loc.category,
              status: 'eligible',
              benefitHighlight: loc.benefitHighlight || loc.benefit || 'Welfare benefit',
              benefit: loc.benefit,
              description: loc.description || '',
              matchReason: reason,
              officialUrl: loc.officialUrl,
            });
          }
        });

        setGuidedMatchedSchemes(matchedFallback);
      } finally {
        setIsEvaluatingGuided(false);
        setIsGuidedComplete(true);
      }
    },
    [userProfile, language, allAvailableSchemes, mergeDetectedProfile, updateUserProfile]
  );

  // Guided step answer handler
  const handleSelectGuidedAnswer = useCallback((attributeUpdates: Partial<UserProfile>) => {
    setGuidedVoiceHeard(null);
    const updated = { ...guidedAnswers, ...attributeUpdates };
    setGuidedAnswers(updated);
    updateUserProfile(attributeUpdates, 'user');

    // If farmer, step 4 is relevant. If other occupation, skip to income
    const isFarmer = String(updated.occupation || '').toLowerCase().includes('farmer');
    const isVendor = String(updated.occupation || '').toLowerCase().includes('vendor');

    if (guidedStep === 3) {
      if (!isFarmer && !isVendor) {
        // Skip occupation details step directly to income
        setGuidedStep(5);
        return;
      }
    }

    if (guidedStep >= 8) {
      // Completed all 9 questions (Step 0 through 8)! Evaluate
      executeGuidedEvaluation(updated);
    } else {
      setGuidedStep((prev) => prev + 1);
    }
  }, [guidedAnswers, guidedStep, executeGuidedEvaluation, updateUserProfile]);

  const handleSkipGuidedQuestion = () => {
    setGuidedVoiceHeard(null);
    if (guidedStep >= 8) {
      executeGuidedEvaluation(guidedAnswers);
    } else {
      setGuidedStep((prev) => prev + 1);
    }
  };

  const handleBackGuidedQuestion = () => {
    setGuidedVoiceHeard(null);
    if (guidedStep === 5) {
      const isFarmer = String(guidedAnswers.occupation || '').toLowerCase().includes('farmer');
      const isVendor = String(guidedAnswers.occupation || '').toLowerCase().includes('vendor');
      if (!isFarmer && !isVendor) {
        setGuidedStep(3);
        return;
      }
    }
    setGuidedStep((prev) => Math.max(0, prev - 1));
  };

  // Conversational Chat message handler
  const handleSendMessage = useCallback(
    async (queryText?: string, isVoice: boolean = false, skipAddUserMsg: boolean = false) => {
      const rawQuery = (queryText !== undefined ? queryText : inputText).trim();
      if (!rawQuery || isSubmittingRef.current) return;

      const now = Date.now();
      if (
        lastSubmissionRef.current &&
        lastSubmissionRef.current.text === rawQuery &&
        now - lastSubmissionRef.current.timestamp < 1500
      ) {
        return;
      }
      lastSubmissionRef.current = { text: rawQuery, timestamp: now };

      if (!isOnline) {
        setApiError(t('offlineChatNotice', language));
        return;
      }

      if (isListening) {
        stopListening();
      }
      stopSpeaking();
      resetTranscript();
      setEditableTranscript('');
      setIsEditingTranscript(false);

      setInputText('');
      setApiError(null);
      isSubmittingRef.current = true;
      setIsSubmitting(true);
      setStreamingText('');

      if (!skipAddUserMsg) {
        addChatMessage({
          sender: 'user',
          text: rawQuery,
          isVoiceInput: isVoice,
        });
      }

      // Check for language difference between user input and current site language
      const langCheck = detectInputLanguage(rawQuery, language);
      if (langCheck.differsFromCurrent) {
        requestLanguageSwitch({
          detectedLang: langCheck.detectedLanguage,
          confidence: langCheck.confidence,
          sourceText: rawQuery,
          triggerType: isVoice ? 'spoken' : 'typed',
          candidates: langCheck.candidates,
          reason: langCheck.reason,
        });
      }

      const sessionId = getSessionId();
      const mappedProfile = mapUserProfileToCitizenAttributes({
        ...userProfile,
        ...guidedAnswers,
      });
      const profilePayload = Object.keys(mappedProfile).length > 0 ? mappedProfile : undefined;

      let accumulatedText = '';
      let incomingCitations: ProvenanceCitationItem[] = [];
      let incomingEligibility: EligibilityOutcomeItem | undefined;
      let incomingFollowups: string[] = [];
      let latestProfile: Record<string, any> = activeProfileState;
      let detectedSchemeId: string | undefined;

      try {
        const cancelStream = streamChatMessage(
          {
            message: rawQuery,
            language,
            session_id: sessionId,
            citizen_profile: profilePayload,
          },
          {
            onMetadata: (meta) => {
              if (meta.scheme_id) {
                detectedSchemeId = meta.scheme_id;
              }
              if (meta.language && ['en', 'hi', 'kn', 'te'].includes(meta.language) && meta.language !== language) {
                requestLanguageSwitch({
                  detectedLang: meta.language as any,
                  confidence: 'script_match',
                  sourceText: rawQuery,
                  triggerType: isVoice ? 'spoken' : 'typed',
                  reason: 'AI detected response language',
                });
              }
            },
            onToken: (token) => {
              accumulatedText += token;
              setStreamingText(accumulatedText);
            },
            onCitations: (citations) => {
              incomingCitations = citations;
              setStreamingCitations(citations);
            },
            onEligibility: (elig) => {
              incomingEligibility = elig;
              if (elig.scheme_id && elig.scheme_id !== 'unspecified') {
                detectedSchemeId = elig.scheme_id;
              }
            },
            onFollowups: (followups) => {
              incomingFollowups = followups;
            },
            onProfile: (profile) => {
              latestProfile = profile;
              setActiveProfileState(profile);
              mergeDetectedProfile(profile);
              setGuidedAnswers((prev) => ({ ...prev, ...profile }));
            },
            onDone: () => {
              abortStreamRef.current = null;
              isSubmittingRef.current = false;
              setIsSubmitting(false);
              setStreamingText('');
              setStreamingCitations([]);

              try {
                const finalMessage = accumulatedText.trim() || t('chatErrorMessage', language);
                addChatMessage({
                  sender: 'assistant',
                  text: finalMessage,
                  citations: incomingCitations.length > 0 ? incomingCitations : undefined,
                  eligibilityResult: incomingEligibility,
                  suggestedFollowups: incomingFollowups.length > 0 ? incomingFollowups : undefined,
                  suggestedSchemeIds: detectedSchemeId ? [detectedSchemeId] : undefined,
                });
              } catch (addErr) {
                console.error('Error committing streamed message:', addErr);
              }
            },
            onError: (err) => {
              abortStreamRef.current = null;
              isSubmittingRef.current = false;
              setIsSubmitting(false);
              setStreamingText('');
              setApiError(err.detail || t('chatErrorMessage', language));
            },
          }
        );

        abortStreamRef.current = cancelStream;
      } catch (err: any) {
        isSubmittingRef.current = false;
        setIsSubmitting(false);
        setStreamingText('');
        setApiError(err.message || t('chatErrorMessage', language));
      }
    },
    [inputText, isOnline, language, activeProfileState, userProfile, guidedAnswers, addChatMessage, isListening, stopListening, stopSpeaking, resetTranscript, mergeDetectedProfile, setDetectedLanguage, requestLanguageSwitch]
  );

  // Auto-submit URL params
  useEffect(() => {
    const q = searchParams.get('q');
    const isVoice = searchParams.get('voice') === 'true' || searchParams.get('voice') === '1';
    if (q && !initialQueryHandledRef.current) {
      initialQueryHandledRef.current = true;
      setActiveMode('chat');
      setSearchParams({}, { replace: true });
      handleSendMessage(q, isVoice);
    }
  }, [searchParams, setSearchParams, handleSendMessage]);

  // Dedicated Guided Flow Voice Input Handler - NEVER leaks spoken input into AI chat
  const handleGuidedVoiceInput = useCallback((speechText: string): boolean => {
    const lower = speechText.toLowerCase().trim();
    if (!lower) return false;

    // Step 0: State
    if (guidedStep === 0) {
      const matchedState = INDIAN_STATES.find((s) => lower.includes(s.toLowerCase()));
      if (matchedState) {
        handleSelectGuidedAnswer({ state: matchedState });
        return true;
      }
    }

    // Step 1: Age
    if (guidedStep === 1) {
      const numMatch = lower.match(/\d+/);
      if (numMatch) {
        const val = parseInt(numMatch[0], 10);
        if (val >= 1 && val <= 115) {
          handleSelectGuidedAnswer({ age: val });
          return true;
        }
      }
      if (lower.includes('youth') || lower.includes('student') || lower.includes('18') || lower.includes('20')) {
        handleSelectGuidedAnswer({ age: 22 });
        return true;
      }
      if (lower.includes('working') || lower.includes('30')) {
        handleSelectGuidedAnswer({ age: 32 });
        return true;
      }
      if (lower.includes('adult') || lower.includes('40') || lower.includes('50')) {
        handleSelectGuidedAnswer({ age: 48 });
        return true;
      }
      if (lower.includes('senior') || lower.includes('pension') || lower.includes('60') || lower.includes('70')) {
        handleSelectGuidedAnswer({ age: 65 });
        return true;
      }
    }

    // Step 2: Gender
    if (guidedStep === 2) {
      if (lower.includes('female') || lower.includes('woman') || lower.includes('महिला') || lower.includes('ಮಹಿಳೆ') || lower.includes('మహిళ')) {
        handleSelectGuidedAnswer({ gender: 'female' });
        return true;
      }
      if (lower.includes('male') || lower.includes('man') || lower.includes('पुरुष') || lower.includes('ಪುರುಷ') || lower.includes('పురుషుడు')) {
        handleSelectGuidedAnswer({ gender: 'male' });
        return true;
      }
      if (lower.includes('other') || lower.includes('transgender')) {
        handleSelectGuidedAnswer({ gender: 'other' });
        return true;
      }
    }

    // Step 3: Primary Occupation
    if (guidedStep === 3) {
      if (lower.includes('farmer') || lower.includes('agriculture') || lower.includes('किसान') || lower.includes('कृषि') || lower.includes('ರೈತ') || lower.includes('రైతు')) {
        handleSelectGuidedAnswer({ occupation: 'Farmer' });
        return true;
      }
      if (lower.includes('vendor') || lower.includes('street') || lower.includes('hawker') || lower.includes('रेहड़ी') || lower.includes('पटरी') || lower.includes('ठेला')) {
        handleSelectGuidedAnswer({ occupation: 'Street Vendor' });
        return true;
      }
      if (lower.includes('daily') || lower.includes('wage') || lower.includes('worker') || lower.includes('construction') || lower.includes('मजदूर') || lower.includes('ಕೂಲಿ')) {
        handleSelectGuidedAnswer({ occupation: 'Daily Wage Worker' });
        return true;
      }
      if (lower.includes('artisan') || lower.includes('craft') || lower.includes('कारीगर') || lower.includes('ಕುಶಲಕರ್ಮಿ')) {
        handleSelectGuidedAnswer({ occupation: 'Artisan' });
        return true;
      }
      if (lower.includes('student') || lower.includes('छात्र') || lower.includes('ವಿದ್ಯಾರ್ಥಿ') || lower.includes('విద్యార్థి')) {
        handleSelectGuidedAnswer({ occupation: 'Student' });
        return true;
      }
      if (lower.includes('home') || lower.includes('housewife') || lower.includes('गृहणी') || lower.includes('ಮನೆಗೆಲಸ')) {
        handleSelectGuidedAnswer({ occupation: 'Homemaker' });
        return true;
      }
    }

    // Step 4: Occupation Details
    if (guidedStep === 4) {
      const isFarmer = String(guidedAnswers.occupation || '').toLowerCase().includes('farmer');
      if (isFarmer) {
        if (lower.includes('small') || lower.includes('marginal') || lower.includes('under 2') || lower.includes('2 acre') || lower.includes('5 acre') || lower.includes('land')) {
          handleSelectGuidedAnswer({ landholding: 'under_2_hectares', ownsAgriculturalLand: true });
          return true;
        }
        if (lower.includes('large') || lower.includes('over 2')) {
          handleSelectGuidedAnswer({ landholding: 'over_2_hectares', ownsAgriculturalLand: true });
          return true;
        }
        if (lower.includes('tenant') || lower.includes('sharecropper') || lower.includes('बटाईदार') || lower.includes('ಗೇಣಿ') || lower.includes('కౌలు')) {
          handleSelectGuidedAnswer({ isTenantFarmer: true, ownsAgriculturalLand: false });
          return true;
        }
        if (lower.includes('dairy') || lower.includes('animal') || lower.includes('allied') || lower.includes('fisher') || lower.includes('पशुपालन')) {
          handleSelectGuidedAnswer({ isAlliedActivityWorker: true });
          return true;
        }
      } else {
        if (lower.includes('yes') || lower.includes('certificate') || lower.includes('id') || lower.includes('हाँ') || lower.includes('ಹೌದು') || lower.includes('అవును')) {
          handleSelectGuidedAnswer({ isStreetVendor: true });
          return true;
        }
        if (lower.includes('no') || lower.includes('नहीं') || lower.includes('ಇಲ್ಲ') || lower.includes('కాదు')) {
          handleSelectGuidedAnswer({ isStreetVendor: false });
          return true;
        }
      }
    }

    // Step 5: Annual Income
    if (guidedStep === 5) {
      if (lower.includes('below') || lower.includes('under 1') || lower.includes('bpl') || lower.includes('antyodaya') || lower.includes('गरीब') || lower.includes('1 लाख से कम')) {
        handleSelectGuidedAnswer({ incomeRange: 'under_100000', hasBplCard: true });
        return true;
      }
      if (lower.includes('1 to 2.5') || lower.includes('2 lakh') || lower.includes('low') || lower.includes('1 लाख')) {
        handleSelectGuidedAnswer({ incomeRange: '100000_250000', hasBplCard: false });
        return true;
      }
      if (lower.includes('2.5 to 5') || lower.includes('3 lakh') || lower.includes('4 lakh') || lower.includes('middle')) {
        handleSelectGuidedAnswer({ incomeRange: '250000_500000', hasBplCard: false });
        return true;
      }
      if (lower.includes('above') || lower.includes('over 5') || lower.includes('5 lakh') || lower.includes('5 लाख')) {
        handleSelectGuidedAnswer({ incomeRange: 'above_500000', hasBplCard: false });
        return true;
      }
    }

    // Step 6: Social Category & Disability
    if (guidedStep === 6) {
      if (lower.includes('sc') || lower.includes('scheduled caste') || lower.includes('अनुसूचित जाति')) {
        handleSelectGuidedAnswer({ socialCategory: 'SC', isDifferentlyAbled: false });
        return true;
      }
      if (lower.includes('st') || lower.includes('scheduled tribe') || lower.includes('अनुसूचित जनजाति')) {
        handleSelectGuidedAnswer({ socialCategory: 'ST', isDifferentlyAbled: false });
        return true;
      }
      if (lower.includes('obc') || lower.includes('other backward') || lower.includes('अन्य पिछड़ा')) {
        handleSelectGuidedAnswer({ socialCategory: 'OBC', isDifferentlyAbled: false });
        return true;
      }
      if (lower.includes('general') || lower.includes('open') || lower.includes('सामान्य')) {
        handleSelectGuidedAnswer({ socialCategory: 'General', isDifferentlyAbled: false });
        return true;
      }
      if (lower.includes('disab') || lower.includes('divyang') || lower.includes('दिव्यांग') || lower.includes('ವಿಶೇಷ ಚೇತನ') || lower.includes('దివ్యాంగుల')) {
        handleSelectGuidedAnswer({ isDifferentlyAbled: true });
        return true;
      }
    }

    // Step 7: Housing & Bank Passbook
    if (guidedStep === 7) {
      if (lower.includes('passbook') || lower.includes('bank') || lower.includes('dbt') || lower.includes('खाता') || lower.includes('ಬ್ಯಾಂಕ್')) {
        handleSelectGuidedAnswer({ ownsPuccaHouse: false, hasSavingsAccount: true });
        return true;
      }
      if (lower.includes('pucca') || lower.includes('concrete') || lower.includes('पक्का') || lower.includes('ಕಾಂಕ್ರೀಟ್')) {
        handleSelectGuidedAnswer({ ownsPuccaHouse: true, hasSavingsAccount: true });
        return true;
      }
      if (lower.includes('no passbook') || lower.includes('neither') || lower.includes('no') || lower.includes('नहीं') || lower.includes('ಇಲ್ಲ')) {
        handleSelectGuidedAnswer({ ownsPuccaHouse: false, hasSavingsAccount: false });
        return true;
      }
    }

    // Step 8: Statutory Exclusions (Tax / Govt job)
    if (guidedStep === 8) {
      if (lower.includes('tax') || lower.includes('आयकर') || lower.includes('ತೆರಿಗೆ') || lower.includes('పన్ను')) {
        handleSelectGuidedAnswer({ paysIncomeTax: true, hasRegularGovtJob: false });
        return true;
      }
      if (lower.includes('govt') || lower.includes('government') || lower.includes('सरकारी') || lower.includes('ಸರ್ಕಾರಿ') || lower.includes('ప్రభుత్వ')) {
        handleSelectGuidedAnswer({ paysIncomeTax: false, hasRegularGovtJob: true });
        return true;
      }
      if (lower.includes('no') || lower.includes('neither') || lower.includes('नहीं') || lower.includes('ಇಲ್ಲ') || lower.includes('కాదు') || lower.includes('none')) {
        handleSelectGuidedAnswer({ paysIncomeTax: false, hasRegularGovtJob: false });
        return true;
      }
    }

    // Unmatched voice option: show friendly guidance pill without polluting AI chat!
    setGuidedVoiceHeard(speechText);
    return false;
  }, [guidedStep, guidedAnswers, handleSelectGuidedAnswer]);

  // Voice-First question text generator for Guided Flow
  const getGuidedQuestionText = useCallback((step: number, lang: Language, answers: Partial<UserProfile>): string => {
    switch (step) {
      case 0:
        return lang === 'hi'
          ? 'आप किस राज्य या केंद्र शासित प्रदेश में रहते हैं?'
          : lang === 'kn'
          ? 'ನೀವು ಯಾವ ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶದಲ್ಲಿ ವಾಸಿಸುತ್ತೀರಿ?'
          : lang === 'te'
          ? 'మీరు ఏ రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతంలో నివసిస్తున్నారు?'
          : 'Which state or union territory do you reside in?';
      case 1:
        return lang === 'hi'
          ? 'आपकी वर्तमान आयु क्या है?'
          : lang === 'kn'
          ? 'ನಿಮ್ಮ ಪ್ರಸ್ತುತ ವಯಸ್ಸು ಎಷ್ಟು?'
          : lang === 'te'
          ? 'మీ ప్రస్తుత వయస్సు ఎంత?'
          : 'What is your current age?';
      case 2:
        return lang === 'hi'
          ? 'आपका लिंग क्या है? महिला, पुरुष या अन्य?'
          : lang === 'kn'
          ? 'ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು? ಮಹಿಳೆ, ಪುರುಷ ಅಥವಾ ಇತರೆ?'
          : lang === 'te'
          ? 'మీ లింగం ఏమిటి? మహిళ, పురుషుడు లేదా ఇతరులా?'
          : 'What is your gender? Female, male, or other?';
      case 3:
        return lang === 'hi'
          ? 'आपका मुख्य व्यवसाय क्या है? जैसे किसान, रेहड़ी पटरी विक्रेता, दैनिक मजदूर, या छात्र?'
          : lang === 'kn'
          ? 'ನಿಮ್ಮ ಮುಖ್ಯ ಉದ್ಯೋಗ ಯಾವುದು? ಉದಾಹರಣೆಗೆ ರೈತ, ಬೀದಿ ವ್ಯಾಪಾರಿ, ಕೂಲಿ ಕಾರ್ಮಿಕ, ಅಥವಾ ವಿದ್ಯಾರ್ಥಿ?'
          : lang === 'te'
          ? 'మీ ప్రధాన వృత్తి ఏమిటి? రైతు, వీధి వ్యాపారి, దినసరి కూలీ, లేదా విద్యಾರ್ಥಿ?'
          : 'What is your primary occupation or livelihood?';
      case 4: {
        const isFarmer = String(answers.occupation || '').toLowerCase().includes('farmer');
        if (isFarmer) {
          return lang === 'hi'
            ? 'क्या आपके पास कृषि भूमि है, या आप बटाईदार किसान हैं?'
            : lang === 'kn'
            ? 'ನಿಮ್ಮ ಬಳಿ ಸ್ವಂತ ಕೃಷಿ ಭೂಮಿ ಇದೆಯೇ ಅಥವಾ ನೀವು ಗೇಣಿ ರೈತರೇ?'
            : lang === 'te'
            ? 'మీకు వ్యవసాయ భూమి ఉందా లేదా మీరు కౌలు రైతులా?'
            : 'Do you own cultivable agricultural land, or do you cultivate as a tenant farmer?';
        }
        return lang === 'hi'
          ? 'क्या आप शहरी क्षेत्र में रेहड़ी, पटरी या ठेला लगाते हैं?'
          : lang === 'kn'
          ? 'ನೀವು ನಗರ ಪ್ರದೇಶದಲ್ಲಿ ಬೀದಿ ವ್ಯಾಪಾರ ಅಥವಾ ತಳ್ಳುಗಾಡಿ ನಡೆಸುತ್ತೀರಾ?'
          : lang === 'te'
          ? 'మీరు వీధి వ్యాపారం లేదా తోపుడు బండి నిర్వహిస్తున్నారా?'
          : 'Do you operate a street vending stall or mobile cart?';
      }
      case 5:
        return lang === 'hi'
          ? 'आपकी अनुमानित वार्षिक पारिवारिक आय कितनी है? क्या आपके पास बीपीएल कार्ड है?'
          : lang === 'kn'
          ? 'ನಿಮ್ಮ ಕುಟುಂಬದ ವಾರ್ಷಿಕ ಆದಾಯ ಎಷ್ಟು? ನಿಮ್ಮ ಬಳಿ ಬಿಪಿಎಲ್ ಕಾರ್ಡ್ ಇದೆಯೇ?'
          : lang === 'te'
          ? 'మీ కుటుంబ వార్షిక ఆదాయం ఎంత? మీ వద్ద బీపీఎల్ కార్డు ఉందా?'
          : 'What is your estimated annual family income?';
      case 6:
        return lang === 'hi'
          ? 'आपकी सामाजिक श्रेणी क्या है? जैसे सामान्य, ओबीसी, एससी, एसटी, या क्या आप दिव्यांग हैं?'
          : lang === 'kn'
          ? 'ನಿಮ್ಮ ಸಾಮಾಜಿಕ ವರ್ಗ ಯಾವುದು? ಸಾಮಾನ್ಯ, ಒಬಿಸಿ, ಎಸ್‌ಸಿ, ಎಸ್‌ಟಿ, ಅಥವಾ ವಿಶೇಷ ಚೇತನರೇ?'
          : lang === 'te'
          ? 'మీ సామాజిక వర్గం ఏమిటి? జనరల్, ఓబీసీ, ఎస్సీ, ఎస్టీ, లేదా దివ్యాంగులా?'
          : 'What is your social category and disability status?';
      case 7:
        return lang === 'hi'
          ? 'क्या आपके पास पक्का मकान है, और क्या डीबीटी सरकारी लाभ के लिए बैंक खाता व पासबुक है?'
          : lang === 'kn'
          ? 'ನಿಮ್ಮ ಬಳಿ ಪಕ್ಕಾ ಮನೆ ಇದೆಯೇ ಮತ್ತು ಬ್ಯಾಂಕ್ ಖಾತೆ ಅಥವಾ ಪಾಸ್‌ಬುಕ್ ಇದೆಯೇ?'
          : lang === 'te'
          ? 'మీకు పక్కా ఇల్లు ఉందా మరియు బ్యాంకు ఖాతా లేదా పాಸ್‌ಬುక్ ఉందా?'
          : 'Do you own a pucca permanent house, and do you have an active bank account with passbook?';
      case 8:
        return lang === 'hi'
          ? 'क्या आप आयकर देते हैं या नियमित सरकारी नौकरी में हैं?'
          : lang === 'kn'
          ? 'ನೀವು ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸುತ್ತೀರಾ ಅಥವಾ ಕಾಯಂ ಸರ್ಕಾರಿ ಉದ್ಯೋಗ ಹೊಂದಿದ್ದೀರಾ?'
          : lang === 'te'
          ? 'మీరు ఆదాయపు పన్ను చెల్లిస్తున్నారా లేదా ప్రభుత్వ ఉద్యోగం ఉందా?'
          : 'Do you pay income tax or hold a permanent government job?';
      default:
        return '';
    }
  }, []);

  // Speak assistant question aloud and automatically begin listening
  const speakQuestionAndListen = useCallback(
    (step: number) => {
      if (!isOnline || isVoicePaused || !isVoiceActive || sttPermissionDenied) return;
      const qText = getGuidedQuestionText(step, language, guidedAnswers);
      if (!qText) return;

      stopSpeaking();
      stopListening();

      if (autoReadAloud && isTtsSupported) {
        speak(qText, {
          lang: language,
          rate: voiceSpeed,
          onEnd: () => {
            if (isVoiceActive && !isVoicePaused && isOnline && !sttPermissionDenied) {
              resetTranscript();
              startListening();
            }
          },
        });
      } else {
        resetTranscript();
        startListening();
      }
    },
    [
      isOnline,
      isVoicePaused,
      isVoiceActive,
      sttPermissionDenied,
      getGuidedQuestionText,
      language,
      guidedAnswers,
      stopSpeaking,
      stopListening,
      autoReadAloud,
      isTtsSupported,
      speak,
      voiceSpeed,
      resetTranscript,
      startListening,
    ]
  );

  // Hands-free speech silence end handler (called after 2s silence)
  const handleHandsFreeSpeechEnd = useCallback(
    (speechText: string) => {
      const trimmed = speechText.trim();
      if (!trimmed || trimmed.length < 2) {
        if (isVoiceActive && !isVoicePaused && isOnline && !sttPermissionDenied) {
          startListening();
        }
        return;
      }

      // Check if user spoke in a different language
      const langCheck = detectInputLanguage(trimmed, language);
      if (langCheck.differsFromCurrent) {
        requestLanguageSwitch({
          detectedLang: langCheck.detectedLanguage,
          confidence: langCheck.confidence,
          sourceText: trimmed,
          triggerType: 'spoken',
          candidates: langCheck.candidates,
          reason: langCheck.reason,
        });
      }

      if (activeMode === 'guided') {
        if (!isGuidedComplete) {
          const handled = handleGuidedVoiceInput(trimmed);
          if (!handled) {
            setUncertainSpokenText(trimmed);
            if (autoReadAloud && isTtsSupported) {
              const confirmPrompt =
                language === 'hi'
                  ? `मैंने सुना "${trimmed}"। कृपया नीचे दिए गए विकल्पों में से चुनें या फिर से कहें।`
                  : `I heard "${trimmed}". Please choose an option below or speak again.`;
              speak(confirmPrompt, {
                lang: language,
                rate: voiceSpeed,
              });
            }
          } else {
            setUncertainSpokenText(null);
          }
        }
      } else {
        // Chat mode
        setUncertainSpokenText(null);
        handleSendMessage(trimmed, true);
      }
    },
    [
      isVoiceActive,
      isVoicePaused,
      isOnline,
      sttPermissionDenied,
      startListening,
      activeMode,
      isGuidedComplete,
      handleGuidedVoiceInput,
      autoReadAloud,
      isTtsSupported,
      language,
      voiceSpeed,
      speak,
      handleSendMessage,
      requestLanguageSwitch,
    ]
  );

  useEffect(() => {
    onSilenceDetectedRef.current = handleHandsFreeSpeechEnd;
  }, [handleHandsFreeSpeechEnd]);

  // Voice Interaction Pause & Resume controls
  const pauseVoiceInteraction = useCallback(() => {
    setIsVoicePaused(true);
    stopListening();
    stopSpeaking();
  }, [stopListening, stopSpeaking]);

  const resumeVoiceInteraction = useCallback(() => {
    setIsVoicePaused(false);
    setIsVoiceActive(true);
    setPermissionDeniedBanner(false);
    if (!isOnline) {
      setApiError(t('offlineChatNotice', language));
      return;
    }
    if (activeMode === 'guided' && !isGuidedComplete) {
      speakQuestionAndListen(guidedStep);
    } else {
      resetTranscript();
      startListening();
    }
  }, [isOnline, activeMode, isGuidedComplete, speakQuestionAndListen, guidedStep, resetTranscript, startListening, language]);

  // Guided mode hands-free question turn-taking
  useEffect(() => {
    if (activeMode !== 'guided' || isGuidedComplete) return;
    if (!isVoiceActive || isVoicePaused || !isOnline || sttPermissionDenied) return;

    if (lastReadStepRef.current !== guidedStep) {
      lastReadStepRef.current = guidedStep;
      const timer = setTimeout(() => {
        speakQuestionAndListen(guidedStep);
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [
    activeMode,
    guidedStep,
    isGuidedComplete,
    isVoiceActive,
    isVoicePaused,
    isOnline,
    sttPermissionDenied,
    speakQuestionAndListen,
  ]);

  // Guided evaluation complete announcement
  useEffect(() => {
    if (isGuidedComplete && guidedMatchedSchemes.length >= 0) {
      stopListening();
      if (autoReadAloud && isTtsSupported && isOnline) {
        const count = guidedMatchedSchemes.length;
        const announcement =
          language === 'hi'
            ? `प्रोफ़ाइल पूरी हो गई। मैंने आपके लिए ${count} योजनाएं खोजी हैं।`
            : language === 'kn'
            ? `ಪ್ರೊಫೈಲ್ ಪೂರ್ಣಗೊಂಡಿದೆ. ನಿಮ್ಮ ಅರ್ಹತೆಗೆ ತಕ್ಕ ${count} ಯೋಜನೆಗಳು ಲಭ್ಯವಿವೆ.`
            : language === 'te'
            ? `ప్రొఫైల్ పూర్తయింది. మీ కోసం ${count} పథకాలు అందుబాటులో ఉన్నాయి.`
            : `Profile setup complete! I found ${count} schemes you may be eligible for. Tap any scheme to view benefits and documents.`;
        speak(announcement, { lang: language, rate: voiceSpeed });
      }
    }
  }, [isGuidedComplete, guidedMatchedSchemes.length, autoReadAloud, isTtsSupported, isOnline, language, voiceSpeed, speak, stopListening]);

  // Microphone permission denied watcher
  useEffect(() => {
    if (sttPermissionDenied || sttErrorType === 'permission_denied') {
      setPermissionDeniedBanner(true);
      setIsVoiceActive(false);
      stopListening();
      stopSpeaking();
    }
  }, [sttPermissionDenied, sttErrorType, stopListening, stopSpeaking]);

  // Handler for Bottom Navigation Voice AI button (and auto-navigation to voice)
  const handleBottomVoiceClick = useCallback(() => {
    // 1. Ensure AI Support Chat is always active by default when entering via Voice AI
    setActiveMode('chat');

    // Remove any stale guided URL params if present
    if (searchParams.get('guided') === 'true' || searchParams.get('mode') === 'guided') {
      const updatedParams = new URLSearchParams(searchParams);
      updatedParams.delete('guided');
      updatedParams.set('mode', 'chat');
      setSearchParams(updatedParams, { replace: true });
    }

    // 2. Prevent multiple simultaneous speech recognition sessions
    if (isListening || isListeningRef.current) {
      return;
    }

    // 2. If microphone permission is denied, show clear/simple error message and allow text input
    if (sttPermissionDenied || sttErrorType === 'permission_denied') {
      setPermissionDeniedBanner(true);
      inputRef.current?.focus();
      return;
    }

    // 3. Gracefully handle browser lacking speech recognition support
    if (!isSttSupported) {
      setApiError(
        language === 'hi'
          ? 'आपके ब्राउज़र में वॉयस इनपुट समर्थित नहीं है। कृपया नीचे टेक्स्ट बॉक्स का उपयोग करें।'
          : language === 'kn'
          ? 'ನಿಮ್ಮ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಬೆಂಬಲಿತವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಪಠ್ಯವನ್ನು ಬಳಸಿ.'
          : language === 'te'
          ? 'మీ బ్రౌజర్‌లో వాయిస్ ఇన్‌పుట్ సపోర్ట్ లేదు. దయచేసి టెక్స్ట్ ఉపయోగించండి.'
          : 'Voice input is not supported in this browser. Please use text input.'
      );
      inputRef.current?.focus();
      return;
    }

    // 4. Handle offline mode
    if (!isOnline) {
      setApiError(t('offlineChatNotice', language));
      return;
    }

    // 5. If speech synthesis is speaking, stop speaking so user can speak immediately
    if (isSpeaking) {
      stopSpeaking();
    }

    // 6. Explicit click unpauses voice, sets voice active, and clears error states
    setIsVoicePaused(false);
    setIsVoiceActive(true);
    setPermissionDeniedBanner(false);
    setApiError(null);
    resetTranscript();
    setGuidedVoiceHeard(null);
    setUncertainSpokenText(null);

    // 7. Immediately start listening for the user's voice
    startListening();

    // 8. Resilient retry tick in case Web Speech instance was initializing on first mount
    const timer = setTimeout(() => {
      if (!isListeningRef.current) {
        try {
          startListening();
        } catch {
          // ignore
        }
      }
    }, 120);

    return () => clearTimeout(timer);
  }, [
    isListening,
    sttPermissionDenied,
    sttErrorType,
    isSttSupported,
    isOnline,
    isSpeaking,
    stopSpeaking,
    language,
    resetTranscript,
    startListening,
    searchParams,
    setSearchParams,
  ]);

  // Sync active mode if searchParams mode changes explicitly
  useEffect(() => {
    const modeParam = searchParams.get('mode');
    const isGuided = searchParams.get('guided') === 'true';
    if (modeParam === 'chat') {
      setActiveMode('chat');
    } else if (modeParam === 'guided' || isGuided) {
      setActiveMode('guided');
    }
  }, [searchParams]);

  const prevStartParamRef = useRef<string | null>(null);
  const initialVoiceHandledRef = useRef<boolean>(false);

  // Auto-start listening when navigated to Voice AI with ?voice=true or ?start=...
  useEffect(() => {
    const currentStart = searchParams.get('start');
    const isVoice = searchParams.get('voice') === 'true' || searchParams.get('voice') === '1';

    if (!initialVoiceHandledRef.current) {
      initialVoiceHandledRef.current = true;
      prevStartParamRef.current = currentStart;
      if (isVoice || currentStart) {
        handleBottomVoiceClick();
      }
      return;
    }

    // If navigated again with a new start timestamp
    if (currentStart && currentStart !== prevStartParamRef.current) {
      prevStartParamRef.current = currentStart;
      handleBottomVoiceClick();
    }
  }, [searchParams, handleBottomVoiceClick]);

  // Listen for custom window event dispatched by BottomNav when already on /assistant
  useEffect(() => {
    const onVoiceEvent = () => {
      handleBottomVoiceClick();
    };
    window.addEventListener('yojana:start-voice-ai', onVoiceEvent);
    return () => {
      window.removeEventListener('yojana:start-voice-ai', onVoiceEvent);
    };
  }, [handleBottomVoiceClick]);

  // VoiceOrb click handler
  const handleOrbClick = () => {
    if (isSpeaking) {
      stopSpeaking();
      if (isVoiceActive && !isVoicePaused) {
        resetTranscript();
        startListening();
      }
      return;
    }
    if (isListening) {
      stopListening();
      const speechToSubmit = (editableTranscript || sttTranscript).trim();
      if (speechToSubmit) {
        if (activeMode === 'guided') {
          handleGuidedVoiceInput(speechToSubmit);
        } else {
          setInputText(speechToSubmit);
          inputRef.current?.focus();
        }
      } else {
        pauseVoiceInteraction();
      }
      return;
    }
    if (!isOnline) {
      setApiError(t('offlineChatNotice', language));
      return;
    }
    resumeVoiceInteraction();
  };

  const orbState: VoiceOrbState = useMemo(() => {
    if (apiError || (sttError && sttErrorType === 'permission_denied')) return 'error';
    if (isSpeaking) return 'speaking';
    if (isVoicePaused || !isVoiceActive) return 'paused';
    if (isSubmitting || streamingText || isEvaluatingGuided) return 'processing';
    if (isListening) return 'listening';
    return 'idle';
  }, [apiError, sttError, sttErrorType, isSpeaking, isVoicePaused, isVoiceActive, isSubmitting, streamingText, isEvaluatingGuided, isListening]);

  const handleResetSession = () => {
    if (abortStreamRef.current) {
      abortStreamRef.current();
      abortStreamRef.current = null;
    }
    stopSpeaking();
    abortListening();
    resetTranscript();
    setEditableTranscript('');
    const currentSessionId = getSessionId();
    resetChatSession(currentSessionId);
    clearChat();
    initialQueryHandledRef.current = false;
    setActiveProfileState({});
    setStreamingCitations([]);
    setApiError(null);
    setStreamingText('');
    isSubmittingRef.current = false;
    setIsSubmitting(false);

    // Reset guided profile
    setGuidedStep(0);
    setGuidedAnswers({});
    setIsGuidedComplete(false);
    setGuidedMatchedSchemes([]);
  };

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col pb-28 selection:bg-sage">
      <Header
        title={t('assistantTitle', language)}
        subtitle={language === 'hi' ? 'आवाज़ सहायक' : 'Voice Assistant'}
        showBack
      />

      {/* Top Controls Strip: Voice Toggle, 4 Languages, Reset */}
      <div className="bg-surface/90 border-b border-sand px-4 py-2 sticky top-16 z-20 backdrop-blur-md">
        <div className="max-w-3xl mx-auto flex flex-wrap items-center justify-between gap-2">
          {/* Voice Output Toggle */}
          <button
            type="button"
            onClick={() => {
              if (autoReadAloud) {
                stopSpeaking();
                setAutoReadAloud(false);
              } else {
                setAutoReadAloud(true);
              }
            }}
            className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border transition-all ${
              autoReadAloud
                ? 'bg-forest text-white border-forest shadow-xs'
                : 'bg-surface text-ink/70 border-sand hover:text-ink'
            }`}
            aria-label={autoReadAloud ? 'Mute voice readouts' : 'Enable voice readouts'}
          >
            {autoReadAloud ? (
              <>
                <Volume2 className="w-3.5 h-3.5 animate-pulse text-amber-300" />
                <span>
                  {language === 'hi'
                    ? 'आवाज़ चालू'
                    : language === 'kn'
                    ? 'ಧ್ವನಿ ಸಕ್ರಿಯ'
                    : language === 'te'
                    ? 'వాయిస్ ఆన్'
                    : 'Voice On'}
                </span>
              </>
            ) : (
              <>
                <VolumeX className="w-3.5 h-3.5" />
                <span>
                  {language === 'hi'
                    ? 'आवाज़ बंद'
                    : language === 'kn'
                    ? 'ಧ್ವನಿ ಮ್ಯೂಟ್'
                    : language === 'te'
                    ? 'వాయిస్ మ్యూట్'
                    : 'Voice Muted'}
                </span>
              </>
            )}
          </button>

          {/* Quick 4-Language Switcher */}
          <div className="flex items-center gap-1" role="region" aria-label="Language selection">
            {(['en', 'hi', 'kn', 'te'] as const).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLanguage(l)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-full border transition-colors ${
                  language === l
                    ? 'bg-forest text-white border-forest shadow-xs'
                    : 'bg-surface text-ink/70 border-sand hover:text-ink hover:bg-sand/30'
                }`}
              >
                {l === 'en' ? 'English' : l === 'hi' ? 'हिन्दी' : l === 'kn' ? 'ಕನ್ನಡ' : 'తెలుగు'}
              </button>
            ))}
          </div>

          {/* Reset / New Session */}
          <button
            onClick={handleResetSession}
            title={t('newConversationCTA', language)}
            className="text-xs font-semibold text-ink/70 hover:text-forest flex items-center gap-1 px-2.5 py-1 rounded-full border border-sand hover:bg-sand/30 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{t('newConversationCTA', language)}</span>
          </button>
        </div>
      </div>

      {/* Mode Switcher: Guided Profile Check vs Freeform Chat */}
      <div className="bg-sand/20 border-b border-sand/40 px-4 py-1.5">
        <div className="max-w-3xl mx-auto flex items-center justify-center gap-2">
          <button
            type="button"
            onClick={() => setActiveMode('guided')}
            className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeMode === 'guided'
                ? 'bg-forest text-white shadow-xs'
                : 'text-ink/70 hover:text-forest bg-surface border border-sand'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>
              {language === 'hi'
                ? 'मार्गदर्शित पात्रता जांच'
                : language === 'kn'
                ? 'ಮಾರ್ಗದರ್ಶಿತ ಅರ್ಹತಾ ಪರಿಶೀಲನೆ'
                : language === 'te'
                ? 'గైడెడ్ అర్హత తనిఖీ'
                : 'Guided Scheme Eligibility'}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveMode('chat')}
            className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
              activeMode === 'chat'
                ? 'bg-forest text-white shadow-xs'
                : 'text-ink/70 hover:text-forest bg-surface border border-sand'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>
              {language === 'hi'
                ? 'AI सहायता चैट'
                : language === 'kn'
                ? 'AI ಚಾಟ್ ಸಹಾಯಕ'
                : language === 'te'
                ? 'AI చాట్ సహాయం'
                : 'AI Support Chat'}
            </span>
          </button>
        </div>
      </div>

      {/* Live Synced Citizen Profile Bar: Active in both AI Guidance Chat & Buttons Mode */}
      {profileChips.length > 0 && (
        <div className="bg-emerald-50/80 border-b border-emerald-200/70 px-4 py-2">
          <div className="max-w-3xl mx-auto flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-0.5">
              <div className="flex items-center gap-1.5 font-bold text-emerald-900 whitespace-nowrap">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
                </span>
                <span>
                  {language === 'hi'
                    ? 'प्रोफ़ाइल सिंक (लाइव):'
                    : language === 'kn'
                    ? 'ಪ್ರೊಫೈಲ್ ಸಿಂಕ್ (ಲೈವ್):'
                    : language === 'te'
                    ? 'ప్రొఫైల్ సింక్ (లైవ్):'
                    : 'Profile Synced:'}
                </span>
              </div>

              {/* Profile Chips */}
              <div className="flex items-center gap-1.5 flex-nowrap">
                {profileChips.map((chip, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-0.5 rounded-full bg-white border border-emerald-200 text-ink font-semibold whitespace-nowrap shadow-2xs flex items-center gap-1 text-[11px]"
                  >
                    <span>{chip.icon}</span>
                    <span>{chip.label}</span>
                  </span>
                ))}
              </div>
            </div>

            <Link
              to="/profile"
              className="text-forest hover:text-forest-dark font-bold underline whitespace-nowrap flex items-center gap-0.5 shrink-0 ml-1 text-[11px]"
              title="Review Full Citizen Profile"
            >
              <span>{language === 'hi' ? 'समीक्षा' : language === 'kn' ? 'ಪರಿಶೀಲಿಸಿ' : language === 'te' ? 'సమీక్షించండి' : 'Review Profile'}</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}

      {/* Error / System Notices */}
      {apiError && (
        <div className="max-w-3xl w-full mx-auto px-4 pt-3">
          <div className="bg-red-50 border border-red-200 text-red-900 rounded-xl p-3 flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{apiError}</span>
            </div>
            <button
              onClick={() => setApiError(null)}
              className="text-xs font-bold text-red-700 hover:underline px-2 py-0.5"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Voice Readout Notice for Missing OS Voice Packs */}
      {voiceUnavailableWarning && (
        <div className="max-w-3xl w-full mx-auto px-4 pt-3">
          <div className="bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-xl p-3 flex items-start justify-between gap-2 shadow-xs">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block">{t('voiceReadoutNotice', language)}</span>
                <p className="mt-0.5 leading-relaxed">{t('voiceNotInstalledNotice', language)}</p>
              </div>
            </div>
            <button
              onClick={() => stopSpeaking()}
              className="text-xs font-bold text-amber-800 hover:underline px-2 py-0.5"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Permission Denied Notice */}
      {permissionDeniedBanner && (
        <div className="max-w-3xl w-full mx-auto px-4 pt-3">
          <div className="bg-red-50 border border-red-300 text-red-950 rounded-2xl p-4 shadow-sm space-y-2">
            <div className="flex items-start gap-2.5">
              <Mic className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5 line-through" />
              <div className="text-xs space-y-1">
                <span className="font-bold block text-sm">
                  {language === 'hi'
                    ? 'माइक्रोफ़ोन अनुमति अवरोधित है'
                    : language === 'kn'
                    ? 'ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ'
                    : language === 'te'
                    ? 'మైక్రోఫోన్ అనుమతి నిరాకరించబడింది'
                    : 'Microphone Access Denied'}
                </span>
                <p className="text-red-900/80 leading-relaxed">
                  {language === 'hi'
                    ? 'ब्राउज़र ने माइक्रोफ़ोन का उपयोग अस्वीकार कर दिया है। आप नीचे दिए गए बटनों या टेक्स्ट बॉक्स का उपयोग करके आगे बढ़ सकते हैं।'
                    : language === 'kn'
                    ? 'ಬ್ರೌಸರ್ ಮೈಕ್ರೊಫೋನ್ ಪ್ರವೇಶವನ್ನು ನಿರಾಕರಿಸಿದೆ. ನೀವು ಕೆಳಗಿನ ಬಟನ್‌ಗಳು ಅಥವಾ ಪಠ್ಯವನ್ನು ಬಳಸಿಕೊಂಡು ಮುಂದುವರಿಯಬಹುದು.'
                    : language === 'te'
                    ? 'బ్రౌజర్ మైక్రోఫోన్ యాక్సెస్‌ను తిరస్కరించింది. మీరు క్రింది బಟన్లు లేదా టెక్స్ట్ ఉపయోగించి కొనసాగవచ్చు.'
                    : 'Microphone permission was denied by your browser. You can seamlessly continue using buttons and text below, or enable microphone in site settings.'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1 pl-7">
              <button
                type="button"
                onClick={() => setPermissionDeniedBanner(false)}
                className="px-3.5 py-1.5 bg-red-700 text-white rounded-xl text-xs font-bold hover:bg-red-800 transition-colors shadow-xs"
              >
                {language === 'hi'
                  ? 'बटन और टेक्स्ट से जारी रखें'
                  : language === 'kn'
                  ? 'ಬಟನ್ ಮತ್ತು ಪಠ್ಯದೊಂದಿಗೆ ಮುಂದುವರಿಯಿರಿ'
                  : language === 'te'
                  ? 'బటన్లు మరియు టెక్స్ట్‌తో కొనసాగండి'
                  : 'Continue with Buttons & Text'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setPermissionDeniedBanner(false);
                  handleBottomVoiceClick();
                }}
                className="px-3 py-1.5 bg-surface text-ink/80 border border-sand rounded-xl text-xs font-semibold hover:bg-sand/30"
              >
                {language === 'hi'
                  ? 'पुनः प्रयास करें'
                  : language === 'kn'
                  ? 'ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ'
                  : language === 'te'
                  ? 'మళ్ళీ ప్రయత్నించండి'
                  : 'Try Again'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Offline Mode Notice */}
      {!isOnline && (
        <div className="max-w-3xl w-full mx-auto px-4 pt-3">
          <div className="bg-amber-50 border border-amber-300 text-amber-950 rounded-2xl p-4 shadow-sm flex items-start justify-between gap-3 text-xs">
            <div className="flex items-start gap-2.5">
              <WifiOff className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold text-sm block">
                  {language === 'hi' ? 'ऑफ़लाइन मोड सक्रिय' : 'Offline Mode Active'}
                </span>
                <p className="text-amber-900/80 leading-relaxed">
                  {language === 'hi'
                    ? 'इस डिवाइस के ब्राउज़र में आवाज़ पहचान (Speech Recognition) के लिए इंटरनेट कनेक्शन आवश्यक है। आप नीचे दिए गए बटनों से पात्रता जांच पूरी कर सकते हैं।'
                    : 'Speech recognition requires an internet connection on this browser. The full profile eligibility flow remains available using the buttons and options below.'}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => checkConnection()}
              className="px-3 py-1.5 bg-amber-200 hover:bg-amber-300 border border-amber-400 text-amber-950 rounded-xl font-bold text-xs shrink-0"
            >
              {t('checkConnectionAction', language)}
            </button>
          </div>
        </div>
      )}

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-4 flex flex-col items-center justify-start gap-4">
        {/* VOICE ORB (Always available for tap-to-speak in both modes) */}
        <div className="w-full flex flex-col items-center justify-center pt-1 pb-2 text-center">
          <VoiceOrb
            state={orbState}
            onClick={handleOrbClick}
            transcript={sttTranscript}
            interimTranscript={sttInterimTranscript}
            errorMessage={sttError || apiError || undefined}
            language={language}
            size="sm"
            onStopSpeaking={() => stopSpeaking()}
            onReplay={() => {}}
          />

          {/* Voice Status & Action Controls */}
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
            {isVoiceActive && !isVoicePaused ? (
              <>
                {isListening && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 text-xs font-bold animate-pulse">
                    <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping" />
                    <span>{language === 'hi' ? 'सुन रहे हैं (बोलें)...' : 'Listening (Hands-Free)...'}</span>
                  </span>
                )}
                {isSpeaking && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-100 text-blue-900 border border-blue-300 text-xs font-bold">
                    <Volume2 className="w-3.5 h-3.5 text-blue-700 animate-pulse" />
                    <span>{language === 'hi' ? 'प्रश्न बोला जा रहा है...' : 'Reading Aloud...'}</span>
                  </span>
                )}
                {(isSubmitting || isEvaluatingGuided) && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300 text-xs font-bold">
                    <Sparkles className="w-3.5 h-3.5 text-amber-700 animate-spin" />
                    <span>{language === 'hi' ? 'प्रक्रिया जारी...' : 'Processing...'}</span>
                  </span>
                )}
                <button
                  type="button"
                  onClick={pauseVoiceInteraction}
                  className="px-3 py-1.5 rounded-full bg-surface border border-sand hover:bg-sand/30 text-ink text-xs font-bold flex items-center gap-1.5 shadow-2xs transition-colors"
                  title="Pause hands-free voice mode"
                >
                  <Pause className="w-3.5 h-3.5 text-ink/70" />
                  <span>{language === 'hi' ? 'आवाज़ रोकें' : 'Pause Voice'}</span>
                </button>
                {isListening && (
                  <button
                    type="button"
                    onClick={() => {
                      const heard = (editableTranscript || sttTranscript).trim();
                      if (heard) {
                        handleHandsFreeSpeechEnd(heard);
                      } else {
                        stopListening();
                      }
                    }}
                    className="px-3.5 py-1.5 rounded-full bg-forest text-white hover:bg-forest-deep text-xs font-bold flex items-center gap-1 shadow-xs transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{language === 'hi' ? 'भेजें (Done)' : 'Done Speaking'}</span>
                  </button>
                )}
                {isSpeaking && (
                  <button
                    type="button"
                    onClick={() => stopSpeaking()}
                    className="px-3 py-1.5 rounded-full bg-red-700 text-white hover:bg-red-800 text-xs font-bold flex items-center gap-1 shadow-xs transition-colors"
                  >
                    <VolumeX className="w-3.5 h-3.5" />
                    <span>{t('stopAudio', language)}</span>
                  </button>
                )}
              </>
            ) : (
              <button
                type="button"
                onClick={resumeVoiceInteraction}
                disabled={!isOnline}
                className="px-4 py-1.5 rounded-full bg-forest text-white hover:bg-forest-deep disabled:opacity-50 text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all active:scale-95"
              >
                <Play className="w-3.5 h-3.5 fill-current text-amber-300" />
                <span>{language === 'hi' ? 'हैंड्स-फ़्री आवाज़ शुरू करें' : 'Resume Hands-Free Voice'}</span>
              </button>
            )}
          </div>

          {/* Uncertain Speech Confirmation Box */}
          {uncertainSpokenText && (
            <div className="max-w-md w-full mx-auto mt-3 bg-amber-50/95 border border-amber-300 rounded-2xl p-3 shadow-sm space-y-2 animate-in fade-in text-left">
              <div className="flex items-start justify-between gap-2 text-xs text-amber-950">
                <div className="flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4 text-amber-700 flex-shrink-0" />
                  <span>
                    <strong>{language === 'hi' ? 'पहचाना गया:' : 'Recognized:'}</strong> &ldquo;{uncertainSpokenText}&rdquo;
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setUncertainSpokenText(null)}
                  className="text-amber-800 font-bold hover:text-amber-950 text-xs px-1"
                >
                  ✕
                </button>
              </div>
              <p className="text-[11px] text-amber-900/80">
                {language === 'hi'
                  ? 'कृपया पुष्टि करें कि क्या यह सही है, या फिर से बोलें।'
                  : 'Please confirm if this is correct, or speak again.'}
              </p>
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    const txt = uncertainSpokenText;
                    setUncertainSpokenText(null);
                    if (activeMode === 'guided') {
                      handleGuidedVoiceInput(txt);
                    } else {
                      handleSendMessage(txt, false);
                    }
                  }}
                  className="px-3 py-1 bg-forest text-white font-bold rounded-lg hover:bg-forest-deep flex items-center gap-1 shadow-2xs"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>{language === 'hi' ? 'पुष्टि करें' : 'Confirm'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUncertainSpokenText(null);
                    resetTranscript();
                    startListening();
                  }}
                  className="px-3 py-1 bg-surface border border-sand text-ink font-semibold rounded-lg hover:bg-sand/30 flex items-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>{language === 'hi' ? 'फिर से बोलें' : 'Speak Again'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const txt = uncertainSpokenText;
                    setUncertainSpokenText(null);
                    setInputText(txt);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-1 bg-surface border border-sand text-ink/70 font-semibold rounded-lg hover:text-ink hover:bg-sand/30"
                >
                  {language === 'hi' ? 'संपादित करें' : 'Edit'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ============================================================== */}
        {/* MODE 1: PROFILE-FIRST GUIDED ELIGIBILITY FLOW                   */}
        {/* ============================================================== */}
        {activeMode === 'guided' && (
          <div className="w-full max-w-2xl space-y-4">
            {!isGuidedComplete ? (
              /* ACTIVE STEP-BY-STEP QUESTION CARD */
              <div className="bg-surface rounded-3xl border border-sand shadow-card p-5 sm:p-6 space-y-5">
                {/* Progress Header */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-ink/70">
                    <span className="text-forest font-bold uppercase tracking-wider">
                      {t('guidedStepProgress', language)} {guidedStep + 1} {t('guidedOf', language)} {TOTAL_GUIDED_STEPS} • {t('guidedSetupTitle', language)}
                    </span>
                    <span>{Math.round(((guidedStep + 1) / TOTAL_GUIDED_STEPS) * 100)}%</span>
                  </div>
                  <div className="w-full bg-sand/40 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-forest h-full rounded-full transition-all duration-300"
                      style={{ width: `${((guidedStep + 1) / TOTAL_GUIDED_STEPS) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Voice Input Heard Pill (Notice without chat pollution) */}
                {guidedVoiceHeard && (
                  <div className="flex items-center justify-between text-xs bg-amber-50 border border-amber-200 text-amber-900 px-3 py-2 rounded-xl animate-in fade-in">
                    <span>
                      <strong>Heard:</strong> &ldquo;{guidedVoiceHeard}&rdquo; — Please select an option below
                    </span>
                    <button
                      type="button"
                      onClick={() => setGuidedVoiceHeard(null)}
                      className="text-amber-800 font-bold ml-2 text-xs hover:text-amber-950"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {/* QUESTION 0: Location (State / UT) */}
                {guidedStep === 0 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'आप किस राज्य या केंद्र शासित प्रदेश में रहते हैं?'
                            : language === 'kn'
                            ? 'ನೀವು ಯಾವ ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶದಲ್ಲಿ ವಾಸಿಸುತ್ತೀರಿ?'
                            : language === 'te'
                            ? 'మీరు ఏ రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతంలో నివసిస్తున్నారు?'
                            : 'Which state or union territory do you reside in?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'केंद्रीय और राज्य-विशिष्ट कल्याणकारी योजनाओं की पात्रता के लिए।'
                            : 'Required to match central schemes and state-specific benefits.'}
                        </p>
                      </div>
                      {isTtsSupported && (
                        <button
                          type="button"
                          onClick={() => {
                            const qText = language === 'hi'
                              ? 'आप किस राज्य या केंद्र शासित प्रदेश में रहते हैं?'
                              : 'Which state or union territory do you reside in?';
                            handleToggleSpeak('q-state', qText);
                          }}
                          className="p-2 rounded-full bg-sage text-forest hover:bg-sage/80"
                          title="Listen to question"
                        >
                          <Volume2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>

                    {/* Quick State Chips */}
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-bold text-ink/60 uppercase tracking-wide">
                        {language === 'hi'
                          ? 'त्वरित चयन:'
                          : language === 'kn'
                          ? 'ತ್ವರಿತ ಆಯ್ಕೆ:'
                          : language === 'te'
                          ? 'త్వరిత ఎంపిక:'
                          : 'Quick Select:'}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {['Karnataka', 'Uttar Pradesh', 'Maharashtra', 'Bihar', 'Tamil Nadu', 'Rajasthan', 'Madhya Pradesh', 'West Bengal'].map(
                          (st) => (
                            <button
                              key={st}
                              type="button"
                              onClick={() => handleSelectGuidedAnswer({ state: st })}
                              className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all active:scale-95 ${
                                guidedAnswers.state === st
                                  ? 'bg-forest text-white border-forest shadow-xs'
                                  : 'bg-canvas text-ink border-sand hover:border-forest/50'
                              }`}
                            >
                              {st}
                            </button>
                          )
                        )}
                      </div>
                    </div>

                    {/* All States Dropdown */}
                    <div className="space-y-1.5 pt-2 border-t border-sand/40">
                      <label className="text-xs font-bold text-ink/80 block">
                        {language === 'hi'
                          ? 'या सभी राज्यों / केंद्र शासित प्रदेशों में से चुनें:'
                          : language === 'kn'
                          ? 'ಅಥವಾ ಎಲ್ಲಾ ರಾಜ್ಯಗಳು / ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶಗಳಿಂದ ಆಯ್ಕೆಮಾಡಿ:'
                          : language === 'te'
                          ? 'లేదా అన్ని రాష్ట్రాలు / కేంద్రపాలిత ప్రాంతాల నుండి ఎంచుకోండి:'
                          : 'Or select from all States / UTs:'}
                      </label>
                      <select
                        value={guidedAnswers.state || ''}
                        onChange={(e) => {
                          if (e.target.value) {
                            handleSelectGuidedAnswer({ state: e.target.value });
                          }
                        }}
                        className="w-full bg-canvas border border-sand rounded-xl px-3 py-2.5 text-xs text-ink font-medium focus:ring-2 focus:ring-forest focus:outline-none"
                      >
                        <option value="">
                          {language === 'hi'
                            ? '-- अपना राज्य या केंद्र शासित प्रदेश चुनें --'
                            : language === 'kn'
                            ? '-- ನಿಮ್ಮ ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ ಆಯ್ಕೆಮಾಡಿ --'
                            : language === 'te'
                            ? '-- మీ రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతాన్ని ఎంచుకోండి --'
                            : '-- Choose your State or UT --'}
                        </option>
                        {INDIAN_STATES.map((st) => (
                          <option key={st} value={st}>
                            {st}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}

                {/* QUESTION 1: Age */}
                {guidedStep === 1 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'आपकी वर्तमान आयु क्या है?'
                            : language === 'kn'
                            ? 'ನಿಮ್ಮ ಪ್ರಸ್ತುತ ವಯಸ್ಸು ಎಷ್ಟು?'
                            : language === 'te'
                            ? 'మీ ప్రస్తుత వయస్సు ఎంత?'
                            : 'What is your current age?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'पेंशन (60+), आजीविका ऋण (18-40) व छात्रवृत्ति के लिए आवश्यक।'
                            : 'Needed for age-specific programs (e.g. 60+ for pensions, 18-40 for loans).'}
                        </p>
                      </div>
                      {isTtsSupported && (
                        <button
                          type="button"
                          onClick={() => {
                            const qText = language === 'hi' ? 'आपकी वर्तमान आयु क्या है?' : 'What is your current age?';
                            handleToggleSpeak('q-age', qText);
                          }}
                          className="p-2 rounded-full bg-sage text-forest hover:bg-sage/80"
                          title="Listen"
                        >
                          <Volume2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>

                    {/* Quick Age Brackets */}
                    <div className="grid grid-cols-2 gap-2.5">
                      {[
                        {
                          label: {
                            en: '18 - 25 years (Youth / Student)',
                            hi: '18 - 25 वर्ष (युवा / छात्र)',
                            kn: '18 - 25 ವರ್ಷ (ಯುವಕ / ವಿದ್ಯಾರ್ಥಿ)',
                            te: '18 - 25 సంవత్సరాలు (యువత / విద్యార్థి)',
                          },
                          ageVal: 22,
                        },
                        {
                          label: {
                            en: '26 - 40 years (Working Age)',
                            hi: '26 - 40 वर्ष (कार्यशील आयु)',
                            kn: '26 - 40 ವರ್ಷ (ದುಡಿಯುವ ವಯಸ್ಸು)',
                            te: '26 - 40 సంవత్సరాలు (పనిచేసే వయస్సు)',
                          },
                          ageVal: 32,
                        },
                        {
                          label: {
                            en: '41 - 59 years (Adult Worker)',
                            hi: '41 - 59 वर्ष (प्रौढ़ श्रमिक)',
                            kn: '41 - 59 ವರ್ಷ (ವಯಸ್ಕ ಕಾರ್ಮಿಕ)',
                            te: '41 - 59 సంవత్సరాలు (వయోజన కార్మికుడు)',
                          },
                          ageVal: 48,
                        },
                        {
                          label: {
                            en: '60+ years (Senior Citizen)',
                            hi: '60+ वर्ष (वरिष्ठ नागरिक)',
                            kn: '60+ ವರ್ಷ (ಹಿರಿಯ ನಾಗರಿಕ)',
                            te: '60+ సంవత్సరాలు (సీనియర్ సిటిజన్)',
                          },
                          ageVal: 65,
                        },
                      ].map((b) => (
                        <button
                          key={b.ageVal}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer({ age: b.ageVal })}
                          className={`p-3 rounded-2xl text-left border transition-all active:scale-95 ${
                            guidedAnswers.age === b.ageVal
                              ? 'bg-forest text-white border-forest shadow-xs'
                              : 'bg-canvas text-ink border-sand hover:border-forest/50'
                          }`}
                        >
                          <span className="font-bold text-xs block">
                            {b.label[language] || b.label.en}
                          </span>
                        </button>
                      ))}
                    </div>

                    {/* Custom Exact Age Box */}
                    <div className="pt-2 border-t border-sand/40 flex items-center gap-2">
                      <span className="text-xs text-ink/70 font-medium">
                        {language === 'hi'
                          ? 'या सटीक आयु दर्ज करें:'
                          : language === 'kn'
                          ? 'ಅಥವಾ ನಿಖರವಾದ ವಯಸ್ಸನ್ನು ನಮೂದಿಸಿ:'
                          : language === 'te'
                          ? 'లేదా ఖచ్చితమైన వయస్సును నమోదు చేయండి:'
                          : 'Or enter exact age:'}
                      </span>
                      <input
                        type="number"
                        min="1"
                        max="115"
                        value={customAgeInput}
                        onChange={(e) => setCustomAgeInput(e.target.value)}
                        placeholder="e.g. 45"
                        className="w-24 bg-canvas border border-sand rounded-xl px-3 py-1.5 text-xs text-ink focus:ring-2 focus:ring-forest focus:outline-none"
                      />
                      <button
                        type="button"
                        disabled={!customAgeInput}
                        onClick={() => {
                          const val = parseInt(customAgeInput, 10);
                          if (val >= 1 && val <= 115) {
                            handleSelectGuidedAnswer({ age: val });
                          }
                        }}
                        className="px-3 py-1.5 bg-forest text-white text-xs font-bold rounded-xl hover:bg-forest-deep disabled:opacity-40"
                      >
                        {language === 'hi'
                          ? 'आयु की पुष्टि करें'
                          : language === 'kn'
                          ? 'ವಯಸ್ಸು ದೃಢೀಕರಿಸಿ'
                          : language === 'te'
                          ? 'వయస్సును ధృవీకరించండి'
                          : 'Confirm Age'}
                      </button>
                    </div>
                  </div>
                )}

                {/* QUESTION 2: Gender */}
                {guidedStep === 2 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'आपका लिंग क्या है?'
                            : language === 'kn'
                            ? 'ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು?'
                            : language === 'te'
                            ? 'మీ లింగం ఏమిటి?'
                            : 'What is your gender?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'कुछ योजनाएं विशेष रूप से महिलाओं व माताओं के लिए हैं।'
                            : 'Certain government schemes offer dedicated benefits and subsidies for women.'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2.5">
                      {[
                        { label: { en: 'Female', hi: 'महिला', kn: 'ಮಹಿಳೆ', te: 'మహిళ' }, val: 'female', icon: '👩' },
                        { label: { en: 'Male', hi: 'पुरुष', kn: 'ಪುರುಷ', te: 'పురుషుడు' }, val: 'male', icon: '👨' },
                        { label: { en: 'Other', hi: 'अन्य', kn: 'ಇತರೆ', te: 'ఇతర' }, val: 'other', icon: '🧑' },
                      ].map((g) => (
                        <button
                          key={g.val}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer({ gender: g.val as any })}
                          className={`p-3.5 rounded-2xl text-center border transition-all active:scale-95 ${
                            guidedAnswers.gender === g.val
                              ? 'bg-forest text-white border-forest shadow-xs'
                              : 'bg-canvas text-ink border-sand hover:border-forest/50'
                          }`}
                        >
                          <span className="text-xl block mb-1">{g.icon}</span>
                          <span className="font-bold text-xs">{g.label[language] || g.label.en}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* QUESTION 3: Primary Occupation */}
                {guidedStep === 3 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'आपका मुख्य व्यवसाय या आजीविका का साधन क्या है?'
                            : language === 'kn'
                            ? 'ನಿಮ್ಮ ಮುಖ್ಯ ಉದ್ಯೋಗ ಅಥವಾ ಜೀವನೋಪಾಯ ಯಾವುದು?'
                            : language === 'te'
                            ? 'మీ ప్రధాన వృత్తి లేదా జీవనోపాధి ఏమిటి?'
                            : 'What is your primary occupation or livelihood?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'सरकारी योजनाएं किसानों, वेंडरों, कारीगरों व श्रमिकों के अनुसार तय होती हैं।'
                            : language === 'kn'
                            ? 'ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ರೈತರು, ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿಗಳು, ಕುಶಲಕರ್ಮಿಗಳು ಮತ್ತು ಕಾರ್ಮಿಕರಿಗೆ ತಕ್ಕಂತೆ ಇರುತ್ತವೆ.'
                            : language === 'te'
                            ? 'ప్రభుత్వ పథకాలు రైతులు, వీధి వ్యాపారులు, కళాకారులు మరియు శ్రామికుల కోసం ప్రత్యేకంగా ఉంటాయి.'
                            : 'Schemes are customized for farmers, street vendors, artisans, and workers.'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {[
                        { label: { en: 'Farmer / Agriculture', hi: 'किसान / कृषि', kn: 'ರೈತ / ಕೃಷಿ', te: 'రైతు / వ్యవసాయం' }, val: 'Farmer', icon: '🌾' },
                        { label: { en: 'Street Vendor / Hawkers', hi: 'रेहड़ी-पटरी वेंडर / फेरीवाले', kn: 'ಬೀದಿಬದಿ ವ್ಯಾಪಾರಿ', te: 'వీధి వ్యాపారి / హాకర్' }, val: 'Street Vendor', icon: '🛒' },
                        { label: { en: 'Daily Wage / Construction Worker', hi: 'दैनिक मजदूर / निर्माण श्रमिक', kn: 'ದೈನಂದಿನ ಕೂಲಿ / ಕಟ್ಟಡ ಕಾರ್ಮಿಕ', te: 'రోజువారీ కూలీ / నిర్మాణ కార్మికుడు' }, val: 'Daily Wage Worker', icon: '🔨' },
                        { label: { en: 'Artisan / Traditional Craft', hi: 'कारीगर / पारंपरिक शिल्पकार', kn: 'ಕುಶಲಕರ್ಮಿ / ಕರಕುಶಲ', te: 'చేతివృత్తుల కళాకారుడు' }, val: 'Artisan', icon: '🧵' },
                        { label: { en: 'Student / Looking for Work', hi: 'छात्र / रोजगार की तलाश में', kn: 'ವಿದ್ಯಾರ್ಥಿ / ಉದ್ಯೋಗಾಕಾಂಕ್ಷಿ', te: 'విద్యార్థి / ఉద్యోగార్ధి' }, val: 'Student', icon: '🎓' },
                        { label: { en: 'Homemaker / Other Worker', hi: 'गृहिणी / अन्य कामगार', kn: 'ಗೃಹಿಣಿ / ಇತರೆ ಕೆಲಸಗಾರ', te: 'గృహిణి / ఇతర శ్రామికుడు' }, val: 'Homemaker', icon: '🏠' },
                      ].map((occ) => (
                        <button
                          key={occ.val}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer({ occupation: occ.val })}
                          className={`p-3.5 rounded-2xl text-left border flex items-center gap-3 transition-all active:scale-95 ${
                            guidedAnswers.occupation === occ.val
                              ? 'bg-forest text-white border-forest shadow-xs'
                              : 'bg-canvas text-ink border-sand hover:border-forest/50'
                          }`}
                        >
                          <span className="text-xl flex-shrink-0">{occ.icon}</span>
                          <span className="font-bold text-xs">{occ.label[language] || occ.label.en}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* QUESTION 4: Details based on Occupation */}
                {guidedStep === 4 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {String(guidedAnswers.occupation).toLowerCase().includes('farmer')
                            ? (language === 'hi'
                                ? 'क्या आपके पास कृषि योग्य भूमि है या आप बटाईदार/पट्टेदार किसान हैं?'
                                : language === 'kn'
                                ? 'ನಿಮ್ಮ ಬಳಿ ಕೃಷಿ ಭೂಮಿ ಇದೆಯೇ ಅಥವಾ ನೀವು ಗೇಣಿದಾರ ರೈತರೇ?'
                                : language === 'te'
                                ? 'మీకు వ్యవసాయ భూమి ఉందా లేదా మీరు కౌలు రైతుగా సాగు చేస్తున్నారా?'
                                : 'Do you own cultivable agricultural land or cultivate as a tenant?')
                            : (language === 'hi'
                                ? 'क्या आप शहरी क्षेत्र में रेहड़ी, पटरी या ठेला लगाते हैं?'
                                : language === 'kn'
                                ? 'ನೀವು ನಗರ ಪ್ರದೇಶದಲ್ಲಿ ಬೀದಿ ವ್ಯಾಪಾರ ಅಥವಾ ತಳ್ಳುಬಂಡಿ ವ್ಯಾಪಾರ ಮಾಡುತ್ತೀರಾ?'
                                : language === 'te'
                                ? 'మీరు పట్టణ ప్రాంతంలో వీధి వ్యాపారం లేదా మొబైల్ బండి నిర్వహిస్తున్నారా?'
                                : 'Do you operate a street vending stall or mobile cart?')}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'पीएम-किसान, केसीसी अथवा पीएम-स्वनिधि के विशिष्ट पात्रता नियमों के लिए आवश्यक।'
                            : language === 'kn'
                            ? 'ಪಿಎಂ-ಕಿಸಾನ್, ಕೆಸಿಸಿ ಅಥವಾ ಪಿಎಂ-ಸ್ವನಿಧಿ ಅರ್ಹತಾ ನಿಯಮಗಳಿಗೆ ಅಗತ್ಯ.'
                            : language === 'te'
                            ? 'పీఎం-కిసాన్, కేసీసీ లేదా పీఎం-స్వనిధి అర్హత నిబంధనల కొరకు అవసరం.'
                            : 'Required for PM-KISAN, KCC, or PM-SVANidhi specific criteria.'}
                        </p>
                      </div>
                    </div>

                    {String(guidedAnswers.occupation).toLowerCase().includes('farmer') ? (
                      <div className="grid grid-cols-1 gap-2.5">
                        {[
                          {
                            label: {
                              en: 'Landowning Farmer (Under 2 Hectares / 5 Acres)',
                              hi: 'भूमि मालिक किसान (2 हेक्टेयर / 5 एकड़ से कम)',
                              kn: 'ಸಣ್ಣ ರೈತ (2 ಹೆಕ್ಟೇರ್ / 5 ಎಕರೆಗಿಂತ ಕಡಿಮೆ)',
                              te: 'చిన్న రైతు (2 హెక్టార్లు / 5 ఎకరాల లోపు)',
                            },
                            updates: { landholding: 'under_2_hectares', ownsAgriculturalLand: true },
                          },
                          {
                            label: {
                              en: 'Large Landowner (Over 2 Hectares / 5 Acres)',
                              hi: 'बड़े भूमि मालिक (2 हेक्टेयर / 5 एकड़ से अधिक)',
                              kn: 'ದೊಡ್ಡ ಭೂಮಾಲೀಕ (2 ಹೆಕ್ಟೇರ್ / 5 ಎಕರೆಗಿಂತ ಹೆಚ್ಚು)',
                              te: 'పెద్ద రైతు (2 హెక్టార్లు / 5 ఎకరాలకు పైగా)',
                            },
                            updates: { landholding: 'over_2_hectares', ownsAgriculturalLand: true },
                          },
                          {
                            label: {
                              en: 'Tenant / Sharecropper Farmer (No owned land)',
                              hi: 'पट्टेदार / बटाईदार किसान (कोई स्वयं की भूमि नहीं)',
                              kn: 'ಗೇಣಿದಾರ / ಪಾಲುದಾರ ರೈತ (ಸ್ವಂತ ಭೂಮಿ ಇಲ್ಲ)',
                              te: 'ಕೌಲು రైతు / వాటా రైతు (సొంత భూమి లేదు)',
                            },
                            updates: { isTenantFarmer: true, ownsAgriculturalLand: false },
                          },
                          {
                            label: {
                              en: 'Allied Agriculture (Dairy, Poultry, Fisheries)',
                              hi: 'संबद्ध कृषि (डेयरी, पशुपालन, मत्स्य पालन)',
                              kn: 'ಕೃಷಿ ಪೂರಕ ಚಟುವಟಿಕೆ (ಡೈರಿ, ಕೋಳಿ ಸಾಕಣೆ, ಮೀನುಗಾರಿಕೆ)',
                              te: 'అనుబంధ వ్యవసాయం (డైరీ, పౌల్ట్రీ, మత్స్య రంగం)',
                            },
                            updates: { isAlliedActivityWorker: true },
                          },
                        ].map((opt, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleSelectGuidedAnswer(opt.updates)}
                            className="p-3.5 rounded-2xl text-left bg-canvas border border-sand hover:border-forest/50 font-bold text-xs text-ink active:scale-95 transition-all"
                          >
                            {opt.label[language] || opt.label.en}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-2.5">
                        {[
                          {
                            label: {
                              en: 'Yes, Urban Vendor with Certificate / ID',
                              hi: 'हाँ, प्रमाण पत्र / पहचान पत्र के साथ शहरी वेंडर',
                              kn: 'ಹೌದು, ಪ್ರಮಾಣಪತ್ರ / ಗುರುತಿನ ಚೀಟಿ ಹೊಂದಿರುವ ವ್ಯಾಪಾರಿ',
                              te: 'అవును, సర్టిఫికేట్ / ఐడీ ఉన్న పట్టణ వ్యాపారి',
                            },
                            updates: { isStreetVendor: true },
                          },
                          {
                            label: {
                              en: 'Yes, Urban Vendor without Certificate yet',
                              hi: 'हाँ, शहरी वेंडर (अभी प्रमाण पत्र नहीं है)',
                              kn: 'ಹೌದು, ಇನ್ನೂ ಪ್ರಮಾಣಪತ್ರ ಪಡೆಯದ ನಗರ ವ್ಯಾಪಾರಿ',
                              te: 'అవును, ఇంకా సర్టిఫికేట్ లేని పట్టణ వ్యాపారి',
                            },
                            updates: { isStreetVendor: true },
                          },
                          {
                            label: {
                              en: 'No, other commercial activity',
                              hi: 'नहीं, अन्य व्यावसायिक गतिविधि',
                              kn: 'ಇಲ್ಲ, ಇತರೆ ವ್ಯಾಪಾರ ಚಟುವಟಿಕೆ',
                              te: 'కాదు, ఇతర వాణిజ్య కార్యకలాపాలు',
                            },
                            updates: { isStreetVendor: false },
                          },
                        ].map((opt, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleSelectGuidedAnswer(opt.updates)}
                            className="p-3.5 rounded-2xl text-left bg-canvas border border-sand hover:border-forest/50 font-bold text-xs text-ink active:scale-95 transition-all"
                          >
                            {opt.label[language] || opt.label.en}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* QUESTION 5: Income */}
                {guidedStep === 5 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'आपकी अनुमानित वार्षिक पारिवारिक आय कितनी है?'
                            : language === 'kn'
                            ? 'ನಿಮ್ಮ ಕುಟುಂಬದ ಅಂದಾಜು ವಾರ್ಷಿಕ ಆದಾಯ ಎಷ್ಟು?'
                            : language === 'te'
                            ? 'మీ కుటుంబ వార్షిక ఆదాయం సుమారు ఎంత?'
                            : 'What is your estimated annual family income?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'कई योजनाएं कम आय वाले परिवारों और बीपीएल कार्डधारकों के लिए हैं।'
                            : language === 'kn'
                            ? 'ಅನೇಕ ಯೋಜನೆಗಳು ಕಡಿಮೆ ಆದಾಯದ ಕುಟುಂಬಗಳು ಮತ್ತು ಬಿಪಿಎಲ್ ಕಾರ್ಡ್‌ದಾರರಿಗೆ ಮೀಸಲಾಗಿವೆ.'
                            : language === 'te'
                            ? 'చాలా పథకాలు తక్కువ ఆదాయం ఉన్న కుటుంబాలు మరియు బిపిఎల్ కార్డుదారుల కోసం ఉద్దేశించబడ్డాయి.'
                            : 'Many schemes are targeted towards low-income households and BPL cardholders.'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {[
                        {
                          label: {
                            en: 'Below ₹1 Lakh (BPL / Antyodaya)',
                            hi: '₹1 लाख से कम (बीपीएल / अंत्योदय)',
                            kn: '₹1 ಲಕ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ (ಬಿಪಿಎಲ್ / ಅಂತ್ಯೋದಯ)',
                            te: '₹1 లక్ష కంటే తక్కువ (బిపిఎల్ / అంత్యోదయ)',
                          },
                          val: 'under_100000',
                          hasBpl: true,
                        },
                        {
                          label: {
                            en: '₹1,00,000 - ₹2,50,000 (Low Income)',
                            hi: '₹1,00,000 - ₹2,50,000 (कम आय वर्ग)',
                            kn: '₹1,00,000 - ₹2,50,000 (ಕಡಿಮೆ ಆದಾಯ)',
                            te: '₹1,00,000 - ₹2,50,000 (తక్కువ ఆదాయం)',
                          },
                          val: '100000_250000',
                          hasBpl: false,
                        },
                        {
                          label: {
                            en: '₹2,50,000 - ₹5,00,000 (Middle Income)',
                            hi: '₹2,50,000 - ₹5,00,000 (मध्यम आय वर्ग)',
                            kn: '₹2,50,000 - ₹5,00,000 (ಮಧ್ಯಮ ಆದಾಯ)',
                            te: '₹2,50,000 - ₹5,00,000 (మధ్యతరగతి ఆదాయం)',
                          },
                          val: '250000_500000',
                          hasBpl: false,
                        },
                        {
                          label: {
                            en: 'Above ₹5,00,000',
                            hi: '₹5,00,000 से अधिक',
                            kn: '₹5,00,000 ಕ್ಕಿಂತ ಹೆಚ್ಚು',
                            te: '₹5,00,000 కంటే ఎక్కువ',
                          },
                          val: 'above_500000',
                          hasBpl: false,
                        },
                      ].map((inc) => (
                        <button
                          key={inc.val}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer({ incomeRange: inc.val, hasBplCard: inc.hasBpl })}
                          className={`p-3.5 rounded-2xl text-left border font-bold text-xs transition-all active:scale-95 ${
                            guidedAnswers.incomeRange === inc.val
                              ? 'bg-forest text-white border-forest shadow-xs'
                              : 'bg-canvas text-ink border-sand hover:border-forest/50'
                          }`}
                        >
                          {inc.label[language] || inc.label.en}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* QUESTION 6: Social Category & Benchmark Disability (PwD) */}
                {guidedStep === 6 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'आपकी सामाजिक श्रेणी और दिव्यांगता की स्थिति क्या है?'
                            : language === 'kn'
                            ? 'ನಿಮ್ಮ ಸಾಮಾಜಿಕ ವರ್ಗ ಮತ್ತು ಅಂಗವಿಕಲತೆಯ ವಿವರ ತಿಳಿಸಿ.'
                            : language === 'te'
                            ? 'మీ సామాజిక వర్గం మరియు దివ్యాంగుల వివరాలను తెలపండి.'
                            : 'What is your social category and disability status?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'आरक्षण-आधारित अनुदान, स्टैंड-अप इंडिया, छात्रवृत्ति और दिव्यांग पेंशन के लिए आवश्यक।'
                            : language === 'kn'
                            ? 'ಮೀಸಲಾತಿ ಆಧಾರಿತ ಅನುದಾನ, ಸ್ಟ್ಯಾಂಡ್-ಅಪ್ ಇಂಡಿಯಾ, ವಿದ್ಯಾರ್ಥಿವೇತನ ಮತ್ತು ವಿಶೇಷ ಚೇತನರ ಪಿಂಚಣಿಗಾಗಿ ಅಗತ್ಯ.'
                            : language === 'te'
                            ? 'రిజర్వేషన్ ఆధారిత రాయితీలు, స్టాండ్-అప్ ఇండియా, పోస్ట్-మెట్రిక్ స్కాలర్‌షిప్‌లు మరియు వికలాంగుల పెన్షన్ల కోసం అవసరం.'
                            : 'Required for affirmative subsidies, Stand-Up India, Post-Matric scholarships, and disability pensions.'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {[
                        {
                          label: {
                            en: 'General / Open Category',
                            hi: 'सामान्य वर्ग (General)',
                            kn: 'ಸಾಮಾನ್ಯ ವರ್ಗ (General)',
                            te: 'జనరల్ కేటగిరీ (General)',
                          },
                          updates: { socialCategory: 'General', isDifferentlyAbled: false },
                        },
                        {
                          label: {
                            en: 'OBC (Other Backward Classes)',
                            hi: 'अन्य पिछड़ा वर्ग (OBC)',
                            kn: 'ಇತರೆ ಹಿಂದುಳಿದ ವರ್ಗಗಳು (OBC)',
                            te: 'ఇతర వెనుకబడిన తరగతులు (OBC)',
                          },
                          updates: { socialCategory: 'OBC', isDifferentlyAbled: false },
                        },
                        {
                          label: {
                            en: 'SC (Scheduled Caste)',
                            hi: 'अनुसूचित जाति (SC)',
                            kn: 'ಪರಿಶಿಷ್ಟ ಜಾತಿ (SC)',
                            te: 'షెడ్యూల్డ్ కులాలు (SC)',
                          },
                          updates: { socialCategory: 'SC', isDifferentlyAbled: false },
                        },
                        {
                          label: {
                            en: 'ST (Scheduled Tribe)',
                            hi: 'अनुसूचित जनजाति (ST)',
                            kn: 'ಪರಿಶಿಷ್ಟ ಪಂಗಡ (ST)',
                            te: 'షెడ್ಯೂಲ್ಡ್ తెగలు (ST)',
                          },
                          updates: { socialCategory: 'ST', isDifferentlyAbled: false },
                        },
                        {
                          label: {
                            en: 'Person with Benchmark Disability (PwD / Divyangjan)',
                            hi: 'दिव्यांगजन (दिव्यांगता / PwD)',
                            kn: 'ವಿಶೇಷ ಚೇತನರು (PwD / ದಿವ್ಯಾಂಗ)',
                            te: 'దివ్యాంగులు (PwD / వికలాంగులు)',
                          },
                          updates: { isDifferentlyAbled: true },
                        },
                        {
                          label: {
                            en: 'Prefer not to state / Skip',
                            hi: 'बताना नहीं चाहते / छोड़ें',
                            kn: 'ತಿಳಿಸಲು ಇಚ್ಛಿಸುವುದಿಲ್ಲ / ಬಿಟ್ಟುಬಿಡಿ',
                            te: 'పేర్కొనడానికి ఇష్టపడటం లేదు / దాటవేయి',
                          },
                          updates: { socialCategory: 'General', isDifferentlyAbled: false },
                        },
                      ].map((opt, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer(opt.updates)}
                          className={`p-3.5 rounded-2xl text-left border font-bold text-xs transition-all active:scale-95 ${
                            guidedAnswers.socialCategory === opt.updates.socialCategory || (opt.updates.isDifferentlyAbled && guidedAnswers.isDifferentlyAbled)
                              ? 'bg-forest text-white border-forest shadow-xs'
                              : 'bg-canvas text-ink border-sand hover:border-forest/50'
                          }`}
                        >
                          {opt.label[language] || opt.label.en}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* QUESTION 7: Housing & Active Bank Passbook for DBT */}
                {guidedStep === 7 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'क्या आपके पास पक्का मकान है, और क्या डीबीटी हेतु बैंक खाता व पासबुक है?'
                            : language === 'kn'
                            ? 'ನಿಮ್ಮ ಬಳಿ ಪಕ್ಕಾ ಮನೆ ಇದೆಯೇ ಮತ್ತು ಡಿಬಿಟಿಗಾಗಿ ಬ್ಯಾಂಕ್ ಖಾತೆ/ಪಾಸ್‌ಬುಕ್ ಇದೆಯೇ?'
                            : language === 'te'
                            ? 'మీకు పక్కా ఇల్లు ఉందా మరియు డిబిటి కోసం బ్యాంకు ఖాతా/పాస్‌బుక్ ఉందా?'
                            : 'Do you own a pucca (permanent) house, and do you have an active bank account with passbook?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'पीएमएवाई आवास पात्रता हेतु पक्का मकान का अभाव जरूरी है। डीबीटी सब्सिडी के लिए बैंक खाता अनिवार्य है।'
                            : language === 'kn'
                            ? 'PMAY ವಸತಿ ಅರ್ಹತೆಗೆ ಪಕ್ಕಾ ಮನೆ ಇಲ್ಲದಿರುವುದು ಅಗತ್ಯ. ನೇರ ನಗದು ವರ್ಗಾವಣೆ (DBT) ಗೆ ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ಕಡ್ಡಾಯ.'
                            : language === 'te'
                            ? 'PMAY గృహ అర్హతకు పక్కా ఇల్లు లేకపోవడం ముఖ్యం. ప్రత్యక్ష ప్రయోజన బదిలీ (DBT) కోసం బ్యాంకు ఖాతా తప్పనిసరి.'
                            : 'Pucca house status determines PMAY housing eligibility. An active bank passbook enables direct benefit transfer (DBT).'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-2.5">
                      {[
                        {
                          label: {
                            en: 'Have Bank Passbook & No Pucca House (Eligible for PMAY housing & DBT benefits)',
                            hi: 'बैंक पासबुक है और पक्का मकान नहीं है (पीएमएवाई आवास और डीबीटी लाभ के पात्र)',
                            kn: 'ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ಇದೆ ಮತ್ತು ಪಕ್ಕಾ ಮನೆ ಇಲ್ಲ (PMAY ವಸತಿ ಮತ್ತು DBT ಸೌಲಭ್ಯಗಳಿಗೆ ಅರ್ಹ)',
                            te: 'బ్యాంకు పాస్‌బుక్ ఉంది మరియు పక్కా ఇల్లు లేదు (PMAY గృహ మరియు DBT ప్రయోజనాలకు అర్హులు)',
                          },
                          updates: { ownsPuccaHouse: false, hasSavingsAccount: true },
                        },
                        {
                          label: {
                            en: 'Have Bank Passbook & Own Pucca House',
                            hi: 'बैंक पासबुक है और स्वयं का पक्का मकान है',
                            kn: 'ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ಇದೆ ಮತ್ತು ಸ್ವಂತ ಪಕ್ಕಾ ಮನೆ ಇದೆ',
                            te: 'బ్యాంకు పాస్‌బుక్ ఉంది మరియు సొంత పక్కా ఇల్లు ఉంది',
                          },
                          updates: { ownsPuccaHouse: true, hasSavingsAccount: true },
                        },
                        {
                          label: {
                            en: 'No Bank Passbook yet & No Pucca House (Need Jan Dhan zero-balance account)',
                            hi: 'अभी बैंक पासबुक नहीं है और पक्का मकान नहीं है (जन धन खाते की आवश्यकता)',
                            kn: 'ಇನ್ನೂ ಬ್ಯಾಂಕ್ ಪಾಸ್‌ಬುಕ್ ಇಲ್ಲ ಮತ್ತು ಪಕ್ಕಾ ಮನೆ ಇಲ್ಲ (ಜನ್ ಧನ್ ಖಾತೆಯ ಅಗತ್ಯವಿದೆ)',
                            te: 'ఇంకా బ్యాంకు పాస్‌బుక్ లేదు మరియు పక్కా ఇల్లు లేదు (జన్ ధన్ ఖాతా అవసరం)',
                          },
                          updates: { ownsPuccaHouse: false, hasSavingsAccount: false },
                        },
                        {
                          label: {
                            en: 'No Pucca House (Living in Kutcha / Thatched / Semi-Pucca dwelling)',
                            hi: 'पक्का मकान नहीं है (कच्चे / घास-फूस के मकान में रहते हैं)',
                            kn: 'ಪಕ್ಕಾ ಮನೆ ಇಲ್ಲ (ಕಚ್ಚಾ / ಗುಡಿಸಲು ಮನೆಯಲ್ಲಿ ವಾಸ)',
                            te: 'పక్కా ఇల్లు లేదు (కచ్చా / పూరి గుడిసెలో నివాసం)',
                          },
                          updates: { ownsPuccaHouse: false },
                        },
                      ].map((opt, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer(opt.updates)}
                          className="p-3.5 rounded-2xl text-left bg-canvas border border-sand hover:border-forest/50 font-bold text-xs text-ink active:scale-95 transition-all"
                        >
                          {opt.label[language] || opt.label.en}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* QUESTION 8: Statutory Exclusions (Tax & Govt Job) */}
                {guidedStep === 8 && (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h2 className="font-heading font-bold text-lg text-ink">
                          {language === 'hi'
                            ? 'क्या आप आयकर देते हैं या नियमित स्थायी सरकारी नौकरी करते हैं?'
                            : language === 'kn'
                            ? 'ನೀವು ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸುತ್ತೀರಾ ಅಥವಾ ಕಾಯಂ ಸರ್ಕಾರಿ ಉದ್ಯೋಗ ಹೊಂದಿದ್ದೀರಾ?'
                            : language === 'te'
                            ? 'మీరు ఆదాయపు పన్ను చెల్లిస్తున్నారా లేదా శాశ్వత ప్రభుత్వ ఉద్యోగం ఉందా?'
                            : 'Do you pay income tax or hold a permanent government job?'}
                        </h2>
                        <p className="text-xs text-ink/65 mt-1">
                          {language === 'hi'
                            ? 'आयकर दाता और सरकारी कर्मचारी कई केंद्रीय कल्याणकारी योजनाओं से वैधानिक रूप से अपात्र हैं।'
                            : language === 'kn'
                            ? 'ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿದಾರರು ಮತ್ತು ಕಾಯಂ ಸರ್ಕಾರಿ ನೌಕರರನ್ನು ಹಲವು ಯೋಜನೆಗಳಿಂದ ಶಾಸನಬದ್ಧವಾಗಿ ಹೊರಗಿಡಲಾಗುತ್ತದೆ.'
                            : language === 'te'
                            ? 'ఆదాయపు పన్ను చెల్లింపుదారులు మరియు శాశ్వత ప్రభుత్వ ఉద్యోగులు అనేక సంక్షేమ పథకాల నుండి చట్టబద్ధంగా మినహాయించబడ్డారు.'
                            : 'Income tax payers and permanent government employees are statutorily excluded from several welfare schemes.'}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-2.5">
                      {[
                        {
                          label: {
                            en: 'No, neither (Eligible for welfare benefits)',
                            hi: 'नहीं, दोनों में से कोई नहीं (कल्याणकारी लाभों के पात्र)',
                            kn: 'ಇಲ್ಲ, ಎರಡೂ ಇಲ್ಲ (ಕಲ್ಯಾಣ ಸೌಲಭ್ಯಗಳಿಗೆ ಅರ್ಹ)',
                            te: 'లేదు, రెండూ కావు (సంక్షేమ ప్రయోజనాలకు అర్హులు)',
                          },
                          updates: { paysIncomeTax: false, hasRegularGovtJob: false },
                        },
                        {
                          label: {
                            en: 'Yes, pay income tax in the last assessment year',
                            hi: 'हाँ, पिछले वर्ष में आयकर का भुगतान किया है',
                            kn: 'ಹೌದು, ಕಳೆದ ವರ್ಷದಲ್ಲಿ ಆದಾಯ ತೆರಿಗೆ ಪಾವತಿಸಲಾಗಿದೆ',
                            te: 'అవును, గత అసెస్‌మెంట్ సంవత్సరంలో ఆదాయపు పన్ను చెల్లించారు',
                          },
                          updates: { paysIncomeTax: true, hasRegularGovtJob: false },
                        },
                        {
                          label: {
                            en: 'Yes, permanent regular government / PSU employee',
                            hi: 'हाँ, स्थायी नियमित सरकारी / पीएसयू कर्मचारी',
                            kn: 'ಹೌದು, ಕಾಯಂ ನಿಯಮಿತ ಸರ್ಕಾರಿ / ಪಿಎಸ್‌ಯು ನೌಕರ',
                            te: 'అవును, శాశ్వత రెగ్యులర్ ప్రభుత్వ / పిఎస్‌యు ఉద్యోగి',
                          },
                          updates: { paysIncomeTax: false, hasRegularGovtJob: true },
                        },
                      ].map((opt, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectGuidedAnswer(opt.updates)}
                          className="p-3.5 rounded-2xl text-left bg-canvas border border-sand hover:border-forest/50 font-bold text-xs text-ink active:scale-95 transition-all"
                        >
                          {opt.label[language] || opt.label.en}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Question Navigation Controls: Back & Skip */}
                <div className="flex items-center justify-between pt-3 border-t border-sand/40 text-xs">
                  {guidedStep > 0 ? (
                    <button
                      type="button"
                      onClick={handleBackGuidedQuestion}
                      className="inline-flex items-center gap-1 font-bold text-ink/70 hover:text-forest transition-colors py-1 px-2.5 rounded-lg hover:bg-sand/30"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>{t('guidedBack', language)}</span>
                    </button>
                  ) : <div />}

                  <button
                    type="button"
                    onClick={handleSkipGuidedQuestion}
                    className="font-semibold text-ink/50 hover:text-ink underline py-1 px-2.5"
                  >
                    {t('guidedSkip', language)}
                  </button>
                </div>
              </div>
            ) : (
              /* ============================================================== */
              /* EVALUATED SCHEMES RESULTS VIEW                                 */
              /* ============================================================== */
              <div className="space-y-4 animate-in fade-in">
                {/* Completion Header Banner */}
                <div className="bg-gradient-to-br from-emerald-800 to-forest rounded-3xl text-white p-5 shadow-lg space-y-2">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-xs font-bold text-emerald-100">
                    <CheckCircle2 className="w-3.5 h-3.5 text-amber-300" />
                    <span>{t('guidedResultsTitle', language)}</span>
                  </div>
                  <h2 className="font-heading font-extrabold text-xl text-white">
                    {guidedMatchedSchemes.length > 0
                      ? (language === 'hi'
                          ? `आपके लिए ${guidedMatchedSchemes.length} सरकारी योजनाएं मिलीं`
                          : language === 'kn'
                          ? `ನಿಮಗಾಗಿ ${guidedMatchedSchemes.length} ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ದೊರೆತಿವೆ`
                          : language === 'te'
                          ? `మీ కోసం ${guidedMatchedSchemes.length} ప్రభుత్వ పథకాలు కనుగొనబడ్డాయి`
                          : `Found ${guidedMatchedSchemes.length} Government Schemes for You`)
                      : (language === 'hi'
                          ? 'कोई सटीक योजना मेल नहीं खाई'
                          : language === 'kn'
                          ? 'ಯಾವುದೇ ನಿಖರವಾದ ಯೋಜನೆ ಹೊಂದಾಣಿಕೆಯಾಗಿಲ್ಲ'
                          : language === 'te'
                          ? 'ఖచ్చితమైన సరిపోలే పథకాలు ఏవీ కనుగొనబడలేదు'
                          : 'No Exact Scheme Matches Found')}
                  </h2>
                  <p className="text-xs text-emerald-100/90 leading-relaxed">
                    {t('guidedResultsSubtitle', language)}
                  </p>
                </div>

                {/* Statutory Authority Disclaimer Alert */}
                <div className="bg-amber-50 border border-amber-300 rounded-2xl p-3.5 flex items-start gap-2.5 shadow-xs text-xs text-amber-950">
                  <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
                  <p className="leading-relaxed">
                    {t('guidedAuthorityDisclaimer', language)}
                  </p>
                </div>

                {/* Scheme Result Cards */}
                <div className="space-y-3">
                  {guidedMatchedSchemes.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => navigate(`/scheme/${s.id}`)}
                      className="bg-surface rounded-2xl border border-sand shadow-card hover:shadow-card-hover p-4 cursor-pointer transition-all space-y-2.5 group"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[10px] font-bold text-ink/60 uppercase tracking-wider block">
                            {s.ministry}
                          </span>
                          <h3 className="font-heading font-bold text-base text-ink group-hover:text-forest transition-colors">
                            {s.name}
                          </h3>
                          {s.nativeName && s.nativeName !== s.name && (
                            <p className="text-xs text-ink/60 font-medium">{s.nativeName}</p>
                          )}
                        </div>
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${
                            s.status === 'eligible'
                              ? 'bg-green-100 text-green-800 border-green-300'
                              : 'bg-amber-100 text-amber-800 border-amber-300'
                          }`}
                        >
                          {s.status === 'eligible' ? 'ELIGIBLE' : 'POSSIBLY ELIGIBLE'}
                        </span>
                      </div>

                      {/* Who it is for */}
                      <div className="flex items-start gap-1.5 text-xs text-ink/80 bg-neutral-canvas/60 p-2 rounded-lg border border-sand/40">
                        <Users className="w-3.5 h-3.5 text-forest flex-shrink-0 mt-0.5" />
                        <span className="leading-snug">{s.description}</span>
                      </div>

                      {/* Key Financial Benefit */}
                      <div className="bg-sage/40 rounded-xl p-2.5 border border-sage/60 space-y-1">
                        <span className="text-[11px] font-bold text-forest uppercase tracking-wide flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-forest" />
                          {t('keyFinancialBenefitHeading', language)}:
                        </span>
                        <p className="text-xs font-bold text-forest-deep leading-relaxed">
                          {s.benefitHighlight}
                        </p>
                      </div>

                      {/* Why matched */}
                      <div className="text-xs text-status-green flex items-center gap-1.5 pt-1 border-t border-sand/40">
                        <Check className="w-3.5 h-3.5 flex-shrink-0" />
                        <span className="font-medium">{s.matchReason}</span>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center justify-between pt-2 border-t border-sand/40 text-xs font-semibold">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/checklist/${s.id}`);
                          }}
                          className="text-ink/70 hover:text-forest flex items-center gap-1"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>Documents & Apply</span>
                        </button>
                        <div className="flex items-center gap-1 text-forest font-bold group-hover:translate-x-0.5 transition-transform">
                          <span>{t('viewDetails', language)}</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Bottom Actions: Edit Answers or Ask AI Chat */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsGuidedComplete(false);
                      setGuidedStep(0);
                    }}
                    className="px-4 py-2 rounded-xl bg-surface border border-sand text-xs font-bold text-ink hover:text-forest flex items-center gap-1.5 shadow-xs"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Edit Profile Answers</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveMode('chat')}
                    className="px-4 py-2 rounded-xl bg-forest text-white text-xs font-bold hover:bg-forest-deep flex items-center gap-1.5 shadow-xs"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Ask AI Questions About Schemes</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ============================================================== */}
        {/* MODE 2: FREEFORM CUSTOMER-SUPPORT AI CHAT                       */}
        {/* ============================================================== */}
        {activeMode === 'chat' && (
          <section className="w-full max-w-2xl space-y-4">
            {chatMessages.map((msg) => {
              const isUser = msg.sender === 'user';
              const currentLangForMsg = activeMessageLang[msg.id];
              const displayedText =
                currentLangForMsg && translations[`${msg.id}_${currentLangForMsg}`]
                  ? translations[`${msg.id}_${currentLangForMsg}`]
                  : msg.text;

              if (isUser) {
                return (
                  <div key={msg.id} className="flex justify-end items-end gap-2 animate-in fade-in">
                    <div className="bg-forest text-white rounded-2xl rounded-tr-sm p-3.5 max-w-[85%] sm:max-w-[75%] shadow-sm">
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</div>
                      <div className="flex items-center justify-end gap-1.5 text-[10px] text-white/70 mt-1">
                        {msg.isVoiceInput && (
                          <span className="inline-flex items-center gap-0.5 text-amber-200">
                            <Mic className="w-2.5 h-2.5" /> Spoken
                          </span>
                        )}
                        <span>{msg.timestamp}</span>
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <div key={msg.id} className="flex flex-col items-start gap-2 animate-in fade-in">
                  <div className="flex items-start gap-3 w-full max-w-[95%] sm:max-w-[85%]">
                    <div className="w-8 h-8 rounded-full bg-forest text-white flex items-center justify-center flex-shrink-0 shadow-xs mt-1">
                      <Bot className="w-4 h-4" />
                    </div>

                    <div className="bg-surface rounded-2xl rounded-tl-sm p-4 border border-sand shadow-sm space-y-3 flex-1">
                      {/* Message Header: Title, Translate dropdown, Audio button */}
                      <div className="flex items-center justify-between gap-2 border-b border-sand/50 pb-2">
                        <span className="font-heading font-bold text-xs text-forest">
                          {t('aiLabel', language)}
                        </span>
                        <div className="flex items-center gap-2">
                          {/* Translate Button & Popover */}
                          <div className="relative">
                            <button
                              type="button"
                              onClick={() =>
                                setOpenTranslateDropdownId(
                                  openTranslateDropdownId === msg.id ? null : msg.id
                                )
                              }
                              className="inline-flex items-center gap-1 text-[11px] font-semibold text-ink/70 hover:text-forest bg-sand/30 hover:bg-sand/60 px-2.5 py-1 rounded-full border border-sand transition-colors"
                            >
                              <Globe className="w-3 h-3 text-forest" />
                              <span>
                                {translatingMsgId === msg.id ? 'Translating...' : 'Translate'}
                              </span>
                            </button>

                            {openTranslateDropdownId === msg.id && (
                              <div className="absolute right-0 top-full mt-1 w-36 bg-surface rounded-xl shadow-lg border border-sand p-1.5 z-20 space-y-1">
                                {LANGUAGES.map((l) => (
                                  <button
                                    key={l.code}
                                    type="button"
                                    onClick={() =>
                                      handleTranslateMessage(msg.id, msg.text, l.code)
                                    }
                                    className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                                      currentLangForMsg === l.code
                                        ? 'bg-forest text-white font-bold'
                                        : 'hover:bg-sand/40 text-ink'
                                    }`}
                                  >
                                    {l.nativeName}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* TTS Audio Speak Button */}
                          {isTtsSupported && (
                            <button
                              type="button"
                              onClick={() => handleToggleSpeak(msg.id, displayedText)}
                              className={`inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full font-bold transition-all ${
                                isSpeaking && currentSpeakingId === msg.id
                                  ? 'bg-amber-600 text-white shadow-xs'
                                  : 'bg-sage text-forest hover:bg-sage/80'
                              }`}
                            >
                              {isSpeaking && currentSpeakingId === msg.id ? (
                                <>
                                  <VolumeX className="w-3 h-3" />
                                  <span>Stop</span>
                                </>
                              ) : (
                                <>
                                  <Volume2 className="w-3 h-3 text-forest" />
                                  <span>Listen</span>
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Genuine Translation Notice Bar */}
                      {currentLangForMsg && (
                        <div className="flex items-center justify-between text-[11px] bg-sage/30 px-2.5 py-1 rounded-lg border border-forest/20 text-forest-deep">
                          <span>
                            Translated to {LANGUAGES.find((l) => l.code === currentLangForMsg)?.nativeName}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setActiveMessageLang((prev) => ({ ...prev, [msg.id]: null }));
                            }}
                            className="font-bold underline ml-2 hover:text-forest"
                          >
                            {t('showOriginalBtn', language)}
                          </button>
                        </div>
                      )}

                      {/* If user toggled Show Original, allow toggling back to Show Translation */}
                      {!currentLangForMsg && translations[`${msg.id}_${language}`] && (
                        <div className="flex items-center justify-end text-[11px]">
                          <button
                            type="button"
                            onClick={() => {
                              setActiveMessageLang((prev) => ({ ...prev, [msg.id]: language }));
                            }}
                            className="font-bold text-forest underline hover:text-forest-deep"
                          >
                            {t('showTranslationBtn', language)}
                          </button>
                        </div>
                      )}

                      {/* Translation Unavailable Notice */}
                      {translationFailedMsgId === msg.id && (
                        <div className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 px-2.5 py-1.5 rounded-lg flex items-center justify-between">
                          <span>{t('translationUnavailableNotice', language)}</span>
                          <button
                            type="button"
                            onClick={() => setTranslationFailedMsgId(null)}
                            className="text-amber-900 font-bold ml-2"
                          >
                            ✕
                          </button>
                        </div>
                      )}

                      {/* Message Body with Markdown */}
                      <div className="text-ink text-sm sm:text-base leading-relaxed font-sans">
                        {currentLangForMsg ? (
                          <MarkdownRenderer content={displayedText} />
                        ) : (
                          <MarkdownRenderer content={msg.text} />
                        )}
                      </div>

                      {/* Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="pt-2 border-t border-sand/50 text-[11px] text-ink/60 flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-forest" />
                          <span>Verified with {msg.citations.length} official government guideline(s).</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Contextual Quick Replies */}
                  {msg.suggestedFollowups && msg.suggestedFollowups.length > 0 && (
                    <div className="pl-11 pt-1 w-full space-y-1.5">
                      <div className="flex flex-wrap gap-2">
                        {msg.suggestedFollowups.map((reply, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => handleSendMessage(reply, false)}
                            className="h-8 px-3 rounded-full border border-sand bg-surface hover:bg-forest hover:text-white hover:border-forest text-xs font-semibold text-ink shadow-xs transition-all flex items-center gap-1 active:scale-95"
                          >
                            <span>{reply}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Live Streaming Message */}
            {isSubmitting && streamingText && (
              <div className="flex items-start gap-3 w-full max-w-[95%] sm:max-w-[85%] animate-in fade-in">
                <div className="w-8 h-8 rounded-full bg-forest text-white flex items-center justify-center flex-shrink-0 shadow-xs mt-1">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-surface rounded-2xl rounded-tl-sm p-4 border border-sand shadow-sm space-y-2 flex-1">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-forest border-b border-sand/50 pb-2">
                    <span>Yojana Saathi</span>
                    <span className="text-[10px] text-ink/50 font-normal ml-auto flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-forest animate-spin" /> Synthesizing...
                    </span>
                  </div>
                  <div className="text-ink text-sm sm:text-base leading-relaxed font-sans">
                    <MarkdownRenderer content={streamingText} />
                    <span className="inline-block w-1.5 h-4 ml-1 bg-forest animate-pulse align-middle" />
                  </div>
                </div>
              </div>
            )}

            {/* Thinking indicator */}
            {isSubmitting && !streamingText && (
              <div className="flex items-center gap-3 bg-surface border border-sand rounded-2xl p-4 shadow-sm w-fit animate-in fade-in">
                <div className="w-8 h-8 rounded-full bg-sage text-forest flex items-center justify-center flex-shrink-0 animate-pulse">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="text-xs text-ink/70 flex items-center gap-2">
                  <span className="font-semibold">{t('thinkingStatus', language)}</span>
                  <span className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-forest rounded-full animate-bounce"></span>
                    <span className="w-1.5 h-1.5 bg-forest rounded-full animate-bounce [animation-delay:0.2s]"></span>
                    <span className="w-1.5 h-1.5 bg-forest rounded-full animate-bounce [animation-delay:0.4s]"></span>
                  </span>
                </div>
              </div>
            )}
          </section>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* BOTTOM INPUT BAR FALLBACK (Accessible text & voice dock) */}
      <div className="fixed bottom-16 left-0 right-0 bg-surface border-t border-sand p-3 shadow-lg z-30">
        <div className="max-w-2xl mx-auto space-y-2">
          {!isOnline && (
            <div
              role="alert"
              className="bg-amber-100 border border-amber-300 rounded-lg px-3 py-1.5 text-xs text-amber-950 flex items-center justify-between gap-2"
            >
              <div className="flex items-center gap-1.5">
                <WifiOff className="w-3.5 h-3.5 text-amber-800 flex-shrink-0" aria-hidden="true" />
                <span className="font-medium">{t('offlineChatNotice', language)}</span>
              </div>
              <button
                type="button"
                onClick={() => checkConnection()}
                className="text-[11px] font-bold text-amber-900 bg-amber-200/90 hover:bg-amber-300 px-2 py-0.5 rounded border border-amber-400 flex-shrink-0"
              >
                {t('checkConnectionAction', language)}
              </button>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleOrbClick}
              disabled={isSubmitting || !isOnline}
              aria-label={t('startVoiceCTA', language)}
              className={`h-11 px-3.5 rounded-full flex items-center justify-center gap-1.5 shadow-sm transition-all text-white font-bold text-xs ${
                isListening ? 'bg-red-700 animate-pulse' : 'bg-forest hover:bg-forest-deep'
              }`}
            >
              <Mic className="w-4 h-4" />
              <span className="hidden sm:inline">
                {isListening ? 'Stop' : language === 'hi' ? 'बोलें' : 'Speak'}
              </span>
            </button>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!inputText.trim()) return;
                if (activeMode === 'guided') {
                  handleGuidedVoiceInput(inputText);
                  setInputText('');
                } else {
                  handleSendMessage();
                }
              }}
              className="flex-1 flex items-center gap-1.5"
            >
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={isSubmitting || !isOnline}
                placeholder={
                  !isOnline
                    ? t('offlineChatNotice', language)
                    : activeMode === 'guided'
                    ? (language === 'hi' ? 'उत्तर टाइप करें या प्रश्न पूछें...' : 'Type answer or ask anything...')
                    : t('chatInputPlaceholder', language)
                }
                className="w-full bg-canvas border border-sand rounded-full px-4 py-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-forest min-h-[44px]"
              />
              <button
                type="submit"
                disabled={!inputText.trim() || isSubmitting || !isOnline}
                aria-label={t('sendAction', language)}
                className="w-11 h-11 rounded-full bg-forest hover:bg-forest-deep disabled:opacity-40 text-white flex items-center justify-center flex-shrink-0 transition-colors shadow-xs"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      <BottomNav onVoiceClick={handleBottomVoiceClick} />
    </div>
  );
};
