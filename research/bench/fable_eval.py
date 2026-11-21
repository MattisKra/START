"""Offline evaluation of claimbot_fable (reader -> rule engine) on the labelled cases, same metric as bench.py.

    uv run --with pyzipper python research/bench/fable_eval.py [--readers SPEC,SPEC] [--cases case_001,...] [--repeats 1]
        [--ka-open 0.9 --kb-open 1.25 --ka-pinned 0.85 --kb-pinned 1.05]

Each reader runs through claimbot_fable.readers (new schema, corrected prompt) and claimbot_fable.engine (limits, anchors, multipliers);
the resulting (a, b) per line is scored against the leaderboard brackets exactly like bench.py (b_regret EUR/line, b_score, a_score,
bias). Compare with research/bench/README.md. Remember: tiny data, brackets not point labels, in-sample on cases 1-4 (the reader
prompt was written after seeing them); only games released after the prompt was frozen count as out-of-sample.
Saved raw reader answers: runs/bench/fable_eval/<stamp>.json (local) so the multipliers can be re-fitted without new calls.
"""
import argparse, collections, importlib.util, json, os, statistics as st, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research/bench/bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
from claimbot.case import load_case  # noqa: E402
from claimbot_fable import engine, readers  # noqa: E402


def score(est, case_id, labels, anns, params):
    rows = []
    lines = engine.compute(est, params)
    for x in lines:
        ln = x.index + 1
        if ln in labels[case_id]:
            s = bench.score_line(dict(a=x.a, b=x.b, t_median=x.m, q=x.q), labels[case_id][ln], anns.get(case_id, {}).get(str(ln), {}))
            s["line"] = ln; rows.append(s)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--readers", default="openrouter:openai/gpt-6-luna:low:noimage,openrouter:openai/gpt-6.1-terra:medium,openrouter:anthropic/claude-fable-5.2:low")
    ap.add_argument("--cases", default=""); ap.add_argument("--repeats", type=int, default=1); ap.add_argument("--budget", type=float, default=4.0)
    ap.add_argument("--from-saved", default="", help="re-score a saved fable_eval json without any API call")
    for k, d in (("ka-open", .9), ("kb-open", 1.25), ("ka-pinned", .85), ("kb-pinned", 1.05)):
        ap.add_argument(f"--{k}", type=float, default=d)
    a = ap.parse_args()
    params = engine.Params(ka_open=a.ka_open, kb_open=a.kb_open, ka_pinned=a.ka_pinned, kb_pinned=a.kb_pinned)
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    cases = [c for c in (a.cases.split(",") if a.cases else sorted(labels)) if c in labels]
    answers = []                                                       # dict(reader, case, rep, est, meta)
    if a.from_saved:
        for r in json.load(open(a.from_saved))["answers"]:
            if r["case"] in cases:
                answers.append(dict(r, est=engine.ReaderCase.model_validate(r["est"])))
    else:
        specs = [readers.parse_spec(s) for s in a.readers.split(",")]
        loaded = {c: load_case(bench.ensure_case(c)) for c in cases}
        spent = [0.0]
        def run(job):
            sp, c, rep = job
            if spent[0] >= a.budget:
                return None
            for _ in range(2):
                try:
                    est, meta = readers.read(loaded[c], sp, fast=not sp.image)
                    spent[0] += (meta.get("usage") or {}).get("cost") or 0
                    return dict(reader=sp.name, case=c, rep=rep, est=est, meta=meta)
                except Exception as e:  # noqa: BLE001
                    err = repr(e)[:160]
            print(f"  FAILED {sp.name} {c}: {err}"); return None
        jobs = [(sp, c, r) for sp in specs for c in cases for r in range(a.repeats)]
        print(f"{len(jobs)} reader calls over cases {cases}")
        with ThreadPoolExecutor(6) as ex:
            for f in as_completed([ex.submit(run, j) for j in jobs]):
                r = f.result()
                if r:
                    answers.append(r); print(f"  {r['reader']:55s} {r['case']} {r['meta']['latency_s']}s ${(r['meta'].get('usage') or {}).get('cost') or 0:.4f}", flush=True)
        out = ROOT / "runs/bench/fable_eval"; out.mkdir(parents=True, exist_ok=True)
        path = out / f"{datetime.now():%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps(dict(answers=[dict(r, est=r["est"].model_dump()) for r in answers]), default=str))
        print(f"spent ${spent[0]:.3f}; saved {path}")
    by = collections.defaultdict(list)
    for r in answers:
        by[r["reader"]] += [dict(x, case=r["case"]) for x in score(r["est"], r["case"], labels, anns, params)]
    act = [dict(x, case=c) for c in cases for x in bench.actual_row(labels[c], anns.get(c, {}))]
    print(f"\nparams {params.ka_open}/{params.kb_open} open, {params.ka_pinned}/{params.kb_pinned} pinned; cases {cases}")
    print(f"{'reader':56s}{'n':>3s}{'b_regret':>9s}{'b_score':>8s}{'a_score':>8s}{'unc':>4s}{'zero_ok':>8s}{'bias':>6s}{'|bias|':>7s}  per-case b_regret")
    def row(name, rows):
        s = bench.summarize(rows)
        pc = " ".join(f"{c[-1]}:{bench.summarize([x for x in rows if x['case'] == c])['b_regret']}" for c in cases)
        print(f"{name:56s}{s['n']:>3d}{str(s['b_regret']):>9s}{str(s['b_score']):>8s}{str(s['a_score']):>8s}{s['n_unc']:>4d}{str(s['zero_ok']):>8s}{str(s['bias']):>6s}{str(s['abs_bias']):>7s}  {pc}")
    row("ACTUAL (live bot at the time)", act)
    for k in sorted(by):
        row(k, by[k])


if __name__ == "__main__":
    main()
