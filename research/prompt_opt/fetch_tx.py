"""Download public leaderboard transactions for a game (GET only, >= 2 s between requests).

Usage: python3 -I fetch_tx.py GAME_ID
Writes data/tx_game_<id>.json (deduplicated list of transactions).
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://c2f.public.quantco.cloud/leaderboard/api/transactions"
OUR = "Kiebler Software Solutions"
OUT = Path(__file__).resolve().parent / "data"


def get(params: dict) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    time.sleep(2.1)
    return data


def fetch_team(game: int, team: str) -> list[dict]:
    items, page = [], 1
    while True:
        d = get({"game_id": game, "team": team, "page": page})
        items += d.get("items", [])
        if page >= d.get("total_pages", 1) or not d.get("items"):
            break
        page += 1
    return items


def main() -> None:
    game = int(sys.argv[1])
    ours = fetch_team(game, OUR)
    teams = sorted({t["issuer"] for t in ours} | {t["reviewer"] for t in ours})
    seen, allt = set(), []
    for t in ours:
        k = (t["issuer"], t["reviewer"], t["line_item_index"])
        if k not in seen:
            seen.add(k)
            allt.append(t)
    for team in teams:
        if team == OUR:
            continue
        for t in fetch_team(game, team):
            k = (t["issuer"], t["reviewer"], t["line_item_index"])
            if k not in seen:
                seen.add(k)
                allt.append(t)
    OUT.mkdir(exist_ok=True)
    (OUT / f"tx_game_{game}.json").write_text(json.dumps(allt, indent=1))
    print(f"game {game}: {len(teams)} teams, {len(allt)} transactions")


if __name__ == "__main__":
    main()
