"""Live dashboard with two charts (stdlib only, no keys). Separate from research/live/lb_chart.py.

    python3 -I research/dash/dash.py --open          # serves http://127.0.0.1:8378 and opens it

Chart 1: our net result per round as a share of the round's total volume, against the context size the playing
         session had at the start of that round.
Chart 2: dollars moved between all teams per round, split into accepted charges and 1.5x penalties.

Where the numbers come from:
  * `matrix` (net per team per completed game) and `games` (schedule): refreshed every --ttl seconds.
  * `transactions`: the API has no "all rows of a game" call, only rows per team. A row has one issuer and one
    reviewer, so the rows of all teams but one hold every row of the game. That is (teams - 1) requests per
    game, done ONCE per completed game by a background thread and then kept.
  * context sizes: NOT in the API. They are read from context_sizes.json next to this file (see its "note").

Load on the API: one request at a time, at least --pace seconds apart (default 1.1), completed games only, so
nothing about a running round is read. The first start reads every completed game (about 11 requests each).

Data handling: other teams' rows are held in memory only while one game is summed. On disk (gitignored
runs/live/dash_volume.json) there are only per-game totals: no team names, no per-team amounts.
"""
import argparse, json, os, threading, time, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = "https://c2f.public.quantco.cloud/leaderboard/api"
HERE = Path(__file__).resolve().parent
PAGE = HERE / "dash.html"
CONTEXT = HERE / "context_sizes.json"
CACHE = HERE.parents[1] / "runs" / "live" / "dash_volume.json"   # gitignored; per-game totals only
_last = [0.0]
_pace = [1.1]


