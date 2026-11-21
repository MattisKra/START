"""Build benchmark labels from the public leaderboard for every completed game.

    python3 -I research/bench/build_labels.py --team "Kiebler Software Solutions"

For each completed game and each invoice line it writes one JSON line to research/bench/labels.jsonl:
  case            e.g. case_001 (game N uses case_N)
  line            invoice POS number (1-based, as on the leaderboard)
  t_lo, t_hi      bracket for the hidden fair value t: t_lo = highest charge that was rejected and paid 1.5x (fair),
                  t_hi = lowest charge that was rejected for 0 (inflated). t_hi null = no inflated charge seen.
  n_fair, n_inflated   how many distinct charges defined each side of the bracket (no team names, no per-team amounts)
  incoming        amounts of the charges WE received on this line: [{a, accepted, paid}] (our own rows; for replaying our b)
  our_a           our own charge (if readable)
Other teams' rows are read in memory only; the output contains no team names and no per-team data.
Reads the same public endpoints as the leaderboard page, 1 request/s, cached under research/data/live/.
Idempotent: games already in labels.jsonl are skipped unless --refresh.
"""
import argparse, importlib.util, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lb", ROOT / "research" / "live" / "lb_analyze.py")
lb = importlib.util.module_from_spec(spec); spec.loader.exec_module(lb)
OUT = ROOT / "runs" / "bench" / "labels.jsonl"   # gitignored: derived from other teams' rows, so never committed


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--team", required=True); ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    src = lb.Source()
    g = src.get("games", completed_only="true", page_size=1000)
    done = sorted(x["id"] for x in (g or {}).get("items", []) if x["status"] == "completed")
    have = set()
    if OUT.exists() and not a.refresh:
        have = {json.loads(l)["game"] for l in OUT.read_text().splitlines() if l.strip()}
    todo = [d for d in done if d not in have]
    print(f"completed games {done}; to label: {todo}")
    new = []
    for gid in todo:
        own = lb.tx_pages(src, gid, a.team, cache=True)
        if own is None:
            print(f"  game {gid}: no own rows"); continue
        teams = sorted({r["issuer"] for r in own} | {r["reviewer"] for r in own})
        allr = list(own)
        for t in teams:
            if t != a.team:
                allr += lb.tx_pages(src, gid, t, cache=False) or []
        bounds = lb.t_bounds(allr)
        iv = lb.issuer_view(own, a.team)
        for ln, (lo, hi, det) in bounds.items():
            inc = [dict(a=lb.a_hat(r["amount"], r["accepted"]) or 0.0, accepted=r["accepted"], paid=r["amount"])
                   for r in own if r["reviewer"] == a.team and r["line_item_index"] == ln]
            new.append(dict(game=gid, case=f"case_{gid:03d}", line=ln, t_lo=round(lo, 2), t_hi=None if hi == float("inf") else round(hi, 2),
                            n_fair=len(det["fair"]), n_inflated=len(det["inflated"]),
                            incoming=inc, our_a=iv.get(ln, {}).get("a"), source="leaderboard transactions, all teams"))
        print(f"  game {gid}: {sum(1 for n in new if n['game'] == gid)} lines labelled")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if new:
        with open(OUT, "a") as f:
            for n in new:
                f.write(json.dumps(n, ensure_ascii=False) + "\n")
    print(f"labels.jsonl now has {sum(1 for _ in open(OUT)) if OUT.exists() else 0} line labels")


if __name__ == "__main__":
    main()
