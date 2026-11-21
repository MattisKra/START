import tempfile
import unittest
from pathlib import Path

from .hybrid import choose
from .hybrid_watch import new_events


class HybridTest(unittest.TestCase):
    def setUp(self):
        self.line = dict(index=1, charge_price=80, acceptance_limit=95, fair_median_gross_if_valid=100,
                         p_valid=.8, evidence="three billed hours")
        self.value = dict(validity=.9, eligible_work=True, gross_median=100)
        self.readers = {name: {1: self.value} for name in ("alpha/low", "alpha/medium", "beta/low")}

    def selected(self):
        return choose([self.line], self.readers, [1])[0]

    def test_two_models_and_common_charge(self):
        row = self.selected()
        self.assertEqual((row["selected"], row["factor_limit"], row["acceptance_limit"], row["charge_price"]),
                         ("fable", 55, 95, 80))
        del self.readers["beta/low"]
        self.assertEqual(self.selected()["selected"], "factor")

    def test_dissent_scope_coverage_and_equidistance(self):
        for change in (dict(eligible_work=False), dict(validity=.5), dict(gross_median=75)):
            self.readers["alpha/medium"] = {1: {**self.value, **change}}
            self.assertEqual(self.selected()["supporting_models"], ["beta"])
            self.assertEqual(self.selected()["acceptance_limit"], 55)

    def test_zero_gate_and_no_readers(self):
        self.readers = {}
        self.line["p_valid"] = .6
        self.assertEqual(self.selected()["acceptance_limit"], 0)
        self.line.pop("p_valid")
        with self.assertRaises(ValueError):
            self.selected()

    def test_partial_trace_line_waits_for_newline(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "trace.jsonl"
            p.write_bytes(b'{"n":1}\n{"n":')
            offsets = {}
            self.assertEqual(list(new_events(p, offsets)), [{"n": 1}])
            with p.open("ab") as f:
                f.write(b'2}\n')
            self.assertEqual(list(new_events(p, offsets)), [{"n": 2}])
            self.assertEqual(list(new_events(p, offsets)), [])
