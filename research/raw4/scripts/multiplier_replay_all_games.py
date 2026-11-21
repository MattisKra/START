"""Single-multiplier replay through ALL completed games: b = k x m and a = k x m for our team, opponents fixed.

    python3 -I research/raw4/scripts/multiplier_replay_all_games.py LB_DIR --us "Team Name"

m = the live median from outputs/model_outputs.json, or our charge / 0.9 where the log is not committed.
Reads other teams' rows in memory from LB_DIR (outside the repo); prints our own replayed totals and per-game inflated counts only.
"""
import importlib.util, json, sys, math
from pathlib import Path
spec = importlib.util.spec_from_file_location("rr", Path(__file__).with_name("replay_rules.py")); rr = importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
fr = rr.fr; INF = rr.INF
D = fr.load(sys.argv[1]); us = sys.argv[sys.argv.index("--us") + 1]
outs = json.loads((Path(__file__).resolve().parents[3] / "outputs" / "model_outputs.json").read_text())["games"]
# our median per line: from outputs where present, else our charge / 0.9 (games 8-9; a-mult was 0.9); lines we judged valid = our b bracket shows we accepted something or b_lo>0, else use q
lines = []
for g, G in D["games"].items():
    sub = {s["index"] + 1: s for s in outs.get(str(g), {}).get("submitted", [])}
    for ln, L in G["lines"].items():
        if ln in sub:
            m, q = sub[ln]["t_median"], sub[ln]["q"]
        else:
            a = L["A"][us]["a"]; B = L["B"][us]
            if not a:
                # our charge unseen: valid if we accepted positive charges
                if B["n_acc_pos"] > 0: m, q = None, 0.9
                else: continue
            else:
                m, q = a / 0.9, (0.9 if B["n_acc_pos"] > 0 else 0.1)
        lines.append((g, ln, L, m, q))
games = sorted(D["games"])
def cost_rule(k):
    per = {g: 0.0 for g in games}
    for g, ln, L, m, q in lines:
        if q < 2/3: b = 0.0
        elif m is None: b = 1e9 if k >= 0.9 else 0.0     # game 8 line 1: our median unknown (> 200): accepts all at k>=0.9, nothing below
        else: b = k * m
        per[g] += rr.cost(b, L, us)
    return per
orc = {g: sum(sum(A["a"] for t, A in L["A"].items() if t != us and A["status"] == "fair") for gg, ln, L, m, q in lines if gg == g) for g in games}
act = {g: sum(L["B"][us]["cost"] for gg, ln, L, m, q in lines if gg == g) for g in games}
print("games", games)
print(f"oracle  {sum(orc.values()):8.0f} | " + " ".join(f"{orc[g]:7.0f}" for g in games))
print(f"actual  {sum(act.values()):8.0f} | " + " ".join(f"{act[g]:7.0f}" for g in games))
for k in (0.0, 0.3, 0.4, 0.5, 0.6, 0.67, 0.8, 0.9, 1.0, 1.25, 1.5, 99):
    p = cost_rule(k)
    print(f"k_b {k:5.2f} {sum(p.values()):8.0f} | " + " ".join(f"{p[g]:7.0f}" for g in games) + f" | games 1-6 {sum(p[g] for g in games if g <= 6):7.0f}  games 7-9 {sum(p[g] for g in games if g >= 7):7.0f}")
# a side
print("\na-rule (pess / opt) on lines with t_lo>0 or near-zero valid-looking lines where our median is known")
al = [(g, ln, L, m) for g, ln, L, m, q in lines if m and q >= 2/3]
for k in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1):
    pp = {g: 0.0 for g in games}; po = {g: 0.0 for g in games}
    for g, ln, L, m in al:
        pp[g] += rr.revenue(k * m, L, us, "pess"); po[g] += rr.revenue(k * m, L, us, "opt")
    print(f"k_a {k:4.2f} pess {sum(pp.values()):8.0f} opt {sum(po.values()):8.0f} | pess per game " + " ".join(f"{pp[g]:6.0f}" for g in games))
# inflated share per game on lines where anyone charged and line not clearly excluded
print("\nshare of positive charges inflated per game (lines with any acceptance or t_lo>0):")
for g, G in D["games"].items():
    n = i = 0
    for ln, L in G["lines"].items():
        if L["t_lo"] <= 0 and not any(A["n_acc"] > 0 and A["status"] != "zero" for A in L["A"].values()): continue
        for t, A in L["A"].items():
            if A["status"] == "zero": continue
            n += 1; i += A["status"] == "inflated"
    print(f"  game {g}: {i}/{n}")
tot = {t["team_name"]: t["total"] for t in D["matrix"]["items"]}
order = sorted(tot.values(), reverse=True)
print("our total", round(tot[us]), "rank", order.index(tot[us]) + 1)
