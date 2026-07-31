#!/usr/bin/env python3
"""Generoi kuntakeskukset.js maakuntakarttojen pistekohteiksi.

Maakuntakartoilla (mk_*) on kohteina kuntien alueet; tämä lisää niiden
rinnalle kuntakeskukset eli kirkonkylien ja kaupunkikeskustojen pisteet.
Ulostulo on samassa muodossa kuin pelin käsin koottu CITY_DATA, joten
peli käyttää niitä tavallisen kaupunkikoneiston kautta.

Lähteet:
  - Wikidata (CC0): kuntanumero (P1203) ja koordinaatti (P625). Wikidatan
    kuntakohteen koordinaatti on keskustaajaman piste, ei rajojen painopiste.
    Tarkistukseen haetaan myös taajama- ja kirkonkyläkohteet (P31 =
    Q61492541 / Q378636) nimineen.
  - Tilastokeskus, kuntapohjaiset tilastointialueet 2026 (CC BY 4.0):
    kuntanumero -> nimi ja rajat. Rajoja käytetään tarkistukseen: jokaisen
    pisteen on osuttava oman kuntansa sisään.
  - world_data.js: kunta -> maakunta -jako luetaan suoraan generoiduista
    kartoista, jolloin listat eivät voi eriytyä pelin kartoista.

Nimeäminen: kohde saa kunnan nimen, paitsi kun kuntakeskuksella on oma
nimi (Rautjärvi -> Simpele). Nämä ovat KESKUS_NIMET-taulussa käsin
tarkistettuina, koska taajamakohteiden nimet ovat Wikidatassa usein
taivutettuja ("Toijalan keskustaajama"). Skripti vertaa jokaista pistettä
lähimpään taajamakohteeseen ja huomauttaa, jos taulusta näyttää puuttuvan
rivi — silloin uusi tapaus on tarkistettava käsin ja lisättävä tauluun tai
TARKISTETUT-joukkoon.

Käyttö:
  python3 fetch_kuntakeskukset.py [kunnat_2026.geojson] [ulostulo.js]

Ilman aineistopolkua kuntarajat haetaan Tilastokeskuksen WFS:stä (sama
kysely kuin build_world.py:n ohjeessa). Wikidata-vastaukset välimuistitetaan
väliaikaishakemistoon, joten toistoajot eivät kuormita palvelinta.
"""
import hashlib
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "maailman-kartta/1.0 (https://github.com/PeteyVonGuldenstein/maailman-kartta)"
CACHE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "kuntakeskukset_cache")
CACHE_AGE = 24 * 3600

WFS_KUNNAT = ("https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS"
              "&version=2.0.0&request=GetFeature"
              "&typename=tilastointialueet:kunta1000k_2026"
              "&outputFormat=application/json&srsName=EPSG:4326")

# kuntien pisteet ja tarkistukseen taajamat/kirkonkylät nimineen
Q_KUNNAT = """SELECT DISTINCT ?code ?coord WHERE {
  ?k wdt:P1203 ?code ; wdt:P625 ?coord .
}"""
Q_TAAJAMAT = """SELECT DISTINCT ?nimi ?coord WHERE {
  VALUES ?t { wd:Q61492541 wd:Q378636 }
  ?s wdt:P31 ?t ; wdt:P625 ?coord ; rdfs:label ?nimi .
  FILTER(lang(?nimi) = "fi")
}"""

# Kunnat, joiden keskustaajamalla on oma nimi (käsin tarkistettu Wikidatan
# taajamakohteista; kaikissa muissa keskus on samanniminen kuin kunta)
KESKUS_NIMET = {
    "Akaa": "Toijala",
    "Huittinen": "Lauttakylä",
    "Iitti": "Kausala",
    "Juupajoki": "Korkeakoski",
    "Kokemäki": "Tulkkila",
    "Luumäki": "Taavetti",
    "Pornainen": "Kirveskoski",
    "Posio": "Ahola",
    "Pyhäjärvi": "Pyhäsalmi",
    "Pälkäne": "Onkkaala",
    "Raasepori": "Tammisaari",
    "Rautjärvi": "Simpele",
    "Ruokolahti": "Rasila",
    "Sastamala": "Vammala",
    "Siikalatva": "Pulkkila",
    "Simo": "Asemakylä",
    "Suomussalmi": "Ämmänsaari",
    "Tohmajärvi": "Kemie",
    "Virolahti": "Virojoki",
}

# Kunnat, joissa lähin taajamakohde on erinimineltään mutta tarkoittaa samaa
# paikkaa (taivutusmuoto tai kunnan osa) — tarkistettu, ei muutosta nimeen
TARKISTETUT = {
    "Hailuoto",      # kohteen nimi on pelkkä "Kirkonkylä"
    "Ii",            # lähin kohde "Iin Hamina", keskus on Iin kirkonkylä
    "Isokyrö", "Juuka", "Lieto", "Loppi", "Turku", "Uusikaupunki",
    "Vihti", "Virrat",   # taivutusmuotoja: "Isonkyrön kirkonkylä" jne.
    "Kärsämäki",     # kohteen nimi on pelkkä "Kirkonkylä"
    "Luoto",         # lähin kohde Fagernäs, kuntakeskus on Holm
    "Ulvila",        # lähin kohde Vanhakylä, kuntakeskus on Friitala
    "Veteli",        # lähin kohde Torppa 1,5 km päässä
}

MAX_KM = 3.0     # tätä kauempana oleva taajamakohde ei kelpaa vertailuun


