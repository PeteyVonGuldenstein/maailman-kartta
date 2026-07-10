#!/usr/bin/env python3
"""Generoi webapp-kuvakkeet (PNG) pelin helikopterihahmosta.

Tuottaa icon-192.png ja icon-512.png (manifest) sekä
apple-touch-icon.png (180 px, iOS-kotivalikko). Aja, jos kuvake muuttuu.
"""
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
SIZE = 1024  # piirretään isona ja pienennetään tarkkuuden vuoksi


def draw_icon():
    img = Image.new("RGB", (SIZE, SIZE), "#40318d")
    d = ImageDraw.Draw(img, "RGBA")
    # kopteri hieman oikealle, jotta vasemmalle työntyvä pyrstö pysyy
    # maskatun kuvakkeen turva-alueella (keskimmäinen 80 %)
    cx, cy = SIZE // 2 + 45, SIZE // 2
    s = 15  # pelin SVG-koordinaattien skaala

    # vaalea kehä ja varjo
    d.ellipse([cx - 300, cy - 300, cx + 300, cy + 300], fill=(255, 255, 255, 26))
    d.ellipse([cx - 13 * s, cy + 5 * s, cx + 15 * s, cy + 11 * s],
              fill=(0, 0, 0, 45))

    # pyrstöpuomi ja pyrstöroottori
    d.line([cx - 22 * s, cy, cx - 9 * s, cy], fill="#a03325", width=int(3 * s))
    d.ellipse([cx - 26.5 * s, cy - 4.5 * s, cx - 17.5 * s, cy + 4.5 * s],
              outline="#7c2417", width=int(1.4 * s))

    # laskutelineet
    for y in (-8.5 * s, 8.5 * s):
        d.line([cx - 8 * s, cy + y, cx + 10 * s, cy + y], fill="#3a3a3a",
               width=int(1.6 * s))

    # runko ja ohjaamo
    d.ellipse([cx - 12 * s, cy - 7 * s, cx + 12 * s, cy + 7 * s],
              fill="#d94f3d", outline="#a03325", width=int(1.2 * s))
    d.ellipse([cx + 6 * s - 3.4 * s, cy - 3.4 * s, cx + 6 * s + 3.4 * s, cy + 3.4 * s],
              fill="#bfe3f0")

    # pyörivä pääroottori: läpikuultava kiekko, yksi lapa ja napa
    rr = 16 * s
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
              fill=(255, 255, 255, 38), outline=(255, 255, 255, 90),
              width=int(0.6 * s))
    a = math.radians(24)
    bx, by = rr * math.cos(a), rr * math.sin(a)
    d.line([cx - bx, cy + by, cx + bx, cy - by], fill="#2b2b2b",
           width=int(1.4 * s))
    d.ellipse([cx - 2 * s, cy - 2 * s, cx + 2 * s, cy + 2 * s], fill="#333333")
    return img


def main():
    img = draw_icon()
    for name, px in (("icon-512.png", 512), ("icon-192.png", 192),
                     ("apple-touch-icon.png", 180)):
        out = os.path.join(ROOT, name)
        img.resize((px, px), Image.LANCZOS).save(out)
        print(f"{out}: {px}x{px}")


if __name__ == "__main__":
    main()
