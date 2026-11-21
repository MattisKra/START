import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .review_turns import ReviewTurns
from .trace import Trace


class ReviewTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name).resolve()
        self.source = self.work / "invoice.txt"
        self.reviews = ReviewTurns([self.source])
        self.trace = Trace(self.work, "review", 100, [1, 2, 3])
        timer = patch("claimbot_shadow.trace.time.time", return_value=120)
        self.clock = timer.start()
        self.addCleanup(timer.stop)
        self.rows = [dict(index=p, charge_price=c, acceptance_limit=b, p_valid=.8,
                          fair_median_gross_if_valid=80, evidence="catalog") for p,c,b in
                     [(3, 10, 10), (2, 150, 20), (1, 15, 150)]]
        self.trace.record(self.rows, dict(policy_proof={"clause": "7.1"}, tool_call="w0"))

    def record(self, action="keep", **changes):
        report = dict(index=1, reason="Invoice quantity verified.", action=action, updates={},
                      **{"pass": 1})
        self.reviews.record(self.trace, {**report, **changes}, ["r"], "w")

    def test_target_order_and_cap(self):
        self.assertIsNone(self.reviews.next(self.trace, 54))
        self.assertIn("position 1,", self.reviews.next(self.trace, 30))
        self.assertIsNone(self.reviews.next(self.trace, 32))
        self.record("revise", updates={"acceptance_limit": 120})
        saved = self.trace.last_on_time
        self.assertEqual(saved["lines"][:2], self.rows[:2])
        self.assertEqual(saved["lines"][2]["acceptance_limit"], 120)
        self.assertIn("position 2,", self.reviews.next(self.trace, 42))
        self.record(index=2, **{"pass": 2})
        self.assertEqual(self.trace.last_on_time["changes"], [])
        self.assertIsNone(self.reviews.next(self.trace, 49))

    def test_invalid_patch_and_late_receipt_preserve_initial(self):
        original = self.trace.last_on_time
        self.reviews.next(self.trace, 50)
        for patch_fields in (dict(index=2), dict(updates={"p_valid": 1.01}, action="revise"),
                             dict(updates={"acceptance_limit": 150}, action="revise"),
                             dict(updates={"p_valid": .5}), dict(reason=" "), {"pass": 2}):
            with self.assertRaises(ValueError):
                self.record(**patch_fields)
        with self.assertRaises(ValueError):
            self.reviews.record(self.trace, dict(index=1, reason="catalog", action="keep", updates={},
                                                **{"pass": 1}), [], "w")
        self.clock.return_value = 160.5
        self.record("revise", updates={"p_valid": .6})
        self.assertEqual(self.trace.last_on_time, original)
        late = json.loads(self.trace.path.read_text().splitlines()[-1])
        self.assertFalse(late["on_time"])

    def test_evidence_must_be_new_and_available_before_write(self):
        def record_source(key, tool="Read", name="invoice.txt", failed=False):
            self.reviews.source(key, "assistant-1", tool, {"file_path": name}, failed, self.work)
        record_source("initial")
        self.reviews.next(self.trace, 20)
        record_source("failed", failed=True)
        record_source("output", name="decision_check.json")
        record_source("created", name="other.txt")
        record_source("list", tool="Glob")
        record_source("r")
        self.assertEqual(self.reviews.prior_sources("assistant-1"), [])
        self.assertEqual(self.reviews.prior_sources("assistant-2"), ["r"])
        self.record()
        self.reviews.next(self.trace, 38)
        self.assertEqual(self.reviews.prior_sources("assistant-3"), [])
