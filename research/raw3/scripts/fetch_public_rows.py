"""Fetch the PUBLIC leaderboard rows into a scratch dir OUTSIDE the repo (1 request/s). Contains no data itself.
usage: python3 -I research/raw3/scripts/fetch_public_rows.py /private/tmp/<scratch>/lb
Only the organisers' public leaderboard endpoints are read (no key, no game API). The script refuses any output directory
that is not under /private/tmp or /tmp, so nothing about other teams can land in the repo."""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path
BASE = "https://c2f.public.quantco.cloud/leaderboard/api"
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
assert str(out.resolve()).startswith(("/private/tmp", "/tmp")), "refusing to cache inside a repo"
last = [0.0]
def get(ep, **q):
    w = 1.05 - (time.monotonic() - last[0])
    if w > 0: time.sleep(w)
    url = f"{BASE}/{ep}?{urllib.parse.urlencode(q)}"
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "team-analysis/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                last[0] = time.monotonic(); return json.load(r)
        except Exception as e:
            print("retry", ep, repr(e)[:80], file=sys.stderr); time.sleep(2 * (i + 1)); last[0] = time.monotonic()
    return None
g = get("games", completed_only="true", page_size=1000)
done = sorted(x["id"] for x in g["items"] if x["status"] == "completed")
m = get("matrix", page=1, game_limit=200)
(out / "matrix.json").write_text(json.dumps(m))
teams = [t["team_name"] for t in m["items"]]
for gid in done:
    f = out / f"tx_{gid}.json"
    if f.exists(): continue
    rows = {}
    ok = True
    for t in teams:
        page = 1
        while True:
            d = get("transactions", game_id=gid, team=t, page=page)
            if d is None: ok = False; break
            for r in d["items"]:
                rows[(r["issuer"], r["reviewer"], r["line_item_index"])] = r
            if page >= d.get("total_pages", 1): break
            page += 1
    if ok:
        f.write_text(json.dumps(list(rows.values())))
        print("game", gid, "rows", len(rows), flush=True)
perf = {}
for t in teams:
    perf[t] = get("performance", team=t)
(out / "perf.json").write_text(json.dumps(perf))
print("done games", done)
