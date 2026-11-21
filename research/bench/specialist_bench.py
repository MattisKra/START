"""One generalist reader versus dedicated specialist agents, and how many price agents make sense. Same metric as bench.py.

    uv run --with pyzipper python research/bench/specialist_bench.py [--budget 2] [--cases ...]

Specialists
  coverage agent  reads policy + description + invoice, returns validity, justified quantity, payout fraction, shared limits, anchors (no prices)
  price agents    see only the description + invoice lines (NO policy), return the justified quantity and the net unit price on the standard
                  basis (same kind and quality, new condition, Germany 2026); a PANEL of k cheap models from different providers, median taken
Merge: validity / fraction / limits / anchors / quantity from the coverage agent, price quantiles = median over the panel, then the usual
claimbot_fable engine. Compared with the single generalist readers (saved answers). Parallel latency = slowest of the agents; cost = sum.
Raw answers are cached in runs/bench/specialist/ so other panel sizes can be recombined without new calls (--recombine FILE).
"""
import argparse, collections, copy, glob, importlib.util, json, statistics as st, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ab", ROOT / "research/bench/arch_bench.py")
ab = importlib.util.module_from_spec(spec); spec.loader.exec_module(ab)
bench, engine, readers = ab.bench, ab.engine, ab.readers
from claimbot.case import load_case
from claimbot_fable.prompt import INSTRUCTIONS
from claimbot_fable.schema import ReaderCase

COVERAGE = INSTRUCTIONS.split("Rules:")[0] + """
You are the COVERAGE SPECIALIST. Do NOT estimate prices: set net_unit_price_p10, net_unit_price_p50 and net_unit_price_p90 to 1.0 for every line and
vat_rate to 0.19. Concentrate on validity (covered, related, p_valid), justified quantity, payout_fraction, aggregate_limits and anchors, and keep each
rationale to ONE sentence with the clause numbers.
Rules: exactly one entry per invoice line in invoice order with 0-based index; p_valid is the probability that the line is both covered and related.
"""
PRICE = """You are the PRICE SPECIALIST for German repair and replacement costs. You see the damage description and the invoice lines WITHOUT prices
(you do not see the policy). For every line give the justified quantity (what the described damage needs; the invoiced quantity may be too high) and the
NET price per unit in EUR for the same kind and quality in new condition / a normal repair by a German tradesperson or retailer in 2026, as p10 / p50 / p90.
Use any price, total or share stated in the description as an anchor and list such a total in anchors. Always set covered=true, related=true, p_valid=1.0,
payout_fraction=1.0, vat_rate=0.19 and leave aggregate_limits empty. Keep each rationale to ONE short sentence. Return exactly one entry per invoice line in
invoice order with 0-based index.
"""
COV_SPECS = {"luna": "openrouter:openai/gpt-6-luna:low:noimage", "terra": "openrouter:openai/gpt-6.1-terra:medium"}
PRICE_SPECS = ["openrouter:openai/gpt-6-luna:low:noimage", "openrouter:anthropic/claude-haiku-5.5:low:noimage", "openrouter:google/gemini-3.8-flash:low:noimage",
               "openrouter:z-ai/glm-5.3-flashx:low:noimage", "openrouter:minimax/minimax-m3.1-flash:low:noimage"]


