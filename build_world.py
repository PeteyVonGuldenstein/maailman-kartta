#!/usr/bin/env python3
"""Generoi world_data.js Natural Earth -aineistoista Maailman kartta -pelille.

Kuusi maanosaa, kullakin oma equirectangular-projektio (cos-korjaus
keskileveyspiirin mukaan), kohdemaat, taustamaat, järvet, joet sekä
etsittävät luonnonkohteet (meret, järvet, joet, aavikot, vuoristot ...).

Käyttö: python3 build_world.py <aineistohakemisto> [ulostulo.js]

Hakemistossa on oltava:
  ne50.geojson                              (ne_50m_admin_0_countries)
  ne10_ukr.geojson                          (Krim Ukrainalle -korvaukset)
  ne_50m_admin_1.geojson                    (ne_50m_admin_1_states_provinces)
  ne_50m_lakes.geojson
  ne_50m_rivers_lake_centerlines.geojson
  syke_jarvet.geojson                       (SYKE Ranta10, Suomen järvet)
  ne_50m_geography_marine_polys.geojson
  ne_50m_geography_regions_polys.geojson
  kunnat_2026.geojson                       (Tilastokeskus, kunta1000k_2026)
  maakunnat_2026.geojson                    (Tilastokeskus, maakunta1000k_2026)
  tiet_1_99.geojson                         (Väylävirasto, tieosoiteverkko)

Kunta- ja maakuntarajat: Tilastokeskus, kuntapohjaiset tilastointialueet
2026 (CC BY 4.0). Haku (maakunnat samoin, typename=...maakunta1000k_2026):
  curl "https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS\
&version=2.0.0&request=GetFeature&typename=tilastointialueet:kunta1000k_2026\
&outputFormat=application/json&srsName=EPSG:4326" -o kunnat_2026.geojson

Valta- ja kantatiet (koristekerros): Väylävirasto, tieosoiteverkko
(CC BY 4.0). Suodatus ajorata<=1 antaa yhden viivan per tie:
  curl "https://avoinapi.vaylapilvi.fi/vaylatiedot/wfs?service=WFS\
&version=2.0.0&request=GetFeature&typeNames=tiestotiedot:tieosoiteverkko\
&outputFormat=application/json&srsName=EPSG:4326\
&cql_filter=tie%3C%3D99%20AND%20ajorata%3C%3D1" -o tiet_1_99.geojson

Suomen järvet (Suomi- ja maakuntakarttojen piirtovesi): SYKE Ranta10,
rantaviiva 1:10 000 (CC BY 4.0). Lataa ja esiyksinkertaista fetch_syke_lakes.py:llä:
  python3 fetch_syke_lakes.py syke_jarvet.geojson
Muut maanosat käyttävät edelleen ne_50m_lakes.geojson-aineistoa.
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

# Manner-USA:n 48 osavaltiota (Alaska, Havaiji ja DC eivät mahdu karttaan)
US_STATES = {
    "Alabama": "Alabama", "Arizona": "Arizona", "Arkansas": "Arkansas",
    "California": "Kalifornia", "Colorado": "Colorado",
    "Connecticut": "Connecticut", "Delaware": "Delaware",
    "Florida": "Florida", "Georgia": "Georgia", "Idaho": "Idaho",
    "Illinois": "Illinois", "Indiana": "Indiana", "Iowa": "Iowa",
    "Kansas": "Kansas", "Kentucky": "Kentucky", "Louisiana": "Louisiana",
    "Maine": "Maine", "Maryland": "Maryland",
    "Massachusetts": "Massachusetts", "Michigan": "Michigan",
    "Minnesota": "Minnesota", "Mississippi": "Mississippi",
    "Missouri": "Missouri", "Montana": "Montana", "Nebraska": "Nebraska",
    "Nevada": "Nevada", "New Hampshire": "New Hampshire",
    "New Jersey": "New Jersey", "New Mexico": "New Mexico",
    "New York": "New York", "North Carolina": "Pohjois-Carolina",
    "North Dakota": "Pohjois-Dakota", "Ohio": "Ohio",
    "Oklahoma": "Oklahoma", "Oregon": "Oregon",
    "Pennsylvania": "Pennsylvania", "Rhode Island": "Rhode Island",
    "South Carolina": "Etelä-Carolina", "South Dakota": "Etelä-Dakota",
    "Tennessee": "Tennessee", "Texas": "Texas", "Utah": "Utah",
    "Vermont": "Vermont", "Virginia": "Virginia",
    "Washington": "Washington", "West Virginia": "Länsi-Virginia",
    "Wisconsin": "Wisconsin", "Wyoming": "Wyoming",
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
    "usa": {
        "name": "Yhdysvallat", "bbox": (-125.5, -66, 24, 49.8), "reflat": 38,
        # kohteet ovat osavaltioita (admin-1); admin-0-maat jäävät taustaksi
        "countries": {}, "exclude": set(),
        "states": US_STATES, "states_admin": "United States of America",
        "features": [
            ("Meksikonlahti", "marine", ["Gulf of Mexico"]),
            ("Chesapeakenlahti", "marine", ["Chesapeake Bay"]),
            ("Yläjärvi", "lake", ["Lake Superior"]),
            ("Michiganjärvi", "lake", ["Lake Michigan"]),
            ("Huronjärvi", "lake", ["Lake Huron"]),
            ("Eriejärvi", "lake", ["Lake Erie"]),
            ("Ontariojärvi", "lake", ["Lake Ontario"]),
            ("Iso Suolajärvi", "lake", ["Great Salt Lake"]),
            ("Kalliovuoret", "region", ["ROCKY MOUNTAINS"]),
            ("Appalakit", "region", ["APPALACHIAN MTS."]),
            ("Suuret tasangot", "region", ["GREAT PLAINS"]),
            ("Sierra Nevada", "region", ["SIERRA NEVADA"]),
            ("Kaskadit", "region", ["CASCADE RANGE"]),
            ("Grand Canyon", "region", ["Grand Canyon"]),
            ("Mississippi", "river", ["Mississippi"]),
            ("Missourijoki", "river", ["Missouri"]),
            ("Coloradojoki", "river", ["Colorado"]),
            ("Rio Grande", "river", ["Rio Grande"]),
            ("Ohiojoki", "river", ["Ohio"]),
            ("Columbiajoki", "river", ["Columbia"]),
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
    "Eteläalpit", "Iso Vedenjakajavuoristo", "Sierra Nevada", "Kaskadit",
}

# Muut symboloitavat aluetyypit: symbolipolku generoidaan kuten vuorille
DESERT_FI = {"Sahara", "Kalahari", "Namibin aavikko", "Gobi", "Atacama",
             "Iso Victorianaavikko"}
PLATEAU_FI = {"Tiibetin ylänkö", "Suuret tasangot", "Patagonia", "Pampa"}
FOREST_FI = {"Amazonin allas", "Kongon allas"}
WETLAND_FI = {"Pantanal"}
CANYON_FI = {"Grand Canyon"}

# ------------------------------------------- englanninkieliset nimet
# Karttojen nimet (kenttä nameEn)
CONT_EN = {
    "suomi": "Finland", "eurooppa": "Europe", "aasia": "Asia",
    "afrikka": "Africa", "usa": "United States",
    "pohjois_amerikka": "North America", "etela_amerikka": "South America",
    "oseania": "Oceania",
}

# Maiden englanninkielinen nimi on NE-aineiston ADMIN; nämä siistitään
COUNTRY_EN_OVERRIDES = {
    "United States of America": "United States",
    "United Republic of Tanzania": "Tanzania",
    "Democratic Republic of the Congo": "DR Congo",
    "Republic of the Congo": "Congo",
    "Republic of Serbia": "Serbia",
    "Guinea Bissau": "Guinea-Bissau",
    "eSwatini": "Eswatini",
    "Federated States of Micronesia": "Micronesia",
}

# Luontokohteiden englanninnos johdetaan NE-nimestä; poikkeukset tähän
# (avain on suomenkielinen nimi)
FEATURE_EN = {
    "Skandinavian niemimaa": "Scandinavian Peninsula",
    "Balkanin niemimaa": "Balkan Peninsula",
    "Iberian niemimaa": "Iberian Peninsula",
    "Lappi": "Lapland",
    "Inarijärvi": "Lake Inari",
    "Tiibetin ylänkö": "Tibetan Plateau",
    "Jangtse": "Yangtze",
    "Keltainenjoki": "Yellow River",
    "Appalakit": "Appalachian Mountains",
    "Jukatanin niemimaa": "Yucatán Peninsula",
    "Atacama": "Atacama Desert",
    "Tulimaa": "Tierra del Fuego",
    "Titicaca": "Lake Titicaca",
    "Amazon": "Amazon",
}


def feature_en(fi, ne_names):
    if fi in FEATURE_EN:
        return FEATURE_EN[fi]
    ne = ne_names[0]
    return ne.title() if ne.isupper() else ne


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


def geom_rings(geom, project, w, h, tol=SIMPLIFY_TOL):
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
        pts = simplify(pts, tol)
        if len(pts) < 3:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) < MIN_RING_DIAG:
            continue
        rings.append(pts)
    return rings


def lake_draw_rings(geom, project, w, h, tol=SIMPLIFY_TOL, min_area=LAKE_MIN_AREA):
    """Järven piirtorenkaat reikineen (isot vain).

    Saaret (sisärenkaat) otetaan mukaan, jotta esim. Saimaa ei piirry
    umpilaikkuna maan päälle, jota pitkin tiet kulkevat; evenodd-täyttö
    tekee niistä reikiä. Saari kelpaa vain, jos sen järvi piirtyy —
    muuten evenodd maalaisi yksinäisen saaren järveksi.
    """
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return []

    def prep(ring):
        pts = clip_ring([project(lon, lat) for lon, lat in ring], w, h)
        if not pts:
            return None
        pts = simplify(pts, tol)
        if len(pts) < 3:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) < MIN_RING_DIAG:
            return None
        return pts

    out = []
    for poly in polys:
        outer = prep(poly[0])
        if outer is None or ring_area_centroid(outer)[0] < min_area:
            continue
        out.append(outer)
        for hole in poly[1:]:
            pts = prep(hole)
            if pts is not None and ring_area_centroid(pts)[0] >= min_area:
                out.append(pts)
    return out


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


def load_roads(geo, eps=1e-6):
    """Tiet numeroittain: tienumero -> murtoviivat (lon, lat).

    Väyläviraston koordinaatit ovat 4-ulotteisia (lon, lat, z, m), joten
    ne litistetään. Saman tien peräkkäiset pätkät ketjutetaan yhtenäisiksi
    viivoiksi, jotta yksinkertaistus tiivistää suorat osuudet pätkärajojen
    yli eikä joka pätkä aloita omaa osapolkua.
    """
    by_tie = {}
    for feat in geo["features"]:
        g = feat["geometry"]
        if g["type"] == "LineString":
            raw = [g["coordinates"]]
        elif g["type"] == "MultiLineString":
            raw = g["coordinates"]
        else:
            continue
        for line in raw:
            pts = [(p[0], p[1]) for p in line]
            if len(pts) >= 2:
                by_tie.setdefault(feat["properties"]["tie"], []).append(pts)

    def near(a, b):
        return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps

    for tie, segs in by_tie.items():
        chains = [list(s) for s in segs]
        merged = True
        while merged:
            merged = False
            out = []
            for seg in chains:
                for c in out:
                    if near(c[-1], seg[0]):
                        c.extend(seg[1:])
                    elif near(c[-1], seg[-1]):
                        c.extend(seg[-2::-1])
                    elif near(c[0], seg[-1]):
                        c[:0] = seg[:-1]
                    elif near(c[0], seg[0]):
                        c[:0] = seg[:0:-1]
                    else:
                        continue
                    merged = True
                    break
                else:
                    out.append(seg)
            chains = out
        by_tie[tie] = chains
    return by_tie


def roads_path(by_tie, lo, hi, project, w, h, tol, dec):
    """Tienumeroiden [lo, hi] tiet yhdeksi SVG-poluksi (koristekerros)."""
    lines = []
    for tie in sorted(by_tie):
        if not lo <= tie <= hi:
            continue
        for chain in by_tie[tie]:
            pts = [project(lon, lat) for lon, lat in chain]
            for run in clip_line(pts, w, h):
                run = simplify(run, tol, closed=False)
                if len(run) < 2:
                    continue
                xs = [p[0] for p in run]
                ys = [p[1] for p in run]
                if math.hypot(max(xs) - min(xs), max(ys) - min(ys)) < 3.0:
                    continue
                lines.append(run)
    return path_d(lines, close=False, dec=dec)


def path_d(rings, close=True, dec=1):
    parts = []
    for ring in rings:
        parts.append("M" + " ".join(f"{x:.{dec}f} {y:.{dec}f}" for x, y in ring)
                     + ("Z" if close else ""))
    return "".join(parts)


def flat(rings, dec=1):
    return [[round(v, dec) if dec else round(v) for pt in r for v in pt]
            for r in rings]


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


def mountain_marks(rings, u, step_u=26.0):
    """Symbolien sijainnit aluepolygonin sisällä (heksamainen ruudukko).

    Väli skaalataan ui-kertoimella u niin, että symbolitiheys näyttää
    samalta joka maanosassa; step_u säätää tiheyttä symbolityypeittäin.
    """
    step = step_u * u
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


def dune_path(marks, u):
    """Aavikon dyynikaari (matala ⌒)."""
    s = 4.5 * u
    parts = []
    for x, y in marks:
        parts.append(f"M{x - s:.1f} {y:.1f}"
                     f"Q{x:.1f} {y - s * 1.1:.1f} {x + s:.1f} {y:.1f}")
    return "".join(parts)


def plateau_path(marks, u):
    """Ylängön/tasangon vaakaviiva."""
    s = 4.5 * u
    parts = []
    for x, y in marks:
        parts.append(f"M{x - s:.1f} {y:.1f}L{x + s:.1f} {y:.1f}")
    return "".join(parts)


def tree_path(marks, u):
    """Sademetsän puusymboli: latvusympyrä ja runko."""
    r = 2.6 * u
    parts = []
    for x, y in marks:
        parts.append(f"M{x - r:.1f} {y:.1f}"
                     f"A{r:.1f} {r:.1f} 0 1 1 {x + r:.1f} {y:.1f}"
                     f"A{r:.1f} {r:.1f} 0 1 1 {x - r:.1f} {y:.1f}"
                     f"M{x:.1f} {y + r:.1f}L{x:.1f} {y + r * 2.2:.1f}")
    return "".join(parts)


def marsh_path(marks, u):
    """Kosteikon suomerkki: vaakaviiva ja pystytupsut."""
    s = 4.5 * u
    parts = []
    for x, y in marks:
        parts.append(f"M{x - s:.1f} {y:.1f}L{x + s:.1f} {y:.1f}"
                     f"M{x - s * 0.55:.1f} {y:.1f}L{x - s * 0.55:.1f} {y - s * 0.7:.1f}"
                     f"M{x:.1f} {y:.1f}L{x:.1f} {y - s * 0.9:.1f}"
                     f"M{x + s * 0.55:.1f} {y:.1f}L{x + s * 0.55:.1f} {y - s * 0.7:.1f}")
    return "".join(parts)


def canyon_path(marks, u):
    """Kanjonin siksak-viiva."""
    s = 4.5 * u
    parts = []
    for x, y in marks:
        parts.append(f"M{x - s * 1.4:.1f} {y + s * 0.5:.1f}"
                     f"L{x - s * 0.5:.1f} {y - s * 0.5:.1f}"
                     f"L{x + s * 0.5:.1f} {y + s * 0.5:.1f}"
                     f"L{x + s * 1.4:.1f} {y - s * 0.5:.1f}")
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
    admin1_geo = (load("ne_50m_admin_1.geojson")
                  if any(c.get("states") for c in CONTINENTS.values()) else None)
    lakes_geo = load("ne_50m_lakes.geojson")
    # Suomen ja maakuntien piirtovesi tarkasta kotimaisesta aineistosta;
    # muut maanosat ja haettavat järvikohteet käyttävät NE-aineistoa
    fin_lakes_geo = load("syke_jarvet.geojson")
    rivers_geo = load("ne_50m_rivers_lake_centerlines.geojson")
    marine_geo = load("ne_50m_geography_marine_polys.geojson")
    regions_geo = load("ne_50m_geography_regions_polys.geojson")
    roads_by_tie = load_roads(load("tiet_1_99.geojson"))

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
        # osavaltiokohteet (admin-1); maat jäävät edellä taustaksi
        if cfg.get("states"):
            for feat in admin1_geo["features"]:
                props = feat["properties"]
                if props.get("admin") != cfg["states_admin"]:
                    continue
                fi = cfg["states"].get(props.get("name"))
                if not fi:
                    continue
                rings = geom_rings(feat["geometry"], project, W, H)
                if rings:
                    target_rings.setdefault(fi, []).extend(rings)
        targets = [{"n": fi, "c": rings_centroid(rings),
                    "d": path_d(rings), "p": flat(rings)}
                   for fi, rings in target_rings.items()]
        # englanninkieliset nimet: maat NE:n ADMIN-nimestä (siistittynä),
        # osavaltiot NE:n name-kentästä; vain jos eri kuin suomalainen
        en_names = {}
        for admin, fi in cfg["countries"].items():
            if admin == "Aland":   # Ahvenanmaa yhdistyy Suomeen
                continue
            en_names.setdefault(fi, COUNTRY_EN_OVERRIDES.get(admin, admin))
        for ne_name, fi in cfg.get("states", {}).items():
            en_names.setdefault(fi, ne_name)
        for t in targets:
            en = en_names.get(t["n"])
            if en and en != t["n"]:
                t["e"] = en
        wanted_fi = set(cfg["countries"].values()) | set(cfg.get("states", {}).values())
        missing = wanted_fi - set(target_rings)
        if missing:
            print(f"!! {cfg['name']}: maita ei löytynyt: {sorted(missing)}")
        targets.sort(key=lambda t: t["n"])

        # järvet piirtoon (isot, saaret reikinä) — kaikki, ei vain kohteet;
        # Suomessa tarkka SYKE-aineisto (väljempi tiivistys, ettei tiedosto paisu
        # saarien myötä), muualla NE
        lake_src = fin_lakes_geo if key == "suomi" else lakes_geo
        lk_tol, lk_min = (1.5, 6.0) if key == "suomi" else (SIMPLIFY_TOL, LAKE_MIN_AREA)
        lake_rings = []
        for feat in lake_src["features"]:
            lake_rings.extend(lake_draw_rings(feat["geometry"], project, W, H,
                                              tol=lk_tol, min_area=lk_min))

        # luonnonkohteet
        kmpx = KM_PER_DEG_PY * (lat1 - lat0) / H
        # sama ui-kerroin kuin pelissä: näkymä 1 050 km × kokokerroin (Eurooppa = 1)
        sc = math.hypot(W, H) * kmpx / ref_diag_km
        u = (1050.0 * sc / kmpx) / 210.0
        features = []
        river_draw = []
        # symbolikohteet: nimijoukko, ruudukon tiheys ja polkugeneraattori
        symbol_types = {
            "mounts":   (MOUNTAIN_FI, 26.0, mountain_path),
            "deserts":  (DESERT_FI,   30.0, dune_path),
            "plateaus": (PLATEAU_FI,  30.0, plateau_path),
            "forests":  (FOREST_FI,   28.0, tree_path),
            "wetlands": (WETLAND_FI,  16.0, marsh_path),
            "canyons":  (CANYON_FI,   16.0, canyon_path),
        }
        symbol_marks = {k: [] for k in symbol_types}
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
                feat = {"n": fi, "k": "j", "c": lines_midpoint(lines),
                        "l": flat(lines)}
                en = feature_en(fi, ne_names)
                if en != fi:
                    feat["e"] = en
                features.append(feat)
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
                feat = {"n": fi, "k": "a", "c": rings_centroid(rings),
                        "p": flat(rings)}
                en = feature_en(fi, ne_names)
                if en != fi:
                    feat["e"] = en
                features.append(feat)
                for sk, (names, step_u, _) in symbol_types.items():
                    if fi in names:
                        # pieni alue voi jäädä ruudukolta väliin: silloin keskipiste
                        marks = mountain_marks(rings, u, step_u)
                        symbol_marks[sk].extend(marks or [tuple(rings_centroid(rings))])
                        break

        world[key] = {
            "name": cfg["name"], "nameEn": CONT_EN[key], "W": W, "H": H,
            "lon0": lon0, "lon1": lon1, "lat0": lat0, "lat1": lat1,
            "cos": round(cos, 6),
            "countries": targets, "bg": "".join(bg),
            "lakes": path_d(lake_rings),
            "rivers": path_d(river_draw, close=False),
            "features": features,
        }
        for sk, (_, _, pathfn) in symbol_types.items():
            world[key][sk] = pathfn(symbol_marks[sk], u)
        # valtatiet koristeeksi Suomen karttaan
        if key == "suomi":
            world[key]["roadsV"] = roads_path(roads_by_tie, 1, 29,
                                              project, W, H, tol=1.2, dec=1)
        print(f"{cfg['name']}: {W:.0f}x{H}, maita {len(targets)}, "
              f"taustaa {len(bg)}, järvirenkaita {len(lake_rings)}, "
              f"luonnonkohteita {len(features)}, symboleita " +
              "/".join(str(len(symbol_marks[k])) for k in symbol_types) +
              (f", tiedataa {len(world[key]['roadsV']) // 1024} kt"
               if key == "suomi" else ""))

    # ------------------------------------------- Suomen maakunnat ja kunnat
    # Manner-Suomen 18 maakuntaa omina karttoinaan; kunnat kohteina samassa
    # muodossa kuin maat, jolloin pelin maa-koneisto toimii sellaisenaan.
    kunnat_geo = load("kunnat_2026.geojson")
    maakunnat_geo = load("maakunnat_2026.geojson")

    def outer_rings_lonlat(geom):
        if geom["type"] == "Polygon":
            return [geom["coordinates"][0]]
        if geom["type"] == "MultiPolygon":
            return [poly[0] for poly in geom["coordinates"]]
        return []

    def lonlat_centroid(geom):
        best = max(outer_rings_lonlat(geom),
                   key=lambda r: ring_area_centroid(r)[0])
        _, cx, cy = ring_area_centroid(best)
        return cx, cy

    def slug(name):
        s = name.lower()
        for a, b in (("ä", "a"), ("ö", "o"), ("å", "a"), ("-", "_"), (" ", "_")):
            s = s.replace(a, b)
        return s

    # kunta kuuluu siihen maakuntaan, jonka sisällä sen keskipiste on;
    # Ahvenanmaan 16 kuntaa jätetään pois (pelissä vain Manner-Suomi)
    mk_feats = [f for f in maakunnat_geo["features"]
                if f["properties"]["nimi"] != "Ahvenanmaa"]
    mk_kunnat = {f["properties"]["nimi"]: [] for f in mk_feats}
    for kf in kunnat_geo["features"]:
        cx, cy = lonlat_centroid(kf["geometry"])
        for mf in maakunnat_geo["features"]:
            if any(point_in_ring(cx, cy, r)
                   for r in outer_rings_lonlat(mf["geometry"])):
                mk_kunnat.get(mf["properties"]["nimi"], []).append(kf)
                break
        else:
            print(f"!! kunta ilman maakuntaa: {kf['properties']['nimi']}")

    for mf in sorted(mk_feats, key=lambda f: f["properties"]["nimi"]):
        mk_nimi = mf["properties"]["nimi"]
        rings_ll = outer_rings_lonlat(mf["geometry"])
        lons = [p[0] for r in rings_ll for p in r]
        lats = [p[1] for r in rings_ll for p in r]
        mrg_lon = (max(lons) - min(lons)) * 0.08
        mrg_lat = (max(lats) - min(lats)) * 0.08
        bbox = (round(min(lons) - mrg_lon, 4), round(max(lons) + mrg_lon, 4),
                round(min(lats) - mrg_lat, 4), round(max(lats) + mrg_lat, 4))
        reflat = (bbox[2] + bbox[3]) / 2
        project, W, H, cos = make_projection(bbox, reflat)

        targets = []
        for kf in mk_kunnat[mk_nimi]:
            # kuntarajoille väljempi yksinkertaistus ja kokonaislukukoordi-
            # naatit, ettei datatiedosto paisu (292 kuntaa lähizoomilla)
            rings = geom_rings(kf["geometry"], project, W, H, tol=2.0)
            if not rings:
                print(f"!! {mk_nimi}: kunta ei mahtunut kartalle: "
                      f"{kf['properties']['nimi']}")
                continue
            targets.append({"n": kf["properties"]["nimi"],
                            "c": rings_centroid(rings),
                            "d": path_d(rings, dec=0), "p": flat(rings, dec=0)})
        targets.sort(key=lambda t: t["n"])

        bg = []
        for feat in countries_geo["features"]:
            admin = feat["properties"].get("ADMIN")
            if admin in ALWAYS_EXCLUDE:
                continue
            geom = overrides.get(admin, feat["geometry"])
            rings = geom_rings(geom, project, W, H)
            if rings:
                bg.append(path_d(rings))

        # väljempi tiivistys ja kokonaislukukoordinaatit (kuten kuntarajoilla),
        # ettei tiedosto paisu tuhansien saarien myötä
        lake_rings = []
        for feat in fin_lakes_geo["features"]:
            lake_rings.extend(lake_draw_rings(feat["geometry"], project, W, H,
                                              tol=2.5, min_area=8.0))

        # joet vain koristeeksi (ei kohteita)
        river_draw = []
        for feat in rivers_geo["features"]:
            river_draw.extend(geom_lines(feat["geometry"], project, W, H))

        # valta- ja kantatiet koristeeksi; sama tiivistys kuin kuntarajoissa
        roads_v = roads_path(roads_by_tie, 1, 29, project, W, H,
                             tol=2.0, dec=0)
        roads_k = roads_path(roads_by_tie, 40, 99, project, W, H,
                             tol=2.0, dec=0)

        world["mk_" + slug(mk_nimi)] = {
            "name": mk_nimi, "nameEn": mf["properties"]["name"],   # virallinen käännös
            "mk": 1, "W": W, "H": H,
            "lon0": bbox[0], "lon1": bbox[1], "lat0": bbox[2], "lat1": bbox[3],
            "cos": round(cos, 6),
            "countries": targets, "bg": "".join(bg),
            "lakes": path_d(lake_rings, dec=0),
            "rivers": path_d(river_draw, close=False),
            "roadsV": roads_v, "roadsK": roads_k,
            "features": [],
        }
        print(f"{mk_nimi}: {W:.0f}x{H}, kuntia {len(targets)}, "
              f"järvirenkaita {len(lake_rings)}, jokipätkiä {len(river_draw)}, "
              f"tiedataa {(len(roads_v) + len(roads_k)) // 1024} kt")

    out = ("// Generoitu build_world.py:llä Natural Earth -aineistoista\n"
           "const CONTINENTS="
           + json.dumps(world, ensure_ascii=False, separators=(",", ":"))
           + ";\n")
    with open(dst, "w") as f:
        f.write(out)
    print(f"{dst}: {len(out) // 1024} KB")


if __name__ == "__main__":
    main()
