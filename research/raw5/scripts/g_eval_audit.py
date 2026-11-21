"""Audit G, step 5: re-run the candidates of research/bench/euro_eval.py and test how much its headline numbers can carry.

    .venv/bin/python -I research/raw5/scripts/g_eval_audit.py FIELD_DIR --us "Team Name" [--games 1-8]

--games A-B restricts the games (default 1-8 = the games behind the README table; euro_eval.py itself takes every game that has saved answers).

Same candidates as euro_eval.py (saved reader answers of games 1-8 through claimbot_fable.engine), scored with the ORIGINAL replay and with the fixed
reference (g_replay_fixed.py). Reports: (a) both lower bounds side by side, (b) how much of each lower bound rests on the unproven 'hidden charge'
ceiling, (c) the per-game split of the best candidate's gain, (d) which candidate pairs can be separated at all, (e) leave-one-game-out selection.
Prints only our own numbers and aggregates; other teams' rows stay in memory.
"""
import glob, importlib.util, itertools, json, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


er = _load("er", ROOT / "research/bench/euro_replay.py")
fx = _load("fx", HERE / "g_replay_fixed.py")
from claimbot_fable import engine                      # noqa: E402
from claimbot_fable.schema import ReaderCase           # noqa: E402

INF = float("inf")
LUNA, TERRA, FABLE = ("openrouter:openai/gpt-6-luna:low:noimage", "openrouter:openai/gpt-6.1-terra:medium", "openrouter:anthropic/claude-fable-5.2:low")
field_dir, us = sys.argv[1], sys.argv[sys.argv.index("--us") + 1]
games = er.load_field(field_dir)
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
saved = {}
for f in sorted(glob.glob(str(ROOT / "runs/bench/fable_eval/*.json"))):
    for r in json.load(open(f))["answers"]:
        saved[(r["reader"], r["case"])] = r
_lo, _hi = (int(x) for x in (sys.argv[sys.argv.index("--games") + 1] if "--games" in sys.argv else "1-8").split("-"))
G = [g for g in sorted(games) if _lo <= g <= _hi and str(g) in logs and all((r, f"case_{g:03d}") in saved for r in (LUNA, TERRA, FABLE))]
rec = {}
for g in G:
    sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs[str(g)]["submitted"]}
    kw = dict(our_b={l: b for l, (a, b) in sub.items()}, our_a={l: a for l, (a, b) in sub.items()})
    rec[g] = dict(er=er.reconstruct(games[g], us, **kw), fx=fx.reconstruct(games[g], us, **kw), sub=sub, act=er.actual_net(games[g], us))
act_total = sum(v["act"] for v in rec.values())
P = engine.Params


def policy_from(reader, params):
    out = {}
    for g in G:
        est = ReaderCase.model_validate(saved[(reader, f"case_{g:03d}")]["est"])
        out[g] = {x.index + 1: (x.a, x.b) for x in engine.compute(est, params)}
    return out


def score(pol, which):
    mod = er if which == "er" else fx
    per = {g: mod.game_value(rec[g][which], us, pol[g])[:2] for g in G}
    return per


def hidden_exposure(pol):
    """EUR of the ORIGINAL lower bound that rest on the heuristic ceiling, the proven ceiling (b') for the same pairs, and the number of such pairs."""
    heur = sound = 0.0; n = 0; n_lines = 0
    for g in G:
        for ln, (a_c, b_c) in pol[g].items():
            line = rec[g]["er"].get(ln)
            if line is None:
                continue
            hit = False
            for i, Ai in line["A"].items():
                if i == us or Ai["a"] is not None or Ai["status"] != "hidden":
                    continue
                floor = max([B["lo"] for jj, B in line["B"].items() if jj != i] + [line.get("our_b", 0.0)])
                if b_c > floor:
                    U, L = line["U"], line["L"]
                    heur += 4 * max(U if U < INF else L, floor, 1.0); sound += b_c; n += 1; hit = True
            n_lines += hit
    return heur, sound, n, n_lines


cands = {"ACTUAL submissions": {g: rec[g]["sub"] for g in G}}
for nm, rd in (("luna", LUNA), ("terra", TERRA), ("fable", FABLE)):
    cands[f"{nm}: engine defaults"] = policy_from(rd, P())
for nm, rd in (("luna", LUNA), ("terra", TERRA)):
    for ka, kb in ((0.8, 1.0), (0.8, 0.8), (0.7, 0.9), (0.9, 1.0), (0.9, 0.7), (1.0, 1.0), (0.6, 0.6)):
        cands[f"{nm}: KA {ka} / KB {kb}"] = policy_from(rd, P(ka_open=ka, kb_open=kb, ka_pinned=ka - .05, kb_pinned=min(kb, 1.05)))
