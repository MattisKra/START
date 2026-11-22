"""Merge all normalized price tables into research/prices/prices.csv.

Inputs:
  norm/*.csv                     written by the fetch scripts, columns COLS, prices already gross EUR
  raw/baupreislexikon/manual.csv filled in by hand in the browser (see plan), converted here

Run: python3 -I research/prices/normalize.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLS = ["source", "item", "unit", "price_gross_eur", "region", "date", "url", "note", "tag"]
VAT = 1.19


def num(s):
    s = (s or "").strip().replace("€", "").replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:          # 1.234,56
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def read_norm():
    rows = []
    for f in sorted((HERE / "norm").glob("*.csv")):
        with f.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                p = num(r.get("price_gross_eur"))
                if p is None or p <= 0:
                    continue
                rows.append({c: (r.get(c) or "").strip() for c in COLS} | {"price_gross_eur": f"{p:.2f}"})
    return rows


def read_bpl():
    f = HERE / "raw" / "baupreislexikon" / "manual.csv"
    rows = []
    if not f.exists():
        return rows
    with f.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            p = num(r.get("preis_mittel"))
            if p is None:
                continue
            menge = num(r.get("menge")) or 1.0
            net = (r.get("netto_brutto") or "").strip().lower().startswith("n")
            gross = p * menge * (VAT if net else 1.0)
            rows.append({
                "source": "baupreislexikon",
                "item": (r.get("position_bpl") or r.get("suchbegriff") or "").strip(),
                "unit": (r.get("einheit") or "").strip() or "line",
                "price_gross_eur": f"{gross:.2f}",
                "region": "PLZ " + (r.get("plz") or "").strip(),
                "date": "2026-11",
                "url": "https://www.baupreislexikon.de/",
                "note": f"min={r.get('preis_min')} max={r.get('preis_max')} menge={menge:g} {'net×1.19' if net else 'gross'}",
                "tag": f"bpl_c{int(num(r['fall'])):02d}_l{int(num(r['zeile']))}",
            })
    return rows


def main():
    rows = read_norm() + read_bpl()
    out = HERE / "prices.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    by = {}
    for r in rows:
        by.setdefault(r["source"], 0)
        by[r["source"]] += 1
    print(f"{len(rows)} rows -> {out.relative_to(HERE.parent.parent)}", by, file=sys.stderr)


if __name__ == "__main__":
    main()
