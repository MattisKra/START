"""Exercise paired reviewer-cost bounds under known and hidden charges, including cap ties."""
import random
import unittest
from itertools import permutations

from policy_family_replay import TEAM, reconstruct, savings


def payment(charge, limit, fair, cap):
    if charge <= limit:
        return min(charge, cap)
    return 1.5 * charge if charge <= fair else 0.


class ReviewerSavingsTest(unittest.TestCase):
    def test_contains_true_paired_saving(self):
        rng = random.Random(19)
        teams = (TEAM, "b", "c", "d", "e")
        for _ in range(5000):
            fair = rng.choice([0, 1, 5, 25, 64, 100])
            cap = max(1, 4 * fair, rng.choice([1, 40, 200]))
            amounts = [0, 1, fair, max(0, fair - 1), fair + 1, cap, cap + 1, 3 * cap]
            charges = {team: rng.choice(amounts) for team in teams}
            limits = {team: rng.choice(amounts) for team in teams}
            rows = [
                dict(line_item_index=1, issuer=i, reviewer=j, accepted=charges[i] <= limits[j],
                     amount=payment(charges[i], limits[j], fair, cap))
                for i, j in permutations(teams, 2)
            ]
            line = reconstruct(rows, TEAM)[1]
            for _ in range(12):
                low, high = sorted(rng.sample(sorted(set(amounts)), 2))
                lo, hi = savings(line, low, high)
                actual = sum(payment(charges[t], low, fair, cap) - payment(charges[t], high, fair, cap)
                             for t in teams if t != TEAM)
                self.assertLessEqual(lo, actual)
                self.assertLessEqual(actual, hi)
            self.assertEqual(savings(line, cap, cap), (0., 0.))
