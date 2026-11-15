import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Clock, XCircle, ArrowRight, AlertCircle, RefreshCw, Volume2, VolumeX } from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { SchemeCard } from '../components/SchemeCard';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { EligibilityStatus, Scheme } from '../types';
import { useApp } from '../context/AppContext';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { t } from '../data/translations';
import { 
  fetchSchemes, 
  evaluateEligibility, 
  mapUserProfileToCitizenAttributes, 
  mapBackendSchemeToFrontend,
  SchemeEligibilityResult
} from '../services/schemeApi';

export const EligibilityResults: React.FC = () => {
  const navigate = useNavigate();
  const { userProfile, language, voiceSpeed } = useApp();
  const [activeTab, setActiveTab] = useState<EligibilityStatus | 'all'>('all');

  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [evaluations, setEvaluations] = useState<SchemeEligibilityResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { isSupported: isTtsSupported, isSpeaking, speak, stop: stopSpeaking } = useSpeechSynthesis(language, voiceSpeed);

  useEffect(() => {
    return () => {
      stopSpeaking();
    };
  }, [stopSpeaking]);

  const loadEligibilityEvaluations = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const citizenAttrs = mapUserProfileToCitizenAttributes(userProfile);

      // Concurrently query the active welfare catalog and the deterministic rule engine
      const [catalogRes, evalRes] = await Promise.all([
        fetchSchemes({ pageSize: 50 }, { signal }),
        evaluateEligibility(
          {
            citizen_attributes: citizenAttrs,
            preferred_language: language,
          },
          { signal }
        ),
      ]);

      const evalMap = new Map<string, SchemeEligibilityResult>();
      for (const res of evalRes.results) {
        evalMap.set(res.scheme_id, res);
      }

      const mappedSchemes = catalogRes.items.map((item) => {
        const evalResult = evalMap.get(item.id);
        return mapBackendSchemeToFrontend(item, language, evalResult);
      });

      setSchemes(mappedSchemes);
      setEvaluations(evalRes.results);
    } catch (err: any) {
      if (err?.isAborted) return;
      console.error('[EligibilityResults] Rule engine evaluation error:', err);
      setErrorMessage(
        err?.isNetworkError
          ? t('chatErrorMessage', language)
          : t('errorLoadingSchemes', language)
      );
    } finally {
      setIsLoading(false);
    }
  }, [userProfile, language]);

  useEffect(() => {
    const controller = new AbortController();
    loadEligibilityEvaluations(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadEligibilityEvaluations]);

  const eligibleSchemes = schemes.filter((s) => s.status === 'eligible');
  const possibleSchemes = schemes.filter((s) => s.status === 'possibly_eligible');
  const ineligibleSchemes = schemes.filter((s) => s.status === 'not_eligible');

  const displayedSchemes = activeTab === 'all'
    ? schemes
    : schemes.filter((s) => s.status === activeTab);

  const firstIneligibleId = ineligibleSchemes[0]?.id;

  const handleReadSummaryAloud = () => {
    if (isSpeaking) {
      stopSpeaking();
      return;
    }
    const summaryTexts: Record<string, string> = {
      en: `You qualify for ${eligibleSchemes.length} schemes. ${possibleSchemes.length} schemes need a little more information. ${ineligibleSchemes.length} schemes you do not currently qualify for.`,
      hi: `आप ${eligibleSchemes.length} योजनाओं के लिए पात्र हो सकते हैं। ${possibleSchemes.length} योजनाओं के लिए थोड़ी और जानकारी चाहिए। ${ineligibleSchemes.length} योजनाओं के लिए आप वर्तमान में पात्र नहीं हैं।`,
      kn: `ನೀವು ${eligibleSchemes.length} ಯೋಜನೆಗಳಿಗೆ ಅರ್ಹರಾಗಿರಬಹುದು. ${possibleSchemes.length} ಯೋಜನೆಗಳಿಗೆ ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಬೇಕು. ${ineligibleSchemes.length} ಯೋಜನೆಗಳಿಗೆ ನೀವು ಪ್ರಸ್ತುತ ಅರ್ಹರಲ್ಲ.`,
      te: `మీరు ${eligibleSchemes.length} పథకాలకు అర్హులు కావచ్చు. ${possibleSchemes.length} పథకాలకు మరింత సమాచారం అవసరం. ${ineligibleSchemes.length} పథకాలకు మీరు ప్రస్తుతం అర్హులు కారు.`,
    };
    speak(summaryTexts[language] || summaryTexts.en);
  };

  return (
    <div className="min-h-screen bg-neutral-canvas pb-24">
      <Header title={t('eligibilitySummaryHeading', language)} subtitle="Rule Engine" showBack />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* Top Summary Banner */}
        <div className="bg-white rounded-card p-4 border border-neutral-mist shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-neutral-slate uppercase tracking-wider">
              {t('eligibilitySummaryHeading', language)}
            </span>
            <div className="flex items-center gap-2">
              {isTtsSupported && (
                <button
                  onClick={handleReadSummaryAloud}
                  className={`flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full border transition-all ${
                    isSpeaking
                      ? 'bg-brand-orange text-white border-brand-orange animate-pulse'
                      : 'bg-orange-50 border-orange-200 text-brand-orange hover:bg-orange-100'
                  }`}
                  aria-label={isSpeaking ? t('stopAudio', language) : t('playAudioAloud', language)}
                >
                  {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
                  <span>{isSpeaking ? t('stopAudio', language) : t('playAudioAloud', language)}</span>
                </button>
              )}
              <span className="text-[11px] font-semibold text-brand-indigo bg-brand-indigo-tint px-2.5 py-0.5 rounded-full">
                {t('ruleEngineTag', language)}
              </span>
            </div>
          </div>

          {/* Metric 3 Buckets with Plain Language Subtitles */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div
              onClick={() => setActiveTab('eligible')}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${
                activeTab === 'eligible'
                  ? 'bg-status-green-bg border-status-green ring-2 ring-status-green/30'
                  : 'bg-green-50/50 border-green-200 hover:bg-green-50'
              }`}
            >
              <span className="block font-heading font-bold text-2xl text-status-green">
                {isLoading ? '...' : eligibleSchemes.length}
              </span>
              <span className="text-xs font-bold text-status-green flex items-center justify-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 inline" /> {t('bucketYouMayBeEligible', language)}
              </span>
              <span className="text-[10px] text-green-700 block mt-0.5">High priority</span>
            </div>

            <div
              onClick={() => setActiveTab('possibly_eligible')}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${
                activeTab === 'possibly_eligible'
                  ? 'bg-status-amber-bg border-status-amber ring-2 ring-status-amber/30'
                  : 'bg-amber-50/50 border-amber-200 hover:bg-amber-50'
              }`}
            >
              <span className="block font-heading font-bold text-2xl text-status-amber">
                {isLoading ? '...' : possibleSchemes.length}
              </span>
              <span className="text-xs font-bold text-status-amber flex items-center justify-center gap-1">
                <Clock className="w-3.5 h-3.5 inline" /> {t('bucketNeedsMoreInfo', language)}
              </span>
              <span className="text-[10px] text-amber-700 block mt-0.5">A few questions left</span>
            </div>

            <div
              onClick={() => setActiveTab('not_eligible')}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${
                activeTab === 'not_eligible'
                  ? 'bg-status-red-bg border-status-red ring-2 ring-status-red/30'
                  : 'bg-red-50/50 border-red-200 hover:bg-red-50'
              }`}
            >
              <span className="block font-heading font-bold text-2xl text-status-red">
                {isLoading ? '...' : ineligibleSchemes.length}
              </span>
              <span className="text-xs font-bold text-status-red flex items-center justify-center gap-1">
                <XCircle className="w-3.5 h-3.5 inline" /> {t('bucketNotEligible', language)}
              </span>
              <span className="text-[10px] text-red-700 block mt-0.5">Clear reasons</span>
            </div>
          </div>
        </div>

        {/* Tab Filters */}
        <div className="flex items-center gap-2 border-b border-neutral-mist pb-2 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-3 py-1.5 rounded-button text-xs font-bold transition-colors whitespace-nowrap ${
              activeTab === 'all'
                ? 'bg-brand-indigo text-white shadow-sm'
                : 'text-neutral-slate hover:text-neutral-ink'
            }`}
          >
            {t('tabAll', language)} ({isLoading ? '...' : schemes.length})
          </button>
          <button
            onClick={() => setActiveTab('eligible')}
            className={`px-3 py-1.5 rounded-button text-xs font-bold transition-colors whitespace-nowrap ${
              activeTab === 'eligible'
                ? 'bg-status-green text-white shadow-sm'
                : 'text-neutral-slate hover:text-neutral-ink'
            }`}
          >
            {t('tabEligible', language)} ({isLoading ? '...' : eligibleSchemes.length})
          </button>
          <button
            onClick={() => setActiveTab('possibly_eligible')}
            className={`px-3 py-1.5 rounded-button text-xs font-bold transition-colors whitespace-nowrap ${
              activeTab === 'possibly_eligible'
                ? 'bg-status-amber text-white shadow-sm'
                : 'text-neutral-slate hover:text-neutral-ink'
            }`}
          >
            {t('tabPossiblyEligible', language)} ({isLoading ? '...' : possibleSchemes.length})
          </button>
          <button
            onClick={() => setActiveTab('not_eligible')}
            className={`px-3 py-1.5 rounded-button text-xs font-bold transition-colors whitespace-nowrap ${
              activeTab === 'not_eligible'
                ? 'bg-status-red text-white shadow-sm'
                : 'text-neutral-slate hover:text-neutral-ink'
            }`}
          >
            {t('tabNotEligible', language)} ({isLoading ? '...' : ineligibleSchemes.length})
          </button>
        </div>

        {/* Special Ineligibility Callout */}
        {activeTab === 'not_eligible' && ineligibleSchemes.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-card p-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-xs text-status-red">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>
                {t('seeRejectionReasonsCTA', language)}
              </span>
            </div>
            <button
              onClick={() => navigate(firstIneligibleId ? `/why-not-eligible/${firstIneligibleId}` : '/why-not-eligible')}
              className="text-xs font-bold text-status-red hover:underline flex items-center gap-1 flex-shrink-0 ml-2"
            >
              <span>{t('viewReasonsAction', language)}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Scheme List States */}
        {isLoading ? (
          <div className="space-y-3" role="status" aria-label={t('evaluatingEligibility', language)}>
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="bg-white rounded-card border border-neutral-mist shadow-card p-4 border-l-4 border-l-neutral-slate/20 animate-pulse space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="h-3 bg-neutral-mist rounded w-1/3"></div>
                  <div className="h-5 bg-neutral-mist rounded-full w-20"></div>
                </div>
                <div className="h-5 bg-neutral-mist rounded w-3/4"></div>
                <div className="h-3 bg-neutral-mist rounded w-1/2"></div>
                <div className="h-12 bg-neutral-canvas rounded-lg"></div>
              </div>
            ))}
          </div>
        ) : errorMessage ? (
          <div className="bg-white rounded-card p-8 border border-neutral-mist text-center space-y-3 shadow-card">
            <div className="w-10 h-10 rounded-full bg-amber-50 text-status-amber flex items-center justify-center mx-auto">
              <AlertCircle className="w-5 h-5" />
            </div>
            <h3 className="font-heading font-bold text-base text-neutral-ink">
              {errorMessage}
            </h3>
            <p className="text-xs text-neutral-slate max-w-sm mx-auto">
              {t('chatErrorMessage', language)}
            </p>
            <button
              onClick={() => loadEligibilityEvaluations()}
              className="inline-flex items-center gap-1.5 bg-brand-indigo text-white text-xs font-bold py-2.5 px-4 rounded-button hover:bg-brand-indigo-hover transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>{t('retryAction', language)}</span>
            </button>
          </div>
        ) : displayedSchemes.length > 0 ? (
          <div className="space-y-3">
            {displayedSchemes.map((scheme) => (
              <SchemeCard key={scheme.id} scheme={scheme} showMatchReasons />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-card p-8 border border-neutral-mist text-center space-y-2 shadow-card">
            <p className="text-xs text-neutral-slate">
              {t('noSchemesFoundDesc', language)}
            </p>
            <button
              onClick={() => setActiveTab('all')}
              className="text-xs text-brand-indigo font-semibold hover:underline"
            >
              {t('viewAll', language)}
            </button>
          </div>
        )}

        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};
