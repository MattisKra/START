"""Leave-one-game-out test: can a price-level bias learned from earlier brackets correct a model's median?

    python3 -I research/raw3/scripts/logo_bias.py

Reads runs/bench/results/*.json (saved model answers) and runs/bench/labels.jsonl (anonymous t brackets). Stdlib only, no network,
contains no data. Reference value per valid line: geometric mean of the bracket when it is two-sided, otherwise t_lo (a LOWER bound,
so 'too low' is understated on those lines). Error = log(model median gross / reference).
Corrections tested, each fitted on the other games only:
  global    one multiplier per model (mean log error of the training lines)
  by-size   two multipliers per model: lines whose model median is below / above SMALL_EUR gross
"""
import collections, glob, json, math, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SMALL_EUR = 120.0
labs = {}
for l in (ROOT / "runs/bench/labels.jsonl").read_text().splitlines():
    d = json.loads(l); labs[(d["case"], d["line"])] = d
ref = {}
for k, L in labs.items():
    if L["t_lo"] > 0:
        ref[k] = (math.sqrt(L["t_lo"] * L["t_hi"]) if L["t_hi"] else L["t_lo"], L["t_hi"] is not None)
rows = collections.defaultdict(list)          # (model, variant) -> [(case, line, mean log median)]
tmp = collections.defaultdict(list)
for f in sorted(glob.glob(str(ROOT / "runs/bench/results/bench_*.json"))):
    for r in json.load(open(f))["results"]:
        for l in r.get("lines") or []:
            if (r["case"], l["line"]) in ref and l["t_med"] > 0:
                tmp[(r["model"].split("/")[-1], r["variant"], r["case"], l["line"])].append(math.log(l["t_med"]))
for (m, v, c, ln), xs in tmp.items():
    rows[(m, v)].append((c, ln, st.mean(xs), len(xs)))
cases = sorted({k[0] for k in ref})
print(f"valid lines with a bracket: {len(ref)} in {len(cases)} games; two-sided: {sum(1 for v in ref.values() if v[1])}")
print(f"{'model':22s}{'variant':16s}{'n':>3s}{'bias':>7s}{'|err| raw':>10s}{'|err| global':>13s}{'|err| by-size':>14s}   per-game mean log error")
agg = collections.defaultdict(list)
for (m, v), rs in sorted(rows.items()):
    if len({c for c, *_ in rs}) < 3:
        continue
    err = {(c, ln): mu - math.log(ref[(c, ln)][0]) for c, ln, mu, _ in rs}
    med = {(c, ln): math.exp(mu) for c, ln, mu, _ in rs}
    raw, glob_, size = [], [], []
    for held in sorted({c for c, _ in err}):
        tr = {k: e for k, e in err.items() if k[0] != held}
        g = st.mean(tr.values())
        s = {True: [e for k, e in tr.items() if med[k] < SMALL_EUR], False: [e for k, e in tr.items() if med[k] >= SMALL_EUR]}
        for k, e in err.items():
            if k[0] != held: continue
            raw.append(abs(e)); glob_.append(abs(e - g))
            grp = s[med[k] < SMALL_EUR]
            size.append(abs(e - (st.mean(grp) if grp else g)))
    per_game = {c[-1]: round(st.mean(e for k, e in err.items() if k[0] == c), 2) for c in sorted({c for c, _ in err})}
    print(f"{m:22s}{v:16s}{len(err):>3d}{st.mean(err.values()):>7.2f}{st.mean(raw):>10.2f}{st.mean(glob_):>13.2f}{st.mean(size):>14.2f}   {per_game}")
    agg["raw"].append(st.mean(raw)); agg["global"].append(st.mean(glob_)); agg["size"].append(st.mean(size))
print(f"\nmean over rows: |err| raw {st.mean(agg['raw']):.2f}  global-corrected {st.mean(agg['global']):.2f}  by-size-corrected {st.mean(agg['size']):.2f}")
print(f"rows where the global correction helped: {sum(g < r for g, r in zip(agg['global'], agg['raw']))}/{len(agg['raw'])}; by-size: {sum(s < r for s, r in zip(agg['size'], agg['raw']))}/{len(agg['raw'])}")
# crowd of models (median over models of v1 and v2 answers)
crowd = collections.defaultdict(list)
for (m, v), rs in rows.items():
    for c, ln, mu, _ in rs:
        crowd[(c, ln)].append(mu)
print("\nper line: log(median over all saved model answers / reference)   [* = reference is only a lower bound]")
for k in sorted(crowd):
    print(f"  {k[0]} line {k[1]}: {st.median(crowd[k]) - math.log(ref[k][0]):+.2f}{'' if ref[k][1] else ' *'}   between-model sd {st.pstdev(crowd[k]):.2f} (n={len(crowd[k])})")
