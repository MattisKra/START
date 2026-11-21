"""A frozen reviewer policy using evidence available before the local deadline."""
import re
from collections import defaultdict

from claimbot.pricing import _belief
from claimbot.schema import LineEstimate
from .checks import check

RULE = ("Use Fable's own charge for all arms. Default to 0.55 times Fable's conditional gross "
        "median if its invalid probability is below 1/3, else zero. Switch differing limits "
        "only if at least two distinct Python models support Fable's limit. Every available "
        "effort of a supporting model must identify hourly or assembly work, pass the same "
        "validity gate, and place its gross median strictly closer to Fable's limit.")
LIMIT_FACTOR = 0.55
REJECT_P = 1 / 3
HOUR_UNITS = {"h", "hr", "hrs", "hour", "hours", "std", "std.", "stunden"}


def reader_values(event):
    values = {}
    for line in event["lines"]:
        estimate = line.get("arriving_reader")
        if not estimate:
            continue
        parsed = LineEstimate.model_validate(estimate)
        q, _, _, median = _belief(parsed)
        hourly = parsed.unit.strip().casefold() in HOUR_UNITS
        assembly = bool(re.search(r"\bassembly\b", parsed.invoice_text, re.IGNORECASE))
        values[line["index"]] = dict(description=parsed.invoice_text, eligible_work=hourly or assembly,
                                     validity=q, gross_median=median)
    return values


def choose(lines, readers, positions):
    issues = check(lines, positions)
    if issues:
        raise ValueError(" | ".join(issues))
    choices = []
    for line in lines:
        pos = line["index"]
        native = line["acceptance_limit"]
        factor = round(LIMIT_FACTOR * line["fair_median_gross_if_valid"], 2) if 1 - line["p_valid"] < REJECT_P else 0.
        grouped = defaultdict(list)
        witnesses = {}
        for member, values in readers.items():
            value = values.get(pos)
            supports = bool(value and value["eligible_work"] and 1 - value["validity"] < REJECT_P
                            and abs(value["gross_median"] - native) < abs(value["gross_median"] - factor))
            grouped[member.split("/", 1)[0]].append(supports)
            witnesses[member] = dict(value=value, supports_fable=supports)
        support = sorted(model for model, votes in grouped.items() if all(votes))
        switch = native != factor and len(support) >= 2
        choices.append(dict(index=pos, charge_price=line["charge_price"], acceptance_limit=native if switch else factor,
                            fable_limit=native, factor_limit=factor, selected="fable" if switch else "factor",
                            fair_median=line["fair_median_gross_if_valid"], p_valid=line["p_valid"],
                            supporting_models=support, readers=witnesses))
    return choices
