"""Reviewer cost of past rounds under b = k x our logged median (valid lines only), for several k.
Rows of other teams are read from the public leaderboard into memory only.

  uv run python research/ensemble_analysis/limit_sim.py 12 13 14 15 16 --k 0.55 0.9
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from claimbot import refs  # noqa: E402

US = "Kiebler Software Solutions"


def rows_of(game: int) -> list[dict]:
    teams = [t["team_name"] for t in refs._get("matrix", page=1, game_limit=20)["items"]]
    seen = {}
    for team in teams:
        page = 1
        while True:
            d = refs._get("transactions", game_id=game, team=team, page=page)
            for r in d.get("items", []):
                seen[(r["issuer"], r["reviewer"], r["line_item_index"])] = r
            if page >= d.get("total_pages", 1) or not d.get("items"):
                break
            page += 1
    return list(seen.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("games", nargs="+", type=int)
    ap.add_argument("--k", nargs="+", type=float, default=[0.55, 0.9])
    args = ap.parse_args()
    logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
    tot = defaultdict(lambda: [0.0, 0.0])
    tot_act = 0.0
    for g in args.games:
        rows = rows_of(g)
        sub = {s["index"] + 1: s for s in logs[str(g)]["submitted"]}
        charge, fair = {}, {}  # (issuer, line) -> charge, True/False/None
        for r in rows:
            key = (r["issuer"], r["line_item_index"])
            if r["accepted"]:
                charge[key] = max(charge.get(key, 0.0), r["amount"])
        for r in rows:
            key = (r["issuer"], r["line_item_index"])
            if not r["accepted"]:
                if r["amount"] > 0:
                    charge[key], fair[key] = r["amount"] / 1.5, True
                else:
                    fair[key] = False
        actual = sum(r["amount"] for r in rows if r["reviewer"] == US)
        tot_act += actual
        out = []
        for k in args.k:
            lo = hi = 0.0
            for (iss, line), a in charge.items():
                if iss == US or a <= 0 or line not in sub:
                    continue
                s = sub[line]
                b = k * s["t_median"] if s["q"] >= 2 / 3 else 0.0
                f = fair.get((iss, line))  # None: accepted by every reviewer, fairness unknown
                if a <= b:
                    lo += a; hi += a
                elif f is True:
                    lo += 1.5 * a; hi += 1.5 * a
                elif f is None:
                    hi += 1.5 * a
            tot[k][0] += lo; tot[k][1] += hi
            out.append(f"k={k:.2f}: {lo:8.0f}" + (f"..{hi:.0f}" if hi - lo > 1 else ""))
        print(f"game {g:2d}  actual cost {actual:8.0f}   " + "   ".join(out))
    print(f"sum      actual cost {tot_act:8.0f}   " + "   ".join(f"k={k:.2f}: {v[0]:8.0f}" + (f"..{v[1]:.0f}" if v[1] - v[0] > 1 else "") for k, v in tot.items()))


if __name__ == "__main__":
    main()
