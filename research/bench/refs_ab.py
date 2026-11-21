"""A/B: does the price-reference block (claimbot/refs.py) change the reader's medians, and does that change the cost-side replay?

    uv run --with pyzipper python research/bench/refs_ab.py FIELD_DIR --us "Team Name" [--games 10-15] [--reps 2] [--effort low]

For each game g the same cheap reader (claimbot.estimator.estimate, CLAIMS_MODEL) reads the case twice per arm:
  noref = case.refs empty
  refs  = refs.block() built ONLY from games < g (forward only, like live), brackets from runs/bench/labels.jsonl (derived from public results)
Reported per arm: where the valid-line medians fall relative to the public bracket [L, U) of t, and the cost-side replay of b = k x median.
Only our own numbers and anonymous aggregates are printed; FIELD_DIR (other teams' rows) must be outside the repo.
Caveats: one model, `reps` draws per arm and game, six games: this is a direction check, not a ranking.
"""
import argparse, concurrent.futures as cf, dataclasses, importlib.util, json, math, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


er = load("er", "research/bench/euro_replay.py")
from claimbot import config, estimator, pricing, refs
from claimbot.case import load_case

ap = argparse.ArgumentParser()
ap.add_argument("field_dir"); ap.add_argument("--us", required=True)
ap.add_argument("--games", default="10-15"); ap.add_argument("--reps", type=int, default=2)
ap.add_argument("--effort", default="low"); ap.add_argument("--emb-cache", default=None)
args = ap.parse_args()
lo_g, hi_g = map(int, args.games.split("-")); GAMES = list(range(lo_g, hi_g + 1))
US = args.us

# ---- forward-only reference rows from our own log + anonymous brackets
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
brk = {}
for ln in (ROOT / "runs/bench/labels.jsonl").read_text().splitlines():
    r = json.loads(ln); brk[(r["game"], r["line"])] = (r["t_lo"], r["t_hi"])
CUR = {"g": 10 ** 6}


def _rows(exclude_game=None):
    rows = []
    for g in sorted(int(x) for x in logs):
        if g >= CUR["g"] or (exclude_game is not None and g == int(exclude_game)):
            continue
        ms = logs[str(g)].get("members") or []
        if not ms:
            continue
        lines = max((m["estimate"]["lines"] for m in ms), key=len)
        for l in lines:
            b = brk.get((g, l["index"] + 1))
            if not b:
                continue
            lo, hi = b
            pv = [x["p_valid"] for m in ms for x in m["estimate"]["lines"] if x["index"] == l["index"]]
            valid = sum(pv) / len(pv) >= 2 / 3 if pv else False
            if lo and lo > 0 and hi is not None: rng = f"{lo:.0f} to {hi:.0f} EUR"
            elif lo and lo > 0: rng = f"at least {lo:.0f} EUR"
            elif hi is not None and valid: rng = f"below {hi:.0f} EUR"
            else: continue
            text = " ".join(l["invoice_text"].split())[:160]
            rows.append({"game": g, "text": text, "rng": rng,
                         "label": f"- case {g}: \"{text}\" ({l['quantity_invoiced']:g} {l['unit']}): {rng}"})
    return rows


refs._rows = _rows
refs.ENABLED = True
if args.emb_cache:
    refs.EMB_CACHE = Path(args.emb_cache)
refs.embed_missing()                       # embeds the past line texts once (text-embedding-3-small, a few cents)

cases = {g: load_case(ROOT / f"runs/bench/cases/case_{g:03d}") for g in GAMES}
blocks = {}
for g in GAMES:
    CUR["g"] = g
    blocks[g] = refs.block(exclude_game=g, case=cases[g])
CUR["g"] = 10 ** 6


def one(g, arm, rep):
    c = dataclasses.replace(cases[g], refs=blocks[g] if arm == "refs" else "")   # a copy per job: threads must not share one Case
    est, meta = estimator.estimate(c, effort=args.effort)
    out = {}
    for l in est.lines:
        q, mu, sg, med = pricing._belief(l)
        out[l.index + 1] = (med, q)
    return g, arm, rep, out, (meta.get("usage") or {})


