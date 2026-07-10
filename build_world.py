#!/usr/bin/env python3
"""Generoi world_data.js Natural Earth -aineistoista Maailman kartta -pelille.

Kuusi maanosaa, kullakin oma equirectangular-projektio (cos-korjaus
keskileveyspiirin mukaan), kohdemaat, taustamaat, järvet, joet sekä
etsittävät luonnonkohteet (meret, järvet, joet, aavikot, vuoristot ...).

Käyttö: python3 build_world.py <aineistohakemisto> [ulostulo.js]

Hakemistossa on oltava:
  ne50.geojson                              (ne_50m_admin_0_countries)
  ne10_ukr.geojson                          (Krim Ukrainalle -korvaukset)
  ne_50m_lakes.geojson
  ne_50m_rivers_lake_centerlines.geojson
  ne_50m_geography_marine_polys.geojson
  ne_50m_geography_regions_polys.geojson
"""
import json
import math
import os
import sys

SIMPLIFY_TOL = 1.0    # px
KM_PER_DEG_PY = 111.32
MIN_RING_DIAG = 2.5   # px
LAKE_MIN_AREA = 5.0   # px^2, pienemmät järvet jätetään piirtämättä

# ---------------------------------------------------------------- maanosat

EU_COUNTRIES = {
    "Iceland": "Islanti", "Norway": "Norja", "Sweden": "Ruotsi",
    "Finland": "Suomi", "Denmark": "Tanska", "Estonia": "Viro",
    "Latvia": "Latvia", "Lithuania": "Liettua", "Poland": "Puola",
    "Germany": "Saksa", "Netherlands": "Alankomaat", "Belgium": "Belgia",
    "Luxembourg": "Luxemburg", "France": "Ranska",
    "United Kingdom": "Iso-Britannia", "Ireland": "Irlanti",
    "Portugal": "Portugali", "Spain": "Espanja", "Italy": "Italia",
    "Switzerland": "Sveitsi", "Austria": "Itävalta",
    "Czechia": "Tšekki", "Czech Republic": "Tšekki",
    "Slovakia": "Slovakia", "Hungary": "Unkari", "Slovenia": "Slovenia",
    "Croatia": "Kroatia", "Bosnia and Herzegovina": "Bosnia ja Hertsegovina",
    "Serbia": "Serbia", "Republic of Serbia": "Serbia",
    "Montenegro": "Montenegro", "Albania": "Albania",
    "North Macedonia": "Pohjois-Makedonia", "Macedonia": "Pohjois-Makedonia",
    "Kosovo": "Kosovo", "Greece": "Kreikka", "Bulgaria": "Bulgaria",
    "Romania": "Romania", "Moldova": "Moldova", "Ukraine": "Ukraina",
    "Belarus": "Valko-Venäjä", "Russia": "Venäjä", "Turkey": "Turkki",
    "Cyprus": "Kypros", "Malta": "Malta",
}

AS_COUNTRIES = {
    "China": "Kiina", "India": "Intia", "Japan": "Japani",
    "Indonesia": "Indonesia", "Pakistan": "Pakistan",
    "Bangladesh": "Bangladesh", "Afghanistan": "Afganistan",
    "Iran": "Iran", "Iraq": "Irak", "Saudi Arabia": "Saudi-Arabia",
    "Yemen": "Jemen", "Oman": "Oman",
    "United Arab Emirates": "Arabiemiraatit", "Israel": "Israel",
    "Jordan": "Jordania", "Syria": "Syyria", "Kazakhstan": "Kazakstan",
    "Uzbekistan": "Uzbekistan", "Turkmenistan": "Turkmenistan",
    "Kyrgyzstan": "Kirgisia", "Tajikistan": "Tadžikistan",
    "Mongolia": "Mongolia", "North Korea": "Pohjois-Korea",
    "South Korea": "Etelä-Korea", "Vietnam": "Vietnam", "Laos": "Laos",
    "Cambodia": "Kambodža", "Thailand": "Thaimaa", "Myanmar": "Myanmar",
    "Malaysia": "Malesia", "Philippines": "Filippiinit",
    "Sri Lanka": "Sri Lanka", "Nepal": "Nepal", "Georgia": "Georgia",
    "Armenia": "Armenia", "Azerbaijan": "Azerbaidžan", "Taiwan": "Taiwan",
}

