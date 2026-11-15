/**
 * Yojana Saathi - Progressive Web App Service Worker
 * Version: 1.0.0 (Phase 6, Milestone 6.6)
 *
 * CACHING PRINCIPLES & PRIVACY ASSURANCES:
 * 1. Safe App Shell & Static Asset Caching only.
 * 2. STRICTLY NEVER cache POST, PUT, DELETE or non-GET requests.
 * 3. STRICTLY NEVER cache /api/* endpoints (chat turns, streaming SSE, document checklists, sessions).
 * 4. STRICTLY NEVER cache personal citizen profile attributes, transcripts, or session credentials.
 * 5. STRICTLY NEVER cache external LLM/AI provider requests.
 * 6. Clean up obsolete cache versions upon service worker activation.
 */

const CACHE_NAME = 'yojana-saathi-shell-v1';

// Critical core app shell assets precached on install
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icon.svg',
  '/icon-192.png',
  '/icon-512.png'
];

// Patterns that must NEVER be stored in Cache Storage under any circumstances
const SENSITIVE_OR_DYNAMIC_PATTERNS = [
  '/api/',
  '/chat',
  '/stream',
  '/documents/collect',
  '/evaluate'
];

/**
 * Service Worker Installation: precache minimal app shell
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

/**
 * Service Worker Activation: clean up obsolete cache versions and claim clients
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[ServiceWorker] Purging legacy cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

/**
 * Determines whether a request is prohibited from caching
 */
function isDisallowedFromCache(request, url) {
  // Non-GET requests (POST, OPTIONS, etc.) can never be cached
  if (request.method !== 'GET') {
    return true;
  }

  // Scheme must be http or https
  if (!url.protocol.startsWith('http')) {
    return true;
  }

  // Dynamic backend APIs and chat streams must NEVER be cached
  for (const pattern of SENSITIVE_OR_DYNAMIC_PATTERNS) {
    if (url.pathname.includes(pattern)) {
      return true;
    }
  }

  // Third-party AI/Gemini or cloud endpoints must never be cached
  if (url.hostname.includes('googleapis.com') || url.hostname.includes('gemini')) {
    return true;
  }

  return false;
}

/**
 * Fetch Event Handler
 */
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // 1. Non-GET requests pass directly through to network without interception
  if (request.method !== 'GET') {
    return;
  }

  // 2. Dynamic API requests: Strict Network-Only. If offline, return explicit 503 JSON.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({
            error: 'offline',
            detail: 'You are currently offline. Dynamic AI evaluation and live queries require an active connection.',
            timestamp: new Date().toISOString()
          }),
          {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json' }
          }
        );
      })
    );
    return;
  }

  // 3. Sensitive / disallowed endpoints pass directly through to network
  if (isDisallowedFromCache(request, url)) {
    return;
  }

  // 4. HTML Navigation requests (SPA page routes): Network-first with cache fallback to /index.html
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => {
        return caches.match('/index.html').then((cachedIndex) => {
          if (cachedIndex) return cachedIndex;
          return caches.match('/');
        });
      })
    );
    return;
  }

  // 5. Static assets (JS, CSS, images, fonts): Cache-first with network fallback and background update
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch in background to update cache for next load
        fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse));
          }
        }).catch(() => {
          // Offline, background update silently fails
        });
        return cachedResponse;
      }

      // Not in cache, fetch from network
      return fetch(request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }

        // Clone and cache the newly fetched static asset
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(request, responseToCache);
        });

        return networkResponse;
      }).catch(() => {
        // Asset fetch failed and not in cache
        return new Response('', { status: 404, statusText: 'Not Found' });
      });
    })
  );
});

