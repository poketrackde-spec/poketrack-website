"""Baut das Vorschaubild (1200x630 PNG) fuer Link-Vorschauen, Suchmaschinen und KI-Antworten.

Aufruf: python tools/vorschaubild.py  -> bilder/poketrack-app-vorschau.png
Neu bauen, wenn sich die App-Screenshots in bilder/app/ aendern.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(WURZEL, "bilder", "poketrack-app-vorschau.png")
B, H = 1200, 630
DUNKEL, FLAECHE, AKZENT, TEXT, LEISE = "#0F1F33", "#1E3A5F", "#F0B429", "#E8EFF7", "#8A9EB8"
FONT = "C:/Windows/Fonts/segoeuib.ttf"
FONT_N = "C:/Windows/Fonts/segoeui.ttf"


def abgerundet(bild, r):
    maske = Image.new("L", bild.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, *bild.size), r, fill=255)
    bild.putalpha(maske)
    return bild


def main():
    img = Image.new("RGB", (B, H), DUNKEL)
    d = ImageDraw.Draw(img)
    # sanfter Verlauf nach rechts
    for x in range(B):
        t = x / B
        c = tuple(int(a + (b - a) * t) for a, b in zip((15, 31, 51), (30, 58, 95)))
        d.line([(x, 0), (x, H)], fill=c)

    logo = Image.open(os.path.join(WURZEL, "logo.png")).convert("RGBA").resize((120, 120), Image.LANCZOS)
    img.paste(abgerundet(logo, 26), (70, 90), abgerundet(logo.copy(), 26))
    d.text((70, 235), "PokéTrack", font=ImageFont.truetype(FONT, 84), fill=TEXT)
    d.text((72, 345), "Pokémon-Karten scannen,", font=ImageFont.truetype(FONT_N, 36), fill=TEXT)
    d.text((72, 390), "sammeln und bewerten", font=ImageFont.truetype(FONT_N, 36), fill=TEXT)
    d.text((72, 455), "Deutsche Marktpreise · Reverse Holo · Preisverlauf", font=ImageFont.truetype(FONT_N, 24), fill=LEISE)
    # Akzent-Pille
    f = ImageFont.truetype(FONT, 24)
    txt = "Kostenlos für iPhone & iPad"
    w = d.textlength(txt, font=f)
    d.rounded_rectangle((70, 520, 70 + w + 44, 568), 24, fill=AKZENT)
    d.text((92, 527), txt, font=f, fill=DUNKEL)

    # drei Screenshots, leicht gestaffelt
    for i, (name, x, y) in enumerate([("statistik", 650, 95), ("scanner", 930, 55), ("start", 790, 75)]):
        s = Image.open(os.path.join(WURZEL, "bilder", "app", name + ".webp")).convert("RGBA")
        s = s.resize((236, int(236 * s.height / s.width)), Image.LANCZOS)
        s = abgerundet(s, 26)
        schatten = Image.new("RGBA", (s.width + 40, s.height + 40), (0, 0, 0, 0))
        ImageDraw.Draw(schatten).rounded_rectangle((20, 24, s.width + 20, s.height + 24), 26, fill=(0, 0, 0, 140))
        schatten = schatten.filter(ImageFilter.GaussianBlur(12))
        img.paste(schatten, (x - 20, y - 20), schatten)
        img.paste(s, (x, y), s)
    img.save(ZIEL, optimize=True)
    print("->", ZIEL, os.path.getsize(ZIEL) // 1024, "KB")


if __name__ == "__main__":
    main()
