"""Head-to-head on past games: claimbot_fable (one reader + rule engine) against the current 8-member ensemble.

Usage (repo root):  uv run python research/ensemble_analysis/fable_vs_ensemble.py [--repeats 2]
Reads past-cases/case_00N, calls the claimbot_fable readers (never the game API), and replays both bots' (a, b)
against the other teams' revealed charges and limits (same replay as redundancy.py). Raw answers: runs/fable_h2h.json.
"""
import argparse, json, math, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research/prompt_opt")); sys.path.insert(0, str(Path(__file__).parent))
import evaluate as E  # noqa: E402
import redundancy as R  # noqa: E402
from claimbot.case import load_case  # noqa: E402
from claimbot_fable import engine, readers  # noqa: E402
from claimbot_fable.schema import ReaderCase  # noqa: E402

SAVE = ROOT / "runs/fable_h2h.json"
READERS = ["anthropic:claude-fable-5-2:low", "openai:gpt-6.1-terra:medium", "openai:gpt-6-luna:low:noimage"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repeats", type=int, default=2); a = ap.parse_args()
    games = R.load()                                   # our ensemble logs + bounds per game
    saved = json.loads(SAVE.read_text()) if SAVE.exists() else {}
    jobs = [(g, r, k) for g in games for r in READERS for k in range(a.repeats) if f"{g}|{r}|{k}" not in saved]
    cases = {g: load_case(ROOT / f"past-cases/case_{g:03d}") for g in games}

    def run(job):
        g, r, k = job
        try:
            est, meta = readers.read(cases[g], readers.parse_spec(r), fast=r.endswith("noimage"))
            return job, {"est": est.model_dump(), "meta": meta}
        except Exception as e:  # noqa: BLE001
            return job, {"error": repr(e)[:300]}
    with ThreadPoolExecutor(6) as ex:
        for (g, r, k), res in ex.map(run, jobs):
            saved[f"{g}|{r}|{k}"] = res
            print("done", g, r, k, res.get("error", res.get("meta", {}).get("latency_s")), flush=True)
    SAVE.write_text(json.dumps(saved, indent=1, ensure_ascii=False, default=str))

    def replay(prices, bd):                           # prices: {0-based index: (a, b, median)}
        net, errs = 0.0, []
        for idx, (pa, pb, med) in prices.items():
            b = bd.get(str(idx + 1))
            if not b:
                continue
            net += E.replay(pa, pb, b)["net"]
            if b["t_lo"] > 0:
                errs.append(R.logdist(med, b["t_lo"], b["t_hi"]))
        return net, errs

    eight = [n for n in {n for g in games.values() for n in g["members"]} if not n.endswith("+web") and "sonnet" not in n]
    rows = {"current 8-member ensemble": {}}
    for g, game in games.items():
        c = R.combined(game, eight)
        rows["current 8-member ensemble"][g] = [replay({i: (p.a, p.b, p.t_median) for i, p in c.items()}, game["bounds"])]
    for key, res in saved.items():
        g, r, k = key.split("|"); g = int(g)
        if "est" not in res or g not in games:
            continue
        out = engine.compute(ReaderCase.model_validate(res["est"]))
        rows.setdefault("fable engine, " + r, {}).setdefault(g, []).append(replay({x.index: (x.a, x.b, x.m) for x in out}, games[g]["bounds"]))
    gs = sorted(games)
    print(f"\n{'bot':52s} " + " ".join(f"{'g' + str(g):>7}" for g in gs) + f" {'sum':>8} {'|err|':>6}  (mean over repeats; min..max of the sum)")
    for name, per in rows.items():
        means = [sum(n for n, _ in per[g]) / len(per[g]) if g in per else float('nan') for g in gs]
        errs = [e for g in per for _, es in per[g] for e in es if e == e]
        reps = min(len(per[g]) for g in per)
        sums = [sum(per[g][k][0] for g in per) for k in range(reps)]
        print(f"{name:52s} " + " ".join(f"{m:7.0f}" for m in means) + f" {sum(means):8.0f} {sum(errs) / max(len(errs), 1):6.2f}  ({min(sums):.0f}..{max(sums):.0f}, {len(per)} games)")
    for key, res in sorted(saved.items()):
        if "est" in res:
            g, r, k = key.split("|")
            out = engine.compute(ReaderCase.model_validate(res["est"]))
            bd = games[int(g)]["bounds"]
            print(f"  g{g} {r.split(':')[1]:18s} #{k} " + "; ".join(f"L{x.index + 1} m={x.m:.0f} a={x.a:.0f} b={x.b:.0f} q={x.q:.2f}{'P' if x.pinned else ''} t[{bd.get(str(x.index + 1), {}).get('t_lo', float('nan')):.0f},{bd.get(str(x.index + 1), {}).get('t_hi')}]" for x in out))
        else:
            print("  ERROR", key, res["error"])


if __name__ == "__main__":
    main()
