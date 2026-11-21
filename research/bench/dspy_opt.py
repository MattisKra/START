"""DSPy prompt optimisation (GEPA) for the case estimator, scored by the same replay metric as bench.py.

    uv run --with dspy --with pyzipper python research/bench/dspy_opt.py eval     [--model openai/gpt-6-luna] [--seed v2_policy_math]
    uv run --with dspy --with pyzipper python research/bench/dspy_opt.py optimize [--model ...] [--reflection anthropic/claude-opus-5.5]
                                                                                   [--max-calls 60] [--min-cases 6] [--force]

What it does
  * Program: one dspy.Predict whose signature takes (policy, description, invoice, ...) and returns the claimbot CaseEstimate
    (pydantic). The instruction text is the thing being optimised; the seed is research/bench/prompts/<seed>.txt.
  * Metric (returns score AND textual feedback, which GEPA's reflection model reads):
      score = 0.6 * mean(b_score) + 0.4 * mean(a_score on certain lines; 0.5 if none), minus 0.1 per excluded line whose b != 0,
      where b_score / a_score come from replaying the production a/b rule against the real charges (see bench.py docstring).
      Feedback lists, per line, the bracket for t, the model's median, p_valid, payout_fraction and our annotation hint.
  * Data: runs/bench/labels.jsonl (local, gitignored) + annotations.json. One dspy.Example per case.
  * Guard: `optimize` refuses to run with fewer than --min-cases labelled cases (default 6) unless --force. With 2-3 cases the
    optimiser just memorises them; use --force only to test the machinery. The optimised instruction is written to
    runs/bench/dspy_optimized_<ts>.txt (local). Review it before use: the feedback contains numbers derived from the leaderboard,
    so an optimised prompt may have copied case-specific values. Never commit it unreviewed.
Cost note: each rollout reads the whole policy (10-20k tokens), so --max-calls is the budget knob.
"""
import argparse, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("bench", ROOT / "research" / "bench" / "bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
import dspy  # noqa: E402
from claimbot.schema import CaseEstimate  # noqa: E402

RUNS = bench.RUNS


def read_case(case_id):
    d = bench.ensure_case(case_id)
    import subprocess
    inv = subprocess.run(["pdftotext", "-layout", str(next(d.glob("invoice*.pdf"))), "-"], capture_output=True, text=True).stdout
    return dict(policy=(d / "policy.txt").read_text(errors="replace"), description=(d / "description.txt").read_text(errors="replace"), invoice=inv)


def make_signature(instructions):
    class EstimateCase(dspy.Signature):
        policy: str = dspy.InputField(desc="policy.txt")
        description: str = dspy.InputField(desc="damage description")
        invoice: str = dspy.InputField(desc="invoice text, lines without prices")
        estimate: CaseEstimate = dspy.OutputField(desc="one entry per invoice line, in invoice order")
    EstimateCase.__doc__ = instructions
    return EstimateCase.with_instructions(instructions)


def build_examples(labels, anns):
    ex = []
    for case in sorted(labels):
        ex.append(dspy.Example(case_id=case, **read_case(case)).with_inputs("policy", "description", "invoice"))
    return ex


def make_metric(labels, anns):
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        case = gold.case_id
        try:
            parsed = json.loads(pred.estimate.model_dump_json())
            rows = bench.score_answer(parsed, labels[case], anns.get(case, {}))
        except Exception as e:  # noqa: BLE001
            return dspy.Prediction(score=0.0, feedback=f"Could not score the answer: {e!r}. Return exactly one entry per invoice line with all fields.")
        bs = [min(max(r["b_score"], 0), 1) for r in rows if r.get("b_score") is not None]
        as_ = [r["a_score"] for r in rows if isinstance(r.get("a_score"), float)]
        zero_bad = sum(1 for r in rows if r.get("zero") and r.get("b") != 0)
        score = 0.6 * (sum(bs) / len(bs) if bs else 0.5) + 0.4 * (sum(as_) / len(as_) if as_ else 0.5) - 0.1 * zero_bad
        fb = []
        for r in rows:
            lab, ann = labels[case][r["line"]], anns.get(case, {}).get(str(r["line"]), {})
            if r.get("zero"):
                fb.append(f"Line {r['line']}: the expert value is 0 (excluded). You gave p_valid={r['q']:.2f}, b={r['b']}. {ann.get('hint', '')}")
            else:
                hi = "unbounded above" if lab["t_hi"] is None else f"below {lab['t_hi']}"
                ratio = r["t_med"] / lab["t_lo"] if lab["t_lo"] else float("nan")
                verdict = "TOO HIGH" if (lab["t_hi"] and r["t_med"] >= lab["t_hi"]) else "TOO LOW" if ratio < 0.85 else "ok"
                fb.append(f"Line {r['line']}: expert value is at least {lab['t_lo']} and {hi}; your gross median was {r['t_med']:.0f} "
                          f"({ratio:.2f} x the lower bound, {verdict}), p_valid={r['q']:.2f}, so b={r['b']}, a={r['a']}. {ann.get('hint', '')}")
        return dspy.Prediction(score=max(score, 0.0), feedback="\n".join(fb))
    return metric


def lm(model, **kw):
    return dspy.LM(f"openrouter/{model}", api_key=os.environ["OPENROUTER_API_KEY"], temperature=kw.pop("temperature", 0.0),
                   max_tokens=kw.pop("max_tokens", 6000), cache=False, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["eval", "optimize"])
    ap.add_argument("--model", default="openai/gpt-6-luna")
    ap.add_argument("--reflection", default="anthropic/claude-opus-5.5")
    ap.add_argument("--seed", default="v2_policy_math")
    ap.add_argument("--max-calls", type=int, default=60)
    ap.add_argument("--min-cases", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    seed = (bench.BENCH / "prompts" / f"{a.seed}.txt").read_text()
    prog = dspy.Predict(make_signature(seed))
    dspy.configure(lm=lm(a.model, extra_body={"reasoning": {"effort": "none"}}))
    data = build_examples(labels, anns)
    metric = make_metric(labels, anns)
    print(f"{len(data)} labelled cases: {[e.case_id for e in data]}; task model {a.model}; seed {a.seed}")

    def evaluate(p, tag):
        scores = []
        for ex in data:
            t0 = time.time()
            pred = p(policy=ex.policy, description=ex.description, invoice=ex.invoice)
            m = metric(ex, pred)
            scores.append(m.score); print(f"  [{tag}] {ex.case_id}: score {m.score:.3f} ({time.time() - t0:.0f}s)\n      " + m.feedback.replace("\n", "\n      "))
        print(f"  [{tag}] mean {sum(scores) / len(scores):.3f}")
        return sum(scores) / len(scores)

    base = evaluate(prog, "seed")
    if a.mode == "eval":
        return
    if len(data) < a.min_cases and not a.force:
        sys.exit(f"\nrefusing to optimise on {len(data)} cases (< {a.min_cases}): it would memorise them. Use --force only to test the machinery.")
    if len(data) < a.min_cases:
        print(f"\nWARNING: --force with {len(data)} cases: train and validation are the same cases; the result is NOT evidence of improvement.")
    gepa = dspy.GEPA(metric=metric, max_metric_calls=a.max_calls, reflection_lm=lm(a.reflection, temperature=1.0, max_tokens=12000),
                     track_stats=False)
    opt = gepa.compile(prog, trainset=data, valset=data)
    new = opt.predict.signature.instructions
    after = evaluate(opt, "optimised")
    out = RUNS / f"dspy_optimized_{time.strftime('%Y%m%d-%H%M%S')}.txt"
    out.write_text(new)
    print(f"\nseed mean {base:.3f} -> optimised mean {after:.3f} (in-sample!). Instruction saved to {out} (local, review before use).")


if __name__ == "__main__":
    main()