AF_COUNTRIES = {
    "Egypt": "Egypti", "Libya": "Libya", "Tunisia": "Tunisia",
    "Algeria": "Algeria", "Morocco": "Marokko", "Mauritania": "Mauritania",
    "Mali": "Mali", "Niger": "Niger", "Chad": "Tšad", "Sudan": "Sudan",
    "South Sudan": "Etelä-Sudan", "Ethiopia": "Etiopia",
    "Eritrea": "Eritrea", "Somalia": "Somalia", "Kenya": "Kenia",
    "United Republic of Tanzania": "Tansania", "Tanzania": "Tansania",
    "Uganda": "Uganda",
    "Democratic Republic of the Congo": "Kongon dem. tasavalta",
    "Republic of the Congo": "Kongo", "Congo": "Kongo",
    "Nigeria": "Nigeria", "Ghana": "Ghana",
    "Ivory Coast": "Norsunluurannikko", "Côte d'Ivoire": "Norsunluurannikko",
    "Senegal": "Senegal", "Guinea": "Guinea", "Cameroon": "Kamerun",
    "Gabon": "Gabon", "Angola": "Angola", "Zambia": "Sambia",
    "Zimbabwe": "Zimbabwe", "Mozambique": "Mosambik",
    "Botswana": "Botswana", "Namibia": "Namibia",
    "South Africa": "Etelä-Afrikka", "Madagascar": "Madagaskar",
    "Burkina Faso": "Burkina Faso", "Malawi": "Malawi",
    "Liberia": "Liberia",
}

NA_COUNTRIES = {
    "Canada": "Kanada", "United States of America": "Yhdysvallat",
    "Mexico": "Meksiko", "Guatemala": "Guatemala", "Honduras": "Honduras",
    "Nicaragua": "Nicaragua", "Costa Rica": "Costa Rica",
    "Panama": "Panama", "Cuba": "Kuuba", "Haiti": "Haiti",
    "Dominican Republic": "Dominikaaninen tasavalta", "Jamaica": "Jamaika",
    "Greenland": "Grönlanti",
}

SA_COUNTRIES = {
    "Brazil": "Brasilia", "Argentina": "Argentiina", "Chile": "Chile",
    "Peru": "Peru", "Bolivia": "Bolivia", "Paraguay": "Paraguay",
    "Uruguay": "Uruguay", "Colombia": "Kolumbia",
    "Venezuela": "Venezuela", "Ecuador": "Ecuador", "Guyana": "Guyana",
    "Suriname": "Suriname",
}

OC_COUNTRIES = {
    "Australia": "Australia", "New Zealand": "Uusi-Seelanti",
    "Papua New Guinea": "Papua-Uusi-Guinea", "Fiji": "Fidži",
    "Solomon Islands": "Salomonsaaret", "Vanuatu": "Vanuatu",
    "East Timor": "Itä-Timor", "Timor-Leste": "Itä-Timor",
}

