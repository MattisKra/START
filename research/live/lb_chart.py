"""Live chart of every team's cumulative score and rank per round (stdlib only, no keys).

    python3 -I research/live/lb_chart.py --open          # serves http://127.0.0.1:8377 and opens it

The leaderboard API sends no CORS headers, so a browser page cannot read it directly. This script serves
lb_chart.html and passes the data through on /api/data.

What it reads: only the organisers' PUBLIC leaderboard endpoints `matrix` (net score per team per completed game) and
`games` (schedule and status). Both hold completed games only, so nothing about a running round is read.
Load on the API: at most one refresh every --ttl seconds (default 15) however many browser tabs are open, and at least
1 s between two requests. Nothing is written to disk; the data lives in memory only.
"""
import argparse, json, os, threading, time, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = "https://c2f.public.quantco.cloud/leaderboard/api"
PAGE = Path(__file__).with_name("lb_chart.html")
_last = [0.0]

# Which of OUR approaches counted in which rounds: (first round, last round, approach, detail).
# The page shows this as colour bands. Colours follow the approach in order of first appearance.
PHASES = [
    (1, 2, "Single agent", "Luna, low and medium effort raced"),
    (3, 6, "Ensemble, changing line-ups", "12 members in game 3, 20 in game 4, 8 logged in game 5, 18 in game 6"),
    (7, 11, "Ensemble, final 8 members", "Fable, Opus, Sol, Terra at low and medium; charge 0.9x median, limit 0.5x median"),
    (12, 17, "Ensemble with price references", "Same 8 members plus price references from finished games; limit 0.9x median after game 12"),
    (18, 18, "Self-learning persistent agent", "The other algorithm, whole-euro charges such as 110, 1150, 12"),
    (19, 19, "Multi-agent setup", "Two Fable readers, Luna fallback, with price references"),
    (20, 20, "Self-learning persistent agent", "The multi-agent parser crashed and submitted nothing; whole-euro charges counted"),
    (21, 21, "Multi-agent setup", "With price references"),
    (22, 100, "Self-learning persistent agent", "A different submitter with whole-euro charges, same pattern as games 18 and 20"),
]


def get(ep, **q):
    wait = 1.05 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(f"{BASE}/{ep}?{urllib.parse.urlencode(q)}", headers={"User-Agent": "team-analysis/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    finally:
        _last[0] = time.monotonic()


def load():
    """One snapshot: per-team cells aligned with game_ids, plus the schedule."""
    game_ids, teams, page = [], [], 1
    while True:
        m = get("matrix", page=page, game_limit=200)
        game_ids = m["game_ids"]
        teams += [{"name": t["team_name"], "cells": t["cells"]} for t in m["items"]]
        if page >= m.get("total_pages", 1):
            break
        page += 1
    games = get("games", page_size=1000)["items"]
    return {"game_ids": game_ids, "teams": teams,
            "games": [{"id": g["id"], "start_time": g["start_time"], "status": g["status"]} for g in games]}


class Feed:
    """Caches the last snapshot. On an upstream error it keeps serving the old one and reports the error."""

    def __init__(self, ttl, extra):
        self.ttl, self.extra = ttl, extra
        self.lock, self.data, self.checked, self.fetched_at, self.error = threading.Lock(), None, None, None, None

    def snapshot(self):
        with self.lock:
            if self.checked is None or time.monotonic() - self.checked >= self.ttl:
                try:
                    self.data, self.fetched_at, self.error = load(), time.time(), None
                except Exception as e:  # noqa: BLE001
                    self.error = repr(e)[:200]
                self.checked = time.monotonic()
            return {**self.extra, **(self.data or {"game_ids": [], "teams": [], "games": []}),
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
    ap.add_argument("--port", type=int, default=8377)
    ap.add_argument("--team", default=os.getenv("CLAIMS_TEAM", "Kiebler Software Solutions"), help="team to highlight")
    ap.add_argument("--ttl", type=float, default=15, help="seconds between two refreshes from the API (min 5)")
    ap.add_argument("--marks", default="53.5,69.5,92.5",
                    help="rounds to mark with a dashed line, e.g. 53.5 = between rounds 53 and 54; '' for none")
    ap.add_argument("--mark-label", default="Compacted")
    ap.add_argument("--open", action="store_true", help="open the page in the browser")
    a = ap.parse_args()
    marks = [float(x) for x in a.marks.split(",") if x.strip()]
    phases = [{"from": f, "to": t, "name": n, "note": d} for f, t, n, d in PHASES]
    feed = Feed(max(a.ttl, 5), {"team": a.team, "marks": marks, "mark_label": a.mark_label, "phases": phases})
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), handler(feed))
    url = f"http://127.0.0.1:{a.port}/"
    print(f"live chart on {url}  (Ctrl+C stops it)", flush=True)
    if a.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
