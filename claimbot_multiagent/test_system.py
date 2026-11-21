import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from claimbot.case import Case, pdf_text
from claimbot import config

from .research import earlier_jobs
from .runner import estimate
from .schema import Assessment, Full, Valuation
from .settlement import combine, invoice_items


class SystemTests(unittest.TestCase):
    def setUp(self):
        self.case = Case(Path("case_012"), "", "", """POS. DESCRIPTION AMOUNT UNIT TOTAL
8 Technician visit 1 flat rate
21 Repair labor on two doors 6 hrs
Created on 1 Jan""")
        self.items = invoice_items(self.case.invoice_text)
        self.full = Full(
            coverage=[dict(position=i.position, covered=True, probability_if_related=1, basis="repair",
                           payout_fraction=1, clause="§1") for i in self.items],
            attribution=[dict(position=i.position, related=True, probability=1, invoice_unit=i.unit, related_share=0.5,
                              attributable_invoice_units=1 if i.position == 8 else None, evidence="One visit and one damaged door")
                         for i, unit in zip(self.items, ["visit", "item"])],
            limits=[dict(positions=[8, 21], amount_gross=105, clause="§2")],
            quotes=[dict(position=i.position, basis="repair", operation=unit, invoice_unit=i.unit,
                         fixed_fee=i.position == 8, operations=1 if i.position == 8 else 2, invoice_units_per_operation=qty, p10=price, p50=price, p90=price, vat=0,
                         inclusions="one visit or hours per door", source="test quote")
                    for i, unit, qty, price in zip(self.items, ["visit", "item"], [1, 2], [90, 60])],
            anchors=[], lookup_queries=[])
        self.fallback = combine(self.items, self.full, self.full)

    def call(self, case, spec, *, fast=False, schema=None, **kwargs):
        if fast:
            return self.fallback, {}
        return schema.model_validate(self.full.model_dump()), {"usage": {"cost": .01}}

    def test_grouped_decimal_quantity(self):
        from claimbot.memtext import parse_invoice_lines
        from claimbot.refs import invoice_lines

        text = ("POS. DESCRIPTION AMOUNT UNIT TOTAL\n"
                " 1    Electricity for drying equipment    2,412.1   kWh\nCreated on 1 Jan")
        item, = invoice_items(text)
        self.assertEqual((item.position, item.quantity, item.unit), (1, 2412.1, "kWh"))
        memory_line, = parse_invoice_lines(text)
        self.assertEqual((memory_line["qty"], memory_line["unit"]), (2412.1, "kWh"))
        self.assertEqual(invoice_lines(text), ["Electricity for drying equipment"])

    def test_all_architectures_use_same_settlement(self):
        for count in [1, 2, 3]:
            record = estimate(self.case, spec=None, count=count, call=self.call)
            self.assertEqual(record["winner"], "specialist", record)
            self.assertEqual([(x["index"], x["median"]) for x in record["payload"]], [(8, 45), (21, 60)])

    def test_incompatible_units_use_fallback(self):
        self.full.quotes[0].invoice_unit = "hour"
        record = estimate(self.case, spec=None, fast="fast", call=self.call)
        self.assertEqual(record["winner"], "mixed")
        self.assertEqual(record["line_sources"], {8: "fallback", 21: "specialist"})
        self.assertEqual([x["median"] for x in record["payload"]], [45, 60])

    def test_deadline_uses_completed_fallback(self):
        def slow(case, spec, **kwargs):
            if kwargs.get("schema") is Valuation:
                time.sleep(.3)
            return self.call(case, spec, **kwargs)
        record = estimate(self.case, spec=None, fast="fast", call=slow, seconds=.07)
        self.assertEqual(record["winner"], "fallback")
        self.assertIn("valuation", record["timed_out"])

    def test_invalid_group_or_duplicate_position_rejected(self):
        self.full.limits[0].positions = [0]
        with self.assertRaises(ValueError):
            combine(self.items, self.full, self.full)
        self.full.coverage[1].position = 8
        with self.assertRaises(ValueError):
            combine(self.items, self.full, self.full)

    def test_group_disagreement_uses_whole_group(self):
        self.fallback.aggregate_limits[0].amount_gross = 70
        record = estimate(self.case, spec=None, fast="fast", call=self.call)
        self.assertEqual(record["winner"], "fallback")
        self.assertEqual(sum(x["median"] for x in record["payload"]), 70)

    def test_excluded_work_preserves_as_valid_price(self):
        self.full.coverage[0].covered = False
        self.full.coverage[0].basis = "other"
        line = combine(self.items, self.full, self.full).lines[0]
        self.assertEqual((line.p_valid, line.net_unit_price_p50), (0, 90))

    def test_policy_selects_replacement_quote(self):
        q = self.full.quotes[1].model_copy(update={"basis": "replacement_new", "p50": 100, "p90": 120})
        self.full.quotes.append(q)
        self.full.coverage[1].basis = "replacement_new"
        self.assertEqual(combine(self.items, self.full, self.full).lines[1].net_unit_price_p50, 100)

    def test_unknown_conversion_falls_back_only_for_affected_position(self):
        self.full.quotes[1].invoice_units_per_operation = None
        record = estimate(self.case, spec=None, fast="fast", call=self.call)
        self.assertEqual(record["line_sources"], {8: "specialist", 21: "fallback"})

    def test_search_failure_preserves_provisional(self):
        self.full.lookup_queries = ["German technician call-out tariff"]
        def unavailable(*args):
            raise RuntimeError("search unavailable")
        with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test"}):
            record = estimate(self.case, spec=None, call=self.call, web=True, search=unavailable)
        self.assertEqual(record["winner"], "specialist")
        self.assertIn("search unavailable", str(record["errors"]))

    def test_search_revision(self):
        self.full.lookup_queries = ["technician rate"]
        def revised(case, spec, **kwargs):
            answer, meta = self.call(case, spec, **kwargs)
            if kwargs["schema"] is Valuation and '"search_evidence"' in case.invoice_text:
                answer.quotes[0].p10 = answer.quotes[0].p50 = answer.quotes[0].p90 = 120
            return answer, meta
        with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test"}):
            record = estimate(self.case, spec=None, call=revised, web=True, search=lambda *args: ["€120"])
        self.assertEqual(record["payload"][0]["median"], 52.5)

    def test_history_uses_only_earlier_cases(self):
        with TemporaryDirectory() as temp:
            for number in (1, 2, 3):
                path = Path(temp) / f"case_{number:03d}"
                path.mkdir()
                (path / "invoice.txt").write_text(self.case.invoice_text)
                (path / "description.txt").write_text("One damaged door.")
                (path / "results.json").write_text("secret result")
            jobs = earlier_jobs(self.items, Path("case_002"), Path(temp))
            self.assertEqual({j["case"] for j in jobs}, {"case_001"})
            self.assertNotIn("secret result", str(jobs))

    def test_archived_text_matches_pdf_table(self):
        archive = config.ROOT / "past-cases"
        for path in sorted(archive.glob("case_*/invoice.txt")):
            pdf = next(path.parent.glob("invoice*.pdf"))
            self.assertEqual(invoice_items(path.read_text()), invoice_items(pdf_text(pdf)), path)


if __name__ == "__main__":
    unittest.main()