def get_json(url, timeout=180, cache=True):
    if cache:
        os.makedirs(CACHE_DIR, exist_ok=True)
        path = os.path.join(CACHE_DIR,
                            hashlib.sha1(url.encode()).hexdigest() + ".json")
        if os.path.exists(path) and time.time() - os.path.getmtime(path) < CACHE_AGE:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    if cache:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    return data


def sparql(query):
    url = ("https://query.wikidata.org/sparql?format=json&query="
           + urllib.parse.quote(query))
    return get_json(url)["results"]["bindings"]


def point(binding, key="coord"):
    lon, lat = binding[key]["value"].replace("Point(", "").rstrip(")").split()
    return float(lat), float(lon)


def outer_rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def dist_km(lat1, lon1, lat2, lon2):
    return math.hypot((lat1 - lat2) * 111.32,
                      (lon1 - lon2) * 111.32 * math.cos(math.radians(lat1)))


def stem(name):
    """Nimen vertailuvartalo: pieni alkukirjain, ääkköset auki, 4 merkkiä."""
    return name.lower().replace("ä", "a").replace("ö", "o")[:4]


def load_maps(path):
    """mk_*-karttojen kuntalistat generoidusta world_data.js:stä."""
    src = open(path, encoding="utf-8").read()
    data = json.loads(src[src.index("{"):src.rindex("}") + 1])
    return {k: [c["n"] for c in v["countries"]]
            for k, v in data.items() if v.get("mk")}


def main():
    kunnat_path = sys.argv[1] if len(sys.argv) > 1 else None
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "kuntakeskukset.js")

    if kunnat_path:
        kunnat = json.load(open(kunnat_path, encoding="utf-8"))
    else:
        print("haetaan kuntarajat Tilastokeskuksen WFS:stä ...", flush=True)
        kunnat = get_json(WFS_KUNNAT)
    print(f"kuntia aineistossa: {len(kunnat['features'])}")

    print("haetaan kuntien ja taajamien pisteet Wikidatasta ...", flush=True)
    pts, dupes = {}, set()
    for r in sparql(Q_KUNNAT):
        code = r["code"]["value"].zfill(3)
        p = point(r)
        if code in pts and pts[code] != p:
            dupes.add(code)          # useampi sijainti samalle kuntanumerolle
        pts.setdefault(code, p)
    taajamat = [(r["nimi"]["value"], *point(r)) for r in sparql(Q_TAAJAMAT)]
    print(f"kuntapisteitä: {len(pts)}, taajamia ja kirkonkyliä: {len(taajamat)}")

    # nimi -> (piste, rajat)
    by_name = {}
    for f in kunnat["features"]:
        p = f["properties"]
        if p["kunta"] in dupes:
            print(f"!! {p['nimi']}: kuntanumerolla {p['kunta']} on Wikidatassa "
                  f"useampi sijainti — tarkista")
        by_name[p["nimi"]] = (pts.get(p["kunta"]), f["geometry"])

    maps = load_maps(os.path.join(ROOT, "world_data.js"))
    out = {}
    problems = 0
    renamed = []
    for key in sorted(maps):
        cities = []
        for kunta in sorted(maps[key]):
            entry = by_name.get(kunta)
            if not entry or not entry[0]:
                print(f"!! {key}: kuntakeskusta ei löytynyt: {kunta}")
                problems += 1
                continue
            (lat, lon), geom = entry
            if not any(point_in_ring(lon, lat, r) for r in outer_rings(geom)):
                print(f"!! {key}: {kunta}: piste {lat},{lon} ei osu kunnan alueelle")
                problems += 1
                continue
            nimi = KESKUS_NIMET.get(kunta, kunta)
            if nimi != kunta:
                renamed.append(f"{kunta} -> {nimi}")
            # tarkistus: mitä lähin taajamakohde sanoo tästä pisteestä
            near, near_km = None, MAX_KM
            for tn, tlat, tlon in taajamat:
                d = dist_km(lat, lon, tlat, tlon)
                if d < near_km:
                    near, near_km = tn, d
            if near and stem(near.split()[0]) != stem(nimi) and kunta not in TARKISTETUT:
                print(f"?? {kunta}: lähin taajama on '{near}' ({near_km:.1f} km) "
                      f"mutta kohteen nimi on '{nimi}' — tarkista käsin ja lisää "
                      f"KESKUS_NIMET- tai TARKISTETUT-tauluun")
            cities.append([nimi, round(lat, 4), round(lon, 4)])
        out[key] = {"pk": cities}
        print(f"{key}: {len(cities)} kuntakeskusta")

    if problems:
        print(f"!! {problems} kuntaa jäi ilman kelvollista keskuspistettä")
        return 1

    js = ("// Generoitu fetch_kuntakeskukset.py:llä\n"
          "// Kuntakeskusten sijainnit ja nimet: Wikidata (CC0)\n"
          "// Kuntien nimet ja rajat: Tilastokeskus, kuntapohjaiset\n"
          "// tilastointialueet 2026 (CC BY 4.0)\n"
          "const KUNTAKESKUKSET="
          + json.dumps(out, ensure_ascii=False, separators=(",", ":"))
          + ";\n")
    with open(dst, "w", encoding="utf-8") as f:
        f.write(js)
    total = sum(len(v["pk"]) for v in out.values())
    print(f"\nkunnasta poikkeava keskuksen nimi ({len(renamed)}): "
          + ", ".join(sorted(renamed)))
    print(f"{dst}: {len(out)} maakuntaa, {total} kuntakeskusta, {len(js) // 1024} kt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
