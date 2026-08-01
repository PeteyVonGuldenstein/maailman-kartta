#!/usr/bin/env python3
"""Staattinen palvelin Maailman kartta -pelille portissa 8095.

Pakkaa tekstiaineistot gzipillä ja sallii selaimen välimuistin
(Cache-Control: no-cache = käytä välimuistia, mutta tarkista aina
palvelimelta onko tiedosto muuttunut). Muuttumaton world_data.js
vastataan silloin 304:llä, eli se siirtyy vain kun se on oikeasti
päivittynyt — ja silloinkin pakattuna (~1,9 MB → ~0,5 MB).
"""
import email.utils
import gzip
import io
import os
from datetime import timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8095
MIN_GZIP = 1024
GZIP_TYPES = {"text/html", "text/css", "text/plain", "text/javascript",
              "application/javascript", "application/json", "image/svg+xml",
              "application/manifest+json"}

_gz_cache = {}   # polku -> (mtime, koko, pakatut tavut)


def gzipped(path, data, st):
    """Pakattu sisältö muistivälimuistista; pakkaa uudelleen jos tiedosto muuttui."""
    key = (st.st_mtime, st.st_size)
    hit = _gz_cache.get(path)
    if hit and hit[0] == key:
        return hit[1]
    out = gzip.compress(data, 6)
    _gz_cache[path] = (key, out)
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith("/"):
                return super().send_head()      # oletus hoitaa uudelleenohjauksen
            path = os.path.join(path, "index.html")
        if not os.path.isfile(path):
            return super().send_head()          # 404 tai hakemistolistaus
        try:
            st = os.stat(path)
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        lastmod = email.utils.formatdate(st.st_mtime, usegmt=True)
        if self.unchanged(st):
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("Last-Modified", lastmod)
            self.end_headers()
            return None

        ctype = self.guess_type(path)
        gz = (ctype.split(";")[0] in GZIP_TYPES and len(body) >= MIN_GZIP
              and "gzip" in self.headers.get("Accept-Encoding", ""))
        if gz:
            body = gzipped(path, body, st)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if gz:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Last-Modified", lastmod)
        self.end_headers()
        return io.BytesIO(body)

    def unchanged(self, st):
        """Onko selaimen versio yhä ajan tasalla (If-Modified-Since)?"""
        ims = self.headers.get("If-Modified-Since")
        if not ims:
            return False
        try:
            when = email.utils.parsedate_to_datetime(ims)
        except (TypeError, IndexError, OverflowError, ValueError):
            return False
        if when is None:
            return False
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return int(when.timestamp()) >= int(st.st_mtime)

    def end_headers(self):
        # no-cache (ei no-store): välimuisti käyttöön, mutta aina tarkistettuna,
        # jotta peliin tehdyt muutokset näkyvät heti seuraavalla latauksella
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Maailman kartta: http://0.0.0.0:{PORT}", flush=True)
    server.serve_forever()
