"""Paired comparison: each +web member vs the same model/effort without web, same run, same line."""
import json, math, sys, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research" / "prompt_opt"))
from claimbot import pricing
from claimbot.schema import CaseEstimate
import evaluate as ev
RUNS = {1: "20261121-144400_game_1_ensemble.json", 2: "20261121-144429_game_2_ensemble.json",
        3: "20261121-144500_game_3_ensemble.json", 4: "20261121-144031_game4_ensemble.json"}
VALID = {(1,1),(2,1),(2,2),(2,4),(3,4),(3,5),(4,2),(4,3)}
def err(m, lo, hi):
    if m < lo: return math.log(m / lo)
    if hi is not None and m >= hi: return math.log(m / hi)
    return 0.0
ratios, closer, searches = [], {"web": 0, "plain": 0, "tie": 0}, []
for g, f in RUNS.items():
    d = json.loads((ROOT / "runs" / f).read_text()); bd = ev.load_bounds(g)
    mem = {m["member"]: {l.index + 1: pricing._belief(l) for l in CaseEstimate(**m["estimate"]).lines} for m in d["members"]}
    searches += [m["meta"].get("web_searches") for m in d["members"] if m["member"].endswith("+web")]
    for line in sorted(next(iter(mem.values()))):
        if (g, line) not in VALID: continue
        lo, hi = bd[str(line)]["t_lo"], bd[str(line)]["t_hi"]
        w = [(n, v[line][3]) for n, v in mem.items() if n.endswith("+web")]
        row = []
        for n, mw in w:
            mp = mem[n[:-4]][line][3]; ratios.append(math.log(mw / mp))
            ew, ep = abs(err(mw, lo, hi)), abs(err(mp, lo, hi))
            closer["web" if ew < ep - 1e-9 else "plain" if ep < ew - 1e-9 else "tie"] += 1
            row.append(f"{mp:.0f}->{mw:.0f}")
        print(f"g{g} l{line} t in [{lo:.0f}, {hi if hi else float('inf'):.0f})  plain->web: " + "  ".join(row))
print("\norder:", "  ".join(n for n, _ in w))
print(f"pairs {len(ratios)}: web/plain median ratio x{math.exp(st.median(ratios)):.2f}, mean x{math.exp(st.mean(ratios)):.2f}, "
      f"web lower in {sum(r < -0.02 for r in ratios)}, higher in {sum(r > 0.02 for r in ratios)}")
print("closer to the t interval:", closer, "| searches per web call:", searches)