jobs = [(g, arm, r) for g in GAMES for arm in ("noref", "refs") for r in range(args.reps)]
res = {}
with cf.ThreadPoolExecutor(8) as ex:
    for g, arm, rep, out, usage in ex.map(lambda j: one(*j), jobs):
        res.setdefault((g, arm), []).append(out)
        print(f"game {g} {arm} rep {rep}: {len(out)} lines, input tokens {usage.get('input_tokens')}")
(ROOT / "runs/bench/refs_ab.json").write_text(json.dumps({f"{g}|{a}": [{str(k): v for k, v in o.items()} for o in os_] for (g, a), os_ in res.items()}))


def agg(g, arm):
    """geometric-mean median and mean q over the reps"""
    outs = res[(g, arm)]; d = {}
    for ln in outs[0]:
        ms = [o[ln][0] for o in outs if ln in o and o[ln][0] > 0]
        qs = [o[ln][1] for o in outs if ln in o]
        d[ln] = (math.exp(sum(map(math.log, ms)) / len(ms)) if ms else 0.0, sum(qs) / len(qs))
    return d


games = er.load_field(args.field_dir)
live = {int(g): {s["index"] + 1: (s["a"], s["b"]) for s in v["submitted"]} for g, v in logs.items()}
rec = {g: er.reconstruct(games[g], US, our_b={l: v[1] for l, v in live.get(g, {}).items()}, our_a={l: v[0] for l, v in live.get(g, {}).items()}) for g in GAMES}


def cost(g, med, k):
    lo = hi = 0.0
    for ln in rec[g]:
        m, q = med.get(ln, (0.0, 0.0))
        b = k * m if q >= 2 / 3 else 0.0
        l, h, *_ = er.line_value(rec[g][ln], US, 0.0, b); lo += -h; hi += -l
    return (lo + hi) / 2


print("\nmedian vs public bracket of t on lines the reader calls valid (q >= 2/3) and whose bracket is informative")
print(f"{'arm':>6s}{'n lines':>9s}{'below L':>9s}{'inside':>8s}{'above U':>9s}{'median |log err| to bracket':>30s}")
for arm in ("noref", "refs"):
    n = bl = ins = ab = 0; errs = []
    for g in GAMES:
        for ln, (m, q) in agg(g, arm).items():
            b = brk.get((g, ln))
            if not b or q < 2 / 3 or m <= 0: continue
            L, U = b; L = L or 0.0
            if L <= 0 and U is None: continue
            n += 1
            if L > 0 and m < L: bl += 1; errs.append(abs(math.log(m / L)))
            elif U is not None and m >= U: ab += 1; errs.append(abs(math.log(m / U)))
            else: ins += 1; errs.append(0.0)
    print(f"{arm:>6s}{n:>9d}{bl:>9d}{ins:>8d}{ab:>9d}{st.median(errs) if errs else float('nan'):>30.3f}")

KS = (0.45, 0.55, 0.7, 0.9, 1.25)
print("\nreviewer cost per arm (EUR, midpoint of the evaluator range) summed over the games, b = k x median")
print(f"{'arm':>6s}" + "".join(f"{('k=' + str(k)):>10s}" for k in KS))
for arm in ("noref", "refs"):
    print(f"{arm:>6s}" + "".join(f"{sum(cost(g, agg(g, arm), k) for g in GAMES):>10.0f}" for k in KS))
act = sum(sum(r['amount'] for r in games[g] if r['reviewer'] == US) for g in GAMES)
print(f"our ACTUAL reviewer cost over games {GAMES[0]}-{GAMES[-1]}: {act:,.0f}")
print("\nper game (k=0.55 / k=0.9):")
for g in GAMES:
    print(f"  game {g}: noref {cost(g, agg(g,'noref'), .55):>7.0f} / {cost(g, agg(g,'noref'), .9):>7.0f}   refs {cost(g, agg(g,'refs'), .55):>7.0f} / {cost(g, agg(g,'refs'), .9):>7.0f}")
