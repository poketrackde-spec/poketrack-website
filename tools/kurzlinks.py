"""Baut die Kurz-Links poketrack.de/<kanal>/ (Bios und Video-Beschreibungen).

iPhone/iPad und Computer -> App Store (mit Kampagnen-Kuerzel ct=<kanal>).
Android -> Play Store, sobald PLAY_LIVE = True ist (Play-Store-Start).
Bis dahin landen auch Android-Nutzer im App Store wie bisher.

Jeder Aufruf meldet vorher anonym Kanal + Geraet an das Backend (/k/<kanal>).

Aufruf:  python tools/kurzlinks.py   (danach committen und pushen)
"""
from pathlib import Path

PLAY_LIVE = False   # beim Play-Store-Start auf True setzen

KANAELE = ["instagram", "tiktok", "threads", "youtube", "facebook"]
BACKEND = "https://poketrack-backend-production.up.railway.app"
PAKET = "com.pokede.app"
ROOT = Path(__file__).resolve().parent.parent


def app_store(kanal: str) -> str:
    return f"https://apps.apple.com/de/app/id6790953375?pt=129170544&ct={kanal}&mt=8"


def play_store(kanal: str) -> str:
    # referrer landet in der Play Console unter "Nutzerakquisition" (utm_source)
    ref = f"utm_source%3D{kanal}%26utm_medium%3Dsocial%26utm_campaign%3Dkurzlink"
    return f"https://play.google.com/store/apps/details?id={PAKET}&referrer={ref}"


def seite(kanal: str) -> str:
    a = app_store(kanal)
    p = play_store(kanal)
    a_html = a.replace("&", "&amp;")
    live = "true" if PLAY_LIVE else "false"
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>PokéTrack laden</title>
<noscript><meta http-equiv="refresh" content="0; url={a_html}"></noscript>
<script>(function(){{var A="{a}",P="{p}",LIVE={live};
var u=navigator.userAgent||"",g=/android/i.test(u)?"android":(/iphone|ipad|ipod/i.test(u)||(/macintosh/i.test(u)&&navigator.maxTouchPoints>1))?"ios":"andere";
var z=(g==="android"&&LIVE)?P:A;
try{{navigator.sendBeacon("{BACKEND}/k/{kanal}?g="+g)}}catch(e){{}}
setTimeout(function(){{location.replace(z)}},150);
document.addEventListener("DOMContentLoaded",function(){{var l=document.getElementById("l");if(l)l.href=z;}});}})();</script>
<style>body{{margin:0;background:#0c182a;color:#eef3f9;font:17px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;text-align:center;padding:16px}}a{{color:#f0b429}}</style>
</head><body><p>Weiter zu PokéTrack …<br><a id="l" href="{a_html}">Hier tippen, falls nichts passiert</a></p></body></html>
"""


def main() -> None:
    for k in KANAELE:
        ziel = ROOT / k / "index.html"
        ziel.parent.mkdir(exist_ok=True)
        ziel.write_text(seite(k), encoding="utf-8")
        print("geschrieben:", ziel.relative_to(ROOT))
    print("Play Store aktiv:", PLAY_LIVE)


if __name__ == "__main__":
    main()
