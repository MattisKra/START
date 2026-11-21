"""Do the photos help? Runs the current ensemble members on past cases WITHOUT images and compares with logged runs with images.

Usage (repo root):  uv run python research/ensemble_analysis/no_image.py 5 6 [--repeats 1]
Never touches the game API. Raw answers: runs/no_image.json (local).
"""
import argparse, dataclasses, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from claimbot import ensemble, pricing  # noqa: E402
from claimbot.case import load_case  # noqa: E402

SAVE = ROOT / "runs/no_image.json"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("games", nargs="+", type=int); ap.add_argument("--repeats", type=int, default=1)
    a = ap.parse_args()
    saved = json.loads(SAVE.read_text()) if SAVE.exists() else {}
    ms = ensemble.members()
    cases = {g: dataclasses.replace(load_case(ROOT / f"past-cases/case_{g:03d}"), images=[], image_blobs=[]) for g in a.games}
    jobs = [(g, m, k) for g in a.games for m in ms for k in range(a.repeats) if f"{g}|{m.name}|{k}" not in saved]

    def run(job):
        g, m, k = job
        try:
            est, meta = ensemble.run_member(cases[g], m)
            return job, {"estimate": est.model_dump(), "meta": meta, "prices": [p.as_dict() for p in pricing.price_case(est)]}
        except Exception as e:  # noqa: BLE001
            return job, {"error": repr(e)[:300]}
    with ThreadPoolExecutor(16) as ex:
        for (g, m, k), res in ex.map(run, jobs):
            saved[f"{g}|{m.name}|{k}"] = res
    SAVE.write_text(json.dumps(saved, indent=1, ensure_ascii=False, default=str))
    for key, r in sorted(saved.items()):
        if "error" in r:
            print("ERROR", key, r["error"]); continue
        u = r["meta"]["usage"]
        print(f"{key:36s} {r['meta']['latency_s']:5.1f}s in={u['input_tokens']:6d} " + "  ".join(
            f"L{p['index'] + 1} q={p['q']:.2f} med={p['t_median']:.0f}" for p in r["prices"]))


if __name__ == "__main__":
    main()
