# ============================================================
# generate_katalog.py – Erzeugt den statischen Karten-Katalog fuer poketrack.de
#   (Phase 1: oeffentliche SEO-Seiten, gebaut aus assets/db.json).
#
# Ausgabe (relativ zu OUT):
#   karten/index.html                          – alle Sets (nach Aera)
#   karten/katalog.css                         – geteilte Styles
#   karten/<set>/index.html                    – Set-Seite (Karten-Grid)
#   karten/<set>/<nr>-<name>/index.html        – Karten-Detailseite
#   karten/sitemap.xml                         – alle Katalog-URLs
#
# Preise:
#   - Sondervarianten (Pokeball/Masterball) werden aus variant_preise GEBACKEN
#     (SEO: Preis steht im HTML) – konsistent mit der App.
#   - Normaler Referenzpreis wird CLIENT-SEITIG vom Backend geladen (gleiche
#     Quelle wie die App), sobald CORS aktiv ist.
#
# Dieses Skript laeuft an zwei Orten und muss deshalb ohne lokale Pfade auskommen:
#   1. lokal ueber poketrack-scraper/deploy.py (nach einem Scrape)
#   2. naechtlich in .github/workflows/katalog.yml (Kartendaten aus /cards)
# Alle drei Eingaben sind darum ueber Umgebungsvariablen ueberschreibbar.
# ============================================================

import json
import os
import re
import html
import datetime
import time
import urllib.request
import urllib.parse

DB = os.environ.get("KATALOG_DB") or r"C:\Users\danie\Documents\Pokemon App\assets\db.json"
SETMETA_TS = (os.environ.get("KATALOG_SETMETA")
              or r"C:\Users\danie\Documents\Pokemon App\src\data\setMetadata.ts")
# Ausgabewurzel (Website-Repo-Root); ueber KATALOG_OUT ueberschreibbar.
OUT = os.environ.get("KATALOG_OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "katalog")


def load_set_meta():
    """Liest Era-Reihenfolge + Logo/Era pro Set aus der App-Datei setMetadata.ts
    (Wahrheitsquelle), damit die Web-Uebersicht 1:1 der App entspricht."""
    txt = open(SETMETA_TS, encoding="utf-8").read()
    m = re.search(r"ERA_ORDER\s*=\s*\[(.*?)\]", txt, re.S)
    era_order = re.findall(r"'([^']+)'", m.group(1)) if m else []
    meta = {}
    for key, body in re.findall(r"'([^']+)':\s*\{([^}]*)\}", txt):
        era_m = re.search(r"era:\s*'([^']*)'", body)
        logo = None
        lm = re.search(r"logo:\s*'([^']*)'", body)
        if lm:
            logo = lm.group(1)
        else:
            tm = re.search(r"logo:\s*TCG\('([^']*)'\)", body)  # TCG('id') -> volle URL
            if tm:
                logo = f"https://images.pokemontcg.io/{tm.group(1)}/logo.png"
        rt_m = re.search(r"reverseTypes:\s*\[([^\]]*)\]", body)
        rtypes = re.findall(r"'([^']+)'", rt_m.group(1)) if rt_m else None
        meta[key] = {"era": era_m.group(1) if era_m else "Weitere Sets",
                     "logo": logo, "reverseTypes": rtypes}
    return era_order, meta
BACKEND = "https://poketrack-backend-production.up.railway.app"
APPSTORE = "https://apps.apple.com/de/app/id6790953375"
BASE = "https://poketrack.de"
MORE_LIMIT = 12
# name -> [(set_name, card)] ueber ALLE Sets (auch bei Einzel-Set-Generierung),
# damit "Mehr Karten von X" set-uebergreifend verlinkt. In main() befuellt.
NAME_INDEX = {}

# db.json-Setname weicht vom Schluessel in setMetadata.ts ab (Umbenennungen) ->
# fuer Era/Logo-Zuordnung aufloesen. Angezeigt wird weiter der db.json-Name.
SET_ALIAS = {
    "Chaos Rising": "Wachsendes Chaos",
    "Fatale Flammen (Mega)": "Fatale Flammen",
}


def _meta(set_meta, set_name):
    return set_meta.get(SET_ALIAS.get(set_name, set_name)) or {}


def card_reverse_variants(card, set_reverse_types):
    """Reverse-Varianten-Keys einer Karte – 1:1 wie App variants.ts::cardReverseTypes.
    Gate inklusiv (has_reverse ODER hat_reverse), damit Sonder-Varianten-Sets wie
    Erhabene Helden (has_reverse=false, hat_reverse=true, reverse_typ='beide') erfasst
    werden. set_reverse_types = reverseTypes des Sets (Default ['reverse'])."""
    if not (card.get("has_reverse") or card.get("hat_reverse")):
        return []
    st = set_reverse_types or ["reverse"]
    typ = card.get("reverse_typ")
    if not typ or typ == "beide":     return st
    if typ == "pokeball":             return [rt for rt in st if "pokeball" in rt]
    if typ == "energie":              return [rt for rt in st if "energie" in rt]
    if typ == "normal":               return ["reverse"]
    if typ == "team_rocket":          return ["reverse_team_rocket"]
    if typ == "energie_team_rocket":  return [rt for rt in st if "energie" in rt] + ["reverse_team_rocket"]
    if typ == "pb_mb_normal":         return ["reverse_pokeball", "reverse_masterball", "reverse"]
    if typ == "pb_normal":            return ["reverse_pokeball", "reverse"]
    return st

# Set -> Aera (kompakt gehalten; unbekannte -> "Weitere Sets")
try:
    import sys
    sys.path.insert(0, os.path.dirname(DB))
except Exception:
    pass

UMLAUT = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "é": "e", "É": "E"}
VARIANT_NAME = {
    "reverse": "Reverse Holo", "reverse_pokeball": "Pokéball Reverse",
    "reverse_masterball": "Masterball Reverse", "reverse_energie": "Energie Reverse",
    "reverse_team_rocket": "Team-Rocket Reverse",
}

# Kartentyp: englischer db.json-Wert -> deutscher Anzeigename (wie in der App)
TYPE_DE = {
    "Fire": "Feuer", "Water": "Wasser", "Grass": "Pflanze", "Lightning": "Elektro",
    "Psychic": "Psycho", "Fighting": "Kampf", "Darkness": "Finsternis", "Metal": "Metall",
    "Dragon": "Drachen", "Fairy": "Fee", "Colorless": "Farblos",
}
# Typ-Farben (aufgehellt, damit sie auf dem dunklen Hintergrund lesbar sind)
TYPE_COLOR = {
    "Feuer": "#FF7043", "Wasser": "#42A5F5", "Pflanze": "#66BB6A", "Elektro": "#FFCA28",
    "Psycho": "#C77DD6", "Kampf": "#D98A4B", "Finsternis": "#A78BC0", "Metall": "#A8B3BF",
    "Drachen": "#E0B84C", "Fee": "#F06FA8", "Farblos": "#C2CAD6",
}


