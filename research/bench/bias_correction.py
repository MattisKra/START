"""Does a price-level bias correction learned from other games help? (replay on saved benchmark answers, no API calls)

    uv run --with pyzipper python research/bench/bias_correction.py [--ref mid|lo] [--variants v1_current,v2_policy_math]

For every saved model answer the per-line log ratio r = log(model median gross / t_ref) is computed on non-excluded lines with a
bracket (t_ref = geometric middle of [t_lo, t_hi) when t_hi exists, else t_lo, which is only a lower bound and therefore overstates
the true bias on lines where t is much larger; --ref lo uses t_lo everywhere for comparison). A game's bias for a (variant, model) is
the mean r over its lines.
Correction: beta = mean bias over the TRAINING games; every price quantile (p10/p50/p90) is multiplied by exp(-lambda * beta) before the
production pricing rule runs. Two evaluation designs:
  logo     leave-one-game-out: train on all other games (uses 'future' games, an optimistic design)
  forward  train on earlier games only, like the live bot would (game 1 has no history and is skipped)
Training pools: 'permodel' = same variant and model; 'pooled' = every model of the same variant (less noise, assumes shared bias).
lambda = 1 (full) or 0.5 (shrunk). Scoring = bench.py (b_regret EUR/line, b_score, a_score, |bias|); rule = 1/3-quantile (B_VALID_MULT=0)
and the live 1.25 x median rule. 'none' = no correction on the same held-out games.
Tiny data (4 games): this tests the machinery and gives a first sign, it does not prove anything.
"""
import argparse, collections, copy, glob, importlib.util, json, math, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research/bench/bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
from claimbot import config  # noqa: E402


def t_ref(lab, ref):
    if ref == "mid" and lab["t_hi"]:
        return math.sqrt(lab["t_lo"] * lab["t_hi"])
    return lab["t_lo"]


def scaled(parsed, factor):
    out = copy.deepcopy(parsed)
    for l in out["lines"]:
        for k in ("net_unit_price_p10", "net_unit_price_p50", "net_unit_price_p90"):
            l[k] = l[k] * factor
    return out


def answer_bias(parsed, case, labels, anns, ref):
    rows = bench.score_answer(parsed, labels[case], anns.get(case, {}))
    rs = []
    for r in rows:
        lab = labels[case][r["line"]]
        if not r["zero"] and lab["t_lo"] > 0 and r["t_med"] > 0:
            rs.append(math.log(r["t_med"] / t_ref(lab, ref)))
    return st.mean(rs) if rs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="mid"); ap.add_argument("--variants", default="v1_current,v2_policy_math")
    a = ap.parse_args()
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    variants = set(a.variants.split(","))
    answers = []                                   # dict(case, game, variant, model, parsed)
    for f in sorted(glob.glob(str(ROOT / "runs/bench/results/bench_*.json"))):
        for r in json.load(open(f))["results"]:
            if r.get("parsed") and r["variant"] in variants and r["case"] in labels and r["parsed"].get("lines"):
                answers.append(dict(case=r["case"], game=int(r["case"].split("_")[1]), variant=r["variant"], model=r["model"], parsed=r["parsed"]))
    games = sorted({x["game"] for x in answers})
    print(f"{len(answers)} saved answers, games {games}, ref={a.ref}")
    # per (variant, model, game) bias, plus pooled per (variant, game)
    pm, pp = collections.defaultdict(list), collections.defaultdict(list)
    for x in answers:
        b = answer_bias(x["parsed"], x["case"], labels, anns, a.ref)
        if b is not None:
            pm[(x["variant"], x["model"], x["game"])].append(b); pp[(x["variant"], x["game"])].append(b)
    mean = lambda xs: st.mean(xs) if xs else None
    print("\nbias per game (mean log(model median / t_ref); + = too high), pooled over models/variants:")
    for g in games:
        v = [b for (vv, gg), bs in pp.items() if gg == g for b in bs]
        print(f"  game {g}: {mean(v):+.2f}  (n answers {len(v)}; spread between models, sd {st.pstdev(v):.2f})")

    def beta(x, train_games, pool):
        if not train_games:
            return None
        if pool == "pooled":
            vals = [mean(pp[(x["variant"], g)]) for g in train_games if pp.get((x["variant"], g))]
        else:
            vals = [mean(pm[(x["variant"], x["model"], g)]) for g in train_games if pm.get((x["variant"], x["model"], g))]
        return mean(vals)

    results = {}
    for design in ("forward", "logo"):
        for pool in ("pooled", "permodel"):
            for lam in (1.0, 0.5):
                for mult in (0.0, 1.25):
                    config.B_VALID_MULT = mult
                    rows = collections.defaultdict(list)
                    for x in answers:
                        g = x["game"]
                        train = [h for h in games if h < g] if design == "forward" else [h for h in games if h != g]
                        if design == "forward" and not train:
                            continue
                        b = beta(x, train, pool)
                        if b is None:
                            continue
                        for name, factor in (("none", 1.0), ("corrected", math.exp(-lam * b))):
                            rows[(name, g)] += bench.score_answer(scaled(x["parsed"], factor), labels[x["case"]], anns.get(x["case"], {}))
                    results[(design, pool, lam, mult)] = rows
    print("\nb_regret EUR/line (lower better) | a_score (higher better) | |bias| ; per held-out game and overall")
    for design in ("forward", "logo"):
        evalg = [g for g in games if not (design == "forward" and g == games[0])]
        print(f"\n== {design}: held-out games {evalg}")
        print(f"{'pool':9s}{'lam':>4s}{'B_mult':>7s} {'':10s}" + "".join(f"{('g' + str(g)):>10s}" for g in evalg) + f"{'ALL':>10s}{'a_score':>9s}{'|bias|':>8s}")
        for pool in ("pooled", "permodel"):
            for lam in (1.0, 0.5):
                for mult in (0.0, 1.25):
                    rows = results[(design, pool, lam, mult)]
                    for name in ("none", "corrected"):
                        if name == "none" and (pool, lam) != ("pooled", 1.0):
                            continue
                        per = [bench.summarize(rows[(name, g)]) for g in evalg]
                        allrows = [r for g in evalg for r in rows[(name, g)]]
                        s = bench.summarize(allrows)
                        print(f"{pool if name == 'corrected' else '-':9s}{(lam if name == 'corrected' else ''):>4}{mult:>7}  {name:10s}" +
                              "".join(f"{p['b_regret']!s:>10s}" for p in per) + f"{s['b_regret']!s:>10s}{s['a_score']!s:>9s}{s['abs_bias']!s:>8s}")


if __name__ == "__main__":
    main()
