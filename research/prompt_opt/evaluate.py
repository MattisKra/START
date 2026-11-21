"""Run candidate prompts through the real estimator + pricing pipeline and score them against t-bounds.

Usage (from repo root):
  uv run python research/prompt_opt/evaluate.py CANDIDATE [CANDIDATE ...] --games 1 2 --runs 2 [--workers 4]
  uv run python research/prompt_opt/evaluate.py --score-only        # rescore all saved runs, print table

A candidate is research/prompt_opt/candidates/<name>.py defining INSTRUCTIONS and optionally SCHEMA
(a pydantic CaseEstimate-compatible class). Raw LLM outputs go to runs_llm/<cand>__g<game>__r<k>.json,
so scoring can be changed without new LLM calls. Never touches the game API.
"""

import argparse
import importlib.util
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI  # noqa: E402

from claimbot import config  # noqa: E402
from claimbot.case import load_case  # noqa: E402
from claimbot.estimator import build_input  # noqa: E402
from claimbot.pricing import price_case  # noqa: E402
from claimbot.schema import CaseEstimate  # noqa: E402

OUR = "Kiebler Software Solutions"
CASES = {1: ROOT / "runs/extracted/game_1", 2: None}  # 2 filled in by case_dir()
OUTDIR = HERE / "runs_llm"


def case_dir(game: int) -> Path:
    cands = sorted((ROOT / "runs/extracted").glob(f"game_{game}*"), key=lambda p: p.stat().st_mtime)
    cands = [p for p in cands if p.name == f"game_{game}" or p.name.startswith(f"game_{game}_")]
    return cands[-1]


