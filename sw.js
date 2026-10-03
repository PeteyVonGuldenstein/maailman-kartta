// Maailman kartta -pelin service worker: välimuisti ensin, päivitys taustalla.
// Peli on staattinen ja data muuttuu harvoin, joten avaus ei jää odottamaan
// verkkoa: vastaus tulee heti välimuistista ja uusi versio haetaan taustalla.
//
// CACHE-nimen loppu on tiedostojen tiiviste, jonka make_offline.py kirjoittaa.
// Mikä tahansa muutos peliin tai dataan muuttaa siis tätä tiedostoa, jolloin
// selain asentaa uuden workerin ja hakee KAIKKI tiedostot kerralla uuteen
// välimuistiin — index.html ja world_data.js eivät voi päätyä eri versioiksi.
const CACHE = "maailman-kartta-c6039ba42f";
const CORE = ["./", "index.html", "world_data.js", "kuntakeskukset.js",
              "manifest.json",
              "icon-192.png", "icon-512.png", "apple-touch-icon.png"];

self.addEventListener("install", e => {
  // cache: "reload" ohittaa selaimen HTTP-välimuistin (GitHub Pages antaa
  // 10 min max-agen), muuten uuteen versioon voisi tulla vanhoja tiedostoja
  e.waitUntil(caches.open(CACHE)
    .then(c => c.addAll(CORE.map(u => new Request(u, { cache: "reload" }))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (new URL(req.url).origin !== location.origin) return;
  const net = fetch(req);
  net.catch(() => {});   // offline: välimuistin osuma riittää
  // kopio otetaan heti, ennen kuin sivu ehtii lukea vastauksen rungon
  const copy = net.then(r => r.ok ? r.clone() : null);
  // tallennus kuuluu waitUntiliin, ettei selain lopeta workeria kesken
  e.waitUntil(copy
    .then(c => c && caches.open(CACHE).then(cache => cache.put(req, c)))
    .catch(() => {}));
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || net));
});
