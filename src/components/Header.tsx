import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Globe, Sparkles, WifiOff, Settings, User } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { LANGUAGES, t } from '../data/translations';
import { LanguageDialog } from './LanguageDialog';
import { SettingsModal } from './SettingsModal';

interface Props {
  title?: string;
  subtitle?: string;
  showBack?: boolean;
}

export const Header: React.FC<Props> = ({ title, subtitle, showBack = false }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { language } = useApp();
  const { isOnline } = useNetworkStatus();

  const [isLangOpen, setIsLangOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const currentLangInfo = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];
  const isHome = location.pathname === '/';
  const isProfile = location.pathname === '/profile';

  return (
    <>
      <header className="sticky top-0 z-30 bg-surface/95 backdrop-blur-md border-b border-sand shadow-sm">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showBack && !isHome && (
              <button
                onClick={() => navigate(-1)}
                aria-label={t('goBack', language)}
                className="p-2 -ml-2 rounded-full hover:bg-sand/40 text-ink transition-colors focus:ring-2 focus:ring-forest"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}

            <div onClick={() => navigate('/')} className="cursor-pointer flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-heading font-bold text-lg text-forest tracking-tight">
                  Yojana Saathi
                </span>
                <span className="text-sand font-normal">|</span>
                <span className="font-heading font-semibold text-base text-ink">
                  {t('appName', language)}
                </span>
                <span className="hidden sm:inline-flex items-center gap-1 text-[10px] bg-sage text-forest px-1.5 py-0.5 rounded-full font-bold ml-1 border border-sage/60">
                  <Sparkles className="w-2.5 h-2.5" /> {t('aiBetaBadge', language)}
                </span>
              </div>
              {title || subtitle ? (
                <span className="text-xs text-ink/70 font-medium truncate max-w-[200px] sm:max-w-xs">
                  {title} {subtitle ? `• ${subtitle}` : ''}
                </span>
              ) : (
                <span className="text-[11px] text-ink/60">{t('appSubheader', language)}</span>
              )}
            </div>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2">
            {/* Offline indicator badge when disconnected */}
            {!isOnline && (
              <span
                role="status"
                className="flex items-center gap-1 bg-amber-100 text-amber-900 border border-amber-300 px-2 py-1 rounded-full text-[11px] font-bold"
                title={t('offlineBannerDesc', language)}
              >
                <WifiOff className="w-3 h-3 text-amber-800" aria-hidden="true" />
                <span>{t('offlineStatusPill', language)}</span>
              </span>
            )}

            {/* Language Switcher Pill */}
            <button
              onClick={() => setIsLangOpen(true)}
              aria-label="Change Language"
              className="flex items-center gap-1.5 bg-sage hover:bg-sage/80 text-forest text-xs font-semibold px-2.5 py-1.5 rounded-full border border-forest/20 transition-all focus:outline-none focus:ring-2 focus:ring-forest"
            >
              <Globe className="w-3.5 h-3.5 text-forest" />
              <span>{currentLangInfo.nativeName}</span>
            </button>

            {/* Settings In-Page Modal Trigger (Replaces navigate('/settings')) */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              aria-label={t('navSettings', language)}
              title={t('navSettings', language)}
              className="p-2 rounded-full border bg-canvas hover:bg-sand/50 text-ink border-sand transition-all focus:outline-none focus:ring-2 focus:ring-forest"
            >
              <Settings className="w-4 h-4" />
            </button>

            {/* Profile Button in Top-Right Header */}
            <button
              onClick={() => navigate('/profile')}
              aria-label={t('navProfile', language)}
              title={t('navProfile', language)}
              className={`p-2 rounded-full border transition-all focus:outline-none focus:ring-2 focus:ring-forest ${
                isProfile
                  ? 'bg-forest text-white border-forest shadow-sm'
                  : 'bg-canvas hover:bg-sand/50 text-ink border-sand'
              }`}
            >
              <User className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* In-page Modals */}
      <LanguageDialog isOpen={isLangOpen} onClose={() => setIsLangOpen(false)} />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </>
  );
};
