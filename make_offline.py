#!/usr/bin/env python3
"""Kokoaa pelin yhdeksi tiedostoksi (maailman-kartta.html).

Upottaa datatiedostot index.html:n sisään, jolloin sivu toimii sellaisenaan
ilman palvelinta ja verkkoyhteyttä (esim. sähköpostin liitteenä jaettuna).
Aja aina kun index.html tai jokin datatiedosto muuttuu.
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = ["world_data.js", "kuntakeskukset.js"]

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