def slug(s):
    s = (s or "").strip().lower()
    for a, b in UMLAUT.items():
        s = s.replace(a, b.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "x"


def num_slug(nummer):
    return slug((nummer or "").split("/")[0])


# Wie formatCardNumber in der App (src/utils/format.ts): bei diesen Sets fuehrende
# Nullen entfernen (8/102 statt 008/102). Alle anderen Sets: Nummer unveraendert.
SET_NUMBER_FORMAT = {
    "Basisset", "Dschungel", "Fossil", "Team Rocket", "Neo Genesis", "Neo Entdeckung",
    "Neo Revelation", "Neo Destiny", "Expedition", "EX Rubin & Saphir", "EX Sandsturm",
}


def fmt_num(nummer, set_name):
    """Anzeige-Nummer wie in der App. NUR fuer Anzeige - URL/Backend-Query bleiben roh."""
    if not nummer:
        return ""
    if set_name not in SET_NUMBER_FORMAT:
        return nummer
    teile = []
    for part in nummer.split("/"):
        try:
            teile.append(str(int(part)))
        except ValueError:
            teile.append(part)
    return "/".join(teile)


def e(s):
    return html.escape(str(s if s is not None else ""))


def euro(v):
    # Deutsches Format mit Tausenderpunkt: 2900.64 -> "2.900,64 €"
    s = f"{v:,.2f}"  # US-Format 2,900.64 -> dann Trennzeichen tauschen
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def datum_de(iso):
    """'2026-08-04' -> '4.8.2026'. Unbekanntes Format bleibt unveraendert."""
    try:
        j, m, t = str(iso).split("-")
        return f"{int(t)}.{int(m)}.{j}"
    except Exception:
        return str(iso)


# Cardmarket-Zustandsstufen auf Deutsch (dieselben Bezeichnungen wie im Scraper).
KONDITION_DE = {
    "nm": "Near Mint", "excellent": "Excellent", "good": "Good",
    "light_played": "Light Played", "played": "Played", "poor": "Poor",
}


# Inline-SVG-Flagge statt Emoji: 🇩🇪 rendert auf Windows nur als "DE".
FLAG_DE = ('<svg class="kflag" viewBox="0 0 5 3" role="img" aria-label="Deutschland">'
           '<rect width="5" height="3" fill="#FFCE00"/>'
           '<rect width="5" height="2" fill="#DD0000"/>'
           '<rect width="5" height="1" fill="#000000"/></svg>')


# Sets, deren Preise nicht abrufbar waren. Lokal ist das ein Hinweis, in der
# naechtlichen Action ein Abbruchgrund: ein Katalog ohne Preise ist genau der
# "minderwertige Inhalt", den AdSense beanstandet hat.
PREIS_FEHLER = []

# Letzter veroeffentlichter Stand: {"/karten/<set>/<karte>/": [preis|null, "YYYY-MM-DD"]}
# Wird mitveroeffentlicht, damit der naechste Lauf weiss, welche Preise sich wirklich
# geaendert haben - siehe stand_laden().
STAND_DATEI = "karten/stand.json"


def stand_laden():
    """Den zuletzt VEROEFFENTLICHTEN Stand holen - bevorzugt von der Live-Seite.

    Warum nicht aus dem Arbeitsordner: In der GitHub-Action ist der bei jedem Lauf
    frisch ausgecheckt, das eingecheckte karten/ ist eingefroren. Der einzige Ort,
    der zuverlaessig sagt, was Google zuletzt gesehen hat, ist die Seite selbst.
    Lokal ist die Live-Seite ebenfalls die richtige Bezugsgroesse: Baue ich zweimal
    ohne Deploy, hat sich fuer Google zwischendurch nichts geaendert.
    """
    # User-Agent ist PFLICHT: GitHub Pages beantwortet den Standardkopf von
    # urllib ("Python-urllib/3.x") mit 403. Ohne den Header schlaegt das Laden
    # jede Nacht fehl, der Vergleich findet nie einen Vorstand - und die Sitemap
    # meldet Google wieder jeden Tag 19.000 Aenderungen.
    anfrage = urllib.request.Request(f"{BASE}/{STAND_DATEI}",
                                     headers={"User-Agent": "poketrack-katalog"})
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as r:
            daten = json.loads(r.read().decode())
            if isinstance(daten, dict) and daten:
                print(f"  Vorstand: {len(daten)} URLs von {BASE} geladen")
                return daten
    except Exception as e:
        print(f"  Vorstand: Live-Abruf fehlgeschlagen ({type(e).__name__}: {e})")
    pfad = os.path.join(OUT, STAND_DATEI)          # Notnagel: letzter lokaler Lauf
    try:
        with open(pfad, encoding="utf-8") as f:
            daten = json.load(f)
        print(f"  Vorstand: {len(daten)} URLs aus {STAND_DATEI} (lokal)")
        return daten
    except Exception:
        print("  Vorstand: keiner gefunden - alle lastmod bekommen das heutige Datum")
        return {}


def preis_gleich(a, b):
    """Preisvergleich fuer die Sitemap. Beide ohne Preis = unveraendert."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) < 0.005


def fetch_set_prices(set_name):
    """Preise + Preisverlauf ALLER Karten eines Sets in einem Aufruf (/set-prices).

    Frueher lief das ueber /price pro Karte. Seit die Kartenseiten auch den Verlauf
    zeigen, waeren das zwei Abrufe je Karte - bei ~19.000 Karten also ~38.000 pro Lauf.
    Jetzt ist es einer pro Set.

    -> {nummer: {"avg": float|None, "stand": "YYYY-MM-DD"|None, "history": [...]}}
    Leeres Dict, wenn das Backend nicht erreichbar ist: dann bleiben die Seiten ohne
    gebackenen Preis, statt dass der Lauf abbricht. Ein Ausfall wird aber in
    PREIS_FEHLER vermerkt - unbeaufsichtigt darf daraus kein Deploy werden.
    """
    q = urllib.parse.urlencode({"set_name": set_name})
    for _ in range(3):
        try:
            with urllib.request.urlopen(f"{BACKEND}/set-prices?{q}", timeout=90) as r:
                return json.loads(r.read().decode()).get("cards") or {}
        except Exception:
            time.sleep(2)
    print(f"      ! Preise fuer '{set_name}' nicht abrufbar - Seiten ohne Preis")
    PREIS_FEHLER.append(set_name)
    return {}


def preis_von(pdata):
    """Normalpreis aus einem /set-prices-Eintrag, oder None."""
    avg = (pdata or {}).get("avg")
    return avg if isinstance(avg, (int, float)) else None


def verlauf_kennzahlen(history):
    """-> (punkte, tief, hoch, veraenderung_prozent|None) aus der Preishistorie."""
    werte = [h["avg_price"] for h in (history or [])
             if isinstance(h.get("avg_price"), (int, float))]
    if not werte:
        return 0, None, None, None
    delta = None
    if len(werte) >= 2 and werte[0]:
        delta = (werte[-1] - werte[0]) / werte[0] * 100
    return len(werte), min(werte), max(werte), delta


def _kurzpreis(v):
    """Achsenbeschriftung: knapp halten, aber ohne den Wert zu verfaelschen.
    0.08 -> '0,08 €'   12.5 -> '12,50 €'   1550 -> '1.550 €'"""
    s = f"{v:,.0f}" if v >= 100 else f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _kurzdatum(iso):
    """'2026-08-04' -> '4.8.'  (Jahr weglassen, die Tabelle darunter hat es voll)"""
    try:
        _, m, t = str(iso).split("-")
        return f"{int(t)}.{int(m)}."
    except Exception:
        return str(iso)


def preischart(history, breite=640, hoehe=240):
    """Preisverlauf als Inline-SVG mit beschrifteten Achsen.

    Kein JavaScript, keine externe Bibliothek - der Graph steht im HTML und ist
    auch ohne JS sichtbar. Bewusst OHNE preserveAspectRatio="none": sonst wird das
    SVG in die Breite gezogen und die Beschriftungen werden mitverzerrt.
    """
    punkte = [(h["date"], h["avg_price"]) for h in (history or [])
              if isinstance(h.get("avg_price"), (int, float))]
    if len(punkte) < 2:
        return ""
    werte = [p[1] for p in punkte]
    lo, hi = min(werte), max(werte)
    # Etwas Luft nach oben und unten, damit die Linie nicht am Rand klebt.
    if hi == lo:
        lo, hi = lo * 0.9 or 0, (hi * 1.1) or 1
    else:
        luft = (hi - lo) * 0.12
        lo, hi = lo - luft, hi + luft
    spanne = (hi - lo) or 1

    li, re_, ob, un = 62, 16, 16, 34   # Platz links fuer Preise, unten fuer Daten
    pb, ph = breite - li - re_, hoehe - ob - un

    def _x(i):
        return li + i * pb / (len(punkte) - 1)

    def _y(v):
        return ob + ph - (v - lo) / spanne * ph

    # Y-Achse: drei Marken (unten / Mitte / oben)
    y_teile = []
    for anteil in (0, 0.5, 1):
        wert = lo + spanne * anteil
        y = _y(wert)
        y_teile.append(
            f'<line x1="{li}" y1="{y:.1f}" x2="{breite - re_}" y2="{y:.1f}" '
            f'stroke="#2E4A6A" stroke-width="1" />'
            f'<text x="{li - 8}" y="{y + 4:.1f}" text-anchor="end" class="kc-lab">'
            f'{e(_kurzpreis(wert))}</text>')

    # X-Achse: erster, mittlerer und letzter Messpunkt
    x_teile = []
    for i in dict.fromkeys([0, len(punkte) // 2, len(punkte) - 1]):
        x_teile.append(
            f'<text x="{_x(i):.1f}" y="{hoehe - 12}" text-anchor="middle" class="kc-lab">'
            f'{e(_kurzdatum(punkte[i][0]))}</text>')

    linie = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, v in enumerate(werte))
    flaeche = f"{li},{ob + ph} {linie} {breite - re_},{ob + ph}"
    # Jeder Messwert bekommt einen Punkt - so ist sichtbar, wie oft gemessen wurde.
    kreise = "".join(
        f'<circle cx="{_x(i):.1f}" cy="{_y(v):.1f}" r="3" fill="#F0B429">'
        f'<title>{e(datum_de(punkte[i][0]))}: {e(euro(v))}</title></circle>'
        for i, v in enumerate(werte))

    return (
        f'<svg class="kchart" viewBox="0 0 {breite} {hoehe}" role="img" '
        f'aria-label="Preisverlauf vom {e(datum_de(punkte[0][0]))} bis '
        f'{e(datum_de(punkte[-1][0]))}, zwischen {e(euro(min(werte)))} und {e(euro(max(werte)))}">'
        + "".join(y_teile)
        + f'<polygon points="{flaeche}" fill="rgba(240,180,41,.14)" />'
        f'<polyline points="{linie}" fill="none" stroke="#F0B429" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round" />'
        + kreise + "".join(x_teile) + "</svg>")


# ── Werbung (Side-Rails) ─────────────────────────────────────────────────────
# Web-Ads laufen ueber Google AdSense (NICHT AdMob – das ist app-only). Sobald die
# Seite live UND von AdSense freigegeben ist, hier IDs eintragen -> echte Anzeigen
# statt Platzhalter-Box. Leer lassen = Platzhalter.
ADSENSE_CLIENT = "ca-pub-8432575775521548"  # Publisher-ID (AdMob+AdSense, ca-pub- fuers Web)
ADSENSE_SLOT_LEFT = ""   # Ad-Unit-ID linker Rail – erst NACH AdSense-Freigabe anlegen
ADSENSE_SLOT_RIGHT = ""  # Ad-Unit-ID rechter Rail – erst NACH AdSense-Freigabe anlegen


def ad_head():
    """AdSense-Loader fuer den <head> (nur wenn konfiguriert)."""
    if ADSENSE_CLIENT:
        return ('<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
                f'?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>')
    return ""


def ad_rail(slot_id, seite):
    """Anzeigen-Spalte (160x600 Wide Skyscraper) - oder GAR NICHTS.

    Frueher stand hier ohne konfigurierten Slot ein leerer grauer Kasten mit der
    Aufschrift "Werbung". Das rahmte jede der 19.000 Seiten mit zwei leeren
    Werbeflaechen ein und liess sie wie eine fuer Anzeigen gebaute Seite aussehen -
    genau der Eindruck, den die AdSense-Beanstandung "minderwertige Inhalte"
    beschreibt. Ohne Slot wird die Spalte jetzt weggelassen, der Inhalt bekommt
    den Platz.
    """
    if not (ADSENSE_CLIENT and slot_id):
        return ""
    return (f'<aside class="kad kad-{seite}"><span class="kad-tag">Anzeige</span>'
            f'<ins class="adsbygoogle" style="display:block;width:160px;height:600px" '
            f'data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{slot_id}"></ins>'
            f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></aside>')


# ── HTML-Bausteine ───────────────────────────────────────────────────────────
def head(title, desc, canonical, og_image=None, noindex=False):
    og = f'<meta property="og:image" content="{e(og_image)}" />' if og_image else ""
    # noindex fuer Karten, zu denen wir gar nichts wissen (kein Preis, kein Verlauf,
    # keine Variante). Solche Seiten haetten ausser Name und Bild keinen Inhalt und
    # zaehlen bei Google als minderwertig - sie sollen den Rest nicht mit runterziehen.
    robots = '<meta name="robots" content="noindex,follow" />' if noindex else ""
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}" />{robots}
<link rel="canonical" href="{e(canonical)}" />
<meta property="og:type" content="website" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(desc)}" />
<meta property="og:locale" content="de_DE" />{og}
<link rel="stylesheet" href="/karten/katalog.css?v=5" />{ad_head()}
<link rel="icon" href="/favicon.ico" sizes="any" /><link rel="icon" type="image/png" href="/favicon.png" sizes="192x192" /><link rel="apple-touch-icon" href="/apple-touch-icon.png" />
</head>
<body>
<nav class="kn"><a href="/" class="kn-logo">Poké<span>Track</span></a>
<div class="kn-links"><a href="/karten/">Katalog</a><a href="/magazin/">Magazin</a><a href="{APPSTORE}" class="kn-cta">App laden</a></div></nav>
<div class="kpage">{ad_rail(ADSENSE_SLOT_LEFT, "left")}
"""


FOOT = f"""{ad_rail(ADSENSE_SLOT_RIGHT, "right")}</div>
<footer class="kf">
<p>PokéTrack ist keine offizielle Pokémon-App und steht in keiner Verbindung zu Nintendo, The Pokémon Company International Inc., Creatures Inc. oder GAME FREAK inc. Alle Rechte an „Pokémon" gehören © 1995–2026 The Pokémon Company International Inc. / Nintendo / Creatures Inc. / GAME FREAK inc.</p>
<p><a href="/karten/">Alle Sets</a> · <a href="/datenschutz.html">Datenschutz</a> · <a href="/impressum.html">Impressum</a></p>
</footer></body></html>"""


def breadcrumb(items):
    # items: list of (label, href or None)
    parts = []
    for label, href in items:
        if href:
            parts.append(f'<a href="{e(href)}">{e(label)}</a>')
        else:
            parts.append(f"<span>{e(label)}</span>")
    return '<div class="kbc">' + " › ".join(parts) + "</div>"


def card_url(set_name, c):
    # _url wird in main() eindeutig vergeben (Kollisions-Suffix bei ???-Nummern)
    return c.get("_url") or f"/karten/{slug(set_name)}/{num_slug(c['nummer'])}-{slug(c['name'])}/"


# ── Seiten ───────────────────────────────────────────────────────────────────
def verlauf_rumpf(history, caption):
    """Text + Chart + Kennzahlen + Tabelle EINER Zeitreihe.

    Ausgelagert, weil es die Reihe inzwischen mehrfach je Karte gibt: Normalpreis,
    Reverse Holo und ggf. Pokeball/Masterball/Energie. Gibt "" zurueck, wenn die
    Reihe zu kurz fuer eine Aussage ist (< 2 Messpunkte).
    """
    n_punkte, tief, hoch, delta = verlauf_kennzahlen(history)
    if n_punkte < 2:
        return ""
    # ALLE Messwerte, nicht nur die letzten zehn - sie stecken im Aufklapper und
    # stoeren die Optik nicht mehr.
    zeilen = "".join(
        f"<tr><td>{e(datum_de(h['date']))}</td><td>{euro(h['avg_price'])}</td></tr>"
        for h in reversed(history)
        if isinstance(h.get("avg_price"), (int, float)))
    if delta is None or abs(delta) < 0.5:
        trend = "in diesem Zeitraum nahezu unverändert geblieben"
    else:
        prozent = f"{abs(delta):.1f}".replace(".", ",")
        trend = (f"in diesem Zeitraum um {prozent} % "
                 f"{'gestiegen' if delta > 0 else 'gefallen'}")
    text = (f"Seit dem {datum_de(history[0]['date'])} wurden {n_punkte} Tagespreise "
            f"erfasst. Der Preis lag zwischen {euro(tief)} und {euro(hoch)} und ist "
            f"{trend}.")
    aktuell = history[-1]["avg_price"]
    if delta is None or abs(delta) < 0.5:
        d_text, d_klasse = "±0 %", ""
    else:
        d_text = f"{'+' if delta > 0 else '−'}{abs(delta):.1f}".replace(".", ",") + " %"
        d_klasse = " kv-up" if delta > 0 else " kv-down"
    kennzahlen = (
        '<div class="kv-zahlen">'
        f'<div class="kv-z"><span>Aktuell</span><b>{euro(aktuell)}</b></div>'
        f'<div class="kv-z"><span>Tiefstand</span><b>{euro(tief)}</b></div>'
        f'<div class="kv-z"><span>Höchststand</span><b>{euro(hoch)}</b></div>'
        f'<div class="kv-z"><span>Veränderung</span><b class="{d_klasse.strip()}">{d_text}</b></div>'
        '</div>')
    return f"""<p class="kv-text">{text}</p>
  {preischart(history)}
  {kennzahlen}
  <details class="kv-details">
    <summary>Alle {n_punkte} erfassten Tagespreise anzeigen</summary>
    <table class="kv-tab">
      <caption>{e(caption)}</caption>
      <thead><tr><th>Datum</th><th>Preis</th></tr></thead>
      <tbody>{zeilen}</tbody>
    </table>
  </details>"""


def render_card(set_name, c, prev_c=None, next_c=None, set_reverse_types=None,
                pdata=None, set_info=None):
    name = c["name"]
    nummer = c["nummer"]
    nummer_disp = fmt_num(nummer, set_name)  # Anzeige-Nummer wie in der App
    canonical = BASE + card_url(set_name, c)
    img = c.get("bild_url") or ""
    rarity = c.get("seltenheit") or ""
    vp = c.get("variant_preise") or {}

    normal = preis_von(pdata)
    history = (pdata or {}).get("history") or []
    stand = (pdata or {}).get("stand")
    n_punkte, tief, hoch, delta = verlauf_kennzahlen(history)

    title = f"{name} {nummer_disp} – {set_name} | Wert & Preis | PokéTrack"
    if normal is not None:
        desc = (f"{name} ({nummer_disp}) aus {set_name} kostet aktuell {euro(normal)} "
                f"(Cardmarket, deutsch, Near Mint). Preisverlauf, Reverse-Varianten "
                f"und Seltenheit im Ueberblick.")
    else:
        desc = (f"{name} ({nummer_disp}) aus {set_name}: Seltenheit, Varianten und "
                f"Preisentwicklung. Sammlung verwalten mit PokéTrack.")

    # Reverse-Varianten wie in der App: aus reverse_typ + Set-reverseTypes ableiten.
    # Jede Variante zeigt den gescrapten variant_preise-Preis ODER faellt (client-
    # seitig) auf den Normalpreis zurueck – genau wie die App.
    variant_rows = ""
    fb_ids = []       # Varianten ohne eigenen Preis -> per JS, NUR wenn auch der
                      # Normalpreis fehlt (sonst backen wir ihn unten direkt ein).
    variant_fakten = []  # (Label, Preis, Angebote, Kondition) fuer den Faktenblock
    for vk in card_reverse_variants(c, set_reverse_types):
        label = VARIANT_NAME.get(vk, "Reverse")
        vpr = vp.get(vk) or {}
        if isinstance(vpr.get("preis"), (int, float)):
            variant_rows += (f'<div class="kp-row"><span>{e(label)}</span>'
                             f'<b>{euro(vpr["preis"])}</b></div>')
            variant_fakten.append((label, vpr["preis"], vpr.get("angebote"), vpr.get("kondition")))
        elif normal is not None:
            # Kein eigener Reverse-Preis -> Naeherung ueber den Normalpreis. Frueher
            # stand hier "lädt…" und der Wert kam per JS; damit sah Google auf JEDER
            # Seite eine leere Preiszeile. Jetzt steht die Zahl im HTML.
            variant_rows += (f'<div class="kp-row"><span>{e(label)}</span>'
                             f'<b>{euro(normal)}</b> <span class="kp-hint">≈ Normalpreis</span></div>')
        else:
            vid = "kpv-" + vk
            fb_ids.append(vid)
            variant_rows += (f'<div class="kp-row"><span>{e(label)}</span>'
                             f'<b><span id="{vid}">lädt…</span></b></div>')

    rarity_badge = f'<span class="kbadge">{e(rarity)}</span>' if rarity else ""
    typ_de = TYPE_DE.get(c.get("typ") or "")
    type_tag = (f'<span class="ktype" style="color:{TYPE_COLOR.get(typ_de, "#8A9EB8")}">{e(typ_de)}</span>'
                if typ_de else "")
    img_tag = (f'<img src="{e(img)}" alt="{e(name)} {e(nummer_disp)} {e(set_name)}" '
               f'width="300" height="418" loading="lazy" />') if img else ""

    # "Mehr Karten von <Name>" – gleiche Karte in anderen Sets (set-uebergreifend)
    more = [(sn, cc) for sn, cc in NAME_INDEX.get(name, [])
            if not (sn == set_name and cc["nummer"] == nummer)]
    more_section = ""
    if more:
        mtiles = ""
        for sn, cc in more[:MORE_LIMIT]:
            img2 = cc.get("bild_url") or ""
            it = (f'<img src="{e(img2)}" alt="{e(name)} – {e(sn)}" width="120" height="167" loading="lazy" />'
                  if img2 else '<div class="kt-noimg"></div>')
            mtiles += (f'<a class="ktile" href="{e(card_url(sn, cc))}">{it}'
                       f'<span class="kt-name">{e(sn)}</span>'
                       f'<span class="kt-num">{e(fmt_num(cc["nummer"], sn))}</span></a>')
        more_section = (f'<section class="kmore"><h2>Mehr Karten von {e(name)}</h2>'
                        f'<div class="kgrid">{mtiles}</div></section>')

    # ── Preisverlauf ────────────────────────────────────────────────────────
    # Graph als Inline-SVG UND als Tabelle. Die Tabelle ist der eigentliche Punkt:
    # Suchmaschinen lesen Text, keine Kurven - und datierte Messwerte sind Inhalt,
    # den es sonst nirgends gibt.
    # Eine Reihe je Variante mit eigener Zeitreihe. Der Reverse-Verlauf kommt seit
    # heute gebuendelt aus /set-prices mit ("variants") - vorher zeigte die Seite
    # bei einer Reverse-Karte den Normalpreis-Verlauf, was bei Karten wie
    # EX Smaragd 70/106 (0,19 EUR normal, 200 EUR reverse) grob irrefuehrend war.
    reihen = []
    rumpf_normal = verlauf_rumpf(history, "Cardmarket, deutsch, Zustand Near Mint")
    if rumpf_normal:
        reihen.append(("Normal", rumpf_normal))
    vhist = (pdata or {}).get("variants") or {}
    for vk in card_reverse_variants(c, set_reverse_types):
        vlabel = VARIANT_NAME.get(vk, "Reverse")
        rumpf = verlauf_rumpf(vhist.get(vk) or [], f"Cardmarket, deutsch, {vlabel}")
        if rumpf:
            reihen.append((vlabel, rumpf))
    # Das CSS deckt kv-p0 bis kv-p4 ab. Aktuell hat kein Set mehr als drei
    # Reverse-Varianten (also hoechstens vier Reihen), aber lieber abschneiden
    # als ein Panel bauen, das sich nicht einblenden laesst.
    reihen = reihen[:5]

    verlauf_block = ""
    if len(reihen) == 1:
        verlauf_block = f"""
<section class="kverlauf">
  <h2>Preisentwicklung von {e(name)} {e(nummer_disp)}</h2>
  {reihen[0][1]}
</section>"""
    elif reihen:
        # Umschalter ohne JavaScript: versteckte Radios, die per :checked das
        # zugehoerige Panel einblenden. Die Panels bleiben dabei im HTML stehen -
        # Suchmaschinen lesen also alle Tabellen, nicht nur die sichtbare.
        radios = "".join(
            f'<input class="kv-radio kv-r{i}" type="radio" name="kvtab" '
            f'id="kv-{i}"{" checked" if i == 0 else ""}>'
            for i, _ in enumerate(reihen))
        labels = "".join(f'<label for="kv-{i}">{e(lbl)}</label>'
                         for i, (lbl, _) in enumerate(reihen))
        panels = "".join(f'<div class="kv-panel kv-p{i}">{rumpf}</div>'
                         for i, (_, rumpf) in enumerate(reihen))
        verlauf_block = f"""
<section class="kverlauf kv-tabbed">
  <h2>Preisentwicklung von {e(name)} {e(nummer_disp)}</h2>
  {radios}
  <div class="kv-leiste">{labels}</div>
  <div class="kv-panels">{panels}</div>
</section>"""

    # ── Faktenblock ─────────────────────────────────────────────────────────
    fakten = [("Set", set_name), ("Kartennummer", nummer_disp)]
    if rarity:
        fakten.append(("Seltenheit", rarity))
    if typ_de:
        fakten.append(("Kartentyp", typ_de))
    if set_info and set_info.get("anzahl"):
        fakten.append(("Karten im Set", f"{set_info['anzahl']}"))
    if set_info and set_info.get("era"):
        fakten.append(("Ära", set_info["era"]))
    if normal is not None:
        fakten.append(("Günstigstes Angebot", f"{euro(normal)} (Near Mint, deutsch)"))
    for label, preis, angebote, kondition in variant_fakten:
        wert = euro(preis)
        zusatz = []
        if angebote:
            zusatz.append(f"{angebote} Angebot{'e' if angebote != 1 else ''}")
        if kondition:
            zusatz.append(f"Zustand {KONDITION_DE.get(str(kondition).lower(), kondition)}")
        if zusatz:
            wert += " (" + ", ".join(zusatz) + ")"
        fakten.append((label, wert))
    if stand:
        fakten.append(("Preisstand", datum_de(stand)))
    fakten_block = (
        '<section class="kfakten"><h2>Kartendaten im Überblick</h2><dl>'
        + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in fakten)
        + "</dl></section>")

    # Ohne Preis, ohne Verlauf und ohne Variantenpreis bliebe nur Name + Bild uebrig.
    leer = normal is None and n_punkte == 0 and not variant_fakten

    # Client-seitiger Preis-Abruf - nur noch als Notnagel fuer Karten ohne
    # gebackenen Preis. Bei allen anderen steht der Wert jetzt im HTML.
    price_js = "" if normal is not None else f"""<script>
(function(){{
  var fb={json.dumps(fb_ids)};
  var setFb=function(t){{fb.forEach(function(id){{var x=document.getElementById(id);if(x)x.textContent=t;}});}};
  var q=new URLSearchParams({{name:{json.dumps(name)},number:{json.dumps(nummer)},set_name:{json.dumps(set_name)}}});
  fetch({json.dumps(BACKEND)}+"/price?"+q).then(function(r){{return r.json();}}).then(function(d){{
    var el=document.getElementById("kprice");
    if(d&&typeof d.avg==="number"){{
      var s=d.avg.toLocaleString("de-DE",{{minimumFractionDigits:2,maximumFractionDigits:2}})+" €";
      el.textContent=s; setFb(s);
    }}else{{el.textContent="Derzeit kein Angebot";el.classList.add("kp-none");setFb("—");}}
  }}).catch(function(){{document.getElementById("kprice").textContent="—";setFb("—");}});
}})();
</script>"""

    # Prev/Next innerhalb des Sets (Reihenfolge = db.json-Liste)
    def _cnav(cc, direction):
        if not cc:
            return '<span class="kcnav-empty"></span>'
        arrow_l = "‹ " if direction == "prev" else ""
        arrow_r = " ›" if direction == "next" else ""
        return (f'<a class="kcnav-link kcnav-{direction}" rel="{direction}" '
                f'href="{e(card_url(set_name, cc))}">{arrow_l}{e(cc["name"])} '
                f'{e(fmt_num(cc["nummer"], set_name))}{arrow_r}</a>')
    card_nav = (f'<nav class="kcnav" aria-label="Karten-Navigation">'
                f'{_cnav(prev_c, "prev")}{_cnav(next_c, "next")}</nav>')

    preis_zelle = (f'<b id="kprice">{euro(normal)}</b>' if normal is not None
                   else '<b id="kprice">lädt…</b>')

    return head(title, desc, canonical, img, noindex=leer) + f"""
<main class="kwrap">
{breadcrumb([("Katalog", "/karten/"), (set_name, f"/karten/{slug(set_name)}/"), (f"{name} {nummer_disp}", None)])}
{card_nav}
<div class="kcard">
  <div class="kcard-img">{img_tag}</div>
  <div class="kcard-info">
    <h1>{e(name)} {e(nummer_disp)}</h1>
    <div class="ktags">{rarity_badge}{type_tag}</div>
    <p class="ksub">{e(set_name)} · Nr. {e(nummer_disp)}</p>
    <div class="kprice-box">
      <div class="kp-row"><span>Referenzpreis (Cardmarket, Normal)</span>{preis_zelle}</div>
      {variant_rows}
    </div>
    <p class="knote">Preise sind Cardmarket-Niedrigpreise (Near Mint, deutsch) und dienen als Orientierung.</p>
    <a class="kappbtn" href="{APPSTORE}">In der PokéTrack-App öffnen →</a>
  </div>
</div>
{verlauf_block}
{fakten_block}
{more_section}
</main>
{price_js}
{FOOT}"""


