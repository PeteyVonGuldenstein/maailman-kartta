# Maailman kartta -pelin resepti

Tällä tiedostolla pelin voi rakentaa uudelleen tekoälyagentilla (tai käsin).
Lyhyt prompti tuottaa samanhenkisen pelin yhdellä kehotteella; täysi speksi
sisältää kaikki yksityiskohdat, joihin tämä toteutus päätyi iteroimalla.

## Lyhyt prompti

> C64:llä oli aikanaan peli nimeltä Euroopan kartta, jossa helikopterilla
> etsittiin kaupunkia tai maata. Tee samanlainen mobiiliselaimessa toimiva
> peli yhtenä HTML-tiedostona ilman riippuvuuksia, mutta koko maailmasta:
> alkuvalikossa valitaan maanosa. Käytä aitoja maiden rajoja, järviä ja
> jokia (Natural Earth 50m GeoJSON → yksinkertaistetut SVG-polut, oma
> equirectangular-projektio per maanosa). Kamera on zoomattu ja seuraa
> kopteria, kulmassa on minikartta. Ohjaus virtuaalitatilla; laskeutuminen
> ja paikan tarkistus tuplanapauttamalla tattia. Pelimuodot: pääkaupungit,
> suurkaupungit, maat, luonnonkohteet (meret, järvet, joet, vuoristot,
> aavikot) ja sekoitus. Aikahyökkäys: kello alkaa 2 min 30 s:sta, oikea
> löytö antaa +5 s, väärä merkkaus vie −20 s ja joka 10. löytö antaa +20 s; peli päättyy, kun kaikki
> pelimuodon kohteet on löydetty tai aika loppuu. Ennätykset maanosittain
> localStorageen. Kaikki tekstit suomeksi.

## Täysi speksi

### Konsepti
Pelaaja valitsee maanosan (Eurooppa, Aasia, Afrikka, Pohjois-Amerikka,
Etelä-Amerikka, Oseania) ja pelimuodon, lentää helikopterilla kartalla ja
etsii pyydetyn kohteen: "Etsi kaupunki: Pariisi", "Etsi maa: Portugali"
tai "Etsi: Sahara". Kierros jatkuu kelloa vastaan, kunnes pelimuodon
kaikki kohteet on löydetty tai aika loppuu.

### Tekniikka
- Yksi HTML-sivu + generoitu `world_data.js` (kehitys); jakeluversiossa
  data upotetaan HTML-tiedostoon (`make_offline.py` → ~650 KB, toimii
  offline). HTML + CSS + vanilla JS + inline-SVG, ei riippuvuuksia.
- Puhtaat funktiot (projektio, point-in-polygon, viivaetäisyys,
  tehtävägeneraattori, pisteytys) skriptin alussa, UI-koodi
  `if (typeof document !== "undefined")` -lohkossa → testattavissa Nodella.
