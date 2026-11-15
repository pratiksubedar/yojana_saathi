import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mic,
  Search,
  ShieldAlert,
  Sparkles,
  ArrowRight,
  Wheat,
  HeartPulse,
  Home as HomeIcon,
  Users,
  AlertCircle,
  RefreshCw,
  Filter,
  Building2,
  MapPin,
  X,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { SchemeCard } from '../components/SchemeCard';
import { CATEGORY_LABELS } from '../data/mockSchemes';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';
import { fetchSchemes, mapBackendSchemeToFrontend } from '../services/schemeApi';
import { Scheme } from '../types';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useApp();
  const schemeExplorerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [allSchemes, setAllSchemes] = useState<Scheme[]>([]);
  const [featuredSchemes, setFeaturedSchemes] = useState<Scheme[]>([]);
  const [totalSchemesCount, setTotalSchemesCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Home Page Filter & Search States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMinistry, setSelectedMinistry] = useState<string>('all');
  const [selectedState, setSelectedState] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const [hasDoneOnboarding, setHasDoneOnboarding] = useState<boolean>(() => {
    try {
      return localStorage.getItem('yojana_onboarding_done') === 'true';
    } catch {
      return false;
    }
  });

  const loadSchemesData = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetchSchemes({ pageSize: 50 }, { signal });
      const mapped = response.items.map((item) =>
        mapBackendSchemeToFrontend(item, language)
      );
      setAllSchemes(mapped);
      setFeaturedSchemes(mapped.slice(0, 3));
      setTotalSchemesCount(response.pagination.total);
    } catch (err: any) {
      if (err?.isAborted) return;
      console.error('[Home] Failed to load schemes from backend:', err);
      setErrorMessage(
        err?.isNetworkError
          ? t('chatErrorMessage', language)
          : t('errorLoadingSchemes', language)
      );
    } finally {
      setIsLoading(false);
    }
  }, [language]);

  useEffect(() => {
    const controller = new AbortController();
    loadSchemesData(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadSchemesData]);

  // Handle Find Schemes Hero CTA: scroll down to Scheme Explorer and focus search
  const handleFindSchemesClick = () => {
    if (schemeExplorerRef.current) {
      schemeExplorerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 400);
    } else {
      navigate('/browse');
    }
  };

  // Distinct list of ministries extracted from live schemes
  const ministryOptions = useMemo(() => {
    const set = new Set<string>();
    allSchemes.forEach((s) => {
      if (s.ministry) set.add(s.ministry);
    });
    return Array.from(set).sort();
  }, [allSchemes]);

  // Multi-criteria client-side filtering for Scheme Explorer
  const filteredSchemes = useMemo(() => {
    return allSchemes.filter((scheme) => {
      // Category filter
      if (selectedCategory !== 'all') {
        if (scheme.category !== selectedCategory) return false;
      }

      // Ministry filter
      if (selectedMinistry !== 'all') {
        if (scheme.ministry?.toLowerCase() !== selectedMinistry.toLowerCase()) return false;
      }

      // State filter (Central schemes apply to all states)
      if (selectedState !== 'all') {
        const stateLower = selectedState.toLowerCase();
        const appliesToState =
          !scheme.stateApplicability ||
          scheme.stateApplicability.includes('ALL') ||
          scheme.stateApplicability.includes('all') ||
          scheme.stateApplicability.some((st: string) => st.toLowerCase().includes(stateLower));
        if (!appliesToState) return false;
      }

      // Search Query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchName = scheme.name.toLowerCase().includes(q);
        const matchNative = (scheme.nativeName || '').toLowerCase().includes(q);
        const matchBenefit = (scheme.benefit || '').toLowerCase().includes(q);
        const matchHighlight = (scheme.benefitHighlight || '').toLowerCase().includes(q);
        const matchDesc = (scheme.description || '').toLowerCase().includes(q);
        const matchMinistry = (scheme.ministry || '').toLowerCase().includes(q);
        if (!matchName && !matchNative && !matchBenefit && !matchHighlight && !matchDesc && !matchMinistry) {
          return false;
        }
      }

      return true;
    });
  }, [allSchemes, selectedCategory, selectedMinistry, selectedState, searchQuery]);

  const resetAllFilters = () => {
    setSearchQuery('');
    setSelectedMinistry('all');
    setSelectedState('all');
    setSelectedCategory('all');
  };

  return (
    <div className="min-h-screen bg-neutral-canvas pb-24">
      <Header />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-6">
        {/* Hero Section with Digital Art & GovTech Branding */}
        <div className="bg-gradient-to-br from-emerald-900 via-forest to-slate-900 rounded-3xl text-white p-6 sm:p-8 shadow-xl relative overflow-hidden border border-emerald-700/30">
          {/* GovTech Digital Art Illustration Background */}
          <div className="absolute right-0 top-0 bottom-0 w-full sm:w-1/2 opacity-20 pointer-events-none overflow-hidden flex items-center justify-end">
            <svg
              className="w-[420px] h-[420px] text-emerald-300 transform translate-x-12 -translate-y-6"
              viewBox="0 0 200 200"
              fill="currentColor"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Stylized Sun & Radial Lines */}
              <circle cx="100" cy="100" r="30" fill="currentColor" fillOpacity="0.4" />
              <path
                d="M100 20 L100 50 M100 150 L100 180 M20 100 L50 100 M150 100 L180 100 M43 43 L65 65 M135 135 L157 157 M43 157 L65 135 M135 65 L157 43"
                stroke="currentColor"
                strokeWidth="4"
                strokeLinecap="round"
                strokeOpacity="0.3"
              />
              {/* Agricultural Waves & Fields */}
              <path
                d="M10 160 Q 50 130, 100 160 T 190 160 L 190 200 L 10 200 Z"
                fill="currentColor"
                fillOpacity="0.3"
              />
              <path
                d="M0 175 Q 60 150, 120 175 T 200 175 L 200 200 L 0 200 Z"
                fill="currentColor"
                fillOpacity="0.5"
              />
            </svg>
          </div>

          <div className="relative z-10 space-y-4 max-w-xl">
            {/* GovTech Trust Badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white/15 backdrop-blur-md text-xs font-semibold text-emerald-100 border border-white/20 shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>{t('homeHeroTag', language)}</span>
              <span className="text-[10px] text-emerald-200 border-l border-white/20 pl-2">
                100% Free • Verified
              </span>
            </div>

            <h1 className="font-heading font-extrabold text-2xl sm:text-4xl leading-tight tracking-tight">
              {t('homeHeroTitle', language)}
            </h1>

            <p className="text-sm sm:text-base text-emerald-100 leading-relaxed font-sans">
              {t('homeHeroSubtitle', language)}
            </p>

            {/* Hero CTAs */}
            <div className="pt-2 flex flex-wrap items-center gap-3">
              {/* Primary Find Schemes CTA (Starts Guided AI Profile Flow) */}
              <button
                type="button"
                onClick={() => navigate('/assistant?guided=true')}
                className="bg-amber-500 hover:bg-amber-600 active:scale-98 text-slate-950 font-bold py-3.5 px-6 rounded-2xl shadow-lg flex items-center justify-center gap-2.5 transition-all text-base min-h-[50px] border border-amber-400/50"
                aria-label={t('findSchemesHeroCTA', language)}
              >
                <Search className="w-5 h-5 text-slate-950" />
                <span>{t('findSchemesHeroCTA', language)}</span>
              </button>

              {/* Text Chat Assistant CTA */}
              <button
                type="button"
                onClick={() => navigate('/assistant')}
                className="text-emerald-100 hover:text-white font-semibold py-2 px-3 text-xs flex items-center gap-1.5 transition-colors"
              >
                <span>{t('orTypeMessage', language)}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>

              {/* Direct Scroll to Directory Link */}
              <button
                type="button"
                onClick={handleFindSchemesClick}
                className="text-xs text-emerald-200/80 hover:text-white underline decoration-emerald-300/40 py-1 px-2 transition-colors ml-auto sm:ml-0"
              >
                {language === 'hi'
                  ? 'या नीचे सभी योजनाएं देखें ↓'
                  : language === 'kn'
                  ? 'ಅಥವಾ ಕೆಳಗೆ ಎಲ್ಲಾ ಯೋಜನೆಗಳನ್ನು ವೀಕ್ಷಿಸಿ ↓'
                  : language === 'te'
                  ? 'లేదా క్రింద అన్ని పథకాలను బ్రౌజ్ చేయండి ↓'
                  : 'Or browse all schemes below ↓'}
              </button>
            </div>
          </div>
        </div>

        {/* First-time Onboarding Invitation */}
        {!hasDoneOnboarding && (
          <div className="bg-emerald-50 border border-emerald-300 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-forest text-white flex items-center justify-center font-bold flex-shrink-0 shadow-xs">
                ✨
              </div>
              <div>
                <h3 className="font-heading font-bold text-sm text-ink">New to Yojana Saathi?</h3>
                <p className="text-xs text-ink/75">Complete a 1-minute quick setup to personalize your welfare eligibility.</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/onboarding')}
              className="bg-forest hover:bg-forest-deep text-white font-bold text-xs px-4 py-2.5 rounded-xl flex items-center gap-1.5 flex-shrink-0 transition-transform active:scale-95 shadow-xs"
            >
              <span>Quick Onboarding</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* How It Works - Visual 3-Step Guide for Low-Literacy Citizens */}
        <div className="bg-white rounded-2xl p-4 border border-sand shadow-card">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="flex flex-col items-center p-2 rounded-xl bg-orange-50/70 border border-orange-100">
              <span className="text-2xl mb-1">🎙️</span>
              <span className="text-xs font-bold text-ink">1. {t('speakToFind', language)}</span>
              <span className="text-[10px] text-ink/70 leading-tight mt-0.5">Tell us your age, job or land</span>
            </div>
            <div className="flex flex-col items-center p-2 rounded-xl bg-indigo-50/70 border border-indigo-100">
              <span className="text-2xl mb-1">⚡</span>
              <span className="text-xs font-bold text-ink">2. Fast Rule Check</span>
              <span className="text-[10px] text-ink/70 leading-tight mt-0.5">Matched with 21+ govt schemes</span>
            </div>
            <div className="flex flex-col items-center p-2 rounded-xl bg-emerald-50/70 border border-emerald-100">
              <span className="text-2xl mb-1">📋</span>
              <span className="text-xs font-bold text-ink">3. Get Benefits</span>
              <span className="text-[10px] text-ink/70 leading-tight mt-0.5">Documents & how to apply</span>
            </div>
          </div>
        </div>

        {/* Quick Discovery by Common Citizen Situations */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-bold text-base text-ink">
              {t('quickStartHeading', language)}
            </h2>
            <span className="text-xs text-ink/60">Instant Guided AI Check</span>
          </div>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              onClick={() => navigate('/assistant?q=I+am+a+farmer+looking+for+schemes')}
              className="p-3.5 rounded-2xl bg-white border border-green-200 hover:border-green-400 hover:bg-green-50/40 transition-all text-left shadow-card flex items-center gap-3 active:scale-98"
            >
              <div className="w-10 h-10 rounded-xl bg-green-100 text-green-700 flex items-center justify-center text-xl flex-shrink-0">
                🌾
              </div>
              <div>
                <span className="text-xs font-bold text-ink block">
                  {t('categoryFarmers', language)}
                </span>
                <span className="text-[11px] text-ink/65 block">PM-KISAN, KCC, Solar pump</span>
              </div>
            </button>

            <button
              onClick={() => navigate('/assistant?q=I+am+a+senior+citizen+looking+for+pension+and+healthcare')}
              className="p-3.5 rounded-2xl bg-white border border-purple-200 hover:border-purple-400 hover:bg-purple-50/40 transition-all text-left shadow-card flex items-center gap-3 active:scale-98"
            >
              <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center text-xl flex-shrink-0">
                👵
              </div>
              <div>
                <span className="text-xs font-bold text-ink block">
                  {t('categorySeniors', language)}
                </span>
                <span className="text-[11px] text-ink/65 block">PM-JAY 70+, NSAP Pension</span>
              </div>
            </button>

            <button
              onClick={() => navigate('/assistant?q=I+am+looking+for+women+and+child+welfare+schemes')}
              className="p-3.5 rounded-2xl bg-white border border-rose-200 hover:border-rose-400 hover:bg-rose-50/40 transition-all text-left shadow-card flex items-center gap-3 active:scale-98"
            >
              <div className="w-10 h-10 rounded-xl bg-rose-100 text-rose-700 flex items-center justify-center text-xl flex-shrink-0">
                👩‍👧
              </div>
              <div>
                <span className="text-xs font-bold text-ink block">
                  {t('categoryWomenChild', language)}
                </span>
                <span className="text-[11px] text-ink/65 block">PMMVY, Sukanya, Ujjwala</span>
              </div>
            </button>

            <button
              onClick={() => navigate('/assistant?q=I+am+a+street+vendor+looking+for+a+business+loan')}
              className="p-3.5 rounded-2xl bg-white border border-amber-200 hover:border-amber-400 hover:bg-amber-50/40 transition-all text-left shadow-card flex items-center gap-3 active:scale-98"
            >
              <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center text-xl flex-shrink-0">
                🛒
              </div>
              <div>
                <span className="text-xs font-bold text-ink block">
                  {t('categoryVendors', language)}
                </span>
                <span className="text-[11px] text-ink/65 block">PM-SVANidhi, Mudra Loan</span>
              </div>
            </button>
          </div>
        </div>

        {/* Live System Metric Strip */}
        <div className="grid grid-cols-3 gap-2.5">
          <div className="bg-white rounded-2xl p-3 border border-sand text-center shadow-card">
            <span className="block font-heading font-extrabold text-lg text-forest">{totalSchemesCount > 0 ? `${totalSchemesCount}+` : '21+'}</span>
            <span className="text-[11px] text-ink/70 font-medium">{t('metricSchemesIndexed', language)}</span>
          </div>
          <div className="bg-white rounded-2xl p-3 border border-sand text-center shadow-card">
            <span className="block font-heading font-extrabold text-lg text-brand-teal">{t('metricLanguages', language)}</span>
            <span className="text-[11px] text-ink/70 font-medium">हिन्दी/ಕನ್ನಡ/తెలుగు/EN</span>
          </div>
          <div className="bg-white rounded-2xl p-3 border border-sand text-center shadow-card">
            <span className="block font-heading font-extrabold text-lg text-emerald-600">100%</span>
            <span className="text-[11px] text-ink/70 font-medium">{t('metricFreeService', language)}</span>
          </div>
        </div>

        {/* INTERACTIVE SCHEME EXPLORER WITH FILTERS */}
        <div ref={schemeExplorerRef} id="scheme-explorer" className="space-y-4 pt-2">
          <div className="bg-white rounded-3xl p-5 border border-sand shadow-card space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-sand/50 pb-3">
              <div>
                <h2 className="font-heading font-bold text-lg text-ink flex items-center gap-2">
                  <Filter className="w-5 h-5 text-forest" />
                  <span>Scheme Directory & Filter</span>
                </h2>
                <p className="text-xs text-ink/65">
                  Browse benefits, eligibility criteria, and filter by Ministry or State.
                </p>
              </div>

              {(searchQuery || selectedMinistry !== 'all' || selectedState !== 'all' || selectedCategory !== 'all') && (
                <button
                  type="button"
                  onClick={resetAllFilters}
                  className="text-xs font-semibold text-forest hover:underline inline-flex items-center gap-1 self-start sm:self-auto"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reset filters</span>
                </button>
              )}
            </div>

            {/* 1. Search Bar */}
            <div className="relative">
              <Search className="w-4 h-4 text-ink/40 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={
                  language === 'hi'
                    ? 'योजना का नाम, लाभ या कीवर्ड खोजें (जैसे ₹6,000, किसान, पेंशन)...'
                    : 'Search scheme by name, benefit or keyword (e.g. ₹6,000, farmer, loan)...'
                }
                className="w-full bg-neutral-canvas border border-sand rounded-xl pl-10 pr-10 py-2.5 text-xs text-ink placeholder:text-ink/40 focus:outline-none focus:ring-2 focus:ring-forest focus:border-transparent transition-all"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 hover:text-ink text-xs p-1"
                >
                  ✕
                </button>
              )}
            </div>

            {/* 2. Dropdown Filters: Ministry & State */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* Ministry Dropdown */}
              <div>
                <label className="text-[11px] font-bold text-ink/60 uppercase tracking-wider block mb-1 flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5 text-forest" />
                  <span>Filter by Ministry</span>
                </label>
                <select
                  value={selectedMinistry}
                  onChange={(e) => setSelectedMinistry(e.target.value)}
                  className="w-full bg-neutral-canvas border border-sand rounded-xl px-3 py-2 text-xs text-ink focus:outline-none focus:ring-2 focus:ring-forest cursor-pointer"
                >
                  <option value="all">All Central Ministries ({totalSchemesCount > 0 ? totalSchemesCount : 21})</option>
                  {ministryOptions.map((min) => (
                    <option key={min} value={min}>
                      {min}
                    </option>
                  ))}
                </select>
              </div>

              {/* State Dropdown */}
              <div>
                <label className="text-[11px] font-bold text-ink/60 uppercase tracking-wider block mb-1 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-forest" />
                  <span>Filter by State Applicability</span>
                </label>
                <select
                  value={selectedState}
                  onChange={(e) => setSelectedState(e.target.value)}
                  className="w-full bg-neutral-canvas border border-sand rounded-xl px-3 py-2 text-xs text-ink focus:outline-none focus:ring-2 focus:ring-forest cursor-pointer"
                >
                  <option value="all">All India (Nationwide Central Schemes)</option>
                  <option value="Karnataka">Karnataka</option>
                  <option value="Andhra Pradesh">Andhra Pradesh</option>
                  <option value="Telangana">Telangana</option>
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Uttar Pradesh">Uttar Pradesh</option>
                  <option value="Bihar">Bihar</option>
                  <option value="Tamil Nadu">Tamil Nadu</option>
                  <option value="Rajasthan">Rajasthan</option>
                  <option value="Madhya Pradesh">Madhya Pradesh</option>
                </select>
              </div>
            </div>

            {/* 3. Category Pills */}
            <div className="pt-1">
              <span className="text-[11px] font-bold text-ink/60 uppercase tracking-wider block mb-2">
                Filter by Category
              </span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { key: 'all', label: 'All Schemes' },
                  { key: 'agriculture', label: CATEGORY_LABELS.agriculture[language] || 'Agriculture' },
                  { key: 'healthcare', label: CATEGORY_LABELS.healthcare[language] || 'Healthcare' },
                  { key: 'housing', label: CATEGORY_LABELS.housing[language] || 'Housing' },
                  { key: 'social_welfare', label: CATEGORY_LABELS.social_welfare[language] || 'Social Welfare' },
                  { key: 'financial_services', label: 'Finance & Loans' },
                  { key: 'women_and_child', label: 'Women & Child' },
                  { key: 'energy', label: 'Solar & Energy' },
                ].map((cat) => (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => setSelectedCategory(cat.key)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                      selectedCategory === cat.key
                        ? 'bg-forest text-white shadow-xs'
                        : 'bg-neutral-canvas text-ink/75 border border-sand hover:text-ink hover:bg-sand/30'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Scheme Cards Stream */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-ink/70 px-1">
              <span className="font-semibold">
                Showing {filteredSchemes.length} of {allSchemes.length} scheme(s)
              </span>
              <button
                onClick={() => navigate('/browse')}
                className="text-forest hover:underline font-bold"
              >
                Browse Full Catalog →
              </button>
            </div>

            {isLoading ? (
              <div className="space-y-3" role="status" aria-label={t('loadingSchemes', language)}>
                {[1, 2, 3].map((n) => (
                  <div
                    key={n}
                    className="bg-white rounded-2xl border border-sand shadow-card p-4 animate-pulse space-y-3"
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
              <div className="bg-white rounded-2xl p-6 border border-sand shadow-card text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-amber-50 text-status-amber flex items-center justify-center mx-auto">
                  <AlertCircle className="w-5 h-5" />
                </div>
                <h3 className="font-heading font-bold text-sm text-ink">{errorMessage}</h3>
                <button
                  onClick={() => loadSchemesData()}
                  className="inline-flex items-center gap-1.5 bg-forest text-white text-xs font-bold py-2 px-4 rounded-xl hover:bg-forest-deep transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>{t('retryAction', language)}</span>
                </button>
              </div>
            ) : filteredSchemes.length === 0 ? (
              <div className="bg-white rounded-2xl p-8 border border-sand shadow-card text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-emerald-50 text-forest flex items-center justify-center mx-auto text-xl">
                  🔍
                </div>
                <h3 className="font-heading font-bold text-sm text-ink">No schemes match your filter</h3>
                <p className="text-xs text-ink/65 max-w-sm mx-auto">
                  Try clearing the search query or selecting "All Central Ministries" to view all available government schemes.
                </p>
                <button
                  type="button"
                  onClick={resetAllFilters}
                  className="inline-flex items-center gap-1.5 bg-forest text-white text-xs font-bold py-2 px-4 rounded-xl hover:bg-forest-deep shadow-xs transition-colors"
                >
                  <span>Reset All Filters</span>
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredSchemes.map((scheme) => (
                  <SchemeCard key={scheme.id} scheme={scheme} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Fallback & System Resilience Quick Link */}
        <div className="bg-white rounded-2xl p-4 border border-sand shadow-card flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-amber-50 text-status-amber flex items-center justify-center flex-shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-ink">
                {t('resilienceBannerTitle', language)}
              </h4>
              <p className="text-[11px] text-ink/65">
                {t('resilienceBannerSubtitle', language)}
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/resilience-states')}
            className="text-xs font-semibold text-forest hover:underline flex-shrink-0 ml-2"
          >
            {t('checkSafetyState', language)} →
          </button>
        </div>

        {/* Official Disclaimer */}
        <DisclaimerBanner />
      </main>

      <BottomNav />
    </div>
  );
};
