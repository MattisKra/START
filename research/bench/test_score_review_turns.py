import unittest

from score_review_turns import audit, compare_at


def receipt(at, limit, number=0):
    return dict(event="decision", elapsed_s=at, on_time=at <= 60,
                trigger=dict(review_pass=number, tool_call=f"w{number}"),
                lines=[dict(index=1, charge_price=0, acceptance_limit=limit, p_valid=.4,
                            fair_median_gross_if_valid=5, evidence="policy exclusion")], changes=[])


class ReviewScoringTest(unittest.TestCase):
    def test_keep_late_and_missing_first_decisions(self):
        from unittest.mock import patch
        first, second = receipt(30, 0), receipt(56, 5, 1)
        def difference(field, initial, final):
            return {"test_delta": final[1][1] - initial[1][1]}
        with patch("score_review_turns.gap", side_effect=difference):
            self.assertEqual(compare_at([first, second], {}, 54)["test_delta"], 0)
            self.assertEqual(compare_at([first, second], {}, 60)["test_delta"], 5)
            self.assertEqual(compare_at([first, receipt(60.5, 5, 1)], {}, 60)["reviews"], 0)
            self.assertEqual(compare_at([receipt(56, 0)], {}, 54)["status"], "missing_initial")

    def test_missing_write_and_final_mismatch_are_rejected(self):
        first = receipt(30, 0)
        with self.assertRaisesRegex(ValueError, "write"):
            audit([first], {1}, first)
        success = dict(event="tool_result", id="w0", failed=False)
        with self.assertRaisesRegex(ValueError, "Final"):
            audit([success, first], {1}, None)