for ex in ("as_valid", "zero"):
    cands[f"luna: KA .8 / KB 1.0, excluded '{ex}'"] = policy_from(LUNA, P(ka_open=.8, kb_open=1.0, ka_pinned=.75, kb_pinned=1.0, excluded_a=ex))

# line coverage of every candidate (a missing line trades with a = b = 0 in reality; euro_replay.game_value skips it)
miss = {n: sum(len(set(rec[g]["er"]) - set(p[g])) for g in G) for n, p in cands.items()}
print(f"games {G}; our actual net over these games {act_total:+.0f}; candidate lines missing from a policy: {sum(miss.values())}")
print(f"\n(a) lower / upper bound of the net, ORIGINAL vs FIXED replay, and the part of the original lower bound that is the unproven hidden-charge ceiling")
print(f"{'candidate':38s} {'orig lo':>9s} {'orig hi':>9s} | {'fixed lo':>9s} {'fixed hi':>9s} | {'d_lo orig':>9s} {'d_lo fixed':>10s} | hidden pairs: n, heuristic EUR, proven ceiling EUR")
S = {}
for n, p in cands.items():
    o = score(p, "er"); f = score(p, "fx")
    S[n] = (o, f)
    olo, ohi = sum(v[0] for v in o.values()), sum(v[1] for v in o.values())
    flo, fhi = sum(v[0] for v in f.values()), sum(v[1] for v in f.values())
    h, s, k, kl = hidden_exposure(p)
    print(f"{n:38s} {olo:>9.0f} {ohi:>9.0f} | {flo:>9.0f} {fhi:>9.0f} | {olo - act_total:>+9.0f} {flo - act_total:>+10.0f} | {k:>3d} pairs on {kl:>2d} lines, {h:>8.0f}, {s:>8.0f}")

print("\n(b) per-game lower-bound delta versus actual (FIXED replay), top candidates; share of the total that comes from the two largest games")
top = sorted((n for n in cands if n != "ACTUAL submissions"), key=lambda n: -sum(v[0] for v in S[n][1].values()))[:6]
print(f"{'candidate':38s} " + " ".join(f"{'g' + str(g):>8s}" for g in G) + f" {'total':>9s}  top-2 games share; games with delta_lo > 0")
for n in top:
    d = [S[n][1][g][0] - rec[g]["act"] for g in G]
    tot = sum(d); big = sorted(d, key=lambda x: -x)[:2]
    print(f"{n:38s} " + " ".join(f"{x:>+8.0f}" for x in d) + f" {tot:>+9.0f}  {sum(big) / tot if tot else float('nan'):>5.0%}; {sum(1 for x in d if x > 0)}/{len(G)}")
print("   actual net per game:               " + " ".join(f"{rec[g]['act']:>+8.0f}" for g in G))

print("\n(c) can two candidates be separated? pairs (A, B) with lower bound of A above upper bound of B, summed over the games (FIXED replay)")
names = [n for n in cands]
sep = [(a, b) for a, b in itertools.permutations(names, 2) if sum(v[0] for v in S[a][1].values()) > sum(v[1] for v in S[b][1].values())]
print(f"   {len(sep)} of {len(names) * (len(names) - 1)} ordered pairs are separated; of these {sum(1 for a, b in sep if b == 'ACTUAL submissions')} are 'candidate surely above ACTUAL', "
      f"{sum(1 for a, b in sep if 'ACTUAL' not in a and 'ACTUAL' not in b)} are candidate versus candidate")
w = [sum(v[1] - v[0] for v in S[n][1].values()) for n in names if n != "ACTUAL submissions"]
los = [sum(v[0] for v in S[n][1].values()) for n in names if n != "ACTUAL submissions"]
print(f"   range width of a candidate: median {st.median(w):.0f} EUR (min {min(w):.0f}, max {max(w):.0f}); spread of the candidates' lower bounds: {max(los) - min(los):.0f} EUR "
      f"(median gap between neighbours {st.median([b - a for a, b in zip(sorted(los), sorted(los)[1:])]):.0f} EUR)")

print("\n(d) leave-one-game-out selection: choose the multiplier candidate with the best lower bound on the other games, then look at the held-out game (FIXED)")
pool = [n for n in names if "KA" in n and "excluded" not in n]
tot_sel = 0.0; tot_best = 0.0
for g in G:
    rest = [x for x in G if x != g]
    pick = max(pool, key=lambda n: sum(S[n][1][x][0] for x in rest))
    d = S[pick][1][g][0] - rec[g]["act"]; h = S[pick][1][g][1] - rec[g]["act"]
    best = max(S[n][1][g][0] for n in pool) - rec[g]["act"]
    tot_sel += d; tot_best += best
    print(f"   held-out game {g}: picked '{pick}'  delta range vs actual on the held-out game [{d:+.0f}, {h:+.0f}]   (best possible lower-bound delta in the pool {best:+.0f})")