# Luonnonkohteet: (fi-nimi, aineisto, NE-nimet)
# aineisto: "marine" | "lake" | "region" | "river"
CONTINENTS = {
    "suomi": {
        "name": "Suomi", "bbox": (17, 33.5, 59, 70.7), "reflat": 65,
        # Ahvenanmaa on aineistossa oma yksikkönsä; yhdistetään Suomeen
        "countries": {"Finland": "Suomi", "Aland": "Suomi"}, "exclude": set(),
        "features": [
            ("Pohjanlahti", "marine", ["Gulf of Bothnia"]),
            ("Suomenlahti", "marine", ["Gulf of Finland"]),
            ("Itämeri", "marine", ["Baltic Sea"]),
            ("Saimaa", "lake", ["Lake Saimaa"]),
            ("Päijänne", "lake", ["Päijänne"]),
            ("Inarijärvi", "lake", ["Inarijärvi"]),
            ("Oulujärvi", "lake", ["Oulujärvi"]),
            ("Pielinen", "lake", ["Pielinen"]),
            ("Laatokka", "lake", ["Lake Ladoga"]),
            ("Kemijoki", "river", ["Kemijoki"]),
            ("Kokemäenjoki", "river", ["Kokemäenjoki"]),
            ("Vuoksi", "river", ["Vuoksi"]),
            ("Lappi", "region", ["LAPLAND"]),
        ],
    },
    "eurooppa": {
        "name": "Eurooppa", "bbox": (-25, 45, 34, 72), "reflat": 50,
        "countries": EU_COUNTRIES, "exclude": {"Greenland"},
        "features": [
            ("Itämeri", "marine", ["Baltic Sea"]),
            ("Pohjanmeri", "marine", ["North Sea"]),
            ("Välimeri", "marine", ["Mediterranean Sea"]),
            ("Mustameri", "marine", ["Black Sea"]),
            ("Biskajanlahti", "marine", ["Bay of Biscay"]),
            ("Norjanmeri", "marine", ["Norwegian Sea"]),
            ("Pohjanlahti", "marine", ["Gulf of Bothnia"]),
            ("Suomenlahti", "marine", ["Gulf of Finland"]),
            ("Adrianmeri", "marine", ["Adriatic Sea"]),
            ("Egeanmeri", "marine", ["Aegean Sea"]),
            ("Englannin kanaali", "marine", ["English Channel"]),
            ("Laatokka", "lake", ["Lake Ladoga"]),
            ("Vänern", "lake", ["Vänern"]),
            ("Genevenjärvi", "lake", ["Lake Geneva"]),
            ("Balaton", "lake", ["Lake Balaton"]),
            ("Alpit", "region", ["ALPS"]),
            ("Pyreneet", "region", ["PYRENEES"]),
            ("Karpaatit", "region", ["CARPATHIAN MOUNTAINS"]),
            ("Skandinavian niemimaa", "region", ["SCANDINAVIA"]),
            ("Balkanin niemimaa", "region", ["BALKAN PEN."]),
            ("Iberian niemimaa", "region", ["PENÍNSULA IBÉRICA"]),
            ("Tonava", "river", ["Danube", "Donau"]),
            ("Rein", "river", ["Rhine", "Rhein", "Rhin"]),
            ("Volga", "river", ["Volga"]),
            ("Dnepr", "river", ["Dnipro", "Dnepre"]),
        ],
    },
    "aasia": {
        "name": "Aasia", "bbox": (25, 150, -12, 60), "reflat": 30,
        "countries": AS_COUNTRIES, "exclude": {"Greenland"},
        "features": [
            ("Arabianmeri", "marine", ["Arabian Sea"]),
            ("Bengalinlahti", "marine", ["Bay of Bengal"]),
            ("Etelä-Kiinan meri", "marine", ["South China Sea"]),
            ("Japaninmeri", "marine", ["Sea of Japan"]),
            ("Keltainenmeri", "marine", ["Yellow Sea"]),
            ("Persianlahti", "marine", ["Persian Gulf"]),
            ("Punainenmeri", "marine", ["Red Sea"]),
            ("Kaspianmeri", "marine", ["Caspian Sea"]),
            ("Thaimaanlahti", "marine", ["Gulf of Thailand"]),
            ("Baikal", "lake", ["Lake Baikal"]),
            ("Kuollutmeri", "lake", ["Dead Sea"]),
            ("Himalaja", "region", ["HIMALAYAS"]),
            ("Gobi", "region", ["GOBI DESERT"]),
            ("Arabian niemimaa", "region", ["ARABIAN PENINSULA"]),
            ("Tiibetin ylänkö", "region", ["PLATEAU OF TIBET"]),
            ("Borneo", "region", ["BORNEO"]),
            ("Sumatra", "region", ["SUMATRA"]),
            ("Jaava", "region", ["JAVA"]),
            ("Jangtse", "river", ["Chang Jiang", "Yangtze"]),
            ("Keltainenjoki", "river", ["Huang"]),
            ("Ganges", "river", ["Ganges"]),
            ("Indus", "river", ["Indus"]),
            ("Mekong", "river", ["Mekong"]),
            ("Eufrat", "river", ["Euphrates", "Al Furat", "Firat"]),
        ],
    },
    "afrikka": {
        "name": "Afrikka", "bbox": (-20, 55, -36, 38), "reflat": 0,
        "countries": AF_COUNTRIES, "exclude": {"Greenland"},
        "features": [
            ("Guineanlahti", "marine", ["Gulf of Guinea"]),
            ("Punainenmeri", "marine", ["Red Sea"]),
            ("Mosambikin kanaali", "marine", ["Mozambique Channel"]),
            ("Sahara", "region", ["SAHARA"]),
            ("Kalahari", "region", ["KALAHARI DESERT"]),
            ("Namibin aavikko", "region", ["NAMIB DESERT"]),
            ("Atlasvuoret", "region", ["ATLAS MOUNTAINS"]),
            ("Etiopian ylänkö", "region", ["ETHIOPIAN HIGHLANDS"]),
            ("Kongon allas", "region", ["CONGO BASIN"]),
            ("Sahel", "region", ["SAHEL"]),
            ("Viktorianjärvi", "lake", ["Lake Victoria"]),
            ("Tanganjikajärvi", "lake", ["Lake Tanganyika"]),
            ("Malawijärvi", "lake", ["Lake Malawi"]),
            ("Tšadjärvi", "lake", ["Lake Chad"]),
            ("Niili", "river", ["Nile"]),
            ("Kongojoki", "river", ["Congo"]),
            ("Nigerjoki", "river", ["Niger"]),
            ("Sambesi", "river", ["Zambezi"]),
        ],
    },
    "pohjois_amerikka": {
        "name": "Pohjois-Amerikka", "bbox": (-170, -50, 5, 72), "reflat": 45,
        "countries": NA_COUNTRIES, "exclude": set(),
        "features": [
            ("Meksikonlahti", "marine", ["Gulf of Mexico"]),
            ("Karibianmeri", "marine", ["Caribbean Sea"]),
            ("Hudsoninlahti", "marine", ["Hudson Bay"]),
            ("Beringinmeri", "marine", ["Bering Sea"]),
            ("Kalliovuoret", "region", ["ROCKY MOUNTAINS"]),
            ("Appalakit", "region", ["APPALACHIAN MTS."]),
            ("Suuret tasangot", "region", ["GREAT PLAINS"]),
            ("Baja California", "region", ["BAJA CALIFORNIA"]),
            ("Florida", "region", ["FLORIDA"]),
            ("Alaska", "region", ["ALASKA"]),
            ("Grand Canyon", "region", ["Grand Canyon"]),
            ("Suuret järvet", "region", ["GREAT LAKES"]),
            ("Jukatanin niemimaa", "region", ["PEN. DE YUCATÁN"]),
            ("Mississippi", "river", ["Mississippi"]),
            ("Yukon", "river", ["Yukon"]),
            ("Colorado", "river", ["Colorado"]),
        ],
    },
    "etela_amerikka": {
        "name": "Etelä-Amerikka", "bbox": (-85, -33, -56, 13), "reflat": 20,
        "countries": SA_COUNTRIES, "exclude": {"Greenland"},
        "features": [
            ("Karibianmeri", "marine", ["Caribbean Sea"]),
            ("La Plata", "marine", ["Río de la Plata"]),
            ("Andit", "region", ["ANDES"]),
            ("Amazonin allas", "region", ["AMAZON BASIN"]),
            ("Patagonia", "region", ["PATAGONIA"]),
            ("Pampa", "region", ["PAMPAS"]),
            ("Atacama", "region", ["DESIERTO DE ATACAMA"]),
            ("Tulimaa", "region", ["TIERRA DEL FUEGO"]),
            ("Pantanal", "region", ["PANTANAL"]),
            ("Titicaca", "lake", ["Lago Titicaca"]),
            ("Amazon", "river", ["Amazonas"]),
            ("Paraná", "river", ["Paraná", "Parana"]),
            ("Orinoco", "river", ["Orinoco"]),
        ],
    },
    "oseania": {
        "name": "Oseania", "bbox": (110, 180, -48, 0), "reflat": 25,
        "countries": OC_COUNTRIES, "exclude": {"Greenland"},
        "features": [
            ("Tasmaninmeri", "marine", ["Tasman Sea"]),
            ("Korallimeri", "marine", ["Coral Sea"]),
            ("Iso valliriutta", "marine", ["Great Barrier Reef"]),
            ("Iso Australianlahti", "marine", ["Great Australian Bight"]),
            ("Tasmania", "region", ["TASMANIA"]),
            ("Uusi-Guinea", "region", ["NEW GUINEA"]),
            ("Eteläalpit", "region", ["SOUTHERN ALPS"]),
            ("Iso Victorianaavikko", "region", ["GREAT VICTORIA DESERT"]),
            ("Iso Vedenjakajavuoristo", "region", ["GREAT DIVIDING RANGE"]),
            ("Murray", "river", ["Murray"]),
            ("Darling", "river", ["Darling"]),
        ],
    },
}

