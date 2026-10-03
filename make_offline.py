#!/usr/bin/env python3
"""Kokoaa pelin yhdeksi tiedostoksi (maailman-kartta.html) ja versioi sw.js:n.

Upottaa datatiedostot index.html:n sisään, jolloin sivu toimii sellaisenaan
ilman palvelinta ja verkkoyhteyttä (esim. sähköpostin liitteenä jaettuna).

Lisäksi sw.js:n CACHE-nimeen kirjoitetaan webappin tiedostojen tiiviste:
jokainen muutos vaihtaa nimen, jolloin puhelimet asentavat uuden version
kokonaisena eikä nimen nostoa voi unohtaa.
Aja aina kun index.html tai jokin datatiedosto muuttuu.
"""
import hashlib
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = ["world_data.js", "kuntakeskukset.js"]
# sama lista kuin sw.js:n CORE (paitsi "./", joka on index.html)
WEBAPP = ["index.html", *DATA, "manifest.json",
          "icon-192.png", "icon-512.png", "apple-touch-icon.png"]

with open(os.path.join(ROOT, "index.html")) as f:
    html = f.read()

for name in DATA:
    tag = f'<script src="{name}"></script>'
    assert tag in html, f"{name}-viittausta ei löytynyt index.html:stä"
    with open(os.path.join(ROOT, name)) as f:
        html = html.replace(tag, "<script>\n" + f.read() + "</script>")

out = os.path.join(ROOT, "maailman-kartta.html")
with open(out, "w") as f:
    f.write(html)
print(f"{out}: {os.path.getsize(out) // 1024} KB")

digest = hashlib.sha256()
for name in WEBAPP:
    with open(os.path.join(ROOT, name), "rb") as f:
        digest.update(f.read())
version = digest.hexdigest()[:10]

sw_path = os.path.join(ROOT, "sw.js")
with open(sw_path) as f:
    sw = f.read()
sw_new, n = re.subn(r'const CACHE = "maailman-kartta-[^"]*";',
                    f'const CACHE = "maailman-kartta-{version}";', sw)
assert n == 1, "CACHE-riviä ei löytynyt sw.js:stä"
if sw_new != sw:
    with open(sw_path, "w") as f:
        f.write(sw_new)
print(f"{sw_path}: välimuisti maailman-kartta-{version}")