def merge(cov: ReaderCase, prices: list[ReaderCase]) -> ReaderCase:
    out = cov.model_copy(deep=True)
    cl = sorted(out.lines, key=lambda l: l.index)
    pl = [sorted(p.lines, key=lambda l: l.index) for p in prices if len(p.lines) == len(cl)]
    for i, l in enumerate(cl):
        if pl:
            for k in ("net_unit_price_p10", "net_unit_price_p50", "net_unit_price_p90"):
                vals = [x[i].__dict__[k] for x in pl if x[i].__dict__[k] > 0]
                if vals:
                    setattr(l, k, st.median(vals))
            l.vat_rate = 0.19
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=2.0); ap.add_argument("--cases", default=""); ap.add_argument("--recombine", default="")
    a = ap.parse_args()
    labels, anns = bench.load_labels(), json.loads((bench.BENCH / "annotations.json").read_text())
    saved = ab.load_saved()
    cases = [c for c in (a.cases.split(",") if a.cases else sorted(labels)) if all((r, c) in saved for r in (ab.LUNA, ab.TERRA, ab.FABLE))]
    raw = {}                                                           # (role, spec, case) -> dict(est, meta)
    if a.recombine:
        for k, v in json.load(open(a.recombine))["raw"].items():
            role, sp, c = k.split("|"); raw[(role, sp, c)] = dict(est=ReaderCase.model_validate(v["est"]), meta=v["meta"])
    else:
        loaded = {c: load_case(bench.ensure_case(c)) for c in cases}
        jobs = [("cov", sp, c) for sp in COV_SPECS.values() for c in cases] + [("price", sp, c) for sp in PRICE_SPECS for c in cases]
        spent = [0.0]
        def run(j):
            role, sp, c = j
            if spent[0] >= a.budget:
                return j, None
            case = copy.copy(loaded[c])
            if role == "price":
                case.policy = "(The policy is not shown to you.)"; case.image_blobs = []
            for _ in range(2):
                try:
                    est, meta = readers.read(case, readers.parse_spec(sp), fast=True, instructions=COVERAGE if role == "cov" else PRICE)
                    spent[0] += (meta.get("usage") or {}).get("cost") or 0
                    return j, dict(est=est, meta=meta)
                except Exception as e:  # noqa: BLE001
                    err = repr(e)[:110]
            print("  FAILED", j[:2], c, err); return j, None
        with ThreadPoolExecutor(10) as ex:
            for f in as_completed([ex.submit(run, j) for j in jobs]):
                j, r = f.result()
                if r:
                    raw[j] = r
        out = ROOT / "runs/bench/specialist"; out.mkdir(parents=True, exist_ok=True)
        path = out / f"{datetime.now():%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps(dict(raw={"|".join(k): dict(est=v["est"].model_dump(), meta=v["meta"]) for k, v in raw.items()}), default=str))
        print(f"spent ${spent[0]:.3f}; saved {path}")

    cost_of = lambda r: ((r["meta"].get("usage") or {}).get("cost") or 0)
    table = collections.OrderedDict()
    def add(name, c, est, cost, lat):
        t = table.setdefault(name, dict(rows=[], cost=[], lat=[]))
        t["rows"] += ab.score_rows([ab.final_line(x.m, x.q, x.pinned) for x in engine.compute(est, ab.P)], c, labels, anns); t["cost"].append(cost); t["lat"].append(lat)
    for c in cases:
        for nm, rd in (("luna", ab.LUNA), ("terra", ab.TERRA), ("fable", ab.FABLE)):
            add(f"GENERALIST {nm}", c, ReaderCase.model_validate(saved[(rd, c)]["est"]), ab.cost_of(saved[(rd, c)]), ab.lat_of(saved[(rd, c)]))
        for cn, csp in COV_SPECS.items():
            if ("cov", csp, c) not in raw:
                continue
            cov = raw[("cov", csp, c)]
            for k in (1, 3, 5):
                panel = [raw[("price", sp, c)] for sp in PRICE_SPECS[:k] if ("price", sp, c) in raw]
                if len(panel) < k:
                    continue
                add(f"coverage:{cn} + price panel k={k}", c, merge(cov["est"], [p["est"] for p in panel]),
                    cost_of(cov) + sum(cost_of(p) for p in panel), max([cov["meta"]["latency_s"]] + [p["meta"]["latency_s"] for p in panel]))
            add(f"coverage:{cn} alone (prices = 1.0, no panel)", c, cov["est"], cost_of(cov), cov["meta"]["latency_s"]) if False else None
        panel3 = [raw[("price", sp, c)] for sp in PRICE_SPECS[:3] if ("price", sp, c) in raw]
        if len(panel3) == 3:                                           # price panel only, validity from the luna generalist (no coverage specialist)
            add("generalist luna validity + price panel k=3", c, merge(ReaderCase.model_validate(saved[(ab.LUNA, c)]["est"]), [p["est"] for p in panel3]),
                ab.cost_of(saved[(ab.LUNA, c)]) + sum(cost_of(p) for p in panel3), max([ab.lat_of(saved[(ab.LUNA, c)])] + [p["meta"]["latency_s"] for p in panel3]))
    act = [dict(x, case=c) for c in cases for x in bench.actual_row(labels[c], anns.get(c, {}))]
    print(f"\ncases {cases}")
    print(f"{'architecture':46s}{'n':>3s}{'b_regret':>9s}{'b_score':>8s}{'a_score':>8s}{'bias':>6s}{'|bias|':>7s}{'$/case':>8s}{'lat s':>7s}  b_regret excl. cases 7-8")
    def row(name, rows, cost=None, lat=None):
        s = bench.summarize(rows); s2 = bench.summarize([r for r in rows if r.get("case") not in ("case_007", "case_008")])
        print(f"{name:46s}{s['n']:>3d}{s['b_regret']!s:>9s}{s['b_score']!s:>8s}{s['a_score']!s:>8s}{s['bias']!s:>6s}{s['abs_bias']!s:>7s}"
              f"{(f'{st.mean(cost):.3f}' if cost else '-'):>8s}{(f'{st.mean(lat):.0f}' if lat else '-'):>7s}  {s2['b_regret']}")
    row("ACTUAL (live bot at the time)", act)
    for k, t in table.items():
        row(k, t["rows"], t["cost"], t["lat"])


if __name__ == "__main__":
    main()
