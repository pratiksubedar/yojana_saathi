/**
 * Yojana Saathi - Network Status and PWA Installation Hook
 * Milestone 6.6: Provides reactive online/offline state, connection checking,
 * and PWA install prompt handling with full cleanup.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface NetworkStatus {
  isOnline: boolean;
  hasReconnected: boolean;
  isInstallable: boolean;
  promptInstall: () => Promise<boolean>;
  checkConnection: () => Promise<boolean>;
}

export function useNetworkStatus(): NetworkStatus {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    return typeof navigator !== 'undefined' ? navigator.onLine : true;
  });

  const [hasReconnected, setHasReconnected] = useState<boolean>(false);
  const [isInstallable, setIsInstallable] = useState<boolean>(false);
  const deferredPromptRef = useRef<any>(null);
  const reconnectTimerRef = useRef<any>(null);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setHasReconnected(true);

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      reconnectTimerRef.current = setTimeout(() => {
        setHasReconnected(false);
      }, 5000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setHasReconnected(false);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      deferredPromptRef.current = e;
      setIsInstallable(true);
    };

    const handleAppInstalled = () => {
      deferredPromptRef.current = null;
      setIsInstallable(false);
      console.log('[PWA] App successfully installed.');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleAppInstalled);
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, []);

  const promptInstall = useCallback(async (): Promise<boolean> => {
    if (!deferredPromptRef.current) {
      return false;
    }

    try {
      deferredPromptRef.current.prompt();
      const choiceResult = await deferredPromptRef.current.userChoice;
      deferredPromptRef.current = null;
      setIsInstallable(false);
      return choiceResult.outcome === 'accepted';
    } catch (err) {
      console.error('[PWA] Error triggering install prompt:', err);
      return false;
    }
  }, []);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setIsOnline(false);
      return false;
    }

    try {
      // Lightweight connection ping with cache busting
      const response = await fetch(`/manifest.webmanifest?_ping=${Date.now()}`, {
        method: 'HEAD',
        cache: 'no-store',
      });
      const online = response.ok;
      setIsOnline(online);
      return online;
    } catch {
      setIsOnline(false);
      return false;
    }
  }, []);

  return {
    isOnline,
    hasReconnected,
    isInstallable,
    promptInstall,
    checkConnection,
  };
}

