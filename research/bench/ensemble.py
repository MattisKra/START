"""Does combining several models beat one model? Replays aggregation rules on saved benchmark answers.

    uv run --with pyzipper python research/bench/ensemble.py [--results runs/bench/results/bench_*.json (default: latest)]
        [--variant v2_policy_math] [--judge-models openai/gpt-6.1-terra,openai/gpt-6-luna] [--judge-budget 1.0]

Aggregators (all end in the same scoring as bench.py: replay of the resulting (a, b) against the real charges):
  single_mean     average score of the single models (what you get by picking a model at random)
  mean_ab         per-line arithmetic mean of each model's a and b
  median_ab       per-line median of each model's a and b
  trim_ab         drop the highest and lowest a and b, average the rest (needs >= 5 models)
  pool            belief pooling: pooled q = mean q_i, pooled log-median = mean of log-medians, pooled sigma =
                  sqrt(mean sigma_i^2 + var(log-medians)), i.e. model DISAGREEMENT widens the belief; then the production rule
                  (a = argmax x P(t>=x), b = 1/3-quantile) is applied once to the pooled belief
  pool_nodis      same without adding the disagreement term (ablation)
  judge:<model>   a final LLM sees the case and all models' answers and returns one reconciled estimate (extra sequential call)
Unit of aggregation: all models of one (variant, case, repeat). Subsets: 'cheap3' = gpt-6-luna + gemini-3.8-flash + claude-haiku-5.5.
"""
import argparse, collections, glob, importlib.util, json, math, os, statistics as st, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research" / "bench" / "bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
from claimbot import config, pricing  # noqa: E402
from claimbot.schema import LineEstimate  # noqa: E402

oc = bench.oc
CHEAP3 = ["openai/gpt-6-luna", "google/gemini-3.8-flash", "anthropic/claude-haiku-5.5"]


def line_price(line):
    line = dict(line); line.setdefault("payout_fraction", 1.0)
    return pricing.price_line(LineEstimate(**line))


def per_model_prices(parsed):
    lines = sorted(parsed["lines"], key=lambda l: l["index"])
    return [line_price(l) for l in lines]


def pool_belief(prices, disagreement=True):
    """prices: list of LinePrice for one line from several models -> (a, b, t_median, q)."""
    q = st.mean(p.q for p in prices)
    pos = [p for p in prices if p.t_median > 0]
    if not pos:
        return dict(a=0.0, b=0.0, t_median=0.0, q=q)
    mus = [math.log(p.t_median) for p in pos]
    mu = st.mean(mus)
    var_s = st.mean(p.sigma ** 2 for p in pos)
    var_d = st.pvariance(mus) if len(mus) > 1 and disagreement else 0.0
    sigma = max(math.sqrt(var_s + var_d), config.MIN_SIGMA)
    a = pricing._best_charge(mu, sigma) * config.CHARGE_MULT
    b = pricing._accept_limit(q, mu, sigma)
    return dict(a=round(a, 2), b=round(b, 2), t_median=math.exp(mu), q=q)


def agg_ab(prices, how):
    avals, bvals = [p.a for p in prices], [p.b for p in prices]
    if how == "trim" and len(prices) >= 5:
        avals, bvals = sorted(avals)[1:-1], sorted(bvals)[1:-1]
    f = st.median if how == "median" else st.mean
    return dict(a=f(avals), b=f(bvals), t_median=st.median(p.t_median for p in prices), q=st.mean(p.q for p in prices))


def compact(parsed):
    out = []
    for l in sorted(parsed["lines"], key=lambda l: l["index"]):
        out.append({k: (round(v, 3) if isinstance(v, float) else v) for k, v in l.items()
                    if k in ("index", "invoice_text", "p_valid", "quantity_justified", "net_unit_price_p10", "net_unit_price_p50",
                             "net_unit_price_p90", "vat_rate", "payout_fraction")} | {"rationale": l["rationale"][:260]})
    return out


JUDGE_ADD = """

You are now the FINAL REVIEWER. Several independent adjusters have already estimated this case (their answers are in the user
message as JSON). Reconcile them: check every disagreement against the policy text and the description, keep the best-supported
value for each line (not simply the average), decide payout_fraction and p_valid from the clauses, and widen p10/p90 where the
adjusters disagree or where the price rests on an assumption. Return ONE final estimate in the required schema."""


