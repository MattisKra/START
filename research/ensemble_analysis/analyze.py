"""Score every ensemble member and several combining rules against the t-bounds of games 1-4.

Run from the repo root: uv run python research/ensemble_analysis/analyze.py
"""
import json, math, sys, statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research" / "prompt_opt"))
from claimbot import pricing, config, ensemble
from claimbot.schema import CaseEstimate
import evaluate as ev

LOGS = {  # game -> ensemble logs (samples)
    1: ["20261121-141900_game_1_ensemble.json", "20261121-144400_game_1_ensemble.json"],
    2: ["20261121-141835_game_2_ensemble.json", "20261121-144429_game_2_ensemble.json"],
    3: ["20261121-142700_game3_ensemble.json", "20261121-144500_game_3_ensemble.json"],
    4: ["20261121-144031_game4_ensemble.json"],
}
VALID = {(1,1),(2,1),(2,2),(2,4),(3,4),(3,5),(4,2),(4,3)}          # t_lo > 0
INVALID = {(1,2),(2,3),(3,1),(3,2),(3,3),(3,6),(4,1)}               # every positive charge seen was inflated
BOUNDS = {g: ev.load_bounds(g) for g in LOGS}
WEIGHT = {m.name: m.weight for m in ensemble.members()}

# samples[(game, sample_idx)] = {member: {line(1-based): (q, mu, sigma, median)}}
samples = {}
for g, files in LOGS.items():
    for k, f in enumerate(files):
        d = json.loads((ROOT / "runs" / f).read_text())
        samples[(g, k)] = {m["member"]: {l.index + 1: pricing._belief(l) for l in CaseEstimate(**m["estimate"]).lines}
                           for m in d["members"]}

def log_err(median, lo, hi):
    """Signed log distance of median to [lo, hi); 0 inside. Open-ended hi: only underestimates are visible."""
    if median <= 0: return float("nan")
    if median < lo: return math.log(median / lo)
    if hi is not None and median >= hi: return math.log(median / hi)
    return 0.0

def price(q, mu, sigma, b_mult=None, reject_p=None):
    old = (config.B_VALID_MULT, config.REJECT_P)
    if b_mult is not None: config.B_VALID_MULT = b_mult
    if reject_p is not None: config.REJECT_P = reject_p
    try:
        return pricing._best_charge(mu, sigma) * config.CHARGE_MULT, pricing._accept_limit(q, mu, sigma)
    finally:
        config.B_VALID_MULT, config.REJECT_P = old

def net(g, line, a, b):
    return ev.replay(a, b, BOUNDS[g][str(line)])["net"]

# ---------- 1. per member ----------
rows = defaultdict(lambda: defaultdict(list))
for (g, k), mem in samples.items():
    for name, lines in mem.items():
        for line, (q, mu, sigma, med) in lines.items():
            key = (g, line); bd = BOUNDS[g].get(str(line))
            if bd is None: continue
            r = rows[name]
            if key in VALID:
                r["q_valid"].append(q); r["err"].append(log_err(med, bd["t_lo"], bd["t_hi"]))
            elif key in INVALID:
                r["q_invalid"].append(q)
            a, b = price(q, mu, sigma) if med > 0 else (0.0, 0.0)
            r[f"net_{g}_{k}"].append(net(g, line, a, b))

def member_net(r):
    per_game = defaultdict(list)
    for key, v in r.items():
        if key.startswith("net_"):
            g = int(key.split("_")[1]); per_game[g].append(sum(v))
    return {g: st.mean(v) for g, v in per_game.items()}

print("== 1. Members (valid lines: 8, invalid: 7; err = log distance of median to the t interval) ==")
print(f"{'member':<30}{'w':>6} {'n':>3} {'bias':>7} {'|err|':>6} {'under':>6} {'q|valid':>8} {'q|inval':>8}   net g1    g2    g3    g4   sum")
out = []
for name, r in rows.items():
    e = [x for x in r["err"] if x == x]
    nets = member_net(r)
    out.append((sum(nets.values()) if len(nets) == 4 else float("nan"), name, r, e, nets))
