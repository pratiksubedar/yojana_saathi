import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  CheckSquare, 
  Square, 
  ExternalLink, 
  MapPin, 
  BookmarkCheck, 
  AlertCircle, 
  RefreshCw, 
  ShieldAlert, 
  ArrowRight,
  CheckCircle2,
  ListOrdered
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';
import { 
  fetchDocumentChecklist, 
  markDocumentCollected, 
  fetchSchemeDetail, 
  SchemeChecklistResponse, 
  SchemeDetailSchema 
} from '../services/schemeApi';
import { getSessionId } from '../services/chatApi';

export const DocumentChecklist: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isSchemeSaved, toggleSaveScheme, language } = useApp();

  const [checklist, setChecklist] = useState<SchemeChecklistResponse | null>(null);
  const [schemeDetail, setSchemeDetail] = useState<SchemeDetailSchema | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUpdatingDocId, setIsUpdatingDocId] = useState<string | null>(null);

  const loadChecklistData = useCallback(async (signal?: AbortSignal) => {
    if (!id || !id.trim()) {
      setIsNotFound(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setIsNotFound(false);
    setErrorMessage(null);

    try {
      const sessionId = getSessionId();
      const [checklistRes, detailRes] = await Promise.all([
        fetchDocumentChecklist(id, sessionId, language, { signal }),
        fetchSchemeDetail(id, { signal }).catch((err) => {
          console.warn('[DocumentChecklist] Scheme detail fallback error:', err?.message || err);
          return null;
        }),
      ]);

      setChecklist(checklistRes);
      setSchemeDetail(detailRes);
    } catch (err: any) {
      if (err?.isAborted) return;
      console.error('[DocumentChecklist] Load error:', err);
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
    loadChecklistData(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadChecklistData]);

  const handleToggleDocument = async (docId: string, currentCollected: boolean) => {
    if (!id || !checklist || isUpdatingDocId) return;

    const newStatus = !currentCollected;
    setIsUpdatingDocId(docId);

    // Optimistically update local view
    setChecklist((prev) => {
      if (!prev) return prev;
      const updatedDocs = prev.documents.map((d) =>
        d.id === docId ? { ...d, is_collected: newStatus } : d
      );
      const newCollectedCount = updatedDocs.filter((d) => d.is_collected).length;
      const newMandatoryCollected = updatedDocs.filter((d) => d.is_mandatory && d.is_collected).length;
      return {
        ...prev,
        documents: updatedDocs,
        collected_count: newCollectedCount,
        mandatory_collected_count: newMandatoryCollected,
        is_complete: newMandatoryCollected === prev.mandatory_count,
      };
    });

    try {
      const sessionId = getSessionId();
      const updatedServerChecklist = await markDocumentCollected({
        session_id: sessionId,
        scheme_id: id,
        document_id: docId,
        is_collected: newStatus,
      });
      setChecklist(updatedServerChecklist);
    } catch (err) {
      console.error('[DocumentChecklist] Failed to persist collected status to session:', err);
      // Revert optimistic update on failure
      loadChecklistData();
    } finally {
      setIsUpdatingDocId(null);
    }
  };

  const schemeName = checklist?.scheme_name?.[language] ||
    checklist?.scheme_name?.en ||
    schemeDetail?.names?.[language] ||
    schemeDetail?.names?.en ||
    id ||
    '';

  const completedCount = checklist?.collected_count ?? 0;
  const totalCount = checklist?.total_documents ?? 0;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const saved = id ? isSchemeSaved(id) : false;
  const portalUrl = checklist?.official_portal_url || schemeDetail?.official_url || 'https://myscheme.gov.in';

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header 
        title={t('documentChecklistTitle', language)} 
        subtitle={schemeName} 
        showBack 
      />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* State 1: Loading Skeleton */}
        {isLoading && (
          <div className="space-y-4" role="status" aria-label={t('loadingSchemes', language)}>
            <div className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-3 animate-pulse">
              <div className="h-4 bg-sand rounded w-1/3"></div>
              <div className="h-2.5 bg-sand rounded-full w-full"></div>
            </div>
            <div className="bg-surface rounded-card p-5 border border-sand shadow-card space-y-4 animate-pulse">
              <div className="h-5 bg-sand rounded w-1/4"></div>
              {[1, 2, 3].map((n) => (
                <div key={n} className="flex items-start gap-3 py-2">
                  <div className="w-5 h-5 bg-sand rounded"></div>
                  <div className="flex-1 space-y-1.5">
                    <div className="h-4 bg-sand rounded w-1/2"></div>
                    <div className="h-3 bg-sand rounded w-3/4"></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* State 2: Not Found (404 / Invalid ID) */}
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

        {/* State 3: Error */}
        {!isLoading && !isNotFound && errorMessage && (
          <div className="bg-surface rounded-card p-8 border border-sand text-center space-y-4 shadow-card">
            <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-800 flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="font-heading font-bold text-base text-ink">
              {errorMessage}
            </h2>
            <button
              onClick={() => loadChecklistData()}
              className="inline-flex items-center gap-1.5 bg-forest hover:bg-forest-deep text-white text-xs font-bold py-2.5 px-4 rounded-full transition-colors shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>{t('retryAction', language)}</span>
            </button>
          </div>
        )}

        {/* State 4: Loaded Document Checklist */}
        {!isLoading && !isNotFound && checklist && (
          <>
            {/* Progress Card */}
            <div className="bg-surface rounded-card p-4 border border-sand shadow-card space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-ink/60 uppercase">
                  {t('readinessProgressTitle', language)}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-forest">
                    {completedCount} / {totalCount} {t('readyCountUnit', language)} ({progressPercent}%)
                  </span>
                  {checklist.is_complete && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold bg-[#EAF5EE] text-[#1F7A4D] px-2 py-0.5 rounded-full border border-[#1F7A4D]/30">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>{t('checklistCompleteBadge', language)}</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-sand/60 h-2.5 rounded-full overflow-hidden">
                <div
                  className="bg-forest h-full transition-all duration-300 rounded-full"
                  style={{ width: `${progressPercent}%` }}
                ></div>
              </div>
            </div>

            {/* Interactive Documents List */}
            <div className="bg-surface rounded-card p-5 border border-sand shadow-card space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-heading font-bold text-base text-ink">
                  {t('documentChecklistTitle', language)}
                </h2>
                <span className="text-xs text-ink/65">
                  {checklist.mandatory_count} {t('mandatoryBadge', language).toLowerCase()}, {checklist.optional_count} {t('optionalBadge', language).toLowerCase()}
                </span>
              </div>

              {checklist.documents.length === 0 ? (
                <div className="text-center py-6 space-y-1">
                  <p className="font-bold text-xs text-ink">
                    {t('noChecklistFoundTitle', language)}
                  </p>
                  <p className="text-xs text-ink/70">
                    {t('noChecklistFoundDesc', language)}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-sand/60">
                  {checklist.documents.map((doc) => {
                    const isChecked = Boolean(doc.is_collected);
                    const docName = doc.names?.[language] || doc.names?.en || doc.id;
                    const docDesc = doc.descriptions?.[language] || doc.descriptions?.en || '';

                    return (
                      <div
                        key={doc.id}
                        onClick={() => handleToggleDocument(doc.id, isChecked)}
                        className="py-3 flex items-start gap-3 cursor-pointer group transition-colors hover:bg-canvas/50 px-1 rounded-lg"
                      >
                        <button
                          type="button"
                          className="mt-0.5 text-forest flex-shrink-0"
                          aria-label={`Mark ${docName} as collected`}
                        >
                          {isChecked ? (
                            <CheckSquare className="w-5 h-5 fill-forest text-white" />
                          ) : (
                            <Square className="w-5 h-5 text-ink/40 group-hover:text-ink" />
                          )}
                        </button>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-sm font-bold ${isChecked ? 'line-through text-ink/40' : 'text-ink'}`}>
                              {docName}
                            </span>

                            {doc.is_mandatory ? (
                              <span className="text-[10px] bg-[#FDF0F0] text-[#8F3D3D] font-semibold px-1.5 py-0.5 rounded border border-[#8F3D3D]/30">
                                {t('mandatoryBadge', language)}
                              </span>
                            ) : (
                              <span className="text-[10px] bg-canvas text-ink/70 font-medium px-1.5 py-0.5 rounded border border-sand">
                                {t('optionalBadge', language)}
                              </span>
                            )}

                            {doc.csc_assisted && (
                              <span className="text-[10px] bg-amber-50 text-amber-900 font-semibold px-1.5 py-0.5 rounded border border-amber-200">
                                {t('cscAssistedBadge', language)}
                              </span>
                            )}
                          </div>

                          {docDesc && (
                            <p className="text-xs text-ink/75 mt-0.5 leading-relaxed">
                              {docDesc}
                            </p>
                          )}

                          <div className="flex items-center gap-3 mt-1 text-[11px] text-ink/60 flex-wrap">
                            {doc.issuer && (
                              <span>
                                <span className="font-medium text-ink/70">{t('issuingAuthorityLabel', language)}:</span> {doc.issuer}
                              </span>
                            )}
                            {doc.source_url && (
                              <a
                                href={doc.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="inline-flex items-center gap-1 text-forest hover:underline font-medium"
                              >
                                <span>{t('officialSourceLink', language)}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Application Procedure (From Scheme Detail if available) */}
            {schemeDetail?.application_procedure && schemeDetail.application_procedure.length > 0 && (
              <div className="bg-white rounded-card p-5 border border-neutral-mist shadow-card space-y-3">
                <h2 className="font-heading font-bold text-base text-neutral-ink flex items-center gap-2">
                  <ListOrdered className="w-5 h-5 text-brand-indigo" />
                  <span>{t('applicationStepsHeading', language)}</span>
                </h2>

                <div className="space-y-3">
                  {schemeDetail.application_procedure.map((step, idx) => {
                    const stepTitle = step.titles?.[language] || step.titles?.en || '';
                    const stepDesc = step.descriptions?.[language] || step.descriptions?.en || '';
                    return (
                      <div key={idx} className="flex items-start gap-3 text-xs text-neutral-ink leading-relaxed">
                        <span className="w-6 h-6 rounded-full bg-brand-indigo-tint text-brand-indigo font-bold flex items-center justify-center text-xs flex-shrink-0 mt-0.5 border border-brand-indigo/30">
                          {step.step_number || idx + 1}
                        </span>
                        <div className="pt-0.5 flex-1">
                          {stepTitle && <span className="font-bold block">{stepTitle}</span>}
                          <span>{stepDesc}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* CSC Physical Assistance Locator Box */}
            <div className="bg-amber-50/60 border border-amber-200 rounded-card p-4 space-y-2">
              <div className="flex items-center gap-2 text-brand-orange font-bold text-xs">
                <MapPin className="w-4 h-4" />
                <span>{t('cscAssistanceHeading', language)}</span>
              </div>
              <p className="text-xs text-neutral-ink leading-relaxed">
                {t('cscAssistanceText', language)}
              </p>
              <a
                href="https://findmycsc.nic.in"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-bold text-brand-indigo hover:underline pt-1"
              >
                <span>{t('findMyCSCLink', language)} (findmycsc.nic.in)</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                onClick={() => {
                  if (id) {
                    if (!saved) toggleSaveScheme(id);
                    navigate('/locker');
                  }
                }}
                className="flex-1 bg-brand-indigo hover:bg-brand-indigo-hover text-white font-bold py-3.5 px-6 rounded-button shadow-md flex items-center justify-center gap-2 text-sm min-h-[50px] transition-transform active:scale-98"
              >
                <BookmarkCheck className="w-5 h-5" />
                <span>{t('saveToLocker', language)}</span>
              </button>

              <a
                href={portalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-white hover:bg-neutral-canvas border border-neutral-mist text-neutral-ink font-semibold py-3 px-5 rounded-button flex items-center justify-center gap-2 text-xs min-h-[48px] shadow-sm transition-colors"
              >
                <span>{t('visitOfficialPortal', language)}</span>
                <ExternalLink className="w-4 h-4 text-brand-indigo" />
              </a>
            </div>
          </>
        )}

        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};
