"""Compare reviewer limits on games 1–15. Run with an external complete-field cache as the only argument."""
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "research/raw5/scripts")]
from claimbot.pricing import _best_charge
from g_replay_fixed import line_parts, reconstruct

TEAM = "Kiebler Software Solutions"
GAMES = range(1, 16)
ANCILLARY = re.compile(r"dispos(al|e)|vehicle|call[- ]?out|diagnostic|shipping|installation|cleaning|"
                       r"leak detection|flat[- ]fee", re.IGNORECASE)


def read(path):
    return json.loads(path.read_text())


def field_for_game(directory, game, teams, archive, matrix):
    rows = read(directory / f"tx_g{game}.json")
    positions = {int(p) for p in archive["lines"]}
    expected = {(p, i, j) for p in positions for i, j in permutations(teams, 2)}
    keys = {(r["line_item_index"], r["issuer"], r["reviewer"]) for r in rows}
    if keys != expected or len(rows) != len(expected):
        raise ValueError(f"Game {game} has incomplete or duplicate settlements")
    nets = defaultdict(float)
    for r in rows:
        nets[r["issuer"]] += r["amount"]
        nets[r["reviewer"]] -= r["amount"]
    column = matrix["game_ids"].index(game)
    for entry in matrix["items"]:
        if abs(nets[entry["team_name"]] - entry["cells"][column]) > .011:
            raise ValueError(f"Game {game} field and standings disagree")
    for role, key in (("issuer", "income"), ("reviewer", "costs")):
        total = sum(r["amount"] for r in rows if r[role] == TEAM)
        if abs(total - archive[key]) > .011:
            raise ValueError(f"Game {game} does not reconcile to archived {key}")
    return rows


def savings(line, low, high):
    """Cost(low) minus cost(high) for one line, same latent state for both limits."""
    if high == low:
        return 0., 0.
    lower = upper = 0.
    for issuer, action in line["A"].items():
        if issuer == TEAM:
            continue
        price, status = action["a"], action["status"]
        if price is None:  # Universally rejected for zero. Any switch adds an inflated payment.
            floor = max(b["lo"] for j, b in line["B"].items() if j != issuer)
            if high > floor:
                lower -= high
            continue
        if price > high or (action["exact"] and price <= low):
            continue
        # When the charge is exactly the settled amount, switching from rejection
        # saves half a fair charge or costs the full inflated payment.
        possibilities = []
        if low < price <= high:
            if status != "inflated" and price < line["U"]:
                possibilities.append(.5 * price)
            if status != "fair" and price > line["L"]:
                possibilities.append(-price)
        if not action["exact"]:
            # A clipped charge exceeds the observed payment and is inflated.
            # It can cross the limit only if some larger charge fits below high.
            possibilities.append(0.)
            if high > price:
                possibilities.append(-price)
        if possibilities:
            lower += min(possibilities)
            upper += max(possibilities)
    return lower, upper


def main(directory):
    matrix = read(directory / "matrix.json")
    teams = {t["team_name"] for t in matrix["items"]}
    if len(teams) != matrix["total"] or TEAM not in teams:
        raise ValueError("Incomplete tournament roster")
    log = read(ROOT / "outputs/model_outputs.json")["games"]
    history = defaultdict(list)
    prior = []
    sums = defaultdict(lambda: [0., 0.])
    issuer_ranges = []
    zero_limit = []
    advisor_split = []
    print("game lines repeats choose_by_family choose_by_last fixed_0.90_savings_EUR advisor_split_savings_EUR")
    for game in GAMES:
        case = ROOT / "past-cases" / f"case_{game:03d}"
        archive = read(case / "results.json")
        rows = field_for_game(directory, game, teams, archive, matrix)
        field = reconstruct(rows, TEAM)  # An attempted submission cannot narrow an interval.
        logged = {p["index"] + 1: p for p in log[str(game)]["submitted"]}
        if set(logged) != set(field):
            raise ValueError(f"Game {game} has unmatched invoice positions")
        family = hashlib.sha256((case / "policy.txt").read_bytes()).digest()
        previous = history[family]
        # Use the higher limit only when earlier games support it even at the lower bound.
        use_family = sum(pair[0] for pair in previous) > 0
        use_last = bool(prior and prior[-1][0] > 0)
        lo = hi = 0.
        zero_lo = zero_hi = split_lo = split_hi = 0.
        descriptions = {l["index"] + 1: l["invoice_text"] for l in log[str(game)]["members"][0]["estimate"]["lines"]}
        for pos, p in logged.items():
            if p["b"] <= 0:  # Preserve the logged eligibility gate for both alternatives.
                continue
            med = p["t_median"]
            base = round(.55 * med, 2)
            from_zero_lo, from_zero_hi = savings(field[pos], 0., base)
            zero_lo -= from_zero_hi
            zero_hi -= from_zero_lo
            if ANCILLARY.search(descriptions[pos]):
                split_lo -= from_zero_hi
                split_hi -= from_zero_lo
            elif previous:
                add_lo, add_hi = savings(field[pos], base, round(1.25 * med, 2))
                split_lo += add_lo
                split_hi += add_hi
            lower, upper = savings(field[pos], base, round(.90 * med, 2))
            lo += lower
            hi += upper
        print(game, len(field), len(previous), int(use_family), int(use_last), f"{lo:.2f} {hi:.2f}", f"{split_lo:.2f} {split_hi:.2f}")
        for label, selected in (("fixed 0.90", True), ("same policy", use_family), ("last game", use_last)):
            if selected:
                sums[label][0] += lo
                sums[label][1] += hi
        if game >= 8:
            # The log records a charge close to 0.90 times the rounded median throughout this block.
            income_low = income_high = 0.
            for pos, p in logged.items():
                med = p["t_median"]
                if abs(p["a"] - .9 * med) > .011:
                    raise ValueError(f"Game {game} does not belong to the fixed-charge period")
                charge = round(_best_charge(math.log(med), p["sigma"]), 2) if med > 0 else 0.
                rev_lo, rev_hi, *_ = line_parts(field[pos], TEAM, charge, 0.)
                income_low += rev_lo
                income_high += rev_hi
            issuer_ranges.append((game, income_low - archive["income"], income_high - archive["income"]))
        zero_limit.append((zero_lo, zero_hi))
        advisor_split.append((split_lo, split_hi))
        previous.append((lo, hi))
        prior.append((lo, hi))
    for label, (lo, hi) in sums.items():
        print(f"{label}: [{lo:.2f}, {hi:.2f}] EUR saved vs fixed 0.55")
    for label, series in (("Zero limit", zero_limit), ("Advisor line split", advisor_split)):
        for start, stop in ((1, 6), (7, 10), (11, 15), (1, 15)):
            subset = series[start - 1:stop]
            print(f"{label} vs fixed 0.55, games {start}-{stop}",
                  *(f"{sum(row[k] for row in subset):.2f}" for k in (0, 1)))
    print("Issuer delta vs settled income, spread-sensitive charge on games 8–15")
    for game, lo, hi in issuer_ranges:
        print(game, f"{lo:.2f} {hi:.2f}")
    print("total", *(f"{sum(row[k] for row in issuer_ranges):.2f}" for k in (1, 2)))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
