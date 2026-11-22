"""Map each test line (testset.json) to one price p per price source.

Fixed, reviewable keyword recipes instead of an LLM: same result on every run, no tokens.
A recipe is a sum of terms; each term is a statistic over rows of one source with a tag
(+ optional item regex), times a quantity. Every source value in prices.csv (e.g. awm_muenchen,
bsr_berlin, taifun_preisatlas) is scored as its own variant.

Assumptions that are not in any source (hours of work, waste volume) are named in ASSUME and
printed into the report, so a hit that only comes from an assumption is visible.

Run: python3 -I research/prices/match.py   (after normalize.py)
"""
import csv
import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Values not taken from any source. Kept small and explicit.
ASSUME = {
    "hours": {  # working hours per trade line for the hourly-rate sources
        "c03_l4": 3.0,   # dented/gouged solid-wood door frame: fill, sand, refinish
        "c03_l5": 2.0,   # scratched/chipped wooden shelf: sand, refinish
        "c04_l3": 1.0,   # "labour and sundries" at a bike shop
        "c07_l1": 4.0,   # thermal-imaging leak detection + replace burst fitting
        "c11_l5": 2.0,   # dented solid-wood side table
    },
    "green_waste_m3": 4.0,  # branches and foliage of one large garden tree (loose volume)
    "green_waste_t": 0.8,   # same, as mass (~0.2 t per loose m³)
    "root_ball_m3": 1.0,    # "single mass under one cubic metre", taken at the cap
    "root_ball_t": 0.8,     # root wood with soil attached
    "glass_m3": 0.05,       # one shed window pane
    "glass_t": 0.02,
}


@dataclass
class T:
    tag: str
    item_re: str | None = None
    qty: float = 1.0
    stat: str = "median"
    amount: str | None = None   # ASSUME key prefix: row unit per m³ -> x <key>_m3, per 1000 kg / t -> x <key>_t
    unit_re: str | None = None  # keep only rows whose unit matches
    fallback: str | None = None # tag to use when the source has no row for `tag`
    optional: bool = False      # add when present, do not drop coverage when missing


LAPTOP_14 = r"(?i)(pro\s*14|14[\"'”\s-]*(zoll|inch)?\s*.*pro|14\")"
MAC_ANY = r"(?i)(macbook|mac\b)"

# family -> line -> list of terms
RECIPES = {
    "wdc": {
        "c01_l1": [T("tv"), T("speaker")],
        "c09_l1": [T("speaker")],
        "c09_l4": [T("tv")],
        "c02_l1": [T("laptop_display", MAC_ANY)],
        "c05_l1": [T("laptop_display", MAC_ANY)],
        "c06_l1": [T("laptop_display", MAC_ANY)],
        "c04_l2": [T("bike_frame"), T("bike_brake")],
        "c11_l5": [T("side_table")],          # replacement price as a proxy for the repair
    },
    "apple": {
        "c02_l1": [T("laptop_display", LAPTOP_14)],
        "c02_l2": [T("laptop_housing", LAPTOP_14)],
        "c05_l1": [T("laptop_display", MAC_ANY), T("laptop_housing", MAC_ANY)],
        "c06_l1": [T("laptop_display", MAC_ANY), T("laptop_housing", MAC_ANY)],
    },
    "waste": {
        "c08_l2": [T("flat_glass", amount="glass")],
        "c08_l3": [T("green_waste", amount="green_waste")],
        "c08_l4": [T("root_stump", amount="root_ball")],
    },
    "rates": {  # hourly rate x assumed hours (+ travel flat rate where the source publishes one)
        lid: [T(tag, qty=ASSUME["hours"][lid], unit_re=r"^h$", fallback=fb),
              T(tag, unit_re=r"(?i)anfahrt", item_re=r"(?i)nahbereich", optional=True)]
        for lid, tag, fb in [("c03_l4", "rate_carpenter", None), ("c03_l5", "rate_carpenter", None),
                             ("c04_l3", "rate_bike", "rate_all_trades"), ("c07_l1", "rate_plumber", None),
                             ("c11_l5", "rate_carpenter", None)]
    },
    "baupreislexikon": {
        lid: [T(f"bpl_{lid}")] for lid in ["c03_l4", "c03_l5", "c07_l1", "c08_l2", "c08_l3", "c08_l4", "c11_l5"]
    },
}

