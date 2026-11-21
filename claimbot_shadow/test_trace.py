import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .__main__ import compare_lines
from .trace import Trace


class ReceiptTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.trace = Trace(Path(temp.name), "arm", 100., [1])
        self.line = dict(index=1, charge_price=22., acceptance_limit=10., evidence="contract rate")

    @patch("claimbot_shadow.trace.time.time", side_effect=[121., 156., 161.])
    def test_last_complete_on_time_receipt(self, clock):
        for limit in (10., 12., 18.):
            self.trace.record([dict(self.line, acceptance_limit=limit)], {"member": "reader"})
        rows = [json.loads(line) for line in self.trace.path.read_text().splitlines()]
        self.assertEqual([True, True, False], [r["on_time"] for r in rows])
        self.assertEqual(rows[1], self.trace.last_on_time)
        self.assertEqual(10., rows[1]["changes"][0]["before"]["acceptance_limit"])
        diff = compare_lines(dict(python=rows[0], fable=rows[1]))
        self.assertEqual((0, 2), (diff[0]["charge_delta"], diff[0]["limit_delta"]))

    def test_invalid_or_missing_decision(self):
        for lines in ([], [self.line, self.line], [dict(self.line, charge_price=float("nan"))]):
            with self.assertRaises(ValueError):
                self.trace.record(lines, {})
        self.assertIsNone(self.trace.last_on_time)
        self.assertIsNone(compare_lines(dict(python=None, fable=None)))
