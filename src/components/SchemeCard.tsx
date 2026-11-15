import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bookmark, 
  BookmarkCheck, 
  ChevronRight, 
  ChevronDown,
  CheckCircle2, 
  XCircle, 
  AlertCircle,
  ExternalLink,
  Calendar,
  FileText,
  ListOrdered,
  Building2,
  Sparkles,
  Users
} from 'lucide-react';
import { Scheme } from '../types';
import { StatusBadge } from './StatusBadge';
import { useApp } from '../context/AppContext';
import { getLocalizedScheme } from '../data/mockSchemes';
import { t } from '../data/translations';

interface Props {
  scheme: Scheme;
  showMatchReasons?: boolean;
}

export const SchemeCard: React.FC<Props> = ({ scheme, showMatchReasons = true }) => {
  const navigate = useNavigate();
  const { isSchemeSaved, toggleSaveScheme, language } = useApp();
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const saved = isSchemeSaved(scheme.id);
  const localizedScheme = getLocalizedScheme(scheme, language);

  const handleCardClick = () => {
    navigate(`/scheme/${scheme.id}`);
  };

  const handleSaveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    toggleSaveScheme(scheme.id);
  };

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded((prev) => !prev);
  };

  const handleExternalLinkClick = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  // Border highlight color based on status
  const borderStatusClass = {
    eligible: 'border-l-4 border-l-[#1F7A4D]',
    possibly_eligible: 'border-l-4 border-l-[#9A6B12]',
    not_eligible: 'border-l-4 border-l-[#8F3D3D]',
  }[scheme.status];

  return (
    <div
      onClick={handleCardClick}
      className={`bg-surface rounded-card border border-sand shadow-card hover:shadow-card-hover transition-all cursor-pointer p-4 relative ${borderStatusClass} group`}
    >
      {/* 1. Top Meta Row: Ministry & Status */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Building2 className="w-3.5 h-3.5 text-ink/60 flex-shrink-0" />
          <span className="text-[11px] font-semibold text-ink/60 uppercase tracking-wider line-clamp-1">
            {localizedScheme.ministry}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* 2. Eligibility Status */}
          <StatusBadge status={localizedScheme.status} size="sm" />
          <button
            onClick={handleSaveClick}
            aria-label={saved ? t('removeFromLocker', language) : t('saveToLocker', language)}
            className="p-1.5 -mr-1 rounded-full text-ink/50 hover:text-forest hover:bg-sand/30 transition-colors"
          >
            {saved ? (
              <BookmarkCheck className="w-5 h-5 text-forest fill-sage" />
            ) : (
              <Bookmark className="w-5 h-5 text-ink/40 group-hover:text-ink" />
            )}
          </button>
        </div>
      </div>

      {/* 1. Scheme Name */}
      <h3 className="font-heading font-bold text-base text-ink leading-snug group-hover:text-forest transition-colors mb-0.5">
        {localizedScheme.name}
      </h3>
      {localizedScheme.nativeName && localizedScheme.nativeName !== localizedScheme.name && (
        <p className="text-xs text-ink/65 mb-2 font-medium">
          {localizedScheme.nativeName}
        </p>
      )}

      {/* 2. Target Beneficiaries: Who it is for */}
      <div className="flex items-start gap-1.5 text-xs text-ink/80 mb-3 bg-neutral-canvas/60 p-2 rounded-lg border border-sand/40">
        <Users className="w-3.5 h-3.5 text-forest flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-bold text-ink">
            {language === 'hi'
              ? 'किसके लिए: '
              : language === 'kn'
              ? 'ಯಾರಿಗಾಗಿ: '
              : language === 'te'
              ? 'ఎవరి కోసం: '
              : 'Who it is for: '}
          </span>
          <span>{localizedScheme.description}</span>
        </div>
      </div>

      {/* 3. Key Benefit Card */}
      <div className="bg-sage/40 rounded-xl p-3 mb-3 border border-sage/60 space-y-1">
        <div className="flex items-center gap-1.5 text-forest">
          <Sparkles className="w-3.5 h-3.5 text-forest flex-shrink-0" />
          <span className="text-xs font-bold uppercase tracking-wider">
            {t('keyFinancialBenefitHeading', language)}
          </span>
        </div>
        <p className="text-xs font-bold text-forest leading-relaxed">
          {localizedScheme.benefitHighlight || localizedScheme.benefit}
        </p>
        {localizedScheme.benefit && localizedScheme.benefit !== localizedScheme.benefitHighlight && (
          <p className="text-[11px] text-ink/75 leading-relaxed pt-1 border-t border-sage/40">
            {localizedScheme.benefit}
          </p>
        )}
      </div>

      {/* 4. Match / Eligibility Reasons */}
      {showMatchReasons && (
        <div className="text-xs text-neutral-slate border-t border-neutral-mist/60 pt-2.5 space-y-1.5 mb-2">
          {/* Matched Criteria */}
          {localizedScheme.matchingCriteria && localizedScheme.matchingCriteria.length > 0 && (
            <div className="space-y-1">
              {localizedScheme.matchingCriteria.slice(0, isExpanded ? 5 : 2).map((item, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-status-green leading-snug">
                  <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span className="leading-snug">{item}</span>
                </div>
              ))}
            </div>
          )}

          {/* Missing Info Criteria */}
          {localizedScheme.status === 'possibly_eligible' && localizedScheme.missingCriteria && localizedScheme.missingCriteria.length > 0 && (
            <div className="space-y-1">
              <span className="text-[11px] font-bold text-status-amber block">
                {t('missingInformationTitle', language)}
              </span>
              {localizedScheme.missingCriteria.slice(0, isExpanded ? 5 : 2).map((item, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-status-amber leading-snug">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span className="leading-snug">{item}</span>
                </div>
              ))}
            </div>
          )}

          {/* Failed Criteria / Exclusions */}
          {localizedScheme.status === 'not_eligible' && localizedScheme.failedCriteria && localizedScheme.failedCriteria.length > 0 && (
            <div className="space-y-1">
              {localizedScheme.failedCriteria.slice(0, isExpanded ? 5 : 2).map((item, idx) => (
                <div key={idx} className="flex items-start gap-1.5 text-status-red leading-snug">
                  <XCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                  <span className="leading-snug">{item}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Expandable Accordion: 6. Required Documents & 7. Application Steps */}
      {isExpanded && (
        <div className="text-xs border-t border-sand/60 pt-3 space-y-3 bg-canvas/60 -mx-4 px-4 py-3 my-2 border-b border-sand/60">
          {/* 6. Required Documents */}
          {localizedScheme.requiredDocuments && localizedScheme.requiredDocuments.length > 0 && (
            <div>
              <span className="font-bold text-ink flex items-center gap-1.5 mb-1.5 text-[11px] uppercase tracking-wider">
                <FileText className="w-3.5 h-3.5 text-forest" />
                {t('documentReadinessHeading', language)}:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {localizedScheme.requiredDocuments.map((doc) => (
                  <span
                    key={doc.id}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                      doc.required
                        ? 'bg-sage text-forest border-sage'
                        : 'bg-sand/40 text-ink/70 border-sand'
                    }`}
                  >
                    <span>{doc.name}</span>
                    <span className="text-[9px] opacity-75">
                      ({doc.required ? t('mandatoryBadge', language) : t('optionalBadge', language)})
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 7. Application Steps */}
          {localizedScheme.applicationSteps && localizedScheme.applicationSteps.length > 0 && (
            <div>
              <span className="font-bold text-ink flex items-center gap-1.5 mb-1.5 text-[11px] uppercase tracking-wider">
                <ListOrdered className="w-3.5 h-3.5 text-forest" />
                {t('applicationStepsHeading', language)}:
              </span>
              <ol className="list-decimal list-inside space-y-1 text-ink/75 text-[11px]">
                {localizedScheme.applicationSteps.map((step, idx) => (
                  <li key={idx} className="leading-snug">
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {/* 8. Official Source Link & 9. Last Verified Date */}
      <div className="flex items-center justify-between text-[11px] text-ink/60 pt-2 border-t border-sand/40">
        {/* 8. Official Source Link */}
        {localizedScheme.officialUrl ? (
          <a
            href={localizedScheme.officialUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleExternalLinkClick}
            className="inline-flex items-center gap-1 text-forest font-semibold hover:underline"
            title={localizedScheme.officialUrl}
          >
            <span>{t('officialSourceLink', language)}</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        ) : (
          <span className="text-ink/50">{t('officialSourceLink', language)}</span>
        )}

        {/* 9. Last Verified Date */}
        <div className="flex items-center gap-1 text-ink/60">
          <Calendar className="w-3 h-3 text-forest" />
          <span>Verified: {localizedScheme.lastUpdated || '2026-10-20'}</span>
        </div>
      </div>

      {/* Card Action Controls: Check Eligibility, Expand Toggle & View Details Link */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs font-semibold pt-2.5 border-t border-sand/40">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/assistant?scheme=${scheme.id}`);
          }}
          className="inline-flex items-center gap-1.5 bg-forest hover:bg-forest-deep active:scale-95 text-white font-bold text-xs py-1.5 px-3 rounded-xl shadow-xs transition-all"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          <span>
            {language === 'hi'
              ? 'पात्रता जांचें'
              : language === 'kn'
              ? 'ಅರ್ಹತೆ ಪರಿಶೀಲಿಸಿ'
              : language === 'te'
              ? 'అర్హత తనిఖీ చేయండి'
              : 'Check My Eligibility'}
          </span>
        </button>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleToggleExpand}
            className="inline-flex items-center gap-1 text-ink/70 hover:text-forest py-1 px-2 rounded-lg hover:bg-sand/30 transition-colors text-[11px]"
          >
            <span>{isExpanded ? 'Less guidance' : 'View guidance & documents'}</span>
            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>

          <div className="flex items-center gap-1 text-forest group-hover:translate-x-0.5 transition-transform font-bold text-[11px]">
            <span>{t('viewDetails', language)}</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </div>
        </div>
      </div>
    </div>
  );
};
