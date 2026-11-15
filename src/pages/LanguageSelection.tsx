import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Volume2, VolumeX, Check, ArrowRight } from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { LANGUAGES, t } from '../data/translations';
import { useApp } from '../context/AppContext';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { Language } from '../types';

const SAMPLE_GREETINGS: Record<Language, string> = {
  en: 'Welcome to Yojana Saathi. Discover government schemes for you.',
  hi: 'योजना साथी में आपका स्वागत है। आपके लिए सरकारी कल्याणकारी योजनाएँ।',
  kn: 'ಯೋಜನೆ ಸಾಥಿಗೆ ಸುಸ್ವಾಗತ. ನಿಮಗಾಗಿ ಸರಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳು.',
  te: 'యోజనా సాథికి స్వాగతం. మీ కోసం ప్రభుత్వ సంక్షేమ పథకాలు.',
};

export const LanguageSelection: React.FC = () => {
  const navigate = useNavigate();
  const { language, setLanguage, voiceSpeed } = useApp();
  const [selectedLang, setSelectedLang] = useState<Language>(language);
  const [playingCode, setPlayingCode] = useState<Language | null>(null);

  const { isSpeaking, speak, stop } = useSpeechSynthesis(selectedLang, voiceSpeed);

  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  useEffect(() => {
    if (!isSpeaking) {
      setPlayingCode(null);
    }
  }, [isSpeaking]);

  const handlePreviewAudio = (code: Language, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isSpeaking && playingCode === code) {
      stop();
      setPlayingCode(null);
    } else {
      stop();
      setPlayingCode(code);
      speak(SAMPLE_GREETINGS[code], { lang: code, rate: voiceSpeed });
    }
  };

  const handleConfirmLanguage = () => {
    stop();
    setLanguage(selectedLang);
    navigate(-1);
  };

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title={t('languageScreenTitle', selectedLang)} subtitle="Language Preference" showBack />

      <main className="max-w-md mx-auto px-4 py-5 space-y-5">
        <div className="text-center space-y-1.5 pt-2">
          <h1 className="font-heading font-bold text-2xl text-ink leading-tight">
            {t('languageScreenTitle', selectedLang)}
          </h1>
          <p className="text-xs text-ink/70">
            {t('languageScreenSubtitle', selectedLang)}
          </p>
        </div>

        {/* 4 Language Cards */}
        <div className="space-y-3">
          {LANGUAGES.map((lang) => {
            const isSelected = selectedLang === lang.code;
            const isPlaying = playingCode === lang.code;

            return (
              <div
                key={lang.code}
                onClick={() => setSelectedLang(lang.code)}
                className={`p-4 rounded-card border transition-all cursor-pointer flex items-center justify-between min-h-[64px] ${
                  isSelected
                    ? 'bg-sage/40 border-forest shadow-card ring-2 ring-forest/20'
                    : 'bg-surface border-sand hover:border-forest/40 hover:bg-canvas shadow-card'
                }`}
              >
                <div className="flex items-center gap-3.5">
                  <div
                    className={`w-6 h-6 rounded-full border flex items-center justify-center transition-colors ${
                      isSelected
                        ? 'bg-forest border-forest text-white'
                        : 'border-sand bg-surface'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                  </div>

                  <div>
                    <div className="flex items-baseline gap-2">
                      <span className="font-heading font-bold text-lg text-ink">
                        {lang.nativeName}
                      </span>
                      <span className="text-xs text-ink/60 font-medium">
                        ({lang.name})
                      </span>
                    </div>
                    <span className="text-[11px] text-ink/50 block line-clamp-1">
                      {lang.subtext}
                    </span>
                  </div>
                </div>

                {/* Audio Preview Button */}
                <button
                  type="button"
                  onClick={(e) => handlePreviewAudio(lang.code, e)}
                  aria-label={`Listen to sample in ${lang.name}`}
                  className={`p-2 rounded-full border transition-all ${
                    isPlaying
                      ? 'bg-amber-600 text-white border-amber-600 animate-pulse'
                      : 'bg-canvas text-ink/70 hover:text-forest border-sand hover:bg-sand/30'
                  }`}
                >
                  {isPlaying ? (
                    <VolumeX className="w-4 h-4" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Informative Helper Note */}
        <div className="bg-surface rounded-card p-4 border border-sand shadow-xs text-xs text-ink/75 leading-relaxed">
          <p>
            {t('languageAudioGuide', selectedLang)}
          </p>
        </div>

        {/* Save / Apply Button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={handleConfirmLanguage}
            className="w-full bg-forest hover:bg-forest-deep text-white font-bold py-3.5 px-6 rounded-full shadow-md flex items-center justify-center gap-2 text-base transition-transform active:scale-98 min-h-[50px]"
          >
            <span>{t('applyLanguageCTA', selectedLang)}</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </main>

      <BottomNav />
    </div>
  );
};
