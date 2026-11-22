#!/usr/bin/env python3
"""Step 1 of the price database: every German EUR offer from the WDC parts in raw/wdc/, not only the 7 tagged kinds.

Writes raw/wdc_all/<part>.tsv with host, price, name, url (one offer per line). Parts run in parallel.
The N-Quads are untrusted data: they are only streamed and parsed as text.

Run: python3 -I research/prices/db_extract.py
"""
import importlib.util
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW, OUT = HERE / "raw" / "wdc", HERE / "raw" / "wdc_all"


def _wdc():
    spec = importlib.util.spec_from_file_location("fetch_wdc", HERE / "fetch_wdc.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _Sink:
    """Stands in for the csv writer of fetch_wdc.process_page; keeps host, price, name, url."""

    def __init__(self, fh):
        self.fh, self.n = fh, 0

    def writerow(self, row):
        _, item, _, price, _, _, url, host, _ = row
        item = item.replace("\t", " ").replace("\n", " ").replace("\r", " ")
        self.fh.write(f"{host}\t{price}\t{item}\t{url}\n")
        self.n += 1


def part(fn):
    w = _wdc()
    w.classify = lambda name, host: "any"          # keep every product, the database decides at query time
    w.MIN_PRICE = 0.5
    dest = OUT / (fn[:-3] + ".tsv")
    if dest.exists():
        return fn, -1
    tmp = dest.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        sink = _Sink(fh)
        w.run_part(str(RAW / fn), sink, set(), {"any": 0})
    tmp.rename(dest)
    return fn, sink.n


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parts = sorted(f for f in os.listdir(RAW) if f.endswith(".gz"))
    with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as ex:
        for fn, n in ex.map(part, parts):
            print(fn, "skipped (exists)" if n < 0 else f"{n} offers", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