ALWAYS_EXCLUDE = {"Antarctica"}

# Nämä luonnonkohteet piirretään kartalle vuoristosymbolein (^^^)
MOUNTAIN_FI = {
    "Alpit", "Pyreneet", "Karpaatit", "Himalaja", "Atlasvuoret",
    "Etiopian ylänkö", "Kalliovuoret", "Appalakit", "Andit",
    "Eteläalpit", "Iso Vedenjakajavuoristo",
}


# ---------------------------------------------------------------- geometria

def make_projection(bbox, reflat, width=1000.0):
    lon0, lon1, lat0, lat1 = bbox
    cos = math.cos(math.radians(reflat))
    scale = width / ((lon1 - lon0) * cos)
    height = round((lat1 - lat0) * scale)

    def project(lon, lat):
        return (lon - lon0) * cos * scale, (lat1 - lat) * scale

    return project, width, height, cos


def clip_ring(ring, w, h):
    """Sutherland–Hodgman-leikkaus suorakulmioon [0,w]x[0,h]."""
    def clip_edge(pts, inside, intersect):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ain, bin_ = inside(a), inside(b)
            if ain:
                out.append(a)
                if not bin_:
                    out.append(intersect(a, b))
            elif bin_:
                out.append(intersect(a, b))
        return out

    def ix_x(x0):
        def f(a, b):
            t = (x0 - a[0]) / (b[0] - a[0])
            return (x0, a[1] + t * (b[1] - a[1]))
        return f

    def ix_y(y0):
        def f(a, b):
            t = (y0 - a[1]) / (b[1] - a[1])
            return (a[0] + t * (b[0] - a[0]), y0)
        return f

    pts = ring
    for inside, intersect in (
        (lambda p: p[0] >= 0, ix_x(0.0)),
        (lambda p: p[0] <= w, ix_x(w)),
        (lambda p: p[1] >= 0, ix_y(0.0)),
        (lambda p: p[1] <= h, ix_y(h)),
    ):
        if len(pts) < 3:
            return []
        pts = clip_edge(pts, inside, intersect)
    return pts if len(pts) >= 3 else []


