"""Separate person-hours from unattended equipment-days in a paired Fable shadow."""
import asyncio
import re

from claimbot_multiagent.settlement import invoice_items
from . import fable_arm
from .trace import write_json

INSTRUCTION = """
Before pricing a line with labour or rental time (including a flat-rate service),
check the case for two separate quantities: payable technician person-hours and
equipment unit-days. For labour distinguish roles, headcount, attended time and
necessary work. For equipment multiply device count by supported rental days.
Separate setup, monitoring and collection visits from unattended runtime. Check
bundled travel, materials and duplicated work. Use gross EUR rates, VAT once.
State the case evidence and label inferred quantities or rates in evidence.
For every line include time_components: null if neither kind applies, otherwise
an object with labour (array of {role, person_hours, gross_per_hour}), equipment
(array of {item, unit_days, gross_per_day}), and other_gross (remaining covered
cost conditional on eligibility). Use an empty array for an absent component.
Use those amounts to calculate fair_median_gross_if_valid to the nearest euro
or cent. Keep coverage probability separate and choose your own charge and limit.
"""

# Frozen invoice-only slice. All positions still enter the primary payoff.
TARGET = re.compile(r"\b(?:technicians?|hours?|labou?r|drying|dryers?|dehumidifi\w*|"
                    r"rentals?|hire|leak detection|assembly|installation)\b", re.I)


def run(case, trace):
    items = invoice_items(case.invoice_text)
    write_json(trace.path.parent / "time_items.json", [
        dict(position=i.position, description=i.description, unit=i.unit,
             target=bool(TARGET.search(i.description) or i.unit.lower() in {"h", "hr", "hrs", "day", "days"}))
        for i in items])
    asyncio.run(fable_arm.run_case(case, trace, prompt_addition=INSTRUCTION))
