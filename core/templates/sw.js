const CACHE_NAME = 'rapidresq-v1';
const ASSETS = [
    '/api/app/',
    '/static/css/style.css',
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap'
];

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener('fetch', (event) => {
    // Fix: Explicitly bypass service worker for Tailwind CDN to resolve CORS issues
    if (event.request.url.includes('tailwindcss.com')) {
        return;
    }

    // Fix: Bypass service worker for other cross-origin requests
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                return response || fetch(event.request);
            })
            .catch(() => {
                // Graceful fallback for offline same-origin requests
                return new Response("Offline mode active.");
            })
    );
});