def clip_line(pts, w, h):
    """Leikkaa murtoviivan suorakulmioon; palauttaa jatkuvien pätkien listan."""
    def inside(p):
        return 0 <= p[0] <= w and 0 <= p[1] <= h

    def clip_seg(a, b):
        # Liang–Barsky
        t0, t1 = 0.0, 1.0
        dx, dy = b[0] - a[0], b[1] - a[1]
        for p, q in ((-dx, a[0]), (dx, w - a[0]), (-dy, a[1]), (dy, h - a[1])):
            if p == 0:
                if q < 0:
                    return None
            else:
                r = q / p
                if p < 0:
                    if r > t1:
                        return None
                    if r > t0:
                        t0 = r
                else:
                    if r < t0:
                        return None
                    if r < t1:
                        t1 = r
        return ((a[0] + t0 * dx, a[1] + t0 * dy),
                (a[0] + t1 * dx, a[1] + t1 * dy))

    runs, cur = [], []
    for i in range(len(pts) - 1):
        seg = clip_seg(pts[i], pts[i + 1])
        if seg is None:
            if len(cur) >= 2:
                runs.append(cur)
            cur = []
            continue
        a, b = seg
        if not cur:
            cur = [a]
        elif cur[-1] != a:
            if len(cur) >= 2:
                runs.append(cur)
            cur = [a]
        cur.append(b)
        if not inside(pts[i + 1]):
            if len(cur) >= 2:
                runs.append(cur)
            cur = []
    if len(cur) >= 2:
        runs.append(cur)
    return runs


