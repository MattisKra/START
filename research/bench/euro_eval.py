"""Score approaches in EUR with the validated replay (euro_replay.py): net range per game and cumulative, versus our actual live results.

    uv run --with pyzipper python research/bench/euro_eval.py FIELD_DIR --us "Team Name"

FIELD_DIR = scratch folder from research/raw4/scripts/fetch_field.py (OUTSIDE the repo). Candidates are the saved reader answers (luna / terra /
fable, games 1-8) through claimbot_fable.engine with different multipliers. Ranges are sound bounds (validated on synthetic fields with known truth,
and the replay of our actual submissions reproduces our actual net); a candidate only counts as better if its whole delta range is above zero.
Only our own numbers are printed. Other teams' rows stay in memory.
"""
import importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, ROOT / rel); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
er = load("er", "research/bench/euro_replay.py"); ab = load("ab", "research/bench/arch_bench.py")
engine = ab.engine
from claimbot_fable.schema import ReaderCase

field_dir, us = sys.argv[1], sys.argv[sys.argv.index("--us") + 1]
games = er.load_field(field_dir)
logs = json.loads((ROOT / "outputs/model_outputs.json").read_text())["games"]
saved = ab.load_saved()
G = [g for g in sorted(games) if str(g) in logs and all((r, f"case_{g:03d}") in saved for r in (ab.LUNA, ab.TERRA, ab.FABLE))]
rec = {}
for g in G:
    sub = {s["index"] + 1: (s["a"], s["b"]) for s in logs[str(g)]["submitted"]}
    rec[g] = (er.reconstruct(games[g], us, our_b={l: b for l, (a, b) in sub.items()}, our_a={l: a for l, (a, b) in sub.items()}), sub, er.actual_net(games[g], us))
act_total = sum(v[2] for v in rec.values())

def evaluate(name, policies):
    lo = hi = 0.0; per = []
    for g in G:
        l, h, _ = er.game_value(rec[g][0], us, policies[g]); lo += l; hi += h; per.append((l, h))
    d_lo = lo - act_total; d_hi = hi - act_total
    wins = sum(1 for g, (l, h) in zip(G, per) if l > rec[g][2]); losses = sum(1 for g, (l, h) in zip(G, per) if h < rec[g][2])
    print(f"{name:52s} net [{lo:9.0f}, {hi:9.0f}]  delta vs actual [{d_lo:+9.0f}, {d_hi:+9.0f}]  surely better in {wins}/{len(G)} games, surely worse in {losses}")

def policy_from(reader, params, games_=G):
    out = {}
    for g in games_:
        est = ReaderCase.model_validate(saved[(reader, f"case_{g:03d}")]["est"])
        out[g] = {x.index + 1: (x.a, x.b) for x in engine.compute(est, params)}
    return out

print(f"games {G}; our actual net over these games: {act_total:+.0f} (exact)\n")
evaluate("ACTUAL submissions (live bot at the time)", {g: rec[g][1] for g in G})
P = engine.Params
for nm, rd in (("luna", ab.LUNA), ("terra", ab.TERRA), ("fable", ab.FABLE)):
    evaluate(f"{nm}: engine defaults (KA .9/.85, KB 1.25/1.05)", policy_from(rd, P()))
print()
for nm, rd in (("luna", ab.LUNA), ("terra", ab.TERRA)):
    for ka, kb in ((0.8, 1.0), (0.8, 0.8), (0.7, 0.9), (0.9, 1.0), (0.9, 0.7), (1.0, 1.0), (0.6, 0.6)):
        evaluate(f"{nm}: KA {ka} / KB {kb}", policy_from(rd, P(ka_open=ka, kb_open=kb, ka_pinned=ka - .05, kb_pinned=min(kb, 1.05))))
print()
for ex in ("as_valid", "zero"):
    evaluate(f"luna: KA .8 / KB 1.0, excluded lines '{ex}'", policy_from(ab.LUNA, P(ka_open=.8, kb_open=1.0, ka_pinned=.75, kb_pinned=1.0, excluded_a=ex)))
