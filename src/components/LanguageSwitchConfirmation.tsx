import React from 'react';
import { Globe, CheckCircle2, X, Sparkles, HelpCircle } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { LANGUAGES, t } from '../data/translations';
import { Language } from '../types';

export const LanguageSwitchConfirmation: React.FC = () => {
  const { language, languageSwitchPrompt, confirmLanguageSwitch, dismissLanguageSwitch } = useApp();

  if (!languageSwitchPrompt) return null;

  const { detectedLang, confidence, reason } = languageSwitchPrompt;
  const detectedInfo = LANGUAGES.find((l) => l.code === detectedLang) || LANGUAGES[0];
  const currentInfo = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];

  const localizedTitles: Record<Language, { heading: string; body: string; confirmBtn: string; dismissBtn: string }> = {
    hi: {
      heading: 'वेबसाइट की भाषा बदलें? / Switch Website Language?',
      body: `आपने हिंदी में बोला/लिखा है। क्या आप पूरी वेबसाइट (नेविगेशन, प्रोफ़ाइल, योजनाएं) को ${detectedInfo.nativeName} में बदलना चाहते हैं?`,
      confirmBtn: `हाँ, वेबसाइट को ${detectedInfo.nativeName} में बदलें`,
      dismissBtn: `वर्तमान भाषा (${currentInfo.nativeName}) रखें`,
    },
    kn: {
      heading: 'ವೆಬ್‌ಸೈಟ್ ಭಾಷೆ ಬದಲಾಯಿಸಬೇಕೆ? / Switch Website Language?',
      body: `ನೀವು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿದ್ದೀರಿ/ಟೈಪ್ ಮಾಡಿದ್ದೀರಿ. ಸಂಪೂರ್ಣ ವೆಬ್‌ಸೈಟ್ (ನ್ಯಾವಿಗೇಷನ್, ಪ್ರೊಫೈಲ್, ಯೋಜನೆಗಳು) ಅನ್ನು ${detectedInfo.nativeName}ಗೆ ಬದಲಾಯಿಸಲು ಬಯಸುವಿರಾ?`,
      confirmBtn: `ಹೌದು, ವೆಬ್‌ಸೈಟ್ ಅನ್ನು ${detectedInfo.nativeName}ಗೆ ಬದಲಾಯಿಸಿ`,
      dismissBtn: `ಈಗಿನ ಭಾಷೆಯಲ್ಲೇ (${currentInfo.nativeName}) ಇರಲಿ`,
    },
    te: {
      heading: 'వెబ్‌సైట్ భాషను మార్చాలా? / Switch Website Language?',
      body: `మీరు తెలుగులో మాట్లాడారు/టైప్ చేశారు. మొత్తం వెబ్‌సైట్‌ను (నావిగేషన్, ప్రొఫైల్, పథకాలు) ${detectedInfo.nativeName}లోకి మార్చాలనుకుంటున్నారా?`,
      confirmBtn: `అవును, వెబ్‌సైట్‌ను ${detectedInfo.nativeName}లోకి మార్చండి`,
      dismissBtn: `ప్రస్తుత భాషలోనే (${currentInfo.nativeName}) ఉంచండి`,
    },
    en: {
      heading: `Switch website to ${detectedInfo.name}?`,
      body: `You are speaking/typing in ${detectedInfo.name} (${detectedInfo.nativeName}). Would you like to switch the entire website—including navigation, profile, and schemes—to ${detectedInfo.name}?`,
      confirmBtn: `Yes, Switch Website to ${detectedInfo.nativeName}`,
      dismissBtn: `Keep ${currentInfo.nativeName}`,
    },
  };

  const currentCopy = localizedTitles[detectedLang] || localizedTitles.en;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Confirm website language change"
      className="fixed inset-x-0 top-0 z-50 flex items-start justify-center p-3 sm:p-4 bg-black/40 backdrop-blur-xs animate-in fade-in"
    >
      <div className="bg-surface max-w-lg w-full rounded-2xl border-2 border-forest/30 shadow-2xl p-4 sm:p-5 space-y-3.5 relative overflow-hidden">
        {/* Decorative Top Accent Bar */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-forest via-amber-500 to-forest" />

        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-full bg-forest/10 text-forest flex items-center justify-center flex-shrink-0">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-heading font-bold text-sm sm:text-base text-ink">
                {currentCopy.heading}
              </h3>
              {reason && (
                <span className="text-[11px] font-semibold text-forest flex items-center gap-1 mt-0.5">
                  <Sparkles className="w-3 h-3" />
                  {reason}
                </span>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={dismissLanguageSwitch}
            aria-label="Close language confirmation"
            className="text-ink/50 hover:text-ink p-1 rounded-lg hover:bg-sand/40 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Informational Message */}
        {confidence === 'script_match' ? (
          <p className="text-xs sm:text-sm text-ink/80 leading-relaxed font-sans">
            {currentCopy.body}
          </p>
        ) : (
          <div className="space-y-2">
            <p className="text-xs sm:text-sm text-ink/80 leading-relaxed">
              We noticed your message might be in a different language. Which language would you like to use for the entire website?
            </p>
            {/* 4 Multi-Language Selection Pills when uncertain */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              {LANGUAGES.map((l) => (
                <button
                  key={l.code}
                  type="button"
                  onClick={() => confirmLanguageSwitch(l.code)}
                  className={`px-3 py-2 rounded-xl text-xs font-bold border transition-all text-left flex items-center justify-between ${
                    language === l.code
                      ? 'bg-forest/10 border-forest text-forest'
                      : 'bg-canvas border-sand hover:border-forest/50 text-ink'
                  }`}
                >
                  <span>{l.nativeName}</span>
                  <span className="text-[10px] text-ink/60 font-medium">({l.name})</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2 pt-2 border-t border-sand/60">
          <button
            type="button"
            onClick={dismissLanguageSwitch}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-ink/70 hover:text-ink bg-canvas border border-sand hover:bg-sand/30 transition-colors"
          >
            {currentCopy.dismissBtn}
          </button>
          <button
            type="button"
            onClick={() => confirmLanguageSwitch(detectedLang)}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-forest hover:bg-forest-deep text-white shadow-sm flex items-center justify-center gap-1.5 transition-transform active:scale-95"
          >
            <CheckCircle2 className="w-4 h-4 text-amber-300" />
            <span>{currentCopy.confirmBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

