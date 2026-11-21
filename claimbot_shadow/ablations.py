"""Predeclared arms scored on identical, timestamped hybrid revisions."""
from collections import defaultdict
import re
from .hybrid import HOUR_UNITS, REJECT_P


def select(row, item):
    native, factor = row["fable_limit"], row["factor_limit"]
    labelled = item.unit.strip().casefold() in HOUR_UNITS or bool(re.search(r"\bassembly\b", item.description, re.I))
    label_switch = labelled and 1 - row["p_valid"] < REJECT_P
    votes = defaultdict(list)
    for member, witness in row["readers"].items():
        value = witness["value"]
        support = bool(value and 1 - value["validity"] < REJECT_P and
                       abs(value["gross_median"] - native) < abs(value["gross_median"] - factor))
        votes[member.split("/", 1)[0]].append(support)
    supporting = sorted(model for model, efforts in votes.items() if all(efforts))
    return dict(index=row["index"], description=item.description, unit=item.unit, charge_price=row["charge_price"],
                factor=factor, fable=native, hybrid=row["acceptance_limit"],
                label_only=native if label_switch else factor, vote_only=native if len(supporting) >= 2 else factor,
                label_matches=labelled, fable_p_valid=row["p_valid"], vote_models=supporting)
