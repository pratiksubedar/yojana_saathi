/**
 * Yojana Saathi - PWA, Service Worker & Offline Resilience Unit Tests
 * Milestone 6.6: Tests manifest validity, service worker rules, cache exclusion,
 * multilingual offline translations, and network resilience.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');

describe('PWA Web App Manifest Validation', () => {
  const manifestPath = path.join(ROOT_DIR, 'public', 'manifest.webmanifest');

  test('manifest.webmanifest exists and parses as valid JSON', () => {
    assert.strictEqual(fs.existsSync(manifestPath), true, 'manifest.webmanifest must exist in public/');
    const raw = fs.readFileSync(manifestPath, 'utf8');
    const manifest = JSON.parse(raw);

    assert.ok(manifest.name, 'manifest must have a name');
    assert.ok(manifest.short_name, 'manifest must have a short_name');
    assert.strictEqual(manifest.start_url, '/', 'start_url must be /');
    assert.strictEqual(manifest.display, 'standalone', 'display must be standalone');
    assert.strictEqual(manifest.theme_color, '#4F46E5', 'theme_color must match brand indigo');
    assert.strictEqual(manifest.background_color, '#F8FAFC', 'background_color must match neutral canvas');
    assert.ok(Array.isArray(manifest.icons), 'icons must be an array');
    assert.ok(manifest.icons.length >= 3, 'must provide at least 192px, 512px, and svg icons');
  });

  test('all icons referenced in manifest exist on disk with valid file size', () => {
    const raw = fs.readFileSync(manifestPath, 'utf8');
    const manifest = JSON.parse(raw);

    for (const icon of manifest.icons) {
      const iconPath = path.join(ROOT_DIR, 'public', icon.src.replace(/^\//, ''));
      assert.strictEqual(fs.existsSync(iconPath), true, `Referenced icon ${icon.src} must exist at ${iconPath}`);
      const stat = fs.statSync(iconPath);
      assert.ok(stat.size > 100, `Icon file ${icon.src} must not be empty (size: ${stat.size} bytes)`);
    }
  });
});

describe('index.html PWA Configuration', () => {
  const indexPath = path.join(ROOT_DIR, 'index.html');

  test('index.html links to web manifest and mobile meta tags', () => {
    const html = fs.readFileSync(indexPath, 'utf8');

    assert.ok(html.includes('rel="manifest"'), 'index.html must link to web manifest');
    assert.ok(html.includes('href="/manifest.webmanifest"'), 'index.html must reference /manifest.webmanifest');
    assert.ok(html.includes('name="theme-color"'), 'index.html must have theme-color meta tag');
    assert.ok(html.includes('name="apple-mobile-web-app-capable"'), 'index.html must declare apple-mobile-web-app-capable');
    assert.ok(html.includes('rel="apple-touch-icon"'), 'index.html must declare apple-touch-icon');
  });
});

describe('Service Worker Security & Caching Rules (sw.js)', () => {
  const swPath = path.join(ROOT_DIR, 'public', 'sw.js');

  test('sw.js exists and defines versioned cache', () => {
    assert.strictEqual(fs.existsSync(swPath), true, 'public/sw.js must exist');
    const swContent = fs.readFileSync(swPath, 'utf8');

    assert.ok(swContent.includes('CACHE_NAME'), 'sw.js must define CACHE_NAME');
    assert.ok(swContent.includes('PRECACHE_ASSETS'), 'sw.js must define PRECACHE_ASSETS');
    assert.ok(swContent.includes('self.addEventListener(\'install\''), 'sw.js must have install listener');
    assert.ok(swContent.includes('self.addEventListener(\'activate\''), 'sw.js must have activate listener');
    assert.ok(swContent.includes('self.addEventListener(\'fetch\''), 'sw.js must have fetch listener');
  });

  test('sw.js cleans up obsolete cache versions upon activation', () => {
    const swContent = fs.readFileSync(swPath, 'utf8');
    assert.ok(swContent.includes('caches.delete'), 'sw.js must purge obsolete cache keys on activate');
    assert.ok(swContent.includes('self.clients.claim()'), 'sw.js must claim clients on activate');
  });

  test('sw.js strictly forbids caching of non-GET requests', () => {
    const swContent = fs.readFileSync(swPath, 'utf8');
    assert.ok(
      swContent.includes("request.method !== 'GET'"),
      'sw.js must check and immediately bypass non-GET requests'
    );
  });

  test('sw.js strictly forbids caching of dynamic /api/ endpoints and handles offline 503', () => {
    const swContent = fs.readFileSync(swPath, 'utf8');

    // Verification of API handling
    assert.ok(swContent.includes("url.pathname.startsWith('/api/')"), 'sw.js must detect /api/ routes');
    assert.ok(swContent.includes('503'), 'sw.js must return 503 Service Unavailable when /api/ is offline');
    assert.ok(swContent.includes('offline'), 'offline response must specify offline error code');

    // Sensitive patterns exclusion
    assert.ok(swContent.includes('/chat'), 'sw.js must prohibit caching chat endpoints');
    assert.ok(swContent.includes('/stream'), 'sw.js must prohibit caching SSE streaming endpoints');
    assert.ok(swContent.includes('/documents/collect'), 'sw.js must prohibit caching citizen document actions');
  });

  test('sw.js provides offline SPA navigation fallback to /index.html', () => {
    const swContent = fs.readFileSync(swPath, 'utf8');
    assert.ok(swContent.includes("request.mode === 'navigate'"), 'sw.js must detect navigation requests');
    assert.ok(swContent.includes('/index.html'), 'sw.js navigation fallback must match /index.html');
  });
});

describe('Multilingual Offline Translations', () => {
  const translationsPath = path.join(ROOT_DIR, 'src', 'data', 'translations.ts');

  test('all required offline translation keys exist for en, hi, kn, and te', () => {
    const content = fs.readFileSync(translationsPath, 'utf8');

    const requiredKeys = [
      'offlineBannerTitle',
      'offlineBannerDesc',
      'offlineStatusPill',
      'onlineStatusPill',
      'reconnectedNotice',
      'installAppAction',
      'offlineChatNotice',
      'checkConnectionAction',
      'offlineFeaturesListTitle',
      'offlineAvailableFeatures',
      'offlineUnavailableFeatures',
    ];

    const requiredLocales = ['en', 'hi', 'kn', 'te'];

    for (const key of requiredKeys) {
      assert.ok(
        content.includes(`${key}: {`),
        `translations.ts must define key: ${key}`
      );
    }

    // Verify key translations contain all 4 languages
    for (const loc of requiredLocales) {
      assert.ok(
        content.includes(`${loc}: '`),
        `translations.ts must contain translations for locale: ${loc}`
      );
    }
  });
});

describe('Network Resilience & Disconnection Handling', () => {
  test('offline guard prevents chat submission without queuing personal data', () => {
    const chatPagePath = path.join(ROOT_DIR, 'src', 'pages', 'AssistantChat.tsx');
    const chatContent = fs.readFileSync(chatPagePath, 'utf8');

    // Confirms offline check in AssistantChat
    assert.ok(chatContent.includes('useNetworkStatus'), 'AssistantChat must use useNetworkStatus');
    assert.ok(chatContent.includes('if (!isOnline)'), 'AssistantChat must block submission when !isOnline');
    assert.ok(chatContent.includes('offlineChatNotice'), 'AssistantChat must display offline notice');
    assert.ok(chatContent.includes('disabled={isSubmitting || !isOnline}'), 'Input form must be disabled when offline');
  });

  test('Header includes reactive offline badge', () => {
    const headerPath = path.join(ROOT_DIR, 'src', 'components', 'Header.tsx');
    const headerContent = fs.readFileSync(headerPath, 'utf8');

    assert.ok(headerContent.includes('useNetworkStatus'), 'Header must use useNetworkStatus');
    assert.ok(headerContent.includes('!isOnline &&'), 'Header must render offline badge when !isOnline');
    assert.ok(headerContent.includes('offlineStatusPill'), 'Header must display localized offlineStatusPill');
  });

  test('App renders OfflineBanner globally', () => {
    const appPath = path.join(ROOT_DIR, 'src', 'App.tsx');
    const appContent = fs.readFileSync(appPath, 'utf8');

    assert.ok(appContent.includes('<OfflineBanner />'), 'App.tsx must include <OfflineBanner />');
  });
});

