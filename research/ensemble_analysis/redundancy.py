"""Which ensemble members are redundant? Cost per member, similarity between members, and reduced ensembles.

Usage (repo root):  uv run python research/ensemble_analysis/redundancy.py
Reads the full-ensemble run logs under runs/ (one per game) and the t-bounds of games 1-4 from
research/prompt_opt/data. Bounds for later games are derived in memory from the public leaderboard
(GET only, 2 s between requests, nothing written to disk). Makes no LLM calls and never touches the game API.
"""

import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research/prompt_opt"))

import evaluate as E  # noqa: E402
from claimbot import ensemble  # noqa: E402
from claimbot.schema import CaseEstimate  # noqa: E402

OUR = "Kiebler Software Solutions"
LOGS = {
    1: "runs/20261121-144400_game_1_ensemble.json",
    2: "runs/20261121-144429_game_2_ensemble.json",
    3: "runs/20261121-144500_game_3_ensemble.json",
    4: "runs/20261121-144031_game4_ensemble.json",
    5: "runs/20261121-145533_game_5_ensemble.json",
}
for extra in sorted((ROOT / "runs").glob("*_game[0-9]*_ensemble.json")):  # live rounds from game 6 on
    n = int(extra.name.split("_game")[1].split("_")[0])
    if n >= 6:
        LOGS[n] = str(extra.relative_to(ROOT))

# USD per 1M tokens: (input, cached input, output). Anthropic from the SDK reference, OpenAI from the pricing page.
PRICE = {
    "claude-fable-5-2": (8.0, 0.20, 40.0),
    "claude-opus-5-5": (4.0, 0.20, 20.0),
    "claude-sonnet-5-5": (2.0, 0.10, 10.0),
    "gpt-6.2-sol": (2.0, 0.10, 10.0),
    "gpt-6.1-terra": (1.0, 0.05, 5.0),
}
SEARCH_USD = 0.01  # per web search call, both providers


def cost(meta: dict) -> float:
    p_in, p_cached, p_out = PRICE[meta["model"]]
    u = meta["usage"]
    if meta["model"].startswith("claude"):
        cached = u.get("cache_read_input_tokens") or 0
        fresh = u["input_tokens"]
    else:
        cached = (u.get("input_tokens_details") or {}).get("cached_tokens") or 0
        fresh = u["input_tokens"] - cached
    return (fresh * p_in + cached * p_cached + u["output_tokens"] * p_out) / 1e6 + SEARCH_USD * (meta.get("web_searches") or 0)


def weight(name: str) -> float:
    model, rest = name.split("/")
    effort = rest.replace("+web", "")
    return ensemble.SIZE_WEIGHT[model] * ensemble.EFFORT_WEIGHT[effort] * (ensemble.WEB_WEIGHT if rest.endswith("+web") else 1.0)


def live_bounds(game: int) -> dict:
    """Same rules as research/prompt_opt/bounds.py, from rows held in memory only."""
    def get(path: str, **params) -> dict:
        url = f"https://c2f.public.quantco.cloud/leaderboard/api/{path}?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
        time.sleep(2.1)
        return d

    teams = [t["team_name"] for t in get("matrix", page=1, game_limit=20)["items"]]
    seen = {}
    for team in teams:  # the endpoint requires a team; every row shows up for its issuer and its reviewer
        page = 1
        while True:
            d = get("transactions", game_id=game, team=team, page=page)
            for r in d.get("items", []):
                seen[(r["issuer"], r["reviewer"], r["line_item_index"])] = r
            if page >= d.get("total_pages", 1) or not d.get("items"):
                break
            page += 1
    rows = list(seen.values())
    by_line = defaultdict(list)
    for t in rows:
        by_line[t["line_item_index"]].append(t)
    out = {}
    for line, rs in sorted(by_line.items()):
        charges, acc = {}, defaultdict(set)
        for r in rs:
            if not r["accepted"] and r["amount"] > 0:
                charges[r["issuer"]] = round(r["amount"] / 1.5, 2)
            if r["accepted"]:
                acc[r["issuer"]].add(round(r["amount"], 2))
        for iss, am in acc.items():
            charges.setdefault(iss, max(am))
        lo, hi = 0.0, float("inf")
        b_lo, b_hi = defaultdict(float), defaultdict(lambda: float("inf"))
        for r in rs:
            a = charges.get(r["issuer"], 0.0)
            if not r["accepted"] and r["amount"] > 0:
                lo = max(lo, a)
            elif not r["accepted"] and r["amount"] == 0 and a > 0:
                hi = min(hi, a)
            if r["accepted"]:
                b_lo[r["reviewer"]] = max(b_lo[r["reviewer"]], a)
            else:
                b_hi[r["reviewer"]] = min(b_hi[r["reviewer"]], a)
        out[str(line)] = {
            "t_lo": lo, "t_hi": None if hi == float("inf") else hi, "charges": charges,
            "b_range": {k: [b_lo[k], None if b_hi[k] == float("inf") else b_hi[k]] for k in set(b_lo) | set(b_hi)},
        }
    return out


