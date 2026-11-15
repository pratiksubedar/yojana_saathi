import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, BookmarkCheck, Mic } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { t } from '../data/translations';

export interface BottomNavProps {
  onVoiceClick?: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ onVoiceClick }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { language, savedSchemeIds } = useApp();

  // Phase 5: Profile access moved to Header.tsx (path: '/profile'); removed from active bottom nav bar
  const navItems = [
    { path: '/', label: t('navHome', language), icon: Home },
    { 
      path: '/assistant', 
      label: t('navVoiceAI', language), 
      icon: Mic, 
      isSpecial: true 
    },
    { 
      path: '/my-schemes', 
      label: t('navLocker', language), 
      icon: BookmarkCheck,
      badge: savedSchemeIds.length > 0 ? savedSchemeIds.length : undefined
    },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-surface/95 backdrop-blur-md border-t border-sand shadow-lg pb-safe">
      <div className="max-w-md md:max-w-xl mx-auto px-6 h-16 flex items-center justify-around">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || 
            (item.path !== '/' && location.pathname.startsWith(item.path));
          const Icon = item.icon;

          if (item.isSpecial) {
            return (
              <button
                key={item.path}
                type="button"
                onClick={() => {
                  const isAssistantPage =
                    location.pathname === '/assistant' ||
                    location.pathname.startsWith('/assistant');

                  if (isAssistantPage) {
                    if (onVoiceClick) {
                      onVoiceClick();
                    }
                    window.dispatchEvent(new CustomEvent('yojana:start-voice-ai'));
                  } else {
                    navigate('/assistant?voice=true&mode=chat&start=' + Date.now());
                  }
                }}
                className="relative -top-3 flex flex-col items-center group focus:outline-none"
                aria-label="Start Voice Conversation"
              >
                <div className={`w-14 h-14 rounded-full flex items-center justify-center shadow-orb transition-transform transform active:scale-95 ${
                  isActive
                    ? 'bg-forest-deep ring-4 ring-forest/20 text-white'
                    : 'bg-forest text-white hover:bg-forest-deep'
                }`}>
                  <Mic className="w-6 h-6 animate-pulse" />
                </div>
                <span className={`text-[11px] font-bold mt-0.5 ${isActive ? 'text-forest' : 'text-ink/70'}`}>
                  {item.label}
                </span>
              </button>
            );
          }

          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`flex-1 flex flex-col items-center justify-center py-1 transition-colors relative min-h-[48px] ${
                isActive ? 'text-forest font-bold' : 'text-ink/60 hover:text-ink'
              }`}
            >
              <div className="relative">
                <Icon className={`w-5 h-5 transition-transform ${isActive ? 'scale-110' : ''}`} />
                {item.badge !== undefined && (
                  <span className="absolute -top-1.5 -right-2 bg-amber-600 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center ring-2 ring-surface">
                    {item.badge}
                  </span>
                )}
              </div>
              <span className="text-[11px] mt-1 font-medium truncate max-w-[80px]">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
