import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  XCircle, 
  ShieldCheck, 
  ShieldAlert, 
  AlertCircle, 
  RefreshCw, 
  HelpCircle, 
  BookOpen, 
  ExternalLink,
  ArrowRight
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { SchemeCard } from '../components/SchemeCard';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';
import { 
  evaluateSingleScheme, 
  evaluateEligibility, 
  fetchSchemeDetail, 
  fetchSchemes,
  mapUserProfileToCitizenAttributes, 
  mapBackendSchemeToFrontend,
  SchemeEligibilityResult,
  SchemeDetailSchema
} from '../services/schemeApi';
import { Scheme } from '../types';

export const WhyNotEligible: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { userProfile, language } = useApp();

  const [evaluation, setEvaluation] = useState<SchemeEligibilityResult | null>(null);
  const [schemeDetail, setSchemeDetail] = useState<SchemeDetailSchema | null>(null);
  const [eligibleAlternatives, setEligibleAlternatives] = useState<Scheme[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadWhyNotEligibleData = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setIsNotFound(false);
    setErrorMessage(null);

    try {
      const citizenAttrs = mapUserProfileToCitizenAttributes(userProfile);

      // Determine target scheme: either route parameter or default to first scheme with evaluation
      let targetSchemeId = id?.trim();

      if (!targetSchemeId) {
        // When no id provided in route, evaluate all schemes to locate first ineligible scheme
        const allEvalRes = await evaluateEligibility(
          { citizen_attributes: citizenAttrs, preferred_language: language },
          { signal }
        );
        const firstIneligible = allEvalRes.results.find((r) => r.status === 'NOT_ELIGIBLE') || allEvalRes.results[0];
        if (!firstIneligible) {
          setIsNotFound(true);
          setIsLoading(false);
          return;
        }
        targetSchemeId = firstIneligible.scheme_id;
      }

      // Concurrently query:
      // 1. Single scheme evaluation
      // 2. Scheme metadata & official citation
      // 3. Overall catalog & evaluations to find verified eligible alternatives
      const [singleEval, detailRes, catalogRes, allEvalsRes] = await Promise.all([
        evaluateSingleScheme(targetSchemeId, citizenAttrs, language, { signal }),
        fetchSchemeDetail(targetSchemeId, { signal }).catch(() => null),
        fetchSchemes({ pageSize: 50 }, { signal }).catch(() => null),
        evaluateEligibility(
          { citizen_attributes: citizenAttrs, preferred_language: language },
          { signal }
        ).catch(() => null),
      ]);

      setEvaluation(singleEval);
      setSchemeDetail(detailRes);

      // Derive strictly verified eligible alternatives from backend results only
      if (catalogRes?.items && allEvalsRes?.results) {
        const evalMap = new Map(allEvalsRes.results.map((r) => [r.scheme_id, r]));
        const alternatives: Scheme[] = [];

        for (const item of catalogRes.items) {
          if (item.id === targetSchemeId) continue;
          const itemEval = evalMap.get(item.id);
          if (itemEval?.status === 'ELIGIBLE') {
            alternatives.push(mapBackendSchemeToFrontend(item, language, itemEval));
          }
        }
        setEligibleAlternatives(alternatives.slice(0, 2));
      } else {
        setEligibleAlternatives([]);
      }
    } catch (err: any) {
      if (err?.isAborted) return;
      if (err?.statusCode === 404 || err?.status === 404) {
        setIsNotFound(true);
      } else {
        console.error('[WhyNotEligible] Failed to evaluate scheme:', err);
        setErrorMessage(
          err?.isNetworkError
            ? t('chatErrorMessage', language)
            : t('errorLoadingSchemes', language)
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [id, userProfile, language]);

  useEffect(() => {
    const controller = new AbortController();
    loadWhyNotEligibleData(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadWhyNotEligibleData]);

  const schemeTitle =
    evaluation?.scheme_name?.[language] ||
    evaluation?.scheme_name?.en ||
    schemeDetail?.names?.[language] ||
    schemeDetail?.names?.en ||
    id ||
    'Selected Scheme';

  const ministryName = schemeDetail?.ministry || 'Government of India';

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title={t('whyNotEligibleHeading', language)} subtitle="Rule Engine Audit" showBack />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* State 1: Loading Skeleton */}
        {isLoading && (
          <div className="space-y-4" role="status" aria-label={t('evaluatingEligibility', language)}>
            <div className="bg-[#FDF0F0] border border-[#8F3D3D]/30 rounded-card p-4 space-y-2 animate-pulse">
              <div className="h-4 bg-rose-200 rounded w-1/3"></div>
              <div className="h-3 bg-rose-100 rounded w-2/3"></div>
            </div>
            <div className="bg-surface rounded-card p-5 border border-sand shadow-card space-y-3 animate-pulse">
              <div className="h-4 bg-sand rounded w-1/4"></div>
              <div className="h-5 bg-sand rounded w-1/2"></div>
              <div className="h-20 bg-canvas rounded-xl"></div>
            </div>
          </div>
        )}

        {/* State 2: 404 Not Found */}
        {!isLoading && isNotFound && (
          <div className="bg-surface rounded-card p-8 border border-sand text-center space-y-4 shadow-card">
            <div className="w-12 h-12 rounded-full bg-[#FDF0F0] text-[#8F3D3D] flex items-center justify-center mx-auto">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h2 className="font-heading font-bold text-lg text-ink">
              {t('schemeNotFoundTitle', language)}
            </h2>
            <p className="text-xs text-ink/70 max-w-md mx-auto">
              {t('schemeNotFoundDesc', language)}
            </p>
            <button
              onClick={() => navigate('/browse')}
              className="inline-flex items-center gap-2 bg-forest hover:bg-forest-deep text-white text-xs font-bold py-2.5 px-5 rounded-full transition-colors shadow-xs"
            >
              <span>{t('backToBrowseCTA', language)}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* State 3: Error Recovery */}
        {!isLoading && !isNotFound && errorMessage && (
          <div className="bg-surface rounded-card p-8 border border-sand text-center space-y-4 shadow-card">
            <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-800 flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="font-heading font-bold text-base text-ink">
              {errorMessage}
            </h2>
            <button
              onClick={() => loadWhyNotEligibleData()}
              className="inline-flex items-center gap-1.5 bg-forest hover:bg-forest-deep text-white text-xs font-bold py-2.5 px-4 rounded-full transition-colors shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>{t('retryAction', language)}</span>
            </button>
          </div>
        )}

        {/* State 4: Loaded Evaluation Result */}
        {!isLoading && !isNotFound && evaluation && (
          <>
            {/* Top Explanation Banner */}
            <div className="bg-[#FDF0F0] border border-[#8F3D3D]/30 rounded-card p-4 space-y-2">
              <div className="flex items-center gap-2 text-[#8F3D3D] font-bold text-sm">
                <XCircle className="w-5 h-5 flex-shrink-0" />
                <span>{t('whyNotEligibleHeading', language)}</span>
              </div>
              <p className="text-xs text-ink/75 leading-relaxed">
                {evaluation.summary?.[language] || evaluation.summary?.en || t('whyNotEligibleSubtext', language)}
              </p>
            </div>

            {/* Failed Criteria Card */}
            <div className="bg-surface rounded-card p-5 border border-sand shadow-card space-y-3">
              <span className="text-xs font-semibold text-ink/60 uppercase">
                {schemeTitle}
              </span>
              <h2 className="font-heading font-bold text-base text-ink">
                {t('failedCriteriaHeading', language)}:
              </h2>

              <div className="space-y-3">
                {evaluation.conditions_failed && evaluation.conditions_failed.length > 0 ? (
                  evaluation.conditions_failed.map((fail, idx) => {
                    const failText = fail.reason?.[language] || fail.reason?.en || `Did not satisfy: ${fail.field}`;
                    const citation = fail.citation;

                    return (
                      <div key={idx} className="bg-canvas border border-[#8F3D3D]/25 rounded-xl p-3.5 flex items-start gap-3">
                        <span className="w-5 h-5 rounded-full bg-[#FDF0F0] text-[#8F3D3D] font-bold flex items-center justify-center text-xs flex-shrink-0 mt-0.5">
                          ✕
                        </span>
                        <div className="flex-1 space-y-1">
                          <span className="text-xs font-bold text-[#8F3D3D] block">
                            {t('conditionNotMetPrefix', language)} {idx + 1}
                          </span>
                          <p className="text-xs text-ink leading-relaxed">
                            {failText}
                          </p>

                          {/* Authoritative Citation for Failed Clause */}
                          {citation && (
                            <div className="mt-2 pt-2 border-t border-sand text-[11px] text-ink/65 flex items-center gap-2 flex-wrap">
                              <BookOpen className="w-3.5 h-3.5 text-forest flex-shrink-0" />
                              {citation.clause && (
                                <span className="font-semibold text-ink">{citation.clause}</span>
                              )}
                              {citation.url && (
                                <a
                                  href={citation.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-0.5 text-forest hover:underline font-medium"
                                >
                                  <span>{t('officialSourceLink', language)}</span>
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-xs text-ink/70">
                    {t('whyNotEligibleSubtext', language)}
                  </p>
                )}
              </div>
            </div>

            {/* Preserved UNKNOWN Criteria (Pending Information) */}
            {evaluation.missing_information && evaluation.missing_information.length > 0 && (
              <div className="bg-surface rounded-card p-5 border border-[#9A6B12]/30 shadow-card space-y-3">
                <div className="flex items-center gap-2 text-[#9A6B12]">
                  <HelpCircle className="w-5 h-5 flex-shrink-0" />
                  <h3 className="font-heading font-bold text-sm text-ink">
                    {t('unknownCriteriaHeading', language)}
                  </h3>
                </div>
                <p className="text-xs text-ink/70 leading-relaxed">
                  {t('unknownCriteriaDesc', language)}
                </p>

                <div className="space-y-2 pt-1">
                  {evaluation.missing_information.map((miss, idx) => {
                    const promptText = miss.prompt?.[language] || miss.prompt?.en || `Missing: ${miss.field}`;
                    return (
                      <div key={idx} className="bg-[#FEF8EA] border border-[#9A6B12]/20 rounded-lg p-3 text-xs text-ink flex items-start gap-2.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#9A6B12] flex-shrink-0 mt-2"></span>
                        <div className="flex-1">
                          <span className="font-bold text-ink block">{promptText}</span>
                          <span className="text-[11px] text-ink/60 mt-0.5 block">
                            {t('requiredAttributeField', language) || 'Attribute'}: {miss.field} ({miss.expected_type})
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Official Guideline Rule Citation */}
            <div className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-2">
              <div className="flex items-center gap-2 text-forest font-bold text-xs">
                <ShieldCheck className="w-4 h-4 text-forest" />
                <span>{t('officialSourceSubtitle', language)}</span>
              </div>
              <p className="text-xs text-ink/70 leading-relaxed">
                {ministryName}. {t('onboardingPrivacyDesc', language)}
              </p>
              <button
                onClick={() => navigate('/profile')}
                className="text-xs font-bold text-forest hover:underline inline-block pt-1"
              >
                {t('editProfile', language)} →
              </button>
            </div>

            {/* Recommended Alternatives Section */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <h3 className="font-heading font-bold text-base text-ink">
                  {t('recommendedAlternativesHeading', language)}
                </h3>
                {eligibleAlternatives.length > 0 && (
                  <span className="text-xs font-bold text-[#1F7A4D] bg-[#EAF5EE] px-2.5 py-0.5 rounded-full border border-[#1F7A4D]/20">
                    {t('statusEligible', language)}
                  </span>
                )}
              </div>

              {eligibleAlternatives.length > 0 ? (
                <div className="space-y-3">
                  {eligibleAlternatives.map((alt) => (
                    <SchemeCard key={alt.id} scheme={alt} />
                  ))}
                </div>
              ) : (
                <div className="bg-surface rounded-card p-6 border border-sand shadow-card text-center space-y-2">
                  <p className="text-xs text-ink/65">
                    {t('noAlternativesFound', language)}
                  </p>
                  <button
                    onClick={() => navigate('/profile')}
                    className="text-xs text-forest font-semibold hover:underline"
                  >
                    {t('editProfile', language)}
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};
