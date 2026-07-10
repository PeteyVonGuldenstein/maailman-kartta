#!/usr/bin/env python3
"""Kokoaa pelin yhdeksi tiedostoksi (euroopan-kartta.html).

Upottaa map_data.js:n index.html:n sisään, jolloin sivu toimii
sellaisenaan ilman palvelinta ja verkkoyhteyttä (esim. sähköpostin
liitteenä jaettuna). Aja aina kun index.html tai map_data.js muuttuu.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
TAG = '<script src="world_data.js"></script>'

with open(os.path.join(ROOT, "index.html")) as f:
    html = f.read()
with open(os.path.join(ROOT, "world_data.js")) as f:
    data = f.read()

assert TAG in html, "world_data.js-viittausta ei löytynyt index.html:stä"
html = html.replace(TAG, "<script>\n" + data + "</script>")

out = os.path.join(ROOT, "maailman-kartta.html")
with open(out, "w") as f:
    f.write(html)
print(f"{out}: {os.path.getsize(out) // 1024} KB")
