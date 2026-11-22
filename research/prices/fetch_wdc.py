#!/usr/bin/env python3
"""Stream-filter WDC schema.org Product N-Quads (2024-12) into research/prices/norm/wdc.csv.

Usage (reads untrusted data, so always run isolated):
    python3 -I fetch_wdc.py [--download] [raw_dir] [out_csv]

--download fetches only the part files holding the listed German retailers (found via
Product_lookup.csv). Parts are never decompressed to disk; they are streamed through gzip.
"""
import csv, gzip, os, re, sys, urllib.request
from collections import defaultdict

LABEL = "2024-12"
BASE = "https://data.dws.informatik.uni-mannheim.de/structureddata/2024-12/quads/classspecific/Product/"
UA = "price-research-script"
HERE = os.path.dirname(os.path.abspath(__file__))
HOSTS = set("""otto.de otto-office.com mediamarkt.de saturn.de cyberport.de notebooksbilliger.de alternate.de
conrad.de expert.de euronics.de fahrrad.de bike-discount.de bike24.de rosebikes.de home24.de moebel.de
xxxlutz.de porta.de idealo.de geizhals.de ifixit.com ebay.de kaufland.de hifi-regler.de teufel.de pollin.de
hood.de""".split())
BIKE_HOSTS = ("bike24", "bike-discount", "rosebikes", "fahrrad")
MIN_PRICE = 5  # EUR; db_extract.py lowers it to keep small parts and cables
HDR = ["source", "item", "unit", "price_gross_eur", "region", "date", "url", "note", "tag"]

I = re.I
EXCL = re.compile(r"halter|kabel|fernbedienung|remote|hülle|huelle|folie|ständer|staender|stativ|ersatz|replacement|"
                  r"spare|adapter|tasche|\bcase\b|cover|\bstand\b|mount|bracket|netzteil|ladeger|charger|schraube|"
                  r"screw|aufkleber|sticker|vorhang|wandmontage|bügel|clip|antenne|reiniger|cleaning|dichtung|"
                  r"lüfter|akku|battery|tastatur|keyboard|scharnier|hinge|bezel|kappe|abdeckung|gutschein|"
                  r"reparatur|repair|bilderrahmen|brille|fotorahmen|schlüssel", I)
EXCL_DISPLAY = re.compile(r"hülle|huelle|schutzfolie|folie|tasche|reiniger|halter|\bcase\b|sleeve|bilderrahmen|\bram\b|\bssd\b|windows|prozessor|processor|dock|adapter|\d ?gb\b|intel|ryzen|\bcore\b|ghz|akku|laptop,|notebook,", I)
EXCL_BIKE = re.compile(r"bremsbel|bremsbeläge|brake ?pad|bremsscheibe|rotor|bremsleitung|bremsflüssigkeit|bremsfl|bremsklotz|"
                       r"bremszug|tasche|\bbag\b|pumpe|rahmenschutz|rahmenschloss|rahmenpolster|aufkleber|sticker|bilderrahmen|"
                       r"tür|fenster|schlüssel|kabel|halter|ständer|ersatz|brille|adapter|schraube|bolt|zugführung|auto|kfz|pkw|"
                       r"motorrad|anhänger|wohnwagen", I)
BIKE_CTX = re.compile(r"bike|fahrrad|\brad\b|mtb|gravel|rennrad|e-?bike|cycl|trekking|city ?rad|kinderrad|bmx|downhill|enduro|"
                      r"shimano|sram|magura|tektro|hope|formula|trp", I)