def load():
    games = {}
    for g, f in LOGS.items():
        d = json.loads((ROOT / f).read_text())
        ms = {}
        for m in d["members"]:
            if m["member"].split("/")[0] not in PRICE:
                continue  # Luna, removed from the ensemble
            ms[m["member"]] = {
                "est": CaseEstimate.model_validate(m["estimate"]),
                "prices": {p["index"]: p for p in m["prices"]},
                "meta": m["meta"],
            }
        try:
            bd = E.load_bounds(g)
        except FileNotFoundError:
            bd = live_bounds(g)
        games[g] = {"members": ms, "bounds": bd}
    return games


def combined(game: dict, names) -> dict:
    res = [(game["members"][n]["est"], weight(n)) for n in names if n in game["members"]]
    return {p.index: p for p in ensemble.combine(res)} if res else {}


def logdist(med: float, lo: float, hi) -> float:
    if med <= 0:
        return float("nan")
    if med < lo:
        return math.log(lo / med)
    if hi is not None and med >= hi:
        return math.log(med / hi)
    return 0.0


def score(games: dict, names) -> dict:
    """Replay net, price error on valid lines, q on valid and invalid lines, shift vs the full ensemble."""
    net, errs, qv, qi, shift = 0.0, [], [], [], []
    per_game = {}
    for g, game in games.items():
        full = combined(game, game["members"])
        sub = combined(game, names)
        gnet = 0.0
        for idx, p in sub.items():
            bd = game["bounds"].get(str(idx + 1))
            if full[idx].t_median > 0 and p.t_median > 0:
                shift.append(abs(math.log(p.t_median / full[idx].t_median)))
            if not bd:
                continue
            gnet += E.replay(p.a, p.b, bd)["net"]
            if bd["t_lo"] > 0:
                errs.append(logdist(p.t_median, bd["t_lo"], bd["t_hi"]))
                qv.append(p.q)
            else:
                qi.append(p.q)
        per_game[g] = gnet
        net += gnet
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")  # noqa: E731
    return {"net": net, "per_game": per_game, "err": mean([e for e in errs if e == e]), "qv": mean(qv), "qi": mean(qi), "shift": mean(shift)}