for tot, name, r, e, nets in sorted(out, key=lambda x: -(x[0] if x[0] == x[0] else -1e9)):
    print(f"{name:<30}{WEIGHT.get(name, 0):>6.2f} {len(e):>3} {st.mean(e):>+7.2f} {st.mean(map(abs, e)):>6.2f} {sum(x < 0 for x in e)/len(e):>6.0%} "
          f"{st.mean(r['q_valid']):>8.2f} {st.mean(r['q_invalid']):>8.2f}  " + " ".join(f"{nets.get(g, float('nan')):>6.0f}" for g in (1,2,3,4)) + f" {tot:>6.0f}")

# ---------- 2. run-to-run noise (same member, same case, two samples) ----------
print("\n== 2. Run-to-run noise: |log ratio| of the median between two runs of the same member on the same line ==")
noise = defaultdict(list)
for g in (1, 2, 3):
    a, b = samples[(g, 0)], samples[(g, 1)]
    for name in a:
        if name in b:
            for line in a[name]:
                if line in b[name] and a[name][line][3] > 0 and b[name][line][3] > 0:
                    noise[name].append(abs(math.log(a[name][line][3] / b[name][line][3])))
for name, v in sorted(noise.items(), key=lambda x: st.mean(x[1])):
    print(f"  {name:<28} mean {st.mean(v):.2f} (x{math.exp(st.mean(v)):.2f})  max x{math.exp(max(v)):.2f}  n={len(v)}")
between = []
for (g, k), mem in samples.items():
    lines = defaultdict(list)
    for name, ls in mem.items():
        for line, (q, mu, s, med) in ls.items():
            if med > 0: lines[line].append(mu)
    between += [st.pstdev(v) for v in lines.values() if len(v) > 2]
print(f"  spread between members on one line: mean sd of log median {st.mean(between):.2f} (x{math.exp(st.mean(between)):.2f})")

# ---------- 3. combining rules ----------
def wmedian(vals, ws):
    pairs = sorted(zip(vals, ws)); half = sum(ws) / 2; acc = 0
    for v, w in pairs:
        acc += w
        if acc >= half: return v

def combine(members, rule, weights):
    """members: {name: (q, mu, sigma, med)} for one line -> (q, mu, sigma)"""
    items = [(n, v) for n, v in members.items() if v[3] > 0]
    ws_all = [weights(n) for n in members]; q = sum(v[0] * w for (n, v), w in zip(members.items(), ws_all)) / sum(ws_all)
    if rule == "q_median":
        q = wmedian([v[0] for v in members.values()], ws_all)
    if not items: return q, None, None
    ws = [weights(n) for n, _ in items]; mus = [v[1] for _, v in items]
    mean_mu = sum(m * w for m, w in zip(mus, ws)) / sum(ws)
    mu = mean_mu if rule == "mean" else wmedian(mus, ws)
    if rule == "q70":   # 70th weighted percentile instead of the median
        pairs = sorted(zip(mus, ws)); acc = 0
        for v, w in pairs:
            acc += w
            if acc >= 0.7 * sum(ws): mu = v; break
    betw = sum(w * (m - mean_mu) ** 2 for m, w in zip(mus, ws)) / sum(ws)
    within = sum(w * v[2] ** 2 for (_, v), w in zip(items, ws)) / sum(ws)
    return q, mu, max(math.sqrt(within + betw), config.MIN_SIGMA)

def run_rule(label, rule="median", weights=lambda n: WEIGHT.get(n, 1.0), keep=lambda n: True, b_mult=None, reject_p=None, shift=0.0):
    per_game = defaultdict(list)
    for (g, k), mem in samples.items():
        if len(mem) < 20: continue  # only the runs that have all 20 members
        tot = 0.0
        lines = sorted({l for ls in mem.values() for l in ls})
        for line in lines:
            if str(line) not in BOUNDS[g]: continue
            ms = {n: ls[line] for n, ls in mem.items() if line in ls and keep(n)}
            if not ms: continue
            q, mu, sigma = combine(ms, rule, weights)
            a, b = price(q, mu + shift, sigma, b_mult, reject_p) if mu is not None else (0.0, 0.0)
            tot += net(g, line, a, b)
        per_game[g].append(tot)
    g = {k: st.mean(v) for k, v in per_game.items()}
    print(f"  {label:<52}" + " ".join(f"{g[i]:>7.0f}" for i in (1, 2, 3, 4)) + f" {sum(g.values()):>8.0f}")