def simplify(pts, tol, closed=True):
    """Douglas–Peucker, iteratiivinen."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1:
            continue
        ax, ay = pts[i0]
        bx, by = pts[i1]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        dmax, imax = -1.0, i0
        for i in range(i0 + 1, i1):
            px, py = pts[i]
            if seg2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
            if d > dmax:
                dmax, imax = d, i
        if dmax > tol:
            keep[imax] = True
            stack.append((i0, imax))
            stack.append((imax, i1))
    return [p for p, k in zip(pts, keep) if k]


def ring_area_centroid(ring):
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a /= 2.0
    if abs(a) < 1e-9:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / n, sum(ys) / n
    return abs(a), cx / (6 * a), cy / (6 * a)


def geom_rings(geom, project, w, h):
    """Geometrian ulkorenkaat projisoituna, leikattuna ja yksinkertaistettuna."""
    if geom["type"] == "Polygon":
        raw = [geom["coordinates"][0]]
    elif geom["type"] == "MultiPolygon":
        raw = [poly[0] for poly in geom["coordinates"]]
    else:
        return []
    rings = []
    for ring in raw:
        pts = [project(lon, lat) for lon, lat in ring]
        pts = clip_ring(pts, w, h)
        if not pts:
            continue
        pts = simplify(pts, SIMPLIFY_TOL)
        if len(pts) < 3:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) < MIN_RING_DIAG:
            continue
        rings.append(pts)
    return rings


def geom_lines(geom, project, w, h):
    """Viivageometrian pätkät projisoituna, leikattuna ja yksinkertaistettuna."""
    if geom["type"] == "LineString":
        raw = [geom["coordinates"]]
    elif geom["type"] == "MultiLineString":
        raw = geom["coordinates"]
    else:
        return []
    lines = []
    for line in raw:
        pts = [project(lon, lat) for lon, lat in line]
        for run in clip_line(pts, w, h):
            run = simplify(run, SIMPLIFY_TOL, closed=False)
            if len(run) >= 2:
                lines.append(run)
    return lines


def path_d(rings, close=True):
    parts = []
    for ring in rings:
        parts.append("M" + " ".join(f"{x:.1f} {y:.1f}" for x, y in ring)
                     + ("Z" if close else ""))
    return "".join(parts)


def flat(rings):
    return [[round(v, 1) for pt in r for v in pt] for r in rings]


def rings_centroid(rings):
    biggest = max(rings, key=lambda r: ring_area_centroid(r)[0])
    _, cx, cy = ring_area_centroid(biggest)
    return [round(cx, 1), round(cy, 1)]


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def mountain_marks(rings, u):
    """Huippusymbolien (^) sijainnit vuoristopolygonin sisällä.

    Heksamainen ruudukko, jonka väli skaalataan ui-kertoimella u niin,
    että symbolitiheys näyttää samalta joka maanosassa.
    """
    step = 26.0 * u
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    marks = []
    y = min(ys) + step / 2
    row = 0
    while y < max(ys):
        x = min(xs) + (step / 2 if row % 2 == 0 else step)
        while x < max(xs):
            if any(point_in_ring(x, y, r) for r in rings):
                marks.append((x, y))
            x += step
        y += step * 0.8
        row += 1
    return marks


def mountain_path(marks, u):
    s = 4.5 * u
    parts = []
    for x, y in marks:
        parts.append(f"M{x - s:.1f} {y + s * 0.7:.1f}"
                     f"L{x:.1f} {y - s * 0.9:.1f}"
                     f"L{x + s:.1f} {y + s * 0.7:.1f}")
    return "".join(parts)


def lines_midpoint(lines):
    longest = max(lines, key=len)
    mid = longest[len(longest) // 2]
    return [round(mid[0], 1), round(mid[1], 1)]


# ---------------------------------------------------------------- kokoaminen

def main():
    src_dir = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "world_data.js"

    def load(name):
        with open(os.path.join(src_dir, name)) as f:
            return json.load(f)

    countries_geo = load("ne50.geojson")
    lakes_geo = load("ne_50m_lakes.geojson")
    rivers_geo = load("ne_50m_rivers_lake_centerlines.geojson")
    marine_geo = load("ne_50m_geography_marine_polys.geojson")
    regions_geo = load("ne_50m_geography_regions_polys.geojson")

    # Krim Ukrainalle: Ukrainan ja Venäjän geometriat POV-aineistosta
    pov = load("ne10_ukr.geojson")
    overrides = {}
    for feat in pov["features"]:
        admin = feat["properties"].get("ADMIN")
        if admin in ("Ukraine", "Russia"):
            overrides[admin] = feat["geometry"]

    def find_features(geo, namekeys, wanted):
        out = []
        for feat in geo["features"]:
            name = None
            for k in namekeys:
                name = feat["properties"].get(k)
                if name:
                    break
            if name in wanted:
                out.append(feat["geometry"])
        return out

    # kokokertoimen verrokki: Euroopan kartan lävistäjä kilometreinä
    def diag_km(cfg):
        _, w, h, _ = make_projection(cfg["bbox"], cfg["reflat"])
        return math.hypot(w, h) * KM_PER_DEG_PY * (cfg["bbox"][3] - cfg["bbox"][2]) / h

    ref_diag_km = diag_km(CONTINENTS["eurooppa"])

    world = {}
    for key, cfg in CONTINENTS.items():
        project, W, H, cos = make_projection(cfg["bbox"], cfg["reflat"])
        lon0, lon1, lat0, lat1 = cfg["bbox"]
        bg = []
        target_rings = {}   # fi-nimi -> renkaat; sama nimi useasta admin-yksiköstä yhdistyy
        for feat in countries_geo["features"]:
            admin = feat["properties"].get("ADMIN")
            if admin in ALWAYS_EXCLUDE or admin in cfg["exclude"]:
                continue
            geom = overrides.get(admin, feat["geometry"])
            rings = geom_rings(geom, project, W, H)
            if not rings:
                continue
            fi = cfg["countries"].get(admin)
            if fi:
                target_rings.setdefault(fi, []).extend(rings)
            else:
                bg.append(path_d(rings))
        targets = [{"n": fi, "c": rings_centroid(rings),
                    "d": path_d(rings), "p": flat(rings)}
                   for fi, rings in target_rings.items()]
        missing = set(cfg["countries"].values()) - set(target_rings)
        if missing:
            print(f"!! {cfg['name']}: maita ei löytynyt: {sorted(missing)}")
        targets.sort(key=lambda t: t["n"])

        # järvet piirtoon (isot) — kaikki, ei vain kohteet
        lake_rings = []
        for feat in lakes_geo["features"]:
            for ring in geom_rings(feat["geometry"], project, W, H):
                if ring_area_centroid(ring)[0] >= LAKE_MIN_AREA:
                    lake_rings.append(ring)

        # luonnonkohteet
        kmpx = KM_PER_DEG_PY * (lat1 - lat0) / H
        # sama ui-kerroin kuin pelissä: näkymä 1 050 km × kokokerroin (Eurooppa = 1)
        sc = math.hypot(W, H) * kmpx / ref_diag_km
        u = (1050.0 * sc / kmpx) / 210.0
        features = []
        river_draw = []
        mount_marks = []
        for fi, kind, ne_names in cfg["features"]:
            wanted = set(ne_names)
            if kind == "river":
                geoms = find_features(rivers_geo, ("name",), wanted)
                lines = []
                for g in geoms:
                    lines.extend(geom_lines(g, project, W, H))
                if not lines:
                    print(f"!! {cfg['name']}: jokea ei löytynyt: {fi} {ne_names}")
                    continue
                features.append({"n": fi, "k": "j",
                                 "c": lines_midpoint(lines),
                                 "l": flat(lines)})
                river_draw.extend(lines)
            else:
                geo = {"marine": marine_geo, "lake": lakes_geo,
                       "region": regions_geo}[kind]
                keys = ("NAME", "name")
                geoms = find_features(geo, keys, wanted)
                rings = []
                for g in geoms:
                    rings.extend(geom_rings(g, project, W, H))
                if not rings:
                    print(f"!! {cfg['name']}: aluetta ei löytynyt: {fi} {ne_names}")
                    continue
                features.append({"n": fi, "k": "a",
                                 "c": rings_centroid(rings),
                                 "p": flat(rings)})
                if fi in MOUNTAIN_FI:
                    mount_marks.extend(mountain_marks(rings, u))

        world[key] = {
            "name": cfg["name"], "W": W, "H": H,
            "lon0": lon0, "lon1": lon1, "lat0": lat0, "lat1": lat1,
            "cos": round(cos, 6),
            "countries": targets, "bg": "".join(bg),
            "lakes": path_d(lake_rings),
            "rivers": path_d(river_draw, close=False),
            "mounts": mountain_path(mount_marks, u),
            "features": features,
        }
        print(f"{cfg['name']}: {W:.0f}x{H}, maita {len(targets)}, "
              f"taustaa {len(bg)}, järvirenkaita {len(lake_rings)}, "
              f"luonnonkohteita {len(features)}, vuorisymboleita {len(mount_marks)}")

    out = ("// Generoitu build_world.py:llä Natural Earth -aineistoista\n"
           "const CONTINENTS="
           + json.dumps(world, ensure_ascii=False, separators=(",", ":"))
           + ";\n")
    with open(dst, "w") as f:
        f.write(out)
    print(f"{dst}: {len(out) // 1024} KB")


if __name__ == "__main__":
    main()
