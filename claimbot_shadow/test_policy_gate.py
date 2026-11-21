import tempfile
import unittest
from pathlib import Path

from .policy_gate import PolicyGate


class PolicyGateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name).resolve()
        self.policy = ("1.1 Recovery of insured items\n\nThe reasonable cost of recovering an insured item is covered.\n\n"
                       "1.2 Excluded costs of ordinary maintenance work\n\nRoutine maintenance is excluded.\n")
        self.gate = PolicyGate(self.work, self.policy)
        self.row = dict(index=1, policy_clause="1.1", policy_quote="cost of recovering an insured item")

    def receive(self, file="policy.txt", error=False, content=None):
        self.gate.result("r", "read-turn", "Read", {"file_path": str(self.work / file)},
                         dict(is_error=error, content=content or [dict(type="text", text=self.policy)]))

    def test_read_before_write_required(self):
        before = self.gate.prior_reads("early-write")
        self.receive()
        self.assertIsNone(self.gate.proof([self.row], before))
        self.assertIsNone(self.gate.proof([self.row], self.gate.prior_reads("read-turn")))
        proof = self.gate.proof([self.row], self.gate.prior_reads("later-write"))
        self.assertEqual((proof["clause"], proof["policy_read_id"]), ("1.1", "r"))

    def test_failed_wrong_file_heading_and_wrong_clause_do_not_count(self):
        self.receive(error=True)
        self.receive(file="invoice.txt")
        self.assertEqual(self.gate.prior_reads("later"), [])
        self.receive(content="1\t1.2 Excluded costs of ordinary maintenance work")
        prior = self.gate.prior_reads("later")
        self.assertIsNone(self.gate.proof([self.row], prior))
        self.assertIsNone(self.gate.proof([dict(index=1, policy_clause="1.2",
                          policy_quote="Excluded costs of ordinary maintenance work")], prior))
        self.receive()
        self.assertIsNone(self.gate.proof([{**self.row, "policy_clause":"1.2"}], prior))
