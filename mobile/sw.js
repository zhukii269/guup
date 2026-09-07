const CACHE_NAME = 'etf-master-v1';
const ASSETS = [
  './',
  './index.html',
  './engine.js',
  './echarts.min.js',
  './manifest.json',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  // 对于静态前端资源使用 Cache First 策略
  if (ASSETS.some(a => event.request.url.includes(a.replace('./', '')))) {
    event.respondWith(
      caches.match(event.request).then(cached => cached || fetch(event.request))
    );
  } else {
    // 对于实时金融行情走 Network First
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
  }
});