print(f"   sum of held-out lower-bound deltas {tot_sel:+.0f} EUR (in-sample best single candidate {max(sum(S[n][1][x][0] for x in G) for n in pool) - act_total:+.0f}; per-game oracle {tot_best:+.0f})")

print("\n(e) how much of the 'better than actual' margin is our own identifiable mistakes: per line, the actual policy's known loss sources")
for g in G:
    for ln, (a, b) in sorted(rec[g]["sub"].items()):
        line = rec[g]["fx"][ln]; me = line["A"].get(us, {})
        n_fair_rej = sum(1 for i, Ai in line["A"].items() if i != us and Ai["status"] == "fair" and Ai["a"] > b)
        pen = sum(1.5 * Ai["a"] for i, Ai in line["A"].items() if i != us and Ai["status"] == "fair" and Ai["a"] > b)
        paid_infl = sum((Ai["x"] or 0) for i, Ai in line["A"].items() if i != us and Ai["status"] == "inflated" and Ai["exact"] and Ai["a"] <= b)
        print(f"   g{g} l{ln}: our a={a:>8.2f} ({me.get('status')}), b={b:>8.2f}; t in [{line['L']:.2f}, {line['U']:.2f}); penalties paid for {n_fair_rej} fair charges {pen:>8.0f}; paid for inflated charges {paid_infl:>8.0f}")

print("\n(f) the two sides separately (FIXED replay): revenue as issuer (depends on the charge a) and cost as reviewer (depends on the limit b)")
act_rev = sum(r["amount"] for g in G for r in games[g] if r["issuer"] == us); act_cost = sum(r["amount"] for g in G for r in games[g] if r["reviewer"] == us)
print(f"   actual: revenue {act_rev:.0f}, cost {act_cost:.0f}")
print(f"{'candidate':38s} {'rev lo':>9s} {'rev hi':>9s} {'width':>8s} | {'cost lo':>9s} {'cost hi':>9s} {'width':>8s} | cost surely below actual by / revenue surely above actual by")
side = {}
for n, p in cands.items():
    rl = rh = cl = ch = 0.0
    for g in G:
        for ln in rec[g]["fx"]:
            a, b = p[g].get(ln, (0.0, 0.0))
            x = fx.line_parts(rec[g]["fx"][ln], us, a, b)
            rl += x[0]; rh += x[1]; cl += x[2]; ch += x[3]
    side[n] = (rl, rh, cl, ch)
    print(f"{n:38s} {rl:>9.0f} {rh:>9.0f} {rh - rl:>8.0f} | {cl:>9.0f} {ch:>9.0f} {ch - cl:>8.0f} | {act_cost - ch:>+9.0f} / {rl - act_rev:>+9.0f}")
names_c = [n for n in cands if n != "ACTUAL submissions"]
sep_cost = sum(1 for a, b in itertools.permutations(names_c, 2) if side[a][3] < side[b][2])
sep_rev = sum(1 for a, b in itertools.permutations(names_c, 2) if side[a][0] > side[b][1])
print(f"   candidate pairs separated on the COST side: {sep_cost} of {len(names_c) * (len(names_c) - 1) // 2} unordered pairs; on the REVENUE side: {sep_rev}")

print("\n(g) reader draw noise: luna has two saved answers for games 1-6; the same multipliers scored on each draw (FIXED, games 1-6 only)")
draws = {}
for f in sorted(glob.glob(str(ROOT / "runs/bench/fable_eval/*.json"))):
    for r in json.load(open(f))["answers"]:
        if r["reader"] == LUNA and r.get("est"):
            draws.setdefault(r["case"], []).append(r)