def render_set(set_name, cards, total=None, priced=0, reverse_total=None, reverse_priced=0):
    canonical = BASE + f"/karten/{slug(set_name)}/"
    title = f"{set_name} – alle Karten & Preise | PokéTrack"
    desc = (f"Alle {len(cards)} Karten aus dem Set {set_name} mit aktuellen Cardmarket-Preisen "
            f"(deutsch, Near Mint). Sammlung tracken mit PokéTrack.")
    total = total or 0
    reverse_total = reverse_total or 0
    total_box = ""
    if reverse_total > 0:
        # Set hat Reverse-Karten -> Aufschluesselung Normal / Reverse / Gesamt
        total_box = (
            f'<div class="ktotal">'
            f'<span class="ktotal-label">Gesamtwert des Sets</span>'
            f'<div class="ktotal-rows">'
            f'<div class="ktotal-line"><span>Normal</span><b>{euro(total)}</b></div>'
            f'<div class="ktotal-line"><span>Reverse Holo</span><b>{euro(reverse_total)}</b></div>'
            f'<div class="ktotal-line ktotal-sum"><span>Gesamt</span><b>{euro(total + reverse_total)}</b></div>'
            f'</div>'
            f'<span class="ktotal-note">Normal: {priced} von {len(cards)} Karten · '
            f'Reverse Holo: {reverse_priced} Karten · '
            f'Cardmarket, deutsch, Near Mint.</span></div>')
    elif total > 0:
        # Set ohne Reverse (z.B. Vintage-Basissets) -> nur ein Gesamtwert
        total_box = (
            f'<div class="ktotal">'
            f'<span class="ktotal-label">Gesamtwert des Sets</span>'
            f'<span class="ktotal-value">{euro(total)}</span>'
            f'<span class="ktotal-note">Summe der günstigsten Near-Mint-Preise (Cardmarket, deutsch) '
            f'von {priced} der {len(cards)} Karten</span></div>')
    tiles = ""
    for c in cards:
        img = c.get("bild_url") or ""
        it = (f'<img src="{e(img)}" alt="{e(c["name"])}" width="120" height="167" loading="lazy" />'
              if img else '<div class="kt-noimg"></div>')
        tiles += (f'<a class="ktile" href="{e(card_url(set_name, c))}">{it}'
                  f'<span class="kt-name">{e(c["name"])}</span>'
                  f'<span class="kt-num">{e(fmt_num(c["nummer"], set_name))}</span></a>')
    # Kurzer Einordnungstext aus den Daten des Sets - kein Fuelltext, sondern das,
    # was ein Sammler wissen will: Umfang, Seltenheitsverteilung, Reverse, Wert.
    selten = {}
    for c in cards:
        s = c.get("seltenheit")
        if s:
            selten[s] = selten.get(s, 0) + 1
    top_selten = sorted(selten.items(), key=lambda x: -x[1])[:4]
    n_rev = sum(1 for c in cards if c.get("has_reverse") or c.get("hat_reverse"))
    saetze = [f"Das Set {e(set_name)} umfasst {len(cards)} Karten."]
    if top_selten:
        saetze.append("Am häufigsten vertreten sind "
                      + ", ".join(f"{e(s)} ({n})" for s, n in top_selten) + ".")
    if n_rev:
        saetze.append(f"Von {n_rev} Karten existiert zusätzlich eine Reverse-Holo-Variante, "
                      f"die separat bepreist wird.")
    if priced:
        saetze.append(f"Für {priced} der {len(cards)} Karten liegt ein aktueller "
                      f"Cardmarket-Preis vor; die Summe ergibt {euro(total)}.")
    intro = ('<section class="kintro"><h2>Über dieses Set</h2><p>'
             + " ".join(saetze) + "</p><p>Alle Preise sind die günstigsten deutschen "
             "Angebote in Zustand Near Mint und werden täglich aktualisiert. Ein Klick "
             "auf eine Karte zeigt ihren Preisverlauf.</p></section>")

    return head(title, desc, canonical) + f"""
<main class="kwrap">
{breadcrumb([("Katalog", "/karten/"), (set_name, None)])}
<h1 class="kh1">{e(set_name)}</h1>
<p class="ksub">{len(cards)} Karten · Preise von Cardmarket (deutsch, Near Mint)</p>
{total_box}
{intro}
<div class="kgrid">{tiles}</div>
</main>
{FOOT}"""


