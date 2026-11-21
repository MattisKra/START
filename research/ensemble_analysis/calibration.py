"""How far the combined median is from the fair-value bracket per line, and which multiples of the median
for the charge (ka) and the acceptance limit (kb) replay best. Bounds of live games are read in memory only.

  uv run python research/ensemble_analysis/calibration.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import redundancy as R  # noqa: E402

E = R.E


def current(game: dict) -> list[str]:
    """Members that are in the ensemble now (no web members, no removed models)."""
    return [n for n in game["members"] if n.split("/")[0] in R.ensemble.SIZE_WEIGHT and not n.endswith("+web")]


def main() -> None:
    games = R.load()
    lines = []  # (game, line, q, median, bounds)
    print("game line     q   median     t_lo     t_hi   t/median")
    for g in sorted(games):
        game = games[g]
        for idx, p in sorted(R.combined(game, current(game)).items()):
            bd = game["bounds"].get(str(idx + 1))
            if not bd:
                continue
            lines.append((g, idx + 1, p.q, p.t_median, bd))
            lo, hi = bd["t_lo"], bd["t_hi"]
            mid = math.sqrt(lo * hi) if lo > 0 and hi else (lo or 0.0)
            print(f"{g:4d} {idx + 1:4d}  {p.q:4.2f} {p.t_median:8.0f} {lo:8.0f} {hi if hi is not None else float('nan'):8.0f}"
                  f"   {mid / p.t_median if p.t_median else float('nan'):6.2f}")

    def net(ka: float, kb: float, sel) -> float:
        tot = 0.0
        for g, _, q, med, bd in lines:
            if g not in sel:
                continue
            b = kb * med if (1 - q) < 1 / 3 else 0.0
            tot += E.replay(ka * med, b, bd)["net"]
        return tot

    all_g = sorted(games)
    kas = [0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 0.9]
    kbs = [0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]
    for label, sel in (("all games", all_g), ("games 6+", [g for g in all_g if g >= 6]), ("games 1-5", [g for g in all_g if g <= 5])):
        print(f"\nreplayed net, {label}; rows ka (charge / median), columns kb (limit / median)")
        print("  ka\\kb " + "".join(f"{kb:8.2f}" for kb in kbs))
        for ka in kas:
            print(f"  {ka:5.2f} " + "".join(f"{net(ka, kb, sel):8.0f}" for kb in kbs))

    print("\nleave one game out: best (ka, kb) on the other games, replayed on the held-out game")
    tot = 0.0
    for h in all_g:
        rest = [g for g in all_g if g != h]
        ka, kb = max(((a, b) for a in kas for b in kbs), key=lambda x: net(x[0], x[1], rest))
        v = net(ka, kb, [h])
        tot += v
        print(f"  game {h:2d}: ka={ka:.2f} kb={kb:.2f} -> {v:8.0f}   (current 0.9/0.5: {net(0.9, 0.5, [h]):8.0f})")
    print(f"  sum {tot:.0f}   (current 0.9/0.5: {net(0.9, 0.5, all_g):.0f})")


if __name__ == "__main__":
    main()
