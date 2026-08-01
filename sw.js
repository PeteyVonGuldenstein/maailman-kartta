// Maailman kartta -pelin service worker: välimuisti ensin, päivitys taustalla.
// Peli on staattinen ja data muuttuu harvoin, joten avaus ei jää odottamaan
// verkkoa: vastaus tulee heti välimuistista ja uusi versio haetaan taustalla
// käyttöön seuraavaa avausta varten.
// Nimen versionumeron nosto pakottaa vanhan välimuistin tyhjennyksen.
const CACHE = "maailman-kartta-v13";
const CORE = ["./", "index.html", "world_data.js", "kuntakeskukset.js",
              "manifest.json",
              "icon-192.png", "icon-512.png", "apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE))
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
  e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => {
    const net = fetch(req).then(resp => {
      if (resp.ok) {
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }
      return resp;
    }).catch(() => hit);
    // osuma tarjoillaan heti; nouto jatkuu taustalla välimuistin päivittämiseksi
    // (waitUntil pitää workerin hengissä siksi aikaa)
    if (hit) e.waitUntil(net);
    return hit || net;
  }));
});