def render_index(sets_items, set_meta, era_order):
    canonical = BASE + "/karten/"
    title = "Pokémon-Karten-Katalog (deutsch) – alle Sets & Preise | PokéTrack"
    desc = ("Durchsuche alle deutschen Pokémon-Sets mit aktuellen Cardmarket-Preisen. "
            "Über 18.000 Karten, 135 Sets. Sammlung & Werte tracken mit der PokéTrack-App.")

    # Nach Aera gruppieren, db.json-Reihenfolge der Sets beibehalten
    by_era = {}
    for set_name, cards in sets_items:
        era = _meta(set_meta, set_name).get("era", "Weitere Sets")
        by_era.setdefault(era, []).append((set_name, cards))
    ordered = [x for x in era_order if x in by_era] + [x for x in by_era if x not in era_order]

    sections = ""
    for era in ordered:
        tiles = ""
        for set_name, cards in by_era[era]:
            logo = _meta(set_meta, set_name).get("logo")
            if logo:
                inner = f'<img src="{e(logo)}" alt="{e(set_name)} Logo" loading="lazy" />'
                meta_line = f"{e(set_name)} · {len(cards)} Karten"
            else:
                inner = f'<span class="kset-fallback">{e(set_name)}</span>'
                meta_line = f"{len(cards)} Karten"
            tiles += (f'<a class="kset" href="/karten/{slug(set_name)}/">'
                      f'<div class="kset-logo">{inner}</div>'
                      f'<span class="kset-meta">{meta_line}</span></a>')
        sections += (f'<section class="kera"><h2 class="kera-h">{FLAG_DE} {e(era)}</h2>'
                     f'<div class="ksetgrid">{tiles}</div></section>')

    n_karten = f"{sum(len(c) for _, c in sets_items):,}".replace(",", ".")
    intro = f"""<section class="kintro">
<h2>Was dieser Katalog enthält</h2>
<p>Hier sind {n_karten} Karten aus {len(sets_items)} auf Deutsch erschienenen
Pokémon-Sets erfasst — von der Basisserie aus dem Jahr 1999 bis zu den aktuellen
Erweiterungen. Zu jeder Karte findest du die Kartennummer, die Seltenheit, den
Kartentyp und den günstigsten deutschen Cardmarket-Preis in Zustand Near Mint.</p>
<p>Die Preise stammen aus einem täglichen Abgleich mit Cardmarket. Wo eine Karte
zusätzlich als Reverse Holo existiert — oder in Sonderformen wie Pokéball- und
Masterball-Muster — wird diese Variante getrennt bepreist, weil sich ihr Wert
deutlich vom normalen Druck unterscheiden kann. Für jede Karte zeichnen wir
außerdem den Preisverlauf auf, sodass sichtbar wird, ob ein Wert steigt oder
fällt.</p>
<p>Der Katalog ist die offene Fassung der PokéTrack-App, mit der du deine eigene
Sammlung verwalten und ihren Wert verfolgen kannst.</p>
</section>"""

    return head(title, desc, canonical) + f"""
<main class="kwrap">
<h1 class="kh1">Pokémon-Karten-Katalog {FLAG_DE}</h1>
<p class="ksub">Alle {len(sets_items)} deutschen Sets mit aktuellen Cardmarket-Preisen — nach Ära sortiert wie in der App.</p>
{intro}
{sections}
</main>
{FOOT}"""


