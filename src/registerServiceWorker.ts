/**
 * Yojana Saathi - Service Worker Registration Manager
 * Milestone 6.6: Registers the versioned PWA service worker over HTTPS or localhost.
 */

export interface ServiceWorkerRegistrationCallbacks {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
  onError?: (error: Error) => void;
}

export function isServiceWorkerSupported(): boolean {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator;
}

export async function registerServiceWorker(
  callbacks?: ServiceWorkerRegistrationCallbacks
): Promise<ServiceWorkerRegistration | null> {
  if (!isServiceWorkerSupported()) {
    console.info('[PWA] Service Worker not supported by this browser.');
    return null;
  }

  // Only register over HTTPS or localhost
  const isLocalhost = Boolean(
    window.location.hostname === 'localhost' ||
    window.location.hostname === '[::1]' ||
    window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/)
  );

  if (window.location.protocol !== 'https:' && !isLocalhost) {
    console.warn('[PWA] Service Worker requires HTTPS or localhost.');
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register('/sw.js', {
      scope: '/',
    });

    registration.onupdatefound = () => {
      const installingWorker = registration.installing;
      if (!installingWorker) return;

      installingWorker.onstatechange = () => {
        if (installingWorker.state === 'installed') {
          if (navigator.serviceWorker.controller) {
            console.log('[PWA] New version available; refresh to activate.');
            callbacks?.onUpdate?.(registration);
          } else {
            console.log('[PWA] App shell precached for offline use.');
            callbacks?.onSuccess?.(registration);
          }
        }
      };
    };

    callbacks?.onSuccess?.(registration);
    return registration;
  } catch (err: any) {
    console.error('[PWA] Service Worker registration failed:', err);
    callbacks?.onError?.(err);
    return null;
  }
}

export async function unregisterServiceWorkers(): Promise<boolean> {
  if (!isServiceWorkerSupported()) return false;
  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      await registration.unregister();
    }
    return true;
  } catch (err) {
    console.error('[PWA] Failed to unregister service workers:', err);
    return false;
  }
}

