import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  MicOff, 
  ShieldAlert, 
  WifiOff, 
  MessageSquare, 
  RefreshCw, 
  ExternalLink, 
  Home, 
  PhoneCall 
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { useApp } from '../context/AppContext';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { t } from '../data/translations';

export const ErrorFallback: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useApp();
  const { isOnline, checkConnection } = useNetworkStatus();
  const [retryState, setRetryState] = useState(false);

  const handleSimulateRetry = async () => {
    setRetryState(true);
    const online = await checkConnection();
    setTimeout(() => {
      setRetryState(false);
      if (online) {
        navigate('/assistant');
      }
    }, 800);
  };

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title={t('resilienceHeaderTitle', language)} subtitle="Fallback States" showBack />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-5">
        <div className="text-center space-y-1.5 pt-1">
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 border border-amber-300">
            {t('resilienceTag', language)}
          </span>
          <h1 className="font-heading font-bold text-xl text-ink">
            {t('resilienceHeaderTitle', language)}
          </h1>
          <p className="text-xs text-ink/70">
            {t('resilienceSubtitle', language)}
          </p>
        </div>

        {/* State 1: Microphone Permission Denied Card */}
        <div className="bg-surface rounded-card p-5 border border-amber-300 shadow-card space-y-3 relative overflow-hidden">
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center flex-shrink-0">
              <MicOff className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider block">
                Scenario 1
              </span>
              <h2 className="font-heading font-bold text-base text-ink">
                {t('scenario1Title', language)}
              </h2>
              <p className="text-xs text-ink/70 mt-1 leading-relaxed">
                {t('scenario1Desc', language)}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
            <button
              onClick={() => navigate('/assistant')}
              className="bg-forest hover:bg-forest-deep text-white font-bold py-2.5 px-4 rounded-full text-xs flex items-center justify-center gap-2 min-h-[44px] shadow-xs"
            >
              <MessageSquare className="w-4 h-4" />
              <span>{t('switchToTextModeAction', language)}</span>
            </button>
          </div>
        </div>

        {/* State 2: Out-of-Knowledge-Base Safe Refusal Card (Hallucination Prevention) */}
        <div className="bg-surface rounded-card p-5 border border-sand shadow-card space-y-3">
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-full bg-sage text-forest flex items-center justify-center flex-shrink-0">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-forest uppercase tracking-wider block">
                Scenario 2 • Anti-Hallucination Safe Refusal
              </span>
              <h2 className="font-heading font-bold text-base text-ink">
                {t('scenario2Title', language)}
              </h2>
              <div className="bg-canvas border border-sand p-2 rounded-lg text-xs my-2">
                <span className="font-bold text-ink">
                  {t('scenario2CitizenQuery', language)}
                </span>
              </div>
              <p className="text-xs text-ink/70 leading-relaxed">
                {t('scenario2Desc', language)}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
            <button
              onClick={() => navigate('/browse')}
              className="bg-forest hover:bg-forest-deep text-white font-bold py-2.5 px-4 rounded-full text-xs flex items-center justify-center gap-2 min-h-[44px] shadow-xs"
            >
              <span>{t('browseSchemesCTA', language)}</span>
            </button>
            <a
              href="https://myscheme.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="bg-canvas border border-sand text-ink font-semibold py-2.5 px-4 rounded-full text-xs flex items-center justify-center gap-1.5 hover:bg-sand/30 min-h-[44px]"
            >
              <span>myScheme.gov.in</span>
              <ExternalLink className="w-3.5 h-3.5 text-forest" />
            </a>
          </div>
        </div>

        {/* State 3: Voice/Network Timeout State */}
        <div className="bg-surface rounded-card p-5 border border-sand shadow-card space-y-3">
          <div className="flex items-start gap-3.5">
            <div className="w-11 h-11 rounded-full bg-sand/40 text-ink/60 flex items-center justify-center flex-shrink-0">
              <WifiOff className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-ink/60 uppercase tracking-wider block">
                Scenario 3 • Connection Timeout
              </span>
              <h2 className="font-heading font-bold text-base text-ink">
                {t('scenario3Title', language)}
              </h2>
              <p className="text-xs text-ink/70 mt-1 leading-relaxed">
                {t('scenario3Desc', language)}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2.5 pt-1">
            <button
              onClick={handleSimulateRetry}
              disabled={retryState}
              className="bg-amber-600 hover:bg-amber-700 text-white font-bold py-2.5 px-4 rounded-full text-xs flex items-center justify-center gap-2 min-h-[44px] shadow-xs"
            >
              <RefreshCw className={`w-4 h-4 ${retryState ? 'animate-spin' : ''}`} />
              <span>{retryState ? 'Connecting...' : t('retrySpeakingAction', language)}</span>
            </button>
            <button
              onClick={() => navigate('/assistant')}
              className="bg-canvas border border-sand text-ink font-semibold py-2.5 px-4 rounded-full text-xs flex items-center justify-center gap-1.5 min-h-[44px]"
            >
              <MessageSquare className="w-4 h-4 text-ink/60" />
              <span>{t('switchToTextModeAction', language)}</span>
            </button>
          </div>
        </div>

        {/* Toll-free Helpline & Home Return */}
        <div className="bg-surface border border-sand rounded-card p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-ink/70">
            <PhoneCall className="w-4 h-4 text-forest" />
            <span>{t('nationalHelpdeskLabel', language)}</span>
          </div>

          <button
            onClick={() => navigate('/')}
            className="text-forest font-bold hover:underline flex items-center gap-1"
          >
            <Home className="w-3.5 h-3.5" />
            <span>{t('navHome', language)}</span>
          </button>
        </div>

        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};
