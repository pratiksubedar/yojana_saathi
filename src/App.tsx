import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';

// Pages
import { Home } from './pages/Home';
import { LanguageSelection } from './pages/LanguageSelection';
import { Onboarding } from './pages/Onboarding';
import { AssistantChat } from './pages/AssistantChat';
import { ProfileConfirmation } from './pages/ProfileConfirmation';
import { BrowseSchemes } from './pages/BrowseSchemes';
import { EligibilityResults } from './pages/EligibilityResults';
import { SchemeDetail } from './pages/SchemeDetail';
import { DocumentChecklist } from './pages/DocumentChecklist';
import { WhyNotEligible } from './pages/WhyNotEligible';
import { MySchemes } from './pages/MySchemes';
import { SettingsProfile } from './pages/SettingsProfile';
import { ErrorFallback } from './pages/ErrorFallback';
import { OfflineBanner } from './components/OfflineBanner';
import { LanguageSwitchConfirmation } from './components/LanguageSwitchConfirmation';

export const App: React.FC = () => {
  return (
    <AppProvider>
      <Router>
        <div className="min-h-screen bg-neutral-canvas text-neutral-ink font-sans selection:bg-brand-indigo/20 selection:text-brand-indigo flex flex-col">
          <OfflineBanner />
          <LanguageSwitchConfirmation />
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/language" element={<LanguageSelection />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/assistant" element={<AssistantChat />} />
              <Route path="/profile" element={<ProfileConfirmation />} />
              <Route path="/browse" element={<BrowseSchemes />} />
              <Route path="/eligibility" element={<EligibilityResults />} />
              <Route path="/scheme/:id" element={<SchemeDetail />} />
              <Route path="/checklist/:id" element={<DocumentChecklist />} />
              <Route path="/why-not-eligible/:id" element={<WhyNotEligible />} />
              <Route path="/why-not-eligible" element={<WhyNotEligible />} />
              <Route path="/my-schemes" element={<MySchemes />} />
              <Route path="/locker" element={<Navigate to="/my-schemes" replace />} />
              <Route path="/settings" element={<SettingsProfile />} />
              <Route path="/resilience-states" element={<ErrorFallback />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </div>
      </Router>
    </AppProvider>
  );
};

export default App;

