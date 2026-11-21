"""Sweep the two engine multipliers over ALL saved reader answers (no API calls): which KA / KB would have done best on games 1-8?

    uv run --with pyzipper python research/bench/multiplier_sweep.py

Uses the latest saved answer per (reader, case) from runs/bench/fable_eval/*.json for luna / terra / fable, the same scoring as bench.py.
Reports b_regret (lower is better) for KB_open and the a_score (higher is better) for KA_open, per case-group, so you can see whether a
multiplier tuned on early games survives games 7-8 (where the whole field priced far above the expert value). Tiny data, in-sample.
"""
import collections, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ab", ROOT / "research/bench/arch_bench.py")
ab = importlib.util.module_from_spec(spec); spec.loader.exec_module(ab)
bench, engine = ab.bench, ab.engine
from claimbot_fable.schema import ReaderCase

labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
saved = ab.load_saved()
cases = [c for c in sorted(labels) if all((r, c) in saved for r in (ab.LUNA, ab.TERRA, ab.FABLE))]
print("cases with all three readers:", cases)
def rows_for(ka, kb, group):
    out = []
    for c in group:
        for r in (ab.LUNA, ab.TERRA, ab.FABLE):
            est = ReaderCase.model_validate(saved[(r, c)]["est"])
            P = engine.Params(ka_open=ka, kb_open=kb, ka_pinned=ka - 0.05, kb_pinned=min(kb, 1.05))
            for x in engine.compute(est, P):
                ln = x.index + 1
                if ln in labels[c]:
                    out.append(bench.score_line(dict(a=x.a, b=x.b, t_median=x.m, q=x.q), labels[c][ln], anns.get(c, {}).get(str(ln), {})))
    return out
groups = {"games 1-6": [c for c in cases if c <= "case_006"], "games 7-8": [c for c in cases if c >= "case_007"], "all": cases}
print("\nKB_open sweep (KA fixed 0.90): b_regret EUR/line | b_score          [lower regret is better]")
print(f"{'KB':>6s}" + "".join(f"{g:>26s}" for g in groups))
for kb in (0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5):
    cells = []
    for g, cs in groups.items():
        s = bench.summarize(rows_for(0.90, kb, cs)); cells.append(f"{s['b_regret']!s:>14s} | {s['b_score']!s:<8s}")
    print(f"{kb:>6.2f}" + "".join(f"{c:>26s}" for c in cells))
print("\nKA_open sweep (KB fixed 1.0): a_score = a/t_lo on certain lines (1.0 = at the lower bound, 0 = inflated) | share inflated")
print(f"{'KA':>6s}" + "".join(f"{g:>26s}" for g in groups))
for ka in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1):
    cells = []
    for g, cs in groups.items():
        rs = rows_for(ka, 1.0, cs); s = bench.summarize(rs)
        sc = [r["a_score"] for r in rs if isinstance(r.get("a_score"), float)]
        infl = sum(1 for x in sc if x == 0.0) / len(sc) if sc else float("nan")
        cells.append(f"{s['a_score']!s:>14s} | {infl:>5.0%}   ")
    print(f"{ka:>6.2f}" + "".join(f"{c:>26s}" for c in cells))
