#!/usr/bin/env python3
"""Lataa SYKE Ranta10 -järvet ja esiyksinkertaistaa ne build_world.py:tä varten.

Lähde: SYKE Ranta10, rantaviiva 1:10 000 (CC BY 4.0). Avoin WFS, ei tunnistetta.
  WFS:   https://paikkatiedot.ymparisto.fi/geoserver/syke_rantaviiva/wfs
  taso:  syke_rantaviiva:Ranta10_Jarvi (MultiPolygon, saaret sisärenkaina)

Raaka 1:10 000 -aineisto on piirtokäyttöön liian raskas (~65 kt/järvi, Saimaa
~60 000 pistettä). Geometria harvennetaan siksi Douglas–Peuckerilla (~80 m) jo
tässä; build_world.py yksinkertaistaa lopuksi vielä pikselitarkkuuteen kunkin
kartan projektiossa. Sivutus + sivukohtainen käsittely pitää muistinkäytön
kurissa (palvelimen katto on 5000 kohdetta/pyyntö).

Käyttö:  python3 fetch_syke_lakes.py <ulostulo.geojson>
"""
import json
import math
import os
import subprocess
import sys
import tempfile

WFS = "https://paikkatiedot.ymparisto.fi/geoserver/syke_rantaviiva/wfs"
TYPENAME = "syke_rantaviiva:Ranta10_Jarvi"
AREA_MIN = 200000     # m^2 (0,2 km²); pienemmät järvet jätetään pois
PAGE = 1000           # kohdetta/pyyntö; pieni sivu = kevyt muisti
TOL_DEG = 0.0008      # ~80 m harvennustoleranssi (lon skaalataan cos(lat):lla)


def perp_dist(p, a, b, kx):
    """Pisteen p etäisyys janasta a–b, lon-akseli skaalattu kx:llä (cos lat)."""
    ax, ay = a[0] * kx, a[1]
    bx, by = b[0] * kx, b[1]
    px, py = p[0] * kx, p[1]
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dp(pts, kx):
    """Iteratiivinen Douglas–Peucker (rekursio kaatuisi Saimaan 60 000 pisteeseen)."""
    n = len(pts)
    if n < 3:
        return pts[:]
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        dmax, idx = 0.0, -1
        for i in range(a + 1, b):
            d = perp_dist(pts[i], pts[a], pts[b], kx)
            if d > dmax:
                dmax, idx = d, i
        if dmax > TOL_DEG and idx != -1:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [pts[i] for i in range(n) if keep[i]]


def simplify_ring(ring):
    """Harventaa suljetun renkaan; palauttaa None jos jäljelle jää liian vähän."""
    kx = math.cos(math.radians(ring[0][1]))
    s = dp([[p[0], p[1]] for p in ring], kx)   # varmuudeksi 2D
    if len(s) < 4:
        return None
    if s[0] != s[-1]:
        s.append(s[0])
    return [[round(p[0], 5), round(p[1], 5)] for p in s]


def simplify_geom(geom):
    """Harventaa polygon/multipolygon-geometrian; ulkorengas pakollinen."""
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return None
    out = []
    for poly in polys:
        rings = []
        for i, ring in enumerate(poly):
            s = simplify_ring(ring)
            if s is None:
                if i == 0:        # ulkorengas katosi -> koko pala pois
                    rings = []
                    break
                continue          # saari katosi -> ohitetaan vain se
            rings.append(s)
        if rings:
            out.append(rings)
    if not out:
        return None
    return {"type": "MultiPolygon", "coordinates": out}


def fetch_page(start):
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature"
           f"&typeNames={TYPENAME}&outputFormat=application/json"
           f"&srsName=EPSG:4326&sortBy=objectid"
           f"&cql_filter=area_m2%3E{AREA_MIN}"
           f"&count={PAGE}&startIndex={start}")
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        subprocess.run(["curl", "-s", "--max-time", "600", "-A", "Mozilla/5.0",
                        "-o", tmp, url], check=True)
        with open(tmp) as f:
            return json.load(f)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else "syke_jarvet.geojson"
    feats = []
    start = 0
    while True:
        d = fetch_page(start)
        got = d.get("features", [])
        for f in got:
            g = simplify_geom(f["geometry"])
            if g is None:
                continue
            p = f.get("properties") or {}
            feats.append({"type": "Feature", "geometry": g,
                          "properties": {"nimi": p.get("nimi"),
                                         "area_m2": p.get("area_m2")}})
        n = len(got)
        print(f"startIndex={start}: haettu {n}, tallessa {len(feats)}", flush=True)
        start += PAGE
        if n < PAGE:
            break
    with open(dst, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats},
                  f, separators=(",", ":"))
    print(f"{dst}: {len(feats)} järveä, {os.path.getsize(dst) // 1024} kt")


if __name__ == "__main__":
    main()