def judge(model, system, content, cands, key, cat):
    extra = [{"type": "text", "text": "\n\nINDEPENDENT ESTIMATES (JSON, one per adjuster):\n" + json.dumps(cands, ensure_ascii=False)}]
    res = oc.call(model, system + JUDGE_ADD, list(content) + extra, oc.pick_reasoning(cat, model, "min"), 6000, key, 150)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="")
    ap.add_argument("--variant", default="v2_policy_math")
    ap.add_argument("--judge-models", default="openai/gpt-6.1-terra,openai/gpt-6-luna")
    ap.add_argument("--judge-budget", type=float, default=1.0)
    a = ap.parse_args()
    f = a.results or sorted(glob.glob(str(ROOT / "runs/bench/results/bench_*.json")))[-1]
    data = json.load(open(f))
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    variant = a.variant
    prompt = (bench.BENCH / "prompts" / f"{variant}.txt").read_text()
    groups = collections.defaultdict(dict)
    for r in data["results"]:
        if r["variant"] == variant and r.get("parsed") and r["parsed"].get("lines"):
            groups[(r["case"], r["rep"])][r["model"]] = r
    print(f"{f}\nvariant {variant}: {len(groups)} groups (case x repeat); models per group "
          f"{sorted({len(g) for g in groups.values()})}")
    rows = collections.defaultdict(list)       # method -> per-line score dicts
    cost, lat = collections.defaultdict(list), collections.defaultdict(list)

    def score_prices(method, case, plist):
        for ln, p in enumerate(plist, 1):
            if ln in labels[case]:
                s = bench.score_line(p, labels[case][ln], anns.get(case, {}).get(str(ln), {})); s["line"] = ln
                rows[method].append(s)

    cat = oc.catalogue(); key = os.environ["OPENROUTER_API_KEY"]
    content = {c: oc.load_case(bench.ensure_case(c), True) for c in {k[0] for k in groups}}
    for (case, rep), g in sorted(groups.items()):
        models = sorted(g)
        per = {m: per_model_prices(g[m]["parsed"]) for m in models}
        n_lines = min(len(v) for v in per.values())
        for m in models:                                          # singles
            score_prices("single_mean", case, [p.as_dict() for p in per[m]])
        for name, subset in (("all", models), ("cheap3", [m for m in CHEAP3 if m in models])):
            if len(subset) < 2:
                continue
            for method, fn in (("mean_ab", lambda ps: agg_ab(ps, "mean")), ("median_ab", lambda ps: agg_ab(ps, "median")),
                               ("trim_ab", lambda ps: agg_ab(ps, "trim")), ("pool", lambda ps: pool_belief(ps)),
                               ("pool_nodis", lambda ps: pool_belief(ps, False))):
                if method == "trim_ab" and len(subset) < 5:
                    continue
                score_prices(f"{method}[{name}{len(subset)}]", case,
                             [fn([per[m][i] for m in subset]) for i in range(n_lines)])
            lat[f"set[{name}]"].append(max(g[m]["latency_s"] for m in subset))
            cost[f"set[{name}]"].append(sum(g[m]["cost"] or 0 for m in subset))

    # ---- judge calls (extra, paid) : one per (case, rep, judge model) over all models of the group
    spent, jobs = [0.0], []
    for jm in [m for m in a.judge_models.split(",") if m]:
        for (case, rep), g in sorted(groups.items()):
            jobs.append((jm, case, rep, g))
    def run_judge(j):
        jm, case, rep, g = j
        if spent[0] >= a.judge_budget:
            return None
        cands = {m.split("/")[-1]: compact(g[m]["parsed"]) for m in sorted(g)}
        res = judge(jm, prompt, content[case], cands, key, cat); spent[0] += res.get("cost") or 0
        return jm, case, rep, res
    with ThreadPoolExecutor(6) as ex:
        for fut in as_completed([ex.submit(run_judge, j) for j in jobs]):
            r = fut.result()
            if not r or not r[3].get("parsed") or not r[3]["parsed"].get("lines"):
                continue
            jm, case, rep, res = r
            plist = [p.as_dict() for p in per_model_prices(res["parsed"])]
            score_prices(f"judge:{jm.split('/')[-1]}[all]", case, plist)
            cost[f"judge:{jm.split('/')[-1]}"].append(res.get("cost") or 0); lat[f"judge:{jm.split('/')[-1]}"].append(res.get("latency_s") or 0)

    print("\nmetrics as in bench.py (b_regret EUR/line lower is better; b_score, a_score higher is better)")
    print(f"{'method':26s}{'n':>4s}{'b_regret':>9s}{'b_score':>8s}{'a_score':>8s}{'unc':>4s}{'zero_ok':>8s}{'bias':>6s}{'|bias|':>7s}")
    order = sorted(rows, key=lambda k: (k != "single_mean", k))
    for k in order:
        s = bench.summarize(rows[k])
        print(f"{k:26s}{s['n']:>4d}{str(s['b_regret']):>9s}{str(s['b_score']):>8s}{str(s['a_score']):>8s}{s['n_unc']:>4d}{str(s['zero_ok']):>8s}{str(s['bias']):>6s}{str(s['abs_bias']):>7s}")
    print("\nextra cost / latency per case (mean):")
    for k in sorted(cost):
        print(f"  {k:24s} cost ${st.mean(cost[k]):.4f}   latency {st.mean(lat[k]):.1f}s (parallel max for sets; judge is sequential on top)")
    print(f"judge spend ${spent[0]:.3f}")


if __name__ == "__main__":
    main()
