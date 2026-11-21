"""Interval-censored estimate of the price-level bias: r = log(t / our median) ~ N(mu, sigma), where each line only gives a bracket.

    python3 -I research/raw3/scripts/censored_bias.py

We never see t, only t_lo <= t < t_hi (t_hi may be missing). The likelihood of one line is Phi((hi-mu)/s) - Phi((lo-mu)/s).
Input: per valid line the bracket and the median the production ensemble produced. The medians below are OUR OWN ensemble's
(research/ensemble_analysis/results.txt, section 4); the brackets are read from the gitignored runs/bench/labels.jsonl.
Stdlib only, no network. A flat prior on mu in [-0.5, 1.0] and on sigma in [0.05, 0.8] is used for the posterior summary.
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUR_MEDIAN = {("case_001", 1): 595.00, ("case_002", 1): 856.80, ("case_002", 2): 321.30, ("case_002", 4): 83.30,
              ("case_003", 4): 238.00, ("case_003", 5): 166.60, ("case_004", 2): 261.36, ("case_004", 3): 71.40}
Phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
obs = []
for l in (ROOT / "runs/bench/labels.jsonl").read_text().splitlines():
    d = json.loads(l); k = (d["case"], d["line"])
    if k in OUR_MEDIAN and d["t_lo"] > 0:
        lo = math.log(d["t_lo"] / OUR_MEDIAN[k]); hi = math.log(d["t_hi"] / OUR_MEDIAN[k]) if d["t_hi"] else math.inf
        obs.append((k, lo, hi))
for k, lo, hi in obs:
    print(f"  {k[0]} line {k[1]}: log(t/median) in [{lo:+.2f}, {('%+.2f' % hi) if hi < math.inf else 'inf'})")


def loglik(mu, s, rows):
    ll = 0.0
    for _, lo, hi in rows:
        p = (Phi((hi - mu) / s) if hi < math.inf else 1.0) - Phi((lo - mu) / s)
        ll += math.log(max(p, 1e-300))
    return ll


def fit(rows, label):
    grid = [(mu / 100, s / 100) for mu in range(-50, 101) for s in range(5, 81)]
    w = [math.exp(loglik(mu, s, rows)) for mu, s in grid]
    Z = sum(w)
    best = grid[max(range(len(w)), key=w.__getitem__)]
    m = sum(wi * mu for wi, (mu, s) in zip(w, grid)) / Z
    sd = sum(wi * s for wi, (mu, s) in zip(w, grid)) / Z
    cum, lo5, hi95 = 0.0, None, None
    marg = {}
    for wi, (mu, s) in zip(w, grid): marg[mu] = marg.get(mu, 0) + wi / Z
    for mu in sorted(marg):
        cum += marg[mu]
        if lo5 is None and cum >= 0.05: lo5 = mu
        if hi95 is None and cum >= 0.95: hi95 = mu
    print(f"{label}: n={len(rows)}  max-likelihood mu {best[0]:+.2f} sigma {best[1]:.2f} | posterior mean mu {m:+.2f} (90 % interval {lo5:+.2f} .. {hi95:+.2f}), mean sigma {sd:.2f}"
          f" | P(mu > 0) = {sum(v for mu, v in marg.items() if mu > 0):.2f}  -> multiply the median by about {math.exp(m):.2f}")


fit(obs, "all valid lines")
for held in sorted({k[0] for k, _, _ in obs}):
    fit([o for o in obs if o[0][0] != held], f"without {held}")
