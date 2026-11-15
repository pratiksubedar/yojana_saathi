import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  Language,
  UserProfile,
  ChatMessage,
  AttributeSource,
  AttributeSourcesMap,
} from '../types';
import { clearSessionId, getSessionId, resetChatSession } from '../services/chatApi';

export interface LanguageSwitchRequest {
  detectedLang: Language;
  confidence: 'script_match' | 'vocabulary_match' | 'uncertain';
  sourceText?: string;
  triggerType?: 'spoken' | 'typed';
  candidates?: Language[];
  reason?: string;
}

interface AppContextType {
  language: Language;
  isManualLanguage: boolean;
  setLanguage: (lang: Language) => void;
  setDetectedLanguage: (lang: Language) => void;
  languageSwitchPrompt: LanguageSwitchRequest | null;
  requestLanguageSwitch: (req: LanguageSwitchRequest) => void;
  confirmLanguageSwitch: (targetLang?: Language) => void;
  dismissLanguageSwitch: () => void;
  userProfile: UserProfile;
  attributeSources: AttributeSourcesMap;
  hasConfirmedProfile: boolean;
  setHasConfirmedProfile: (val: boolean) => void;
  updateUserProfile: (updates: Partial<UserProfile>, source?: AttributeSource) => void;
  clearProfileAttribute: (key: keyof UserProfile) => void;
  mergeDetectedProfile: (backendProfile: Record<string, any>, force?: boolean) => void;
  savedSchemeIds: string[];
  toggleSaveScheme: (schemeId: string) => void;
  isSchemeSaved: (schemeId: string) => boolean;
  recentlyViewedSchemeIds: string[];
  recordViewedScheme: (schemeId: string) => void;
  chatMessages: ChatMessage[];
  addChatMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  clearChat: () => void;
  voiceSpeed: number;
  setVoiceSpeed: (speed: number) => void;
  autoReadAloud: boolean;
  setAutoReadAloud: (val: boolean) => void;
  largeTextMode: boolean;
  setLargeTextMode: (val: boolean) => void;
  highContrastMode: boolean;
  setHighContrastMode: (val: boolean) => void;
  resetSession: () => void;
}

// Strictly empty by default: never fabricate citizen attributes
const DEFAULT_PROFILE: UserProfile = {};

export const getWelcomeMessage = (lang: Language): ChatMessage => {
  const texts: Record<Language, string> = {
    en: 'Hello! I am Yojana Saathi. I can help you discover government schemes you may be eligible for. You can speak naturally or type your question.',
    hi: 'नमस्ते! मैं योजना साथी हूँ। मैं आपको उन सरकारी योजनाओं की खोज करने में मदद कर सकता हूँ जिनके लिए आप पात्र हो सकते हैं। आप बोलकर या लिखकर पूछ सकते हैं।',
    kn: 'ನಮಸ್ಕಾರ! ನಾನು ಯೋಜನೆ ಸಾಥಿ. ನೀವು ಅರ್ಹರಾಗಬಹುದಾದ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳನ್ನು ಕಂಡುಹಿಡಿಯಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ. ನೀವು ಧ್ವನಿ ಮೂಲಕ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ ಪ್ರಶ್ನೆ ಕೇಳಬಹುದು.',
    te: 'నమస్కారం! నేను యోజనా సాథి. మీరు అర్హులయ్యే ప్రభుత్వ పథకాలను కనుగొనడంలో నేను మీకు సహాయం చేయగలను. మీరు మాట్లాడి లేదా టైప్ చేసి అడగవచ్చు.',
  };

  return {
    id: 'msg-init-1',
    sender: 'assistant',
    text: texts[lang] || texts.en,
    timestamp: '11:00 AM',
    suggestedSchemeIds: ['pm-kisan', 'pm-jay', 'pmay-g'],
  };
};

const VALID_LANGUAGES: Language[] = ['en', 'hi', 'kn', 'te'];

const getInitialLanguage = (): Language => {
  try {
    const saved = localStorage.getItem('yojana_lang');
    if (saved === 'ta' || saved === 'bn') {
      localStorage.setItem('yojana_lang', 'en');
      return 'en';
    }
    if (saved && VALID_LANGUAGES.includes(saved as Language)) {
      return saved as Language;
    }
  } catch {
    // ignore
  }
  return 'en';
};

