import React from 'react';
import { Check, X, Globe } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { LANGUAGES } from '../data/translations';
import { Language } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const LanguageDialog: React.FC<Props> = ({ isOpen, onClose }) => {
  const { language, setLanguage } = useApp();

  if (!isOpen) return null;

  const handleSelect = (langCode: Language) => {
    setLanguage(langCode);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="lang-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface rounded-2xl shadow-xl border border-sand w-full max-w-sm overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-sand bg-canvas">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-forest" />
            <h3 id="lang-dialog-title" className="font-heading font-bold text-base text-ink">
              Choose Language / भाषा चुनें
            </h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="p-1 rounded-full hover:bg-sand/40 text-ink/70 hover:text-ink transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-2">
          {LANGUAGES.map((lang) => {
            const isSelected = language === lang.code;
            return (
              <button
                key={lang.code}
                onClick={() => handleSelect(lang.code)}
                className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-forest bg-sage/40 text-forest font-semibold shadow-sm'
                    : 'border-sand hover:border-forest/40 hover:bg-canvas text-ink'
                }`}
              >
                <div>
                  <div className="text-base font-bold">{lang.nativeName}</div>
                  <div className="text-xs text-ink/60">{lang.name} • {lang.subtext}</div>
                </div>
                {isSelected && (
                  <div className="w-6 h-6 rounded-full bg-forest text-white flex items-center justify-center">
                    <Check className="w-4 h-4" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

