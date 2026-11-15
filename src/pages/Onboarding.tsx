import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  ArrowRight,
  Sparkles,
  HelpCircle,
  SkipForward,
  UserCheck,
  Check,
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';
import { INDIAN_STATES_AND_UTS, OCCUPATION_OPTIONS, CASTE_CATEGORIES } from './ProfileConfirmation';

export const FARMER_TYPES = [
  'Landowner',
  'Tenant / Sharecropper',
  'Animal Husbandry / Fisheries',
  'Other Allied',
];

export const Onboarding: React.FC = () => {
  const navigate = useNavigate();
  const { language, updateUserProfile } = useApp();

  const [age, setAge] = useState<string>('');
  const [state, setState] = useState<string>('');
  const [occupation, setOccupation] = useState<string>('');
  const [farmerType, setFarmerType] = useState<string>('');
  const [annualIncome, setAnnualIncome] = useState<string>('');
  const [socialCategory, setSocialCategory] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const isFarmer = occupation === 'Farmer';

  const handleFinishOnboarding = (skip: boolean = false) => {
    if (!skip) {
      if (age.trim()) {
        const numAge = Number(age);
        if (!Number.isFinite(numAge) || numAge < 0 || numAge > 120) {
          setError('Please enter a valid age between 0 and 120.');
          return;
        }
      }

      const updates: Record<string, any> = {};
      if (age.trim()) updates.age = Number(age);
      if (state.trim()) updates.state = state;
      if (occupation.trim()) updates.occupation = occupation;
      if (isFarmer && farmerType.trim()) {
        updates.farmerType = farmerType;
        if (farmerType.includes('Landowner')) {
          updates.ownsAgriculturalLand = true;
        } else if (farmerType.includes('Tenant')) {
          updates.isTenantFarmer = true;
        } else if (farmerType.includes('Animal') || farmerType.includes('Allied')) {
          updates.isAlliedActivityWorker = true;
        }
      }
      if (annualIncome.trim()) {
        const numInc = Number(annualIncome);
        if (Number.isFinite(numInc) && numInc >= 0) {
          updates.annualIncome = numInc;
        }
      }
      if (socialCategory.trim()) updates.socialCategory = socialCategory;

      if (Object.keys(updates).length > 0) {
        updateUserProfile(updates, 'user');
      }
    }

    try {
      localStorage.setItem('yojana_onboarding_done', 'true');
    } catch {
      // ignore
    }

    navigate('/assistant');
  };

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title="Welcome / स्वागत है" subtitle="Citizen Onboarding" showBack />

      <main className="max-w-xl mx-auto px-4 py-5 space-y-5">
        {/* Header Intro */}
        <div className="bg-surface p-5 rounded-2xl border border-sand shadow-sm space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-full bg-forest text-white flex items-center justify-center font-bold text-sm">
              <Sparkles className="w-4 h-4" />
            </span>
            <div>
              <h1 className="font-heading font-bold text-xl text-ink">
                Quick Citizen Onboarding
              </h1>
              <p className="text-xs text-ink/70">
                Set a few basic details so Yojana Saathi can instantly find matching schemes for you.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold">
            {error}
          </div>
        )}

        {/* Onboarding Form */}
        <div className="bg-surface p-5 rounded-2xl border border-sand shadow-sm space-y-5">
          {/* 1. Age */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-ink">
              Your Age (years)
            </label>
            <p className="text-[11px] text-ink/60">
              Schemes such as PM-KMY (18-40) or NSAP pensions (60+) have statutory age thresholds.
            </p>
            <input
              type="number"
              min="0"
              max="120"
              placeholder="e.g. 35"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
            />
          </div>

          {/* 2. State */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-ink">
              State of Residence
            </label>
            <p className="text-[11px] text-ink/60">
              Filters state-specific welfare rules and regional execution guidelines.
            </p>
            <select
              value={state}
              onChange={(e) => setState(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
            >
              <option value="">Select your State or UT</option>
              {INDIAN_STATES_AND_UTS.map((st) => (
                <option key={st.code} value={st.name}>
                  {st.name}
                </option>
              ))}
            </select>
          </div>

          {/* 3. Occupation */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-ink">
              Primary Occupation
            </label>
            <p className="text-[11px] text-ink/60">
              Helps identify vocation-targeted schemes (PM-KISAN, PM-SVANidhi, Vishwakarma, etc.).
            </p>
            <select
              value={occupation}
              onChange={(e) => {
                setOccupation(e.target.value);
                if (e.target.value !== 'Farmer') setFarmerType('');
              }}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
            >
              <option value="">Select your primary occupation</option>
              {OCCUPATION_OPTIONS.map((occ) => (
                <option key={occ} value={occ}>
                  {occ}
                </option>
              ))}
            </select>
          </div>

          {/* 3b. Farmer Type (conditional) */}
          {isFarmer && (
            <div className="p-3.5 rounded-xl bg-sage/30 border border-forest/20 space-y-2 animate-fade-in">
              <label className="block text-xs font-bold text-forest-deep">
                Agricultural Activity / Cultivator Category
              </label>
              <p className="text-[11px] text-ink/70">
                Crucial for Kisan Credit Card (KCC) and PM-KISAN landholder qualification.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {FARMER_TYPES.map((ft) => (
                  <button
                    type="button"
                    key={ft}
                    onClick={() => setFarmerType(ft)}
                    className={`p-2.5 rounded-xl border text-left text-xs font-semibold transition-all flex items-center justify-between ${
                      farmerType === ft
                        ? 'bg-forest text-white border-forest shadow-sm'
                        : 'bg-surface text-ink border-sand hover:border-forest/40'
                    }`}
                  >
                    <span>{ft}</span>
                    {farmerType === ft && <Check className="w-3.5 h-3.5" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 4. Annual Income (Optional) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-ink">
                Annual Family Income (₹)
              </label>
              <span className="text-[11px] font-semibold text-ink/50 bg-sand/40 px-2 py-0.5 rounded">
                Optional
              </span>
            </div>
            <p className="text-[11px] text-ink/60">
              Income ceilings apply for subsidized credit, housing grants, or Ayushman health cover.
            </p>
            <input
              type="number"
              min="0"
              placeholder="e.g. 150000"
              value={annualIncome}
              onChange={(e) => setAnnualIncome(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
            />
          </div>

          {/* 5. Social Category (Optional) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold text-ink">
                Social / Reservation Category
              </label>
              <span className="text-[11px] font-semibold text-ink/50 bg-sand/40 px-2 py-0.5 rounded">
                Optional
              </span>
            </div>
            <p className="text-[11px] text-ink/60">
              Only required if a scheme provides special affirmative allowances or relaxed norms.
            </p>
            <select
              value={socialCategory}
              onChange={(e) => setSocialCategory(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-sand bg-canvas text-ink text-sm focus:ring-2 focus:ring-forest focus:outline-none"
            >
              <option value="">Prefer not to state / Select</option>
              {CASTE_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Zero PII Privacy Notice */}
        <div className="p-3.5 rounded-xl bg-forest/5 border border-forest/20 flex items-start gap-2.5 text-xs text-forest-deep">
          <ShieldCheck className="w-4 h-4 text-forest flex-shrink-0 mt-0.5" />
          <p>
            <span className="font-bold">Zero Permanent PII:</span> These attributes are kept exclusively in session memory for matching welfare criteria. We never collect or store your Aadhaar or bank account numbers.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={() => handleFinishOnboarding(true)}
            className="flex-1 py-3 px-4 rounded-xl border border-sand bg-surface hover:bg-sand/30 text-ink/70 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
          >
            <SkipForward className="w-3.5 h-3.5" />
            <span>Skip & Continue to Chat</span>
          </button>
          <button
            type="button"
            onClick={() => handleFinishOnboarding(false)}
            className="flex-1 py-3 px-4 rounded-xl bg-forest hover:bg-forest-deep text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-md transition-all active:scale-98"
          >
            <UserCheck className="w-4 h-4" />
            <span>Save & Start Exploring</span>
          </button>
        </div>
      </main>

      <BottomNav />
    </div>
  );
};
