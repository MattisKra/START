"""Benchmark agent ARCHITECTURES (orchestrations) on the labelled cases, same metric as bench.py / fable_eval.py.

    uv run --with pyzipper python research/bench/arch_bench.py [--new-calls] [--review-specs SPEC,SPEC] [--budget 3]

Offline (no API call; uses the saved reader answers in runs/bench/fable_eval/*.json for luna / terra / fable):
  single:<reader>     one reader through the engine (reference)
  median3             three readers in parallel; per line the geometric median of the gross median m, mean P(valid), any 'pinned'; engine multipliers
  robust3             three readers in parallel; charge at the LOWEST a, accept up to the HIGHEST b (b only if a majority says valid): minimax regret under the cliff at t
  cascade             luna + terra first; if they disagree (validity differs, |log m ratio| > 0.35, or payout fraction differs by > 0.2) the strong reader's answer is used
                      (cost counts luna + terra, plus fable only when escalated)
With --new-calls (spends a little):
  review:<spec>       cheap draft (luna) -> a review agent re-checks every clause and number against the policy and returns a corrected answer
  memory:<reader>     the reader also sees the experts' outcome for the lines of cases with the SAME policy edition (policy overlap >= 0.7)
Metrics: b_regret EUR/line, b_score, a_score, bias, cost per case, escalation rate. In-sample caveat as everywhere: cases 1-4 shaped the prompt,
brackets are not point labels, ~21 lines. Treat differences below ~50 EUR/line as noise.
"""
import argparse, collections, glob, importlib.util, json, math, os, re, statistics as st, sys, copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bench", ROOT / "research/bench/bench.py")
bench = importlib.util.module_from_spec(spec); spec.loader.exec_module(bench)
from claimbot.case import load_case  # noqa: E402
from claimbot_fable import engine, readers  # noqa: E402
from claimbot_fable.schema import ReaderCase  # noqa: E402

LUNA, TERRA, FABLE = ("openrouter:openai/gpt-6-luna:low:noimage", "openrouter:openai/gpt-6.1-terra:medium", "openrouter:anthropic/claude-fable-5.2:low")
P = engine.Params()


def load_saved():
    latest = {}
    for f in sorted(glob.glob(str(ROOT / "runs/bench/fable_eval/*.json"))):
        for r in json.load(open(f))["answers"]:
            latest[(r["reader"], r["case"])] = r
    return latest


def cost_of(r):
    return ((r.get("meta") or {}).get("usage") or {}).get("cost") or 0.0


def lat_of(r):
    return (r.get("meta") or {}).get("latency_s") or 0.0


def final_line(m, q, pinned, p=P):
    ka, kb = (p.ka_pinned, p.kb_pinned) if pinned else (p.ka_open, p.kb_open)
    a = ka * m
    if q < p.excluded_below:
        a = a if p.excluded_a == "as_valid" else (0.0 if p.excluded_a == "zero" else a * float(p.excluded_a))
    a = min(a, p.max_a_over_median * m) if m > 0 else 0.0
    b = 0.0 if q < p.b_zero_below else kb * m
    return dict(a=a, b=b, t_median=m, q=q)


def outs(est):
    return engine.compute(est, P)


def combine(per, how):
    n = min(len(o) for o in per)
    rows = []
    for i in range(n):
        xs = [o[i] for o in per]
        ms = [x.m for x in xs if x.m > 0]
        m = math.exp(st.median(math.log(v) for v in ms)) if ms else 0.0
        q = st.mean(x.q for x in xs); pin = any(x.pinned for x in xs)
        if how == "median":
            rows.append(final_line(m, q, pin))
        else:  # robust: lowest a, highest b among readers, b only when a majority thinks the line is valid
            maj = sum(1 for x in xs if x.q >= P.b_zero_below) > len(xs) / 2
            rows.append(dict(a=min(x.a for x in xs), b=max((x.b for x in xs), default=0.0) if maj else 0.0, t_median=m, q=q))
    return rows


