"""PokeTrack-Waechter: prueft von aussen, ob Server, Preise, Website und Bilder
in Ordnung sind, und meldet Probleme sofort per ntfy aufs Handy.

Laeuft alle 30 Minuten als GitHub-Action (.github/workflows/waechter.yml).
Der Laptop-Teil (poketrack-scraper/waechter_lokal.py) nutzt pruefen() fuer die
taegliche Zusammenfassung mit, meldet diese Punkte aber nicht selbst.

Hier stehen KEINE Geheimnisse: Der ntfy-Kanal kommt aus der Umgebung
(NTFY_KANAL, GitHub-Geheimnis), das Repo ist oeffentlich.

Aufruf:  python tools/waechter.py [--stand datei.json] [--trocken]
"""
import datetime as dt
import json
import os
import random
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

BACKEND = "https://poketrack-backend-production.up.railway.app"
WEBSITE = "https://poketrack.de"
BILDER = "https://images.poketrack.de"
APP_STORE_ID = "6790953375"
REPO = "poketrackde-spec/poketrack-website"
WIEN = ZoneInfo("Europe/Vienna")

# Ab wann (Ortszeit) der Preis-Sync einer Sprache gelaufen sein muss.
# Sync-Zeiten: DE 05:00, JP 07:00, EN 09:00 (cron-job.org) - plus Puffer.
# Ab dieser Stunde (Wien) muss der Sync gelaufen sein. Seit 29.10.2026 laufen alle
# nachts (cron-job.org): DE 03:00, EN 03:45, JP 04:45 - weit weg von Deploys,
# die den Server neu starten und einen laufenden Sync abbrechen.
PREISE_FAELLIG = {"de": 6, "en": 6, "jp": 7}
SYNC_UHRZEIT = {"de": "3:00", "en": "3:45", "jp": "4:45"}
MIN_KARTEN = {"db": 19000, "db_en": 21000, "db_jp": 29000}
WIEDERHOLEN_STUNDEN = 6     # ungeloestes Problem hoechstens so oft erneut melden


def jetzt() -> dt.datetime:
    return dt.datetime.now(WIEN)


# ── Netz ──────────────────────────────────────────────────────────────────────

