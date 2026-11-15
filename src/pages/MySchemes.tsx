import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookmarkCheck,
  CheckCircle2,
  AlertCircle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Compass,
  User,
  ArrowRight,
  Clock,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';
import {
  fetchSchemes,
  evaluateEligibility,
  mapBackendSchemeToFrontend,
  mapUserProfileToCitizenAttributes,
  SchemeEligibilityResult,
} from '../services/schemeApi';
import { Scheme } from '../types';

type TabKey = 'eligible' | 'needs_info' | 'not_eligible' | 'saved' | 'recent';

export const MySchemes: React.FC = () => {
  const navigate = useNavigate();
  const {
    userProfile,
    hasConfirmedProfile,
    savedSchemeIds,
    toggleSaveScheme,
    recentlyViewedSchemeIds,
    language,
  } = useApp();

  const [activeTab, setActiveTab] = useState<TabKey>('eligible');
  const [schemesById, setSchemesById] = useState<Record<string, Scheme>>({});
  const [evaluations, setEvaluations] = useState<SchemeEligibilityResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const citizenAttributes = useMemo(
    () => mapUserProfileToCitizenAttributes(userProfile),
    [userProfile]
  );
  const hasAnyAttribute = Object.keys(citizenAttributes).length > 0;

  const runEvaluation = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const schemesRes = await fetchSchemes({ pageSize: 50 });
      const map: Record<string, Scheme> = {};
      for (const item of schemesRes.items || []) {
        map[item.id] = mapBackendSchemeToFrontend(item, language);
      }
      setSchemesById(map);

      if (hasAnyAttribute) {
        const evalRes = await evaluateEligibility({
          citizen_attributes: citizenAttributes,
          preferred_language: language,
        });
        const normalized = (evalRes.results || []).map((ev) => {
          if (ev.status === 'POSSIBLY_ELIGIBLE') {
            return {
              ...ev,
              status:
                ev.missing_information && ev.missing_information.length > 0
                  ? ('NEEDS_MORE_INFORMATION' as const)
                  : ('NOT_VERIFIED' as const),
            };
          }
          return ev;
        });
        setEvaluations(normalized);
      } else {
        setEvaluations([]);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || t('errorLoadingSchemes', language));
    } finally {
      setIsLoading(false);
    }
  }, [citizenAttributes, hasAnyAttribute, language]);

  useEffect(() => {
    runEvaluation();
  }, [runEvaluation]);

  const eligibleList = useMemo(
    () => evaluations.filter((e) => e.status === 'ELIGIBLE'),
    [evaluations]
  );
  const needsInfoList = useMemo(
    () =>
      evaluations.filter(
        (e) => e.status === 'NEEDS_MORE_INFORMATION' || e.status === 'NOT_VERIFIED' || e.status === 'POSSIBLY_ELIGIBLE'
      ),
    [evaluations]
  );
  const notEligibleList = useMemo(
    () => evaluations.filter((e) => e.status === 'NOT_ELIGIBLE'),
    [evaluations]
  );

  useEffect(() => {
    if (!hasAnyAttribute && savedSchemeIds.length > 0) {
      setActiveTab('saved');
    }
  }, [hasAnyAttribute, savedSchemeIds.length]);

  const renderEvaluationCard = (ev: SchemeEligibilityResult) => {
    const scheme = schemesById[ev.scheme_id];
    const title = ev.scheme_name?.[language] || ev.scheme_name?.en || scheme?.name || ev.scheme_id;
    const summary = ev.summary?.[language] || ev.summary?.en || '';

    const statusConfig = {
      ELIGIBLE: {
        badge: 'Eligible',
        cls: 'bg-[#EAF5EE] text-[#1F7A4D] border-[#1F7A4D]/30',
        Icon: CheckCircle2,
      },
      NEEDS_MORE_INFORMATION: {
        badge: 'Needs More Info',
        cls: 'bg-[#FEF8EA] text-[#9A6B12] border-[#9A6B12]/30',
        Icon: HelpCircle,
      },
      NOT_VERIFIED: {
        badge: 'Not Verified',
        cls: 'bg-canvas text-ink/60 border-sand',
        Icon: AlertCircle,
      },
      POSSIBLY_ELIGIBLE: {
        badge: 'Needs More Info',
        cls: 'bg-[#FEF8EA] text-[#9A6B12] border-[#9A6B12]/30',
        Icon: HelpCircle,
      },
      NOT_ELIGIBLE: {
        badge: 'Not Eligible',
        cls: 'bg-[#FDF0F0] text-[#8F3D3D] border-[#8F3D3D]/30',
        Icon: XCircle,
      },
    }[ev.status];

    const StatusIcon = statusConfig.Icon;

    return (
      <div
        key={ev.scheme_id}
        className="bg-surface rounded-card border border-sand shadow-card p-4 space-y-3"
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            {scheme?.ministry && (
              <span className="text-[11px] font-semibold text-ink/60 uppercase block">
                {scheme.ministry}
              </span>
            )}
            <h3
              onClick={() => navigate(`/scheme/${ev.scheme_id}`)}
              className="font-heading font-bold text-base text-ink hover:text-forest cursor-pointer"
            >
              {title}
            </h3>
          </div>
          <span
            className={`inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full border flex-shrink-0 ${statusConfig.cls}`}
          >
            <StatusIcon className="w-3.5 h-3.5" />
            <span>{statusConfig.badge}</span>
          </span>
        </div>

        <p className="text-xs text-ink/75 leading-relaxed">{summary}</p>

        {scheme?.benefit && (
          <div className="bg-sage/40 border border-sage/60 p-2.5 rounded-lg flex items-center justify-between text-xs">
            <span className="font-semibold text-forest">Benefit:</span>
            <span className="font-bold text-forest">{scheme.benefit}</span>
          </div>
        )}

        {/* Understandable reasons for NOT_ELIGIBLE */}
        {ev.status === 'NOT_ELIGIBLE' && ev.conditions_failed?.length > 0 && (
          <div className="bg-red-50/70 border border-red-100 rounded-lg p-2.5 space-y-1">
            <span className="text-[11px] font-bold text-rose-800 block">Unmet Criteria:</span>
            <ul className="list-disc list-inside text-xs text-ink space-y-0.5">
              {ev.conditions_failed.slice(0, 3).map((cond) => (
                <li key={cond.condition_id}>
                  {cond.reason?.[language] || cond.reason?.en || `${cond.field} condition not met`}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Missing attributes for NEEDS_MORE_INFORMATION */}
        {(ev.status === 'NEEDS_MORE_INFORMATION' || ev.status === 'POSSIBLY_ELIGIBLE') &&
          ev.missing_information?.length > 0 && (
          <div className="bg-amber-50/70 border border-amber-200 rounded-lg p-2.5 space-y-1">
            <span className="text-[11px] font-bold text-amber-900 block">
              Information needed to confirm:
            </span>
            <ul className="list-disc list-inside text-xs text-ink space-y-0.5">
              {ev.missing_information.slice(0, 3).map((m) => (
                <li key={m.field}>{m.prompt?.[language] || m.prompt?.en || m.field}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={() => navigate(`/scheme/${ev.scheme_id}`)}
            className="flex-1 py-2 px-3 bg-forest hover:bg-forest-deep text-white font-bold text-xs rounded-full flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>{t('viewDetails', language)}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => toggleSaveScheme(ev.scheme_id)}
            className="py-2 px-3 bg-surface hover:bg-sand/30 text-ink font-semibold text-xs rounded-full border border-sand transition-colors"
          >
            {savedSchemeIds.includes(ev.scheme_id) ? t('savedBadge', language) : t('saveToLocker', language)}
          </button>
        </div>
      </div>
    );
  };

  const renderSchemeSummaryCard = (sid: string, allowRemove: boolean) => {
    const scheme = schemesById[sid];
    return (
      <div
        key={sid}
        className="bg-white rounded-card border border-neutral-mist shadow-card p-4 space-y-2.5"
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="text-[11px] font-semibold text-neutral-slate uppercase block">
              {scheme?.ministry || 'Government of India'}
            </span>
            <h3
              onClick={() => navigate(`/scheme/${sid}`)}
              className="font-heading font-bold text-base text-neutral-ink hover:text-brand-indigo cursor-pointer"
            >
              {scheme?.name || sid.toUpperCase()}
            </h3>
          </div>
          {allowRemove && (
            <button
              type="button"
              onClick={() => toggleSaveScheme(sid)}
              className="p-1.5 text-neutral-slate hover:text-status-red rounded-full hover:bg-neutral-mist/40"
              title={t('removeFromLocker', language)}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
        {scheme?.benefit && (
          <p className="text-xs text-brand-teal font-semibold">{scheme.benefit}</p>
        )}
        <button
          type="button"
          onClick={() => navigate(`/scheme/${sid}`)}
          className="w-full py-2 px-3 bg-neutral-canvas hover:bg-neutral-mist/40 text-brand-indigo font-bold text-xs rounded-button border border-neutral-mist flex items-center justify-center gap-1"
        >
          <span>{t('viewDetails', language)}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title={t('navLocker', language)} subtitle="Session Eligibility Discovery" showBack />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* Top Summary & Re-evaluate Card */}
        <div className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-full bg-sage text-forest flex items-center justify-center flex-shrink-0">
                <BookmarkCheck className="w-5 h-5" />
              </div>
              <div>
                <h1 className="font-heading font-bold text-base text-ink">
                  {t('navLocker', language)}
                </h1>
                <p className="text-xs text-ink/65">
                  Preliminary scheme matches for your active session profile
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => navigate('/profile')}
                className="py-2 px-3 text-xs font-semibold text-ink bg-surface hover:bg-sand/30 rounded-full border border-sand inline-flex items-center gap-1.5"
              >
                <User className="w-3.5 h-3.5 text-forest" />
                <span>{t('editProfile', language)}</span>
              </button>
              <button
                type="button"
                onClick={runEvaluation}
                disabled={isLoading}
                className="py-2 px-3 text-xs font-bold text-white bg-forest hover:bg-forest-deep rounded-full inline-flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                <span>Re-evaluate</span>
              </button>
            </div>
          </div>

          <div className="flex items-start gap-2 text-xs text-forest bg-sage/50 p-2.5 rounded-lg border border-sage/60">
            <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5 text-forest" />
            <span>
              Session-only results: Your profile and eligibility matches are kept in memory only and cleared when you close or reset your session.
            </span>
          </div>
        </div>

        {/* Prompt to set up temporary profile if none exists */}
        {!hasAnyAttribute && !hasConfirmedProfile && (
          <div className="bg-amber-50 border border-amber-200 rounded-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <h2 className="font-heading font-bold text-sm text-amber-950">
                No active eligibility profile yet
              </h2>
              <p className="text-xs text-amber-900/90">
                Share your age, occupation, income, land ownership, state, and caste category to see which schemes you may qualify for.
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className="bg-forest hover:bg-forest-deep text-white font-bold py-2.5 px-4 rounded-full text-xs flex-shrink-0 inline-flex items-center gap-1.5 shadow-xs"
            >
              <User className="w-4 h-4" />
              <span>Set Up Profile</span>
            </button>
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {[
            { id: 'eligible' as TabKey, label: `Eligible (${eligibleList.length})` },
            { id: 'needs_info' as TabKey, label: `Needs Info (${needsInfoList.length})` },
            { id: 'not_eligible' as TabKey, label: `Not Eligible (${notEligibleList.length})` },
            { id: 'saved' as TabKey, label: `Saved (${savedSchemeIds.length})` },
            { id: 'recent' as TabKey, label: `Recently Viewed (${recentlyViewedSchemeIds.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 rounded-full text-xs font-bold whitespace-nowrap border transition-colors ${
                activeTab === tab.id
                  ? 'bg-forest text-white border-forest shadow-xs'
                  : 'bg-surface text-ink/70 border-sand hover:bg-sand/30'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Loading / Error */}
        {isLoading && (
          <div className="bg-surface rounded-card p-6 border border-sand text-center text-xs text-ink/70 space-y-2">
            <RefreshCw className="w-5 h-5 text-forest animate-spin mx-auto" />
            <p>Evaluating schemes against deterministic eligibility rules...</p>
          </div>
        )}

        {errorMessage && (
          <div className="bg-red-50 border border-red-200 rounded-card p-3.5 flex items-center justify-between gap-3 text-xs text-status-red">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button type="button" onClick={runEvaluation} className="font-bold underline">
              Retry
            </button>
          </div>
        )}

        {/* Tab Contents */}
        {!isLoading && activeTab === 'eligible' && (
          <div className="space-y-3">
            {eligibleList.length > 0 ? (
              eligibleList.map(renderEvaluationCard)
            ) : (
              <div className="bg-white rounded-card p-6 border border-neutral-mist text-center text-xs text-neutral-slate space-y-2">
                <p>
                  {hasAnyAttribute
                    ? 'No schemes matched all criteria as fully Eligible yet. Check "Needs Info" to see schemes requiring additional details.'
                    : 'Complete your temporary profile to evaluate eligible schemes.'}
                </p>
              </div>
            )}
          </div>
        )}

        {!isLoading && activeTab === 'needs_info' && (
          <div className="space-y-3">
            {needsInfoList.length > 0 ? (
              needsInfoList.map(renderEvaluationCard)
            ) : (
              <div className="bg-white rounded-card p-6 border border-neutral-mist text-center text-xs text-neutral-slate">
                No schemes waiting on additional profile details.
              </div>
            )}
          </div>
        )}

        {!isLoading && activeTab === 'not_eligible' && (
          <div className="space-y-3">
            {notEligibleList.length > 0 ? (
              notEligibleList.map(renderEvaluationCard)
            ) : (
              <div className="bg-white rounded-card p-6 border border-neutral-mist text-center text-xs text-neutral-slate">
                No schemes marked Not Eligible for your current profile.
              </div>
            )}
          </div>
        )}

        {!isLoading && activeTab === 'saved' && (
          <div className="space-y-3">
            {savedSchemeIds.length > 0 ? (
              savedSchemeIds.map((sid) => renderSchemeSummaryCard(sid, true))
            ) : (
              <div className="bg-white rounded-card p-8 border border-neutral-mist text-center space-y-3">
                <Compass className="w-8 h-8 text-neutral-slate mx-auto" />
                <p className="text-xs text-neutral-slate">
                  No schemes saved in this session yet.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/browse')}
                  className="bg-brand-indigo hover:bg-brand-indigo-hover text-white font-bold py-2 px-4 rounded-button text-xs"
                >
                  {t('browseSchemes', language)}
                </button>
              </div>
            )}
          </div>
        )}

        {!isLoading && activeTab === 'recent' && (
          <div className="space-y-3">
            {recentlyViewedSchemeIds.length > 0 ? (
              recentlyViewedSchemeIds.map((sid) => renderSchemeSummaryCard(sid, false))
            ) : (
              <div className="bg-white rounded-card p-6 border border-neutral-mist text-center text-xs text-neutral-slate flex flex-col items-center gap-2">
                <Clock className="w-5 h-5 text-neutral-slate" />
                <span>Schemes you open during this session will appear here.</span>
              </div>
            )}
          </div>
        )}

        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};

