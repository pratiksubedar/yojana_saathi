import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Bookmark, 
  BookmarkCheck, 
  ExternalLink, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Calendar, 
  Building2, 
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Volume2,
  VolumeX,
  AlertCircle,
  RefreshCw,
  Clock,
  BookOpen,
  ListOrdered,
  Users,
  Sparkles
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { StatusBadge } from '../components/StatusBadge';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { useApp } from '../context/AppContext';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';
import { t } from '../data/translations';
import { 
  fetchSchemeDetail, 
  fetchSchemeProvenance, 
  mapBackendSchemeToFrontend,
  SchemeDetailSchema,
  SchemeProvenanceResponse
} from '../services/schemeApi';
import { Scheme } from '../types';

export const SchemeDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isSchemeSaved, toggleSaveScheme, language, voiceSpeed } = useApp();

  const [scheme, setScheme] = useState<Scheme | null>(null);
  const [rawDetail, setRawDetail] = useState<SchemeDetailSchema | null>(null);
  const [provenance, setProvenance] = useState<SchemeProvenanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { isSupported: isTtsSupported, isSpeaking, speak, stop: stopSpeaking } = useSpeechSynthesis(language, voiceSpeed);

  useEffect(() => {
    return () => {
      stopSpeaking();
    };
  }, [stopSpeaking]);

  const loadSchemeData = useCallback(async (signal?: AbortSignal) => {
    if (!id || !id.trim()) {
      setIsNotFound(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setIsNotFound(false);
    setErrorMessage(null);

    try {
      // Concurrently fetch authoritative scheme detail and official provenance
      const [detailRes, provenanceRes] = await Promise.all([
        fetchSchemeDetail(id, { signal }),
        fetchSchemeProvenance(id, { signal }).catch((err) => {
          console.warn('[SchemeDetail] Provenance unavailable:', err?.message || err);
          return null;
        }),
      ]);

      setRawDetail(detailRes);
      setProvenance(provenanceRes);
      setScheme(mapBackendSchemeToFrontend(detailRes, language));
    } catch (err: any) {
      if (err?.isAborted) return;
      console.error('[SchemeDetail] Fetch error:', err);
      if (err?.status === 404) {
        setIsNotFound(true);
      } else {
        setErrorMessage(
          err?.isNetworkError
            ? t('chatErrorMessage', language)
            : t('errorLoadingSchemes', language)
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [id, language]);

  useEffect(() => {
    const controller = new AbortController();
    loadSchemeData(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadSchemeData]);

  // Re-map localized strings when user switches language in header
  useEffect(() => {
    if (rawDetail) {
      setScheme(mapBackendSchemeToFrontend(rawDetail, language));
    }
  }, [language, rawDetail]);

  const handleReadSchemeAloud = () => {
    if (!scheme) return;
    if (isSpeaking) {
      stopSpeaking();
    } else {
      const narrative = `${scheme.name}. ${scheme.benefitHighlight}. ${scheme.description}`;
      speak(narrative, { lang: language, rate: voiceSpeed });
    }
  };

  const saved = scheme ? isSchemeSaved(scheme.id) : false;

  return (
    <div className="min-h-screen bg-neutral-canvas pb-24">
      <Header 
        title={scheme ? scheme.name : t('viewDetails', language)} 
        subtitle={t('viewDetails', language)} 
        showBack 
      />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* State 1: Loading Skeleton */}
        {isLoading && (
          <div className="space-y-4" role="status" aria-label={t('loadingSchemes', language)}>
            <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-4 animate-pulse">
              <div className="h-4 bg-neutral-mist rounded w-1/3"></div>
              <div className="h-6 bg-neutral-mist rounded w-2/3"></div>
              <div className="h-4 bg-neutral-mist rounded w-1/2"></div>
              <div className="h-16 bg-neutral-canvas rounded-xl"></div>
              <div className="h-12 bg-neutral-mist/60 rounded"></div>
            </div>
            <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-3 animate-pulse">
              <div className="h-5 bg-neutral-mist rounded w-1/4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-neutral-mist rounded w-full"></div>
                <div className="h-4 bg-neutral-mist rounded w-5/6"></div>
              </div>
            </div>
          </div>
        )}

        {/* State 2: Not Found (404 / Invalid ID) */}
        {!isLoading && isNotFound && (
          <div className="bg-white rounded-card p-8 border border-neutral-mist text-center space-y-4 shadow-card">
            <div className="w-12 h-12 rounded-full bg-status-red-bg text-status-red flex items-center justify-center mx-auto">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h2 className="font-heading font-bold text-lg text-neutral-ink">
              {t('schemeNotFoundTitle', language)}
            </h2>
            <p className="text-xs text-neutral-slate max-w-md mx-auto">
              {t('schemeNotFoundDesc', language)}
            </p>
            <button
              onClick={() => navigate('/browse')}
              className="inline-flex items-center gap-2 bg-brand-indigo text-white text-xs font-bold py-2.5 px-5 rounded-button hover:bg-brand-indigo-hover transition-colors"
            >
              <span>{t('backToBrowseCTA', language)}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* State 3: Network / Server Error */}
        {!isLoading && !isNotFound && errorMessage && (
          <div className="bg-white rounded-card p-8 border border-neutral-mist text-center space-y-4 shadow-card">
            <div className="w-12 h-12 rounded-full bg-amber-50 text-status-amber flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="font-heading font-bold text-base text-neutral-ink">
              {errorMessage}
            </h2>
            <p className="text-xs text-neutral-slate max-w-md mx-auto">
              {t('chatErrorMessage', language)}
            </p>
            <button
              onClick={() => loadSchemeData()}
              className="inline-flex items-center gap-1.5 bg-brand-indigo text-white text-xs font-bold py-2.5 px-4 rounded-button hover:bg-brand-indigo-hover transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>{t('retryAction', language)}</span>
            </button>
          </div>
        )}

        {/* State 4: Loaded Scheme Details in Exact 7-Step Hierarchy */}
        {!isLoading && !isNotFound && scheme && (
          <>
            {/* 1. Who it is for */}
            <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-1.5 text-xs text-neutral-slate font-medium mb-1">
                    <Building2 className="w-3.5 h-3.5 text-forest" />
                    <span>{scheme.ministry}</span>
                  </div>
                  <h1 className="font-heading font-bold text-xl sm:text-2xl text-neutral-ink">
                    {scheme.name}
                  </h1>
                  <p className="text-sm font-medium text-neutral-slate">
                    {scheme.nativeName}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2 flex-shrink-0">
                  <StatusBadge status={scheme.status} size="md" />
                  <div className="flex items-center gap-2">
                    {isTtsSupported && (
                      <button
                        onClick={handleReadSchemeAloud}
                        className={`flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-xl border transition-all ${
                          isSpeaking
                            ? 'bg-brand-orange text-white border-brand-orange shadow-md animate-pulse'
                            : 'bg-orange-50 border-orange-200 text-brand-orange hover:bg-orange-100'
                        }`}
                        aria-label={isSpeaking ? t('stopAudio', language) : t('readSchemeToMe', language)}
                      >
                        {isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4 text-brand-orange" />}
                        <span>{isSpeaking ? t('stopAudio', language) : t('readSchemeToMe', language)}</span>
                      </button>
                    )}
                    <button
                      onClick={() => toggleSaveScheme(scheme.id)}
                      className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl border transition-colors ${
                        saved
                          ? 'bg-brand-indigo-tint border-brand-indigo text-brand-indigo'
                          : 'bg-white border-neutral-mist text-neutral-slate hover:text-neutral-ink'
                      }`}
                      aria-label={saved ? t('removeFromLocker', language) : t('saveToLocker', language)}
                    >
                      {saved ? <BookmarkCheck className="w-4 h-4 fill-brand-indigo" /> : <Bookmark className="w-4 h-4" />}
                      <span>{saved ? t('savedBadge', language) : t('saveToLocker', language)}</span>
                    </button>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-neutral-mist/50">
                <h2 className="text-xs font-bold text-forest uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-forest" />
                  <span>1. Who it is for ({t('sevenStepsTitle1', language)})</span>
                </h2>
                <p className="text-sm text-neutral-ink leading-relaxed">
                  {scheme.description}
                </p>
                <div className="mt-2 text-xs font-medium text-neutral-slate">
                  <span>{t('sevenStepsTitle2', language)}</span>
                </div>
                {scheme.status === 'eligible' && (
                  <p className="text-xs text-status-green font-semibold mt-1 bg-green-50 p-2 rounded-lg border border-green-200">
                    ✓ Based on your profile, you satisfy the primary eligibility criteria for this scheme.
                  </p>
                )}
                {scheme.status === 'possibly_eligible' && (
                  <p className="text-xs text-status-amber font-semibold mt-1 bg-amber-50 p-2 rounded-lg border border-amber-200">
                    ⏳ You may qualify for this scheme pending verification of remaining statutory documents.
                  </p>
                )}
              </div>
            </div>

            {/* 2. What benefit it provides */}
            <div className="bg-gradient-to-r from-teal-50 to-emerald-50 border border-teal-200 rounded-card p-5 shadow-card space-y-2">
              <h2 className="text-xs font-bold text-brand-teal uppercase tracking-wide flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>2. What benefit it provides ({t('sevenStepsTitle3', language)})</span>
              </h2>
              <p className="font-heading font-bold text-lg sm:text-xl text-emerald-800 leading-snug">
                {scheme.benefitHighlight}
              </p>
              {scheme.benefit && scheme.benefit !== scheme.benefitHighlight && (
                <p className="text-xs text-ink/75 leading-relaxed pt-1 border-t border-teal-200/60">
                  {scheme.benefit}
                </p>
              )}
            </div>

            {/* 3. Eligibility criteria */}
            <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-3">
              <h2 className="font-heading font-bold text-base text-neutral-ink flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-status-green" />
                <span>3. Eligibility criteria ({t('sevenStepsTitle4', language)})</span>
              </h2>

              <div className="space-y-2.5">
                {scheme.criteriaList.map((crit, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-neutral-ink leading-relaxed">
                    <span className="w-5 h-5 rounded-full bg-status-green-bg text-status-green flex items-center justify-center font-bold text-[11px] flex-shrink-0 mt-0.5">
                      ✓
                    </span>
                    <span>{crit}</span>
                  </div>
                ))}
              </div>

              {scheme.exclusions.length > 0 && (
                <div className="pt-3 border-t border-neutral-mist/60 space-y-2">
                  <span className="text-xs font-bold text-status-red block">
                    {t('exclusionsHeading', language)}:
                  </span>
                  {scheme.exclusions.map((excl, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-neutral-slate leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-status-red flex-shrink-0 mt-2"></span>
                      <span>{excl}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 4. Required documents */}
            <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-heading font-bold text-base text-neutral-ink flex items-center gap-2">
                  <FileText className="w-5 h-5 text-brand-indigo" />
                  <span>4. Required documents ({t('sevenStepsTitle5', language)})</span>
                </h2>
                <button
                  onClick={() => navigate(`/checklist/${scheme.id}`)}
                  className="text-xs font-semibold text-brand-indigo hover:underline flex items-center gap-1"
                >
                  {t('viewDocumentsCTA', language)} <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-neutral-ink">
                <div className="p-2.5 rounded-lg bg-neutral-canvas border border-neutral-mist/60 flex items-center gap-2">
                  <span className="text-brand-indigo font-bold">📄</span>
                  <span>Aadhaar Card / Official Identity Proof</span>
                </div>
                <div className="p-2.5 rounded-lg bg-neutral-canvas border border-neutral-mist/60 flex items-center gap-2">
                  <span className="text-brand-indigo font-bold">🏦</span>
                  <span>Active Bank Account Passbook (DBT Linked)</span>
                </div>
                {scheme.id.includes('kisan') || scheme.id.includes('kcc') ? (
                  <div className="p-2.5 rounded-lg bg-neutral-canvas border border-neutral-mist/60 flex items-center gap-2">
                    <span className="text-brand-indigo font-bold">🌾</span>
                    <span>Landholding Records (RoR / Khatian / Khatauni)</span>
                  </div>
                ) : null}
              </div>
            </div>

            {/* 5. How to apply */}
            <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-3">
              <h2 className="font-heading font-bold text-base text-neutral-ink flex items-center gap-2">
                <ListOrdered className="w-5 h-5 text-brand-indigo" />
                <span>5. How to apply ({t('sevenStepsTitle6', language)})</span>
              </h2>

              <div className="space-y-2.5">
                {(scheme.applicationSteps && scheme.applicationSteps.length > 0
                  ? scheme.applicationSteps
                  : [
                      'Visit the nearest Common Service Centre (CSC) or official online portal.',
                      'Fill out the application form with your Aadhaar and bank details.',
                      'Submit the required identity and category documents for departmental verification.',
                    ]
                ).map((step, idx) => (
                  <div key={idx} className="flex items-start gap-3 text-xs text-neutral-ink leading-relaxed">
                    <span className="w-5 h-5 rounded-full bg-brand-indigo-tint text-brand-indigo flex items-center justify-center font-bold text-[11px] flex-shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 6. Official source and last verification date */}
            <div className="bg-white rounded-card p-5 border border-indigo-100 shadow-card space-y-3">
              <h2 className="font-heading font-bold text-base text-brand-indigo flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-brand-indigo" />
                <span>6. Official source and last verification date ({t('sevenStepsTitle7', language)})</span>
              </h2>

              <div className="space-y-2 text-xs text-neutral-slate">
                <div className="flex items-center justify-between gap-2 p-3 rounded-lg bg-neutral-canvas border border-neutral-mist/60 flex-wrap">
                  <div className="flex items-center gap-1.5 font-medium text-neutral-ink">
                    <Calendar className="w-4 h-4 text-neutral-slate" />
                    <span>{t('lastUpdatedLabel', language)}: {scheme.lastUpdated}</span>
                  </div>
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-green-50 text-status-green border border-green-200">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    {provenance?.verification?.verification_status || 'Verified Official'}
                  </span>
                </div>

                <a
                  href={scheme.officialUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full bg-brand-indigo hover:bg-brand-indigo-hover text-white font-bold py-3 px-5 rounded-xl shadow flex items-center justify-center gap-2 text-sm transition-all"
                >
                  <span>{t('visitOfficialPortal', language)} ({scheme.portalName})</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>
            </div>

            {/* Read Aloud Bottom Floating Dock */}
            {isTtsSupported && (
              <div className="flex justify-center pt-2">
                <button
                  onClick={handleReadSchemeAloud}
                  className={`flex items-center gap-2 font-bold px-5 py-3 rounded-2xl shadow-lg border transition-all ${
                    isSpeaking
                      ? 'bg-brand-orange text-white border-brand-orange animate-pulse'
                      : 'bg-white border-brand-indigo text-brand-indigo hover:bg-brand-indigo-tint'
                  }`}
                >
                  {isSpeaking ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5 text-brand-indigo" />}
                  <span>{isSpeaking ? t('stopAudio', language) : t('readSchemeToMe', language)}</span>
                </button>
              </div>
            )}
          </>
        )}

        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};
