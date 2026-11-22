#!/usr/bin/env python3
"""Local price database: answers "what does this invoice line cost?" in milliseconds, without an LLM.

Data (all downloaded once, see fetch_*.py and db_extract.py):
  offers  every EUR offer of German web shops in the WDC schema.org crawl 2024-12 (name, price, shop), full-text indexed
  refs    hourly rates by trade (TAIFUN Preisatlas, Clean-Invoice), call-out flat rates, municipal waste fees

Query: an English invoice line is mapped to a concept by a fixed keyword table (CONCEPTS). A concept is either goods
(full-text search over the German offers plus include / exclude filters), an hourly rate, a call-out flat rate or a waste
fee. Lines no concept matches get a plain full-text search and are marked "low". No concept, no data: the answer is None.

Stdlib only. Run:
  python3 -I research/prices/pricedb.py build                      # raw/wdc_all/*.tsv + prices.csv -> pricedb.sqlite
  python3 -I research/prices/pricedb.py q "TV set" [--qty 1 --unit pcs --trade "Electronics Retail"]
  python3 -I research/prices/pricedb.py search "füllventil"        # raw full-text search, to check a concept by hand
"""
import csv
import json
import re
import sqlite3
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "pricedb.sqlite"
I = re.I


# ---------------------------------------------------------------------------------------------------------------- build

