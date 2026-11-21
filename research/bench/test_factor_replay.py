import unittest

from factor_replay import replay, winner
from policy_family_replay import TEAM, reconstruct


class FactorReplayTest(unittest.TestCase):
    def test_line_verdict_requires_strict_improvement(self):
        for bounds, expected in [([1, 2], "python_factors"), ([-2, -1], "fable"),
                                 ([0, 0], "tie"), ([-1, 2], "unresolved"),
                                 ([0, 1], "unresolved"), ([-1, 0], "unresolved")]:
            self.assertEqual(winner(bounds), expected)

    def test_independent_belief_and_legacy_replay(self):
        rows = [dict(line_item_index=1, issuer=i, reviewer=j, accepted=True, amount=20)
                for i, j in ((TEAM, "other"), ("other", TEAM))]
        field = reconstruct(rows, TEAM)
        cfg = dict(charge_factor=.9, limit_factor=.55, reject_p=1/3)
        row = dict(index=1, charge_price=20, acceptance_limit=40, evidence="estimated frame")
        def run():
            return replay(field, {1: (20, 40)}, {"lines": [row]}, cfg)
        self.assertEqual(run()["explicit_beliefs"]["status"], "unavailable")
        self.assertEqual(run()["fixed_charge_ratio_vs_native"]["issuer_change"], [0, 0])
        row.update(fair_median_gross_if_valid=100, p_valid=.8)
        self.assertEqual(run()["explicit_beliefs"]["hybrid_actions"][1], (90, 55))
        explicit = run()["explicit_beliefs"]
        for metric, bounds in explicit["python_factors_vs_native"].items():
            self.assertEqual(explicit["lines"][0][metric], bounds)
        self.assertEqual(explicit["lines"][0]["fable_limit"], 40)
        row["p_valid"] = .6
        self.assertEqual(run()["explicit_beliefs"]["hybrid_actions"][1], (90, 0))
        row["p_valid"] = float("nan")
        self.assertEqual(run()["explicit_beliefs"]["status"], "unavailable")
