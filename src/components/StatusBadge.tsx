import React from 'react';
import { CheckCircle2, Clock, XCircle } from 'lucide-react';
import { EligibilityStatus } from '../types';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';

interface Props {
  status: EligibilityStatus;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<Props> = ({ status, showIcon = true, size = 'md' }) => {
  const { language } = useApp();

  let text = '';
  let colorClass = '';
  let IconComponent = CheckCircle2;

  switch (status) {
    case 'eligible':
      text = t('statusEligible', language);
      colorClass = 'bg-[#EAF5EE] text-[#1F7A4D] border-[#1F7A4D]/30';
      IconComponent = CheckCircle2;
      break;
    case 'possibly_eligible':
      text = t('statusPossiblyEligible', language);
      colorClass = 'bg-[#FEF8EA] text-[#9A6B12] border-[#9A6B12]/30';
      IconComponent = Clock;
      break;
    case 'not_eligible':
      text = t('statusNotEligible', language);
      colorClass = 'bg-[#FDF0F0] text-[#8F3D3D] border-[#8F3D3D]/30';
      IconComponent = XCircle;
      break;
  }

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 font-semibold gap-1',
    md: 'text-xs px-2.5 py-1 font-semibold gap-1.5',
    lg: 'text-sm px-3.5 py-1.5 font-bold gap-2',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border ${colorClass} ${sizeClasses} tracking-wide uppercase transition-colors`}
      role="status"
    >
      {showIcon && <IconComponent className={size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
      <span>{text}</span>
    </span>
  );
};
