"""Fetch every team's transaction rows for all completed games from the organisers' PUBLIC leaderboard endpoints.

    python3 -I research/raw4/scripts/fetch_field.py OUT_DIR        # OUT_DIR must be OUTSIDE the repo (e.g. under /private/tmp)

Contains no data. Output (other teams' rows) goes to OUT_DIR only and must never be copied into the repo.
Same endpoints the leaderboard page uses, no key, at most 1 request per second, incremental (completed games already on disk are skipped).
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://c2f.public.quantco.cloud/leaderboard/api"
_last = [0.0]


def get(ep, **q):
    wait = 1.05 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    url = f"{BASE}/{ep}?{urllib.parse.urlencode(q)}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "team-analysis/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                _last[0] = time.monotonic()
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            _last[0] = time.monotonic()
            print(f"  ! {ep} {q}: {e!r} (try {attempt + 1}/3)", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    return None


def main():
    out = Path(sys.argv[1]).resolve()
    repo = Path(__file__).resolve().parents[3]
    assert repo not in out.parents and out != repo, "OUT_DIR must be outside the repo"
    out.mkdir(parents=True, exist_ok=True)
    g = get("games", completed_only="true", page_size=1000)
    done = sorted(x["id"] for x in g["items"] if x["status"] == "completed")
    (out / "games.json").write_text(json.dumps(g))
    m = get("matrix", page=1, game_limit=200)
    (out / "matrix.json").write_text(json.dumps(m))
    teams = [t["team_name"] for t in m["items"]]
    print(f"completed games {done}; {len(teams)} teams")
    for gid in done:
        f = out / f"tx_g{gid}.json"
        if f.exists():
            continue
        rows = {}
        for t in teams:
            page = 1
            while True:
                d = get("transactions", game_id=gid, team=t, page=page)
                if not d:
                    break
                for r in d["items"]:
                    rows[(r["issuer"], r["reviewer"], r["line_item_index"])] = r
                if page >= d.get("total_pages", 1):
                    break
                page += 1
        f.write_text(json.dumps(list(rows.values())))
        print(f"  game {gid}: {len(rows)} distinct rows")
    perf = {}
    for t in teams:
        perf[t] = get("performance", team=t)
    (out / "performance.json").write_text(json.dumps(perf))


if __name__ == "__main__":
    main()