G2 = [g for g in G if len(draws.get(f"case_{g:03d}", [])) >= 2]
act2 = sum(rec[g]["act"] for g in G2)
print(f"   games with two luna draws: {G2}; actual net on them {act2:+.0f}")
for ka, kb in ((0.9, 1.25), (0.8, 1.0), (0.8, 0.8), (0.7, 0.9), (0.6, 0.6)):
    prm = P(ka_open=ka, kb_open=kb, ka_pinned=(0.85 if (ka, kb) == (0.9, 1.25) else ka - .05), kb_pinned=min(kb, 1.05))
    out = []
    for d in (0, 1):
        lo = hi = 0.0
        for g in G2:
            est = ReaderCase.model_validate(draws[f"case_{g:03d}"][d]["est"])
            pol = {x.index + 1: (x.a, x.b) for x in engine.compute(est, prm)}
            l, h, _ = fx.game_value(rec[g]["fx"], us, pol); lo += l; hi += h
        out.append((lo - act2, hi - act2))
    print(f"   luna KA {ka} / KB {kb}: delta vs actual  draw 1 [{out[0][0]:+.0f}, {out[0][1]:+.0f}]   draw 2 [{out[1][0]:+.0f}, {out[1][1]:+.0f}]   lower bounds differ by {abs(out[0][0] - out[1][0]):.0f} EUR")

print("\n(h) sweeps on the luna answer (FIXED): the revenue bound as a function of KA (KB irrelevant) and the cost bound as a function of KB (KA irrelevant)")
def sides(reader, ka, kb):
    pol = policy_from(reader, P(ka_open=ka, kb_open=kb, ka_pinned=ka, kb_pinned=kb))
    rl = rh = cl = ch = 0.0
    for g in G:
        for ln in rec[g]["fx"]:
            a, b = pol[g].get(ln, (0.0, 0.0))
            x = fx.line_parts(rec[g]["fx"][ln], us, a, b); rl += x[0]; rh += x[1]; cl += x[2]; ch += x[3]
    return rl, rh, cl, ch
for nm, rd in (("luna", LUNA), ("terra", TERRA), ("fable", FABLE)):
    print(f"   {nm}: KA    " + " ".join(f"{k / 100:>7.2f}" for k in range(50, 115, 5)))
    v = [sides(rd, k / 100, 1.0) for k in range(50, 115, 5)]
    print(f"   {nm}: rev lo" + " ".join(f"{x[0]:>7.0f}" for x in v))
    print(f"   {nm}: rev hi" + " ".join(f"{x[1]:>7.0f}" for x in v))
    print(f"   {nm}: KB    " + " ".join(f"{k / 100:>7.2f}" for k in range(50, 155, 10)))
    v = [sides(rd, 0.8, k / 100) for k in range(50, 155, 10)]
    print(f"   {nm}: cost lo" + " ".join(f"{x[2]:>6.0f} " for x in v))
    print(f"   {nm}: cost hi" + " ".join(f"{x[3]:>6.0f} " for x in v))
print(f"   (actual: revenue {act_rev:.0f}, cost {act_cost:.0f}; one multiplier for open and pinned lines in this sweep)")

print("\n(i) replay of our ACTUAL submissions, every logged game (FIXED): must be exact")
for g in sorted(games):
    if str(g) not in logs:
        continue
    sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs[str(g)]["submitted"]}
    kw = dict(our_b={l: b for l, (a, b) in sub.items()}, our_a={l: a for l, (a, b) in sub.items()})
    lo, hi, idn = fx.game_value(fx.reconstruct(games[g], us, **kw), us, sub); act = er.actual_net(games[g], us)
    print(f"   game {g}: actual {act:.2f}  replay [{lo:.2f}, {hi:.2f}]  identified {idn:.0%}")

print("\n(j) cost side per game, luna answer, one KB for all lines (FIXED): is 'lower KB costs less' the same story in every game?")
kbs = (0.5, 0.6, 0.8, 1.0, 1.25)
print("   game  actual cost | " + " | ".join(f"KB {k:<4} [lo, hi]   " for k in kbs))
wins = {k: 0 for k in kbs}
for g in G:
    cells = []
    actc = sum(r["amount"] for r in games[g] if r["reviewer"] == us)
    rng_ = {}
    for k in kbs:
        est = ReaderCase.model_validate(saved[(LUNA, f"case_{g:03d}")]["est"])
        pol = {x.index + 1: (x.a, x.b) for x in engine.compute(est, P(ka_open=0.8, kb_open=k, ka_pinned=0.8, kb_pinned=k))}
        cl = ch = 0.0
        for ln in rec[g]["fx"]:
            a, b = pol.get(ln, (0.0, 0.0)); x = fx.line_parts(rec[g]["fx"][ln], us, a, b); cl += x[2]; ch += x[3]
        rng_[k] = (cl, ch); cells.append(f"[{cl:>6.0f}, {ch:>6.0f}]    ")
        wins[k] += ch < actc
    print(f"   {g:>4d} {actc:>12.0f} | " + " | ".join(cells))
print("   games in which the cost is surely below our actual cost: " + ", ".join(f"KB {k}: {v}/{len(G)}" for k, v in wins.items()))
