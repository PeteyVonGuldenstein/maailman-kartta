// Maailman kartta -pelin puhtaiden funktioiden testit (Node, ilman DOM:ia)
const fs = require("fs");
const assert = require("assert");

const dir = "/root/euroopan-kartta";
const worldData = fs.readFileSync(dir + "/world_data.js", "utf8");
const html = fs.readFileSync(dir + "/index.html", "utf8");
const m = html.match(/<script>\n("use strict";[\s\S]*?)<\/script>/);
assert(m, "peliskripti löytyy HTML:stä");

// Ajetaan data + peliskripti; document ei ole määritelty, joten UI-lohko ohitetaan
globalThis.assert = assert;
(0, eval)(worldData + m[1] + `
// --- testit samassa scopessa ---
const KEYS = ["suomi","eurooppa","aasia","afrikka","pohjois_amerikka","usa","etela_amerikka","oseania"];
let seed = 42;
const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

// apurit: aluekohtaiset toleranssit kuten pelissä (km × kokokerroin)
function tol(C) {
  const k = kmPerPx(C), s = sizeScale(C, CONTINENTS.eurooppa);
  return { coast: 35 * s / k, ctr: 60 * s / k, line: 50 * s / k, hit: 85 * s / k };
}
function country(C, n) { return C.countries.find(c => c.n === n); }
function feature(C, n) { return C.features.find(f => f.n === n); }
function inCountry(C, name, lon, lat) {
  const [x, y] = project(lon, lat, C);
  const t = tol(C);
  return pointInArea(x, y, country(C, name), t.coast, t.ctr);
}
function inFeature(C, name, lon, lat) {
  const f = feature(C, name);
  const [x, y] = project(lon, lat, C);
  const t = tol(C);
  return f.k === "j" ? nearLines(x, y, f.l, t.line) : pointInArea(x, y, f, t.coast, t.ctr);
}

// Rakenne ja tehtävägeneraattori joka maanosalle ja muodolle
for (const key of KEYS) {
  const C = CONTINENTS[key];
  const cities = CITY_DATA[key];
  assert(C && cities, key + ": data olemassa");
  assert(C.countries.length >= (key === "suomi" ? 1 : 7), key + ": kohdemaita on");
  assert(C.features.length >= 10, key + ": luonnonkohteita on");
  // kaikki kaupungit kartalla ja jonkin polygonin lähistöllä
  for (const c of cities.pk.concat(cities.kau)) {
    const [x, y] = project(c[2], c[1], C);
    assert(x >= 0 && x <= C.W && y >= 0 && y <= C.H, key + ": " + c[0] + " kartalla");
  }
  // maatehtävät vain, jos kohdemaita on useampi (Suomessa vain yksi);
  // sekoituksessa sama kaupunki lasketaan kerran (esim. Boston: suurkaupunki + pääkaupunki)
  const nc = C.countries.length >= 2 ? C.countries.length : 0;
  const opk = cities.opk || [];
  const uniqCities = new Set([...cities.pk, ...cities.kau, ...opk].map(c => c[0])).size;
  const poolSize = { pk: cities.pk.length, kau: cities.kau.length, opk: opk.length,
    maa: nc, luonto: C.features.length,
    seka: uniqCities + nc + C.features.length };
  for (const mode of ["pk", "kau", "opk", "maa", "luonto", "seka"]) {
    const t = makeTasks(mode, C, cities, rnd);
    assert.strictEqual(t.length, poolSize[mode], key + "/" + mode + ": koko kohdelista");
    assert.strictEqual(new Set(t.map(x => x.kind + ":" + x.name)).size, t.length, key + "/" + mode + ": ei toistoja");
    for (const task of t)
      assert(task.x >= 0 && task.x <= C.W && task.y >= 0 && task.y <= C.H,
        key + "/" + mode + ": kohde kartalla: " + task.name);
  }
}

// Kokokerroin: Eurooppa on verrokki, isommat > 1, Suomi < 1
assert.strictEqual(sizeScale(CONTINENTS.eurooppa, CONTINENTS.eurooppa), 1, "Euroopan kerroin on 1");
assert(sizeScale(CONTINENTS.aasia, CONTINENTS.eurooppa) > 2, "Aasian kerroin > 2");
assert(sizeScale(CONTINENTS.suomi, CONTINENTS.eurooppa) < 0.3, "Suomen kerroin < 0,3");

// Suomen kartta: kaupungit ja luonnonkohteet
const FI = CONTINENTS.suomi;
assert(inCountry(FI, "Suomi", 24.94, 60.17), "Helsinki on Suomessa (Suomen kartta)");
assert(inCountry(FI, "Suomi", 19.94, 60.10), "Maarianhamina on Suomessa (Ahvenanmaa mukana)");
assert(!inCountry(FI, "Suomi", 18.06, 59.33), "Tukholma ei ole Suomessa");
assert(inFeature(FI, "Saimaa", 28.88, 61.87), "Savonlinna on Saimaalla");
assert(inFeature(FI, "Lappi", 25.73, 66.50), "Rovaniemi on Lapissa");
assert(inFeature(FI, "Kemijoki", 25.73, 66.50), "Rovaniemi on Kemijoen varrella");
assert(inFeature(FI, "Pohjanlahti", 20.0, 62.5), "Pohjanlahti osuu");

// Yhdysvaltain osavaltiot
const US = CONTINENTS.usa;
assert.strictEqual(US.countries.length, 48, "48 osavaltiota");
assert(inCountry(US, "Kalifornia", -118.24, 34.05), "Los Angeles on Kaliforniassa");
assert(inCountry(US, "Texas", -95.37, 29.76), "Houston on Texasissa");
assert(inCountry(US, "New York", -78.88, 42.89), "Buffalo on New Yorkin osavaltiossa");
assert(!inCountry(US, "Nevada", -118.24, 34.05), "Los Angeles ei ole Nevadassa");
assert.strictEqual(CITY_DATA.usa.opk.length, 48, "48 osavaltion pääkaupunkia");
{ // jokainen pääkaupunki on jonkin osavaltion alueella
  const t = tol(US);
  for (const c of CITY_DATA.usa.opk) {
    const [x, y] = project(c[2], c[1], US);
    assert(US.countries.some(s => pointInArea(x, y, s, t.coast, t.ctr)),
      c[0] + " on osavaltiossa");
  }
}
assert(inCountry(US, "Kalifornia", -121.49, 38.58), "Sacramento on Kaliforniassa");
assert(inCountry(US, "Texas", -97.74, 30.27), "Austin on Texasissa");
assert(inFeature(US, "Yläjärvi", -87.5, 47.6), "Yläjärvi osuu");
assert(inFeature(US, "Mississippi", -90.05, 35.15), "Memphis on Mississippin varrella");
assert(inFeature(US, "Grand Canyon", -112.1, 36.1), "Grand Canyon osuu");

// Tunnetut sijainnit: kaupunki maansa sisällä
const EU = CONTINENTS.eurooppa;
assert(inCountry(EU, "Suomi", 24.94, 60.17), "Helsinki on Suomessa");
assert(inCountry(EU, "Ranska", 2.35, 48.86), "Pariisi on Ranskassa");
assert(!inCountry(EU, "Saksa", 2.35, 48.86), "Pariisi ei ole Saksassa");
assert(inCountry(EU, "Ukraina", 34.10, 44.95), "Krim on Ukrainassa");
const AS = CONTINENTS.aasia;
assert(inCountry(AS, "Japani", 139.69, 35.68), "Tokio on Japanissa");
assert(inCountry(AS, "Kiina", 116.40, 39.90), "Peking on Kiinassa");
assert(inCountry(AS, "Intia", 77.21, 28.61), "Delhi on Intiassa");
const AF = CONTINENTS.afrikka;
assert(inCountry(AF, "Egypti", 31.24, 30.04), "Kairo on Egyptissä");
assert(inCountry(AF, "Etelä-Afrikka", 18.42, -33.93), "Kapkaupunki on Etelä-Afrikassa");
const NA = CONTINENTS.pohjois_amerikka;
assert(inCountry(NA, "Yhdysvallat", -74.01, 40.71), "New York on Yhdysvalloissa");
assert(inCountry(NA, "Kanada", -79.38, 43.65), "Toronto on Kanadassa");
assert(inCountry(NA, "Grönlanti", -51.72, 64.18), "Nuuk on Grönlannissa");
const SA = CONTINENTS.etela_amerikka;
assert(inCountry(SA, "Brasilia", -47.88, -15.79), "Brasília on Brasiliassa");
assert(inCountry(SA, "Chile", -70.66, -33.45), "Santiago on Chilessä");
const OC = CONTINENTS.oseania;
assert(inCountry(OC, "Australia", 151.21, -33.87), "Sydney on Australiassa");
assert(inCountry(OC, "Uusi-Seelanti", 174.78, -41.29), "Wellington on Uudessa-Seelannissa");

// Luonnonkohteet: piste alueen sisällä / joen varrella
assert(inFeature(EU, "Itämeri", 19.5, 58.0), "Itämeri osuu");
assert(inFeature(EU, "Alpit", 10.0, 46.5), "Alpit osuu");
assert(inFeature(EU, "Tonava", 18.9, 45.3), "Tonavan varsi osuu");
assert(inFeature(AS, "Himalaja", 86.9, 28.0), "Himalaja osuu");
assert(inFeature(AS, "Kaspianmeri", 50.5, 41.5), "Kaspianmeri osuu");
assert(inFeature(AF, "Sahara", 10.0, 23.0), "Sahara osuu");
assert(inFeature(AF, "Niili", 31.24, 30.04), "Kairo on Niilin varrella");
assert(inFeature(NA, "Meksikonlahti", -90.0, 25.0), "Meksikonlahti osuu");
assert(inFeature(NA, "Kalliovuoret", -106.0, 40.0), "Kalliovuoret osuu");
assert(inFeature(SA, "Amazon", -60.02, -3.12), "Manaus on Amazonin varrella");
assert(inFeature(SA, "Andit", -70.0, -30.0), "Andit osuu");
assert(inFeature(OC, "Tasmania", 146.5, -42.0), "Tasmania osuu");
// meri ei ole maa
const sea = project(-15, 50, EU);
assert(!EU.countries.some(c => pointInArea(sea[0], sea[1], c, 7, 12)), "Atlantti ei ole maa");

// Aikahyökkäys
assert.strictEqual(START_TIME, 150, "lähtöaika 2 min 30 s");
assert.strictEqual(TIME_BONUS, 10, "bonus +10 s");
assert.strictEqual(TIME_PENALTY, 10, "sakko -10 s");
assert.strictEqual(STREAK_EVERY, 10, "bonus joka 10. löydöstä");
assert.strictEqual(STREAK_BONUS, 20, "sarjabonus +20 s");
assert.strictEqual(fmtTime(150), "2:30", "ajan muotoilu");
assert.strictEqual(fmtTime(65), "1:05", "ajan muotoilu, etunolla");
assert.strictEqual(fmtTime(-3), "0:00", "ei negatiivista aikaa");
assert(betterResult({f:5,t:0}, undefined), "ensimmäinen tulos on ennätys");
assert(betterResult({f:6,t:0}, {f:5,t:90}), "enemmän löytöjä voittaa");
assert(!betterResult({f:5,t:0}, {f:6,t:0}), "vähemmän löytöjä häviää");
assert(betterResult({f:5,t:60}, {f:5,t:30}), "tasatilanteessa aika ratkaisee");

console.log("Kaikki testit OK");
`);