def disagree(est_a, est_b):
    la, lb = sorted(est_a.lines, key=lambda l: l.index), sorted(est_b.lines, key=lambda l: l.index)
    oa, ob = outs(est_a), outs(est_b)
    for x, y, l1, l2 in zip(oa, ob, la, lb):
        if (x.q >= 0.5) != (y.q >= 0.5):
            return True
        if x.m > 0 and y.m > 0 and abs(math.log(x.m / y.m)) > 0.35 and max(x.q, y.q) >= 0.5:
            return True
        if abs(l1.payout_fraction - l2.payout_fraction) > 0.2:
            return True
    return False


def score_rows(rows, case, labels, anns):
    out = []
    for i, r in enumerate(rows, 1):
        if i in labels[case]:
            s = bench.score_line(r, labels[case][i], anns.get(case, {}).get(str(i), {})); s["line"] = i; s["case"] = case; out.append(s)
    return out


def policy_overlap(a, b):
    L = lambda c: {l.strip() for l in (bench.RUNS / "cases" / c / "policy.txt").read_text(errors="replace").splitlines() if len(l.strip()) > 25}
    A, B = L(a), L(b)
    return len(A & B) / len(A | B)


def draft_json(est):
    d = [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in l.model_dump().items() if k != "rationale"} | {"rationale": l.rationale[:220]} for l in sorted(est.lines, key=lambda l: l.index)]
    return json.dumps(dict(lines=d, aggregate_limits=[x.model_dump() for x in est.aggregate_limits], anchors=[x.model_dump() for x in est.anchors]), ensure_ascii=False)