def main() -> None:
    games = load()
    all_names = sorted({n for g in games.values() for n in g["members"]}, key=lambda n: -weight(n))
    n_lines = sum(len(combined(g, g["members"])) for g in games.values())
    print(f"games {sorted(games)}, {n_lines} lines, {len(all_names)} members")
    for g, game in games.items():
        print(f"  game {g}: " + "; ".join(f"L{k} t in [{v['t_lo']:.0f}, {v['t_hi'] if v['t_hi'] is None else round(v['t_hi'])})" for k, v in sorted(game["bounds"].items())))

    # ---- 1. cost per member
    print("\n== 1. Cost per round (USD, mean over games), tokens and latency ==")
    costs = {}
    print(f"{'member':30s} {'w':>5} {'USD':>7} {'in tok':>8} {'out tok':>8} {'lat s':>6}")
    for n in all_names:
        metas = [g["members"][n]["meta"] for g in games.values() if n in g["members"]]
        costs[n] = sum(cost(m) for m in metas) / len(metas)
        print(f"{n:30s} {weight(n):5.2f} {costs[n]:7.3f} {sum(m['usage']['input_tokens'] for m in metas) / len(metas):8.0f} "
              f"{sum(m['usage']['output_tokens'] for m in metas) / len(metas):8.0f} {sum(m['latency_s'] for m in metas) / len(metas):6.1f}")
    total = sum(costs.values())
    print(f"{'all members':30s} {'':5} {total:7.3f}  -> {total * 95:.0f} USD for the ~95 remaining rounds")
    groups = defaultdict(float)
    for n, c in costs.items():
        groups[n.split("/")[0] + (" +web" if n.endswith("+web") else "")] += c
    for k, v in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  {k:28s} {v:7.3f}  {100 * v / total:4.0f}%")

    # ---- 2. similarity: residual of each member's log median against the full-ensemble median, per line
    resid = defaultdict(dict)
    for g, game in games.items():
        full = combined(game, game["members"])
        for n, m in game["members"].items():
            for idx, p in m["prices"].items():
                if p["t_median"] > 0 and full[idx].t_median > 0:
                    resid[n][(g, idx)] = math.log(p["t_median"] / full[idx].t_median)

    def corr(a: str, b: str):
        keys = sorted(set(resid[a]) & set(resid[b]))
        if len(keys) < 5:
            return None
        x, y = [resid[a][k] for k in keys], [resid[b][k] for k in keys]
        mx, my = sum(x) / len(x), sum(y) / len(y)
        sx = math.sqrt(sum((v - mx) ** 2 for v in x)); sy = math.sqrt(sum((v - my) ** 2 for v in y))
        return sum((u - mx) * (v - my) for u, v in zip(x, y)) / (sx * sy) if sx and sy else None

    def dist(a: str, b: str):
        keys = sorted(set(resid[a]) & set(resid[b]))
        return sum(abs(resid[a][k] - resid[b][k]) for k in keys) / len(keys) if keys else None

    print("\n== 2. Similarity of price estimates between members (deviation from the ensemble median, per line) ==")
    kinds = defaultdict(list)
    for a, b in combinations(all_names, 2):
        ma, ra = a.split("/"); mb, rb = b.split("/")
        c, d = corr(a, b), dist(a, b)
        if c is None:
            continue
        if ma == mb and ra.replace("+web", "") != rb.replace("+web", "") and ra.endswith("+web") == rb.endswith("+web"):
            kinds["same model, low vs medium"].append((c, d, a, b))
        elif ma == mb and ra.replace("+web", "") == rb.replace("+web", ""):
            kinds["same model and effort, plain vs web"].append((c, d, a, b))
        elif ma == mb:
            kinds["same model, other"].append((c, d, a, b))
        elif ma.startswith("claude") == mb.startswith("claude"):
            kinds["different model, same provider"].append((c, d, a, b))
        else:
            kinds["different provider"].append((c, d, a, b))
    for k, v in kinds.items():
        print(f"  {k:38s} pairs {len(v):3d}  mean corr {sum(x[0] for x in v) / len(v):+.2f}  mean |log ratio| {sum(x[1] for x in v) / len(v):.2f}")
    print("  most similar pairs:")
    allp = sorted((x for v in kinds.values() for x in v), key=lambda x: x[1])
    for c, d, a, b in allp[:10]:
        print(f"    {a:30s} {b:30s} corr {c:+.2f}  |log ratio| {d:.2f}")

    # ---- 3. reduced ensembles
    def sel(pred):
        return [n for n in all_names if pred(n.split("/")[0], n.split("/")[1].replace("+web", ""), n.endswith("+web"))]

    subsets = {
        "all 18 (current)": all_names,
        "without web members (10)": sel(lambda m, e, w: not w),
        "without low effort (9)": sel(lambda m, e, w: e == "medium"),
        "medium, no web (5)": sel(lambda m, e, w: e == "medium" and not w),
        "low, no web (5)": sel(lambda m, e, w: e == "low" and not w),
        "without Sonnet (16)": sel(lambda m, e, w: "sonnet" not in m),
        "without Opus (14)": sel(lambda m, e, w: "opus" not in m),
        "without Fable (14)": sel(lambda m, e, w: "fable" not in m),
        "without Sol (14)": sel(lambda m, e, w: "sol" not in m),
        "without Terra (14)": sel(lambda m, e, w: "terra" not in m),
        "without Sonnet, no web (8)": sel(lambda m, e, w: "sonnet" not in m and not w),
        "Fable+Terra+Opus+Sol medium (4)": sel(lambda m, e, w: "sonnet" not in m and e == "medium" and not w),
        "Fable+Terra+Opus medium (3)": sel(lambda m, e, w: ("fable" in m or "terra" in m or "opus" in m) and e == "medium" and not w),
        "Fable+Terra medium (2)": sel(lambda m, e, w: ("fable" in m or "terra" in m) and e == "medium" and not w),
        "Fable+Terra low+medium (4)": sel(lambda m, e, w: ("fable" in m or "terra" in m) and not w),
        "Fable+Terra+Sol low+medium (6)": sel(lambda m, e, w: ("fable" in m or "terra" in m or "sol" in m) and not w),
        "Terra+Sol low+medium (4)": sel(lambda m, e, w: ("terra" in m or "sol" in m) and not w),
        "Terra+Sol medium (2)": sel(lambda m, e, w: ("terra" in m or "sol" in m) and e == "medium" and not w),
        "Terra low+medium + Fable medium (3)": sel(lambda m, e, w: not w and ("terra" in m or ("fable" in m and e == "medium"))),
        "Fable medium only (1)": ["claude-fable-5-2/medium"],
        "Terra medium only (1)": ["gpt-6.1-terra/medium"],
    }
    print("\n== 3. Reduced ensembles (replay net against the other teams' revealed charges and limits) ==")
    gs = sorted(games)
    print(f"{'ensemble':38s} {'USD/rd':>7} {'net':>7} " + " ".join(f"{'g' + str(g):>6}" for g in gs) + f" {'|err|':>6} {'q|val':>6} {'q|inv':>6} {'shift':>6}")
    for name, names in subsets.items():
        s = score(games, names)
        c = sum(costs[n] for n in names)
        print(f"{name:38s} {c:7.2f} {s['net']:7.0f} " + " ".join(f"{s['per_game'][g]:6.0f}" for g in gs)
              + f" {s['err']:6.2f} {s['qv']:6.2f} {s['qi']:6.2f} {s['shift']:6.2f}")

    # ---- 4. each member alone and left out
    print("\n== 4. Each member: alone, and the ensemble without it ==")
    base = score(games, all_names)
    print(f"{'member':30s} {'USD':>6} {'alone net':>10} {'alone |err|':>11} {'net without':>12} {'change':>7}")
    for n in all_names:
        alone = score(games, [n])
        wo = score(games, [m for m in all_names if m != n])
        print(f"{n:30s} {costs[n]:6.3f} {alone['net']:10.0f} {alone['err']:11.2f} {wo['net']:12.0f} {wo['net'] - base['net']:+7.0f}")


if __name__ == "__main__":
    main()
