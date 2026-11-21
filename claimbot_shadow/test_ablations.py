import unittest

from claimbot_multiagent.settlement import Item
from .ablations import select


class AblationTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(index=1, charge_price=65, fable_limit=100, factor_limit=55,
                        acceptance_limit=55, p_valid=.9, readers={})
        self.hour = Item(1, "Installer", 3, "hrs")
        self.part = Item(1, "Frame", 1, "pcs")

    def witness(self, member, median=100, validity=.9):
        self.row["readers"][member] = {"value": {"gross_median": median, "validity": validity,
                                                  "eligible_work": False}}

    def test_label_requires_fable_validity_and_no_votes(self):
        for item in (self.hour, Item(1, "Bicycle assembly costs", 1, "flat rate")):
            result = select(self.row, item)
            self.assertEqual((result["label_only"], result["vote_only"]), (100, 55))
        self.row["p_valid"] = .6
        self.assertEqual(select(self.row, self.hour)["label_only"], 55)

    def test_vote_ignores_label_and_counts_models(self):
        self.witness("alpha/medium")
        self.witness("alpha/low")
        self.assertEqual(select(self.row, self.part)["vote_only"], 55)
        self.witness("beta/low")
        result = select(self.row, self.part)
        self.assertEqual((result["charge_price"], result["label_only"], result["vote_only"]), (65, 55, 100))
        for median, validity in ((77.5, .9), (100, .6)):
            self.witness("alpha/low", median, validity)
            self.assertEqual(select(self.row, self.part)["vote_only"], 55)
