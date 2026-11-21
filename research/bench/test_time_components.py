import unittest

from score_time_components import breakdown, compare


class ComponentTest(unittest.TestCase):
    def test_gross_costs_for_labour_and_equipment(self):
        parts = dict(labour=[dict(role="technician", person_hours=2.5, gross_per_hour=78)],
                     equipment=[dict(item="dryer", unit_days=7, gross_per_day=22)], other_gross=30)
        row = dict(time_components=parts, fair_median_gross_if_valid=379)
        checked = breakdown(row)
        self.assertEqual(checked["status"], "reconciled")
        self.assertEqual((checked["labour_gross"], checked["equipment_gross"]), (195, 154))
        self.assertEqual(breakdown(dict(row, fair_median_gross_if_valid=380))["status"], "median_mismatch")
        self.assertEqual(breakdown(dict(row, time_components=dict(parts, equipment=[])))["equipment_gross"], 0)

    def test_missing_and_malformed_are_distinct(self):
        for parts, status in [(None, "declared_inapplicable"), ({}, "malformed"),
                              (dict(labour=[], equipment=[], other_gross=10), "empty_components"),
                              (dict(labour=[], equipment=[False], other_gross=0), "malformed")]:
            self.assertEqual(breakdown(dict(time_components=parts))["status"], status)
        self.assertEqual(breakdown({})["status"], "missing")

    def test_unrelated_line_and_equal_actions(self):
        row = dict(index=1, charge_price=20, acceptance_limit=0, time_components=None)
        receipt = dict(lines=[row], elapsed_s=20)
        field = {1: dict(A={})}
        items = {1: dict(position=1, description="Fixed item", unit="pcs", target=False)}
        report = compare(field, items, receipt, receipt)
        self.assertEqual(report["net"], [0, 0])
        self.assertIsNone(report["target_payoff"])
        self.assertEqual(report["lines"][0]["components"]["status"], "declared_inapplicable")