CSS = """/* PokéTrack Katalog – nutzt die Farben der Hauptseite */
:root{--primary:#1E3A5F;--dark:#0F1F33;--accent:#F0B429;--text:#E8EFF7;--muted:#8A9EB8;--surface:#162D4A;--border:#2E4A6A;--r:12px}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--dark);color:var(--text);line-height:1.6}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.kn{position:sticky;top:0;z-index:10;display:flex;justify-content:space-between;align-items:center;height:60px;padding:0 20px;background:rgba(15,31,51,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.kn-logo{font-weight:800;font-size:20px;color:var(--text)}.kn-logo span{color:var(--accent)}
.kn-links{display:flex;gap:16px;align-items:center}.kn-links a{color:var(--muted);font-size:14px;font-weight:600}
.kn-cta{background:var(--accent);color:var(--dark)!important;padding:6px 14px;border-radius:100px}
.kwrap{max-width:1000px;margin:0 auto;padding:24px 20px 60px}
/* Werbung: Side-Rails links/rechts, zentrierter Inhalt in der Mitte */
.kpage{display:flex;justify-content:center;align-items:flex-start;gap:28px;width:100%}
.kpage>.kwrap{flex:0 1 1000px;min-width:0;margin:0}
.kad{flex:0 0 160px;position:sticky;top:80px;align-self:flex-start;display:flex;flex-direction:column;align-items:center;gap:4px;padding-top:24px}
.kad-box{width:160px;height:600px;background:var(--surface);border:1px dashed var(--border);border-radius:var(--r);display:flex;align-items:center;justify-content:center}
.kad-tag{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:1.5px}
@media(max-width:1400px){.kad{display:none}}
.kbc{font-size:13px;color:var(--muted);margin-bottom:20px}.kbc a{color:var(--muted)}.kbc span{color:var(--text)}
/* Prev/Next-Kartennavigation */
.kcnav{display:flex;justify-content:space-between;gap:12px;margin:0 0 20px}
.kcnav-empty{flex:1}
.kcnav-link{flex:1;min-width:0;display:flex;align-items:center;gap:4px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:600;color:var(--text);overflow:hidden;white-space:nowrap;text-overflow:ellipsis;transition:border-color .15s}
.kcnav-link:hover{border-color:var(--accent);text-decoration:none}
.kcnav-prev{justify-content:flex-start}
.kcnav-next{justify-content:flex-end;text-align:right}
.kh1{font-size:clamp(24px,4vw,34px);font-weight:800;letter-spacing:-.5px}
.ksub{color:var(--muted);margin:6px 0 24px}
.ktotal{display:flex;flex-direction:column;gap:3px;background:rgba(240,180,41,.10);border:1px solid rgba(240,180,41,.45);border-radius:var(--r);padding:16px 20px;margin:0 0 26px}
.ktotal-label{font-size:11px;text-transform:uppercase;letter-spacing:1.2px;font-weight:700;color:var(--muted)}
.ktotal-value{font-size:30px;font-weight:800;color:var(--accent);line-height:1.1}
.ktotal-note{font-size:12px;color:var(--muted)}
.ktotal-rows{display:flex;flex-direction:column;gap:5px;margin:2px 0 4px}
.ktotal-line{display:flex;justify-content:space-between;align-items:baseline;gap:16px}
.ktotal-line span{font-size:14px;color:var(--muted)}
.ktotal-line b{font-size:19px;font-weight:700;color:var(--text);font-variant-numeric:tabular-nums}
.ktotal-sum{border-top:1px solid rgba(240,180,41,.35);padding-top:7px;margin-top:2px}
.ktotal-sum span{color:var(--text);font-weight:700;font-size:15px}
.ktotal-sum b{font-size:26px;font-weight:800;color:var(--accent)}
/* Index: Sets nach Aera gruppiert, mit Logos */
.kera{margin-bottom:44px}
.kera-h{font-size:14px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;color:var(--text);margin-bottom:18px;border-bottom:1px solid var(--border);padding-bottom:10px;display:flex;align-items:center;gap:8px}
.kflag{height:0.72em;width:auto;border-radius:2px;vertical-align:baseline;box-shadow:0 0 0 1px rgba(255,255,255,.18)}
.ksetgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}
.kset{display:flex;flex-direction:column;align-items:center;text-align:center;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:18px 14px 14px}
.kset:hover{border-color:var(--accent);transform:translateY(-3px);text-decoration:none;transition:.15s}
.kset-logo{height:72px;width:100%;display:flex;align-items:center;justify-content:center;margin-bottom:12px}
.kset-logo img{max-height:72px;max-width:92%;object-fit:contain}
.kset-fallback{font-weight:800;color:var(--text);font-size:16px;line-height:1.2}
.kset-meta{font-size:12px;color:var(--muted);font-weight:600;line-height:1.35}
/* Set-Seite: Karten-Grid */
.kgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:18px}
@media(max-width:700px){.kgrid{grid-template-columns:repeat(3,1fr);gap:12px}}
@media(max-width:430px){.kgrid{grid-template-columns:repeat(2,1fr)}}
.ktile{display:flex;flex-direction:column;align-items:center;text-align:center;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:10px}
.ktile:hover{border-color:var(--accent);transform:translateY(-2px);text-decoration:none;transition:.15s}
.ktile img{width:100%;height:auto;border-radius:6px}
.kt-noimg{width:100%;aspect-ratio:5/7;background:var(--border);border-radius:6px}
.kt-name{font-size:12px;font-weight:600;color:var(--text);margin-top:6px;line-height:1.25}.kt-num{font-size:11px;color:var(--muted)}
.kmore{margin-top:40px}.kmore h2{font-size:20px;font-weight:800;margin-bottom:16px}
/* Karten-Detail */
.kcard{display:flex;gap:28px;flex-wrap:wrap;background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:24px}
.kcard-img{flex:0 0 300px;max-width:100%}.kcard-img img{width:100%;height:auto;border-radius:12px}
.kcard-info{flex:1;min-width:260px}
.kcard-info h1{font-size:26px;font-weight:800;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.kbadge{background:var(--accent);color:var(--dark);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;padding:4px 8px;border-radius:6px}
.ktags{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0}
.ktype{border:1px solid currentColor;border-radius:100px;padding:3px 12px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.kprice-box{margin:18px 0;border:1px solid var(--border);border-radius:12px;overflow:hidden}
.kp-row{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-top:1px solid var(--border)}
.kp-row:first-child{border-top:none}.kp-row span{color:var(--muted);font-size:14px}
.kp-row b{font-size:20px;font-weight:800;color:var(--accent)}.kp-none{color:var(--muted)!important;font-size:15px!important}
.kp-approx{font-size:12px;font-weight:600;color:var(--muted)}
.knote{font-size:12px;color:var(--muted);margin-bottom:18px}
.kappbtn{display:inline-block;background:var(--accent);color:var(--dark);font-weight:700;padding:12px 20px;border-radius:12px}
.kappbtn:hover{text-decoration:none;opacity:.9}
.kf{border-top:1px solid var(--border);padding:30px 20px;text-align:center;max-width:800px;margin:0 auto;color:var(--muted);font-size:12px}
.kf p{margin-bottom:8px}.kf a{color:var(--muted)}
/* Preisverlauf + Faktenblock */
.kverlauf,.kfakten,.kintro{margin-top:32px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:20px}
.kverlauf h2,.kfakten h2{font-size:18px;margin-bottom:10px}
.kv-text{color:var(--muted);font-size:14px;margin-bottom:14px}
.kchart{display:block;width:100%;height:auto;max-width:640px;margin:0 auto 16px}
.kc-lab{fill:#8A9EB8;font-size:13px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-variant-numeric:tabular-nums}
.kv-zahlen{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.kv-z{background:var(--surface);padding:10px 12px;display:flex;flex-direction:column;gap:2px}
.kv-z span{color:var(--muted);font-size:12px}
.kv-z b{font-size:16px;font-variant-numeric:tabular-nums}
.kv-up{color:#5FD38D}.kv-down{color:#F07A7A}
/* Varianten-Umschalter im Preisverlauf - reines CSS, kein JavaScript.
   Die Radios bleiben fokussierbar (nur transparent), damit der Umschalter
   auch per Tastatur bedienbar ist; display:none wuerde das kaputt machen. */
.kv-radio{position:absolute;opacity:0;width:0;height:0}
.kv-leiste{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
.kv-leiste label{cursor:pointer;padding:6px 14px;border:1px solid var(--border);border-radius:999px;font-size:13px;font-weight:600;color:var(--muted);background:var(--dark);user-select:none}
.kv-leiste label:hover{color:var(--text)}
.kv-panel{display:none}
.kv-r0:checked~.kv-panels>.kv-p0,.kv-r1:checked~.kv-panels>.kv-p1,
.kv-r2:checked~.kv-panels>.kv-p2,.kv-r3:checked~.kv-panels>.kv-p3,
.kv-r4:checked~.kv-panels>.kv-p4{display:block}
.kv-r0:checked~.kv-leiste label[for="kv-0"],.kv-r1:checked~.kv-leiste label[for="kv-1"],
.kv-r2:checked~.kv-leiste label[for="kv-2"],.kv-r3:checked~.kv-leiste label[for="kv-3"],
.kv-r4:checked~.kv-leiste label[for="kv-4"]{background:var(--accent);border-color:var(--accent);color:#0B1220}
.kv-r0:focus-visible~.kv-leiste label[for="kv-0"],.kv-r1:focus-visible~.kv-leiste label[for="kv-1"],
.kv-r2:focus-visible~.kv-leiste label[for="kv-2"],.kv-r3:focus-visible~.kv-leiste label[for="kv-3"],
.kv-r4:focus-visible~.kv-leiste label[for="kv-4"]{outline:2px solid var(--accent);outline-offset:2px}
.kv-details{margin-top:14px}
.kv-details summary{cursor:pointer;color:var(--accent);font-size:14px;font-weight:600;padding:6px 0;list-style-position:inside}
.kv-details summary:hover{text-decoration:underline}
.kv-details[open] summary{margin-bottom:6px}
.kv-tab{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
.kv-tab caption{caption-side:top;text-align:left;color:var(--muted);font-size:12px;padding-bottom:8px}
.kv-tab th,.kv-tab td{padding:6px 8px;border-bottom:1px solid var(--border);text-align:left}
.kv-tab th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.kv-tab td:last-child,.kv-tab th:last-child{text-align:right}
.kfakten dl{display:grid;grid-template-columns:minmax(120px,auto) 1fr;gap:8px 20px;font-size:14px}
.kfakten dt{color:var(--muted)}.kfakten dd{font-weight:600}
.kp-hint{color:var(--muted);font-size:12px;font-weight:400;margin-left:4px}
.kintro p{color:var(--muted);font-size:14px}.kintro p+p{margin-top:10px}
.kintro h2{font-size:18px;margin-bottom:10px;color:var(--text)}
@media(max-width:560px){.kcard-img{flex-basis:100%}.kfakten dl{grid-template-columns:1fr;gap:2px 0}.kfakten dd{margin-bottom:8px}.kv-zahlen{grid-template-columns:repeat(2,1fr)}}
"""