R = {
    "laptop_display": (re.compile(r"(display|bildschirm|screen|lcd|panel)", I),
                       re.compile(r"macbook|laptop|notebook|thinkpad|ideapad|latitude|xps|surface|ultrabook|a1(706|708|989|990|932|466|502|425|398)", I)),
    "bike_brake": (re.compile(r"scheibenbremse|disc ?brake|bremsset|brake ?set|bremshebel|brake ?lever|bremssattel|brake ?caliper|"
                              r"felgenbremse|v-?brake|rim ?brake|\bbremse\b|\bbremsen\b|\bbrakes?\b", I), None),
    "bike_frame": (re.compile(r"fahrradrahmen|rennradrahmen|bike ?frame|frameset|rahmenset|\brahmen\b|\bframe\b", I), None),
    "side_table": (re.compile(r"beistelltisch|side ?table|end ?table|couchtisch.*(satz|set)|beistell", I),
                   re.compile(r"massiv|eiche|buche|holz|wood|oak|beech|walnuss|walnut|esche|ahorn|kiefer|akazie|teak|nussbaum|mango", I)),
    "speaker": (re.compile(r"lautsprecher|soundbar|sound ?bar|heimkino|home ?cinema|speaker|surround|subwoofer|regalbox|standbox|"
                           r"hifi-?boxen|stereo-?set", I), None),
    "tv": (re.compile(r"fernseher|television|\btv\b|\boled\b|\bqled\b|smart-?tv|\bled-?tv\b|\bgoogle tv\b|\bfire tv\b|\bqned\b|\bneo qled\b", I), None),
    "laptop14": (re.compile(r"macbook (pro|air)|notebook|laptop|ultrabook|chromebook|thinkpad|ideapad|zenbook|vivobook|swift|"
                            r"gram|envy|spectre|elitebook|probook|latitude|inspiron|vostro|yoga|surface laptop", I),
                 re.compile(r"\b1[34]([.,]\d)?\s?(\"|”|''|zoll|inch|in\b|-inch|-zoll)|macbook air 13|macbook pro 14|"
                            r"\b13[.,]\d\b|\b14[.,]\d\b|\b(13|14)\s?(\"|”)", I)),
}
ORDER = ["laptop_display", "bike_brake", "bike_frame", "side_table", "speaker", "tv", "laptop14"]
TV_EXTRA_EXCL = re.compile(r"tv-?box|tv-?stick|receiver|dvb|set-?top|tv-?board|tv-?möbel|lowboard|tv-?schrank|tv-?tisch|tv-?kabel|"
                           r"notebook|laptop|macbook|streaming|spiegel|\bfire tv stick|chromecast|beamer|projektor|monitor|soundbar", I)
SIZE_IN = re.compile(r"(\d{2,3})(?:[.,]\d)?\s?(?:\"|”|''|zoll|inch|-inch|-zoll|in\b)", I)
LAPTOP_NEW_EXCL = re.compile(r"gebraucht|refurb|used|b-ware|generalüberholt|renewed|defekt", I)

LINE = re.compile(r'^(\S+) <([^>]+)> (.+) <([^>]+)>\s+\.\s*$')
PRED_KEEP = (b"/name>", b"/price>", b"/lowPrice>", b"/priceCurrency>", b"/offers>")


def classify(name, host):
    if LAPTOP_NEW_EXCL.search(name):
        return None
    for tag in ORDER:
        pat, extra = R[tag]
        if not pat.search(name):
            continue
        if extra is not None and not extra.search(name):
            continue
        if tag == "laptop_display":
            if EXCL_DISPLAY.search(name):
                continue
            return tag
        if tag in ("bike_brake", "bike_frame"):
            if EXCL_BIKE.search(name):
                continue
            if not (BIKE_CTX.search(name) or any(h in host for h in BIKE_HOSTS)):
                continue
            return tag
        if EXCL.search(name):
            continue
        if tag == "tv" and TV_EXTRA_EXCL.search(name):
            continue
        return tag
    return None


def parse_price(s):
    s = re.sub(r"[^\d.,]", "", s.strip())
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        a, b = s.rsplit(",", 1)
        s = a.replace(",", "") + "." + b if len(b) <= 2 else s.replace(",", "")
    elif s.count(".") > 1:
        a, b = s.rsplit(".", 1)
        s = a.replace(".", "") + "." + b if len(b) <= 2 else s.replace(".", "")
    elif "." in s and len(s.rsplit(".", 1)[1]) == 3:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def lit(o):
    if o.startswith('"'):
        e = o.rfind('"')
        return o[1:e].replace('\\"', '"').replace("\\n", " ").replace("\\t", " ")
    return None


