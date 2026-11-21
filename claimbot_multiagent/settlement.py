"""Normalize the printed invoice table once and adapt the readers to Fable."""
import re
from collections import defaultdict
from dataclasses import dataclass

from claimbot_fable.schema import AggregateLimit, Anchor, ReaderCase, ReaderLine

from .schema import Assessment, Valuation


@dataclass(frozen=True)
class Item:
    position: int
    description: str
    quantity: float
    unit: str


def invoice_items(text):
    items = []
    table = False
    # Poppler preserves columns, pypdf emits a single space between cells.
    # A wrapped description may precede the quantity in plain PDF extraction.
    pending = []
    quantity_unit = r"(\d+(?:[.,]\d+)?)\s+([A-Za-z€²³][\w²³/%.-]*(?: rate)?)"
    row = re.compile(r"^(\d+)\s+(.+?)\s+" + quantity_unit + r"$")
    for raw in text.splitlines():
        line = raw.strip()
        if re.search(r"POS\.?\s+DESCRIPTION\s+AMOUNT\s+UNIT", line, re.I):
            table = True
            continue
        if line.startswith("Created on") or line == "INVOICE":
            table = False
        if not table or not line:
            continue
        if pending:
            pending.append(line)
            if not re.fullmatch(quantity_unit, line):
                continue
            line = " ".join(pending)
            pending = []
        match = row.fullmatch(line)
        if match:
            pos, description, quantity, unit = match.groups()
            items.append(Item(int(pos), description, float(quantity.replace(",", ".")), unit))
        elif re.match(r"^\d+\s", line):
            pending = [line]
        elif items:
            last = items[-1]
            items[-1] = Item(last.position, last.description + " " + line, last.quantity, last.unit)
    if pending:
        raise ValueError(f"unreadable invoice position: {pending[0]}")
    if not items or len({i.position for i in items}) != len(items):
        raise ValueError("missing or duplicate printed invoice positions")
    return items


def position_rows(rows, indices):
    grouped = defaultdict(list)
    for row in rows:
        if row.position not in indices:
            raise ValueError(f"unexpected printed position {row.position}")
        grouped[row.position].append(row)
    return grouped


def specialist_line(item, index, coverage, attribution, quotes):
    if len(coverage) != 1 or len(attribution) != 1:
        raise ValueError("missing or duplicate eligibility finding")
    c, a = coverage[0], attribution[0]
    unit = item.unit.casefold()
    if a.invoice_unit.casefold() != unit:
        raise ValueError("attribution uses a different invoice unit")
    eligible = c.covered and a.related and c.payout_fraction > 0
    valid = [q for q in quotes if q.invoice_unit.casefold() == unit and q.p10 <= q.p50 <= q.p90]
    choices = [q for q in valid if q.basis == c.basis]
    if not choices and c.basis in {"repair", "service"}:
        choices = [q for q in valid if q.basis == "invoice_work"]
    if not choices and not eligible:
        choices = valid  # A unique as-valid market quote supports the configured excluded-line strategy.
    if len(choices) != 1:
        raise ValueError(f"no unique {c.basis} quote in {item.unit}")
    q = choices[0]
    if q.operations is None or q.invoice_units_per_operation is None:
        raise ValueError("unsupported conversion to invoice units")
    reasonable = q.operations * q.invoice_units_per_operation
    quantity = reasonable
    if eligible:
        if q.fixed_fee and a.related_share < 1 and a.attributable_invoice_units is None:
            raise ValueError("partial work with unknown attributable fixed-fee count")
        if not q.fixed_fee:
            quantity *= a.related_share
        if a.attributable_invoice_units is not None:
            quantity = min(quantity, a.attributable_invoice_units)
        if quantity <= 0:
            raise ValueError("eligible work has no justified invoice units")
    return ReaderLine(index=index, invoice_text=item.description, unit=item.unit,
        quantity_invoiced=item.quantity, quantity_justified=min(item.quantity, quantity),
        covered=c.covered, related=a.related,
        p_valid=c.probability_if_related * a.probability if eligible else 0,
        net_unit_price_p10=q.p10, net_unit_price_p50=q.p50, net_unit_price_p90=q.p90,
        vat_rate=q.vat, payout_fraction=c.payout_fraction,
        rationale=f"{c.clause} | {a.evidence} | {q.operations} {q.operation} × "
                  f"{q.invoice_units_per_operation} {item.unit} | {q.inclusions} | {q.source}")


def group_key(group):
    if isinstance(group, AggregateLimit):
        return ("cap", tuple(sorted(group.line_indices)), group.amount_gross)
    return (group.kind, tuple(sorted(group.line_indices)), group.total_gross)


def assemble(items, assessment, valuation, fallback=None):
    indices = {item.position: index for index, item in enumerate(items)}
    def members(positions):
        if not positions or len(set(positions)) != len(positions) or not set(positions) <= indices.keys():
            raise ValueError(f"invalid group positions {positions}")
        return [indices[p] for p in positions]

    caps = [AggregateLimit(line_indices=members(x.positions), amount_gross=x.amount_gross, clause=x.clause)
            for x in assessment.limits]
    anchors = [Anchor(line_indices=members(x.positions), total_gross=x.total_gross, kind=x.kind, quote=x.quote)
               for x in valuation.anchors]
    groups = {group_key(g): g for g in [*caps, *anchors]}
    grouped = [position_rows(rows, indices) for rows in (assessment.coverage, assessment.attribution, valuation.quotes)]
    reasons = {}
    lines = {}
    for i, item in enumerate(items):
        try:
            lines[i] = specialist_line(item, i, *(rows[item.position] for rows in grouped))
        except ValueError as exc:
            reasons[i] = str(exc)
    if fallback is not None:
        other = {group_key(g): g for g in [*fallback.aggregate_limits, *fallback.anchors]}
        # Any disputed membership, amount or kind is resolved as a single connected group.
        affected = {i for key in groups.keys() ^ other.keys() for i in key[1]}
        all_keys = groups.keys() | other.keys()
        while True:
            expanded = affected.union(*(key[1] for key in all_keys if affected.intersection(key[1])))
            if expanded == affected:
                break
            affected = expanded
        for i in affected:
            reasons[i] = "disputed cap or anchor group"
        groups = {k: v for k, v in groups.items() if not affected.intersection(k[1])}
        groups.update({k: v for k, v in other.items() if affected.intersection(k[1])})
        for line in fallback.lines:
            if line.index in reasons:
                lines[line.index] = line
    elif reasons:
        raise ValueError(", ".join(f"position {items[i].position}: {reason}" for i, reason in reasons.items()))
    estimate = ReaderCase(damage_summary="Invoice assessment", policy_notes="See per-line evidence",
        lines=[lines[i] for i in range(len(items))],
        aggregate_limits=[g for g in groups.values() if isinstance(g, AggregateLimit)],
        anchors=[g for g in groups.values() if isinstance(g, Anchor)])
    return estimate, {item.position: reasons[i] for i, item in enumerate(items) if i in reasons}


def combine(items, assessment: Assessment, valuation: Valuation):
    return assemble(items, assessment, valuation)[0]
