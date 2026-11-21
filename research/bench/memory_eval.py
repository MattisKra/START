"""Forward evaluation of the case memory against what the settlements prove about the fair value t.

    uv run python research/bench/memory_eval.py [--games 2-9] [--variants clauses,neighbours,both] [--model M] [--effort low]
                                                 [--repeats 1] [--rebuild] [--dry]

For each settled game N in past-cases/ (with results.json):
  1. memory build --until N-1 --out runs/memory/bench/N   (only games < N, as live; enrichment calls are cached)
  2. one estimate WITHOUT memory ("none") and one per variant WITH the block (clauses = clause warnings only,
     neighbours = similar earlier lines only, both = the full block), same model, effort and prompt otherwise
  3. price every line with pricing.price_line (as live) and score it against the proven bracket for t:
       --labels leaderboard (default): our own rows merged with the bracket from ALL teams' public leaderboard rows
         (runs/bench/labels.jsonl from research/bench/build_labels.py; organisers' OK on 2026-11-21)
       --labels own: our own rows only (t_lo = our charge accepted as fair / a fair charge we rejected,
         t_hi = our charge rejected as inflated)
     Lines with neither bound are not scored.

Metrics per variant, over ALL scored lines (a variant without a block for a case counts with its "none" answer, so
abstaining cannot look good):
  b_short   EUR by which b lies below a proven t_lo  (we would reject a charge we KNOW is fair; it costs 1.5x)
  b_over    EUR by which b lies above a proven t_hi  (we would accept a charge we KNOW is inflated)
  a_over    lines where a > proven t_hi              (our charge would be rejected: 0 income)
  a_short   EUR by which a lies below a proven t_lo  (money left on the table)
  miss      lines where the median lies outside the proven interval
These are one-sided and coarse; they grow with every settled game. --dry prints the blocks and makes no LLM call.
Results go to runs/memory/eval/<stamp>.json (gitignored).
"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from claimbot import config, memory, memory_build, pricing  # noqa: E402
from claimbot.case import load_case  # noqa: E402

PARTS = dict(clauses=("warnings",), neighbours=("neighbours",), both=("warnings", "neighbours"))


def games_arg(s: str) -> list[int]:
    out = []
    for p in s.split(","):
        lo, _, hi = p.partition("-")
        out += list(range(int(lo), int(hi or lo) + 1))
    return out


def score(prices, obs) -> list[dict]:
    rows = []
    for p in prices:
        o = obs.get(p.index + config.INDEX_BASE)
        if not o or (o["t_lo"] is None and o["t_hi"] is None):
            continue
        lo, hi = o["t_lo"], o["t_hi"]
        rows.append(dict(
            line=p.index + config.INDEX_BASE, a=p.a, b=p.b, median=p.t_median, q=p.q, t_lo=lo, t_hi=hi,
            b_short=max(0.0, lo - p.b) if lo is not None else 0.0,
            b_over=max(0.0, p.b - hi) if hi is not None else 0.0,
            a_over=int(hi is not None and p.a > hi),
            a_short=max(0.0, lo - p.a) if lo is not None else 0.0,
            miss=int((lo is not None and p.q * p.t_median < lo) or (hi is not None and p.q * p.t_median >= hi)),
        ))
    return rows


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    s = lambda k: round(sum(r[k] for r in rows), 2)
    return dict(n=n, b_short=s("b_short"), b_over=s("b_over"), a_over=s("a_over"), a_short=s("a_short"), miss=s("miss"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default="2-99")
    ap.add_argument("--variants", default="clauses,neighbours,both")
    ap.add_argument("--model", default=config.MODEL)
    ap.add_argument("--effort", default=config.FAST_EFFORT)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--labels", choices=["own", "leaderboard"], default=config.MEMORY_LABELS)
    ap.add_argument("--dry", action="store_true", help="build and print the blocks, no estimate calls")
    a = ap.parse_args()
    variants = [v.strip() for v in a.variants.split(",") if v.strip()]
    wanted = set(games_arg(a.games))
    games = [g for g in sorted(int(d.name.split("_")[1]) for d in config.PAST_DIR.glob("case_*")
                               if (d / "results.json").exists()) if g in wanted]
    if not a.dry and not config.OPENAI_KEY:
        raise SystemExit("OPENAI_KEY missing (needed for the estimates; use --dry to only print the blocks)")

    lbl = memory_build.observed_leaderboard() if a.labels == "leaderboard" else {}
    if a.labels == "leaderboard" and not lbl:
        raise SystemExit("runs/bench/labels.jsonl missing: python3 -I research/bench/build_labels.py --team ...")
    plan = []  # (game, variant, references or None)
    cases, obs = {}, {}
    for g in games:
        d = config.PAST_DIR / f"case_{g:03d}"
        own = memory_build.observed_own(d)
        lines = {l["pos"] for l in memory_build.mt.parse_invoice_lines(memory_build.load_past(d)["invoice"])} | set(own)
        obs[g] = {pos: memory_build.merge_obs(own.get(pos), lbl.get((g, pos))) for pos in lines}
        if not any(o["t_lo"] is not None or o["t_hi"] is not None for o in obs[g].values()):
            print(f"game {g}: no proven bound, skipped")
            continue
        out = config.MEMORY_DIR / "bench" / str(g)
        if a.rebuild or not (out / "manifest.json").exists():
            memory_build.build(until=g - 1, out=out, labels=a.labels, verbose=False)
        m = memory.Memory()
        cases[g] = load_case(d)
        plan.append((g, "none", None))
        if not m.load(out):
            print(f"game {g}: bench build unusable, only 'none'")
            continue
        for v in variants:
            res = m.query(cases[g], until=g - 1, parts=PARTS[v])
            print(f"game {g} {v:<10s} status {res['status']:<7s} {res.get('ms', 0):>5} ms")
            if res.get("block"):
                plan.append((g, v, res["block"]))
                if a.dry:
                    print(res["block"], "\n")
    if a.dry:
        return

    def run(job):
        g, v, refs, r = job
        from claimbot.estimator import estimate
        try:
            est, meta = estimate(cases[g], effort=a.effort, model=a.model, references=refs)
        except Exception as e:  # noqa: BLE001
            return job, None, dict(error=repr(e))
        return job, [pricing.price_line(l) for l in est.lines], meta

    jobs = [(g, v, refs, r) for g, v, refs in plan for r in range(a.repeats)]
    print(f"\n{len(jobs)} estimate calls ({a.model}/{a.effort})")
    results = {}
    with ThreadPoolExecutor(4) as ex:
        for (g, v, refs, r), prices, meta in ex.map(run, jobs):
            results.setdefault((g, v), []).append(dict(rows=score(prices, obs[g]) if prices else None, meta=meta))

    tot = {v: [] for v in ["none"] + variants}
    print("\nper game  [lines | b_short EUR | b_over EUR | a_over | a_short EUR | miss]")
    for g in sorted(cases):
        base = [x for rep in results.get((g, "none"), []) if rep["rows"] for x in rep["rows"]]
        if not base:
            print(f"  game {g}: baseline failed, game left out")
            continue
        tot["none"] += base
        cells = []
        for v in variants:
            got = [x for rep in results.get((g, v), []) if rep["rows"] for x in rep["rows"]]
            rows = got or base  # no block, or the call failed: the baseline answer is what would have been submitted
            tot[v] += rows
            s = summarize(rows)
            cells.append(f"{v}{'' if got else '(=none)'} {s['b_short']} | {s['b_over']} | {s['a_over']} | {s['a_short']} | {s['miss']}")
        s0 = summarize(base)
        print(f"  game {g:>3} n {s0['n']:>2}  none {s0['b_short']} | {s0['b_over']} | {s0['a_over']} | {s0['a_short']} | {s0['miss']}    "
              + "    ".join(cells))
    print("\nALL scored lines:")
    for v, rows in tot.items():
        print(f"  {v:<11s} {summarize(rows)}")
    usage = [rep["meta"].get("usage") for reps in results.values() for rep in reps if rep["meta"].get("usage")]
    tok_in = sum(u.get("input_tokens", 0) for u in usage)
    tok_out = sum(u.get("output_tokens", 0) for u in usage)
    print(f"tokens: in {tok_in}, out {tok_out} over {len(usage)} calls")
    outdir = config.MEMORY_DIR / "eval"
    outdir.mkdir(parents=True, exist_ok=True)
    f = outdir / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    f.write_text(json.dumps(dict(model=a.model, effort=a.effort, labels=a.labels, games=sorted(cases), variants=variants,
                                 summary={v: summarize(r) for v, r in tot.items()},
                                 results={f"{g}/{v}": reps for (g, v), reps in results.items()}), indent=1))
    print(f"saved {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