def host_of(url):
    m = re.match(r"https?://([^/:?#]+)", url)
    return m.group(1).lower() if m else ""


def accept_host(host, url):
    if host.endswith(".de"):
        return True
    # German pages of other shops (e.g. ifixit.com/de, de.* subdomains)
    return bool(re.search(r"^de\.|/de(/|-de/|$)|/de-de/|/de_de/", host + url[url.find(host) + len(host):], I))


def process_page(url, host, g, out, seen, stats):
    names, price, cur, parent = g["name"], g["price"], g["cur"], g["parent"]
    for node, p in price.items():
        c = cur.get(node)
        de_host = host.endswith(".de")
        if c is not None:
            if c.strip().upper() not in ("EUR", "€"):
                continue
        elif not de_host:
            continue
        val = parse_price(p)
        if val is None or not (MIN_PRICE <= val <= 20000):
            continue
        name, n, depth = names.get(node), node, 0
        while not name and depth < 3:
            n = parent.get(n)
            if n is None:
                break
            name = names.get(n)
            depth += 1
        if not name:
            continue
        name = " ".join(name.split())
        tag = classify(name, host)
        if not tag:
            continue
        key = (url, round(val, 2))
        if key in seen:
            continue
        seen.add(key)
        item = name[:200]
        if tag == "tv":
            m = SIZE_IN.search(name)
            if m:
                item += f" [{m.group(1)} inch]"
        out.writerow(["wdc", item, "pcs", f"{val:.2f}", "DE", LABEL, url, host, tag])
        stats[tag] += 1


def run_part(path, out, seen, stats):
    with gzip.open(path, "rb") as f:
        cur_url, host, g = None, "", None
        for raw in f:
            if not any(k in raw for k in PRED_KEEP):
                continue
            m = LINE.match(raw.decode("utf-8", "replace"))
            if not m:
                continue
            s, p, o, url = m.groups()
            if url != cur_url:
                if g is not None:
                    process_page(cur_url, host, g, out, seen, stats)
                cur_url, host = url, host_of(url)
                g = None if not accept_host(host, url) else {"name": {}, "price": {}, "cur": {}, "parent": {}}
            if g is None:
                continue
            pn = p.rsplit("/", 1)[-1]
            if pn == "name":
                v = lit(o)
                if v and s not in g["name"]:
                    g["name"][s] = v
            elif pn in ("price", "lowPrice"):
                v = lit(o)
                if v is not None and s not in g["price"]:
                    g["price"][s] = v
            elif pn == "priceCurrency":
                v = lit(o)
                if v:
                    g["cur"][s] = v
            elif pn == "offers" and not o.startswith('"'):
                g["parent"][o] = s
        if g is not None:
            process_page(cur_url, host, g, out, seen, stats)


def download(raw_dir):
    import io
    req = urllib.request.Request(BASE + "Product_lookup.csv", headers={"User-Agent": UA})
    parts = set()
    with urllib.request.urlopen(req) as r:
        for row in csv.DictReader(io.TextIOWrapper(r, encoding="utf-8")):
            if row["pld"] in HOSTS:
                parts.add(row["file_lookup"])
    for p in sorted(parts):
        dest = os.path.join(raw_dir, p)
        if os.path.exists(dest):
            continue
        req = urllib.request.Request(BASE + p, headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as r, open(dest, "wb") as w:
            while chunk := r.read(1 << 20):
                w.write(chunk)
        print("downloaded", p, file=sys.stderr)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    raw_dir = args[0] if args else os.path.join(HERE, "raw", "wdc")
    out_csv = args[1] if len(args) > 1 else os.path.join(HERE, "norm", "wdc.csv")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    if "--download" in sys.argv:
        download(raw_dir)
    seen, stats = set(), defaultdict(int)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HDR)
        for fn in sorted(os.listdir(raw_dir)):
            if fn.endswith(".gz"):
                run_part(os.path.join(raw_dir, fn), w, seen, stats)
                print("done", fn, dict(stats), file=sys.stderr)


if __name__ == "__main__":
    main()