claude = lambda n: n.startswith("claude")
web = lambda n: n.endswith("+web")
print("\n== 3. Combining rules: replayed net per game (the 20-member run of each game) ==")
print(f"  {'rule':<52}{'g1':>7} {'g2':>7} {'g3':>7} {'g4':>7} {'sum':>8}")
run_rule("current: size-weighted median, b>=1.25x")
run_rule("unweighted median", weights=lambda n: 1.0)
run_rule("size-weighted mean of logs", rule="mean")
run_rule("no web members", keep=lambda n: not web(n))
run_rule("web members only", keep=web)
run_rule("Claude only (Fable, Opus, Sonnet)", keep=claude)
run_rule("OpenAI only (Sol, Terra, Luna)", keep=lambda n: not claude(n))
run_rule("Fable + Opus only", keep=lambda n: "fable" in n or "opus" in n)
run_rule("without Luna and Terra", keep=lambda n: "luna" not in n and "terra" not in n)
run_rule("medium effort only", keep=lambda n: "/medium" in n)
run_rule("low effort only", keep=lambda n: "/low" in n)
print("  -- acceptance limit b (weighted median kept) --")
run_rule("b = 1/3-quantile only (rule before 14:40)", b_mult=0.0)
for m in (1.0, 1.25, 1.5, 2.0):
    run_rule(f"b >= {m}x median", b_mult=m)
print("  -- bias correction: shift the log-median up before pricing a and b --")
for s in (0.1, 0.2, 0.3):
    run_rule(f"median x{math.exp(s):.2f}, b>=1.25x", shift=s)
run_rule("70th weighted percentile instead of median", rule="q70")

print("  -- re-weighting --")
BIAS = {"claude-fable-5-2": 1.0, "gpt-6.1-terra": 1.0, "gpt-6-luna": 0.5, "claude-opus-5-5": 1.0, "gpt-6.2-sol": 0.5, "claude-sonnet-5-5": 0.5}
run_rule("web weight x1.0 instead of x1.5", weights=lambda n: WEIGHT.get(n, 1.0) / (1.5 if web(n) else 1.0))
run_rule("web weight x0.5", weights=lambda n: WEIGHT.get(n, 1.0) / (3.0 if web(n) else 1.0))
run_rule("Fable + Terra (no web)", keep=lambda n: ("fable" in n or "terra" in n) and not web(n))
run_rule("Fable + Terra + Opus (no web)", keep=lambda n: ("fable" in n or "terra" in n or "opus" in n) and not web(n))
run_rule("Fable only (no web)", keep=lambda n: "fable" in n and not web(n))

print("\n== 4. Per line: t bounds vs members' medians (20-member runs) ==")
for (g, k), mem in sorted(samples.items()):
    if len(mem) < 20: continue
    for line in sorted({l for ls in mem.values() for l in ls}):
        bd = BOUNDS[g].get(str(line))
        if not bd: continue
        meds = sorted(v[line][3] for v in mem.values() if line in v and v[line][3] > 0)
        qs = [v[line][0] for v in mem.values() if line in v]
        q, mu, sg = combine({n: ls[line] for n, ls in mem.items() if line in ls}, "median", lambda n: WEIGHT.get(n, 1.0))
        hi = bd["t_hi"]
        tag = "valid" if (g, line) in VALID else "t~0"
        print(f"  g{g} l{line} {tag:<5} t in [{bd['t_lo']:>7.2f}, {hi if hi is not None else float('inf'):>7.2f})  members min {meds[0]:>7.2f} / med {meds[len(meds)//2]:>7.2f} / max {meds[-1]:>7.2f}"
              f"  ensemble {math.exp(mu):>7.2f}  q mean {st.mean(qs):.2f} (min {min(qs):.2f}, max {max(qs):.2f})")