REVIEW = ("\n\nREVIEW TASK: another adjuster produced the DRAFT below. Re-check every clause it cites and every number against the policy and the "
          "description (valid or excluded, payout fraction, justified quantity, shared limits, anchors, valuation basis, price level). Correct mistakes, keep what is "
          "right, and return YOUR OWN FINAL ANSWER in the required schema.\nDRAFT:\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-calls", action="store_true"); ap.add_argument("--budget", type=float, default=3.0)
    ap.add_argument("--review-specs", default=f"{TERRA},{FABLE}"); ap.add_argument("--memory-readers", default=f"{LUNA},{TERRA}")
    a = ap.parse_args()
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    saved = load_saved()
    cases = [c for c in sorted(labels) if all((r, c) in saved for r in (LUNA, TERRA, FABLE))]
    est = lambda r, c: ReaderCase.model_validate(saved[(r, c)]["est"])
    table = collections.OrderedDict()      # name -> dict(rows=[], cost=[], lat=[], esc=[])
    def add(name, case, rows, cost, lat, esc=None):
        t = table.setdefault(name, dict(rows=[], cost=[], lat=[], esc=[]))
        t["rows"] += score_rows(rows, case, labels, anns); t["cost"].append(cost); t["lat"].append(lat)
        if esc is not None:
            t["esc"].append(esc)

    for c in cases:
        for nm, r in (("luna", LUNA), ("terra", TERRA), ("fable", FABLE)):
            add(f"single:{nm}", c, [final_line(x.m, x.q, x.pinned) for x in outs(est(r, c))], cost_of(saved[(r, c)]), lat_of(saved[(r, c)]))
        per = [outs(est(r, c)) for r in (LUNA, TERRA, FABLE)]
        par_cost = sum(cost_of(saved[(r, c)]) for r in (LUNA, TERRA, FABLE)); par_lat = max(lat_of(saved[(r, c)]) for r in (LUNA, TERRA, FABLE))
        add("median3 (parallel)", c, combine(per, "median"), par_cost, par_lat)
        add("robust3 (min a / max b)", c, combine(per, "robust"), par_cost, par_lat)
        esc = disagree(est(LUNA, c), est(TERRA, c))
        cc = cost_of(saved[(LUNA, c)]) + cost_of(saved[(TERRA, c)]) + (cost_of(saved[(FABLE, c)]) if esc else 0)
        ll = max(lat_of(saved[(LUNA, c)]), lat_of(saved[(TERRA, c)])) + (lat_of(saved[(FABLE, c)]) if esc else 0)
        rows = [final_line(x.m, x.q, x.pinned) for x in outs(est(FABLE, c))] if esc else combine([outs(est(LUNA, c)), outs(est(TERRA, c))], "median")
        add("cascade luna+terra -> fable", c, rows, cc, ll, esc=int(esc))

    if a.new_calls:
        loaded = {c: load_case(bench.ensure_case(c)) for c in cases}
        spent = [0.0]
        def call(spec_s, case, c):
            if spent[0] >= a.budget:
                return None
            for _ in range(2):
                try:
                    e, meta = readers.read(case, readers.parse_spec(spec_s), fast=not readers.parse_spec(spec_s).image)
                    spent[0] += (meta.get("usage") or {}).get("cost") or 0
                    return e, meta
                except Exception as ex:  # noqa: BLE001
                    err = repr(ex)[:120]
            print(f"  FAILED {spec_s} {c}: {err}"); return None
        for rs in [s for s in a.review_specs.split(",") if s]:
            for c in cases:
                cs = copy.copy(loaded[c]); cs.description = loaded[c].description + REVIEW + draft_json(est(LUNA, c))
                r = call(rs, cs, c)
                if r:
                    e, meta = r
                    add(f"review {rs.split(':')[1].split('/')[-1]}(draft=luna)", c, [final_line(x.m, x.q, x.pinned) for x in outs(e)],
                        cost_of(saved[(LUNA, c)]) + ((meta.get('usage') or {}).get('cost') or 0), lat_of(saved[(LUNA, c)]) + meta["latency_s"])
        fam = {c: [d for d in cases if d != c and policy_overlap(c, d) >= 0.7] for c in cases}
        print("same-edition siblings (policy overlap >= 0.7):", {c: s for c, s in fam.items() if s})
        for rs in [s for s in a.memory_readers.split(",") if s]:
            for c in [c for c in cases if fam[c]]:
                blk = []
                for d in fam[c]:
                    for ln, lab in sorted(labels[d].items()):
                        txt = next((l.invoice_text for l in sorted(est(LUNA, d).lines, key=lambda l: l.index)[ln - 1:ln]), "?")
                        zero = bench.is_zero(lab, anns.get(d, {}).get(str(ln), {}))
                        res = "EXCLUDED (0)" if zero else (f"at least EUR {lab['t_lo']:.0f} gross" + ("" if not lab['t_hi'] else f" and below {lab['t_hi']:.0f}"))
                        blk.append(f"- \"{txt}\": experts' amount {res}")
                cs = copy.copy(loaded[c]); cs.description = loaded[c].description + (
                    "\n\nEARLIER CASES WITH THE SAME POLICY EDITION (settled by the experts; use as anchors only where the item is comparable):\n" + "\n".join(blk))
                r = call(rs, cs, c)
                if r:
                    e, meta = r
                    add(f"memory:{rs.split(':')[1].split('/')[-1]}", c, [final_line(x.m, x.q, x.pinned) for x in outs(e)], (meta.get("usage") or {}).get("cost") or 0, meta["latency_s"])
                    base = f"single:{'luna' if rs == LUNA else 'terra'}"
                    add(base + " (same cases as memory)", c, [final_line(x.m, x.q, x.pinned) for x in outs(est(rs, c))], cost_of(saved[(rs, c)]), lat_of(saved[(rs, c)]))
        print(f"new-call spend ${spent[0]:.3f}")

    act = [x for c in cases for x in [dict(y, case=c) for y in bench.actual_row(labels[c], anns.get(c, {}))]]
    print(f"\ncases {cases}; params {P.ka_open}/{P.kb_open} open {P.ka_pinned}/{P.kb_pinned} pinned")
    print(f"{'architecture':38s}{'n':>3s}{'b_regret':>9s}{'b_score':>8s}{'a_score':>8s}{'bias':>6s}{'|bias|':>7s}{'$/case':>8s}{'lat s':>7s}{'esc':>5s}")
    def row(name, rows, cost=None, lat=None, esc=None):
        s = bench.summarize(rows)
        print(f"{name:38s}{s['n']:>3d}{str(s['b_regret']):>9s}{str(s['b_score']):>8s}{str(s['a_score']):>8s}{str(s['bias']):>6s}{str(s['abs_bias']):>7s}"
              f"{(f'{st.mean(cost):.3f}' if cost else '-'):>8s}{(f'{st.mean(lat):.0f}' if lat else '-'):>7s}{(f'{sum(esc)}/{len(esc)}' if esc else ''):>5s}")
    row("ACTUAL (live bot at the time)", act)
    for k, t in table.items():
        row(k, t["rows"], t["cost"], t["lat"], t["esc"] or None)


if __name__ == "__main__":
    main()
