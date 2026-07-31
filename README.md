# Maailman kartta 🚁

C64-henkinen maantiedon etsintäpeli: lennä helikopterilla ja etsi kaupungit,
maat, kunnat, kuntakeskukset ja luonnonkohteet kartalta. Suomi, kuusi maanosaa ja Manner-Suomen
18 maakuntaa kuntineen, aikahyökkäys- ja opettelumuodot. Pelikieleksi voi
vaihtaa englannin (🌐-nappi valikossa; paikannimetkin vaihtuvat, ennätykset
ovat yhteiset). Toimii puhelimessa webappina, myös offline. PWA-sovelluksen
nimi on aina suomeksi.

**Pelaa: https://peteyvonguldenstein.github.io/maailman-kartta/**

Avaa linkki puhelimessa ja lisää peli aloitusnäytölle
(iPhone: Safari → jaa → *Lisää Koti-valikkoon*; Android: Chrome → ⋮ → *Asenna sovellus*)
— sen jälkeen peli toimii ilman verkkoyhteyttä.

Kartat: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
Kunta- ja maakuntarajat: [Tilastokeskus](https://geo.stat.fi/),
kuntapohjaiset tilastointialueet 2026 (CC BY 4.0).
Suomen järvet: [SYKE](https://www.syke.fi/avointieto) Ranta10, rantaviiva
1:10 000 (CC BY 4.0). Valta- ja kantatiet: [Väylävirasto](https://vayla.fi/),
tieosoiteverkko (CC BY 4.0). Kuntakeskusten sijainnit ja nimet:
[Wikidata](https://www.wikidata.org/) (CC0) — kohde on kunnan keskustaajama,
joten nimi on esimerkiksi Rautjärven sijasta Simpele.
Generointi: `build_world.py`, `fetch_syke_lakes.py` ja
`fetch_kuntakeskukset.py`. Testit: `node test_game.js`
(pelilogiikka ilman selainta) ja `node test_ui.js` (käyttöliittymä headless
Chromiumilla; vaatii `npx playwright install chromium` ja ajetun
`make_offline.py`:n).
