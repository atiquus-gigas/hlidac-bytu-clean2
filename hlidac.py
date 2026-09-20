import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import os
import re
import json
import smtplib
import cloudscraper
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup

# -----------------------------
# 1) KONFIGURACE FILTRŮ
# -----------------------------

MAX_CENA = 25000
POVOLENE_DISPOZICE = ["2+1", "3+kk", "3+KK", "3+Kk"]
POVOLENE_LOKALITY = ["Praha", "Praha-západ", "Praha západ"]
POVOLENE_PATRA = ["Přízemí", "1. patro", "1.patro", "1", "0"]
POVOLEN_VYTAH = True

# -----------------------------
# 2) HISTORIE
# -----------------------------

HIST_FILE = "historie_bytu.txt"
scraper = cloudscraper.create_scraper()

def load_history():
    if not os.path.exists(HIST_FILE):
        with open(HIST_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return set()
    with open(HIST_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

HIST = load_history()

def save_history():
    with open(HIST_FILE, "w", encoding="utf-8") as f:
        for item in sorted(HIST):
            f.write(item + "\n")

# -----------------------------
# 3) EMAIL
# -----------------------------

EMAIL = os.getenv("EMAIL_UZIVATELE")
HESLO = os.getenv("HESLO_APLIKACE")

def posli_email(portal, titulek, cena, lokalita, patro, odkaz):
    subject = f"Nový byt – {portal}"
    body = f"""
Portál: {portal}
Titulek: {titulek}
Cena: {cena}
Lokalita: {lokalita}
Patro / výtah: {patro}
Odkaz: {odkaz}
"""

    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL, HESLO)
            server.send_message(msg)
        print(f"📧 Odeslán e‑mail: {titulek}")
    except Exception as e:
        print("❌ Chyba e‑mailu:", e)

# -----------------------------
# 4) FILTR
# -----------------------------

def splnuje_filtry(titulek, cena, lokalita, patro, vytah):
    try:
        cena_int = int(re.sub(r"\D", "", str(cena)))
    except:
        return False

    if cena_int > MAX_CENA:
        return False

    if not any(loc.lower() in lokalita.lower() for loc in POVOLENE_LOKALITY):
        return False

    if not any(disp.lower() in titulek.lower() for disp in POVOLENE_DISPOZICE):
        return False

    if patro:
        if not any(p.lower() in patro.lower() for p in POVOLENE_PATRA):
            if not (POVOLEN_VYTAH and "výtah" in patro.lower()):
                return False

    return True

# -----------------------------
# 5) IMPORT MODULŮ PORTÁLŮ
# -----------------------------
# očekávané API: fetch(scraper) -> list[dict] se strukturou:
# {
#   "portal": "Sreality",
#   "eid": "sreality_123",
#   "titulek": "...",
#   "cena": "25000",
#   "lokalita": "Praha",
#   "patro": "1. patro",
#   "vytah": True/False,
#   "odkaz": "https://..."
# }

from sources.sreality import fetch as fetch_sreality
from sources.bezrealitky import fetch as fetch_bezrealitky
from sources.bazos import fetch as fetch_bazos
from sources.ultranet import fetch as fetch_ultranet
from sources.realitymix import fetch as fetch_realitymix
from sources.idnes import fetch as fetch_idnes
from sources.realingo import fetch as fetch_realingo
from sources.expats import fetch as fetch_expats
from sources.realitycechy import fetch as fetch_realitycechy
from sources.realcity import fetch as fetch_realcity
from sources.hyperreality import fetch as fetch_hyperreality
from sources.maxima import fetch as fetch_maxima

PORTAL_FETCHERS = [
    fetch_sreality,
    fetch_bezrealitky,
    fetch_bazos,
    fetch_ultranet,
    fetch_realitymix,
    fetch_idnes,
    fetch_realingo,
    fetch_expats,
    fetch_realitycechy,
    fetch_realcity,
    fetch_hyperreality,
    fetch_maxima,
]

# -----------------------------
# 6) ORCHESTRÁTOR PORTÁLŮ
# -----------------------------

def zpracuj_portal(fetch_func):
    try:
        offers = fetch_func(scraper)
    except Exception as e:
        print(f"❌ Chyba portálu {fetch_func.__module__}:", e)
        return

    for o in offers:
        portal = o.get("portal", "Neznámý")
        eid = o.get("eid")
        titulek = o.get("titulek", "")
        cena = o.get("cena", "0")
        lokalita = o.get("lokalita", "")
        patro = o.get("patro", "")
        vytah = o.get("vytah", False)
        odkaz = o.get("odkaz", "")

        if not eid:
            continue

        if eid in HIST:
            continue

        if splnuje_filtry(titulek, cena, lokalita, patro, vytah):
            HIST.add(eid)
            posli_email(portal, titulek, cena, lokalita, patro, odkaz)

# -----------------------------
# 7) MAIN
# -----------------------------

if __name__ == "__main__":
    print("🚀 Kontrola bytů…")