_CHANGED = set()  # relative Pfade, deren Inhalt sich ggue. dem deployten Stand geaendert hat


ARTIKEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artikel")

DATUM_LANG = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]


def artikel_bauen(sterne, reverse_daten):
    """Schreibt die Magazin-Artikel mit den Preisen des heutigen Laufs.

    Der Prosatext steht in tools/artikel/ und ist handgeschrieben; ersetzt werden
    nur die {{PLATZHALTER}} - Galerie, Tabellen, Kennzahlen, Datum.

    Faellt die Preisabfrage aus, bleibt die bereits veroeffentlichte Datei stehen,
    statt mit leeren Tabellen ueberschrieben zu werden: Ein Artikel mit gestrigen
    Preisen ist deutlich besser als einer ohne.
    """
    heute = datetime.date.today()
    stand = f"{heute.day}. {DATUM_LANG[heute.month]} {heute.year}"

    # ── Gold Stars ──────────────────────────────────────────────────────────
    mit_preis = [s for s in sterne if s["preis"]]
    if len(mit_preis) < 10:
        print(f"  ⚠ Artikel Gold Stars uebersprungen: nur {len(mit_preis)} Preise")
    else:
        sortiert = sorted(sterne, key=lambda s: -(s["preis"] or 0))
        karten = "\n".join(
            f'  <figure class="gs-karte">\n'
            f'    <img src="{e(s["bild"])}" alt="{e(s["name"])} ☆ {e(s["nummer"])} aus {e(s["set"])}"'
            f' loading="lazy" width="245" height="342">\n'
            f'    <figcaption>\n'
            f'      <b><a href="{e(s["url"])}">{e(s["name"])} ☆</a></b>\n'
            f'      <span>{e(s["set"])} · {e(s["nummer"])}</span>\n'
            f'      <strong class="gs-preis">{euro(s["preis"]) if s["preis"] else "kein Angebot"}</strong>\n'
            f'    </figcaption>\n  </figure>' for s in sortiert)
        itemlist = json.dumps({
            "@context": "https://schema.org", "@type": "ItemList",
            "name": "Gold Stars der EX-Ära", "numberOfItems": len(sortiert),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": f'{s["name"]} ☆ ({s["set"]} {s["nummer"]})',
                 "url": s["url"]}
                for i, s in enumerate(sortiert)],
        }, ensure_ascii=False)

        ohne = [s for s in sortiert if not s["preis"]]
        if ohne:
            namen = ", ".join(f'{s["name"]} ☆ aus {s["set"]}' for s in ohne)
            titel = "Ohne Angebot" if len(ohne) > 1 else f'Ohne Angebot: {ohne[0]["name"]} ☆'
            text = (f"Für {namen} gibt es auf Cardmarket derzeit kein einziges deutsches "
                    f"Angebot. Das ist kein Datenfehler, sondern der Normalzustand bei "
                    f"Karten dieser Seltenheit: Es kommt vor, dass wochenlang kein "
                    f"Exemplar auf dem Markt ist.")
        else:
            titel = "Aktuell sind alle Sterne zu haben"
            text = ("Derzeit steht für jede Gold Star mindestens ein deutsches Angebot. "
                    "Das ist nicht selbstverständlich — bei Karten dieser Seltenheit "
                    "kommt es vor, dass einzelne wochenlang gar nicht handelbar sind.")

        # Beide aus der sortierten Liste: mit_preis steht in Quellreihenfolge,
        # dessen letzter Eintrag ist irgendeine Karte, nicht die guenstigste.
        bepreist = [s for s in sortiert if s["preis"]]
        teuerste, guenstigste = bepreist[0], bepreist[-1]
        artikel_schreiben("gold-stars-ex-aera.html", {
            "STAND": stand, "STAND_ISO": heute.isoformat(),
            "GS_ANZAHL": str(len(sortiert)),
            "GS_GALERIE": f'<div class="gs-galerie">\n{karten}\n</div>',
            "GS_ITEMLIST": itemlist,
            "GS_MAX_NAME": f'{teuerste["name"]} ☆',
            "GS_MAX_PREIS": euro(teuerste["preis"]),
            "GS_MAX_BILD": teuerste["bild"],
            "GS_MIN_NAME": f'{guenstigste["name"]} ☆',
            "GS_MIN_PREIS": euro(guenstigste["preis"]),
            "GS_OHNE_TITEL": titel, "GS_OHNE_TEXT": text,
        })

    # ── Reverse Holo ────────────────────────────────────────────────────────
    if len(reverse_daten) < 200:
        print(f"  ⚠ Artikel Reverse uebersprungen: nur {len(reverse_daten)} Preise")
        return

    preise = sorted(d["reverse"] for d in reverse_daten)
    median = preise[len(preise) // 2]
    unter5 = sum(1 for p in preise if p < 5)

    mit_verhaeltnis = sorted(
        (d for d in reverse_daten if d["normal"] and d["normal"] > 0),
        key=lambda d: -(d["reverse"] / d["normal"]))
    top = mit_verhaeltnis[:8]
    zeilen = "".join(
        f'<tr><td><span class="mini"><img src="{e(d["bild"])}" alt="{e(d["name"])} '
        f'{e(d["nummer"])} aus {e(d["set"])}" loading="lazy" width="44" height="61">'
        f'<a href="{e(d["url"])}">{e(d["name"])} {e(d["nummer"])}</a></span></td>'
        f'<td>{e(d["set"])}</td><td class="z">{euro(d["normal"])}</td>'
        f'<td class="z">{euro(d["reverse"])}</td>'
        f'<td class="z">{d["reverse"] / d["normal"]:.0f}×</td>'
        f'<td class="z">{d["angebote"] or "–"}</td></tr>' for d in top)
    abstaende = (
        '<div class="tabelle">\n<table>\n'
        f'<caption>Größte Preisabstände Reverse zu Normal, deutsche Karten, Stand {stand}</caption>\n'
        '<thead><tr><th>Karte</th><th>Set</th><th class="z">Normal</th>'
        '<th class="z">Reverse</th><th class="z">Faktor</th><th class="z">Angebote</th></tr></thead>\n'
        f'<tbody>{zeilen}</tbody>\n</table>\n</div>')

    je_set = {}
    for d in reverse_daten:
        je_set.setdefault(d["set"], []).append(d["reverse"])
    reihen = sorted(((s, len(v), sorted(v)[len(v) // 2], max(v))
                     for s, v in je_set.items()), key=lambda r: -r[2])
    mz = "".join(
        f'<tr><td><a href="/karten/{slug(s)}/">{e(s)}</a></td><td class="z">{n}</td>'
        f'<td class="z">{euro(med)}</td><td class="z">{euro(mx)}</td></tr>'
        for s, n, med, mx in reihen)
    mediane = (
        '<div class="tabelle">\n<table>\n'
        '<caption>Reverse-Preise je Set: Anzahl erfasster Karten, Median und Höchstwert</caption>\n'
        '<thead><tr><th>Set</th><th class="z">Karten</th><th class="z">Median</th>'
        '<th class="z">Maximum</th></tr></thead>\n'
        f'<tbody>{mz}</tbody>\n</table>\n</div>')

    spitze = mit_verhaeltnis[0]
    artikel_schreiben("reverse-holo-ex-aera.html", {
        "STAND": stand, "STAND_ISO": heute.isoformat(),
        "RV_ANZAHL": f"{len(reverse_daten):,}".replace(",", "."),
        "RV_SETS": str(len(je_set)),
        "RV_MEDIAN": euro(median), "RV_UNTER5": str(unter5),
        "RV_ABSTAENDE": abstaende, "RV_MEDIANE": mediane,
        "RV_TOP_NAME": spitze["name"], "RV_TOP_SET": spitze["set"],
        "RV_TOP_NORMAL": euro(spitze["normal"]), "RV_TOP_REVERSE": euro(spitze["reverse"]),
        "RV_TOP_BILD": spitze["bild"],
    })


def artikel_schreiben(datei, werte):
    pfad = os.path.join(ARTIKEL_DIR, datei)
    if not os.path.exists(pfad):
        print(f"  ⚠ Vorlage fehlt: {pfad}")
        return
    html = open(pfad, encoding="utf-8").read()
    for k, v in werte.items():
        html = html.replace("{{" + k + "}}", str(v))
    offen = re.findall(r"\{\{[A-Z_0-9]+\}\}", html)
    if offen:
        print(f"  ⚠ {datei}: unbefuellte Platzhalter {sorted(set(offen))} - nicht geschrieben")
        return
    write(f"magazin/{datei}", html)
    print(f"  Magazin: {datei} mit tagesaktuellen Preisen geschrieben")


def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    # Echte Inhaltsaenderung erkennen (LF-normalisiert, da Git-Checkout ggf. CRLF hat)
    # -> nur geaenderte Seiten bekommen spaeter ein neues <lastmod> in der Sitemap.
    old = None
    if os.path.exists(full):
        try:
            with open(full, encoding="utf-8") as f:
                old = f.read()
        except Exception:
            old = None
    if old is None or old.replace("\r\n", "\n") != content:
        _CHANGED.add(path)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main(only_set=None):
    with open(DB, encoding="utf-8-sig") as f:
        db = json.load(f)

    # Eindeutige URL je Karte VORHER vergeben (ueber ALLE Sets). Bei gleichem
    # Slug im selben Set (v.a. ???-Nummern) -> Zaehler-Suffix -2/-3. Stabil, damit
    # Writer und "Mehr Karten"-Links denselben Pfad nutzen.
    for sn, cards in db["sets"].items():
        used = {}
        for c in cards:
            base = f"{num_slug(c['nummer'])}-{slug(c['name'])}"
            used[base] = used.get(base, 0) + 1
            suffix = "" if used[base] == 1 else f"-{used[base]}"
            c["_url"] = f"/karten/{slug(sn)}/{base}{suffix}/"

    # Namens-Index ueber ALLE Sets (fuer "Mehr Karten von X"), unabhaengig von only_set
    global NAME_INDEX
    NAME_INDEX = {}
    for sn, cards in db["sets"].items():
        for c in cards:
            NAME_INDEX.setdefault(c["name"], []).append((sn, c))

    sets = list(db["sets"].items())
    if only_set:
        sets = [(n, c) for n, c in sets if n == only_set]

    era_order, set_meta = load_set_meta()
    write("karten/katalog.css", CSS)
    write("karten/index.html", render_index(list(db["sets"].items()), set_meta, era_order))

    urls = [f"{BASE}/karten/"]
    preis_je_url = {}
    stand_alt = stand_laden()
    n_cards = 0
    n_noindex = 0
    # Rohdaten fuer die Magazin-Artikel, waehrend des Laufs eingesammelt - so
    # braucht es keinen zweiten Durchgang durch alle Sets.
    artikel_sterne = []
    artikel_reverse = []
    for si, (set_name, cards) in enumerate(sets, 1):
        meta = _meta(set_meta, set_name)
        set_rt = meta.get("reverseTypes") or ["reverse"]
        set_info = {"anzahl": len(cards), "era": meta.get("era")}
        # Preise + Verlauf des ganzen Sets in EINEM Abruf. Backend nicht erreichbar
        # -> leeres Dict -> Seiten ohne gebackenen Preis, aber der Lauf laeuft weiter.
        preise = fetch_set_prices(set_name)
        prices = [preis_von(preise.get(c["nummer"])) for c in cards]
        vals = [p for p in prices if p]
        total, priced = sum(vals), len(vals)
        # Reverse: gescrapter Wert (variant_preise['reverse']) ODER Fallback Normalpreis.
        rev_vals = []
        for c, p in zip(cards, prices):
            if not (c.get("has_reverse") or c.get("hat_reverse")):
                continue
            rp = (c.get("variant_preise") or {}).get("reverse") or {}
            val = rp["preis"] if isinstance(rp.get("preis"), (int, float)) else p
            if val:
                rev_vals.append(val)
        reverse_total, reverse_priced = sum(rev_vals), len(rev_vals)
        print(f"  [{si}/{len(sets)}] {set_name}: {priced}/{len(cards)} bepreist, "
              f"Normal {total:.2f} + Reverse {reverse_total:.2f} EUR")

        # Rohdaten fuer die Magazin-Artikel. Nur die EX-Aera - genau darueber
        # schreiben beide Artikel. "Star" trifft sonst auch die Prism-Star-Karten
        # der modernen Sets, die nichts mit Gold Stars zu tun haben.
        if set_name.startswith("EX "):
            for c, p in zip(cards, prices):
                anzeige = "EX Holon Phantoms" if set_name == "EX Holo Phantoms" else set_name
                u = BASE + card_url(set_name, c)
                if "Star" in (c.get("seltenheit") or ""):
                    artikel_sterne.append({
                        "set": anzeige, "nummer": c["nummer"], "name": c["name"],
                        "bild": c.get("bild_url") or "", "url": u, "preis": p})
                rp = (c.get("variant_preise") or {}).get("reverse") or {}
                if isinstance(rp.get("preis"), (int, float)):
                    artikel_reverse.append({
                        "set": anzeige, "nummer": c["nummer"], "name": c["name"],
                        "bild": c.get("bild_url") or "", "url": u,
                        "reverse": rp["preis"], "normal": p,
                        "angebote": rp.get("angebote")})

        write(f"karten/{slug(set_name)}/index.html",
              render_set(set_name, cards, total, priced, reverse_total, reverse_priced))
        urls.append(f"{BASE}/karten/{slug(set_name)}/")
        for i, c in enumerate(cards):
            prev_c = cards[i - 1] if i > 0 else None
            next_c = cards[i + 1] if i < len(cards) - 1 else None
            seite = render_card(set_name, c, prev_c, next_c, set_rt,
                                preise.get(c["nummer"]), set_info)
            write(c["_url"].strip("/") + "/index.html", seite)
            # Seiten auf noindex gehoeren nicht in die Sitemap - sonst melden wir
            # Google genau die Seiten an, von denen wir sagen, er soll sie ignorieren.
            if 'name="robots"' in seite:
                n_noindex += 1
            else:
                urls.append(BASE + c["_url"])
                preis_je_url[c["_url"]] = prices[i]   # Schluessel = Pfad, wie in stand.json
            n_cards += 1

    artikel_bauen(artikel_sterne, artikel_reverse)

    # Sitemap – <lastmod> nur bumpen, wenn sich der PREIS geaendert hat.
    #
    # Frueher zaehlte jede HTML-Aenderung. Das ging, solange von Hand deployt wurde.
    # Seit die Action naechtlich baut, haengt an jeder Karte ein neuer Verlaufspunkt,
    # das HTML aendert sich also IMMER - wir wuerden Google jede Nacht 19.000
    # "Aenderungen" melden und unser Crawl-Budget in Rauschen verbrennen.
    # Der Preis ist das, was die Seite inhaltlich ausmacht; nur er zaehlt.
    #
    # Seiten ohne Preis (Katalog- und Set-Seiten) behalten die alte Regel.
    today = datetime.date.today().isoformat()
    old_lastmod = {}
    sm_path = os.path.join(OUT, "karten/sitemap.xml")
    if os.path.exists(sm_path):
        for m in re.finditer(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>",
                             open(sm_path, encoding="utf-8").read()):
            old_lastmod[m.group(1)] = m.group(2)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    # Zusaetzliche, kleine Sitemap NUR mit Katalog- und Set-Seiten.
    #
    # Rein zur Messung: Die Search Console weist Abdeckung je Sitemap aus. In einer
    # Datei mit 18.800 Karten geht unter, ob die 138 Set-Seiten ankommen - und
    # genau die haben das groessere Suchvolumen und die schwaechere Konkurrenz.
    #
    # Die URLs stehen damit in zwei Sitemaps. Das ist erlaubt, Google fuehrt sie
    # zusammen; die Alternative waere gewesen, die bestehende, sorgfaeltig
    # abgestimmte Datei umzubauen - mehr Risiko fuer denselben Erkenntnisgewinn.
    sm_sets = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    stand_neu = {}
    n_neu = n_karten_url = 0
    for u in urls:
        pfad = u[len(BASE):]
        if pfad in preis_je_url:                       # Kartenseite -> Preisvergleich
            n_karten_url += 1
            neu = preis_je_url[pfad]
            alt = stand_alt.get(pfad) or [None, None]
            alt_preis = alt[0] if len(alt) > 0 else None
            alt_datum = alt[1] if len(alt) > 1 else None
            if alt_datum and preis_gleich(alt_preis, neu):
                lastmod = alt_datum
            else:
                lastmod, n_neu = today, n_neu + 1
            stand_neu[pfad] = [neu, lastmod]
        else:                                          # Katalog-/Set-Seite
            datei = pfad.strip("/") + "/index.html"
            if datei in _CHANGED:
                lastmod, n_neu = today, n_neu + 1
            else:
                lastmod = old_lastmod.get(u, today)
            sm_sets.append(f"<url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>")
        sm.append(f"<url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>")
    sm.append("</urlset>")
    sm_sets.append("</urlset>")
    write("karten/sitemap.xml", "\n".join(sm))
    write("karten/sitemap-sets.xml", "\n".join(sm_sets))
    write(STAND_DATEI, json.dumps(stand_neu, separators=(",", ":")))
    print(f"  Sitemap: {n_neu}/{len(urls)} URLs mit neuem lastmod ({today}), "
          f"Rest behaelt altes Datum")
    print(f"  Set-Sitemap: {len(sm_sets) - 3} Katalog-/Set-Seiten "
          f"-> karten/sitemap-sets.xml")
    print(f"  Stand fortgeschrieben: {len(stand_neu)} Kartenpreise -> {STAND_DATEI}")

    print(f"Generiert: {len(sets)} Sets, {n_cards} Karten, {len(urls)} URLs -> {OUT}")
    print(f"  Ohne jede Preisinfo (noindex, nicht in der Sitemap): {n_noindex} Karten")

    # Notbremse fuer den unbeaufsichtigten Lauf: Waren zu viele Sets nicht abrufbar,
    # steht auf zu vielen Seiten kein Preis. Lieber den alten Stand online lassen,
    # als eine halbe Website zu veroeffentlichen.
    if PREIS_FEHLER:
        anteil = len(PREIS_FEHLER) / max(len(sets), 1)
        print(f"  ! Preise fehlten fuer {len(PREIS_FEHLER)} von {len(sets)} Sets: "
              f"{', '.join(PREIS_FEHLER[:6])}{' ...' if len(PREIS_FEHLER) > 6 else ''}")
        if anteil > 0.05:
            raise SystemExit(
                f"ABBRUCH: {len(PREIS_FEHLER)} Sets ohne Preise ({anteil:.0%}) - "
                f"Backend nicht erreichbar? Es wird nichts veroeffentlicht.")


if __name__ == "__main__":
    import sys
    main(only_set=sys.argv[1] if len(sys.argv) > 1 else None)
