import tempfile
import unittest
from pathlib import Path

from .exclusions import audit
from .policy_gate import PolicyGate


class ExclusionAuditTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        work = Path(tmp.name).resolve()
        quote = "Loss caused by ordinary wear is excluded"
        policy = "1.2 Exclusions\n\n" + quote + ".\n"
        self.gate = PolicyGate(work, policy)
        self.gate.result("r", "first", "Read", {"file_path": str(work / "policy.txt")},
                         {"content": policy})
        self.row = dict(index=1, coverage_check={
            "exclusion": dict(status="applies", clause="1.2", quote=quote, basis="Report describes ordinary wear."),
            "endorsement": dict(status="not_evidenced", clause=None, quote=None, basis="Schedule unavailable.")})

    def test_prior_read_and_case_only_status(self):
        prior = self.gate.prior_reads("write")
        self.assertEqual(prior, ["r"])
        finding = audit([self.row], self.gate, prior)[0]
        self.assertEqual(finding["exclusion"]["audit"], "verified_policy_quote")
        self.assertEqual(finding["endorsement"]["audit"], "case_claim_without_policy_quote")
        self.assertEqual(audit([self.row], self.gate, [])[0]["exclusion"]["audit"], "unverified_policy_quote")

    def test_missing_invalid_and_blank_findings_are_retained(self):
        self.row["coverage_check"]["endorsement"]["basis"] = ""
        self.row["coverage_check"]["exclusion"]["status"] = ["applies"]
        findings = audit([self.row, {"index": 2}], self.gate, ["r"])
        self.assertEqual(findings[0]["endorsement"]["audit"], "missing_basis")
        self.assertEqual(findings[0]["exclusion"]["audit"], "missing_or_invalid")
        self.assertEqual(findings[1]["exclusion"]["audit"], "missing_or_invalid")
