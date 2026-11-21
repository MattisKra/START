"""Do known fair values of past games help as price references in the prompt? Leave-one-game-out test.

Usage (repo root):  uv run python research/ensemble_analysis/price_refs.py [--games 1 2 ...] [--repeats 1]
For each game the current ensemble members are run with a reference list built from all OTHER completed games
(line text, quantity, bracket of the fair value from the public leaderboard). The result is compared with the logged
run without references, using the same replay as redundancy.py. Never touches the game API. Raw answers: runs/price_refs.json.
"""
import argparse, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "research/prompt_opt")); sys.path.insert(0, str(Path(__file__).parent))
import evaluate as E  # noqa: E402
import redundancy as R  # noqa: E402
from claimbot import anthropic_estimator, ensemble, estimator  # noqa: E402
from claimbot.case import load_case  # noqa: E402
from claimbot.schema import CaseEstimate  # noqa: E402

SAVE = ROOT / "runs/price_refs.json"
_orig = estimator.case_text


def ref_block(games: dict, skip: int) -> str:
    rows = []
    for g, game in sorted(games.items()):
        if g == skip:
            continue
        est = next(iter(game["members"].values()))["est"]
        for l in est.lines:
            bd = game["bounds"].get(str(l.index + 1))
            if not bd or bd["t_lo"] <= 0 and bd["t_hi"] is None:
                continue                       # no information, or a line worth 0 for policy reasons
            lo, hi = bd["t_lo"], bd["t_hi"]
            if lo <= 0:
                continue                       # only an upper bound: may be an excluded line, not a price signal
            rng = f"about {lo:.0f} to {hi:.0f}" if hi is not None else f"at least {lo:.0f}"
            rows.append(f"- \"{l.invoice_text[:110]}\" ({l.quantity_invoiced:g} {l.unit}): {rng} EUR")
    return ("PRICE REFERENCES from earlier, unrelated cases of the same assessor (final amounts owed, gross totals for the whole "
            "line, after any policy reduction). Use them only to calibrate the general price level of similar kinds of lines; "
            "the present case has its own policy and facts.\n" + "\n".join(rows) + "\n\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--games", nargs="*", type=int); ap.add_argument("--repeats", type=int, default=1)
    a = ap.parse_args()
    games = R.load()
    todo = a.games or sorted(games)
    saved = json.loads(SAVE.read_text()) if SAVE.exists() else {}
    ms = ensemble.members()
    for g in todo:
        block = ref_block(games, g)
        if g == todo[0]:
            print(block)
        patched = lambda case, _b=block: _b + _orig(case)  # noqa: E731
        estimator.case_text = patched; anthropic_estimator.case_text = patched
        case = load_case(ROOT / f"past-cases/case_{g:03d}")
        jobs = [(m, k) for m in ms for k in range(a.repeats) if f"{g}|{m.name}|{k}" not in saved]

        def run(job):
            m, k = job
            try:
                est, meta = ensemble.run_member(case, m)
                return job, {"estimate": est.model_dump(), "meta": meta}
            except Exception as e:  # noqa: BLE001
                return job, {"error": repr(e)[:300]}
        with ThreadPoolExecutor(8) as ex:
            for (m, k), res in ex.map(run, jobs):
                saved[f"{g}|{m.name}|{k}"] = res
                if "error" in res:
                    print("ERROR", g, m.name, res["error"])
        SAVE.write_text(json.dumps(saved, indent=1, ensure_ascii=False, default=str))
        print("game", g, "done", flush=True)

    w = {m.name: m.weight for m in ms}
    tot = {"base": 0.0, "refs": 0.0}
    print(f"\n{'game':5s}{'line':5s}{'fair value':>16s} | {'base med':>9s}{'a':>8s}{'b':>8s}{'net':>8s} | {'refs med':>9s}{'a':>8s}{'b':>8s}{'net':>8s}")
    for g in sorted(games):
        with_refs = [(CaseEstimate.model_validate(r["estimate"]), w[k.split("|")[1]]) for k, r in saved.items()
                     if k.startswith(f"{g}|") and k.endswith("|0") and "estimate" in r and k.split("|")[1] in w]
        if not with_refs:
            continue
        base = R.combined(games[g], [n for n in games[g]["members"] if n in w])
        refs = {p.index: p for p in ensemble.combine(with_refs)}
        for i in sorted(base):
            bd = games[g]["bounds"].get(str(i + 1))
            if not bd:
                continue
            nb, nr = E.replay(base[i].a, base[i].b, bd)["net"], E.replay(refs[i].a, refs[i].b, bd)["net"]
            tot["base"] += nb; tot["refs"] += nr
            fv = f"[{bd['t_lo']:.0f}, {'inf' if bd['t_hi'] is None else round(bd['t_hi'])})"
            print(f"{g:<5d}{i + 1:<5d}{fv:>16s} | {base[i].t_median:9.0f}{base[i].a:8.0f}{base[i].b:8.0f}{nb:8.0f} | {refs[i].t_median:9.0f}{refs[i].a:8.0f}{refs[i].b:8.0f}{nr:8.0f}")
    print(f"\nreplayed net: without references {tot['base']:.0f}, with references {tot['refs']:.0f}")


if __name__ == "__main__":
    main()
