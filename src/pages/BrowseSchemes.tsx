import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, X, SlidersHorizontal, AlertCircle, RefreshCw } from 'lucide-react';
import { Header } from '../components/Header';
import { BottomNav } from '../components/BottomNav';
import { SchemeCard } from '../components/SchemeCard';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { CATEGORY_LABELS } from '../data/mockSchemes';
import { SchemeCategory, Scheme } from '../types';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';
import { fetchSchemes, mapBackendSchemeToFrontend } from '../services/schemeApi';

export const BrowseSchemes: React.FC = () => {
  const { language } = useApp();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCategory = (searchParams.get('category') as SchemeCategory) || 'all';

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<SchemeCategory>(initialCategory);

  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const categories: SchemeCategory[] = [
    'all',
    'agriculture',
    'healthcare',
    'housing',
    'social_welfare',
    'employment',
    'women_and_child',
    'energy',
  ];

  // 300ms debounce to prevent firing backend requests on every keystroke
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Keep state synced if URL category changes externally
  useEffect(() => {
    const urlCategory = (searchParams.get('category') as SchemeCategory) || 'all';
    if (urlCategory !== selectedCategory) {
      setSelectedCategory(urlCategory);
    }
  }, [searchParams]);

  const handleCategoryChange = (cat: SchemeCategory) => {
    setSelectedCategory(cat);
    if (cat === 'all') {
      searchParams.delete('category');
    } else {
      searchParams.set('category', cat);
    }
    setSearchParams(searchParams);
  };

  const loadSchemes = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const cleanQ = debouncedQuery.trim();
        const categoryParam = selectedCategory === 'all' ? undefined : selectedCategory;

        const response = await fetchSchemes(
          {
            category: categoryParam,
            q: cleanQ || undefined,
            pageSize: 50,
          },
          { signal }
        );

        const mapped = response.items.map((item) =>
          mapBackendSchemeToFrontend(item, language)
        );
        setSchemes(mapped);
        setTotalCount(response.pagination.total);
      } catch (err: any) {
        if (err?.isAborted) return;
        console.error('[BrowseSchemes] Failed to fetch schemes:', err);
        setErrorMessage(
          err?.isNetworkError
            ? t('chatErrorMessage', language)
            : t('errorLoadingSchemes', language)
        );
      } finally {
        setIsLoading(false);
      }
    },
    [debouncedQuery, selectedCategory, language]
  );

  useEffect(() => {
    const controller = new AbortController();
    loadSchemes(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadSchemes]);

  const handleResetFilters = () => {
    setSearchQuery('');
    setDebouncedQuery('');
    handleCategoryChange('all');
  };

  return (
    <div className="min-h-screen bg-canvas text-ink pb-24">
      <Header title={t('navBrowse', language)} subtitle="Directory & Filter" showBack />

      <main className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="w-5 h-5 text-ink/50 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('browseSearchPlaceholder', language)}
            className="w-full bg-surface border border-sand rounded-card pl-11 pr-10 py-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-forest shadow-card min-h-[48px]"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-ink/50 hover:text-ink p-1"
              aria-label="Clear search query"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Category Filter Pills (Horizontal Scroll) */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-1">
          {categories.map((cat) => {
            const isSelected = selectedCategory === cat;
            const labelObj = CATEGORY_LABELS[cat];
            const primaryLabel = labelObj ? (labelObj[language] || labelObj.en) : cat;

            return (
              <button
                key={cat}
                onClick={() => handleCategoryChange(cat)}
                className={`px-3.5 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 min-h-[36px] ${
                  isSelected
                    ? 'bg-forest text-white shadow-xs'
                    : 'bg-surface text-ink/70 border border-sand hover:border-forest/40'
                }`}
              >
                <span>{primaryLabel}</span>
              </button>
            );
          })}
        </div>

        {/* Results Counter & Active Filter Badge */}
        <div className="flex items-center justify-between text-xs text-ink/65 pt-1 px-1">
          <span>
            {isLoading ? '...' : totalCount} {t('schemesDisplayedCount', language)}
          </span>
          {(selectedCategory !== 'all' || searchQuery.trim() !== '') && (
            <button
              onClick={handleResetFilters}
              className="text-forest hover:underline font-semibold"
            >
              {t('resetFilter', language)}
            </button>
          )}
        </div>

        {/* Schemes List States */}
        {isLoading ? (
          <div className="space-y-3" role="status" aria-label={t('loadingSchemes', language)}>
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="bg-surface rounded-card border border-sand shadow-card p-4 border-l-4 border-l-sand animate-pulse space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="h-3 bg-sand/60 rounded w-1/3"></div>
                  <div className="h-5 bg-sand/60 rounded-full w-20"></div>
                </div>
                <div className="h-5 bg-sand/60 rounded w-3/4"></div>
                <div className="h-3 bg-sand/60 rounded w-1/2"></div>
                <div className="h-12 bg-canvas rounded-lg"></div>
              </div>
            ))}
          </div>
        ) : errorMessage ? (
          <div className="bg-surface rounded-card p-8 border border-sand text-center space-y-3 shadow-card">
            <div className="w-10 h-10 rounded-full bg-amber-50 text-amber-800 flex items-center justify-center mx-auto">
              <AlertCircle className="w-5 h-5" />
            </div>
            <h3 className="font-heading font-bold text-base text-ink">
              {errorMessage}
            </h3>
            <p className="text-xs text-ink/70 max-w-sm mx-auto">
              {t('chatErrorMessage', language)}
            </p>
            <button
              onClick={() => loadSchemes()}
              className="inline-flex items-center gap-1.5 bg-forest hover:bg-forest-deep text-white text-xs font-bold py-2.5 px-4 rounded-full transition-colors shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>{t('retryAction', language)}</span>
            </button>
          </div>
        ) : schemes.length > 0 ? (
          <div className="space-y-3">
            {schemes.map((scheme) => (
              <SchemeCard key={scheme.id} scheme={scheme} />
            ))}
          </div>
        ) : (
          <div className="bg-surface rounded-card p-8 border border-sand text-center space-y-3 shadow-card">
            <SlidersHorizontal className="w-10 h-10 text-ink/40 mx-auto" />
            <h3 className="font-heading font-bold text-base text-ink">
              {t('noSchemesFoundTitle', language)}
            </h3>
            <p className="text-xs text-ink/70 max-w-sm mx-auto">
              {t('noSchemesFoundDesc', language)}
            </p>
            <button
              onClick={handleResetFilters}
              className="bg-forest hover:bg-forest-deep text-white text-xs font-bold py-2.5 px-4 rounded-full shadow-xs"
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
