// sw.js - Service Worker for Cache Control
const CACHE_NAME = "muslim-stints-v1";
const FORCE_UPDATE = true; // Set to true during development

self.addEventListener("install", (event) => {
  console.log("Service Worker installing...");
  if (FORCE_UPDATE) {
    // Skip waiting and immediately activate
    self.skipWaiting();
  }
});

self.addEventListener("activate", (event) => {
  console.log("Service Worker activating...");

  event.waitUntil(
    // Clear all caches on activation
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log("Deleting cache:", cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        // Take control of all pages immediately
        return self.clients.claim();
      })
  );
});

self.addEventListener("fetch", (event) => {
  // During development, always fetch from network
  if (FORCE_UPDATE || event.request.url.includes("localhost")) {
    event.respondWith(
      fetch(event.request.clone()).catch(() => {
        // If network fails, try cache as fallback
        return caches.match(event.request);
      })
    );
    return;
  }

  // For production, implement cache-first strategy for static assets
  if (
    event.request.url.includes(".js") ||
    event.request.url.includes(".css") ||
    event.request.url.includes(".html")
  ) {
    event.respondWith(
      fetch(event.request.clone())
        .then((response) => {
          // Don't cache if it's not a successful response
          if (
            !response ||
            response.status !== 200 ||
            response.type !== "basic"
          ) {
            return response;
          }

          // Clone the response for caching
          const responseToCache = response.clone();

          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });

          return response;
        })
        .catch(() => {
          // Network failed, try cache
          return caches.match(event.request);
        })
    );
  }
});

// Listen for messages from the main thread
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }

  if (event.data && event.data.type === "CLEAR_CACHE") {
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      })
      .then(() => {
        console.log("All caches cleared");
        event.ports[0].postMessage({ success: true });
      });
  }
});