def get(ep, **q):
    """One GET, never sooner than the pace after the previous one. Only the worker thread calls this."""
    wait = _pace[0] - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(f"{BASE}/{ep}?{urllib.parse.urlencode(q)}", headers={"User-Agent": "team-analysis/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    finally:
        _last[0] = time.monotonic()


def game_volume(gid, teams):
    """Totals of one completed game from the rows of all teams but one. Team names stay in memory."""
    seen, lines = {}, set()
    for team in teams[:-1] if len(teams) > 1 else teams:
        page = 1
        while True:
            d = get("transactions", game_id=gid, team=team, page=page, page_size=1000)
            for r in d["items"]:
                seen[(r["issuer"], r["reviewer"], r["line_item_index"])] = (bool(r["accepted"]), float(r["amount"]))
                lines.add(r["line_item_index"])
            if page >= d.get("total_pages", 1):
                break
            page += 1
    acc = sum(a for ok, a in seen.values() if ok)
    pen = sum(a for ok, a in seen.values() if not ok)
    return {"accepted": round(acc, 2), "penalty": round(pen, 2), "rows": len(seen), "lines": len(lines),
            "n_accepted": sum(1 for ok, a in seen.values() if ok and a > 0),
            "n_penalty": sum(1 for ok, a in seen.values() if not ok and a > 0),
            "complete": len(seen) == len(teams) * (len(teams) - 1) * len(lines)}


class Feed:
    """Holds the latest snapshot. A single worker thread talks to the API; requests only read the snapshot."""

    def __init__(self, team, ttl):
        self.team, self.ttl = team, ttl
        self.lock = threading.Lock()
        self.game_ids, self.net, self.teams, self.games = [], {}, [], []
        self.zero_sum = {}
        self.volume, self.failed = {}, {}
        self.fetched_at, self.error, self.current = None, None, None
        if CACHE.exists():
            try:
                self.volume = {int(k): v for k, v in json.loads(CACHE.read_text()).items()}
            except Exception:  # noqa: BLE001  a broken cache is rebuilt from the API
                self.volume = {}

    def refresh(self):
        game_ids, rows, page = [], [], 1
        while True:
            m = get("matrix", page=page, game_limit=200)
            game_ids = m["game_ids"]
            rows += m["items"]
            if page >= m.get("total_pages", 1):
                break
            page += 1
        games = get("games", page_size=1000)["items"]
        mine = next((t["cells"] for t in rows if t["team_name"] == self.team), None)
        with self.lock:
            self.game_ids = game_ids
            self.teams = sorted(t["team_name"] for t in rows)
            self.net = {g: (mine[i] if mine and i < len(mine) else None) for i, g in enumerate(game_ids)}
            self.zero_sum = {g: round(sum((t["cells"][i] or 0) for t in rows if i < len(t["cells"])), 2) for i, g in enumerate(game_ids)}
            self.games = [{"id": g["id"], "start_time": g["start_time"], "status": g["status"]} for g in games]
            self.fetched_at = time.time()
            self.error = None if mine is not None else f"team '{self.team}' is not on the leaderboard"

    def next_missing(self):
        with self.lock:
            now = time.monotonic()
            for g in self.game_ids:
                if g not in self.volume and self.failed.get(g, 0) <= now:
                    return g, list(self.teams)
        return None, None

    def run(self):
        checked = None
        while True:
            try:
                if checked is None or time.monotonic() - checked >= self.ttl:
                    checked = time.monotonic()
                    self.refresh()
                gid, teams = self.next_missing()
                if gid is None:
                    time.sleep(1)
                    continue
                with self.lock:
                    self.current = gid
                try:
                    v = game_volume(gid, teams)
                except Exception as e:  # noqa: BLE001
                    with self.lock:
                        self.failed[gid] = time.monotonic() + 60      # try this game again in a minute
                        self.error = f"round {gid}: {e!r}"[:200]
                    continue
                with self.lock:
                    self.volume[gid] = v
                    self.current = None
                    CACHE.parent.mkdir(parents=True, exist_ok=True)
                    tmp = CACHE.with_suffix(".tmp")
                    tmp.write_text(json.dumps({str(k): self.volume[k] for k in sorted(self.volume)}))
                    os.replace(tmp, CACHE)
            except Exception as e:  # noqa: BLE001
                with self.lock:
                    self.error = repr(e)[:200]
                time.sleep(5)

    def snapshot(self):
        try:
            ctx = json.loads(CONTEXT.read_text())      # read on every request, so edits show up without a restart
        except Exception as e:  # noqa: BLE001
            ctx = {"error": f"context_sizes.json: {e!r}"[:200], "tokens": {}, "segments": []}
        with self.lock:
            ids = list(self.game_ids)
            return {"team": self.team, "n_teams": len(self.teams), "game_ids": ids,
                    "net": [self.net.get(g) for g in ids],
                    "zero_sum": [self.zero_sum.get(g) for g in ids],
                    "volume": [self.volume.get(g) for g in ids],
                    "loading": self.current, "missing": sum(1 for g in ids if g not in self.volume),
                    "games": self.games, "context": ctx, "pace": _pace[0],
                    "fetched_at": self.fetched_at, "error": self.error}


def handler(feed):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                self.reply(PAGE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/data":
                self.reply(json.dumps(feed.snapshot()).encode(), "application/json")
            else:
                self.send_error(404)

        def reply(self, body, ctype):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # quiet
            pass

    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8378)
    ap.add_argument("--team", default=os.getenv("CLAIMS_TEAM", "Kiebler Software Solutions"), help="our team")
    ap.add_argument("--ttl", type=float, default=20, help="seconds between two refreshes of the standings (min 10)")
    ap.add_argument("--pace", type=float, default=1.1, help="seconds between two API requests (min 1)")
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    a = ap.parse_args()
    _pace[0] = max(a.pace, 1.0)
    feed = Feed(a.team, max(a.ttl, 10))
    threading.Thread(target=feed.run, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), handler(feed))
    url = f"http://127.0.0.1:{a.port}/"
    print(f"dashboard on {url}  (Ctrl+C stops it)", flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
