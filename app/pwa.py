from __future__ import annotations

MANIFEST = {
    "name": "Owlet Dashboard",
    "short_name": "Owlet",
    "id": "/",
    "description": "Private Owlet Dream Sock / Smart Sock history dashboard.",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f5f7fb",
    "theme_color": "#122033",
    "orientation": "portrait-primary",
    "categories": ["health", "utilities"],
    "icons": [
        {
            "src": "/icon-32.png",
            "sizes": "32x32",
            "type": "image/png",
            "purpose": "any",
        },
        {
            "src": "/icon-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any maskable",
        },
        {
            "src": "/icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable",
        },
    ],
}

SERVICE_WORKER_JS = """
const CACHE_NAME = 'owlet-dashboard-v2';
// Only truly immutable assets are safe to serve cache-first. Styles and
// scripts change with every release, so they go network-first below —
// otherwise one stale theme.css leaves the app half-styled until the
// cache happens to rotate.
const IMMUTABLE = [
  '/favicon.ico',
  '/icon-32.png',
  '/icon-180.png',
  '/icon-192.png',
  '/icon-512.png',
  '/logo.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(IMMUTABLE.concat(['/', '/manifest.webmanifest'])))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

function networkFirst(request, cacheKey) {
  return fetch(request)
    .then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(cacheKey || request, copy));
      }
      return response;
    })
    .catch(() => caches.match(cacheKey || request).then(cached => cached || Response.error()));
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.includes('/api/')) return;
  if (url.pathname.startsWith('/share/')) return;

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, '/'));
    return;
  }

  if (IMMUTABLE.includes(url.pathname)) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        return response;
      }))
    );
    return;
  }

  // theme.css, insights.js, manifest — fresh when online, cached offline
  event.respondWith(networkFirst(request));
});
""".strip()
