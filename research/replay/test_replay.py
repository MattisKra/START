import json
import unittest
from pathlib import Path

from replay import payout, score, score_suite

HERE = Path(__file__).resolve().parent


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((HERE / "example_case.json").read_text())
        self.values = json.loads((HERE / "example_submission.json").read_text())

    def test_submission(self):
        report = score(self.case, self.values)
        self.assertEqual((report["income"], report["costs"], report["net"]), (135, 95, 40))

    def test_payoffs_and_cap(self):
        for a, b, expected in [(100, 100, 100), (100, 99, 150), (120, 120, 120),
                               (120, 119, 0), (500, 500, 400)]:
            self.assertEqual(payout(a, b, 100, 400), expected)

    def test_missing_line(self):
        self.assertEqual(score(self.case, [])["net"], -142.5)

    def test_suite_uses_every_case(self):
        cases = [dict(scenario=dict(self.case, case_id=k), baseline=self.values) for k in ("1", "2")]
        suite = dict(revision="fixture", cases=cases)
        self.assertEqual(score_suite(suite)["totals"]["net"], 80)
        self.assertEqual(score_suite(suite, {"1": [], "2": self.values})["totals"]["net"], -102.5)
        with self.assertRaises(ValueError):
            score_suite(suite, {"1": self.values})

    def test_invalid_values(self):
        for override in ({"index": 2}, {"charge_price": -1}, {"acceptance_limit": float("nan")}):
            with self.assertRaises(ValueError):
                score(self.case, [dict(self.values[0], **override)])
        with self.assertRaises(ValueError):
            score(self.case, self.values * 2)
