/**
 * Yojana Saathi - Accessible Multilingual Offline & Network Status Banner
 * Milestone 6.6: Renders reactive connection state, offline details,
 * connection check trigger, and PWA installation prompt.
 */

import React, { useState } from 'react';
import { WifiOff, Wifi, RefreshCw, Download, Info, ChevronDown, ChevronUp, X } from 'lucide-react';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';

export const OfflineBanner: React.FC = () => {
  const { isOnline, hasReconnected, isInstallable, promptInstall, checkConnection } = useNetworkStatus();
  const { language } = useApp();
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [showDetails, setShowDetails] = useState<boolean>(false);
  const [isInstallDismissed, setIsInstallDismissed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('yojana_install_dismissed') === 'true';
    } catch {
      return false;
    }
  });

  const handleDismissInstall = () => {
    setIsInstallDismissed(true);
    try {
      localStorage.setItem('yojana_install_dismissed', 'true');
    } catch {
      // ignore
    }
  };

  const handleCheckConnection = async () => {
    setIsChecking(true);
    await checkConnection();
    setTimeout(() => {
      setIsChecking(false);
    }, 600);
  };

  if (isOnline && !hasReconnected && (!isInstallable || isInstallDismissed)) {
    return null;
  }

  return (
    <div className="w-full">
      {/* 1. Offline Alert Banner */}
      {!isOnline && (
        <aside
          role="status"
          aria-live="polite"
          className="bg-amber-50 border-b border-amber-300 text-amber-950 px-4 py-3 transition-all"
        >
          <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-amber-200/80 text-amber-900 flex items-center justify-center flex-shrink-0 mt-0.5 sm:mt-0">
                <WifiOff className="w-4 h-4" aria-hidden="true" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-heading font-bold text-xs uppercase tracking-wider text-amber-900">
                    {t('offlineStatusPill', language)}
                  </span>
                  <span className="text-[10px] bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full font-semibold border border-amber-300">
                    {t('offlineBannerTitle', language)}
                  </span>
                </div>
                <p className="text-xs text-amber-900/90 mt-0.5 leading-relaxed">
                  {t('offlineBannerDesc', language)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end flex-wrap pt-1 sm:pt-0">
              <button
                type="button"
                onClick={() => setShowDetails(!showDetails)}
                aria-expanded={showDetails}
                className="text-xs text-amber-900 hover:text-amber-950 font-semibold px-2.5 py-1.5 rounded border border-amber-300/80 bg-white/60 flex items-center gap-1 min-h-[36px]"
              >
                <Info className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t('offlineFeaturesListTitle', language)}</span>
                {showDetails ? (
                  <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
                )}
              </button>

              <button
                type="button"
                onClick={handleCheckConnection}
                disabled={isChecking}
                aria-label={t('checkConnectionAction', language)}
                className="bg-amber-900 hover:bg-amber-950 text-white font-semibold text-xs px-3 py-1.5 rounded flex items-center gap-1.5 min-h-[36px] transition-colors"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin' : ''}`}
                  aria-hidden="true"
                />
                <span>{isChecking ? 'Checking...' : t('checkConnectionAction', language)}</span>
              </button>
            </div>
          </div>

          {/* Expandable Offline Capabilities Breakdown */}
          {showDetails && (
            <div className="max-w-4xl mx-auto mt-3 pt-3 border-t border-amber-200/80 text-xs space-y-1.5">
              <p className="text-emerald-900 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block"></span>
                {t('offlineAvailableFeatures', language)}
              </p>
              <p className="text-amber-900/90 font-medium flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block"></span>
                {t('offlineUnavailableFeatures', language)}
              </p>
            </div>
          )}
        </aside>
      )}

      {/* 2. Reconnected Success Notice */}
      {isOnline && hasReconnected && (
        <aside
          role="status"
          aria-live="polite"
          className="bg-emerald-50 border-b border-emerald-300 text-emerald-950 px-4 py-2 text-xs font-semibold flex items-center justify-center gap-2 animate-fade-in"
        >
          <Wifi className="w-4 h-4 text-emerald-700" aria-hidden="true" />
          <span>{t('reconnectedNotice', language)}</span>
        </aside>
      )}

      {/* 3. Optional PWA Install Action Bar */}
      {isOnline && isInstallable && !hasReconnected && !isInstallDismissed && (
        <div className="bg-forest/10 border-b border-forest/20 text-forest-deep px-4 py-2 text-xs">
          <div className="max-w-4xl mx-auto flex items-center justify-between gap-2">
            <span className="font-medium text-ink text-[11px] sm:text-xs">
              Install Yojana Saathi on your device for instant offline access to welfare schemes
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={promptInstall}
                className="bg-forest hover:bg-forest-deep text-white font-bold px-3 py-1 rounded-full text-[11px] flex items-center gap-1.5 shadow-sm transition-colors"
              >
                <Download className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{t('installAppAction', language)}</span>
              </button>
              <button
                type="button"
                onClick={handleDismissInstall}
                aria-label="Dismiss installation banner"
                title="Dismiss"
                className="p-1 rounded-full hover:bg-forest/20 text-ink/60 hover:text-ink transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