def load_candidate(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / "candidates" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.INSTRUCTIONS, getattr(mod, "SCHEMA", CaseEstimate)


def run_one(cand: str, game: int, k: int) -> Path:
    out = OUTDIR / f"{cand}__g{game}__r{k}.json"
    if out.exists():
        return out
    instructions, schema = load_candidate(cand)
    case = load_case(case_dir(game))
    client = OpenAI(api_key=config.OPENAI_KEY, timeout=120, max_retries=1)
    t0 = time.monotonic()
    resp = client.responses.parse(
        model=config.MODEL,
        instructions=instructions,
        input=build_input(case),
        reasoning={"effort": "medium"},
        text_format=schema,
    )
    est = resp.output_parsed
    rec = {
        "cand": cand, "game": game, "run": k,
        "latency_s": round(time.monotonic() - t0, 1),
        "usage": resp.usage.model_dump() if resp.usage else None,
        "estimate": est.model_dump(),
    }
    OUTDIR.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    print(f"done {out.name} in {rec['latency_s']}s", flush=True)
    return out


# ---------------------------------------------------------------- scoring

def load_bounds(game: int) -> dict:
    return json.loads((HERE / "data" / f"bounds_game_{game}.json").read_text())


def t_point(lo: float, hi) -> float:
    if hi is None:
        return lo * 1.25 if lo > 0 else float("nan")
    if lo <= 0:
        return hi / 2 if hi < 50 else 0.0  # all inflated charges rejected, none fair -> treat as ~0
    return math.sqrt(lo * hi)


def t_grid(lo: float, hi) -> list[float]:
    """t values spread log-uniformly over the bound interval (t is only known to lie in [lo, hi))."""
    if lo <= 0:
        return [0.0]  # every positive charge seen was inflated -> treat t as 0
    if hi is None:
        hi = lo * 1.5
    return [lo * (hi / lo) ** (i / 4) * (0.999 if i == 4 else 1) for i in range(5)]


def replay(a: float, b: float, line: dict) -> dict:
    """Our money on one line vs the other teams' revealed charges/limits, averaged over t in the bound interval."""
    outs = [replay_t(a, b, line, t) for t in t_grid(line["t_lo"], line["t_hi"])]
    return {k: sum(o[k] for o in outs) / len(outs) for k in outs[0]}


def replay_t(a: float, b: float, line: dict, t: float) -> dict:
    charges = {k: v for k, v in line["charges"].items() if k != OUR}
    brange = {k: v for k, v in line["b_range"].items() if k != OUR}
    cap = max(4 * t, 1e9)  # cap rarely binds for sane charges; ignore
    recv = pay = 0.0
    # we as issuer
    for r, (blo, bhi) in brange.items():
        bhi = float("inf") if bhi is None else bhi
        b_r = blo if bhi == float("inf") else (blo + bhi) / 2  # point guess for their b
        if a <= 0:
            continue
        if a <= b_r:
            recv += min(a, cap)
        elif a <= t:
            recv += 1.5 * a
    # we as reviewer
    for iss, ai in charges.items():
        if ai <= 0:
            continue
        if ai <= b:
            pay += min(ai, cap)
        elif ai <= t:
            pay += 1.5 * ai
    return {"recv": recv, "pay": pay, "net": recv - pay}


def score_run(rec: dict, bounds: dict) -> dict:
    est = CaseEstimate.model_validate(rec["estimate"]) if "lines" in rec["estimate"] else None
    prices = price_case(est)
    lines = []
    tot = {"net": 0.0, "recv": 0.0, "pay": 0.0}
    for p in prices:
        key = str(p.index + 1)
        if key not in bounds:
            continue
        bd = bounds[key]
        lo, hi = bd["t_lo"], bd["t_hi"]
        hi_f = float("inf") if hi is None else hi
        a_fair = "fair" if p.a <= lo else ("INFL" if p.a >= hi_f else "?")
        if p.a == 0:
            a_fair = "zero"
        b_ok = lo <= p.b < hi_f if lo > 0 else p.b < hi_f
        # log distance of the valid-median (times q) to interval
        med = p.t_median
        if lo > 0:
            if med < lo:
                ld = math.log(lo / max(med, 1e-6))
            elif med >= hi_f:
                ld = math.log(med / hi_f)
            else:
                ld = 0.0
        else:  # t ~ 0: penalize q*median via how much mass we put on t>0
            ld = None
        r = replay(p.a, p.b, bd)
        for k2 in tot:
            tot[k2] += r[k2]
        lines.append({"line": int(key), "a": p.a, "b": p.b, "med": med, "q": p.q, "a_status": a_fair,
                      "b_ok": b_ok, "logdist": ld, **r})
    return {"lines": lines, **tot}


def score_all() -> list[dict]:
    rows = []
    for f in sorted(OUTDIR.glob("*.json")):
        rec = json.loads(f.read_text())
        bfile = HERE / "data" / f"bounds_game_{rec['game']}.json"
        if not bfile.exists():
            continue
        s = score_run(rec, load_bounds(rec["game"]))
        rows.append({"cand": rec["cand"], "game": rec["game"], "run": rec["run"], **s})
    # reference: a = b = t_lo (charge the highest charge known to be fair, accept up to it)
    for bf in sorted((HERE / "data").glob("bounds_game_*.json")):
        game = int(bf.stem.split("_")[-1])
        bd = json.loads(bf.read_text())
        lines, tot = [], {"net": 0.0, "recv": 0.0, "pay": 0.0}
        for key, d in bd.items():
            x = d["t_lo"]
            r = replay(x, x, d)
            for k in tot:
                tot[k] += r[k]
            lines.append({"line": int(key), "a": x, "b": x, "med": x, "q": 1.0 if x > 0 else 0.0,
                          "a_status": "fair" if x > 0 else "zero", "b_ok": True, "logdist": 0.0 if x > 0 else None, **r})
        rows.append({"cand": "~ref_a=b=t_lo", "game": game, "run": 1, "lines": lines, **tot})
    return rows


def print_table(rows: list[dict]) -> str:
    out = []
    out.append("| cand | game | run | per line: a (status) / b (ok?) / med / q | net replay |")
    out.append("|---|---|---|---|---:|")
    for r in sorted(rows, key=lambda x: (x["cand"], x["game"], x["run"])):
        cells = "; ".join(
            f"L{l['line']}: a={l['a']:.0f}({l['a_status']}) b={l['b']:.0f}({'ok' if l['b_ok'] else 'X'}) "
            f"med={l['med']:.0f} q={l['q']:.2f}" for l in r["lines"])
        out.append(f"| {r['cand']} | {r['game']} | {r['run']} | {cells} | {r['net']:.0f} |")
    # summary per candidate
    out.append("")
    out.append("| cand | runs | mean net replay | fair charges | inflated charges | b in bounds | mean logdist (lines with t>0) |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    cands = sorted({r["cand"] for r in rows})
    for c in cands:
        rs = [r for r in rows if r["cand"] == c]
        ls = [l for r in rs for l in r["lines"]]
        n_fair = sum(l["a_status"] in ("fair",) for l in ls)
        n_infl = sum(l["a_status"] == "INFL" for l in ls)
        n_b = sum(l["b_ok"] for l in ls)
        lds = [l["logdist"] for l in ls if l["logdist"] is not None]
        games = sorted({r["game"] for r in rs})
        per_game = {g: sum(r["net"] for r in rs if r["game"] == g) / max(1, sum(r["game"] == g for r in rs)) for g in games}
        mean_net = sum(per_game.values())
        out.append(f"| {c} | {len(rs)} | {mean_net:.0f} ({', '.join(f'g{g}:{v:.0f}' for g, v in per_game.items())}) | "
                   f"{n_fair}/{len(ls)} | {n_infl}/{len(ls)} | {n_b}/{len(ls)} | "
                   f"{(sum(lds) / len(lds)) if lds else float('nan'):.2f} |")
    txt = "\n".join(out)
    print(txt)
    return txt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cands", nargs="*")
    ap.add_argument("--games", nargs="+", type=int, default=[1])
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--score-only", action="store_true")
    args = ap.parse_args()
    if not args.score_only:
        jobs = [(c, g, k) for c in args.cands for g in args.games for k in range(1, args.runs + 1)]
        with ThreadPoolExecutor(args.workers) as ex:
            futs = [ex.submit(run_one, *j) for j in jobs]
            for f in futs:
                try:
                    f.result()
                except Exception as e:  # keep going
                    print("ERROR", repr(e), flush=True)
    rows = score_all()
    txt = print_table(rows)
    (HERE / "results.md").write_text(txt + "\n")
    (HERE / "results.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
