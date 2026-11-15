import React from 'react';
import { ShieldCheck, ExternalLink } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';

export const DisclaimerBanner: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { language } = useApp();

  return (
    <div className={`bg-sand/40 border border-sand rounded-card text-ink/75 text-xs flex items-start gap-2.5 ${compact ? 'p-2.5' : 'p-3.5'}`}>
      <ShieldCheck className="w-4 h-4 text-forest flex-shrink-0 mt-0.5" />
      <div className="flex-1 leading-relaxed">
        <span className="font-semibold text-ink">{t('unofficialDisclaimerPrefix', language)}: </span>
        {t('disclaimerText', language)}
        <a
          href="https://myscheme.gov.in"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-forest font-semibold ml-1.5 hover:underline"
        >
          myScheme.gov.in <ExternalLink className="w-3 h-3 inline" />
        </a>
      </div>
    </div>
  );
};
