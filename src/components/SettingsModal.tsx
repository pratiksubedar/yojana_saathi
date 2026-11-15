import React, { useState } from 'react';
import {
  X,
  Volume2,
  Globe,
  Eye,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  Contrast,
  Type,
  Check,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { LANGUAGES, t } from '../data/translations';
import { Language } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<Props> = ({ isOpen, onClose }) => {
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

  const [resetDone, setResetDone] = useState(false);

  if (!isOpen) return null;

  const handleReset = () => {
    resetSession();
    setResetDone(true);
    setTimeout(() => {
      setResetDone(false);
      onClose();
    }, 800);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-2xl shadow-2xl border border-sand w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-sand bg-canvas">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-full bg-forest/10 text-forest flex items-center justify-center font-bold">
              ⚙️
            </span>
            <div>
              <h3 id="settings-dialog-title" className="font-heading font-bold text-lg text-ink">
                {t('settingsTitle', language)}
              </h3>
              <p className="text-xs text-ink/60">Preferences & Accessibility</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="p-1.5 rounded-full hover:bg-sand/40 text-ink/70 hover:text-ink transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto">
          {/* 1. Language Preference */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-ink/70 flex items-center gap-1.5 mb-2.5">
              <Globe className="w-3.5 h-3.5 text-forest" />
              <span>Language / भाषा / ಭಾಷೆ / భాష</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {LANGUAGES.map((l) => {
                const isSelected = language === l.code;
                return (
                  <button
                    key={l.code}
                    onClick={() => setLanguage(l.code as Language)}
                    className={`p-2.5 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'border-forest bg-sage/40 text-forest font-bold ring-1 ring-forest'
                        : 'border-sand hover:border-forest/30 bg-canvas text-ink'
                    }`}
                  >
                    <div className="text-sm font-semibold">{l.nativeName}</div>
                    <div className="text-[11px] text-ink/60">{l.name}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Voice & Speech Assistant */}
          <div className="space-y-4 pt-2 border-t border-sand">
            <label className="text-xs font-bold uppercase tracking-wider text-ink/70 flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-forest" />
              <span>Voice & Audio Settings</span>
            </label>

            {/* Auto Read-aloud Switch */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-canvas border border-sand">
              <div>
                <div className="text-sm font-semibold text-ink">Auto Read-Aloud</div>
                <div className="text-xs text-ink/60">Automatically read assistant responses using speech synthesis</div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={autoReadAloud}
                onClick={() => setAutoReadAloud(!autoReadAloud)}
                className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out ${
                  autoReadAloud ? 'bg-forest justify-end' : 'bg-sand justify-start'
                }`}
              >
                <div className="w-4 h-4 rounded-full bg-white shadow-md transform transition-transform" />
              </button>
            </div>

            {/* Voice Speed Slider */}
            <div className="p-3 rounded-xl bg-canvas border border-sand space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-ink">Speech Speed</span>
                <span className="font-mono font-bold text-forest bg-sage/60 px-2 py-0.5 rounded">
                  {voiceSpeed.toFixed(2)}x
                </span>
              </div>
              <input
                type="range"
                min="0.75"
                max="1.50"
                step="0.05"
                value={voiceSpeed}
                onChange={(e) => setVoiceSpeed(parseFloat(e.target.value))}
                className="w-full accent-forest cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-ink/50 font-medium">
                <span>0.75x (Slower)</span>
                <span>1.0x (Normal)</span>
                <span>1.5x (Faster)</span>
              </div>
            </div>
          </div>

          {/* 3. Accessibility Controls */}
          <div className="space-y-3 pt-2 border-t border-sand">
            <label className="text-xs font-bold uppercase tracking-wider text-ink/70 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-forest" />
              <span>Accessibility</span>
            </label>

            {/* Large Text Mode */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-canvas border border-sand">
              <div className="flex items-center gap-2.5">
                <Type className="w-4 h-4 text-forest" />
                <div>
                  <div className="text-sm font-semibold text-ink">Large Text Mode</div>
                  <div className="text-xs text-ink/60">Increases base font size for higher readability</div>
                </div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={largeTextMode}
                onClick={() => setLargeTextMode(!largeTextMode)}
                className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out ${
                  largeTextMode ? 'bg-forest justify-end' : 'bg-sand justify-start'
                }`}
              >
                <div className="w-4 h-4 rounded-full bg-white shadow-md" />
              </button>
            </div>

            {/* High Contrast Mode */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-canvas border border-sand">
              <div className="flex items-center gap-2.5">
                <Contrast className="w-4 h-4 text-forest" />
                <div>
                  <div className="text-sm font-semibold text-ink">High Contrast Mode</div>
                  <div className="text-xs text-ink/60">Boosts borders and color contrast</div>
                </div>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={highContrastMode}
                onClick={() => setHighContrastMode(!highContrastMode)}
                className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out ${
                  highContrastMode ? 'bg-forest justify-end' : 'bg-sand justify-start'
                }`}
              >
                <div className="w-4 h-4 rounded-full bg-white shadow-md" />
              </button>
            </div>
          </div>

          {/* 4. Privacy Notice */}
          <div className="p-3.5 rounded-xl bg-forest/5 border border-forest/15 flex items-start gap-2.5 text-xs text-forest-deep">
            <ShieldCheck className="w-4 h-4 text-forest flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Zero Permanent PII Storage:</span> Yojana Saathi operates with ephemeral session memory. No Aadhaar numbers, phone numbers, or bank account credentials are ever collected or stored permanently.
            </div>
          </div>

          {/* 5. Reset Session / Clear Data */}
          <div className="pt-2 border-t border-sand">
            <button
              onClick={handleReset}
              disabled={resetDone}
              className={`w-full py-2.5 px-4 rounded-xl border flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
                resetDone
                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  : 'bg-canvas hover:bg-rose-50 text-rose-700 border-rose-200 hover:border-rose-300'
              }`}
            >
              {resetDone ? (
                <>
                  <Check className="w-4 h-4 text-emerald-700" />
                  <span>Session Cleared!</span>
                </>
              ) : (
                <>
                  <RotateCcw className="w-4 h-4" />
                  <span>Clear Conversation & Reset Profile</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

