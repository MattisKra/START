"""Case-only historical retrieval and a bounded, cached price search."""
import json
import os
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

import requests

from claimbot import config

from .settlement import invoice_items


def earlier_jobs(items, directory, archive=None):
    match = re.fullmatch(r"case_(\d+)", Path(directory).name)
    if not match:
        return []
    cutoff = int(match[1])
    archive = archive or config.ROOT / "past-cases"
    def tokens(text):
        return set(re.findall(r"[a-z]{3,}", text.lower())) - {
            "the", "and", "for", "with", "from", "including", "incl", "damage"}
    terms = [(tokens(i.description), i.unit.casefold()) for i in items]
    candidates = []
    frequency = Counter()
    for path in sorted(archive.glob("case_*/invoice.txt")):
        case_id = re.fullmatch(r"case_(\d+)", path.parent.name)
        if not case_id or int(case_id[1]) >= cutoff:
            continue
        try:
            prior = invoice_items(path.read_text())
            description = (path.parent / "description.txt").read_text()[:1200]
        except (OSError, ValueError):
            continue
        for line in prior:
            words = tokens(line.description)
            candidates.append((path.parent.name, line, description, words))
            frequency.update(words)
    ranked = []
    for case_id, line, description, words in candidates:
        score = max(sum(1 / frequency[w] for w in t & words) / max(1, len(t | words))
                    * (1.25 if line.unit.casefold() == unit else 1) for t, unit in terms)
        if score:
            ranked.append((score, dict(case=case_id, position=line.position, task=line.description,
                                       billed_quantity=line.quantity, unit=line.unit, incident=description)))
    return [entry for _, entry in sorted(ranked, key=lambda pair: -pair[0])[:3]]


def lookup(query, cache, timeout):
    key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not key:
        raise ValueError("BRAVE_SEARCH_API_KEY is required for online lookup")
    cache.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(cache, timeout=1) as db:
        db.execute("CREATE TABLE IF NOT EXISTS quotes (query TEXT PRIMARY KEY, fetched REAL, evidence TEXT)")
        row = db.execute("SELECT evidence FROM quotes WHERE query=? AND fetched>?",
                         (query, time.time() - 86400 * 30)).fetchone()
        if row:
            return json.loads(row[0])
        response = requests.get("https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "country": "DE", "count": 3},
            headers={"X-Subscription-Token": key}, timeout=timeout)
        response.raise_for_status()
        hits = [dict(url=r["url"], title=r["title"], snippet=r.get("description", ""),
                     date=r.get("page_age")) for r in response.json().get("web", {}).get("results", [])]
        db.execute("INSERT OR REPLACE INTO quotes VALUES (?,?,?)", (query, time.time(), json.dumps(hits)))
        return hits