- `<head>`issä pieni virheenkerääjä, joka näyttää JS-virheet (tai "koodi
  ei käynnisty" -varoituksen) aloitusruudussa — tärkeä offline-jakelussa,
  koska monet esikatselimet eivät suorita JavaScriptiä.
- Retro-teema: C64-sininen (#40318d), violetti kehys (#7869c4),
  keltainen korostus (#ffd94a).

### Kartat (build_world.py)
- Aineistot (Natural Earth GeoJSON): `ne_50m_admin_0_countries` (+
  `ne_10m_admin_0_countries_ukr`, jolla Krim piirretään Ukrainalle),
  `ne_50m_lakes`, `ne_50m_rivers_lake_centerlines`,
  `ne_50m_geography_marine_polys`, `ne_50m_geography_regions_polys`.
- Per maanosa: oma bbox ja equirectangular-projektio cos-korjauksella
  (Eurooppa lon −25…45, lat 34…72, cos 50°; Aasia 25…150/−12…60, cos 30°;
  Afrikka −20…55/−36…38, cos 0°; P-Amerikka −170…−50/5…72, cos 45°;
  E-Amerikka −85…−33/−56…13, cos 20°; Oseania 110…180/−48…0, cos 25°).
  Kaikki leveys 1000; Sutherland–Hodgman-leikkaus, Douglas–Peucker 1 px.
- Kohdemaat kuratoituina suomenkielisin nimin (Eurooppa 42, Aasia 37,
  Afrikka 37, P-Am 13, E-Am 12, Oseania 7); muut maat taustaväriin,
  Antarktis pois, Grönlanti mukana vain P-Amerikassa (kohteena).
- Isot järvet piirretään merenvärisinä, kohdejoet ohuina sinisinä viivoina.
- Luonnonkohteet (10–25/maanosa): meripolygonit (Itämeri, Meksikonlahti,
  Korallimeri…), järvet (Baikal, Viktorianjärvi, Titicaca…), aluepolygonit
  (Sahara, Himalaja, Andit, Alpit, Tasmania…) ja joet keskilinjoina
  (Niili, Amazon, Jangtse, Tonava, Mississippi, Murray…).

### Pelimekaniikka
- Ohjaus: analoginen virtuaalitatti vasemmassa alakulmassa (128 px,
  kuollut alue 15 %, poikkeutus = suunta ja nopeus, pointer capture) TAI
  kosketus karttaan (kopteri lentää osoitettuun pisteeseen, tarttuu
  lähimpään kaupunkimerkkiin) TAI nuolinäppäimet.
- Laskeutuminen ja tarkistus VAIN tuplanapauttamalla tattia (< 350 ms)
  tai välilyönnillä — ei pysähtymällä. 600 ms:n jäähy estää tuplasakot.
- Km-pohjaiset vakiot skaalataan maanosan mittakaavaan (km/px =
  111,32 × lat-väli / H): näkymä 1 050 km lyhyemmällä ruutusivulla,
  nopeus 650 km/s, kaupunkiosuma 85 km, merkkiin tarttuminen 110 km,
  jokiosuma 50 km, rannikkotoleranssi 35 km, keskipistefallback 60 km.
  Myös grafiikan koot (kopteri 0,6×, merkit r 5, nimilaput 15 px,
  viivanpaksuudet) kerrotaan ui-skaalalla U = VIEW/210, jotta näyttökoko
  on sama joka maanosassa.
- Osumatarkistus: kaupunki = etäisyys ≤ 85 km; maa ja aluekohde =
  point-in-polygon + rannikkotoleranssi + keskipistesäde; joki =
  etäisyys keskilinjasta ≤ 50 km.
- Kamera seuraa kopteria pehmeästi (lerp 3/s) ennakolla (nopeus × 0,35),
  minikartta kulmassa (`<use>` samaan #world-ryhmään, näkymäsuorakulmio
  ja kopteripiste skaalataan maanosan kokoon).
- Aikahyökkäys: kierros käy läpi pelimuodon koko kohdelistan. Kello alkaa
  2 min 30 s:sta ja käy koko ajan (paitsi löytöjuhlinnan aikana); oikea
  löytö +5 s, väärä merkkaus −20 s, joka 10. löydöstä sarjabonus +20 s. Peli päättyy, kun kaikki kohteet on
  löydetty tai aika loppuu. Tulos = löydettyjen määrä; täydessä
  läpäisyssä tasatilanteen ratkaisee jäljelle jäänyt aika. HUD:ssa
  löytölaskuri ja kello (punainen alle 30 s). Ennätykset `localStorage`en
  avaimella `maanosa:muoto`, versionumero mukana (nosto nollaa).
- Huti: punainen suuntanuoli ja "Ei osunut! −20 s · X on n. NNN km päässä."
  Osuma: vihreä pulssi, nimi paljastuu kartalle, maa värjäytyy vihreäksi,
  nouseva duuriääni (WebAudio).
- Kaupunkimerkit (valkoiset pallot, ei nimiä) näkyvät kaupunkimuodoissa;
  mailla ja luonnonkohteilla ei merkkejä.

### Sisältö
Pääkaupungit ja suurkaupungit suomalaisin nimin per maanosa (Eurooppa
41 + 37, Aasia 38 + 17, Afrikka 37 + 10, P-Am 13 + 18, E-Am 12 + 14,
Oseania 7 + 11), koordinaatit datana HTML:ssä. Kaikki UI-tekstit suomeksi.

### Jakelu
Pythonin `ThreadingHTTPServer` (portti 8095, `Cache-Control: no-store`) +
`@reboot`-cron; offline-tiedosto `maailman-kartta.html` jaettavaksi.