def build():
    tmp = DB.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE offers(id INTEGER PRIMARY KEY, name TEXT, price REAL, host TEXT, url TEXT);
        CREATE TABLE refs(source TEXT, item TEXT, unit TEXT, price REAL, region TEXT, date TEXT, url TEXT, note TEXT, tag TEXT);
        CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
    """)
    seen, n_raw = set(), 0
    for f in sorted((HERE / "raw" / "wdc_all").glob("*.tsv")):
        rows = []
        with f.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) != 4:
                    continue
                host, price, name, url = p
                n_raw += 1
                key = (host, name.lower(), price)      # the same product is listed on many category pages
                if key in seen:
                    continue
                seen.add(key)
                rows.append((name, float(price), host, url))
        con.executemany("INSERT INTO offers(name, price, host, url) VALUES (?,?,?,?)", rows)
    with (HERE / "prices.csv").open(newline="", encoding="utf-8") as fh:
        refs = [r for r in csv.DictReader(fh) if r["source"] != "wdc"]
    con.executemany("INSERT INTO refs VALUES (?,?,?,?,?,?,?,?,?)",
                    [(r["source"], r["item"], r["unit"], float(r["price_gross_eur"]), r["region"], r["date"], r["url"],
                      r["note"], r["tag"]) for r in refs])
    con.executescript("""
        CREATE VIRTUAL TABLE offers_fts USING fts5(name, content='offers', content_rowid='id',
                                                   tokenize="unicode61 remove_diacritics 2", prefix='3 4 5 6');
        INSERT INTO offers_fts(rowid, name) SELECT id, name FROM offers;
        INSERT INTO offers_fts(offers_fts) VALUES('optimize');
    """)
    con.executemany("INSERT INTO meta VALUES (?,?)", [
        ("built", time.strftime("%Y-%m-%d %H:%M")), ("offers", str(len(seen))), ("offers_raw", str(n_raw)),
        ("refs", str(len(refs))), ("offers_source", "Web Data Commons schema.org Product 2024-12, German shops, EUR")])
    con.commit()
    con.execute("VACUUM")
    con.close()
    tmp.replace(DB)
    print(f"{len(seen)} offers ({n_raw} before de-duplication), {len(refs)} rate/fee rows -> {DB.name} "
          f"({DB.stat().st_size / 1e6:.0f} MB)")


# ------------------------------------------------------------------------------------------------------------- concepts

# Accessories and spare parts that share a word with the product ("TV" finds wall mounts). Applied to every goods concept
# unless the concept sets its own list.
ACCESSORY = (r"halter|kabel|fernbedienung|remote|hülle|huelle|folie|ständer|staender|stativ|ersatzteil|adapter|tasche|"
             r"\bcase\b|cover|mount|bracket|netzteil|ladeger|charger|schraube|aufkleber|sticker|wandmontage|clip|antenne|"
             r"reiniger|dichtung|akku\b|battery|abdeckung|gutschein|bilderrahmen|schutz|zubehör|zubehoer|gebraucht|"
             r"refurb|b-ware|defekt|für |fuer |\bfor\b|passend")


@dataclass
class C:
    id: str
    en: str                      # regex on the English invoice line
    kind: str = "goods"          # goods | rate | travel | fee | none
    fts: str = ""                # goods: FTS5 query over the German offer names
    must: str = ""               # goods: the offer name has to match this as well
    exclude: str = ACCESSORY     # goods: drop offers whose name matches
    lo: float = 0.0              # goods: lowest price that can still be the product itself, not a part of it
    hi: float = 20000.0
    tag: str = ""                # rate / fee: tag in refs
    level: str = ""              # rate: regex on the refs item ("Meister", "Geselle")
    amount: tuple = ()           # fee: (assumed m³, assumed t) for one invoice piece
    note: str = ""


# Order matters: the first concept whose `en` matches wins, so specific lines come before general ones.
CONCEPTS = [
    # --- lines the web cannot price (own flat fees, or the value depends on the damage, not on a list price)
    C("shipping", r"\b(shipping|delivery|postage)\b", "none", note="carrier flat fee, not in the data"),
    C("admin", r"\b(administrative|processing|claim-processing|catering|electricity)\b", "none", note="not a market good"),
    C("diagnostic", r"\b(diagnos\w+|inspection|assessment|safety check|report)\b", "none", note="service flat fee, no source"),

    # --- call-out
    C("travel", r"\b(vehicle costs?|travel costs?)\b", "travel", note="call-out flat rate, near zone"),

    # --- labour by the hour
    C("hours_master", r"\b(senior|master|foreman)\b.*\bhours?\b", "rate", level="Meister"),
    C("hours_apprentice", r"\b(apprentice|helper|trainee)\b.*\bhours?\b", "none", note="no apprentice rate in the data"),
    C("hours", r"\bhours?\b|\blabou?r\b", "rate", level="Geselle"),

    # --- disposal (fee per tonne or m³ at the Munich recycling centre, times an assumed amount)
    C("waste_green", r"dispos\w+.*\b(green waste|branches|foliage)\b", "fee", tag="green_waste", amount=(4.0, 0.8)),
    C("waste_timber", r"dispos\w+.*\b(timber|wood|table|furniture)\b", "fee", tag="timber", amount=(1.0, 0.3)),
    C("waste_soil", r"dispos\w+.*\b(soil|topsoil|grit|rubble|construction waste)\b", "fee", tag="soil_rubble", amount=(0.5, 0.75)),
    C("waste_other", r"\bdispos\w+", "none", note="no fee published for this kind of waste"),

    # --- repairs: a repair is not the price of the new item
    C("laptop_repair", r"\b(laptop|notebook|mac)\b.*\b(repair|damage)\b|\b(screen|housing|corner)\b.*\brepair\b", "none",
      note="manufacturer repair prices (Apple) could not be downloaded"),
    C("repair", r"\b(repair|refinish|touch-up|polish|re-plaster|repaint|cleaning|drying|removal|installation|assembly|"
                r"drilling|detection|pinpointing|measurement|freeing)\b", "none", note="job price: no job-price source yet (baupreislexikon missing)"),

    # --- goods
    C("tv", r"\b(tv|television)\b", fts="fernseher OR tv OR oled OR qled OR television",
      must=r"fernseher|smart-?tv|(led|oled|qled|lcd)-?tv|\btv\b.*\d{2}\s?(zoll|\"|''|cm)|\d{2}\s?(zoll|\"|''|cm).*\btv\b", lo=150,
      exclude=ACCESSORY + r"|tv-?box|tv-?stick|receiver|dvb|set-?top|board|möbel|moebel|schrank|tisch|streaming|beamer|sessel|sofa|"
                          r"projektor|monitor|soundbar|lautsprecher|kopfhörer|rack|regal|bank|wand|lift|hocker|liege"),
    C("av_receiver", r"\b(av receiver|amplifier|receiver)\b", fts="receiver OR verstärker OR verstaerker OR amplifier",
      must=r"av-?receiver|a/v-?receiver|heimkino-?receiver|stereo-?receiver|netzwerk-?receiver|vollverstärker|"
           r"stereo-?verstärker|hifi-?verstärker", lo=100,
      exclude=ACCESSORY + r"|sat-?receiver|dvb|kopfhörer|bluetooth-?receiver|funk|auto|kfz|gitarre|bass"),
    C("speaker_system", r"\b(speaker|sound ?system|hi-?fi)\b",
      fts="lautsprecher* OR soundbar OR heimkino* OR surround* OR soundsystem OR stereoanlage OR kompaktanlage",
      must=r"soundbar|heimkino|surround|5\.1|2\.1|3\.1|7\.1|lautsprecher-?(set|system|paar)|stereo-?(set|anlage)|"
           r"kompaktanlage|soundsystem|standlautsprecher|regallautsprecher|aktivlautsprecher|hifi", lo=50,
      exclude=ACCESSORY + r"|kopfhörer|auto|kfz|einbau|decken|megafon|gaming-?stuhl",
      note="a system: soundbar, home cinema set, hi-fi pair; single portable speakers are left out"),
    C("dvd_player", r"\b(dvd|blu-?ray)\b", fts="dvd* OR bluray* OR blu", must=r"(dvd|blu-?ray)-?(player|spieler|recorder)", lo=20,
      exclude=ACCESSORY + r"|tragbar.*auto|laufwerk|brenner|rohling"),
    C("router", r"\brouter\b", fts="router OR fritzbox OR fritz", must=r"router|fritz!?box", lo=15,
      exclude=ACCESSORY + r"|fräs|fraes|oberfräse|cnc|tisch|premiumsim|\bsim\b|notebook|macbook|ideapad"),
    C("console", r"\b(games? console|playstation|xbox|nintendo)\b", fts="playstation OR xbox OR nintendo OR spielkonsole OR konsole",
      must=r"(playstation|ps5|xbox|nintendo switch).*(konsole|console|slim|pro|digital|oled|\bgb\b|\btb\b)|spielkonsole", lo=100,
      exclude=ACCESSORY + r"|controller|spiel\b|game\b|headset|lenkrad|skin"),
    C("hdmi", r"\bhdmi\b", fts="hdmi", must=r"hdmi-?kabel|hdmi.*kabel|kabel.*hdmi", exclude=r"adapter|switch|splitter|extender|verteiler|umschalter|konverter|receiver", hi=100),
    C("remote", r"\bremote controls?\b", fts="fernbedienung OR remote", must=r"(universal|ersatz|tv|fernseh)-? ?fernbedienung|fernbedienung (für|fuer|kompatibel)|^fernbedienung", hi=150,
      exclude=r"hülle|huelle|halter|schutz|garage|tor\b|auto|kfz|steckdose|led|licht|lampe|ventilator|heiz"),
    C("wall_mount", r"\b(wall-?mount|bracket)\b", fts="wandhalterung OR wandhalter OR halterung", must=r"(tv|fernseh|monitor|bildschirm).*(wandhalter|halterung)|wandhalter.*(tv|fernseh|zoll)", exclude=r"lautsprecher|boxen|fahrrad"),
    C("power_lead", r"\b(mains plug|power lead|power cable|power cord)\b", fts="netzkabel OR kaltgerätekabel OR stromkabel OR schukostecker",
      must=r"netzkabel|kaltgerätekabel|stromkabel|schuko-?stecker", hi=100,
      exclude=r"adapter|verlängerung|trommel|leiste|netzwerk|\blan\b|usb|hdmi|lade|subwoofer|modul"),
    C("laptop", r"\b(laptop|notebook|macbook)\b", fts="notebook OR laptop OR macbook OR ultrabook", must=r"notebook|laptop|macbook|ultrabook", lo=250,
      exclude=ACCESSORY + r"|rucksack|ständer|kühler|tisch|dock|ram\b|ssd\b|display\b|tastatur|lüfter"),
    C("bike_frame", r"\b(bicycle|bike)\b.*\bframe\b|\bframe\b.*\b(bicycle|bike)\b", fts="rahmen OR rahmenset OR frameset OR frame",
      must=r"fahrradrahmen|rennradrahmen|mtb-?rahmen|rahmenset|frameset|rahmenkit|(bike|gravel|rennrad|mtb|enduro|trekking).*\b(rahmen|frame)\b", lo=80,
      exclude=r"tasche|schutz|schloss|polster|aufkleber|bilderrahmen|tür|fenster|halter|pumpe|brille|adapter|bag\b|auto|kfz|motorrad|"
              r"\d+[- ]?gang|kinderfahrrad|e-?bike|fahrrad für"),
    C("bike_brake", r"\b(bicycle|bike)\b.*\bbrakes?\b|\bbrakes?\b.*\b(bicycle|bike)\b", fts="scheibenbremse* OR bremse OR bremsen OR bremsset OR felgenbremse* OR brake",
      must=r"scheibenbremse|bremsset|bremsen-?set|felgenbremse|v-?brake|disc ?brake|(shimano|sram|magura|tektro|hope|trp|formula).*(bremse|brake)", lo=10,
      exclude=r"belag|beläge|bremsbel|pad\b|pads\b|scheibe\b|rotor|leitung|flüssigkeit|zug\b|klotz|schuh|adapter|schraube|entlüft|auto|kfz|pkw|"
              r"motorrad|anhänger|kinderwagen|rollator|hebel\b|\d+[- ]?gang|kinderfahrrad|e-?bike|fahrrad für|zoll fahrrad|scooter|roller"),
    C("table", r"\btable\b", fts="tisch OR esstisch OR küchentisch OR beistelltisch OR couchtisch",
      must=r"esstisch|küchentisch|beistelltisch|couchtisch|esszimmertisch", lo=30,
      exclude=r"decke|läufer|set\b|lampe|leuchte|bein\b|beine\b|gestell|platte\b|schutz|folie|kicker|tennis|bügel|wickel|schreib|"
              r"garten|camping|klapp|kinder", note="dining, kitchen, side and coffee tables"),
    C("glass_pane", r"\bglass pane\b|\breplacement glass\b", "none", note="cut to size: the shops only list appliance shelves and stove glass"),
    C("filling_valve", r"\bfilling valve\b|\bfill valve\b", fts="füllventil* OR schwimmerventil* OR fuellventil*", must=r"füllventil|schwimmerventil|fuellventil",
      exclude=r"dichtung|membran|ersatzteil-?set|aquarium|tränke"),
    C("hose", r"\b(connection|supply|flexible) hose\b", fts="anschlussschlauch* OR panzerschlauch* OR flexschlauch* OR zulaufschlauch*",
      must=r"anschlussschlauch|panzerschlauch|flexschlauch|zulaufschlauch", hi=100, exclude=r"druckluft|kompressor|gas\b|hydraulik|staubsauger|pool|schwimmbad|saug|garten|armatur|kessel|reservoir|set\b"),
    C("pipe_material", r"\binsulation\b|\bcopper pipe\b|\bfittings?\b|\btransition pieces?\b|\bconsumables\b|\bmaterial\b", "none",
      note="bundle of small material or a job; the shops list single pieces (see `search rohrisolierung*`, `search pressfitting*`)"),
    C("dryer", r"\b(condensation dryer|dehumidifier|drying equipment)\b", fts="bautrockner* OR luftentfeuchter*",
      must=r"bautrockner|luftentfeuchter", lo=40, exclude=ACCESSORY + r"|granulat|nachfüll|beutel|tabs|wäsche",
      note="purchase price; an invoice usually bills the rent"),
    C("paint", r"\bfacade paint\b|\bpaint\b", fts="fassadenfarbe*", must=r"fassadenfarbe", exclude=r"pinsel|rolle|abtön"),
    C("plaster", r"\bplaster\b", fts="putz OR unterputz OR fassadenputz OR oberputz", must=r"fassadenputz|oberputz|grundputz|kalkzementputz|reibeputz",
      exclude=r"kelle|profil|schiene|maschine|dose\b|schalter"),
    C("primer", r"\bpriming\b|\bprimer\b", fts="tiefengrund* OR putzgrund* OR grundierung*", must=r"tiefengrund|putzgrund|grundierung", exclude=r"pinsel|rolle|nagel|holz|metall|rost|make-?up|foundation|eyeshadow|adapter"),
]

TRADE_RATE = [  # invoice trade -> (rate tag, word in the call-out rows)
    (r"plumb|leak|drying|heating|sanit", "rate_plumber", "Installateur"),
    (r"electr", "rate_electrician", "Elektriker"),
    (r"paint|plaster", "rate_painter", "Maler"),
    (r"carpent|joiner|glaz|furniture|restor", "rate_carpenter", "Tischler"),
]


# ---------------------------------------------------------------------------------------------------------------- query

_con = None


def con():
    global _con
    if _con is None:
        _con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
    return _con


def _quant(vals):
    v = sorted(vals)
    if len(v) >= 4:
        q = statistics.quantiles(v, n=4)
        return round(q[0], 2), round(statistics.median(v), 2), round(q[2], 2)
    return round(v[0], 2), round(statistics.median(v), 2), round(v[-1], 2)


def _trade(trade, text):
    for pat, tag, word in TRADE_RATE:
        if re.search(pat, text, I):          # the line itself says the trade ("Painter hours")
            return tag, word
    for pat, tag, word in TRADE_RATE:        # else the first trade named on the invoice
        if re.search(pat, trade or "", I):
            return tag, word
    return "rate_all_trades", ""


USED_HOSTS = ("www.ebay.de", "www.hood.de")  # marketplaces with used goods and spare parts: not a new-for-old price


def search(fts, must="", exclude="", lo=0.0, hi=20000.0, limit=50000, used=False):
    """Offers matching an FTS5 query and the filters: [(price, name, host)]. used=True keeps the second-hand marketplaces."""
    rows = con().execute(
        "SELECT o.price, o.name, o.host FROM offers_fts f JOIN offers o ON o.id = f.rowid "
        "WHERE offers_fts MATCH ? AND o.price BETWEEN ? AND ? LIMIT ?", (fts, lo, hi, limit)).fetchall()
    m = re.compile(must, I) if must else None
    x = re.compile(exclude, I) if exclude else None
    return [r for r in rows if (not m or m.search(r[1])) and not (x and x.search(r[1])) and (used or r[2] not in USED_HOSTS)]


def _goods(c, rows, qty, conf):
    if len(rows) < 5:
        return None
    hosts = {r[2] for r in rows}
    p25, p50, p75 = _quant([r[0] for r in rows])
    mid = min(rows, key=lambda r: abs(r[0] - p50))
    return {"concept": c.id, "kind": "goods", "confidence": conf if len(hosts) >= 2 else "low", "unit_p25": p25, "unit_p50": p50,
            "unit_p75": p75, "qty": qty, "p25": round(p25 * qty, 2), "p50": round(p50 * qty, 2), "p75": round(p75 * qty, 2),
            "n": len(rows), "shops": len(hosts), "source": "wdc 2024-12 (German web shops, new goods, gross)",
            "example": f"{mid[1][:70]} ({mid[0]:.0f} EUR, {mid[2]})", "note": c.note}


def _rate(c, text, qty, unit, trade):
    tag, _ = _trade(trade, text)
    rows = con().execute("SELECT price, item, source, region FROM refs WHERE tag = ? AND unit = 'h'", (tag,)).fetchall()
    if c.level:
        lvl = [r for r in rows if re.search(c.level, r[1], I)]
        # sources without a master / journeyman split (min-max ranges) stay in for both levels
        rows = lvl + [r for r in rows if not re.search(r"Meister|Geselle", r[1], I)] if lvl else rows
    if not rows:
        return None
    by = [r for r in rows if re.search(r"bayern|münchen|muenchen", r[3], I)]
    rows = by or rows
    p25, p50, p75 = _quant([r[0] for r in rows])
    out = {"concept": c.id, "kind": "rate", "confidence": "ok", "unit_p25": p25, "unit_p50": p50, "unit_p75": p75,
           "n": len(rows), "shops": len({r[2] for r in rows}), "source": ", ".join(sorted({r[2] for r in rows})) + " (EUR/h gross)",
           "example": f"{rows[0][1]} ({rows[0][0]:.0f} EUR/h)", "note": tag}
    if re.match(r"h(rs?|ours?)?\.?$", unit or "", I) and qty:
        out |= {"qty": qty, "p25": round(p25 * qty, 2), "p50": round(p50 * qty, 2), "p75": round(p75 * qty, 2)}
    else:  # a flat-rate labour line: the data has the rate, not the hours
        out |= {"qty": None, "p25": None, "p50": None, "p75": None, "confidence": "rate only",
                "note": tag + "; hours are not on the invoice, so there is no line total"}
    return out


def _travel(c, text, trade):
    _, word = _trade(trade, text)
    rows = con().execute("SELECT price, item, source FROM refs WHERE unit = 'Anfahrt' AND item LIKE '%Nahbereich%'").fetchall()
    own = [r for r in rows if word and word in r[1]]
    rows = own or rows
    if not rows:
        return None
    p25, p50, p75 = _quant([r[0] for r in rows])
    return {"concept": c.id, "kind": "travel", "confidence": "ok" if own else "low", "unit_p25": p25, "unit_p50": p50, "unit_p75": p75,
            "qty": 1, "p25": p25, "p50": p50, "p75": p75, "n": len(rows), "shops": 1, "source": "clean_invoice (call-out, near zone, gross)",
            "example": f"{rows[0][1]} ({rows[0][0]:.0f} EUR)", "note": "min-max range of the source" + ("" if own else "; all trades")}


def _fee(c, qty):
    rows = con().execute("SELECT price, item, unit, source FROM refs WHERE tag = ? AND source LIKE 'awm%' AND price > 0", (c.tag,)).fetchall()
    m3, t = c.amount
    vals = []
    for price, item, unit, src in rows:
        if re.search(r"1000\s*kg", unit):
            vals.append((price * t, item))
        elif re.search(r"m3|m³", unit):
            vals.append((price * m3, item))
    if not vals:
        return None
    p50 = round(statistics.median(v for v, _ in vals), 2)
    return {"concept": c.id, "kind": "fee", "confidence": "assumed amount", "unit_p25": p50, "unit_p50": p50, "unit_p75": p50, "qty": qty,
            "p25": round(p50 * qty, 2), "p50": round(p50 * qty, 2), "p75": round(p50 * qty, 2), "n": len(vals), "shops": 1,
            "source": "awm_muenchen (recycling-centre fee, gross)", "example": vals[0][1],
            "note": f"assumes {m3:g} m³ / {t:g} t per piece; the fee covers the waste only, not collection or labour"}


STOP = set("the a an of and or for to in on at from with incl including new old damaged surge small large per by is was that "
           "this same one two replacement supply standard comparable original affected".split())


def _fallback(text, qty):
    words = [w for w in re.findall(r"[a-zA-ZäöüÄÖÜß]{3,}", text) if w.lower() not in STOP][:4]
    if not words:
        return None
    rows = search(" AND ".join(f'"{w}"' for w in words), exclude=ACCESSORY)
    c = C("fulltext", "", note="no concept; plain full-text match on: " + " ".join(words))
    return _goods(c, rows, qty, "low")


def lookup(text, qty=1.0, unit="pcs", trade=""):
    """Price view for one invoice line, or None. Totals are gross EUR for the whole line."""
    qty = qty or 1.0
    head = re.sub(r"\(.*?\)|\(.*$", " ", text).strip() or text   # remarks in brackets do not pick the concept
    for c in CONCEPTS:
        if not re.search(c.en, head, I):
            continue
        if c.kind == "none":
            return {"concept": c.id, "kind": "none", "confidence": "none", "p50": None, "note": c.note}
        if c.kind == "rate":
            return _rate(c, text, qty, unit, trade)
        if c.kind == "travel":
            return _travel(c, text, trade)
        if c.kind == "fee":
            return _fee(c, qty)
        return _goods(c, search(c.fts, c.must, c.exclude, c.lo, c.hi), qty, "ok")
    return _fallback(head, qty)


def fmt(text, r):
    if r is None:
        return f"{text[:60]:<60} no match"
    if r.get("p50") is None:
        extra = f"{r['unit_p50']:.0f} EUR/h ({r['unit_p25']:.0f}-{r['unit_p75']:.0f})" if r["kind"] == "rate" else "no price"
        return f"{text[:60]:<60} {extra}  [{r['concept']}: {r['note']}]"
    return (f"{text[:60]:<60} {r['p50']:>8.0f} EUR ({r['p25']:.0f}-{r['p75']:.0f})  [{r['concept']}, {r['confidence']}, "
            f"n={r['n']}, {r['shops']} sources] e.g. {r['example']}")


def main():
    a = sys.argv[1:]
    if not a or a[0] == "build":
        return build()
    opt = {a[i][2:]: a[i + 1] for i in range(2, len(a) - 1, 2) if a[i].startswith("--")}
    if a[0] == "search":
        rows = search(a[1], opt.get("must", ""), opt.get("exclude", ""), float(opt.get("lo", 0)))
        if rows:
            p25, p50, p75 = _quant([r[0] for r in rows])
            print(f"{len(rows)} offers, {len({r[2] for r in rows})} shops, median {p50} (p25 {p25}, p75 {p75})")
        for r in sorted(rows)[:: max(1, len(rows) // 25)]:
            print(f"{r[0]:>9.2f}  {r[1][:90]}  [{r[2]}]")
        return
    t0 = time.perf_counter()
    r = lookup(a[1], float(opt.get("qty", 1)), opt.get("unit", "pcs"), opt.get("trade", ""))
    ms = (time.perf_counter() - t0) * 1000
    print(fmt(a[1], r))
    if "--json" in a:
        print(json.dumps(r, indent=1, ensure_ascii=False))
    print(f"({ms:.1f} ms, no LLM)")


if __name__ == "__main__":
    main()