FAMILY_OF = {  # source value prefix -> family
    "wdc": "wdc", "apple": "apple", "awm": "waste", "bsr": "waste", "srh": "waste", "awb": "waste",
    "taifun": "rates", "clean_invoice": "rates", "baupreislexikon": "baupreislexikon",
}


def family(source):
    for pre, fam in FAMILY_OF.items():
        if source.startswith(pre):
            return fam
    return None


def is_m3(unit):
    return bool(re.search(r"(?i)m³|m3|kubik", unit or ""))


def is_t(unit):
    return bool(re.search(r"(?i)1000\s*kg|/\s*t\b|tonne", unit or ""))


def convert(term, row):
    """Price of the whole amount, or None when the row's unit does not fit the assumed amount."""
    p = float(row["price_gross_eur"])
    if not term.amount:
        return p
    u = row["unit"]
    if is_t(u):
        return p * ASSUME[term.amount + "_t"]
    if is_m3(u):
        return p * ASSUME[term.amount + "_m3"]
    m = re.search(r"(?i)unter\s*(\d+)\s*kg", row["item"])
    if m and re.search(r"(?i)pauschal", u):  # flat fee for small loads only
        return p if ASSUME[term.amount + "_t"] * 1000 < float(m.group(1)) else None
    if re.search(r"(?i)st(ü|ue)ck|pcs|anlieferung", u):
        return p
    return None


def select(rows, term, tag):
    sel = [r for r in rows if r["tag"] == tag]
    if term.item_re:
        sel = [r for r in sel if re.search(term.item_re, r["item"])]
    if term.unit_re:
        sel = [r for r in sel if re.search(term.unit_re, r["unit"])]
    return sel


def pick(rows, term):
    sel = select(rows, term, term.tag)
    tag = term.tag
    if not sel and term.fallback:
        sel, tag = select(rows, term, term.fallback), term.fallback
    if not sel:
        return None
    # prefer Bavarian / Munich rows when the source has them (policyholder is in Munich)
    by = [r for r in sel if re.search(r"(?i)bayern|\bBY\b|münchen|munich|80331", r["region"])]
    sel = by or sel
    pairs = [(convert(term, r), r) for r in sel]
    pairs = [(p, r) for p, r in pairs if p is not None]
    if not pairs:
        return None
    sel = [r for _, r in pairs]
    vals = sorted(p for p, _ in pairs)
    st = {"median": statistics.median, "min": min, "max": max}[term.stat](vals)
    q = statistics.quantiles(vals, n=4) if len(vals) >= 4 else [vals[0], st, vals[-1]]
    return {
        "tag": tag, "n": len(vals), "stat": term.stat, "value": round(st, 2), "qty": term.qty,
        "p25": round(q[0], 2), "p75": round(q[2], 2),
        "example": {k: sel[0][k] for k in ("item", "unit", "price_gross_eur", "url")},
        "regional": bool(by),
    }


def main():
    rows = list(csv.DictReader((HERE / "prices.csv").open(encoding="utf-8")))
    test = json.loads((HERE / "testset.json").read_text())["lines"]
    variants = sorted({r["source"] for r in rows if family(r["source"])})
    out = {"assume": ASSUME, "matches": []}
    for src in variants:
        fam = family(src)
        srows = [r for r in rows if r["source"] == src]
        for line in test:
            terms = RECIPES[fam].get(line["id"])
            if not terms:
                continue
            parts = [(t, pick(srows, t)) for t in terms]
            if any(p is None and not t.optional for t, p in parts):
                continue  # source cannot price every required component -> no coverage
            parts = [p for _, p in parts if p is not None]
            p = sum(pt["value"] * pt["qty"] for pt in parts)
            out["matches"].append({"line": line["id"], "source": src, "family": fam, "p": round(p, 2), "parts": parts})
    (HERE / "matches.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{len(out['matches'])} matches over {len(variants)} source variants -> research/prices/matches.json")


if __name__ == "__main__":
    main()