const getInitialBoolean = (key: string, fallback: boolean): boolean => {
  try {
    const val = localStorage.getItem(key);
    if (val === 'true') return true;
    if (val === 'false') return false;
  } catch {
    // ignore
  }
  return fallback;
};

const getInitialNumber = (key: string, fallback: number): number => {
  try {
    const val = localStorage.getItem(key);
    if (val !== null) {
      const parsed = parseFloat(val);
      if (!Number.isNaN(parsed)) return parsed;
    }
  } catch {
    // ignore
  }
  return fallback;
};

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage);
  const [isManualLanguage, setIsManualLanguage] = useState<boolean>(false);
  const [languageSwitchPrompt, setLanguageSwitchPrompt] = useState<LanguageSwitchRequest | null>(null);

  // Strictly in-memory citizen profile & personalized state — NEVER persisted to browser storage
  const [userProfile, setUserProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [attributeSources, setAttributeSources] = useState<AttributeSourcesMap>({});
  const [hasConfirmedProfile, setHasConfirmedProfile] = useState<boolean>(false);
  const [savedSchemeIds, setSavedSchemeIds] = useState<string[]>([]);
  const [recentlyViewedSchemeIds, setRecentlyViewedSchemeIds] = useState<string[]>([]);

  const getInitialChatMessages = (lang: Language): ChatMessage[] => {
    try {
      const raw = sessionStorage.getItem('yojana_session_chat');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch {}
    return [getWelcomeMessage(lang)];
  };

  // Chat messages stored in tab ephemeral session storage - survives page reload
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() =>
    getInitialChatMessages(getInitialLanguage())
  );

  useEffect(() => {
    try {
      if (chatMessages && chatMessages.length > 0) {
        sessionStorage.setItem('yojana_session_chat', JSON.stringify(chatMessages));
      }
    } catch {}
  }, [chatMessages]);

  // Non-PII UI/accessibility preferences
  const [voiceSpeed, setVoiceSpeedState] = useState<number>(() => getInitialNumber('yojana_voice_speed', 1.0));
  const [autoReadAloud, setAutoReadAloudState] = useState<boolean>(() => getInitialBoolean('yojana_auto_read', true));
  const [largeTextMode, setLargeTextModeState] = useState<boolean>(() => getInitialBoolean('yojana_large_text', false));
  const [highContrastMode, setHighContrastModeState] = useState<boolean>(() => getInitialBoolean('yojana_high_contrast', false));

  // Purge any legacy personal storage items on startup (preserve active session chat)
  useEffect(() => {
    try {
      localStorage.removeItem('yojana_chat');
      localStorage.removeItem('yojana_profile');
      sessionStorage.removeItem('yojana_profile');
      localStorage.removeItem('yojana_saved_schemes');
      localStorage.removeItem('yojana_locker_docs');
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem('yojana_lang', language);
    } catch {
      // ignore
    }
  }, [language]);

  // Apply real accessibility attributes to document root
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.style.fontSize = largeTextMode ? '18px' : '';
      document.documentElement.classList.toggle('high-contrast', highContrastMode);
    }
  }, [largeTextMode, highContrastMode]);

  const requestLanguageSwitch = (req: LanguageSwitchRequest) => {
    if (req.detectedLang !== language) {
      setLanguageSwitchPrompt(req);
    }
  };

  const confirmLanguageSwitch = (targetLang?: Language) => {
    const chosen = targetLang || languageSwitchPrompt?.detectedLang;
    if (chosen && VALID_LANGUAGES.includes(chosen)) {
      setLanguage(chosen);
    }
    setLanguageSwitchPrompt(null);
  };

  const dismissLanguageSwitch = () => {
    setLanguageSwitchPrompt(null);
  };

  const setLanguage = (lang: Language) => {
    setIsManualLanguage(true);
    setLanguageState(lang);
    setChatMessages((prev) =>
      prev.map((msg) => {
        if (msg.sender === 'assistant' && (msg.id === 'msg-init-1' || msg.id.startsWith('msg-init-'))) {
          return getWelcomeMessage(lang);
        }
        return msg;
      })
    );
  };

  const setDetectedLanguage = (lang: Language) => {
    if (lang && VALID_LANGUAGES.includes(lang) && lang !== language) {
      requestLanguageSwitch({
        detectedLang: lang,
        confidence: 'script_match',
        triggerType: 'spoken',
        candidates: [lang, language],
        reason: 'Detected during interaction',
      });
    }
  };

  const setVoiceSpeed = (speed: number) => {
    setVoiceSpeedState(speed);
    try {
      localStorage.setItem('yojana_voice_speed', String(speed));
    } catch {
      // ignore
    }
  };

  const setAutoReadAloud = (val: boolean) => {
    setAutoReadAloudState(val);
    try {
      localStorage.setItem('yojana_auto_read', String(val));
    } catch {
      // ignore
    }
  };

  const setLargeTextMode = (val: boolean) => {
    setLargeTextModeState(val);
    try {
      localStorage.setItem('yojana_large_text', String(val));
    } catch {
      // ignore
    }
  };

  const setHighContrastMode = (val: boolean) => {
    setHighContrastModeState(val);
    try {
      localStorage.setItem('yojana_high_contrast', String(val));
    } catch {
      // ignore
    }
  };

  const updateUserProfile = (updates: Partial<UserProfile>, source: AttributeSource = 'user') => {
    setUserProfile((prev) => {
      const next = { ...prev };
      for (const [k, v] of Object.entries(updates)) {
        const key = k as keyof UserProfile;
        if (v === undefined || v === null || (typeof v === 'string' && v.trim() === '')) {
          delete next[key];
        } else {
          (next as any)[key] = v;
        }
      }
      // Enforce consistency: if ownsAgriculturalLand is explicitly false, clear landholdingHectares
      if (next.ownsAgriculturalLand === false) {
        delete next.landholdingHectares;
      }
      return next;
    });

    setAttributeSources((prev) => {
      const next = { ...prev };
      for (const [k, v] of Object.entries(updates)) {
        const key = k as keyof UserProfile;
        if (v === undefined || v === null || (typeof v === 'string' && v.trim() === '')) {
          delete next[key];
        } else {
          next[key] = source;
        }
      }
      if (updates.ownsAgriculturalLand === false) {
        delete next.landholdingHectares;
      }
      return next;
    });
  };

  const clearProfileAttribute = (key: keyof UserProfile) => {
    setUserProfile((prev) => {
      const next = { ...prev };
      delete next[key];
      if (key === 'ownsAgriculturalLand') {
        delete next.landholdingHectares;
      }
      return next;
    });
    setAttributeSources((prev) => {
      const next = { ...prev };
      delete next[key];
      if (key === 'ownsAgriculturalLand') {
        delete next.landholdingHectares;
      }
      return next;
    });
  };

  const mergeDetectedProfile = (backendProfile: Record<string, any>, force = false) => {
    if (!backendProfile || typeof backendProfile !== 'object') return;
    const mappedUpdates: Partial<UserProfile> = {};

    if (backendProfile.age !== undefined && backendProfile.age !== null) {
      mappedUpdates.age = Number(backendProfile.age);
    }
    if (backendProfile.occupation) {
      mappedUpdates.occupation = String(backendProfile.occupation);
    }
    if (backendProfile.occupationDetail || backendProfile.occupation_detail) {
      mappedUpdates.occupationDetail = String(backendProfile.occupationDetail || backendProfile.occupation_detail);
    }
    const landHa = backendProfile.landholdingHectares ?? backendProfile.landholding_hectares;
    if (landHa !== undefined && landHa !== null) {
      mappedUpdates.landholdingHectares = Number(landHa);
      mappedUpdates.ownsAgriculturalLand = Number(landHa) > 0;
    }
    const ownsLand = backendProfile.ownsAgriculturalLand ?? backendProfile.owns_agricultural_land;
    if (ownsLand !== undefined && ownsLand !== null) {
      mappedUpdates.ownsAgriculturalLand = Boolean(ownsLand);
    }
    if (backendProfile.landholding) {
      mappedUpdates.landholding = String(backendProfile.landholding);
    }
    const inc = backendProfile.annualIncome ?? backendProfile.annual_income ?? backendProfile.annual_income_inr;
    if (inc !== undefined && inc !== null) {
      mappedUpdates.annualIncome = Number(inc);
    }
    const incRange = backendProfile.incomeRange ?? backendProfile.income_range;
    if (incRange) {
      mappedUpdates.incomeRange = String(incRange);
    }
    if (backendProfile.state) {
      mappedUpdates.state = String(backendProfile.state);
    }
    if (backendProfile.district) {
      mappedUpdates.district = String(backendProfile.district);
    }
    if (backendProfile.gender) {
      mappedUpdates.gender = String(backendProfile.gender);
    }
    const socCat = backendProfile.socialCategory ?? backendProfile.social_category;
    if (socCat) {
      mappedUpdates.socialCategory = String(socCat);
    }
    const bpl = backendProfile.hasBPLCard ?? backendProfile.hasBplCard ?? backendProfile.has_bpl_card ?? backendProfile.is_bpl;
    if (bpl !== undefined && bpl !== null) {
      mappedUpdates.hasBPLCard = Boolean(bpl);
      mappedUpdates.hasBplCard = Boolean(bpl);
    }
    const diffAbled = backendProfile.isDifferentlyAbled ?? backendProfile.is_differently_abled;
    if (diffAbled !== undefined && diffAbled !== null) {
      mappedUpdates.isDifferentlyAbled = Boolean(diffAbled);
    }
    const fType = backendProfile.farmerType ?? backendProfile.farmer_type;
    if (fType) {
      mappedUpdates.farmerType = String(fType);
    }
    const def = backendProfile.isBankDefaulter ?? backendProfile.is_bank_defaulter ?? backendProfile.has_willful_bank_default;
    if (def !== undefined && def !== null) {
      mappedUpdates.isBankDefaulter = Boolean(def);
    }
    const tenant = backendProfile.isTenantFarmer ?? backendProfile.is_tenant_farmer;
    if (tenant !== undefined && tenant !== null) {
      mappedUpdates.isTenantFarmer = Boolean(tenant);
    }
    const allied = backendProfile.isAlliedActivityWorker ?? backendProfile.is_allied_activity_worker;
    if (allied !== undefined && allied !== null) {
      mappedUpdates.isAlliedActivityWorker = Boolean(allied);
    }
    const vendor = backendProfile.isStreetVendor ?? backendProfile.is_street_vendor;
    if (vendor !== undefined && vendor !== null) {
      mappedUpdates.isStreetVendor = Boolean(vendor);
    }
    const unorg = backendProfile.isUnorganisedWorker ?? backendProfile.is_unorganised_worker;
    if (unorg !== undefined && unorg !== null) {
      mappedUpdates.isUnorganisedWorker = Boolean(unorg);
    }
    const pucca = backendProfile.ownsPuccaHouse ?? backendProfile.owns_pucca_house;
    if (pucca !== undefined && pucca !== null) {
      mappedUpdates.ownsPuccaHouse = Boolean(pucca);
    }
    const tax = backendProfile.paysIncomeTax ?? backendProfile.pays_income_tax;
    if (tax !== undefined && tax !== null) {
      mappedUpdates.paysIncomeTax = Boolean(tax);
    }
    const govt = backendProfile.hasRegularGovtJob ?? backendProfile.has_regular_govt_job ?? backendProfile.is_regular_govt_employee;
    if (govt !== undefined && govt !== null) {
      mappedUpdates.hasRegularGovtJob = Boolean(govt);
    }
    const pen = backendProfile.monthlyPension ?? backendProfile.monthly_pension ?? backendProfile.monthly_pension_inr;
    if (pen !== undefined && pen !== null) {
      mappedUpdates.monthlyPension = Number(pen);
    }
    const sav = backendProfile.hasSavingsAccount ?? backendProfile.has_savings_account;
    if (sav !== undefined && sav !== null) {
      mappedUpdates.hasSavingsAccount = Boolean(sav);
    }
    const passbook = backendProfile.hasBankPassbook ?? backendProfile.has_bank_passbook ?? backendProfile.has_savings_account ?? backendProfile.hasSavingsAccount;
    if (passbook !== undefined && passbook !== null) {
      mappedUpdates.hasBankPassbook = Boolean(passbook);
    }
    const preg = backendProfile.isPregnantOrLactating ?? backendProfile.is_pregnant_or_lactating;
    if (preg !== undefined && preg !== null) {
      mappedUpdates.isPregnantOrLactating = Boolean(preg);
    }

    // Never overwrite attributes that the user explicitly confirmed/provided unless force is true
    const filteredUpdates: Partial<UserProfile> = {};
    for (const [k, v] of Object.entries(mappedUpdates)) {
      const key = k as keyof UserProfile;
      if (force || attributeSources[key] !== 'user' || userProfile[key] === undefined || userProfile[key] === null) {
        (filteredUpdates as any)[key] = v;
      }
    }

    if (Object.keys(filteredUpdates).length > 0) {
      updateUserProfile(filteredUpdates, force ? 'user' : 'detected');
    }
  };

  const toggleSaveScheme = (schemeId: string) => {
    setSavedSchemeIds((prev) =>
      prev.includes(schemeId) ? prev.filter((id) => id !== schemeId) : [...prev, schemeId]
    );
  };

  const isSchemeSaved = (schemeId: string) => {
    return savedSchemeIds.includes(schemeId);
  };

  const recordViewedScheme = (schemeId: string) => {
    setRecentlyViewedSchemeIds((prev) => {
      const filtered = prev.filter((id) => id !== schemeId);
      return [schemeId, ...filtered].slice(0, 8);
    });
  };

  const addChatMessage = (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMsg: ChatMessage = {
      ...msg,
      id: 'msg-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
      timestamp: timeStr,
    };
    setChatMessages((prev) => [...prev, newMsg]);
  };

  const clearChat = () => {
    setIsManualLanguage(false);
    setChatMessages([getWelcomeMessage(language)]);
    try {
      sessionStorage.removeItem('yojana_session_chat');
      sessionStorage.removeItem('yojana_chat');
      localStorage.removeItem('yojana_chat');
      sessionStorage.removeItem('yojana_profile');
      localStorage.removeItem('yojana_profile');
    } catch {
      // ignore
    }
    clearSessionId();
  };

  const resetSession = () => {
    setIsManualLanguage(false);
    const activeSessionId = getSessionId();
    resetChatSession(activeSessionId);
    setUserProfile(DEFAULT_PROFILE);
    setAttributeSources({});
    setHasConfirmedProfile(false);
    setSavedSchemeIds([]);
    setRecentlyViewedSchemeIds([]);
    setChatMessages([getWelcomeMessage(language)]);
    try {
      sessionStorage.removeItem('yojana_session_chat');
      localStorage.removeItem('yojana_profile');
      sessionStorage.removeItem('yojana_profile');
      localStorage.removeItem('yojana_saved_schemes');
      localStorage.removeItem('yojana_locker_docs');
      localStorage.removeItem('yojana_chat');
      sessionStorage.removeItem('yojana_chat');
    } catch {
      // ignore
    }
    clearSessionId();
  };

  return (
    <AppContext.Provider
      value={{
        language,
        isManualLanguage,
        setLanguage,
        setDetectedLanguage,
        languageSwitchPrompt,
        requestLanguageSwitch,
        confirmLanguageSwitch,
        dismissLanguageSwitch,
        userProfile,
        attributeSources,
        hasConfirmedProfile,
        setHasConfirmedProfile,
        updateUserProfile,
        clearProfileAttribute,
        mergeDetectedProfile,
        savedSchemeIds,
        toggleSaveScheme,
        isSchemeSaved,
        recentlyViewedSchemeIds,
        recordViewedScheme,
        chatMessages,
        addChatMessage,
        clearChat,
        voiceSpeed,
        setVoiceSpeed,
        autoReadAloud,
        setAutoReadAloud,
        largeTextMode,
        setLargeTextMode,
        highContrastMode,
        setHighContrastMode,
        resetSession,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
