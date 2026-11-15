import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Globe,
  Volume2,
  ShieldCheck,
  Trash2,
  ArrowRight,
  Info,
  Check,
  Eye,
  User,
  Smartphone,
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { LANGUAGES, t } from '../data/translations';
import { useApp } from '../context/AppContext';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { useNetworkStatus } from '../hooks/useNetworkStatus';

export const SettingsProfile: React.FC = () => {
  const navigate = useNavigate();
  const {
    language,
    setLanguage,
    voiceSpeed,
    setVoiceSpeed,
    autoReadAloud,
    setAutoReadAloud,
    largeTextMode,
    setLargeTextMode,
    highContrastMode,
    setHighContrastMode,
    resetSession,
  } = useApp();

  const { isOnline } = useNetworkStatus();
  const { isSupported: ttsSupported, isSpeaking, speak, stop } = useSpeechSynthesis(
    language,
    voiceSpeed
  );

  const [clearSuccess, setClearSuccess] = useState(false);

  const handleClearSession = () => {
    if (window.confirm(t('clearSessionConfirmMsg', language))) {
      resetSession();
      setClearSuccess(true);
      setTimeout(() => setClearSuccess(false), 3000);
    }
  };

  const handleTestVoice = () => {
    if (isSpeaking) {
      stop();
      return;
    }
    const samplePhrases: Record<string, string> = {
      en: 'Hello! Yojana Saathi voice assistance is ready.',
      hi: 'नमस्ते! योजना साथी वॉयस सहायता तैयार है।',
      kn: 'ನಮಸ್ಕಾರ! ಯೋಜನೆ ಸಾಥಿ ಧ್ವನಿ ಸಹಾಯ ಸಿದ್ಧವಾಗಿದೆ.',
      te: 'నమస్కారం! యోజనా సాథి వాయిస్ సహాయం సిద్ధంగా ఉంది.',
    };
    speak(samplePhrases[language] || samplePhrases.en, {
      lang: language,
      rate: voiceSpeed,
      messageId: 'settings-voice-test',
    });
  };

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title={t('navSettings', language)} subtitle="Preferences & Accessibility" showBack />

      <main className="max-w-3xl mx-auto px-4 py-5 space-y-4">
        {/* 1. Language & Regional Preferences */}
        <section className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-3">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-forest" />
            <h2 className="font-heading font-bold text-sm text-ink">
              Language & Regional Preferences
            </h2>
          </div>
          <p className="text-xs text-ink/70">
            Select your preferred interface and voice language.
          </p>

          <div className="grid grid-cols-2 gap-2.5">
            {LANGUAGES.map((lang) => {
              const isSelected = language === lang.code;
              return (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setLanguage(lang.code)}
                  aria-pressed={isSelected}
                  className={`p-3 rounded-lg border text-left flex items-center justify-between transition-all min-h-[48px] ${
                    isSelected
                      ? 'bg-sage/50 border-forest text-forest font-bold'
                      : 'bg-canvas border-sand text-ink hover:bg-sand/30'
                  }`}
                >
                  <div>
                    <span className="block text-sm leading-tight">{lang.nativeName}</span>
                    <span className="text-[11px] text-ink/60 font-normal">
                      {lang.name}
                    </span>
                  </div>
                  {isSelected && <Check className="w-4 h-4 text-forest flex-shrink-0" />}
                </button>
              );
            })}
          </div>
        </section>

        {/* 2. Voice & Speech Preferences */}
        <section className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-forest" />
              <h2 className="font-heading font-bold text-sm text-ink">
                Voice & Speech Preferences
              </h2>
            </div>
            {ttsSupported && (
              <button
                type="button"
                onClick={handleTestVoice}
                className="text-xs font-semibold text-forest bg-sage hover:bg-sage/80 px-2.5 py-1 rounded-full transition-colors border border-sage/60"
              >
                {isSpeaking ? 'Stop Test' : 'Test Voice'}
              </button>
            )}
          </div>

          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-sm font-semibold text-ink block">
                {t('autoReadAloudLabel', language)}
              </span>
              <span className="text-xs text-ink/70">
                Automatically speak assistant responses aloud
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={autoReadAloud}
              aria-label={t('autoReadAloudLabel', language)}
              onClick={() => setAutoReadAloud(!autoReadAloud)}
              className={`w-12 h-6 rounded-full transition-colors p-0.5 flex items-center flex-shrink-0 ${
                autoReadAloud ? 'bg-forest justify-end' : 'bg-sand justify-start'
              }`}
            >
              <span className="w-5 h-5 rounded-full bg-white shadow-sm block" />
            </button>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-sand/60">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-ink">
                {t('voiceSpeedLabel', language)}
              </span>
              <span className="font-bold text-forest">{voiceSpeed}x</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[0.8, 1.0, 1.2].map((speed) => (
                <button
                  key={speed}
                  type="button"
                  onClick={() => setVoiceSpeed(speed)}
                  className={`py-2 rounded-lg text-xs font-bold border transition-colors min-h-[40px] ${
                    voiceSpeed === speed
                      ? 'bg-forest text-white border-forest shadow-xs'
                      : 'bg-canvas text-ink border-sand hover:bg-sand/30'
                  }`}
                >
                  {speed === 0.8 ? '0.8x Slow' : speed === 1.0 ? '1.0x Normal' : '1.2x Fast'}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* 3. Accessibility */}
        <section className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-4">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-forest" />
            <h2 className="font-heading font-bold text-sm text-ink">
              Accessibility
            </h2>
          </div>

          <div className="flex items-center justify-between gap-3">
            <div>
              <span className="text-sm font-semibold text-ink block">
                Larger Text Size
              </span>
              <span className="text-xs text-ink/70">
                Increase base font size across all screens for easier reading
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={largeTextMode}
              aria-label="Larger Text Size"
              onClick={() => setLargeTextMode(!largeTextMode)}
              className={`w-12 h-6 rounded-full transition-colors p-0.5 flex items-center flex-shrink-0 ${
                largeTextMode ? 'bg-forest justify-end' : 'bg-sand justify-start'
              }`}
            >
              <span className="w-5 h-5 rounded-full bg-white shadow-sm block" />
            </button>
          </div>

          <div className="flex items-center justify-between gap-3 pt-2 border-t border-sand/60">
            <div>
              <span className="text-sm font-semibold text-ink block">
                High Contrast Mode
              </span>
              <span className="text-xs text-ink/70">
                Strengthen borders and text contrast for outdoor visibility
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={highContrastMode}
              aria-label="High Contrast Mode"
              onClick={() => setHighContrastMode(!highContrastMode)}
              className={`w-12 h-6 rounded-full transition-colors p-0.5 flex items-center flex-shrink-0 ${
                highContrastMode ? 'bg-forest justify-end' : 'bg-sand justify-start'
              }`}
            >
              <span className="w-5 h-5 rounded-full bg-white shadow-sm block" />
            </button>
          </div>
        </section>

        {/* 4. Privacy & Data Controls */}
        <section className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-forest" />
            <h2 className="font-heading font-bold text-sm text-ink">
              Privacy & Data Controls
            </h2>
          </div>

          <p className="text-xs text-ink/70 leading-relaxed">
            Yojana Saathi uses zero-knowledge ephemeral sessions. Conversation history and profile attributes are kept in memory only, and local Locker files never leave your device.
          </p>

          <button
            type="button"
            onClick={handleClearSession}
            className="w-full py-2.5 bg-red-50 hover:bg-red-100 text-rose-800 font-bold text-xs rounded-full border border-red-200 flex items-center justify-center gap-1.5 transition-colors min-h-[44px]"
          >
            <Trash2 className="w-4 h-4" />
            <span>{t('clearSessionResetBtn', language)}</span>
          </button>

          {clearSuccess && (
            <p className="text-xs text-emerald-700 font-semibold text-center" role="status">
              {t('sessionClearedMsg', language)}
            </p>
          )}
        </section>

        {/* 5. App Preferences & Profile Shortcut */}
        <section className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-3">
          <div className="flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-forest" />
            <h2 className="font-heading font-bold text-sm text-ink">
              App Information
            </h2>
          </div>

          <div className="flex items-center justify-between text-xs py-1">
            <span className="text-ink/70">Connection Status</span>
            <span
              className={`font-bold px-2 py-0.5 rounded-full ${
                isOnline
                  ? 'bg-[#EAF5EE] text-[#1F7A4D]'
                  : 'bg-amber-100 text-amber-900'
              }`}
            >
              {isOnline ? 'Online' : 'Offline Mode'}
            </span>
          </div>

          <button
            type="button"
            onClick={() => navigate('/profile')}
            className="w-full flex items-center justify-between p-3 rounded-lg bg-canvas hover:bg-sand/30 border border-sand text-xs font-bold text-ink transition-colors"
          >
            <span className="flex items-center gap-2">
              <User className="w-4 h-4 text-forest" />
              <span>Manage Citizen Profile</span>
            </span>
            <ArrowRight className="w-4 h-4 text-ink/60" />
          </button>
        </section>

        <DisclaimerBanner />

        <div className="text-center pt-2 text-[11px] text-ink/60 flex items-center justify-center gap-1">
          <Info className="w-3.5 h-3.5" />
          <span>Yojana Saathi • Civic Welfare Assistant</span>
        </div>
      </main>

      <BottomNav />
    </div>
  );
};