def zahl_de(n) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def holen(url, timeout=20, daten=None, kopf=None, versuche=2):
    """(status, bytes, sekunden, header). Netzfehler -> status 0. Ein zweiter
    Versuch nach 15 s, damit ein einzelner Aussetzer keinen Alarm ausloest."""
    letzter = (0, b"", 0.0, {})
    for i in range(versuche):
        t = time.time()
        req = urllib.request.Request(url, data=daten, headers={"User-Agent": "PokeTrack-Waechter", **(kopf or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), time.time() - t, dict(r.headers)
        except urllib.error.HTTPError as e:
            letzter = (e.code, e.read() or b"", time.time() - t, dict(e.headers or {}))
            if e.code < 500:
                return letzter
        except Exception as e:  # Zeitueberschreitung, DNS, SSL ...
            letzter = (0, str(e).encode(), time.time() - t, {})
        if i < versuche - 1:
            time.sleep(15)
    return letzter


def holen_json(url, timeout=20, **kw):
    status, roh, sek, kopf = holen(url, timeout, **kw)
    try:
        return status, json.loads(roh.decode("utf-8-sig")), sek
    except Exception:
        return status, None, sek


def ssl_tage(host) -> float | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=15) as s:
            with ctx.wrap_socket(s, server_hostname=host) as t:
                ende = ssl.cert_time_to_seconds(t.getpeercert()["notAfter"])
        return (ende - time.time()) / 86400
    except Exception:
        return None


# ── Pruefungen ────────────────────────────────────────────────────────────────
# Jede Pruefung haengt Befunde an: (schluessel, stufe, text). stufe: "alarm"
# (sofort, laut) oder "warnung" (sofort, normal). ok-Meldungen sammelt `ok`.

class Befund:
    def __init__(self):
        self.probleme: dict[str, tuple[str, str]] = {}
        self.ok: list[str] = []
        self.info: dict = {}

    def problem(self, schluessel, stufe, text):
        self.probleme[schluessel] = (stufe, text)

    def gut(self, text):
        self.ok.append(text)


def pruefe_status(b: Befund, stand: dict):
    status, s, sek = holen_json(f"{BACKEND}/status", timeout=30)
    b.info["status_sek"] = round(sek, 1)
    if status != 200 or not s:
        b.problem("server", "alarm", f"Server antwortet nicht (Status {status}). App-Preise, Sync und Katalog-Updates sind betroffen.")
        return None
    if sek > 5:
        b.problem("server_langsam", "alarm",
                  f"/status braucht {sek:.0f} s - die Apps warten nur 5 s und bekommen so KEINE Katalog-Updates.")
    else:
        b.gut(f"Server antwortet ({sek:.1f} s)")

    # Kataloge
    for vs, minimum in MIN_KARTEN.items():
        name = {"db": "deutsch", "db_en": "englisch", "db_jp": "japanisch"}[vs]
        if not s.get(f"{vs}_version"):
            b.problem(f"katalog_{vs}", "alarm", f"Katalog {name}: keine Version gemeldet - Apps laden keine Updates.")
        elif (s.get(f"{vs}_cards") or 0) < minimum:
            b.problem(f"katalog_{vs}", "alarm", f"Katalog {name}: nur {s.get(f'{vs}_cards')} Karten (erwartet ≥ {minimum:,}).".replace(",", "."))
    b.info["kataloge"] = {vs: (s.get(f"{vs}_version"), s.get(f"{vs}_cards")) for vs in MIN_KARTEN}

    # Preise heute gemessen? (Zaehlungen hoechstens 15 min alt)
    heute = s.get("heute") or {}
    stunde = jetzt().hour
    b.info["preise"] = {}
    for sp, ab in PREISE_FAELLIG.items():
        h = heute.get(sp) or {}
        b.info["preise"][sp] = h.get("gemessen")
        if not s.get("zahlen_stand"):
            continue   # Zaehlungen laufen gerade erst an (nach Neustart)
        name = {"de": "deutsch", "en": "englisch", "jp": "japanisch"}[sp]
        if stunde >= ab and not h.get("cron_gelaufen"):
            b.problem(f"preise_{sp}", "alarm",
                      f"Preise {name} heute NICHT aktualisiert (Sync fällig seit {SYNC_UHRZEIT[sp]}). cron-job.org prüfen.")
        elif stunde >= ab and not s.get("sync_running") and (h.get("zeilen") or 0) > 0 \
                and h["gemessen"] < 0.5 * h["zeilen"]:
            # 28.10.2026: Sync brach mittendrin ab (DE 10.104 statt ~37.000)
            b.problem(f"preise_{sp}", "alarm",
                      f"Preise {name} nur teilweise aktualisiert: {zahl_de(h['gemessen'])} von {zahl_de(h['zeilen'])}. Sync abgebrochen?")
        sync = (s.get("letzte_syncs") or {}).get(sp) or {}
        if sync.get("status") == "fehler" and str(sync.get("zeit", "")).startswith(jetzt().date().isoformat()):
            b.problem(f"sync_{sp}", "alarm", f"Preis-Sync {name} abgestürzt: {str(sync.get('fehler') or sync.get('error'))[:160]}")
    # Immer mitzaehlen, damit die Zahl der Pruefungen nicht mit der Uhrzeit schwankt
    if not any(k.startswith(("preise_", "sync_")) for k in b.probleme):
        b.gut("Preise pünktlich (alle fälligen Sprachen gemessen)")

    # Schluessel am Server
    fehlend = [k for k, v in (s.get("konfiguration") or {}).items() if not v]
    if fehlend:
        b.problem("konfiguration", "alarm", "Am Server fehlen Einstellungen: " + ", ".join(fehlend))

    # Laeufe: Sicherung (taeglich), Preisalarme (taeglich 10:00), Wochenrueckblick (So 18:00)
    for name, feld, max_h, titel in (("sicherung", "letzte_sicherung", 30, "Datensicherung der Konten"),
                                     ("preisalarme", "letzte_preisalarme", 30, "Preisalarm-Lauf"),
                                     ("wochenrueckblick", "letzte_wochenrueckblicke", 8 * 24, "Wochenrückblick")):
        lauf = s.get(feld) or {}
        if lauf.get("status") == "fehler":
            b.problem(f"lauf_{name}", "alarm", f"{titel} fehlgeschlagen: {lauf.get('fehler', '')[:160]}")
        elif lauf.get("zeit"):
            alter = (dt.datetime.now() - dt.datetime.fromisoformat(lauf["zeit"])).total_seconds() / 3600
            if alter > max_h:
                b.problem(f"lauf_{name}", "warnung", f"{titel} lief zuletzt vor {alter / 24:.1f} Tagen.")

    # Preis-API-Kontingent
    k = s.get("api_kontingent") or {}
    b.info["api_kontingent"] = k
    if k.get("status") in (401, 403):
        b.problem("api_zugang", "alarm", f"Preis-API lehnt den Schlüssel ab (HTTP {k['status']}).")
    elif k.get("rest") is not None and k["rest"] < 300:
        b.problem("api_kontingent", "warnung", f"Preis-API: nur noch {k['rest']} Abrufe übrig heute.")
    return s


def pruefe_app_endpunkte(b: Befund, stand: dict):
    fehler = []
    for pfad, pruef in (("/kommende-sets", lambda d: "sets" in d),
                        ("/umfrage", lambda d: "umfragen" in d),
                        ("/sealed", lambda d: len(d.get("produkte") or []) > 0),
                        ("/app-version", lambda d: bool(d.get("aktuell")))):
        status, d, sek = holen_json(BACKEND + pfad, timeout=20)
        if status != 200 or not d or not pruef(d):
            fehler.append(f"{pfad} ({status})")
        elif pfad == "/app-version":
            b.info["app_version_server"] = d.get("aktuell")
    if fehler:
        b.problem("app_endpunkte", "alarm", "App-Schnittstellen gestört: " + ", ".join(fehler))
    else:
        b.gut("App-Schnittstellen (Sets, Umfrage, Sealed, Version)")

    # Kennt der Server die Version, die im App Store steht? (sonst kein Update-Hinweis)
    status, d, _ = holen_json(f"https://itunes.apple.com/lookup?id={APP_STORE_ID}&country=de")
    treffer = (d or {}).get("results") or []
    if treffer:
        store = treffer[0].get("version")
        b.info["app_store"] = {"version": store, "bewertung": treffer[0].get("averageUserRating"),
                               "anzahl": treffer[0].get("userRatingCount")}
        server = b.info.get("app_version_server")
        # Nach einem Release hinkt Apples Lookup je nach Region ein paar Stunden
        # hinterher - erst melden, wenn die Abweichung 3 h besteht.
        if server and store and server != store:
            seit = stand.setdefault("app_version_abweichung_seit", time.time())
            if time.time() - seit > 3 * 3600:
                b.problem("app_version", "warnung",
                          f"Server meldet App-Version {server}, im Store ist {store} - der Update-Hinweis zeigt das Falsche.")
        else:
            stand.pop("app_version_abweichung_seit", None)


def pruefe_website(b: Befund):
    fehler = []
    for pfad, muss in (("/", "PokéTrack"), ("/app/", None), ("/datenschutz", None), ("/karten/", None),
                       ("/.well-known/apple-app-site-association", "applinks")):
        status, roh, _, _ = holen(WEBSITE + pfad, timeout=30)
        if status != 200 or (muss and muss.encode() not in roh):
            fehler.append(f"{pfad} ({status})")
    if fehler:
        b.problem("website", "alarm", "Website gestört: " + ", ".join(fehler))
    else:
        b.gut("Website, Web-App und App-Links erreichbar")

    status, roh, _, kopf = holen(f"{BILDER}/delta-herrschaft.png", timeout=30)
    if status != 200 or not (kopf.get("Content-Type", "") or "").startswith("image"):
        b.problem("bilder", "alarm", f"Bilder-Server antwortet nicht richtig ({status}) - Kartenbilder fehlen in der App.")

    for host in ("poketrack.de", "images.poketrack.de", "poketrack-backend-production.up.railway.app"):
        tage = ssl_tage(host)
        if tage is not None and tage < 14:
            b.problem(f"ssl_{host}", "warnung", f"Sicherheitszertifikat von {host} läuft in {tage:.0f} Tagen ab.")


def pruefe_github(b: Befund):
    kopf = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        kopf["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    status, d, _ = holen_json(f"https://api.github.com/repos/{REPO}/actions/workflows/katalog.yml/runs?per_page=10", kopf=kopf)
    laeufe = [r for r in (d or {}).get("workflow_runs", []) if r.get("status") == "completed"]
    if not laeufe:
        return
    letzter = laeufe[0]
    erfolg = [r for r in laeufe if r.get("conclusion") == "success"]
    if letzter.get("conclusion") not in ("success", "cancelled"):
        b.problem("katalog_action", "warnung",
                  f"Website-Katalog: letzter Bau fehlgeschlagen ({letzter.get('conclusion')}). {letzter.get('html_url')}")
    elif erfolg:
        alter = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(erfolg[0]["updated_at"].replace("Z", "+00:00"))).total_seconds() / 3600
        if alter > 30:
            b.problem("katalog_action", "warnung", f"Website-Katalog seit {alter:.0f} h nicht neu gebaut.")


def pruefe_katalog_inhalt(b: Befund, stand: dict):
    """Einmal am Tag (ab 08:00): Kataloge laden wie die App, Preise auf
    Einbrueche und Spruenge pruefen, Stichprobe Kartenbilder."""
    heute = jetzt().date().isoformat()
    if jetzt().hour < 8 or stand.get("katalog_geprueft") == heute:
        return
    # Wie die App: /cards/teile (nur Statuspruefung) und /cards fuer den Inhalt
    status, d, sek = holen_json(f"{BACKEND}/cards/teile", timeout=120,
                                daten=json.dumps({"sprache": "de", "stufe": 2, "reihenfolge_summe": "", "summen": {}}).encode(),
                                kopf={"Content-Type": "application/json"})
    if status != 200 or not d or not d.get("version") or not d.get("sets"):
        b.problem("katalog_teile", "alarm", f"/cards/teile liefert keinen Katalog ({status}) - Apps laden dann den ganzen Katalog oder gar nichts.")

    status, d, sek = holen_json(f"{BACKEND}/cards?sprache=de&stufe=2", timeout=180)
    if status != 200 or not d or not d.get("sets"):
        b.problem("katalog_inhalt", "alarm", f"/cards (deutsch) liefert keinen Katalog ({status}).")
        return
    preise, bilder = {}, []
    for set_name, karten in d["sets"].items():
        for k in karten:
            p = k.get("preis_normal")
            if isinstance(p, (int, float)) and p > 0:
                preise[f"{set_name}|{k.get('nummer')}|{k.get('name')}"] = round(float(p), 2)
            if k.get("bild_url"):
                bilder.append(k["bild_url"])
    vorher = stand.get("preise_de") or {}
    b.info["preise_de_anzahl"] = len(preise)
    if vorher:
        if len(preise) < 0.95 * len(vorher):
            b.problem("preise_einbruch", "alarm",
                      f"Deutsche Preise: nur noch {len(preise):,} Karten mit Preis (gestern {len(vorher):,}).".replace(",", "."))
        gemeinsam = [x for x in preise if x in vorher]
        spruenge = [x for x in gemeinsam if max(preise[x], vorher[x]) / max(min(preise[x], vorher[x]), 0.01) >= 3 and max(preise[x], vorher[x]) >= 2]
        b.info["preis_spruenge"] = len(spruenge)
        if gemeinsam and len(spruenge) > 0.03 * len(gemeinsam):
            beispiele = "; ".join(f"{x.split('|')[2]} ({x.split('|')[0]}) {vorher[x]:.2f}→{preise[x]:.2f} €" for x in spruenge[:3])
            b.problem("preis_spruenge", "alarm",
                      f"{len(spruenge)} deutsche Preise haben sich über Nacht verdreifacht oder gedrittelt - Datenfehler? z. B. {beispiele}")
    stand["preise_de"] = preise
    stand["katalog_geprueft"] = heute

    kaputt = 0
    for url in random.sample(bilder, min(5, len(bilder))):
        status, _, _, kopf = holen(url, timeout=30, versuche=1)
        if status != 200:
            kaputt += 1
    if kaputt >= 2:
        b.problem("kartenbilder", "warnung", f"{kaputt} von 5 zufälligen Kartenbildern laden nicht.")


def pruefen(stand: dict) -> Befund:
    b = Befund()
    for f in (pruefe_status, pruefe_app_endpunkte, pruefe_website, pruefe_github, pruefe_katalog_inhalt):
        try:
            if f in (pruefe_status, pruefe_katalog_inhalt, pruefe_app_endpunkte):
                f(b, stand)
            else:
                f(b)
        except Exception as e:  # ein Fehler im Waechter selbst soll die anderen Pruefungen nicht stoppen
            b.problem(f"waechter_{f.__name__}", "warnung", f"Wächter-Prüfung {f.__name__} ist abgestürzt: {type(e).__name__}: {e}")
    return b


# ── Melden ────────────────────────────────────────────────────────────────────

def ntfy(kanal, titel, text, prio=3, tags=None, trocken=False):
    if trocken or not kanal:
        print(f"[ntfy {prio}] {titel}\n{text}\n")
        return
    daten = json.dumps({"topic": kanal, "title": titel, "message": text, "priority": prio,
                        "tags": tags or []}).encode("utf-8")
    req = urllib.request.Request("https://ntfy.sh/", data=daten, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def melden(b: Befund, stand: dict, kanal: str, quelle: str, trocken=False):
    """Neue Probleme sofort, ungeloeste alle WIEDERHOLEN_STUNDEN erneut, behobene
    einmal mit 'wieder ok'. `stand['offen']` merkt sich, was schon gemeldet ist."""
    offen = stand.setdefault("offen", {})
    t = time.time()
    for schluessel, (stufe, text) in b.probleme.items():
        alt = offen.get(schluessel)
        if alt is None or t - alt["gemeldet"] > WIEDERHOLEN_STUNDEN * 3600:
            prio = 5 if stufe == "alarm" else 4
            zusatz = "" if alt is None else f"\n(besteht seit {dt.datetime.fromtimestamp(alt['seit'], WIEN):%d.%m. %H:%M})"
            ntfy(kanal, ("🚨 " if stufe == "alarm" else "⚠️ ") + "PokéTrack: Problem", text + zusatz, prio,
                 ["rotating_light" if stufe == "alarm" else "warning", quelle], trocken)
            offen[schluessel] = {"seit": alt["seit"] if alt else t, "gemeldet": t, "text": text}
    # Jeder Waechter (GitHub, Laptop) hat seine eigene Stand-Datei.
    for schluessel in list(offen):
        if schluessel not in b.probleme:
            ntfy(kanal, "✅ PokéTrack: wieder ok", f"Behoben: {offen[schluessel]['text']}", 3, ["white_check_mark"], trocken)
            del offen[schluessel]


WOCHENTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def grund_zusammenfassung(b: Befund, stand: dict, kanal: str, trocken=False):
    """Taeglich ab 08:00 aus der Cloud - kommt auch, wenn der Laptop aus ist
    (seit 29.10.2026). Nur oeffentliche Daten; Downloads, Einnahmen, Abos und
    Nutzer schickt der Laptop-Waechter separat ("Zahlen"), sobald er laeuft."""
    jz = jetzt()
    heute = jz.date().isoformat()
    # Zeitfenster begrenzen: geht der Actions-Cache verloren, kaeme sie sonst
    # bei jedem Lauf des Tages erneut.
    if not (8 <= jz.hour < 12) or stand.get("zusammenfassung") == heute:
        return
    zeilen = []
    if b.probleme:
        zeilen.append(f"⚠️ {len(b.probleme)} Problem{'e' if len(b.probleme) > 1 else ''}:")
        zeilen += [f"  • {text}" for _, text in b.probleme.values()]
    else:
        zeilen.append(f"✅ Alles läuft ({len(b.ok)} Prüfungen ok)")
    zeilen.append("")
    pr = b.info.get("preise") or {}
    k = b.info.get("api_kontingent") or {}
    preise = " · ".join(f"{sp.upper()} {zahl_de(n)}" if n else f"{sp.upper()} –" for sp, n in pr.items())
    zeilen.append(f"💰 Preise heute gemessen: {preise}"
                  + (f" · API-Rest {zahl_de(k['rest'])}/{zahl_de(k.get('limit') or 0)}" if k.get("rest") is not None else ""))
    kat = b.info.get("kataloge") or {}
    if kat:
        zeilen.append("📚 Kataloge: " + " · ".join(f"{n} {zahl_de(c or 0)}" for n, (v, c) in zip(("DE", "EN", "JP"), kat.values())))
    st = b.info.get("app_store") or {}
    if st.get("bewertung"):
        zeilen.append(f"⭐ App Store: {st['bewertung']:.1f} ★ aus {st.get('anzahl')} Bewertungen (DE) · Version {st.get('version')}")
    if b.info.get("preis_spruenge") is not None:
        zeilen.append(f"🔎 Preis-Check: {zahl_de(b.info.get('preise_de_anzahl'))} deutsche Karten mit Preis, "
                      f"{b.info['preis_spruenge']} auffällige Sprünge")
    zeilen.append("")
    zeilen.append("📊 Downloads, Einnahmen und Nutzer folgen vom Laptop, sobald er läuft.")
    ntfy(kanal, f"☀️ PokéTrack – {WOCHENTAG[jz.weekday()]} {jz:%d.%m.}", "\n".join(zeilen), 3, ["sunny", "github"], trocken)
    stand["zusammenfassung"] = heute


def main(argv):
    pfad = "waechter_stand.json"
    if "--stand" in argv:
        pfad = argv[argv.index("--stand") + 1]
    trocken = "--trocken" in argv
    try:
        stand = json.load(open(pfad, encoding="utf-8"))
    except Exception:
        stand = {}
    b = pruefen(stand)
    kanal = os.environ.get("NTFY_KANAL", "").strip()
    if not kanal and not trocken:
        print("NTFY_KANAL fehlt - nur Ausgabe.")
        trocken = True
    melden(b, stand, kanal, "github", trocken)
    if "--zusammenfassung" in argv:
        stand.pop("zusammenfassung", None)
    grund_zusammenfassung(b, stand, kanal, trocken)
    if kanal and not trocken and not stand.get("verbunden"):
        ntfy(kanal, "🔗 GitHub-Wächter verbunden",
             f"Prüft ab jetzt alle 30 Minuten Server, Preise, Website und Bilder.\n"
             f"Erster Lauf: {len(b.ok)} Prüfungen ok, {len(b.probleme)} Probleme.", 3, ["link"])
        stand["verbunden"] = jetzt().isoformat(timespec="seconds")
    stand["zuletzt"] = jetzt().isoformat(timespec="seconds")
    json.dump(stand, open(pfad, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(b.ok)} ok, {len(b.probleme)} Probleme")
    for k, (stufe, text) in b.probleme.items():
        print(f"  [{stufe}] {k}: {text}")
    print("Info:", json.dumps({k: v for k, v in b.info.items()}, ensure_ascii=False, default=str)[:1500])


if __name__ == "__main__":
    main(sys.argv[1:])
