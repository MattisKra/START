"""Replay a change of the production pricing rule on SAVED benchmark answers (no API calls).

    uv run --with pyzipper python research/bench/rule_replay.py [--mult 0,1.0,1.25,1.5] [--variant v1_current,v2_policy_math]

Loads every runs/bench/results/bench_*.json that stored raw answers, rescoring each answer with claimbot.pricing under different
CLAIMS_B_VALID_MULT values (0 = the old pure 1/3-quantile rule). Scoring as in bench.py. Per-case rows keep games separate, so
you can see which games a rule helps (a rule tuned after game N is only fair to judge on games > N).
"""
import argparse, collections, glob, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research/bench/bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
from claimbot import config  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--mult", default="0,1.0,1.25,1.5"); ap.add_argument("--variant", default="v1_current,v2_policy_math")
a = ap.parse_args()
labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
variants = set(a.variant.split(","))
answers = []                                   # (case, variant, model, rep, parsed) de-duplicated across files
seen = set()
for f in sorted(glob.glob(str(ROOT / "runs/bench/results/bench_*.json"))):
    for r in json.load(open(f))["results"]:
        if r.get("parsed") and r["variant"] in variants and r["case"] in labels:
            k = (r["case"], r["variant"], r["model"], r["rep"], f)
            answers.append((r["case"], r["variant"], r["model"], r["parsed"]))
print(f"{len(answers)} saved answers over cases {sorted({x[0] for x in answers})}")
cases = sorted({x[0] for x in answers})
print(f"{'rule (B_VALID_MULT)':20s}" + "".join(f"{c:>16s}" for c in cases) + f"{'ALL':>16s}   (b_regret EUR/line | b_score)")
for m in [float(x) for x in a.mult.split(",")]:
    config.B_VALID_MULT = m
    per = collections.defaultdict(list)
    for case, v, mod, parsed in answers:
        try:
            per[case] += bench.score_answer(parsed, labels[case], anns.get(case, {}))
        except Exception:
            pass
    row = f"{('old 1/3-quantile' if m == 0 else f'{m}x median'):20s}"
    for c in cases:
        s = bench.summarize(per[c]); row += f"{s['b_regret']!s:>9s}|{s['b_score']!s:<6s}"
    s = bench.summarize([x for c in cases for x in per[c]]); row += f"{s['b_regret']!s:>9s}|{s['b_score']!s:<6s}"
    print(row)
act = {c: bench.summarize(bench.actual_row(labels[c], anns.get(c, {}))) for c in cases}
print(f"{'ACTUAL live bot':20s}" + "".join(f"{act[c]['b_regret']!s:>9s}|{act[c]['b_score']!s:<6s}" for c in cases))
